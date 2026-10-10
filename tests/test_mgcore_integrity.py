"""Tests for canonicalisation, quote verification, schema validation, config and the
human-task queue."""

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared"))

from mgcore import canon, config, hq, quotes, schema  # noqa: E402

DISC = os.path.join(ROOT, "skills", "market-gap-discovery")
PSL = canon.PublicSuffix.load(os.path.join(DISC, "assets", "psl-mini.txt"))


class CanonTests(unittest.TestCase):
    def test_normalize_url_strips_tracking_and_fragment(self):
        u = canon.normalize_url("HTTPS://WWW.Example.com:443/Pricing/?utm_source=x&b=2&a=1#top")
        self.assertEqual(u, "https://www.example.com/Pricing?a=1&b=2")

    def test_registrable_domains(self):
        self.assertEqual(PSL.registrable("www.example.com"), "example.com")
        self.assertEqual(PSL.registrable("app.example.com"), "example.com")
        self.assertEqual(PSL.registrable("shop.example.co.uk"), "example.co.uk")
        self.assertEqual(PSL.registrable("foo.vercel.app"), "foo.vercel.app")
        self.assertEqual(PSL.registrable("a.b.ck"), "a.b.ck")      # wildcard *.ck
        self.assertEqual(PSL.registrable("www.ck"), "www.ck")       # exception !www.ck

    def test_entity_keys(self):
        k = lambda url, kind="product": canon.entity_key(url, kind, PSL)  # noqa: E731
        self.assertEqual(k("https://www.invoiceapp.io/pricing?utm_medium=a"), "dom:invoiceapp.io")
        self.assertEqual(k("https://github.com/Acme/Tool.git"), "gh:acme/tool")
        self.assertEqual(k("https://wordpress.org/plugins/invoicing-pro/"), "wp:invoicing-pro")
        self.assertEqual(k("https://wordpress.org/support/plugin/invoicing-pro/reviews/"), "wp:invoicing-pro")
        self.assertEqual(k("https://apps.apple.com/us/app/some-app/id123456789"), "app:ios:123456789")
        self.assertEqual(k("https://play.google.com/store/apps/details?id=com.Acme.App&hl=en"), "app:android:com.acme.app")
        self.assertEqual(k("https://marketplace.atlassian.com/apps/1213456/tool-name"), "atl:1213456")
        self.assertEqual(k("https://apps.shopify.com/invoice-hero"), "shopify:invoice-hero")
        self.assertEqual(k("https://stackoverflow.com/questions/tagged/invoicing"), "se:stackoverflow:invoicing")
        self.assertEqual(k("https://community.vendor.com/c/feature-requests", "community"), "site:community.vendor.com")
        self.assertEqual(k("https://alternativeto.net/software/foo/about/"), "alt:foo")
        # Live-run defects: a Google redirect keyed Honeybadger as dom:google.com, and a Firefox add-on
        # listing keyed Userback as dom:mozilla.org.
        self.assertEqual(k("https://www.google.com/url?q=https://www.honeybadger.io/pricing&sa=U"), "dom:honeybadger.io")
        self.assertEqual(k("https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.userback.io%2F"), "dom:userback.io")
        self.assertEqual(k("https://addons.mozilla.org/en-US/firefox/addon/userback/"), "ext:firefox:userback")
        self.assertEqual(k("https://microsoftedge.microsoft.com/addons/detail/tool/abcdefghijklmnopabcdefghijklmnop"),
                         "ext:edge:abcdefghijklmnopabcdefghijklmnop")
        self.assertEqual(k("https://sites.google.com/view/someapp"), "site:sites.google.com/view")
        self.assertNotEqual(k("https://www.apple.com/app-store/"), "dom:apple.com")

    def test_union_find_prefers_domain_keys(self):
        uf = canon.UnionFind()
        uf.union("alt:foo", "dom:foo.com")
        uf.union("wp:foo", "alt:foo")
        self.assertEqual(uf.find("wp:foo"), "dom:foo.com")


