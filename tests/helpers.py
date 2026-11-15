"""Shared builders for the tests. Nothing here talks to a real model or touches a real ollama."""
from __future__ import annotations

import copy
import tempfile
from typing import Any, Dict, Optional

import yaml

from arena.engine.events import EventBus
from arena.engine.game import Game
from arena.engine.models import ModelHub
from arena.engine.permadeath import Permadeath
from arena.engine.store import RunStore
from arena.llm.hardware import Hardware
from arena.llm.mock import MockBackend
from arena.llm.ollama_tools import ModelLedger
from arena.lore.omens import DEFAULT_MODS

BASE: Dict[str, Any] = {
    "api": {"provider": "mock", "model": "m1", "temperature": 0.9},
    "models": ["m1", "m2", "m3"],
    "roster": ["vellum", "glitchwick", "aurelia", "rictus", "jester9", "sage"],
    "narrator_model": "narr",
    "god_model": "narr",
    "game": {"cycles": 8},
}


def config(**game: Any) -> Dict[str, Any]:
    cfg = copy.deepcopy(BASE)
    cfg["game"].update(game)
    return cfg


def make_game(seed: int = 1, store: Optional[RunStore] = None, hub: Optional[ModelHub] = None,
              backend: Optional[MockBackend] = None, **game: Any) -> Game:
    g = Game(config(**game), backend or MockBackend(seed), EventBus(), seed=seed, store=store, hub=hub)
    g.s.omen_mods = dict(DEFAULT_MODS)       # as if a cycle had begun with a plain Notice
    return g


def tmp_store(seed: int = 1) -> RunStore:
    return RunStore.create(tempfile.mkdtemp(), seed)


class FakeAdmin:
    """Stands in for ollama. Records every delete instead of running one."""

    def __init__(self, models: Optional[Dict[str, float]] = None):
        self.models = dict(models or {})
        self.removed: list = []
        self.pulled: list = []

    def up(self) -> bool:
        return True

    def installed(self) -> Dict[str, float]:
        return dict(self.models)

    def has(self, model: str) -> bool:
        return model in self.models

    def pull(self, model: str, on_progress=None, timeout: int = 0) -> bool:
        self.models[model] = 2.0
        self.pulled.append(model)
        return True

    def remove(self, model: str) -> bool:
        self.models.pop(model, None)
        self.removed.append(model)
        return True


def make_hub(models: Dict[str, float], protected=(), enabled: bool = True, include_preexisting: bool = False,
             owned=None):
    """`owned` are the models the arena installed (default: every model that is not protected)."""
    admin = FakeAdmin(models)
    ledger = ModelLedger(tempfile.mktemp(suffix=".json"))
    ledger.snapshot_protected(protected)
    for m in (owned if owned is not None else [m for m in models if m not in set(protected)]):
        ledger.mark_owned(m)
    perm = Permadeath(admin, ledger, enabled=enabled, include_preexisting=include_preexisting)
    return ModelHub(admin, ledger, perm, Hardware(vram_gb=8, ram_gb=16, ram_free_gb=10)), admin, ledger
