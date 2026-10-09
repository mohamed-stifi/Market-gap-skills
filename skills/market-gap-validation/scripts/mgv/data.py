"""Ingest human-provided exports and analyse them with each Test Card's frozen decision rule
(method cards V05, V06, V09)."""

import csv
import glob
import math
import os
import random
import re

from mgcore import reliability, state, stats, survey, themes
from mgcore.jsonio import now_iso, read_json, read_jsonl, sha256_file, write_json, write_jsonl

from .common import CliError, cfg, load_state, out, require, save_state, v
from .prereg import is_tampered

KIND_COLUMNS = {
    "visits": ["channel", "visitors"], "signups": ["channel", "signups"], "clicks": ["channel", "clicks", "visitors"],
    "loi": ["count", "contacted"], "presale": ["count", "contacted"],
    "survey-odi": ["respondent", "outcome", "importance", "satisfaction"],
    "survey-kano": ["respondent", "feature", "functional", "dysfunctional"],
    "survey-vw": ["respondent", "too_cheap", "cheap", "expensive", "too_expensive"],
    "ellis": ["respondent", "answer"], "spike": ["test", "passed"],
}
COUNT_COLUMNS = {"visits": ["visitors"], "signups": ["signups"], "clicks": ["clicks", "visitors"], "loi": ["count", "contacted"],
                 "presale": ["count", "contacted"]}
