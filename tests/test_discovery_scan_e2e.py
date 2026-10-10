"""End-to-end simulation of a scan-depth discovery run (method card D28): init --depth scan, one landscape
round, map, traction, opportunity scan, two evidence rounds by successive halving, red flags, ranking and the
script-written report, then a deep run drafted from the best option. Fake subagents, fake network."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import test_discovery_e2e as base  # noqa: E402
from test_discovery_e2e import DISC, DOMAINS, QUOTES, FakeAgents, fake_raw_get, gs

from mgd import flow, net, opportunities, privacy  # noqa: E402
from mgcore.jsonio import read_json, read_jsonl, write_json, write_jsonl  # noqa: E402


class ScanAgents(FakeAgents):
    def __init__(self, run):
        FakeAgents.__init__(self, run)
        self.spawned = {}

    def handle(self, apath):
        a = read_json(apath)
        self.spawned[a["role"]] = self.spawned.get(a["role"], 0) + 1
        FakeAgents.handle(self, apath)

    def do_mapping(self, a):
        FakeAgents.do_mapping(self, a)
        lines = []
        for i, line in enumerate(read_jsonl(self.path("landscape/entity-attributes.jsonl"))[0]):
            if line["category"] == "invoicing":
                # Two well-installed but poorly rated products (clone-wedge), all on the web (port to gmail-add-on),
                # one open-source self-hosted product (hosted-oss).
                line["platform"] = ["web"] if i % 3 else ["web", "wordpress-plugin"]
                line["signals"] = {"ratings_count": 40 + 25 * i, "rating_avg": 2.9 if i in (1, 2) else 4.6}
                if i == 4:
                    line.update(approach="horizontal-saas", deployment="self-hosted", license="MIT")
                    line["pricing"] = dict(line["pricing"], model="free", min_paid_month=None)
            lines.append(line)
        write_jsonl(self.path("landscape/entity-attributes.jsonl"), lines)

    def do_evidence(self, a):
        mode = a["mode"]
        sid = a["scout_id"]
        recs = []
        if mode == "evidence:opportunity":
            for j, cand in enumerate(a["inputs"]["candidates"]):
                for k in range(5):
                    n = 7 * (ord(sid) - 64) + 11 * j + k + 100 * a["inputs"]["scan_round"]
                    pattern, stype = DOMAINS[n % len(DOMAINS)]
                    url = pattern % n
                    sha = gs("snapshot", self.run, url, "--by", a["assignment_id"])[1].split()[0]
                    stance, strength, _t, quote = QUOTES[n % len(QUOTES)]
                    recs.append({"url": url, "source": "web", "source_type": stype, "snapshot": sha, "quote": quote,
                                 "stance": stance, "strength": strength, "credibility": "independent",
                                 "author_hash": privacy.author_hash(self.run, stype, "user%d" % (n % 13)),
                                 "posted_at": "2026-05-01", "entity_ids": list(cand.get("base_entities") or [])[:1],
                                 "candidate_ids": [cand["opp_id"], "OPP-999"] if k == 0 else [cand["opp_id"]]})
            write_jsonl(self.path(a["outputs"][0]["path"]), recs)
            return
        if mode == "evidence:leads":
            # Two authors who pay an assistant for the job: the productize lens fires on the second scan pass.
            for n in (3, 11, 19):
                pattern, stype = DOMAINS[n % len(DOMAINS)]
                url = pattern % n
                sha = gs("snapshot", self.run, url, "--by", a["assignment_id"])[1].split()[0]
                stance, strength, _t, quote = QUOTES[n % len(QUOTES)]
                recs.append({"url": url, "source": "web", "source_type": stype, "snapshot": sha, "quote": quote, "stance": stance,
                             "strength": strength, "credibility": "independent",
                             "author_hash": privacy.author_hash(self.run, stype, "lead%d" % n), "posted_at": "2026-04-01",
                             "entity_ids": ["dom:alpha.io"]})
            write_jsonl(self.path(a["outputs"][0]["path"]), recs)
            write_jsonl(self.path(a["outputs"][1]["path"]), [])
            return
        FakeAgents.do_evidence(self, a)

    def do_redflag(self, a):
        for i, opt in enumerate(a["inputs"]["options"]):
            write_json(self.path(a["outputs"][i]["path"]), {
                "opp_id": opt["opp_id"], "verdict": "flag" if i == 1 else "clear",
                "existing": [{"name": "Alpha Invoices", "url": "https://www.alpha.io/", "snapshot": None, "covers": "partial"}],
                "searches": [{"source": "web", "query": "q%d" % k, "results": 4} for k in range(2)],
                "gates": {"regulatory_load": "low", "human_ops_burden": "low", "agent_buildability": "yes", "platform_risk": 1,
                          "tos_feasible": True},
                "growth_loop": {"type": "powered-by", "note": "Reminder emails carry a small footer link."},
                "note": "Partial overlap with Alpha Invoices; the wedge looks open."})


class ScanE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run_dir = os.path.join(self.tmp, "scan-translators")
        self._orig = (net._raw_get, net._rate_limit)
        net._raw_get = fake_raw_get
        net._rate_limit = lambda run, host, interval: None
        os.environ.pop("MGD_CONTACT", None)

    def tearDown(self):
        net._raw_get, net._rate_limit = self._orig
        shutil.rmtree(self.tmp)

    def drive(self, run, agents, limit=300):
        trace = []
        for _ in range(limit):
            try:
                flow.decide(run)
                self.fail("decide must raise an action")
            except flow.Act as act:
                trace.append(act.verdict + " " + act.argline[:90])
                if act.verdict == "DONE":
                    return trace, act
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
                    ex.update(run_id=os.path.basename(run), seed=11, depth="scan")
                    ex["budget"] = {"subagents_max": 30, "fetches_max": 3000}
                    write_json(os.path.join(run, "protocol.json"), ex)
                else:
                    self.fail("unexpected action %s %s\n%s\n%s" % (act.verdict, act.argline, act.notes, trace[-6:]))
        self.fail("did not finish; trace tail: %s" % trace[-10:])

    def test_scan_run_reaches_done_cheaply(self):
        run = self.run_dir
        code, out_ = gs("init", run, "--topic", "invoicing for freelance translators", "--seed", "11", "--depth", "scan")
        self.assertEqual(code, 0, out_)
        self.assertEqual(read_json(os.path.join(run, "protocol.json"))["depth"], "scan")
        agents = ScanAgents(run)
        trace, done = self.drive(run, agents)
        joined = "\n".join(trace)
        # Scan skips PRESS, snowballing, the screening audit, coding, gap cards and the writer subagent.
        for phase in ("--phase press", "--phase snowball", "--phase coding", "--phase synthesis", "--phase writer", "screen-audit"):
            self.assertNotIn(phase, joined)
        self.assertIn("traction", joined)
        self.assertIn("opportunities report", joined)
        st = read_json(os.path.join(run, "state.json"))
        self.assertEqual(st["landscape"]["round"], 1)
        self.assertEqual(st["landscape"]["verdict"], "STOP_UNSATURATED")
        # Successive halving: round 2 re-tests the better half of the options that have evidence (round-1 tests plus
        # evidence-led options the leads miner surfaced).
        scan = st["evidence"]["scan"]
        self.assertEqual([x["scan_round"] for x in scan], [1, 2])
        self.assertTrue(scan[0]["leads"])
        self.assertLessEqual(len(scan[1]["candidates"]), (scan[1]["pool"] + 1) // 2)
        self.assertLess(len(scan[1]["candidates"]), scan[1]["pool"])
        used = st["budget"]["subagents_used"]
        self.assertLessEqual(used, 20, agents.spawned)
        self.assertNotIn("coder", agents.spawned)
        self.assertNotIn("writer", agents.spawned)
        # Every lens that the fixture sets up fires: clone-wedge (installed, low-rated), port (gmail-add-on has no
        # product), hosted-oss (MIT, self-hosted), and productize from the leads miner on the second pass.
        cands = read_jsonl(os.path.join(run, "opportunities", "candidates.jsonl"))[0]
        lenses = set(c["lens"] for c in cands)
        for lens in ("clone-wedge", "port", "hosted-oss", "productize"):
            self.assertIn(lens, lenses, sorted(lenses))
        self.assertTrue(any(c["lens"] == "port" and (c["twist"] or {}).get("to") == "gmail-add-on" for c in cands))
        # Unknown option ids are dropped at merge; tags survive.
        led = read_jsonl(os.path.join(run, "evidence", "ledger.jsonl"))[0]
        self.assertTrue(all("OPP-999" not in (r.get("candidate_ids") or []) for r in led))
        self.assertTrue(any(r.get("candidate_ids") for r in led))
        rk = read_json(os.path.join(run, "opportunities", "ranking.json"))
        self.assertGreaterEqual(len(rk["ranked"]), 3)
        self.assertEqual(rk["ranked"][0]["status"], "promising")
        rep = read_json(os.path.join(run, "output", "opportunities.json"))
        self.assertTrue(rep["next_runs"])
        with open(os.path.join(run, "output", "opportunities.md"), encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("## Top options", md)
        self.assertIn("Ambition math", md)
        prisma = read_json(os.path.join(run, "output", "prisma.json"))
        self.assertIn("opportunities", prisma)
        self.assertTrue(any("opportunities.md" in n for n in done.notes))
        self.assertEqual(gs("validate", run)[0], 0)
        # A narrow deep run drafted from the best option: valid protocol, depth deep, its lens first.
        opp = rep["next_runs"][0]
        deep = os.path.join(self.tmp, "deep-from-scan")
        code, out_ = gs("init", deep, "--from-run", run, "--opportunity", opp, "--seed", "5")
        self.assertEqual(code, 0, out_)
        proto = read_json(os.path.join(deep, "protocol.json"))
        self.assertEqual(proto["depth"], "deep")
        self.assertEqual(proto["run_id"], "deep-from-scan")
        lens = [c for c in cands if c["opp_id"] == opp][0]["lens"]
        self.assertEqual(proto["lenses"][0], lens)
        code, out_ = gs("protocol", "check", deep)
        self.assertEqual(code, 0, out_)


if __name__ == "__main__":
    unittest.main()

_ = base
