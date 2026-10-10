"""prisma, validate (--report), compare and purge (method card D25)."""

import datetime as dt
import glob
import json
import os
import re

from mgcore import richness, state, stats
from mgcore.jsonio import now_iso, read_json, read_jsonl, write_json

from .common import CliError, alias_map, cfg, entities, out, p, protocol, require_run, load_state, save_state, validate

HANDLE = re.compile(r"(?<![\w.])(@[A-Za-z0-9_]{2,}|u/[A-Za-z0-9_-]{2,})")


# ---------------------------------------------------------------- PRISMA
def cmd_prisma(args):
    run = args.run
    require_run(run)
    ents = entities(run)
    merges = [read_json(f) for f in glob.glob(p(run, "landscape", "**", "merge.json"), recursive=True)]
    units = read_json(p(run, "landscape", "units.json"), {}) or {}
    by_family = {}
    for u in units.values():
        by_family[u["family"]] = by_family.get(u["family"], 0) + u.get("items", 0)
    reasons = {}
    for e in ents:
        if e.get("status") == "excluded":
            rc = (e.get("screening") or {}).get("reason_code", "?")
            reasons[rc] = reasons.get(rc, 0) + 1
    ver = {}
    for e in ents:
        if e.get("status") == "included":
            s = (e.get("verified") or {}).get("status", "pending")
            ver[s] = ver.get(s, 0) + 1
    inc_ok = [e for e in ents if e.get("status") == "included" and (e.get("verified") or {}).get("status") == "ok"]
    landscape = {
        "records_identified": sum(m.get("items", 0) for m in merges if m),
        "identified_by_family": by_family,
        "unique_entities": len(ents),
        "duplicates_removed": sum(m.get("matched_existing", 0) for m in merges if m),
        "invalid_items": sum(len(m.get("invalid", [])) for m in merges if m),
        "screened": sum(1 for e in ents if e.get("status") != "new"),
        "excluded_by_reason": reasons,
        "unsure": sum(1 for e in ents if e.get("status") == "unsure"),
        "included": sum(1 for e in ents if e.get("status") == "included"),
        "verification": ver,
        "included_verified": len(inc_ok),
        "counted_in_saturation": sum(1 for e in inc_ok if set(e.get("found_via", [])) & {"sampling", "probe"}),
        "snowball_only": sum(1 for e in inc_ok if e.get("found_via") == ["snowball"]),
    }
    q = read_jsonl(p(run, "queries.jsonl"))[0]
    searches = {}
    for r in q:
        k = "%s (%s)" % (r.get("source"), r.get("method"))
        searches[k] = searches.get(k, 0) + 1
    ev_merges = [read_json(f) for f in sorted(glob.glob(p(run, "evidence", "round-*", "merge.json")))]
    led = read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]
    vstat = {}
    for r in led:
        s = r.get("verification", {}).get("status", "pending")
        vstat[s] = vstat.get(s, 0) + 1
    by_type = {}
    for r in led:
        if r.get("verification", {}).get("status") == "verified":
            by_type[r["source_type"]] = by_type.get(r["source_type"], 0) + 1
    # A retry re-submits the same round after mechanical fixes: its accepted records move from
    # "rejected" to "accepted"; counting the retry as new submissions would double-count.
    retried = sum((read_json(f) or {}).get("accepted", 0)
                  for f in glob.glob(p(run, "evidence", "round-*", "merge-retry-*.json")))
    evidence = {"submitted": sum(m.get("accepted", 0) + m.get("duplicates", 0) + len(m.get("rejected", [])) for m in ev_merges if m),
                "rejected_at_merge": sum(len(m.get("rejected", [])) for m in ev_merges if m) - retried,
                "accepted_on_retry": retried,
                "duplicates": sum(m.get("duplicates", 0) for m in ev_merges if m),
                "in_ledger": len(led), "verification": vstat, "verified_by_source_type": by_type,
                "rounds": len(ev_merges)}
    # Limitations the miners cannot see on their own: pools screened only at the top (no stopping test),
    # and products first seen in evidence (the landscape missed them).
    pool_min = cfg(run).get("evidence.stoptest_pool_min")
    ev_q = [r for r in q if str(r.get("by") or "").startswith("EV-")]
    large = [r for r in ev_q if r.get("method") != "stoptest" and isinstance(r.get("total_hits"), int)
             and r["total_hits"] > pool_min and (r.get("items") or 0) < r["total_hits"]]
    tested = sum(1 for r in ev_q if r.get("method") == "stoptest")
    evidence["large_pools"] = {"over_pool_min": len(large), "stop_tested": tested,
                               "truncated_without_test": max(0, len(large) - tested)}
    known = alias_map(run)
    evidence["post_landscape_discoveries"] = sorted({x for r in led for x in (r.get("entity_ids") or []) if x not in known})
    agr = read_json(p(run, "coding", "agreement.json"), {}) or {}
    th = read_json(p(run, "coding", "themes.json"), {}) or {}
    coding = {"codebook_version": agr.get("version"), "agreement": agr.get("verdict"), "themes_saturated": th.get("saturated"),
              "records_coded": th.get("records")}
    cards = read_jsonl(p(run, "gaps", "cards.jsonl"))[0]
    st_c = {}
    for cdx in cards:
        st_c[cdx["status"]] = st_c.get(cdx["status"], 0) + 1
    rk = read_json(p(run, "gaps", "ranking.json"), {}) or {}
    gaps = {"cards_proposed": len(cards), "by_status": st_c, "gated_out": len(rk.get("excluded", [])) - st_c.get("killed", 0),
            "ranked": len(rk.get("ranked", []))}
    doc = {"computed_at": now_iso(), "landscape": landscape, "searches": searches, "evidence": evidence, "coding": coding, "gaps": gaps}
    opp_md = []
    if os.path.exists(p(run, "opportunities", "candidates.jsonl")):
        # Opportunity lenses (D26) and the scan funnel (D28): generated -> tested -> by evidence tier -> red flags -> ranked.
        oc = read_jsonl(p(run, "opportunities", "candidates.jsonl"))[0]
        osc = (read_json(p(run, "opportunities", "scores.json"), {}) or {}).get("candidates", {})
        ork = read_json(p(run, "opportunities", "ranking.json"), {}) or {}
        orf = read_jsonl(p(run, "opportunities", "redflags.jsonl"))[0]
        by_lens, by_tier, rf_v = {}, {}, {}
        for x in oc:
            by_lens[x["lens"]] = by_lens.get(x["lens"], 0) + 1
        for v in osc.values():
            by_tier[v["status"]] = by_tier.get(v["status"], 0) + 1
        for x in orf:
            rf_v[x["verdict"]] = rf_v.get(x["verdict"], 0) + 1
        doc["opportunities"] = {"generated": len(oc), "by_lens": by_lens, "by_evidence_tier": by_tier,
                                "tested": sum(n for k, n in by_tier.items() if k not in ("untested", "excluded")),
                                "redflag_checked": len(orf), "redflag_verdicts": rf_v,
                                "excluded": len(ork.get("excluded", [])), "ranked": len(ork.get("ranked", []))}
        o = doc["opportunities"]
        opp_md = ["", "## Opportunities", "", "| Stage | Count |", "|---|---|",
                  "| Options generated (all lenses) | %d |" % o["generated"],
                  "| Tested with evidence | %d |" % o["tested"],
                  "| Promising | %d |" % by_tier.get("promising", 0),
                  "| Contradicted | %d |" % by_tier.get("contradicted", 0),
                  "| Red-flag checked | %d |" % o["redflag_checked"],
                  "| Killed by red flags, gates or the protocol | %d |" % o["excluded"],
                  "| Ranked | %d |" % o["ranked"], "",
                  "Options by lens: " + ", ".join("%s %d" % kv for kv in sorted(by_lens.items()))]
    write_json(p(run, "output", "prisma.json"), doc)
    md = ["# PRISMA-style flow", "",
          "## Landscape", "",
          "| Stage | Count |", "|---|---|",
          "| Records identified (all units) | %d |" % landscape["records_identified"],
          "| Duplicates merged | %d |" % landscape["duplicates_removed"],
          "| Unique entities | %d |" % landscape["unique_entities"],
          "| Screened | %d |" % landscape["screened"],
          "| Excluded | %d |" % sum(reasons.values()),
          "| Unsure (not counted) | %d |" % landscape["unsure"],
          "| Included | %d |" % landscape["included"],
          "| Included and verified | %d |" % landscape["included_verified"],
          "| Counted in saturation | %d |" % landscape["counted_in_saturation"], "",
          "Exclusions by reason: " + (", ".join("%s %d" % (k, v) for k, v in sorted(reasons.items())) or "none"), "",
          "## Evidence", "",
          "| Stage | Count |", "|---|---|",
          "| Records submitted by miners | %d |" % evidence["submitted"],
          "| Rejected at merge | %d |" % evidence["rejected_at_merge"],
          "| Duplicates | %d |" % evidence["duplicates"],
          "| In ledger | %d |" % evidence["in_ledger"],
          "| Quote verified | %d |" % vstat.get("verified", 0), "",
          "## Gaps", "",
          "| Stage | Count |", "|---|---|",
          "| Cards proposed | %d |" % gaps["cards_proposed"],
          "| Insufficient evidence | %d |" % st_c.get("insufficient", 0),
          "| Killed by red team | %d |" % st_c.get("killed", 0),
          "| Gated out | %d |" % max(gaps["gated_out"], 0),
          "| Ranked | %d |" % gaps["ranked"], "",
          "## Searches (PRISMA-S log)", ""] + ["- %s: %d" % (k, v) for k, v in sorted(searches.items())] + opp_md
    with open(p(run, "output", "prisma.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    st = load_state(run)
    state.touch(st, "prisma")
    save_state(run, st)
    out("PRISMA flow written: %d records identified -> %d unique -> %d included & verified; %d evidence records verified; %d gaps ranked." % (
        landscape["records_identified"], landscape["unique_entities"], landscape["included_verified"], vstat.get("verified", 0), gaps["ranked"]))
    return 0


# ---------------------------------------------------------------- validate
CHECKS = [
    ("protocol.json", "protocol", "json"),
    ("lexicon/round-*/scout-*.json", "lexicon-output", "json"),
    ("lexicon/press.json", "press", "json"),
    ("landscape/round-*/scout-*.json", "landscape-output", "json"),
    ("landscape/probe/*/scout-P.json", "landscape-output", "json"),
    ("landscape/snowball/iter-*/scout-*.json", "landscape-output", "json"),
    ("landscape/screen/batch-*/screen-*.jsonl", "screening", "jsonl"),
    ("landscape/classification.json", "classification", "json"),
    ("landscape/entity-attributes.jsonl", "entity-attributes", "jsonl"),
    ("evidence/ledger.jsonl", "evidence", "jsonl"),
    ("evidence/round-*/miner-*.jsonl", "evidence", "jsonl"),
    ("evidence/why-now.jsonl", "why-now", "jsonl"),
    ("evidence/round-*/why-now-*.jsonl", "why-now", "jsonl"),
    ("evidence/signals/*.json", "signal", "json"),
    ("coding/codebook.v*.json", "codebook", "json"),
    ("coding/codebook.json", "codebook", "json"),
    ("coding/codebook-draft-v*.json", "codebook", "json"),
    ("coding/codes-A.jsonl", "code-assignment", "jsonl"),
    ("coding/codes-B.jsonl", "code-assignment", "jsonl"),
    ("coding/codes-A-v*-b*.jsonl", "code-assignment", "jsonl"),
    ("coding/codes-B-v*.jsonl", "code-assignment", "jsonl"),
    ("analysis/supply.jsonl", "supply", "jsonl"),
    ("gaps/cards.jsonl", "gap-card", "jsonl"),
    ("gaps/redteam/GAP-*.json", "redteam", "json"),
    ("gaps/judgments.jsonl", "judgment", "jsonl"),
    ("gaps/sizing-inputs.json", "sizing-inputs", "json"),
    ("output/handoff.json", "handoff", "json"),
    ("output/watchlist.json", "watchlist", "json"),
    ("opportunities/candidates.jsonl", "opportunity", "jsonl"),
    ("opportunities/redflags/OPP-*.json", "redflag", "json"),
    ("opportunities/redflags.jsonl", "redflag", "jsonl"),
    ("output/next-runs/OPP-*.protocol.json", "protocol", "json"),
    ("**/assign*.json", "assignment", "json"),
]


def _validate_all(run):
    report = {}
    for pattern, schema_name, fmt in CHECKS:
        for path in sorted(glob.glob(p(run, pattern), recursive=True)):
            relp = os.path.relpath(path, run)
            errs = []
            if fmt == "json":
                doc = read_json(path)
                errs = validate(doc, schema_name) if doc is not None else ["unreadable"]
            else:
                recs, bad = read_jsonl(path)
                errs = ["line %d: invalid JSON" % n for n, _ in bad]
                for i, r in enumerate(recs, 1):
                    errs += ["record %d: %s" % (i, e) for e in validate(r, schema_name)[:2]]
            report[relp] = errs
    tasks = (read_json(p(run, "human-tasks.json"), {}) or {}).get("tasks", [])
    report["human-tasks.json"] = [e for t in tasks for e in validate(t, "human-task")]
    return report


def _report_checks(run, c):
    errors, warnings = [], []
    led = {r["id"]: r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]}
    dossier_path = p(run, "output", "dossier.md")
    handoff = read_json(p(run, "output", "handoff.json"))
    if not os.path.exists(dossier_path):
        errors.append("output/dossier.md is missing")
        return errors, warnings
    if handoff is None:
        errors.append("output/handoff.json is missing")
        return errors, warnings
    with open(dossier_path, encoding="utf-8") as fh:
        dossier = fh.read()
    ids = set(re.findall(r"EV-\d{6}", dossier)) | set(re.findall(r"EV-\d{6}", json.dumps(handoff)))
    for eid in sorted(ids):
        if eid not in led:
            errors.append("%s is cited but does not exist" % eid)
        elif led[eid].get("verification", {}).get("status") != "verified":
            errors.append("%s is cited but not verified" % eid)
    rk = read_json(p(run, "gaps", "ranking.json"), {}) or {}
    ranked = [x["gap_id"] for x in rk.get("ranked", [])]
    opp_ids = [o["gap_id"] for o in handoff.get("opportunities", [])]
    for gid in opp_ids:
        if gid not in ranked:
            errors.append("%s is in the handoff but not in the ranking (excluded or unscored)" % gid)
    if opp_ids != ranked[:len(opp_ids)]:
        errors.append("handoff opportunities must follow the ranking order: %s" % ", ".join(ranked[:len(opp_ids)]))
    cert = (read_json(p(run, "gaps", "certainty.json"), {}) or {}).get("gaps", {})
    for o in handoff.get("opportunities", []):
        ct = cert.get(o["gap_id"], {})
        for k in ("pain", "demand", "demand_strength"):
            if ct and o.get("certainty", {}).get(k) != ct.get(k):
                errors.append("%s certainty.%s is %r but gaps/certainty.json says %r" % (o["gap_id"], k, o.get("certainty", {}).get(k), ct.get(k)))
        for q in o.get("top_quotes", []):
            r = led.get(q.get("evidence_id"))
            if r and q.get("quote", "").strip() != r["quote"].strip():
                errors.append("%s quote for %s differs from the ledger; quote verbatim" % (o["gap_id"], q.get("evidence_id")))
    if HANDLE.search(dossier):
        errors.append("dossier contains what looks like a username (%s); remove it" % HANDLE.search(dossier).group(0))
    low = dossier.lower()
    for word in ("limitation", "coverage", "prisma"):
        if word not in low:
            errors.append("dossier lacks a '%s' section (see D25)" % word)
    if "saturat" in low and not re.search(r"at least|lower bound", low):
        warnings.append("saturation is mentioned without lower-bound wording ('at least', 'lower bound')")
    as_of = protocol(run).get("as_of")
    stale_m = c.get("evidence.stale_months")
    if as_of:
        cutoff = dt.date.fromisoformat(as_of) - dt.timedelta(days=30 * stale_m)
        for gid in opp_ids:
            card = next((x for x in read_jsonl(p(run, "gaps", "cards.jsonl"))[0] if x["gap_id"] == gid), None)
            if not card:
                continue
            sup = [led[x] for x in card["supporting_evidence"] if x in led]
            old = [r["id"] for r in sup if r.get("posted_at") and len(r["posted_at"]) >= 7 and r["posted_at"][:7] < cutoff.isoformat()[:7]]
            if sup and len(old) > len(sup) / 2.0:
                warnings.append("%s: most supporting evidence is older than %d months" % (gid, stale_m))
            if len(set(r.get("domain") for r in sup)) <= 1:
                warnings.append("%s rests on a single domain" % gid)
    return errors, warnings


def _validate_one(run, path, schema_name=None):
    """Validate a single file (agents self-check their own output without reading anyone else's)."""
    import fnmatch
    relp = os.path.relpath(os.path.abspath(path), os.path.abspath(run)) if os.path.isabs(path) or path.startswith(run) else path
    full = p(run, relp)
    if not schema_name:
        for pattern, name, _fmt in CHECKS:
            if fnmatch.fnmatch(relp, pattern):
                schema_name = name
                break
    if not schema_name:
        raise CliError("cannot infer the schema for %s; pass --schema NAME" % relp)
    if not os.path.exists(full):
        raise CliError("%s does not exist" % relp)
    if relp.endswith(".jsonl"):
        recs, bad = read_jsonl(full)
        errs = ["line %d: invalid JSON" % n for n, _ in bad]
        for i, r in enumerate(recs, 1):
            errs += ["record %d: %s" % (i, e) for e in validate(r, schema_name)[:3]]
    else:
        doc = read_json(full)
        errs = validate(doc, schema_name) if doc is not None else ["unreadable JSON"]
    return relp, schema_name, errs


def cmd_validate(args):
    run = args.run
    require_run(run)
    if getattr(args, "file", None):
        relp, name, errs = _validate_one(run, args.file, getattr(args, "schema", None))
        if errs:
            out("%s does not match schema %s:" % (relp, name))
            for e in errs[:20]:
                out("  - " + e)
            return 1
        out("%s matches schema %s." % (relp, name))
        return 0
    rep = _validate_all(run)
    bad = {k: v for k, v in rep.items() if v}
    for k, v in sorted(bad.items()):
        out("%s: %d problem(s)" % (k, len(v)))
        for e in v[:5]:
            out("  - " + e)
    if not bad:
        out("All %d artifacts validate against their schemas." % len(rep))
    code = 1 if bad else 0
    if args.report:
        c = cfg(run)
        errors, warnings = _report_checks(run, c)
        errors += ["%s: schema problems" % k for k in bad if k.startswith("output/")]
        ok = not errors
        write_json(p(run, "output", "report-check.json"), {"checked_at": now_iso(), "ok": ok, "errors": errors, "warnings": warnings})
        st = load_state(run)
        for key, g in st.get("groups", {}).items():
            if key.startswith("writer-") and not g.get("merged"):
                g["merged"] = True
        state.touch(st, "report_check")
        save_state(run, st)
        out("Report check: %s (%d errors, %d warnings)." % ("PASS" if ok else "FAIL", len(errors), len(warnings)))
        for e in errors[:15]:
            out("  error: " + e)
        for w in warnings[:10]:
            out("  warning: " + w)
        code = 0 if ok else 1
    return code


# ---------------------------------------------------------------- compare
def _gap_signature(run, card, led):
    urls = set(led[x]["url"] for x in card["supporting_evidence"] if x in led)
    return set(card.get("incumbents", [])) | urls


def cmd_compare(args):
    a, b = args.run_a, args.run_b
    require_run(a)
    require_run(b)
    c = cfg(a)
    ea = set(e["entity_id"] for e in entities(a) if e.get("status") == "included" and (e.get("verified") or {}).get("status") == "ok")
    eb = set(e["entity_id"] for e in entities(b) if e.get("status") == "included" and (e.get("verified") or {}).get("status") == "ok")
    missed, sd = richness.two_source_missing(len(ea), len(eb), len(ea & eb))
    k = c.get("reproducibility.top_k")
    ra = (read_json(p(a, "gaps", "ranking.json"), {}) or {}).get("ranked", [])[:k]
    rb = (read_json(p(b, "gaps", "ranking.json"), {}) or {}).get("ranked", [])[:k]
    la = {r["id"]: r for r in read_jsonl(p(a, "evidence", "ledger.jsonl"))[0]}
    lb = {r["id"]: r for r in read_jsonl(p(b, "evidence", "ledger.jsonl"))[0]}
    ca = {x["gap_id"]: x for x in read_jsonl(p(a, "gaps", "cards.jsonl"))[0]}
    cb = {x["gap_id"]: x for x in read_jsonl(p(b, "gaps", "cards.jsonl"))[0]}
    thr = c.get("reproducibility.gap_match_jaccard")
    matches, mapped_b = [], []
    for x in rb:
        sig_b = _gap_signature(b, cb[x["gap_id"]], lb) if x["gap_id"] in cb else set()
        best, best_j = None, 0.0
        for y in ra:
            sig_a = _gap_signature(a, ca[y["gap_id"]], la) if y["gap_id"] in ca else set()
            jj = richness.jaccard(sig_a, sig_b) if (sig_a or sig_b) else 0.0
            if jj > best_j:
                best, best_j = y["gap_id"], jj
        if best and best_j >= thr:
            matches.append({"run_b": x["gap_id"], "run_a": best, "jaccard": best_j})
            mapped_b.append(best)
        else:
            mapped_b.append("B:" + x["gap_id"])
    result = {"entity_jaccard": richness.jaccard(ea, eb), "entities_a": len(ea), "entities_b": len(eb), "entities_both": len(ea & eb),
              "webster_kemp_missed": missed, "webster_kemp_sd": sd, "top_k": k, "top_k_matches": len(matches),
              "matches": matches, "rbo": stats.rbo([x["gap_id"] for x in ra], mapped_b, c.get("reproducibility.rbo_p")),
              "pass": richness.jaccard(ea, eb) >= c.get("reproducibility.entity_jaccard_min") and len(matches) >= c.get("reproducibility.top_k_match_min")}
    if args.out:
        write_json(args.out, result)
    out(json.dumps(result, indent=2))
    return 0


# ---------------------------------------------------------------- purge
def cmd_purge(args):
    run = args.run
    require_run(run)
    days = args.days if args.days is not None else cfg(run).get("evidence.retention_days")
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    removed = 0
    for meta_path in glob.glob(p(run, "snapshots", "*.meta.json")):
        meta = read_json(meta_path, {}) or {}
        try:
            at = dt.datetime.fromisoformat(meta.get("fetched_at", ""))
        except ValueError:
            continue
        if at < cutoff:
            for ext in (".raw", ".txt"):
                f = meta_path.replace(".meta.json", ext)
                if os.path.exists(f):
                    os.remove(f)
                    removed += 1
            meta["purged_at"] = now_iso()
            write_json(meta_path, meta)
    out("Purged %d snapshot files older than %d days (hashes and metadata kept; quotes in the ledger stay). Re-verification is no longer possible for purged records." % (removed, days))
    return 0
