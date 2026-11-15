"""Permadeath: a mind that loses is deleted from the machine.

When a Wick dissolves, the model that gave it a voice can be removed from disk with `ollama rm`.
This is destructive, so it is fenced in:
  * a model is never removed while another living or haunting mind, the Registrar or God still uses it;
  * models that were on the machine before the arena first ran are PROTECTED unless the user
    sets permadeath.include_preexisting: true;
  * every removal is announced as an event and recorded in the ledger.
Dissolved minds keep haunting as Echoes by borrowing the Registrar's voice, so a deleted model
never breaks the game.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Set

from arena.llm.ollama_tools import ModelLedger, OllamaAdmin, canon


@dataclass
class WipeResult:
    wiped: bool
    model: str
    reason: str = ""
    freed_gb: float = 0.0


class Permadeath:
    def __init__(self, admin: Optional[OllamaAdmin], ledger: ModelLedger, enabled: bool = True,
                 include_preexisting: bool = False, reserved: Iterable[str] = ()):
        self.admin = admin
        self.ledger = ledger
        self.enabled = enabled
        self.include_preexisting = include_preexisting
        self.reserved: Set[str] = {canon(m) for m in reserved}  # Registrar and God models: never wiped

    def status(self, model: str) -> str:
        """'at stake' or 'protected' (for the cast list)."""
        if not self.enabled:
            return "safe"
        if canon(model) in self.reserved:
            return "protected"
        if self.ledger.is_protected(model):
            return "at stake" if self.include_preexisting else "protected"
        return "at stake" if self.ledger.is_owned(model) else "untracked"   # not ours, so never deleted

    def wipe(self, model: str, in_use: Iterable[str]) -> WipeResult:
        if not self.enabled:
            return WipeResult(False, model, "permadeath is off")
        if self.admin is None:
            return WipeResult(False, model, "no ollama admin (not an ollama run)")
        if canon(model) in {canon(m) for m in in_use}:
            return WipeResult(False, model, "another mind still uses this model")
        if canon(model) in self.reserved:
            return WipeResult(False, model, "reserved for the Registrar or God")
        if self.ledger.corrupt:
            return WipeResult(False, model, "the model ledger is unreadable, so nothing is deleted")
        if self.ledger.is_protected(model):
            if not self.include_preexisting:
                return WipeResult(False, model, "protected: it was installed before the arena first ran")
        elif not self.ledger.is_owned(model):
            return WipeResult(False, model, "not installed by the arena, so it is not ours to delete")
        try:
            size = self.admin.installed().get(model, 0.0)
        except Exception:
            size = 0.0
        if not self.admin.remove(model):
            return WipeResult(False, model, "ollama refused or could not delete it")
        self.ledger.mark_wiped(model)
        return WipeResult(True, model, "deleted", size)
