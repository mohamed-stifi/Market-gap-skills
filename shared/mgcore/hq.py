"""Human-task queue (HT-NNN): things only the human operator can do.

Secrets are never written here: tasks ask the human to set environment variables.
"""

import os

from .jsonio import now_iso, read_json, write_json

TYPES = ("account", "key", "payment", "legal", "outward-action", "judgment", "directive")


def _path(run):
    return os.path.join(run, "human-tasks.json")


def load(run):
    return read_json(_path(run), {"tasks": []})


def save(run, data):
    write_json(_path(run), data)
    render_md(run, data)


def add(run, type_, title, why, steps, returns, phase, blocking=False, fallback=None, gate=None):
    if type_ not in TYPES:
        raise ValueError("type must be one of %s" % ", ".join(TYPES))
    data = load(run)
    if gate:
        for t in data["tasks"]:
            if t.get("gate") == gate and t["status"] == "open":
                return t
    num = len(data["tasks"]) + 1
    task = {"id": "HT-%03d" % num, "type": type_, "title": title, "why": why, "steps": steps,
            "returns": returns, "phase": phase, "blocking": bool(blocking), "fallback": fallback,
            "status": "open", "note": None, "created_at": now_iso(), "closed_at": None, "gate": gate}
    data["tasks"].append(task)
    save(run, data)
    return task


def close(run, task_id, status, note=None):
    if status not in ("done", "declined"):
        raise ValueError("status must be done or declined")
    data = load(run)
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            t["note"] = note
            t["closed_at"] = now_iso()
            save(run, data)
            return t
    raise KeyError("no such task: %s" % task_id)


def find_gate(run, gate):
    for t in load(run)["tasks"]:
        if t.get("gate") == gate:
            return t
    return None


def latest_gate(run, name):
    """Latest task for a gate, matching 'name' or attempt-numbered 'name#N'."""
    found = None
    for t in load(run)["tasks"]:
        g = t.get("gate") or ""
        if g == name or g.startswith(name + "#"):
            found = t
    return found


def open_tasks(run, blocking_only=False):
    return [t for t in load(run)["tasks"] if t["status"] == "open" and (t["blocking"] or not blocking_only)]


def render_md(run, data=None):
    data = data or load(run)
    lines = ["# Human tasks", "",
             "Only the human operator can do these. Mark them with `hq done RUN HT-NNN --note ...` "
             "or `hq decline RUN HT-NNN --note ...`. Never paste secrets here: set environment variables.", ""]
    for t in data["tasks"]:
        lines.append("## %s · %s · %s%s" % (t["id"], t["status"].upper(), t["title"], " · BLOCKING" if t["blocking"] else ""))
        lines.append("- Type: %s · Phase: %s" % (t["type"], t["phase"]))
        lines.append("- Why: %s" % t["why"])
        lines.append("- Steps: %s" % t["steps"])
        lines.append("- Return: %s" % t["returns"])
        if t.get("fallback"):
            lines.append("- If declined: %s" % t["fallback"])
        if t.get("note"):
            lines.append("- Note: %s" % t["note"])
        lines.append("")
    with open(os.path.join(run, "human-tasks.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
