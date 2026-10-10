"""End-to-end simulation of a discovery run: a driver follows `gapscan.py next`, fake subagents
write schema-valid outputs, and a fake network serves canned pages. Exercises every phase from
init to DONE without touching the real network."""

import contextlib
import glob
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISC = os.path.join(ROOT, "skills", "market-gap-discovery")
sys.path.insert(0, os.path.join(DISC, "scripts"))

import gapscan  # noqa: E402
from mgd import flow, net, privacy  # noqa: E402
from mgcore.jsonio import read_json, read_jsonl, write_json, write_jsonl  # noqa: E402

PRODUCTS = [("alpha", "Alpha Invoices"), ("bravo", "Bravo Billing"), ("charlie", "Charlie Pay"), ("delta", "Delta Ledger"),
            ("echo", "Echo Quotes"), ("foxtrot", "Foxtrot Books"), ("golf", "Golf Receipts"), ("hotel", "Hotel Hours")]
COMMUNITY = ("https://forum.translators-hub.org/c/business", "Translators Hub Business Forum")
QUOTES = [
    ("pain", "S2", "forum", "Last month two agencies paid me 60 days late and I had to chase every single late payment by hand"),
    ("workaround", "S3", "forum", "I keep a spreadsheet of every unpaid invoice and send reminder emails myself each Friday"),
    ("pain", "S1", "review", "The invoicing tool cannot handle currency conversion for my clients in Switzerland"),
    ("wtp", "S4", "review", "I paid a virtual assistant 200 dollars a month just to chase late payment reminders for me"),
    ("switch", "S3", "qa", "We switched from a big accounting suite because it was built for agencies, not for a solo translator"),
    ("praise", "S2", "review", "The automatic reminders in this app saved me hours of chasing late payment every month"),
    ("wish", "S0", "qa", "I wish my invoicing tool could chase late payment automatically in the client's own language"),
    ("pain", "S2", "issue", "Currency rounding broke three invoices to Japanese agencies and I had to reissue them by hand"),
]
DOMAINS = [("https://forum.translators-hub.org/t/%d", "forum"), ("https://www.proz-reviews.net/review/%d", "review"),
           ("https://qa.freelance-answers.io/q/%d", "qa"), ("https://github.com/acme/invoicer/issues/%d", "issue")]


def fake_raw_get(url, timeout=20, headers=None, max_bytes=None):
    parts = urllib.parse.urlsplit(url)
    if parts.path == "/robots.txt":
        return 404, url, "text/plain", b"", None
    if parts.netloc == "hn.algolia.com":
        q = dict(urllib.parse.parse_qsl(parts.query))
        nf = q.get("numericFilters", "")
        month_idx = 0
        if "created_at_i>=" in nf:
            start = int(nf.split("created_at_i>=")[1].split(",")[0])
            month_idx = (start - 1704067200) // (30 * 86400)
        if q.get("query"):
            hits = 40 if 14 <= month_idx <= 17 else 6
        else:
            hits = 1000
        return 200, url, "application/json", json.dumps({"nbHits": hits, "hits": []}).encode(), None
    for slug, name in PRODUCTS + [("omega", "Omega CRM"), ("india", "India Inbox")]:
        if parts.netloc == "%s.io" % slug or parts.netloc == "www.%s.io" % slug:
            body = "<html><head><title>%s</title></head><body><h1>%s</h1><p>Invoicing for freelancers. Pricing from $12/month.</p></body></html>" % (name, name)
            return 200, url, "text/html", body.encode(), None
    if url.startswith(COMMUNITY[0]):
        return 200, url, "text/html", ("<h1>%s</h1>" % COMMUNITY[1]).encode(), None
    if "news.example.org" in url:
        return 200, url, "text/html", b"<p>From 2026 the e-invoicing mandate requires structured invoices for all B2B sales in the EU.</p>", None
    for pattern, _t in DOMAINS:
        prefix = pattern.split("%d")[0]
        if url.startswith(prefix):
            n = int(url[len(prefix):])
            q = QUOTES[n % len(QUOTES)][3]
            body = "<html><body><div class='post'><p>Posted by someone.</p><p>%s.</p></div></body></html>" % q.replace("'", "&#39;")
            return 200, url, "text/html", body.encode(), None
    return 404, url, "text/html", b"not found", None


