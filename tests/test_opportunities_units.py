"""Unit tests for the opportunity lenses (D26), traction (D27) and the scan funnel (D28) on a small synthetic run."""

import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "market-gap-discovery", "scripts"))

from mgd import net, opportunities as opm, traction  # noqa: E402
from mgcore.jsonio import read_jsonl, write_json, write_jsonl  # noqa: E402


def ent(eid, name, url):
    return {"entity_id": eid, "kind": "product", "names": [name], "urls": [url], "aliases": [], "status": "included",
            "verified": {"status": "ok", "snapshot": "a" * 64}}


def attrs(eid, cat, price=None, free=False, platform=("web",), approach="hosted-saas", deployment="cloud", langs=("en",),
          integrations=(), segments=("solo",), **kw):
    a = {"entity_id": eid, "approach": approach, "category": cat, "segments": list(segments),
         "pricing": {"model": "subscription" if price else "free", "min_paid_month": price, "currency": "USD", "free_tier": free},
         "platform": list(platform), "deployment": deployment, "languages": list(langs), "integrations": list(integrations),
         "evidence": ["a" * 64]}
    a.update(kw)
    return a


def rec(i, eid, stance, quote, author, strength="S2", domain="forum.example.org", cands=None):
    r = {"id": "EV-%06d" % i, "url": "https://%s/t/%d" % (domain, i), "source": "web", "source_type": "forum",
         "snapshot": "b" * 64, "quote": quote, "stance": stance, "strength": strength, "credibility": "independent",
         "author_hash": "ah_%016x" % author, "entity_ids": [eid] if eid else [], "domain": domain,
         "verification": {"status": "verified"}}
    if cands:
        r["candidate_ids"] = cands
    return r


class Fixture(object):
    def __init__(self):
        self.run = tempfile.mkdtemp()
        for d in ("landscape", "evidence", "opportunities", "coding", "analysis", "output", "snapshots", "cache"):
            os.makedirs(os.path.join(self.run, d))
        write_json(os.path.join(self.run, "state.json"), {"seed": 1, "groups": {}, "evidence": {"round": 0}})
        self.proto = {"run_id": "x", "topic": "invoicing", "picos": {"population": "solo founders"}, "ambition": {"min_arr_usd": 12000},
                      "variation_dimensions": {"platform": ["shopify", "web"], "language": ["de"]},
                      "founder_fit": {"exclusions": ["crypto"]}, "scope": {"out": []}, "as_of": "2026-10-01"}

    def write(self, ents, atts, trac=(), led=(), whynow=(), supply=()):
        write_json(os.path.join(self.run, "protocol.json"), self.proto)
        write_jsonl(os.path.join(self.run, "landscape", "entities.jsonl"), ents)
        write_jsonl(os.path.join(self.run, "landscape", "entity-attributes.jsonl"), atts)
        write_jsonl(os.path.join(self.run, "landscape", "traction.jsonl"), list(trac))
        write_jsonl(os.path.join(self.run, "evidence", "ledger.jsonl"), list(led))
        write_jsonl(os.path.join(self.run, "evidence", "why-now.jsonl"), list(whynow))
        write_jsonl(os.path.join(self.run, "analysis", "supply.jsonl"), list(supply))
        write_json(os.path.join(self.run, "landscape", "classification.json"),
                   {"facets": {"category": [{"id": "invoicing", "label": "Invoicing"}, {"id": "analytics", "label": "Analytics"},
                                            {"id": "crm", "label": "CRM"}],
                               "platform": [{"id": "web", "label": "Web"}, {"id": "shopify", "label": "Shopify"}]}})

    def close(self):
        shutil.rmtree(self.run)


def trow(eid, installs, rating, count=100, source="wp"):
    return {"entity_id": eid, "key": eid, "source": source, "installs": installs, "ratings_count": count, "rating_avg": rating,
            "ratings_dist": None, "price_usd": None, "snapshot": "c" * 64, "retrieved_at": "2026-10-01", "via": "snapshot"}


