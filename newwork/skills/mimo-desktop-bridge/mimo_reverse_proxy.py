#!/usr/bin/env python3
"""mimo_reverse_proxy.py - a stable local endpoint in front of MiMo Desktop's
undocumented (and per-launch random) localhost API.

WHY
---
MiMo Desktop writes a NEW random port and a NEW bearer token every launch into
`%APPDATA%\\Xiaomi MiMo\\desktop-api.json`. It also rejects any request whose
`Host` header is not exactly `127.0.0.1:<that port>`. So every caller otherwise
has to: read the json, remember the port, remember the token, and re-do all of
that after every restart.

This proxy fixes that once:

    caller  ->  http://127.0.0.1:8848/v1/...        (stable, no token needed)
            ->  proxy re-reads the credential file, injects
                Host: 127.0.0.1:<real port>  +  Authorization: Bearer <token>
            ->  MiMo Desktop API

Features
--------
* **Transparent passthrough** for every `/v1/*` route, including the SSE feed
  (`/v1/sessions/{sid}/events`) which is streamed, never buffered.
* **Credential auto-refresh**: re-reads `desktop-api.json` (cached for
  `--cred-ttl` seconds) and retries once on a connection error, so restarting
  MiMo does NOT require restarting callers.
* **Browser status page** at `/` : upstream port/pid, health, and the session
  list with each session's working directory - so "which session do I use?"
  becomes a glance instead of a script.
* **Discovery helpers**: `/_proxy/status`, `/_proxy/sessions[?dir=...]`.

What it deliberately does NOT do
--------------------------------
* It cannot create or delete sessions - the API has no such route. A session
  must still be created once in the MiMo Desktop UI.
* It does not bypass anything: it is still your own local app, your own quota.
* It does not make MiMo fast. A MiMo turn is genuinely 15-25 min of work; the
  real speed lever is running several sessions in parallel.

USAGE
-----
    python mimo_reverse_proxy.py                 # binds 127.0.0.1:8848
    python mimo_reverse_proxy.py --port 9000 -v

Then, from any other tool:
    curl http://127.0.0.1:8848/health
    curl http://127.0.0.1:8848/v1/sessions
    curl -N http://127.0.0.1:8848/v1/sessions/<sid>/events

Callers in this repo pick it up automatically when `MIMO_BASE_URL` is set
(see mimo_bridge.load_endpoint):
    MIMO_BASE_URL=http://127.0.0.1:8848 python orchestrate_mimo.py ...

Stdlib only. Nothing is written to disk.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --------------------------------------------------------------- credentials


def _user_data_dir() -> str:
    appdata = os.environ.get("APPDATA")
    if appdata and os.path.isdir(appdata):
        return os.path.join(appdata, "Xiaomi MiMo")
    return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Xiaomi MiMo")


CRED_FILE = os.path.join(_user_data_dir(), "desktop-api.json")

_cred_lock = threading.Lock()
_cred_cache: dict = {"at": 0.0, "port": None, "token": None, "pid": None}


class UpstreamUnavailable(RuntimeError):
    pass


def load_upstream(ttl: float, force: bool = False) -> tuple[int, str, int]:
    """Return (port, token, pid) for the live MiMo API.

    Cached for `ttl` seconds so a burst of proxied requests does not hammer the
    disk, but always re-readable - MiMo rotates both port and token per launch.
    """
    now = time.time()
    with _cred_lock:
        if not force and _cred_cache["port"] and (now - _cred_cache["at"]) < ttl:
            return _cred_cache["port"], _cred_cache["token"], _cred_cache["pid"]
        if not os.path.isfile(CRED_FILE):
            raise UpstreamUnavailable(
                f"credential file not found: {CRED_FILE} - is MiMo Desktop running?")
        try:
            with open(CRED_FILE, "r", encoding="utf-8") as fh:
                cred = json.load(fh)
        except Exception as e:  # noqa: BLE001  (partial write during relaunch)
            raise UpstreamUnavailable(f"credential file unreadable: {e!r}")
        port = int(cred["port"])
        _cred_cache.update(at=now, port=port, token=str(cred["token"]),
                           pid=int(cred.get("pid") or 0))
        return _cred_cache["port"], _cred_cache["token"], _cred_cache["pid"]


# ------------------------------------------------------- hop-by-hop stripping

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host",
}


def _clean_headers(headers) -> list[tuple[str, str]]:
    out = []
    for k, v in headers.items():
        if k.lower() in _HOP_BY_HOP:
            continue
        out.append((k, v))
    return out


# ------------------------------------------------------------------- handler


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MiMoReverseProxy/1.0"
    # Push each relayed frame out immediately instead of coalescing small writes
    # (matters for SSE: `: ping` frames are a handful of bytes every 25 s).
    disable_nagle_algorithm = True

    # -- config injected by serve()
    upstream_ttl: float = 2.0
    verbose: bool = False
    client_token: str | None = None

    # ---------- logging
    def log_message(self, fmt, *a):  # noqa: A003
        if self.verbose:
            sys.stderr.write("[proxy] %s - %s\n" % (self.address_string(), fmt % a))

    # ---------- helpers
    def _json(self, code: int, payload) -> None:
        blob = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def _html(self, code: int, body: str) -> None:
        blob = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def _read_body(self) -> bytes | None:
        n = self.headers.get("Content-Length")
        if n:
            try:
                return self.rfile.read(int(n))
            except Exception:  # noqa: BLE001
                return None
        if (self.headers.get("Transfer-Encoding") or "").lower() == "chunked":
            # We do not expect chunked bodies from our own callers; read defensively.
            buf = bytearray()
            while True:
                line = self.rfile.readline().strip()
                if not line:
                    break
                try:
                    size = int(line.split(b";")[0], 16)
                except ValueError:
                    break
                if size == 0:
                    self.rfile.readline()
                    break
                buf += self.rfile.read(size)
                self.rfile.readline()
            return bytes(buf)
        return None

    def _authorized(self) -> bool:
        if not self.client_token:
            return True
        got = (self.headers.get("Authorization") or "").strip()
        return got in (f"Bearer {self.client_token}", self.client_token)

    # ---------- routing
    def do_GET(self):  # noqa: N802
        self._dispatch("GET")

    def do_POST(self):  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self):  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self):  # noqa: N802
        self._dispatch("DELETE")

    def do_OPTIONS(self):  # noqa: N802
        self._dispatch("OPTIONS")

    def _dispatch(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "hint": "set Authorization: Bearer <--client-token>"})
            return
        if path in ("/", "/index.html"):
            self._page_index()
            return
        if path == "/_proxy/status":
            self._proxy_status()
            return
        if path == "/_proxy/sessions":
            self._proxy_sessions(parsed.query)
            return
        if path == "/health":            # convenience alias
            self._forward(method, "/v1/health", parsed.query)
            return
        if path.startswith("/v1/") or path == "/v1":
            self._forward(method, path, parsed.query)
            return
        self._json(404, {"error": "not found", "path": path,
                         "hint": "try / , /health , /_proxy/status , or /v1/*"})

    # ---------- local pages
    def _upstream_info(self):
        try:
            port, _tok, pid = load_upstream(self.upstream_ttl)
            return {"ok": True, "port": port, "pid": pid}
        except UpstreamUnavailable as e:
            return {"ok": False, "error": str(e)}

    def _proxy_status(self) -> None:
        up = self._upstream_info()
        info = {"proxy": {"host": self.server.server_address[0],
                          "port": self.server.server_address[1],
                          "client_token_required": bool(self.client_token)},
                "upstream": up}
        if up["ok"]:
            st, payload = self._call_upstream("GET", "/v1/health", "", None)
            info["upstream_health"] = {"http": st, "body": payload}
        self._json(200 if up["ok"] else 503, info)

    def _proxy_sessions(self, query: str) -> None:
        st, payload = self._call_upstream("GET", "/v1/sessions", query or "limit=200", None)
        if st != 200 or not isinstance(payload, list):
            self._json(st or 502, payload)
            return
        qs = urllib.parse.parse_qs(query or "")
        want = (qs.get("dir") or [None])[0]
        rows = []
        for s in payload:
            d = s.get("directory") or ""
            if want:
                if os.path.normcase(os.path.normpath(d)) != os.path.normcase(os.path.normpath(want)):
                    continue
            t = (s.get("time") or {}).get("updated") or 0
            rows.append({"id": s.get("id"), "title": s.get("title"),
                         "directory": d, "projectID": s.get("projectID"),
                         "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(t / 1000)) if t else None})
        rows.sort(key=lambda r: r["updated"] or "", reverse=True)
        self._json(200, rows)

    def _page_index(self) -> None:
        up = self._upstream_info()
        if not up["ok"]:
            self._html(503, f"""<!doctype html><meta charset="utf-8">
