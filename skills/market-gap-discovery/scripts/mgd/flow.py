"""`gapscan.py next` and `gapscan.py status`: derive the single next action from the run
folder, so any agent (or a new session) can resume deterministically."""

import glob
import json
import os
import re

from mgcore import hq, state
from mgcore.jsonio import read_json, read_jsonl, sha256_json, sha256_file

from . import gaps, models
from .common import SCRIPTS_DIR, cfg, entities, out, p, protocol, require_run, load_state, save_state
from .setup import protocol_errors, protocol_warnings

GAPSCAN = os.path.join(SCRIPTS_DIR, "gapscan.py")


class Act(Exception):
    def __init__(self, verdict, args, notes=None, phase=None):
        Exception.__init__(self, verdict)
        self.verdict, self.argline, self.notes, self.phase = verdict, args, list(notes or []), phase


def RUN(cmd, *notes, **kw):
    raise Act("RUN", "gapscan.py " + cmd, notes, kw.get("phase"))


def DO(card, task, *notes, **kw):
    raise Act("DO", "%s %s" % (card, task), notes, kw.get("phase"))


def SPAWN(role, run, paths, *notes, **kw):
    # Tell the orchestrator which model tier each subagent should run on (all assignments of a
    # group share a role, so the first one speaks for the group).
    mnote = models.note(read_json(p(run, paths[0]), {}) or {}) if paths else None
    notes = tuple(notes) + ((mnote,) if mnote else ())
    raise Act("SPAWN", "%s %d %s" % (role, len(paths), " ".join(p(run, x) for x in paths)), notes, kw.get("phase"))


def BLOCKED(task, *notes, **kw):
    raise Act("BLOCKED", task["id"], ("human task: %s (%s)" % (task["title"], task["type"]),) + notes, kw.get("phase"))


def _group(run, st, key):
    g = st.get("groups", {}).get(key)
    if not g:
        return None, []
    if g.get("merged"):
        return "merged", []
    missing = []
    for apath in g["paths"]:
        a = read_json(p(run, apath)) or {}
        if any(not os.path.exists(p(run, o["path"])) for o in a.get("outputs", [])):
            missing.append(apath)
    return ("spawn" if missing else "ready"), missing


def _handle(run, st, key, role, merge_cmd, phase):
    s, missing = _group(run, st, key)
    if s == "spawn":
        SPAWN(role, run, missing, "independent work: start these subagents in parallel; each reads only its assignment", phase=phase)
    if s == "ready":
        RUN(merge_cmd, phase=phase)
    return s


def _gate(run, st, name, fingerprint, title, why, steps, phase):
    if (protocol(run).get("autonomy") or st.get("autonomy")) != "gated":
        return
    gates = st.setdefault("gates", {})
    g = gates.get(name, {"attempt": 0})
    task = hq.find_gate(run, "%s#%d" % (name, g["attempt"])) if g["attempt"] else None
    if task is None or (task["status"] == "declined" and g.get("fingerprint") != fingerprint):
        g = {"attempt": g["attempt"] + 1, "fingerprint": fingerprint}
        gates[name] = g
        task = hq.add(run, "judgment", title, why, steps, "`gapscan.py hq done RUN HT-NNN` to approve, or `hq decline RUN HT-NNN --note WHY`",
                      phase, blocking=True, gate="%s#%d" % (name, g["attempt"]))
        save_state(run, st)
    if task["status"] == "open":
        BLOCKED(task, "gated run: the human approves before work continues", phase=phase)
    if task["status"] == "declined":
        DO({"protocol": "D01", "landscape": "D04", "shortlist": "D23"}[name],
           "revise per the human's note on %s: %s" % (task["id"], task.get("note") or "(no note)"),
           "after revising, call next again: a new approval request is created automatically", phase=phase)


def _stale(st, derived, inputs):
    return state.stale(st, derived, inputs)


