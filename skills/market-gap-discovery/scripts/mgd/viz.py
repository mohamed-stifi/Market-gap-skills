"""`gapscan.py viz RUN`: charts, an offline HTML dashboard and a one-page plain-language summary.

Reads a finished (or partly finished) run folder and writes output/dashboard/NN-slug.png,
output/dashboard/index.html (one self-contained file: images inlined as data URIs, inline CSS, no
scripts, light and dark), output/dashboard/manifest.json and output/summary.md. Every number shown is
read or counted from the run's files; a chart whose inputs are missing is skipped with a reason.
matplotlib is imported lazily so the core gapscan commands stay standard-library only.
"""

import base64
import csv
import datetime as dt
import glob
import html
import io
import math
import os
import random
import re
import statistics
import textwrap
import warnings

from mgcore import config, richness
from mgcore.jsonio import now_iso, read_json, read_jsonl, write_json

from .common import ASSETS, CliError, cfg, out, p

DPI = 150
WIDTH = 10.5  # inches: 1575 px, readable when scaled to a laptop-width column

# Reference palette (dataviz skill, references/palette.md): categorical slots 1-4, status steps,
# a blue ordinal ramp and chart chrome. Dark mode is its own selected set, not an inversion.
LIGHT = {
    "name": "light", "surface": "#fcfcfb", "page": "#f9f9f7", "ink": "#0b0b0b", "ink2": "#52514e",
    "muted": "#898781", "grid": "#e1e0d9", "axis": "#c3c2b7", "wash": "#f0efec", "gray": "#a8a69f",
    "s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100",
    "good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b",
    "ramp": ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"], "tint": 0.16,
}
DARK = {
    "name": "dark", "surface": "#1a1a19", "page": "#0d0d0d", "ink": "#ffffff", "ink2": "#c3c2b7",
    "muted": "#898781", "grid": "#2c2c2a", "axis": "#383835", "wash": "#383835", "gray": "#6b6a65",
    "s1": "#3987e5", "s2": "#d95926", "s3": "#199e70", "s4": "#c98500",
    "good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b",
    "ramp": ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"], "tint": 0.30,
}

DEMAND = ("pain", "wish", "workaround", "switch", "wtp")
STANCES = [("pain", "Pain"), ("wish", "Wish"), ("workaround", "Workaround"), ("switch", "Switched tools"),
           ("wtp", "Will pay or paid"), ("praise", "Praise"), ("contra", "Contra")]
STRENGTHS = [("S0", "opinion"), ("S1", "generic\ncomplaint"), ("S2", "specific\nevent"), ("S3", "costly\nworkaround"),
             ("S4", "money\nspent")]
PRICE_GROUPS = [("freemium", "Free tier + paid plans"), ("paid", "Paid only"), ("free", "Free or open source"),
                ("other", "Bundled or unknown")]
PRICE_GROUP_OF = {"freemium": "freemium", "subscription": "paid", "one-time": "paid", "usage-based": "paid",
                  "transaction-fee": "paid", "quote-based": "paid", "free": "free", "open-source": "free"}
SAT_VERDICT = {
    "SATURATED": ("Saturated", "the search found nearly everything it is likely to find"),
    "STOP_UNSATURATED": ("Stopped before saturation", "more products probably exist than were found"),
    "EXPAND": ("Not saturated yet", "more search rounds were still due"),
    "NEEDS_PROBE": ("Probe pending", "the estimates passed but a holdout probe was still due"),
}
CARD_STATUS = {"survives": ("Survives", "good"), "weakened": ("Weakened", "warning"), "killed": ("Killed", "critical"),
               "insufficient": ("Too little evidence", "gray"), "candidate": ("Candidate", "s1")}
PHASES = {
    "lexicon": "Search vocabulary", "press": "Query review", "landscape": "Landscape scouts", "screen": "Screening",
    "snowball": "Snowball search", "probe": "Holdout probe", "mapping": "Attribute mapping", "evidence": "Evidence mining",
    "coding-open": "Open coding", "coding-closed": "Closed coding", "coding-reliability": "Second coder",
    "supply": "Supply mapping", "synthesis": "Gap synthesis", "redteam": "Red team", "sizing": "Sizing",
    "writer": "Report writing",
}
SECTIONS = [("The answer", ["08", "09", "04"]), ("The market", ["03", "10", "11"]),
            ("The evidence", ["05", "06", "07"]), ("How thorough was the search", ["01", "02", "12"])]
# Deep runs also show the options every lens generated (chart 13, D26) next to the gap cards.
DEEP_SECTIONS = [("The answer", ["08", "09", "13", "04"])] + SECTIONS[1:]


class _Skip(Exception):
    """A chart cannot be drawn from the run's files; the message says why."""


def _need(cond, reason):
    if not cond:
        raise _Skip(reason)


# ---------------------------------------------------------------- run access
class _Run(object):
    """Cached, forgiving reads of a run folder: a missing or unreadable file reads as empty."""

    def __init__(self, run):
        self.run = run
        self._memo = {}
        try:
            self.c = cfg(run)
        except ValueError:
            self.c = config.Config(os.path.join(ASSETS, "defaults.json"), {})

    def _get(self, key, fn):
        if key not in self._memo:
            try:
                self._memo[key] = fn()
            except (ValueError, OSError, UnicodeDecodeError):
                self._memo[key] = None
        return self._memo[key]

    def json(self, *parts):
        return self._get(("json",) + parts, lambda: read_json(p(self.run, *parts)))

    def jsonl(self, *parts):
        return self._get(("jsonl",) + parts, lambda: read_jsonl(p(self.run, *parts))[0]) or []

    def csv(self, *parts):
        def load():
            path = p(self.run, *parts)
            if not os.path.exists(path):
                return []
            with open(path, newline="", encoding="utf-8") as fh:
                return list(csv.DictReader(fh))
        return self._get(("csv",) + parts, load) or []

    def files(self, *parts):
        return sorted(glob.glob(p(self.run, *parts)))

    @property
    def protocol(self):
        doc = self.json("protocol.json")
        return doc if isinstance(doc, dict) else {}

    def default(self, key):
        node = self.c.defaults
        for part in key.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return node.get("value") if isinstance(node, dict) else None

    def entities(self):
        return {e["entity_id"]: e for e in self.jsonl("landscape", "entities.jsonl") if e.get("entity_id")}

    def verified(self):
        return [r for r in self.jsonl("evidence", "ledger.jsonl") if (r.get("verification") or {}).get("status") == "verified"]

    def category_labels(self):
        cls = self.json("landscape", "classification.json") or {}
        facets = cls.get("facets") if isinstance(cls, dict) else None
        return {x["id"]: x.get("label") or x["id"] for x in (facets or {}).get("category", []) if isinstance(x, dict) and x.get("id")}

    def codebook(self):
        lock = self.json("coding", "codebook.lock.json")
        book = None
        if isinstance(lock, dict) and lock.get("version") is not None:
            book = self.json("coding", "codebook.v%s.json" % lock["version"])
        if not book:
            versions = []
            for f in self.files("coding", "codebook.v*.json"):
                mo = re.search(r"codebook\.v(\d+)\.json$", f)
                if mo:
                    versions.append(int(mo.group(1)))
            if versions:
                book = self.json("coding", "codebook.v%d.json" % max(versions))
        if not book:
            book = self.json("coding", "codebook.json")
        return {x["id"]: x for x in (book or {}).get("codes", []) if isinstance(x, dict) and x.get("id")}

    def cards(self):
        return [c for c in self.jsonl("gaps", "cards.jsonl") if c.get("gap_id")]

    def redteam(self):
        res = {}
        for f in self.files("gaps", "redteam", "GAP-*.json"):
            doc = self.json("gaps", "redteam", os.path.basename(f))
            if isinstance(doc, dict) and doc.get("gap_id"):
                res[doc["gap_id"]] = doc
        return res


# ---------------------------------------------------------------- formatting
def _int(x):
    return "{:,}".format(int(round(float(x))))


_DOLLAR = "$"  # escaped by build() on matplotlib versions without text.parse_math


def _money(x, sign=None):
    x = float(x)
    if abs(x) >= 1e6:
        s = "%.1fM" % (x / 1e6)
    elif abs(x) >= 1e5:
        s = "%.0fk" % (x / 1e3)
    elif abs(x) >= 1e3:
        s = "%.1fk" % (x / 1e3)
    elif x == int(x) or abs(x) >= 10:
        s = "%.0f" % x
    else:
        s = "%.2f" % x
    return (_DOLLAR if sign is None else sign) + s.replace(".0k", "k").replace(".0M", "M")


def _money_full(x, sign=None):
    return (_DOLLAR if sign is None else sign) + "{:,.0f}".format(float(x))


def _pct(x, digits=0):
    return ("%." + str(digits) + "f%%") % (100.0 * x)


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _clip(text, n):
    text = " ".join(str(text or "").split())
    if len(text) <= n:
        return text
    return text[:n - 1].rsplit(" ", 1)[0].rstrip(",;:(") + "…"


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", " ".join(str(text or "").split())) if s.strip()]


def _wrap(text, width_in, fs):
    chars = max(20, int((width_in - 0.5) * 72.0 / (fs * 0.5)))
    lines = []
    for para in str(text).split("\n"):
        lines += textwrap.wrap(para, chars) or [""]
    return lines


def _plural(n, word, plural=None):
    return "%s %s" % (_int(n), word if n == 1 else (plural or word + "s"))


# ---------------------------------------------------------------- figure frame
class _Frame(object):
    """A figure with a title, a one-sentence reading guide, an optional callout and a source footer.
    `body` is the height in inches left for the plot itself, so long notes never squeeze the data."""

    def __init__(self, m, T, title, subtitle, sources, body=4.0, notes=None, callout=None, w=WIDTH):
        self.T, self.title, self.subtitle, self.sources = T, title, subtitle, list(sources)
        sub = _wrap(subtitle, w, 10.5)
        call = _wrap(callout, w, 10.5) if callout else []
        foot = []
        for note in ["Source: " + ", ".join(self.sources)] + [n for n in (notes or []) if n]:
            foot += _wrap(note, w, 8.2)
        head_h = 0.22 + 0.36 + 0.205 * len(sub) + (0.04 + 0.205 * len(call) if call else 0) + 0.1
        foot_h = 0.14 + 0.165 * len(foot) + 0.05
        h = head_h + body + foot_h
        self.fig = fig = m.Figure(figsize=(w, h), dpi=DPI, facecolor=T["surface"])
        m.FigureCanvasAgg(fig)
        pad, y = 0.24, h - 0.22
        fig.text(pad / w, y / h, title, ha="left", va="top", fontsize=15, fontweight="bold", color=T["ink"])
        y -= 0.36
        for line in sub:
            fig.text(pad / w, y / h, line, ha="left", va="top", fontsize=10.5, color=T["ink2"])
            y -= 0.205
        if call:
            y -= 0.04
            for line in call:
                fig.text(pad / w, y / h, line, ha="left", va="top", fontsize=10.5, fontweight="bold", color=T["ink"])
                y -= 0.205
        yb = 0.14
        for line in reversed(foot):
            fig.text(pad / w, yb / h, line, ha="left", va="bottom", fontsize=8.2, color=T["muted"])
            yb += 0.165
        self.rect = [0.0, foot_h / h, 1.0, (h - head_h) / h]
        self.pads = {}
        self.done = False

    def layout(self):
        # tight_layout ignores gridspecs with their own hspace/wspace, so spacing goes through pads.
        if self.done:
            return
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.fig.tight_layout(rect=self.rect, pad=0.7, **self.pads)
        self.done = True

    def png(self):
        self.layout()
        buf = io.BytesIO()
        self.fig.savefig(buf, format="png", dpi=DPI, facecolor=self.T["surface"])
        return buf.getvalue()


