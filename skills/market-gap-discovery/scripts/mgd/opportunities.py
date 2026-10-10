"""Opportunity lenses (method card D26) and the scan funnel (D28).

A gap (unmet need, little supply) is one kind of opportunity. Most small SaaS businesses start from
another kind: a proven product with one improvement, two tools merged into one, a proven model moved to
a new platform, a cheaper tier for priced-out users, a replacement after a shutdown, a hosted version of
an open-source tool, or software for a job people pay a person to do. Each lens is a deterministic rule
over what the run already holds (landscape attributes, traction, supply, verified evidence, why-now
events), so generating many options costs no subagent; evidence is then spent only on the best ones.

Commands:
  opportunities scan RUN    candidates.jsonl from every lens in protocol.lenses (no network, no LLM)
  opportunities score RUN   evidence per candidate from the verified ledger -> scores.json
  opportunities rank RUN    tiers, red flags and ambition math -> ranking.json
  opportunities report RUN  output/opportunities.md + .json + next-runs/OPP-NNN.protocol.json
"""

import math
import os
import re

from mgcore import state
from mgcore.jsonio import now_iso, read_json, read_jsonl, today, write_json, write_jsonl

from . import traction as traction_mod
from .common import (CliError, alias_map, cfg, entities, included_verified, out, p, protocol, require_run, resolve_ids,
                     load_state, save_state, validate)

LENSES = ["gap", "clone-wedge", "bundle", "unbundle", "port", "down-market", "replace", "hosted-oss", "productize"]
LENS_LABEL = {
    "gap": "Unmet need (gap)",
    "clone-wedge": "Proven product + one improvement",
    "bundle": "Two tools merged into one",
    "unbundle": "One part of a suite, done simply",
    "port": "Proven model on a new platform, language or segment",
    "down-market": "Cheaper, simpler tier for priced-out users",
    "replace": "Replacement after a shutdown, price rise or platform change",
    "hosted-oss": "Hosted version of an open-source tool",
    "productize": "Software for a job people pay a person to do",
}
SUPPORT = ("pain", "wish", "switch", "workaround", "wtp")
COUNTER = ("praise", "contra")

# Wedge dimensions: what users complain about in proven products. Coded X- codes win when the run has
# them (deep runs); otherwise a transparent keyword rule tags the quote (scan runs have no codebook).
X_TO_WEDGE = {"X-PRICE": "price", "X-COMPLEX": "simplicity", "X-RELIAB": "reliability", "X-SUPPORT": "support",
              "X-LANG": "language", "X-INTEG": "integration", "X-SCALE": "limits", "X-FRAG": "fragmentation"}
WEDGE_RX = [
    ("price", r"expensive|overpriced|pric(e|ey|ing)|cost(s|ly)?\b|afford|too much (money|per)|\$\d"),
    ("simplicity", r"complicated|complex|bloated|confusing|overkill|learning curve|hard to (use|set ?up)|clunky|too many (features|options|settings)"),
    ("reliability", r"\bbug|crash|broken|unreliable|stopped working|doesn'?t work|not working|outage|down again|\bslow\b|laggy"),
    ("support", r"(no|slow|poor|bad|terrible) (support|response|customer service)|support (never|didn'?t|ignored)|no reply"),
    ("language", r"translat|locali[sz]|in (french|german|spanish|arabic|portuguese|japanese)|my language|multilingual"),
    ("integration", r"integrat|doesn'?t (sync|connect)|no api|webhook|zapier|export|import"),
    ("limits", r"\blimit(s|ed)?\b|\bcap(ped)?\b|quota|paywall|upgrade to (use|get)|free plan only"),
    ("privacy", r"privacy|gdpr|cookie banner|tracking my|data (sold|sharing)"),
    ("fragmentation", r"juggl|separate tools|(two|three|several|multiple) (different )?(tools|apps|services)|switch(ing)? between|stitch"),
]
WEDGE_ADJ = {"price": "Cheaper", "simplicity": "Simpler", "reliability": "More reliable", "support": "Better-supported",
             "language": "Localized", "integration": "Better-integrated", "limits": "Uncapped", "privacy": "Privacy-first",
             "fragmentation": "All-in-one", "unknown": "Better-rated"}
# Paying a person needs a paying or hiring verb near the person: "too expensive for a solo freelancer" is a segment,
# not a service (a unit test caught the looser rule).
SERVICE_RX = re.compile(r"\b(hire[ds]?|hiring|pay(s|ing)?|paid|outsourc\w*|contract(ed|ing)?)\b[^.!?]{0,40}?"
                        r"\b(freelancers?|contractors?|agency|agencies|virtual assistants?|assistants?|VA|consultants?|bookkeepers?|"
                        r"accountants?|developers?|someone|a person|people)\b|\b(upwork|fiverr)\b", re.I)
SHUTDOWN_RX = re.compile(r"shut(ting)? down|shutdown|sunset|discontinu|deprecat|end of life|\bEOL\b|acquired|acquisition|"
                         r"price (increase|hike)|raised (its |their )?prices|withdr[ae]w|no longer (support|available|offer)|being removed|killed off", re.I)
UNBUNDLE_RX = re.compile(r"only (need|use|want)|just (need|want|use)|overkill|bloated|too many features|don'?t need (all|most)|"
                         r"paying for (features|things) I (don'?t|never) use", re.I)
HOSTED_RX = re.compile(r"hosted (version|option|service)|managed (version|hosting|service)|cloud version|don'?t want to self.?host|"
                       r"self.?hosting is (a pain|hard|too)|pain to (host|maintain)|someone (to )?host", re.I)
REGULATED_RX = re.compile(r"\btax|\bvat\b|merchant of record|payment process|money transmi|\bkyc\b|\baml\b|medical|health|clinical|"
                          r"legal advice|financial advice|insurance|lending|\bloan|crypto|securities|payroll", re.I)
MARKETPLACE_PLATFORMS = {"ios", "android", "wordpress", "atlassian", "shopify", "chrome", "slack", "zapier", "figma", "notion"}
PLUGIN_APPROACHES = {"plugin", "marketplace-app", "mobile-companion", "native-app", "browser-extension", "third-party-client"}
LICENSE_OK = {"MIT", "APACHE-2.0", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "ISC", "MPL-2.0", "GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0",
              "UNLICENSE", "0BSD", "ZLIB"}
LICENSE_DUTY = {"AGPL-3.0"}
LICENSE_BLOCKED = {"SSPL-1.0", "BUSL-1.1", "BSL-1.1", "ELASTIC-2.0", "ELV2", "COMMONS-CLAUSE", "PROPRIETARY", "FAIR-SOURCE", "FSL-1.1"}
PRICE_CURRENCIES = ("USD", "EUR", "GBP", None)  # comparable enough to rank price floors; never converted or summed


def _author(r):
    return r["author_hash"] if r.get("author_hash") not in (None, "unknown") else "rec:" + r["id"]


def _pct(values):
    """Mid-rank percentile of each value within its list (0..1)."""
    vals = sorted(values)
    n = float(len(vals))
    res = {}
    for v in set(vals):
        below = sum(1 for x in vals if x < v)
        equal = sum(1 for x in vals if x == v)
        res[v] = (below + 0.5 * equal) / n
    return res


def _quantile(vals, q):
    vals = sorted(vals)
    if not vals:
        return None
    k = (len(vals) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 3) if xs else None


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _slug(s, n=40):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", (s or "").lower())).strip("-")[:n].strip("-")


def lenses_of(proto):
    want = proto.get("lenses") or LENSES
    return [x for x in LENSES if x in want]


def depth_of(proto):
    return proto.get("depth") or "deep"


