"""init, protocol (check/show/freeze/amend), doctor and hq commands."""

import json
import os
import re
import secrets
import shutil
import subprocess
import sys

from mgcore import hq, state
from mgcore.jsonio import append_jsonl, now_iso, read_json, sha256_json, today, write_json

from . import net
from .common import (CliError, EXIT_BLOCKED, cfg, channels, out, p, protocol, require_run, save_state, load_state,
                     validate)

RUN_DIRS = ["lexicon", "landscape", "snapshots", "raw", "evidence", "evidence/signals", "coding", "analysis",
            "gaps", "gaps/redteam", "output", "cache"]


def draft_protocol(run_id, topic, title, seed, autonomy):
    return {
        "schema_version": "1.0", "run_id": run_id, "title": title or topic, "topic": topic,
        "question": "",
        "picos": {"population": "", "intervention": "", "comparator": "", "outcomes": "", "setting": ""},
        "scope": {"in": [], "out": []},
        "business_models": ["b2b-saas"],
        "geography": ["global"], "languages": ["en"],
        "as_of": today(), "recency_days": 730,
        "eligibility": {"include": [], "exclude": []},
        "founder_fit": {"skills": [], "budget_usd": 0, "hours_per_week": 0, "exclusions": [],
                        "schlep_tolerance": "medium", "unfair_advantages": []},
        "ambition": {"min_arr_usd": 0},
        "variation_dimensions": {"segment": [], "language": [], "platform": [], "price_tier": [],
                                 "delivery": [], "integration": [], "ai_native": [True, False]},
        "competing_factors": [],
        "sources": {"allowed_tiers": [0, 1], "tier2_enabled": [], "excluded_extra": []},
        "autonomy": autonomy, "budget": {"subagents_max": 80, "fetches_max": 3000},
        "overrides": {}, "seed": seed, "notes": "",
    }


def cmd_init(args):
    run = args.run
    if os.path.exists(p(run, "state.json")):
        raise CliError("%s already holds a run; choose a new folder." % run)
    for d in RUN_DIRS:
        os.makedirs(p(run, d), exist_ok=True)
    with open(p(run, ".salt"), "w") as fh:
        fh.write(secrets.token_hex(16))
    seed = args.seed if args.seed is not None else secrets.randbelow(10 ** 9)
    run_id = os.path.basename(os.path.normpath(run))
    write_json(p(run, "protocol.json"), draft_protocol(run_id, args.topic, args.title, seed, args.autonomy))
    st = {"schema_version": "1.0", "run_id": run_id, "created_at": now_iso(), "seed": seed,
          "autonomy": args.autonomy, "independence": "full", "groups": {},
          "lexicon": {"round": 0, "merged": 0, "overlap": None},
          "landscape": {"round": 0, "merged": 0, "used_blocks": [], "used_personas": [], "family_units": {},
                        "screen_batch": 0, "verdict": None, "expand_units": None, "sampling_closed": False,
                        "probe_count": 0, "snowball_iteration": 0, "snowballed": []},
          "evidence": {"round": 0, "merged": 0, "why_now_seq": 0, "ev_seq": 0},
          "coding": {"version": 0, "revisions": 0, "closed_batches": 0},
          "report": {"writer_rounds": 0}}
    save_state(run, st)
    state.event(run, "init", topic=args.topic, seed=seed, autonomy=args.autonomy)
    out("Created run %s (seed %d, autonomy %s)." % (run, seed, args.autonomy))
    out("Next: fill protocol.json following method card D01, then `gapscan.py protocol check %s`." % run)
    return 0


def protocol_errors(run, proto=None):
    proto = proto if proto is not None else protocol(run)
    errs = validate(proto, "protocol")
    if proto.get("run_id") and proto["run_id"] != os.path.basename(os.path.normpath(run)):
        errs.append("$.run_id: must equal the run folder name (%s)" % os.path.basename(os.path.normpath(run)))
    fams = channels().get("families", {})
    src = proto.get("sources", {}) or {}
    for fam in src.get("tier2_enabled", []) or []:
        if fams.get(fam, {}).get("tier") != 2:
            errs.append("$.sources.tier2_enabled: %s is not a tier-2 family in channels.json" % fam)
        elif 2 not in (src.get("allowed_tiers") or []):
            errs.append("$.sources.allowed_tiers: must include 2 when tier2_enabled is not empty")
    dims = proto.get("variation_dimensions") or {}
    if not any(v for k, v in dims.items() if k != "ai_native"):
        errs.append("$.variation_dimensions: list at least one value in one dimension (method card D19)")
    return errs


