"""Deterministic GO / ITERATE / PIVOT / KILL verdict and artifact validation (method card V10)."""

import glob
import os
import re

from mgcore import state
from mgcore.jsonio import now_iso, read_json, write_json

from .common import CliError, cards, cfg, load_state, out, require, save_state, target_assumptions, v, validate
from .prereg import is_tampered

ACTION = {"kill": "KILL", "pivot": "PIVOT", "iterate": "ITERATE"}


def assumption_status(a, runs, c):
    ladder = c.get("evidence_ladder")
    lvl = lambda e: ladder.get(e, 0)  # noqa: E731
    passes = [r for r in runs if r["result"] == "PASS"]
    fails = [r for r in runs if r["result"] == "FAIL"]
    if not runs:
        return "untested", []
    if passes and fails:
        return "inconclusive", ["conflicting results: %s pass, %s fail" % (", ".join(r["id"] for r in passes), ", ".join(r["id"] for r in fails))]
    if fails:
        return "invalidated", ["%s failed" % ", ".join(r["id"] for r in fails)]
    if passes:
        if a["type"] == "desirability":
            strong = [r for r in passes if lvl(r["level"]) >= c.get("verdict.desirability_min_level")]
        elif a["type"] == "viability":
            strong = [r for r in passes if lvl(r["level"]) >= c.get("verdict.viability_min_level")
                      or (r["rule"] == "van-westendorp" and not r.get("directional"))]
        else:
            strong = passes
        if strong:
            return "validated", ["%s passed at evidence level %s" % (r["id"], r["level"]) for r in strong]
        return "supported", ["passed only with weak evidence (%s); escalate to stronger evidence" % ", ".join(r["level"] for r in passes)]
    return "inconclusive", ["%s inconclusive" % ", ".join(r["id"] for r in runs)]


def compute(run):
    c = cfg()
    assumptions = target_assumptions(run)
    tests = cards(run)
    st = load_state(run)
    exp_state = st.get("experiments", {})
    results = {}
    for exp, card in tests.items():
        if card.get("status") == "draft":
            continue
        res = read_json(v(run, "results", "%s.json" % exp))
        if is_tampered(run, exp):
            r = "TAMPERED"
        elif res:
            r = res["result"]
        else:
            r = "NOT_RUN" if exp_state.get(exp, {}).get("status") == "closed" else "PENDING"
        results[exp] = {"id": exp, "result": r, "rule": card["decision_rule"], "level": card["evidence_level"],
                        "directional": bool(res and res.get("directional")), "assumptions": card["assumption_ids"],
                        "on_fail": card["on_fail"], "on_inconclusive": card["on_inconclusive"]}
    statuses = {}
    for aid, a in assumptions.items():
        runs = [r for r in results.values() if aid in r["assumptions"] and r["result"] in ("PASS", "FAIL", "INCONCLUSIVE", "TAMPERED")]
        runs = [dict(r, result="INCONCLUSIVE") if r["result"] == "TAMPERED" else r for r in runs]
        s, why = assumption_status(a, runs, c)
        statuses[aid] = {"id": aid, "type": a["type"], "importance": a["importance"],
                         "critical": a["importance"] >= c.get("assumptions.critical_importance_min"),
                         "status": s, "why": why, "experiments": [r["id"] for r in runs]}
    critical = [x for x in statuses.values() if x["critical"]]
    actions, reasons = [], []
    for x in critical:
        if x["status"] == "invalidated":
            for eid in x["experiments"]:
                if results[eid]["result"] == "FAIL":
                    actions.append(ACTION[results[eid]["on_fail"]])
                    reasons.append("%s (%s) invalidated by %s -> pre-registered action %s" % (x["id"], x["type"], eid, results[eid]["on_fail"]))
    if actions:
        order = c.get("verdict.precedence")
        verdict = sorted(actions, key=order.index)[0]
    else:
        need = [x for x in critical if x["type"] in ("desirability", "viability")]
        if need and all(x["status"] == "validated" for x in need) and {"desirability", "viability"} <= set(x["type"] for x in need):
            verdict = "GO"
            reasons.append("every critical desirability and viability assumption is validated with strong enough evidence")
        else:
            verdict = "ITERATE"
            open_ = [x["id"] for x in critical if x["status"] != "validated"]
            reasons.append("critical assumptions not yet validated: %s" % (", ".join(open_) or "none tested"))
    ladder = c.get("demand_strength")
    passed_levels = set(r["level"] for r in results.values() if r["result"] == "PASS")
    strength = "strong" if passed_levels & set(ladder["strong"]) else ("moderate" if passed_levels & set(ladder["moderate"]) else "weak")
    return {"computed_at": now_iso(), "verdict": verdict, "reasons": reasons, "assumptions": list(statuses.values()),
            "experiments": list(results.values()), "demand_strength": strength,
            "rule": "KILL > PIVOT > ITERATE > GO when critical assumptions disagree; GO needs validated desirability and viability"}


