"""ModelHub: choosing, installing and retiring models for the minds.

The hub is the one place that decides which models play, so the rest of the engine never needs
to know about disks, downloads or the catalog.
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, Iterable, List, Optional, Set

from arena.engine.permadeath import Permadeath
from arena.llm import catalog
from arena.llm.hardware import Hardware
from arena.llm.ollama_tools import ModelLedger, OllamaAdmin, Progress

# Models that are poor at in-character talk, however popular.
_AVOID = ("coder", "code", "starcoder", "sql", "math", "guard", "shield", "llava", "bakllava", "moondream",
          "minicpm-v", "-vl", "vision", "embed", "rerank", "reward", "tool")


class ModelHub:
    def __init__(self, admin: Optional[OllamaAdmin], ledger: ModelLedger, permadeath: Permadeath,
                 hw: Hardware, max_model_gb: float = 2.5, auto_install: bool = True):
        self.admin = admin
        self.ledger = ledger
        self.permadeath = permadeath
        self.hw = hw
        self.max_model_gb = max_model_gb
        self.auto_install = auto_install
        self._pulling: Set[str] = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------------- inspection --
    def installed(self) -> Dict[str, float]:
        try:
            return self.admin.installed() if self.admin else {}
        except Exception:
            return {}

    def cap_gb(self) -> float:
        return min(self.max_model_gb, self.hw.usable_gb * 0.85)

    # ------------------------------------------------------------------------------ planning --
    def candidates(self, exclude: Iterable[str] = ()) -> List[catalog.Variant]:
        ex = set(exclude)
        pool = catalog.pool_for(self.hw.usable_gb, avoid_thinking=True, max_gb=self.cap_gb(), limit=200)
        return [v for v in pool if v.tag not in ex and not any(w in v.tag.lower() for w in _AVOID)]

    def plan(self, n: int, exclude: Iterable[str] = (), max_preinstalled: Optional[int] = None) -> List[str]:
        """Pick n distinct models to play. New models are preferred over ones already on the machine:
        at most a third may be pre-installed unless there is nothing else that fits."""
        have = self.installed()
        pre = {m for m in have if self.ledger.is_protected(m)}
        limit_pre = max(1, n // 3) if max_preinstalled is None else max_preinstalled
        chosen: List[str] = []
        used_pre = 0
        for v in self.candidates(exclude):
            if len(chosen) >= n:
                break
            if v.tag in pre:
                if used_pre >= limit_pre:
                    continue
                used_pre += 1
            chosen.append(v.tag)
        return chosen

    def pick_newborn_model(self, in_use: Iterable[str]) -> Optional[str]:
        """A model for a mind arriving mid-season: an owned model that is idle, else a fresh catalog pick."""
        used = set(in_use)
        have = self.installed()
        for m in have:
            if self.ledger.is_owned(m) and m not in used and not self.permadeath.reserved & {m}:
                return m
        for v in self.candidates(exclude=used):
            if v.tag not in have and self.auto_install:
                return v.tag
        return None

    # ------------------------------------------------------------------------- installing --
    def ensure(self, model: str, progress: Optional[Progress] = None) -> bool:
        """Make sure a model is installed, pulling it if needed. Blocks until done."""
        if not self.admin:
            return False
        if self.admin.has(model):
            return True
        with self._lock:
            if model in self._pulling:
                return False
            self._pulling.add(model)
        try:
            ok = self.admin.pull(model, progress)
            if ok:
                self.ledger.mark_owned(model)
            return ok
        finally:
            with self._lock:
                self._pulling.discard(model)

    def ensure_async(self, model: str, progress: Optional[Progress], done: Callable[[str, bool], None]) -> None:
        def run():
            done(model, self.ensure(model, progress))
        threading.Thread(target=run, daemon=True, name=f"pull-{model}").start()
