"""URL normalisation and canonical entity keys.

Products are keyed by registrable domain (Public Suffix List rules: normal, wildcard and
exception rules), or by a platform-native id when they live inside a marketplace or code host.
Communities on generic hosts keep the full host because forums often sit on subdomains.
"""

import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING = re.compile(r"^(utm_[a-z]+|gclid|fbclid|msclkid|mc_cid|mc_eid|ref|ref_src|ref_url|source|_hsenc|_hsmi|igshid|yclid|si)$", re.I)


def normalize_url(url):
    """Lower-case scheme and host, drop default ports, fragments and tracking parameters,
    sort remaining query parameters and strip a trailing slash (except the root)."""
    url = (url or "").strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower().rstrip(".")
    port = parts.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = "%s:%d" % (host, port)
    path = parts.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _TRACKING.match(k)]
    query.sort()
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def host_of(url):
    return (urlsplit(normalize_url(url)).hostname or "").lower()


class PublicSuffix(object):
    def __init__(self, lines):
        self.normal, self.wild, self.exc = set(), set(), set()
        for line in lines:
            line = line.strip().split()[0] if line.strip() else ""
            if not line or line.startswith("//"):
                continue
            line = line.lower()
            if line.startswith("!"):
                self.exc.add(line[1:])
            elif line.startswith("*."):
                self.wild.add(line[2:])
            else:
                self.normal.add(line)

    @classmethod
    def load(cls, *paths):
        for p in paths:
            if p and os.path.exists(p):
                with open(p, "r", encoding="utf-8") as fh:
                    return cls(fh.readlines())
        return cls([])

    def public_suffix(self, host):
        labels = host.split(".")
        best = labels[-1:]
        for i in range(len(labels)):
            cand = ".".join(labels[i:])
            if cand in self.exc:
                best_exc = labels[i + 1:]
                return ".".join(best_exc)
            if cand in self.normal and len(labels[i:]) > len(best):
                best = labels[i:]
            if i > 0:
                parent = ".".join(labels[i:])
                if parent in self.wild and len(labels[i - 1:]) > len(best):
                    best = labels[i - 1:]
        return ".".join(best)

    def registrable(self, host):
        host = (host or "").lower().strip(".")
        if not host or re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
            return host
        suffix = self.public_suffix(host)
        if host == suffix:
            return host
        rest = host[: -len(suffix) - 1] if suffix else host
        label = rest.split(".")[-1]
        return label + "." + suffix if suffix else label


_PLATFORM = [
    (re.compile(r"^(?:www\.)?github\.com$"), re.compile(r"^/([^/]+)/([^/]+)"), lambda m: "gh:%s/%s" % (m.group(1).lower(), m.group(2).lower().replace(".git", ""))),
    (re.compile(r"^(?:[a-z]+\.)?wordpress\.org$"), re.compile(r"^/(?:support/)?plugins?/([^/]+)"), lambda m: "wp:%s" % m.group(1).lower()),
    (re.compile(r"^apps\.apple\.com$"), re.compile(r"/id(\d+)"), lambda m: "app:ios:%s" % m.group(1)),
    (re.compile(r"^(?:chromewebstore\.google\.com|chrome\.google\.com)$"), re.compile(r"/detail/(?:[^/]+/)?([a-p]{32})"), lambda m: "ext:chrome:%s" % m.group(1)),
    (re.compile(r"^addons\.mozilla\.org$"), re.compile(r"/addon/([^/?#]+)"), lambda m: "ext:firefox:%s" % m.group(1).lower()),
    (re.compile(r"^microsoftedge\.microsoft\.com$"), re.compile(r"/addons/detail/(?:[^/]+/)?([a-z]{32})"), lambda m: "ext:edge:%s" % m.group(1)),
    (re.compile(r"^marketplace\.atlassian\.com$"), re.compile(r"^/apps/(\d+)"), lambda m: "atl:%s" % m.group(1)),
    (re.compile(r"^apps\.shopify\.com$"), re.compile(r"^/([^/?#]+)"), lambda m: "shopify:%s" % m.group(1).lower()),
    (re.compile(r"^(?:www\.)?zapier\.com$"), re.compile(r"^/apps/([^/]+)"), lambda m: "zapier:%s" % m.group(1).lower()),
    (re.compile(r"^(?:[a-z0-9-]+\.)?slack\.com$"), re.compile(r"^/(?:apps|marketplace)/([A-Za-z0-9]+)"), lambda m: "slack:%s" % m.group(1)),
    (re.compile(r"^(?:www\.)?producthunt\.com$"), re.compile(r"^/(?:products|posts)/([^/?#]+)"), lambda m: "ph:%s" % m.group(1).lower()),
    (re.compile(r"^(?:www\.|old\.)?reddit\.com$"), re.compile(r"^/r/([^/]+)"), lambda m: "sub:%s" % m.group(1).lower()),
    (re.compile(r"^(?:www\.)?alternativeto\.net$"), re.compile(r"^/software/([^/]+)"), lambda m: "alt:%s" % m.group(1).lower()),
    (re.compile(r"^(?:www\.)?saashub\.com$"), re.compile(r"^/([^/?#]+)"), lambda m: "saashub:%s" % m.group(1).lower()),
]
_SE_TAG = re.compile(r"^/questions/tagged/([^/?#]+)")
_SE_HOST = re.compile(r"^(stackoverflow\.com|superuser\.com|serverfault\.com|askubuntu\.com|([a-z0-9-]+)\.stackexchange\.com)$")


