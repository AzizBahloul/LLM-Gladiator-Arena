"""Design tokens are measured, not assumed. No emoji anywhere in the project's own files."""
import re
from pathlib import Path

from arena.ui.theme import TEXT_PAIRS, TOKENS, contrast, css_variables

ROOT = Path(__file__).resolve().parent.parent


def test_every_text_pair_is_readable():
    for fg, bg in TEXT_PAIRS:
        ratio = contrast(TOKENS[fg], TOKENS[bg])
        floor = 4.5
        assert ratio >= floor, f"{fg} on {bg} is {ratio:.2f}, below {floor}"


def test_persona_colours_are_readable_and_not_the_accent_or_danger():
    from arena.lore.personas import PERSONAS
    for p in PERSONAS.values():
        for bg in ("bg", "surface"):
            assert contrast(p.color, TOKENS[bg]) >= 4.5, f"{p.name} is hard to read on {bg}"
        assert p.color.lower() not in (TOKENS["ember"].lower(), TOKENS["danger"].lower())


def test_css_variables_cover_every_token():
    assert set(css_variables()) == {k.replace("_", "-") for k in TOKENS}


EMOJI = re.compile("[\\U0001F000-\\U0001FAFF\\u2600-\\u27BF\\u2B00-\\u2BFF\\uFE0F]")


def test_no_emoji_in_source_docs_or_config():
    offenders = []
    for pat in ("arena/**/*.py", "tests/*.py", "main.py", "README.md", "docs/*.md", "config.yaml"):
        for f in ROOT.glob(pat):
            if "catalog_data" in f.name:
                continue
            if EMOJI.search(f.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(f.relative_to(ROOT)))
    assert not offenders, offenders
