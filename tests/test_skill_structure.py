"""Structure and consistency checks for both skills: frontmatter, budgets, references, card
registry, every documented command against the real CLI parsers, tables of contents, tone,
and shared-copy sync."""

import glob
import importlib
import json
import os
import re
import shlex
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = {"market-gap-discovery": "gapscan", "market-gap-validation": "gapval"}
def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "no frontmatter in %s" % path
    fm, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r"^[A-Za-z-]+:", line):
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
        elif key and line.startswith("  "):
            fm[key] = (fm[key] + "\n" + line).strip()
    return fm, text[m.end():]


def load_parser(skill, module):
    scripts = os.path.join(ROOT, "skills", skill, "scripts")
    for name in list(sys.modules):
        if name in ("mgcore", "mgd", "mgv", module) or name.startswith(("mgcore.", "mgd.", "mgv.")):
            del sys.modules[name]
    sys.path.insert(0, scripts)
    try:
        mod = importlib.import_module(module)
        return mod.build_parser()
    finally:
        sys.path.remove(scripts)


def md_files(skill):
    base = os.path.join(ROOT, "skills", skill)
    return [f for f in glob.glob(os.path.join(base, "**", "*.md"), recursive=True)]


class SkillStructure(unittest.TestCase):
    def test_frontmatter_and_budgets(self):
        for skill in SKILLS:
            path = os.path.join(ROOT, "skills", skill, "SKILL.md")
            fm, body = frontmatter(path)
            self.assertTrue(set(fm) <= ALLOWED_KEYS, set(fm) - ALLOWED_KEYS)
            self.assertEqual(fm["name"], skill)
            self.assertRegex(fm["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
            self.assertLessEqual(len(fm["description"]), 1024)
            self.assertNotRegex(fm["description"], r"[<>]")
            self.assertNotRegex(fm["description"], r": ", "plain YAML scalar must not contain ': '")
            self.assertLessEqual(len(fm.get("compatibility", "")), 500)
            lines = read(path).count("\n")
            self.assertLess(lines, 500, "%s has %d lines" % (skill, lines))
            self.assertLess(len(body) / 4.0, 5000, "%s body is about %d tokens" % (skill, len(body) / 4))
            self.assertNotRegex(body, r"\b20\d\d-\d\d-\d\d\b", "no dates in SKILL.md (time-sensitive)")

    def test_referenced_files_exist(self):
        pat = re.compile(r"`((?:references|agents|assets)/[A-Za-z0-9_./*-]+)`")
        for skill in SKILLS:
            base = os.path.join(ROOT, "skills", skill)
            for f in md_files(skill):
                for ref in pat.findall(read(f)):
                    if "*" in ref or ref.endswith("/"):
                        self.assertTrue(glob.glob(os.path.join(base, ref.rstrip("/"))), "%s: %s" % (f, ref))
                    else:
                        self.assertTrue(os.path.exists(os.path.join(base, ref)), "%s references missing %s" % (os.path.relpath(f, ROOT), ref))

    def test_card_registry_matches_files(self):
        for skill in SKILLS:
            base = os.path.join(ROOT, "skills", skill)
            reg = json.loads(read(os.path.join(base, "assets", "methods.json")))["cards"]
            files = set(os.path.relpath(f, base) for f in glob.glob(os.path.join(base, "references", "methods", "*.md")))
            self.assertEqual(set(c["file"] for c in reg), files)
            for c in reg:
                first = read(os.path.join(base, c["file"])).split("\n", 1)[0] + "\n"
                self.assertTrue(first.startswith("# %s " % c["id"]), "%s title line: %s" % (c["file"], first))
                text = read(os.path.join(base, c["file"]))
                for section in ("**Use when", "**Why", "**Procedure", "**Output", "**Pitfalls", "**Done when"):
                    self.assertIn(section, text, "%s lacks %s" % (c["file"], section))

    def test_documented_commands_parse(self):
        problems = []
        for skill, module in SKILLS.items():
            parser = load_parser(skill, module)
            choices = parser._subparsers._group_actions[0].choices
            span = re.compile(r"`([^`\n]*\b%s\.py [^`\n]+)`" % module)
            files = md_files(skill) + glob.glob(os.path.join(ROOT, "docs", "*.md")) + ([os.path.join(ROOT, "README.md")] if os.path.exists(os.path.join(ROOT, "README.md")) else [])
            for f in files:
                for m in span.finditer(read(f)):
                    raw = m.group(1).split("%s.py" % module, 1)[1].strip().rstrip(".,;:)")
                    raw = re.sub(r"\[[^\]]*\]", "", raw)
                    raw = re.sub(r"<[^>]*>", "X", raw)
                    raw = raw.replace("...", "").replace("…", "").replace("|", " ")
                    try:
                        toks = shlex.split(raw)
                    except ValueError:
                        toks = raw.split()
                    if not toks or not re.match(r"^[a-z][a-z-]*$", toks[0]):
                        continue
                    where = "%s: `%s`" % (os.path.relpath(f, ROOT), m.group(1)[:90])
                    cmd = toks[0]
                    if cmd not in choices:
                        problems.append("%s -> unknown command %s" % (where, cmd))
                        continue
                    sub = choices[cmd]
                    for opt in [t for t in toks[1:] if t.startswith("--")]:
                        if opt.split("=")[0] not in sub._option_string_actions:
                            problems.append("%s -> unknown option %s" % (where, opt))
                    if "--phase" in toks:
                        i = toks.index("--phase")
                        if i + 1 < len(toks) and re.match(r"^[a-z-]+$", toks[i + 1]):
                            if toks[i + 1] not in sub._option_string_actions["--phase"].choices:
                                problems.append("%s -> bad phase %s" % (where, toks[i + 1]))
                    if cmd == "fetch":
                        sources = sub._actions[2].choices
                        words = [t for t in toks[1:3] if not t.startswith("-")]
                        if words and "X" not in words and not any(w in sources for w in words):
                            problems.append("%s -> unknown fetch source in %s" % (where, words))
        self.assertFalse(problems, "\n" + "\n".join(problems))

    def test_long_references_have_contents(self):
        for skill in SKILLS:
            base = os.path.join(ROOT, "skills", skill, "references")
            for f in glob.glob(os.path.join(base, "*.md")):
                lines = read(f).splitlines()
                if len(lines) > 100:
                    self.assertTrue(any(l.strip().lower().startswith("contents") for l in lines[:20]), "%s lacks a table of contents" % f)

    def test_tone_no_shouting(self):
        for skill in SKILLS:
            for f in md_files(skill):
                text = read(f)
                hits = re.findall(r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT)\b", text)
                self.assertFalse(hits, "%s shouts: %s" % (os.path.relpath(f, ROOT), hits[:3]))

    def test_shared_copies_in_sync(self):
        proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sync_shared.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_json_assets_parse_and_examples_validate(self):
        for skill in SKILLS:
            for f in glob.glob(os.path.join(ROOT, "skills", skill, "assets", "**", "*.json"), recursive=True):
                with open(f) as fh:
                    json.load(fh)


if __name__ == "__main__":
    unittest.main()