def gs(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = gapscan.main([str(a) for a in argv])
    return code, buf.getvalue()


class FakeAgents(object):
    def __init__(self, run):
        self.run = run

    def path(self, rel):
        return os.path.join(self.run, rel)

    def handle(self, apath):
        a = read_json(apath)
        mode = a["mode"]
        fn = getattr(self, "do_" + mode.split(":")[0].replace("-", "_"))
        fn(a)

    # ---- lexicon / press
    def do_lexicon(self, a):
        base = {"segment": ["freelance translators", "solo translators"], "job": ["send invoices", "chase late payments"],
                "category": ["invoicing software", "billing app"], "tool": ["alpha invoices", "bravo billing"],
                "pain": ["late payment", "currency conversion"], "workaround": ["spreadsheet", "manual reminders"], "other": []}
        if a["scout_id"] == "C":
            base["tool"] = base["tool"] + ["charlie pay"]
        write_json(self.path(a["outputs"][0]["path"]), {"assignment_id": a["assignment_id"], "scout_id": a["scout_id"], "mode": "lexicon",
                                                        "facets": base, "queries": [{"source": "web", "query": "invoicing for translators", "results": 10}],
                                                        "tool_calls": 3})

    def do_press(self, a):
        item = {"status": "ok"}
        write_json(self.path("lexicon/press.json"), {"assignment_id": a["assignment_id"], "verdict": "ok",
                                                     "checklist": {k: item for k in ("translation", "operators", "synonyms", "spelling", "limits", "other")},
                                                     "add": {"segment": ["literary translators"]}, "remove": []})

    # ---- landscape
    def _items(self, unit_id, snowball=False):
        items = []
        for i, (slug, name) in enumerate(PRODUCTS):
            if (sum(map(ord, unit_id + slug)) % 10) < 8 or snowball:
                items.append({"name": name, "url": "https://www.%s.io/" % slug, "kind": "product"})
        if not snowball:
            items.append({"name": "Omega CRM", "url": "https://omega.io/", "kind": "product"})
            items.append({"name": COMMUNITY[1], "url": COMMUNITY[0], "kind": "community"})
        return items

    def do_landscape(self, a):
        units = []
        for ch in a["channels"]:
            units.append({"unit_id": ch["unit_id"], "family": ch["family"], "queries": [{"query": b["query"], "source": ch["family"], "results": 5} for b in ch["query_blocks"][:2]],
                          "items": self._items(ch["unit_id"])})
        write_json(self.path(a["outputs"][0]["path"]), {"assignment_id": a["assignment_id"], "scout_id": a["scout_id"], "mode": a["mode"],
                                                        "units": units, "stop_reason": "exhausted", "tool_calls": 6})

    do_probe = do_landscape

    def do_snowball(self, a):
        ch = a["channels"][0]
        items = []
        if ch["unit_id"].startswith("SB-01") and a["scout_id"] == "A":
            items = [{"name": "India Inbox", "url": "https://india.io/", "kind": "product", "via_entity": a["inputs"]["seeds"][0]["entity_id"], "direction": "backward"}]
        write_json(self.path(a["outputs"][0]["path"]), {"assignment_id": a["assignment_id"], "scout_id": a["scout_id"], "mode": "snowball",
                                                        "units": [{"unit_id": ch["unit_id"], "family": "snowball", "queries": [], "items": items}],
                                                        "stop_reason": "exhausted", "tool_calls": 2})

    def do_screen(self, a):
        lines = []
        for e in a["inputs"]["entities"]:
            out_ = "omega" in e["entity_id"]
            lines.append({"entity_id": e["entity_id"], "decision": "exclude" if out_ else "include",
                          "reason_code": "EX-OUT-OF-SCOPE" if out_ else "IN", "duplicate_of": None, "note": "", "screener": a["scout_id"]})
        write_jsonl(self.path(a["outputs"][0]["path"]), lines)

    def do_mapping(self, a):
        vals = lambda ids: [{"id": i, "label": i, "definition": "Definition of %s." % i} for i in ids]  # noqa: E731
        write_json(self.path("landscape/classification.json"), {
            "assignment_id": a["assignment_id"],
            "facets": {"approach": vals(["horizontal-saas", "vertical-saas", "forum"]), "category": vals(["invoicing", "community"]),
                       "segment": vals(["solo", "agency"]), "pricing_model": vals(["subscription", "free"]),
                       "platform": vals(["web"]), "deployment": vals(["cloud"])},
            "competing_factors": [{"id": "CF01", "label": "Price", "definition": "Monthly price"},
                                  {"id": "CF02", "label": "Reminders", "definition": "Automatic payment reminders"},
                                  {"id": "CF03", "label": "Currencies", "definition": "Multi-currency support"}]})
        lines = []
        for i, e in enumerate(a["inputs"]["entities"]):
            prod = e["kind"] == "product"
            lines.append({"entity_id": e["entity_id"], "approach": "vertical-saas" if prod and i % 2 else ("horizontal-saas" if prod else "forum"),
                          "category": "invoicing" if prod else "community", "segments": ["solo"] if i % 2 else ["agency"],
                          "pricing": {"model": "subscription" if prod else "free", "min_paid_month": 12 + i if prod else None, "currency": "USD",
                                      "free_tier": False, "per_seat": False, "snapshot": e["snapshot"]},
                          "platform": ["web"], "deployment": "cloud", "languages": ["en"], "integrations": [],
                          "evidence": [e["snapshot"]], "signals": {"ratings_count": 10 * i}})
        write_jsonl(self.path("landscape/entity-attributes.jsonl"), lines)

    # ---- evidence
    def do_evidence(self, a):
        sid = a["scout_id"]
        recs = []
        offset = {"A": 0, "B": 1, "C": 2}[sid]
        for k in range(offset, 48, 3):
            pattern, stype = DOMAINS[k % len(DOMAINS)]
            url = pattern % k
            code, out_ = gs("snapshot", self.run, url, "--by", "miner-" + sid)
            sha = out_.split()[0]
            stance, strength, _t, quote = QUOTES[k % len(QUOTES)]
            recs.append({"url": url, "source": "web", "source_type": stype, "snapshot": sha, "quote": quote,
                         "stance": stance, "strength": strength, "credibility": "independent",
                         "author_hash": privacy.author_hash(self.run, stype, "user%d" % (k % 11)),
                         "posted_at": "2026-0%d-1%d" % (1 + k % 8, k % 9), "entity_ids": ["dom:alpha.io"] if stance == "praise" else []})
        write_jsonl(self.path(a["outputs"][0]["path"]), recs)
        if sid == "C":
            gs("fetch", self.run, "hn-counts", "--query", "late payment invoice", "--from", "2024-01", "--to", "2025-12", "--by", "miner-C")
            code, out_ = gs("snapshot", self.run, "https://news.example.org/regulation", "--by", "miner-C")
            sha = out_.split()[0]
            write_jsonl(self.path(a["outputs"][1]["path"]), [{
                "factor": "legal", "change": "EU e-invoicing mandate requires structured invoices for B2B sales", "date": "2026-01",
                "url": "https://news.example.org/regulation", "snapshot": sha,
                "quote": "the e-invoicing mandate requires structured invoices for all B2B sales in the EU",
                "job_unlocked": "Send compliant structured invoices", "strength": "strong"}])

    # ---- coding
    CODES = [("J-INVOICE", "job", "Send and track invoices"), ("O-FAST-PAY", "outcome", "Minimize the time it takes to get paid"),
             ("P-LATE-PAY", "pain", "Late payments need manual chasing"), ("P-CURRENCY", "pain", "Currency handling breaks invoices"),
             ("S-SOLO", "segment", "Solo freelance translators"), ("S-AGENCY", "segment", "Translation agencies as clients"),
             ("G-AUTO", "gain", "Automation saves time")]

    def do_open(self, a):
        codes = [{"id": i, "type": t, "label": l, "definition": "Records about: %s." % l, "include": "Explicit mention.", "exclude": "Unrelated."}
                 for i, t, l in self.CODES]
        write_json(self.path(a["outputs"][0]["path"]), {"version": 1, "codes": codes})

    def do_revise(self, a):
        # Revise mode: sharpen the codes the run sent back, using the disagreements it lists.
        inp = a["inputs"]
        self.revise_inputs = inp
        book = read_json(self.path(inp["current_codebook"]))
        targets = set(x["code"] for x in inp["codes_to_revise"])
        codes = [dict(x, include="Sharpened after the disagreements: the author works alone." if x["id"] in targets else x["include"])
                 for x in book["codes"] if x["id"][:2] not in ("X-", "F-", "T-")]
        write_json(self.path(a["outputs"][0]["path"]), {"version": book["version"] + 1, "codes": codes})

    @staticmethod
    def code_quote(q):
        ql = q.lower()
        codes = ["J-INVOICE"]
        if "late" in ql or "chase" in ql or "unpaid" in ql:
            codes += ["P-LATE-PAY", "O-FAST-PAY"]
        if "currency" in ql:
            codes.append("P-CURRENCY")
        if "solo" in ql or "my" in ql or " me " in ql:
            codes.append("S-SOLO")
        if "agenc" in ql:
            codes.append("S-AGENCY")
        if "automatic" in ql or "saved" in ql:
            codes.append("G-AUTO")
        if "switched" in ql:
            codes += ["F-PUSH", "T-DECIDE"]
        return codes

    def _code(self, a, coder, drop=()):
        v = int(a["inputs"]["codebook"].split(".v")[1].split(".")[0])
        lines = [{"evidence_id": r["id"], "coder": coder, "codebook_version": v,
                  "codes": [x for x in self.code_quote(r["quote"]) if x not in drop],
                  "strength": {q[3]: q[1] for q in QUOTES}.get(r["quote"], "S1"), "outcome_statement": None, "intensity": 2,
                  "new_code_proposals": []}
                 for r in a["inputs"]["records"]]
        write_jsonl(self.path(a["outputs"][0]["path"]), lines)

    def do_closed(self, a):
        self._code(a, "A")

    def do_reliability(self, a):
        # Under codebook v1 coder B never sees S-SOLO in the quotes, so its alpha fails and the run must revise.
        v = int(a["inputs"]["codebook"].split(".v")[1].split(".")[0])
        self._code(a, "B", drop={"S-SOLO"} if v == 1 else ())

    # ---- synthesis
    def do_supply(self, a):
        lines = []
        for i, e in enumerate(a["inputs"]["entities"]):
            lines.append({"entity_id": e["entity_id"], "jobs_served": ["J-INVOICE"], "factor_levels": {"CF01": 1 + i % 3, "CF02": i % 2, "CF03": 0},
                          "evidence": [e["snapshot"]]})
        write_jsonl(self.path("analysis/supply.jsonl"), lines)

    def do_synthesis(self, a):
        led = [r for r in read_jsonl(self.path("evidence/ledger.jsonl"))[0] if r["verification"]["status"] == "verified"]
        late = [r["id"] for r in led if "late payment" in r["quote"].lower() or "chase" in r["quote"].lower() or "unpaid" in r["quote"].lower()]
        cur = [r["id"] for r in led if "currency" in r["quote"].lower()]
        wtp = [r["id"] for r in led if r["stance"] == "wtp"]
        praise = [r["id"] for r in led if r["stance"] == "praise"]
        common = {"picos": {"population": "Solo freelance translators", "intervention": "Invoicing and payment follow-up",
                            "comparator": "Generic invoicing suites and spreadsheets", "outcomes": ["O-FAST-PAY"], "setting": "Web, EU clients"},
                  "robinson_reason": "insufficient", "egm_type": "absolute", "segment_codes": ["S-SOLO"],
                  "why_empty": "Incumbents target agencies and accountants, not solo translators.", "origin_methods": ["D16", "D17", "D20"],
                  "status": "candidate"}
        cards = [
            dict(common, gap_id="GAP-001", title="Automatic late-payment chasing for solo translators",
                 statement="Although invoicing tools exist, automatic multilingual chasing of late payments for solo translators remains unserved, because incumbents target agencies. This matters because late payments cost solo translators hours every month.",
                 gap_type={"primary": "feature", "secondary": ["segment"], "catalyst": "regulation"}, sa_mode="neglect",
                 codes=["J-INVOICE", "O-FAST-PAY", "P-LATE-PAY"], incumbents=["dom:alpha.io"],
                 supporting_evidence=(late + wtp)[:14], counter_evidence=praise[:2], why_now=["WN-001"],
                 demand_signals=["SIG-hn-late-payment-invoice"],
                 assumptions=[{"id": "A1", "text": "Solo translators will pay for automatic chasing", "type": "viability", "riskiest_test": "pre-sale"}]),
            dict(common, gap_id="GAP-002", title="Currency-safe invoicing for translators with foreign clients",
                 statement="Although multi-currency invoicing exists, rounding-safe currency handling for translators invoicing foreign agencies remains poorly served, because tools are built for domestic invoicing. This matters because broken invoices delay payment.",
                 gap_type={"primary": "quality", "secondary": [], "catalyst": "none"}, sa_mode="confusion", egm_type="none",
                 codes=["J-INVOICE", "P-CURRENCY"], incumbents=["dom:bravo.io"], supporting_evidence=(cur + wtp)[:12],
                 counter_evidence=[], why_now=[], demand_signals=[],
                 assumptions=[{"id": "A1", "text": "Currency errors are frequent enough to switch tools", "type": "desirability", "riskiest_test": "interviews"}]),
        ]
        write_jsonl(self.path("gaps/cards.jsonl"), cards)

    def do_redteam(self, a):
        for o in a["outputs"]:
            gid = os.path.basename(o["path"]).replace(".json", "")
            write_json(self.path(o["path"]), {
                "gap_id": gid, "verdict": "survives" if gid == "GAP-001" else "weakened",
                "existing_solutions": [{"name": "Alpha Invoices", "url": "https://www.alpha.io/", "snapshot": None, "covers": "partial"}],
                "failed_attempts": [], "why_empty": "Small segment overlooked by suites built for agencies.",
                "five_forces": {"rivalry": "medium", "new_entrants": "medium", "substitutes": "high", "buyer_power": "medium", "supplier_power": "low"},
                "premortem": ["Too small a niche", "Clients ignore reminders", "Payment providers copy the feature"],
                "evidence": [], "searches": [{"source": "web", "query": "q%d" % i, "results": 3} for i in range(3)],
                "judgment": {"regulatory_load": "low", "human_ops_burden": "low", "agent_buildability": "yes", "platform_risk": 1,
                             "tos_feasible": True, "right_to_win": 2,
                             "reach_channels": [{"channel": "Translators Hub", "type": "community", "url": COMMUNITY[0], "size": 12000, "evidence": []},
                                                {"channel": "invoice reminder translators", "type": "keyword", "url": "https://example.org/kw", "size": 900, "evidence": ["EV-000001"]}],
                             "rationale": {k: "Reasoned from the evidence." for k in ("regulatory_load", "human_ops_burden", "agent_buildability", "platform_risk", "right_to_win")}}})

    def do_sizing(self, a):
        g = {}
        for gid in a["inputs"]["cards"]:
            g[gid] = {"accounts": {"low": 20000, "base": 40000, "high": 60000, "source": "https://example.org/translator-census"},
                      "arpa_year_usd": {"low": 96, "base": 144, "high": 240, "source": "price ladder median"},
                      "reachable_share": {"low": 0.1, "base": 0.2, "high": 0.3, "rationale": "communities reachable"},
                      "conversion": {"low": 0.02, "base": 0.04, "high": 0.06, "rationale": "assumption", "assumption": True},
                      "win_rate": {"low": 0.3, "base": 0.5, "high": 0.6, "rationale": "assumption", "assumption": True}}
        write_json(self.path("gaps/sizing-inputs.json"), {"assignment_id": a["assignment_id"], "gaps": g})

    # ---- writer
    def do_write(self, a):
        rk = read_json(self.path("gaps/ranking.json"))
        cert = read_json(self.path("gaps/certainty.json"))["gaps"]
        led = {r["id"]: r for r in read_jsonl(self.path("evidence/ledger.jsonl"))[0]}
        cards = {c["gap_id"]: c for c in read_jsonl(self.path("gaps/cards.jsonl"))[0]}
        opps = []
        lines = ["# Market gap dossier", "", "## Bottom line", ""]
        for x in rk["ranked"]:
            card = cards[x["gap_id"]]
            ids = [i for i in card["supporting_evidence"] if led[i]["verification"]["status"] == "verified"][:3]
            ct = cert[x["gap_id"]]
            opps.append({"rank": x["rank"], "gap_id": x["gap_id"], "title": x["title"], "statement": card["statement"], "score": x["total"],
                         "p_top3": x["p_top3"], "certainty": {"pain": ct["pain"], "demand": ct["demand"], "demand_strength": ct["demand_strength"]},
                         "icp": {"description": "Solo translators", "where_they_gather": [COMMUNITY[0]]},
                         "jtbd": {"job": "Get paid on time", "outcomes": ["O-FAST-PAY"]},
                         "top_quotes": [{"evidence_id": i, "quote": led[i]["quote"], "url": led[i]["url"]} for i in ids],
                         "competitors": card["incumbents"], "pricing_hypothesis": {"model": "subscription", "basis": "price ladder"},
                         "mvp": {"in_scope": ["reminders"], "out_of_scope": ["accounting"], "agent_buildability": "yes"},
                         "experiments": [{"id": "EXP-01", "assumption_id": "A1", "type": "smoke-test", "hypothesis_xyz": "At least 8% of translators visiting will join", "metric": "signup rate"}],
                         "gtm_channels": [COMMUNITY[0]], "kill_criteria": ["Fewer than 4% sign up"], "risks": ["small niche"], "assumptions": card["assumptions"]})
            lines += ["### #%d %s (%s)" % (x["rank"], x["title"], x["gap_id"]), "Evidence: " + ", ".join(ids), ""]
        lines += ["## Coverage and limitations", "", "The landscape is a lower bound: at least the products listed exist.", "",
                  "## PRISMA flow", "", "See output/prisma.md."]
        with open(self.path("output/dossier.md"), "w") as fh:
            fh.write("\n".join(lines))
        prot = read_json(self.path("protocol.lock.json"))
        write_json(self.path("output/handoff.json"), {"schema_version": "1.0", "run_id": os.path.basename(self.run), "generated_at": "2026-10-09T00:00:00Z",
                                                      "protocol_sha256": prot["sha256"],
                                                      "coverage": {"landscape": {}, "themes": {}, "independence": "full", "coverage_gaps": []},
                                                      "opportunities": opps, "limitations": ["desk evidence only"]})
        write_json(self.path("output/watchlist.json"), {"run_id": os.path.basename(self.run), "generated_at": "2026-10-09T00:00:00Z",
                                                        "rerun_cadence_days": 30, "items": [{"kind": "competitor", "target": "dom:alpha.io", "why": "closest incumbent"}]})

    do_fix = do_write


class DiscoveryE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run_dir = os.path.join(self.tmp, "example-translators")
        self._orig = (net._raw_get, net._rate_limit)
        net._raw_get = fake_raw_get
        net._rate_limit = lambda run, host, interval: None
        os.environ.pop("MGD_CONTACT", None)

    def tearDown(self):
        net._raw_get, net._rate_limit = self._orig
        shutil.rmtree(self.tmp)

    def test_full_run_reaches_done(self):
        run = self.run_dir
        self.assertEqual(gs("init", run, "--topic", "invoicing for freelance translators", "--seed", "11")[0], 0)
        agents = FakeAgents(run)
        trace = []
        for _ in range(400):
            try:
                flow.decide(run)
                self.fail("decide must raise an action")
            except flow.Act as act:
                trace.append(act.verdict + " " + act.argline[:80])
                if act.verdict == "DONE":
                    break
                if act.verdict == "RUN":
                    argv = act.argline.split()[1:]
                    if argv[0] == "doctor":
                        argv.append("--offline")
                    code, out_ = gs(*argv)
                    self.assertEqual(code, 0, "command failed: %s\n%s\ntrace tail: %s" % (" ".join(argv), out_, trace[-6:]))
                elif act.verdict == "SPAWN":
                    for path in act.argline.split()[2:]:
                        agents.handle(path)
                elif act.verdict == "DO" and act.argline.startswith("D01"):
                    ex = read_json(os.path.join(DISC, "assets", "templates", "protocol.example.json"))
                    ex["run_id"] = os.path.basename(run)
                    ex["seed"] = 11
                    write_json(os.path.join(run, "protocol.json"), ex)
                else:
                    self.fail("unexpected action %s %s\n%s" % (act.verdict, act.argline, act.notes))
        else:
            self.fail("did not finish; trace tail: %s" % trace[-10:])
        self.assertTrue(trace[-1].startswith("DONE"), trace[-5:])
        sat = read_json(os.path.join(run, "landscape", "saturation.json"))
        self.assertEqual(sat["verdict"], "SATURATED")
        units = read_json(os.path.join(run, "landscape", "units.json"))
        # 9 units in round 1, 3 in round 2 and 1 probe: every unit id must be unique so T is right.
        self.assertEqual(sat["overall"]["T"], 13)
        self.assertEqual(len([u for u, m in units.items() if m["mode"] == "landscape"]), 12)
        self.assertTrue(any("PROBE" in t or "probe" in t for t in trace))
        check = read_json(os.path.join(run, "output", "report-check.json"))
        self.assertTrue(check["ok"], check)
        rk = read_json(os.path.join(run, "gaps", "ranking.json"))
        self.assertEqual([x["gap_id"] for x in rk["ranked"]][0], "GAP-001")
        prisma = read_json(os.path.join(run, "output", "prisma.json"))
        ents = [e for e in read_jsonl(os.path.join(run, "landscape", "entities.jsonl"))[0]]
        self.assertEqual(prisma["landscape"]["included_verified"],
                         sum(1 for e in ents if e["status"] == "included" and e["verified"]["status"] == "ok"))
        self.assertEqual(prisma["landscape"]["excluded_by_reason"].get("EX-OUT-OF-SCOPE"), 1)
        self.assertGreaterEqual(prisma["landscape"]["snowball_only"], 1)
        bursts = read_json(os.path.join(run, "evidence", "bursts.json"))
        self.assertTrue(any(s.get("significant") for s in bursts["series"]))
        agr = read_json(os.path.join(run, "coding", "agreement.json"))
        self.assertEqual(agr["verdict"], "accept")
        # One revision cycle: v1 failed on S-SOLO, the reviser saw the disagreements, v2 was recoded and accepted.
        self.assertEqual(agr["version"], 2)
        self.assertEqual(read_json(os.path.join(run, "state.json"))["coding"]["revisions"], 1)
        rev = agents.revise_inputs
        self.assertEqual([x["code"] for x in rev["codes_to_revise"]], ["S-SOLO"])
        self.assertTrue(any(d["code"] == "S-SOLO" and d["coder_a"] and not d["coder_b"] for d in rev["disagreements"]))
        v2_closed = read_json(sorted(glob.glob(os.path.join(run, "coding", "closed-assign-v2-*.json")))[0])
        self.assertTrue(v2_closed["inputs"].get("previous_codes"))
        # The coder brief re-grades strength with D10, so closed and reliability coders must be given it (a live run missed this).
        coder_assigns = (glob.glob(os.path.join(run, "coding", "closed-assign-*.json"))
                         + glob.glob(os.path.join(run, "coding", "reliability-assign-*.json")))
        self.assertGreaterEqual(len(coder_assigns), 2)
        for f in coder_assigns:
            reads = " ".join(read_json(f)["read"])
            for card in ("D10-", "D13-", "D14-"):
                self.assertIn(card, reads, f)
            self.assertTrue(all("strength" not in r for r in read_json(f)["inputs"]["records"]), f)  # no anchoring
        self.assertEqual(agr["strength_vs_miner"]["kappa"], 1.0)
        code, out_ = gs("validate", run)
        self.assertEqual(code, 0, out_)
        # Fewer than evidence.target_candidates cards passed and a near-miss failed only on evidence
        # counts, so the flow ran one targeted round on its own (a live run needed the human for this).
        st = read_json(os.path.join(run, "state.json"))
        self.assertEqual(st["evidence"].get("targeted_rounds"), 1)
        tgt = st["evidence"]["targeted"][0]
        ta = read_json(os.path.join(run, "evidence", "round-%02d" % tgt["round"], "assign-A.json"))
        self.assertEqual(ta["mode"], "evidence:targeted")
        self.assertIn(ta["inputs"]["target_card"]["gap_id"], tgt["cards"])
        self.assertTrue(any("NOT in target_card.domains" in r for r in ta["rules"]))
        # Every assignment carries a model tier; machine-checked roles run on the fast tier by default.
        self.assertEqual(ta["model"]["tier"], "fast")
        self.assertEqual(ta["model"]["names"]["claude-code"], "haiku")
        wa = read_json(os.path.join(run, "output", "writer-assign-01.json"))
        self.assertEqual(wa["model"]["tier"], "standard")
        self.assertTrue(any(t.startswith("SPAWN") for t in trace))
        # A gap map recomputed after the cards were checked (new evidence, revised codebook) makes `next`
        # rebuild the cards in update mode before any red team (a live run went straight to red team).
        from mgcore import state as mstate
        st = read_json(os.path.join(run, "state.json"))
        mstate.touch(st, "gapmap")
        write_json(os.path.join(run, "state.json"), st)
        for expect in ("variants", "--phase synthesis"):
            with self.assertRaises(flow.Act) as cm:
                flow.decide(run)
            self.assertIn(expect, cm.exception.argline)
            self.assertEqual(gs(*cm.exception.argline.split()[1:])[0], 0)
        sy = read_json(os.path.join(run, "gaps", "synth-assign.json"))
        prev = sy["inputs"]["previous_cards"]
        self.assertRegex(prev, r"^gaps/cards\.previous-\d+\.jsonl$")
        self.assertTrue(os.path.exists(os.path.join(run, prev)))
        self.assertFalse(os.path.exists(os.path.join(run, "gaps", "cards.jsonl")))
        # Supply records the codebook it was mapped under; a newer codebook makes `next` re-map it in
        # update mode (a live run revised the codebook after supply and new jobs looked unserved).
        st = read_json(os.path.join(run, "state.json"))
        self.assertEqual(st["groups"]["supply"]["codebook_version"], 2)
        st["groups"]["supply"]["codebook_version"] = 1
        write_json(os.path.join(run, "state.json"), st)
        with self.assertRaises(flow.Act) as cm:
            flow.decide(run)
        self.assertEqual(cm.exception.verdict, "RUN")
        self.assertIn("--phase supply", cm.exception.argline)
        self.assertEqual(gs("assign", run, "--phase", "supply")[0], 0)
        sa = read_json(os.path.join(run, "analysis", "supply-assign.json"))
        self.assertEqual(sa["inputs"]["previous_codebook_version"], 1)
        self.assertEqual(sa["inputs"]["previous_supply"], "analysis/supply.jsonl")
        self.assertTrue(any("Update mode" in r for r in sa["rules"]))


if __name__ == "__main__":
    unittest.main()
