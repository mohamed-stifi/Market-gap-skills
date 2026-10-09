"""Co-occurrence analysis with van Eck & Waltman (2009) association strength.

AS_ij = c_ij / (c_i * c_j), with c_i = sum_{j != i} c_ij (total co-occurrences of i).
Multiplying by 2m (m = 1/2 sum_i c_i) gives observed / expected co-occurrence under
independence, so ratio > 1 means the pair co-occurs more than chance.
"""

from itertools import combinations


def cooccurrence(records, keep=None):
    """records: iterable of code collections. keep: optional predicate on codes."""
    c = {}
    for codes in records:
        cs = sorted(set(x for x in codes if keep is None or keep(x)))
        for a, b in combinations(cs, 2):
            c[(a, b)] = c.get((a, b), 0) + 1
    return c


def association_strength(pairs, min_count=3, between=None):
    """pairs: {(a, b): c_ab} with a < b. between: optional (predA, predB) to keep only
    cross-group pairs (e.g. segment x pain). Returns list sorted by ratio desc."""
    totals = {}
    for (a, b), v in pairs.items():
        totals[a] = totals.get(a, 0) + v
        totals[b] = totals.get(b, 0) + v
    m = sum(totals.values()) / 2.0
    out = []
    for (a, b), v in pairs.items():
        if v < min_count:
            continue
        if between is not None:
            pa, pb = between
            if not ((pa(a) and pb(b)) or (pa(b) and pb(a))):
                continue
        as_ab = v / float(totals[a] * totals[b])
        out.append({"a": a, "b": b, "count": v, "association_strength": as_ab,
                    "observed_over_expected": 2.0 * m * as_ab})
    out.sort(key=lambda r: (-r["observed_over_expected"], -r["count"], r["a"], r["b"]))
    return out
