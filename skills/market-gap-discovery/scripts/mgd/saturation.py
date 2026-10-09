"""`gapscan.py saturation RUN`: the doctoral "~90% intersection" rule made statistical
(method card D04). Sampling units are scout x channel family; snowball-only finds are excluded."""

import itertools
import math

from mgcore import richness, state
from mgcore.jsonio import now_iso, read_json, read_jsonl, write_json

from .common import cfg, included_verified, out, p, require_run, load_state, save_state


def _summary(incidence, z, c):
    s = richness.summarize_incidence(incidence, z=z)
    t, q1, q2, u = s["T"], s["Q1"], s["Q2"], s["U"]
    theta = c.get("landscape.completeness_target_theta")
    s["units_for_coverage"] = richness.units_for_coverage(t, q1, q2, u, c.get("landscape.coverage_target"))
    s["units_for_completeness"] = richness.units_for_fraction(t, q1, q2, s["S_obs"], s["chao2"]["estimate"], theta)
    return s


def cmd_saturation(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    st = load_state(run)
    ls = st["landscape"]
    z = c.get("landscape.z")
    units = read_json(p(run, "landscape", "units.json"), {}) or {}
    sampling_units = {u: m for u, m in units.items() if m.get("mode") in ("landscape", "probe")}
    probe_units = {u for u, m in units.items() if m.get("mode") == "probe"}
    ents = included_verified(read_jsonl(p(run, "landscape", "entities.jsonl"))[0])
    counted = [e for e in ents if set(e.get("found_in_units", [])) & set(sampling_units)]

    def inc_for(kind=None, unit_filter=None):
        inc = {}
        for e in counted:
            if kind and e["kind"] != kind:
                continue
            us = [u for u in e["found_in_units"] if u in sampling_units and (unit_filter is None or unit_filter(u))]
            if us:
                inc[e["entity_id"]] = set(us)
        return inc

    overall = _summary(inc_for(), z, c)
    overall["T"] = len(sampling_units)
    kinds = {}
    for kind in ("product", "community", "directory"):
        capable = {u for u, m in sampling_units.items() if kind in (m.get("kinds") or [])}
        inc = inc_for(kind, lambda u, cap=capable: u in cap)
        s = _summary(inc, z, c) if inc else {"S_obs": 0}
        s["capable_units"] = len(capable)
        kinds[kind] = s

    # Marginal yield of the latest landscape round.
    r = ls.get("round", 0)
    first = {}
    for e in counted:
        rounds = [units[u]["round"] for u in e["found_in_units"] if u in sampling_units and units[u].get("round")]
        if rounds:
            first[e["entity_id"]] = min(rounds)
    before = sum(1 for v in first.values() if v < r)
    new_r = sum(1 for v in first.values() if v == r)
    yield_r = (new_r / float(before)) if before else None

    # Pairwise Jaccard between scouts in the latest round (diagnostic for correlated scouts).
    by_scout = {}
    for e in counted:
        for u in e["found_in_units"]:
            m = units.get(u, {})
            if m.get("mode") == "landscape" and m.get("round") == r:
                by_scout.setdefault(m["scout"], set()).add(e["entity_id"])
    pairs = [richness.jaccard(by_scout[a], by_scout[b]) for a, b in itertools.combinations(sorted(by_scout), 2)]
    mean_j = sum(pairs) / len(pairs) if pairs else None

    # Probe new-share: entities found by the latest probe that no sampling unit found before it.
    # A probe counts only if it ran after the latest sampling round (no round since).
    probe = None
    latest_group = "probe-%d" % ls.get("probe_count", 0)
    latest = [u for u in probe_units if units[u].get("group") == latest_group]
    if latest and ls.get("probe_round") == r:
        last = latest[0]
        found = [e for e in counted if last in e["found_in_units"]]
        new = [e for e in found if not (set(e["found_in_units"]) & (set(sampling_units) - probe_units))]
        probe = {"unit": last, "found": len(found), "new": len(new),
                 "new_share": (len(new) / float(len(found))) if found else 0.0}

    theta = c.get("landscape.completeness_target_theta")
    cov_t = c.get("landscape.coverage_target")
    reasons = []
    est_ok = overall["Q1"] == 0 or (overall["coverage"] >= cov_t and overall["completeness"] >= theta)
    if not est_ok:
        reasons.append("coverage %.3f (target %.2f), completeness %.3f (target %.2f)" % (overall["coverage"], cov_t, overall["completeness"], theta))
    t_ok = overall["T"] >= c.get("landscape.min_units_T")
    if not t_ok:
        reasons.append("only %d sampling units (minimum %d)" % (overall["T"], c.get("landscape.min_units_T")))
    prod = kinds["product"]
    kind_ok = prod.get("S_obs", 0) >= c.get("landscape.min_per_kind")
    if not kind_ok:
        reasons.append("only %d verified products (minimum %d)" % (prod.get("S_obs", 0), c.get("landscape.min_per_kind")))
    for kind in ("community", "directory"):
        s = kinds[kind]
        if s.get("S_obs", 0) >= c.get("landscape.min_per_kind") and s.get("Q1", 0) > 0 and s.get("coverage", 1) < cov_t:
            reasons.append("%s coverage %.3f below target" % (kind, s["coverage"]))
            kind_ok = False
    y_ok = r >= 2 and yield_r is not None and yield_r <= c.get("landscape.max_marginal_yield")
    if not y_ok:
        reasons.append("marginal yield %s in round %d (need <= %.2f from round 2)" % ("n/a" if yield_r is None else "%.3f" % yield_r, r, c.get("landscape.max_marginal_yield")))
    if est_ok and t_ok and kind_ok and y_ok:
        if probe is None:
            verdict = "NEEDS_PROBE"
        elif probe["new_share"] <= c.get("landscape.probe_max_new_share"):
            verdict = "SATURATED"
        elif r >= c.get("landscape.max_rounds"):
            verdict = "STOP_UNSATURATED"
            reasons.append("probe found %.0f%% new items and no rounds remain" % (100 * probe["new_share"]))
        else:
            verdict = "EXPAND"
            reasons.append("probe found %.0f%% new items (max %.0f%%)" % (100 * probe["new_share"], 100 * c.get("landscape.probe_max_new_share")))
    elif r >= c.get("landscape.max_rounds"):
        verdict = "STOP_UNSATURATED"
    else:
        verdict = "EXPAND"
    expand = None
    if verdict == "EXPAND":
        t_need = overall.get("units_for_coverage")
        lo = c.get("landscape.scouts")
        hi = max(lo, overall["T"])
        expand = int(min(hi, max(lo, t_need if t_need is not None else lo * c.get("landscape.units_per_scout"))))
    correlated = bool(mean_j is not None and mean_j > 0.85 and overall["S_obs"] < 15)
    doc = {"computed_at": now_iso(), "round": r, "verdict": verdict, "reasons": reasons, "expand_units": expand,
           "overall": overall, "per_kind": kinds, "marginal_yield": yield_r, "new_in_round": new_r,
           "mean_pairwise_jaccard": mean_j, "correlated_scouts": correlated, "probe": probe,
           "independence": st.get("independence", "full"),
           "note": "All estimates are lower bounds: correlated searches and hard-to-find products make coverage look higher than it is."}
    write_json(p(run, "landscape", "saturation.json"), doc)
    ls["verdict"] = verdict
    ls["expand_units"] = expand
    if verdict in ("SATURATED", "STOP_UNSATURATED"):
        ls["sampling_closed"] = True
    state.touch(st, "saturation")
    save_state(run, st)
    ch = overall["chao2"]
    out("Saturation (round %d): S_obs=%d, T=%d, Q1=%d, Q2=%d | Chao2 %.1f (95%% CI %.1f-%.1f) | completeness %.2f | coverage %.3f%s" % (
        r, overall["S_obs"], overall["T"], overall["Q1"], overall["Q2"], ch["estimate"], ch["ci_low"], ch["ci_high"],
        overall["completeness"], overall["coverage"], "" if yield_r is None else " | yield %.3f" % yield_r))
    if probe:
        out("Probe %s: %d found, %d new (%.0f%%)." % (probe["unit"], probe["found"], probe["new"], 100 * probe["new_share"]))
    out("Verdict: %s%s" % (verdict, (" (k=%d units)" % expand) if expand else ""))
    for reason in reasons:
        out("  - " + reason)
    if correlated:
        out("  - warning: scouts look correlated (mean Jaccard %.2f with few products); diversify personas and channels." % mean_j)
    return 0
