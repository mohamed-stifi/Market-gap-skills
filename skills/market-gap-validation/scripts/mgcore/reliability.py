"""Inter-rater reliability: Krippendorff's alpha (nominal), Cohen's kappa, Landis-Koch bands,
and per-code reliability for multi-label coding.

Sources: Krippendorff, "Computing Krippendorff's Alpha-Reliability" (worked examples .095,
.692, .743); Krippendorff 2004 thresholds (.800 / .667); O'Connor & Joffe 2020 (per-code
reliability for multi-label codes, minimum positives); Landis & Koch 1977 bands.
"""


def krippendorff_alpha_nominal(units):
    """units: iterable of lists of values (one per coder; None = missing).

    Returns alpha or None when undefined (fewer than 2 pairable values, or one category only).
    """
    o = {}
    for values in units:
        vals = [v for v in values if v is not None]
        m = len(vals)
        if m < 2:
            continue
        w = 1.0 / (m - 1)
        for i in range(m):
            for j in range(m):
                if i != j:
                    key = (vals[i], vals[j])
                    o[key] = o.get(key, 0.0) + w
    if not o:
        return None
    n_c = {}
    for (c, _k), v in o.items():
        n_c[c] = n_c.get(c, 0.0) + v
    n = sum(n_c.values())
    if n <= 1:
        return None
    diag = sum(v for (c, k), v in o.items() if c == k)
    expected = sum(x * (x - 1) for x in n_c.values())
    denom = n * (n - 1) - expected
    if denom == 0:
        return None
    return ((n - 1) * diag - expected) / denom


def cohen_kappa(labels_a, labels_b):
    """Cohen's kappa for two coders over the same units. Returns None when p_e == 1."""
    pairs = [(a, b) for a, b in zip(labels_a, labels_b) if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for a, b in pairs if a == b) / float(n)
    cats = set(a for a, _ in pairs) | set(b for _, b in pairs)
    pe = 0.0
    for c in cats:
        pa = sum(1 for a, _ in pairs if a == c) / float(n)
        pb = sum(1 for _, b in pairs if b == c) / float(n)
        pe += pa * pb
    if pe >= 1.0:
        return None
    return (po - pe) / (1.0 - pe)


def landis_koch(kappa):
    if kappa is None:
        return "undefined"
    if kappa < 0:
        return "poor"
    if kappa <= 0.20:
        return "slight"
    if kappa <= 0.40:
        return "fair"
    if kappa <= 0.60:
        return "moderate"
    if kappa <= 0.80:
        return "substantial"
    return "almost perfect"


def classify_alpha(alpha, accept=0.8, provisional=0.667):
    if alpha is None:
        return "not-assessable"
    if alpha >= accept:
        return "accept"
    if alpha >= provisional:
        return "provisional"
    return "revise"


def per_code_reliability(codes_a, codes_b, min_positives=5, accept=0.8, provisional=0.667):
    """Per-code binary reliability for multi-label coding.

    codes_a, codes_b: dict unit_id -> set of codes, for the double-coded units.
    Returns dict(units, codes: {code: {...}}, verdict, weak_codes).
    """
    shared = sorted(set(codes_a) & set(codes_b))
    all_codes = set()
    for u in shared:
        all_codes |= set(codes_a[u]) | set(codes_b[u])
    result = {}
    for code in sorted(all_codes):
        a = [code in codes_a[u] for u in shared]
        b = [code in codes_b[u] for u in shared]
        positives = sum(1 for x, y in zip(a, b) if x or y)
        alpha = krippendorff_alpha_nominal([[x, y] for x, y in zip(a, b)])
        kappa = cohen_kappa(a, b)
        status = "not-assessable" if positives < min_positives else classify_alpha(alpha, accept, provisional)
        result[code] = {"positives": positives, "alpha": alpha, "kappa": kappa,
                        "landis_koch": landis_koch(kappa), "status": status,
                        "applied_by_a": sum(a), "applied_by_b": sum(b)}
    assessable = {c: r for c, r in result.items() if r["status"] != "not-assessable"}
    weak = sorted(c for c, r in assessable.items() if r["status"] == "revise")
    prov = sorted(c for c, r in assessable.items() if r["status"] == "provisional")
    if not shared or not assessable:
        verdict = "insufficient"
    elif weak:
        verdict = "revise"
    elif prov:
        verdict = "provisional"
    else:
        verdict = "accept"
    return {"units": len(shared), "codes": result, "verdict": verdict,
            "weak_codes": weak, "provisional_codes": prov,
            "not_assessable": sorted(c for c, r in result.items() if r["status"] == "not-assessable")}


def label_reliability(labels_a, labels_b, accept=0.8, provisional=0.667):
    """Reliability of a single nominal label per unit (e.g. include/exclude, strength S0-S4)."""
    shared = sorted(set(labels_a) & set(labels_b))
    a = [labels_a[u] for u in shared]
    b = [labels_b[u] for u in shared]
    alpha = krippendorff_alpha_nominal([[x, y] for x, y in zip(a, b)])
    kappa = cohen_kappa(a, b)
    agree = sum(1 for x, y in zip(a, b) if x == y)
    return {"units": len(shared), "alpha": alpha, "kappa": kappa, "landis_koch": landis_koch(kappa),
            "percent_agreement": (agree / float(len(shared))) if shared else None,
            "status": classify_alpha(alpha, accept, provisional) if shared else "not-assessable"}
