"""Verbatim quote verification against raw snapshots.

A quote counts as evidence only if, after light normalisation (Unicode NFKC, quotes/dashes,
whitespace, case, HTML entities), it appears in the snapshot text. Ellipses split a quote into
segments that must appear in order. Paraphrases fail by design.
"""

import html
import re
import unicodedata

_TRANSLATE = {
    ord("‘"): "'", ord("’"): "'", ord("‚"): "'", ord("‛"): "'",
    ord("′"): "'", ord("´"): "'", ord("`"): "'",
    ord("“"): '"', ord("”"): '"', ord("„"): '"', ord("‟"): '"',
    ord("″"): '"', ord("«"): '"', ord("»"): '"',
    ord("‐"): "-", ord("‑"): "-", ord("‒"): "-", ord("–"): "-",
    ord("—"): "-", ord("―"): "-", ord("−"): "-",
    ord(" "): " ", ord(" "): " ", ord(" "): " ",
    ord("​"): None, ord("‌"): None, ord("‍"): None, ord("﻿"): None,
}
_WS = re.compile(r"\s+")
_ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…|\[\.\.\.\]|\[…\])\s*")


def normalize(text):
    text = html.unescape(text or "")
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_TRANSLATE)
    text = text.replace("…", "...")
    text = _WS.sub(" ", text)
    return text.strip().casefold()


def verify_quote(quote, snapshot_text):
    """Return (ok, offset). Offset is the position of the first segment in normalised text."""
    t = normalize(snapshot_text)
    raw_segments = _ELLIPSIS.split(quote or "")
    segments = [normalize(s) for s in raw_segments]
    segments = [s for s in segments if s]
    if not segments:
        return False, None
    pos = 0
    first = None
    for seg in segments:
        idx = t.find(seg, pos)
        if idx < 0:
            return False, None
        if first is None:
            first = idx
        pos = idx + len(seg)
    return True, first