def cmd_verdict(args):
    run = args.run
    require(run)
    doc = compute(run)
    pending = [e["id"] for e in doc["experiments"] if e["result"] == "PENDING"]
    if pending:
        doc["note"] = "experiments still pending: %s" % ", ".join(pending)
    write_json(v(run, "verdict.json"), doc)
    st = load_state(run)
    state.touch(st, "verdict")
    save_state(run, st)
    out("Verdict: %s (demand strength %s)" % (doc["verdict"], doc["demand_strength"]))
    for r in doc["reasons"]:
        out("  - " + r)
    return 0


def cmd_validate(args):
    run = args.run
    require(run)
    errs = []
    checks = [("ost.json", "ost")] + [(os.path.relpath(f, v(run)), "test-card") for f in glob.glob(v(run, "prereg", "EXP-*.json")) if not f.endswith(".lock.json")]
    checks += [(os.path.relpath(f, v(run)), "learning-card") for f in glob.glob(v(run, "learning-cards", "EXP-*.json"))]
    if os.path.exists(v(run, "validated-handoff.json")):
        checks.append(("validated-handoff.json", "validated-handoff"))
    for relp, name in checks:
        doc = read_json(v(run, relp))
        errs += ["%s: %s" % (relp, e) for e in (validate(doc, name) if doc is not None else ["missing"])]
    for exp in cards(run):
        if is_tampered(run, exp):
            errs.append("%s: Test Card changed after freezing" % exp)
    verdict = read_json(v(run, "verdict.json"))
    vh = read_json(v(run, "validated-handoff.json"))
    if verdict and vh:
        if vh.get("verdict") != verdict["verdict"]:
            errs.append("validated-handoff verdict %s differs from verdict.json %s" % (vh.get("verdict"), verdict["verdict"]))
        if vh.get("demand_strength") != verdict["demand_strength"]:
            errs.append("validated-handoff demand_strength differs from verdict.json")
        res = {e["id"]: e["result"] for e in verdict["experiments"]}
        for e in vh.get("experiments", []):
            if e["id"] in res and e["result"] != res[e["id"]] and not (res[e["id"]] == "PENDING" and e["result"] == "NOT_RUN"):
                errs.append("validated-handoff reports %s as %s but the results say %s" % (e["id"], e["result"], res[e["id"]]))
        for e in verdict["experiments"]:
            if e["result"] in ("PASS", "FAIL", "INCONCLUSIVE", "TAMPERED") and not os.path.exists(v(run, "learning-cards", "%s.json" % e["id"])):
                errs.append("%s has no Learning Card" % e["id"])
    if os.path.exists(v(run, "report.md")) and verdict:
        with open(v(run, "report.md"), encoding="utf-8") as fh:
            rep = fh.read()
        if verdict["verdict"] not in rep:
            errs.append("report.md does not state the verdict %s" % verdict["verdict"])
        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", rep):
            errs.append("report.md contains an email address")
    ok = not errs
    write_json(v(run, "validate-check.json"), {"checked_at": now_iso(), "ok": ok, "errors": errs})
    st = load_state(run)
    for key, g in st.get("groups", {}).items():
        if key.startswith("report-") and not g.get("merged"):
            g["merged"] = True
    state.touch(st, "validate")
    save_state(run, st)
    if errs:
        out("Validation artifacts need fixing (%d):" % len(errs))
        for e in errs[:15]:
            out("  - " + e)
        return 1
    out("All validation artifacts are valid and consistent with verdict.json.")
    return 0
