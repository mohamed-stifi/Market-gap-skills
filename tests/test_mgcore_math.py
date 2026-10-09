"""Unit tests for shared/mgcore math, using published worked examples as test vectors.

Run: python3 -m unittest discover tests
"""

import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared"))

from mgcore import assoc, bursts, reliability, richness, stats, survey, themes  # noqa: E402


class Chao2Tests(unittest.TestCase):
    # Chao & Colwell 2017 worked example: T=12, Q1=9, Q2=4, S_obs=27.
    def test_point_estimate_se_and_ci(self):
        r = richness.chao2(27, 12, 9, 4)
        self.assertAlmostEqual(r["estimate"], 36.28, places=2)
        self.assertAlmostEqual(r["se"], 8.31, places=2)
        self.assertAlmostEqual(r["ci_low"], 29.06, places=2)
        self.assertAlmostEqual(r["ci_high"], 68.77, places=2)

    def test_q2_zero_uses_bias_corrected_form(self):
        r = richness.chao2(20, 10, 5, 0)
        self.assertAlmostEqual(r["estimate"], 20 + 0.9 * 5 * 4 / 2.0)
        self.assertGreater(r["ci_high"], r["estimate"])

    def test_no_singletons_returns_observed(self):
        r = richness.chao2(15, 8, 0, 3)
        self.assertEqual(r["estimate"], 15)
        self.assertEqual(r["ci_low"], 15)

    def test_single_unit_does_not_extrapolate(self):
        self.assertEqual(richness.chao2(10, 1, 10, 0)["estimate"], 10)


class CoverageTests(unittest.TestCase):
    def test_chao_jost_coverage(self):
        self.assertAlmostEqual(richness.coverage(12, 9, 4, 102), 0.918, places=3)

    def test_units_for_target_coverage(self):
        self.assertEqual(richness.units_for_coverage(12, 9, 4, 102, 0.95), 7)
        # Check the solution: coverage after 7 more units reaches 0.95, after 6 it does not.
        self.assertGreaterEqual(richness.extrapolated_coverage(12, 9, 4, 102, 7), 0.95)
        self.assertLess(richness.extrapolated_coverage(12, 9, 4, 102, 6), 0.95)

    def test_units_for_coverage_already_met(self):
        self.assertEqual(richness.units_for_coverage(12, 1, 4, 102, 0.95), 0)

    def test_units_for_fraction(self):
        s_hat = richness.chao2(27, 12, 9, 4)["estimate"]
        self.assertAlmostEqual(richness.units_for_fraction(12, 9, 4, 27, s_hat, 0.9), 12.08, places=1)

    def test_webster_kemp(self):
        missed, sd = richness.two_source_missing(177, 265, 171)
        self.assertAlmostEqual(missed, 3.9, places=1)
        self.assertAlmostEqual(sd, 2.5, places=1)

    def test_frequency_counts(self):
        inc = {"a": {"u1"}, "b": {"u1", "u2"}, "c": {"u2"}, "d": {"u1", "u2", "u3"}}
        q, u = richness.frequency_counts(inc)
        self.assertEqual(q, {1: 2, 2: 1, 3: 1})
        self.assertEqual(u, 2 + 2 + 3)

    def test_jaccard(self):
        self.assertEqual(richness.jaccard({1, 2}, {2, 3}), 1 / 3.0)
        self.assertEqual(richness.jaccard(set(), set()), 1.0)


class WilsonTests(unittest.TestCase):
    def test_wilson_interval(self):
        lo, hi, p = stats.wilson(20, 100)
        self.assertAlmostEqual(lo, 0.133, places=3)
        self.assertAlmostEqual(hi, 0.289, places=3)
        self.assertEqual(p, 0.2)

    def test_decision_rule(self):
        self.assertEqual(stats.wilson_decision(20, 100, 0.10)["result"], "PASS")
        self.assertEqual(stats.wilson_decision(2, 100, 0.10)["result"], "FAIL")
        self.assertEqual(stats.wilson_decision(10, 100, 0.10)["result"], "INCONCLUSIVE")
        self.assertEqual(stats.wilson_decision(20, 50, 0.10, min_n=100)["result"], "INCONCLUSIVE")
        # A separate kill threshold below the success threshold.
        self.assertEqual(stats.wilson_decision(5, 200, 0.10, kill=0.04)["result"], "INCONCLUSIVE")
        self.assertEqual(stats.wilson_decision(1, 300, 0.10, kill=0.04)["result"], "FAIL")

    def test_sample_size(self):
        self.assertEqual(stats.sample_size(0.10, 0.05), 139)
        self.assertEqual(stats.sample_size(0.05, 0.03), 203)


