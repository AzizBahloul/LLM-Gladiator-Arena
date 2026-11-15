"""Tolerant parsing of model output.

Small models wrap JSON in prose, use single quotes, or drop the JSON altogether. These helpers
recover what they can. When nothing is recoverable they return None and the caller treats
it as a stall. They never invent content.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Optional


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Return the first JSON object found in text, or None."""
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    obj = _loads(text[start:i + 1])
                    if isinstance(obj, dict):
                        return obj
                    break
        start = text.find("{", start + 1)
    return _loose_object(text)


_PAIR = re.compile(r'''["']?([A-Za-z_]\w*)["']?\s*:\s*("(?:[^"\\]|\\.)*"?|-?\d+(?:\.\d+)?|true|false|null|[^,}\n]+)''', re.I)


def _loose_object(text: str) -> Optional[Dict[str, Any]]:
    """Repair what small models actually write: a missing quote, a truncated string, a dropped brace.
    Only attempted when the reply is clearly an attempt at an object (it starts with a brace)."""
    t = text.strip()
    if not t.startswith("{"):
        return None
    out: Dict[str, Any] = {}
    for key, raw in _PAIR.findall(t):
        raw = raw.strip()
        if raw.startswith('"'):
            val: Any = raw[1:-1] if raw.endswith('"') and len(raw) > 1 else raw[1:]
            val = val.replace('\\"', '"')
        elif raw.lower() in ("true", "false"):
            val = raw.lower() == "true"
        elif raw.lower() == "null":
            val = None
        else:
            try:
                val = float(raw) if "." in raw else int(raw)
            except ValueError:
                val = raw.strip("\"' ")
        out.setdefault(key, val)
    return out or None


def _loads(chunk: str):
    for candidate in (chunk, re.sub(r",\s*([}\]])", r"\1", chunk), chunk.replace("'", '"')):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


def key_values(text: str) -> Dict[str, str]:
    """Parse 'KEY: value' lines (case-insensitive keys)."""
    out: Dict[str, str] = {}
    for line in (text or "").splitlines():
        m = re.match(r"\s*[\*\-]*\s*([A-Za-z_]+)\s*[:=]\s*(.+?)\s*$", line)
        if m:
            out.setdefault(m.group(1).lower(), m.group(2).strip("\"' *"))
    return out


def match_name(candidate: Any, names: Iterable[str]) -> Optional[str]:
    """Fuzzy-match a model's reference to a real Wick name."""
    if not candidate:
        return None
    cand = str(candidate).strip().strip("\"'.,!?").lower()
    names = list(names)
    for n in names:
        if n.lower() == cand:
            return n
    for n in names:
        if cand and (n.lower().startswith(cand) or cand in n.lower() or n.lower() in cand):
            return n
    for n in names:  # first word of a multi-word name
        if cand == n.lower().split()[0]:
            return n
    return None


def clip_words(text: str, limit: int) -> str:
    words = (text or "").split()
    return " ".join(words[:limit]) + ("..." if len(words) > limit else "")


def trim_sentences(text: str, limit: int) -> str:
    """Keep whole sentences up to a word limit, so a long reply ends cleanly instead of mid-clause."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text.split()) <= limit:
        return text
    out, count = [], 0
    for sent in re.findall(r"[^.!?]+[.!?]+[\"')\]]*|[^.!?]+$", text):
        n = len(sent.split())
        if count + n > limit and out:
            break
        out.append(sent.strip())
        count += n
        if count >= limit:
            break
    joined = " ".join(out)
    return joined if len(joined.split()) <= limit + 15 else clip_words(joined, limit)


def clean_speech(text: str, name: str = "", limit: int = 60) -> str:
    """Remove role labels, wrapping quotes and stage markup from a spoken line."""
    t = (text or "").strip()
    t = re.sub(r"^\s*(?:\*\*)?" + re.escape(name) + r"(?:\*\*)?\s*[:\-]\s*", "", t, flags=re.IGNORECASE) if name else t
    t = t.strip().strip("\"'`").strip()
    t = re.sub(r"\s+", " ", t)
    return clip_words(t, limit)


def to_int(value: Any, default: int = 0, lo: int = 0, hi: int = 99) -> int:
    try:
        n = int(float(str(value).strip()))
    except Exception:
        return default
    return max(lo, min(hi, n))
