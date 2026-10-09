#!/usr/bin/env python3
"""gapval.py: deterministic backbone of the market-gap-validation skill.

Designs are pre-registered and frozen, outward actions are human tasks, and verdicts come from
frozen decision rules. Start with `gapval.py init RUN` and follow `gapval.py next RUN`.
Full reference: references/cli.md. Standard library only (Python 3.8+).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mgv import assets, assign, data, flow, framing, prereg, setup, verdict  # noqa: E402
from mgv.common import CliError  # noqa: E402


def build_parser():
    ap = argparse.ArgumentParser(prog="gapval.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command")

    s = sub.add_parser("init", help="start validation from a discovery handoff or a standalone idea")
    s.add_argument("run")
    s.add_argument("--handoff")
    s.add_argument("--gap")
    s.add_argument("--idea")
    s.add_argument("--autonomy", choices=["autonomous", "gated"], default="autonomous")
    s.set_defaults(func=setup.cmd_init)

    for name, fn, help_ in (("next", flow.cmd_next, "print the single next action"), ("status", flow.cmd_status, "summarise validation")):
        s = sub.add_parser(name, help=help_)
        s.add_argument("run")
        s.add_argument("--json", action="store_true")
        s.set_defaults(func=fn)

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
    s.set_defaults(func=assign.cmd_assign)

    s = sub.add_parser("ost", help="Opportunity Solution Tree utilities")
    s.add_argument("action", choices=["check"])
    s.add_argument("run")
    s.set_defaults(func=framing.cmd_ost)

    s = sub.add_parser("assumptions", help="assumption mapping")
    s.add_argument("action", choices=["rank"])
    s.add_argument("run")
    s.set_defaults(func=framing.cmd_assumptions)

    s = sub.add_parser("samplesize", help="n = ceil(z^2 p(1-p) / h^2)")
    s.add_argument("--p", type=float, required=True)
    s.add_argument("--h", type=float, required=True)
    s.add_argument("--z", type=float, default=1.96)
    s.set_defaults(func=framing.cmd_samplesize)

    s = sub.add_parser("prereg", help="draft, check, freeze or verify Test Cards")
    s.add_argument("action", choices=["new", "check", "freeze", "verify"])
    s.add_argument("run")
    s.add_argument("experiment_id", nargs="?")
    s.add_argument("--experiment")
    s.add_argument("--type", choices=sorted(prereg.TYPE_DEFAULTS))
    s.add_argument("--assumption")
    s.set_defaults(func=prereg.cmd_prereg)

    s = sub.add_parser("utm", help="tracked links per channel")
    s.add_argument("run")
    s.add_argument("--experiment", required=True)
    s.add_argument("--base-url", required=True)
    s.add_argument("--channels", required=True)
    s.set_defaults(func=assets.cmd_utm)

    s = sub.add_parser("assets", help="honesty and completeness checks for assets")
    s.add_argument("action", choices=["check"])
    s.add_argument("run")
    s.add_argument("experiment_id")
    s.set_defaults(func=assets.cmd_assets)

    s = sub.add_parser("ingest", help="ingest a human-provided export")
    s.add_argument("run")
    s.add_argument("--experiment", required=True)
    s.add_argument("--kind", required=True, choices=sorted(list(data.KIND_COLUMNS) + ["interviews"]))
    s.add_argument("--file", required=True)
    s.set_defaults(func=data.cmd_ingest)

    s = sub.add_parser("stats", help="apply an experiment's frozen decision rule")
    s.add_argument("run")
    s.add_argument("--experiment", required=True)
    s.set_defaults(func=data.cmd_stats)

    for name, fn, help_ in (("agreement", data.cmd_agreement, "interview coding agreement"),
                            ("themes", data.cmd_themes, "interview theme saturation"),
                            ("verdict", verdict.cmd_verdict, "GO / ITERATE / PIVOT / KILL"),
                            ("validate", verdict.cmd_validate, "schema and consistency checks")):
        s = sub.add_parser(name, help=help_)
        s.add_argument("run")
        s.set_defaults(func=fn)
    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 1
    if getattr(args, "experiment", None) and getattr(args, "experiment_id", None) is None and args.command == "prereg":
        args.experiment_id = args.experiment
    try:
        return args.func(args) or 0
    except CliError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
