"""Shared helpers for gapscan.py commands: paths, config, schemas, run access."""

import glob
import os
import sys

from mgcore import canon, config, schema, state
from mgcore.jsonio import read_json, read_jsonl

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.dirname(SCRIPTS_DIR)
ASSETS = os.path.join(SKILL_DIR, "assets")
SCHEMAS = os.path.join(ASSETS, "schemas")

EXIT_OK, EXIT_USAGE, EXIT_BLOCKED, EXIT_BUDGET = 0, 1, 2, 3

_REGISTRY = None


class CliError(Exception):
    def __init__(self, message, code=EXIT_USAGE):
        Exception.__init__(self, message)
        self.code = code


def registry():
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = schema.SchemaRegistry(SCHEMAS)
    return _REGISTRY


def validate(doc, schema_name):
    return schema.validate(doc, registry().load(schema_name), registry())


def p(run, *parts):
    return os.path.join(run, *parts)


def rel(run, path):
    return os.path.relpath(path, run)


def require_run(run):
    if not os.path.exists(p(run, "state.json")):
        raise CliError("%s is not a run folder (no state.json). Create one with `gapscan.py init RUN --topic ...`." % run)


def protocol(run):
    return read_json(p(run, "protocol.json"), {}) or {}


def cfg(run):
    return config.Config(os.path.join(ASSETS, "defaults.json"), protocol(run))


def load_state(run):
    return state.load(run)


def save_state(run, st):
    state.save(run, st)


def psl(run):
    return canon.PublicSuffix.load(p(run, "cache", "public_suffix_list.dat"), os.path.join(ASSETS, "psl-mini.txt"))


def channels():
    return read_json(os.path.join(ASSETS, "channels.json"), {})


def personas():
    return read_json(os.path.join(ASSETS, "personas.json"), {}).get("personas", [])


def methods():
    return {c["id"]: c for c in read_json(os.path.join(ASSETS, "methods.json"), {}).get("cards", [])}


def card_paths(*ids):
    m = methods()
    return [m[i]["file"] for i in ids if i in m]


def jsonl(path):
    recs, errs = read_jsonl(path)
    if errs:
        raise CliError("%s has invalid JSON on line(s) %s" % (path, ", ".join(str(n) for n, _ in errs[:5])))
    return recs


def entities(run):
    return read_jsonl(p(run, "landscape", "entities.jsonl"))[0]


def alias_map(run):
    """Every entity key, primary id or alias, mapped to the entity's primary id. Landscape merges join an
    app and its website into one entity; evidence may cite either key."""
    m = {}
    for e in entities(run):
        m[e["entity_id"]] = e["entity_id"]
        for a in e.get("aliases") or []:
            m.setdefault(a, e["entity_id"])
    return m


def resolve_ids(ids, amap):
    """Primary ids for a record's entity_ids, de-duplicated, order kept; unknown keys pass through."""
    out_ = []
    for x in ids or []:
        y = amap.get(x, x)
        if y not in out_:
            out_.append(y)
    return out_


def ledger(run):
    return read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]


def verified_ledger(run):
    return [r for r in ledger(run) if r.get("verification", {}).get("status") == "verified"]


def codebook(run):
    return read_json(p(run, "coding", "codebook.json"))


def frozen_codebook(run):
    lock = read_json(p(run, "coding", "codebook.lock.json"))
    if not lock:
        return None
    return read_json(p(run, "coding", "codebook.v%d.json" % lock["version"]))


def files(pattern):
    return sorted(glob.glob(pattern))


def out(msg=""):
    sys.stdout.write(msg + "\n")


def warn(msg):
    sys.stderr.write("warning: " + msg + "\n")


def included_verified(ents):
    return [e for e in ents if e.get("status") == "included" and e.get("verified", {}).get("status") == "ok"]
