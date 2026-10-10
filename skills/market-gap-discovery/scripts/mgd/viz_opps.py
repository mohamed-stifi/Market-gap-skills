"""Opportunity charts (method cards D26-D28) and the scan run's one-page summary, drawn by viz.build.

13 options by lens and evidence tier (scan and deep runs), 14 opportunity map (structural signal against
evidence), 15 proven but poorly rated products (traction against rating), 16 platform coverage (where a proven
category is missing). Every number is read or counted from the run's files.
"""

import os

from . import opportunities as opm
from .viz import (_Frame, _Skip, _clip, _int, _legend, _money, _need, _panel_title, _patch, _place_labels, _plural, _style,
                  _tip, CHARTS, SAT_VERDICT)

TIERS = [("promising", "Promising", "good"), ("thin", "Thin evidence", "s1"), ("untested", "Not tested yet", "gray"),
         ("contradicted", "Contradicted", "critical"), ("excluded", "Excluded", "serious")]
SHORT = {"gap": "Unmet need", "clone-wedge": "Proven product + one fix", "bundle": "Merge two tools", "unbundle": "One part of a suite",
         "port": "New platform, language or segment", "down-market": "Cheaper tier", "replace": "Replacement after a change",
         "hosted-oss": "Hosted open source", "productize": "Software for paid human work"}


def _status_map(R):
    sc = ((R.json("opportunities", "scores.json") or {}).get("candidates")) or {}
    rk = R.json("opportunities", "ranking.json") or {}
    excl = set(x.get("opp_id") for x in rk.get("excluded") or [])
    res = {}
    for c in R.jsonl("opportunities", "candidates.jsonl"):
        oid = c.get("opp_id")
        if not oid:
            continue
        if oid in excl or c.get("status") == "excluded":
            res[oid] = "excluded"
        else:
            res[oid] = (sc.get(oid) or {}).get("status") or "untested"
    return res


# ---------------------------------------------------------------- 13 options by lens
def chart_options(R, T, m):
    cands = [c for c in R.jsonl("opportunities", "candidates.jsonl") if c.get("opp_id") and c.get("lens")]
    _need(cands, "opportunities/candidates.jsonl is missing (run `gapscan.py opportunities scan RUN`)")
    st = _status_map(R)
    counts = {}
    for c in cands:
        counts.setdefault(c["lens"], {}).setdefault(st.get(c["opp_id"], "untested"), 0)
        counts[c["lens"]][st.get(c["opp_id"], "untested")] += 1
    lenses = sorted(counts, key=lambda k: (-sum(counts[k].values()), k))
    tested = sum(1 for v in st.values() if v not in ("untested", "excluded"))
    F = _Frame(m, T, "%s options from %s kinds of opportunity" % (_int(len(cands)), len(lenses)),
               "Each bar is one lens (kind of opportunity); its segments show how far the evidence got: promising, thin, not "
               "tested yet, contradicted, or excluded by red flags, gates or the protocol. %s were tested with evidence." % _int(tested),
               ["opportunities/candidates.jsonl", "opportunities/scores.json", "opportunities/ranking.json"],
               body=max(2.2, 0.9 + 0.36 * len(lenses)))
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid=None)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])
    for y, lens in enumerate(lenses):
        left = 0
        for key, _lab, tone in TIERS:
            n = counts[lens].get(key, 0)
            if n:
                ax.barh(y, n, left=left, height=0.62, color=T[tone], edgecolor=T["surface"], linewidth=1.2)
                if n >= 2:
                    ax.text(left + n / 2.0, y, str(n), ha="center", va="center", fontsize=8.8,
                            color="#ffffff" if tone in ("good", "s1", "critical") else T["ink"])
                left += n
        _tip(ax, T, left, y, _int(left), fs=9.4, weight="bold")
    ax.set_yticks(range(len(lenses)))
    ax.set_yticklabels([SHORT.get(k, k) for k in lenses], fontsize=9.6, color=T["ink"])
    ax.set_ylim(len(lenses) - 0.5, -0.9)
    ax.set_xlim(0, max(sum(v.values()) for v in counts.values()) * 1.12)
    _legend(ax, T, [_patch(m, T[t], lab) for _k, lab, t in TIERS], ncol=5)
    rows = [[SHORT.get(k, k), k, sum(counts[k].values())] + [counts[k].get(t, 0) for t, _l, _c in TIERS] for k in lenses]
    return {"frame": F, "table": (["Lens", "Key", "Options"] + [lab for _k, lab, _t in TIERS], rows)}


