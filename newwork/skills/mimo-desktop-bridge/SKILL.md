---
name: mimo-desktop-bridge
description: Drive Xiaomi MiMo Desktop (小米 MiMo 桌面版) from an external agent — submit tasks, stream live execution events, and read back deliverables through its undocumented localhost HTTP API. Use when the user wants to hand a planned task off to MiMo Desktop, check its sessions, watch a running turn, or orchestrate it as an executor. Triggers on "控制 MiMo Desktop", "交给 MiMo 执行", "MiMo 会话", "mimo desktop 桥接".
agent_created: true
---

# MiMo Desktop Bridge

Xiaomi MiMo Desktop is an Electron app (install: `%LOCALAPPDATA%\Programs\Xiaomi MiMo\`)
that runs an opencode-derived engine and exposes an **undocumented localhost HTTP API**
on a random port, guarded by a per-launch bearer token.

This skill lets an external agent act as the *orchestrator* (plan → hand off → collect)
while MiMo Desktop acts as the *executor*.

## Discovery: how the endpoint is found

On every launch MiMo writes a credential file:

```
%APPDATA%\Xiaomi MiMo\desktop-api.json
{"api":1,"port":41166,"token":"<64-hex>","pid":23328}
```

- Port is random per launch — always re-read the file, never hardcode.
- Token rotates each launch.
- Server rejects requests whose `Host` header is not exactly `127.0.0.1:<port>` or `localhost:<port>`.
- Auth header: `Authorization: Bearer <token>`. Missing/wrong token → `401 {"code":"unauthorized"}`.

Verify with `GET /health` → `{"ok":true,"api":1,"app":"<ver>","engine":"ready"}`.

## The complete route table (api v1)

There are only five routes. All paths are absolute from the root (no extra prefix beyond `/v1`):

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/health` | liveness + engine state |
| GET | `/v1/sessions?limit=N` | list sessions (limit default 200, max 2000) |
| GET | `/v1/sessions/{sid}/messages?dir=` | full transcript |
| GET | `/v1/sessions/{sid}/events?dir=` | **SSE live event feed** |
| POST | `/v1/sessions/{sid}/turns` | **submit a task** → `202 {"ok":true}` |
| GET | `/v1/sessions/{sid}/files?u=<path>&dir=` | read a produced file |

`{sid}` must match `^[A-Za-z0-9_.-]+$`.

### POST /v1/sessions/{sid}/turns — request body

```json
{
  "message": "required, non-empty string",
  "model":   "required, e.g. mimo-x-pro-preview",
  "dir":     "optional working directory",
  "perm":    "optional permission mode, e.g. 完全访问权限",
  "origin":  "optional",
  "files":   ["optional", "attachment", "paths"],
  "plugins": ["optional", "plugin", "ids"]
}
```

`message` and `model` are both mandatory — omitting either returns
`400 {"code":"bad-request"}`. This is the cheapest way to probe the route.

Read defaults from `%APPDATA%\Xiaomi MiMo\preferences.json`:
`model` (e.g. `mimo-x-pro-preview`), `perm`, `fullAccessEnabled`.

### GET /v1/sessions/{sid}/events — SSE event types

`meta`, `busy`, `permission`, `ui`, `text-partial`, `idle`, `closed`.

- `ui` payloads carry `{kind: "title"|"text"|"tool"|"usage", ...}`.
  `ui.kind == "usage"` reports token accounting per model call.
- A turn is finished when `idle` arrives after at least one `busy`.
- The stream keeps the connection open; server sends `: ping` every 25 s.

## Hard limitations

- **No session-creation endpoint.** The API can only drive *existing* sessions.
  A session must be created once in the MiMo Desktop UI (which also pins its
  working directory). Then it can be driven headlessly, forever.
- **No session deletion** either. Anything you submit is appended to the user's
  real conversation history and consumes their quota.
- The engine may report `not-logged-in` (503) — MiMo needs a signed-in Xiaomi
  account or a configured API key.

## Latency & liveness — read this before you think it is hung

A MiMo agentic turn is **slow**, and it goes quiet for minutes at a time. Measured
on one trivial extraction task (11 text files, 6 tool turns):

| Observation | Value |
|---|---|
| Total wall time | **~15 min** |
| Longest silent gap (no events at all) | **~9 min** |
| Bridge `--timeout 900` | expired first, **but the reply was already complete** |

Rules that follow from this:

1. **A silent stream is not a stuck stream.** The server pings every 25 s; visible
   events may be much rarer than that.
2. **Always set a generous `--timeout`** (≥1800 s for real work) and print a
   heartbeat so "alive but slow" is distinguishable from "dead".
3. **On timeout, read the transcript before retrying.** MiMo often has finished:
   `mimo_bridge.py messages <sid> --max-chars 4000`. Re-submitting the turn wastes
   the user's quota and appends a duplicate to their real history.
4. **Do NOT add a socket timeout to the SSE reader to implement a heartbeat.**
   `http.client`'s chunked reader is permanently broken by a read timeout — every
   later read raises `OSError: cannot read from timed out object`. Read the stream
   in a worker thread and heartbeat from the main thread instead
   (see `../../scripts/orchestrate_mimo.py::watch`).
5. **MiMo over-engineers.** It will turn "read these files and extract fields" into
   "write a script / call PowerShell to count things". Say explicitly in the brief:
   *direct file reading is enough — do not write scripts or shell out to compute.*

## Usage

The bundled bridge script uses only the Python standard library:

```bash
PY=<python>
$PY mimo_bridge.py health
$PY mimo_bridge.py sessions
$PY mimo_bridge.py messages <sid> --max-chars 500
$PY mimo_bridge.py events  <sid> --timeout 600
$PY mimo_bridge.py run     <sid> "<detailed task brief>" --timeout 1800
$PY mimo_bridge.py file    <sid> <relative/path> --out local_copy
```

`run` = submit + stream until idle, i.e. the full handoff in one call.

## Reverse proxy (stops the port/token churn)

The raw API is annoying to drive because **both the port and the token change on
every MiMo relaunch**, behind a `Host`-header check. `mimo_reverse_proxy.py` fixes
that: it is a stdlib `ThreadingHTTPServer` on a **fixed** local address
(default `127.0.0.1:8848`) that re-reads `desktop-api.json`, injects the correct
`Host` + `Authorization`, and relays everything — including the SSE stream — to the
live upstream. When MiMo restarts, the proxy notices the credential change and
reconnects on the next request, with **no script edits and no restart of your side**.

```bash
$PY skills/mimo-desktop-bridge/mimo_reverse_proxy.py --port 8848 -v
# → [proxy] upstream MiMo API: 127.0.0.1:41166 (pid 23328)
#   [proxy] listening on http://127.0.0.1:8848
```

Then point the whole repo at it with **one** env var — `mimo_bridge.py` honours it
and so does `orchestrate_mimo.py` (no code change):

```bash
export MIMO_BASE_URL=http://127.0.0.1:8848
# (Windows cmd:  set MIMO_BASE_URL=http://127.0.0.1:8848 )
$PY skills/mimo-desktop-bridge/mimo_bridge.py run <sid> "<brief>" --timeout 1800
```

Handy helpers exposed by the proxy itself:

| Path | Purpose |
|---|---|
| `GET /` | browser status page (upstream health + session list) |
| `GET /_proxy/status` | JSON: proxy config + live upstream health |
| `GET /_proxy/sessions` | sessions with `directory` + `updated` (sorted) |
| `GET /_proxy/sessions?dir=<substr>` | filter sessions by working-directory substring |

Flags: `--port` (default 8848) · `--host` (default 127.0.0.1) · `--client-token`
(optional; if set, callers must send `MIMO_TOKEN=<that>`/`Authorization: Bearer`) ·
`--cred-ttl` (seconds to cache the credential file, default 2) · `-v` verbose.

**Reverse proxy vs reverse-engineering — not the same thing:**

- *Reverse-engineering* = figuring out what the undocumented API **is** (the
  routes, the header rules, the body schema). Done once; recorded above.
- *Reverse-proxying* = wrapping the API you now understand behind a **stable
  address** so the volatile bits (port, token, `Host`) are no longer the caller's
  problem. Done once; removes the per-launch churn entirely.

## Orchestration pattern

1. `sessions` → pick the target session; confirm `directory` matches the intended project.
2. Write the plan yourself. Convert it into **one dense, self-contained brief** —
   MiMo does not see this conversation, so every path, constraint and acceptance
   criterion must be spelled out.
3. `run <sid> "<brief>"` and let the event stream run. Watch for `permission`
   events: if the session is not on 完全访问权限, MiMo will block waiting for a
   human click, and the turn will hang until timeout.
4. Collect the result: `messages` for the final text, `files` for artifacts.
5. Verify the artifacts on disk yourself — treat MiMo's summary as a claim.

## Reverse-engineering notes (if the API changes)

Routes live in `resources/app.asar` (plain-text JS despite the extension):

```bash
grep -a -b -o "invalid or missing token" resources/app.asar   # locate the server code
```

The route matcher is the function immediately following that error-code table;
route kinds are produced by a small path parser that whitelists `v1/health`,
`v1/sessions`, `v1/sessions/{sid}/{messages|events|turns|files}`.
The turn body schema is parsed in the `case"turns"` handler near `sendTurn(...)`.