def decide(run):
    st = load_state(run)
    c = cfg(run)
    proto = protocol(run)
    # ---------------- P0 setup
    if not os.path.exists(p(run, "doctor.json")):
        RUN("doctor %s" % run, "check sources, keys and network before anything else", phase="P0")
    lock = read_json(p(run, "protocol.lock.json"))
    if not lock:
        errs = protocol_errors(run)
        if errs:
            DO("D01", "fill protocol.json (method card D01), then run `gapscan.py protocol check %s`" % run, *errs[:6], phase="P0")
        _gate(run, st, "protocol", sha256_file(p(run, "protocol.json")), "Approve the research protocol",
              "Gated run: the protocol (question, scope, eligibility, sources, thresholds) is the pre-registration.",
              "Read protocol.json; approve or decline with a note.", "P0")
        RUN("protocol freeze %s" % run, "pre-registration: the protocol is hashed before any search",
            *["advice before freezing: " + w for w in protocol_warnings(run)], phase="P0")
    if sha256_json(proto) != lock["sha256"]:
        DO("D01", "protocol.json changed after freezing: restore it and record changes with `gapscan.py protocol amend`", phase="P0")
    used = st.get("budget", {}).get("subagents_used", 0)
    if used >= c.get("budget.subagents_max"):
        t = hq.add(run, "judgment", "Subagent budget exhausted", "The run used its subagent budget (%d)." % used,
                   "Decide whether to raise budget.subagents_max with `protocol amend` or to stop and report.",
                   "an amendment or `hq decline` to stop", "budget", blocking=True, gate="budget#%d" % used)
        if t["status"] == "open":
            BLOCKED(t, phase="budget")
    # ---------------- P1 lexicon
    lx = st["lexicon"]
    if lx["round"] == 0:
        RUN("assign %s --phase lexicon" % run, "three scouts harvest vocabulary independently (D02)", phase="P1")
    _handle(run, st, "lexicon-R%02d" % lx["round"], "scout", "merge %s --phase lexicon" % run, "P1")
    if (lx.get("overlap") or 0) < c.get("lexicon.overlap_target") and lx["round"] < c.get("lexicon.max_rounds"):
        RUN("assign %s --phase lexicon" % run, "lexicon overlap %.2f < %.2f: one expansion round" % (lx.get("overlap") or 0, c.get("lexicon.overlap_target")), phase="P1")
    s = _handle(run, st, "press", "reviewer", "lexicon apply-press %s" % run, "P1")
    if s is None:
        RUN("assign %s --phase press" % run, "PRESS peer review of the search strategy before sampling", phase="P1")
    # ---------------- P2 landscape
    ls = st["landscape"]
    if ls["round"] == 0:
        RUN("assign %s --phase landscape" % run, "ADVANCE P2: sampling units = scout x channel family", phase="P2")
    _handle(run, st, "landscape-R%02d" % ls["round"], "scout", "merge %s --phase landscape" % run, "P2")
    if ls.get("probe_count"):
        _handle(run, st, "probe-%d" % ls["probe_count"], "scout", "merge %s --phase probe" % run, "P2")
    if ls.get("snowball_iteration"):
        _handle(run, st, "snowball-%02d" % ls["snowball_iteration"], "scout", "merge %s --phase snowball" % run, "P2")
    ents = entities(run)
    if ls.get("screen_batch") and any(e.get("status") == "new" for e in ents):
        _handle(run, st, "screen-%02d" % ls["screen_batch"], "screener", "merge %s --phase screen" % run, "P2")
    # Audit after every screening merge, so a reliable audit can retire screener B early and a weak
    # one stops the run before more batches are screened under an unclear rule.
    if ls.get("screen_batch") and _stale(st, "screen_audit", ["screen_merge"]):
        RUN("screen-audit %s" % run, "Krippendorff alpha between screeners A and B", phase="P2")
    audit = read_json(p(run, "landscape", "screening-audit.json"), {}) or {}
    if audit.get("status") == "revise" and state.mark(st, "protocol") < state.mark(st, "screen_audit"):
        DO("D06", "screening audit alpha is low: clarify the eligibility rule behind the disagreements with `gapscan.py protocol amend`, recording the limitation", phase="P2")
    if any(e.get("status") == "new" for e in ents):
        RUN("assign %s --phase screen" % run, "screen new entities: screener A all, screener B an audit sample until screening is shown reliable (D06)", phase="P2")
    if any(e.get("status") == "included" and not e.get("verified") for e in ents):
        RUN("entities verify %s" % run, "only included entities whose page exists and names them count", phase="P2")
    if not ls.get("sampling_closed"):
        if _stale(st, "saturation", ["landscape_merge", "screen_merge", "entities_verify"]):
            RUN("saturation %s" % run, "capture-recapture check of the doctoral ~90% rule (D04)", phase="P2")
        v = ls.get("verdict")
        if v == "EXPAND":
            RUN("assign %s --phase landscape --units %d" % (run, ls.get("expand_units") or c.get("landscape.scouts")),
                "landscape EXPAND k=%s: see landscape/saturation.json reasons" % ls.get("expand_units"), phase="P2")
        if v == "NEEDS_PROBE":
            RUN("assign %s --phase probe" % run, "landscape PROBE: estimators pass; a fresh holdout scout checks them", phase="P2")
    sat = read_json(p(run, "landscape", "saturation.json"), {}) or {}
    if not ls.get("snowball_done"):
        it = ls.get("snowball_iteration", 0)
        note = "landscape %s -> snowballing (D05)" % sat.get("verdict")
        if it == 0:
            RUN("assign %s --phase snowball" % run, note, phase="P2")
        new_inc = [e for e in ents if e.get("first_group") == "snowball-%02d" % it and e.get("status") == "included"
                   and (e.get("verified") or {}).get("status") == "ok"]
        pending_seeds = [e for e in ents if e.get("status") == "included" and (e.get("verified") or {}).get("status") == "ok"
                         and e["entity_id"] not in set(ls.get("snowballed", []))]
        if new_inc and pending_seeds and it < c.get("snowball.max_iterations"):
            RUN("assign %s --phase snowball" % run, "snowball iteration %d added %d entities: continue" % (it, len(new_inc)), phase="P2")
        ls["snowball_done"] = True
        save_state(run, st)
    _gate(run, st, "landscape", [state.mark(st, "landscape_merge"), state.mark(st, "protocol")], "Approve the market landscape",
          "Gated run: check the landscape and saturation before evidence mining.",
          "Read landscape/saturation.json and landscape/entities.jsonl; approve or decline with a note.", "P2")
    s = _handle(run, st, "mapping", "synthesizer", "merge %s --phase mapping" % run, "P2")
    if s is None:
        RUN("assign %s --phase mapping" % run, "systematic map: classification scheme and attributes (D07)", phase="P2")
    # ---------------- P3 evidence
    ev = st["evidence"]
    if ev["round"] == 0:
        RUN("assign %s --phase evidence" % run, "ADVANCE P3: miners harvest evidence by stance (D08-D12)", phase="P3")
    _handle(run, st, "evidence-R%02d" % ev["round"], "miner", "merge %s --phase evidence" % run, "P3")
    if _stale(st, "verify", ["evidence_merge"]):
        RUN("verify %s" % run, "every quote is checked against its snapshot", phase="P3")
    sigs = glob.glob(p(run, "evidence", "signals", "*.json"))
    bpath = p(run, "evidence", "bursts.json")
    if sigs and (not os.path.exists(bpath) or max(os.path.getmtime(x) for x in sigs) > os.path.getmtime(bpath)):
        RUN("bursts %s" % run, "Kleinberg bursts with a shuffle test on demand signals (D11)", phase="P3")
    verified = [r for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0] if r.get("verification", {}).get("status") == "verified"]
    if not verified:
        if ev["round"] < c.get("evidence.max_rounds"):
            RUN("assign %s --phase evidence" % run, "no verified evidence yet: another round", phase="P3")
        DO("D08", "no verified evidence after %d rounds: review coverage-gaps.jsonl and doctor.json, then widen the protocol with `protocol amend` or stop and report" % ev["round"], phase="P3")
    # ---------------- P4 coding
    cd = st["coding"]
    nxt = "coding-open-v%d" % (cd.get("version", 0) + 1)
    s, _m = _group(run, st, nxt)
    if s == "spawn":
        SPAWN("coder", run, _m, "open coding: draft the codebook (D13)", phase="P4")
    if s == "ready":
        RUN("codebook freeze %s" % run, "freeze and hash the codebook before closed coding", phase="P4")
    if cd.get("version", 0) == 0:
        RUN("assign %s --phase coding-open" % run, "ADVANCE P4: open coding on a stratified base sample", phase="P4")
    v = cd["version"]
    for key in sorted(k for k, g in st.get("groups", {}).items() if g["phase"] == "coding-closed" and not g.get("merged")):
        _handle(run, st, key, "coder", "merge %s --phase coding" % run, "P4")
    coded = set(r["evidence_id"] for r in read_jsonl(p(run, "coding", "codes-A.jsonl"))[0] if r["codebook_version"] == v)
    if any(r["id"] not in coded for r in verified):
        RUN("assign %s --phase coding-closed" % run, "coder A applies codebook v%d to every verified record" % v, phase="P4")
    rel = sorted(k for k in st.get("groups", {}) if re.match(r"coding-reliability-v%d(-t\d+)?$" % v, k))
    if not rel:
        RUN("assign %s --phase coding-reliability" % run,
            "independent coder B double-codes a random core plus enough records for every frequent code (D14)", phase="P4")
    for key in rel:
        _handle(run, st, key, "coder", "merge %s --phase coding" % run, "P4")
    if _stale(st, "agreement", ["coding_merge"]):
        RUN("agreement %s" % run, "Krippendorff alpha per code", phase="P4")
    if cd.get("agreement") == "insufficient":
        RUN("assign %s --phase coding-reliability" % run,
            "top up coder B's sample: some frequent codes still have too few double-coded positives (D14)", phase="P4")
    if cd.get("agreement") == "revise" and cd.get("revisions", 0) < c.get("coding.max_revisions"):
        RUN("assign %s --phase coding-open --revise" % run, "reliability too low for some codes: revise the codebook", phase="P4")
    if _stale(st, "themes", ["coding_merge"]):
        RUN("themes %s" % run, "theme saturation (coverage + Guest-Namey-Chen)", phase="P4")
    if cd.get("themes") == "unsaturated" and ev["round"] < c.get("evidence.max_rounds"):
        RUN("assign %s --phase evidence" % run, "themes unsaturated: another evidence round focused on singleton themes", phase="P3")
    s = _handle(run, st, "supply", "synthesizer", "merge %s --phase supply" % run, "P4")
    if s is None:
        RUN("assign %s --phase supply" % run, "map which jobs each product serves (D15)", phase="P4")
    sup_g = st.get("groups", {}).get("supply", {})
    sup_v = sup_g.get("codebook_version")
    if sup_v is None:
        m = re.search(r"codebook\.v(\d+)\.json", str(((read_json(p(run, "analysis", "supply-assign.json"), {}) or {}).get("inputs") or {}).get("codebook")))
        sup_v = int(m.group(1)) if m else cd["version"]
    if sup_g.get("merged") and sup_v != cd["version"]:
        # A revised codebook can add or drop jobs; supply mapped under the old one would show new
        # jobs as unserved (false absolute gaps). Re-map, updating only the changed codes.
        RUN("assign %s --phase supply" % run, "supply was mapped under codebook v%s, now v%d: update it for changed codes (D15)" % (
            sup_v if sup_v is not None else "?", cd["version"]), phase="P4")
    if _stale(st, "matrix", ["supply", "mapping", "coding_merge", "verify"]):
        RUN("matrix %s" % run, phase="P4")
    if _stale(st, "gapmap", ["matrix", "coding_merge", "verify"]):
        RUN("gapmap %s" % run, "demand-supply gap map (D16)", phase="P4")
    # ---------------- P5 gaps
    if _stale(st, "variants", ["gapmap"]):
        RUN("variants %s" % run, "change-one-dimension candidates (D19)", phase="P5")
    s, missing = _group(run, st, "synthesis")
    if s is None:
        RUN("assign %s --phase synthesis" % run, "ADVANCE P5: gap spotting, problematization and variation into gap cards", phase="P5")
    if s == "merged" and _stale(st, "cards_check", ["gapmap"]):
        # New evidence or a revised codebook changed the gap map after the cards were checked:
        # red-teaming the old cards would appraise claims the evidence no longer supports.
        RUN("assign %s --phase synthesis" % run, "gap map changed since the cards were checked: update the gap cards (D20)", phase="P5")
    if s == "spawn":
        SPAWN("synthesizer", run, missing, phase="P5")
    if s == "ready":
        check = read_json(p(run, "gaps", "card-check.json"))
        cards_mtime = os.path.getmtime(p(run, "gaps", "cards.jsonl"))
        if check and not check.get("ok") and os.path.getmtime(p(run, "gaps", "card-check.json")) >= cards_mtime:
            DO("D20", "fix gaps/cards.jsonl as listed in gaps/card-check.json (or re-spawn the synthesizer with that list), then `cards check`", *check["problems"][:5], phase="P5")
        RUN("cards check %s" % run, "thresholds and triangulation per card (D20)", phase="P5")
    cards = read_jsonl(p(run, "gaps", "cards.jsonl"))[0]
    candidates = [x for x in cards if x["status"] != "insufficient"]
    # Too few cards pass and some fail only on evidence counts (domains, source types, authors, demand):
    # one targeted round mines new domains for those cards before the red team. Live run: this lifted
    # passing cards from 1 to 3; without it the near-misses were simply dropped.
    if (_group(run, st, "redteam")[0] is None and len(candidates) < c.get("evidence.target_candidates")
            and ev.get("targeted_rounds", 0) < c.get("evidence.max_targeted_rounds") and ev["round"] < c.get("evidence.max_rounds")):
        near = gaps.near_misses(run, c.get("evidence.miners"))
        if near:
            RUN("assign %s --phase evidence --targeted" % run,
                "only %d card(s) pass; near-miss card(s) %s fail on evidence that new domains could supply: one targeted round (D08)" % (
                    len(candidates), ", ".join("%s %s" % (x["gap_id"], x["shortfall"]) for x in near)), phase="P3")
    # ---------------- P6 appraisal
    if candidates:
        s = _handle(run, st, "redteam", "red-team", "merge %s --phase redteam" % run, "P6")
        if s is None:
            RUN("assign %s --phase redteam" % run, "ADVANCE P6: adversarial red team per gap (D21)", phase="P6")
        if _stale(st, "certainty", ["redteam", "verify", "agreement", "saturation"]):
            RUN("certainty %s" % run, "GRADE-CERQual style certainty (D22)", phase="P6")
        survivors = [x for x in cards if x["status"] in ("survives", "weakened")]
        if survivors:
            s, missing = _group(run, st, "sizing")
            if s is None:
                RUN("assign %s --phase sizing" % run, "bottom-up sizing inputs (D24)", phase="P6")
            if s == "spawn":
                SPAWN("synthesizer", run, missing, phase="P6")
            if s == "ready":
                RUN("size %s" % run, phase="P6")
        if _stale(st, "score", ["certainty", "size", "redteam"]):
            RUN("score %s" % run, "gates, anchored rubric and weight sensitivity (D23)", phase="P6")
        _gate(run, st, "shortlist", state.mark(st, "score"), "Approve the ranked shortlist",
              "Gated run: confirm the ranking before the dossier is written.", "Read gaps/ranking.json; approve or decline with a note.", "P6")
    # ---------------- P7 report
    if _stale(st, "prisma", ["score", "cards_check", "verify"]):
        RUN("prisma %s" % run, "ADVANCE P7: PRISMA-style flow counts", phase="P7")
    rep = st.get("report", {})
    n = rep.get("writer_rounds", 0)
    s, missing = _group(run, st, "writer-%02d" % n) if n else (None, [])
    if s is None:
        RUN("assign %s --phase writer" % run, "dossier + handoff.json + watchlist (D25)", phase="P7")
    if s == "spawn":
        SPAWN("writer", run, missing, phase="P7")
    if s == "ready" or _stale(st, "report_check", ["prisma"]):
        RUN("validate %s --report" % run, "check the dossier against the ledger", phase="P7")
    check = read_json(p(run, "output", "report-check.json"), {}) or {}
    if not check.get("ok"):
        if n < 3:
            RUN("assign %s --phase writer" % run, "report check failed: writer fix pass", *check.get("errors", [])[:5], phase="P7")
        DO("D25", "the report check still fails after 3 writer passes: fix output/ yourself, then `validate --report`", *check.get("errors", [])[:5], phase="P7")
    # Readable outputs: a one-page summary and charts, built by a script from the run's files (no subagent).
    notes = []
    if _stale(st, "viz", ["report_check", "score", "prisma", "cards_check"]):
        if viz_available():
            RUN("viz %s" % run, "one-page summary.md and dashboard charts for the human (D25)", phase="P7")
        notes.append("dashboard skipped: matplotlib is not installed. Install it (`pip install matplotlib`), then run "
                     "`gapscan.py viz %s` for output/summary.md and output/dashboard/index.html" % run)
    show = ["summary.md", "dashboard/index.html"] if not notes else []
    raise Act("DONE", "", ["deliverables: %s" % ", ".join(os.path.join(run, "output", f) for f in show + ["dossier.md", "handoff.json", "prisma.md", "watchlist.json"])]
              + notes + [("show the human output/summary.md and the dashboard first; " if show else "") + "spend: `gapscan.py status %s`" % run,
                         "next skill: market-gap-validation reads output/handoff.json"], "P7")