# ---------------------------------------------------------------- context
class Ctx(object):
    """Everything the lens rules read, loaded once."""

    def __init__(self, run):
        self.run = run
        self.c = cfg(run)
        self.proto = protocol(run)
        amap = alias_map(run)
        self.prods = {e["entity_id"]: e for e in included_verified(entities(run)) if e["kind"] == "product"}
        self.names = {k: (e.get("names") or [k])[0] for k, e in self.prods.items()}
        self.urls = {k: (e.get("urls") or [None])[0] for k, e in self.prods.items()}
        self.attrs = {a["entity_id"]: a for a in read_jsonl(p(run, "landscape", "entity-attributes.jsonl"))[0] if a["entity_id"] in self.prods}
        cls = read_json(p(run, "landscape", "classification.json"), {}) or {}
        self.labels = {}
        for facet, vals in (cls.get("facets") or {}).items():
            for v in vals or []:
                self.labels[(facet, v.get("id"))] = v.get("label") or v.get("id")
        self.by_cat = {}
        for eid, a in sorted(self.attrs.items()):
            self.by_cat.setdefault(a.get("category") or "uncategorised", []).append(eid)
        # Traction percentiles within each source (installs and rating counts are not comparable across stores).
        self.trac = {k: v for k, v in traction_mod.load(run).items() if k in self.prods}
        self.tpct, self.rpct = {}, {}
        min_r = self.c.get("opportunity.min_ratings_for_rating")
        for src in sorted(set(r.get("source") for r in self.trac.values())):
            rows = {k: r for k, r in self.trac.items() if r.get("source") == src}
            for metric in ("installs", "ratings_count"):
                vals = {k: r[metric] for k, r in rows.items() if r.get(metric) is not None}
                if len(vals) >= 3:
                    pc = _pct(list(vals.values()))
                    for k, v in vals.items():
                        self.tpct[k] = max(self.tpct.get(k, 0.0), pc[v])
            rated = {k: r["rating_avg"] for k, r in rows.items() if r.get("rating_avg") is not None and (r.get("ratings_count") or 0) >= min_r}
            if len(rated) >= 3:
                pc = _pct(list(rated.values()))
                for k, v in rated.items():
                    self.rpct[k] = pc[v]
        # Prices: monthly entry price of paid plans (currencies kept apart from conversion; used to rank only).
        self.price = {}
        for eid, a in self.attrs.items():
            pr = a.get("pricing") or {}
            if pr.get("min_paid_month") and pr.get("currency") in PRICE_CURRENCIES:
                self.price[eid] = float(pr["min_paid_month"])
        led = [r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0] if (r.get("verification") or {}).get("status") == "verified"]
        self.led = {r["id"]: r for r in led}
        self.by_entity = {}
        for r in led:
            r["_eids"] = [x for x in resolve_ids(r.get("entity_ids"), amap) if x in self.prods]
            for eid in r["_eids"]:
                self.by_entity.setdefault(eid, []).append(r)
        self.codes = {}
        for r in read_jsonl(p(run, "coding", "codes-A.jsonl"))[0]:
            cur = self.codes.get(r["evidence_id"])
            if cur is None or r["codebook_version"] >= cur["codebook_version"]:
                self.codes[r["evidence_id"]] = r
        lock = read_json(p(run, "coding", "codebook.lock.json"))
        book = read_json(p(run, "coding", "codebook.v%d.json" % lock["version"]), {}) if lock else {}
        self.code_labels = {x["id"]: x.get("label") or x["id"] for x in (book or {}).get("codes", [])}
        self.supply = {s["entity_id"]: s.get("jobs_served") or [] for s in read_jsonl(p(run, "analysis", "supply.jsonl"))[0]}
        self.gapmap = read_json(p(run, "analysis", "gapmap.json"), {}) or {}
        self.whynow = read_jsonl(p(run, "evidence", "why-now.jsonl"))[0]

    def label(self, facet, value):
        return self.labels.get((facet, value)) or (value or "").replace("-", " ")

    def wedges(self, r):
        coded = self.codes.get(r["id"])
        if coded:
            dims = sorted(set(X_TO_WEDGE[x] for x in coded.get("codes") or [] if x in X_TO_WEDGE))
            if dims:
                return dims
        q = r.get("quote") or ""
        return [d for d, rx in WEDGE_RX if re.search(rx, q, re.I)]

    def segment_of(self, eids):
        counts = {}
        for e in eids:
            for s in (self.attrs.get(e) or {}).get("segments") or []:
                counts[s] = counts.get(s, 0) + 1
        if not counts:
            return None
        return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]

    def top_traction(self, eids, n=3):
        return sorted(eids, key=lambda e: (-(self.tpct.get(e) if self.tpct.get(e) is not None else -1), e))[:n]


def _cand(x, lens, key, title, category, base, prior_parts, why, needs, evidence=(), twist=None, pair=None, extra=None):
    parts = {k: (round(v, 3) if v is not None else None) for k, v in prior_parts.items()}
    return dict({"lens": lens, "key": key, "title": title[:120], "category": category,
                 "category_label": x.label("category", category) if category else None,
                 "segment": x.segment_of(base), "base_entities": list(base),
                 "base_names": [x.names.get(e, e) for e in base], "twist": twist, "pair": pair,
                 # Unknown parts count as neutral 0.5: dropping them would let the least-measured options rank first
                 # (a replay of the first live run put every language port at 1.00 that way).
                 "prior": _mean([0.5 if v is None else v for v in parts.values()]) or 0.0, "prior_parts": parts, "why": why, "needs": needs,
                 "evidence_ids": sorted(set(evidence)), "flags": [], "status": "candidate"}, **(extra or {}))


# ---------------------------------------------------------------- lens rules
def _clone_wedge(x):
    c = x.c
    q, low, min_auth = c.get("opportunity.traction_quantile"), c.get("opportunity.low_rating_quantile"), c.get("opportunity.wedge_min_authors")
    out_ = []
    for cat, eids in sorted(x.by_cat.items()):
        proven = [e for e in eids if (x.tpct.get(e) or 0) >= q]
        if not proven:
            continue
        wedge_auth, wedge_recs, weak = {}, {}, []
        for e in proven:
            recs = x.by_entity.get(e, [])
            comp = [r for r in recs if r["stance"] in SUPPORT]
            pra = [r for r in recs if r["stance"] in COUNTER]
            if (x.rpct.get(e) is not None and x.rpct[e] <= low) or (len(set(map(_author, comp))) >= 2 and len(comp) >= len(pra)):
                weak.append(e)
            for r in comp:
                for d in x.wedges(r):
                    wedge_auth.setdefault(d, set()).add(_author(r))
                    wedge_recs.setdefault(d, []).append(r["id"])
        dims = sorted((d for d, a in wedge_auth.items() if len(a) >= min_auth and d != "fragmentation"),
                      key=lambda d: (-len(wedge_auth[d]), d))[: c.get("opportunity.max_per_category")]
        if not dims and weak:
            dims = ["unknown"]
        base = x.top_traction(sorted(set(weak) | set(proven)))
        paid = [e for e in base if x.price.get(e)]
        for d in dims:
            names = ", ".join(x.names.get(e, e) for e in base[:2])
            rated = [x.rpct[e] for e in base if x.rpct.get(e) is not None]
            out_.append(_cand(x, "clone-wedge", "clone-wedge|%s|%s" % (cat, d),
                              "%s alternative to %s (%s)" % (WEDGE_ADJ.get(d, d.title()), names, x.label("category", cat)),
                              cat, base,
                              {"traction": max(x.tpct.get(e) or 0 for e in base),
                               "dissatisfaction": (1 - min(rated)) if rated else None,
                               "paid_share": (len(paid) / float(len(base))) if base else None},
                              ["%d proven product(s) in the top traction third of their store" % len(proven),
                               ("%d author(s) complain about %s" % (len(wedge_auth.get(d, ())), d)) if d != "unknown"
                               else "low ratings, but no complaint names the wedge yet"],
                              ["complaints that name the wedge, from at least 2 domains", "switch or willingness-to-pay records",
                               "a check that no product already sells this wedge"],
                              wedge_recs.get(d, []), twist={"dimension": "wedge", "from": names, "to": d}))
    return out_


