"""Event bus. The engine emits events, and interfaces (terminal UI, console, chronicle file)
subscribe. The engine knows nothing about how events are shown."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Event kinds. 'audience' marks things only a spectator sees, never another mind.
KINDS = (
    "title", "act", "cycle", "notice", "speech", "whisper", "stall",
    "ward", "strike", "betray", "siege", "siege_say", "pact", "gift", "scry", "ritual",
    "accuse", "testimony", "vote", "verdict", "dissolve", "last_words", "echo", "seal",
    "edict", "motion", "ember", "directive", "chronicle", "margin", "ending", "epilogue",
    "think", "state", "system", "fizzle", "income", "arrival", "wipe", "swap", "season",
)


@dataclass
class Event:
    kind: str
    text: str
    actor: str = ""
    target: str = ""
    cycle: int = 0
    act: int = 1
    audience: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


class EventBus:
    def __init__(self) -> None:
        self._subs: List[Callable[[Event], None]] = []
        self._lock = threading.Lock()
        self.history: List[Event] = []

    def subscribe(self, fn: Callable[[Event], None]) -> None:
        self._subs.append(fn)

    def emit(self, event: Event) -> None:
        with self._lock:
            self.history.append(event)
        for fn in list(self._subs):
            try:
                fn(event)
            except Exception:  # a broken view must never stop the game
                pass