<title>MiMo reverse proxy</title>
<style>body{{font-family:system-ui,'Microsoft YaHei',sans-serif;margin:40px;color:#1a2230}}
code{{background:#f2f5f9;padding:2px 6px;border-radius:4px}}.bad{{color:#a32d2d}}</style>
<h1>MiMo 反代</h1>
<p class="bad">上游不可用：{up['error']}</p>
<p>请先启动 MiMo Desktop。</p>""")
            return
        st, health = self._call_upstream("GET", "/v1/health", "", None)
        st2, sessions = self._call_upstream("GET", "/v1/sessions", "limit=200", None)
        rows = ""
        if isinstance(sessions, list):
            for s in sorted(sessions, key=lambda s: (s.get("time") or {}).get("updated") or 0, reverse=True):
                d = s.get("directory") or ""
                t = (s.get("time") or {}).get("updated") or 0
                when = time.strftime("%Y-%m-%d %H:%M", time.localtime(t / 1000)) if t else ""
                rows += (f"<tr><td><code>{s.get('id')}</code></td><td>{s.get('title') or ''}</td>"
                         f"<td><code>{d}</code></td><td>{when}</td></tr>")
        self._html(200, f"""<!doctype html><meta charset="utf-8">
<title>MiMo reverse proxy</title>
<style>
 body{{font-family:system-ui,'Microsoft YaHei',sans-serif;margin:40px;color:#1a2230;line-height:1.6}}
 code{{background:#f2f5f9;padding:2px 6px;border-radius:4px}}
 table{{border-collapse:collapse;margin-top:8px}} td,th{{border:1px solid #d6dce5;padding:6px 10px;font-size:14px}}
 th{{background:#f7f9fc;text-align:left}} h1{{color:#0e3f8c}}
 .row{{background:#f7f9fc;border-left:4px solid #1e4fa8;padding:10px 14px;margin:8px 0;border-radius:6px}}
</style>
<h1>MiMo 反代 · 运行中</h1>
<div class="row">代理地址 <code>http://{self.server.server_address[0]}:{self.server.server_address[1]}</code><br>
上游 MiMo 端口 <code>{up['port']}</code>（pid {up['pid']}）· health: <code>{json.dumps(health, ensure_ascii=False)}</code></div>
<div class="row">直接把任何 <code>/v1/*</code> 请求发到本代理即可，<b>无需知道端口与 token</b>；<br>
SSE 事件流也会原样转发：<code>curl -N http://127.0.0.1:{self.server.server_address[1]}/v1/sessions/&lt;sid&gt;/events</code></div>
<h3>会话（挑一个 <code>directory</code> 对得上的用）</h3>
<table><tr><th>id</th><th>标题</th><th>工作目录</th><th>更新时间</th></tr>{rows}</table>
<p style="color:#8b97a8;font-size:13px">注意：反代不能新建会话。新会话仍需在 MiMo Desktop 界面里建一次。</p>""")

    # ---------- upstream plumbing
    def _call_upstream(self, method: str, path: str, query: str, body: bytes | None,
                       force_cred: bool = False):
        """Non-streaming helper: returns (http_status, parsed_or_raw)."""
        try:
            port, token, _pid = load_upstream(self.upstream_ttl, force=force_cred)
        except UpstreamUnavailable as e:
            return 503, {"error": "upstream unavailable", "detail": str(e)}
        url = path + (("?" + query) if query else "")
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
        try:
            headers = {"Host": f"127.0.0.1:{port}", "Authorization": f"Bearer {token}",
                       "Accept": "application/json"}
            if body is not None:
                headers["Content-Type"] = "application/json"
            conn.request(method, url, body=body, headers=headers)
            resp = conn.getresponse()
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw) if raw.strip() else None
            except Exception:  # noqa: BLE001
                return resp.status, raw
        except Exception as e:  # noqa: BLE001
            return 502, {"error": "upstream connect failed", "detail": repr(e)}
        finally:
            conn.close()

    def _forward(self, method: str, path: str, query: str) -> None:
        body = self._read_body()
        url = path + (("?" + query) if query else "")
        for attempt in (1, 2):
            try:
                port, token, _pid = load_upstream(self.upstream_ttl, force=(attempt == 2))
            except UpstreamUnavailable as e:
                self._json(503, {"error": "upstream unavailable", "detail": str(e),
                                 "hint": "start MiMo Desktop"})
                return
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=None)
            try:
                headers = {"Host": f"127.0.0.1:{port}",
                           "Authorization": f"Bearer {token}",
                           "Accept": self.headers.get("Accept") or "*/*"}
                if body is not None:
                    headers["Content-Type"] = self.headers.get("Content-Type") or "application/json"
                conn.request(method, url, body=body, headers=headers)
                resp = conn.getresponse()
            except Exception as e:  # noqa: BLE001
                conn.close()
                if attempt == 1:
                    # MiMo may have restarted (new port/token) between calls; retry
                    # once with a forced credential re-read.
                    self.log_message("upstream connect failed (%r), retrying with fresh creds", e)
                    continue
                self._json(502, {"error": "upstream connect failed", "detail": repr(e)})
                return

            self._relay(resp)
            conn.close()
            return

    def _relay(self, resp) -> None:
        """Relay an upstream response, streaming (never buffering) when unbounded."""
        status = resp.status
        hdrs = _clean_headers(resp.headers)
        length = resp.headers.get("Content-Length")
        chunked = resp.headers.get("Transfer-Encoding", "").lower() == "chunked" \
            or (length is None and status not in (204, 304))

        self.send_response(status)
        for k, v in hdrs:
            self.send_header(k, v)
        if length is not None:
            self.send_header("Content-Length", length)
        elif chunked:
            self.send_header("Transfer-Encoding", "chunked")
        else:
            self.send_header("Connection", "close")
        # SSE must not be cached anywhere on the way
        if "event-stream" in (resp.headers.get("Content-Type") or ""):
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        try:
            # NOTE: use read1(), NOT read(). On a buffered/chunked reader,
            # read(n) blocks until it has n bytes (or EOF) - for an SSE stream
            # whose frames are tiny (`: ping` every 25 s) that means "never
            # forward anything". read1() returns after a single underlying read,
            # i.e. one chunk / one flush-worth of bytes, so the stream flows.
            if length is not None:
                remaining = int(length)
                while remaining > 0:
                    buf = resp.read1(min(65536, remaining))
                    if not buf:
                        break
                    self.wfile.write(buf)
                    self.wfile.flush()
                    remaining -= len(buf)
            elif chunked:
                while True:
                    buf = resp.read1(65536)
                    if not buf:
                        break
                    self.wfile.write(b"%X\r\n" % len(buf) + buf + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            else:
                while True:
                    buf = resp.read1(65536)
                    if not buf:
                        break
                    self.wfile.write(buf)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            self.log_message("client disconnected mid-stream")
        finally:
            try:
                resp.close()
            except Exception:  # noqa: BLE001
                pass


# --------------------------------------------------------------------- serve


def main() -> int:
    ap = argparse.ArgumentParser(description="Stable reverse proxy for MiMo Desktop's local API.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8848)
    ap.add_argument("--cred-ttl", type=float, default=2.0,
                    help="seconds to cache the port/token read (default 2)")
    ap.add_argument("--client-token", default=None,
                    help="optional: require this bearer token from callers")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    ProxyHandler.upstream_ttl = args.cred_ttl
    ProxyHandler.verbose = args.verbose
    ProxyHandler.client_token = args.client_token

    try:
        port, _tok, pid = load_upstream(0.0)
        print(f"[proxy] upstream MiMo API: 127.0.0.1:{port} (pid {pid})", file=sys.stderr)
    except UpstreamUnavailable as e:
        print(f"[proxy] WARNING: {e}", file=sys.stderr)
        print("[proxy] (the proxy will still serve; it retries on each request)", file=sys.stderr)

    try:
        httpd = ThreadingHTTPServer((args.host, args.port), ProxyHandler)
    except OSError as e:
        print(f"[proxy] cannot bind {args.host}:{args.port} -> {e}", file=sys.stderr)
        return 1
    httpd.daemon_threads = True
    base = f"http://{args.host}:{args.port}"
    print(f"[proxy] listening on {base}", file=sys.stderr)
    print(f"[proxy]   status page : {base}/", file=sys.stderr)
    print(f"[proxy]   health      : {base}/health", file=sys.stderr)
    print(f"[proxy]   sessions    : {base}/_proxy/sessions", file=sys.stderr)
    print(f"[proxy]   passthrough : {base}/v1/*", file=sys.stderr)
    print(f"[proxy] hint: export MIMO_BASE_URL={base} to route the repo's scripts through it",
          file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[proxy] bye", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