def viz_available():
    import importlib.util
    return importlib.util.find_spec("matplotlib") is not None


def cmd_viz(args):
    """`gapscan.py viz RUN`: summary.md + dashboard (mgd/viz.py). Imported lazily so the core stays stdlib-only."""
    require_run(args.run)
    from . import viz
    rc = viz.cmd_viz(args)
    st = load_state(args.run)
    state.touch(st, "viz")
    save_state(args.run, st)
    return rc


def cmd_next(args):
    run = args.run
    require_run(run)
    try:
        decide(run)
        act = Act("DONE", "", [])
    except Act as a:
        act = a
    line = act.verdict + ((" " + act.argline) if act.argline else "")
    cmd = None
    if act.verdict == "RUN":
        cmd = "python3 %s %s" % (GAPSCAN, act.argline.split(" ", 1)[1])
    if args.json:
        out(json.dumps({"verdict": act.verdict, "args": act.argline, "phase": act.phase, "notes": act.notes, "cmd": cmd}, indent=2))
        return 0
    out(line)
    if act.phase:
        out("NOTE phase %s" % act.phase)
    for n in act.notes:
        out("NOTE " + str(n))
    if cmd:
        out("NOTE cmd: " + cmd)
    return 0


def _spend(run, st, by):
    """Assignments (= subagents) per phase or per model tier, from the assignment files of every group."""
    counts = {}
    for g in (st.get("groups") or {}).values():
        for apath in g.get("paths", []):
            if by == "phase":
                k = g.get("phase")
            else:
                k = ((read_json(p(run, apath), {}) or {}).get("model") or {}).get("tier") or "unrecorded"
            counts[k] = counts.get(k, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def cmd_status(args):
    run = args.run
    require_run(run)
    st = load_state(run)
    c = cfg(run)
    sat = read_json(p(run, "landscape", "saturation.json"), {}) or {}
    ents = entities(run)
    agr = read_json(p(run, "coding", "agreement.json"), {}) or {}
    th = read_json(p(run, "coding", "themes.json"), {}) or {}
    rk = read_json(p(run, "gaps", "ranking.json"), {}) or {}
    led = read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]
    gaps_cov = read_jsonl(p(run, "coverage-gaps.jsonl"))[0]
    info = {
        "run": run, "autonomy": st.get("autonomy"), "independence": st.get("independence"),
        "lexicon_rounds": st["lexicon"]["round"], "lexicon_overlap": st["lexicon"].get("overlap"),
        "landscape_rounds": st["landscape"]["round"], "saturation_verdict": sat.get("verdict"),
        "coverage": (sat.get("overall") or {}).get("coverage"), "completeness": (sat.get("overall") or {}).get("completeness"),
        "entities": len(ents), "included_verified": sum(1 for e in ents if e.get("status") == "included" and (e.get("verified") or {}).get("status") == "ok"),
        "evidence_rounds": st["evidence"]["round"], "evidence_records": len(led),
        "verified_records": sum(1 for r in led if r.get("verification", {}).get("status") == "verified"),
        "codebook_version": st["coding"].get("version"), "agreement": agr.get("verdict"), "themes_saturated": th.get("saturated"),
        "ranked_gaps": [(x["rank"], x["gap_id"], round(x["total"], 1)) for x in rk.get("ranked", [])],
        "budget": {"subagents": "%d/%d" % (st.get("budget", {}).get("subagents_used", 0), c.get("budget.subagents_max"))},
        "spend_by_phase": _spend(run, st, "phase"), "spend_by_tier": _spend(run, st, "tier"),
        "model_escalations": [(x["role"], x["level"], x["reason"]) for x in (st.get("models") or {}).get("log", [])],
        "open_human_tasks": [t["id"] + " " + t["title"] for t in hq.open_tasks(run)],
        "coverage_gaps": len(gaps_cov),
    }
    if args.json:
        out(json.dumps(info, indent=2))
        return 0
    for k, v in info.items():
        out("%-20s %s" % (k, v))
    return 0
