"""`gapscan.py merge RUN --phase PHASE`: validate agent outputs and fold them into the run's
ledgers. Agents never edit ledgers directly; merges are the only writers."""

import json
import os
import re

from mgcore import canon, state
from mgcore.jsonio import append_jsonl, now_iso, read_json, read_jsonl, write_json, write_jsonl

from . import lexicon as lexmod
from . import net
from .common import (CliError, alias_map, codebook, entities, resolve_ids, frozen_codebook, out, p, psl, require_run, load_state,
                     save_state, validate)
from .privacy import author_hash

RAW_HANDLE = re.compile(r"(^|\s)(@[A-Za-z0-9_]{2,}|u/[A-Za-z0-9_-]{2,})")


def _group(st, key):
    g = st.get("groups", {}).get(key)
    if not g:
        raise CliError("no assignment group %s; run `assign` first" % key)
    return g


def _outputs(run, g):
    res = []
    for apath in g["paths"]:
        a = read_json(p(run, apath))
        for o in a["outputs"]:
            if not os.path.exists(p(run, o["path"])):
                raise CliError("missing output %s (assignment %s); spawn that subagent again" % (o["path"], apath))
            res.append((a, o))
    return res


def _jsonl_valid(run, path, schema_name, label):
    recs, errs = read_jsonl(p(run, path))
    problems = ["line %d: invalid JSON (%s)" % (n, m) for n, m in errs]
    good = []
    for i, r in enumerate(recs, 1):
        e = validate(r, schema_name)
        if e:
            problems.append("record %d: %s" % (i, "; ".join(e[:3])))
        else:
            good.append(r)
    return good, problems


# ---------------------------------------------------------------- landscape / probe / snowball
def _load_entities(run):
    ents = entities(run)
    by_id = {e["entity_id"]: e for e in ents}
    alias = {}
    for e in ents:
        for k in [e["entity_id"]] + e.get("aliases", []):
            alias[k] = e["entity_id"]
    return by_id, alias


_STATUS_RANK = {"included": 3, "unsure": 2, "new": 1, "excluded": 0}


def _absorb(by_id, alias, keep, drop):
    a, b = by_id[keep], by_id.pop(drop)
    for f in ("names", "urls", "aliases", "found_in_units", "found_via"):
        a[f] = sorted(set(a.get(f, [])) | set(b.get(f, [])))
    a["aliases"] = sorted(set(a["aliases"]) | {drop})
    if _STATUS_RANK.get(b.get("status"), 0) > _STATUS_RANK.get(a.get("status"), 0):
        a["status"], a["screening"], a["verified"] = b.get("status"), b.get("screening"), b.get("verified")
    for k in a["aliases"] + [keep]:
        alias[k] = keep