class QuoteTests(unittest.TestCase):
    SNAP = "<p>We’ve tried “Billio” — it’s way too   expensive for a solo translator.</p> Also no PDF export in French."

    def test_verbatim_passes_after_normalisation(self):
        ok, off = quotes.verify_quote("we've tried \"Billio\" - it's way too expensive for a solo translator", self.SNAP)
        self.assertTrue(ok)
        self.assertIsNotNone(off)

    def test_paraphrase_fails(self):
        ok, _ = quotes.verify_quote("Billio is too pricey for solo translators", self.SNAP)
        self.assertFalse(ok)

    def test_ellipsis_segments_in_order(self):
        self.assertTrue(quotes.verify_quote("way too expensive ... no PDF export in French", self.SNAP)[0])
        self.assertFalse(quotes.verify_quote("no PDF export in French ... way too expensive", self.SNAP)[0])

    def test_tampered_snapshot_fails(self):
        tampered = self.SNAP.replace("expensive", "cheap")
        self.assertFalse(quotes.verify_quote("way too expensive for a solo translator", tampered)[0])


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.reg = schema.SchemaRegistry(os.path.join(DISC, "assets", "schemas"), os.path.join(ROOT, "shared", "schemas"))

    def test_all_schemas_load(self):
        for d in (os.path.join(DISC, "assets", "schemas"), os.path.join(ROOT, "skills", "market-gap-validation", "assets", "schemas"), os.path.join(ROOT, "shared", "schemas")):
            for name in os.listdir(d):
                if name.endswith(".schema.json"):
                    s = schema.SchemaRegistry(d).load(name[:-len(".schema.json")])
                    self.assertIn("$id", s, name)

    def test_evidence_record(self):
        s = self.reg.load("evidence")
        good = {"url": "https://news.ycombinator.com/item?id=1", "source": "hn", "source_type": "forum",
                "snapshot": "a" * 64, "quote": "I export to a spreadsheet every Friday", "stance": "workaround",
                "strength": "S3", "credibility": "independent", "author_hash": "ah_0123456789abcdef"}
        self.assertEqual(schema.validate(good, s, self.reg), [])
        bad = dict(good, stance="angry", quote="x" * 300)
        errs = schema.validate(bad, s, self.reg)
        self.assertTrue(any("stance" in e for e in errs))
        self.assertTrue(any("longer than 280" in e for e in errs))
        self.assertTrue(schema.validate(dict(good, author_hash="@janedoe"), s, self.reg))

    def test_cross_file_ref(self):
        s = self.reg.load("redteam")
        doc = {"gap_id": "GAP-001", "verdict": "survives", "existing_solutions": [], "failed_attempts": [],
               "why_empty": "Incumbents target agencies, not solo translators.",
               "five_forces": {"rivalry": "low", "new_entrants": "medium", "substitutes": "high",
                               "buyer_power": "medium", "supplier_power": "low"},
               "premortem": ["a", "b", "c"],
               "searches": [{"source": "web", "query": "q1"}, {"source": "hn", "query": "q2"}, {"source": "gh", "query": "q3"}],
               "judgment": {"regulatory_load": "low"}}
        errs = schema.validate(doc, s, self.reg)
        self.assertTrue(any("judgment" in e and "missing required field" in e for e in errs))

    def test_protocol_example_is_valid_when_present(self):
        path = os.path.join(DISC, "assets", "templates", "protocol.example.json")
        if not os.path.exists(path):
            self.skipTest("example not written yet")
        import json
        with open(path) as fh:
            doc = json.load(fh)
        self.assertEqual(schema.validate(doc, self.reg.load("protocol"), self.reg), [])


class ConfigTests(unittest.TestCase):
    def test_defaults_and_overrides(self):
        path = os.path.join(DISC, "assets", "defaults.json")
        c = config.Config(path, {"overrides": {"landscape": {"coverage_target": 0.97}}, "budget": {"subagents_max": 10}})
        self.assertEqual(c.get("landscape.coverage_target"), 0.97)
        self.assertEqual(c.get("landscape.completeness_target_theta"), 0.9)
        self.assertEqual(c.get("budget.subagents_max"), 10)

    def test_every_default_has_a_source(self):
        for skill in ("market-gap-discovery", "market-gap-validation"):
            import json
            with open(os.path.join(ROOT, "skills", skill, "assets", "defaults.json")) as fh:
                d = json.load(fh)
            for path, node in config.leaves(d):
                self.assertTrue(node.get("source"), "%s:%s has no source" % (skill, path))


class HumanTaskTests(unittest.TestCase):
    def test_queue_round_trip(self):
        run = tempfile.mkdtemp()
        try:
            t = hq.add(run, "key", "Set MGD_CONTACT", "Wikimedia requires a contact UA", "export MGD_CONTACT=...",
                       "environment variable", "P0", blocking=False, gate=None)
            self.assertEqual(t["id"], "HT-001")
            g1 = hq.add(run, "judgment", "Approve protocol", "gated run", "review", "hq done", "P0", True, gate="protocol")
            g2 = hq.add(run, "judgment", "Approve protocol", "gated run", "review", "hq done", "P0", True, gate="protocol")
            self.assertEqual(g1["id"], g2["id"])
            self.assertEqual(len(hq.open_tasks(run, blocking_only=True)), 1)
            hq.close(run, g1["id"], "done", "ok")
            self.assertEqual(hq.find_gate(run, "protocol")["status"], "done")
            self.assertTrue(os.path.exists(os.path.join(run, "human-tasks.md")))
        finally:
            shutil.rmtree(run)


if __name__ == "__main__":
    unittest.main()
