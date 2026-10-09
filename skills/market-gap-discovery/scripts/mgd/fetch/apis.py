"""Tier-1 API adapters (see assets/channels.json for access terms and limits)."""

import calendar
import datetime as dt
import json
import os
import re
import shutil
import time
import subprocess
import urllib.parse

from mgcore import canon
from mgcore.jsonio import sha256_bytes, write_json

from .. import net
from ..common import CliError, EXIT_BLOCKED, p, validate
from ..privacy import author_hash

EXCERPT = 600


class Ctx(object):
    def __init__(self, run, args, fetch_budget):
        self.run = run
        self.args = args
        self.budget = fetch_budget
        self.by = args.by

    def get_json(self, url, source, min_interval=1.0, robots=False, headers=None, max_bytes=None, reuse_hours=0):
        if reuse_hours:
            sha = net.snapshot_for(self.run, url, reuse_hours)
            if sha and os.path.exists(p(self.run, "snapshots", sha + ".raw")):
                with open(p(self.run, "snapshots", sha + ".raw"), "rb") as fh:
                    try:
                        return json.loads(fh.read().decode("utf-8", "replace")), sha
                    except ValueError:
                        pass
        for attempt in range(2):
            status, final, ctype, body = net.get(self.run, url, source=source, robots=robots, min_interval=min_interval,
                                                 by=self.by, headers=headers, budget=self.budget, max_bytes=max_bytes)
            if status != 200:
                net.coverage_gap(self.run, source, url, "HTTP %d" % status, self.by)
                raise CliError("HTTP %d from %s" % (status, url), EXIT_BLOCKED)
            try:
                data = json.loads(body.decode("utf-8", "replace"))
            except ValueError:
                if attempt == 0:
                    time.sleep(2)  # transient: a truncated body is usually fine on the second try
                    continue
                net.coverage_gap(self.run, source, url, "non-JSON response twice (transient)", self.by)
                raise CliError("transient: non-JSON response from %s twice; skip this query and continue" % url, EXIT_BLOCKED)
            sha = net.save_snapshot(self.run, url, final, status, ctype, body, "api:" + source, self.by)
            return data, sha

    def get_text(self, url, source, min_interval=2.0, robots=True):
        status, final, ctype, body = net.get(self.run, url, source=source, robots=robots, min_interval=min_interval,
                                             by=self.by, budget=self.budget)
        if status != 200:
            net.coverage_gap(self.run, source, url, "HTTP %d" % status, self.by)
            raise CliError("HTTP %d from %s" % (status, url), EXIT_BLOCKED)
        sha = net.save_snapshot(self.run, url, final, status, ctype, body, "api:" + source, self.by)
        return body.decode("utf-8", "replace"), sha

    def save_combined(self, source, url, payload):
        body = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
        return net.save_snapshot(self.run, url, url, 200, "application/json", body, "api-aggregate:" + source, self.by)


def _clean(text):
    if not text:
        return ""
    return net.html_to_text(text) if ("<" in text or "&" in text) else text.strip()


def _excerpt(text):
    t = re.sub(r"\s+", " ", _clean(text)).strip()
    return t[:EXCERPT]


def _date(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return dt.datetime.utcfromtimestamp(value).date().isoformat()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(value))
    return m.group(1) if m else None


def _require(arg, name):
    if not arg:
        raise CliError("--%s is required for this source" % name)
    return arg


