"""Run state: counters, staleness marks, budget, and an append-only event log.

Every command that writes an artifact calls touch(state, name), which advances a global
sequence number. A derived artifact is stale when any of its inputs was touched after it.
"""

import os

from .jsonio import append_jsonl, now_iso, read_json, write_json


def state_path(run, sub=None):
    return os.path.join(run, sub, "state.json") if sub else os.path.join(run, "state.json")


def load(run, sub=None, default=None):
    st = read_json(state_path(run, sub))
    if st is None:
        st = default if default is not None else {}
    st.setdefault("seq", 0)
    st.setdefault("marks", {})
    st.setdefault("budget", {"subagents_used": 0, "fetches_used": 0})
    return st


def save(run, st, sub=None):
    st["updated_at"] = now_iso()
    write_json(state_path(run, sub), st)


def touch(st, name):
    st["seq"] = int(st.get("seq", 0)) + 1
    st.setdefault("marks", {})[name] = st["seq"]
    return st["seq"]


def mark(st, name):
    return st.get("marks", {}).get(name, -1)


def stale(st, derived, inputs):
    d = mark(st, derived)
    if d < 0:
        return True
    return any(mark(st, i) > d for i in inputs)


def event(run, kind, sub=None, **data):
    path = os.path.join(run, sub, "events.jsonl") if sub else os.path.join(run, "events.jsonl")
    append_jsonl(path, {"ts": now_iso(), "kind": kind, "data": data})


def spend(st, key, amount=1):
    b = st.setdefault("budget", {})
    b[key] = int(b.get(key, 0)) + amount
    return b[key]
