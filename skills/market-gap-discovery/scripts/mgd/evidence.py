"""Evidence integrity commands: snapshot, hash-author, log-query, verify, stoptest
(method cards D08-D10)."""

import os

from mgcore import quotes, state, stats
from mgcore.jsonio import append_jsonl, now_iso, read_jsonl, write_json, write_jsonl

from . import models, net
from .common import CliError, EXIT_BLOCKED, cfg, out, p, require_run, load_state, save_state
from .privacy import author_hash


def cmd_snapshot(args):
    run = args.run
    require_run(run)
    budget = cfg(run).get("budget.fetches_max")
    interval = cfg(run).get("evidence.min_interval_seconds")
    blocked = 0
    for url in args.urls:
        existing = None if args.refresh else net.snapshot_for(run, url)
        if existing:
            out("%s 200 %s (reused snapshot from the last 24 h)" % (existing, url))
            continue
        try:
            status, final, ctype, body = net.get(run, url, source="snapshot", robots=True, min_interval=interval,
                                                 by=args.by, budget=budget)
        except net.Blocked as exc:
            blocked += 1
            out("BLOCKED %s: %s (recorded as a coverage gap; do not work around it)" % (url, exc))
            continue
        sha = net.save_snapshot(run, url, final, status, ctype, body, "urllib", args.by)
        out("%s %d %s" % (sha, status, url))
        if status != 200:
            out("  note: HTTP %d; the page may not contain what you expect" % status)
    return EXIT_BLOCKED if blocked == len(args.urls) else 0


def cmd_hash_author(args):
    require_run(args.run)
    out(author_hash(args.run, args.platform, args.handle))
    return 0


def cmd_log_query(args):
    require_run(args.run)
    append_jsonl(p(args.run, "queries.jsonl"), {
        "at": now_iso(), "by": args.by, "unit": args.unit, "source": args.source, "query": args.query,
        "filters": args.filters, "total_hits": args.count, "method": "agent-web-search"})
    out("logged")
    return 0


def cmd_verify(args):
    run = args.run
    require_run(run)
    led = read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]
    counts = {"verified": 0, "failed": 0, "no_snapshot": 0}
    failed = []
    for r in led:
        text = net.snapshot_text(run, r["snapshot"])
        if text is None:
            r["verification"] = {"status": "no_snapshot", "offset": None, "checked_at": now_iso()}
            counts["no_snapshot"] += 1
            failed.append({"id": r["id"], "url": r["url"], "reason": "snapshot missing"})
            continue
        ok, off = quotes.verify_quote(r["quote"], text)
        r["verification"] = {"status": "verified" if ok else "failed", "offset": off, "checked_at": now_iso()}
        counts["verified" if ok else "failed"] += 1
        if not ok:
            failed.append({"id": r["id"], "url": r["url"], "quote": r["quote"][:120],
                           "reason": "quote not found verbatim in snapshot %s" % r["snapshot"][:16]})
    write_jsonl(p(run, "evidence", "ledger.jsonl"), led)
    total = len(led)
    write_json(p(run, "evidence", "verify-report.json"), {"checked_at": now_iso(), "total": total, "counts": counts,
                                                         "verified_share": (counts["verified"] / float(total)) if total else None,
                                                         "failed": failed})
    st = load_state(run)
    state.touch(st, "verify")
    # Cheap-tier miners are safe because this check catches bad quotes; if a round's quotes verify
    # poorly, the next miners run one tier up.
    r = st.get("evidence", {}).get("round")
    mine = [x for x in led if x.get("round") == r]
    if mine:
        share = sum(1 for x in mine if x["verification"]["status"] == "verified") / float(len(mine))
        lim = cfg(run).get("models.escalate_on").get("miner_verify_below")
        if share < lim and models.escalate_once(st, "verify-R%02d" % r, "miner", "round %d quotes %.0f%% verified (< %.0f%%)" % (r, 100 * share, 100 * lim)):
            out("Miners escalated one model tier for later rounds: round %d verified %.0f%% of its quotes." % (r, 100 * share))
    save_state(run, st)
    out("Quote verification: %d of %d verified (%.0f%%); %d failed; %d without snapshot. Only verified records count." % (
        counts["verified"], total, 100.0 * counts["verified"] / total if total else 0, counts["failed"], counts["no_snapshot"]))
    for f in failed[:8]:
        out("  %s: %s" % (f["id"], f["reason"]))
    return 0


def cmd_stoptest(args):
    res = stats.callaghan_stop(args.unseen, args.sample_n, args.sample_k, args.found, args.recall, args.confidence)
    out("%s p=%.4f (K_tar=%d, recall target %.2f at %.0f%% confidence)" % (
        res["decision"], res["p_value"], res["k_tar"], args.recall, 100 * args.confidence))
    if args.run:
        append_jsonl(p(args.run, "queries.jsonl"), {"at": now_iso(), "by": args.by, "method": "stoptest",
                                                    "source": args.source, "query": args.query, "stoptest": dict(res, unseen=args.unseen,
                                                    sample_n=args.sample_n, sample_k=args.sample_k, found=args.found)})
    return 0