FORBIDDEN = {"email", "e-mail", "mail", "name", "first_name", "last_name", "full_name", "phone", "telephone", "address", "ip", "ip_address"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
KINDS_FOR_TYPE = {
    "smoke-test": ["visits", "signups"], "fake-door": ["clicks"], "loi": ["loi"], "presale": ["presale"], "concierge": ["presale"],
    "odi-survey": ["survey-odi"], "kano-survey": ["survey-kano"], "pricing-survey": ["survey-vw"],
    "problem-interviews": ["interviews"], "switch-interviews": ["interviews"], "tech-spike": ["spike"], "search-demand": ["spike"],
}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        raise CliError("not a number: %r" % (x,))


def cmd_ingest(args):
    run = args.run
    require(run)
    exp, kind, path = args.experiment, args.kind, args.file
    folder = v(run, "data", exp)
    os.makedirs(folder, exist_ok=True)
    st = load_state(run)
    if kind == "interviews":
        if not os.path.isdir(path):
            raise CliError("--file must be a folder of .txt transcripts for interviews")
        recs = []
        for f in sorted(glob.glob(os.path.join(path, "*.txt"))):
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
            if EMAIL.search(text) or PHONE.search(text):
                raise CliError("%s contains an email address or phone number: pseudonymise transcripts before ingesting" % os.path.basename(f))
            st["iv_seq"] = st.get("iv_seq", 0) + 1
            recs.append({"record_id": "IV-%06d" % st["iv_seq"], "file": os.path.basename(f), "sha256": sha256_file(f), "text": text[:20000]})
        if not recs:
            raise CliError("no .txt transcripts in %s" % path)
        write_jsonl(os.path.join(folder, "interviews.jsonl"), recs)
        out("Ingested %d interview transcripts for %s." % (len(recs), exp))
    else:
        if kind not in KIND_COLUMNS:
            raise CliError("unknown kind %s" % kind)
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            raise CliError("%s has no rows" % path)
        cols = set(k.strip().lower() for k in rows[0].keys())
        bad = cols & FORBIDDEN
        if bad:
            raise CliError("export contains personal data columns (%s): export pseudonymous respondent ids only" % ", ".join(sorted(bad)))
        missing = [c for c in KIND_COLUMNS[kind] if c not in cols]
        if missing:
            raise CliError("%s is missing columns: %s" % (kind, ", ".join(missing)))
        for r in rows:
            if any(EMAIL.search(str(val or "")) for val in r.values()):
                raise CliError("export contains an email address: remove personal data first")
        norm = [{k.strip().lower(): (val.strip() if isinstance(val, str) else val) for k, val in r.items()} for r in rows]
        for i, r in enumerate(norm, 1):
            for col in COUNT_COLUMNS.get(kind, []):
                try:
                    num = float(r[col])
                except (TypeError, ValueError):
                    raise CliError("row %d: %s must be a number, got %r" % (i, col, r[col]))
                if num < 0 or num != int(num):
                    raise CliError("row %d: %s must be a non-negative whole number, got %r" % (i, col, r[col]))
            if kind == "clicks" and float(r["clicks"]) > float(r["visitors"]):
                raise CliError("row %d: clicks exceed visitors" % i)
            if kind in ("loi", "presale") and float(r["count"]) > float(r["contacted"]):
                raise CliError("row %d: count exceeds contacted" % i)
        write_json(os.path.join(folder, kind + ".json"), {"kind": kind, "rows": norm, "source_sha256": sha256_file(path), "ingested_at": now_iso()})
        out("Ingested %d %s rows for %s." % (len(norm), kind, exp))
    e = st.setdefault("experiments", {}).setdefault(exp, {})
    e.setdefault("ingested", [])
    if kind not in e["ingested"]:
        e["ingested"].append(kind)
    state.touch(st, "ingest_%s" % exp)
    save_state(run, st)
    return 0


def _rows(run, exp, kind):
    doc = read_json(v(run, "data", exp, kind + ".json"))
    return doc["rows"] if doc else None


def _interview_codes(run, exp, coder="A"):
    return {r["record_id"]: set(r["codes"]) for r in read_jsonl(v(run, "data", exp, "codes-%s.jsonl" % coder))[0]}


def analyse(run, card):
    c = cfg()
    exp, rule = card["id"], card["decision_rule"]
    z = c.get("stats.z")
    crit = card.get("criteria") or {}
    res = {"experiment": exp, "rule": rule, "evidence_level": card["evidence_level"], "computed_at": now_iso(), "directional": False}
    if is_tampered(run, exp):
        res.update(result="TAMPERED", reason="the Test Card changed after it was frozen")
        return res
    if rule == "wilson":
        if card["type"] == "smoke-test":
            vis, sig = _rows(run, exp, "visits"), _rows(run, exp, "signups")
            if vis is None or sig is None:
                raise CliError("smoke tests need both visits and signups exports")
            per = {}
            for r in vis:
                per.setdefault(r["channel"], [0, 0])[1] += int(_num(r["visitors"]))
            for r in sig:
                per.setdefault(r["channel"], [0, 0])[0] += int(_num(r["signups"]))
        elif card["type"] == "fake-door":
            per = {}
            for r in _rows(run, exp, "clicks") or []:
                per.setdefault(r["channel"], [0, 0])
                per[r["channel"]][0] += int(_num(r["clicks"]))
                per[r["channel"]][1] += int(_num(r["visitors"]))
        else:
            kind = KINDS_FOR_TYPE[card["type"]][0]
            rows = _rows(run, exp, kind) or []
            per = {"all": [sum(int(_num(r["count"])) for r in rows), sum(int(_num(r["contacted"])) for r in rows)]}
        bad = [ch for ch, (a, b) in per.items() if a > b]
        if bad:
            raise CliError("more successes than visitors in channel(s) %s: check the exports (UTM channels must match)" % ", ".join(sorted(bad)))
        k = sum(x[0] for x in per.values())
        n = sum(x[1] for x in per.values())
        res.update(stats.wilson_decision(k, n, card["success_threshold"], card["kill_threshold"], z, card["min_n"]))
        res["per_channel"] = {ch: stats.wilson_decision(a, b, card["success_threshold"], card["kill_threshold"], z, 1) for ch, (a, b) in sorted(per.items())}
    elif rule == "themes":
        codes = _interview_codes(run, exp)
        recs = read_jsonl(v(run, "data", exp, "interviews.jsonl"))[0]
        coded = [r["record_id"] for r in recs if r["record_id"] in codes]
        want = set(crit.get("problem_codes") or [])
        k = sum(1 for rid in coded if codes[rid] & want)
        res.update(stats.wilson_decision(k, len(coded), card["success_threshold"], card["kill_threshold"], z, card["min_n"]))
        gnc = themes.guest_namey_chen([(rid, codes[rid]) for rid in coded], base=c.get("interviews.gnc_base"),
                                      run=c.get("interviews.gnc_run"), threshold=c.get("interviews.gnc_threshold"))
        res["saturation"] = {kk: gnc.get(kk) for kk in ("saturated", "point", "base_codes")}
        agr = (read_json(v(run, "agreement.json"), {}) or {}).get(exp)
        res["agreement"] = agr.get("verdict") if agr else None
    elif rule == "odi":
        rows = _rows(run, exp, "survey-odi") or []
        table = survey.odi_scores(rows, tuple(c.get("surveys.odi_top_two_box")), c.get("surveys.odi_underserved"),
                                  c.get("surveys.odi_high"), c.get("surveys.odi_extreme"), z)
        target = [t for t in table if t["outcome"] in set(crit.get("outcomes") or [])]
        n = min([t["n"] for t in target] or [0])
        need = crit.get("min_opportunity", c.get("surveys.odi_underserved"))
        res.update(table=table, n=n)
        if n < card["min_n"]:
            res.update(result="INCONCLUSIVE", reason="sample below the pre-registered minimum")
        elif target and all(t["opportunity"] >= need for t in target):
            res.update(result="PASS", reason="every target outcome scores >= %s" % need)
        elif target and all(t["opportunity"] < need or t["label"] == "overserved" for t in target):
            res.update(result="FAIL", reason="no target outcome reaches %s" % need)
        else:
            res.update(result="INCONCLUSIVE", reason="mixed outcomes")
        res["directional"] = n < c.get("surveys.odi_min_n")
    elif rule == "kano":
        rows = _rows(run, exp, "survey-kano") or []
        feats = survey.kano_features(rows, tuple(c.get("surveys.kano_tie_order")))
        target = [f for f in feats if f["feature"] in set(crit.get("features") or [])]
        n = min([f["n"] for f in target] or [0])
        ok = set(crit.get("pass_categories") or [])
        res.update(features=feats, n=n)
        if n < card["min_n"]:
            res.update(result="INCONCLUSIVE", reason="sample below the pre-registered minimum")
        elif target and all(f["category"] in ok and not f["tied"] for f in target):
            res.update(result="PASS", reason="target features fall in %s" % ", ".join(sorted(ok)))
        elif target and all(f["category"] in ("I", "R") for f in target):
            res.update(result="FAIL", reason="target features are indifferent or reverse")
        else:
            res.update(result="INCONCLUSIVE", reason="mixed or tied categories")
        res["directional"] = n < c.get("surveys.kano_min_n")
    elif rule == "van-westendorp":
        rows = _rows(run, exp, "survey-vw") or []
        nms = c.get("surveys.nms_calibration")
        vw = survey.van_westendorp(rows, nms=nms)
        price = crit.get("price_point_month_usd") or card.get("price_point_month_usd")
        res.update(price_point=price, psm=vw, n=vw.get("n", 0))
        lo, hi = (vw.get("acceptable_range") or [None, None])
        if vw.get("n", 0) < card["min_n"] or lo is None or hi is None:
            res.update(result="INCONCLUSIVE", reason="sample below minimum or range undefined")
        elif lo <= price <= hi:
            res.update(result="PASS", reason="planned price %.2f inside the acceptable range %.2f-%.2f" % (price, lo, hi))
        else:
            res.update(result="FAIL", reason="planned price %.2f outside the acceptable range %.2f-%.2f" % (price, lo, hi))
        res["directional"] = vw.get("n", 0) < c.get("surveys.vw_min_n")
    elif rule == "ellis":
        rows = _rows(run, exp, "ellis") or []
        res.update(survey.ellis([r["answer"] for r in rows], card["success_threshold"], z, card["min_n"]))
    elif rule == "criteria":
        rows = _rows(run, exp, "spike") or []
        got = {r["test"]: str(r["passed"]).strip().lower() in ("true", "1", "yes", "pass") for r in rows}
        tests = crit.get("acceptance_tests") or []
        missing = [t for t in tests if t not in got]
        if missing:
            res.update(result="INCONCLUSIVE", reason="tests without a result: %s" % ", ".join(missing))
        elif all(got[t] for t in tests):
            res.update(result="PASS", reason="all acceptance tests passed")
        else:
            res.update(result="FAIL", reason="failed: %s" % ", ".join(t for t in tests if not got[t]))
        res["tests"] = got
    return res


def cmd_stats(args):
    run = args.run
    require(run)
    card = read_json(v(run, "prereg", "%s.json" % args.experiment))
    if not card or card.get("status") == "draft":
        raise CliError("%s is not a frozen Test Card" % args.experiment)
    res = analyse(run, card)
    write_json(v(run, "results", "%s.json" % card["id"]), res)
    st = load_state(run)
    st.setdefault("experiments", {}).setdefault(card["id"], {})["status"] = "analyzed"
    state.touch(st, "stats_%s" % card["id"])
    save_state(run, st)
    extra = ""
    if "ci_low" in res:
        extra = " (%s/%s, 95%% CI %.3f-%.3f vs X=%.3f)" % (res.get("k"), res.get("n"), res["ci_low"], res["ci_high"], card["success_threshold"])
    out("%s: %s%s%s" % (card["id"], res["result"], extra, " [directional]" if res.get("directional") else ""))
    if res.get("reason"):
        out("  reason: " + res["reason"])
    return 0


def cmd_agreement(args):
    run = args.run
    require(run)
    c = cfg()
    doc = read_json(v(run, "agreement.json"), {}) or {}
    for path in sorted(glob.glob(v(run, "data", "EXP-*", "codes-B.jsonl"))):
        exp = os.path.basename(os.path.dirname(path))
        a, b = _interview_codes(run, exp, "A"), _interview_codes(run, exp, "B")
        need = c.get("interviews.min_positives_per_code")
        res = reliability.per_code_reliability(a, b, need, c.get("interviews.alpha_accept"), c.get("interviews.alpha_provisional"))
        if res["verdict"] == "insufficient":
            res["verdict"] = "provisional"
        # A code coder A used often enough to matter but that the double-coded sample could not measure is provisional,
        # never silently accepted (same rule as discovery D14). Codes on every transcript cannot separate them and are skipped.
        freq = {}
        for codes in a.values():
            for code in codes:
                freq[code] = freq.get(code, 0) + 1
        unmeasured = sorted(k for k, n in freq.items() if need <= n < len(a)
                            and res["codes"].get(k, {}).get("status", "not-assessable") == "not-assessable")
        if unmeasured and res["verdict"] != "revise":
            res["provisional_codes"] = sorted(set(res["provisional_codes"]) | set(unmeasured))
            res["verdict"] = "provisional"
        res["unmeasured_codes"] = unmeasured
        doc[exp] = dict(res, computed_at=now_iso())
        out("%s interview coding agreement over %d transcripts: %s (weak: %s)" % (exp, res["units"], res["verdict"], ", ".join(res["weak_codes"]) or "none"))
    write_json(v(run, "agreement.json"), doc)
    st = load_state(run)
    state.touch(st, "agreement")
    save_state(run, st)
    return 0


def cmd_themes(args):
    run = args.run
    require(run)
    c = cfg()
    doc = {}
    for path in sorted(glob.glob(v(run, "data", "EXP-*", "codes-A.jsonl"))):
        exp = os.path.basename(os.path.dirname(path))
        codes = _interview_codes(run, exp)
        seq = sorted(codes.items())
        gnc = themes.guest_namey_chen(seq, base=c.get("interviews.gnc_base"), run=c.get("interviews.gnc_run"),
                                      threshold=c.get("interviews.gnc_threshold"))
        doc[exp] = {"interviews": len(seq), "saturated": gnc["saturated"], "point": gnc.get("point"), "base_codes": gnc.get("base_codes")}
        out("%s interview themes: %s after %d interviews (%s)" % (exp, "SATURATED" if gnc["saturated"] else "not saturated", len(seq), gnc.get("point") or "-"))
    write_json(v(run, "themes.json"), doc)
    st = load_state(run)
    state.touch(st, "themes")
    save_state(run, st)
    return 0


def reliability_sample(records, seed):
    n = len(records)
    k = n if n <= 15 else max(5, int(math.ceil(0.2 * n)))
    rng = random.Random(seed)
    return sorted(rng.sample(records, k), key=lambda r: r["record_id"])