def merge_landscape(run, phase):
    require_run(run)
    st = load_state(run)
    ls = st["landscape"]
    if phase == "landscape":
        key, via, rnd = "landscape-R%02d" % ls["round"], "sampling", ls["round"]
    elif phase == "probe":
        key, via, rnd = "probe-%d" % ls.get("probe_count", 0), "probe", ls["round"]
    else:
        key, via, rnd = "snowball-%02d" % ls.get("snowball_iteration", 0), "snowball", None
    g = _group(st, key)
    if g.get("merged"):
        raise CliError("%s is already merged" % key)
    ps = psl(run)
    by_id, alias = _load_entities(run)
    units = read_json(p(run, "landscape", "units.json"), {}) or {}
    stats = {"items": 0, "new_entities": 0, "matched_existing": 0, "invalid": []}
    queries_logged = set()
    for q in read_jsonl(p(run, "queries.jsonl"))[0]:
        queries_logged.add((q.get("unit"), q.get("source"), q.get("query")))
    for a, o in _outputs(run, g):
        doc = read_json(p(run, o["path"]))
        errs = validate(doc, "landscape-output")
        if errs:
            raise CliError("%s is invalid:\n  %s" % (o["path"], "\n  ".join(errs[:10])))
        allowed = {c["unit_id"]: c for c in a.get("channels", [])}
        for unit in doc["units"]:
            uid = unit["unit_id"]
            if uid not in allowed:
                stats["invalid"].append("%s: unit %s is not in the assignment" % (o["path"], uid))
                continue
            ch = allowed[uid]
            units[uid] = {"scout": doc["scout_id"], "family": ch["family"], "kinds": ch["kinds"], "round": rnd,
                          "mode": doc["mode"], "group": key, "assignment_id": a["assignment_id"],
                          "stop_reason": unit.get("stop_reason") or doc.get("stop_reason"), "items": len(unit["items"])}
            for q in unit.get("queries", []):
                if (uid, q.get("source"), q.get("query")) not in queries_logged:
                    append_jsonl(p(run, "queries.jsonl"), {"at": now_iso(), "by": "scout-" + doc["scout_id"], "unit": uid,
                                                           "source": q.get("source"), "query": q.get("query"),
                                                           "total_hits": q.get("results"), "method": "agent-reported"})
                    queries_logged.add((uid, q.get("source"), q.get("query")))
            for it in unit["items"]:
                stats["items"] += 1
                if net.excluded_reason(it["url"]):
                    stats["invalid"].append("%s: %s is an excluded source" % (uid, it["url"]))
                    continue
                keys = [canon.entity_key(it["url"], it["kind"], ps)]
                if it.get("listing_url") and not net.excluded_reason(it["listing_url"]):
                    keys.append(canon.entity_key(it["listing_url"], it["kind"], ps))
                found = sorted(set(alias[k] for k in keys if k in alias))
                if found:
                    keep = sorted(found, key=canon._key_rank)[0]
                    for other in found:
                        if other != keep:
                            _absorb(by_id, alias, keep, other)
                    stats["matched_existing"] += 1
                else:
                    keep = sorted(keys, key=canon._key_rank)[0]
                    by_id[keep] = {"entity_id": keep, "kind": it["kind"], "names": [], "urls": [], "aliases": [],
                                   "found_in_units": [], "found_via": [], "first_round": rnd, "first_group": key,
                                   "status": "new", "screening": None, "verified": None}
                    stats["new_entities"] += 1
                e = by_id[keep]
                e["names"] = sorted(set(e["names"]) | {it["name"].strip()})
                e["urls"] = e["urls"] + [canon.normalize_url(it["url"])] if canon.normalize_url(it["url"]) not in e["urls"] else e["urls"]
                e["aliases"] = sorted(set(e["aliases"]) | set(k for k in keys if k != keep))
                e["found_in_units"] = sorted(set(e["found_in_units"]) | {uid})
                e["found_via"] = sorted(set(e["found_via"]) | {via})
                for k in keys:
                    alias[k] = keep
    write_jsonl(p(run, "landscape", "entities.jsonl"), sorted(by_id.values(), key=lambda e: e["entity_id"]))
    write_json(p(run, "landscape", "units.json"), units)
    folder = os.path.dirname(g["paths"][0])
    write_json(p(run, folder, "merge.json"), dict(stats, group=key, merged_at=now_iso()))
    g["merged"] = True
    if phase == "landscape":
        ls["merged"] = ls["round"]
    state.touch(st, "landscape_merge")
    save_state(run, st)
    state.event(run, "merge_" + phase, group=key, **{k: v for k, v in stats.items() if k != "invalid"})
    out("Merged %s: %d items, %d new entities, %d matched existing, %d invalid." % (
        key, stats["items"], stats["new_entities"], stats["matched_existing"], len(stats["invalid"])))
    for msg in stats["invalid"][:10]:
        out("  invalid: " + msg)
    return 0


