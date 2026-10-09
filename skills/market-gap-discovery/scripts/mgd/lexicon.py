"""Lexicon merge (independent vocabularies -> overlap -> union), deterministic query blocks,
and PRESS-review application (method card D02)."""

import hashlib
import itertools
import os
import re

from mgcore import richness, state
from mgcore.jsonio import read_json, write_json

from .common import CliError, out, p, require_run, load_state, save_state, validate

FACETS = ["segment", "job", "category", "tool", "pain", "workaround", "other"]

# (id, template, facets, intent). Landscape intents find products; evidence intents find pains.
# Workarounds pair with segments (who does them), and the `other` facet (billing units, tax and
# payment-term jargon) gets its own templates, following the PRESS review of a live run.
TEMPLATES = [
    ("cat-seg", "{category} for {segment}", ("category", "segment"), "landscape"),
    ("cat-software", "{category} software", ("category",), "landscape"),
    ("best-cat-seg", "best {category} for {segment}", ("category", "segment"), "landscape"),
    ("tool-alt", "{tool} alternative", ("tool",), "landscape"),
    ("alt-to-tool", "alternative to {tool}", ("tool",), "landscape"),
    ("tool-vs", "{tool} vs", ("tool",), "landscape"),
    ("job-tool", "{job} tool", ("job",), "landscape"),
    ("job-seg", "{job} {segment}", ("job", "segment"), "landscape"),
    ("app-to-job", "app to {job}", ("job",), "landscape"),
    ("cat-other", "{category} {other}", ("category", "other"), "landscape"),
    ("howto-job", "how do I {job}", ("job",), "evidence"),
    ("pain-cat", "{pain} {category}", ("pain", "category"), "evidence"),
    ("tool-pain", "{tool} {pain}", ("tool", "pain"), "evidence"),
    ("wish-tool", "I wish {tool}", ("tool",), "evidence"),
    ("seg-workaround", "{segment} {workaround}", ("segment", "workaround"), "evidence"),
    ("seg-job-problem", "{segment} {job} problem", ("segment", "job"), "evidence"),
    ("other-seg", "{other} {segment}", ("other", "segment"), "evidence"),
    ("cat-too-expensive", "{category} too expensive", ("category",), "evidence"),
]
PER_TEMPLATE = 12


STOP = {"a", "an", "the", "for", "of", "to", "and", "or", "in", "on", "with", "by", "my", "your", "our"}


def term_key(t):
    """Normalised key for overlap: lower case, plural-insensitive, order-insensitive, no stop-words,
    so 'late payments' and 'Payment, late' count as the same term."""
    toks = []
    for tok in re.findall(r"[a-z0-9]+", norm_term(t)):
        if tok in STOP:
            continue
        if len(tok) > 4 and tok.endswith("ies"):
            tok = tok[:-3] + "y"
        elif tok.endswith(("sses", "ches", "shes", "xes", "zes")):
            tok = tok[:-2]
        elif len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        toks.append(tok)
    return " ".join(sorted(toks))


def norm_term(t):
    t = re.sub(r"\s+", " ", (t or "").strip().strip("\"'`.,;:!?()[]{}")).casefold()
    return t


def _protocol_tokens(proto):
    proto = proto or {}
    parts = [proto.get("topic") or "", proto.get("question") or ""]
    parts += list((proto.get("picos") or {}).values())
    parts += list((proto.get("scope") or {}).get("in") or [])
    parts += [str(x) for x in ((proto.get("variation_dimensions") or {}).get("segment") or [])]
    toks = set()
    for part in parts:
        toks |= set(term_key(str(part)).split())
    return toks


def _priority(entry, proto_tokens):
    """Consensus between independent scouts first, then reviewer- and protocol-curated terms, then
    relevance to the protocol's own words. Alphabetical order never decides what gets searched."""
    found = entry.get("found_by", [])
    scouts = len(set(f for f in found if f.startswith("R")))
    curated = 2 if ("PRESS" in found or "PROTOCOL" in found) else 0
    toks = set(term_key(entry["term"]).split())
    relevant = 1 if toks & proto_tokens else 0
    return scouts + curated + relevant


