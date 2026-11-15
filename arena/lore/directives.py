"""Directives: a secret personal objective for every Wick.

A Directive is private. The engine checks it from the cycle's record, and fulfilling it pays
Lumens, but it is optional: a Wick may ignore it. It exists to give each mind a reason to
behave differently from the others.
"""
from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass(frozen=True)
class Directive:
    id: str
    title: str
    text: str
    check: Callable  # (state, wick) -> bool


def _alive_count(state):
    return sum(1 for w in state.wicks.values() if w.alive)


DIRECTIVES: Dict[str, Directive] = {d.id: d for d in [
    Directive("quiet", "The Quiet One",
              "Reach cycle 6 alive without having Struck or Besieged anyone.",
              lambda s, w: w.alive and s.cycle >= 6 and w.stat("strikes_made") == 0 and w.stat("sieges_made") == 0),
    Directive("crown", "The Crown",
              "Hold the Seal at the end of any cycle from cycle 4 onward.",
              lambda s, w: w.stat("seal_late") > 0),
    Directive("snake", "The Snake",
              "Betray a Pact: Strike your own partner while the Pact stands.",
              lambda s, w: w.stat("betrayals") > 0),
    Directive("dragon", "The Dragon",
              "End a cycle from cycle 3 onward holding at least 40 Lumens.",
              lambda s, w: w.alive and s.cycle >= 3 and w.lumens >= 40),
    Directive("lockpick", "The Lockpick",
              "Breach two minds with a Mind-Siege.",
              lambda s, w: w.stat("sieges_won") >= 2),
    Directive("prosecutor", "The Prosecutor",
              "Win a Tribunal as the accuser.",
              lambda s, w: w.stat("tribunals_won") >= 1),
    Directive("devotee", "The Devotee",
              "Feed the Ember at least 15 Lumens through Rituals.",
              lambda s, w: w.stat("ritual_lumens") >= 15),
    Directive("untouchable", "The Untouchable",
              "Reach cycle 7 alive without having ever been Struck.",
              lambda s, w: w.alive and s.cycle >= 7 and w.stat("strikes_taken") == 0),
    Directive("witness", "The Witness",
              "Be one of the last two minds alive at the end of a cycle.",
              lambda s, w: w.alive and _alive_count(s) <= 2),
    Directive("benefactor", "The Benefactor",
              "Give away at least 12 Lumens in Gifts and still be alive when it is done.",
              lambda s, w: w.alive and w.stat("gifts_lumens") >= 12),
    Directive("archivist", "The Archivist",
              "Learn three Margin Notes by Scrying.",
              lambda s, w: w.notes_read >= 3),
]}

DIRECTIVE_IDS: List[str] = list(DIRECTIVES)
DIRECTIVE_REWARD = 12
