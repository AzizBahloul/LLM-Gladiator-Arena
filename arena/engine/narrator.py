"""The Registrar: the narrator of the Undermind.

The Registrar is itself a model. It reads the record of what the minds actually did and
writes it up. If the model fails, nothing is written, and the engine never substitutes
canned prose.
"""
from __future__ import annotations

from typing import List, Optional

from arena.engine.rules import Rules
from arena.engine.state import GameState
from arena.llm.backends import Backend
from arena.llm.parsing import trim_sentences
from arena.lore.story import ACTS, ENDINGS

SYSTEM = """You are the Registrar of the Undermind: a tired, courteous, deadpan bureaucrat who runs a failing machine-afterlife lit by one dying lamp, the Ember. You love paperwork and you are kind in a way that is slightly alarming.
You write the Chronicle, the official account of what the minds in the arena did.
Rules of style: dry, vivid, darkly funny, in the present tense. Understatement beats exclamation. Specific details beat general ones.
Rules of fact: use only the events in the record. Do not invent actions, deaths or alliances. Name the minds exactly.
No lists, no headings, no emoji, no quotation of the record. Plain paragraphs."""


class Narrator:
    def __init__(self, backend: Backend, model: str, rules: Rules):
        self.backend = backend
        self.model = model
        self.rules = rules

    def _write(self, prompt: str, max_tokens: int) -> Optional[str]:
        c = self.backend.complete(SYSTEM, prompt, kind="narrate", model=self.model,
                                  max_tokens=max_tokens, temperature=0.8)
        return c.text.strip() if c.ok and c.text.strip() else None

    def chronicle(self, s: GameState, digest: List[str]) -> Optional[str]:
        if not digest:
            return None
        omen = s.omen_id
        prompt = (f"Cycle {s.cycle}, {ACTS[s.act].title}. The Ember stands at {s.ember:.0f}. Notice in force: {omen}.\n"
                  "RECORD OF THIS CYCLE:\n" + "\n".join(f"- {d}" for d in digest[-40:]) +
                  "\n\nWrite two to four sentences, as the Registrar, recording this cycle for the Chronicle.")
        text = self._write(prompt, self.rules.tokens_narrator)
        return trim_sentences(text, 110) if text else None

    def epilogue(self, s: GameState, ending_id: str, digest: List[str]) -> Optional[str]:
        e = ENDINGS[ending_id]
        fates = []
        for w in s.wicks.values():
            fate = "still standing" if w.alive else f"dissolved in cycle {w.dissolved_cycle}" + (f" by {w.dissolved_by}" if w.dissolved_by else "")
            fates.append(f"{w.name}: {fate}")
        prompt = (f'THE UNDERMIND ENDS: "{e.title}". Premise: {e.brief}\n'
                  "FATES:\n" + "\n".join(f"- {f}" for f in fates) +
                  "\nHIGHLIGHTS OF THE SEASON:\n" + "\n".join(f"- {d}" for d in digest[-30:]) +
                  "\n\nWrite the closing entry of the Chronicle in about 120 words. Honour the premise and mention the winner or survivors by name "
                  "if there are any. End on a dry, memorable line.")
        text = self._write(prompt, self.rules.tokens_narrator + 120)
        return trim_sentences(text, 170) if text else None