LANG_NAMES = {"de": "German", "es": "Spanish", "fr": "French", "pt": "Portuguese", "pt-br": "Brazilian Portuguese", "it": "Italian",
              "ja": "Japanese", "zh": "Chinese", "ko": "Korean", "ru": "Russian", "ar": "Arabic", "nl": "Dutch", "tr": "Turkish",
              "pl": "Polish", "hi": "Hindi", "id": "Indonesian", "sv": "Swedish", "en": "English", "he": "Hebrew", "vi": "Vietnamese"}


def lang_name(code):
    return LANG_NAMES.get((code or "").lower(), code)


def _port_title(x, cat, dim, src, t):
    c = x.label("category", cat)
    if dim == "language":
        return "%s in %s (proven in %s)" % (c, lang_name(t), lang_name(src))
    if dim == "platform":
        return "%s on %s (proven on %s)" % (c, x.label("platform", t), x.label("platform", src))
    return "%s for %s (proven for %s)" % (c, x.label("segment", t).lower(), x.label("segment", src).lower())


def _port(x):
    c = x.c
    dims = x.proto.get("variation_dimensions") or {}
    min_src, max_tgt, min_size = c.get("opportunity.port_min_source"), c.get("opportunity.port_max_target"), c.get("opportunity.port_min_dimension_size")
    getters = {"platform": lambda a: a.get("platform") or [], "language": lambda a: a.get("languages") or [],
               "segment": lambda a: a.get("segments") or []}
    out_ = []
    for dim, get in getters.items():
        glob_counts = {}
        for a in x.attrs.values():
            for v in get(a):
                glob_counts[v] = glob_counts.get(v, 0) + 1
        declared = [v for v in dims.get(dim) or [] if v]
        if dim == "language":
            targets = set(declared)  # only languages the protocol names: the run cannot see unserved languages otherwise
        else:
            targets = set(declared) or set(v for v, n in glob_counts.items() if n >= min_size)
        targets -= {"unknown", "other", ""}
        biggest = float(max(glob_counts.values())) if glob_counts else 1.0
        multi = {cat: sum(1 for e in eids if len(x.attrs[e].get("languages") or []) > 1) / float(len(eids)) for cat, eids in x.by_cat.items()}
        for cat, eids in sorted(x.by_cat.items()):
            if len(eids) < min_src:
                continue
            cnt = {}
            for e in eids:
                for v in get(x.attrs[e]):
                    cnt[v] = cnt.get(v, 0) + 1
            sources = sorted((v for v, n in cnt.items() if n >= min_src and v not in ("unknown", "other")), key=lambda v: (-cnt[v], v))
            if not sources:
                continue
            opts = []
            for t in sorted(targets):
                if cnt.get(t, 0) > max_tgt or t in sources:
                    continue
                src = sources[0]
                src_eids = [e for e in eids if src in get(x.attrs[e])]
                base = x.top_traction(src_eids)
                tr = [x.tpct[e] for e in base if x.tpct.get(e) is not None]
                opts.append(_cand(x, "port", "port|%s|%s|%s" % (cat, dim, t),
                                  _port_title(x, cat, dim, src, t), cat, base,
                                  {"source_strength": min(1.0, cnt[src] / (2.0 * min_src)), "category_traction": _mean(tr),
                                   "target_size": (glob_counts.get(t, 0) / biggest) if dim != "language" else None,
                                   # Most mapped products list only their UI's main language, so "no German product" is weak
                                   # evidence unless the category's language data shows variety.
                                   "absence": (1.0 if cnt.get(t, 0) == 0 else 0.5) if (dim != "language" or multi.get(cat, 0) >= 0.2) else 0.5},
                                  ["%d products on %s %s, %d on %s" % (cnt[src], dim, src, cnt.get(t, 0), t)],
                                  ["requests for this %s from %s users" % (x.label("category", cat).lower(), t),
                                   "a check that the leader has no %s version" % t, "size of the %s market for this job" % t],
                                  twist={"dimension": dim, "from": src, "to": t}))
            opts.sort(key=lambda k: (-k["prior"], k["key"]))
            out_ += opts[: c.get("opportunity.max_per_category")]
    return out_


def _down_market(x):
    c = x.c
    out_ = []
    for cat, eids in sorted(x.by_cat.items()):
        paid = [e for e in eids if x.price.get(e)]
        if len(paid) < c.get("opportunity.down_market_min_paid"):
            continue
        # Compare with the entry prices of the other categories: a category's own prices would make a large
        # category's floor sit low in the distribution by construction.
        others = [v for e, v in x.price.items() if (x.attrs.get(e) or {}).get("category") != cat]
        if len(others) < c.get("opportunity.down_market_min_paid"):
            continue
        hi = _quantile(others, c.get("opportunity.down_market_price_quantile"))
        floor = min(x.price[e] for e in paid)
        pc = {floor: sum(1 for v in others if v <= floor) / float(len(others))}
        known = [x.attrs[e]["pricing"].get("free_tier") for e in eids if (x.attrs[e].get("pricing") or {}).get("free_tier") is not None]
        free_share = (sum(1 for v in known if v) / float(len(known))) if known else None
        if floor < hi or (free_share is not None and free_share >= c.get("opportunity.down_market_max_free_share")):
            continue
        price_recs = [r["id"] for e in eids for r in x.by_entity.get(e, []) if r["stance"] in SUPPORT and "price" in x.wedges(r)]
        base = sorted(paid, key=lambda e: (x.price[e], e))[:3]
        out_.append(_cand(x, "down-market", "down-market|%s" % cat,
                          "Low-cost %s (paid plans start at %.0f/month)" % (x.label("category", cat).lower(), floor), cat, base,
                          {"price_floor": pc.get(floor), "no_free_tier": (1 - free_share) if free_share is not None else None,
                           "paid_products": min(1.0, len(paid) / 6.0)},
                          ["cheapest paid plan %.0f/month costs more than %.0f%% of entry prices in other categories" % (floor, 100 * pc.get(floor, 0)),
                           "free tier share %s" % ("unknown" if free_share is None else "%.0f%%" % (100 * free_share))],
                          ["price complaints from small buyers", "evidence that a cheaper, smaller product is enough for them"],
                          price_recs, twist={"dimension": "price", "from": "%.0f/month" % floor, "to": "lower tier"}))
    return out_