# ---------------------------------------------------------------- 14 opportunity map
def chart_map(R, T, m):
    rk = R.json("opportunities", "ranking.json") or {}
    rows = [x for x in (rk.get("ranked") or []) if x.get("opp_id")]
    _need(rows, "opportunities/ranking.json is missing or ranks nothing (run `gapscan.py opportunities rank RUN`)")
    st = _status_map(R)
    tone = dict((k, t) for k, _l, t in TIERS)
    F = _Frame(m, T, "Opportunity map: structural signal against evidence",
               "Each dot is one option. Right = stronger signals in the market map (traction, prices, platforms, catalysts); "
               "up = more verified evidence (distinct authors, weighted by evidence strength). The best options sit top right; "
               "the top 10 by rank are labelled.",
               ["opportunities/ranking.json", "opportunities/scores.json"], body=4.6,
               notes=["Structural signal is the lens rule's prior (0-1); unknown parts count as 0.5. Evidence score is 1.0 at %s "
                      "strength-weighted authors." % R.c.get("scan.evidence_full")])
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid="both")
    xs = [x.get("prior") or 0 for x in rows]
    ys = [x.get("evidence_score") or 0 for x in rows]
    for x, y, r in zip(xs, ys, rows):
        ax.scatter([x], [y], s=46, color=T[tone.get(st.get(r["opp_id"], "untested"), "gray")], edgecolors=T["surface"], linewidths=1, zorder=3)
    ax.set_xlim(-0.03, 1.05)
    ax.set_ylim(-0.05, 1.08)
    ax.set_xlabel("Structural signal (lens prior, 0-1)", fontsize=10, color=T["ink2"])
    ax.set_ylabel("Evidence score (0-1)", fontsize=10, color=T["ink2"])
    _legend(ax, T, [_patch(m, T[t], lab) for k, lab, t in TIERS if k != "excluded"], ncol=4)
    F.layout()
    items = [{"x": x.get("prior") or 0, "y": x.get("evidence_score") or 0, "r_px": 5, "priority": -x.get("rank", 99),
              "text": "%s %s" % (x["opp_id"], SHORT.get(x["lens"], x["lens"]).lower())} for x in rows[:10]]
    _place_labels(F.fig, ax, items, T, fs=8.4)
    table = [[x.get("rank"), x["opp_id"], SHORT.get(x["lens"], x["lens"]), _clip(x.get("title"), 70), x.get("prior"), x.get("evidence_score"),
              x.get("status"), x.get("redflag") or "-"] for x in rows]
    return {"frame": F, "table": (["Rank", "Option", "Kind", "Title", "Structural", "Evidence", "Tier", "Red flag"], table)}


# ---------------------------------------------------------------- 15 proven but poorly rated
def chart_proven(R, T, m):
    try:
        x = opm.Ctx(R.run)
    except Exception as exc:  # a partial run: the context needs the landscape files
        raise _Skip("the landscape files are incomplete (%s)" % _clip(exc, 80))
    pts = [(e, x.tpct[e], (x.trac.get(e) or {}).get("rating_avg"), (x.trac.get(e) or {}).get("source"))
           for e in x.tpct if (x.trac.get(e) or {}).get("rating_avg") is not None
           and ((x.trac.get(e) or {}).get("ratings_count") or 0) >= x.c.get("opportunity.min_ratings_for_rating")]
    _need(len(pts) >= 5, "fewer than 5 products have both traction and a rating (landscape/traction.jsonl)")
    q = x.c.get("opportunity.traction_quantile")
    low = x.c.get("opportunity.low_rating_quantile")
    # Ring the chart's message only: proven products in the bottom third of their store's ratings.
    base = set(e for e in x.tpct if x.tpct[e] >= q and x.rpct.get(e) is not None and x.rpct[e] <= low)
    stores = {"wp": ("WordPress.org", "s1"), "apple": ("App Store", "s2"), "atl": ("Atlassian", "s3")}
    F = _Frame(m, T, "Proven but poorly rated: where a better version could win",
               "Each dot is one marketplace product. Right = more installs or ratings than others in its store (percentile); "
               "down = lower average rating. Products right of the line are proven; ringed ones are also in the bottom third "
               "of their store's ratings, the raw material of 'proven product + one fix' options.",
               ["landscape/traction.jsonl", "opportunities/candidates.jsonl"], body=4.4,
               notes=["Percentiles are within each store, so WordPress installs and App Store rating counts are comparable. "
                      "Ratings from fewer than %s reviews are left out." % x.c.get("opportunity.min_ratings_for_rating")])
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid="both")
    ax.axvspan(q, 1.02, color=T["s1"], alpha=0.06, lw=0)
    ax.axvline(q, color=T["ink2"], lw=1, ls="--")
    ax.annotate("proven (top third)", (q, 5.02), xytext=(4, 0), textcoords="offset points", fontsize=8.8, color=T["ink2"], va="bottom")
    for src, (lab, col) in stores.items():
        sel = [p_ for p_ in pts if p_[3] == src]
        if sel:
            ax.scatter([p_[1] for p_ in sel], [p_[2] for p_ in sel], s=30, color=T[col], alpha=0.8, edgecolors=T["surface"], linewidths=0.8, zorder=3, label=lab)
    other = [p_ for p_ in pts if p_[3] not in stores]
    if other:
        ax.scatter([p_[1] for p_ in other], [p_[2] for p_ in other], s=30, color=T["gray"], alpha=0.8, zorder=3, label="Other")
    ringed = [p_ for p_ in pts if p_[0] in base]
    if ringed:
        ax.scatter([p_[1] for p_ in ringed], [p_[2] for p_ in ringed], s=150, facecolors="none", edgecolors=T["ink"], linewidths=1.3, zorder=4)
    ax.set_xlim(-0.02, 1.04)
    ax.set_ylim(max(0.8, min(p_[2] for p_ in pts) - 0.3), 5.2)
    ax.set_xlabel("Traction percentile within its store", fontsize=10, color=T["ink2"])
    ax.set_ylabel("Average rating (stars)", fontsize=10, color=T["ink2"])
    handles = [_patch(m, T[col], lab) for src, (lab, col) in stores.items() if any(p_[3] == src for p_ in pts)]
    _legend(ax, T, handles, ncol=4)
    F.layout()
    if ringed:
        _place_labels(F.fig, ax, [{"x": p_[1], "y": p_[2], "r_px": 9, "text": _clip(x.names.get(p_[0], p_[0]), 28)} for p_ in ringed[:12]], T, fs=8.4)
    rows = [[x.names.get(e, e), src, round(t, 2), r, "yes" if e in base else ""] for e, t, r, src in sorted(pts, key=lambda p_: (-p_[1], p_[2]))]
    return {"frame": F, "table": (["Product", "Store", "Traction pct", "Rating", "Proven, poorly rated"], rows)}