# ---------------------------------------------------------------- screening
def merge_screen(run):
    st = load_state(run)
    k = st["landscape"]["screen_batch"]
    key = "screen-%02d" % k
    g = _group(st, key)
    by_id, _alias = _load_entities(run)
    decisions = {}
    problems = []
    for a, o in _outputs(run, g):
        recs, errs = _jsonl_valid(run, o["path"], "screening", o["path"])
        problems += ["%s %s" % (o["path"], e) for e in errs]
        expected = set(x["entity_id"] for x in a["inputs"]["entities"])
        got = set(r["entity_id"] for r in recs)
        missing = expected - got
        if missing:
            problems.append("%s misses decisions for %s" % (o["path"], ", ".join(sorted(missing)[:10])))
        decisions.setdefault(a["scout_id"], {}).update({r["entity_id"]: r for r in recs if r["entity_id"] in expected})
    if problems:
        raise CliError("screening outputs need fixing:\n  " + "\n  ".join(problems[:15]))
    for eid, r in decisions.get("A", {}).items():
        if eid not in by_id:
            continue
        status = {"include": "included", "exclude": "excluded", "unsure": "unsure"}[r["decision"]]
        by_id[eid]["status"] = status
        by_id[eid]["screening"] = {"decision": r["decision"], "reason_code": r["reason_code"], "note": r.get("note"),
                                   "duplicate_of": r.get("duplicate_of"), "batch": k}
    for sid in ("A", "B"):
        for r in decisions.get(sid, {}).values():
            append_jsonl(p(run, "landscape", "screening.jsonl"), dict(r, batch=k))
    write_jsonl(p(run, "landscape", "entities.jsonl"), sorted(by_id.values(), key=lambda e: e["entity_id"]))
    g["merged"] = True
    state.touch(st, "screen_merge")
    save_state(run, st)
    inc = sum(1 for r in decisions.get("A", {}).values() if r["decision"] == "include")
    out("Screening batch %d merged: %d decisions (%d included); %d audit decisions kept for the audit." % (
        k, len(decisions.get("A", {})), inc, len(decisions.get("B", {}))))
    return 0


# ---------------------------------------------------------------- mapping
def merge_mapping(run):
    st = load_state(run)
    g = _group(st, "mapping")
    cls = read_json(p(run, "landscape", "classification.json"))
    errs = validate(cls, "classification") if cls else ["classification.json missing"]
    if errs:
        raise CliError("classification.json is invalid:\n  " + "\n  ".join(errs[:10]))
    ids = {f: set(v["id"] for v in vals) for f, vals in cls["facets"].items()}
    recs, problems = _jsonl_valid(run, "landscape/entity-attributes.jsonl", "entity-attributes", "attributes")
    by_id, _ = _load_entities(run)
    for r in recs:
        e = by_id.get(r["entity_id"])
        if not e or e.get("status") != "included":
            problems.append("%s is not an included entity" % r["entity_id"])
        if r["approach"] not in ids["approach"]:
            problems.append("%s: approach %s not in classification" % (r["entity_id"], r["approach"]))
        if r["category"] not in ids["category"]:
            problems.append("%s: category %s not in classification" % (r["entity_id"], r["category"]))
        for s in r.get("segments", []):
            if s not in ids["segment"]:
                problems.append("%s: segment %s not in classification" % (r["entity_id"], s))
        for sha in r.get("evidence", []):
            if not os.path.exists(p(run, "snapshots", sha + ".raw")):
                problems.append("%s: snapshot %s does not exist" % (r["entity_id"], sha))
    if problems:
        raise CliError("mapping outputs need fixing:\n  " + "\n  ".join(problems[:15]))
    g["merged"] = True
    state.touch(st, "mapping")
    save_state(run, st)
    out("Mapping merged: %d facets, %d competing factors, %d entities described." % (len(ids), len(cls["competing_factors"]), len(recs)))
    return 0


# ---------------------------------------------------------------- evidence
def _norm_quote(q):
    return re.sub(r"\s+", " ", q.strip().casefold())


def _snapshot_id(run, sid):
    """Full snapshot id for `sid`; a unique prefix of >= 12 hex chars resolves to the full sha256 name."""
    if not sid or os.path.exists(p(run, "snapshots", sid + ".meta.json")):
        return sid
    if len(sid) >= 12 and re.fullmatch(r"[0-9a-f]+", sid):
        hits = [f[:-len(".meta.json")] for f in os.listdir(p(run, "snapshots"))
                if f.startswith(sid) and f.endswith(".meta.json")]
        if len(hits) == 1:
            return hits[0]
    return sid