def protocol_warnings(run, proto=None):
    """Non-blocking advice: settings that make a run expensive or its evidence thin."""
    proto = proto if proto is not None else protocol(run)
    c = cfg(run)
    warns = []
    inter = (proto.get("picos") or {}).get("intervention") or ""
    jobs = [x for x in re.split(r"[,;]", inter.split(":", 1)[-1]) if len(x.strip()) > 2]
    if len(jobs) >= c.get("scope.broad_jobs_warning"):
        warns.append(("picos.intervention names about %d jobs. Each job is its own sub-market: a broad run spends most of its budget "
                      "mapping supply and spreads evidence thin (live run: 7 jobs -> 395 competitors, 1 weak surviving gap). "
                      "Prefer one run per job, or keep at most 3.") % len(jobs))
    if not proto.get("cost_profile"):
        warns.append("cost_profile not set: using '%s' (fast tier for scouts, screeners, miners, coders; standard for synthesis, "
                     "red team, writer). Set budget or quality with `protocol amend` if needed." % c.get("models.profile"))
    return warns


def cmd_protocol(args):
    run = args.run
    require_run(run)
    action = args.action
    if action == "show":
        out(json.dumps(protocol(run), indent=2, ensure_ascii=False))
        return 0
    if action == "check":
        errs = protocol_errors(run)
        if errs:
            out("protocol.json is not ready (%d problems):" % len(errs))
            for e in errs:
                out("  - " + e)
            return 1
        out("protocol.json is valid.")
        for w in protocol_warnings(run):
            out("  warning: " + w)
        return 0
    if action == "freeze":
        errs = protocol_errors(run)
        if errs:
            raise CliError("protocol.json is not valid; run `protocol check` first.")
        lock_path = p(run, "protocol.lock.json")
        if os.path.exists(lock_path):
            raise CliError("protocol is already frozen; change it with `protocol amend`.")
        proto = protocol(run)
        if proto.get("autonomy") == "gated":
            gate = hq.latest_gate(run, "protocol")
            if not gate or gate["status"] != "done":
                raise CliError("gated run: the human must approve the protocol first (see `next`).", EXIT_BLOCKED)
        lock = {"sha256": sha256_json(proto), "frozen_at": now_iso(), "amendments": []}
        write_json(lock_path, lock)
        st = load_state(run)
        st["autonomy"] = proto.get("autonomy", st.get("autonomy"))
        state.touch(st, "protocol")
        save_state(run, st)
        state.event(run, "protocol_freeze", sha256=lock["sha256"])
        out("Protocol frozen (sha256 %s)." % lock["sha256"])
        return 0
    if action == "amend":
        lock_path = p(run, "protocol.lock.json")
        lock = read_json(lock_path)
        if not lock:
            raise CliError("protocol is not frozen yet; edit protocol.json directly before freezing.")
        if not args.reason:
            raise CliError("--reason is required for an amendment.")
        proto = protocol(run)
        old = sha256_json(proto)
        if old != lock["sha256"]:
            raise CliError("protocol.json was edited after freezing; restore it and use `protocol amend`.")
        st = load_state(run)
        applied = []
        for item in args.set or []:
            if "=" not in item:
                raise CliError("--set expects KEY=JSON, got %r" % item)
            key, raw = item.split("=", 1)
            try:
                value = json.loads(raw)
            except ValueError:
                value = raw
            node = proto
            parts = key.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value
            if key == "independence":
                st["independence"] = value
            applied.append({"key": key, "value": value})
        errs = protocol_errors(run, proto)
        if errs:
            raise CliError("amendment would make the protocol invalid: " + "; ".join(errs[:3]))
        write_json(p(run, "protocol.json"), proto)
        new = sha256_json(proto)
        lock["amendments"].append({"at": now_iso(), "reason": args.reason, "sets": applied, "old_sha256": old, "new_sha256": new})
        lock["sha256"] = new
        write_json(lock_path, lock)
        state.touch(st, "protocol")
        save_state(run, st)
        state.event(run, "protocol_amend", reason=args.reason, sets=applied)
        out("Amendment %d recorded (sha256 %s)." % (len(lock["amendments"]), new))
        return 0
    raise CliError("unknown protocol action %s" % action)


DOCTOR_PROBES = {
    "hn": ("https://hn.algolia.com/api/v1/search?query=saas&hitsPerPage=1", False),
    "se": ("https://api.stackexchange.com/2.3/info?site=stackoverflow", False),
    "wp": ("https://api.wordpress.org/plugins/info/1.2/?action=query_plugins&request[search]=invoice&request[per_page]=1", False),
    "apple": ("https://itunes.apple.com/search?term=invoice&entity=software&limit=1", False),
    "atl": ("https://marketplace.atlassian.com/rest/2/addons?text=jira&limit=1", False),
    "yc": ("https://yc-oss.github.io/api/meta.json", False),
}


