"""Matrices, demand-supply gap map and bursts (method cards D11, D15, D16)."""

import csv
import glob
import os

from mgcore import assoc, bursts, state, stats
from mgcore.jsonio import now_iso, read_json, read_jsonl, write_json

from .common import CliError, alias_map, cfg, entities, resolve_ids, included_verified, out, p, require_run, load_state, save_state

DEMAND_STANCES = ("pain", "wish", "workaround", "switch", "wtp")


def _write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def _coded(run):
    """Verified ledger records joined with coder A's latest codes."""
    codes = {}
    for r in read_jsonl(p(run, "coding", "codes-A.jsonl"))[0]:
        cur = codes.get(r["evidence_id"])
        if cur is None or r["codebook_version"] >= cur["codebook_version"]:
            codes[r["evidence_id"]] = r
    out_ = []
    for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]:
        if r.get("verification", {}).get("status") != "verified":
            continue
        c = codes.get(r["id"])
        out_.append(dict(r, codes=set(c["codes"]) if c else set(), coded_strength=c["strength"] if c else r["strength"]))
    return out_


def _book(run):
    lock = read_json(p(run, "coding", "codebook.lock.json"))
    if not lock:
        raise CliError("no frozen codebook")
    return read_json(p(run, "coding", "codebook.v%d.json" % lock["version"]))


def cmd_matrix(args):
    run = args.run
    require_run(run)
    ents = {e["entity_id"]: e for e in included_verified(entities(run))}
    attrs = {a["entity_id"]: a for a in read_jsonl(p(run, "landscape", "entity-attributes.jsonl"))[0]}
    supply = {s["entity_id"]: s for s in read_jsonl(p(run, "analysis", "supply.jsonl"))[0]}
    cls = read_json(p(run, "landscape", "classification.json"), {}) or {}
    factors = cls.get("competing_factors", [])
    recs = _coded(run)
    book = _book(run)
    pains = [x["id"] for x in book["codes"] if x["type"] == "pain" or x["id"].startswith("X-")]
    ev_by_entity = {}
    amap = alias_map(run)
    for r in recs:
        for eid in resolve_ids(r.get("entity_ids"), amap):
            ev_by_entity.setdefault(eid, []).append(r)
    rows = []
    for eid in sorted(ents):
        a = attrs.get(eid, {})
        pr = a.get("pricing", {})
        s = supply.get(eid, {})
        evs = ev_by_entity.get(eid, [])
        rows.append([eid, "; ".join(ents[eid].get("names", [])), a.get("approach"), a.get("category"),
                     "; ".join(a.get("segments", [])), pr.get("model"), pr.get("min_paid_month"), pr.get("currency"),
                     pr.get("free_tier"), pr.get("per_seat"), "; ".join(a.get("platform", [])), a.get("deployment"),
                     "; ".join(a.get("languages", [])), len(a.get("integrations", [])), "; ".join(s.get("jobs_served", [])),
                     len(evs), sum(1 for r in evs if r["stance"] in DEMAND_STANCES), sum(1 for r in evs if r["stance"] == "praise")])
    _write_csv(p(run, "analysis", "competitor_matrix.csv"),
               ["entity_id", "names", "approach", "category", "segments", "pricing_model", "min_paid_month", "currency",
                "free_tier", "per_seat", "platform", "deployment", "languages", "n_integrations", "jobs_served",
                "evidence_records", "demand_records", "praise_records"], rows)
    ladder = []
    for eid, a in attrs.items():
        pr = a.get("pricing", {})
        ladder.append([eid, pr.get("model"), pr.get("min_paid_month"), pr.get("currency"), pr.get("free_tier"), pr.get("per_seat")])
    ladder.sort(key=lambda r: (r[3] or "ZZZ", r[2] if r[2] is not None else float("inf")))
    _write_csv(p(run, "analysis", "price_ladder.csv"), ["entity_id", "model", "min_paid_month", "currency", "free_tier", "per_seat"], ladder)
    summary = {}
    for r in ladder:
        if r[2] is not None and r[3]:
            summary.setdefault(r[3], []).append(r[2])
    price_summary = {cur: {"n": len(v), "min": min(v), "median": stats.quantile(v, 0.5), "max": max(v)} for cur, v in summary.items()}
    canvas = [[f["id"], f["label"]] + [supply.get(eid, {}).get("factor_levels", {}).get(f["id"]) for eid in sorted(ents)] for f in factors]
    _write_csv(p(run, "analysis", "strategy_canvas.csv"), ["factor_id", "factor"] + sorted(ents), canvas)
    pain_rows = []
    for eid in sorted(ents):
        evs = ev_by_entity.get(eid, [])
        row = [eid]
        for code in pains:
            row.append(len(set(r["author_hash"] if r["author_hash"] != "unknown" else r["id"] for r in evs if code in r["codes"])))
        pain_rows.append(row)
    _write_csv(p(run, "analysis", "pain_by_entity.csv"), ["entity_id"] + pains, pain_rows)
    write_json(p(run, "analysis", "matrix.json"), {"computed_at": now_iso(), "entities": len(ents), "factors": len(factors),
                                                   "price_summary": price_summary})
    st = load_state(run)
    state.touch(st, "matrix")
    save_state(run, st)
    out("Matrices written: %d entities x %d attributes, price ladder (%s), strategy canvas with %d factors." % (
        len(ents), 18, ", ".join("%s n=%d" % (k, v["n"]) for k, v in price_summary.items()) or "no prices", len(factors)))
    return 0


