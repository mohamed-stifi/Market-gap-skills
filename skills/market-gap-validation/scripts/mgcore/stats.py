"""General statistics: Wilson interval and decision rule, sample size, hypergeometric
stopping test, Dirichlet sampling, rank-biased overlap.

Sources: Wilson 1927 (formula as in the market-methods track, test 20/100 -> 13.3-28.9%);
sample size n = z^2 p(1-p)/h^2 (Wald approximation); Callaghan & Mueller-Hansen 2020
statistical stopping criterion; Webber, Moffat & Zobel 2010 rank-biased overlap.
"""

import math
import random
from fractions import Fraction


def wilson(k, n, z=1.96):
    """Wilson score interval. Returns (low, high, p_hat); p_hat is None when n == 0."""
    if n <= 0:
        return 0.0, 1.0, None
    if k < 0 or k > n:
        raise ValueError("successes must be between 0 and n (got k=%s, n=%s)" % (k, n))
    p = k / float(n)
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half), p


def wilson_decision(k, n, success, kill=None, z=1.96, min_n=1):
    """Pre-registered decision rule.

    PASS if the lower bound >= success threshold; FAIL if the upper bound < kill threshold
    (kill defaults to the success threshold); otherwise INCONCLUSIVE. Samples below min_n are
    INCONCLUSIVE regardless of the observed rate.
    """
    kill = success if kill is None else kill
    low, high, p = wilson(k, n, z)
    out = {"k": k, "n": n, "p_hat": p, "ci_low": low, "ci_high": high,
           "success_threshold": success, "kill_threshold": kill, "min_n": min_n}
    if n < min_n:
        out["result"] = "INCONCLUSIVE"
        out["reason"] = "sample below pre-registered minimum"
    elif low >= success:
        out["result"] = "PASS"
        out["reason"] = "lower bound >= success threshold"
    elif high < kill:
        out["result"] = "FAIL"
        out["reason"] = "upper bound < kill threshold"
    else:
        out["result"] = "INCONCLUSIVE"
        out["reason"] = "interval straddles the thresholds"
    return out


def sample_size(p, h, z=1.96):
    """n = ceil(z^2 p (1-p) / h^2). 10% +/- 5pp -> 139; 5% +/- 3pp -> 203."""
    if not (0 < p < 1) or h <= 0:
        raise ValueError("p must be in (0,1) and h > 0")
    return int(math.ceil(z * z * p * (1.0 - p) / (h * h) - 1e-9))


def hypergeom_cdf(k, population, successes, draws):
    """P(X <= k) for X ~ Hypergeometric(population N, successes K, draws n), exact."""
    if successes > population or draws > population or k < 0:
        return 0.0
    total = math.comb(population, draws)
    acc = 0
    lo = max(0, draws - (population - successes))
    for i in range(lo, min(k, successes, draws) + 1):
        acc += math.comb(successes, i) * math.comb(population - successes, draws - i)
    return float(Fraction(acc, total))


def callaghan_stop(unseen, sample_n, sample_k, found_ranked, recall=0.95, confidence=0.95):
    """Callaghan & Mueller-Hansen 2020 stopping test for screening a ranked pool.

    After ranked screening found `found_ranked` relevant items, `sample_n` items were drawn
    at random from the `unseen` remainder and `sample_k` were relevant. H0: recall < target.
    K_tar = floor(rho_seen / recall - found_ranked + 1); p = P(X <= k | K_tar). Stop when
    p < 1 - confidence.
    """
    rho_seen = found_ranked + sample_k
    k_tar = int(math.floor(rho_seen / float(recall) - found_ranked + 1))
    k_tar = max(k_tar, sample_k + 1)
    if k_tar > unseen:
        p = 0.0
    else:
        p = hypergeom_cdf(sample_k, unseen, k_tar, sample_n)
    return {"rho_seen": rho_seen, "k_tar": k_tar, "p_value": p,
            "decision": "STOP" if p < 1.0 - confidence else "CONTINUE",
            "recall_target": recall, "confidence": confidence}


def dirichlet(alphas, rng):
    draws = [rng.gammavariate(a, 1.0) if a > 0 else 0.0 for a in alphas]
    s = sum(draws)
    return [d / s for d in draws] if s > 0 else [1.0 / len(alphas)] * len(alphas)


def make_rng(seed):
    return random.Random(seed)


def rbo(list_a, list_b, p=0.9):
    """Extrapolated rank-biased overlap for two rankings (Webber et al. 2010, eq. 32).

    Uses the common prefix depth k = min(len). Returns a value in [0, 1].
    """
    k = min(len(list_a), len(list_b))
    if k == 0:
        return 0.0
    seen_a, seen_b = set(), set()
    overlap = 0
    total = 0.0
    x_k = 0
    for d in range(1, k + 1):
        a, b = list_a[d - 1], list_b[d - 1]
        if a == b:
            overlap += 1
        else:
            if a in seen_b:
                overlap += 1
            if b in seen_a:
                overlap += 1
        seen_a.add(a)
        seen_b.add(b)
        total += (overlap / float(d)) * (p ** d)
        x_k = overlap
    return (x_k / float(k)) * (p ** k) + ((1.0 - p) / p) * total


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def quantile(values, q):
    vals = sorted(values)
    if not vals:
        return None
    pos = (len(vals) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)
