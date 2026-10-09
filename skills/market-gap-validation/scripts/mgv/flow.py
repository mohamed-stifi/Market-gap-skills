"""`gapval.py next` / `status`: the single next validation action, derived from the run folder.
Outward actions are always human tasks, whatever the autonomy setting."""

import json
import os

from mgcore import hq, state
from mgcore.jsonio import read_json, sha256_json

from .assets import LANDING_TYPES
from .common import SCRIPTS_DIR, cards, load_state, out, p, require, save_state, v
from .data import KINDS_FOR_TYPE
from .prereg import _hash

GAPVAL = os.path.join(SCRIPTS_DIR, "gapval.py")


class Act(Exception):
    def __init__(self, verdict, argline, notes=None, phase=None):
        Exception.__init__(self, verdict)
        self.verdict, self.argline, self.notes, self.phase = verdict, argline, list(notes or []), phase


def RUN(cmd, *notes, **kw):
    raise Act("RUN", "gapval.py " + cmd, notes, kw.get("phase"))


def DO(card, task, *notes, **kw):
    raise Act("DO", "%s %s" % (card, task), notes, kw.get("phase"))


def SPAWN(role, run, paths, *notes, **kw):
    raise Act("SPAWN", "%s %d %s" % (role, len(paths), " ".join(p(run, x) for x in paths)), notes, kw.get("phase"))


def BLOCKED(task, *notes, **kw):
    raise Act("BLOCKED", task["id"], ("human task: %s (%s)" % (task["title"], task["type"]),) + notes, kw.get("phase"))


def _group(run, st, key):
    g = st.get("groups", {}).get(key)
    if not g:
        return None, []
    if g.get("merged"):
        return "merged", []
    missing = []
    for apath in g["paths"]:
        a = read_json(p(run, apath)) or {}
        if any(not os.path.exists(p(run, o["path"])) for o in a.get("outputs", [])):
            missing.append(apath)
    return ("spawn" if missing else "ready"), missing


def _latest(st, prefix):
    keys = sorted(k for k in st.get("groups", {}) if k.startswith(prefix))
    return keys[-1] if keys else None


SLUG_TYPES = [("stripe", "payment"), ("payment", "payment"), ("presale", "payment"), ("deposit", "payment"), ("ads", "payment"),
              ("budget", "payment"), ("post", "outward-action"), ("outreach", "outward-action"), ("email", "outward-action"),
              ("recruit", "outward-action"), ("publish", "outward-action"), ("deploy", "account"), ("hosting", "account"),
              ("domain", "account"), ("form", "account"), ("analytics", "account"), ("legal", "legal"), ("privacy", "legal")]


def _ht_type(slug):
    s = slug.lower()
    for k, t in SLUG_TYPES:
        if k in s:
            return t
    return "outward-action"


def _launch_tasks(run, st, card):
    exp = card["id"]
    e = st.setdefault("experiments", {}).setdefault(exp, {})
    if e.get("hts"):
        return e["hts"]
    ids = []
    for slug in card["required_ht"]:
        t = hq.add(run, _ht_type(slug), "%s: %s" % (exp, slug),
                   "Experiment %s (%s) needs this before it can run; agents never publish, post, send or pay." % (exp, card["type"]),
                   "See validation/assets/%s/ (posts.md, landing.html, survey.md, interview-guide.md) for the drafts to use." % exp,
                   "a note with the URL, confirmation or the environment variable you set", "V4", blocking=True)
        ids.append(t["id"])
    kinds = KINDS_FOR_TYPE.get(card["type"], [])
    where = ", ".join("validation/data/%s/%s" % (exp, "interviews/ (one .txt per interview)" if k == "interviews" else k + ".csv") for k in kinds)
    t = hq.add(run, "account", "%s: export results" % exp,
               "The analysis needs the raw counts or responses when the experiment ends (after %d days or %d units)." % (card["duration_days"], card["min_n"]),
               "Save the export(s) at: %s. Use pseudonymous respondent ids only; no names, emails or phone numbers." % where,
               "the files at those paths, then `hq done`", "V5", blocking=True)
    ids.append(t["id"])
    e["hts"] = ids
    save_state(run, st)
    return ids


