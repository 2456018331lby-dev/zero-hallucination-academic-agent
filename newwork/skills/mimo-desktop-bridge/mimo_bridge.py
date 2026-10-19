#!/usr/bin/env python3
"""
mimo_bridge.py - Drive Xiaomi MiMo Desktop from the outside.

Discovers the local Desktop API (port + bearer token) from
%APPDATA%\\Xiaomi MiMo\\desktop-api.json and exposes:

    health                       probe the API
    sessions  [--limit N]        list sessions (id, title, dir)
    messages  <sid>              dump a session transcript
    events    <sid> [--timeout]  stream the SSE event feed
    send      <sid> "<message>"  submit one turn (async, returns 202)
    run       <sid> "<message>"  submit + stream until idle, print result
    file      <sid> <path>       read a file the session produced

No third-party dependencies: urllib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def _user_data_dir() -> str:
    """%APPDATA%\\Xiaomi MiMo, with a home-relative fallback for stripped envs."""
    appdata = os.environ.get("APPDATA")
    if appdata and os.path.isdir(appdata):
        return os.path.join(appdata, "Xiaomi MiMo")
    return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Xiaomi MiMo")


USER_DATA = _user_data_dir()
CRED_FILE = os.path.join(USER_DATA, "desktop-api.json")
PREFS_FILE = os.path.join(USER_DATA, "preferences.json")


class BridgeError(RuntimeError):
    pass


def load_endpoint() -> tuple[str, str]:
    """Return (base_url, token) from the desktop-api.json credential file.

    Honours `MIMO_BASE_URL`: if set (e.g. `http://127.0.0.1:8848`), all calls go
    through that reverse proxy instead of the rotating port. The proxy injects
    the real `Host` + `Authorization` itself, so the token returned here is only
    a placeholder -- unless the proxy was started with --client-token, in which
    case set MIMO_TOKEN to the same value.
    """
    env_base = (os.environ.get("MIMO_BASE_URL") or "").strip().rstrip("/")
    if env_base:
        if not env_base.endswith("/v1"):
            env_base += "/v1"
        return env_base, (os.environ.get("MIMO_TOKEN") or "via-reverse-proxy")

    if not os.path.isfile(CRED_FILE):
        raise BridgeError(
            f"credential file not found: {CRED_FILE}\n"
            "Is MiMo Desktop running?"
        )
    with open(CRED_FILE, "r", encoding="utf-8") as fh:
        cred = json.load(fh)
    port = int(cred["port"])
    token = str(cred["token"])
    # host check on the server side requires 127.0.0.1:<port> exactly
    return f"http://127.0.0.1:{port}/v1", token


def load_prefs() -> dict:
    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def request(method: str, path: str, token: str, base: str,
            body: dict | None = None, timeout: float = 60.0):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


# ---------------------------------------------------------------- commands

def cmd_health(args) -> int:
    base, token = load_endpoint()
    status, payload = request("GET", "/health", token, base)
    print(f"HTTP {status}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status == 200 else 1


def cmd_sessions(args) -> int:
    base, token = load_endpoint()
    status, payload = request("GET", f"/sessions?limit={args.limit}", token, base)
    if status != 200:
        print(f"HTTP {status}: {payload}", file=sys.stderr)
        return 1
    for s in payload or []:
        print(f"{s.get('id')}")
        print(f"    title   : {s.get('title')}")
        print(f"    slug    : {s.get('slug')}")
        print(f"    dir     : {s.get('directory')}")
        print(f"    project : {s.get('projectID')}")
        t = s.get("time") or {}
        if t.get("updated"):
            print(f"    updated : {time.strftime('%Y-%m-%d %H:%M', time.localtime(t['updated'] / 1000))}")
    return 0


def cmd_messages(args) -> int:
    base, token = load_endpoint()
    status, payload = request("GET", f"/sessions/{args.session}/messages", token, base)
    if status != 200:
        print(f"HTTP {status}: {payload}", file=sys.stderr)
        return 1
    for msg in payload or []:
        info = msg.get("info") or {}
        role = info.get("role", "?")
        parts = msg.get("parts") or []
        texts = [p.get("text", "") for p in parts if p.get("type") == "text"]
        body = "\n".join(t for t in texts if t)
        print(f"--- {role} ---")
        print(body[: args.max_chars] if body else "(no text part)")
        print()
    return 0


def _stream_events(session: str, timeout: float, quiet: bool, stop_on_idle: bool) -> None:
    base, token = load_endpoint()
    req = urllib.request.Request(base + f"/sessions/{session}/events", method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "text/event-stream")
    deadline = time.time() + timeout
    saw_busy = False
    with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
        event_name = None
        for raw in resp:
            if time.time() > deadline:
                if not quiet:
                    print("[bridge] timeout reached", file=sys.stderr)
                break
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if line.startswith("event:"):
                event_name = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                evt = json.loads(payload)
            except Exception:
                continue
            kind = evt.get("type") or event_name
            if kind == "busy":
                saw_busy = True
            if not quiet:
                _render_event(kind, evt)
            if stop_on_idle:
                if kind == "idle" and saw_busy:
                    return
                if kind == "closed":
                    return


def _render_event(kind: str, evt: dict) -> None:
    if kind == "ui":
        ui = evt.get("ui") or {}
        k = ui.get("kind")
        if k == "text":
            print(ui.get("text", ""))
        elif k == "tool":
            name = ui.get("name") or ui.get("tool") or "?"
            print(f"[tool] {name}")
        else:
            print(f"[ui:{k}] {json.dumps(ui, ensure_ascii=False)[:300]}")
    elif kind == "permission":
        print(f"[permission] {json.dumps(evt.get('req', {}), ensure_ascii=False)[:300]}")
    elif kind == "text-partial":
        print(f"[partial] {evt.get('text', '')}")
    elif kind in ("meta", "busy", "idle", "closed"):
        print(f"[{kind}]")
    else:
        print(f"[{kind}] {json.dumps(evt, ensure_ascii=False)[:300]}")


def cmd_events(args) -> int:
    _stream_events(args.session, args.timeout, args.quiet, stop_on_idle=False)
    return 0


def cmd_send(args) -> int:
    base, token = load_endpoint()
    prefs = load_prefs()
    model = args.model or prefs.get("model") or "mimo-x-pro-preview"
    body: dict = {"message": args.message, "model": model}
    if args.perm:
        body["perm"] = args.perm
    elif prefs.get("perm"):
        body["perm"] = prefs["perm"]
    if args.dir:
        body["dir"] = args.dir
    if args.files:
        body["files"] = args.files.split(",")
    status, payload = request("POST", f"/sessions/{args.session}/turns", token, base, body)
    print(f"HTTP {status} {json.dumps(payload, ensure_ascii=False)}")
    if status == 202 and not args.no_watch:
        print("[bridge] watching events until idle ...", file=sys.stderr)
        _stream_events(args.session, args.timeout, args.quiet, stop_on_idle=True)
    return 0 if status == 202 else 1


def cmd_run(args) -> int:
    """send + watch until idle, then print the final assistant message."""
    args_no_watch = argparse.Namespace(**vars(args))
    args_no_watch.no_watch = True
    rc = cmd_send(args_no_watch)
    if rc != 0:
        return rc
    print("[bridge] watching events until idle ...", file=sys.stderr)
    _stream_events(args.session, args.timeout, args.quiet, stop_on_idle=True)
    return 0


def cmd_file(args) -> int:
    base, token = load_endpoint()
    url = f"{base}/sessions/{args.session}/files?u={urllib.parse.quote(args.path)}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        blob = resp.read()
    if args.out:
        with open(args.out, "wb") as fh:
            fh.write(blob)
        print(f"wrote {len(blob)} bytes -> {args.out}")
    else:
        sys.stdout.write(blob.decode("utf-8", "replace"))
    return 0


import urllib.parse  # noqa: E402  (used by cmd_file)


def main() -> int:
    p = argparse.ArgumentParser(description="Bridge to Xiaomi MiMo Desktop's local API")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health").set_defaults(fn=cmd_health)

    sp = sub.add_parser("sessions")
    sp.add_argument("--limit", type=int, default=200)
    sp.set_defaults(fn=cmd_sessions)

    sp = sub.add_parser("messages")
    sp.add_argument("session")
    sp.add_argument("--max-chars", type=int, default=4000)
    sp.set_defaults(fn=cmd_messages)

    sp = sub.add_parser("events")
    sp.add_argument("session")
    sp.add_argument("--timeout", type=float, default=600)
    sp.add_argument("--quiet", action="store_true")
    sp.set_defaults(fn=cmd_events)

    sp = sub.add_parser("send")
    sp.add_argument("session")
    sp.add_argument("message")
    sp.add_argument("--model", default=None)
    sp.add_argument("--perm", default=None)
    sp.add_argument("--dir", default=None)
    sp.add_argument("--files", default=None, help="comma-separated paths")
    sp.add_argument("--timeout", type=float, default=900)
    sp.add_argument("--quiet", action="store_true")
    sp.add_argument("--no-watch", action="store_true")
    sp.set_defaults(fn=cmd_send)

    sp = sub.add_parser("run")
    sp.add_argument("session")
    sp.add_argument("message")
    sp.add_argument("--model", default=None)
    sp.add_argument("--perm", default=None)
    sp.add_argument("--dir", default=None)
    sp.add_argument("--files", default=None)
    sp.add_argument("--timeout", type=float, default=1800)
    sp.add_argument("--quiet", action="store_true")
    sp.set_defaults(fn=cmd_run)

    sp = sub.add_parser("file")
    sp.add_argument("session")
    sp.add_argument("path")
    sp.add_argument("--out", default=None)
    sp.set_defaults(fn=cmd_file)

    args = p.parse_args()
    try:
        return args.fn(args)
    except BridgeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
