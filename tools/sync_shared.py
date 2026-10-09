#!/usr/bin/env python3
"""Copy the single source of truth in shared/ into each skill so every skill is
self-contained when installed alone.

  shared/mgcore/*.py            -> skills/<skill>/scripts/mgcore/
  shared/schemas/*.schema.json  -> skills/<skill>/assets/schemas/
  shared/references/glossary.md -> skills/<skill>/references/glossary.md

Run after editing anything in shared/. tests/test_skill_structure.py fails when copies drift.
Usage: python3 tools/sync_shared.py [--check]
"""

import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = ["market-gap-discovery", "market-gap-validation"]


def pairs():
    out = []
    src_core = os.path.join(ROOT, "shared", "mgcore")
    src_schemas = os.path.join(ROOT, "shared", "schemas")
    for skill in SKILLS:
        base = os.path.join(ROOT, "skills", skill)
        for name in sorted(os.listdir(src_core)):
            if name.endswith(".py"):
                out.append((os.path.join(src_core, name), os.path.join(base, "scripts", "mgcore", name)))
        for name in sorted(os.listdir(src_schemas)):
            if name.endswith(".schema.json"):
                out.append((os.path.join(src_schemas, name), os.path.join(base, "assets", "schemas", name)))
        out.append((os.path.join(ROOT, "shared", "references", "glossary.md"),
                    os.path.join(base, "references", "glossary.md")))
    return out


def main(argv):
    check = "--check" in argv
    drift = []
    for src, dst in pairs():
        same = os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False)
        if same:
            continue
        if check:
            drift.append(os.path.relpath(dst, ROOT))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print("synced", os.path.relpath(dst, ROOT))
    if check and drift:
        print("out of sync:\n  " + "\n  ".join(drift))
        return 1
    if check:
        print("shared copies are in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
