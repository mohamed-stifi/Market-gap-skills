#!/usr/bin/env python3
"""gapscan.py: deterministic backbone of the market-gap-discovery skill.

Agents search, read and label; this script counts, merges, verifies, scores and decides.
Start with `gapscan.py init RUN --topic ...`, then follow `gapscan.py next RUN`.
Full reference: references/cli.md. Standard library only (Python 3.8+).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mgd import analysis, assign, coding, entities, evidence, flow, gaps, merge, report, saturation, setup  # noqa: E402
from mgd import lexicon as lexmod  # noqa: E402
from mgd.common import CliError  # noqa: E402
from mgd.fetch import ADAPTERS, cmd_fetch  # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(prog="gapscan.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command")

    s = sub.add_parser("init", help="create a run folder and a protocol draft")
    s.add_argument("run")
    s.add_argument("--topic", required=True)
    s.add_argument("--title")
    s.add_argument("--seed", type=int)
    s.add_argument("--autonomy", choices=["autonomous", "gated"], default="autonomous")
    s.set_defaults(func=setup.cmd_init)

    s = sub.add_parser("doctor", help="check sources, keys and network; record coverage gaps")
    s.add_argument("run")
    s.add_argument("--offline", action="store_true")
    s.set_defaults(func=setup.cmd_doctor)

    s = sub.add_parser("protocol", help="check, show, freeze or amend the protocol")
    s.add_argument("action", choices=["check", "show", "freeze", "amend"])
    s.add_argument("run")
    s.add_argument("--reason")
    s.add_argument("--set", action="append", metavar="KEY=JSON")
    s.set_defaults(func=setup.cmd_protocol)

    s = sub.add_parser("next", help="print the single next action")
    s.add_argument("run")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=flow.cmd_next)

    s = sub.add_parser("status", help="summarise the run")
    s.add_argument("run")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=flow.cmd_status)

    s = sub.add_parser("hq", help="human-task queue")
    s.add_argument("action", choices=["list", "add", "done", "decline"])
    s.add_argument("run")
    s.add_argument("task", nargs="?")
    s.add_argument("--type", choices=["account", "key", "payment", "legal", "outward-action", "judgment", "directive"])
    s.add_argument("--title")
    s.add_argument("--why")
    s.add_argument("--steps")
    s.add_argument("--returns")
    s.add_argument("--phase")
    s.add_argument("--blocking", action="store_true")
    s.add_argument("--fallback")
    s.add_argument("--note")
    s.set_defaults(func=setup.cmd_hq)

    s = sub.add_parser("assign", help="write assignment files for subagents")
    s.add_argument("run")
    s.add_argument("--phase", required=True, choices=sorted(assign.PHASES))
    s.add_argument("--units", type=int)
    s.add_argument("--batch", type=int)
    s.add_argument("--revise", action="store_true")
    s.add_argument("--targeted", action="store_true",
                   help="evidence only: one miner per near-miss gap card, mining domains the card does not have yet")
    s.set_defaults(func=assign.cmd_assign)

    s = sub.add_parser("merge", help="validate and merge agent outputs")
    s.add_argument("run")
    s.add_argument("--phase", required=True, choices=["lexicon", "landscape", "probe", "snowball", "screen", "mapping",
                                                       "evidence", "coding", "supply", "redteam"])
    s.add_argument("--retry", action="store_true",
                   help="evidence only: merge the current round again after fixing rejected records; "
                        "records already in the ledger count as duplicates")
    s.set_defaults(func=merge.cmd_merge)

    s = sub.add_parser("lexicon", help="lexicon utilities")
    s.add_argument("action", choices=["apply-press"])
    s.add_argument("run")
    s.set_defaults(func=lexmod.cmd_apply_press)

    s = sub.add_parser("entities", help="entity utilities")
    s.add_argument("action", choices=["verify"])
    s.add_argument("run")
    s.add_argument("--limit", type=int)
    s.add_argument("--recheck", action="store_true", help="re-evaluate name misses from existing snapshots")
    s.set_defaults(func=entities.cmd_verify_entities)

    s = sub.add_parser("codebook", help="codebook utilities")
    s.add_argument("action", choices=["freeze"])
    s.add_argument("run")
    s.set_defaults(func=coding.cmd_codebook_freeze)

    s = sub.add_parser("fetch", help="tier-1 source adapters")
    s.add_argument("run")
    s.add_argument("source", choices=sorted(ADAPTERS))
    s.add_argument("--query")
    s.add_argument("--tags")
    s.add_argument("--since")
    s.add_argument("--limit", type=int)
    s.add_argument("--from", dest="from_")
    s.add_argument("--to")
    s.add_argument("--months", type=int)
    s.add_argument("--site")
    s.add_argument("--article")
    s.add_argument("--project")
    s.add_argument("--slug")
    s.add_argument("--id")
    s.add_argument("--key")
    s.add_argument("--country")
    s.add_argument("--pages", type=int)
    s.add_argument("--unit")
    s.add_argument("--by")
    s.add_argument("--show", type=int, default=25)
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("snapshot", help="robots-checked raw snapshot of pages")
    s.add_argument("run")
    s.add_argument("urls", nargs="+")
    s.add_argument("--by")
    s.add_argument("--refresh", action="store_true")
    s.set_defaults(func=evidence.cmd_snapshot)

    s = sub.add_parser("hash-author", help="print the salted author hash")
    s.add_argument("run")
    s.add_argument("platform")
    s.add_argument("handle")
    s.set_defaults(func=evidence.cmd_hash_author)

    s = sub.add_parser("log-query", help="log a web search run with the agent's own tool")
    s.add_argument("run")
    s.add_argument("--source", required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--count", type=int)
    s.add_argument("--filters")
    s.add_argument("--unit")
    s.add_argument("--by")
    s.set_defaults(func=evidence.cmd_log_query)

    s = sub.add_parser("stoptest", help="statistical stopping test for large ranked pools")
    s.add_argument("--unseen", type=int, required=True)
    s.add_argument("--sample-n", type=int, required=True)
    s.add_argument("--sample-k", type=int, required=True)
    s.add_argument("--found", type=int, required=True)
    s.add_argument("--recall", type=float, default=0.95)
    s.add_argument("--confidence", type=float, default=0.95)
    s.add_argument("--run")
    s.add_argument("--source")
    s.add_argument("--query")
    s.add_argument("--by")
    s.set_defaults(func=evidence.cmd_stoptest)

    simple = [("saturation", saturation.cmd_saturation, "saturation estimators and verdict"),
              ("verify", evidence.cmd_verify, "verify every quote against its snapshot"),
              ("screen-audit", coding.cmd_screen_audit, "screening agreement (alpha)"),
              ("agreement", coding.cmd_agreement, "coding agreement per code"),
              ("themes", coding.cmd_themes, "theme saturation"),
              ("bursts", analysis.cmd_bursts, "burst detection on signals"),
              ("matrix", analysis.cmd_matrix, "competitor matrix, price ladder, strategy canvas"),
              ("gapmap", analysis.cmd_gapmap, "demand-supply gap map"),
              ("variants", gaps.cmd_variants, "change-one-dimension candidates"),
              ("certainty", gaps.cmd_certainty, "certainty of evidence per gap"),
              ("size", gaps.cmd_size, "bottom-up TAM/SAM/SOM"),
              ("score", gaps.cmd_score, "gates, rubric and sensitivity"),
              ("prisma", report.cmd_prisma, "PRISMA-style flow counts")]
    for name, fn, help_ in simple:
        s = sub.add_parser(name, help=help_)
        s.add_argument("run")
        s.set_defaults(func=fn)

    s = sub.add_parser("cards", help="gap-card utilities")
    s.add_argument("action", choices=["check"])
    s.add_argument("run")
    s.set_defaults(func=gaps.cmd_cards_check)

    s = sub.add_parser("validate", help="schema-check every artifact; --report also checks the dossier; --file checks one file")
    s.add_argument("run")
    s.add_argument("--report", action="store_true")
    s.add_argument("--file", help="validate only this file (path inside RUN); agents use it to self-check their output")
    s.add_argument("--schema", help="schema name when it cannot be inferred from the path")
    s.set_defaults(func=report.cmd_validate)

    s = sub.add_parser("compare", help="reproducibility metrics between two runs")
    s.add_argument("run_a")
    s.add_argument("run_b")
    s.add_argument("--out")
    s.set_defaults(func=report.cmd_compare)

    s = sub.add_parser("purge", help="delete snapshot bodies older than the retention period")
    s.add_argument("run")
    s.add_argument("--days", type=int)
    s.set_defaults(func=report.cmd_purge)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 1
    try:
        return args.func(args) or 0
    except CliError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return exc.code
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