def decide(run):
    if not os.path.exists(v(run, "state.json")):
        if os.path.exists(p(run, "output", "handoff.json")):
            RUN("init %s" % run, "read the discovery handoff and select the top-ranked opportunity", phase="V0")
        DO("V01", "start with `gapval.py init RUN --idea TEXT` for a standalone idea, or `--handoff PATH`", phase="V0")
    st = load_state(run)
    # ---------------- V1 frame
    s, missing = _group(run, st, "ost")
    if s is None:
        RUN("assign %s --phase ost" % run, "Opportunity Solution Tree with >= 3 solutions (V01-V02)", phase="V1")
    if s == "spawn":
        SPAWN("designer", run, missing, phase="V1")
    ost_mtime = os.path.getmtime(v(run, "ost.json"))
    if st.get("ost_checked_mtime") != ost_mtime:
        st["ost_checked_mtime"] = ost_mtime
        save_state(run, st)
        RUN("ost check %s" % run, phase="V1")
    if not st.get("ost_ok"):
        DO("V01", "fix validation/ost.json (run `gapval.py ost check` to see the problems), or re-spawn the designer", phase="V1")
    st["groups"]["ost"]["merged"] = True
    if state.stale(st, "assumptions", ["ost"]):
        RUN("assumptions rank %s" % run, "importance x missing evidence; test the riskiest first", phase="V1")
    # ---------------- V2 design and pre-register
    key = _latest(st, "design-")
    s, missing = _group(run, st, key) if key else (None, [])
    if key is None:
        RUN("assign %s --phase design" % run, "one pre-registered Test Card per selected assumption (V03-V04)", phase="V2")
    if s == "spawn":
        SPAWN("designer", run, missing, phase="V2")
    tests = cards(run)
    for exp, card in sorted(tests.items()):
        if os.path.exists(v(run, "prereg", "%s.lock.json" % exp)) or st.get("experiments", {}).get(exp, {}).get("status") == "closed":
            continue
        chk = st.get("experiments", {}).get(exp, {}).get("check")
        if chk and not chk["ok"] and chk.get("card_sha") == _hash(card):
            DO("V04", "fix %s (validation/prereg/%s.json), then `gapval.py prereg check %s %s`" % (exp, exp, run, exp), *chk["errors"][:5], phase="V2")
        RUN("prereg freeze %s %s" % (run, exp), "pre-registration: thresholds are hashed before any data", phase="V2")
    if key:
        st["groups"][key]["merged"] = True
    frozen = {e: c for e, c in tests.items() if os.path.exists(v(run, "prereg", "%s.lock.json" % e))}
    fp = sha256_json(sorted((e, _hash(c)) for e, c in frozen.items()))
    gates = st.setdefault("gates", {})
    g = gates.get("plan", {"attempt": 0})
    task = hq.find_gate(run, "plan#%d" % g["attempt"]) if g["attempt"] else None
    if task is None or (task["status"] == "declined" and g.get("fingerprint") != fp):
        g = {"attempt": g["attempt"] + 1, "fingerprint": fp}
        gates["plan"] = g
        summary = "; ".join("%s %s X=%.2f n>=%d budget $%s" % (e, c["type"], c["success_threshold"], c["min_n"], c["budget_usd"]) for e, c in sorted(frozen.items()))
        task = hq.add(run, "judgment", "Approve the experiment plan and budget",
                      "Experiments contact real people and may spend money; the human approves them first. Plan: %s" % summary,
                      "Read validation/prereg/*.json and validation/ethics notes; approve with `hq done`, or `hq decline --note WHY`.",
                      "approval or a decline note", "V2", blocking=True, gate="plan#%d" % g["attempt"])
        save_state(run, st)
    if task["status"] == "open":
        BLOCKED(task, "validation always waits for the human before anything outward-facing", phase="V2")
    if task["status"] == "declined":
        DO("V03", "the human declined the plan (%s): close or replace experiments with new Test Cards (new ids), then call next" % (task.get("note") or "no note"), phase="V2")
    # ---------------- V3 assets
    need_assets = [c for c in frozen.values() if not st.get("experiments", {}).get(c["id"], {}).get("assets_ok")
                   and st.get("experiments", {}).get(c["id"], {}).get("status") != "closed"]
    if need_assets:
        key = _latest(st, "assets-")
        s, missing = _group(run, st, key) if key else (None, [])
        if s is None or s == "merged":
            RUN("assign %s --phase assets" % run, "drafts only: landing page, survey, interview guide, posts (V05-V07)", phase="V3")
        if s == "spawn":
            SPAWN("builder", run, missing, phase="V3")
        for c in need_assets:
            chk_path = v(run, "assets", c["id"], "assets-check.json")
            chk = read_json(chk_path)
            files_m = [os.path.getmtime(os.path.join(v(run, "assets", c["id"]), f)) for f in os.listdir(v(run, "assets", c["id"]))
                       if f != "assets-check.json"] if os.path.isdir(v(run, "assets", c["id"])) else []
            if chk and not chk["ok"] and files_m and os.path.getmtime(chk_path) >= max(files_m):
                DO("V07", "fix the assets of %s as listed in validation/assets/%s/assets-check.json" % (c["id"], c["id"]), *chk["errors"][:5], phase="V3")
            RUN("assets check %s %s" % (run, c["id"]), "honest fake doors: disclosure, consent, privacy, no fake social proof", phase="V3")
        st["groups"][key]["merged"] = True
        save_state(run, st)
    # ---------------- V4 launch (human) and V5 data
    for exp, card in sorted(frozen.items()):
        e = st.setdefault("experiments", {}).setdefault(exp, {})
        if e.get("status") in ("closed", "analyzed"):
            continue
        ids = _launch_tasks(run, st, card)
        tasks = {t["id"]: t for t in hq.load(run)["tasks"]}
        if any(tasks[i]["status"] == "declined" for i in ids):
            e["status"] = "closed"
            save_state(run, st)
            continue
        if card["type"] in LANDING_TYPES and card["type"] != "loi" and not os.path.exists(v(run, "assets", exp, "utm.json")):
            deploy = [tasks[i] for i in ids[:-1] if tasks[i]["status"] == "done" and ("http" in (tasks[i].get("note") or ""))]
            if deploy or all(tasks[i]["status"] == "done" for i in ids[:-1]):
                DO("V07", "create tracked links: `gapval.py utm %s --experiment %s --base-url URL --channels %s` using the deployed URL from the human's note" % (
                    run, exp, ",".join(card["channels"])), phase="V4")
        for i in ids:
            if tasks[i]["status"] == "open":
                BLOCKED(tasks[i], "experiment %s" % exp, phase="V4" if i != ids[-1] else "V5")
        for kind in KINDS_FOR_TYPE.get(card["type"], []):
            if kind in e.get("ingested", []):
                continue
            src = v(run, "data", exp, "interviews") if kind == "interviews" else v(run, "data", exp, kind + ".csv")
            if os.path.exists(src):
                RUN("ingest %s --experiment %s --kind %s --file %s" % (run, exp, kind, src), phase="V5")
            DO("V09", "the export for %s is missing at %s: ask the human (reopen with `hq add`) and call next" % (exp, src), phase="V5")
        if card["decision_rule"] == "themes":
            if not os.path.exists(v(run, "data", exp, "codes-A.jsonl")):
                key = "interview-coding-"
                gk = _latest(st, key)
                s, missing = _group(run, st, gk) if gk else (None, [])
                if s in (None, "merged", "ready"):
                    RUN("assign %s --phase interview-coding" % run, "coder A codes every transcript (V05)", phase="V5")
                SPAWN("coder", run, missing, phase="V5")
            if not os.path.exists(v(run, "data", exp, "codes-B.jsonl")):
                gk = _latest(st, "interview-reliability-")
                s, missing = _group(run, st, gk) if gk else (None, [])
                if s in (None, "merged", "ready"):
                    RUN("assign %s --phase interview-reliability" % run, "independent coder B on a sample", phase="V5")
                SPAWN("coder", run, missing, phase="V5")
            if state.stale(st, "agreement", ["ingest_%s" % exp]) or exp not in (read_json(v(run, "agreement.json"), {}) or {}):
                RUN("agreement %s" % run, phase="V5")
            if exp not in (read_json(v(run, "themes.json"), {}) or {}):
                RUN("themes %s" % run, phase="V5")
        RUN("stats %s --experiment %s" % (run, exp), "apply the frozen decision rule", phase="V5")
    # ---------------- V6 decide and report
    if state.stale(st, "verdict", ["stats_%s" % e for e in frozen] + ["prereg"]) or not os.path.exists(v(run, "verdict.json")):
        RUN("verdict %s" % run, "deterministic GO / ITERATE / PIVOT / KILL", phase="V6")
    n = st.get("report_rounds", 0)
    s, missing = _group(run, st, "report-%02d" % n) if n else (None, [])
    if s is None:
        RUN("assign %s --phase report" % run, "Learning Cards, report and validated-handoff.json (V10)", phase="V6")
    if s == "spawn":
        SPAWN("analyst", run, missing, phase="V6")
    if s == "ready" or state.stale(st, "validate", ["verdict"]):
        RUN("validate %s" % run, phase="V6")
    chk = read_json(v(run, "validate-check.json"), {}) or {}
    if not chk.get("ok"):
        if n < 3:
            RUN("assign %s --phase report" % run, "validation report failed its checks: analyst fix pass", *chk.get("errors", [])[:5], phase="V6")
        DO("V10", "fix validation/ artifacts as listed in validation/validate-check.json, then `gapval.py validate`", phase="V6")
    verdict = read_json(v(run, "verdict.json"))
    raise Act("DONE", "", ["verdict: %s (demand strength %s)" % (verdict["verdict"], verdict["demand_strength"]),
                           "deliverables: %s" % ", ".join(v(run, f) for f in ("report.md", "validated-handoff.json", "verdict.json"))], "V6")


