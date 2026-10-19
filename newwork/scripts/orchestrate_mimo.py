#!/usr/bin/env python3
"""orchestrate_mimo.py - hand a well-specified, repetitive subtask to MiMo Desktop.

WHY THIS EXISTS
---------------
In this project the *orchestrator* (the main agent / you) owns:
    - decisions, decomposition, and all "hard thinking"
    - the final deliverable and every judgement call
and MiMo Desktop owns:
    - rule-clear, prompt-clear, repetitive labour (bulk extraction, file sweeps,
      lookups, reformatting) that would otherwise burn the orchestrator's context.

This script is the hand-off mechanism:

    read a brief file  ->  submit it to a MiMo session  ->  watch until idle
    ->  capture the final assistant reply  ->  write it to an output file

A brief must be SELF-CONTAINED (MiMo cannot see the orchestrator's conversation):
state the input paths, the exact output format, and the acceptance criteria.

LATENCY WARNING
---------------
A MiMo agentic turn is slow. A trivial-looking extraction over 11 files has been
observed to take ~15 minutes, and there can be multi-minute gaps between visible
events. That is normal, not a hang. This script therefore prints a HEARTBEAT to
stderr every `--heartbeat` seconds so the operator can tell "alive but slow" from
"actually stuck". Increase --timeout for real workloads.

USAGE
-----
    python orchestrate_mimo.py \
        --brief-file briefs/metadata-audit.md \
        --out work/mimo_metadata_audit.md \
        --workspace "C:/path/to/project"     # picks the MiMo session bound to it
or
    python orchestrate_mimo.py --brief "…inline brief…" --out result.md --session ses_xxx

Options:
    --brief / --brief-file   exactly one is required
    --out                    where to save MiMo's final reply (required)
    --session                explicit MiMo session id
    --workspace              if --session omitted, auto-pick the session bound to
                             this directory (falls back to the most recently updated)
    --timeout                seconds to wait for completion (default 1800)
    --heartbeat              seconds between liveness lines (default 60, 0=off)
    --quiet                  don't echo the live event stream

Exit codes: 0 = captured a reply (whether by idle or timeout), 1 = no reply at all.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.join(HERE, "..", "skills", "mimo-desktop-bridge", "mimo_bridge.py")


def load_bridge():
    """Import mimo_bridge.py by path so this script stays location-independent."""
    path = os.path.normpath(BRIDGE)
    if not os.path.isfile(path):
        sys.exit(f"bridge not found: {path}")
    spec = importlib.util.spec_from_file_location("mimo_bridge", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pick_session(bridge, workspace: str | None) -> str:
    base, token = bridge.load_endpoint()
    status, payload = bridge.request("GET", "/sessions?limit=200", token, base)
    if status != 200 or not payload:
        sys.exit(f"cannot list sessions (HTTP {status})")
    if workspace:
        target = os.path.normcase(os.path.normpath(workspace))
        for s in payload:
            d = s.get("directory")
            if d and os.path.normcase(os.path.normpath(d)) == target:
                return s["id"]
    payload = sorted(payload, key=lambda s: (s.get("time") or {}).get("updated") or 0, reverse=True)
    return payload[0]["id"]


def last_assistant_text(bridge, session: str) -> str:
    base, token = bridge.load_endpoint()
    status, payload = bridge.request("GET", f"/sessions/{session}/messages", token, base)
    if status != 200 or not payload:
        return ""
    for msg in reversed(payload):
        info = msg.get("info") or {}
        if info.get("role") != "assistant":
            continue
        texts = [p.get("text", "") for p in (msg.get("parts") or []) if p.get("type") == "text"]
        body = "\n".join(t for t in texts if t).strip()
        if body:
            return body
    return ""


def watch(bridge, session: str, timeout: float, heartbeat: float, quiet: bool) -> str:
    """Stream the SSE feed until idle. Returns 'idle' | 'timeout' | 'closed' | 'error'.

    The stream is read in a worker thread (a blocking `for line in resp` loop) while
    the main thread emits periodic heartbeats. We deliberately do NOT use per-read
    socket timeouts: once http.client's chunked reader times out it raises
    `OSError: cannot read from timed out object` on every subsequent read.
    """
    state: dict = {"ended": None}
    t0 = time.time()
    deadline = t0 + timeout
    poll = max(1.0, heartbeat) if heartbeat else 30.0

    def worker() -> None:
        try:
            base, token = bridge.load_endpoint()
            req = urllib.request.Request(base + f"/sessions/{session}/events", method="GET")
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Accept", "text/event-stream")
            event_name = None
            saw_busy = False
            with urllib.request.urlopen(req, timeout=timeout + 60) as resp:
                for raw in resp:
                    if time.time() > deadline:
                        state["ended"] = "timeout"
                        return
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    if line.startswith("event:"):
                        event_name = line[6:].strip()
                        continue
                    if not line.startswith("data:"):
                        continue                                  # includes ": ping"
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
                        bridge._render_event(kind, evt)
                    if kind == "idle" and saw_busy:
                        state["ended"] = "idle"
                        return
                    if kind == "closed":
                        state["ended"] = "closed"
                        return
            state["ended"] = "closed"
        except Exception as e:                                    # noqa: BLE001
            state["ended"] = "error"
            state["err"] = repr(e)

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    while th.is_alive():
        th.join(timeout=poll)
        if time.time() > deadline:
            # Hard deadline: the worker only re-checks when a line arrives (the
            # server pings every 25s), so enforce it here instead. The daemon
            # reader thread is abandoned; the process exits shortly after.
            state["ended"] = state["ended"] or "timeout"
            break
        if th.is_alive():
            print(f"[heartbeat] alive {time.time() - t0:.0f}s / {timeout:.0f}s", file=sys.stderr)
    ended = state["ended"] or "error"
    if ended == "error":
        print(f"[heartbeat] stream error: {state.get('err')}", file=sys.stderr)
    else:
        print(f"[heartbeat] ended={ended} after {time.time() - t0:.0f}s", file=sys.stderr)
    return ended


def main() -> int:
    ap = argparse.ArgumentParser(description="Hand a self-contained subtask to MiMo Desktop.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--brief", help="inline brief text")
    g.add_argument("--brief-file", help="path to a brief file")
    ap.add_argument("--out", required=True, help="save MiMo's final reply here")
    ap.add_argument("--session", default=None, help="explicit MiMo session id")
    ap.add_argument("--workspace", default=None, help="dir to match a session against")
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--heartbeat", type=float, default=60.0, help="seconds between liveness lines (0=off)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    brief = args.brief if args.brief else open(args.brief_file, encoding="utf-8").read()
    if not brief.strip():
        sys.exit("brief is empty")

    bridge = load_bridge()
    session = args.session or pick_session(bridge, args.workspace)
    if not args.quiet:
        print(f"[orchestrator] session = {session}", file=sys.stderr)
        print(f"[orchestrator] brief   = {len(brief)} chars", file=sys.stderr)

    base, token = bridge.load_endpoint()
    prefs = bridge.load_prefs()
    body = {"message": brief, "model": prefs.get("model") or "mimo-x-pro-preview"}
    if prefs.get("perm"):
        body["perm"] = prefs["perm"]
    if args.workspace:
        body["dir"] = args.workspace

    status, payload = bridge.request("POST", f"/sessions/{session}/turns", token, base, body)
    if not args.quiet:
        print(f"[orchestrator] submit -> HTTP {status} {json.dumps(payload, ensure_ascii=False)}", file=sys.stderr)
    if status != 202:
        sys.exit(f"submit failed: HTTP {status} {payload}")

    t0 = time.time()
    ended = watch(bridge, session, args.timeout, args.heartbeat, args.quiet)
    reply = last_assistant_text(bridge, session)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(reply)

    note = {"idle": "completed normally",
            "timeout": "TIMED OUT (reply may be partial - re-read the session or raise --timeout)",
            "closed": "stream closed by server",
            "error": "stream error (see heartbeat line above)"}[ended]
    print(f"[orchestrator] ended={ended} ({note}) after {time.time() - t0:.0f}s; "
          f"reply {len(reply)} chars -> {args.out}", file=sys.stderr)
    return 0 if reply else 1


if __name__ == "__main__":
    raise SystemExit(main())