def cmd_doctor(args):
    run = args.run
    require_run(run)
    report = {"checked_at": now_iso(), "python": sys.version.split()[0], "families": {}, "tier2": {}, "warnings": []}
    if sys.version_info < (3, 8):
        report["warnings"].append("Python 3.8+ is required")
    contact = os.environ.get("MGD_CONTACT")
    report["contact_set"] = bool(contact)
    if not contact:
        t = hq.add(run, "key", "Set MGD_CONTACT for polite API access",
                   "Wikimedia requires a contact User-Agent; other APIs appreciate one. Only the human may choose what contact to publish.",
                   "export MGD_CONTACT='your-project-url or contact email' in the shell that runs the agent",
                   "the environment variable MGD_CONTACT (never written to files)", "P0", blocking=False,
                   fallback="Wikipedia pageview signals are skipped and recorded as a coverage gap.", gate="contact")
        report["warnings"].append("MGD_CONTACT not set (%s)" % t["id"])
    gh = shutil.which("gh")
    gh_ok = False
    if gh:
        try:
            gh_ok = subprocess.run([gh, "auth", "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20).returncode == 0
        except Exception:
            gh_ok = False
    report["families"]["gh"] = {"status": "ok" if gh_ok else "unavailable",
                                "detail": "gh authenticated" if gh_ok else ("gh not installed" if not gh else "gh not logged in")}
    if not gh_ok:
        hq.add(run, "account", "Log in to GitHub CLI", "GitHub issue and repo search needs an authenticated gh CLI.",
               "Run `gh auth login` in a terminal (read-only scopes are enough).", "gh auth status shows logged in", "P0",
               blocking=False, fallback="GitHub family skipped; recorded as a coverage gap.", gate="gh")
    if os.environ.get("CODEX_SANDBOX_NETWORK_DISABLED"):
        report["warnings"].append("Codex sandbox reports network disabled: run Codex with network access for discovery.")
    fams = channels().get("families", {})
    for fam, (url, _robots) in DOCTOR_PROBES.items():
        if args.offline:
            report["families"][fam] = {"status": "skipped", "detail": "--offline"}
            continue
        status, detail = net.probe(url)
        report["families"][fam] = {"status": "ok" if status == 200 else "unreachable", "detail": detail}
    if contact and not args.offline:
        status, detail = net.probe("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Invoice/monthly/20250101/20250301")
        report["families"]["wiki"] = {"status": "ok" if status == 200 else "unreachable", "detail": detail}
    else:
        report["families"]["wiki"] = {"status": "skipped", "detail": "needs MGD_CONTACT" if not contact else "--offline"}
    psl_path = p(run, "cache", "public_suffix_list.dat")
    if not args.offline and not os.path.exists(psl_path):
        ok = net.download("https://publicsuffix.org/list/public_suffix_list.dat", psl_path)
        report["psl"] = "full list cached" if ok else "using psl-mini.txt"
    else:
        report["psl"] = "full list cached" if os.path.exists(psl_path) else "using psl-mini.txt"
    for fam, meta in fams.items():
        if meta.get("tier") == 2:
            envs = [e.strip() for e in (meta.get("env") or "").replace(" or ", ",").split(",") if e.strip()]
            report["tier2"][fam] = {"env": meta.get("env"), "key_present": bool(envs) and all(os.environ.get(e) for e in envs)}
    for fam, res in report["families"].items():
        if res["status"] != "ok":
            append_jsonl(p(run, "coverage-gaps.jsonl"), {"at": now_iso(), "source": fam, "reason": res["detail"], "by": "doctor"})
    write_json(p(run, "doctor.json"), report)
    st = load_state(run)
    state.touch(st, "doctor")
    save_state(run, st)
    ok = [f for f, r in report["families"].items() if r["status"] == "ok"]
    out("doctor: reachable families: %s" % (", ".join(sorted(ok)) or "none"))
    for w in report["warnings"]:
        out("  warning: " + w)
    out("Wrote doctor.json; unreachable sources were recorded in coverage-gaps.jsonl.")
    return 0


def cmd_hq(args):
    run = args.run
    require_run(run)
    if args.action == "list":
        data = hq.load(run)
        if not data["tasks"]:
            out("No human tasks.")
        for t in data["tasks"]:
            out("%s [%s]%s %s (%s, phase %s)" % (t["id"], t["status"], " BLOCKING" if t["blocking"] else "", t["title"], t["type"], t["phase"]))
            if t["status"] == "open":
                out("    why: %s\n    steps: %s\n    return: %s" % (t["why"], t["steps"], t["returns"]))
        return 0
    if args.action == "add":
        t = hq.add(run, args.type, args.title, args.why, args.steps, args.returns, args.phase or "-",
                   blocking=args.blocking, fallback=args.fallback)
        out("Added %s." % t["id"])
        return 0
    if args.action in ("done", "decline"):
        t = hq.close(run, args.task, "done" if args.action == "done" else "declined", args.note)
        st = load_state(run)
        state.touch(st, "hq")
        save_state(run, st)
        state.event(run, "hq_" + args.action, task=t["id"], note=args.note)
        out("%s marked %s." % (t["id"], t["status"]))
        return 0
    raise CliError("unknown hq action")