class StoppingTests(unittest.TestCase):
    def test_hypergeom_cdf(self):
        self.assertAlmostEqual(stats.hypergeom_cdf(0, 10, 2, 3), 56 / 120.0)
        self.assertAlmostEqual(stats.hypergeom_cdf(2, 10, 2, 3), 1.0)

    def test_callaghan(self):
        cont = stats.callaghan_stop(unseen=1000, sample_n=300, sample_k=0, found_ranked=95)
        self.assertEqual(cont["k_tar"], 6)
        self.assertEqual(cont["decision"], "CONTINUE")
        stop = stats.callaghan_stop(unseen=1000, sample_n=600, sample_k=0, found_ranked=95)
        self.assertEqual(stop["decision"], "STOP")


class ReliabilityTests(unittest.TestCase):
    def test_krippendorff_binary_two_coders(self):
        a = [0, 1, 0, 0, 0, 0, 0, 0, 1, 0]
        b = [1, 1, 1, 0, 0, 1, 0, 0, 0, 0]
        self.assertAlmostEqual(reliability.krippendorff_alpha_nominal(list(zip(a, b))), 0.095, places=3)

    def test_krippendorff_nominal_two_coders(self):
        a = list("aabbdcccedda")
        b = list("babbbcccdddd")
        b[8] = "e"  # observer B: b a b b b c c c e d d d
        self.assertEqual("".join(b), "babbbccceddd")
        self.assertAlmostEqual(reliability.krippendorff_alpha_nominal(list(zip(a, b))), 0.692, places=3)

    def test_krippendorff_four_coders_missing(self):
        n = None
        data = [
            [1, 2, 3, 3, 2, 1, 4, 1, 2, n, n, n],
            [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, n, 3],
            [n, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, n],
            [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, n],
        ]
        units = [[row[i] for row in data] for i in range(12)]
        self.assertAlmostEqual(reliability.krippendorff_alpha_nominal(units), 0.743, places=3)

    def test_cohen_kappa_textbook(self):
        a = ["y"] * 25 + ["n"] * 25
        b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
        k = reliability.cohen_kappa(a, b)
        self.assertAlmostEqual(k, 0.4)
        self.assertEqual(reliability.landis_koch(k), "fair")

    def test_kappa_undefined(self):
        self.assertIsNone(reliability.cohen_kappa(["x"] * 5, ["x"] * 5))
        self.assertIsNone(reliability.krippendorff_alpha_nominal([["x", "x"]] * 5))

    def test_per_code_reliability(self):
        units = ["u%d" % i for i in range(20)]
        a = {u: set() for u in units}
        b = {u: set() for u in units}
        for i, u in enumerate(units):
            if i < 8:
                a[u].add("P-ONE")
                b[u].add("P-ONE")
            if i % 2 == 0:
                a[u].add("P-TWO")
            if i % 3 == 0:
                b[u].add("P-TWO")
        a["u19"].add("P-RARE")
        res = reliability.per_code_reliability(a, b, min_positives=5)
        self.assertEqual(res["codes"]["P-ONE"]["status"], "accept")
        self.assertEqual(res["codes"]["P-RARE"]["status"], "not-assessable")
        self.assertEqual(res["verdict"], "revise")
        self.assertIn("P-TWO", res["weak_codes"])


class ThemeTests(unittest.TestCase):
    def test_guest_namey_chen(self):
        recs = [("r1", {"a", "b"}), ("r2", {"b", "c"}), ("r3", {"a", "d"}), ("r4", {"c"}),
                ("r5", {"e"}), ("r6", {"a"}), ("r7", {"b"}), ("r8", {"c"})]
        res = themes.guest_namey_chen(recs, base=4, run=2, threshold=0.05)
        self.assertEqual(res["base_codes"], 4)
        self.assertAlmostEqual(res["runs"][0]["ratio"], 0.25)
        self.assertEqual(res["point"], "5+2")

    def test_theme_coverage(self):
        recs = [("r%d" % i, {"a", "b"} if i % 2 else {"a"}) for i in range(10)]
        res = themes.coverage_summary(recs)
        self.assertEqual(res["S_obs"], 2)
        self.assertEqual(res["coverage"], 1.0)


class BurstTests(unittest.TestCase):
    def test_detects_synthetic_burst(self):
        pts = [(100, 2)] * 24
        for t in (10, 11, 12, 13):
            pts[t] = (100, 15)
        res = bursts.kleinberg(pts, s=2, gamma=1)
        self.assertEqual(len(res["bursts"]), 1)
        self.assertEqual((res["bursts"][0]["start"], res["bursts"][0]["end"]), (10, 13))
        _obs, p = bursts.shuffle_test(pts, random.Random(7), shuffles=200)
        self.assertLess(p, 0.05)

    def test_flat_series_has_no_burst(self):
        res = bursts.kleinberg([(100, 5)] * 12)
        self.assertEqual(res["bursts"], [])


class AssocTests(unittest.TestCase):
    def test_association_strength(self):
        recs = [["a", "b"], ["a", "b"], ["a", "c"], ["b", "c"], ["a", "b"]]
        pairs = assoc.cooccurrence(recs)
        out = {(r["a"], r["b"]): r for r in assoc.association_strength(pairs, min_count=1)}
        self.assertAlmostEqual(out[("a", "b")]["association_strength"], 3 / 16.0)
        self.assertAlmostEqual(out[("a", "b")]["observed_over_expected"], 1.875)


