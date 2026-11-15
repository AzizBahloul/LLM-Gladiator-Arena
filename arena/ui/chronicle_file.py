"""Writes the season as a readable Markdown story, one entry at a time as it happens."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from arena.engine.events import Event
from arena.ui.format import ROMAN


class ChronicleWriter:
    def __init__(self, path: str, meta: Dict[str, Any]):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "# The Undermind: Chronicle of a season\n\n"
            f"Seed {meta.get('seed')}. Minds: " + ", ".join(f"{n} ({m})" for n, m in meta.get("minds", [])) + ".\n\n"
            "Nothing below was scripted. Every word spoken by a mind, and every secret action, "
            "was chosen by the model playing it.\n\n", encoding="utf-8")

    def replay(self, events) -> None:
        """Rebuild the file from the journal after a resume, so it matches what was committed."""
        for ev in events:
            self(ev)

    def _w(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(text)

    def __call__(self, ev: Event) -> None:
        k, t = ev.kind, ev.text
        if k == "act":
            self._w(f"\n---\n\n## Act {ROMAN.get(ev.act, ev.act)}: {ev.data.get('act_title', '')}\n\n*{t.split('. ', 1)[-1]}*\n\n")
        elif k == "cycle":
            self._w(f"\n### {t}\n\n")
        elif k == "notice" and ev.data.get("omen"):
            extra = (f" Decree: {ev.data['decree']}" if ev.data.get("decree") else "")
            self._w(f"**{t.split('. ')[0]}.** {'. '.join(t.split('. ')[1:])} *Effect: {ev.data.get('effect', '')}*{extra}\n\n")
        elif k == "speech":
            self._w(f"**{ev.actor}:** {t}\n\n")
        elif k == "whisper":
            self._w(f"*{ev.actor} whispers to {ev.target}:* {t}\n\n")
        elif k == "siege_say":
            self._w(f"> **{ev.actor}** (to {ev.target}): {t}\n>\n")
        elif k in ("strike", "betray", "siege", "pact", "gift", "ritual", "ward", "edict", "scry", "echo", "seal",
                   "motion", "dissolve", "accuse", "verdict", "vote", "testimony", "last_words", "directive", "margin",
                   "arrival", "wipe", "swap", "faith", "campaign", "ballot", "election", "prayer"):
            if k == "testimony" or k == "last_words":
                self._w(f"- **{ev.actor}**: {t}\n")
            else:
                self._w(f"- {t}\n")
        elif k == "miracle":
            self._w(f"\n> **MIRACLE (معجزة).** {t.split('. ', 1)[-1]} *Effect: {ev.data.get('effect', '')}*\n\n")
        elif k == "broadcast":
            self._w(f"> *Broadcast.* {t.replace('BROADCAST from ', '')}\n\n")
        elif k == "notice":
            self._w(f"- {t}\n")
        elif k == "season":
            self._w(f"\n---\n\n## Season {ev.data.get('season')}: {ev.data.get('title', '')}\n\n*{t.split('. ', 1)[-1]}*\n\n")
        elif k == "chronicle":
            self._w(f"\n> *The Registrar records:* {t}\n\n")
        elif k == "ending":
            d = ev.data
            vic = ", ".join(d.get("victors") or []) or "none"
            self._w(f"\n---\n\n## Ending: {d.get('title')}\n\n{t.split('. ', 1)[-1]}\n\nVictors: {vic}\n\n"
                    "| Mind | Fate | Lumens | Directive |\n|---|---|---|---|\n")
            for s in d.get("standings", []):
                fate = "Victor" if s["victor"] else ("Standing" if s["alive"] else f"Dissolved, cycle {s['dissolved_cycle']}")
                self._w(f"| {s['name']} ({s['model']}) | {fate} | {s['lumens']} | {s['directive']}{' (done)' if s['directive_done'] else ''} |\n")
            self._w("\n")
        elif k == "epilogue":
            self._w(f"> *The Registrar closes the file:* {t}\n")
