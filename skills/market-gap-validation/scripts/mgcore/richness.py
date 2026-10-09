"""Incidence-based richness and coverage estimators used as stopping rules.

Sampling units are independent searches (scout x channel family); "species" are entities
(or codes, for theme saturation). All estimates are lower bounds when searches are
correlated or some items are much harder to find than others.

Sources (see docs/research-notes.md for verification notes):
- Chao2 point estimate, variance and log-normal CI: Chao & Colwell 2017, eqs 2b, 3a-3c.
- Sample coverage for incidence data and extrapolated coverage: Chao & Jost 2012.
- Additional sampling to detect a fraction g of richness: Chao et al. 2009.
- Two-source capture-recapture with variance: Webster & Kemp 2013, eqs 23-24.
"""

import math


def frequency_counts(incidence):
    """incidence: mapping item -> iterable of unit ids. Returns {k: Q_k} and U = sum k*Q_k."""
    q = {}
    for units in incidence.values():
        k = len(set(units))
        if k > 0:
            q[k] = q.get(k, 0) + 1
    u = sum(k * n for k, n in q.items())
    return q, u


def chao2(s_obs, t, q1, q2, z=1.96):
    """Chao2 estimate with variance and log-normal 95% CI.

    Returns dict(estimate, var, se, ci_low, ci_high, note).
    """
    if t < 2 or s_obs == 0:
        return {"estimate": float(s_obs), "var": None, "se": None, "ci_low": float(s_obs),
                "ci_high": float(s_obs), "note": "fewer than 2 sampling units or nothing observed: no extrapolation"}
    a = (t - 1.0) / t
    if q1 == 0:
        return {"estimate": float(s_obs), "var": None, "se": None, "ci_low": float(s_obs),
                "ci_high": float(s_obs), "note": "Q1 = 0: no singletons, estimate equals S_obs (variance needs a bootstrap)"}
    if q2 > 0:
        est = s_obs + a * q1 * q1 / (2.0 * q2)
        r = q1 / float(q2)
        var = q2 * (0.25 * a * a * r ** 4 + a * a * r ** 3 + 0.5 * a * r * r)
        note = "bias-uncorrected Chao2 (Q2 > 0)"
    else:
        est = s_obs + a * q1 * (q1 - 1) / 2.0
        var = 0.25 * a * a * q1 * (2 * q1 - 1) ** 2 + 0.5 * a * q1 * (q1 - 1) - 0.25 * a * a * q1 ** 4 / est
        note = "Chao2 with Q2 = 0 (bias-corrected form)"
    d = est - s_obs
    if d <= 0 or var is None or var <= 0:
        lo = hi = float(est)
    else:
        r_ci = math.exp(z * math.sqrt(math.log(1.0 + var / (d * d))))
        lo = s_obs + d / r_ci
        hi = s_obs + d * r_ci
    return {"estimate": est, "var": var, "se": math.sqrt(var) if var and var > 0 else None,
            "ci_low": lo, "ci_high": hi, "note": note}


def _coverage_b(t, q1, q2):
    if q2 > 0:
        return (t - 1.0) * q1 / ((t - 1.0) * q1 + 2.0 * q2)
    if q1 <= 1:
        return 0.0
    return (t - 1.0) * (q1 - 1) / ((t - 1.0) * (q1 - 1) + 2.0)


def coverage(t, q1, q2, u):
    """Sample coverage C-hat for incidence data (Chao & Jost 2012)."""
    if u <= 0:
        return 0.0
    if q1 == 0:
        return 1.0
    return 1.0 - (q1 / float(u)) * _coverage_b(t, q1, q2)


def extrapolated_coverage(t, q1, q2, u, extra):
    """Coverage after `extra` more units: 1 - (Q1/U) * B^(extra+1)."""
    if u <= 0:
        return 0.0
    if q1 == 0:
        return 1.0
    return 1.0 - (q1 / float(u)) * _coverage_b(t, q1, q2) ** (extra + 1)


def units_for_coverage(t, q1, q2, u, target):
    """Smallest number of extra units t* with extrapolated coverage >= target.

    t* = ceil(ln((1 - C*) U / Q1) / ln B) - 1, solved from Chao & Jost 2012's
    extrapolated coverage. Returns 0 if already reached, None if not computable.
    """
    if u <= 0 or t < 2:
        return None
    if q1 == 0 or coverage(t, q1, q2, u) >= target:
        return 0
    b = _coverage_b(t, q1, q2)
    if b <= 0.0 or b >= 1.0:
        return None
    val = (1.0 - target) * u / float(q1)
    if val <= 0:
        return None
    return max(0, int(math.ceil(math.log(val) / math.log(b) - 1e-12)) - 1)


def units_for_fraction(t, q1, q2, s_obs, s_hat, g):
    """Extra units m_g needed to detect a fraction g of the estimated richness (Chao et al. 2009).

    m_g = ln[1 - (T/(T-1)) (2 Q2 / Q1^2) (g S_hat - S_obs)] / ln[1 - 2 Q2 / ((T-1) Q1 + 2 Q2)].
    Returns 0 when already reached, None when not computable (Q2 = 0 is unverified, or the
    target lies beyond what the formula can reach).
    """
    if g * s_hat <= s_obs:
        return 0.0
    if t < 2 or q1 == 0 or q2 == 0:
        return None
    x = (t / (t - 1.0)) * (2.0 * q2 / (q1 * q1)) * (g * s_hat - s_obs)
    if x >= 1.0:
        return None
    den = math.log(1.0 - 2.0 * q2 / ((t - 1.0) * q1 + 2.0 * q2))
    if den == 0:
        return None
    return math.log(1.0 - x) / den


def two_source_missing(a, b, ab):
    """Webster & Kemp 2013 eqs 23-24: estimated items missed by both of two complete searches.

    a, b: items found by each source; ab: found by both. Returns (missed, sd) or (None, None).
    """
    if ab <= 0:
        return None, None
    missed = (a - ab + 1.0) * (b - ab + 1.0) / ab
    if ab <= 1:
        return missed, None
    var = (a - ab + 1.0) * (b - ab + 1.0) * (a + 1.0) * (b + 1.0) / (ab * ab * (ab - 1.0))
    return missed, math.sqrt(var)


def chapman(n1, n2, m):
    """Chapman's bias-corrected Lincoln-Petersen estimate of total population size."""
    return (n1 + 1.0) * (n2 + 1.0) / (m + 1.0) - 1.0


def jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    return len(a & b) / float(len(a | b))


def summarize_incidence(incidence, z=1.96):
    """Full summary used by the saturation and theme-saturation commands."""
    units = set()
    for us in incidence.values():
        units.update(us)
    t = len(units)
    q, u = frequency_counts(incidence)
    s_obs = sum(q.values())
    q1, q2 = q.get(1, 0), q.get(2, 0)
    est = chao2(s_obs, t, q1, q2, z=z)
    cov = coverage(t, q1, q2, u)
    return {
        "S_obs": s_obs, "T": t, "Q1": q1, "Q2": q2, "U": u,
        "chao2": est,
        "completeness": (s_obs / est["estimate"]) if est["estimate"] else 1.0,
        "coverage": cov,
    }