def platform_key(url):
    nu = normalize_url(url)
    parts = urlsplit(nu)
    host = (parts.hostname or "").lower()
    path = parts.path
    if host == "play.google.com":
        q = dict(parse_qsl(parts.query))
        if path.startswith("/store/apps/details") and q.get("id"):
            return "app:android:%s" % q["id"].lower()
    m_host = _SE_HOST.match(host)
    if m_host:
        m = _SE_TAG.match(path)
        site = m_host.group(2) or m_host.group(1).split(".")[0]
        if m:
            return "se:%s:%s" % (site, m.group(1).lower())
    for host_re, path_re, fmt in _PLATFORM:
        if host_re.match(host):
            m = path_re.search(path)
            if m:
                return fmt(m)
    return None


# Redirect wrappers seen in search results: the real target sits in a query parameter.
_REDIRECTS = [
    (re.compile(r"^(?:www\.)?google\.[a-z.]+$"), re.compile(r"^/url$"), ("q", "url")),
    (re.compile(r"^(?:html\.|lite\.)?duckduckgo\.com$"), re.compile(r"^/l/?$"), ("uddg",)),
    (re.compile(r"^l\.facebook\.com$|^lm\.facebook\.com$"), re.compile(r"^/l\.php$"), ("u",)),
]
# Big shared hosts: many unrelated products live on them, so their registrable domain must never
# become a product key (a live run keyed Honeybadger as dom:google.com and Userback as dom:mozilla.org).
_SHARED = {"google.com", "apple.com", "mozilla.org", "microsoft.com", "amazon.com", "medium.com", "notion.site",
           "substack.com", "youtube.com", "linkedin.com", "x.com", "twitter.com", "facebook.com", "news.ycombinator.com"}


def unwrap_redirect(url):
    """Return the target of a known redirect wrapper URL, or the URL unchanged."""
    parts = urlsplit(normalize_url(url))
    host = (parts.hostname or "").lower()
    for host_re, path_re, params in _REDIRECTS:
        if host_re.match(host) and path_re.match(parts.path):
            q = dict(parse_qsl(parts.query))
            for k in params:
                if q.get(k, "").startswith(("http://", "https://")):
                    return q[k]
    return url


def entity_key(url, kind, psl):
    """Canonical key for an entity URL: platform id if any, else dom:/site: keys."""
    url = unwrap_redirect(url)
    pk = platform_key(url)
    if pk:
        return pk
    host = host_of(url)
    if kind == "community":
        h = host[4:] if host.startswith("www.") else host
        return "site:%s" % h
    reg = psl.registrable(host)
    if reg in _SHARED or host in _SHARED:
        # Keep the host plus the first path segment so different products on one platform stay apart.
        seg = (urlsplit(normalize_url(url)).path.strip("/").split("/") or [""])[0].lower()
        return "site:%s%s" % (host[4:] if host.startswith("www.") else host, ("/" + seg) if seg else "")
    return "dom:%s" % reg


class UnionFind(object):
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return ra
        keep, drop = sorted([ra, rb], key=_key_rank)
        self.parent[drop] = keep
        return keep


def _key_rank(key):
    """Prefer domain keys as the canonical id, then platform keys, then directory pointers."""
    order = {"dom": 0, "gh": 1, "wp": 1, "app": 1, "ext": 1, "atl": 1, "shopify": 1, "zapier": 1,
             "slack": 1, "site": 1, "sub": 1, "se": 1, "ph": 2, "alt": 3, "saashub": 3}
    return (order.get(key.split(":", 1)[0], 2), key)
