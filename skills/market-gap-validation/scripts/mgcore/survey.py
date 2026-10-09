"""Survey analytics for validation: ODI opportunity scores, Kano categories with Better/Worse
coefficients, Van Westendorp Price Sensitivity Meter with the Newton-Miller-Smith extension,
and the Sean Ellis product-market-fit share.

Sources: Ulwick / Strategyn (top-two-box importance and satisfaction /10;
Opp = I + max(I - S, 0); test I=7.4, S=2.8 -> 12.0); Kano evaluation table and Berger et al.
1993 coefficients; Van Westendorp definitions as documented in the R package
pricesensitivitymeter (PMC = too cheap x not cheap, PME = too expensive x not expensive);
Newton, Miller & Smith 1993 calibration; Ellis / Vohra PMF survey.
"""

from . import stats


# ---------------------------------------------------------------- ODI
def odi_scores(rows, top_two=(4, 5), underserved=10.0, high=12.0, extreme=15.0, z=1.96):
    """rows: iterable of dicts with outcome, importance (1-5), satisfaction (1-5)."""
    by = {}
    for r in rows:
        by.setdefault(r["outcome"], []).append((int(r["importance"]), int(r["satisfaction"])))
    out = []
    for outcome, vals in sorted(by.items()):
        n = len(vals)
        ki = sum(1 for i, _ in vals if i in top_two)
        ks = sum(1 for _, s in vals if s in top_two)
        imp = 10.0 * ki / n
        sat = 10.0 * ks / n
        opp = imp + max(imp - sat, 0.0)
        if sat > imp:
            label = "overserved"
        elif opp > extreme:
            label = "extreme"
        elif opp > high:
            label = "high"
        elif opp >= underserved:
            label = "underserved"
        else:
            label = "appropriately served"
        il, ih, _ = stats.wilson(ki, n, z)
        sl, sh, _ = stats.wilson(ks, n, z)
        out.append({"outcome": outcome, "n": n, "importance": imp, "satisfaction": sat,
                    "opportunity": opp, "label": label,
                    "importance_ci": [10 * il, 10 * ih], "satisfaction_ci": [10 * sl, 10 * sh]})
    out.sort(key=lambda r: -r["opportunity"])
    return out


def odi_opportunity(importance, satisfaction):
    return importance + max(importance - satisfaction, 0.0)


# ---------------------------------------------------------------- Kano
_KANO_ANSWERS = {"l": "L", "like": "L", "1": "L",
                 "m": "M", "must-be": "M", "expect": "M", "2": "M",
                 "n": "N", "neutral": "N", "3": "N",
                 "w": "W", "live-with": "W", "tolerate": "W", "4": "W",
                 "d": "D", "dislike": "D", "5": "D"}

_KANO_TABLE = {
    "L": {"L": "Q", "M": "A", "N": "A", "W": "A", "D": "O"},
    "M": {"L": "R", "M": "I", "N": "I", "W": "I", "D": "M"},
    "N": {"L": "R", "M": "I", "N": "I", "W": "I", "D": "M"},
    "W": {"L": "R", "M": "I", "N": "I", "W": "I", "D": "M"},
    "D": {"L": "R", "M": "R", "N": "R", "W": "R", "D": "Q"},
}


def kano_answer(value):
    key = str(value).strip().lower()
    if key not in _KANO_ANSWERS:
        raise ValueError("unknown Kano answer: %r" % (value,))
    return _KANO_ANSWERS[key]


def kano_category(functional, dysfunctional):
    return _KANO_TABLE[kano_answer(functional)][kano_answer(dysfunctional)]


def kano_features(rows, tie_order=("M", "O", "A", "I", "R", "Q")):
    """rows: dicts with feature, functional, dysfunctional. Returns per-feature results."""
    by = {}
    for r in rows:
        cat = kano_category(r["functional"], r["dysfunctional"])
        by.setdefault(r["feature"], {k: 0 for k in "AOMIRQ"})[cat] += 1
    out = []
    for feature, counts in sorted(by.items()):
        top = max(counts.values())
        winners = [c for c in tie_order if counts[c] == top]
        cat = winners[0]
        base = counts["A"] + counts["O"] + counts["M"] + counts["I"]
        better = (counts["A"] + counts["O"]) / float(base) if base else None
        worse = -(counts["O"] + counts["M"]) / float(base) if base else None
        out.append({"feature": feature, "n": sum(counts.values()), "counts": counts,
                    "category": cat, "tied": len(winners) > 1, "better": better, "worse": worse})
    return out


