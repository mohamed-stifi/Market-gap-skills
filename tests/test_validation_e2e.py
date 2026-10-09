"""End-to-end simulation of the validation skill: fake designer/builder/analyst subagents and a
simulated human operator (approves, deploys, posts, exports data) drive `gapval.py next` to a
deterministic verdict. Also checks tamper detection and the honesty checks on landing pages."""

import contextlib
import csv
import io
import json
import os
import random
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAL = os.path.join(ROOT, "skills", "market-gap-validation")
sys.path.insert(0, os.path.join(VAL, "scripts"))

import gapval  # noqa: E402
from mgcore import hq  # noqa: E402
from mgcore.jsonio import read_json, write_json  # noqa: E402
from mgv import flow  # noqa: E402

LANDING = """<!doctype html><html><body data-experiment="EXP-02"><h1>Get paid on time, in your clients' language</h1>
<p>Automatic, polite payment reminders for solo translators.</p><p>Plans from $15/month, up to 3 users.</p>
<form><input type="email" name="contact" required><label><input type="checkbox" id="consent" required> I agree to be contacted about early access.</label>
<button>Join the waitlist</button></form>
<section id="disclosure" hidden><p>We have not built this yet. Join the waitlist and we will tell you when it is ready.</p></section>
<a href="privacy.html">Privacy notice</a></body></html>"""