def _bundle(x):
    c = x.c
    by_name = {}
    for eid, nm in x.names.items():
        by_name.setdefault(_norm(nm), eid)
    cat_of = {e: a.get("category") for e, a in x.attrs.items()}
    links, recs = {}, {}
    for e, a in x.attrs.items():
        for integ in a.get("integrations") or []:
            e2 = by_name.get(_norm(integ))
            if e2 and cat_of.get(e2) and cat_of[e2] != cat_of[e]:
                pair = tuple(sorted((cat_of[e], cat_of[e2])))
                links[pair] = links.get(pair, 0) + 1
    for r in x.led.values():
        cats = sorted(set(cat_of[e] for e in r.get("_eids") or [] if cat_of.get(e)))
        for i in range(len(cats)):
            for j in range(i + 1, len(cats)):
                pair = (cats[i], cats[j])
                links[pair] = links.get(pair, 0) + 1
                recs.setdefault(pair, []).append(r["id"])
        if "fragmentation" in x.wedges(r) and r["stance"] in SUPPORT and len(cats) == 1:
            recs.setdefault(("_frag", cats[0]), []).append(r["id"])
    top_job = {}
    if x.supply:
        for cat, eids in x.by_cat.items():
            cnt = {}
            for e in eids:
                for j in x.supply.get(e, []):
                    cnt[j] = cnt.get(j, 0) + 1
            if cnt:
                top_job[cat] = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    out_ = []
    for pair, n in sorted(links.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < c.get("opportunity.bundle_min_links") or pair[0] == "_frag":
            continue
        a_, b_ = pair
        joint = None
        if a_ in top_job and b_ in top_job:
            joint = sum(1 for e, js in x.supply.items() if top_job[a_] in js and top_job[b_] in js)
            if joint > c.get("opportunity.bundle_max_joint"):
                continue
        base = x.top_traction(x.by_cat.get(a_, []), 2) + x.top_traction(x.by_cat.get(b_, []), 2)
        tr = [x.tpct[e] for e in base if x.tpct.get(e) is not None]
        frag = recs.get(("_frag", a_), []) + recs.get(("_frag", b_), [])
        out_.append(_cand(x, "bundle", "bundle|%s|%s" % pair,
                          "%s + %s in one product" % (x.label("category", a_), x.label("category", b_).lower()), a_, base,
                          {"links": min(1.0, n / 6.0), "joint_absence": None if joint is None else (1.0 if joint == 0 else 0.5),
                           "traction": _mean(tr)},
                          ["%d integration links or co-mentions between the two categories" % n,
                           "joint supply %s" % ("not measured (no supply map)" if joint is None else "%d product(s) do both jobs" % joint)],
                          ["users who use both tools and want one", "a check that no product already does both well"],
                          recs.get(pair, []) + frag, pair=list(pair), twist={"dimension": "bundle", "from": a_, "to": b_}))
    return out_[: c.get("opportunity.max_per_lens")]


def _unbundle(x):
    c = x.c
    out_ = []
    if x.supply:
        for e, jobs in sorted(x.supply.items()):
            if e not in x.attrs or len(jobs) < c.get("opportunity.unbundle_min_jobs"):
                continue
            comp = [r for r in x.by_entity.get(e, []) if r["stance"] in SUPPORT and set(x.wedges(r)) & {"simplicity", "price"}]
            if (x.tpct.get(e) or 0) < c.get("opportunity.traction_quantile") and len(set(map(_author, comp))) < 2:
                continue
            best = None
            for j in jobs:
                standalone = sum(1 for o, js in x.supply.items() if o != e and j in js and len(js) <= 2)
                if standalone <= c.get("opportunity.unbundle_max_standalone") and (best is None or standalone < best[1]):
                    best = (j, standalone)
            if best:
                j, n = best
                out_.append(_cand(x, "unbundle", "unbundle|%s|%s" % (e, j),
                                  "Just the %s part of %s, done simply" % (x.code_labels.get(j, j).lower(), x.names.get(e, e)),
                                  x.attrs[e].get("category"), [e],
                                  {"suite_traction": x.tpct.get(e), "standalone_scarcity": 1.0 if n == 0 else 0.5},
                                  ["%s serves %d jobs; %d standalone product(s) do '%s'" % (x.names.get(e, e), len(jobs), n, x.code_labels.get(j, j))],
                                  ["users who need only this part", "complaints about the suite's price or complexity"],
                                  [r["id"] for r in comp], twist={"dimension": "scope", "from": "%d jobs" % len(jobs), "to": j}))
    seen = set(o["base_entities"][0] for o in out_)
    for e, recs in sorted(x.by_entity.items()):
        hits = [r for r in recs if r["stance"] in SUPPORT and UNBUNDLE_RX.search(r.get("quote") or "")]
        if e in seen or len(set(map(_author, hits))) < c.get("opportunity.evidence_led_min_authors"):
            continue
        out_.append(_cand(x, "unbundle", "unbundle|%s|simple" % e, "Simpler single-purpose version of %s" % x.names.get(e, e),
                          (x.attrs.get(e) or {}).get("category"), [e], {"suite_traction": x.tpct.get(e)},
                          ["%d author(s) say they use only part of %s" % (len(set(map(_author, hits))), x.names.get(e, e))],
                          ["which part they use", "whether a smaller product would be enough"], [r["id"] for r in hits],
                          twist={"dimension": "scope", "from": "suite", "to": "single job"}))
    return out_[: c.get("opportunity.max_per_lens")]


def _replace(x):
    c = x.c
    as_of = x.proto.get("as_of") or today()
    out_ = []
    by_name = {_norm(nm): e for e, nm in x.names.items() if len(_norm(nm)) >= 4}

    def recency(date):
        if not date:
            return None
        try:
            y, m = int(date[:4]), int(date[5:7] or 1) if len(date) >= 7 else 1
            ay, am = int(as_of[:4]), int(as_of[5:7])
        except ValueError:
            return None
        months = (ay - y) * 12 + (am - m)
        return 1.0 if months <= 12 else (0.5 if months <= 24 else 0.25)
    for w in x.whynow:
        text = "%s %s" % (w.get("change") or "", w.get("quote") or "")
        if not SHUTDOWN_RX.search(text):
            continue
        hit = [e for k, e in by_name.items() if k in _norm(text)]
        cat = (x.attrs.get(hit[0]) or {}).get("category") if hit else None
        out_.append(_cand(x, "replace", "replace|%s" % w.get("id"),
                          "Replacement after: %s" % (w.get("change") or "")[:90], cat, hit[:3],
                          {"recency": recency(w.get("date")), "affected_traction": _mean([x.tpct.get(e) for e in hit])},
                          ["catalyst %s (%s, %s)" % (w.get("id"), w.get("factor"), w.get("date"))],
                          ["users looking for an alternative because of this change", "who already captured them"],
                          [], twist={"dimension": "catalyst", "from": w.get("id"), "to": "replacement"}, extra={"why_now": [w.get("id")]}))
    for e, recs in sorted(x.by_entity.items()):
        hits = [r for r in recs if r["stance"] in ("switch", "pain", "wish") and SHUTDOWN_RX.search(r.get("quote") or "")]
        if len(set(map(_author, hits))) < c.get("opportunity.evidence_led_min_authors"):
            continue
        out_.append(_cand(x, "replace", "replace|%s" % e, "Migration target for %s users" % x.names.get(e, e),
                          (x.attrs.get(e) or {}).get("category"), [e],
                          {"recency": recency(max((r.get("posted_at") or "") for r in hits) or None), "affected_traction": x.tpct.get(e)},
                          ["%d author(s) mention %s shutting down, being acquired or raising prices" % (len(set(map(_author, hits))), x.names.get(e, e))],
                          ["how many users are leaving", "which alternatives they already chose"], [r["id"] for r in hits],
                          twist={"dimension": "catalyst", "from": e, "to": "replacement"}))
    return out_[: c.get("opportunity.max_per_lens")]


def _license_class(lic):
    s = (lic or "").strip().upper().replace(" ", "-")
    if not s:
        return "unknown"
    if s in LICENSE_BLOCKED or "SSPL" in s or "BUSL" in s or "ELASTIC" in s or "COMMONS" in s:
        return "blocked"
    if s in LICENSE_DUTY or s.startswith("AGPL"):
        return "duty"
    if s in LICENSE_OK or any(s.startswith(k) for k in ("MIT", "APACHE", "BSD", "MPL", "GPL", "LGPL")):
        return "ok"
    return "unknown"


def _hosted_oss(x):
    out_ = []
    for e, a in sorted(x.attrs.items()):
        oss = a.get("approach") in ("open-source-tool", "open-core", "self-hosted-licensed") or (a.get("pricing") or {}).get("model") == "open-source"
        if not oss and a.get("deployment") != "self-hosted":
            continue
        # Plugins and marketplace apps run inside their host (WordPress, Jira): "self-hosted" there is not a server
        # someone could host for others (a replay of the first live run proposed "Hosted WP Statistics").
        if a.get("approach") in PLUGIN_APPROACHES or set(a.get("platform") or []) & MARKETPLACE_PLATFORMS:
            continue
        lic = _license_class(a.get("license"))
        if lic == "blocked":
            continue
        asks = [r for r in x.by_entity.get(e, []) if HOSTED_RX.search(r.get("quote") or "")]
        out_.append(_cand(x, "hosted-oss", "hosted-oss|%s" % e,
                          "Hosted %s (%s%s)" % (x.names.get(e, e), x.label("category", a.get("category")).lower(),
                                                 ", " + a["license"] if a.get("license") else ", license unknown"),
                          a.get("category"), [e],
                          {"traction": x.tpct.get(e), "no_official_cloud": 1.0 if a.get("deployment") == "self-hosted" else 0.4,
                           "license": {"ok": 1.0, "duty": 0.6, "unknown": 0.5}[lic]},
                          ["%s is self-hosted or open source (deployment %s, license %s)" % (x.names.get(e, e), a.get("deployment"), a.get("license") or "unknown")],
                          ["requests for a hosted version", "the license text (hosting rights, trademark)", "whether the maintainers sell hosting"],
                          [r["id"] for r in asks], twist={"dimension": "delivery", "from": "self-hosted", "to": "hosted"},
                          extra={"license": a.get("license"), "license_class": lic}))
    out_.sort(key=lambda k: (-k["prior"], k["key"]))
    return out_[: x.c.get("opportunity.max_per_lens")]


def _productize(x):
    groups = {}
    for r in x.led.values():
        if r["stance"] not in ("workaround", "wtp", "switch", "pain") or not SERVICE_RX.search(r.get("quote") or ""):
            continue
        cats = sorted(set((x.attrs.get(e) or {}).get("category") for e in r.get("_eids") or [] if (x.attrs.get(e) or {}).get("category")))
        jobs = [k for k in (x.codes.get(r["id"]) or {}).get("codes") or [] if k.startswith("J-")]
        key = cats[0] if cats else (jobs[0] if jobs else "general")
        groups.setdefault(key, []).append(r)
    out_ = []
    for key, recs in sorted(groups.items()):
        auth = set(map(_author, recs))
        if len(auth) < x.c.get("opportunity.evidence_led_min_authors"):
            continue
        label = x.code_labels.get(key) or x.label("category", key)
        cat = key if (("category", key) in x.labels or key in x.by_cat) else None
        out_.append(_cand(x, "productize", "productize|%s" % key, "Software for the %s work people now pay someone to do" % label.lower(),
                          cat, [], {"evidence_led": min(1.0, len(auth) / 5.0)},
                          ["%d author(s) pay a person (freelancer, agency, assistant) for this" % len(auth)],
                          ["what the person does each time", "what they charge", "whether software can do it without human judgment"],
                          [r["id"] for r in recs], twist={"dimension": "delivery", "from": "paid service", "to": "software"}))
    return out_[: x.c.get("opportunity.max_per_lens")]


def _gap(x):
    out_ = []
    for j in x.gapmap.get("jobs") or []:
        if j.get("cell") not in ("absolute", "synthesis"):
            continue
        out_.append(_cand(x, "gap", "gap|%s" % j["code"], "Unmet: %s" % (j.get("label") or j["code"]), None,
                          list(j.get("incumbents") or [])[:3],
                          {"demand": min(1.0, (j.get("demand_authors") or 0) / 20.0), "supply_absence": 1.0 if j["cell"] == "absolute" else 0.6},
                          ["gap-map cell %s: %s demand authors, supply %s" % (j["cell"], j.get("demand_authors"), j.get("supply"))],
                          ["a red-team search for existing solutions"], j.get("evidence_ids") or [],
                          twist={"dimension": "job", "from": None, "to": j["code"]}, extra={"codes": [j["code"]]}))
    return out_


RULES = {"gap": _gap, "clone-wedge": _clone_wedge, "bundle": _bundle, "unbundle": _unbundle, "port": _port,
         "down-market": _down_market, "replace": _replace, "hosted-oss": _hosted_oss, "productize": _productize}


def _flags(x, cand):
    text = " ".join(str(v) for v in (cand["title"], cand.get("category_label"), (cand.get("twist") or {}).get("to")) if v)
    if REGULATED_RX.search(text):
        cand["flags"].append("regulated-risk")
    tw = cand.get("twist") or {}
    if cand["lens"] == "port" and tw.get("dimension") == "platform" and tw.get("to") in MARKETPLACE_PLATFORMS:
        cand["flags"].append("platform-dependency")
    if cand.get("license_class") == "duty":
        cand["flags"].append("license-duty: AGPL requires offering the source of a modified version to network users")
    if cand.get("license_class") == "unknown" and cand["lens"] == "hosted-oss":
        cand["flags"].append("license-check")
    ff = x.proto.get("founder_fit") or {}
    low = text.lower()
    for term in list(ff.get("exclusions") or []) + list((x.proto.get("scope") or {}).get("out") or []):
        t = (term or "").strip().lower()
        if len(t) >= 4 and t in low:
            cand["flags"].append("excluded: matches '%s'" % term)
            cand["status"] = "excluded"


def ambition_math(x, cand):
    amb = ((x.proto.get("ambition") or {}).get("min_arr_usd") or 0) / 12.0
    pool = [x.price[e] for e in cand["base_entities"] if x.price.get(e)] or \
           [x.price[e] for e in x.by_cat.get(cand.get("category"), []) if x.price.get(e)]
    price = _quantile(pool, 0.5) if pool else None
    if cand["lens"] == "down-market" and price:
        price = price / 2.0  # a cheaper tier: assume half the incumbents' median entry price
    installs = sum(int(x.trac[e]["installs"]) for e in cand["base_entities"] if x.trac.get(e) and x.trac[e].get("installs"))
    res = {"target_mrr": round(amb, 2) if amb else None, "price_ref_month": round(price, 2) if price else None,
           "customers_needed": int(math.ceil(amb / price)) if amb and price else None, "base_installs": installs or None}
    res["share_of_base_installs"] = round(res["customers_needed"] / float(installs), 5) if res["customers_needed"] and installs else None
    res["note"] = ("Customers needed at the incumbents' median entry price%s; share of the base products' installs is a reach "
                   "check, not a forecast." % (" halved for a cheaper tier" if cand["lens"] == "down-market" else ""))
    return res


def proven(x, eids, paid_only=False):
    """Which of these products are proven (top traction third of their store), optionally with a paid plan.
    Used by `cards check`, `certainty` and `score` for every lens other than gap: people already install and pay.
    `x` is a Ctx (build it once per command)."""
    q = x.c.get("opportunity.traction_quantile")
    return sorted(e for e in set(eids or []) if (x.tpct.get(e) or 0) >= q and (not paid_only or x.price.get(e)))


# ---------------------------------------------------------------- scan
def scan(run):
    x = Ctx(run)
    c = x.c
    want = lenses_of(x.proto)
    ids_path = p(run, "opportunities", "ids.json")
    ids = read_json(ids_path, {}) or {}
    prev = {r["key"]: r for r in read_jsonl(p(run, "opportunities", "candidates.jsonl"))[0]}
    report = {}
    cands = []
    for lens in want:
        got = RULES[lens](x)
        got.sort(key=lambda k: (-k["prior"], k["key"]))
        kept = got[: c.get("opportunity.max_per_lens")]
        note = None
        if lens == "gap" and not x.gapmap.get("jobs"):
            note = "needs the coded gap map (deep runs); scans find unmet needs through the other lenses' evidence"
        elif lens == "unbundle" and not x.supply and not kept:
            note = "no supply map; only evidence-led unbundling (users who use one part of a suite) can fire"
        elif lens in ("productize", "replace") and not x.led and not x.whynow:
            note = "evidence-led lens: fires after the first evidence round"
        report[lens] = {"generated": len(got), "kept": len(kept), "note": note}
        cands += kept
    for k in cands:
        _flags(x, k)
        k["ambition"] = ambition_math(x, k)
    # Candidates persist once generated (evidence may already be tagged with their ids); a rule that no
    # longer fires marks them instead of deleting them.
    now_keys = set(k["key"] for k in cands)
    for key, old in prev.items():
        if key not in now_keys:
            old = dict(old)
            if "rule no longer fires" not in old.get("flags", []):
                old.setdefault("flags", []).append("rule no longer fires")
            cands.append(old)
    cands.sort(key=lambda k: (-k["prior"], LENSES.index(k["lens"]), k["key"]))
    nxt = max([int(v.split("-")[1]) for v in ids.values()] or [0])
    for k in cands:
        if k["key"] not in ids:
            nxt += 1
            ids[k["key"]] = "OPP-%03d" % nxt
        k["opp_id"] = ids[k["key"]]
        old = prev.get(k["key"])
        if old and old.get("status") not in (None, "candidate") and k["status"] == "candidate":
            k["status"] = old["status"]
    cands = cands[: c.get("opportunity.max_candidates")]
    order = ["opp_id", "lens", "title", "status", "prior", "prior_parts", "category", "category_label", "segment", "base_entities",
             "base_names", "twist", "pair", "why", "needs", "evidence_ids", "flags", "ambition", "key"]
    rows = [dict({k: cand.get(k) for k in order}, **{k: v for k, v in cand.items() if k not in order}) for cand in cands]
    for r in rows:
        errs = validate(r, "opportunity")
        if errs:
            raise CliError("internal: candidate %s invalid: %s" % (r.get("opp_id"), "; ".join(errs[:3])))
    write_jsonl(p(run, "opportunities", "candidates.jsonl"), rows)
    write_json(ids_path, ids)
    doc = {"computed_at": now_iso(), "depth": depth_of(x.proto), "lenses": report,
           "inputs": {"products": len(x.prods), "with_attributes": len(x.attrs), "with_traction": len(x.tpct),
                      "with_rating_percentile": len(x.rpct), "with_price": len(x.price), "verified_records": len(x.led),
                      "coded_records": len(x.codes), "supply_map": bool(x.supply), "gap_map": bool(x.gapmap.get("jobs")),
                      "why_now": len(x.whynow)},
           "candidates": len(rows), "by_lens": {lens: sum(1 for r in rows if r["lens"] == lens) for lens in want},
           "note": "Prior = mean of each lens's structural signals (0..1), never evidence; evidence is scored separately."}
    write_json(p(run, "opportunities", "scan.json"), doc)
    st = load_state(run)
    state.touch(st, "opp_scan")
    save_state(run, st)
    return rows, doc


# ---------------------------------------------------------------- score
def _records_for(run, cands):
    led = {r["id"]: r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0] if (r.get("verification") or {}).get("status") == "verified"}
    tagged = {}
    for r in led.values():
        for oid in r.get("candidate_ids") or []:
            tagged.setdefault(oid, []).append(r["id"])
    res = {}
    for cand in cands:
        ids = sorted(set([i for i in cand.get("evidence_ids") or [] if i in led] + tagged.get(cand["opp_id"], [])))
        res[cand["opp_id"]] = [led[i] for i in ids]
    return res


