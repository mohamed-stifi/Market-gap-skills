"""Shared helpers for gapval.py commands."""

import glob
import os
import sys

from mgcore import config, schema, state
from mgcore.jsonio import read_json

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
ASSETS = os.path.join(SKILL_DIR, "assets")
SCHEMAS = os.path.join(ASSETS, "schemas")
EXIT_OK, EXIT_USAGE, EXIT_BLOCKED, EXIT_BUDGET = 0, 1, 2, 3
_REG = None


class CliError(Exception):
    def __init__(self, message, code=EXIT_USAGE):
        Exception.__init__(self, message)
        self.code = code


def registry():
    global _REG
    if _REG is None:
        _REG = schema.SchemaRegistry(SCHEMAS)
    return _REG


def validate(doc, name):
    return schema.validate(doc, registry().load(name), registry())


def v(run, *parts):
    return os.path.join(run, "validation", *parts)


def p(run, *parts):
    return os.path.join(run, *parts)


def cfg():
    return config.Config(os.path.join(ASSETS, "defaults.json"), {})


def require(run):
    if not os.path.exists(v(run, "state.json")):
        raise CliError("no validation state in %s; run `gapval.py init %s` first" % (run, run))


def load_state(run):
    return state.load(run, "validation")


def save_state(run, st):
    state.save(run, st, "validation")


def touch(run, st, name):
    state.touch(st, name)
    save_state(run, st)


def cards(run):
    out_ = {}
    for path in sorted(glob.glob(v(run, "prereg", "EXP-*.json"))):
        if path.endswith(".lock.json"):
            continue
        doc = read_json(path)
        if doc and doc.get("id"):
            out_[doc["id"]] = doc
    return out_


def ost(run):
    return read_json(v(run, "ost.json"))


def target_assumptions(run):
    o = ost(run) or {}
    for s in o.get("solutions", []):
        if s["id"] == o.get("target_solution"):
            return {a["id"]: a for a in s["assumptions"]}
    return {}


def out(msg=""):
    sys.stdout.write(msg + "\n")