def merge_evidence(run, retry=False):
    st = load_state(run)
    ev = st["evidence"]
    r = ev["round"]
    g = _group(st, "evidence-R%02d" % r)
    if g.get("merged") and not retry:
        raise CliError("evidence round %d already merged (after fixing rejected records, use --retry)" % r)
    ps = psl(run)
    led = read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]
    seen = set((x["url"], _norm_quote(x["quote"])) for x in led)
    _wn_key = lambda x: json.dumps({k: v for k, v in x.items() if k not in ("id", "miner", "round")}, sort_keys=True)
    wn_seen = set(_wn_key(x) for x in read_jsonl(p(run, "evidence", "why-now.jsonl"))[0])
    amap = alias_map(run)
    report = {"round": r, "accepted": 0, "duplicates": 0, "rejected": [], "why_now": 0, "retry": bool(retry)}
    for a, o in _outputs(run, g):
        recs, errs = read_jsonl(p(run, o["path"]))
        report["rejected"] += ["%s line %d: invalid JSON" % (o["path"], n) for n, _m in errs]
        for i, rec in enumerate(recs, 1):
            where = "%s #%d" % (o["path"], i)
            if o["schema"] == "why-now":
                e = validate(rec, "why-now")
                if e:
                    report["rejected"].append("%s: %s" % (where, "; ".join(e[:2])))
                    continue
                rec["snapshot"] = _snapshot_id(run, rec["snapshot"])
                if not os.path.exists(p(run, "snapshots", rec["snapshot"] + ".raw")):
                    report["rejected"].append("%s: snapshot %s does not exist" % (where, rec["snapshot"]))
                    continue
                if _wn_key(rec) in wn_seen:
                    report["duplicates"] += 1
                    continue
                wn_seen.add(_wn_key(rec))
                ev["why_now_seq"] = ev.get("why_now_seq", 0) + 1
                rec = dict(rec, id="WN-%03d" % ev["why_now_seq"], miner=a.get("scout_id"), round=r)
                append_jsonl(p(run, "evidence", "why-now.jsonl"), rec)
                report["why_now"] += 1
                continue
            for raw in ("author", "author_handle", "username", "user"):
                if raw in rec:
                    report["rejected"].append("%s: raw author field '%s' is not allowed; use author_hash" % (where, raw))
                    rec = None
                    break
            if rec is None:
                continue
            e = validate(rec, "evidence")
            if e:
                report["rejected"].append("%s: %s" % (where, "; ".join(e[:2])))
                continue
            if RAW_HANDLE.search(rec["quote"]):
                report["rejected"].append("%s: quote contains a username/handle; choose a quote without it" % where)
                continue
            reason = net.excluded_reason(rec["url"])
            if reason:
                report["rejected"].append("%s: excluded source (%s)" % (where, reason))
                continue
            rec["snapshot"] = _snapshot_id(run, rec["snapshot"])
            meta = read_json(p(run, "snapshots", rec["snapshot"] + ".meta.json"))
            if not meta:
                report["rejected"].append("%s: snapshot %s was not created by gapscan" % (where, rec["snapshot"]))
                continue
            k = (rec["url"], _norm_quote(rec["quote"]))
            if k in seen:
                report["duplicates"] += 1
                continue
            seen.add(k)
            ids = resolve_ids(rec.get("entity_ids"), amap)
            unknown = [x for x in ids if x not in amap]
            ev["ev_seq"] = ev.get("ev_seq", 0) + 1
            rec = dict(rec)
            if "entity_ids" in rec:
                rec["entity_ids"] = ids
            rec.update({"id": "EV-%06d" % ev["ev_seq"], "miner": a.get("scout_id"), "round": r,
                        "domain": ps.registrable(canon.host_of(rec["url"])),
                        "retrieved_at": meta.get("fetched_at"), "verification": {"status": "pending", "offset": None}})
            if unknown:
                rec["note"] = ((rec.get("note") or "") + " unknown entity ids: %s" % ", ".join(unknown))[:300]
                for x in unknown:
                    report.setdefault("unknown_entities", {}).setdefault(x, []).append(rec["id"])
            led.append(rec)
            report["accepted"] += 1
    write_jsonl(p(run, "evidence", "ledger.jsonl"), led)
    name = "merge.json"
    if retry and os.path.exists(p(run, "evidence", "round-%02d" % r, name)):
        k = 1
        while os.path.exists(p(run, "evidence", "round-%02d" % r, "merge-retry-%d.json" % k)):
            k += 1
        name = "merge-retry-%d.json" % k
    write_json(p(run, "evidence", "round-%02d" % r, name), report)
    g["merged"] = True
    ev["merged"] = r
    state.touch(st, "evidence_merge")
    save_state(run, st)
    state.event(run, "merge_evidence", round=r, accepted=report["accepted"], rejected=len(report["rejected"]))
    out("Evidence round %d merged: %d accepted, %d duplicates, %d rejected, %d why-now entries." % (
        r, report["accepted"], report["duplicates"], len(report["rejected"]), report["why_now"]))
    if report.get("unknown_entities"):
        # Products first seen while mining evidence: the landscape missed them. Report, never hide.
        out("Post-landscape discoveries: %d product key(s) named in evidence are not in the landscape (%s). "
            "They are listed in evidence/round-%02d/merge.json and belong in the dossier's limitations." % (
                len(report["unknown_entities"]), ", ".join(sorted(report["unknown_entities"])[:8]), r))
    for msg in report["rejected"][:12]:
        out("  rejected: " + msg)
    out("Next: `gapscan.py verify %s` checks every quote against its snapshot." % run)
    return 0


