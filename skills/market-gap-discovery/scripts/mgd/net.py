"""Polite, auditable HTTP: excluded-source checks, robots.txt (RFC 9309), per-host rate limits,
Retry-After, raw snapshots with sha256, text extraction, and coverage-gap logging.

The contact string in the User-Agent comes only from the MGD_CONTACT environment variable,
which the human sets. Nothing else about the user is ever sent.
"""

import gzip
import html
import http.client
import socket
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from html.parser import HTMLParser

from mgcore import canon
from mgcore.jsonio import append_jsonl, now_iso, read_json, sha256_bytes, write_json

from .common import CliError, EXIT_BLOCKED, channels, p

try:
    import fcntl  # POSIX only; used to serialise per-host rate limiting across processes
except ImportError:  # pragma: no cover
    fcntl = None

MAX_BYTES = 6 * 1024 * 1024
AI_AGENT_TOKENS = ["ClaudeBot", "Claude-User", "anthropic-ai", "GPTBot", "ChatGPT-User", "CCBot"]


class Truncated(Exception):
    """A response ended early (connection cut or bad compression); worth one retry."""


TRANSIENT = (http.client.IncompleteRead, EOFError, ConnectionResetError, socket.timeout, Truncated)


class Blocked(CliError):
    def __init__(self, message, reason):
        CliError.__init__(self, message, EXIT_BLOCKED)
        self.reason = reason


def user_agent():
    contact = os.environ.get("MGD_CONTACT", "").strip()
    return "market-gap-discovery/1.0 (%s)" % contact if contact else "market-gap-discovery/1.0"


def excluded_reason(url, extra_domains=()):
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    reg = channels()
    for item in reg.get("excluded", []):
        d = item["domain"].lower()
        if host == d or host.endswith("." + d):
            return item["reason"]
    for d in extra_domains or []:
        d = d.lower()
        if host == d or host.endswith("." + d):
            return "excluded by the protocol (sources.excluded_extra)"
    path = parts.path + ("?" + parts.query if parts.query else "")
    for item in reg.get("excluded_paths", []):
        if host != item["domain"]:
            continue
        if "path_prefix" in item and path.startswith(item["path_prefix"]):
            return item["reason"]
        if "path_regex" in item and re.search(item["path_regex"], parts.path):
            return item["reason"]
    return None


def coverage_gap(run, source, url, reason, by=None):
    append_jsonl(p(run, "coverage-gaps.jsonl"), {"at": now_iso(), "source": source, "url": url, "reason": reason, "by": by})


