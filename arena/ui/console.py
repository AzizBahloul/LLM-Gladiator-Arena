"""Plain console renderer for runs without the full-screen interface."""
from __future__ import annotations

from rich.console import Console
from rich.text import Text

from arena.engine.events import Event
from arena.ui import format as F
from arena.ui.theme import TOKENS as C
from arena.ui.tui import wordmark


class ConsoleRenderer:
    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def banner(self, cast) -> None:
        self.console.print()
        self.console.print(wordmark())
        self.console.print(Text("A failing archive. One lamp. Minds kept for review.", style=f"italic {C['muted']}"))
        self.console.print()
        for c in cast:
            self.console.print(Text.assemble((c["name"], f"bold {c['color']}"), ("  " + c["epithet"], C["muted"]), ("  " + c["model"], C["faint"])))
        self.console.print()

    def __call__(self, ev: Event) -> None:
        if ev.kind in ("state", "think", "income"):
            return
        entry = F.parley_entry(ev) or F.stage_entry(ev)
        if entry is not None:
            self.console.print(entry)