def cmd_next(args):
    run = args.run
    try:
        decide(run)
        act = Act("DONE", "", [])
    except Act as a:
        act = a
    cmd = "python3 %s %s" % (GAPVAL, act.argline.split(" ", 1)[1]) if act.verdict == "RUN" else None
    if args.json:
        out(json.dumps({"verdict": act.verdict, "args": act.argline, "phase": act.phase, "notes": act.notes, "cmd": cmd}, indent=2))
        return 0
    out(act.verdict + ((" " + act.argline) if act.argline else ""))
    if act.phase:
        out("NOTE phase %s" % act.phase)
    for n in act.notes:
        out("NOTE %s" % n)
    if cmd:
        out("NOTE cmd: " + cmd)
    return 0


def cmd_status(args):
    run = args.run
    require(run)
    st = load_state(run)
    verdict = read_json(v(run, "verdict.json"), {}) or {}
    info = {"gap": st.get("gap_id"), "standalone": st.get("standalone"),
            "experiments": {e: x.get("status") for e, x in st.get("experiments", {}).items()},
            "verdict": verdict.get("verdict"), "demand_strength": verdict.get("demand_strength"),
            "open_human_tasks": [t["id"] + " " + t["title"] for t in hq.open_tasks(run)]}
    if args.json:
        out(json.dumps(info, indent=2))
    else:
        for k, val in info.items():
            out("%-18s %s" % (k, val))
    return 0
