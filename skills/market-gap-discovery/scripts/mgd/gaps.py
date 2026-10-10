"""Gap construction and appraisal: variants (D19), cards check (D20), certainty (D22),
sizing (D24) and scoring with sensitivity (D23)."""

import csv
import json
import os
import random

from mgcore import state, stats
from mgcore.jsonio import now_iso, read_json, read_jsonl, write_json, write_jsonl

from . import opportunities
from .common import CliError, alias_map, cfg, entities, resolve_ids, included_verified, out, p, protocol, require_run, load_state, save_state, validate

LEVELS = ["Very low", "Low", "Moderate", "High"]


def _ledger_map(run):
    return {r["id"]: r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]}


def _author(r):
    return r["author_hash"] if r.get("author_hash") not in (None, "unknown") else None


def _book(run):
    lock = read_json(p(run, "coding", "codebook.lock.json"))
    return read_json(p(run, "coding", "codebook.v%d.json" % lock["version"])) if lock else None


def _codes_a(run):
    best = {}
    for r in read_jsonl(p(run, "coding", "codes-A.jsonl"))[0]:
        cur = best.get(r["evidence_id"])
        if cur is None or r["codebook_version"] >= cur["codebook_version"]:
            best[r["evidence_id"]] = r
    return best


# ---------------------------------------------------------------- variants
def cmd_variants(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    dims = protocol(run).get("variation_dimensions") or {}
    attrs = {a["entity_id"]: a for a in read_jsonl(p(run, "landscape", "entity-attributes.jsonl"))[0]}
    ents = [e for e in included_verified(entities(run)) if e["kind"] == "product" and e["entity_id"] in attrs]
    praise = {}
    amap = alias_map(run)
    for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]:
        if r.get("verification", {}).get("status") == "verified" and r["stance"] == "praise":
            for eid in resolve_ids(r.get("entity_ids"), amap):
                praise[eid] = praise.get(eid, 0) + 1

    def strength(e):
        s = attrs[e["entity_id"]].get("signals") or {}
        return (praise.get(e["entity_id"], 0), s.get("ratings_count") or 0, s.get("installs") or 0, s.get("stars") or 0, e["entity_id"])
    proven = sorted(ents, key=strength, reverse=True)[: c.get("variation.top_products")]
    getters = {"segment": lambda a: a.get("segments", []), "language": lambda a: a.get("languages", []),
               "platform": lambda a: a.get("platform", []), "integration": lambda a: a.get("integrations", []),
               "price_tier": lambda a: [a.get("pricing", {}).get("model")]}
    cands = []
    for e in proven:
        a = attrs[e["entity_id"]]
        for dim in sorted(dims):
            for val in dims[dim]:
                if dim == "ai_native":
                    if val is not True:
                        continue
                    have, supplied = [], []
                elif dim in getters:
                    have = getters[dim](a)
                    if val in have:
                        continue
                    supplied = sorted(o for o, oa in attrs.items() if o != e["entity_id"] and oa.get("category") == a.get("category") and val in getters[dim](oa))
                else:
                    have, supplied = [], []
                cands.append({"base_entity": e["entity_id"], "category": a.get("category"), "dimension": dim,
                              "from": have, "to": val, "supplied_by": supplied,
                              "status": "supplied" if supplied else ("unknown-supply" if dim not in getters else "needs_evidence")})
    cands = cands[: c.get("variation.max_candidates")]
    for i, v in enumerate(cands, 1):
        v["variant_id"] = "VAR-%03d" % i
    write_jsonl(p(run, "gaps", "variants.jsonl"), cands)
    st = load_state(run)
    state.touch(st, "variants")
    save_state(run, st)
    open_ = sum(1 for v in cands if v["status"] != "supplied")
    out("Variants: %d candidates from %d proven products (%d without existing supply). Each needs evidence before it becomes a card." % (
        len(cands), len(proven), open_))
    return 0


