"""Codebook freezing, inter-coder agreement, theme saturation and the screening audit
(method cards D06, D13, D14)."""

import random
import re

from mgcore import reliability, state, themes
from mgcore.jsonio import now_iso, read_json, read_jsonl, sha256_json, write_json

from .common import CliError, cfg, out, p, require_run, load_state, save_state, validate

STD_PREFIX = re.compile(r"^(X|F|T)-")


def cmd_codebook_freeze(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    st = load_state(run)
    cd = st["coding"]
    v = cd.get("version", 0) + 1
    prev = read_json(p(run, "coding", "codebook.v%d.json" % (v - 1))) if v > 1 else None
    assignment = read_json(p(run, "coding", "open-assign-v%d.json" % v), {}) or {}
    draft_rel = ((assignment.get("outputs") or [{}])[0]).get("path") or "coding/codebook.json"
    draft = read_json(p(run, draft_rel))
    if draft is None:
        raise CliError("%s is missing; the open-coding subagent writes it" % draft_rel)
    standard = c.get("coding.standard_codes")
    std_ids = set(x["id"] for x in standard)
    own = [x for x in draft.get("codes", []) if not STD_PREFIX.match(x.get("id", ""))]
    stray = [x["id"] for x in draft.get("codes", []) if STD_PREFIX.match(x.get("id", "")) and x["id"] not in std_ids]
    if stray:
        raise CliError("X-/F-/T- prefixes are reserved for the standard codes; rename: %s" % ", ".join(stray))
    # Standard codes start from the previous frozen version (so earlier sharpening carries forward), else from defaults.
    # A draft may sharpen one: include, exclude and examples change; id, type, label and definition stay fixed so runs compare.
    base_std = {x["id"]: x for x in (prev or {}).get("codes", []) if x["id"] in std_ids}
    sharpen = {x["id"]: x for x in draft.get("codes", []) if x.get("id") in std_ids}
    std_codes = []
    for x in standard:
        y = dict(base_std.get(x["id"]) or dict(x, examples=[], parent=None, job_step=None, outcome_statement=None))
        y.update({k: x[k] for k in ("id", "type", "label", "definition")})
        y.update({k: sharpen[x["id"]][k] for k in ("include", "exclude", "examples") if sharpen.get(x["id"], {}).get(k)})
        std_codes.append(y)
    book = {"version": v, "frozen": True, "codes": own + std_codes, "notes": draft.get("notes", "")}
    errs = validate(book, "codebook")
    ids = [x["id"] for x in book["codes"]]
    dupes = sorted(set(i for i in ids if ids.count(i) > 1))
    if dupes:
        errs.append("duplicate code ids: %s" % ", ".join(dupes))
    for x in own:
        if x.get("parent") and x["parent"] not in ids:
            errs.append("%s: parent %s does not exist" % (x["id"], x["parent"]))
    if len(own) > c.get("coding.max_own_codes"):
        errs.append("%d own codes exceed coding.max_own_codes (%d): merge codes, or raise the limit with `protocol amend`"
                    % (len(own), c.get("coding.max_own_codes")))
    if not any(x["type"] in ("job", "outcome") for x in own):
        errs.append("define at least one job or outcome code (method card D13)")
    if errs:
        raise CliError("codebook draft is not valid:\n  " + "\n  ".join(errs[:12]))
    changed = {"added": [], "removed": [], "changed": []}
    if prev:
        pv = {x["id"]: x for x in prev["codes"]}
        nv = {x["id"]: x for x in book["codes"]}
        changed["added"] = sorted(set(nv) - set(pv))
        changed["removed"] = sorted(set(pv) - set(nv))
        changed["changed"] = sorted(i for i in set(nv) & set(pv)
                                    if any(nv[i].get(k) != pv[i].get(k) for k in ("definition", "include", "exclude", "type")))
        targets = [x["code"] for x in (assignment.get("inputs") or {}).get("codes_to_revise") or []]
        if targets and not set(targets) & (set(changed["changed"]) | set(changed["removed"])):
            raise CliError("the revised codebook leaves every code it had to revise unchanged (%s): sharpen, split or merge "
                           "them as method card D13 step 10 says" % ", ".join(targets))
    write_json(p(run, "coding", "codebook.v%d.json" % v), book)
    write_json(p(run, "coding", "codebook.lock.json"), {"version": v, "sha256": sha256_json(book), "frozen_at": now_iso(), "changes": changed})
    g = st.get("groups", {}).get("coding-open-v%d" % v)
    if g:
        g["merged"] = True
    cd["version"] = v
    state.touch(st, "codebook")
    save_state(run, st)
    state.event(run, "codebook_freeze", version=v, codes=len(book["codes"]), changes=changed)
    out("Codebook v%d frozen: %d own codes + %d standard codes." % (v, len(own), len(standard)))
    if prev:
        out("Changes vs v%d: +%d, -%d, ~%d. Coder A recodes all records under v%d; coder B re-checks a fresh sample." % (
            v - 1, len(changed["added"]), len(changed["removed"]), len(changed["changed"]), v))
    return 0


def _latest_codes(run, coder, version=None):
    recs = read_jsonl(p(run, "coding", "codes-%s.jsonl" % coder))[0]
    best = {}
    for r in recs:
        if version is not None and r["codebook_version"] != version:
            continue
        cur = best.get(r["evidence_id"])
        if cur is None or r["codebook_version"] >= cur["codebook_version"]:
            best[r["evidence_id"]] = r
    return best


def cmd_agreement(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    st = load_state(run)
    v = st["coding"]["version"]
    a = _latest_codes(run, "A", v)
    b = _latest_codes(run, "B", v)
    if not b:
        raise CliError("coder B has no codes for v%d yet" % v)
    from .assign import held_out_ids, reliability_sample
    held = held_out_ids(run, v)
    shared = sorted((set(a) & set(b)) - held)
    res = reliability.per_code_reliability({k: set(a[k]["codes"]) for k in shared}, {k: set(b[k]["codes"]) for k in shared},
                                           min_positives=c.get("coding.min_positives_per_code"),
                                           accept=c.get("coding.alpha_accept"), provisional=c.get("coding.alpha_provisional"))
    strength = reliability.label_reliability({k: a[k]["strength"] for k in shared}, {k: b[k]["strength"] for k in shared},
                                             c.get("coding.alpha_accept"), c.get("coding.alpha_provisional"))
    led = {r["id"]: r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]}
    graded = sorted(k for k in a if led.get(k, {}).get("strength"))
    vs_miner = reliability.label_reliability({k: led[k]["strength"] for k in graded}, {k: a[k]["strength"] for k in graded},
                                             c.get("coding.alpha_accept"), c.get("coding.alpha_provisional"))
    # Eligible codes: coder A applied them often enough to back a finding. Each needs a measured alpha (D14).
    need = c.get("coding.min_positives_per_code")
    pool = {e: set(rec["codes"]) for e, rec in a.items()
            if e not in held and led.get(e, {}).get("verification", {}).get("status") == "verified"}
    freq = {}
    for codes_ in pool.values():
        for code in codes_:
            freq[code] = freq.get(code, 0) + 1
    eligible = sorted(k for k, n in freq.items() if n >= need)
    # A code on every record cannot separate records, so its alpha (undefined: no variation) is never needed.
    constant = [k for k in eligible if all(k in codes_ for codes_ in pool.values())]
    unassessed = [k for k in eligible if k not in constant
                  and res["codes"].get(k, {}).get("status", "not-assessable") == "not-assessable"]
    # Same pool and selection rule as `assign --phase coding-reliability`, so the two never disagree about a top-up.
    more = reliability_sample(list(pool), pool, set(b), need, 0, 1, random.Random(0))
    topup = unassessed if (unassessed and more) else []
    verdict = res["verdict"]
    if verdict != "revise" and topup:
        verdict = "insufficient"
        res["note"] = ("%d code(s) that coder A applied at least %d times have too few double-coded positives (%s): "
                       "`assign --phase coding-reliability` tops up coder B's sample." % (len(topup), need, ", ".join(topup[:6])))
    elif verdict == "insufficient":
        verdict = "provisional"
        res["note"] = "Too few double-coded positives to assess most codes; treated as provisional."
    if verdict != "revise":
        # A code that could back a finding but whose reliability is unknown is provisional, never silently accepted.
        res["provisional_codes"] = sorted(set(res["provisional_codes"]) | set(k for k in unassessed if k not in topup))
        if verdict == "accept" and res["provisional_codes"]:
            verdict = "provisional"
    doc = dict(res, version=v, verdict=verdict, eligible_codes=eligible, unassessed_codes=unassessed, constant_codes=constant,
               held_out=len(held),
               strength=strength, strength_vs_miner=vs_miner, computed_at=now_iso(),
               revisions=st["coding"].get("revisions", 0))
    write_json(p(run, "coding", "agreement.json"), doc)
    st["coding"]["agreement"] = verdict
    state.touch(st, "agreement")
    save_state(run, st)
    out("Agreement on codebook v%d over %d double-coded records: %s (%d of %d eligible codes measured; weak codes: %s; provisional: %s; "
        "strength alpha %s)." % (
            v, res["units"], verdict.upper(), len(eligible) - len(unassessed), len(eligible), ", ".join(res["weak_codes"]) or "none",
            ", ".join(res["provisional_codes"]) or "none", "n/a" if strength["alpha"] is None else "%.2f" % strength["alpha"]))
    if res.get("note"):
        out(res["note"])
    out("Evidence strength, miner vs coder A over %d records: alpha %s, kappa %s (%s)." % (
        vs_miner["units"], "n/a" if vs_miner["alpha"] is None else "%.2f" % vs_miner["alpha"],
        "n/a" if vs_miner["kappa"] is None else "%.2f" % vs_miner["kappa"], vs_miner["landis_koch"]))
    return 0


def cmd_themes(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    st = load_state(run)
    v = st["coding"]["version"]
    book = read_json(p(run, "coding", "codebook.v%d.json" % v))
    if not book:
        raise CliError("no frozen codebook")
    types = set(c.get("coding.theme_code_types"))
    theme_ids = set(x["id"] for x in book["codes"] if x["type"] in types)
    a = _latest_codes(run, "A")
    verified = [r["id"] for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]
                if r.get("verification", {}).get("status") == "verified"]
    seq = []
    for eid in sorted(verified):
        if eid not in a:
            continue
        rec = a[eid]
        codes = set(x for x in rec["codes"] if x in theme_ids)
        for prop in rec.get("new_code_proposals") or []:
            codes.add("NEW:" + re.sub(r"\s+", " ", prop["label"].strip().casefold()))
        seq.append((eid, codes))
    if not seq:
        raise CliError("no coded verified records yet")
    cov = themes.coverage_summary(seq, z=1.96)
    gnc = themes.guest_namey_chen(seq, base=c.get("coding.gnc_base"), run=c.get("coding.gnc_run"),
                                  threshold=c.get("coding.gnc_threshold"))
    inc = themes.theme_incidence(seq)
    singles = sorted(k for k, vset in inc.items() if len(vset) == 1)
    labels = {x["id"]: x["label"] for x in book["codes"]}
    saturated = cov["coverage"] >= c.get("coding.theme_coverage_target") and gnc["saturated"]
    doc = {"computed_at": now_iso(), "codebook_version": v, "records": len(seq), "coverage": cov["coverage"],
           "themes_observed": cov["S_obs"], "themes_estimated": cov["chao2"], "completeness": cov["completeness"],
           "guest_namey_chen": {k: gnc[k] for k in ("base_codes", "saturated", "point", "threshold", "base", "run") if k in gnc},
           "gnc_note": "Base and run adapted from Guest, Namey & Chen 2020 (interviews: base 4, run 2) to short desk posts.",
           "saturated": saturated,
           "singleton_codes": [{"code": k, "label": labels.get(k, k.replace("NEW:", "proposed: "))} for k in singles]}
    write_json(p(run, "coding", "themes.json"), doc)
    st["coding"]["themes"] = "saturated" if saturated else "unsaturated"
    state.touch(st, "themes")
    save_state(run, st)
    out("Themes: %d observed (Chao2 %.1f), coverage %.3f, GNC %s -> %s." % (
        cov["S_obs"], cov["chao2"]["estimate"], cov["coverage"], gnc.get("point") or "not reached",
        "SATURATED" if saturated else "UNSATURATED"))
    return 0


def cmd_screen_audit(args):
    run = args.run
    require_run(run)
    c = cfg(run)
    recs = read_jsonl(p(run, "landscape", "screening.jsonl"))[0]
    a, b = {}, {}
    for r in recs:
        key = "%s@%s" % (r["entity_id"], r.get("batch"))
        (a if r["screener"] == "A" else b)[key] = r["decision"]
    res = reliability.label_reliability(a, b, c.get("screening.alpha_accept"), c.get("screening.alpha_provisional"))
    dis = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    doc = dict(res, computed_at=now_iso(), disagreements=[{"entity": k.split("@")[0], "A": a[k], "B": b[k]} for k in dis])
    write_json(p(run, "landscape", "screening-audit.json"), doc)
    st = load_state(run)
    state.touch(st, "screen_audit")
    save_state(run, st)
    out("Screening audit over %d double-screened entities: alpha %s, kappa %s (%s) -> %s; %d disagreements." % (
        res["units"], "n/a" if res["alpha"] is None else "%.2f" % res["alpha"],
        "n/a" if res["kappa"] is None else "%.2f" % res["kappa"], res["landis_koch"], res["status"], len(dis)))
    return 0