# ---------------------------------------------------------------- Van Westendorp
def _crossing(prices, f, g):
    """First price where f - g changes sign from positive to non-positive (linear interp)."""
    prev = None
    for i, p in enumerate(prices):
        diff = f[i] - g[i]
        if prev is not None:
            p0, d0 = prev
            if d0 > 0 and diff <= 0:
                if d0 == diff:
                    return p
                return p0 + (p - p0) * d0 / (d0 - diff)
        if diff == 0 and prev is None:
            return p
        prev = (p, diff)
    return None


def van_westendorp(rows, nms=None):
    """rows: dicts with too_cheap, cheap, expensive, too_expensive (numbers), optional
    likely_cheap, likely_expensive (1-5). nms: calibration dict {'5': .7, ...} to enable NMS.
    """
    valid, dropped = [], 0
    for r in rows:
        tc, c, e, te = (float(r["too_cheap"]), float(r["cheap"]), float(r["expensive"]),
                        float(r["too_expensive"]))
        if tc <= c <= e <= te:
            valid.append(dict(r, too_cheap=tc, cheap=c, expensive=e, too_expensive=te))
        else:
            dropped += 1
    n = len(valid)
    if n == 0:
        return {"n": 0, "dropped_inconsistent": dropped, "note": "no consistent respondents"}
    prices = sorted(set(v for r in valid for v in (r["too_cheap"], r["cheap"], r["expensive"], r["too_expensive"])))
    too_cheap = [sum(1 for r in valid if r["too_cheap"] >= p) / float(n) for p in prices]
    cheap = [sum(1 for r in valid if r["cheap"] >= p) / float(n) for p in prices]
    expensive = [sum(1 for r in valid if r["expensive"] <= p) / float(n) for p in prices]
    too_expensive = [sum(1 for r in valid if r["too_expensive"] <= p) / float(n) for p in prices]
    not_cheap = [1.0 - x for x in cheap]
    not_expensive = [1.0 - x for x in expensive]
    out = {
        "n": n, "dropped_inconsistent": dropped,
        "opp": _crossing(prices, too_cheap, too_expensive),
        "ipp": _crossing(prices, cheap, expensive),
        "pmc": _crossing(prices, too_cheap, not_cheap),
        "pme": _crossing(prices, not_expensive, too_expensive),
        "convention": "PMC = too cheap x not cheap; PME = too expensive x not expensive",
    }
    out["acceptable_range"] = [out["pmc"], out["pme"]]
    def _has(r, k):
        return str(r.get(k, "")).strip() not in ("", "None")
    if nms is not None and all(_has(r, "likely_cheap") and _has(r, "likely_expensive") for r in valid):
        out.update(_nms(valid, prices, nms))
    return out


def _interp(x, x0, y0, x1, y1):
    if x1 == x0:
        return max(y0, y1)
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _trial_at(r, p, nms):
    pc = nms[str(int(r["likely_cheap"]))]
    pe = nms[str(int(r["likely_expensive"]))]
    tc, c, e, te = r["too_cheap"], r["cheap"], r["expensive"], r["too_expensive"]
    if p < tc or p > te:
        return 0.0
    if p <= c:
        return _interp(p, tc, 0.0, c, pc)
    if p <= e:
        return _interp(p, c, pc, e, pe)
    return _interp(p, e, pe, te, 0.0)


def _nms(valid, prices, nms):
    curve = []
    for p in prices:
        trial = sum(_trial_at(r, p, nms) for r in valid) / float(len(valid))
        curve.append({"price": p, "trial": trial, "revenue_index": p * trial})
    best_trial = max(curve, key=lambda x: (x["trial"], -x["price"]))
    best_rev = max(curve, key=lambda x: (x["revenue_index"], -x["price"]))
    return {"nms_curve": curve, "nms_trial_optimum": best_trial["price"],
            "nms_revenue_optimum": best_rev["price"]}


# ---------------------------------------------------------------- Sean Ellis PMF
def ellis(answers, threshold=0.4, z=1.96, min_n=40):
    norm = [str(a).strip().lower() for a in answers]
    na = sum(1 for a in norm if a in ("na", "n/a", "no longer use", "not applicable"))
    very = sum(1 for a in norm if a.startswith("very"))
    n = len(norm) - na
    decision = stats.wilson_decision(very, n, threshold, None, z=z, min_n=min_n)
    decision["very_disappointed_share"] = (very / float(n)) if n else None
    decision["excluded_na"] = na
    return decision
