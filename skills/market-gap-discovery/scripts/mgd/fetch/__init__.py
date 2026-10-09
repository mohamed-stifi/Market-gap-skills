"""`gapscan.py fetch RUN SOURCE ...`: tier-1 adapters.

Every adapter snapshots the raw response (sha256), normalises items, hashes authors with the
run salt, logs the query (PRISMA-S) and prints a compact listing with total hits so agents can
quote verbatim from snapshot-backed text.

Normalised item fields: n, source, id, url, title, text (excerpt), author_hash, posted_at,
metrics, snapshot, kind_hint (product|community|evidence), entity_url, listing_url.
"""

import os

from mgcore.jsonio import append_jsonl, now_iso, write_jsonl

from ..common import CliError, cfg, out, p, require_run
from . import apis

ADAPTERS = {
    "hn": apis.hn, "hn-counts": apis.hn_counts, "hn-hiring": apis.hn_hiring,
    "se": apis.se, "se-counts": apis.se_counts,
    "gh-issues": apis.gh_issues, "gh-repos": apis.gh_repos,
    "wiki-views": apis.wiki_views,
    "wp-search": apis.wp_search, "wp-plugin": apis.wp_plugin, "wp-reviews": apis.wp_reviews,
    "apple-search": apis.apple_search, "apple-reviews": apis.apple_reviews,
    "atl-search": apis.atl_search, "atl-reviews": apis.atl_reviews,
    "yc": apis.yc,
}


def cmd_fetch(args):
    run = args.run
    require_run(run)
    if args.source not in ADAPTERS:
        raise CliError("unknown source %s; choose from %s" % (args.source, ", ".join(sorted(ADAPTERS))))
    ctx = apis.Ctx(run, args, cfg(run).get("budget.fetches_max"))
    result = ADAPTERS[args.source](ctx)
    items = result.get("items", [])
    for i, it in enumerate(items, 1):
        it["n"] = i
    raw_path = None
    if items:
        raw_path = p(run, "raw", args.source, "%s.jsonl" % (result.get("snapshot") or "nosnap")[:16])
        write_jsonl(raw_path, items)
    append_jsonl(p(run, "queries.jsonl"), {
        "at": now_iso(), "by": args.by, "unit": args.unit, "source": args.source, "method": "gapscan fetch",
        "query": result.get("query"), "filters": result.get("filters"), "total_hits": result.get("total_hits"),
        "items": len(items), "snapshot": result.get("snapshot"), "signal": result.get("signal_path")})
    out("source: %s | query: %s | total hits: %s | items: %d | snapshot: %s" % (
        args.source, result.get("query"), result.get("total_hits"), len(items), result.get("snapshot")))
    if result.get("warning"):
        out("warning: " + result["warning"])
    if result.get("signal_path"):
        out("signal series written: %s" % os.path.relpath(result["signal_path"], run))
    for it in items[: args.show]:
        metrics = ", ".join("%s=%s" % (k, v) for k, v in sorted((it.get("metrics") or {}).items()) if v is not None)
        out("[%d] %s | %s | %s | %s | %s | snap:%s" % (
            it["n"], (it.get("title") or "")[:90], it.get("url"), it.get("posted_at") or "-",
            it.get("author_hash") or "-", metrics, (it.get("snapshot") or "")[:16]))
        if it.get("text"):
            out("     " + it["text"][:300].replace("\n", " "))
    if raw_path:
        out("all items: %s" % os.path.relpath(raw_path, run))
    for note in result.get("notes", []):
        out("note: " + note)
    return 0