def _ranked(entries, proto_tokens=frozenset(), seed=0):
    def tie(e):
        return hashlib.sha256(("%s|%s" % (seed, e["term"])).encode("utf-8")).hexdigest()
    return [e["term"] for e in sorted(entries, key=lambda e: (-_priority(e, proto_tokens), tie(e)))]


def _combos(lists, cap):
    if len(lists) == 1:
        return [(x,) for x in lists[0][:cap]]
    a, b = lists
    out_, d = [], 0
    while len(out_) < cap and d < len(a) + len(b):
        for i in range(d + 1):
            j = d - i
            if i < len(a) and j < len(b):
                out_.append((a[i], b[j]))
                if len(out_) >= cap:
                    break
        d += 1
    return out_


_DOUBLE = re.compile(r"\b(\w+)(\s+\1\b)+", re.I)


def build_blocks(lexicon, proto=None, seed=0):
    ptok = _protocol_tokens(proto)
    ranked = {f: _ranked(lexicon["facets"].get(f, []), ptok, seed) for f in FACETS}
    blocks, n, seen = [], 0, set()
    for tid, tpl, facets, intent in TEMPLATES:
        lists = [ranked[f] for f in facets]
        if any(not l for l in lists):
            continue
        for combo in _combos(lists, PER_TEMPLATE):
            query = _DOUBLE.sub(r"\1", tpl.format(**dict(zip(facets, combo)))).strip()
            if query.lower() in seen:
                continue
            seen.add(query.lower())
            n += 1
            blocks.append({"id": "QB-%03d" % n, "template": tid, "query": query,
                           "facets": dict(zip(facets, combo)), "intent": intent})
    return blocks


def _add_protocol_terms(lex, proto):
    """The protocol's own variation segments are searched too (PICOS-anchored search strategy)."""
    segs = [norm_term(str(x)) for x in ((proto or {}).get("variation_dimensions") or {}).get("segment") or []]
    existing = set(e["term"] for e in lex["facets"].setdefault("segment", []))
    for t in segs:
        if t and t not in existing:
            lex["facets"]["segment"].append({"term": t, "found_by": ["PROTOCOL"], "first_round": None})
            existing.add(t)


