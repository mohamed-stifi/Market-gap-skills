"""Pre-registration: draft, check, freeze and verify Test Cards (method cards V03, V04).

Freezing hashes the card (excluding its status field). Editing a frozen card is detected by
`prereg verify` and the experiment is reported as TAMPERED, so thresholds cannot move after
data arrives.
"""

import glob
import os

from mgcore import stats
from mgcore.jsonio import now_iso, read_json, sha256_json, write_json

from .common import CliError, cards, cfg, load_state, ost, out, require, save_state, v, validate

TYPE_DEFAULTS = {
    "search-demand": ("criteria", "desk"),
    "problem-interviews": ("themes", "interview"),
    "switch-interviews": ("themes", "interview"),
    "odi-survey": ("odi", "survey"),
    "kano-survey": ("kano", "survey"),
    "pricing-survey": ("van-westendorp", "survey"),
    "smoke-test": ("wilson", "email"),
    "fake-door": ("wilson", "click"),
    "loi": ("wilson", "loi"),
    "presale": ("wilson", "presale"),
    "concierge": ("wilson", "call"),
    "tech-spike": ("criteria", "prototype"),
}
PAYMENT_WORDS = ("stripe", "payment", "presale", "deposit", "ads", "ad-budget", "budget")


def _hash(card):
    return sha256_json({k: val for k, val in card.items() if k != "status"})


def draft(exp_id, type_, assumption_ids, solution_id):
    rule, level = TYPE_DEFAULTS[type_]
    return {"id": exp_id, "assumption_ids": assumption_ids, "solution_id": solution_id, "type": type_,
            "hypothesis": {"we_believe": "", "to_verify": "", "measure": "", "right_if": ""},
            "xyz": {"x": 0.0, "y": "", "z": ""}, "metric": {"name": "", "numerator": "", "denominator": ""},
            "evidence_level": level, "success_threshold": 0.0, "kill_threshold": 0.0, "planning_p": None,
            "half_width": None, "min_n": 1, "decision_rule": rule, "price_point_month_usd": None, "criteria": {},
            "duration_days": 14, "budget_usd": 0, "channels": [],
            "ethics": {"disclosure": True, "consent": True, "no_charge_without_consent": True, "privacy_notice": True,
                       "exposure_limit": ""},
            "required_ht": [], "on_pass": "continue", "on_fail": "iterate", "on_inconclusive": "extend",
            "pivot_hypothesis": None, "x_derivation": "", "status": "draft"}


def problems(run, card):
    c = cfg()
    errs, warns = validate(card, "test-card"), []
    if errs:
        return errs, warns
    o = ost(run) or {}
    all_ids = set(a["id"] for s in o.get("solutions", []) for a in s["assumptions"])
    sols = set(s["id"] for s in o.get("solutions", []))
    for a in card["assumption_ids"]:
        if a not in all_ids:
            errs.append("assumption %s is not in ost.json" % a)
    if card["solution_id"] not in sols:
        errs.append("solution %s is not in ost.json" % card["solution_id"])
    rule = card["decision_rule"]
    crit = card.get("criteria") or {}
    if card["kill_threshold"] > card["success_threshold"]:
        errs.append("kill_threshold must be <= success_threshold")
    if rule in ("wilson", "themes", "ellis") and abs(card["xyz"]["x"] - card["success_threshold"]) > 1e-9:
        errs.append("xyz.x must equal success_threshold (the XYZ hypothesis is the pre-registered bar)")
    if rule == "wilson":
        if card.get("planning_p") and card.get("half_width"):
            need = stats.sample_size(card["planning_p"], card["half_width"], c.get("stats.z"))
            if card["min_n"] < need:
                errs.append("min_n %d is below the sample size %d for p=%.2f +/- %.2f" % (card["min_n"], need, card["planning_p"], card["half_width"]))
        elif card["evidence_level"] in ("click", "email"):
            errs.append("set planning_p and half_width so min_n can be checked (`gapval.py samplesize`)")
        if card["evidence_level"] in ("click", "email") and card["min_n"] < c.get("stats.min_visitors_floor"):
            errs.append("min_n must be at least %d visitors for web experiments" % c.get("stats.min_visitors_floor"))
        if card["success_threshold"] <= 0:
            errs.append("success_threshold must be above 0")
    if rule == "themes":
        if card["min_n"] < c.get("interviews.min_interviews"):
            errs.append("min_n must be at least %d interviews" % c.get("interviews.min_interviews"))
        if not crit.get("problem_codes"):
            errs.append("criteria.problem_codes lists the codes that count as 'has the problem'")
    if rule == "odi":
        if not crit.get("outcomes"):
            errs.append("criteria.outcomes lists the outcome codes to test")
        if card["min_n"] < c.get("surveys.odi_min_n"):
            warns.append("min_n below %d: ODI results will be labelled directional" % c.get("surveys.odi_min_n"))
    if rule == "kano":
        if not crit.get("features") or not crit.get("pass_categories"):
            errs.append("criteria.features and criteria.pass_categories are required")
        if card["min_n"] < c.get("surveys.kano_min_n"):
            warns.append("min_n below %d: Kano categories will be labelled directional" % c.get("surveys.kano_min_n"))
    if rule == "van-westendorp":
        if not (crit.get("price_point_month_usd") or card.get("price_point_month_usd")):
            errs.append("criteria.price_point_month_usd (the planned price) is required")
        if card["min_n"] < c.get("surveys.vw_min_n"):
            warns.append("min_n below %d per segment: price range will be directional" % c.get("surveys.vw_min_n"))
    if rule == "ellis" and abs(card["success_threshold"] - c.get("surveys.ellis_threshold")) > 1e-9:
        warns.append("the Sean Ellis benchmark is 0.40")
    if rule == "criteria" and not crit.get("acceptance_tests"):
        errs.append("criteria.acceptance_tests lists the pass/fail tests")
    if card["type"] in ("smoke-test", "fake-door") and not card["channels"]:
        errs.append("list the traffic channels (each gets a UTM link)")
    if card["evidence_level"] in ("presale", "deposit") and not any(w in s for s in card["required_ht"] for w in PAYMENT_WORDS):
        errs.append("money-taking experiments need a payment human task in required_ht (e.g. 'stripe-payment-link')")
    if card["budget_usd"] > 0 and not any(w in s for s in card["required_ht"] for w in PAYMENT_WORDS):
        errs.append("a budget above 0 needs a payment/ads human task in required_ht")
    if card["on_fail"] == "pivot" and not card.get("pivot_hypothesis"):
        errs.append("on_fail 'pivot' needs a pivot_hypothesis")
    return errs, warns