# ---------------------------------------------------------------- coding
def merge_coding(run):
    st = load_state(run)
    cd = st["coding"]
    v = cd["version"]
    book = frozen_codebook(run)
    if not book:
        raise CliError("no frozen codebook")
    valid_codes = set(c["id"] for c in book["codes"])
    verified = set(r["id"] for r in read_jsonl(p(run, "evidence", "ledger.jsonl"))[0]
                   if r.get("verification", {}).get("status") == "verified")
    pending = [k for k, g in st.get("groups", {}).items()
               if g["phase"] in ("coding-closed", "coding-reliability") and not g.get("merged")]
    if not pending:
        raise CliError("no unmerged coding assignments")
    problems = []
    merged_a = {(r["evidence_id"], r["codebook_version"]): r for r in read_jsonl(p(run, "coding", "codes-A.jsonl"))[0]}
    for key in pending:
        g = st["groups"][key]
        for a, o in _outputs(run, g):
            recs, errs = _jsonl_valid(run, o["path"], "code-assignment", o["path"])
            problems += ["%s %s" % (o["path"], e) for e in errs]
            expected = set(x["id"] for x in a["inputs"]["records"])
            for r in recs:
                bad = [c for c in r["codes"] if c not in valid_codes]
                if bad:
                    problems.append("%s: %s uses codes not in codebook v%d: %s" % (o["path"], r["evidence_id"], v, ", ".join(bad)))
                if r["evidence_id"] not in verified or r["evidence_id"] not in expected:
                    problems.append("%s: %s is not a verified record of this assignment" % (o["path"], r["evidence_id"]))
                if r["codebook_version"] != v:
                    problems.append("%s: %s uses codebook_version %s, expected %d" % (o["path"], r["evidence_id"], r["codebook_version"], v))
            missing = expected - set(r["evidence_id"] for r in recs)
            if missing:
                problems.append("%s misses %d records (e.g. %s)" % (o["path"], len(missing), ", ".join(sorted(missing)[:5])))
            if a["scout_id"] == "A":
                for r in recs:
                    merged_a[(r["evidence_id"], r["codebook_version"])] = r
    if problems:
        raise CliError("coding outputs need fixing:\n  " + "\n  ".join(problems[:15]))
    write_jsonl(p(run, "coding", "codes-A.jsonl"), sorted(merged_a.values(), key=lambda r: (r["codebook_version"], r["evidence_id"])))
    for key in pending:
        g = st["groups"][key]
        if g["phase"] == "coding-reliability":
            # Top-ups add to coder B's codes; they never replace earlier double-coded records.
            allb = {(x["evidence_id"], x["codebook_version"]): x for x in read_jsonl(p(run, "coding", "codes-B.jsonl"))[0]}
            for path in g["paths"]:
                src = read_json(p(run, path))["outputs"][0]["path"]
                for r in read_jsonl(p(run, src))[0]:
                    allb[(r["evidence_id"], r["codebook_version"])] = r
            write_jsonl(p(run, "coding", "codes-B.jsonl"), sorted(allb.values(), key=lambda r: (r["codebook_version"], r["evidence_id"])))
        g["merged"] = True
    state.touch(st, "coding_merge")
    save_state(run, st)
    out("Coding merged for codebook v%d (%d groups)." % (v, len(pending)))
    return 0