def _style(ax, T, grid="x", fs=9.5):
    ax.set_facecolor(T["surface"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(T["axis"])
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=T["axis"], labelcolor=T["ink2"], labelsize=fs, length=0, pad=5)
    if grid:
        ax.grid(axis=grid, color=T["grid"], linewidth=0.8, linestyle="-")
        ax.set_axisbelow(True)
    else:
        ax.grid(False)


def _bare_x(ax):
    ax.spines["bottom"].set_visible(False)
    ax.set_xticks([])


def _panel_title(ax, T, text, sub=None, legend=False):
    """Panel heading; leaves room for a one-line note (sub) and/or a legend row under it."""
    gap = 26 if legend else 0
    ax.set_title(text, loc="left", fontsize=11, fontweight="bold", color=T["ink"], pad=8 + gap + (16 if sub else 0))
    if sub:
        ax.annotate(sub, (0, 1), xycoords="axes fraction", xytext=(0, 4 + gap), textcoords="offset points", ha="left",
                    va="bottom", fontsize=9, color=T["ink2"])


def _legend(ax, T, handles, ncol=4, loc="lower left", anchor=(0.0, 1.0)):
    leg = ax.legend(handles=handles, ncol=ncol, loc=loc, bbox_to_anchor=anchor, frameon=False, fontsize=9.5,
                    handlelength=1.0, handleheight=1.0, columnspacing=1.4, borderaxespad=0.3)
    for t in leg.get_texts():
        t.set_color(T["ink2"])
    return leg


def _ramp(T, n):
    r = T["ramp"]
    if n <= 1:
        return [r[2]]
    return [r[int(round(i * (len(r) - 1) / float(n - 1)))] for i in range(n)]


def _tip(ax, T, x, y, text, dx=5, fs=9.5, color=None, weight="normal", ha="left"):
    ax.annotate(text, (x, y), xytext=(dx if ha == "left" else -dx, 0), textcoords="offset points", ha=ha, va="center",
                fontsize=fs, color=color or T["ink"], fontweight=weight, annotation_clip=False)


def _overlap(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _inside(px, py, b):
    return b[0] <= px <= b[2] and b[1] <= py <= b[3]


def _place_labels(fig, ax, items, T, fs=8.6):
    """Label every point without overlaps (greedy, in display pixels): try 16 directions around each
    marker, nearest ring first; a label placed away from its marker gets a thin leader line, and
    leaders may not cut through other labels or markers. items: dicts with x, y, r_px, text."""
    rend = fig.canvas.get_renderer()
    axbb = ax.get_window_extent(rend)
    px2pt = 72.0 / fig.dpi
    boxes = []
    for it in items:
        it["cx"], it["cy"] = ax.transData.transform((it["x"], it["y"]))
        r = it["r_px"]
        it["own"] = (it["cx"] - r, it["cy"] - r, it["cx"] + r, it["cy"] + r)
        boxes.append(it["own"])
    for it in items:  # crowded points choose first; isolated ones always find room
        it["crowd"] = sum(1 for o in items if o is not it and math.hypot(o["cx"] - it["cx"], o["cy"] - it["cy"]) < 70)
    probe = ax.text(0, 0, "", fontsize=fs)
    dirs = [(math.cos(a), math.sin(a)) for a in [math.radians(d) for d in
                                                (0, 180, 90, 270, 45, 135, 315, 225, 22.5, 157.5, 337.5, 202.5, 67.5, 112.5, 292.5, 247.5)]]
    segs = []
    for it in sorted(items, key=lambda i: (-i["crowd"], -i.get("priority", 0))):
        probe.set_text(it["text"])
        bb = probe.get_window_extent(rend)
        w, h = bb.width, bb.height
        best, found = None, False
        for k, gap in enumerate((3, 12, 24, 38, 55, 75, 100)):
            for cx_, sy_ in dirs:
                d = it["r_px"] + gap
                ux, uy = cx_ * d, sy_ * d
                ha = "left" if cx_ > 0.3 else ("right" if cx_ < -0.3 else "center")
                va = "bottom" if sy_ > 0.3 else ("top" if sy_ < -0.3 else "center")
                ax_, ay_ = it["cx"] + ux, it["cy"] + uy
                x0 = ax_ if ha == "left" else (ax_ - w if ha == "right" else ax_ - w / 2.0)
                y0 = ay_ if va == "bottom" else (ay_ - h if va == "top" else ay_ - h / 2.0)
                box = (x0 - 6, y0 - 2, x0 + w + 6, y0 + h + 2)
                cost = sum(_overlap(box, b) for b in boxes)
                cost += 400.0 * sum(1 for (px, py) in segs if _inside(px, py, box))
                if k >= 2:
                    for t in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
                        px, py = it["cx"] + ux * t, it["cy"] + uy * t
                        cost += 400.0 * sum(1 for b in boxes if b is not it["own"] and _inside(px, py, b))
                if box[0] < axbb.x0 or box[2] > axbb.x1 or box[1] < axbb.y0 or box[3] > axbb.y1:
                    cost += 1e7
                if cost == 0:
                    best, found = (0, ux, uy, ha, va, box, k), True
                    break
                if best is None or cost + k * 60.0 < best[0]:
                    best = (cost + k * 60.0, ux, uy, ha, va, box, k)
            if found:
                break
        _, ux, uy, ha, va, box, k = best
        kw = {}
        if k >= 2:
            kw["arrowprops"] = dict(arrowstyle="-", color=T["muted"], lw=0.7, shrinkA=1, shrinkB=it["r_px"] * px2pt + 1)
            segs += [(it["cx"] + ux * t, it["cy"] + uy * t) for t in (0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85)]
        ax.annotate(it["text"], (it["x"], it["y"]), xytext=(ux * px2pt, uy * px2pt), textcoords="offset points", ha=ha, va=va,
                    fontsize=fs, color=it.get("color") or T["ink"], zorder=5, annotation_clip=False, **kw)
        boxes.append(box)
    probe.remove()


def _patch(m, color, label):
    return m.patches.Patch(facecolor=color, edgecolor="none", label=label)


# ---------------------------------------------------------------- 01 funnel
def chart_funnel(R, T, m):
    pr = R.json("output", "prisma.json")
    _need(isinstance(pr, dict), "output/prisma.json is missing (run `gapscan.py prisma RUN`)")
    L, E, G = pr.get("landscape") or {}, pr.get("evidence") or {}, pr.get("gaps") or {}
    groups = []
    if L.get("unique_entities"):
        excl = sum((L.get("excluded_by_reason") or {}).values())
        failed = (L.get("included") or 0) - (L.get("included_verified") or 0)
        groups.append(("Products and sites (landscape search)", [
            ("Records found by searches", L.get("records_identified"), None),
            ("Unique products and sites", L.get("unique_entities"), "%s merged" % _plural(L.get("duplicates_removed") or 0, "duplicate")),
            ("Screened against the protocol", L.get("screened"), None),
            ("Included", L.get("included"), "%s excluded, %s unsure" % (_int(excl), _int(L.get("unsure") or 0))),
            ("Included and confirmed live", L.get("included_verified"), ("%s failed the live check" % _int(failed)) if failed else None)]))
    if E.get("submitted") or E.get("in_ledger"):
        groups.append(("Evidence quotes", [
            ("Quotes submitted by miners", E.get("submitted"), None),
            ("Kept in the evidence ledger", E.get("in_ledger"), "%s rejected, %s" % (
                _int(max(E.get("rejected_at_merge") or 0, 0)), _plural(E.get("duplicates") or 0, "duplicate"))),
            ("Quote found on the saved page", (E.get("verification") or {}).get("verified"), None)]))
    if G.get("cards_proposed"):
        bs, n = G.get("by_status") or {}, G["cards_proposed"]
        ins, kil, gated = bs.get("insufficient", 0), bs.get("killed", 0), G.get("gated_out") or 0
        groups.append(("Gap ideas", [
            ("Gap cards written", n, None),
            ("Passed the evidence thresholds", n - ins, ("%d with too little evidence" % ins) if ins else None),
            ("Not killed by the red team", n - ins - kil, ("%d killed" % kil) if kil else None),
            ("Ranked", G.get("ranked"), ("%d gated out" % gated) if gated > 0 else None)]))
    groups = [(name, [s for s in st if s[1] is not None]) for name, st in groups]
    groups = [g for g in groups if g[1]]
    _need(groups, "output/prisma.json has no counts yet")
    nbars = sum(len(g[1]) for g in groups)
    notes, sources = [], ["output/prisma.json"]
    audit = R.json("landscape", "screening-audit.json")
    if isinstance(audit, dict) and _num(audit.get("alpha")) is not None:
        sources.append("landscape/screening-audit.json")
        notes.append("Screening double-check: two screeners agreed with alpha %.2f (%s) on %s." % (
            audit["alpha"], audit.get("status", "?"), _plural(audit.get("units") or 0, "entity", "entities")))
    F = _Frame(m, T, "From search results to gap ideas",
               "Read each block top to bottom: every bar is one step of the pipeline, the number is what was left after it, "
               "and the grey note says what that step removed.",
               sources, body=0.3 + 0.36 * nbars + 0.5 * len(groups), notes=notes)
    gs = F.fig.add_gridspec(len(groups), 1, height_ratios=[len(g[1]) + 0.6 for g in groups])
    F.pads = {"h_pad": 1.6}
    rows = []
    for gi, (name, stages) in enumerate(groups):
        ax = F.fig.add_subplot(gs[gi])
        _style(ax, T, grid=None)
        _bare_x(ax)
        ax.spines["left"].set_visible(False)
        vals = [s[1] for s in stages]
        ys = list(range(len(stages)))
        ax.barh(ys, vals, height=0.56, color=_ramp(T, len(stages)), edgecolor=T["surface"], linewidth=1.5)
        ax.set_yticks(ys)
        ax.set_yticklabels([s[0] for s in stages], fontsize=10, color=T["ink"])
        ax.set_ylim(len(stages) - 0.5, -0.6)
        ax.set_xlim(0, (max(vals) or 1) * 1.7)
        for y, (label, v, note) in enumerate(stages):
            num = _int(v)
            _tip(ax, T, v, y, num, fs=10.5, weight="bold")
            if note:
                _tip(ax, T, v, y, note, dx=12 + 6.6 * len(num), fs=9.2, color=T["muted"])
            rows.append([name, label, _int(v), note or ""])
        _panel_title(ax, T, name)
    return {"frame": F, "table": (["Block", "Step", "Count", "Removed at this step"], rows)}


# ---------------------------------------------------------------- 02 saturation
def _reconstruct_history(R, sat):
    """Per-round Chao2 rebuilt from units.json and the final entity list. Used only when
    saturation.json has no history and only if its last round reproduces the recorded estimate."""
    units = R.json("landscape", "units.json")
    if not isinstance(units, dict):
        return None
    su = {u: mm for u, mm in units.items() if isinstance(mm, dict) and mm.get("mode") in ("landscape", "probe")}
    ents = [e for e in R.entities().values() if e.get("status") == "included" and (e.get("verified") or {}).get("status") == "ok"]
    rounds = sorted(set(mm.get("round") for mm in su.values() if isinstance(mm.get("round"), int)))
    if not su or not ents or not rounds:
        return None
    hist, first = [], {}
    for e in ents:
        rs = [su[u]["round"] for u in e.get("found_in_units") or [] if u in su and isinstance(su[u].get("round"), int)]
        if rs:
            first[e["entity_id"]] = min(rs)
    for r in rounds:
        us = set(u for u, mm in su.items() if isinstance(mm.get("round"), int) and mm["round"] <= r)
        inc = {}
        for e in ents:
            hit = set(u for u in e.get("found_in_units") or [] if u in us)
            if hit:
                inc[e["entity_id"]] = hit
        if not inc:
            continue
        s = richness.summarize_incidence(inc, z=R.c.get("landscape.z") or 1.96)
        before = sum(1 for v in first.values() if v < r)
        new = sum(1 for v in first.values() if v == r)
        ch = s.get("chao2") or {}
        hist.append({"round": r, "T": len(us), "S_obs": s["S_obs"], "chao2": ch.get("estimate"), "ci_low": ch.get("ci_low"),
                     "ci_high": ch.get("ci_high"), "coverage": s.get("coverage"), "completeness": s.get("completeness"),
                     "marginal_yield": (new / float(before)) if before else None})
    ov = sat.get("overall") or {}
    est = (ov.get("chao2") or {}).get("estimate")
    if not hist or hist[-1]["S_obs"] != ov.get("S_obs") or est is None or hist[-1]["chao2"] is None \
            or abs(hist[-1]["chao2"] - est) > 1e-6 * max(1.0, abs(est)):
        return None
    hist[-1]["T"] = ov.get("T", hist[-1]["T"])
    return hist


def _sat_history(R, sat):
    hist = [h for h in sat.get("history") or [] if isinstance(h, dict) and h.get("S_obs") is not None]
    if hist:
        return sorted(hist, key=lambda h: h.get("round") or 0), "history"
    try:
        rec = _reconstruct_history(R, sat)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        rec = None
    if rec:
        return rec, "reconstructed"
    ov = sat.get("overall") or {}
    if ov.get("S_obs") is None:
        return [], None
    ch = ov.get("chao2") or {}
    return [{"round": sat.get("round") or 1, "T": ov.get("T"), "S_obs": ov["S_obs"], "chao2": ch.get("estimate"),
             "ci_low": ch.get("ci_low"), "ci_high": ch.get("ci_high"), "coverage": ov.get("coverage"),
             "completeness": ov.get("completeness"), "marginal_yield": sat.get("marginal_yield")}], "final"


def chart_saturation(R, T, m):
    sat = R.json("landscape", "saturation.json")
    _need(isinstance(sat, dict) and sat.get("overall"), "landscape/saturation.json is missing (run `gapscan.py saturation RUN`)")
    hist, how = _sat_history(R, sat)
    _need(hist, "landscape/saturation.json has no estimates")
    verdict = sat.get("verdict") or hist[-1].get("verdict") or ""
    plain = SAT_VERDICT.get(verdict, (verdict, ""))
    why = "; ".join(sat.get("reasons") or [])
    callout = "Verdict: %s (%s)%s" % (plain[0].lower(), verdict, (". Why: " + why) if why else ".") if verdict else None
    notes = []
    sources = ["landscape/saturation.json"]
    if how == "reconstructed":
        sources += ["landscape/units.json", "landscape/entities.jsonl"]
        notes.append("Earlier rounds are reconstructed from units.json and the final screening decisions (saturation.json "
                     "keeps no history); the last round reproduces saturation.json exactly.")
    elif how == "final":
        notes.append("Only the latest round is recorded, so the trend over rounds is not shown.")
    if sat.get("note"):
        notes.append(sat["note"])
    F = _Frame(m, T, "Did the landscape search find (nearly) everything?",
               "Left: products found by the sampled search and the statistical estimate of how many exist (shaded = 95% range). "
               "Right: how complete the search looks; the search may stop once both lines clear the target.",
               sources, body=4.0, notes=notes, callout=callout)
    gs = F.fig.add_gridspec(1, 2, width_ratios=[1.12, 1])
    F.pads = {"w_pad": 3.0}
    ax, ax2 = F.fig.add_subplot(gs[0]), F.fig.add_subplot(gs[1])
    for a in (ax, ax2):
        _style(a, T, grid="y")
    xs = [h.get("round") for h in hist]
    S = [h.get("S_obs") for h in hist]
    C = [_num(h.get("chao2")) for h in hist]
    lo = [_num(h.get("ci_low")) for h in hist]
    hi = [_num(h.get("ci_high")) for h in hist]
    last = hist[-1]
    ymax = 1.3 * max([v for v in (_num(last.get("ci_high")), _num(last.get("chao2"))) if v] + S)
    clip = lambda v: min(v, ymax) if v is not None else None  # noqa: E731
    if len(hist) > 1:
        ok = [i for i in range(len(xs)) if lo[i] is not None and hi[i] is not None]
        ax.fill_between([xs[i] for i in ok], [clip(lo[i]) for i in ok], [clip(hi[i]) for i in ok], color=T["s2"], alpha=0.14, lw=0)
        okc = [i for i in range(len(xs)) if C[i] is not None]
        ax.plot([xs[i] for i in okc], [clip(C[i]) for i in okc], color=T["s2"], lw=2, marker="o", markersize=6,
                markeredgecolor=T["surface"], markeredgewidth=1.5, label="Estimated total (Chao2)")
        ax.plot(xs, S, color=T["s1"], lw=2, marker="o", markersize=6, markeredgecolor=T["surface"], markeredgewidth=1.5,
                label="Found by the search")
    else:
        if lo[0] is not None and hi[0] is not None:
            ax.vlines(xs, [clip(lo[0])], [clip(hi[0])], color=T["s2"], lw=6, alpha=0.25)
        ax.plot(xs, [clip(C[0])], "o", color=T["s2"], markersize=9, markeredgecolor=T["surface"], label="Estimated total (Chao2)")
        ax.plot(xs, S, "o", color=T["s1"], markersize=9, markeredgecolor=T["surface"], label="Found by the search")
    for i, x in enumerate(xs):
        for v in (hi[i], C[i]):
            if v is not None and v > ymax:
                ax.annotate("range continues to %s ↑" % _int(v), (x, ymax), xytext=(8, -2), textcoords="offset points", ha="left",
                            va="top", fontsize=8.5, color=T["ink2"])
                break
    ax.set_ylim(0, ymax)
    ax.set_xlim(min(xs) - 0.4, max(xs) + (1.5 if len(xs) > 1 else 1.2))
    ax.set_xticks(xs)
    ax.set_xticklabels(["Round %s" % x for x in xs])
    ax.yaxis.set_major_formatter(m.ticker.FuncFormatter(lambda v, _: _int(v)))
    ya, yb = S[-1], C[-1]
    if yb is not None and abs(clip(yb) - ya) < 0.09 * ymax:
        yb = ya + 0.09 * ymax
    _tip(ax, T, xs[-1], ya, "Found: %s" % _int(S[-1]), dx=9, fs=9.5, weight="bold")
    if C[-1] is not None:
        rng = (" (%s–%s)" % (_int(lo[-1]), _int(hi[-1]))) if lo[-1] is not None and hi[-1] is not None else ""
        _tip(ax, T, xs[-1], clip(yb), "Estimated: %s%s" % (_int(C[-1]), rng), dx=9, fs=9.5)
    _legend(ax, T, ax.get_legend_handles_labels()[0][::-1], ncol=2)
    _panel_title(ax, T, "Products found vs estimated to exist", legend=True)
    cov = [_num(h.get("coverage")) for h in hist]
    comp = [_num(h.get("completeness")) for h in hist]
    style = dict(lw=2, marker="o", markersize=6, markeredgecolor=T["surface"], markeredgewidth=1.5)
    ends = []
    for vals, color, label in ((cov, T["s3"], "Coverage"), (comp, T["s4"], "Completeness")):
        pts = [(x, v) for x, v in zip(xs, vals) if v is not None]
        if pts:
            ax2.plot([a for a, _ in pts], [b for _, b in pts], color=color, label=label, **style)
            ends.append([pts[-1][0], pts[-1][1], "%s %s" % (label, _pct(pts[-1][1]))])
    if len(ends) == 2 and abs(ends[0][1] - ends[1][1]) < 0.07:
        hi_i = 0 if ends[0][1] >= ends[1][1] else 1
        ends[hi_i][1] = ends[1 - hi_i][1] + 0.07
    for x, y, txt in ends:
        _tip(ax2, T, x, y, txt, dx=9, fs=9.5, weight="bold")
    targets = {}
    for key, name in (("landscape.coverage_target", "coverage"), ("landscape.completeness_target_theta", "completeness")):
        cur, dflt = _num(R.c.get(key)), _num(R.default(key))
        if cur is not None:
            targets.setdefault(round(cur, 4), []).append(("target", name))
        if dflt is not None and cur is not None and abs(dflt - cur) > 1e-9:
            targets.setdefault(round(dflt, 4), []).append(("original target", name))
    lowered = any(kind == "original target" for v in targets.values() for kind, _ in v)
    xr = max(xs) + (1.7 if len(xs) > 1 else 1.4)
    tvals = sorted(targets)
    for i, v in enumerate(tvals):
        what = targets[v]
        kinds = sorted(set(k for k, _ in what))
        names = " and ".join(sorted(set(n for _, n in what)))
        if kinds == ["original target"]:
            txt = "Original %s target %s" % (names, _pct(v))
        elif lowered:
            txt = "Target now %s (amended)" % _pct(v)
        else:
            txt = "%s target %s" % (names.capitalize(), _pct(v))
        below = i + 1 < len(tvals) and tvals[i + 1] - v < 0.08
        ax2.axhline(v, color=T["ink2"], lw=1, zorder=1)
        ax2.annotate(txt, (xr, v), xytext=(-2, -3 if below else 3), textcoords="offset points", ha="right",
                     va="top" if below else "bottom", fontsize=8.6, color=T["ink2"])
    ax2.set_ylim(0, 1.08)
    ax2.set_xlim(min(xs) - 0.4, xr)
    ax2.set_xticks(xs)
    ax2.set_xticklabels(["Round %s" % x for x in xs])
    ax2.yaxis.set_major_formatter(m.ticker.PercentFormatter(xmax=1.0, decimals=0))
    _legend(ax2, T, ax2.get_legend_handles_labels()[0], ncol=2)
    _panel_title(ax2, T, "How complete the search looks", legend=True)
    rows = [[h.get("round"), h.get("T"), h.get("S_obs"), _int(h["chao2"]) if _num(h.get("chao2")) is not None else "",
             ("%s–%s" % (_int(h["ci_low"]), _int(h["ci_high"]))) if _num(h.get("ci_low")) is not None and _num(h.get("ci_high")) is not None else "",
             _pct(h["coverage"]) if _num(h.get("coverage")) is not None else "",
             _pct(h["completeness"]) if _num(h.get("completeness")) is not None else "",
             ("%.3f" % h["marginal_yield"]) if _num(h.get("marginal_yield")) is not None else ""] for h in hist]
    return {"frame": F, "table": (["Round", "Sampling units", "Found", "Estimated", "95% range", "Coverage", "Completeness",
                                   "New finds vs before"], rows)}


# ---------------------------------------------------------------- 03 crowding
def chart_crowding(R, T, m):
    attrs = [a for a in R.jsonl("landscape", "entity-attributes.jsonl") if a.get("entity_id")]
    _need(attrs, "landscape/entity-attributes.jsonl is missing or empty (run the mapping phase)")
    ents = R.entities()
    if ents:
        ok = set(k for k, e in ents.items() if e.get("status") == "included" and (e.get("verified") or {}).get("status") == "ok"
                 and e.get("kind", "product") == "product")
        attrs = [a for a in attrs if a["entity_id"] in ok]
    _need(attrs, "no included and verified product has mapped attributes")
    labels = R.category_labels()
    by = {}
    for a in attrs:
        cat = a.get("category") or "other"
        g = PRICE_GROUP_OF.get((a.get("pricing") or {}).get("model"), "other")
        by.setdefault(cat, {})
        by[cat][g] = by[cat].get(g, 0) + 1
    cats = sorted(by, key=lambda c: (-sum(by[c].values()), labels.get(c, c)))
    top, rest = cats[:20], cats[20:]
    used = [(g, lab) for g, lab in PRICE_GROUPS if any(by[c].get(g) for c in top)]
    colors = {"freemium": T["s1"], "paid": T["s2"], "free": T["s3"], "other": T["gray"]}
    notes = []
    if rest:
        notes.append("Not shown: %s with %s." % (_plural(len(rest), "smaller category", "smaller categories"),
                                                 _plural(sum(sum(by[c].values()) for c in rest), "product")))
    F = _Frame(m, T, "Where competitors crowd",
               "Each bar counts the verified products in one category; longer bars mean a more crowded market. "
               "Colours split each category by how products charge.",
               ["landscape/entity-attributes.jsonl", "landscape/entities.jsonl", "landscape/classification.json"],
               body=max(2.0, 0.7 + 0.3 * len(top)), notes=notes)
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid=None)
    _bare_x(ax)
    ax.spines["left"].set_visible(False)
    ys = list(range(len(top)))
    left = [0] * len(top)
    handles = []
    for g, lab in used:
        vals = [by[c].get(g, 0) for c in top]
        ax.barh(ys, vals, left=left, height=0.6, color=colors[g], edgecolor=T["surface"], linewidth=1.5)
        left = [a + b for a, b in zip(left, vals)]
        handles.append(_patch(m, colors[g], lab))
    for y, tot in zip(ys, left):
        _tip(ax, T, tot, y, _int(tot), fs=9.5, weight="bold")
    ax.set_yticks(ys)
    ax.set_yticklabels([labels.get(c, c) for c in top], fontsize=9.8, color=T["ink"])
    ax.set_ylim(len(top) - 0.5, -0.7)
    ax.set_xlim(0, max(left) * 1.1)
    _legend(ax, T, handles, ncol=len(handles))
    rows = [[labels.get(c, c), sum(by[c].values())] + [by[c].get(g, 0) for g, _ in PRICE_GROUPS] for c in cats]
    return {"frame": F, "table": (["Category", "Products"] + [lab for _, lab in PRICE_GROUPS], rows)}


# ---------------------------------------------------------------- 04 gap map
def chart_gapmap(R, T, m):
    gm = R.json("analysis", "gapmap.json")
    jobs = [j for j in (gm or {}).get("jobs", []) if _num(j.get("supply")) is not None and _num(j.get("demand_weighted")) is not None]
    _need(jobs, "analysis/gapmap.json is missing or maps no jobs (run `gapscan.py gapmap RUN`)")
    cells = [("absolute", "Absolute gap: demand, almost no products", T["s2"]),
             ("synthesis", "Synthesis gap: people stitch several tools together", T["s1"]),
             ("none", "No gap type flagged", T["gray"])]
    color = {k: c for k, _, c in cells}
    sx = statistics.median([float(j["supply"]) for j in jobs])
    sy = statistics.median([float(j["demand_weighted"]) for j in jobs])
    counts = {}
    for j in jobs:
        counts[j.get("cell") or "none"] = counts.get(j.get("cell") or "none", 0) + 1
    recs = [int(j.get("demand_records") or 0) for j in jobs]
    F = _Frame(m, T, "Demand vs supply: where the gaps are",
               "Each bubble is one job people are trying to get done. Higher = more people asking (weighted by how strong their "
               "evidence is); further right = more products already serving it; bigger = more verified quotes. "
               "The shaded corner (above-median demand, below-median supply) is where gaps live.",
               ["analysis/gapmap.json"], body=5.6,
               notes=["Bubble size: %s to %s verified quotes. Medians: supply %s products, demand %.2f. Both axes use a square-root "
                      "scale so the crowded low end stays readable." % (
                          _int(min(recs)), _int(max(recs)), _int(sx) if sx == int(sx) else "%.1f" % sx, sy)])
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid="both")
    np = m.np
    fwd = lambda v: np.sign(v) * np.sqrt(np.abs(v))  # noqa: E731
    inv = lambda v: np.sign(v) * np.square(v)  # noqa: E731
    ax.set_xscale("function", functions=(fwd, inv))
    ax.set_yscale("function", functions=(fwd, inv))
    xmax = max(float(j["supply"]) for j in jobs)
    ymax = max(float(j["demand_weighted"]) for j in jobs)
    xlim, ylim = (-0.006 * xmax - 0.05, xmax * 1.12 + 0.5), (-0.004 * ymax - 0.02, ymax * 1.3 + 0.2)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    nice = [0, 1, 2, 5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500, 1000]
    ax.set_xticks([t for t in nice if t <= xlim[1]])
    ax.set_yticks([t for t in nice if t <= ylim[1]])
    ax.xaxis.set_major_formatter(m.ticker.FuncFormatter(lambda v, _: _int(v)))
    ax.yaxis.set_major_formatter(m.ticker.FuncFormatter(lambda v, _: _int(v)))
    ax.xaxis.set_minor_locator(m.ticker.NullLocator())
    ax.yaxis.set_minor_locator(m.ticker.NullLocator())
    ax.add_patch(m.patches.Rectangle((xlim[0], sy), sx - xlim[0], ylim[1] - sy, facecolor=T["s2"], alpha=0.07, lw=0, zorder=0))
    ax.annotate("Where gaps live: more demand, fewer products", (xlim[0], ylim[1]), xytext=(8, -8), textcoords="offset points",
                ha="left", va="top", fontsize=9.5, color=T["ink2"], fontweight="bold")
    sizes = [36 + 15 * r for r in recs]
    order = sorted(range(len(jobs)), key=lambda i: -sizes[i])
    for k, _, _ in cells:
        idx = [i for i in order if (jobs[i].get("cell") or "none") == k]
        if idx:
            ax.scatter([float(jobs[i]["supply"]) for i in idx], [float(jobs[i]["demand_weighted"]) for i in idx],
                       s=[sizes[i] for i in idx], color=color[k], edgecolors=T["surface"], linewidths=1.5, zorder=3, alpha=0.95)
    ax.set_xlabel("Supply: products serving this job", fontsize=10, color=T["ink2"])
    ax.set_ylabel("Demand: people asking, weighted by evidence strength", fontsize=10, color=T["ink2"])
    handles = [m.lines.Line2D([0], [0], marker="o", color="none", markerfacecolor=c, markeredgecolor="none", markersize=9,
                              label="%s (%d)" % (lab, counts.get(k, 0))) for k, lab, c in cells]
    _legend(ax, T, handles, ncol=2)
    F.layout()
    items = [{"x": float(j["supply"]), "y": float(j["demand_weighted"]), "r_px": math.sqrt(sizes[i]) / 2.0 * DPI / 72.0 + 1,
              "text": j.get("label") or j.get("code"), "priority": float(j["demand_weighted"]) - 0.01 * float(j["supply"]),
              "color": T["ink"] if (j.get("cell") or "none") != "none" or (float(j["demand_weighted"]) >= sy and float(j["supply"]) <= sx) else T["ink2"]}
             for i, j in enumerate(jobs)]
    _place_labels(F.fig, ax, items, T)
    rows = [[j.get("code"), j.get("label"), _int(j["supply"]), "%.2f" % float(j["demand_weighted"]), j.get("demand_authors", ""),
             j.get("demand_records", ""), j.get("demand_domains", ""), j.get("cell") or "none"]
            for j in sorted(jobs, key=lambda j: -float(j["demand_weighted"]))]
    return {"frame": F, "table": (["Code", "Job", "Supply", "Demand (weighted)", "Authors", "Quotes", "Domains", "Gap type"], rows)}