def cmd_prereg(args):
    run = args.run
    require(run)
    st = load_state(run)
    if args.action == "new":
        if not args.experiment or not args.type or not args.assumption:
            raise CliError("--experiment, --type and --assumption are required")
        path = v(run, "prereg", args.experiment + ".json")
        if os.path.exists(path):
            raise CliError("%s already exists" % path)
        o = ost(run) or {}
        write_json(path, draft(args.experiment, args.type, args.assumption.split(","), o.get("target_solution", "SOL-1")))
        out("Draft Test Card written: %s (fill it, then `prereg check`)." % path)
        return 0
    if args.action == "verify":
        tampered = []
        for lock_path in sorted(glob.glob(v(run, "prereg", "EXP-*.lock.json"))):
            lock = read_json(lock_path)
            card = read_json(lock_path.replace(".lock.json", ".json"))
            if not card or _hash(card) != lock["sha256"]:
                tampered.append(lock["id"])
        st["tampered"] = tampered
        save_state(run, st)
        if tampered:
            out("TAMPERED after freezing: %s. Their results will be reported as TAMPERED." % ", ".join(tampered))
            return 1
        out("All frozen Test Cards match their pre-registration hashes.")
        return 0
    exp = args.experiment_id
    card = read_json(v(run, "prereg", "%s.json" % exp)) if exp else None
    if card is None:
        raise CliError("no Test Card %s" % exp)
    errs, warns = problems(run, card)
    st.setdefault("experiments", {}).setdefault(exp, {})["check"] = {"ok": not errs, "at": now_iso(),
                                                                     "card_sha": _hash(card), "errors": errs}
    if args.action == "check":
        save_state(run, st)
        for w in warns:
            out("  warning: " + w)
        if errs:
            out("%s is not ready:" % exp)
            for e in errs:
                out("  - " + e)
            return 1
        out("%s passes the pre-registration checks." % exp)
        return 0
    if args.action == "freeze":
        if errs:
            save_state(run, st)
            raise CliError("%s fails pre-registration checks:\n  %s" % (exp, "\n  ".join(errs)))
        if os.path.exists(v(run, "prereg", "%s.lock.json" % exp)):
            raise CliError("%s is already frozen" % exp)
        card["status"] = "frozen"
        write_json(v(run, "prereg", "%s.json" % exp), card)
        write_json(v(run, "prereg", "%s.lock.json" % exp), {"id": exp, "sha256": _hash(card), "frozen_at": now_iso()})
        st["experiments"][exp]["status"] = "frozen"
        from mgcore import state as _state
        _state.touch(st, "prereg")
        save_state(run, st)
        for w in warns:
            out("  warning: " + w)
        out("%s frozen (sha256 %s). Thresholds can no longer change." % (exp, _hash(card)[:16]))
        return 0
    raise CliError("unknown prereg action")


def is_tampered(run, exp):
    lock = read_json(v(run, "prereg", "%s.lock.json" % exp))
    card = read_json(v(run, "prereg", "%s.json" % exp))
    return bool(lock) and (not card or _hash(card) != lock["sha256"])
