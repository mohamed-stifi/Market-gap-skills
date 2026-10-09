"""Theme saturation: incidence coverage over records x codes, plus the Guest, Namey & Chen
(2020) base/run test.

Records (posts, reviews, interviews) are the sampling units; codes are the "species".
"""

from . import richness


def theme_incidence(coded_records):
    """coded_records: ordered list of (record_id, iterable_of_codes). Returns code -> set(records)."""
    inc = {}
    for rid, codes in coded_records:
        for c in set(codes):
            inc.setdefault(c, set()).add(rid)
    return inc


def coverage_summary(coded_records, z=1.96):
    inc = theme_incidence(coded_records)
    summary = richness.summarize_incidence(inc, z=z)
    # Units with no codes still count as sampling units.
    summary["T"] = len(coded_records)
    t = summary["T"]
    q1, q2, u = summary["Q1"], summary["Q2"], summary["U"]
    summary["coverage"] = richness.coverage(t, q1, q2, u)
    summary["chao2"] = richness.chao2(summary["S_obs"], t, q1, q2, z=z)
    est = summary["chao2"]["estimate"]
    summary["completeness"] = summary["S_obs"] / est if est else 1.0
    return summary


def guest_namey_chen(coded_records, base=4, run=2, threshold=0.05):
    """Guest, Namey & Chen 2020 saturation assessment.

    base: number of initial records whose unique codes form the denominator.
    run: number of subsequent records checked for new codes; runs slide by one record.
    Saturation is reached at the first run whose new codes / base codes <= threshold.
    Returns dict(base_codes, runs: [...], saturated, point) where point is 'k+r'.
    """
    n = len(coded_records)
    if n < base + run:
        return {"base_codes": None, "runs": [], "saturated": False, "point": None,
                "note": "fewer records than base + run"}
    base_codes = set()
    for _rid, codes in coded_records[:base]:
        base_codes |= set(codes)
    if not base_codes:
        return {"base_codes": 0, "runs": [], "saturated": False, "point": None,
                "note": "base records carry no codes"}
    runs = []
    point = None
    for start in range(base, n - run + 1):
        seen = set()
        for _rid, codes in coded_records[:start]:
            seen |= set(codes)
        new = set()
        for _rid, codes in coded_records[start:start + run]:
            new |= set(codes) - seen
        ratio = len(new) / float(len(base_codes))
        runs.append({"start": start, "new_codes": sorted(new), "ratio": ratio})
        if point is None and ratio <= threshold:
            point = "%d+%d" % (start, run)
    return {"base_codes": len(base_codes), "runs": runs, "saturated": point is not None,
            "point": point, "threshold": threshold, "base": base, "run": run}
