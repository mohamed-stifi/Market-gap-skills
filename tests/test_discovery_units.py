"""Targeted tests for discovery safeguards: false-saturation simulation, gated human approval,
protocol tamper detection, evidence-merge rejections, excluded sources and robots opt-outs."""

import contextlib
import io
import json
import os
import random
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISC = os.path.join(ROOT, "skills", "market-gap-discovery")
sys.path.insert(0, os.path.join(DISC, "scripts"))

import gapscan  # noqa: E402
from mgcore import hq  # noqa: E402
from mgcore.jsonio import read_jsonl, read_json, write_json, write_jsonl  # noqa: E402
from mgd import flow, net, privacy  # noqa: E402


def gs(*argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        code = gapscan.main([str(a) for a in argv])
    return code, buf.getvalue() + err.getvalue()


def new_run(tmp, name="example-translators", autonomy="autonomous"):
    run = os.path.join(tmp, name)
    gs("init", run, "--topic", "invoicing for freelance translators", "--seed", "3", "--autonomy", autonomy)
    ex = read_json(os.path.join(DISC, "assets", "templates", "protocol.example.json"))
    ex.update(run_id=name, seed=3, autonomy=autonomy)
    write_json(os.path.join(run, "protocol.json"), ex)
    write_json(os.path.join(run, "doctor.json"), {"families": {}})
    return run


def next_act(run):
    try:
        flow.decide(run)
    except flow.Act as a:
        return a
    raise AssertionError("no action")


class SaturationSimulation(unittest.TestCase):
    """Correlated scouts that only reach easy-to-find products make raw overlap look complete.
    The estimators then pass, so the probe (a fresh persona and channel) must block the stop."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run = new_run(self.tmp)
        gs("protocol", "freeze", self.run)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write(self, units, found, probe=None):
        st = read_json(os.path.join(self.run, "state.json"))
        st["landscape"].update(round=2, merged=2, probe_count=1 if probe else 0, probe_round=2 if probe else None)
        write_json(os.path.join(self.run, "state.json"), st)
        write_json(os.path.join(self.run, "landscape", "units.json"), units)
        ents = []
        for pid, us in sorted(found.items()):
            ents.append({"entity_id": "dom:%s.io" % pid, "kind": "product", "names": [pid], "urls": [], "aliases": [],
                         "found_in_units": sorted(us), "found_via": ["sampling"], "first_round": 1, "first_group": "landscape-R01",
                         "status": "included", "screening": {}, "verified": {"status": "ok"}})
        write_jsonl(os.path.join(self.run, "landscape", "entities.jsonl"), ents)

    def test_probe_blocks_false_saturation(self):
        rng = random.Random(42)
        easy = ["easy%03d" % i for i in range(50)]
        hard = ["hard%03d" % i for i in range(150)]
        units = {}
        found = {}
        for r in (1, 2):
            for s in "ABC":
                for k in range(3 if r == 1 else 1):
                    uid = "R%02d-%s%d-web" % (r, s, k + 1)
                    units[uid] = {"scout": s, "family": "web", "kinds": ["product"], "round": r, "mode": "landscape", "group": "landscape-R%02d" % r}
                    for pid in easy:  # correlated scouts: same engine, same easy products
                        if rng.random() < 0.9:
                            found.setdefault(pid, set()).add(uid)
        self._write(units, found)
        gs("saturation", self.run)
        sat = read_json(os.path.join(self.run, "landscape", "saturation.json"))
        self.assertEqual(sat["verdict"], "NEEDS_PROBE", sat["reasons"])  # raw overlap looks complete
        units["PROBE-1-hn"] = {"scout": "P", "family": "hn", "kinds": ["product"], "round": 2, "mode": "probe", "group": "probe-1"}
        for pid in rng.sample(hard, 20) + rng.sample(easy, 5):
            found.setdefault(pid, set()).add("PROBE-1-hn")
        self._write(units, found, probe=True)
        gs("saturation", self.run)
        sat = read_json(os.path.join(self.run, "landscape", "saturation.json"))
        self.assertGreater(sat["probe"]["new_share"], 0.5)
        self.assertEqual(sat["verdict"], "EXPAND")  # the probe blocks the false stop


class LexiconKeys(unittest.TestCase):
    def test_term_keys_normalise_case_plurals_order_and_stopwords(self):
        from mgd.lexicon import term_key
        self.assertEqual(term_key("Late Payments"), term_key("payment, late"))
        self.assertEqual(term_key("the late payment"), term_key("late payment"))
        self.assertEqual(term_key("invoices"), term_key("invoice"))
        self.assertEqual(term_key("agencies"), term_key("agency"))
        self.assertNotEqual(term_key("invoice"), term_key("invoicing"))


class QueryBlocks(unittest.TestCase):
    """Regression tests for defects a live PRESS review found: alphabetical tie-breaking decided what
    was searched, curated terms never reached a block, doubled words, an unused facet."""

    def _lex(self):
        f = lambda terms, by: [{"term": t, "found_by": by, "first_round": 1} for t in terms]  # noqa: E731
        return {"facets": {
            "segment": f(["aaa generic segment", "abc self-employed"], ["R01-A"]) + f(["freelance translator"], ["PRESS"]),
            "job": f(["chase unpaid invoices"], ["R01-A", "R01-B"]) + f(["add mention"], ["R01-C"]),
            "category": f(["invoicing software"], ["R01-A"]), "tool": f(["invoice ninja"], ["R01-B"]),
            "pain": f(["late payment"], ["R01-A"]), "workaround": f(["spreadsheet"], ["R01-C"]),
            "other": f(["per word rate"], ["R01-B"])}}

    def test_curated_and_consensus_terms_rank_first(self):
        from mgd.lexicon import build_blocks
        proto = {"topic": "invoicing for freelance translators", "variation_dimensions": {"segment": []}}
        blocks = build_blocks(self._lex(), proto, seed=1)
        first_seg = [b["facets"]["segment"] for b in blocks if b["template"] == "cat-seg"][0]
        self.assertEqual(first_seg, "freelance translator")
        first_job = [b["facets"]["job"] for b in blocks if b["template"] == "howto-job"][0]
        self.assertEqual(first_job, "chase unpaid invoices")

    def test_no_doubled_words_and_other_facet_used(self):
        from mgd.lexicon import build_blocks
        blocks = build_blocks(self._lex(), {}, seed=1)
        self.assertFalse([b for b in blocks if re.search(r"\b(\w+)\s+\1\b", b["query"], re.I)])
        self.assertTrue(any("per word rate" in b["query"] for b in blocks))
        self.assertTrue(any(b["template"] == "seg-workaround" for b in blocks))


class ReliabilitySample(unittest.TestCase):
    """A random reliability sample measured 3 of 38 eligible codes in a live run; the stratified top-up fixes that."""

    def setUp(self):
        import random
        from mgd.assign import reliability_sample
        self.sample, self.random = reliability_sample, random
        # 100 records: COMMON on every 2nd, RARE on 6 records, TOORARE on 3 records
        self.codes = {"EV-%03d" % i: set() for i in range(100)}
        for i in range(0, 100, 2):
            self.codes["EV-%03d" % i].add("COMMON")
        for i in (7, 23, 41, 59, 77, 95):
            self.codes["EV-%03d" % i].add("RARE")
        for i in (11, 13, 17):
            self.codes["EV-%03d" % i].add("TOORARE")

    def positives(self, ids, code):
        return sum(1 for e in ids if code in self.codes[e])

    def test_core_plus_stratified_topup(self):
        new = self.sample(list(self.codes), self.codes, set(), 5, 20, 60, self.random.Random(1))
        self.assertGreaterEqual(len(new), 20)
        self.assertGreaterEqual(self.positives(new, "RARE"), 5)
        self.assertGreaterEqual(self.positives(new, "COMMON"), 5)
        self.assertLess(self.positives(new, "TOORARE"), 3 + 1)  # never targeted: below `need` in the whole pool

    def test_topup_skips_done_records_and_respects_cap(self):
        done = set("EV-%03d" % i for i in range(0, 40))  # B coded 40 records, holding RARE twice (EV-007, EV-023)
        new = self.sample(list(self.codes), self.codes, done, 5, 20, 60, self.random.Random(1))
        self.assertFalse(set(new) & done)
        self.assertEqual(self.positives(set(new) | done, "RARE"), 5)
        self.assertEqual(len(new), 3)  # no new random core once B has started: only what the targets need
        capped = self.sample(list(self.codes), self.codes, set(), 5, 20, 3, self.random.Random(1))
        self.assertEqual(len(capped), 3)

    def test_near_universal_code_gets_negatives(self):
        codes = {e: {"NEARALL"} for e in self.codes}
        for i in range(90, 96):
            codes["EV-%03d" % i] = set()  # only 6 records lack the code
        done = set("EV-%03d" % i for i in range(0, 40))  # all positives: alpha would be undefined
        new = self.sample(list(codes), codes, done, 5, 20, 60, self.random.Random(1))
        self.assertEqual(sum(1 for e in new if not codes[e]), 5)


class NameMatching(unittest.TestCase):
    """Real false negatives from a live run: products whose page names them slightly differently."""

    def test_tolerant_name_matching(self):
        from mgd.entities import _name_found
        self.assertTrue(_name_found(["AIR - Automated Invoice Reminder"], "AIR-Automated Invoice Reminder - Apps on Google Play", "app:android:x"))
        self.assertTrue(_name_found(["Zap-Bill"], "Free Invoice Generator & Invoice Maker | Zap Bill", "dom:zap-bill.com"))
        self.assertTrue(_name_found(["Square Invoices"], "Power your entire business | Square", "dom:squareup.com"))
        self.assertTrue(_name_found(["GetPaid \u2013 Payment forms, Buy now buttons"], "Payment forms | GetPaid", "wp:invoicing"))
        self.assertTrue(_name_found(["Invoice Maker\u30fbBilling App"], "Saldo Apps - Your Cloud Bookkeeping", "dom:saldoapps.com"))
        self.assertFalse(_name_found(["Bravo Billing"], "Welcome to our cooking blog", "dom:unrelated.com"))
        # a generic first word alone is not a match
        self.assertFalse(_name_found(["Invoice Maker (Workly)"], "A different invoice tool for teams", "app:ios:1"))


class ShortReads(unittest.TestCase):
    def test_read_all_loops_over_short_reads(self):
        class Stream(object):
            def __init__(self, data):
                self.data = data
            def read(self, n):
                n = min(n, 1000)  # the socket hands over at most 1000 bytes per call
                chunk, self.data = self.data[:n], self.data[n:]
                return chunk
        self.assertEqual(len(net._read_all(Stream(b"x" * 83974), 6 * 1024 * 1024)), 83974)
        self.assertEqual(len(net._read_all(Stream(b"x" * 5000), 3000)), 3001)  # capped at max_bytes + 1


class Redirects(unittest.TestCase):
    def test_308_is_followed_like_307(self):
        import urllib.request
        req = urllib.request.Request("https://old.example.org/page", headers={"User-Agent": "x"})
        new = net._Redirect().redirect_request(req, None, 308, "Permanent Redirect", {}, "https://new.example.org/page")
        self.assertIsNotNone(new)
        self.assertEqual(new.full_url, "https://new.example.org/page")


class YcTerms(unittest.TestCase):
    def test_stopwords_short_tokens_and_whole_words(self):
        from mgd.fetch.apis import _yc_terms, _yc_words
        self.assertEqual(_yc_terms("invoice generator for literary translators"), ["generator", "invoice", "literary", "translator"])
        self.assertNotIn("per", _yc_terms("price per word"))
        self.assertFalse(_yc_words("personal-finance") & set(_yc_terms("rate per word")))  # no substring matches
        self.assertTrue(_yc_words("payments") & set(_yc_terms("payment reminders")))


class GatedFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run = new_run(self.tmp, autonomy="gated")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_protocol_gate_approve_decline_revise(self):
        act = next_act(self.run)
        self.assertEqual(act.verdict, "BLOCKED")
        task_id = act.argline
        self.assertEqual(gs("protocol", "freeze", self.run)[0], 2)  # cannot freeze before approval
        hq.close(self.run, task_id, "declined", "Narrow the scope to EU clients")
        act = next_act(self.run)
        self.assertEqual(act.verdict, "DO")
        self.assertIn("Narrow the scope", act.argline)
        proto = read_json(os.path.join(self.run, "protocol.json"))
        proto["geography"] = ["EU"]
        write_json(os.path.join(self.run, "protocol.json"), proto)
        act = next_act(self.run)
        self.assertEqual(act.verdict, "BLOCKED")
        self.assertNotEqual(act.argline, task_id)  # a new approval request
        hq.close(self.run, act.argline, "done", "ok")
        act = next_act(self.run)
        self.assertEqual((act.verdict, act.argline.split()[1]), ("RUN", "protocol"))
        self.assertEqual(gs("protocol", "freeze", self.run)[0], 0)


class Integrity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run = new_run(self.tmp)
        gs("protocol", "freeze", self.run)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_tampering_after_freeze_is_detected(self):
        proto = read_json(os.path.join(self.run, "protocol.json"))
        proto["recency_days"] = 99
        write_json(os.path.join(self.run, "protocol.json"), proto)
        act = next_act(self.run)
        self.assertEqual(act.verdict, "DO")
        self.assertIn("changed after freezing", act.argline)

    def test_amendment_is_logged(self):
        code, _ = gs("protocol", "amend", self.run, "--reason", "human directive: focus on EU", "--set", 'geography=["EU"]')
        self.assertEqual(code, 0)
        lock = read_json(os.path.join(self.run, "protocol.lock.json"))
        self.assertEqual(len(lock["amendments"]), 1)
        self.assertEqual(lock["amendments"][0]["reason"], "human directive: focus on EU")

    def test_author_hash_format_and_stability(self):
        h1 = privacy.author_hash(self.run, "hn", "JaneDoe")
        h2 = privacy.author_hash(self.run, "hn", "janedoe ")
        self.assertRegex(h1, r"^ah_[0-9a-f]{16}$")
        self.assertEqual(h1, h2)
        self.assertEqual(privacy.author_hash(self.run, "hn", ""), "unknown")

    def test_excluded_sources_and_ai_robots_optout(self):
        self.assertIsNotNone(net.excluded_reason("https://www.g2.com/products/x/reviews"))
        self.assertIsNotNone(net.excluded_reason("https://play.google.com/store/getreviews?id=1"))
        self.assertIsNone(net.excluded_reason("https://play.google.com/store/apps/details?id=x"))
        self.assertIsNone(net.excluded_reason("https://news.ycombinator.com/item?id=1"))
        with self.assertRaises(net.Blocked):
            net.get(self.run, "https://www.capterra.com/p/1/x/reviews")
        cache = os.path.join(self.run, "cache", "robots", "blog.example.com.json")
        import time
        write_json(cache, {"fetched_epoch": time.time(), "status": 200,
                           "body": "User-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"})
        self.assertFalse(net.robots_allowed(self.run, "https://blog.example.com/post"))
        write_json(cache, {"fetched_epoch": time.time(), "status": 503, "body": ""})
        self.assertFalse(net.robots_allowed(self.run, "https://blog.example.com/post"))  # RFC 9309: 5xx = disallow all
        write_json(cache, {"fetched_epoch": time.time(), "status": 404, "body": ""})
        self.assertTrue(net.robots_allowed(self.run, "https://blog.example.com/post"))  # 4xx = allow

    def test_user_agent_contact_only_from_env(self):
        os.environ.pop("MGD_CONTACT", None)
        self.assertEqual(net.user_agent(), "market-gap-discovery/1.0")
        os.environ["MGD_CONTACT"] = "https://example.org/contact"
        try:
            self.assertIn("https://example.org/contact", net.user_agent())
        finally:
            os.environ.pop("MGD_CONTACT", None)

    def test_evidence_merge_rejects_bad_records(self):
        st = read_json(os.path.join(self.run, "state.json"))
        sha = "a" * 64
        os.makedirs(os.path.join(self.run, "snapshots"), exist_ok=True)
        with open(os.path.join(self.run, "snapshots", sha + ".raw"), "w") as fh:
            fh.write("x")
        write_json(os.path.join(self.run, "snapshots", sha + ".meta.json"), {"fetched_at": "2026-10-09T00:00:00+00:00"})
        rel = "evidence/round-01/miner-A.jsonl"
        good = {"url": "https://forum.example.org/t/1", "source": "web", "source_type": "forum", "snapshot": sha,
                "quote": "I chase every late payment by hand", "stance": "pain", "strength": "S2",
                "credibility": "independent", "author_hash": "ah_0123456789abcdef",
                "entity_ids": ["dom:known-product.com", "dom:missing-product.com"]}
        os.makedirs(os.path.join(self.run, "landscape"), exist_ok=True)
        write_jsonl(os.path.join(self.run, "landscape", "entities.jsonl"),
                    [{"entity_id": "app:ios:1", "aliases": ["dom:known-product.com"], "status": "included", "kind": "product"}])
        bad = [dict(good, author="janedoe"),
               dict(good, url="https://www.g2.com/products/x/reviews", quote="another quote here for g2"),
               dict(good, snapshot="b" * 64, quote="snapshot does not exist here"),
               dict(good, quote="thanks @janedoe for the tip about chasing invoices"),
               dict(good, quote="x" * 300)]
        write_jsonl(os.path.join(self.run, rel), [good] + bad + [good])
        apath = "evidence/round-01/assign-A.json"
        write_json(os.path.join(self.run, apath), {"assignment_id": "EV-R01-A", "scout_id": "A",
                                                   "outputs": [{"path": rel, "schema": "evidence", "format": "jsonl"}]})
        st["evidence"]["round"] = 1
        st.setdefault("groups", {})["evidence-R01"] = {"phase": "evidence", "role": "miner", "paths": [apath], "merged": False}
        write_json(os.path.join(self.run, "state.json"), st)
        code, out_ = gs("merge", self.run, "--phase", "evidence")
        self.assertEqual(code, 0, out_)
        self.assertIn("1 accepted, 1 duplicates, 5 rejected", out_)
        self.assertIn("Post-landscape discoveries: 1 product key(s) named in evidence are not in the landscape (dom:missing-product.com)", out_)
        led = read_jsonl(os.path.join(self.run, "evidence", "ledger.jsonl"))[0]
        self.assertEqual(led[0]["entity_ids"], ["app:ios:1", "dom:missing-product.com"])  # alias stored as its primary id

    def test_revision_gets_disagreements_and_pooled_proposals(self):
        recs = [{"id": "EV-%06d" % i, "quote": "quote number %d about invoices" % i, "stance": "pain", "source_type": "forum",
                 "url": "https://forum.example.org/t/%d" % i, "strength": "S2", "entity_ids": [],
                 "verification": {"status": "verified"}} for i in range(1, 13)]
        os.makedirs(os.path.join(self.run, "evidence"), exist_ok=True)
        write_jsonl(os.path.join(self.run, "evidence", "ledger.jsonl"), recs)
        prop = {"label": "Let clients pay online", "definition": "Clients pay an invoice through a payment link"}
        a = [{"evidence_id": r["id"], "coder": "A", "codebook_version": 1, "codes": ["F-HABIT"] if i % 2 else [],
              "strength": "S2", "intensity": 1, "new_code_proposals": [prop] if i < 6 else []} for i, r in enumerate(recs)]
        b = [{"evidence_id": r["id"], "coder": "B", "codebook_version": 1, "codes": ["F-HABIT"] if i % 3 == 0 else [],
              "strength": "S2", "intensity": 1, "new_code_proposals": [prop] if i in (0, 7) else []} for i, r in enumerate(recs)]
        write_jsonl(os.path.join(self.run, "coding", "codes-A.jsonl"), a)
        write_jsonl(os.path.join(self.run, "coding", "codes-B.jsonl"), b)
        write_json(os.path.join(self.run, "coding", "agreement.json"),
                   {"verdict": "revise", "weak_codes": ["F-HABIT"], "provisional_codes": [], "codes": {"F-HABIT": {"alpha": 0.4, "status": "revise"}}})
        st = read_json(os.path.join(self.run, "state.json"))
        st["coding"]["version"] = 1
        write_json(os.path.join(self.run, "state.json"), st)
        code, out_ = gs("assign", self.run, "--phase", "coding-open", "--revise")
        self.assertEqual(code, 0, out_)
        inputs = read_json(os.path.join(self.run, "coding", "open-assign-v2.json"))["inputs"]
        self.assertEqual(inputs["codes_to_revise"][0]["code"], "F-HABIT")
        self.assertTrue(inputs["disagreements"])
        self.assertTrue(all(d["coder_a"] != d["coder_b"] and d["quote"] for d in inputs["disagreements"]))
        top = inputs["proposals"][0]
        self.assertEqual((top["label"], top["count"], top["coders"], top["eligible"]), ("Let clients pay online", 7, ["A", "B"], True))

    def test_revision_sharpens_standard_codes_and_holds_out_examples(self):
        from mgd.assign import held_out_ids
        cpath = lambda *x: os.path.join(self.run, "coding", *x)
        own = [{"id": "J-SEND", "type": "job", "label": "Send invoices", "definition": "Sending invoices to clients.",
                "include": "Any sending.", "exclude": "Drafts.", "examples": ["EV-000001"]},
               {"id": "P-LATE", "type": "pain", "label": "Late payment", "definition": "Clients pay after the due date.",
                "include": "Paid late.", "exclude": "On time."}]
        os.makedirs(cpath(), exist_ok=True)
        write_json(cpath("codebook.json"), {"version": 1, "codes": own})
        self.assertEqual(gs("codebook", "freeze", self.run)[0], 0)
        habit = [x for x in read_json(cpath("codebook.v1.json"))["codes"] if x["id"] == "F-HABIT"][0]

        def revision(v, draft_codes, targets, notes=""):
            write_json(cpath("open-assign-v%d.json" % v), {"outputs": [{"path": "coding/codebook-draft-v%d.json" % v}],
                                                           "inputs": {"codes_to_revise": [{"code": t} for t in targets]}})
            write_json(cpath("codebook-draft-v%d.json" % v), {"version": v, "codes": draft_codes, "notes": notes})
            return gs("codebook", "freeze", self.run)

        code, out_ = revision(2, own, ["F-HABIT"])  # nothing listed changed: refused
        self.assertNotEqual(code, 0)
        self.assertIn("unchanged", out_)
        sharp = dict(habit, include="Praise of the current way as a reason to stay.", label="ignored", examples=["EV-000002"])
        self.assertEqual(revision(2, own + [sharp], ["F-HABIT"], notes="R1: see EV-000003.")[0], 0)
        v2 = {x["id"]: x for x in read_json(cpath("codebook.v2.json"))["codes"]}
        self.assertEqual(v2["F-HABIT"]["include"], "Praise of the current way as a reason to stay.")
        self.assertEqual(v2["F-HABIT"]["label"], habit["label"])  # fixed fields stay fixed
        self.assertIn("F-HABIT", read_json(cpath("codebook.lock.json"))["changes"]["changed"])
        self.assertEqual(held_out_ids(self.run, 2), {"EV-000001", "EV-000002", "EV-000003"})
        own3 = [dict(own[1], include="Paid after the due date, as the author states.")] + own[:1]
        self.assertEqual(revision(3, own3, ["P-LATE"])[0], 0)
        v3 = {x["id"]: x for x in read_json(cpath("codebook.v3.json"))["codes"]}
        self.assertEqual(v3["F-HABIT"]["include"], "Praise of the current way as a reason to stay.")  # carried forward

    def test_freeze_enforces_the_own_code_limit(self):
        many = [{"id": "J-TASK-%02d" % i, "type": "job", "label": "Task %d" % i, "definition": "Doing task number %d." % i,
                 "include": "Mentions it.", "exclude": "Does not."} for i in range(41)]
        os.makedirs(os.path.join(self.run, "coding"), exist_ok=True)
        write_json(os.path.join(self.run, "coding", "codebook.json"), {"version": 1, "codes": many})
        code, out_ = gs("codebook", "freeze", self.run)
        self.assertNotEqual(code, 0)
        self.assertIn("max_own_codes", out_)

    def test_empty_202_is_a_bot_challenge(self):
        orig = net._raw_get
        net._raw_get = lambda url, timeout=20, headers=None, max_bytes=None: (202, url, "text/html", b"", None)
        try:
            with self.assertRaises(net.Blocked):
                net.get(self.run, "https://shop.example.com/pricing", robots=False, min_interval=0)
        finally:
            net._raw_get = orig
        with open(os.path.join(self.run, "coverage-gaps.jsonl")) as fh:
            self.assertIn("bot challenge", fh.read())


if __name__ == "__main__":
    unittest.main()
