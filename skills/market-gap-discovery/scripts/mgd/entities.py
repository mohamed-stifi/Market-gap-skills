"""`gapscan.py entities verify RUN`: confirm each included entity exists (HTTP 200 and its
name appears on the page) using script-made snapshots. Unverified entities never count."""

import json
import re

from mgcore import quotes, state
from mgcore.jsonio import read_jsonl, write_jsonl

from . import net
from .common import CliError, cfg, out, p, require_run, load_state, save_state


_SEPS = [":", " - ", " \u2013 ", " \u2014 ", "|", "\u30fb", "(", "\u25b8", " & ", " by "]
_WORDS = re.compile(r"[a-z0-9]+")


def _flat(text):
    return " " + " ".join(_WORDS.findall(quotes.normalize(text))) + " "


def _variants(name):
    """The name plus its core: without parentheses and before separators.
    A live run showed exact matching rejects real products ('Zap-Bill' vs 'Zap Bill', 'Harvest: Track Time & Invoice' vs 'Harvest')."""
    out = {name, re.sub(r"\(.*?\)", "", name)}
    for sep in _SEPS:
        if sep in name:
            out.add(name.split(sep)[0])
    return [v for v in out if len(_flat(v).strip()) >= 3]


def _name_found(names, text, entity_id):
    flat = _flat(text)
    for n in names:
        for v in _variants(n):
            fv = _flat(v).strip()
            if fv and (" " + fv + " ") in flat:
                return True
    if entity_id.startswith("dom:"):
        label = re.sub(r"[^a-z0-9]", "", entity_id[4:].split(".")[0].lower())
        # A brand word counts only when it is part of the site's own domain ('Square' on squareup.com).
        # A generic first word ('Invoice') alone would match almost any page in the niche.
        for n in names:
            for tok in _WORDS.findall(quotes.normalize(n)):
                if len(tok) >= 4 and tok in label and (" " + tok + " ") in flat:
                    return True
        if len(label) >= 4 and label in flat.replace(" ", ""):
            return True
    return False


def _verify_url(entity):
    eid = entity["entity_id"]
    m = re.match(r"^app:ios:(\d+)$", eid)
    if m:
        return "https://itunes.apple.com/lookup?id=%s" % m.group(1), False
    m = re.match(r"^wp:(.+)$", eid)
    if m:
        return "https://api.wordpress.org/plugins/info/1.2/?action=plugin_information&request[slug]=%s" % m.group(1), False
    urls = entity.get("urls") or []
    if eid.startswith("dom:"):
        dom = eid[4:]
        for u in urls:
            if dom in u:
                return u, True
    return (urls[0] if urls else None), True


def cmd_verify_entities(args):
    run = args.run
    require_run(run)
    ents = read_jsonl(p(run, "landscape", "entities.jsonl"))[0]
    if getattr(args, "recheck", False):
        # Re-evaluate earlier name misses from their existing snapshots (no new fetch).
        changed = {"ok": 0, "name_missing": 0}
        for e in ents:
            v = e.get("verified") or {}
            if e.get("status") == "included" and v.get("status") in ("ok", "name_missing") and v.get("snapshot"):
                ok = _name_found(e.get("names", []), net.snapshot_text(run, v["snapshot"]) or "", e["entity_id"])
                new_status = "ok" if ok else "name_missing"
                if new_status != v["status"]:
                    v["status"] = new_status
                    changed[new_status] += 1
        write_jsonl(p(run, "landscape", "entities.jsonl"), ents)
        st = load_state(run)
        state.touch(st, "entities_verify")
        save_state(run, st)
        out("Recheck from existing snapshots: %d now verified, %d no longer verified." % (changed["ok"], changed["name_missing"]))
        return 0
    todo = [e for e in ents if e.get("status") == "included" and not e.get("verified")]
    limit = args.limit or cfg(run).get("landscape.verify_batch")
    done = 0
    for e in todo[:limit]:
        url, robots = _verify_url(e)
        if not url:
            e["verified"] = {"status": "not_found", "detail": "no URL"}
            continue
        existing = net.snapshot_for(run, url)
        try:
            if existing:
                sha, status = existing, 200
            else:
                status, final, ctype, body = net.get(run, url, source="verify", robots=robots, min_interval=3.0, by="entities-verify")
                sha = net.save_snapshot(run, url, final, status, ctype, body, "verify", "entities-verify")
            if status != 200:
                e["verified"] = {"status": "not_found", "http_status": status, "snapshot": sha}
            else:
                text = net.snapshot_text(run, sha) or ""
                ok = _name_found(e.get("names", []), text, e["entity_id"])
                e["verified"] = {"status": "ok" if ok else "name_missing", "http_status": status, "snapshot": sha, "url": url}
        except net.Blocked as exc:
            e["verified"] = {"status": "blocked", "detail": exc.reason, "url": url}
        except CliError:
            raise
        except Exception as exc:  # unexpected parse problems: record, never crash the run
            e["verified"] = {"status": "error", "detail": exc.__class__.__name__, "url": url}
        done += 1
    write_jsonl(p(run, "landscape", "entities.jsonl"), ents)
    st = load_state(run)
    state.touch(st, "entities_verify")
    save_state(run, st)
    remaining = len(todo) - done
    counts = {}
    for e in ents:
        if e.get("verified"):
            counts[e["verified"]["status"]] = counts.get(e["verified"]["status"], 0) + 1
    out("Verified %d entities (%s); %d still pending%s." % (
        done, json.dumps(counts, sort_keys=True), remaining, " — run `entities verify` again" if remaining else ""))
    return 0