def score(run):
    c = cfg(run)
    cands = read_jsonl(p(run, "opportunities", "candidates.jsonl"))[0]
    weights = c.get("evidence.strength_weights")
    recs = _records_for(run, cands)
    res = {}
    for cand in cands:
        rs = recs.get(cand["opp_id"], [])
        sup = [r for r in rs if r["stance"] in SUPPORT]
        con = [r for r in rs if r["stance"] in COUNTER]
        best = {}
        for r in sup:
            a = _author(r)
            best[a] = max(best.get(a, 0.0), weights.get(r["strength"], 0.0))
        ev = min(1.0, sum(best.values()) / float(c.get("scan.evidence_full")))
        share = len(con) / float(len(sup) + len(con)) if (sup or con) else 0.0
        domains = set(r.get("domain") for r in sup)
        if cand.get("status") == "excluded":
            status = "excluded"
        elif len(con) >= 2 and share > c.get("scan.max_counter_share"):
            status = "contradicted"
        elif len(sup) >= c.get("scan.min_records") and len(domains) >= c.get("scan.min_domains") and len(best) >= c.get("scan.min_authors"):
            status = "promising"
        elif sup:
            status = "thin"
        else:
            status = "untested"
        res[cand["opp_id"]] = {"status": status, "evidence_score": round(ev, 3), "records": len(rs), "support": len(sup),
                               "counter": len(con), "counter_share": round(share, 3), "authors": len(best), "domains": len(domains),
                               "source_types": len(set(r["source_type"] for r in sup)), "s4_authors": len(set(_author(r) for r in sup if r["strength"] == "S4")),
                               "evidence_ids": [r["id"] for r in rs]}
    write_json(p(run, "opportunities", "scores.json"), {"computed_at": now_iso(), "candidates": res,
                                                       "thresholds": {k: c.get("scan." + k) for k in ("min_records", "min_domains", "min_authors", "max_counter_share", "evidence_full")}})
    st = load_state(run)
    state.touch(st, "opp_score")
    save_state(run, st)
    return res


