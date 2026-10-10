"""`gapscan.py traction RUN`: installs, ratings and rating spread for marketplace products (method card D27).

A script, not a subagent. First it reads the marketplace API responses the run already saved (scouts'
`wp-search`, `apple-search`, `atl-search` calls), which costs no network. Then, unless `--offline`, it looks
up the products still missing (WordPress.org plugin_information, iTunes lookup), within a fetch budget.
Every number cites the snapshot it came from, so traction counts as script-verified demand evidence:
people already install, rate and pay for products that do this job.
"""

import glob
import json
import os
import re
import types

from mgcore import state
from mgcore.jsonio import now_iso, read_json, read_jsonl, write_jsonl

from .common import CliError, cfg, entities, included_verified, out, p, require_run, load_state, save_state

SOURCES = ("wp", "apple", "atl")


def _num(x):
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def _price(v):
    v = _num(v)
    return v if v is not None and v >= 0 else None


def _wp_row(pl):
    slug = pl.get("slug")
    if not slug:
        return None
    rating = _num(pl.get("rating"))
    dist = pl.get("ratings") if isinstance(pl.get("ratings"), dict) else None
    return "wp:%s" % slug, {"source": "wp", "installs": _num(pl.get("active_installs")), "ratings_count": _num(pl.get("num_ratings")),
                             "rating_avg": round(rating / 20.0, 3) if rating is not None else None,
                             "ratings_dist": {str(k): int(v) for k, v in dist.items()} if dist else None, "price_usd": None}


def _apple_row(r):
    tid = r.get("trackId")
    if not tid:
        return None
    return "app:ios:%s" % tid, {"source": "apple", "installs": None, "ratings_count": _num(r.get("userRatingCount")),
                                 "rating_avg": _num(r.get("averageUserRating")), "ratings_dist": None,
                                 "price_usd": _price(r.get("price")) if (r.get("currency") in (None, "USD")) else None}


def _atl_row(ad):
    href = ((ad.get("_links") or {}).get("alternate") or {}).get("href") or ""
    m = re.search(r"/apps/(\d+)", href)
    if not m:
        return None
    emb = ad.get("_embedded") or {}
    rev = emb.get("reviews") or {}
    return "atl:%s" % m.group(1), {"source": "atl", "installs": _num((emb.get("distribution") or {}).get("totalInstalls")),
                                    "ratings_count": _num(rev.get("count")), "rating_avg": _num(rev.get("averageStars")),
                                    "ratings_dist": None, "price_usd": None}


def _rows_from(method, data):
    """(key, row) pairs from one saved API response."""
    if not isinstance(data, dict):
        return []
    if method == "api:wp":
        items = data.get("plugins") if isinstance(data.get("plugins"), list) else ([data] if data.get("slug") else [])
        return [x for x in (_wp_row(pl) for pl in items if isinstance(pl, dict)) if x]
    if method == "api:apple":
        return [x for x in (_apple_row(r) for r in data.get("results") or [] if isinstance(r, dict)) if x]
    if method == "api:atl":
        items = (data.get("_embedded") or {}).get("addons")
        items = items if isinstance(items, list) else ([data] if data.get("key") else [])
        return [x for x in (_atl_row(ad) for ad in items if isinstance(ad, dict)) if x]
    return []


def from_snapshots(run):
    """Latest row per marketplace key from the run's saved API responses (no network)."""
    best = {}
    for meta_path in glob.glob(p(run, "snapshots", "*.meta.json")):
        meta = read_json(meta_path, {}) or {}
        method = meta.get("method")
        if method not in ("api:wp", "api:apple", "api:atl"):
            continue
        raw = meta_path[: -len(".meta.json")] + ".raw"
        try:
            with open(raw, "rb") as fh:
                data = json.loads(fh.read().decode("utf-8", "replace"))
        except (OSError, ValueError):
            continue
        for key, row in _rows_from(method, data):
            row = dict(row, snapshot=meta.get("sha256"), retrieved_at=meta.get("fetched_at"), via="snapshot")
            cur = best.get(key)
            # Keep the newest response; on ties the one with more filled numbers.
            filled = sum(1 for k in ("installs", "ratings_count", "rating_avg") if row.get(k) is not None)
            if cur is None or (row["retrieved_at"] or "", filled) > (cur["retrieved_at"] or "", cur["_filled"]):
                best[key] = dict(row, _filled=filled)
    for row in best.values():
        row.pop("_filled", None)
    return best


