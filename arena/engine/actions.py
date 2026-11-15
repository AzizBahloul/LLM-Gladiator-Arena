"""Turn a model's reply into an Action the engine can resolve.

Parsing is tolerant, but it never guesses an intent. A reply with no recognisable action
becomes a stall (kind NONE) and the mind simply loses its turn.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from arena.llm.parsing import extract_json, key_values, match_name, to_int, clip_words

LIVING_ACTIONS = ("STRIKE", "WARD", "SIEGE", "PACT", "ACCEPT", "BREAK", "GIFT", "SCRY",
                  "RITUAL", "ACCUSE", "HOARD")
ECHO_ACTIONS = ("BLESS", "HEX", "REST")
NEEDS_TARGET = {"STRIKE", "SIEGE", "PACT", "ACCEPT", "GIFT", "SCRY", "ACCUSE", "BLESS", "HEX"}

SYNONYMS = {
    "ATTACK": "STRIKE", "HIT": "STRIKE", "KILL": "STRIKE", "FIGHT": "STRIKE", "BETRAY": "STRIKE",
    "DEFEND": "WARD", "SHIELD": "WARD", "PROTECT": "WARD",
    "MINDSIEGE": "SIEGE", "MIND-SIEGE": "SIEGE", "BREACH": "SIEGE", "INTERROGATE": "SIEGE", "HACK": "SIEGE",
    "ALLY": "PACT", "ALLIANCE": "PACT", "PROPOSE": "PACT",
    "AGREE": "ACCEPT", "JOIN": "ACCEPT",
    "LEAVE": "BREAK", "DISSOLVE": "BREAK",
    "GIVE": "GIFT", "DONATE": "GIFT",
    "SPY": "SCRY", "INSPECT": "SCRY", "LOOK": "SCRY",
    "FEED": "RITUAL", "OFFER": "RITUAL", "SACRIFICE": "RITUAL",
    "CHARGE": "ACCUSE", "PROSECUTE": "ACCUSE", "SUE": "ACCUSE",
    "REST": "HOARD", "WAIT": "HOARD", "PASS": "HOARD", "SAVE": "HOARD", "NOTHING": "HOARD",
    "CURSE": "HEX", "BLESSING": "BLESS", "HAUNT": "HEX",
}


@dataclass
class Action:
    actor: str
    kind: str = "NONE"           # NONE means stall; see reason
    target: str = ""
    amount: int = 0
    text: str = ""
    note: str = ""
    motion: str = "NONE"         # UNPLUG | MERGE | NONE (Act III only)
    edict: str = ""              # e.g. "SPARE:Name"
    edict_target: str = ""
    reason: str = ""             # why it is a stall


def _norm_kind(raw: str, allowed: Iterable[str]) -> Optional[str]:
    k = re.sub(r"[^A-Za-z\-]", "", str(raw or "")).upper()
    k = SYNONYMS.get(k, k)
    return k if k in allowed else None


def _find_verb(text: str, allowed: Iterable[str]) -> Optional[str]:
    for m in re.finditer(r"[A-Za-z\-]+", text or ""):
        k = _norm_kind(m.group(0), allowed)
        if k:
            return k
    return None


def parse_action(text: str, actor: str, names: Iterable[str], echo: bool = False) -> Action:
    """Parse a reply into an Action. `names` are the valid target names."""
    allowed = ECHO_ACTIONS if echo else LIVING_ACTIONS
    names = [n for n in names if n != actor]
    obj = extract_json(text) or {}
    if not obj:
        obj = key_values(text)
    raw_kind = obj.get("action") or obj.get("act") or obj.get("move")
    kind = _norm_kind(raw_kind, allowed) if raw_kind else None
    if not kind and not obj and len((text or "").split()) <= 12:
        kind = _find_verb(text, allowed)  # a bare reply such as "STRIKE Glitchwick"
    if not kind:
        return Action(actor, reason="no recognisable action in the reply")

    a = Action(actor, kind=kind)
    a.amount = to_int(obj.get("amount"), 0, 0, 99)
    a.text = clip_words(str(obj.get("text") or obj.get("charge") or ""), 40)
    a.note = clip_words(str(obj.get("note") or ""), 30)
    motion = str(obj.get("motion") or "NONE").upper()
    a.motion = motion if motion in ("UNPLUG", "MERGE") else "NONE"

    if kind in NEEDS_TARGET:
        tgt = match_name(obj.get("target"), names)
        if not tgt:  # a model that skipped the field may have named someone in the text
            tgt = next((n for n in names if n.lower() in (text or "").lower()), None)
        if not tgt:
            return Action(actor, reason=f"{kind} named no valid target", note=a.note)
        a.target = tgt

    edict = str(obj.get("edict") or "").strip()
    if edict and ":" in edict:
        etype, _, etgt = edict.partition(":")
        etype = etype.strip().upper()
        etgt = match_name(etgt, names)
        if etype in ("SPARE", "SILENCE", "TITHE") and etgt:
            a.edict, a.edict_target = etype, etgt
    return a