# ---------------------------------------------------------------- 05 evidence profile
def chart_evidence_profile(R, T, m):
    ver = R.verified()
    _need(ver, "evidence/ledger.jsonl has no verified records")
    n = len(ver)
    st = {}
    for r in ver:
        st[r.get("stance")] = st.get(r.get("stance"), 0) + 1
    stances = [(k, lab) for k, lab in STANCES if st.get(k)] + [(k, str(k)) for k in sorted(set(st) - set(k for k, _ in STANCES), key=str)]
    strength = {}
    for r in ver:
        strength[r.get("strength")] = strength.get(r.get("strength"), 0) + 1
    srcs = {}
    for r in ver:
        srcs[r.get("source_type") or "unknown"] = srcs.get(r.get("source_type") or "unknown", 0) + 1
    doms = {}
    for r in ver:
        doms[r.get("domain") or "unknown"] = doms.get(r.get("domain") or "unknown", 0) + 1
    dom_sorted = sorted(doms.items(), key=lambda kv: (-kv[1], kv[0]))
    top2 = sum(v for _, v in dom_sorted[:2]) / float(n)
    flag = top2 > 0.6
    callout = ("Concentration flag: the top 2 websites supply %s of verified quotes (above 60%%)." % _pct(top2)) if flag else \
        ("The top 2 websites supply %s of verified quotes (no flag below 60%%)." % _pct(top2))
    F = _Frame(m, T, "What the %s verified quotes look like" % _int(n),
               "Four views of the same quotes: what people said, how strong the evidence is (S0 opinion up to S4 money spent), "
               "what kind of page it came from, and which websites supplied it.",
               ["evidence/ledger.jsonl (verified records)"], body=5.9, callout=callout)
    gs = F.fig.add_gridspec(2, 2)
    F.pads = {"h_pad": 2.2, "w_pad": 3.0}
    rows = []
    # A: stance
    ax = F.fig.add_subplot(gs[0, 0])
    _style(ax, T, grid=None)
    _bare_x(ax)
    ax.spines["left"].set_visible(False)
    ys = list(range(len(stances)))
    vals = [st[k] for k, _ in stances]
    ax.barh(ys, vals, height=0.66, color=[T["s1"] if k in DEMAND else T["gray"] for k, _ in stances])
    for y, v in zip(ys, vals):
        _tip(ax, T, v, y, _int(v), fs=9.2)
    ax.set_yticks(ys)
    ax.set_yticklabels([lab for _, lab in stances], fontsize=9.5, color=T["ink"])
    ax.set_ylim(len(ys) - 0.5, -0.6)
    ax.set_xlim(0, max(vals) * 1.18)
    _panel_title(ax, T, "What people said", "number of quotes by stance", legend=True)
    _legend(ax, T, [_patch(m, T["s1"], "Counts as demand"), _patch(m, T["gray"], "Balance (praise, contra)")], ncol=2)
    rows += [["Stance", lab, st[k], _pct(st[k] / float(n))] for k, lab in stances]
    # B: strength ladder
    ax = F.fig.add_subplot(gs[0, 1])
    _style(ax, T, grid=None)
    ax.spines["left"].set_visible(False)
    ax.set_yticks([])
    keys = [k for k, _ in STRENGTHS]
    vals = [strength.get(k, 0) for k in keys]
    xs = list(range(len(keys)))
    ax.bar(xs, vals, width=0.62, color=_ramp(T, len(keys)))
    for x, v in zip(xs, vals):
        ax.annotate(_int(v), (x, v), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9.2, color=T["ink"])
    ax.set_xticks(xs)
    ax.set_xticklabels(["%s\n%s" % (k, lab) for k, lab in STRENGTHS], fontsize=8.6, color=T["ink2"])
    ax.set_ylim(0, max(vals + [1]) * 1.18)
    _panel_title(ax, T, "How strong the evidence is", "weakest (left) to strongest (right)", legend=True)
    rows += [["Strength", "%s %s" % (k, lab.replace("\n", " ")), strength.get(k, 0), _pct(strength.get(k, 0) / float(n))] for k, lab in STRENGTHS]
    # C: source types
    ax = F.fig.add_subplot(gs[1, 0])
    _style(ax, T, grid=None)
    _bare_x(ax)
    ax.spines["left"].set_visible(False)
    items = sorted(srcs.items(), key=lambda kv: (-kv[1], kv[0]))
    ys = list(range(len(items)))
    ax.barh(ys, [v for _, v in items], height=0.66, color=T["s1"])
    for y, (_, v) in zip(ys, items):
        _tip(ax, T, v, y, _int(v), fs=9.2)
    ax.set_yticks(ys)
    ax.set_yticklabels([k.replace("qa", "Q&A").capitalize() if k != "qa" else "Q&A" for k, _ in items], fontsize=9.5, color=T["ink"])
    ax.set_ylim(len(ys) - 0.5, -0.6)
    ax.set_xlim(0, max(v for _, v in items) * 1.18)
    _panel_title(ax, T, "Kind of page", "number of quotes")
    rows += [["Source type", k, v, _pct(v / float(n))] for k, v in items]
    # D: domains
    ax = F.fig.add_subplot(gs[1, 1])
    _style(ax, T, grid=None)
    _bare_x(ax)
    ax.spines["left"].set_visible(False)
    shown = dom_sorted[:7]
    other = dom_sorted[7:]
    items = [(k, v) for k, v in shown] + ([("Other (%s)" % _plural(len(other), "site"), sum(v for _, v in other))] if other else [])
    ys = list(range(len(items)))
    cols = [(T["critical"] if (flag and i < 2) else T["s1"]) for i in range(len(shown))] + ([T["gray"]] if other else [])
    ax.barh(ys, [v for _, v in items], height=0.66, color=cols)
    for y, (_, v) in zip(ys, items):
        _tip(ax, T, v, y, _pct(v / float(n)), fs=9.2)
    ax.set_yticks(ys)
    ax.set_yticklabels([k for k, _ in items], fontsize=9.5, color=T["ink"])
    ax.set_ylim(len(ys) - 0.5, -0.6)
    ax.set_xlim(0, max(v for _, v in items) * 1.22)
    _panel_title(ax, T, "Which websites", "share of verified quotes")
    rows += [["Website", k, v, _pct(v / float(n))] for k, v in dom_sorted]
    return {"frame": F, "table": (["View", "Value", "Quotes", "Share"], rows)}