def _author_key(r):
    return r["author_hash"] if r.get("author_hash") not in (None, "unknown") else "rec:" + r["id"]


def cmd_gapmap(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    weights = c.get("evidence.strength_weights")
    book = _book(run)
    job_codes = [x for x in book["codes"] if x["type"] in ("job", "outcome")]
    recs = _coded(run)
    amap = alias_map(run)
    attrs = {a["entity_id"]: a for a in read_jsonl(p(run, "landscape", "entity-attributes.jsonl"))[0]}
    supply = read_jsonl(p(run, "analysis", "supply.jsonl"))[0]
    serves = {}
    for s in supply:
        for j in s["jobs_served"]:
            serves.setdefault(j, set()).add(s["entity_id"])
    approaches = sorted(set(a.get("approach") for a in attrs.values() if a.get("approach")))
    jobs = []
    max_d = 0.0
    for jc in job_codes:
        code = jc["id"]
        dem = [r for r in recs if code in r["codes"] and r["stance"] in DEMAND_STANCES]
        per_author = {}
        for r in dem:
            k = _author_key(r)
            per_author[k] = max(per_author.get(k, 0.0), weights.get(r.get("coded_strength") or r["strength"], 0.0))
        d = sum(per_author.values())
        max_d = max(max_d, d)
        incumbents = serves.get(code, set())
        about = [r for r in recs if code in r["codes"] and set(resolve_ids(r.get("entity_ids"), amap)) & incumbents]
        praise = set(_author_key(r) for r in about if r["stance"] == "praise")
        pain = set(_author_key(r) for r in about if r["stance"] in ("pain", "switch"))
        if praise or pain:
            s_p, flag = 10.0 * len(praise) / float(len(praise) + len(pain)), None
        else:
            s_p, flag = 0.0, "no_satisfaction_data"
        frag = [r for r in dem if r["codes"] & {"X-FRAG", "X-INTEG"}]
        by_approach = {ap: sorted(e for e in incumbents if attrs.get(e, {}).get("approach") == ap) for ap in approaches}
        authors = len(per_author)
        n_sup = len(incumbents)
        if n_sup <= c.get("gapmap.absolute_supply_max") and authors >= c.get("gapmap.min_demand_authors"):
            cell = "absolute"
        elif n_sup >= c.get("gapmap.synthesis_supply_min") and dem and len(frag) / float(len(dem)) >= c.get("gapmap.synthesis_fragmentation_share"):
            cell = "synthesis"
        else:
            cell = "none"
        jobs.append({"code": code, "label": jc["label"], "type": jc["type"], "job_step": jc.get("job_step"),
                     "demand_weighted": d, "demand_authors": authors,
                     "demand_domains": len(set(r.get("domain") for r in dem)), "demand_records": len(dem),
                     "supply": n_sup, "supply_by_approach": {k: len(v) for k, v in by_approach.items()},
                     "incumbents": sorted(incumbents), "satisfaction_proxy": s_p, "flag": flag,
                     "fragmentation_share": (len(frag) / float(len(dem))) if dem else 0.0, "cell": cell,
                     "evidence_ids": sorted(r["id"] for r in dem)[:50]})
    for j in jobs:
        i_p = 10.0 * j["demand_weighted"] / max_d if max_d else 0.0
        j["importance_proxy"] = i_p
        j["opportunity_proxy"] = i_p + max(i_p - j["satisfaction_proxy"], 0.0)
    jobs.sort(key=lambda j: (-j["opportunity_proxy"], j["code"]))
    seg_ids = set(x["id"] for x in book["codes"] if x["type"] == "segment")
    pain_ids = set(x["id"] for x in book["codes"] if x["type"] == "pain" or x["id"].startswith("X-"))
    pairs = assoc.cooccurrence([r["codes"] for r in recs], keep=lambda x: x in seg_ids or x in pain_ids)
    assoc_rows = [a for a in assoc.association_strength(pairs, c.get("gapmap.assoc_min_cooccurrence"),
                                                        between=(lambda x: x in seg_ids, lambda x: x in pain_ids))
                  if a["observed_over_expected"] > 1.0]
    _write_csv(p(run, "analysis", "association.csv"), ["a", "b", "count", "association_strength", "observed_over_expected"],
               [[a["a"], a["b"], a["count"], round(a["association_strength"], 6), round(a["observed_over_expected"], 3)] for a in assoc_rows])
    seg_demand = {}
    for r in recs:
        if r["stance"] not in DEMAND_STANCES:
            continue
        for s in r["codes"] & seg_ids:
            for j in r["codes"] & set(x["code"] for x in jobs):
                seg_demand.setdefault(s, {}).setdefault(j, set()).add(_author_key(r))
    doc = {"computed_at": now_iso(), "note": "opportunity_proxy is for ranking only; never compare it with survey ODI thresholds (10/12/15).",
           "approaches": approaches, "jobs": jobs, "association": assoc_rows,
           "segment_x_job_authors": {s: {j: len(v) for j, v in d.items()} for s, d in seg_demand.items()}}
    write_json(p(run, "analysis", "gapmap.json"), doc)
    st = load_state(run)
    state.touch(st, "gapmap")
    save_state(run, st)
    cells = {}
    for j in jobs:
        cells[j["cell"]] = cells.get(j["cell"], 0) + 1
    out("Gap map: %d job/outcome codes (%s); %d segment-specific pain pairs. Top proxy opportunities: %s" % (
        len(jobs), ", ".join("%d %s" % (v, k) for k, v in sorted(cells.items())), len(assoc_rows),
        ", ".join("%s %.1f" % (j["code"], j["opportunity_proxy"]) for j in jobs[:5])))
    return 0


def cmd_bursts(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    st = load_state(run)
    import random
    rng = random.Random("%s|bursts" % st.get("seed"))
    results = []
    for path in sorted(glob.glob(p(run, "evidence", "signals", "*.json"))):
        sig = read_json(path)
        pts = sig["points"]
        if sig["kind"] == "proportion":
            obs, pval = bursts.shuffle_test([(x["d"], x["r"]) for x in pts], rng, shuffles=c.get("bursts.shuffles"),
                                           s=c.get("bursts.s"), gamma=c.get("bursts.gamma"))
            bl = [{"start": pts[b["start"]]["period"], "end": pts[b["end"]]["period"], "weight": b["weight"]} for b in obs["bursts"]]
            results.append({"series_id": sig["series_id"], "term": sig["term"], "source": sig["source"], "kind": "proportion",
                            "bursts": bl, "p_value": pval, "significant": bool(bl) and pval < c.get("bursts.alpha")})
        else:
            tr = bursts.trend([x["value"] for x in pts])
            results.append({"series_id": sig["series_id"], "term": sig["term"], "source": sig["source"], "kind": "absolute", "trend": tr})
    write_json(p(run, "evidence", "bursts.json"), {"computed_at": now_iso(), "series": results})
    state.touch(st, "bursts")
    save_state(run, st)
    sig = [r for r in results if r.get("significant")]
    out("Bursts: %d series analysed; %d with a significant burst (p < %.2f): %s" % (
        len(results), len(sig), c.get("bursts.alpha"), ", ".join("%s %s..%s" % (r["term"], r["bursts"][0]["start"], r["bursts"][-1]["end"]) for r in sig) or "none"))
    return 0