# ---------------------------------------------------------------- cards check
def _opp_ctx(run, cards):
    """Opportunity context (traction percentiles, prices) only when some card has a lens other than gap."""
    if any((x.get("lens") or "gap") != "gap" for x in cards):
        return opportunities.Ctx(run)
    return None


def near_misses(run, limit=3):
    """Insufficient cards that more evidence could fix, closest to passing first.

    Returns [{gap_id, title, codes, shortfall, domains}] from gaps/card-check.json; `domains` are the
    card's current supporting domains, which a targeted miner should avoid in favour of new ones."""
    check = read_json(p(run, "gaps", "card-check.json"), {}) or {}
    cards = {x["gap_id"]: x for x in read_jsonl(p(run, "gaps", "cards.jsonl"))[0]}
    led = _ledger_map(run)
    rows = []
    for gid, res in (check.get("cards") or {}).items():
        if res.get("pass") or not res.get("fixable_by_evidence") or gid not in cards:
            continue
        card = cards[gid]
        doms = sorted(set(led[e].get("domain") for e in card.get("supporting_evidence", []) if e in led and led[e].get("domain")))
        gap = sum(res.get("shortfall", {}).values())
        rows.append({"gap_id": gid, "title": card.get("title"), "codes": card.get("codes", []),
                     "shortfall": res.get("shortfall", {}), "domains": doms, "_gap": gap})
    rows.sort(key=lambda x: (x["_gap"], x["gap_id"]))
    for x in rows:
        x.pop("_gap")
    return rows[:limit]


def domain_shares(run):
    """Share of verified evidence records per registrable domain, largest first."""
    led = [r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0] if r.get("verification", {}).get("status") == "verified"]
    counts = {}
    for r in led:
        counts[r.get("domain")] = counts.get(r.get("domain"), 0) + 1
    n = float(len(led)) or 1.0
    return [{"domain": d, "records": k, "share": round(k / n, 3)} for d, k in sorted(counts.items(), key=lambda x: (-x[1], str(x[0])))]