def _months(start, end):
    s = dt.date(int(start[:4]), int(start[5:7]), 1)
    e = dt.date(int(end[:4]), int(end[5:7]), 1)
    if e < s:
        raise CliError("--to must not be before --from")
    out = []
    cur = s
    while cur <= e:
        last = calendar.monthrange(cur.year, cur.month)[1]
        start_ts = calendar.timegm(cur.timetuple())
        nxt = dt.date(cur.year + (cur.month // 12), cur.month % 12 + 1, 1)
        out.append(("%04d-%02d" % (cur.year, cur.month), start_ts, calendar.timegm(nxt.timetuple()), cur, last))
        cur = nxt
    if len(out) > 60:
        raise CliError("at most 60 months per series")
    return out


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "term"


def _write_signal(ctx, source, term, kind, points, sha):
    sid = "SIG-%s-%s" % (source, _slug(term))
    doc = {"series_id": sid, "source": source, "term": term, "kind": kind, "points": points,
           "snapshot": sha, "retrieved_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"}
    errs = validate(doc, "signal")
    if errs:
        raise CliError("signal series invalid: " + "; ".join(errs[:3]))
    path = p(ctx.run, "evidence", "signals", sid + ".json")
    write_json(path, doc)
    return path


# ---------------------------------------------------------------- Hacker News (Algolia)
HN = "https://hn.algolia.com/api/v1/"


def hn(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    # Exact matching: Algolia's default typo tolerance inflates matches about 15x (verified live).
    params = {"query": q, "hitsPerPage": min(a.limit or 30, 100), "typoTolerance": "false"}
    tags = a.tags or "(story,comment)"
    params["tags"] = tags
    filters = []
    if a.since:
        ts = calendar.timegm(dt.datetime.strptime(a.since, "%Y-%m-%d").timetuple())
        filters.append("created_at_i>%d" % ts)
        params["numericFilters"] = ",".join(filters)
    url = HN + "search?" + urllib.parse.urlencode(params)
    data, sha = ctx.get_json(url, "hn", 1.0)
    items = []
    for h in data.get("hits", []):
        is_comment = bool(h.get("comment_text"))
        text = h.get("comment_text") or h.get("story_text") or ""
        items.append({
            "source": "hn", "id": h.get("objectID"),
            "url": "https://news.ycombinator.com/item?id=%s" % h.get("objectID"),
            "title": h.get("title") or h.get("story_title") or "(comment)",
            "text": _excerpt(text), "author_hash": author_hash(ctx.run, "hn", h.get("author")),
            "posted_at": _date(h.get("created_at")),
            "metrics": {"points": h.get("points"), "comments": h.get("num_comments")},
            "snapshot": sha, "kind_hint": "evidence" if is_comment or text else "product",
            "entity_url": h.get("url") if not is_comment else None, "listing_url": None})
    return {"query": q, "filters": {"tags": tags, "numeric": filters}, "total_hits": data.get("nbHits"),
            "items": items, "snapshot": sha}


def hn_counts(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    months = _months(_require(a.from_, "from"), _require(a.to, "to"))
    tags = a.tags or "(story,comment)"
    payload, points = [], []
    for label, s, e, _c, _l in months:
        nf = "created_at_i>=%d,created_at_i<%d" % (s, e)
        term_url = HN + "search?" + urllib.parse.urlencode({"query": q, "tags": tags, "numericFilters": nf, "hitsPerPage": 0,
                                                             "typoTolerance": "false"})
        base_url = HN + "search?" + urllib.parse.urlencode({"query": "", "tags": tags, "numericFilters": nf, "hitsPerPage": 0})
        r, _ = ctx.get_json(term_url, "hn", 1.0)
        d, _ = ctx.get_json(base_url, "hn", 1.0)
        payload.append({"period": label, "term": r.get("nbHits"), "total": d.get("nbHits"), "term_url": term_url, "total_url": base_url})
        points.append({"period": label, "d": int(d.get("nbHits") or 0), "r": int(r.get("nbHits") or 0)})
    sha = ctx.save_combined("hn-counts", HN + "search", {"query": q, "tags": tags, "months": payload})
    path = _write_signal(ctx, "hn", q, "proportion", points, sha)
    return {"query": q, "filters": {"tags": tags, "from": a.from_, "to": a.to}, "total_hits": sum(x["r"] for x in points),
            "items": [], "snapshot": sha, "signal_path": path}


def hn_hiring(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    months = a.months or 6
    url = HN + "search_by_date?" + urllib.parse.urlencode({"tags": "story,author_whoishiring", "hitsPerPage": months * 3})
    data, _sha = ctx.get_json(url, "hn", 1.0)
    stories = [h for h in data.get("hits", []) if "who is hiring" in (h.get("title") or "").lower()][:months]
    items, total = [], 0
    last_sha = None
    for s in stories:
        curl = HN + "search?" + urllib.parse.urlencode({"query": q, "tags": "comment,story_%s" % s["objectID"], "hitsPerPage": 50,
                                                         "typoTolerance": "false"})
        cdata, sha = ctx.get_json(curl, "hn", 1.0)
        last_sha = sha
        total += cdata.get("nbHits") or 0
        for h in cdata.get("hits", []):
            items.append({"source": "hn-hiring", "id": h.get("objectID"),
                          "url": "https://news.ycombinator.com/item?id=%s" % h.get("objectID"),
                          "title": s.get("title"), "text": _excerpt(h.get("comment_text")),
                          "author_hash": author_hash(ctx.run, "hn", h.get("author")),
                          "posted_at": _date(h.get("created_at")), "metrics": {}, "snapshot": sha,
                          "kind_hint": "evidence", "entity_url": None, "listing_url": None})
    return {"query": q, "filters": {"months": months, "stories": [s.get("objectID") for s in stories]},
            "total_hits": total, "items": items, "snapshot": last_sha}


# ---------------------------------------------------------------- Stack Exchange
SE = "https://api.stackexchange.com/2.3/"


def _se_params(extra):
    key = os.environ.get("STACKEXCHANGE_KEY")
    if key:
        extra["key"] = key
    return extra


def se(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    site = a.site or "stackoverflow"
    params = _se_params({"order": "desc", "sort": "relevance", "q": q, "site": site,
                         "pagesize": min(a.limit or 30, 100), "filter": "withbody"})
    url = SE + "search/advanced?" + urllib.parse.urlencode(params)
    data, sha = ctx.get_json(url, "se", 1.0)
    notes = []
    if data.get("backoff"):
        notes.append("API asked to back off %s s; wait before the next se call" % data["backoff"])
    if "quota_remaining" in data:
        notes.append("quota remaining: %s" % data["quota_remaining"])
    items = []
    for qd in data.get("items", []):
        owner = (qd.get("owner") or {}).get("display_name")
        items.append({"source": "se", "id": qd.get("question_id"), "url": qd.get("link"),
                      "title": _clean(qd.get("title")), "text": _excerpt(qd.get("body")),
                      "author_hash": author_hash(ctx.run, "se:" + site, owner),
                      "posted_at": _date(qd.get("creation_date")),
                      "metrics": {"score": qd.get("score"), "views": qd.get("view_count"), "answers": qd.get("answer_count")},
                      "snapshot": sha, "kind_hint": "evidence", "entity_url": None,
                      "listing_url": None, "tags": qd.get("tags")})
    return {"query": q, "filters": {"site": site}, "total_hits": data.get("total", len(items)), "items": items,
            "snapshot": sha, "notes": notes}


def se_counts(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    site = a.site or "stackoverflow"
    months = _months(_require(a.from_, "from"), _require(a.to, "to"))
    payload, points = [], []
    for label, s, e, _c, _l in months:
        turl = SE + "search/advanced?" + urllib.parse.urlencode(_se_params({"q": q, "site": site, "fromdate": s, "todate": e - 1, "filter": "total"}))
        burl = SE + "questions?" + urllib.parse.urlencode(_se_params({"site": site, "fromdate": s, "todate": e - 1, "filter": "total"}))
        r, _ = ctx.get_json(turl, "se", 1.0)
        d, _ = ctx.get_json(burl, "se", 1.0)
        payload.append({"period": label, "term": r.get("total"), "total": d.get("total")})
        points.append({"period": label, "d": int(d.get("total") or 0), "r": int(r.get("total") or 0)})
    sha = ctx.save_combined("se-counts", SE + "search/advanced", {"query": q, "site": site, "months": payload})
    path = _write_signal(ctx, "se", q + " " + site, "proportion", points, sha)
    return {"query": q, "filters": {"site": site, "from": a.from_, "to": a.to}, "total_hits": sum(x["r"] for x in points),
            "items": [], "snapshot": sha, "signal_path": path}


# ---------------------------------------------------------------- GitHub via gh
def _gh(ctx, argv, source):
    gh = shutil.which("gh")
    if not gh:
        net.coverage_gap(ctx.run, source, "gh", "gh CLI not installed", ctx.by)
        raise CliError("gh CLI is not installed; see the human task from `doctor`.", EXIT_BLOCKED)
    if ctx.budget is not None and net.fetch_count(ctx.run) >= ctx.budget:
        raise CliError("fetch budget exhausted", 3)
    net._rate_limit(ctx.run, "api.github.com", 2.0)
    proc = subprocess.run([gh] + argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if proc.returncode != 0:
        net.coverage_gap(ctx.run, source, "gh " + " ".join(argv[:3]), proc.stderr.decode("utf-8", "replace")[:200], ctx.by)
        raise CliError("gh failed: %s" % proc.stderr.decode("utf-8", "replace")[:300], EXIT_BLOCKED)
    body = proc.stdout
    sha = net.save_snapshot(ctx.run, "gh:" + " ".join(argv), "gh:" + " ".join(argv), 200, "application/json", body, "gh-cli", ctx.by)
    return json.loads(body.decode("utf-8", "replace") or "[]"), sha


def gh_issues(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    data, sha = _gh(ctx, ["search", "issues", q, "--limit", str(min(a.limit or 30, 100)), "--json",
                          "title,url,body,author,createdAt,commentsCount,repository,state"], "gh")
    items = []
    for it in data:
        repo = (it.get("repository") or {}).get("nameWithOwner")
        items.append({"source": "gh-issues", "id": it.get("url"), "url": it.get("url"), "title": it.get("title"),
                      "text": _excerpt(it.get("body")), "author_hash": author_hash(ctx.run, "github", (it.get("author") or {}).get("login")),
                      "posted_at": _date(it.get("createdAt")), "metrics": {"comments": it.get("commentsCount"), "state": it.get("state")},
                      "snapshot": sha, "kind_hint": "evidence",
                      "entity_url": "https://github.com/%s" % repo if repo else None, "listing_url": None})
    return {"query": q, "filters": {}, "total_hits": len(items), "items": items, "snapshot": sha,
            "notes": ["gh search returns at most --limit results; total_hits is the number returned"]}


def gh_repos(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    data, sha = _gh(ctx, ["search", "repos", q, "--limit", str(min(a.limit or 30, 100)), "--json",
                          "fullName,url,description,stargazersCount,updatedAt,homepage,isArchived"], "gh")
    items = []
    for it in data:
        items.append({"source": "gh-repos", "id": it.get("fullName"), "url": it.get("url"), "title": it.get("fullName"),
                      "text": _excerpt(it.get("description")), "author_hash": None, "posted_at": _date(it.get("updatedAt")),
                      "metrics": {"stars": it.get("stargazersCount"), "archived": it.get("isArchived")},
                      "snapshot": sha, "kind_hint": "product", "entity_url": it.get("homepage") or it.get("url"),
                      "listing_url": it.get("url")})
    return {"query": q, "filters": {}, "total_hits": len(items), "items": items, "snapshot": sha}


# ---------------------------------------------------------------- Wikimedia pageviews
def wiki_views(ctx):
    a = ctx.args
    if not os.environ.get("MGD_CONTACT"):
        net.coverage_gap(ctx.run, "wiki", "wikimedia.org", "MGD_CONTACT not set (Wikimedia requires a contact User-Agent)", ctx.by)
        raise CliError("Wikimedia requires a contact User-Agent: the human must set MGD_CONTACT (see `hq list`).", EXIT_BLOCKED)
    article = _require(a.article, "article").replace(" ", "_")
    months = _months(_require(a.from_, "from"), _require(a.to, "to"))
    start = "%s0100" % months[0][0].replace("-", "")
    end_label = months[-1]
    end = "%04d%02d%02d00" % (end_label[3].year, end_label[3].month, end_label[4])
    project = a.project or "en.wikipedia"
    url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/%s/all-access/user/%s/monthly/%s/%s" % (
        project, urllib.parse.quote(article, safe=""), start, end)
    data, sha = ctx.get_json(url, "wiki", 1.0)
    points = []
    for it in data.get("items", []):
        ts = it.get("timestamp", "")
        points.append({"period": "%s-%s" % (ts[:4], ts[4:6]), "value": it.get("views", 0)})
    path = _write_signal(ctx, "wiki", article, "absolute", points, sha)
    return {"query": article, "filters": {"project": project}, "total_hits": sum(x["value"] for x in points),
            "items": [], "snapshot": sha, "signal_path": path}


# ---------------------------------------------------------------- WordPress.org
WP = "https://api.wordpress.org/plugins/info/1.2/"


def wp_search(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    url = WP + "?" + urllib.parse.urlencode({"action": "query_plugins", "request[search]": q,
                                              "request[per_page]": min(a.limit or 30, 100)})
    data, sha = ctx.get_json(url, "wp", 2.0)
    items = []
    for pl in data.get("plugins", []):
        slug = pl.get("slug")
        items.append({"source": "wp", "id": slug, "url": "https://wordpress.org/plugins/%s/" % slug,
                      "title": _clean(pl.get("name")), "text": _excerpt(pl.get("short_description")),
                      "author_hash": None, "posted_at": _date(pl.get("last_updated")),
                      "metrics": {"rating": pl.get("rating"), "num_ratings": pl.get("num_ratings"),
                                  "active_installs": pl.get("active_installs")},
                      "snapshot": sha, "kind_hint": "product", "entity_url": pl.get("homepage") or None,
                      "listing_url": "https://wordpress.org/plugins/%s/" % slug})
    return {"query": q, "filters": {}, "total_hits": (data.get("info") or {}).get("results"), "items": items, "snapshot": sha}


def wp_plugin(ctx):
    slug = _require(ctx.args.slug, "slug")
    url = WP + "?" + urllib.parse.urlencode({"action": "plugin_information", "request[slug]": slug})
    data, sha = ctx.get_json(url, "wp", 2.0)
    if data.get("error"):
        raise CliError("WordPress.org: %s" % data["error"])
    item = {"source": "wp", "id": slug, "url": "https://wordpress.org/plugins/%s/" % slug, "title": _clean(data.get("name")),
            "text": _excerpt((data.get("sections") or {}).get("description")), "author_hash": None,
            "posted_at": _date(data.get("last_updated")),
            "metrics": {"rating": data.get("rating"), "num_ratings": data.get("num_ratings"),
                        "ratings_1to5": data.get("ratings"), "active_installs": data.get("active_installs"),
                        "support_threads": data.get("support_threads"),
                        "support_threads_resolved": data.get("support_threads_resolved")},
            "snapshot": sha, "kind_hint": "product", "entity_url": data.get("homepage") or None,
            "listing_url": "https://wordpress.org/plugins/%s/" % slug}
    return {"query": slug, "filters": {}, "total_hits": 1, "items": [item], "snapshot": sha}


def _rss_items(text):
    return re.findall(r"<item>(.*?)</item>", text, flags=re.S)


def _tag(block, name):
    m = re.search(r"<%s[^>]*>(.*?)</%s>" % (re.escape(name), re.escape(name)), block, flags=re.S)
    if not m:
        return None
    val = re.sub(r"<!\[CDATA\[(.*?)\]\]>", lambda x: x.group(1), m.group(1), flags=re.S)
    return val.strip()


def wp_reviews(ctx):
    slug = _require(ctx.args.slug, "slug")
    url = "https://wordpress.org/support/plugin/%s/reviews/feed/" % urllib.parse.quote(slug)
    text, sha = ctx.get_text(url, "wp", 2.0, robots=True)
    items = []
    for block in _rss_items(text):
        link = _tag(block, "link")
        pub = _tag(block, "pubDate")
        try:
            posted = dt.datetime.strptime(pub[:25].strip(), "%a, %d %b %Y %H:%M:%S").date().isoformat() if pub else None
        except ValueError:
            posted = None
        items.append({"source": "wp-reviews", "id": link, "url": link or url, "title": _clean(_tag(block, "title")),
                      "text": _excerpt(_tag(block, "description")),
                      "author_hash": author_hash(ctx.run, "wordpress.org", _tag(block, "dc:creator")),
                      "posted_at": posted, "metrics": {}, "snapshot": sha, "kind_hint": "evidence",
                      "entity_url": None, "listing_url": "https://wordpress.org/plugins/%s/" % slug})
    return {"query": slug, "filters": {}, "total_hits": len(items), "items": items, "snapshot": sha}


# ---------------------------------------------------------------- Apple
def apple_search(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    cc = a.country or "us"
    url = "https://itunes.apple.com/search?" + urllib.parse.urlencode({"term": q, "entity": "software", "country": cc,
                                                                       "limit": min(a.limit or 30, 200)})
    data, sha = ctx.get_json(url, "apple", 3.0)
    items = []
    for r in data.get("results", []):
        items.append({"source": "apple", "id": r.get("trackId"), "url": r.get("trackViewUrl"), "title": r.get("trackName"),
                      "text": _excerpt(r.get("description")), "author_hash": None, "posted_at": _date(r.get("currentVersionReleaseDate")),
                      "metrics": {"rating": r.get("averageUserRating"), "ratings": r.get("userRatingCount"),
                                  "price": r.get("formattedPrice"), "seller": r.get("sellerName")},
                      "snapshot": sha, "kind_hint": "product", "entity_url": r.get("sellerUrl") or r.get("trackViewUrl"),
                      "listing_url": r.get("trackViewUrl")})
    return {"query": q, "filters": {"country": cc}, "total_hits": data.get("resultCount"), "items": items, "snapshot": sha}


def apple_reviews(ctx):
    a = ctx.args
    app_id = _require(a.id, "id")
    cc = a.country or "us"
    pages = max(1, min(a.pages or 2, 10))
    items, last_sha = [], None
    for page in range(1, pages + 1):
        url = "https://itunes.apple.com/%s/rss/customerreviews/page=%d/id=%s/sortby=mostrecent/json" % (cc, page, app_id)
        data, sha = ctx.get_json(url, "apple", 3.0, robots=True)
        last_sha = sha
        entries = (data.get("feed") or {}).get("entry") or []
        if isinstance(entries, dict):
            entries = [entries]
        for e in entries:
            if "im:rating" not in e:
                continue
            items.append({"source": "apple-reviews", "id": (e.get("id") or {}).get("label"), "url": url,
                          "title": (e.get("title") or {}).get("label"), "text": _excerpt((e.get("content") or {}).get("label")),
                          "author_hash": author_hash(ctx.run, "apple", ((e.get("author") or {}).get("name") or {}).get("label")),
                          "posted_at": _date((e.get("updated") or {}).get("label")),
                          "metrics": {"rating": (e.get("im:rating") or {}).get("label")}, "snapshot": sha,
                          "kind_hint": "evidence", "entity_url": None,
                          "listing_url": "https://apps.apple.com/app/id%s" % app_id})
        if not entries:
            break
    warning = None
    if not items:
        # Seen live: the same app returned 50 reviews, then an empty feed an hour later, on every URL variant.
        warning = ("Apple returned an empty review feed. The feed is intermittent, so this is missing data, "
                   "never evidence of zero complaints; it is logged as a coverage gap.")
        net.coverage_gap(ctx.run, "apple-reviews", "https://itunes.apple.com/%s/rss/customerreviews/id=%s" % (cc, app_id),
                         "empty review feed (intermittent: missing data, not zero reviews)", ctx.by)
    return {"query": app_id, "filters": {"country": cc, "pages": pages}, "total_hits": len(items), "items": items,
            "snapshot": last_sha, "warning": warning}


# ---------------------------------------------------------------- Atlassian Marketplace
ATL = "https://marketplace.atlassian.com/rest/2/"


def atl_search(ctx):
    a = ctx.args
    q = _require(a.query, "query")
    url = ATL + "addons?" + urllib.parse.urlencode({"text": q, "limit": min(a.limit or 30, 50)})
    data, sha = ctx.get_json(url, "atl", 2.0)
    items = []
    for ad in (data.get("_embedded") or {}).get("addons", []):
        emb = ad.get("_embedded") or {}
        link = ((ad.get("_links") or {}).get("alternate") or {}).get("href")
        if link and link.startswith("/"):
            link = "https://marketplace.atlassian.com" + link
        items.append({"source": "atl", "id": ad.get("key"), "url": link, "title": ad.get("name"),
                      "text": _excerpt(ad.get("summary") or ad.get("tagLine")), "author_hash": None, "posted_at": None,
                      "metrics": {"installs": (emb.get("distribution") or {}).get("totalInstalls"),
                                  "stars": (emb.get("reviews") or {}).get("averageStars"),
                                  "reviews": (emb.get("reviews") or {}).get("count"), "key": ad.get("key")},
                      "snapshot": sha, "kind_hint": "product", "entity_url": link, "listing_url": link})
    return {"query": q, "filters": {}, "total_hits": data.get("count"), "items": items, "snapshot": sha}


def atl_reviews(ctx):
    key = _require(ctx.args.key, "key")
    url = ATL + "addons/%s/reviews?" % urllib.parse.quote(key) + urllib.parse.urlencode({"limit": min(ctx.args.limit or 50, 50)})
    data, sha = ctx.get_json(url, "atl", 2.0)
    items = []
    for rv in (data.get("_embedded") or {}).get("reviews", []):
        author = ((rv.get("_embedded") or {}).get("author") or {}).get("name")
        items.append({"source": "atl-reviews", "id": rv.get("id") or rv.get("date"), "url": url,
                      "title": "%s stars" % rv.get("stars"), "text": _excerpt(rv.get("review")),
                      "author_hash": author_hash(ctx.run, "atlassian", author), "posted_at": _date(rv.get("date")),
                      "metrics": {"stars": rv.get("stars"), "helpful": rv.get("totalVotes")}, "snapshot": sha,
                      "kind_hint": "evidence", "entity_url": None, "listing_url": None})
    return {"query": key, "filters": {}, "total_hits": data.get("count", len(items)), "items": items, "snapshot": sha}


# ---------------------------------------------------------------- YC directory mirror
YC = "https://yc-oss.github.io/api/"


_YC_STOP = {"for", "per", "the", "and", "with", "from", "best", "tool", "tools", "app", "apps", "software", "alternative",
            "how", "your", "that", "this", "into", "free", "online"}


def _yc_terms(q):
    """Whole-word, stop-word-free, plural-normalised query terms (substring matching put 'per' inside
    'personal-finance' and similar in a live run)."""
    out_ = []
    for t in re.split(r"[^a-z0-9]+", q.lower()):
        if len(t) < 4 or t in _YC_STOP:
            continue
        if t.endswith("ies") and len(t) > 4:
            t = t[:-3] + "y"
        elif t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        out_.append(t)
    return sorted(set(out_))


def _yc_words(text):
    return set(_yc_terms(text.replace("-", " ")))


def yc(ctx):
    """Search the yc-oss mirror: match query terms against tag and industry names in meta.json,
    fetch only those small files, and fall back to the full companies file when nothing matches."""
    a = ctx.args
    q = _require(a.query, "query")
    terms = _yc_terms(q)
    meta, _ = ctx.get_json(YC + "meta.json", "yc", 1.0, reuse_hours=24)
    if not terms:
        raise CliError("the query has no usable terms after removing stop-words")
    groups = []
    for kind in ("tags", "industries"):
        for key, info in (meta.get(kind) or {}).items():
            if _yc_words(key) & set(terms):
                groups.append(info["api"])
    groups = sorted(set(groups))[:8]
    sources = groups or [YC + "companies/all.json"]
    need = max(1, (len(terms) + 1) // 2)
    seen, scored, last_sha = set(), [], None
    for url in sources:
        # The full companies file is ~2 MB gzip and >6 MB decoded: allow it, and reuse it for 24 h within the run.
        data, sha = ctx.get_json(url, "yc", 1.0, max_bytes=64 * 1024 * 1024, reuse_hours=24)
        last_sha = sha
        for c in data if isinstance(data, list) else []:
            if c.get("slug") in seen:
                continue
            hay = _yc_words(" ".join(str(c.get(k) or "") for k in ("name", "one_liner", "long_description", "tags", "industries", "industry")))
            score = len(set(terms) & hay)
            if score >= need:
                seen.add(c.get("slug"))
                scored.append((score, c, sha))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("name"))))
    items = []
    for score, c, sha in scored:
        items.append({"source": "yc", "id": c.get("slug"), "url": c.get("website") or c.get("url"),
                      "title": c.get("name"), "text": _excerpt(c.get("one_liner")), "author_hash": None,
                      "posted_at": None, "metrics": {"batch": c.get("batch"), "status": c.get("status"),
                                                     "team_size": c.get("team_size"), "terms_matched": score},
                      "snapshot": sha, "kind_hint": "product", "entity_url": c.get("website"),
                      "listing_url": c.get("url")})
    limit = a.limit or 50
    return {"query": q, "filters": {"groups": groups or ["companies/all"]}, "total_hits": len(items),
            "items": items[:limit], "snapshot": last_sha,
            "notes": ["matched tag/industry files: %s" % (", ".join(g.rsplit("/", 2)[-2] + "/" + g.rsplit("/", 1)[-1] for g in groups) or "none (searched all companies)")]}