# ---------------------------------------------------------------- 16 platform coverage
def chart_coverage(R, T, m):
    try:
        x = opm.Ctx(R.run)
    except Exception as exc:
        raise _Skip("the landscape files are incomplete (%s)" % _clip(exc, 80))
    _need(x.attrs, "landscape/entity-attributes.jsonl is missing or empty")
    plat = {}
    for a in x.attrs.values():
        for v in a.get("platform") or []:
            plat[v] = plat.get(v, 0) + 1
    ports = set()
    for c in R.jsonl("opportunities", "candidates.jsonl"):
        tw = c.get("twist") or {}
        if c.get("lens") == "port" and tw.get("dimension") == "platform":
            ports.add((c.get("category"), tw.get("to")))
    targets = sorted(set(t for _c, t in ports))
    plats = [k for k, _n in sorted(plat.items(), key=lambda kv: (-kv[1], kv[0])) if k not in ("unknown", "other") and k not in targets]
    plats = plats[: max(3, 9 - len(targets))] + targets  # port targets always get a column, empty or not
    cats = sorted(x.by_cat, key=lambda k: (-len(x.by_cat[k]), k))[:14]
    for c_, _t in sorted(ports):
        if c_ in x.by_cat and c_ not in cats:
            cats.append(c_)
    _need(len(plats) >= 2 and cats, "fewer than two platforms in the mapped attributes")
    grid = [[sum(1 for e in x.by_cat[cat] if p_ in (x.attrs[e].get("platform") or [])) for p_ in plats] for cat in cats]
    top = max(max(r) for r in grid) or 1
    F = _Frame(m, T, "Where proven categories are missing a platform",
               "Rows are categories, columns are platforms; each cell counts the mapped products. Empty cells next to full "
               "ones are candidate ports; outlined cells are the ones the scan turned into options.",
               ["landscape/entity-attributes.jsonl", "opportunities/candidates.jsonl"], body=max(2.6, 0.9 + 0.34 * len(cats)))
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid=None)
    for s in ax.spines.values():
        s.set_visible(False)
    cmap = m.mpl.colors.LinearSegmentedColormap.from_list("ramp", [T["wash"]] + T["ramp"])
    ax.imshow([[v / float(top) for v in r] for r in grid], cmap=cmap, aspect="auto", vmin=0, vmax=1)
    for i, r in enumerate(grid):
        for j, v in enumerate(r):
            ax.text(j, i, str(v) if v else "", ha="center", va="center", fontsize=8.8,
                    color="#ffffff" if v / float(top) > 0.45 else T["ink"])
            if (cats[i], plats[j]) in ports:
                ax.add_patch(m.patches.Rectangle((j - 0.48, i - 0.48), 0.96, 0.96, fill=False, edgecolor=T["s2"], lw=2))
    ax.set_xticks(range(len(plats)))
    ax.set_xticklabels([x.label("platform", p_) for p_ in plats], fontsize=9, color=T["ink"], rotation=20, ha="right")
    ax.set_yticks(range(len(cats)))
    ax.set_yticklabels(["%s (%d)" % (x.label("category", c), len(x.by_cat[c])) for c in cats], fontsize=9.2, color=T["ink"])
    rows = [[x.label("category", cats[i])] + grid[i] for i in range(len(cats))]
    return {"frame": F, "table": (["Category"] + [x.label("platform", p_) for p_ in plats], rows)}


