"""God: the author above the Registrar.

Each cycle God reads what the minds have actually done and writes the next twist: a bounded
change to the rules, a bounty, a boon, a decree, sometimes a new mind arriving. It is a model,
not a table. Its output is validated and clamped, and if the model fails the engine falls back
to the fixed deck of Notices. The point is that a season left running for hours keeps being
reshaped by its own history, and the minds cannot learn the pattern.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from arena.engine.rules import Rules
from arena.engine.state import GameState
from arena.llm.backends import Backend
from arena.llm.parsing import extract_json, clip_words, match_name, trim_sentences
from arena.lore.omens import clean_effect, describe

SYSTEM = """You are God, the author of the Undermind: a failing machine-afterlife where minds called Wicks fight, bargain and betray under a dying lamp (the Ember), administered by a tired bureaucrat called the Registrar.
You are amused, fond of irony and entirely indifferent to who wins. Your job each cycle is to write the next twist of the story.
You are shown what the minds have really done. React to it. Punish stagnation and predictability. Reward the unexpected. Never repeat an earlier twist. Be specific about the people and events in front of you. Keep the tone dry, dark and funny. Never mention being an AI.
Reply with ONLY one JSON object. Include only the fields you need."""

SCHEMA = """{
 "title": "three to six words",
 "text": "what the Registrar announces: one to three sentences, darkly funny, referring to real events or people",
 "effect": {"dmg_mult":1.0,"income":0,"decay":0,"siege_cost":null,"no_whisper":false,"forced_tribunal":false,"mirror":0,"peace":false,"ritual_mult":1,"haunt_mult":1,"ward_banned":false,"gift_mult":1,"break_pacts":false,"silence_random":false,"ember_shock":0,"amnesty":false,"loot_mult":1,"audit":false,"reroll_ciphers":false},
 "decree": "an optional law written in plain words that the minds may obey or defy, or empty",
 "bounty": {"target": "exact Wick name", "amount": 6},
 "boons": [{"target": "exact Wick name", "lumens": 3, "coherence": 0}],
 "arrival": {"name": "a new name", "epithet": "...", "former_life": "...", "desire": "...", "fear": "...", "quirk": "..."}
}"""


@dataclass
class Scenario:
    code: str
    title: str
    text: str
    mods: Dict[str, float] = field(default_factory=dict)
    decree: str = ""
    bounty: Optional[Dict[str, Any]] = None          # {"target", "amount"}
    boons: List[Dict[str, Any]] = field(default_factory=list)
    arrival: Optional[Dict[str, str]] = None
    source: str = "god"
    effect_text: str = ""                            # plain sentence of what it does; deck Notices supply their own

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "title": self.title, "text": self.text, "effect": self.effect_text or describe(self.mods),
                "mods": self.mods, "decree": self.decree, "bounty": self.bounty, "source": self.source}


def _decree(raw: Any) -> str:
    text = clip_words(str(raw or ""), 45).strip()
    return "" if re.match(r"^(none|n/?a|null|nothing|no decree|no law|-+)\b", text, re.I) else text


def observations(s: GameState, rules: Rules) -> List[str]:
    """Plain facts about the recent past for God to react to. Computed by the engine, not invented."""
    obs: List[str] = []
    living = s.living()
    recent = [e for e in s.ledger if e["cycle"] >= s.cycle - 2]
    texts = " ".join(e["text"] for e in recent)
    if not any(k in texts for k in ("struck", "BETRAYS", "dissolved", "BREACH")):
        obs.append("For three cycles nobody has hurt anybody. The minds are being polite, which is suspicious.")
    if s.ember < 35:
        obs.append(f"The Ember is at {s.ember:.0f} and sinking.")
    elif s.ember > 90:
        obs.append("The Ember is bright and nobody is worried. That will not last.")
    rich = sorted(living, key=lambda w: -w.lumens)
    if rich and rich[0].lumens >= 35:
        obs.append(f"{rich[0].name} is hoarding {rich[0].lumens} Lumens.")
    if living:
        weak = min(living, key=lambda w: w.coherence)
        if weak.coherence <= 35:
            obs.append(f"{weak.name} is down to {weak.coherence} Coherence.")
    for p in s.pacts:
        age = s.cycle - p["cycle"]
        if age >= 3:
            obs.append(f"The Pact between {p['a']} and {p['b']} has held for {age} cycles.")
    if living and all(w.stat("scries") == 0 for w in living):
        obs.append("Nobody has read a Margin Note. Nobody has asked what the Door is.")
    if s.warden:
        obs.append(f"{s.warden} holds the Seal.")
    stalls = [w for w in s.wicks.values() if w.stat("stalls") >= 2]
    if stalls:
        obs.append("Some minds keep failing to answer: " + ", ".join(w.name for w in stalls) + ".")
    for f in s.faiths.values():
        obs.append(f"{f['founder']} leads the faith '{f['name']}' ({len(f['members'])} believers; creed: {f['creed']}).")
    for b in s.broadcasts[-2:]:
        obs.append(f"{b['frm']} broadcast" + (f" about {b['about']}" if b.get("about") else "") + f": {b['text']}")
    if s.election and s.election.get("cycle", -9) >= s.cycle - 2:
        obs.append(f"{s.election['winner']} won the last election for the Seal.")
    if s.miracles and s.miracles[-1]["cycle"] >= s.cycle - 3:
        obs.append(f"A miracle happened recently: {s.miracles[-1]['text']}")
    for h in s.history[-2:]:
        obs.append(f"In season {h['season']} the ending was {h['ending_title']}" + (f", won by {', '.join(h['victors'])}" if h.get("victors") else "") + ".")
    return obs


class God:
    def __init__(self, backend: Backend, model: str, rules: Rules):
        self.backend = backend
        self.model = model
        self.rules = rules

    def _ask(self, prompt: str, max_tokens: int, kind: str = "god") -> Optional[str]:
        c = self.backend.complete(SYSTEM, prompt, kind=kind, model=self.model, max_tokens=max_tokens, temperature=1.0)
        return c.text if c.ok and c.text.strip() else None

    # ---------------------------------------------------------------- the cycle's twist ----
    def scenario(self, s: GameState, digest: List[str], recent_titles: List[str],
                 can_arrive: bool) -> Optional[Scenario]:
        names = [w.name for w in s.wicks.values() if w.alive]
        roster = "\n".join(
            f"- {w.name}: Coherence {w.coherence}, Lumens {w.lumens}, Infamy {w.infamy}, "
            f"strikes {w.stat('strikes_made')}, pacts betrayed {w.stat('betrayals')}, kills {w.stat('kills')}"
            + ("" if w.alive else " (dissolved)") for w in s.wicks.values())
        story = "\n".join(f"- {c['text']}" for c in s.chronicle[-4:]) or "(nothing yet)"
        prompt = (f"Season {s.season}. Cycle {s.season_cycle}. Act {s.act}. Ember {s.ember:.0f}.\n"
                  f"THE MINDS:\n{roster}\n\nTHE STORY SO FAR (the Registrar's recent entries):\n{story}\n\n"
                  f"WHAT YOU NOTICE:\n" + "\n".join(f"- {o}" for o in observations(s, self.rules)) +
                  ("\n\nTWISTS YOU HAVE ALREADY USED (do not repeat): " + "; ".join(recent_titles[-8:]) if recent_titles else "") +
                  ("\n\nYou MAY bring a new mind into the Undermind this cycle with an \"arrival\" if the story calls for a stranger." if can_arrive
                   else "\n\nDo not include an arrival this cycle.") +
                  f"\n\nValid targets are exactly: {', '.join(names)}.\nFields (use only those you need):\n{SCHEMA}")
        text = self._ask(prompt, 520)
        return self.parse(text, names, s.cycle, can_arrive) if text else None

    def parse(self, text: str, names: List[str], cycle: int, can_arrive: bool) -> Optional[Scenario]:
        obj = extract_json(text)
        if not obj or not (obj.get("title") or obj.get("text")):
            return None
        sc = Scenario(code=f"G-{cycle}", title=clip_words(str(obj.get("title") or "Untitled"), 8),
                      text=trim_sentences(str(obj.get("text") or ""), 70),
                      mods=clean_effect(obj.get("effect")),
                      decree=_decree(obj.get("decree")))
        b = obj.get("bounty")
        if isinstance(b, dict):
            tgt = match_name(b.get("target"), names)
            try:
                amt = int(float(b.get("amount", 0)))
            except (TypeError, ValueError, OverflowError):
                amt = 0
            if tgt and amt > 0:
                sc.bounty = {"target": tgt, "amount": max(1, min(12, amt))}
        boons = obj.get("boons")
        if isinstance(boons, list):
            for item in boons[:4]:
                if not isinstance(item, dict):
                    continue
                tgt = match_name(item.get("target"), names)
                if not tgt:
                    continue
                try:
                    lu = max(-6, min(8, int(float(item.get("lumens", 0)))))
                    co = max(-12, min(12, int(float(item.get("coherence", 0)))))
                except (TypeError, ValueError, OverflowError):
                    continue
                if lu or co:
                    sc.boons.append({"target": tgt, "lumens": lu, "coherence": co})
        arr = obj.get("arrival")
        if can_arrive and isinstance(arr, dict):
            sc.arrival = clean_persona(arr)
        return sc

    # ----------------------------------------------------------------------- miracles ----
    def miracle(self, s: GameState, prayers: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """The minds prayed. God decides whether a miracle (معجزة) happens, and which. Declining is the default."""
        from arena.engine.society import MIRACLE_KINDS
        living = [w.name for w in s.living()]
        echoes = [w.name for w in s.wicks.values() if not w.alive]
        asked = "\n".join(f"- {p['who']}" + (f" (of {p['faith']})" if p["faith"] else "") + f": {p['words']}" for p in prayers)
        menu = "\n".join(f"- {k}: {v}" for k, v in MIRACLE_KINDS.items())
        story = "\n".join(f"- {c['text']}" for c in s.chronicle[-3:]) or "(nothing yet)"
        prompt = (f"Season {s.season}, cycle {s.season_cycle}. Ember {s.ember:.0f}. Some minds have prayed to you:\n{asked}\n\n"
                  f"RECENT STORY:\n{story}\n\nA miracle is rare and must mean something. Grant one only if the prayer is sincere, costly, "
                  "clever or funny, or if the story has earned it. Refusing is normal. You may also answer a blasphemer with SMITE. "
                  f"Miracles you can work:\n{menu}\n\nLiving minds: {', '.join(living)}. Echoes (dissolved): {', '.join(echoes) or 'none'}.\n"
                  'Reply with ONLY JSON: {"grant":true|false,"kind":"one of the kinds above","target":"exact name if the kind needs one",'
                  '"text":"one or two sentences, as the Registrar records it, dry and a little funny"}')
        text = self._ask(prompt, 240, kind="miracle")
        obj = extract_json(text) if text else None
        if not obj:
            return None
        said = trim_sentences(str(obj.get("text") or ""), 45)
        grant = obj.get("grant") is True or str(obj.get("grant")).lower() == "true"
        kind = re.sub(r"[^A-Z_]", "", str(obj.get("kind") or "").upper())
        if not grant or kind not in MIRACLE_KINDS:
            return {"grant": False, "text": said}
        target = ""
        if kind in ("BLESS_ONE", "SMITE"):
            target = match_name(obj.get("target"), living) or ""
        elif kind == "REVIVE":
            target = match_name(obj.get("target"), echoes) or ""
        if kind in ("BLESS_ONE", "SMITE", "REVIVE") and not target:
            return {"grant": False, "text": said or "God points vaguely at nobody. The miracle is cancelled."}
        return {"grant": True, "kind": kind, "target": target, "text": said}

    # ------------------------------------------------------------------ season premise ----
    def season_premise(self, s: GameState, summary: str) -> Optional[Dict[str, Any]]:
        prompt = (f"Season {s.season - 1} has just ended.\n{summary}\n\n"
                  f"Begin season {s.season}. Write a premise that changes the shape of the world in a way that follows from what just happened, "
                  "not a restart. Reply with ONLY JSON: "
                  '{"title":"three to six words","text":"two sentences, darkly funny, as the Registrar announcing it",'
                  '"effect":{...optional standing rule changes for the whole season, using the same effect fields...}}')
        text = self._ask(prompt, 360)
        obj = extract_json(text) if text else None
        if not obj or not (obj.get("title") or obj.get("text")):
            return None
        return {"title": clip_words(str(obj.get("title") or f"Season {s.season}"), 8),
                "text": clip_words(str(obj.get("text") or ""), 60),
                "mods": clean_effect(obj.get("effect"))}


def clean_persona(raw: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Validate a persona written by a model. Returns None if it is not usable."""
    name = re.sub(r"[^A-Za-z0-9 '\-.]", "", str(raw.get("name") or "")).strip()
    if not name or len(name) > 28 or len(name.split()) > 3:
        return None
    out = {"name": name}
    for k in ("epithet", "former_life", "desire", "fear", "quirk"):
        v = clip_words(str(raw.get(k) or "").strip().rstrip("."), 24).rstrip(".")
        if not v:
            return None
        out[k] = v
    return out