class LensRules(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        ents, atts, trac = [], [], []
        for i in range(6):  # invoicing: 6 web products, prices 40..65, no free tier; two big but poorly rated
            eid = "wp:inv%d" % i
            ents.append(ent(eid, "Inv %d" % i, "https://inv%d.example.com/" % i))
            atts.append(attrs(eid, "invoicing", price=40 + 5 * i, integrations=["Ana 0"] if i < 3 else []))
            trac.append(trow(eid, [100000, 90000, 500, 400, 300, 200][i], [3.1, 3.2, 4.8, 4.7, 4.9, 4.6][i]))
        for i in range(4):  # analytics: cheap, free tiers, one on shopify
            eid = "dom:ana%d.com" % i
            ents.append(ent(eid, "Ana %d" % i, "https://ana%d.com/" % i))
            # Two analytics products already on Shopify: above port_max_target (1), so no port there.
            atts.append(attrs(eid, "analytics", price=5 + i, free=True, platform=("web", "shopify") if i < 2 else ("web",)))
        ents.append(ent("dom:oss.dev", "OSS Inbox", "https://oss.dev/"))
        atts.append(attrs("dom:oss.dev", "crm", approach="open-source-tool", deployment="self-hosted", license="MIT"))
        ents.append(ent("dom:sspl.dev", "SSPL Thing", "https://sspl.dev/"))
        atts.append(attrs("dom:sspl.dev", "crm", approach="open-core", deployment="self-hosted", license="SSPL-1.0"))
        ents.append(ent("wp:plug", "Some Plugin", "https://wordpress.org/plugins/plug/"))
        atts.append(attrs("wp:plug", "crm", approach="plugin", deployment="self-hosted", platform=("wordpress",)))
        led = [rec(1, "wp:inv0", "pain", "Way too expensive for a solo freelancer, the price doubled", 1),
               rec(2, "wp:inv1", "switch", "We left because the pricing is absurd for two invoices a month", 2, domain="qa.example.net"),
               rec(3, "wp:inv0", "workaround", "I hired a virtual assistant to chase invoices every Friday", 3, "S4"),
               rec(4, "dom:ana1.com", "wtp", "I pay a freelancer 50 dollars a week to send these reports", 4, "S4"),
               rec(5, "wp:inv1", "pain", "Inv 1 was acquired and the price increase killed it for us", 5),
               rec(6, "wp:inv1", "switch", "After the acquisition they raised prices, so we are migrating", 6)]
        wn = [{"id": "WN-001", "factor": "platform", "change": "Inv 0 is shutting down its free plan in 2026", "date": "2026-06",
               "quote": "we are sunsetting the free plan"}]
        self.f.write(ents, atts, trac, led, wn)
        self.rows, self.doc = opm.scan(self.f.run)
        self.by = {}
        for r in self.rows:
            self.by.setdefault(r["lens"], []).append(r)

    def tearDown(self):
        self.f.close()

    def test_clone_wedge_names_the_wedge(self):
        cw = self.by["clone-wedge"]
        price = [r for r in cw if r["twist"]["to"] == "price"]
        self.assertTrue(price, cw)
        self.assertTrue(price[0]["title"].startswith("Cheaper alternative to Inv 0"))
        self.assertIn("EV-000001", price[0]["evidence_ids"])
        self.assertGreater(price[0]["prior_parts"]["dissatisfaction"], 0.5)

    def test_port_only_to_thin_targets(self):
        ports = [r for r in self.by.get("port", []) if r["twist"]["dimension"] == "platform"]
        self.assertEqual([(r["category"], r["twist"]["to"]) for r in ports], [("invoicing", "shopify")])
        self.assertIn("on Shopify", ports[0]["title"])
        lang = [r for r in self.by.get("port", []) if r["twist"]["dimension"] == "language"]
        self.assertTrue(lang and "in German" in lang[0]["title"])
        # Language data shows no variety, so absence of German products counts as unknown (0.5), not proof.
        self.assertEqual(lang[0]["prior_parts"]["absence"], 0.5)

    def test_down_market_for_expensive_floor_only(self):
        self.assertEqual([r["category"] for r in self.by["down-market"]], ["invoicing"])

    def test_bundle_from_integration_links(self):
        self.assertEqual([r["pair"] for r in self.by["bundle"]], [["analytics", "invoicing"]])

    def test_hosted_oss_respects_license_and_plugins(self):
        hosted = [r["base_entities"][0] for r in self.by["hosted-oss"]]
        self.assertEqual(hosted, ["dom:oss.dev"])

    def test_replace_and_productize_are_evidence_led(self):
        keys = [r["key"] for r in self.by["replace"]]
        self.assertIn("replace|WN-001", keys)
        self.assertIn("replace|wp:inv1", keys)
        # One author pays an assistant (invoicing) and one pays a freelancer (analytics): neither category reaches
        # evidence_led_min_authors, and "too expensive for a solo freelancer" is not a paid service.
        self.assertNotIn("productize", self.by)

    def test_unknown_prior_parts_are_neutral(self):
        for r in self.rows:
            vals = [0.5 if v is None else v for v in r["prior_parts"].values()]
            self.assertAlmostEqual(r["prior"], round(sum(vals) / len(vals), 3), places=3)

    def test_ids_are_stable_and_candidates_persist(self):
        first = {r["key"]: r["opp_id"] for r in self.rows}
        # Remove the open-source product: its option no longer fires but keeps its id, flagged.
        atts = [a for a in read_jsonl(os.path.join(self.f.run, "landscape", "entity-attributes.jsonl"))[0] if a["entity_id"] != "dom:oss.dev"]
        write_jsonl(os.path.join(self.f.run, "landscape", "entity-attributes.jsonl"), atts)
        rows, _doc = opm.scan(self.f.run)
        again = {r["key"]: r["opp_id"] for r in rows}
        for k, v in first.items():
            self.assertEqual(again.get(k), v, k)
        gone = [r for r in rows if r["key"] == "hosted-oss|dom:oss.dev"][0]
        self.assertIn("rule no longer fires", gone["flags"])

    def test_ambition_math(self):
        cw = [r for r in self.by["clone-wedge"] if r["twist"]["to"] == "price"][0]
        am = cw["ambition"]
        self.assertEqual(am["target_mrr"], 1000.0)
        self.assertEqual(am["customers_needed"], -(-1000 // am["price_ref_month"]))
        # Base = the proven products (top traction third of the store): Inv 0 and Inv 1.
        self.assertEqual(cw["base_entities"], ["wp:inv0", "wp:inv1"])
        self.assertEqual(am["base_installs"], 190000)
        self.assertAlmostEqual(am["share_of_base_installs"], am["customers_needed"] / 190000.0, places=5)


class ProductizeAndExclusion(unittest.TestCase):
    def test_productize_needs_two_authors_and_exclusions_apply(self):
        f = Fixture()
        try:
            ents = [ent("dom:a.com", "A", "https://a.com/"), ent("dom:b.com", "B", "https://b.com/")]
            atts = [attrs("dom:a.com", "crm"), attrs("dom:b.com", "crm")]
            led = [rec(1, "dom:a.com", "workaround", "We hired a contractor to clean the CRM data monthly", 1, "S4"),
                   rec(2, "dom:b.com", "wtp", "I pay an agency to keep our CRM tidy every quarter", 2, "S4", domain="b.example")]
            wn = [{"id": "WN-001", "factor": "economic", "change": "A crypto CRM was discontinued", "date": "2026-01"}]
            f.write(ents, atts, [], led, wn)
            rows, _d = opm.scan(f.run)
            prod = [r for r in rows if r["lens"] == "productize"]
            self.assertEqual(len(prod), 1)
            self.assertEqual(sorted(prod[0]["evidence_ids"]), ["EV-000001", "EV-000002"])
            rep = [r for r in rows if r["lens"] == "replace"][0]
            self.assertEqual(rep["status"], "excluded")
            self.assertTrue(any(x.startswith("excluded") for x in rep["flags"]))
        finally:
            f.close()


class FunnelAndScore(unittest.TestCase):
    def test_score_tiers_and_successive_halving(self):
        f = Fixture()
        try:
            ents = [ent("wp:p%d" % i, "P%d" % i, "https://p%d.example/" % i) for i in range(6)]
            atts = [attrs("wp:p%d" % i, "invoicing", price=10 + i, platform=("web",)) for i in range(6)]
            trac = [trow("wp:p%d" % i, 1000 * (i + 1), 4.5) for i in range(6)]
            f.proto["variation_dimensions"] = {"platform": ["shopify"]}
            f.write(ents, atts, trac)
            rows, _d = opm.scan(f.run)
            self.assertTrue(rows)
            first = opm.select(f.run, 1)
            self.assertTrue(first)
            oid = first[0]["opp_id"]
            led = [rec(i, "wp:p5", "pain", "Shopify stores need this but nothing exists %d" % i, i, domain="d%d.example" % (i % 2), cands=[oid])
                   for i in range(1, 5)]
            led.append(rec(9, "wp:p5", "praise", "The web version is fine for us", 9, cands=[oid]))
            write_jsonl(os.path.join(f.run, "evidence", "ledger.jsonl"), led)
            sc = opm.score(f.run)
            self.assertEqual(sc[oid]["status"], "promising")
            self.assertEqual(sc[oid]["counter"], 1)
            self.assertEqual(opm.select(f.run, 2), [x for x in opm.tested_pool(f.run)][:1])
            doc = opm.rank(f.run)
            self.assertEqual(doc["ranked"][0]["opp_id"], oid)
        finally:
            f.close()


class TractionParse(unittest.TestCase):
    def test_reads_saved_marketplace_responses(self):
        f = Fixture()
        try:
            run = f.run
            wp = {"plugins": [{"slug": "inv", "rating": 84, "num_ratings": 120, "active_installs": 20000,
                               "ratings": {"5": 90, "4": 10, "3": 5, "2": 5, "1": 10}}]}
            ap = {"resultCount": 1, "results": [{"trackId": 123, "averageUserRating": 3.9, "userRatingCount": 450, "price": 4.99, "currency": "USD"}]}
            at = {"_embedded": {"addons": [{"key": "k", "_links": {"alternate": {"href": "/apps/777/thing"}},
                                            "_embedded": {"distribution": {"totalInstalls": 3000}, "reviews": {"averageStars": 3.5, "count": 40}}}]}}
            for body, method in ((wp, "api:wp"), (ap, "api:apple"), (at, "api:atl")):
                raw = json.dumps(body).encode()
                net.save_snapshot(run, "https://api.example/%s" % method, "https://api.example/%s" % method, 200, "application/json", raw, method)
            rows = traction.from_snapshots(run)
            self.assertEqual(rows["wp:inv"]["installs"], 20000)
            self.assertAlmostEqual(rows["wp:inv"]["rating_avg"], 4.2)
            self.assertEqual(rows["wp:inv"]["ratings_dist"]["1"], 10)
            self.assertEqual(rows["app:ios:123"]["ratings_count"], 450)
            self.assertEqual(rows["app:ios:123"]["price_usd"], 4.99)
            self.assertEqual(rows["atl:777"]["installs"], 3000)
            ents = [ent("wp:inv", "Inv", "https://wordpress.org/plugins/inv/"), ent("dom:x.com", "X", "https://x.com/")]
            ents[1]["aliases"] = ["app:ios:123"]
            f.write(ents, [attrs("wp:inv", "invoicing"), attrs("dom:x.com", "invoicing")])
            out_rows, s = traction.build(run, offline=True)
            self.assertEqual(sorted(r["entity_id"] for r in out_rows), ["dom:x.com", "wp:inv"])
            self.assertEqual(s["from_snapshots"], 2)
        finally:
            f.close()


class Helpers(unittest.TestCase):
    def test_percentile_and_quantile(self):
        pc = opm._pct([1, 2, 2, 3])
        self.assertEqual(pc[1], 0.125)
        self.assertEqual(pc[2], 0.5)
        self.assertEqual(opm._quantile([1, 2, 3, 4], 0.5), 2.5)

    def test_license_classes(self):
        self.assertEqual(opm._license_class("MIT"), "ok")
        self.assertEqual(opm._license_class("AGPL-3.0-only"), "duty")
        self.assertEqual(opm._license_class("SSPL-1.0"), "blocked")
        self.assertEqual(opm._license_class("Elastic License 2.0"), "blocked")
        self.assertEqual(opm._license_class(None), "unknown")


if __name__ == "__main__":
    unittest.main()