# ---------------------------------------------------------------- 06 evidence over time
def chart_timeline(R, T, m):
    ver = R.verified()
    _need(ver, "evidence/ledger.jsonl has no verified records")
    dated, year_only, undated = [], 0, 0
    for r in ver:
        s = str(r.get("posted_at") or "")
        mo = re.match(r"^(\d{4})-(\d{2})", s)
        if mo and 1 <= int(mo.group(2)) <= 12:
            dated.append((int(mo.group(1)), int(mo.group(2)), r.get("stance")))
        elif re.match(r"^\d{4}$", s):
            year_only += 1
        else:
            undated += 1
    _need(dated, "no verified record has a posted month")
    first = min((y, mth) for y, mth, _ in dated)
    lastd = max((y, mth) for y, mth, _ in dated)
    span = (lastd[0] - first[0]) * 12 + lastd[1] - first[1] + 1
    quarterly = span > 36
    group_of = lambda s: "demand" if s in DEMAND else (s if s in ("praise", "contra") else "other")  # noqa: E731
    groups = [("demand", "Demand (pain, wish, workaround, switch, will pay)", T["s1"]), ("praise", "Praise", T["s3"]),
              ("contra", "Contra", T["s2"]), ("other", "Other", T["gray"])]
    bins = {}
    for y, mth, s in dated:
        key = (y, (mth - 1) // 3 * 3 + 1) if quarterly else (y, mth)
        bins.setdefault(key, {})
        g = group_of(s)
        bins[key][g] = bins[key].get(g, 0) + 1
    used = [g for g in groups if any(b.get(g[0]) for b in bins.values())]
    pr = R.protocol
    notes = []
    if year_only or undated:
        notes.append("Not shown: %s." % ", ".join(x for x in (
            ("%s with a year only" % _plural(year_only, "quote")) if year_only else "",
            ("%s without a date" % _plural(undated, "quote")) if undated else "") if x))
    window, callout = None, None
    try:
        as_of = dt.date.fromisoformat(str(pr.get("as_of")))
        days = int(pr.get("recency_days"))
        cutoff = as_of - dt.timedelta(days=days)
        window = (cutoff, as_of, days)
        inside = sum(1 for y, mth, _ in dated if "%04d-%02d" % (y, mth) >= cutoff.isoformat()[:7])
        callout = "%s of %s dated quotes (%s) were posted inside the %s-day recency window (since %s)." % (
            _int(inside), _int(len(dated)), _pct(inside / float(len(dated))), _int(days), cutoff.isoformat())
    except (TypeError, ValueError):
        notes.append("The protocol records no as_of date or recency_days, so the recency window is not marked.")
    F = _Frame(m, T, "When the evidence was posted",
               "Each bar counts verified quotes posted in one %s, split by what they say. The shaded band is the protocol's recency "
               "window: quotes inside it describe the market as it is now." % ("quarter" if quarterly else "month"),
               ["evidence/ledger.jsonl", "protocol.json (as_of, recency_days)"], body=3.6, notes=notes, callout=callout)
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid="y")
    width = 74 if quarterly else 24
    keys = sorted(bins)
    xs = [m.mdates.date2num(dt.date(y, mth, 1)) + (45 if quarterly else 15) for y, mth in keys]
    bottom = [0] * len(keys)
    handles = []
    for g, lab, col in used:
        vals = [bins[k].get(g, 0) for k in keys]
        ax.bar(xs, vals, width=width, bottom=bottom, color=col, edgecolor=T["surface"], linewidth=0.8)
        bottom = [a + b for a, b in zip(bottom, vals)]
        handles.append(_patch(m, col, lab))
    top = max(bottom)
    x0 = m.mdates.date2num(dt.date(first[0], 1, 1))
    x1 = max(xs[-1] + 40, m.mdates.date2num(window[1]) + 20 if window else 0)
    if window:
        # Nothing can be posted after as_of, so the band runs to the plot edge (the last bar is centred past as_of).
        lo = m.mdates.date2num(window[0])
        ax.axvspan(lo, x1, color=T["s1"], alpha=0.08, lw=0, zorder=0)
        ax.annotate("Recency window\n%s days to %s" % (_int(window[2]), window[1].isoformat()), (x1, top * 1.2), xytext=(-4, -2),
                    textcoords="offset points", ha="right", va="top", fontsize=8.8, color=T["ink2"])
    ax.set_xlim(x0, x1)
    ax.set_ylim(0, top * 1.22)
    ax.xaxis_date()
    years = lastd[0] - first[0] + 1
    ax.xaxis.set_major_locator(m.mdates.YearLocator(base=1 if years <= 12 else 2))
    ax.xaxis.set_major_formatter(m.mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_locator(m.ticker.MaxNLocator(integer=True))
    ax.set_ylabel("Verified quotes", fontsize=10, color=T["ink2"])
    if len(handles) > 1:
        _legend(ax, T, handles, ncol=len(handles))
    rows = [["%d Q%d" % (y, (mth - 1) // 3 + 1) if quarterly else "%d-%02d" % (y, mth)] + [bins[(y, mth)].get(g, 0) for g, _, _ in used]
            for y, mth in keys]
    return {"frame": F, "table": (["Period"] + [lab.split(" (")[0] for _, lab, _ in used], rows)}


# ---------------------------------------------------------------- 07 coding reliability
def chart_reliability(R, T, m):
    agr = R.json("coding", "agreement.json")
    _need(isinstance(agr, dict) and agr.get("codes"), "coding/agreement.json is missing (run `gapscan.py agreement RUN`)")
    codes = agr["codes"]
    elig = agr.get("eligible_codes") or [k for k, v in codes.items() if v.get("status") in ("accept", "provisional", "weak", "revise")]
    items = [(k, codes[k]) for k in elig if k in codes and _num(codes[k].get("alpha")) is not None]
    _need(items, "no code had enough positive examples to test agreement")
    items.sort(key=lambda kv: (-kv[1]["alpha"], kv[0]))
    book = R.codebook()
    acc = _num(R.c.get("coding.alpha_accept")) or 0.8
    prov = _num(R.c.get("coding.alpha_provisional")) or 0.667
    word = {"accept": ("reliable", T["good"], "✓"), "provisional": ("tentative", T["warning"], "~")}
    na = len(agr.get("not_assessable") or [])
    tally = {}
    for _, v in items:
        tally[v.get("status")] = tally.get(v.get("status"), 0) + 1
    verdict = agr.get("verdict") or "unknown"
    plain = {"accept": "reliable", "provisional": "provisional (supports tentative conclusions only)",
             "revise": "needs a codebook revision", "weak": "needs a codebook revision"}.get(verdict, verdict)
    callout = "Verdict: %s. %s reliable, %s tentative, %s unreliable%s." % (
        plain, _int(tally.get("accept", 0)), _int(tally.get("provisional", 0)),
        _int(sum(v for k, v in tally.items() if k not in ("accept", "provisional"))),
        ("; %s too rare to test" % _plural(na, "more code")) if na else "")
    notes = []
    s1, s2 = agr.get("strength") or {}, agr.get("strength_vs_miner") or {}
    if _num(s1.get("alpha")) is not None:
        notes.append("Strength ratings (S0-S4): coder vs coder alpha %.2f (%s)%s." % (
            s1["alpha"], s1.get("status", ""), ("; coder vs miner alpha %.2f (%s)" % (s2["alpha"], s2.get("status", "")))
            if _num(s2.get("alpha")) is not None else ""))
    if agr.get("units"):
        notes.append("Agreement measured on %s double-coded quotes, codebook v%s." % (_int(agr["units"]), agr.get("version", "?")))
    sources = ["coding/agreement.json", "coding/codebook.v*.json"]
    th = R.json("coding", "themes.json")
    if isinstance(th, dict) and th.get("themes_observed") is not None:
        sources.append("coding/themes.json")
        est = _num((th.get("themes_estimated") or {}).get("estimate"))
        notes.append("Themes: %s observed%s; theme saturation %s." % (
            _int(th["themes_observed"]), (" of about %s estimated" % _int(est)) if est is not None else "",
            "reached" if th.get("saturated") else "not reached"))
    F = _Frame(m, T, "Do two independent coders agree?",
               "Each bar is one code (a job, pain or theme) that two coders applied separately; Krippendorff's alpha of 1 means "
               "perfect agreement. Bars past %.2f are reliable; %.3f-%.2f supports tentative conclusions only." % (acc, prov, acc),
               sources, body=max(1.8, 0.6 + 0.27 * len(items)), notes=notes, callout=callout)
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid=None)
    ax.spines["left"].set_visible(False)
    ys = list(range(len(items)))
    vals = [float(v["alpha"]) for _, v in items]
    cols = [word.get(v.get("status"), ("unreliable", T["critical"], "✗"))[1] for _, v in items]
    ax.barh(ys, vals, height=0.52, color=cols)
    for y, (k, v) in zip(ys, items):
        w = word.get(v.get("status"), ("unreliable", T["critical"], "✗"))
        ax.annotate("%.2f %s %s" % (float(v["alpha"]), w[2], w[0]), (max(float(v["alpha"]), 0), y), xytext=(5, 0),
                    textcoords="offset points", ha="left", va="center", fontsize=9, color=T["ink"], zorder=5,
                    bbox=dict(boxstyle="square,pad=0.15", fc=T["surface"], ec="none"))
    labels = []
    for k, _ in items:
        lab = (book.get(k) or {}).get("label")
        labels.append(("%s (%s)" % (lab, k)) if lab and len(lab) + len(k) < 58 else (lab or k))
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9.2, color=T["ink"])
    ax.set_ylim(len(ys) - 0.5, -1.4)
    lo = min(0.0, min(vals))
    ax.set_xlim(lo, 1.32)
    for v, txt, side in ((prov, "tentative from %.3f" % prov, -1), (acc, "reliable from %.2f" % acc, 1)):
        ax.axvline(v, color=T["ink2"], lw=1, zorder=1)
        ax.annotate(txt, (v, -0.75), ha="left" if side > 0 else "right", va="bottom", fontsize=8.8, color=T["ink2"],
                    xytext=(4 * side, 0), textcoords="offset points")
    ax.set_xticks([x / 10.0 for x in range(int(math.floor(lo * 10)), 11, 2)])
    ax.xaxis.set_major_formatter(m.ticker.FuncFormatter(lambda v, _: "%.1f" % v))
    rows = [[k, (book.get(k) or {}).get("label", ""), "%.3f" % float(v["alpha"]), v.get("positives", ""), v.get("status", "")] for k, v in items]
    rows += [[k, (book.get(k) or {}).get("label", ""), "", (codes.get(k) or {}).get("positives", ""), "not assessable"]
             for k in agr.get("not_assessable") or []]
    return {"frame": F, "table": (["Code", "Label", "Alpha", "Positives", "Status"], rows)}


# ---------------------------------------------------------------- 08 gap scorecard
def _card_order(cards, checks):
    rank = {"survives": 0, "candidate": 1, "weakened": 2, "killed": 3, "insufficient": 4}
    return sorted(cards, key=lambda c: (rank.get(c.get("status"), 5), len((checks.get(c["gap_id"]) or {}).get("reasons") or []),
                                        c["gap_id"]))


def chart_scorecard(R, T, m):
    cards = R.cards()
    _need(cards, "gaps/cards.jsonl is missing or empty (run the synthesis phase)")
    cc = R.json("gaps", "card-check.json")
    checks = (cc or {}).get("cards") or {}
    rt = R.redteam()
    cards = _card_order(cards, checks)
    th = [("records", "Quotes", R.c.get("gap_card.min_records")), ("domains", "Websites", R.c.get("gap_card.min_domains")),
          ("source_types", "Kinds of page", R.c.get("gap_card.min_source_types")), ("authors", "Authors", R.c.get("gap_card.min_authors"))]
    notes = [] if checks else ["gaps/card-check.json is missing, so the threshold columns are empty."]
    F = _Frame(m, T, "Gap cards: which ideas held up",
               "One row per gap idea. The first five columns are the evidence thresholds every idea must pass (green tick = met, "
               "red cross = short); the last two say what happened to it.",
               ["gaps/cards.jsonl", "gaps/card-check.json", "gaps/redteam/*.json"], body=0.75 + 0.43 * len(cards), notes=notes)
    ax = F.fig.add_subplot(111)
    ax.set_facecolor(T["surface"])
    ax.axis("off")
    widths = [1.0, 1.05, 1.15, 1.0, 1.4, 1.85, 1.45]
    lw = 5.0
    cols_x = [lw + sum(widths[:i]) for i in range(len(widths))]
    total_w = lw + sum(widths)
    ax.set_xlim(0, total_w)
    ax.set_ylim(len(cards) + 0.1, -1.25)
    heads = [(lab, "need ≥%s" % v) for _, lab, v in th] + [("Triangulation", "pain, demand, supply"), ("Final status", ""), ("Red team", "")]
    for i, (h1, h2) in enumerate(heads):
        ax.text(cols_x[i] + widths[i] / 2.0, -0.62, h1, ha="center", va="bottom", fontsize=9.4, fontweight="bold", color=T["ink"])
        if h2:
            ax.text(cols_x[i] + widths[i] / 2.0, -0.58, h2, ha="center", va="top", fontsize=8.2, color=T["muted"])
    ax.text(0.05, -0.62, "Gap idea", ha="left", va="bottom", fontsize=9.4, fontweight="bold", color=T["ink"])
    rows = []
    for r, c in enumerate(cards):
        gid = c["gap_id"]
        num = (checks.get(gid) or {}).get("numbers") or {}
        ax.text(0.05, r + 0.5, gid, ha="left", va="center", fontsize=9.2, fontweight="bold", color=T["ink"])
        ax.text(1.0, r + 0.5, _clip(c.get("title") or "", 50), ha="left", va="center", fontsize=9.0, color=T["ink2"])
        cells = []
        for i, (key, _, need) in enumerate(th):
            v = num.get(key)
            ok = v is not None and need is not None and v >= need
            cells.append((i, None if v is None else ok, ("✓ " if ok else "✗ ") + _int(v) if v is not None else "–"))
        tri = num.get("triangulation")
        if isinstance(tri, dict) and tri:
            missing = [k for k in ("pain", "demand", "supply") if not tri.get(k)]
            cells.append((4, not missing, "✓ all 3" if not missing else "✗ no " + "/".join(missing)))
        else:
            cells.append((4, None, "–"))
        for i, ok, txt in cells:
            x, w = cols_x[i], widths[i]
            if ok is not None:
                ax.add_patch(m.patches.FancyBboxPatch((x + 0.06, r + 0.1), w - 0.12, 0.8, boxstyle="round,pad=0,rounding_size=0.12",
                                                      facecolor=T["good"] if ok else T["critical"], alpha=T["tint"] + (0 if ok else 0.04),
                                                      lw=0))
            ax.text(x + w / 2.0, r + 0.5, txt, ha="center", va="center", fontsize=9, color=T["ink"] if ok is not None else T["muted"])
        status = c.get("status") or "?"
        sl, tone = CARD_STATUS.get(status, (status, "gray"))
        rv = (rt.get(gid) or {}).get("verdict")
        for i, (txt, tn) in enumerate(((sl, tone), (rv.capitalize() if rv else "–", CARD_STATUS.get(rv, ("", "gray"))[1] if rv else None))):
            x, w = cols_x[5 + i], widths[5 + i]
            if tn:
                ax.add_patch(m.patches.FancyBboxPatch((x + 0.08, r + 0.14), w - 0.16, 0.72, boxstyle="round,pad=0,rounding_size=0.2",
                                                      facecolor=T[tn], alpha=T["tint"] + 0.06, lw=0))
            ax.text(x + w / 2.0, r + 0.5, txt, ha="center", va="center", fontsize=9, color=T["ink"] if tn else T["muted"],
                    fontweight="bold" if tn in ("good", "warning", "critical") else "normal")
        ax.plot([0, total_w], [r + 1, r + 1], color=T["grid"], lw=0.8)
        rows.append([gid, c.get("title", "")] + [num.get(k, "") for k, _, _ in th] +
                    ["yes" if isinstance(tri, dict) and all(tri.get(k) for k in ("pain", "demand", "supply")) else ("no" if tri else "")] +
                    [status, rv or "", "; ".join((checks.get(gid) or {}).get("reasons") or [])])
    return {"frame": F, "table": (["Gap", "Title", "Quotes", "Websites", "Kinds of page", "Authors", "Triangulated", "Status",
                                   "Red team", "Shortfalls"], rows)}


# ---------------------------------------------------------------- 09 ranking and sizing
def chart_ranking(R, T, m):
    rk = R.json("gaps", "ranking.json") or {}
    ranked = [x for x in rk.get("ranked") or [] if x.get("gap_id")][:10]
    sizing = ((R.json("gaps", "sizing.json") or {}).get("gaps")) or {}
    _need(ranked or sizing, "no gap was ranked or sized (gaps/ranking.json and gaps/sizing.json are missing or empty)")
    titles = dict((c["gap_id"], c.get("title", "")) for c in R.cards())
    gids = [x["gap_id"] for x in ranked] + [g for g in sorted(sizing) if g not in set(x["gap_id"] for x in ranked)]
    amb = _num((R.protocol.get("ambition") or {}).get("min_arr_usd"))
    callout = None
    if amb and gids and gids[0] in sizing:
        base = _num((((sizing[gids[0]].get("usd_per_year") or {}).get("base")) or {}).get("som"))
        if base is not None:
            callout = "%s base case: %s a year obtainable revenue, %s the founder ambition of %s a year." % (
                gids[0], _money_full(base), "above" if base >= amb else "below", _money_full(amb))
    F = _Frame(m, T, "Ranked gaps and how big they could be",
               "Left: the desk score out of 100 (longer = stronger case) and how often the gap stays in the top 3 when the "
               "criteria weights are varied. Right: obtainable revenue per year (low to high, dot = base case) against the "
               "founder's ambition line.",
               ["gaps/ranking.json", "gaps/sizing.json", "protocol.json (ambition.min_arr_usd)"],
               body=max(2.1, 1.0 + 0.8 * len(gids)), callout=callout,
               notes=[rk.get("note") or "", (sizing and (R.json("gaps", "sizing.json") or {}).get("note")) or ""])
    gs = F.fig.add_gridspec(1, 2, width_ratios=[1, 1.15])
    F.pads = {"w_pad": 1.0}
    ax, ax2 = F.fig.add_subplot(gs[0]), F.fig.add_subplot(gs[1])
    ys = list(range(len(gids)))
    _style(ax, T, grid=None)
    _bare_x(ax)
    ax.spines["left"].set_visible(False)
    by = dict((x["gap_id"], x) for x in ranked)
    ax.barh(ys, [100] * len(ys), height=0.24, color=T["wash"], lw=0)
    for y, g in zip(ys, gids):
        x = by.get(g)
        if x and _num(x.get("total")) is not None:
            ax.barh([y], [float(x["total"])], height=0.24, color=T["s1"], lw=0)
            p3 = _num(x.get("p_top3"))
            ax.annotate("%.1f / 100" % float(x["total"]) + ("   top 3 in %s of weightings" % _pct(p3) if p3 is not None else ""),
                        (0, y - 0.2), ha="left", va="bottom", fontsize=9.2, color=T["ink"], xytext=(0, 1), textcoords="offset points")
            parts = ["%s %s" % (k.replace("_", " "), v) for k, v in (x.get("scores") or {}).items()]
            if parts:
                half = (len(parts) + 1) // 2
                ax.annotate("  ·  ".join(parts[:half]) + "\n" + "  ·  ".join(parts[half:]) + "   (each 0-3)", (0, y + 0.2),
                            ha="left", va="top", fontsize=8.4, color=T["ink2"], xytext=(0, -2), textcoords="offset points",
                            linespacing=1.4)
        else:
            ax.annotate("not ranked", (0, y - 0.2), ha="left", va="bottom", fontsize=9.2, color=T["muted"])
    ax.set_yticks(ys)
    ax.set_yticklabels(["%s\n%s" % (g, _clip(titles.get(g) or (by.get(g) or {}).get("title", ""), 34)) for g in gids], fontsize=9.2,
                       color=T["ink"])
    ax.set_xlim(0, 104)
    ax.set_ylim(len(ys) - 0.3, -0.75)
    _panel_title(ax, T, "Desk score")
    _style(ax2, T, grid="x")
    ax2.spines["left"].set_visible(False)
    ax2.set_yticks([])
    vals = []
    for y, g in zip(ys, gids):
        u = (sizing.get(g) or {}).get("usd_per_year") or {}
        lo, base, hi = [_num((u.get(k) or {}).get("som")) for k in ("low", "base", "high")]
        if lo is None and base is None and hi is None:
            ax2.annotate("not sized", (0.5, y), xycoords=("axes fraction", "data"), ha="center", va="center", fontsize=9, color=T["muted"])
            continue
        pts = [v for v in (lo, base, hi) if v is not None and v > 0]
        vals += pts
        if lo and hi:
            ax2.plot([lo, hi], [y, y], color=T["gray"], lw=2, solid_capstyle="round", zorder=2)
        for v, tag in ((lo, "low"), (hi, "high")):
            if v:
                ax2.plot([v], [y], "o", color=T["gray"], markersize=6, markeredgecolor=T["surface"], zorder=3)
                ax2.annotate("%s %s" % (tag, _money(v)), (v, y), xytext=(0, -9), textcoords="offset points", ha="center", va="top",
                             fontsize=8.6, color=T["ink2"])
        if base:
            ax2.plot([base], [y], "o", color=T["s1"], markersize=10, markeredgecolor=T["surface"], markeredgewidth=2, zorder=4)
            ax2.annotate("base %s" % _money(base), (base, y), xytext=(0, 9), textcoords="offset points", ha="center", va="bottom",
                         fontsize=9.2, fontweight="bold", color=T["ink"], zorder=5,
                         bbox=dict(boxstyle="square,pad=0.15", fc=T["surface"], ec="none"))
    if amb:
        vals.append(amb)
    if vals:
        lo_v, hi_v = min(vals), max(vals)
        ax2.set_xscale("log")
        ax2.set_xlim(10 ** (math.floor(math.log10(lo_v)) - 0.15), 10 ** (math.ceil(math.log10(hi_v)) + 0.15))
        ticks = [10 ** k for k in range(int(math.floor(math.log10(lo_v))), int(math.ceil(math.log10(hi_v))) + 1)]
        ax2.set_xticks(ticks)
        ax2.xaxis.set_major_formatter(m.ticker.FuncFormatter(lambda v, _: _money(v)))
        ax2.xaxis.set_minor_locator(m.ticker.NullLocator())
    if amb:
        ax2.axvline(amb, color=T["s2"], lw=1.5, zorder=1)
        ax2.annotate("Ambition %s / year" % _money(amb), (amb, -0.62), ha="left", va="center", fontsize=9, color=T["ink"],
                     xytext=(5, 0), textcoords="offset points")
    ax2.set_ylim(len(ys) - 0.3, -0.75)
    _panel_title(ax2, T, "Obtainable revenue per year (SOM)")
    crit = list((rk.get("weights") or {}).keys()) or sorted(set(k for x in ranked for k in (x.get("scores") or {})))
    rows = []
    for g in gids:
        x = by.get(g) or {}
        u = (sizing.get(g) or {}).get("usd_per_year") or {}
        rows.append([g, titles.get(g) or x.get("title", ""), x.get("rank", ""), ("%.1f" % x["total"]) if _num(x.get("total")) is not None else "",
                     _pct(x["p_top3"]) if _num(x.get("p_top3")) is not None else ""] +
                    [_money_full((u.get(k) or {}).get("som"), "$") if _num((u.get(k) or {}).get("som")) is not None else "" for k in ("low", "base", "high")] +
                    [(x.get("scores") or {}).get(k, "") for k in crit])
    return {"frame": F, "table": (["Gap", "Title", "Rank", "Score", "Top 3 share", "SOM low", "SOM base", "SOM high"] +
                                  ["%s (0-3)" % k.replace("_", " ") for k in crit], rows)}


# ---------------------------------------------------------------- 10 price ladder
def chart_prices(R, T, m):
    attrs = dict((a["entity_id"], a) for a in R.jsonl("landscape", "entity-attributes.jsonl") if a.get("entity_id"))
    rows_in = R.csv("analysis", "price_ladder.csv")
    src = ["analysis/price_ladder.csv", "landscape/entity-attributes.jsonl"]
    if not rows_in:
        src = ["landscape/entity-attributes.jsonl"]
        rows_in = [dict(entity_id=k, min_paid_month=(a.get("pricing") or {}).get("min_paid_month"),
                        currency=(a.get("pricing") or {}).get("currency")) for k, a in attrs.items()]
    labels = R.category_labels()
    by, other_cur = {}, 0
    for r in rows_in:
        v = _num(r.get("min_paid_month"))
        if v is None or v <= 0:
            continue
        if (r.get("currency") or "").upper() != "USD":
            other_cur += 1
            continue
        cat = (attrs.get(r.get("entity_id")) or {}).get("category") or "uncategorised"
        by.setdefault(cat, []).append(v)
    _need(by, "no USD minimum paid price was recorded (analysis/price_ladder.csv or entity attributes)")
    cats = [c for c in by if len(by[c]) >= 2]
    single = [c for c in by if len(by[c]) < 2]
    cats = sorted(cats, key=lambda c: (-len(by[c]), c))[:22]
    _need(cats, "fewer than two USD prices in every category")
    cats.sort(key=lambda c: (statistics.median(by[c]), c))
    notes = []
    if other_cur:
        notes.append("Left out: %s in other currencies." % _plural(other_cur, "price"))
    if single:
        notes.append("Left out: %s with a single USD price." % _plural(len(single), "category", "categories"))
    F = _Frame(m, T, "What competitors charge",
               "Each dot is one product's cheapest paid plan per month (USD); the dark tick and the number on the right are the "
               "category median. Cheapest categories at the top. The scale is logarithmic, so equal distances mean equal "
               "price ratios.",
               src, body=max(2.0, 0.7 + 0.3 * len(cats)), notes=notes)
    ax = F.fig.add_subplot(111)
    _style(ax, T, grid="x")
    ax.spines["left"].set_visible(False)
    rnd = random.Random(7)
    allv = []
    for y, c in enumerate(cats):
        vs = by[c]
        allv += vs
        ax.scatter(vs, [y + rnd.uniform(-0.2, 0.2) for _ in vs], s=34, color=T["s1"], alpha=0.75, edgecolors=T["surface"],
                   linewidths=1, zorder=3)
        med = statistics.median(vs)
        ax.plot([med, med], [y - 0.34, y + 0.34], color=T["ink"], lw=2.2, zorder=4, solid_capstyle="round")
    ax.set_xscale("log")
    lo, hi = min(allv), max(allv)
    ax.set_xlim(lo / 1.6, hi * 1.6)
    ticks = [t for t in (0.5, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000) if lo / 1.6 <= t <= hi * 1.6]
    ax.set_xticks(ticks)
    ax.xaxis.set_major_formatter(m.ticker.FuncFormatter(lambda v, _: _money(v)))
    ax.xaxis.set_minor_locator(m.ticker.NullLocator())
    ax.set_yticks(range(len(cats)))
    ax.set_yticklabels(["%s (%d)" % (labels.get(c, c), len(by[c])) for c in cats], fontsize=9.5, color=T["ink"])
    ax.set_ylim(len(cats) - 0.5, -0.6)
    ax2 = ax.twinx()  # right-hand labels for the medians only (same scale, no second measure)
    ax2.set_ylim(ax.get_ylim())
    ax2.set_yticks(range(len(cats)))
    ax2.set_yticklabels([_money(statistics.median(by[c])) for c in cats], fontsize=9.5, color=T["ink"], fontweight="bold")
    ax2.tick_params(length=0, pad=6)
    for s in ax2.spines.values():
        s.set_visible(False)
    ax2.annotate("Median", (1, 1), xycoords="axes fraction", xytext=(6, 4), textcoords="offset points", ha="left", va="bottom",
                 fontsize=9, color=T["ink2"])
    ax.set_xlabel("Cheapest paid plan, USD per month (log scale)", fontsize=10, color=T["ink2"])
    rows = [[labels.get(c, c), len(by[c]), _money(min(by[c]), "$"), _money(statistics.median(by[c]), "$"), _money(max(by[c]), "$")]
            for c in sorted(by, key=lambda c: statistics.median(by[c]))]
    return {"frame": F, "table": (["Category", "Prices", "Cheapest", "Median", "Highest"], rows)}


# ---------------------------------------------------------------- 11 demand bursts
def _month(s):
    mo = re.match(r"^(\d{4})-(\d{2})", str(s or ""))
    return dt.date(int(mo.group(1)), int(mo.group(2)), 1) if mo else None


def chart_bursts(R, T, m):
    b = R.json("evidence", "bursts.json")
    series = [s for s in (b or {}).get("series") or [] if s.get("series_id")]
    _need(series, "evidence/bursts.json is missing or has no series (run `gapscan.py bursts RUN`)")
    sigs = {}
    for f in R.files("evidence", "signals", "*.json"):
        doc = R.json("evidence", "signals", os.path.basename(f))
        if isinstance(doc, dict) and doc.get("series_id"):
            sigs[doc["series_id"]] = doc
    series = [s for s in series if s["series_id"] in sigs][:6]
    _need(series, "evidence/signals/*.json (the raw series behind bursts.json) are missing")
    wn = R.jsonl("evidence", "why-now.jsonl")
    F = _Frame(m, T, "Is interest rising? Demand bursts",
               "Each panel tracks how often a term appears per month. Shaded spans are bursts the burst test found; orange "
               "means statistically significant, grey means it could be chance. Ticks at the bottom mark dated why-now events.",
               ["evidence/bursts.json", "evidence/signals/*.json", "evidence/why-now.jsonl"], body=0.2 + 2.3 * len(series))
    gs = F.fig.add_gridspec(len(series), 1)
    F.pads = {"h_pad": 2.0}
    rows = []
    for i, s in enumerate(series):
        sig = sigs[s["series_id"]]
        ax = F.fig.add_subplot(gs[i])
        _style(ax, T, grid="y")
        pts = []
        for x in sig.get("points") or []:
            d = _month(x.get("period"))
            if d is None:
                continue
            if s.get("kind") == "proportion" or sig.get("kind") == "proportion":
                den, num = _num(x.get("d")), _num(x.get("r"))
                if den:
                    pts.append((d, 1e5 * num / den, x))
            elif _num(x.get("value")) is not None:
                pts.append((d, float(x["value"]), x))
        if not pts:
            ax.text(0.5, 0.5, "no points", transform=ax.transAxes, ha="center", color=T["muted"])
            continue
        prop = s.get("kind") == "proportion"
        xs = [m.mdates.date2num(d) + 14 for d, _, _ in pts]
        ys = [v for _, v, _ in pts]
        sig_flag = bool(s.get("significant"))
        for bst in s.get("bursts") or []:
            a, z = _month(bst.get("start")), _month(bst.get("end"))
            if a and z:
                ax.axvspan(m.mdates.date2num(a), m.mdates.date2num(z) + 30, color=T["s2"] if sig_flag else T["gray"],
                           alpha=0.18 if sig_flag else 0.2, lw=0, zorder=0)
        ax.plot(xs, ys, color=T["s1"], lw=2, zorder=3, solid_joinstyle="round")
        ax.plot([xs[-1]], [ys[-1]], "o", color=T["s1"], markersize=6, markeredgecolor=T["surface"], markeredgewidth=1.5, zorder=4)
        top = max(ys) * 1.25 if max(ys) > 0 else 1
        ax.set_ylim(0, top)
        term = str(s.get("term") or "").lower()
        marks = {}
        for w in wn:
            d = _month(w.get("date"))
            rel = [str(t).lower() for t in w.get("related_terms") or []]
            if d and term and term in rel and xs[0] - 31 <= m.mdates.date2num(d) <= xs[-1] + 31:
                marks.setdefault(d, []).append(str(w.get("id") or "why-now"))
        for d, ids in sorted(marks.items()):
            xd = m.mdates.date2num(d) + 14
            ax.plot([xd, xd], [0, top * 0.12], color=T["ink2"], lw=1.2, zorder=4)
            ax.annotate("\n".join(ids), (xd, top * 0.12), xytext=(0, 1), textcoords="offset points", ha="center",
                        va="bottom", fontsize=8, color=T["ink2"], zorder=5,
                        bbox=dict(boxstyle="square,pad=0.1", fc=T["surface"], ec="none", alpha=0.85))
        pv = _num(s.get("p_value"))
        verdict = ("significant burst" if sig_flag else ("burst not significant" if s.get("bursts") else "no burst")) if prop else \
            "trend: %s" % (s.get("trend") or {}).get("direction", "n/a") if isinstance(s.get("trend"), dict) else ""
        _panel_title(ax, T, "“%s” on %s: %s%s" % (s.get("term"), (s.get("source") or "").upper() or "?", verdict,
                                                          (" (p = %.3f)" % pv) if pv is not None else ""))
        ax.set_xlim(xs[0] - 20, xs[-1] + 20)
        ax.xaxis_date()
        ax.xaxis.set_major_locator(m.mdates.MonthLocator(bymonth=(1, 7)))
        ax.xaxis.set_major_formatter(m.mdates.DateFormatter("%b %Y"))
        ax.set_ylabel("per 100k items" if prop else "value", fontsize=9, color=T["ink2"])
        for d, v, x in pts:
            rows.append([s.get("term"), d.strftime("%Y-%m"), ("%.2f" % v), x.get("r", ""), x.get("d", "")])
    return {"frame": F, "table": (["Term", "Month", "Rate per 100k", "Matches", "All items"], rows)}


# ---------------------------------------------------------------- 12 run effort
def _ts(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def chart_effort(R, T, m):
    events = R.jsonl("events.jsonl")
    st = R.json("state.json") or {}
    lock = R.json("protocol.lock.json") or {}
    per, timeline = {}, []
    for e in events:
        if e.get("kind") == "assign":
            ph = (e.get("data") or {}).get("phase") or "?"
            k = len((e.get("data") or {}).get("files") or [])
            per[ph] = per.get(ph, 0) + k
            t = _ts(e.get("ts"))
            if t and k:
                timeline.append((t, k))
    src = ["events.jsonl"]
    if not per:
        for g in (st.get("groups") or {}).values():
            if isinstance(g, dict) and g.get("phase"):
                per[g["phase"]] = per.get(g["phase"], 0) + len(g.get("paths") or [])
        src = ["state.json (groups)"]
    _need(per, "events.jsonl and state.json record no subagent assignments")
    amends = [a for a in lock.get("amendments") or [] if isinstance(a, dict)]
    used = (st.get("budget") or {}).get("subagents_used")
    cap = _num(R.c.get("budget.subagents_max"))
    total = sum(per.values())
    sub = "%s subagents assigned" % _int(total)
    if used is not None and cap:
        sub = "%s of %s subagents used" % (_int(used), _int(cap))
    F = _Frame(m, T, "Where the effort went: %s" % sub,
               "Left: subagents assigned per pipeline phase, in the order they ran. Right: the running total over the run, with "
               "each protocol amendment marked by its number (listed below).",
               src + ["state.json (budget)", "protocol.lock.json (amendments)"],
               body=max(3.0, 1.9 + 0.24 * len(per) + 0.24 * min(len(amends), 8)))
    nrow = 2 if amends else 1
    gs = F.fig.add_gridspec(nrow, 2, width_ratios=[1, 1.25],
                            height_ratios=[0.4 + 0.24 * len(per), 0.45 + 0.24 * min(len(amends), 8)] if amends else [1])
    F.pads = {"w_pad": 2.0, "h_pad": 1.6}
    ax = F.fig.add_subplot(gs[0, 0])
    _style(ax, T, grid=None)
    _bare_x(ax)
    ax.spines["left"].set_visible(False)
    phases = list(per)
    ys = list(range(len(phases)))
    ax.barh(ys, [per[k] for k in phases], height=0.66, color=T["s1"])
    for y, k in zip(ys, phases):
        _tip(ax, T, per[k], y, _int(per[k]), fs=9.2)
    ax.set_yticks(ys)
    ax.set_yticklabels([PHASES.get(k, k) for k in phases], fontsize=9.4, color=T["ink"])
    ax.set_ylim(len(ys) - 0.5, -0.6)
    ax.set_xlim(0, max(per.values()) * 1.15)
    _panel_title(ax, T, "Subagents per phase")
    ax2 = F.fig.add_subplot(gs[0, 1])
    _style(ax2, T, grid="y")
    if timeline:
        timeline.sort()
        xs, cum, run = [], [], 0
        for t, k in timeline:
            run += k
            xs.append(m.mdates.date2num(t))
            cum.append(run)
        ax2.step(xs, cum, where="post", color=T["s1"], lw=2)
        ax2.plot([xs[-1]], [cum[-1]], "o", color=T["s1"], markersize=6, markeredgecolor=T["surface"], zorder=4)
        _tip(ax2, T, xs[-1], cum[-1], _int(cum[-1]), dx=7, fs=9.5, weight="bold")
        top = max(cum[-1], cap or 0) * 1.15
        span = xs[-1] - xs[0]
        if cap:
            ax2.axhline(cap, color=T["ink2"], lw=1)
            ax2.annotate("Budget now: %s" % _int(cap), (xs[0], cap), xytext=(2, 3), textcoords="offset points", fontsize=8.8,
                         color=T["ink2"], va="bottom", zorder=5, bbox=dict(boxstyle="square,pad=0.1", fc=T["surface"], ec="none"))
        groups = []  # amendments close in time share one marker
        for i, a in enumerate(amends, 1):
            t = _ts(a.get("at"))
            if t:
                xa = m.mdates.date2num(t)
                ax2.axvline(xa, color=T["s2"], lw=1, alpha=0.6, zorder=1)
                if groups and xa - groups[-1][0] < 0.035 * (span or 1):
                    groups[-1][1].append(i)
                else:
                    groups.append([xa, [i]])
        for xa, ids in groups:
            ax2.annotate(",".join(str(i) for i in ids), (xa, top), xytext=(0, -2), textcoords="offset points", ha="center", va="top",
                         fontsize=8.8, fontweight="bold", color=T["ink"], zorder=6,
                         bbox=dict(boxstyle="round,pad=0.25", fc=T["surface"], ec=T["s2"], lw=1))
        ax2.set_ylim(0, top * 1.04)
        ax2.set_xlim(xs[0] - 0.03 * span - 0.001, xs[-1] + 0.1 * span + 0.001)
        ax2.xaxis_date()
        loc = m.mdates.AutoDateLocator(maxticks=7)
        ax2.xaxis.set_major_locator(loc)
        ax2.xaxis.set_major_formatter(m.mdates.DateFormatter("%H:%M" if span < 1.5 else "%d %b"))
        _panel_title(ax2, T, "Running total of subagents")
    else:
        ax2.axis("off")
        ax2.text(0.5, 0.5, "events.jsonl has no timed assignments", ha="center", va="center", color=T["muted"], fontsize=9.5)
    if amends:
        axt = F.fig.add_subplot(gs[1, :])
        axt.axis("off")
        _panel_title(axt, T, "Protocol amendments after the freeze (%d)" % len(amends))
        for i, a in enumerate(amends[:8], 1):
            t = _ts(a.get("at"))
            keys = ", ".join(s.get("key", "?") for s in a.get("sets") or [] if isinstance(s, dict))
            line = "%d.  %s  %s  %s" % (i, t.strftime("%H:%M") if t else "", ("[" + keys + "]") if keys else "", _clip(a.get("reason"), 120))
            axt.text(0, 1 - (i - 0.4) / float(min(len(amends), 8) + 0.2), line, transform=axt.transAxes, ha="left", va="center",
                     fontsize=8.8, color=T["ink2"])
    rows = [[PHASES.get(k, k), k, per[k]] for k in phases]
    rows += [["Amendment %d" % i, a.get("at", ""), "; ".join(s.get("key", "?") for s in a.get("sets") or [] if isinstance(s, dict))]
             for i, a in enumerate(amends, 1)]
    return {"frame": F, "table": (["Phase", "Key", "Subagents"], rows)}


CHARTS = [
    ("01", "funnel", "Search and screening funnel", chart_funnel),
    ("02", "saturation", "Landscape saturation", chart_saturation),
    ("03", "crowding", "Competitor crowding by category", chart_crowding),
    ("04", "gap-map", "Demand-supply gap map", chart_gapmap),
    ("05", "evidence-profile", "Evidence profile", chart_evidence_profile),
    ("06", "evidence-timeline", "Evidence over time", chart_timeline),
    ("07", "coding-reliability", "Coding reliability", chart_reliability),
    ("08", "gap-scorecard", "Gap cards scorecard", chart_scorecard),
    ("09", "ranking-sizing", "Ranking and sizing", chart_ranking),
    ("10", "price-ladder", "Price ladder", chart_prices),
    ("11", "demand-bursts", "Demand bursts", chart_bursts),
    ("12", "run-effort", "Run effort and amendments", chart_effort),
]


# ---------------------------------------------------------------- plain-language summary
def _shortfall(reason):
    pats = [(r"(\d+) domains? \(need (\d+)\)", "evidence from only %s; %s needed", ("website", None)),
            (r"(\d+) verified supporting records? \(need (\d+)\)", "only %s; %s needed", ("verified quote", None)),
            (r"(\d+) source types? \(need (\d+)\)", "only %s; %s needed", ("kind of page", "kinds of page")),
            (r"(\d+) distinct authors? \(need (\d+)\)", "only %s; %s needed", ("distinct author", None))]
    for pat, txt, word in pats:
        mo = re.match(pat, reason or "")
        if mo:
            return txt % (_plural(int(mo.group(1)), word[0], word[1]), mo.group(2))
    mo = re.match(r"triangulation incomplete \((.*)\)", reason or "")
    if mo:
        miss = [k for k, v in re.findall(r"(\w+)=(\w+)", mo.group(1)) if v != "True"]
        return "no %s signal (pain, demand and supply must all show up)" % "/".join(miss or ["?"])
    return reason or "below the evidence thresholds"


def _kill_reason(gid, doc):
    full = [s.get("name") for s in doc.get("existing_solutions") or [] if isinstance(s, dict) and s.get("covers") == "full" and s.get("name")]
    parts = []
    if full:
        parts.append("%s already cover%s it fully (%s)" % (_plural(len(full), "existing product"), "s" if len(full) == 1 else "",
                                                          ", ".join(full[:3]) + (" and more" if len(full) > 3 else "")))
    sent = [s for s in _sentences(doc.get("why_empty")) if len(s) >= 40]
    if sent:
        parts.append(_clip(sent[0], 190))
    if not parts:
        return "see gaps/redteam/%s.json." % gid
    return " ".join(x if x.endswith((".", "…")) else x + "." for x in parts)


def _summary(R):
    pr = R.protocol
    title = pr.get("title") or pr.get("topic") or os.path.basename(os.path.abspath(R.run))
    S = {"title": title, "question": pr.get("question") or pr.get("topic") or "", "tiles": [], "sections": []}
    cards = R.cards()
    checks = ((R.json("gaps", "card-check.json") or {}).get("cards")) or {}
    rt = R.redteam()
    rk = R.json("gaps", "ranking.json") or {}
    ranked = [x for x in rk.get("ranked") or [] if x.get("gap_id")]
    cert = ((R.json("gaps", "certainty.json") or {}).get("gaps")) or {}
    sizing = ((R.json("gaps", "sizing.json") or {}).get("gaps")) or {}
    amb = _num((pr.get("ambition") or {}).get("min_arr_usd"))
    status = {}
    for c in cards:
        status[c.get("status")] = status.get(c.get("status"), 0) + 1
    by_id = dict((c["gap_id"], c) for c in cards)
    prisma = R.json("output", "prisma.json") or {}
    ver = R.verified()
    sat = R.json("landscape", "saturation.json") or {}
    # tiles
    if cards:
        S["tiles"].append(("Gap ideas that made the ranking", "%d of %d" % (len(ranked), len(cards)), None if ranked else "critical"))
        S["tiles"].append(("Killed by the red team", _int(status.get("killed", 0)), None))
        S["tiles"].append(("Too little evidence", _int(status.get("insufficient", 0)), None))
    if ver:
        S["tiles"].append(("Verified quotes", _int(len(ver)), None))
    iv = (prisma.get("landscape") or {}).get("included_verified")
    if iv is not None:
        S["tiles"].append(("Products and sites mapped", _int(iv), None))
    if sat.get("verdict"):
        S["tiles"].append(("Landscape search", SAT_VERDICT.get(sat["verdict"], (sat["verdict"],))[0],
                           "good" if sat["verdict"] == "SATURATED" else "warning"))
    # verdict
    lines = []
    if not cards:
        lines.append("No gap cards yet (gaps/cards.jsonl is missing), so there is no verdict.")
    elif not ranked:
        lines.append("**No gap idea survived.** Of %s, %d were killed by the red team and %d had too little evidence." % (
            _plural(len(cards), "gap card"), status.get("killed", 0), status.get("insufficient", 0)))
    else:
        lines.append("**%s of %s made the final ranking.** %d were killed by the red team and %d had too little evidence." % (
            _int(len(ranked)), _plural(len(cards), "gap idea"), status.get("killed", 0), status.get("insufficient", 0)))
        for x in ranked[:3]:
            gid = x["gap_id"]
            c = cert.get(gid) or x.get("certainty") or {}
            rv = (rt.get(gid) or {}).get("verdict")
            bits = ["**#%s %s: %s.**" % (x.get("rank", "?"), gid, x.get("title") or (by_id.get(gid) or {}).get("title", ""))]
            if rv:
                why = [s for s in _sentences((rt.get(gid) or {}).get("why_empty")) if len(s) >= 40]
                bits.append("Red team: %s%s." % (rv, (" (“%s”)" % _clip(why[0], 140).rstrip(".")) if why else ""))
            if c:
                bits.append("Evidence certainty: pain %s, demand %s; demand strength %s." % (c.get("pain", "?"), c.get("demand", "?"),
                                                                                         c.get("demand_strength", "?")))
            if _num(x.get("total")) is not None:
                if len(ranked) <= 3:
                    # With three or fewer ranked gaps every gap is "top 3" under any weighting: p_top3 says nothing.
                    rank_note = " (the only %s ranked, so the weighting test cannot separate it from others)" % _plural(len(ranked), "gap") \
                        if len(ranked) > 1 else " (the only ranked gap, so the weighting test cannot separate it from others)"
                else:
                    rank_note = (", in the top 3 under %s of alternative weightings" % _pct(x["p_top3"])) if _num(x.get("p_top3")) is not None else ""
                bits.append("Desk score %.1f of 100%s." % (float(x["total"]), rank_note))
            u = (sizing.get(gid) or {}).get("usd_per_year") or {}
            lo, base, hi = [_num((u.get(k) or {}).get("som")) for k in ("low", "base", "high")]
            if base is not None:
                s = "Obtainable revenue: %s a year in the base case (low %s, high %s)" % (
                    _money_full(base, "$"), _money_full(lo, "$") if lo is not None else "?", _money_full(hi, "$") if hi is not None else "?")
                if amb:
                    s += ", %s your ambition of %s a year" % ("above" if base >= amb else "below", _money_full(amb, "$"))
                bits.append(s + ".")
            lines.append(" ".join(bits))
    S["sections"].append(("Verdict", lines))
    # killed
    killed = [c for c in cards if c.get("status") == "killed"]
    if killed:
        S["sections"].append(("Killed by the red team, and why", ["**%s %s**: %s" % (
            c["gap_id"], c.get("title", ""), _kill_reason(c["gap_id"], rt.get(c["gap_id"]) or {})) for c in killed]))
    # near misses
    ins = [c for c in cards if c.get("status") == "insufficient"]
    if ins:
        ins.sort(key=lambda c: (len((checks.get(c["gap_id"]) or {}).get("reasons") or ["?"] * 9),
                                -((checks.get(c["gap_id"]) or {}).get("numbers") or {}).get("records", 0), c["gap_id"]))
        close = [c for c in ins if len((checks.get(c["gap_id"]) or {}).get("reasons") or []) == 1][:5]
        lines = ["**%s %s**: %s." % (c["gap_id"], c.get("title", ""), _shortfall(((checks.get(c["gap_id"]) or {}).get("reasons") or [""])[0]))
                 for c in close]
        rest = [c for c in ins if c not in close]
        if rest:
            lines.append("%s fell short on several checks: %s." % (_plural(len(rest), "more idea"), ", ".join(c["gap_id"] for c in rest)))
        S["sections"].append(("Near misses (too little evidence)", lines))
    # next experiment
    ho = R.json("output", "handoff.json") or {}
    opps = [o for o in ho.get("opportunities") or [] if isinstance(o, dict)]
    exps = [(o, e) for o in opps for e in o.get("experiments") or [] if isinstance(e, dict)]
    if exps:
        o, e = exps[0]
        lines = ["**%s (%s) for %s**: %s" % (e.get("id", "EXP"), str(e.get("type", "experiment")).replace("-", " "), o.get("gap_id", "?"),
                                              e.get("hypothesis_xyz") or e.get("metric") or "")]
        kc = [k for k in o.get("kill_criteria") or [] if isinstance(k, str)]
        if kc:
            lines.append("Stop if: %s." % "; ".join(kc[:2]).rstrip("."))
        S["sections"].append(("Next recommended experiment", lines))
    elif cards:
        S["sections"].append(("Next recommended experiment", ["No handoff yet (output/handoff.json is missing)."]))
    # caveats
    lines = []
    ov = sat.get("overall") or {}
    if sat.get("verdict") and ov.get("S_obs") is not None:
        ch = ov.get("chao2") or {}
        s = "Landscape search: %s. It found at least %s products in its sampled searches" % (
            SAT_VERDICT.get(sat["verdict"], (sat["verdict"],))[0].lower() + " (%s)" % sat["verdict"], _int(ov["S_obs"]))
        if _num(ch.get("estimate")) is not None:
            s += "; about %s are estimated to exist (95%% range %s to %s)" % (_int(ch["estimate"]), _int(ch.get("ci_low", 0)),
                                                                            _int(ch.get("ci_high", 0)))
        if _num(ov.get("completeness")) is not None and _num(ov.get("coverage")) is not None:
            s += ", so the search is roughly %s complete (coverage %s)" % (_pct(ov["completeness"]), _pct(ov["coverage"]))
        lines.append(s + ". All such counts are lower bounds.")
    tg = []
    for key in ("landscape.completeness_target_theta", "landscape.coverage_target"):
        cur, dflt = _num(R.c.get(key)), _num(R.default(key))
        if cur is not None and dflt is not None and abs(cur - dflt) > 1e-9:
            tg.append("%s from %s to %s" % (key.split(".")[1].replace("_target_theta", "").replace("_target", ""), _pct(dflt), _pct(cur)))
    if tg:
        lines.append("Saturation targets were lowered by protocol amendment: %s." % ", ".join(tg))
    lock = R.json("protocol.lock.json") or {}
    if lock.get("amendments"):
        lines.append("The protocol was amended %s after it was frozen." % _plural(len(lock["amendments"]), "time"))
    gaps_log = R.jsonl("coverage-gaps.jsonl")
    if gaps_log:
        snaps = sum(1 for g in gaps_log if g.get("source") == "snapshot")
        unavail = [x for x in (ho.get("sources") or {}).get("unavailable") or [] if isinstance(x, str)]
        s = "%s logged" % _plural(len(gaps_log), "coverage gap")
        if snaps:
            s += " (%s pages could not be saved)" % _int(snaps)
        if unavail:
            s += "; unavailable sources: %s" % "; ".join(unavail[:4])
        lines.append(s + ".")
    agr = R.json("coding", "agreement.json") or {}
    if agr.get("verdict"):
        pv = agr.get("provisional_codes") or []
        lines.append("Coding agreement: %s%s." % (agr["verdict"], (" (%s only tentatively reliable)" % _plural(len(pv), "code")) if pv else ""))
    if ver:
        doms = {}
        for r in ver:
            doms[r.get("domain")] = doms.get(r.get("domain"), 0) + 1
        top2 = sorted(doms.values(), reverse=True)[:2]
        share = sum(top2) / float(len(ver))
        lines.append("The two largest websites supply %s of the %s verified quotes%s." % (
            _pct(share), _int(len(ver)), " (concentration flag: above 60%)" if share > 0.6 else ""))
    note = rk.get("note") or next((v.get("note") for v in cert.values() if isinstance(v, dict) and v.get("note")), None)
    if note:
        lines.append(note)
    if lines:
        S["sections"].append(("Caveats", lines))
    return S


def _md(S, charts, dash_rel):
    out_ = ["# %s: results at a glance" % S["title"], ""]
    if S["question"]:
        out_ += ["**Question.** %s" % S["question"], ""]
    if S["tiles"]:
        out_ += [" | ".join("%s: **%s**" % (lab, val) for lab, val, _ in S["tiles"]), ""]
    for head, lines in S["sections"]:
        out_ += ["## %s" % head, ""] + ["- " + ln for ln in lines] + [""]
    made = [c for c in charts if c.get("file")]
    out_ += ["## Charts", "", "%s charts in `%s` (open `index.html` for all of them on one page)%s." % (
        _int(len(made)), dash_rel, ("; %d skipped for missing inputs" % (len(charts) - len(made))) if len(made) < len(charts) else "")]
    return "\n".join(out_) + "\n"


# ---------------------------------------------------------------- HTML
CSS = """
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6d68;
--line:rgba(11,11,11,.10);--grid:#e1e0d9;--good:#0ca30c;--good-ink:#006300;--warn:#fab219;--crit:#d03b3b;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;
--ink:#ffffff;--ink2:#c3c2b7;--muted:#9b9991;--line:rgba(255,255,255,.10);--grid:#2c2c2a;--good-ink:#0ca30c;--accent:#3987e5}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;--muted:#9b9991;
--line:rgba(255,255,255,.10);--grid:#2c2c2a;--good-ink:#0ca30c;--accent:#3987e5}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:1.75rem;line-height:1.2;margin:0 0 6px}
h2{font-size:1.25rem;margin:40px 0 12px}
h3{font-size:1rem;margin:20px 0 6px}
p,li{color:var(--ink2)}
strong{color:var(--ink)}
.q{max-width:72ch;margin:0 0 18px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin:0 0 18px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:0 0 18px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.tile .l{font-size:.82rem;color:var(--muted)}
.tile .v{font-size:1.6rem;font-weight:600;line-height:1.25;color:var(--ink)}
.tile .s{display:inline-block;width:.6rem;height:.6rem;border-radius:50%;margin-right:.4rem;vertical-align:middle}
.exec ul{margin:4px 0 0;padding-left:1.15rem}
.exec li{margin:0 0 6px;max-width:95ch}
.exec h3:first-child{margin-top:0}
figure{margin:0}
figure img{display:block;width:100%;height:auto;border-radius:8px}
details{margin-top:10px;font-size:.9rem}
summary{cursor:pointer;color:var(--accent)}
.tw{overflow-x:auto;margin-top:8px}
table{border-collapse:collapse;font-size:.85rem;min-width:100%}
th,td{text-align:left;padding:4px 10px;border-bottom:1px solid var(--grid);vertical-align:top;font-variant-numeric:tabular-nums}
th{color:var(--ink);font-weight:600}
td{color:var(--ink2)}
nav{font-size:.9rem;color:var(--muted);margin:0 0 8px}
nav a{color:var(--accent);margin-right:14px;text-decoration:none}
.skip li{color:var(--muted)}
footer{margin-top:40px;font-size:.82rem;color:var(--muted)}
"""


def _inline(text):
    t = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)


def _html(S, charts, run, generated, sections=None):
    sections = sections or SECTIONS
    tone = {"good": "var(--good)", "warning": "var(--warn)", "critical": "var(--crit)"}
    h = ["<!doctype html>", "<html lang=\"en\">", "<head>", "<meta charset=\"utf-8\">",
         "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
         "<title>%s</title>" % html.escape("%s: results" % S["title"]), "<style>%s</style>" % CSS, "</head>", "<body>", "<main>"]
    h.append("<h1>%s</h1>" % html.escape(S["title"]))
    if S["question"]:
        h.append("<p class=\"q\"><strong>Question.</strong> %s</p>" % html.escape(S["question"]))
    if S["tiles"]:
        h.append("<div class=\"tiles\">")
        for lab, val, tn in S["tiles"]:
            dot = ("<span class=\"s\" style=\"background:%s\" aria-hidden=\"true\"></span>" % tone[tn]) if tn in tone else ""
            h.append("<div class=\"tile\"><div class=\"l\">%s</div><div class=\"v\">%s%s</div></div>" % (
                html.escape(lab), dot, html.escape(str(val))))
        h.append("</div>")
    h.append("<section class=\"card exec\" aria-label=\"Executive summary\">")
    for head, lines in S["sections"]:
        h.append("<h3>%s</h3><ul>%s</ul>" % (html.escape(head), "".join("<li>%s</li>" % _inline(ln) for ln in lines)))
    h.append("</section>")
    by = dict((c["id"], c) for c in charts)
    nav = [(name, "s%d" % i) for i, (name, ids) in enumerate(sections) if any(by.get(x, {}).get("png") for x in ids)]
    if nav:
        h.append("<nav>%s</nav>" % "".join("<a href=\"#%s\">%s</a>" % (a, html.escape(n)) for n, a in nav))
    for i, (name, ids) in enumerate(sections):
        made = [by[x] for x in ids if by.get(x, {}).get("png")]
        if not made:
            continue
        h.append("<h2 id=\"s%d\">%s</h2>" % (i, html.escape(name)))
        for c in made:
            alt = html.escape("%s. %s" % (c["chart_title"], c["subtitle"]), quote=True)
            dark = ("<source media=\"(prefers-color-scheme: dark)\" srcset=\"data:image/png;base64,%s\">" % c["png_dark"]) if c.get("png_dark") else ""
            h.append("<section class=\"card\" id=\"c%s\"><figure><picture>%s<img src=\"data:image/png;base64,%s\" alt=\"%s\" "
                     "width=\"%d\" height=\"%d\"></picture></figure>" % (c["id"], dark, c["png"], alt, c["w"], c["h"]))
            cols, rows = c.get("table") or ([], [])
            if rows:
                h.append("<details><summary>Data table (%s)</summary><div class=\"tw\"><table><thead><tr>%s</tr></thead><tbody>%s"
                         "</tbody></table></div></details>" % (
                             _plural(len(rows), "row"), "".join("<th>%s</th>" % html.escape(str(x)) for x in cols),
                             "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % html.escape(str(v)) for v in r) for r in rows[:400])))
            h.append("</section>")
    skipped = [c for c in charts if c.get("skipped_reason")]
    if skipped:
        h.append("<h2>Charts not drawn</h2><ul class=\"skip\">%s</ul>" % "".join(
            "<li><strong>%s</strong>: %s</li>" % (html.escape(c["title"]), html.escape(c["skipped_reason"])) for c in skipped))
    h.append("<footer>Generated %s from the run folder %s. Every number is read or counted from the run's files; "
             "the full method and quotes are in %s.</footer>" % (html.escape(generated), html.escape(os.path.basename(os.path.abspath(run))), html.escape(S.get("detail") or "output/dossier.md")))
    h += ["</main>", "</body>", "</html>"]
    return "\n".join(h) + "\n"


# ---------------------------------------------------------------- build
class _Mpl(object):
    """The matplotlib pieces build() needs, imported lazily."""


def _load_mpl(run):
    if not os.environ.get("MPLCONFIGDIR"):  # sandboxes often have no writable home for matplotlib's cache
        d = p(run, "cache", "mpl")
        try:
            os.makedirs(d, exist_ok=True)
            os.environ["MPLCONFIGDIR"] = os.path.abspath(d)
        except OSError:
            pass
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import dates, font_manager, lines, patches, ticker
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        import numpy  # ships with matplotlib; used only for the square-root axis transform
    except ImportError:
        raise CliError("the viz step needs matplotlib: pip install matplotlib (core gapscan commands stay stdlib-only)")
    m = _Mpl()
    m.mpl, m.Figure, m.FigureCanvasAgg = matplotlib, Figure, FigureCanvasAgg
    m.mdates, m.ticker, m.patches, m.lines, m.font_manager = dates, ticker, patches, lines, font_manager
    m.np = numpy
    return m


def _fonts(m):
    have = set(f.name for f in m.font_manager.fontManager.ttflist)
    fam = [f for f in ("Arial", "Helvetica", "Liberation Sans", "Noto Sans") if f in have][:1]
    return fam + ["DejaVu Sans"]


def _rel(run, path):
    a, b = os.path.abspath(path), os.path.abspath(run)
    return os.path.relpath(a, b) if a.startswith(b + os.sep) else a


def build(run, out_dir=None):
    """Draw every chart the run's files support, then write the HTML dashboard, summary.md and a manifest.

    Default layout: RUN/output/dashboard/{NN-slug.png, index.html, manifest.json} and RUN/output/summary.md.
    With out_dir, everything (summary.md included) goes into out_dir; the run folder then only gains the
    matplotlib cache (RUN/cache/mpl) when MPLCONFIGDIR is unset."""
    if not os.path.isdir(run):
        raise CliError("%s is not a folder" % run)
    m = _load_mpl(run)
    R = _Run(run)
    dash = out_dir or p(run, "output", "dashboard")
    sum_path = os.path.join(out_dir, "summary.md") if out_dir else p(run, "output", "summary.md")
    os.makedirs(dash, exist_ok=True)
    rc = {"font.family": _fonts(m), "font.size": 10, "axes.unicode_minus": False, "svg.fonttype": "none",
          "path.simplify": True, "figure.max_open_warning": 0}
    if "text.parse_math" in m.mpl.rcParams:
        rc["text.parse_math"] = False  # dollar amounts are text, not mathtext
    else:
        global _DOLLAR
        _DOLLAR = "\\$"
    from . import viz_opps  # opportunity charts (D26-D28); imported here to avoid a cycle
    chart_list, sections = viz_opps.charts_for(R)
    charts = []
    with m.mpl.rc_context(rc):
        for num, slug, title, fn in chart_list:
            path = os.path.join(dash, "%s-%s.png" % (num, slug))
            entry = {"id": num, "file": None, "title": title}
            try:
                res = fn(R, LIGHT, m)
                png = res["frame"].png()
                with open(path, "wb") as fh:
                    fh.write(png)
                dark = fn(R, DARK, m)["frame"].png()
                fig = res["frame"].fig
                entry.update(file=_rel(run, path), subtitle=res["frame"].subtitle, chart_title=res["frame"].title,
                             sources=res["frame"].sources, table=res.get("table"),
                             png=base64.b64encode(png).decode("ascii"), png_dark=base64.b64encode(dark).decode("ascii"),
                             w=int(fig.get_figwidth() * DPI), h=int(fig.get_figheight() * DPI))
            except _Skip as exc:
                entry["skipped_reason"] = str(exc)
            except Exception as exc:  # one malformed input must not stop the other charts
                entry["skipped_reason"] = "could not draw (%s: %s)" % (type(exc).__name__, _clip(exc, 160))
            if entry.get("skipped_reason") and os.path.exists(path):
                os.remove(path)
            charts.append(entry)
    S = viz_opps.summary_scan(R) if sections else _summary(R)
    generated = now_iso()
    html_path = os.path.join(dash, "index.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(_html(S, charts, run, generated, sections or DEEP_SECTIONS))
    with open(sum_path, "w", encoding="utf-8") as fh:
        fh.write(_md(S, charts, _rel(run, dash)))
    keep = ("id", "file", "title", "subtitle", "sources", "skipped_reason")
    manifest = {"generated_at": generated, "charts": [dict((k, c[k]) for k in keep if k in c) for c in charts],
                "html": _rel(run, html_path), "summary": _rel(run, sum_path)}
    write_json(os.path.join(dash, "manifest.json"), manifest)
    return manifest


def cmd_viz(args):
    run = args.run
    man = build(run, getattr(args, "out", None))

    def show(x):
        return x if os.path.isabs(x) else p(run, x)
    for c in man["charts"]:
        if c.get("skipped_reason"):
            out("skipped  %s: %s" % (c["title"], c["skipped_reason"]))
        else:
            out("chart    %s  (%s)" % (show(c["file"]), c["title"]))
    out("dashboard  %s" % show(man["html"]))
    out("summary    %s" % show(man["summary"]))
    return 0