OPP_CHARTS = [("13", "opportunity-options", "Options by kind and evidence", chart_options),
              ("14", "opportunity-map", "Opportunity map", chart_map),
              ("15", "proven-products", "Proven but poorly rated products", chart_proven),
              ("16", "platform-coverage", "Platform coverage", chart_coverage)]


def charts_for(R):
    """Chart list and dashboard sections for this run's depth."""
    if (R.protocol.get("depth") or "deep") == "scan":
        keep = dict((c[0], c) for c in CHARTS)
        charts = [keep[k] for k in ("01", "03", "05", "10", "12")] + OPP_CHARTS
        sections = [("The options", ["13", "14"]), ("Proof of demand and openings", ["15", "16", "10"]),
                    ("The evidence", ["05"]), ("How thorough was the search", ["01", "03", "12"])]
        return charts, sections
    return list(CHARTS) + OPP_CHARTS[:1], None


# ---------------------------------------------------------------- scan summary
def summary_scan(R):
    pr = R.protocol
    title = pr.get("title") or pr.get("topic") or os.path.basename(os.path.abspath(R.run))
    S = {"title": title, "question": pr.get("question") or pr.get("topic") or "", "tiles": [], "sections": [], "detail": "output/opportunities.md"}
    doc = R.json("output", "opportunities.json") or {}
    cn = doc.get("counts") or {}
    items = doc.get("opportunities") or []
    st = R.json("state.json") or {}
    if cn:
        S["tiles"].append(("Options generated", _int(cn.get("candidates", 0)), None))
        S["tiles"].append(("Tested with evidence", _int(cn.get("tested", 0)), None))
        S["tiles"].append(("Promising", _int(cn.get("promising", 0)), "good" if cn.get("promising") else "warning"))
    ver = R.verified()
    if ver:
        S["tiles"].append(("Verified quotes", _int(len(ver)), None))
    iv = ((R.json("output", "prisma.json") or {}).get("landscape") or {}).get("included_verified")
    if iv is not None:
        S["tiles"].append(("Products mapped", _int(iv), None))
    used = (st.get("budget") or {}).get("subagents_used")
    if used is not None:
        S["tiles"].append(("Subagents used", _int(used), None))
    lines = []
    if not items:
        lines.append("No ranked options yet (output/opportunities.json is missing): run `gapscan.py opportunities report RUN`.")
    for it in items[:5]:
        ev = it.get("evidence") or {}
        am = it.get("ambition") or {}
        rf = (it.get("redflag") or {}).get("verdict")
        bits = ["**#%s %s: %s** (%s)." % (it.get("rank"), it.get("opp_id"), it.get("title"), (it.get("lens_label") or "").lower())]
        bits.append("Evidence: %s, %s from %s on %s." % (it.get("status"), _plural(ev.get("support", 0), "supporting record"),
                                                         _plural(ev.get("authors", 0), "author"), _plural(ev.get("domains", 0), "website")))
        if rf:
            bits.append("Red-flag check: %s." % rf)
        if am.get("customers_needed"):
            bits.append("%s paying customers at %s/month reach %s/month." % (_int(am["customers_needed"]), _money(am["price_ref_month"], "$"),
                                                                            _money(am["target_mrr"], "$")))
        lines.append(" ".join(bits))
    S["sections"].append(("Best options", lines))
    nxt = [it for it in items if it.get("next_run")]
    if nxt:
        S["sections"].append(("Next step", ["Pick one and run the full method on it as a narrow question: `%s`" % nxt[0]["next_run"]["command"]]
                              + ["Also drafted: %s (%s)." % (it["opp_id"], it["next_run"]["protocol"]) for it in nxt[1:]]))
    cav = list(doc.get("limitations") or [])
    sat = R.json("landscape", "saturation.json") or {}
    if sat.get("verdict") and not any("saturation" in x for x in cav):
        cav.append("Landscape search: %s." % SAT_VERDICT.get(sat["verdict"], (sat["verdict"], ""))[0].lower())
    if cav:
        S["sections"].append(("Caveats", cav))
    return S
