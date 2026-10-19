"""Dump per-message head/tail of a MiMo session (head/tail only, not truncated)."""
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.normpath(os.path.join(HERE, "..", "mimo_bridge.py"))
spec = importlib.util.spec_from_file_location("mb", BRIDGE)
mb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mb)

base, token = mb.load_endpoint()
sid = 'ses_ffe5f6103a281ffeawsHEYMgWq'
status, payload = mb.request('GET', f'/sessions/{sid}/messages', token, base)
print('status', status, 'n', len(payload or []))
for i, m in enumerate(payload or []):
    info = m.get('info') or {}
    role = info.get('role', '?')
    ts = info.get('time') or {}
    created = ts.get('created') if isinstance(ts, dict) else ts
    parts = m.get('parts') or []
    texts = [p.get('text', '') for p in parts if p.get('type') == 'text']
    body = '\n'.join(t for t in texts if t)
    print(f'\n### [{i}] role={role} created={created} len={len(body)}')
    print('TAIL:', repr(body[-260:]))
