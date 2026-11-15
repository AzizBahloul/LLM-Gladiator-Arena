"""Tunable numbers of the game, read from config.yaml (`game:` section)."""
from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Dict, Tuple


@dataclass
class Rules:
    cycles: int = 12                 # cycles per season; 0 means a season ends only through the story
    endless: bool = False            # after an ending, God starts a new season and the run continues
    god: bool = True                 # God writes each cycle's twist; False uses the fixed deck of Notices
    arrivals_max: int = 2            # new minds God may bring in per season
    arrival_min_cycle: int = 3
    max_wicks: int = 8
    min_minds: int = 4               # a new season refills the roster up to this many minds
    permadeath: bool = True          # a dissolved mind's model is deleted from disk (see engine/permadeath.py)
    parley_rounds: int = 1
    siege_exchanges: int = 3
    workers: int = 1                 # parallel model calls when collecting actions

    start_coherence: int = 100
    start_lumens: int = 12
    base_income: int = 1
    warden_income: int = 3
    pact_income: int = 2

    strike_cost: int = 1
    strike_base: int = 10
    strike_per_lumen: int = 3
    max_boost: int = 5
    ward_cost: int = 2
    siege_cost: int = 3
    scry_cost: int = 2
    accuse_cost: int = 1
    hoard_gain: int = 2
    betray_mult: float = 1.5

    ember_start: float = 100.0
    ember_cap: float = 120.0
    decay_act1: float = 3.0
    decay_act2: float = 4.0
    decay_act3: float = 6.0
    feed_per_dissolution: float = 6.0
    feed_per_lumen: float = 1.5
    dim_threshold: float = 30.0      # below this the dark makes everyone bolder
    bright_threshold: float = 80.0   # above this everyone is a little richer

    echo_charges: int = 3
    haunt_amount: int = 8
    act2_cycle: int = 4
    act3_cycle: int = 8

    temperature: float = 0.9
    tokens_parley: int = 160
    tokens_action: int = 260
    tokens_siege: int = 160
    tokens_short: int = 120
    tokens_narrator: int = 320

    def decay_for(self, act: int) -> float:
        return {1: self.decay_act1, 2: self.decay_act2}.get(act, self.decay_act3)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "Rules":
        known = {f.name for f in fields(cls)}
        merged: Dict[str, Any] = {}
        merged.update({k: v for k, v in (config.get("game") or {}).items() if k in known})
        merged["temperature"] = float((config.get("api") or {}).get("temperature", cls.temperature))
        return cls(**merged)