def _lookup(run, key, budget):
    """Fetch one product's numbers through the API adapters. Returns a row or None (failures are coverage gaps)."""
    from .fetch import apis
    kind, _sep, ident = key.partition(":")
    if kind == "app":
        ident = key.split(":", 2)[2]
        args = types.SimpleNamespace(id=ident, country="us", by="traction")
        fn, method = apis.apple_lookup, "api:apple"
    elif kind == "wp":
        args = types.SimpleNamespace(slug=ident, by="traction")
        fn, method = apis.wp_plugin, "api:wp"
    else:
        return None
    try:
        res = fn(apis.Ctx(run, args, budget))
    except CliError:
        return None
    sha = res.get("snapshot")
    raw = p(run, "snapshots", (sha or "") + ".raw")
    if not sha or not os.path.exists(raw):
        return None
    with open(raw, "rb") as fh:
        data = json.loads(fh.read().decode("utf-8", "replace"))
    rows = dict(_rows_from(method, data))
    row = rows.get(key)
    if row is None:
        return None
    meta = read_json(p(run, "snapshots", sha + ".meta.json"), {}) or {}
    return dict(row, snapshot=sha, retrieved_at=meta.get("fetched_at") or now_iso(), via="lookup")


def build(run, offline=False):
    c = cfg(run)
    prods = [e for e in included_verified(entities(run)) if e["kind"] == "product"]
    keys_of = {}
    for e in prods:
        ks = [e["entity_id"]] + list(e.get("aliases") or [])
        keys_of[e["entity_id"]] = [k for k in ks if k.split(":")[0] in ("wp", "app", "atl")]
    snap = from_snapshots(run)
    rows, missing = {}, []
    for eid, ks in sorted(keys_of.items()):
        if not ks:
            continue
        hit = next((snap[k] for k in ks if k in snap), None)
        if hit:
            rows[eid] = dict(hit, entity_id=eid, key=next(k for k in ks if k in snap))
        else:
            missing.append((eid, ks[0]))
    looked = failed = 0
    skipped = []
    if not offline:
        cap = c.get("traction.max_lookups")
        for eid, key in missing:
            if key.startswith("atl:"):
                skipped.append(eid)  # no documented Atlassian endpoint by numeric app id; scouts' search responses cover most
                continue
            if looked >= cap:
                skipped.append(eid)
                continue
            looked += 1
            row = _lookup(run, key, c.get("budget.fetches_max"))
            if row:
                rows[eid] = dict(row, entity_id=eid, key=key)
            else:
                failed += 1
    else:
        skipped = [eid for eid, _k in missing]
    order = ("entity_id", "key", "source", "installs", "ratings_count", "rating_avg", "ratings_dist", "price_usd", "snapshot", "retrieved_at", "via")
    out_rows = [{k: r.get(k) for k in order} for _e, r in sorted(rows.items())]
    write_jsonl(p(run, "landscape", "traction.jsonl"), out_rows)
    st = load_state(run)
    state.touch(st, "traction")
    st.setdefault("traction", {}).update({"rows": len(out_rows), "looked_up": looked, "lookup_failed": failed,
                                          "not_looked_up": len(skipped), "marketplace_products": sum(1 for v in keys_of.values() if v),
                                          "products": len(prods), "at": now_iso()})
    save_state(run, st)
    return out_rows, {"marketplace_products": sum(1 for v in keys_of.values() if v), "products": len(prods),
                      "from_snapshots": sum(1 for r in out_rows if r["via"] == "snapshot"), "looked_up": looked,
                      "lookup_failed": failed, "not_looked_up": len(skipped)}


def load(run):
    """entity_id -> traction row, from traction.jsonl, falling back to the mapper's `signals` fields."""
    rows = {r["entity_id"]: r for r in read_jsonl(p(run, "landscape", "traction.jsonl"))[0]}
    for a in read_jsonl(p(run, "landscape", "entity-attributes.jsonl"))[0]:
        s = a.get("signals") or {}
        if a["entity_id"] in rows or not any(s.get(k) is not None for k in ("installs", "ratings_count", "rating_avg", "stars")):
            continue
        eid = a["entity_id"]
        src = "wp" if eid.startswith("wp:") else ("apple" if eid.startswith("app:") else ("atl" if eid.startswith("atl:") else ("gh" if s.get("stars") is not None else "other")))
        rows[eid] = {"entity_id": eid, "key": eid, "source": src, "installs": s.get("installs") if s.get("installs") is not None else s.get("stars"),
                     "ratings_count": s.get("ratings_count"), "rating_avg": s.get("rating_avg"), "ratings_dist": None,
                     "price_usd": None, "snapshot": None, "retrieved_at": None, "via": "mapping"}
    return rows


def cmd_traction(args):
    run = args.run
    require_run(run)
    if not os.path.exists(p(run, "landscape", "entities.jsonl")):
        raise CliError("no landscape yet: traction reads included products")
    rows, s = build(run, offline=getattr(args, "offline", False))
    out("Traction: %d of %d marketplace products have numbers (%d from saved API responses, %d looked up, %d lookups failed, %d not looked up); "
        "%d products in all. Written to landscape/traction.jsonl." % (
            len(rows), s["marketplace_products"], s["from_snapshots"], s["looked_up"] - s["lookup_failed"], s["lookup_failed"],
            s["not_looked_up"], s["products"]))
    return 0
