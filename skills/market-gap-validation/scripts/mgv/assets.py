"""UTM links and honesty checks for validation assets (method card V07, references/ethics.md)."""

import os
import re
import urllib.parse

from mgcore import state
from mgcore.jsonio import now_iso, read_json, write_json

from .common import CliError, load_state, out, require, save_state, v

LANDING_TYPES = ("smoke-test", "fake-door", "presale", "loi")
SURVEY_TYPES = ("odi-survey", "kano-survey", "pricing-survey")
INTERVIEW_TYPES = ("problem-interviews", "switch-interviews")
SOCIAL_PROOF = [r"testimonial", r"\b(trusted|used|loved|chosen) by\b", r"as seen (on|in)\b", r"\bjoin (over |more than )?\d",
                r"\b\d(\.\d)?\s*/\s*5\b", "★★★", r"\bcustomer stories\b"]
PAYMENT = [r'autocomplete="cc-', r'name="card', r"\bcvc\b", r"\bcvv\b", r"checkout\.stripe", r"paypal\.com/", r"buy now"]


def required_assets(card):
    t = card["type"]
    req = []
    if t in LANDING_TYPES:
        req += ["landing.html", "privacy.md"]
        if card["channels"]:
            req.append("posts.md")
    if t in SURVEY_TYPES:
        req.append("survey.md")
    if t in INTERVIEW_TYPES:
        req.append("interview-guide.md")
    if t in ("tech-spike", "search-demand"):
        req.append("plan.md")
    return req


def check_assets(run, card):
    exp = card["id"]
    folder = v(run, "assets", exp)
    errs = []
    for f in required_assets(card):
        if not os.path.exists(os.path.join(folder, f)):
            errs.append("missing %s" % f)
    landing = os.path.join(folder, "landing.html")
    if os.path.exists(landing):
        with open(landing, encoding="utf-8") as fh:
            html = fh.read()
        low = html.lower()
        if 'id="disclosure"' not in low:
            errs.append('landing.html needs a disclosure block with id="disclosure" (the product is not built yet)')
        if 'id="consent"' not in low:
            errs.append('landing.html needs a consent checkbox with id="consent"')
        if not re.search(r'href="[^"]*privacy', low):
            errs.append("landing.html needs a link to the privacy notice")
        if 'data-experiment="%s"' % exp.lower() not in low:
            errs.append('landing.html needs data-experiment="%s"' % exp)
        if "{{" in html:
            errs.append("landing.html still contains template placeholders {{...}}")
        for pat in SOCIAL_PROOF:
            if re.search(pat, low):
                errs.append("landing.html contains social proof (%s): never fabricate testimonials, counts, logos or ratings" % pat)
        pays = [pat for pat in PAYMENT if re.search(pat, low)]
        if pays:
            if card["evidence_level"] not in ("presale", "deposit"):
                errs.append("landing.html takes payment details but the experiment's evidence level is %s" % card["evidence_level"])
            elif not re.search(r"you will be charged|authori[sz]e|refund", low):
                errs.append("a payment form needs explicit consent text (what is charged, when, and the refund policy)")
    return errs


def cmd_assets(args):
    run = args.run
    require(run)
    card = read_json(v(run, "prereg", "%s.json" % args.experiment_id))
    if not card:
        raise CliError("no Test Card %s" % args.experiment_id)
    errs = check_assets(run, card)
    write_json(v(run, "assets", card["id"], "assets-check.json"), {"checked_at": now_iso(), "ok": not errs, "errors": errs})
    st = load_state(run)
    st.setdefault("experiments", {}).setdefault(card["id"], {})["assets_ok"] = not errs
    state.touch(st, "assets_%s" % card["id"])
    save_state(run, st)
    if errs:
        out("%s assets need fixing:" % card["id"])
        for e in errs:
            out("  - " + e)
        return 1
    out("%s assets pass the honesty and completeness checks." % card["id"])
    return 0


def cmd_utm(args):
    run = args.run
    require(run)
    card = read_json(v(run, "prereg", "%s.json" % args.experiment))
    if not card:
        raise CliError("no Test Card %s" % args.experiment)
    if not re.match(r"^https?://", args.base_url or ""):
        raise CliError("--base-url must be an http(s) URL")
    links = {}
    for ch in [c.strip() for c in args.channels.split(",") if c.strip()]:
        parts = urllib.parse.urlsplit(args.base_url)
        q = urllib.parse.parse_qsl(parts.query) + [("utm_source", ch), ("utm_medium", card["type"]), ("utm_campaign", card["id"])]
        links[ch] = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path or "/", urllib.parse.urlencode(q), ""))
    write_json(v(run, "assets", card["id"], "utm.json"), {"base_url": args.base_url, "links": links, "created_at": now_iso()})
    out("UTM links for %s:" % card["id"])
    for ch, url in links.items():
        out("  %s: %s" % (ch, url))
    return 0
