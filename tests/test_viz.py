"""Tests for the viz step: charts, the offline HTML dashboard and the plain-language summary are built
from a small synthetic run; charts whose inputs are missing are skipped with a reason, never crash.
Skipped as a whole when matplotlib is not installed (core gapscan commands stay stdlib-only)."""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISC = os.path.join(ROOT, "skills", "market-gap-discovery")
sys.path.insert(0, os.path.join(DISC, "scripts"))

from mgcore.jsonio import write_json, write_jsonl  # noqa: E402

HAVE_MPL = importlib.util.find_spec("matplotlib") is not None
if HAVE_MPL:
    from mgd import viz  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n"
ALL_IDS = ["%02d" % i for i in range(1, 13)]


def make_run(base):
    """A finished-looking run with every input except demand bursts and the run log."""
    run = os.path.join(base, "example-run")
    w = lambda rel, doc: write_json(os.path.join(run, rel), doc)  # noqa: E731
    wl = lambda rel, recs: write_jsonl(os.path.join(run, rel), recs)  # noqa: E731
    w("protocol.json", {"title": "Invoicing for freelance translators", "topic": "invoicing for freelance translators",
                        "question": "Which invoicing jobs of freelance translators are under-served?",
                        "as_of": "2026-10-01", "recency_days": 730, "ambition": {"min_arr_usd": 12000}})
    w("output/prisma.json", {
        "landscape": {"records_identified": 40, "unique_entities": 20, "duplicates_removed": 20, "screened": 20,
                      "excluded_by_reason": {"EX-OUT-OF-SCOPE": 8}, "unsure": 2, "included": 10, "included_verified": 9},
        "evidence": {"submitted": 12, "rejected_at_merge": 1, "duplicates": 1, "in_ledger": 10, "verification": {"verified": 8}},
        "gaps": {"cards_proposed": 3, "by_status": {"weakened": 1, "killed": 1, "insufficient": 1}, "gated_out": 0, "ranked": 1}})
    cats = ["invoicing", "invoicing", "invoicing", "payments", "payments", "time-tracking"]
    ents, attrs, ladder = [], [], ["entity_id,model,min_paid_month,currency,free_tier,per_seat"]
    for i, cat in enumerate(cats):
        eid = "dom:p%d.io" % i
        ents.append({"entity_id": eid, "kind": "product", "names": ["P%d" % i], "status": "included",
                     "verified": {"status": "ok"}, "found_in_units": ["R01-A1-web"], "found_via": ["sampling"]})
        price = 5.0 * (i + 1)
        attrs.append({"entity_id": eid, "category": cat, "approach": "hosted-saas",
                      "pricing": {"model": "freemium" if i % 2 else "subscription", "min_paid_month": price, "currency": "USD"}})
        ladder.append("%s,subscription,%s,USD,False," % (eid, price))
    wl("landscape/entities.jsonl", ents)
    wl("landscape/entity-attributes.jsonl", attrs)
    os.makedirs(os.path.join(run, "analysis"), exist_ok=True)
    with open(os.path.join(run, "analysis", "price_ladder.csv"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(ladder) + "\n")
    w("landscape/classification.json", {"facets": {"category": [{"id": "invoicing", "label": "Invoicing"},
                                                                {"id": "payments", "label": "Payments"},
                                                                {"id": "time-tracking", "label": "Time tracking"}]}})
    w("landscape/saturation.json", {
        "round": 2, "verdict": "STOP_UNSATURATED", "reasons": ["marginal yield 0.300 in round 2 (need <= 0.05 from round 2)"],
        "overall": {"S_obs": 9, "T": 12, "chao2": {"estimate": 14.0, "ci_low": 10.0, "ci_high": 30.0}, "completeness": 0.64,
                    "coverage": 0.7},
        "history": [{"round": 1, "T": 6, "S_obs": 6, "chao2": 12.0, "ci_low": 7.0, "ci_high": 40.0, "coverage": 0.5,
                     "completeness": 0.5, "marginal_yield": None, "verdict": "EXPAND"},
                    {"round": 2, "T": 12, "S_obs": 9, "chao2": 14.0, "ci_low": 10.0, "ci_high": 30.0, "coverage": 0.7,
                     "completeness": 0.64, "marginal_yield": 0.3, "verdict": "STOP_UNSATURATED"}],
        "note": "All estimates are lower bounds."})
    w("analysis/gapmap.json", {"jobs": [
        {"code": "J-CHASE-LATE", "label": "Chase late payments", "supply": 1, "demand_weighted": 6.5, "demand_authors": 6,
         "demand_records": 7, "demand_domains": 3, "cell": "absolute"},
        {"code": "J-CONVERT-CURRENCY", "label": "Convert currencies", "supply": 6, "demand_weighted": 2.0, "demand_authors": 3,
         "demand_records": 3, "demand_domains": 2, "cell": "synthesis"},
        {"code": "J-SEND-INVOICE", "label": "Send an invoice", "supply": 12, "demand_weighted": 1.0, "demand_authors": 2,
         "demand_records": 2, "demand_domains": 1, "cell": "none"}]})
    stances = ["pain", "workaround", "pain", "wtp", "switch", "praise", "wish", "contra"]
    recs = []
    for i, st in enumerate(stances):
        recs.append({"id": "EV-%06d" % (i + 1), "stance": st, "strength": "S%d" % (i % 5), "domain": ["forum.example.org", "reviews.example.net",
                     "qa.example.io"][i % 3], "source_type": ["forum", "review", "qa"][i % 3],
                     "posted_at": "%d-%02d-15" % (2023 + i % 4, 1 + i), "credibility": "independent", "author_hash": "ah_%d" % i,
                     "verification": {"status": "verified"}})
    recs.append({"id": "EV-000099", "stance": "pain", "strength": "S1", "domain": "x.org", "source_type": "forum",
                 "verification": {"status": "pending"}})
    wl("evidence/ledger.jsonl", recs)
    w("coding/agreement.json", {"verdict": "provisional", "units": 30, "version": 1,
                                "eligible_codes": ["J-CHASE-LATE", "X-PRICE"], "not_assessable": ["J-SEND-INVOICE"],
                                "codes": {"J-CHASE-LATE": {"alpha": 0.91, "status": "accept", "positives": 6},
                                          "X-PRICE": {"alpha": 0.72, "status": "provisional", "positives": 5},
                                          "J-SEND-INVOICE": {"alpha": 1.0, "status": "not-assessable", "positives": 1}}})
    w("coding/codebook.lock.json", {"version": 1})
    w("coding/codebook.v1.json", {"version": 1, "codes": [{"id": "J-CHASE-LATE", "type": "job", "label": "Chase late payments"},
                                                          {"id": "X-PRICE", "type": "cross", "label": "Price mismatch"}]})
    wl("gaps/cards.jsonl", [
        {"gap_id": "GAP-001", "title": "Automatic late-payment chasing for solo translators", "status": "weakened"},
        {"gap_id": "GAP-002", "title": "Multi-currency invoices without rounding errors", "status": "killed"},
        {"gap_id": "GAP-003", "title": "Invoices in the client's language", "status": "insufficient"}])
    num = lambda r, d, s, a: {"records": r, "domains": d, "source_types": s, "authors": a,  # noqa: E731
                              "triangulation": {"pain": True, "demand": True, "supply": True}}
    w("gaps/card-check.json", {"cards": {
        "GAP-001": {"pass": True, "reasons": [], "numbers": num(7, 3, 3, 6)},
        "GAP-002": {"pass": True, "reasons": [], "numbers": num(6, 3, 2, 5)},
        "GAP-003": {"pass": False, "reasons": ["2 domains (need 3)"], "numbers": num(5, 2, 2, 4)}}})
    w("gaps/redteam/GAP-001.json", {"gap_id": "GAP-001", "verdict": "weakened",
                                    "why_empty": "Several tools offer reminders already, but none in the client's own language."})
    w("gaps/redteam/GAP-002.json", {"gap_id": "GAP-002", "verdict": "killed",
                                    "existing_solutions": [{"name": "Bravo Billing", "covers": "full"}],
                                    "why_empty": "It is not empty. Bravo Billing converts currencies with exact rounding for every client."})
    w("gaps/ranking.json", {"ranked": [{"gap_id": "GAP-001", "title": "Automatic late-payment chasing for solo translators",
                                        "total": 55.5, "p_top3": 0.9, "rank": 1}], "note": "Desk evidence only."})
    w("gaps/sizing.json", {"gaps": {"GAP-001": {"usd_per_year": {"low": {"som": 900}, "base": {"som": 18240}, "high": {"som": 90000}}}}})
    w("gaps/certainty.json", {"gaps": {"GAP-001": {"pain": "Moderate", "demand": "Low", "demand_strength": "weak"}}})
    return run


@unittest.skipUnless(HAVE_MPL, "matplotlib is not installed; the viz step is optional")
class VizBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = mock.patch.dict(os.environ)  # build() may set MPLCONFIGDIR; restore it afterwards
        cls.env.start()
        cls.tmp = tempfile.mkdtemp()
        cls.rdir = make_run(cls.tmp)
        cls.man = viz.build(cls.rdir)
        cls.by = dict((c["id"], c) for c in cls.man["charts"])

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        shutil.rmtree(cls.tmp)

    def test_manifest_lists_every_chart(self):
        self.assertEqual([c["id"] for c in self.man["charts"]], ALL_IDS)
        for c in self.man["charts"]:
            self.assertTrue(c["title"])
            self.assertTrue(c.get("file") or c.get("skipped_reason"), c)
        on_disk = json.load(open(os.path.join(self.rdir, "output", "dashboard", "manifest.json"), encoding="utf-8"))
        self.assertEqual(on_disk["charts"], self.man["charts"])

    def test_expected_pngs_exist_and_are_pngs(self):
        for cid in ALL_IDS[:10]:
            c = self.by[cid]
            self.assertNotIn("skipped_reason", c, c.get("skipped_reason"))
            path = os.path.join(self.rdir, c["file"])
            self.assertRegex(os.path.basename(path), r"^%s-[a-z0-9-]+\.png$" % cid)
            with open(path, "rb") as fh:
                data = fh.read()
            self.assertTrue(data.startswith(PNG), path)
            self.assertGreater(len(data), 5000, path)

    def test_missing_inputs_are_skipped_with_a_reason(self):
        self.assertIsNone(self.by["11"]["file"])
        self.assertIn("bursts.json", self.by["11"]["skipped_reason"])
        self.assertIsNone(self.by["12"]["file"])
        self.assertIn("events.jsonl", self.by["12"]["skipped_reason"])
        self.assertFalse(os.path.exists(os.path.join(self.rdir, "output", "dashboard", "11-demand-bursts.png")))
        for c in self.man["charts"]:  # a crash inside a chart is also reported as a skip; none expected here
            self.assertNotIn("could not draw", c.get("skipped_reason", ""), c)

    def test_html_is_self_contained(self):
        path = os.path.join(self.rdir, self.man["html"])
        text = open(path, encoding="utf-8").read()
        self.assertEqual(text.count('<img src="data:image/png;base64,'), 10)
        self.assertIn("prefers-color-scheme: dark", text)
        self.assertNotRegex(text, r"<script")
        self.assertNotRegex(text, r"<link")
        self.assertNotRegex(text, r"(src|href|srcset)=[\"']https?://")
        self.assertNotRegex(text, r"url\(\s*['\"]?https?://")
        self.assertIn("Which invoicing jobs of freelance translators are under-served?", text)
        self.assertIn("Demand bursts", text)  # listed under "Charts not drawn"

    def test_summary_reads_numbers_from_files(self):
        path = os.path.join(self.rdir, self.man["summary"])
        self.assertEqual(path, os.path.join(self.rdir, "output", "summary.md"))
        text = open(path, encoding="utf-8").read()
        self.assertLess(text.count("\n"), 60)
        self.assertIn("Which invoicing jobs of freelance translators are under-served?", text)
        self.assertIn("**1 of 3 gap ideas made the final ranking.**", text)
        self.assertIn("GAP-001", text)
        self.assertIn("$18,240", text)
        self.assertIn("above your ambition of $12,000", text)
        self.assertIn("pain Moderate, demand Low", text)
        self.assertIn("1 existing product already covers it fully (Bravo Billing)", text)
        self.assertIn("GAP-003", text)
        self.assertIn("evidence from only 2 websites; 3 needed", text)
        self.assertIn("at least 9 products", text)
        self.assertIn("8 verified quotes", text)

    def test_cmd_viz_prints_one_line_per_chart(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = viz.cmd_viz(argparse.Namespace(run=self.rdir, out=None))
        self.assertEqual(code, 0)
        lines = buf.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 14)
        self.assertTrue(any(ln.startswith("skipped") and "Demand bursts" in ln for ln in lines))
        self.assertTrue(lines[-2].startswith("dashboard") and lines[-2].endswith("index.html"))
        self.assertTrue(lines[-1].startswith("summary") and lines[-1].endswith("summary.md"))


@unittest.skipUnless(HAVE_MPL, "matplotlib is not installed; the viz step is optional")
class VizEdgeCases(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ)
        self.env.start()
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp)

    def test_empty_run_skips_everything(self):
        run = os.path.join(self.tmp, "empty")
        os.makedirs(run)
        man = viz.build(run)
        self.assertEqual(len(man["charts"]), 12)
        for c in man["charts"]:
            self.assertIsNone(c["file"])
            self.assertTrue(c["skipped_reason"])
            self.assertNotIn("could not draw", c["skipped_reason"])
        self.assertTrue(os.path.exists(os.path.join(run, "output", "dashboard", "index.html")))
        self.assertTrue(os.path.exists(os.path.join(run, "output", "summary.md")))
        self.assertEqual(glob_pngs(os.path.join(run, "output", "dashboard")), [])

    def test_out_dir_and_mpl_config_dir(self):
        run = make_run(self.tmp)
        out_dir = os.path.join(self.tmp, "elsewhere")
        env = dict((k, v) for k, v in os.environ.items() if k != "MPLCONFIGDIR")
        with mock.patch.dict(os.environ, env, clear=True):
            man = viz.build(run, out_dir=out_dir)
            self.assertTrue(os.path.isdir(os.path.join(run, "cache", "mpl")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "summary.md")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "08-gap-scorecard.png")))
        self.assertTrue(os.path.isabs(man["html"]))
        self.assertFalse(os.path.exists(os.path.join(run, "output", "dashboard")))
        self.assertFalse(os.path.exists(os.path.join(run, "output", "summary.md")))

    def test_malformed_input_skips_only_that_chart(self):
        run = make_run(self.tmp)
        with open(os.path.join(run, "analysis", "gapmap.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        write_json(os.path.join(run, "coding", "agreement.json"), {"codes": {"X": {"alpha": "n/a", "status": "accept"}}})
        man = viz.build(run)
        by = dict((c["id"], c) for c in man["charts"])
        self.assertIn("gapmap.json", by["04"]["skipped_reason"])
        self.assertTrue(by["07"]["skipped_reason"])
        self.assertTrue(by["08"]["file"])

    def test_saturation_without_history_uses_latest_round(self):
        run = make_run(self.tmp)
        sat = json.load(open(os.path.join(run, "landscape", "saturation.json"), encoding="utf-8"))
        del sat["history"]
        write_json(os.path.join(run, "landscape", "saturation.json"), sat)
        hist, how = viz._sat_history(viz._Run(run), sat)
        self.assertEqual(how, "final")
        self.assertEqual([h["S_obs"] for h in hist], [9])
        man = viz.build(run)
        self.assertTrue(man["charts"][1]["file"])

    def test_gapscan_cli_runs_viz(self):
        import gapscan
        run = make_run(self.tmp)
        write_json(os.path.join(run, "state.json"), {"run_id": "example-run"})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = gapscan.main(["viz", run])
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("index.html", buf.getvalue())
        self.assertTrue(os.path.exists(os.path.join(run, "output", "summary.md")))

    def test_missing_matplotlib_is_a_clear_error(self):
        run = os.path.join(self.tmp, "r")
        os.makedirs(run)
        with mock.patch.dict(sys.modules, {"matplotlib": None}):
            with self.assertRaises(viz.CliError) as ctx:
                viz.build(run)
        self.assertIn("pip install matplotlib", str(ctx.exception))


def glob_pngs(folder):
    return sorted(f for f in os.listdir(folder) if re.search(r"\.png$", f))


if __name__ == "__main__":
    unittest.main()
