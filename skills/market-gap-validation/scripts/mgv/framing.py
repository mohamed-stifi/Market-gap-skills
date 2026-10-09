"""OST check, assumption ranking and sample size (method cards V01, V02, V04)."""

from mgcore import stats
from mgcore.jsonio import now_iso, write_json

from .common import CliError, cfg, load_state, ost, out, require, touch, v, validate


def ost_problems(run):
    doc = ost(run)
    if doc is None:
        return ["validation/ost.json is missing"]
    errs = validate(doc, "ost")
    if errs:
        return errs
    ids = [a["id"] for s in doc["solutions"] for a in s["assumptions"]]
    dupes = sorted(set(i for i in ids if ids.count(i) > 1))
    if dupes:
        errs.append("assumption ids must be unique across the tree: %s" % ", ".join(dupes))
    sols = {s["id"]: s for s in doc["solutions"]}
    if doc["target_solution"] not in sols:
        errs.append("target_solution %s is not one of the solutions" % doc["target_solution"])
    else:
        types = set(a["type"] for a in sols[doc["target_solution"]]["assumptions"])
        for t in ("desirability", "viability"):
            if t not in types:
                errs.append("the target solution needs at least one %s assumption" % t)
    if len(set(s["concept"].strip().lower() for s in doc["solutions"])) < len(doc["solutions"]):
        errs.append("solutions must be genuinely different concepts")
    return errs


def cmd_ost(args):
    run = args.run
    require(run)
    errs = ost_problems(run)
    st = load_state(run)
    st["ost_ok"] = not errs
    touch(run, st, "ost")
    if errs:
        out("ost.json needs fixing:")
        for e in errs:
            out("  - " + e)
        return 1
    out("OST valid: %d solutions; target %s." % (len(ost(run)["solutions"]), ost(run)["target_solution"]))
    return 0


def cmd_assumptions(args):
    run = args.run
    require(run)
    if ost_problems(run):
        raise CliError("fix ost.json first (`gapval.py ost check`)")
    c = cfg()
    doc = ost(run)
    target = [s for s in doc["solutions"] if s["id"] == doc["target_solution"]][0]
    rows = []
    for a in target["assumptions"]:
        risk = a["importance"] * (5 - a["evidence"])
        ice = a["ice"]["impact"] * a["ice"]["confidence"] * a["ice"]["ease"]
        rows.append(dict(a, risk=risk, ice_score=ice, critical=a["importance"] >= c.get("assumptions.critical_importance_min")))
    rows.sort(key=lambda r: (-r["risk"], -r["ice_score"], r["id"]))
    k = c.get("assumptions.experiments_per_round")
    for i, r in enumerate(rows):
        r["selected"] = i < k and r["risk"] > 0
    write_json(v(run, "assumptions-ranked.json"), {"computed_at": now_iso(), "solution": target["id"], "assumptions": rows,
                                                   "rule": "risk = importance x (5 - evidence); ties by ICE; test the important, low-evidence ones first"})
    st = load_state(run)
    touch(run, st, "assumptions")
    out("Assumptions ranked: " + "; ".join("%s risk %d%s%s" % (r["id"], r["risk"], " critical" if r["critical"] else "", " SELECTED" if r["selected"] else "") for r in rows))
    return 0


def cmd_samplesize(args):
    n = stats.sample_size(args.p, args.h, args.z)
    out("n = %d (p=%.3f, half-width=%.3f, z=%.2f)" % (n, args.p, args.h, args.z))
    return 0