def gv(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = gapval.main([str(a) for a in argv])
    return code, buf.getvalue()


def card(exp, type_, aid, rule, level, **kw):
    base = {"id": exp, "assumption_ids": [aid], "solution_id": "SOL-1", "type": type_,
            "hypothesis": {"we_believe": "Solo translators want this enough to act", "to_verify": "we will run %s" % type_,
                           "measure": "the pre-registered metric", "right_if": "the decision rule passes"},
            "xyz": {"x": 0.0, "y": "solo translators", "z": "act"}, "metric": {"name": "rate", "numerator": "k", "denominator": "n"},
            "evidence_level": level, "success_threshold": 0.0, "kill_threshold": 0.0, "planning_p": None, "half_width": None,
            "min_n": 100, "decision_rule": rule, "price_point_month_usd": None, "criteria": {}, "duration_days": 14, "budget_usd": 0,
            "channels": [], "ethics": {"disclosure": True, "consent": True, "no_charge_without_consent": True, "privacy_notice": True,
                                       "exposure_limit": "max 500 visitors"},
            "required_ht": [], "on_pass": "continue", "on_fail": "iterate", "on_inconclusive": "extend", "pivot_hypothesis": None,
            "x_derivation": "Needed 40 customers from 500 reachable visitors at 50% trial-to-paid: 8% sign-up.", "status": "draft"}
    base.update(kw)
    return base


class FakeValidationAgents(object):
    def __init__(self, run):
        self.run = run

    def handle(self, apath):
        a = read_json(apath)
        getattr(self, "do_" + a["mode"].replace("-", "_"))(a)

    def do_ost(self, a):
        ice = {"impact": 8, "confidence": 5, "ease": 6}
        sols = []
        for i, concept in enumerate(["Automatic multilingual reminders", "Concierge chasing service", "Invoice templates with payment links"], 1):
            sols.append({"id": "SOL-%d" % i, "concept": concept, "differentiator": "Built for solo translators",
                         "assumptions": [{"id": "A%d" % (3 * i - 2), "text": "Translators sign up when they see it", "type": "desirability", "importance": 5, "evidence": 1, "ice": ice},
                                         {"id": "A%d" % (3 * i - 1), "text": "They pay about 15 USD per month", "type": "viability", "importance": 5, "evidence": 0, "ice": ice},
                                         {"id": "A%d" % (3 * i), "text": "Reminders can be generated in FR, DE, ES", "type": "feasibility", "importance": 3, "evidence": 2, "ice": ice}]})
        write_json(os.path.join(self.run, "validation", "ost.json"), {
            "assignment_id": a["assignment_id"], "outcome": {"metric": "Days sales outstanding for solo translators", "target": "-30%", "why": "late payments"},
            "opportunity": {"gap_id": None, "statement": "Solo translators lose hours chasing late payments from agencies", "evidence_ids": []},
            "solutions": sols, "target_solution": "SOL-1"})

    def do_design(self, a):
        for item in a["inputs"]["plan"]:
            exp, aid = item["experiment"], item["assumption"]
            if aid == "A2":
                c = card(exp, "pricing-survey", aid, "van-westendorp", "survey", criteria={"price_point_month_usd": 15},
                         required_ht=["post:survey-link"], on_fail="pivot", pivot_hypothesis="Agencies pay instead of translators")
            elif aid == "A1":
                c = card(exp, "smoke-test", aid, "wilson", "email", success_threshold=0.08, kill_threshold=0.04, xyz={"x": 0.08, "y": "solo translators", "z": "join the waitlist"},
                         planning_p=0.08, half_width=0.04, min_n=180, channels=["translators-hub", "newsletter"],
                         required_ht=["deploy-landing", "post:translators-hub", "post:newsletter"], on_fail="kill")
            else:
                c = card(exp, "tech-spike", aid, "criteria", "prototype", criteria={"acceptance_tests": ["reminders in FR DE ES", "detect overdue invoices"]}, min_n=1)
            write_json(os.path.join(self.run, "validation", "prereg", exp + ".json"), c)

    def do_assets(self, a):
        for o in a["outputs"]:
            path = os.path.join(self.run, o["path"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(LANDING if path.endswith("landing.html") else "# Draft\nHonest draft for the human to review.\n")

    def do_report(self, a):
        verdict = read_json(os.path.join(self.run, "validation", "verdict.json"))
        for o in a["outputs"]:
            if "learning-cards" in o["path"]:
                exp = os.path.basename(o["path"]).replace(".json", "")
                res = [e for e in verdict["experiments"] if e["id"] == exp][0]
                write_json(os.path.join(self.run, o["path"]), {"experiment_id": exp, "result": res["result"],
                                                               "we_believed": "We believed the assumption holds",
                                                               "we_observed": "We observed the pre-registered metric",
                                                               "we_learned": "We learned from the frozen rule result",
                                                               "therefore": "Therefore we follow the pre-registered action", "evidence_level": res["level"]})
        with open(os.path.join(self.run, "validation", "report.md"), "w") as fh:
            fh.write("# Validation report\n\nVerdict: %s\n" % verdict["verdict"])
        write_json(os.path.join(self.run, "validation", "validated-handoff.json"), {
            "schema_version": "1.0", "generated_at": "2026-10-09T00:00:00Z", "gap_id": None, "source_handoff_sha256": None,
            "verdict": verdict["verdict"], "assumptions": [{"id": x["id"], "status": x["status"]} for x in verdict["assumptions"]],
            "experiments": [{"id": e["id"], "result": e["result"]} for e in verdict["experiments"]],
            "demand_strength": verdict["demand_strength"], "validated_icp": {}, "price": {"month_usd": 15}, "channels": [],
            "next_steps": ["Build the MVP"], "watchlist": {"pmf_survey": "after launch, >= 40 responses"}})

    do_fix = do_report


class Human(object):
    """Simulated operator: approves, deploys, posts and exports pseudonymous data."""

    def __init__(self, run, signups=30):
        self.run = run
        self.signups = signups

    def act(self, task_id):
        t = [x for x in hq.load(self.run)["tasks"] if x["id"] == task_id][0]
        title = t["title"]
        note = "done"
        if "deploy" in title:
            note = "deployed at https://landing.example.org/"
        if "export results" in title:
            exp = title.split(":")[0]
            self._export(exp)
        hq.close(self.run, task_id, "done", note)

    def _csv(self, path, header, rows):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)

    def _export(self, exp):
        c = read_json(os.path.join(self.run, "validation", "prereg", exp + ".json"))
        d = os.path.join(self.run, "validation", "data", exp)
        if c["type"] == "smoke-test":
            self._csv(os.path.join(d, "visits.csv"), ["channel", "visitors"], [["translators-hub", 120], ["newsletter", 80]])
            hub = (self.signups * 3) // 5
            self._csv(os.path.join(d, "signups.csv"), ["channel", "signups"], [["translators-hub", hub], ["newsletter", self.signups - hub]])
        elif c["type"] == "pricing-survey":
            rng = random.Random(5)
            rows = []
            for i in range(120):
                tc = rng.randint(3, 6)
                ch = tc + rng.randint(3, 6)
                ex = ch + rng.randint(8, 14)
                te = ex + rng.randint(6, 12)
                rows.append(["r%03d" % i, tc, ch, ex, te])
            self._csv(os.path.join(d, "survey-vw.csv"), ["respondent", "too_cheap", "cheap", "expensive", "too_expensive"], rows)
        elif c["type"] == "tech-spike":
            self._csv(os.path.join(d, "spike.csv"), ["test", "passed"], [["reminders in FR DE ES", "true"], ["detect overdue invoices", "true"]])


def drive(test, run, agents, human, max_steps=200):
    trace = []
    for _ in range(max_steps):
        try:
            flow.decide(run)
            test.fail("decide must raise")
        except flow.Act as act:
            trace.append(act.verdict + " " + act.argline[:90])
            if act.verdict == "DONE":
                return trace
            if act.verdict == "RUN":
                code, out_ = gv(*act.argline.split()[1:])
                test.assertEqual(code, 0, "%s failed:\n%s\n%s" % (act.argline, out_, trace[-5:]))
            elif act.verdict == "SPAWN":
                for path in act.argline.split()[2:]:
                    agents.handle(path)
            elif act.verdict == "BLOCKED":
                human.act(act.argline)
            elif act.verdict == "DO" and "utm" in act.argline:
                gv("utm", run, "--experiment", "EXP-02", "--base-url", "https://landing.example.org/", "--channels", "translators-hub,newsletter")
            else:
                test.fail("unexpected %s %s %s" % (act.verdict, act.argline, act.notes))
    test.fail("no DONE; tail %s" % trace[-8:])


class ValidationE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run = os.path.join(self.tmp, "idea-run")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_go_verdict(self):
        self.assertEqual(gv("init", self.run, "--idea", "Automatic multilingual late-payment chasing for solo translators")[0], 0)
        trace = drive(self, self.run, FakeValidationAgents(self.run), Human(self.run, signups=30))
        verdict = read_json(os.path.join(self.run, "validation", "verdict.json"))
        self.assertEqual(verdict["verdict"], "GO", verdict["reasons"])
        self.assertEqual(verdict["demand_strength"], "moderate")
        res = {e["id"]: e["result"] for e in verdict["experiments"]}
        self.assertEqual(sorted(res.values()), ["PASS", "PASS", "PASS"])
        self.assertTrue(any(t.startswith("BLOCKED") for t in trace))  # the human approved and acted
        self.assertEqual(read_json(os.path.join(self.run, "validation", "validate-check.json"))["ok"], True)

    def test_kill_when_smoke_test_fails(self):
        gv("init", self.run, "--idea", "Automatic multilingual late-payment chasing for solo translators")
        drive(self, self.run, FakeValidationAgents(self.run), Human(self.run, signups=2))
        verdict = read_json(os.path.join(self.run, "validation", "verdict.json"))
        self.assertEqual(verdict["verdict"], "KILL", verdict["reasons"])

    def test_tampering_and_landing_honesty(self):
        gv("init", self.run, "--idea", "x idea for tamper test")
        agents = FakeValidationAgents(self.run)
        agents.do_ost({"assignment_id": "OST-1"})
        c = card("EXP-01", "smoke-test", "A1", "wilson", "email", success_threshold=0.08, kill_threshold=0.04,
                 xyz={"x": 0.08, "y": "t", "z": "join"}, planning_p=0.08, half_width=0.04, min_n=100,
                 channels=["hub"], required_ht=["deploy-landing"])
        write_json(os.path.join(self.run, "validation", "prereg", "EXP-01.json"), c)
        code, out_ = gv("prereg", "check", self.run, "EXP-01")
        self.assertEqual(code, 1)
        self.assertIn("below the sample size", out_)
        c["min_n"] = 180
        write_json(os.path.join(self.run, "validation", "prereg", "EXP-01.json"), c)
        self.assertEqual(gv("prereg", "freeze", self.run, "EXP-01")[0], 0)
        c = read_json(os.path.join(self.run, "validation", "prereg", "EXP-01.json"))
        c["success_threshold"] = 0.02  # moving the goalposts after freezing
        write_json(os.path.join(self.run, "validation", "prereg", "EXP-01.json"), c)
        self.assertEqual(gv("prereg", "verify", self.run)[0], 1)
        folder = os.path.join(self.run, "validation", "assets", "EXP-01")
        os.makedirs(folder)
        with open(os.path.join(folder, "landing.html"), "w") as fh:
            fh.write(LANDING.replace("EXP-02", "EXP-01").replace("Plans from", "Trusted by 2,000 translators. Plans from"))
        for f in ("privacy.md", "posts.md"):
            with open(os.path.join(folder, f), "w") as fh:
                fh.write("x")
        code, out_ = gv("assets", "check", self.run, "EXP-01")
        self.assertEqual(code, 1)
        self.assertIn("social proof", out_)


class InterviewFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run = os.path.join(self.tmp, "idea-run")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_standalone_interviews_end_to_end(self):
        gv("init", self.run, "--idea", "Automatic multilingual late-payment chasing for solo translators")
        FakeValidationAgents(self.run).do_ost({"assignment_id": "OST-1"})
        c = card("EXP-01", "problem-interviews", "A1", "themes", "interview", success_threshold=0.5, kill_threshold=0.3,
                 xyz={"x": 0.5, "y": "solo translators", "z": "describe chasing late payments in the last 3 months"},
                 min_n=10, criteria={"problem_codes": ["P-LATE-PAY"]}, required_ht=["recruit:translators-hub"])
        write_json(os.path.join(self.run, "validation", "prereg", "EXP-01.json"), c)
        self.assertEqual(gv("prereg", "freeze", self.run, "EXP-01")[0], 0)
        folder = os.path.join(self.tmp, "transcripts")
        os.makedirs(folder)
        for i in range(12):
            with open(os.path.join(folder, "int%02d.txt" % i), "w") as fh:
                fh.write("Interviewee %d: last month I chased two agencies for payment. " % i if i < 9 else "Interviewee %d: payments are fine." % i)
        with open(os.path.join(folder, "zz-leak.txt"), "w") as fh:
            fh.write("contact me at someone@example.org")
        self.assertEqual(gv("ingest", self.run, "--experiment", "EXP-01", "--kind", "interviews", "--file", folder)[0], 1)  # PII rejected
        os.remove(os.path.join(folder, "zz-leak.txt"))
        self.assertEqual(gv("ingest", self.run, "--experiment", "EXP-01", "--kind", "interviews", "--file", folder)[0], 0)
        self.assertEqual(gv("assign", self.run, "--phase", "interview-coding")[0], 0)
        book = read_json(os.path.join(self.run, "validation", "codebook.json"))
        self.assertIn("P-LATE-PAY", [x["id"] for x in book["codes"]])
        self.assertIn("F-PUSH", [x["id"] for x in book["codes"]])
        recs = [json.loads(l) for l in open(os.path.join(self.run, "validation", "data", "EXP-01", "interviews.jsonl"))]
        def code(rec, coder):
            has = "chased" in rec["text"]
            return {"record_id": rec["record_id"], "coder": coder, "codes": ["P-LATE-PAY", "F-PUSH"] if has else ["F-HABIT"]}
        with open(os.path.join(self.run, "validation", "data", "EXP-01", "codes-A.jsonl"), "w") as fh:
            fh.write("\n".join(json.dumps(code(r, "A")) for r in recs) + "\n")
        self.assertEqual(gv("assign", self.run, "--phase", "interview-reliability")[0], 0)
        sample = [json.loads(l) for l in open(os.path.join(self.run, "validation", "data", "EXP-01", "reliability-sample.jsonl"))]
        self.assertEqual(len(sample), 12)
        with open(os.path.join(self.run, "validation", "data", "EXP-01", "codes-B.jsonl"), "w") as fh:
            fh.write("\n".join(json.dumps(code(r, "B")) for r in sample) + "\n")
        self.assertEqual(gv("agreement", self.run)[0], 0)
        self.assertEqual(read_json(os.path.join(self.run, "validation", "agreement.json"))["EXP-01"]["verdict"], "accept")
        # If B's sample never contains a frequent code, that code is unmeasured: the verdict cannot be accept.
        bpath = os.path.join(self.run, "validation", "data", "EXP-01", "codes-B.jsonl")
        with open(bpath, "w") as fh:
            fh.write("\n".join(json.dumps(code(r, "B")) for r in sample if "chased" not in r["text"]) + "\n")
        self.assertEqual(gv("agreement", self.run)[0], 0)
        agr = read_json(os.path.join(self.run, "validation", "agreement.json"))["EXP-01"]
        self.assertEqual(agr["verdict"], "provisional")
        self.assertIn("P-LATE-PAY", agr["unmeasured_codes"])
        with open(bpath, "w") as fh:
            fh.write("\n".join(json.dumps(code(r, "B")) for r in sample) + "\n")
        self.assertEqual(gv("agreement", self.run)[0], 0)
        self.assertEqual(gv("themes", self.run)[0], 0)
        self.assertEqual(gv("stats", self.run, "--experiment", "EXP-01")[0], 0)
        res = read_json(os.path.join(self.run, "validation", "results", "EXP-01.json"))
        self.assertEqual((res["k"], res["n"]), (9, 12))
        self.assertEqual(res["result"], "INCONCLUSIVE")  # 9/12: Wilson 0.47-0.91 straddles X = 0.5
        self.assertTrue(res["saturation"]["saturated"])


if __name__ == "__main__":
    unittest.main()