# ---------------------------------------------------------------- supply
def merge_supply(run):
    st = load_state(run)
    g = _group(st, "supply")
    book = frozen_codebook(run)
    jobs = set(c["id"] for c in book["codes"] if c["type"] in ("job", "outcome"))
    cls = read_json(p(run, "landscape", "classification.json"), {}) or {}
    factors = set(f["id"] for f in cls.get("competing_factors", []))
    recs, problems = _jsonl_valid(run, "analysis/supply.jsonl", "supply", "supply")
    by_id, _ = _load_entities(run)
    for r in recs:
        if by_id.get(r["entity_id"], {}).get("status") != "included":
            problems.append("%s is not an included entity" % r["entity_id"])
        bad = [j for j in r["jobs_served"] if j not in jobs]
        if bad:
            problems.append("%s: unknown job/outcome codes %s" % (r["entity_id"], ", ".join(bad)))
        badf = [f for f in r["factor_levels"] if f not in factors]
        if badf:
            problems.append("%s: unknown competing factors %s" % (r["entity_id"], ", ".join(badf)))
        for f, lvl in r["factor_levels"].items():
            if lvl not in (0, 1, 2, 3):
                problems.append("%s: factor %s level must be 0-3" % (r["entity_id"], f))
        for sha in r["evidence"]:
            if not os.path.exists(p(run, "snapshots", sha + ".raw")):
                problems.append("%s: snapshot %s does not exist" % (r["entity_id"], sha))
    if problems:
        raise CliError("supply.jsonl needs fixing:\n  " + "\n  ".join(problems[:15]))
    g["merged"] = True
    state.touch(st, "supply")
    save_state(run, st)
    out("Supply merged: %d entities mapped to jobs." % len(recs))
    return 0


# ---------------------------------------------------------------- red team
def merge_redteam(run):
    st = load_state(run)
    g = _group(st, "redteam")
    cards = read_jsonl(p(run, "gaps", "cards.jsonl"))[0]
    by = {c["gap_id"]: c for c in cards}
    problems, judgments = [], []
    for a, o in _outputs(run, g):
        doc = read_json(p(run, o["path"]))
        e = validate(doc, "redteam")
        if e:
            problems.append("%s: %s" % (o["path"], "; ".join(e[:4])))
            continue
        if doc["gap_id"] not in by:
            problems.append("%s: unknown gap %s" % (o["path"], doc["gap_id"]))
            continue
        by[doc["gap_id"]]["status"] = doc["verdict"]
        judgments.append(dict(doc["judgment"], gap_id=doc["gap_id"]))
    if problems:
        raise CliError("red-team outputs need fixing:\n  " + "\n  ".join(problems[:15]))
    write_jsonl(p(run, "gaps", "cards.jsonl"), cards)
    write_jsonl(p(run, "gaps", "judgments.jsonl"), judgments)
    g["merged"] = True
    state.touch(st, "redteam")
    save_state(run, st)
    verdicts = {}
    for j in judgments:
        verdicts[by[j["gap_id"]]["status"]] = verdicts.get(by[j["gap_id"]]["status"], 0) + 1
    out("Red team merged: %s." % ", ".join("%d %s" % (n, v) for v, n in sorted(verdicts.items())))
    return 0


def cmd_merge(args):
    run = args.run
    require_run(run)
    ph = args.phase
    if ph == "lexicon":
        return lexmod.merge_lexicon(run)
    if ph in ("landscape", "probe", "snowball"):
        return merge_landscape(run, ph)
    if ph == "screen":
        return merge_screen(run)
    if ph == "mapping":
        return merge_mapping(run)
    if ph == "evidence":
        return merge_evidence(run, retry=getattr(args, "retry", False))
    if getattr(args, "retry", False):
        raise CliError("--retry applies only to --phase evidence")
    if ph == "coding":
        return merge_coding(run)
    if ph == "supply":
        return merge_supply(run)
    if ph == "redteam":
        return merge_redteam(run)
    raise CliError("unknown merge phase %s" % ph)
