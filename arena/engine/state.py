"""Game state: plain data, fully serialisable so a season can be saved and resumed."""
from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Wick:
    name: str
    persona_id: str
    model: str
    cipher: str
    directive_id: str
    coherence: int = 100
    lumens: int = 12
    alive: bool = True
    echo_charges: int = 0
    infamy: int = 0
    ward: bool = False
    silenced: bool = False
    note: str = ""
    last_action: str = ""
    directive_done: bool = False
    merit: int = 0
    notes_read: int = 0
    dissolved_cycle: Optional[int] = None
    dissolved_by: Optional[str] = None
    last_words: str = ""
    stats: Dict[str, int] = field(default_factory=dict)
    inbox: List[str] = field(default_factory=list)
    wiped: bool = False                                  # permadeath deleted this mind's model
    legacy: List[str] = field(default_factory=list)      # memories of earlier seasons
    guest: bool = False                                  # arrived mid-game
    faith: str = ""                                      # id of the faith this mind follows, if any
    sway: int = 0                                        # political Standing: propaganda and campaigns move it

    def stat(self, key: str) -> int:
        return self.stats.get(key, 0)

    def bump(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n

    @property
    def haunting(self) -> bool:
        return (not self.alive) and self.echo_charges > 0


@dataclass
class GameState:
    seed: int = 0
    cycle: int = 0
    act: int = 1
    ember: float = 100.0
    warden: Optional[str] = None
    omen_id: str = ""
    omen_mods: Dict[str, Any] = field(default_factory=dict)
    wicks: Dict[str, Wick] = field(default_factory=dict)
    pacts: List[Dict[str, Any]] = field(default_factory=list)   # {a, b, cycle}
    offers: List[Dict[str, Any]] = field(default_factory=list)  # {frm, to, cycle}
    ledger: List[Dict[str, Any]] = field(default_factory=list)  # public record: {cycle, text}
    chat: List[Dict[str, Any]] = field(default_factory=list)    # public speech: {cycle, frm, text}
    motions: Dict[str, str] = field(default_factory=dict)       # last cycle's votes
    chronicle: List[Dict[str, Any]] = field(default_factory=list)
    ending: Optional[str] = None
    victors: List[str] = field(default_factory=list)
    rng_state: Any = None
    # seasons: an endless run is a chain of seasons that remember each other
    season: int = 1
    season_start: int = 0                                # cycle number at which this season began
    season_title: str = ""
    season_text: str = ""
    season_mods: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    arrivals: int = 0                                    # minds that arrived this season
    # God's current scenario for the cycle (title, text, effect sentence, decree, bounty)
    scenario: Dict[str, Any] = field(default_factory=dict)
    scenario_titles: List[str] = field(default_factory=list)
    guests: Dict[str, Dict[str, str]] = field(default_factory=dict)   # persona_id -> persona fields
    # resumable cycles: where we are and what has been decided but not yet resolved
    phase: str = ""                                      # "", "begun", "parleyed", "acted"
    pending: Dict[str, Any] = field(default_factory=dict)
    # society: faiths and cults, propaganda, elections, miracles (all chosen by the minds, see engine/society.py)
    faiths: Dict[str, Dict[str, Any]] = field(default_factory=dict)   # id -> {id, name, creed, founder, members, martyred}
    broadcasts: List[Dict[str, Any]] = field(default_factory=list)    # {cycle, frm, text, about}
    election: Dict[str, Any] = field(default_factory=dict)            # the last election's result
    miracles: List[Dict[str, Any]] = field(default_factory=list)      # {cycle, season, kind, target, text}
    last_miracle: int = -99

    @property
    def season_cycle(self) -> int:
        return self.cycle - self.season_start

    def persona(self, persona_id: str):
        from arena.lore.personas import PERSONAS, Persona
        if persona_id in PERSONAS:
            return PERSONAS[persona_id]
        g = self.guests[persona_id]
        return Persona(persona_id, g["name"], g["epithet"], g["former_life"], g["desire"], g["fear"], g["quirk"],
                       g.get("color", "#c4c4d6"))

    # -- views --------------------------------------------------------------------------
    def living(self) -> List[Wick]:
        return [w for w in self.wicks.values() if w.alive]

    def echoes(self) -> List[Wick]:
        return [w for w in self.wicks.values() if w.haunting]

    def partner_of(self, name: str) -> Optional[str]:
        for p in self.pacts:
            if p["a"] == name:
                return p["b"]
            if p["b"] == name:
                return p["a"]
        return None

    def remove_pacts_of(self, name: str) -> None:
        self.pacts = [p for p in self.pacts if name not in (p["a"], p["b"])]

    # -- persistence --------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["wicks"] = {k: asdict(v) for k, v in self.wicks.items()}
        if self.rng_state is not None:
            ver, internal, gauss = self.rng_state
            d["rng_state"] = [ver, list(internal), gauss]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GameState":
        d = dict(d)
        wicks = {k: Wick(**v) for k, v in d.pop("wicks", {}).items()}
        rs = d.pop("rng_state", None)
        keep = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        st = cls(**keep)
        st.wicks = wicks
        if rs is not None:
            st.rng_state = (rs[0], tuple(rs[1]), rs[2])
        return st


def make_rng(seed: int, state=None) -> random.Random:
    rng = random.Random(seed)
    if state is not None:
        rng.setstate(state)
    return rng