def merge_lexicon(run):
    require_run(run)
    st = load_state(run)
    r = st["lexicon"]["round"]
    key = "lexicon-R%02d" % r
    group = st.get("groups", {}).get(key)
    if not group:
        raise CliError("no lexicon round assigned; run `assign --phase lexicon` first")
    scouts = {}
    for apath in group["paths"]:
        a = read_json(p(run, apath))
        opath = a["outputs"][0]["path"]
        doc = read_json(p(run, opath))
        if doc is None:
            raise CliError("missing scout output %s" % opath)
        errs = validate(doc, "lexicon-output")
        if errs:
            raise CliError("%s is invalid:\n  " % opath + "\n  ".join(errs[:10]))
        scouts[doc["scout_id"]] = {f: set(norm_term(t) for t in doc["facets"].get(f, []) if norm_term(t)) for f in FACETS}
    lex = read_json(p(run, "lexicon", "lexicon.json"), {"facets": {f: [] for f in FACETS}, "rounds": []})
    index = {(f, e["term"]): e for f in FACETS for e in lex["facets"].get(f, [])}
    for sid, facets in sorted(scouts.items()):
        for f, terms in facets.items():
            for t in sorted(terms):
                e = index.get((f, t))
                if not e:
                    e = {"term": t, "found_by": [], "first_round": r}
                    lex["facets"].setdefault(f, []).append(e)
                    index[(f, t)] = e
                tag = "R%02d-%s" % (r, sid)
                if tag not in e["found_by"]:
                    e["found_by"].append(tag)
    pairs = []
    ids = sorted(scouts)
    for x, y in itertools.combinations(ids, 2):
        # Overlap is judged on normalised keys across facets (scouts may file a term under different facets).
        kx = set(term_key(t) for f in FACETS for t in scouts[x][f]) - {""}
        ky = set(term_key(t) for f in FACETS for t in scouts[y][f]) - {""}
        exact = richness.jaccard(set(t for f in FACETS for t in scouts[x][f]), set(t for f in FACETS for t in scouts[y][f]))
        per_facet = {f: richness.jaccard(set(map(term_key, scouts[x][f])), set(map(term_key, scouts[y][f])))
                     for f in FACETS if scouts[x][f] or scouts[y][f]}
        pairs.append({"a": x, "b": y, "overall": richness.jaccard(kx, ky), "exact": exact, "per_facet": per_facet})
    mean = sum(pp["overall"] for pp in pairs) / len(pairs) if pairs else 1.0
    lex["rounds"].append({"round": r, "scouts": ids, "mean_jaccard": mean})
    write_json(p(run, "lexicon", "round-%02d" % r, "overlap.json"), {"round": r, "pairs": pairs, "mean_jaccard": mean})
    proto = read_json(p(run, "protocol.json"), {}) or {}
    _add_protocol_terms(lex, proto)
    write_json(p(run, "lexicon", "lexicon.json"), lex)
    blocks = build_blocks(lex, proto, st.get("seed", 0))
    write_json(p(run, "lexicon", "query-blocks.json"), {"blocks": blocks})
    st["lexicon"]["merged"] = r
    st["lexicon"]["overlap"] = mean
    group["merged"] = True
    state.touch(st, "lexicon_merge")
    save_state(run, st)
    state.event(run, "merge_lexicon", round=r, mean_jaccard=mean, blocks=len(blocks))
    total = sum(len(v) for v in lex["facets"].values())
    out("Lexicon round %d merged: %d terms, mean pairwise Jaccard %.2f, %d query blocks." % (r, total, mean, len(blocks)))
    return 0


def cmd_apply_press(args):
    run = args.run
    require_run(run)
    st = load_state(run)
    group = st.get("groups", {}).get("press")
    doc = read_json(p(run, "lexicon", "press.json"))
    if not group or doc is None:
        raise CliError("no PRESS review found; assign and spawn the reviewer first")
    errs = validate(doc, "press")
    if errs:
        raise CliError("press.json is invalid:\n  " + "\n  ".join(errs[:10]))
    lex = read_json(p(run, "lexicon", "lexicon.json"))
    added, removed = 0, 0
    remove = set(norm_term(t) for t in doc.get("remove", []))
    for f in FACETS:
        before = len(lex["facets"].get(f, []))
        lex["facets"][f] = [e for e in lex["facets"].get(f, []) if e["term"] not in remove]
        removed += before - len(lex["facets"][f])
        existing = set(e["term"] for e in lex["facets"][f])
        for t in (doc.get("add") or {}).get(f, []):
            nt = norm_term(t)
            if nt and nt not in existing:
                lex["facets"][f].append({"term": nt, "found_by": ["PRESS"], "first_round": None})
                existing.add(nt)
                added += 1
    lex["press"] = {"verdict": doc["verdict"], "added": added, "removed": removed}
    proto = read_json(p(run, "protocol.json"), {}) or {}
    _add_protocol_terms(lex, proto)
    write_json(p(run, "lexicon", "lexicon.json"), lex)
    blocks = build_blocks(lex, proto, st.get("seed", 0))
    write_json(p(run, "lexicon", "query-blocks.json"), {"blocks": blocks})
    group["merged"] = True
    state.touch(st, "lexicon_press")
    save_state(run, st)
    state.event(run, "press_applied", added=added, removed=removed, verdict=doc["verdict"])
    out("PRESS review applied (%s): +%d terms, -%d terms, %d query blocks." % (doc["verdict"], added, removed, len(blocks)))
    return 0