TIER = {"promising": 0, "thin": 1, "untested": 2, "contradicted": 3}


def redflags(run):
    return {r["opp_id"]: r for r in read_jsonl(p(run, "opportunities", "redflags.jsonl"))[0]}


def rank(run):
    c = cfg(run)
    cands = read_jsonl(p(run, "opportunities", "candidates.jsonl"))[0]
    sc = (read_json(p(run, "opportunities", "scores.json"), {}) or {}).get("candidates", {})
    rf = redflags(run)
    w = c.get("scan.rank_weights")
    rows, excluded = [], []
    for cand in cands:
        s = sc.get(cand["opp_id"]) or {"status": "untested", "evidence_score": 0.0}
        flag = rf.get(cand["opp_id"])
        reasons = []
        if s["status"] == "excluded" or cand.get("status") == "excluded":
            reasons += [f for f in cand.get("flags", []) if f.startswith("excluded")] or ["excluded by the protocol"]
        if flag and flag["verdict"] == "killed":
            reasons.append("red flag: killed (%s)" % (flag.get("note") or "an existing product already does this"))
        if flag and flag.get("gates"):
            from .gaps import _gates
            reasons += _gates(flag["gates"], c.get("scoring.gates"))
        combined = w["prior"] * (cand.get("prior") or 0.0) + w["evidence"] * s["evidence_score"]
        row = {"opp_id": cand["opp_id"], "lens": cand["lens"], "title": cand["title"], "status": s["status"],
               "redflag": flag["verdict"] if flag else None, "prior": cand.get("prior"), "evidence_score": s["evidence_score"],
               "combined": round(combined, 3), "flags": cand.get("flags", []), "ambition": cand.get("ambition")}
        if reasons:
            excluded.append(dict(row, reasons=reasons))
        else:
            rows.append(row)
    rows.sort(key=lambda r: (TIER.get(r["status"], 9), 1 if r["redflag"] == "flag" else 0, -r["combined"], r["opp_id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    doc = {"computed_at": now_iso(), "ranked": rows, "excluded": excluded, "weights": w,
           "note": "Order: evidence tier (promising, thin, untested, contradicted), then red-flag status, then "
                   "prior x weight + evidence x weight. A scan ranks options to test next; it is not a verdict."}
    write_json(p(run, "opportunities", "ranking.json"), doc)
    st = load_state(run)
    state.touch(st, "opp_rank")
    save_state(run, st)
    return doc


def select(run, round_no):
    """Successive halving: round 1 tests the best `scan.evidence_candidates` by prior (lens-diverse);
    round 2 keeps the best `scan.keep_fraction` of those by evidence and tests them again on new domains."""
    c = cfg(run)
    cands = [k for k in read_jsonl(p(run, "opportunities", "candidates.jsonl"))[0] if k.get("status") != "excluded"]
    if round_no == 1:
        n, cap = c.get("scan.evidence_candidates"), c.get("scan.max_per_lens")
        picked, per = [], {}
        for k in sorted(cands, key=lambda k: (-(k.get("prior") or 0), k["opp_id"])):
            if per.get(k["lens"], 0) < cap and len(picked) < n:
                picked.append(k)
                per[k["lens"]] = per.get(k["lens"], 0) + 1
        for k in sorted(cands, key=lambda k: (-(k.get("prior") or 0), k["opp_id"])):
            if len(picked) >= n:
                break
            if k not in picked:
                picked.append(k)
        return picked
    tested = tested_pool(run, cands)
    keep = int(math.ceil(len(tested) * c.get("scan.keep_fraction")))
    return tested[:keep]


def tested_pool(run, cands=None):
    """Options with some supporting evidence (round-1 tests and evidence-led options the leads miner found), best first."""
    if cands is None:
        cands = [k for k in read_jsonl(p(run, "opportunities", "candidates.jsonl"))[0] if k.get("status") != "excluded"]
    sc = (read_json(p(run, "opportunities", "scores.json"), {}) or {}).get("candidates", {})
    tested = [k for k in cands if (sc.get(k["opp_id"]) or {}).get("status") in ("promising", "thin")]
    tested.sort(key=lambda k: (TIER[sc[k["opp_id"]]["status"]], -sc[k["opp_id"]]["evidence_score"], -(k.get("prior") or 0), k["opp_id"]))
    return tested


# ---------------------------------------------------------------- report and next runs
QUESTION = {
    "clone-wedge": "Would {seg} switch from {base} to a {wedge} alternative, and could a small agent-built product reach ${mrr:,.0f}/month with it?",
    "port": "Do {seg} on {to} want {cat} that is already proven on {frm}, and could a small agent-built product reach ${mrr:,.0f}/month there?",
    "down-market": "Would {seg} pay for a cheaper, simpler {cat} than today's paid plans, and could it reach ${mrr:,.0f}/month?",
    "bundle": "Do {seg} who use both {cat} and {cat2} want them in one product, and could it reach ${mrr:,.0f}/month?",
    "unbundle": "Do users of {base} need only one part of it, and would a simple single-purpose product reach ${mrr:,.0f}/month?",
    "replace": "Where do users go after this change ({title}), and could a small agent-built replacement reach ${mrr:,.0f}/month?",
    "hosted-oss": "Would users of {base} pay for a hosted version, does the license allow it, and could it reach ${mrr:,.0f}/month?",
    "productize": "Could software replace the paid human work in '{title}', and could it reach ${mrr:,.0f}/month?",
    "gap": "Is '{title}' really unserved for {seg}, and could a small agent-built product reach ${mrr:,.0f}/month?",
}


def next_protocol(run, cand, new_run_id=None):
    """A narrow deep-run protocol draft for one candidate (the human or agent still reviews and freezes it)."""
    from .setup import draft_protocol
    proto = protocol(run)
    x_labels = {}
    cls = read_json(p(run, "landscape", "classification.json"), {}) or {}
    for facet, vals in (cls.get("facets") or {}).items():
        for v in vals or []:
            x_labels[(facet, v.get("id"))] = v.get("label") or v.get("id")
    seg_id = cand.get("segment")
    seg = x_labels.get(("segment", seg_id)) or (seg_id or "").replace("-", " ") or (proto.get("picos") or {}).get("population") or "small teams"
    tw = cand.get("twist") or {}
    cat = cand.get("category_label") or (cand.get("category") or "").replace("-", " ") or proto.get("topic")
    pair = cand.get("pair") or []
    cat2 = (x_labels.get(("category", pair[1])) or pair[1]) if len(pair) > 1 else ""
    mrr =(((proto.get("ambition") or {}).get("min_arr_usd")) or 12000) / 12.0
    q = QUESTION[cand["lens"]].format(seg=seg.lower(), base=", ".join(cand.get("base_names") or []) or "today's products",
                                      wedge=WEDGE_ADJ.get(tw.get("to"), "better").lower(), to=tw.get("to"), frm=tw.get("from"),
                                      cat=(cat or "").lower(), cat2=cat2.lower(),
                                      title=cand["title"], mrr=mrr)
    rid = new_run_id or "%s-%s" % (cand["opp_id"].lower(), _slug(cand["title"], 30))
    d = draft_protocol(rid, cand["title"], cand["title"], proto.get("seed", 0) + int(cand["opp_id"].split("-")[1]), proto.get("autonomy") or "autonomous")
    pic = proto.get("picos") or {}
    d.update({
        "question": q,
        "picos": {"population": seg, "intervention": cand["title"],
                  "comparator": ", ".join(cand.get("base_names") or []) + ("; " if cand.get("base_names") else "") + "workarounds and doing nothing",
                  "outcomes": pic.get("outcomes") or "time saved, money saved, revenue", "setting": pic.get("setting") or "online, self-serve"},
        "scope": {"in": [x for x in [cat, tw.get("to") if tw.get("dimension") in ("platform", "language", "segment") else None] if x],
                  "out": list((proto.get("scope") or {}).get("out") or [])},
        "business_models": proto.get("business_models") or ["b2b-saas"], "geography": proto.get("geography") or ["global"],
        "languages": sorted(set((proto.get("languages") or ["en"]) + ([tw["to"]] if tw.get("dimension") == "language" else []))),
        "recency_days": proto.get("recency_days") or 730,
        "eligibility": {"include": ["Products and services that do %s for %s" % ((cat or "this job").lower(), seg.lower()),
                                    "Workarounds people use for the same job (spreadsheets, scripts, freelancers)"],
                        "exclude": list((proto.get("eligibility") or {}).get("exclude") or [])},
        "founder_fit": proto.get("founder_fit") or d["founder_fit"], "ambition": proto.get("ambition") or {"min_arr_usd": 12000},
        "variation_dimensions": {k: v for k, v in (proto.get("variation_dimensions") or {}).items()},
        "competing_factors": list(proto.get("competing_factors") or []),
        "sources": proto.get("sources") or d["sources"], "budget": {"subagents_max": 60, "fetches_max": 2500},
        "depth": "deep", "lenses": [cand["lens"], "gap"] if cand["lens"] != "gap" else ["gap"],
        "cost_profile": proto.get("cost_profile") or "balanced",
        "seed_entities": [{"name": n, "url": u} for n, u in zip(cand.get("base_names") or [], cand.get("base_urls") or []) if u][:5],
        "notes": "Drafted from scan run %s, %s (%s). Review the question, PICOS and eligibility, then freeze." % (
            os.path.basename(os.path.normpath(run)), cand["opp_id"], LENS_LABEL[cand["lens"]]),
    })
    if not any(v for k, v in d["variation_dimensions"].items() if k != "ai_native"):
        d["variation_dimensions"]["price_tier"] = ["low"]
    return d


def report(run):
    c = cfg(run)
    proto = protocol(run)
    rk = read_json(p(run, "opportunities", "ranking.json"), {}) or {}
    cands = {k["opp_id"]: k for k in read_jsonl(p(run, "opportunities", "candidates.jsonl"))[0]}
    sc = (read_json(p(run, "opportunities", "scores.json"), {}) or {}).get("candidates", {})
    rf = redflags(run)
    led = {r["id"]: r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]}
    scan_doc = read_json(p(run, "opportunities", "scan.json"), {}) or {}
    sat = read_json(p(run, "landscape", "saturation.json"), {}) or {}
    ents = {e["entity_id"]: e for e in entities(run)}
    top_n = c.get("scan.report_top")
    items = []
    for r in rk.get("ranked", []):
        cand = dict(cands[r["opp_id"]])
        cand["base_urls"] = [(ents.get(e, {}).get("urls") or [None])[0] for e in cand.get("base_entities") or []]
        s = sc.get(r["opp_id"]) or {}
        quotes = []
        for eid in s.get("evidence_ids") or []:
            rec = led.get(eid)
            if rec and rec["stance"] in SUPPORT and len(quotes) < 3:
                quotes.append({"evidence_id": eid, "quote": rec["quote"], "url": rec["url"], "stance": rec["stance"], "strength": rec["strength"]})
        items.append({"rank": r["rank"], "opp_id": r["opp_id"], "lens": r["lens"], "lens_label": LENS_LABEL[r["lens"]], "title": r["title"],
                      "status": r["status"], "redflag": rf.get(r["opp_id"]), "prior": r["prior"], "evidence": s,
                      "why": cand.get("why"), "needs": cand.get("needs"), "flags": cand.get("flags"), "ambition": cand.get("ambition"),
                      "base_names": cand.get("base_names"), "twist": cand.get("twist"), "quotes": quotes, "_cand": cand})
    nxt_dir = p(run, "output", "next-runs")
    os.makedirs(nxt_dir, exist_ok=True)
    drafts = []
    for it in items:
        if len(drafts) >= c.get("scan.next_runs"):
            break
        if it["status"] in ("promising", "thin") and (it["redflag"] or {}).get("verdict") != "killed":
            d = next_protocol(run, it["_cand"])
            errs = [e for e in validate(d, "protocol")]
            if errs:
                raise CliError("internal: next-run protocol for %s invalid: %s" % (it["opp_id"], "; ".join(errs[:3])))
            path = os.path.join(nxt_dir, "%s.protocol.json" % it["opp_id"])
            write_json(path, d)
            it["next_run"] = {"protocol": os.path.relpath(path, run), "run_id": d["run_id"],
                              "command": "gapscan.py init gap-runs/%s --from-run %s --opportunity %s" % (d["run_id"], run, it["opp_id"])}
            drafts.append(it["opp_id"])
    for it in items:
        it.pop("_cand", None)
    doc = {"schema_version": "1.0", "run_id": os.path.basename(os.path.normpath(run)), "generated_at": now_iso(),
           "question": proto.get("question"), "depth": depth_of(proto), "lenses": lenses_of(proto),
           "landscape": {"products": scan_doc.get("inputs", {}).get("products"), "verdict": sat.get("verdict"),
                         "completeness": (sat.get("overall") or {}).get("completeness"), "coverage": (sat.get("overall") or {}).get("coverage")},
           "counts": {"candidates": len(cands), "ranked": len(items), "excluded": len(rk.get("excluded", [])),
                      "promising": sum(1 for i in items if i["status"] == "promising"), "tested": sum(1 for i in items if i["status"] != "untested")},
           "opportunities": items, "excluded": rk.get("excluded", []), "next_runs": drafts,
           "limitations": _limitations(run, scan_doc, sat)}
    write_json(p(run, "output", "opportunities.json"), doc)
    with open(p(run, "output", "opportunities.md"), "w", encoding="utf-8") as fh:
        fh.write(_markdown(doc, top_n))
    st = load_state(run)
    state.touch(st, "opp_report")
    save_state(run, st)
    return doc


def _limitations(run, scan_doc, sat):
    lim = ["A scan is a breadth sample: one landscape round, single screening, no codebook and no double coding. "
           "Treat each opportunity as a lead to test, not a finding."]
    if sat.get("verdict") != "SATURATED":
        lim.append("Landscape search stopped before saturation (%s): product counts are lower bounds." % (sat.get("verdict") or "not computed"))
    inp = scan_doc.get("inputs") or {}
    if inp.get("products"):
        lim.append("Traction numbers exist for %d of %d products (marketplace listings only); products without them are "
                   "never ranked as proven." % (inp.get("with_traction", 0), inp["products"]))
    gaps_ = read_jsonl(p(run, "coverage-gaps.jsonl"))[0]
    if gaps_:
        lim.append("%d coverage gaps logged (blocked or empty sources); see coverage-gaps.jsonl." % len(gaps_))
    return lim


def _money(v):
    return "-" if v is None else ("$%s" % format(int(round(v)), ","))


def _markdown(doc, top_n):
    L = ["# Opportunity scan: %s" % doc["run_id"], ""]
    if doc.get("question"):
        L += ["**Question.** " + doc["question"], ""]
    cn = doc["counts"]
    L += ["%d options generated from %s products; %d tested with evidence; %d promising; %d excluded (protocol, red flags or gates)." % (
        cn["candidates"], doc["landscape"].get("products") or "?", cn["tested"], cn["promising"], cn["excluded"]), ""]
    L += ["## Top options", "", "| # | Option | Kind | Evidence | Red flag | Customers for target |", "|---|---|---|---|---|---|"]
    for it in doc["opportunities"][:top_n]:
        ev = it["evidence"] or {}
        am = it.get("ambition") or {}
        cust = ("%s at %s/mo" % (am["customers_needed"], _money(am["price_ref_month"]))) if am.get("customers_needed") else "-"
        L.append("| %d | %s (%s) | %s | %s: %s records, %s authors, %s domains | %s | %s |" % (
            it["rank"], it["title"], it["opp_id"], it["lens_label"], it["status"], ev.get("support", 0), ev.get("authors", 0),
            ev.get("domains", 0), (it.get("redflag") or {}).get("verdict") or "not checked", cust))
    L.append("")
    for it in doc["opportunities"][: min(top_n, 5)]:
        L += ["### %d. %s (%s)" % (it["rank"], it["title"], it["opp_id"]), "",
              "- **Kind:** %s." % it["lens_label"],
              "- **Why it showed up:** %s." % "; ".join(it.get("why") or [])]
        if it.get("base_names"):
            L.append("- **Proven products it builds on:** %s." % ", ".join(it["base_names"]))
        am = it.get("ambition") or {}
        if am.get("customers_needed"):
            share = (" (%.2f%% of their %s installs)" % (100 * am["share_of_base_installs"], format(am["base_installs"], ","))) if am.get("share_of_base_installs") else ""
            L.append("- **Ambition math:** %s paying customers at %s/month reach %s/month%s." % (
                am["customers_needed"], _money(am["price_ref_month"]), _money(am["target_mrr"]), share))
        for qd in it.get("quotes") or []:
            L.append("- > \"%s\" (%s, %s %s)" % (qd["quote"], qd["evidence_id"], qd["stance"], qd["strength"]))
        rf_ = it.get("redflag") or {}
        if rf_:
            L.append("- **Red-flag check:** %s. %s" % (rf_.get("verdict"), rf_.get("note") or ""))
        if it.get("flags"):
            L.append("- **Flags:** %s." % "; ".join(it["flags"]))
        L.append("- **Still needed:** %s." % "; ".join(it.get("needs") or []))
        if it.get("next_run"):
            L.append("- **Deep run:** `%s` (protocol draft: `%s`)." % (it["next_run"]["command"], it["next_run"]["protocol"]))
        L.append("")
    if doc.get("excluded"):
        L += ["## Excluded", ""] + ["- %s %s: %s" % (e["opp_id"], e["title"], "; ".join(e["reasons"])) for e in doc["excluded"][:15]] + [""]
    L += ["## Limitations", ""] + ["- " + x for x in doc["limitations"]] + [""]
    return "\n".join(L)


# ---------------------------------------------------------------- commands
def cmd_opportunities(args):
    run = args.run
    require_run(run)
    act = args.action
    if act == "scan":
        if not os.path.exists(p(run, "landscape", "entity-attributes.jsonl")):
            raise CliError("no landscape map yet (landscape/entity-attributes.jsonl): the scan reads product attributes")
        rows, doc = scan(run)
        out("Opportunity scan: %d candidates (%s)." % (len(rows), ", ".join("%s %d" % (k, v) for k, v in doc["by_lens"].items() if v)))
        for lens, r in doc["lenses"].items():
            if r.get("note"):
                out("  %s: %s" % (lens, r["note"]))
        for r in rows[:8]:
            out("  %s %-12s prior %.2f  %s" % (r["opp_id"], r["lens"], r["prior"], r["title"]))
        return 0
    if act == "score":
        res = score(run)
        counts = {}
        for v in res.values():
            counts[v["status"]] = counts.get(v["status"], 0) + 1
        out("Opportunity evidence: %s." % ", ".join("%s %d" % kv for kv in sorted(counts.items())))
        return 0
    if act == "rank":
        doc = rank(run)
        out("Opportunity ranking: %s" % "; ".join("#%d %s %s (%s, %.2f)" % (r["rank"], r["opp_id"], r["lens"], r["status"], r["combined"])
                                                    for r in doc["ranked"][:8]))
        if doc["excluded"]:
            out("  excluded: %s" % ", ".join("%s (%s)" % (e["opp_id"], e["reasons"][0]) for e in doc["excluded"][:8]))
        return 0
    if act == "report":
        doc = report(run)
        out("Wrote output/opportunities.md and output/opportunities.json (%d ranked); next-run protocol drafts: %s." % (
            len(doc["opportunities"]), ", ".join(doc["next_runs"]) or "none"))
        return 0
    raise CliError("unknown action %s" % act)
