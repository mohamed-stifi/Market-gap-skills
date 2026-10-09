"""Pseudonymous author ids: ah_ + 16 hex of sha256(salt | platform | handle).

The salt lives in RUN/.salt and never leaves the run folder, so hashes can count distinct
authors without storing who they are (GDPR data minimisation).
"""

import hashlib
import os

from .common import CliError, p


def salt(run):
    path = p(run, ".salt")
    if not os.path.exists(path):
        raise CliError("missing %s; was the run created with `gapscan.py init`?" % path)
    with open(path) as fh:
        return fh.read().strip()


def author_hash(run, platform, handle):
    if handle is None or not str(handle).strip():
        return "unknown"
    raw = "%s|%s|%s" % (salt(run), str(platform).strip().lower(), str(handle).strip().lower())
    return "ah_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
