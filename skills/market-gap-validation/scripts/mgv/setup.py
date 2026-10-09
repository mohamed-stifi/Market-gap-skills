"""init and hq commands for validation."""

import json
import os
import shutil

from mgcore import hq, state
from mgcore.jsonio import now_iso, read_json, sha256_file, write_json

from .common import CliError, cfg, out, p, require, v, validate, load_state, save_state


def cmd_init(args):
    run = args.run
    if os.path.exists(v(run, "state.json")):
        raise CliError("validation already initialised in %s" % run)
    handoff_path = args.handoff or p(run, "output", "handoff.json")
    opp, src_sha, gap_id = None, None, None
    if args.idea:
        os.makedirs(run, exist_ok=True)
        opp = {"rank": None, "gap_id": None, "title": args.idea[:100], "statement": args.idea,
               "certainty": {"pain": "Very low", "demand": "Very low", "demand_strength": "weak"},
               "icp": {"description": "", "where_they_gather": []}, "jtbd": {"job": "", "outcomes": []},
               "top_quotes": [], "competitors": [], "assumptions": [],
               "note": "Standalone idea without discovery evidence: certainty starts at Very low."}
    else:
        handoff = read_json(handoff_path)
        if handoff is None:
            raise CliError("no handoff at %s; pass --handoff PATH or --idea TEXT" % handoff_path)
        errs = validate(handoff, "handoff")
        if errs:
            raise CliError("handoff.json is invalid:\n  " + "\n  ".join(errs[:8]))
        opps = handoff.get("opportunities", [])
        if not opps:
            raise CliError("the handoff has no opportunities: discovery found no gap that met its thresholds")
        if args.gap:
            match = [o for o in opps if o["gap_id"] == args.gap]
            if not match:
                raise CliError("gap %s is not in the handoff (have %s)" % (args.gap, ", ".join(o["gap_id"] for o in opps)))
            opp = match[0]
        else:
            opp = sorted(opps, key=lambda o: o["rank"])[0]
        src_sha = sha256_file(handoff_path)
        gap_id = opp["gap_id"]
    for d in ("prereg", "assets", "data", "results", "learning-cards"):
        os.makedirs(v(run, d), exist_ok=True)
    write_json(v(run, "opportunity.json"), opp)
    book = None
    lock = read_json(p(run, "coding", "codebook.lock.json"))
    if lock:
        book = p(run, "coding", "codebook.v%d.json" % lock["version"])
        shutil.copy2(book, v(run, "codebook.json"))
    st = {"schema_version": "1.0", "created_at": now_iso(), "gap_id": gap_id, "source_handoff_sha256": src_sha,
          "autonomy": args.autonomy, "standalone": bool(args.idea), "experiments": {}, "groups": {}, "report_rounds": 0}
    save_state(run, st)
    state.event(run, "validation_init", sub="validation", gap_id=gap_id, idea=args.idea)
    out("Validation initialised for %s%s." % (gap_id or "a standalone idea", " (codebook copied from discovery)" if book else ""))
    out("Next: `gapval.py next %s`." % run)
    return 0


def cmd_hq(args):
    run = args.run
    require(run)
    if args.action == "list":
        for t in hq.load(run)["tasks"]:
            out("%s [%s]%s %s (%s, phase %s)" % (t["id"], t["status"], " BLOCKING" if t["blocking"] else "", t["title"], t["type"], t["phase"]))
            if t["status"] == "open":
                out("    why: %s\n    steps: %s\n    return: %s" % (t["why"], t["steps"], t["returns"]))
        return 0
    if args.action == "add":
        t = hq.add(run, args.type, args.title, args.why, args.steps, args.returns, args.phase or "-", args.blocking, args.fallback)
        out("Added %s." % t["id"])
        return 0
    t = hq.close(run, args.task, "done" if args.action == "done" else "declined", args.note)
    st = load_state(run)
    state.touch(st, "hq")
    save_state(run, st)
    out("%s marked %s." % (t["id"], t["status"]))
    return 0
