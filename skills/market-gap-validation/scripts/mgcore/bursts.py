"""Kleinberg (2002) two-state burst detection for batched proportion series, with a
timestamp-shuffle significance test, plus a simple trend summary for absolute series.

Batched model: period t has d_t documents of which r_t mention the term.
p0 = sum(r)/sum(d); p1 = min(s * p0, 0.9999).
sigma_i(t) = -ln[ C(d_t, r_t) p_i^r_t (1 - p_i)^(d_t - r_t) ].
Moving up a state costs gamma * ln(n) (n = number of periods); moving down is free.
"""

import math


def _log_binom(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _sigma(d, r, p):
    if d == 0:
        return 0.0
    if p <= 0.0:
        return 0.0 if r == 0 else float("inf")
    if p >= 1.0:
        return 0.0 if r == d else float("inf")
    return -(_log_binom(d, r) + r * math.log(p) + (d - r) * math.log(1.0 - p))


def kleinberg(points, s=2.0, gamma=1.0):
    """points: list of (d, r). Returns dict(states, bursts:[{start,end,weight}], p0, p1)."""
    n = len(points)
    total_d = sum(d for d, _ in points)
    total_r = sum(r for _, r in points)
    if n == 0 or total_d == 0 or total_r == 0:
        return {"states": [0] * n, "bursts": [], "p0": 0.0, "p1": 0.0}
    p0 = total_r / float(total_d)
    p1 = min(s * p0, 0.9999)
    up = gamma * math.log(max(n, 2))
    cost = [[0.0, 0.0] for _ in range(n)]
    back = [[0, 0] for _ in range(n)]
    sig = [(_sigma(d, r, p0), _sigma(d, r, p1)) for d, r in points]
    cost[0][0] = sig[0][0]
    cost[0][1] = sig[0][1] + up
    for t in range(1, n):
        for j in (0, 1):
            best, arg = None, 0
            for i in (0, 1):
                trans = up if j > i else 0.0
                c = cost[t - 1][i] + trans
                if best is None or c < best:
                    best, arg = c, i
            cost[t][j] = best + sig[t][j]
            back[t][j] = arg
    state = 0 if cost[n - 1][0] <= cost[n - 1][1] else 1
    states = [0] * n
    for t in range(n - 1, -1, -1):
        states[t] = state
        state = back[t][state]
    bursts = []
    t = 0
    while t < n:
        if states[t] == 1:
            start = t
            weight = 0.0
            while t < n and states[t] == 1:
                weight += sig[t][0] - sig[t][1]
                t += 1
            bursts.append({"start": start, "end": t - 1, "weight": weight})
        else:
            t += 1
    return {"states": states, "bursts": bursts, "p0": p0, "p1": p1}


def max_weight(result):
    return max([b["weight"] for b in result["bursts"]] or [0.0])


def shuffle_test(points, rng, shuffles=200, s=2.0, gamma=1.0):
    observed = kleinberg(points, s=s, gamma=gamma)
    obs_max = max_weight(observed)
    if obs_max <= 0:
        return observed, 1.0
    exceed = 0
    pts = list(points)
    for _ in range(shuffles):
        rng.shuffle(pts)
        if max_weight(kleinberg(pts, s=s, gamma=gamma)) >= obs_max:
            exceed += 1
    return observed, (1.0 + exceed) / (1.0 + shuffles)


def trend(values):
    """Trend summary for absolute series (e.g. pageviews): last-12 vs previous-12 ratio and
    least-squares slope of log(1 + value) per period."""
    n = len(values)
    out = {"periods": n}
    if n >= 24:
        last = sum(values[-12:])
        prev = sum(values[-24:-12])
        out["yoy_ratio"] = (last / prev) if prev > 0 else None
    if n >= 3:
        xs = list(range(n))
        ys = [math.log1p(v) for v in values]
        mx = sum(xs) / float(n)
        my = sum(ys) / float(n)
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        out["log_slope_per_period"] = sxy / sxx if sxx else 0.0
    return out