class SurveyTests(unittest.TestCase):
    def test_odi_formula(self):
        self.assertAlmostEqual(survey.odi_opportunity(7.4, 2.8), 12.0)

    def test_odi_scores(self):
        rows = [{"outcome": "O-X", "importance": i, "satisfaction": s}
                for i, s in [(5, 1), (5, 2), (4, 2), (5, 3), (2, 4)]]
        res = survey.odi_scores(rows)[0]
        self.assertAlmostEqual(res["importance"], 8.0)
        self.assertAlmostEqual(res["satisfaction"], 2.0)
        self.assertAlmostEqual(res["opportunity"], 14.0)
        self.assertEqual(res["label"], "high")

    def test_kano_table(self):
        self.assertEqual(survey.kano_category("like", "dislike"), "O")
        self.assertEqual(survey.kano_category("L", "N"), "A")
        self.assertEqual(survey.kano_category("N", "D"), "M")
        self.assertEqual(survey.kano_category("L", "L"), "Q")
        self.assertEqual(survey.kano_category("D", "L"), "R")
        self.assertEqual(survey.kano_category("W", "W"), "I")

    def test_kano_coefficients(self):
        rows = ([{"feature": "f", "functional": "L", "dysfunctional": "N"}] * 5 +
                [{"feature": "f", "functional": "L", "dysfunctional": "D"}] * 3 +
                [{"feature": "f", "functional": "N", "dysfunctional": "D"}] * 2)
        r = survey.kano_features(rows)[0]
        self.assertEqual(r["category"], "A")
        self.assertAlmostEqual(r["better"], 0.8)
        self.assertAlmostEqual(r["worse"], -0.5)

    def test_van_westendorp_hand_checked(self):
        rows = [
            {"too_cheap": 5, "cheap": 10, "expensive": 20, "too_expensive": 30},
            {"too_cheap": 8, "cheap": 12, "expensive": 25, "too_expensive": 35},
            {"too_cheap": 10, "cheap": 15, "expensive": 30, "too_expensive": 40},
            {"too_cheap": 12, "cheap": 20, "expensive": 35, "too_expensive": 50},
            {"too_cheap": 30, "cheap": 20, "expensive": 10, "too_expensive": 5},
        ]
        r = survey.van_westendorp(rows)
        self.assertEqual(r["n"], 4)
        self.assertEqual(r["dropped_inconsistent"], 1)
        self.assertAlmostEqual(r["pmc"], 12)
        self.assertAlmostEqual(r["opp"], 15)
        self.assertAlmostEqual(r["ipp"], 20)
        self.assertAlmostEqual(r["pme"], 30)

    def test_nms_extension(self):
        rows = [
            {"too_cheap": 5, "cheap": 10, "expensive": 20, "too_expensive": 30, "likely_cheap": 5, "likely_expensive": 3},
            {"too_cheap": 8, "cheap": 12, "expensive": 25, "too_expensive": 35, "likely_cheap": 4, "likely_expensive": 2},
        ]
        r = survey.van_westendorp(rows, nms={"5": 0.7, "4": 0.5, "3": 0.3, "2": 0.1, "1": 0.0})
        self.assertIn("nms_trial_optimum", r)
        self.assertLessEqual(r["nms_trial_optimum"], r["nms_revenue_optimum"])

    def test_van_westendorp_empty_likelihood_columns(self):
        rows = [{"too_cheap": 5, "cheap": 10, "expensive": 20, "too_expensive": 30, "likely_cheap": "", "likely_expensive": ""},
                {"too_cheap": 8, "cheap": 12, "expensive": 25, "too_expensive": 35, "likely_cheap": "", "likely_expensive": ""}]
        r = survey.van_westendorp(rows, nms={"5": 0.7, "4": 0.5, "3": 0.3, "2": 0.1, "1": 0.0})
        self.assertNotIn("nms_trial_optimum", r)
        self.assertEqual(r["n"], 2)

    def test_ellis(self):
        answers = ["very"] * 30 + ["somewhat"] * 15 + ["not"] * 5 + ["na"] * 3
        r = survey.ellis(answers)
        self.assertAlmostEqual(r["very_disappointed_share"], 0.6)
        self.assertEqual(r["result"], "PASS")


class MiscTests(unittest.TestCase):
    def test_rbo(self):
        self.assertAlmostEqual(stats.rbo(list("abcde"), list("abcde")), 1.0)
        self.assertAlmostEqual(stats.rbo(list("abc"), list("xyz")), 0.0)
        mid = stats.rbo(list("abcde"), list("abxyz"))
        self.assertTrue(0 < mid < 1)

    def test_dirichlet(self):
        w = stats.dirichlet([50 * 0.5, 50 * 0.3, 50 * 0.2], random.Random(1))
        self.assertAlmostEqual(sum(w), 1.0)


if __name__ == "__main__":
    unittest.main()