def cmd_cards_check(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    recs, errs = read_jsonl(p(run, "gaps", "cards.jsonl"))
    problems = ["line %d: invalid JSON" % n for n, _m in errs]
    led = _ledger_map(run)
    book = _book(run) or {"codes": []}
    codes = set(x["id"] for x in book["codes"])
    wn = set(x.get("id") for x in read_jsonl(p(run, "evidence", "why-now.jsonl"))[0])
    series = set(os.path.splitext(f)[0] for f in os.listdir(p(run, "evidence", "signals"))) if os.path.isdir(p(run, "evidence", "signals")) else set()
    ents = {e["entity_id"]: e for e in entities(run)}
    gm = read_json(p(run, "analysis", "gapmap.json"), {}) or {}
    cells = {j["code"]: j["cell"] for j in gm.get("jobs", [])}
    results = {}
    seen_ids = set()
    octx = _opp_ctx(run, recs)
    for i, card in enumerate(recs, 1):
        e = validate(card, "gap-card")
        if e:
            problems.append("card %d (%s): %s" % (i, card.get("gap_id", "?"), "; ".join(e[:3])))
            continue
        if card["gap_id"] in seen_ids:
            problems.append("duplicate gap_id %s" % card["gap_id"])
            continue
        seen_ids.add(card["gap_id"])
        reasons = []
        sup = []
        for eid in card["supporting_evidence"]:
            r = led.get(eid)
            if not r:
                reasons.append("%s does not exist" % eid)
            elif r.get("verification", {}).get("status") != "verified":
                reasons.append("%s is not verified" % eid)
            else:
                sup.append(r)
        for eid in card["counter_evidence"]:
            if eid not in led:
                reasons.append("counter evidence %s does not exist" % eid)
        bad_codes = [x for x in card["codes"] + card["segment_codes"] if x not in codes]
        if bad_codes:
            reasons.append("unknown codes: %s" % ", ".join(bad_codes))
        bad_wn = [x for x in card["why_now"] if x not in wn]
        if bad_wn:
            reasons.append("unknown why-now ids: %s" % ", ".join(bad_wn))
        authors = set(_author(r) for r in sup if _author(r))
        domains = set(r.get("domain") for r in sup)
        types = set(r["source_type"] for r in sup)
        nums = {"records": len(sup), "domains": len(domains), "source_types": len(types), "authors": len(authors)}
        if len(sup) < c.get("gap_card.min_records"):
            reasons.append("%d verified supporting records (need %d)" % (len(sup), c.get("gap_card.min_records")))
        if len(domains) < c.get("gap_card.min_domains"):
            reasons.append("%d domains (need %d)" % (len(domains), c.get("gap_card.min_domains")))
        if len(types) < c.get("gap_card.min_source_types"):
            reasons.append("%d source types (need %d)" % (len(types), c.get("gap_card.min_source_types")))
        if len(authors) < c.get("gap_card.min_authors"):
            reasons.append("%d distinct authors (need %d)" % (len(authors), c.get("gap_card.min_authors")))
        if c.get("gap_card.require_triangulation"):
            lens = card.get("lens") or "gap"
            pain = any(r["stance"] in ("pain", "wish", "workaround", "switch") for r in sup)
            demand = bool(set(card.get("demand_signals") or []) & series) or any(
                r["stance"] == "wtp" or r["strength"] == "S4" or r["source_type"] == "job-post" for r in sup)
            base = list(card.get("base_entities") or []) + list(card["incumbents"])
            if lens != "gap":
                # Other lenses build on proven products: their installs and ratings (script-made traction) are demand.
                prov = opportunities.proven(octx, base)
                nums["proven_products"] = len(prov)
                demand = demand or len(prov) >= c.get("opportunity.min_proven_products")
                supply = bool(base) and all(ents.get(x, {}).get("verified", {}).get("status") == "ok" for x in base)
            else:
                supply = (bool(card["incumbents"]) and all(ents.get(x, {}).get("verified", {}).get("status") == "ok" for x in card["incumbents"])) \
                    or any(cells.get(x) == "absolute" for x in card["codes"])
            nums["triangulation"] = {"pain": pain, "demand": demand, "supply": supply}
            if not (pain and demand and supply):
                reasons.append("triangulation incomplete (pain=%s, demand=%s, supply=%s)" % (pain, demand, supply))
        ok = not reasons
        card["status"] = "candidate" if ok else "insufficient"
        # Structured shortfall: what more evidence could fix (counts, missing pain/demand) versus what
        # it cannot (bad ids, unknown codes, no verified supply). Drives the targeted evidence round.
        short = {k: c.get("gap_card.min_" + k) - nums[k] for k in ("records", "domains", "source_types", "authors")
                 if nums[k] < c.get("gap_card.min_" + k)}
        tri = nums.get("triangulation") or {}
        short.update({k: 1 for k in ("pain", "demand") if tri and not tri.get(k)})
        count_reasons = sum(1 for x in reasons if "(need" in x or x.startswith("triangulation"))
        fixable = bool(reasons) and count_reasons == len(reasons) and tri.get("supply", True)
        results[card["gap_id"]] = {"pass": ok, "reasons": reasons, "numbers": nums, "shortfall": short, "fixable_by_evidence": fixable}
    variants = read_jsonl(p(run, "gaps", "variants.jsonl"))[0]
    used = set(card.get("variant_of") for card in recs if card.get("variant_of"))
    discarded = [v["variant_id"] for v in variants if v["variant_id"] not in used]
    doc = {"computed_at": now_iso(), "ok": not problems, "problems": problems, "cards": results,
           "discarded_variants": discarded, "discard_reason": "no card with verified evidence was built from these variants"}
    write_json(p(run, "gaps", "card-check.json"), doc)
    if not problems:
        write_jsonl(p(run, "gaps", "cards.jsonl"), recs)
    st = load_state(run)
    g = st.get("groups", {}).get("synthesis")
    if g and not problems:
        g["merged"] = True
    state.touch(st, "cards_check")
    save_state(run, st)
    passed = sum(1 for r in results.values() if r["pass"])
    out("Cards check: %d cards, %d pass, %d insufficient; %d variants discarded (no evidence)." % (len(results), passed, len(results) - passed, len(discarded)))
    for prob in problems[:10]:
        out("  fix: " + prob)
    for gid, r in results.items():
        if not r["pass"]:
            out("  %s insufficient: %s" % (gid, "; ".join(r["reasons"][:3])))
    return 1 if problems else 0


# ---------------------------------------------------------------- certainty
def _level(share, moderate, serious):
    if share > serious:
        return "serious"
    if share > moderate:
        return "moderate"
    return "none"


def cmd_certainty(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    led = _ledger_map(run)
    codes_a = _codes_a(run)
    book = _book(run)
    types = {x["id"]: x["type"] for x in book["codes"]}
    agr = read_json(p(run, "coding", "agreement.json"), {}) or {}
    weak = set(agr.get("weak_codes", []))
    prov = set(agr.get("provisional_codes", []))
    sat = read_json(p(run, "landscape", "saturation.json"), {}) or {}
    st = load_state(run)
    degraded = st.get("independence") == "degraded"
    low_cov = (sat.get("overall", {}).get("coverage", 0) < c.get("certainty.coverage_moderate_below")) or sat.get("verdict") == "STOP_UNSATURATED"
    verified_ids = [k for k, r in led.items() if r.get("verification", {}).get("status") == "verified"]
    out_doc = {}
    all_cards = read_jsonl(p(run, "gaps", "cards.jsonl"))[0]
    octx = _opp_ctx(run, all_cards)
    for card in all_cards:
        if card["status"] in ("insufficient", "killed"):
            continue
        sup = [led[x] for x in card["supporting_evidence"] if x in led and led[x].get("verification", {}).get("status") == "verified"]
        con = [led[x] for x in card["counter_evidence"] if x in led and led[x].get("verification", {}).get("status") == "verified"]
        n = len(sup) or 1
        bias = sum(1 for r in sup if r["credibility"] in ("vendor", "incentivized", "affiliate")) / float(n)
        incons = len(con) / float(len(sup) + len(con)) if (sup or con) else 0.0
        indirect = sum(1 for r in sup if r.get("indirect")) / float(n)
        authors = set(_author(r) for r in sup if _author(r))
        conc = {}
        conc["risk_of_bias"] = {"level": _level(bias, c.get("certainty.bias_moderate"), c.get("certainty.bias_serious")), "share": bias}
        conc["inconsistency"] = {"level": _level(incons, c.get("certainty.inconsistency_moderate"), c.get("certainty.inconsistency_serious")), "share": incons}
        conc["indirectness"] = {"level": _level(indirect, c.get("certainty.indirect_moderate"), c.get("certainty.indirect_serious")), "share": indirect}
        a_lvl = "serious" if len(authors) < c.get("certainty.authors_serious_below") else ("moderate" if len(authors) < c.get("certainty.authors_moderate_below") else "none")
        pain_codes = [x for x in card["codes"] if types.get(x) == "pain" or x.startswith("X-")]
        job_codes = [x for x in card["codes"] if types.get(x) in ("job", "outcome")]
        den = [k for k in verified_ids if k in codes_a and set(codes_a[k]["codes"]) & set(job_codes)]
        num = [k for k in den if set(codes_a[k]["codes"]) & set(pain_codes)]
        ci = None
        if den:
            lo, hi, _p = stats.wilson(len(num), len(den))
            ci = {"k": len(num), "n": len(den), "low": lo, "high": hi, "width": hi - lo}
        ci_lvl = "moderate" if ci and ci["width"] > c.get("certainty.ci_width_moderate") else "none"
        imp = "serious" if "serious" in (a_lvl, ci_lvl) else ("moderate" if "moderate" in (a_lvl, ci_lvl) else "none")
        conc["imprecision"] = {"level": imp, "authors": len(authors), "prevalence_ci": ci}
        used_weak = sorted(set(card["codes"]) & weak)
        used_prov = sorted(set(card["codes"]) & prov)
        conc["methodological_limitations"] = {"level": "serious" if used_weak else ("moderate" if used_prov else "none"),
                                              "weak_codes": used_weak, "provisional_codes": used_prov}
        pb = "serious" if (low_cov and degraded) else ("moderate" if (low_cov or degraded) else "none")
        conc["publication_bias"] = {"level": pb, "low_coverage": low_cov, "independence_degraded": degraded}
        pts = 0
        for k in ("methodological_limitations", "inconsistency", "imprecision", "indirectness"):
            pts += {"serious": 2, "moderate": 1}.get(conc[k]["level"], 0)
        pain_cert = "High" if pts == 0 else ("Moderate" if pts == 1 else ("Low" if pts <= 3 else "Very low"))
        lvl = 1
        moderates = 0
        for k in ("risk_of_bias", "inconsistency", "indirectness", "imprecision", "publication_bias"):
            if conc[k]["level"] == "serious":
                lvl -= 1
            elif conc[k]["level"] == "moderate":
                moderates += 1
        lvl -= moderates // 2
        lvl = max(lvl, 0)
        s4 = [r for r in sup if r["strength"] == "S4"]
        s4_auth = set(_author(r) for r in s4 if _author(r))
        magnitude = len(s4_auth) >= c.get("certainty.magnitude_min_authors") and len(set(r.get("domain") for r in s4)) >= 2
        scale_auth = set(_author(r) for r in sup if _author(r) and "X-SCALE" in (codes_a.get(r["id"], {}).get("codes") or []))
        dose = len(scale_auth) >= c.get("certainty.dose_response_min_authors")
        # Market spend (lenses other than gap): proven products with paid plans show money already flows for this job.
        spend = False
        if (card.get("lens") or "gap") != "gap" and octx is not None:
            spend = len(opportunities.proven(octx, list(card.get("base_entities") or []) + card["incumbents"], paid_only=True)) \
                >= c.get("certainty.market_spend_min_products")
        lvl = min(lvl + (1 if (magnitude or spend) else 0) + (1 if dose else 0), 2)
        out_doc[card["gap_id"]] = {"pain": pain_cert, "demand": LEVELS[lvl], "demand_strength": "weak", "concerns": conc,
                                   "pain_points": pts, "upgrades": {"magnitude": magnitude, "dose_response": dose, "market_spend": spend},
                                   "note": "Desk-only: demand strength stays weak until validation experiments."}
    write_json(p(run, "gaps", "certainty.json"), {"computed_at": now_iso(), "gaps": out_doc})
    state.touch(st, "certainty")
    save_state(run, st)
    out("Certainty rated for %d gaps: %s" % (len(out_doc), ", ".join("%s pain=%s demand=%s" % (k, v["pain"], v["demand"]) for k, v in sorted(out_doc.items()))))
    return 0


# ---------------------------------------------------------------- sizing
def cmd_size(args):
    run = args.run
    require_run(run)
    doc = read_json(p(run, "gaps", "sizing-inputs.json"))
    if not doc:
        raise CliError("gaps/sizing-inputs.json is missing")
    errs = validate(doc, "sizing-inputs")
    for gid, g in (doc.get("gaps") or {}).items():
        for k in ("accounts", "arpa_year_usd", "reachable_share", "conversion", "win_rate"):
            v = g.get(k, {})
            if v and not (v["low"] <= v["base"] <= v["high"]):
                errs.append("%s.%s: needs low <= base <= high" % (gid, k))
            if v.get("snapshot") and not os.path.exists(p(run, "snapshots", v["snapshot"] + ".raw")):
                errs.append("%s.%s: snapshot %s does not exist" % (gid, k, v["snapshot"]))
    if errs:
        raise CliError("sizing inputs need fixing:\n  " + "\n  ".join(errs[:12]))
    res = {}
    for gid, g in doc["gaps"].items():
        row = {}
        for lvl in ("low", "base", "high"):
            tam = g["accounts"][lvl] * g["arpa_year_usd"][lvl]
            sam = tam * g["reachable_share"][lvl]
            som = sam * g["conversion"][lvl] * g["win_rate"][lvl]
            row[lvl] = {"tam": tam, "sam": sam, "som": som}
        res[gid] = {"usd_per_year": row, "sources": {k: g[k]["source"] for k in ("accounts", "arpa_year_usd")},
                    "assumptions": {k: g[k]["rationale"] for k in ("reachable_share", "conversion", "win_rate")}}
    write_json(p(run, "gaps", "sizing.json"), {"computed_at": now_iso(), "gaps": res,
                                               "note": "Bottom-up: accounts x ARPA; reachable share, conversion and win rate are assumptions for validation."})
    st = load_state(run)
    g = st.get("groups", {}).get("sizing")
    if g:
        g["merged"] = True
    state.touch(st, "size")
    save_state(run, st)
    out("Sizing: " + "; ".join("%s SOM base $%.0f/yr (range %.0f-%.0f)" % (k, v["usd_per_year"]["base"]["som"], v["usd_per_year"]["low"]["som"], v["usd_per_year"]["high"]["som"]) for k, v in sorted(res.items())))
    return 0


# ---------------------------------------------------------------- scoring
_ORDER3 = {"low": 0, "medium": 1, "high": 2}
_BUILD = {"no": 0, "partial": 1, "yes": 2}


def _gates(j, gates):
    reasons = []
    if _ORDER3[j["regulatory_load"]] > _ORDER3[gates["regulatory_load_max"]]:
        reasons.append("regulatory load %s" % j["regulatory_load"])
    if _ORDER3[j["human_ops_burden"]] > _ORDER3[gates["human_ops_burden_max"]]:
        reasons.append("human-ops burden %s" % j["human_ops_burden"])
    if _BUILD[j["agent_buildability"]] < _BUILD[gates["agent_buildability_min"]]:
        reasons.append("agent-buildability %s" % j["agent_buildability"])
    if j["platform_risk"] > gates["platform_risk_max"]:
        reasons.append("platform risk %d" % j["platform_risk"])
    if gates.get("tos_feasible_required") and not j["tos_feasible"]:
        reasons.append("ToS not feasible")
    return reasons


def cmd_score(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    st = load_state(run)
    led = _ledger_map(run)
    cards = [x for x in read_jsonl(p(run, "gaps", "cards.jsonl"))[0] if x["status"] in ("survives", "weakened", "killed")]
    judg = {j["gap_id"]: j for j in read_jsonl(p(run, "gaps", "judgments.jsonl"))[0]}
    cert = (read_json(p(run, "gaps", "certainty.json"), {}) or {}).get("gaps", {})
    sizing = (read_json(p(run, "gaps", "sizing.json"), {}) or {}).get("gaps", {})
    wn = {x["id"]: x for x in read_jsonl(p(run, "evidence", "why-now.jsonl"))[0]}
    burst_sig = set(s["series_id"] for s in (read_json(p(run, "evidence", "bursts.json"), {}) or {}).get("series", []) if s.get("significant"))
    gm = read_json(p(run, "analysis", "gapmap.json"), {}) or {}
    cells = {j["code"]: j["cell"] for j in gm.get("jobs", [])}
    supply = read_jsonl(p(run, "analysis", "supply.jsonl"))[0]
    attrs = {a["entity_id"]: a for a in read_jsonl(p(run, "landscape", "entity-attributes.jsonl"))[0]}
    target = (protocol(run).get("ambition") or {}).get("min_arr_usd")
    weights = c.get("scoring.weights")
    gates = c.get("scoring.gates")
    rows, scored, excluded = [], [], []
    octx = _opp_ctx(run, cards)
    for card in cards:
        gid = card["gap_id"]
        if card["status"] == "killed":
            excluded.append({"gap_id": gid, "title": card["title"], "reasons": ["red-team verdict: killed"]})
            continue
        j = judg.get(gid)
        if not j:
            excluded.append({"gap_id": gid, "title": card["title"], "reasons": ["no red-team judgment"]})
            continue
        g = _gates(j, gates)
        if g:
            excluded.append({"gap_id": gid, "title": card["title"], "reasons": g})
            continue
        sup = [led[x] for x in card["supporting_evidence"] if x in led and led[x].get("verification", {}).get("status") == "verified"]
        auth = lambda rs: set(_author(r) for r in rs if _author(r))  # noqa: E731
        sc, why = {}, {}
        s3 = [r for r in sup if r["strength"] in ("S3", "S4") and r["stance"] in ("workaround", "switch")]
        s4 = [r for r in sup if r["strength"] == "S4"]
        sc["pain"] = 3 if (len(auth(s4)) >= 2 or len(auth(sup)) >= 20) else (2 if len(auth(s3)) >= 2 else 1)
        why["pain"] = "%d authors; %d S3+ workaround/switch authors; %d S4 authors" % (len(auth(sup)), len(auth(s3)), len(auth(s4)))
        pay_recs = [r for r in sup if r["strength"] == "S4" or r["stance"] == "wtp"]
        job_codes = set(card["codes"])
        paid_inc = [s["entity_id"] for s in supply if set(s["jobs_served"]) & job_codes and (attrs.get(s["entity_id"], {}).get("pricing", {}).get("min_paid_month") or 0) > 0]
        lens = card.get("lens") or "gap"
        spend = opportunities.proven(octx, list(card.get("base_entities") or []) + card["incumbents"], paid_only=True) \
            if (lens != "gap" and octx is not None) else []
        if len(auth(pay_recs)) >= 3 and len(set(r.get("domain") for r in pay_recs)) >= 2:
            sc["pay"] = 3
        elif pay_recs or len(spend) >= c.get("certainty.market_spend_min_products"):
            sc["pay"] = 2
        elif paid_inc:
            sc["pay"] = 1
        else:
            sc["pay"] = 0
        why["pay"] = "%d wtp/S4 records from %d authors; %d paid incumbents%s" % (
            len(pay_recs), len(auth(pay_recs)), len(paid_inc), "; %d proven paid products (market spend)" % len(spend) if spend else "")
        som = ((sizing.get(gid) or {}).get("usd_per_year") or {}).get("base", {}).get("som")
        if som is None or not target:
            sc["size"] = 0
        else:
            sc["size"] = 3 if som >= 3 * target else (2 if som >= target else (1 if som >= 0.25 * target else 0))
        why["size"] = "SOM base %s vs target %s" % (som, target)
        cell_types = set(cells.get(x) for x in card["codes"])
        if card["status"] == "weakened":
            sc["competition"] = 1
        elif lens != "gap":
            # Clone-wedge, port, bundle and the rest enter markets with incumbents by design: an open wedge earns 2, never 3.
            sc["competition"] = 2
        else:
            sc["competition"] = 3 if (cell_types & {"absolute", "synthesis"}) else 2
        why["competition"] = "red team %s; lens %s; cells %s" % (card["status"], lens, ", ".join(sorted(x for x in cell_types if x)))
        strengths = [wn[x]["strength"] for x in card["why_now"] if x in wn]
        strong = [s for s in strengths if s in ("moderate", "strong")]
        burst = bool(set(card.get("demand_signals") or []) & burst_sig)
        sc["why_now"] = 3 if (len(strong) >= 2 or burst) else (2 if strong else (1 if strengths else 0))
        why["why_now"] = "%d catalysts (%d moderate/strong); significant burst: %s" % (len(strengths), len(strong), burst)
        ch = j.get("reach_channels", [])
        sized = [x for x in ch if x.get("size") is not None]
        typed = [x for x in ch if x["type"] in ("marketplace", "integration", "keyword") and x.get("evidence")]
        sc["reach"] = 3 if (len(ch) >= 2 and typed) else (2 if len(sized) >= 2 else (1 if ch else 0))
        why["reach"] = "%d channels (%d sized, %d marketplace/integration/keyword with evidence)" % (len(ch), len(sized), len(typed))
        sc["right_to_win"] = j["right_to_win"]
        why["right_to_win"] = j["rationale"]["right_to_win"]
        total = 100.0 * sum(weights[k] * sc[k] for k in weights) / 3.0
        ct = cert.get(gid, {})
        scored.append({"gap_id": gid, "title": card["title"], "lens": lens, "scores": sc, "why": why, "total": total,
                       "certainty": {"pain": ct.get("pain"), "demand": ct.get("demand"), "demand_strength": ct.get("demand_strength", "weak")},
                       "authors": len(auth(sup))})
        for k in weights:
            rows.append([gid, k, sc[k], weights[k], why[k]])
    rank_of = {"High": 3, "Moderate": 2, "Low": 1, "Very low": 0, None: -1}

    def key(x, tot):
        return (-tot, -rank_of.get(x["certainty"]["pain"], -1), -rank_of.get(x["certainty"]["demand"], -1), -x["authors"], x["gap_id"])
    scored.sort(key=lambda x: key(x, x["total"]))
    rng = random.Random("%s|score" % st.get("seed"))
    names = sorted(weights)
    base = [weights[k] for k in names]
    conc = c.get("scoring.dirichlet_concentration")
    top_n = c.get("scoring.top_n")
    hits = {x["gap_id"]: 0 for x in scored}
    ranks = {x["gap_id"]: [] for x in scored}
    for _ in range(c.get("scoring.draws")):
        w = dict(zip(names, stats.dirichlet([conc * b for b in base], rng)))
        order = sorted(scored, key=lambda x: key(x, 100.0 * sum(w[k] * x["scores"][k] for k in names) / 3.0))
        for i, x in enumerate(order, 1):
            ranks[x["gap_id"]].append(i)
            if i <= top_n:
                hits[x["gap_id"]] += 1
    draws = float(c.get("scoring.draws"))
    ranked = []
    for i, x in enumerate(scored, 1):
        ranked.append(dict(x, rank=i, p_top3=hits[x["gap_id"]] / draws, median_rank=stats.quantile(ranks[x["gap_id"]], 0.5)))
    with open(p(run, "gaps", "scores.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["gap_id", "criterion", "score", "weight", "rationale"])
        for r in rows:
            w.writerow(r)
    write_json(p(run, "gaps", "ranking.json"), {"computed_at": now_iso(), "weights": weights, "ranked": ranked, "excluded": excluded,
                                                "note": "Scores rank desk evidence; demand strength stays weak until validation."})
    state.touch(st, "score")
    save_state(run, st)
    out("Ranking: " + "; ".join("#%d %s %.1f (p_top3 %.2f)" % (x["rank"], x["gap_id"], x["total"], x["p_top3"]) for x in ranked) +
        ("; excluded: %s" % ", ".join("%s (%s)" % (e["gap_id"], "; ".join(e["reasons"])) for e in excluded) if excluded else ""))
    return 0