class _Redirect(urllib.request.HTTPRedirectHandler):
    """Follow 308 Permanent Redirect like 307 (urllib before Python 3.11 refuses 308)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return urllib.request.HTTPRedirectHandler.redirect_request(self, req, fp, 307 if code == 308 else code, msg, headers, newurl)

    http_error_308 = urllib.request.HTTPRedirectHandler.http_error_302


_OPENER = urllib.request.build_opener(_Redirect)


def _read_all(fp, max_bytes):
    """Read until end of stream or max_bytes + 1. A single read(n) may return fewer bytes than
    available (a live run lost the second half of an 84 KB page that way)."""
    chunks, total = [], 0
    while total <= max_bytes:
        chunk = fp.read(min(65536, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def _raw_get(url, timeout=20, headers=None, max_bytes=None):
    max_bytes = max_bytes or MAX_BYTES
    req = urllib.request.Request(url, headers=dict({"User-Agent": user_agent(), "Accept-Encoding": "gzip, deflate"}, **(headers or {})))
    try:
        resp = _OPENER.open(req, timeout=timeout)
        status = resp.getcode()
        final = resp.geturl()
        ctype = resp.headers.get("Content-Type", "")
        enc = resp.headers.get("Content-Encoding", "")
        body = _read_all(resp, max_bytes)
        retry = resp.headers.get("Retry-After")
    except urllib.error.HTTPError as exc:
        status = exc.code
        final = url
        ctype = exc.headers.get("Content-Type", "") if exc.headers else ""
        enc = exc.headers.get("Content-Encoding", "") if exc.headers else ""
        body = _read_all(exc, max_bytes) if hasattr(exc, "read") else b""
        retry = exc.headers.get("Retry-After") if exc.headers else None
    if enc == "gzip" or body[:2] == b"\x1f\x8b":
        try:
            body = gzip.decompress(body)
        except (OSError, EOFError) as exc:
            raise Truncated("gzip body incomplete: %s" % exc)
    elif enc == "deflate":
        try:
            body = zlib.decompress(body)
        except zlib.error as exc:
            raise Truncated("deflate body incomplete: %s" % exc)
    return status, final, ctype, body[:max_bytes], retry


def probe(url):
    last = None
    for attempt in range(3):
        try:
            status, _f, _c, _b, _r = _raw_get(url, timeout=15)
            return status, "HTTP %d" % status
        except TRANSIENT as exc:
            last = exc
            time.sleep(1 + attempt)
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:  # DNS, TLS, proxy refusal
            return None, "unreachable: %s" % exc.__class__.__name__
    return None, "unreachable after retries: %s" % last.__class__.__name__


def download(url, path):
    try:
        status, _f, _c, body, _r = _raw_get(url, timeout=30)
        if status == 200 and body:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(body)
            return True
    except Exception:
        return False
    return False


def robots_allowed(run, url):
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc.lower()
    cache_path = p(run, "cache", "robots", re.sub(r"[^a-z0-9.-]", "_", host) + ".json")
    cached = read_json(cache_path)
    fresh = cached and (time.time() - cached.get("fetched_epoch", 0)) < 24 * 3600
    if not fresh:
        robots_url = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
        try:
            status, _f, _c, body, _r = _raw_get(robots_url, timeout=15)
            text = body.decode("utf-8", "replace")
        except Exception:
            status, text = 599, ""
        cached = {"fetched_epoch": time.time(), "status": status, "body": text[:200000]}
        write_json(cache_path, cached)
    status = cached["status"]
    if status is None or status >= 500:
        return False  # RFC 9309: unreachable robots.txt (5xx) means complete disallow
    if status in (401, 403):
        return False  # conservative: treat an access-denied robots.txt as disallow
    if 400 <= status < 500:
        return True  # RFC 9309: unavailable robots.txt (4xx) allows access
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(cached["body"].splitlines())
    # These fetches are made by an AI agent, so publishers' explicit opt-outs for AI agents apply too.
    agents = [user_agent(), "*"] + AI_AGENT_TOKENS
    return all(rp.can_fetch(a, url) for a in agents)


def _rate_limit(run, host, min_interval):
    lock_dir = p(run, "cache", "rate")
    os.makedirs(lock_dir, exist_ok=True)
    path = os.path.join(lock_dir, re.sub(r"[^a-z0-9.-]", "_", host))
    with open(path, "a+") as fh:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        raw = fh.read().strip()
        last = float(raw) if raw else 0.0
        wait = last + min_interval - time.time()
        if wait > 0:
            time.sleep(wait)
        fh.seek(0)
        fh.truncate()
        fh.write(str(time.time()))
        fh.flush()
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_UN)


def fetch_count(run):
    path = p(run, "cache", "fetch-count.jsonl")
    if not os.path.exists(path):
        return 0
    with open(path) as fh:
        return sum(1 for _ in fh)


def get(run, url, source="web", robots=True, min_interval=3.0, by=None, headers=None, budget=None, max_bytes=None):
    """Fetch url politely. Returns (status, final_url, content_type, body). Raises Blocked."""
    proto = read_json(p(run, "protocol.json"), {}) or {}
    reason = excluded_reason(url, (proto.get("sources") or {}).get("excluded_extra") or [])
    if reason:
        coverage_gap(run, source, url, "excluded source: " + reason, by)
        raise Blocked("refused: %s is an excluded source (%s)" % (url, reason), "excluded")
    if budget is not None and fetch_count(run) >= budget:
        raise CliError("fetch budget exhausted (%d); raise budget.fetches_max with `protocol amend`." % budget, 3)
    if robots and not robots_allowed(run, url):
        coverage_gap(run, source, url, "disallowed by robots.txt", by)
        raise Blocked("robots.txt disallows %s" % url, "robots")
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    for attempt in range(3):
        _rate_limit(run, host, min_interval)
        append_jsonl(p(run, "cache", "fetch-count.jsonl"), {"at": now_iso(), "url": url, "by": by})
        try:
            status, final, ctype, body, retry = _raw_get(url, headers=headers, max_bytes=max_bytes)
        except TRANSIENT as exc:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            coverage_gap(run, source, url, "network error after retries: %s" % exc.__class__.__name__, by)
            raise Blocked("network error fetching %s after retries: %s" % (url, exc), "network")
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
            # Only genuine network/protocol failures become coverage gaps; programming errors must surface.
            coverage_gap(run, source, url, "network error: %s" % exc.__class__.__name__, by)
            raise Blocked("network error fetching %s: %s" % (url, exc), "network")
        if status == 429 and attempt < 2 and retry and retry.isdigit() and int(retry) <= 60:
            time.sleep(int(retry))
            continue
        if status in (401, 403, 429):
            coverage_gap(run, source, url, "HTTP %d" % status, by)
            raise Blocked("HTTP %d for %s: stopping as required (no workarounds)" % (status, url), "http-%d" % status)
        if status == 202 and not (body or b"").strip():
            # Bot-protection services answer 202 with an empty body and a JavaScript challenge (seen live).
            coverage_gap(run, source, url, "HTTP 202 with empty body (bot challenge)", by)
            raise Blocked("HTTP 202 with an empty body for %s: a bot challenge; stopping as required" % url, "challenge")
        return status, final, ctype, body
    raise Blocked("rate-limited by %s" % host, "http-429")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "blockquote", "pre", "td", "th", "dd", "dt"}

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(markup):
    ex = _TextExtractor()
    try:
        ex.feed(markup)
        ex.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", markup)
    text = "".join(ex.parts)
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def _strings(node, acc):
    if isinstance(node, str):
        acc.append(html_to_text(html.unescape(node)) if "<" in node or "&" in node else node)
    elif isinstance(node, dict):
        for v in node.values():
            _strings(v, acc)
    elif isinstance(node, list):
        for v in node:
            _strings(v, acc)


def extract_text(body, content_type):
    text = body.decode("utf-8", "replace")
    ctype = (content_type or "").lower()
    stripped = text.lstrip()
    if "json" in ctype or stripped[:1] in ("{", "["):
        try:
            acc = []
            _strings(json.loads(text), acc)
            return "\n".join(acc)
        except ValueError:
            pass
    if "xml" in ctype or "rss" in ctype or stripped.startswith("<?xml"):
        text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", lambda m: m.group(1), text, flags=re.S)
        return html_to_text(html.unescape(html_to_text(text)))
    return html_to_text(text)


def save_snapshot(run, url, final_url, status, content_type, body, method, by=None, extra=None):
    sha = sha256_bytes(body)
    base = p(run, "snapshots", sha)
    if not os.path.exists(base + ".raw"):
        os.makedirs(p(run, "snapshots"), exist_ok=True)
        with open(base + ".raw", "wb") as fh:
            fh.write(body)
        with open(base + ".txt", "w", encoding="utf-8") as fh:
            fh.write(extract_text(body, content_type))
    meta = {"sha256": sha, "url": url, "final_url": final_url, "status": status, "content_type": content_type,
            "fetched_at": now_iso(), "method": method, "bytes": len(body), "by": by}
    if extra:
        meta.update(extra)
    write_json(base + ".meta.json", meta)
    append_jsonl(p(run, "cache", "snapshot-index.jsonl"), {"url": canon.normalize_url(url), "sha256": sha, "at": meta["fetched_at"], "status": status})
    return sha


def snapshot_for(run, url, max_age_hours=24):
    """Most recent snapshot sha for url if fetched within max_age_hours, else None."""
    path = p(run, "cache", "snapshot-index.jsonl")
    if not os.path.exists(path):
        return None
    key = canon.normalize_url(url)
    found = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("url") == key and rec.get("status") == 200:
                found = rec
    if not found:
        return None
    meta = read_json(p(run, "snapshots", found["sha256"] + ".meta.json"), {})
    try:
        import datetime as _dt
        at = _dt.datetime.fromisoformat(meta.get("fetched_at", found["at"]))
        age = (_dt.datetime.now(_dt.timezone.utc) - at).total_seconds() / 3600.0
        if age > max_age_hours:
            return None
    except Exception:
        return None
    return found["sha256"]


def snapshot_text(run, sha):
    path = p(run, "snapshots", sha + ".txt")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()
