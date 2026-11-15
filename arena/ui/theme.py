"""Design tokens: the single source of truth for colour in every interface.

World: a failing archive lit by one lamp. Warm near-black surfaces and warm paper text carry
almost everything. There is exactly one accent (Ember amber, used for the Ember, the Registrar
and the Seal) and one danger tone (used only for lost Coherence and dissolution). Speaker hues
come from the personas and are used only to tell voices apart.

Every text pair here is measured in tests/test_design.py, not assumed.
"""
from __future__ import annotations

from typing import Dict

TOKENS: Dict[str, str] = {
    # surfaces
    "bg": "#14120f",          # screen
    "surface": "#1b1814",     # panels
    "raised": "#26221b",      # hover / selected / current
    "line": "#3f382c",        # hairline borders
    # text
    "text": "#ece4d3",        # warm paper
    "muted": "#a69d8a",       # secondary text
    "faint": "#8a8272",       # tertiary text, still legible
    # roles (one accent, one danger)
    "ember": "#f2a550",
    "ember_low": "#c9782a",   # gauge when the Ember is under half
    "danger": "#e8695c",
    "ok": "#9cbf8f",          # healthy Coherence bar; the only calm green, used for bars only
    # bar track
    "track": "#322d24",
}

# Foreground / background pairs that must stay readable (checked by the design test).
TEXT_PAIRS = [
    ("text", "bg"), ("text", "surface"), ("text", "raised"),
    ("muted", "bg"), ("muted", "surface"), ("muted", "raised"),
    ("faint", "bg"), ("faint", "surface"),
    ("ember", "bg"), ("ember", "surface"), ("ember", "raised"),
    ("ember_low", "surface"),
    ("danger", "bg"), ("danger", "surface"), ("danger", "raised"),
    ("ok", "surface"),
]


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def css_variables() -> Dict[str, str]:
    """Tokens in the form Textual CSS reads as $name."""
    return {k.replace("_", "-"): v for k, v in TOKENS.items()}
