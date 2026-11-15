"""The model picker: swap a mind into another model, or bring a newborn in from one.

Opened with `m` while a run is going. A model that is not installed yet is downloaded first
(progress shows on the Stage), and the change happens at the start of the next cycle, so no
mind is cut off in the middle of a turn.
"""
from __future__ import annotations

from typing import Any, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, OptionList, Static
from textual.widgets.option_list import Option

from arena.ui.theme import TOKENS as C


class ModelScreen(ModalScreen):
    BINDINGS = [Binding("escape", "close", "Close")]

    CSS = """
    ModelScreen { align: center middle; background: $u-bg 70%; }
    #picker { width: 96%; max-width: 110; height: 90%; background: $u-surface; border: round $u-ember; padding: 1 2; }
    #picker-title { text-style: bold; margin-bottom: 1; }
    #picker-cols { height: 1fr; }
    #minds-col { width: 34; margin-right: 2; }
    #models-col { width: 1fr; }
    #minds, #models { height: 1fr; border: round $u-line; background: $u-bg; }
    #minds:focus, #models:focus { border: round $u-ember; }
    #filter { margin-bottom: 1; border: round $u-line; background: $u-bg; }
    #filter:focus { border: round $u-ember; }
    #picker-actions { height: 3; margin-top: 1; }
    #picker-actions Button { margin-right: 2; }
    #picker-note { color: $u-muted; height: auto; margin-top: 1; }
    ModelScreen OptionList > .option-list--option-highlighted { background: $u-raised; color: $u-text; text-style: bold; }
    ModelScreen OptionList:focus > .option-list--option-highlighted { background: $u-raised; color: $u-text; }
    ModelScreen OptionList > .option-list--option-hover { background: $u-raised; }
    ModelScreen Button { background: $u-raised; color: $u-text; border: none; border-top: none; border-bottom: none; }
    ModelScreen Button:hover { background: $u-line; }
    ModelScreen Button:focus { text-style: bold reverse; }
    ModelScreen Button.-primary { background: $u-ember; color: $u-bg; }
    ModelScreen Button.-primary:hover { background: $u-ember-low; }
    """

    def __init__(self, game) -> None:
        super().__init__()
        self.game = game
        self.hub = getattr(game, "hub", None)
        self._rows: List[Any] = []

    # ------------------------------------------------------------------------ layout ---
    def compose(self) -> ComposeResult:
        with Vertical(id="picker"):
            yield Static(Text("Models", style=f"bold {C['text']}"), id="picker-title")
            with Horizontal(id="picker-cols"):
                with Vertical(id="minds-col"):
                    yield Static(Text("Minds", style=C["muted"]))
                    yield OptionList(id="minds")
                with Vertical(id="models-col"):
                    yield Input(placeholder="Filter models, for example llama or 3b", id="filter")
                    yield OptionList(id="models")
            with Horizontal(id="picker-actions"):
                yield Button("Birth a new mind from this model", id="born", variant="primary")
                yield Button("Move the selected mind into this model", id="swap")
                yield Button("Close", id="close")
            yield Static("", id="picker-note")

    def on_mount(self) -> None:
        self._fill_minds()
        self._fill_models("")
        if self.hub is None:
            self._note("Changing models needs a run on ollama. This run uses a test double or a hosted API.")
        else:
            self._note("Pick a mind on the left and a model on the right. The change lands at the start of the next cycle.")
        self.query_one("#models", OptionList).focus()

    def _note(self, message: str) -> None:
        self.query_one("#picker-note", Static).update(Text(message, style=C["muted"]))

    # -------------------------------------------------------------------------- data ---
    def _fill_minds(self) -> None:
        box = self.query_one("#minds", OptionList)
        box.clear_options()
        for w in self.game.s.wicks.values():
            stake = self.hub.permadeath.status(w.model) if self.hub else ""
            state = "" if w.alive else ("echo" if w.haunting else "dissolved")
            t = Text()
            t.append(w.name, style=f"bold {self.game.s.persona(w.persona_id).color}")
            t.append(f"\n{w.model}", style=C["faint"])
            if state or stake:
                t.append("  " + ", ".join(x for x in (state, stake) if x), style=C["faint"])
            box.add_option(Option(t, id=w.name))
        if box.option_count:
            box.highlighted = 0

    def _fill_models(self, query: str) -> None:
        from arena.llm import catalog
        box = self.query_one("#models", OptionList)
        box.clear_options()
        self._rows = []
        if self.hub is None:
            return
        have = self.hub.installed()
        seen = set()
        rows = []
        q = query.lower().strip()
        for tag, gb in sorted(have.items()):
            if q and q not in tag.lower():
                continue
            rows.append((tag, gb, True, ""))
            seen.add(tag)
        cap = self.hub.cap_gb()
        for v in catalog.search(q, max_gb=cap)[:120]:
            if v.tag in seen or v.thinking or any(x in v.tag.lower() for x in ("embed", "guard", "coder", "-vl", "llava")):
                continue
            rows.append((v.tag, v.est_gb, False, v.description))
        for tag, gb, installed, desc in rows[:150]:
            t = Text()
            t.append(tag, style=f"bold {C['text']}")
            t.append(f"   {gb:g} GB", style=C["muted"])
            t.append("   installed" if installed else "   will download", style=C["faint"])
            if desc:
                t.append("\n" + (desc if len(desc) < 90 else desc[:87] + "..."), style=C["faint"])
            box.add_option(Option(t, id=tag))
            self._rows.append(tag)
        if box.option_count:
            box.highlighted = 0

    def _model(self) -> Optional[str]:
        box = self.query_one("#models", OptionList)
        i = box.highlighted
        return box.get_option_at_index(i).id if i is not None and box.option_count else None

    def _mind(self) -> Optional[str]:
        box = self.query_one("#minds", OptionList)
        i = box.highlighted
        return box.get_option_at_index(i).id if i is not None and box.option_count else None

    # ----------------------------------------------------------------------- events ----
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter":
            self._fill_models(event.value)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "models":
            self._born()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "born":
            self._born()
        elif event.button.id == "swap":
            self._swap()
        else:
            self.dismiss(None)

    def _born(self) -> None:
        model = self._model()
        if self.hub is None or not model:
            return
        self.app.run_worker(lambda: self.game.request_newborn(model), thread=True)   # off the UI thread: it may download
        self._note(f"A new mind will be born from {model} at the start of the next cycle.")

    def _swap(self) -> None:
        model, name = self._model(), self._mind()
        if self.hub is None or not model or not name:
            return
        self.app.run_worker(lambda: self.game.request_swap(name, model), thread=True)
        self._note(f"{name} will move into {model} at the start of the next cycle.")

    def action_close(self) -> None:
        self.dismiss(None)
