"""The Undermind terminal interface (Textual).

Design: a failing archive lit by one lamp. The Stage (what happened) leads and takes the
remaining width. The roster of minds is narrow, Parley sits beside the Stage, and the Ember
is the only warm object in the masthead. Colour comes only from arena.ui.theme.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Group
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import RichLog, Static

from arena.engine.events import Event
from arena.ui import format as F
from arena.ui.models_screen import ModelScreen
from arena.ui.theatre import Theatre
from arena.ui.theme import TOKENS as C, css_variables

# PACES are speed steps. 0.35 is the default and means the Theatre plays at its natural speed;
# the Theatre holds each event for (its own hold time) x (pace / 0.35). 0.0 skips the holds.
PACES = [0.0, 0.15, 0.35, 0.7, 1.2]
NATURAL_PACE = 0.35
THEATRE_MIN_HEIGHT = 30      # below this many rows the Stage gets the whole centre column

# A five-row block wordmark. The I is the lamp, so it is the only letter in Ember.
_GLYPHS = {
    "U": ["█   █", "█   █", "█   █", "█   █", " ███ "],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    "D": ["████ ", "█   █", "█   █", "█   █", "████ "],
    "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    "R": ["████ ", "█   █", "████ ", "█  █ ", "█   █"],
    "M": ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
    "I": ["█████", "  █  ", "  █  ", "  █  ", "█████"],
}


def wordmark(word: str = "UNDERMIND") -> Text:
    rows: List[Text] = []
    for r in range(5):
        line = Text()
        for i, ch in enumerate(word):
            style = C["ember"] if ch == "I" else C["text"]
            line.append(_GLYPHS[ch][r], style=style)
            if i < len(word) - 1:
                line.append("  ")
        rows.append(line)
    out = Text()
    for i, row in enumerate(rows):
        out.append_text(row)
        if i < len(rows) - 1:
            out.append("\n")
    return out


# =============================================================================== widgets ==
class Masthead(Static):
    """Title, act, cycle, the Notice in force, and the Ember gauge."""

    def __init__(self, **kw: Any) -> None:
        super().__init__("", **kw)
        self.snap: Dict[str, Any] = {}
        self.ember_shown = 100.0
        self.notice = ""

    def set_snapshot(self, snap: Dict[str, Any]) -> None:
        self.snap = snap
        self.refresh()

    def tick(self) -> None:
        target = float(self.snap.get("ember", 100.0))
        if abs(self.ember_shown - target) > 0.2:
            self.ember_shown += (target - self.ember_shown) * 0.18
            self.refresh()
        elif self.ember_shown != target:
            self.ember_shown = target
            self.refresh()

    def render(self):
        snap = self.snap
        width = self.size.width or 100
        act = snap.get("act", 1)
        left = Text("THE UNDERMIND", style=f"bold {C['text']}")
        mid = Text()
        if snap.get("cycle"):
            if snap.get("season", 1) > 1:
                mid.append(f"Season {snap['season']}  ", style=f"bold {C['ember']}")
            mid.append(f"Act {F.ROMAN.get(act, act)}" + ("  " if width >= 100 else ""), style=f"bold {C['text']}")
            if width >= 100:
                mid.append(f"{snap.get('act_title', '')}", style=C["muted"])
            mid.append(f"{'   ' if width >= 100 else '  '}Cycle {snap['cycle']}" + (f" of {snap['cycles']}" if snap.get("cycles") else ""), style=C["muted"])
        else:
            mid.append("The file is not yet open", style=C["muted"])
        ember = self.ember_shown
        gw = 14 if width < 100 else (24 if width < 140 else 32)
        right = Text()
        right.append("Ember ", style=C["muted"])
        right.append_text(F.bar(ember, 100, gw, F.ember_color(ember)))
        right.append(f" {ember:>3.0f}", style=f"bold {F.ember_color(ember)}")

        grid = Table.grid(expand=True, padding=(0, 1))
        if width >= 100:
            grid.add_column(ratio=1)
            grid.add_column(ratio=2, justify="center")
            grid.add_column(justify="right", no_wrap=True)
            grid.add_row(left, mid, right)
        else:
            grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
            grid.add_column(justify="right", no_wrap=True)
            grid.add_row(mid, right)
        avail = max(10, (self.size.width or 80) - 6)
        omen = self.notice or "Waiting for the first Notice."
        if len(omen) > avail:
            omen = omen[: avail - 1].rstrip() + "…"
        return Group(grid, Text(omen, style=C["faint"]))


class Roster(Static):
    """The minds: Coherence, Lumens, and status in words."""

    def __init__(self, **kw: Any) -> None:
        super().__init__("", **kw)
        self.snap: Dict[str, Any] = {}
        self.thinking = ""
        self._redraw()

    def set_snapshot(self, snap: Dict[str, Any], thinking: str = "") -> None:
        self.snap, self.thinking = snap, thinking
        self._redraw()

    def on_resize(self, event: events.Resize) -> None:
        self._redraw()

    def _redraw(self) -> None:
        # update() (not render()) so the container re-measures the height as minds change.
        self.update(self._build())

    def _build(self):
        wicks = self.snap.get("wicks")
        if not wicks:
            return Text("Waiting for the minds to arrive.", style=C["faint"])
        width = max(20, (self.size.width or 30))
        blocks: List[Any] = []
        for w in wicks:
            name_style = f"bold {w['color']}" if w["alive"] else f"strike {C['faint']}"
            head = Text(w["name"], style=name_style)
            if w["warden"] and w["alive"]:
                head.append("  Seal", style=f"bold {C['ember']}")
            lines: List[Text] = [head]
            if w["alive"]:
                bw = max(8, min(14, width - 22))
                row = Text()
                row.append_text(F.bar(w["coherence"], 100, bw, F.coherence_color(w["coherence"])))
                row.append(f" {w['coherence']:>3}", style=f"bold {F.coherence_color(w['coherence'])}")
                row.append(f"  {w['lumens']} Lumens", style=C["muted"])
                lines.append(row)
                tags: List[str] = []
                if w["partner"]:
                    tags.append(f"pact with {w['partner'].split()[0]}")
                if w.get("faith"):
                    tags.append(w["faith"])
                if w["ward"]:
                    tags.append("warded")
                if w["silenced"]:
                    tags.append("silenced")
                status = Text(", ".join(tags) if tags else w["model"], style=C["muted"] if tags else C["faint"],
                              no_wrap=True, overflow="ellipsis")
                if self.thinking == w["name"]:
                    status = Text("thinking", style=f"bold {C['ember']}")
                lines.append(status)
            else:
                echo = f"Echo, {w['echo']} hauntings left" if w["echo"] else "Faded"
                lines.append(Text(echo, style=C["faint"]))
                gone = ("deleted from disk: " if w.get("wiped") else "") + w["model"]
                lines.append(Text(gone, style=C["danger"] if w.get("wiped") else C["faint"], no_wrap=True, overflow="ellipsis"))
            blocks.append(Group(*lines))
        return Group(*blocks)


class StatusBar(Static):
    def __init__(self, **kw: Any) -> None:
        super().__init__("", **kw)
        self.left = Text("")
        self.right = ""

    def set(self, left: Text, right: str) -> None:
        self.left, self.right = left, right
        self.refresh()

    def render(self):
        width = (self.size.width or 100) - 4
        right = self.right if width >= 90 else ""
        if right and len(self.left.plain) + len(right) + 2 > width:
            right = ""                      # the live status outranks the key hints: drop the hints, not the news
        room = max(10, width - len(right) - 2)
        left = self.left.copy()
        if len(left.plain) > room:
            left.truncate(room - 1)
            left.append("…")
        pad = max(1, width - len(left.plain) - len(right))
        out = Text()
        out.append_text(left)
        out.append(" " * pad)
        out.append(right, style=C["faint"])
        return out


# ================================================================================ screens ==
class Splash(Screen):
    BINDINGS = [Binding("enter,space", "open", "Open the file"), Binding("q,escape", "app.quit", "Quit")]

    def __init__(self, cast: List[Dict[str, str]], provider: str) -> None:
        super().__init__()
        self.cast, self.provider = cast, provider

    def compose(self) -> ComposeResult:
        with Vertical(id="splash"):
            narrow = (self.app.size.width or 100) < 66
            yield Static(Text("U N D E R M I N D", style=f"bold {C['text']}") if narrow else wordmark(), id="mark")
            yield Static(Text("A failing archive. One lamp. Minds kept for review.", style=f"italic {C['muted']}"), id="tag")
            yield Static(self._cast_table(), id="cast")
            yield Static(Text("No human writes their moves. Press Enter to open the file.", style=C["text"]), id="enter")

    def _cast_table(self):
        wide = (self.app.size.width or 100) >= 84
        t = Table(box=None, show_header=False, pad_edge=False, padding=(0, 2), expand=False)
        t.add_column(no_wrap=True)
        if wide:
            t.add_column(no_wrap=True, overflow="ellipsis")
        t.add_column(no_wrap=True)
        for c in self.cast:
            row = [Text(c["name"], style=f"bold {c['color']}")]
            if wide:
                row.append(Text(c["epithet"], style=C["muted"]))
            row.append(Text(c["model"], style=C["faint"]))
            t.add_row(*row)
        return t

    def action_open(self) -> None:
        self.dismiss(True)


# ==================================================================================== app ==
class UndermindApp(App):
    TITLE = "The Undermind"

    CSS = """
    Screen { background: $u-bg; color: $u-text; layout: vertical; }

    #splash { align: center middle; height: 100%; width: 100%; }
    #splash > Static { width: auto; max-width: 100%; margin-bottom: 1; }
    #mark { margin-bottom: 1; }
    #enter { margin-top: 1; }

    #masthead { height: 3; padding: 0 2; background: $u-surface; border-bottom: solid $u-line; }
    #body { height: 1fr; padding: 0 1; }
    #roster-wrap { width: 34; border: round $u-line; background: $u-surface; padding: 0 1; }
    #roster-wrap:focus { border: round $u-ember; }
    #centre { width: 1fr; height: 100%; }
    #theatre { height: 45%; min-height: 16; max-height: 24; border: round $u-line; background: $u-bg; padding: 0; }
    #theatre.hidden { display: none; }
    #stage { width: 100%; height: 1fr; border: round $u-line; background: $u-bg; padding: 0 1; }
    #stage:focus { border: round $u-ember; }
    #parley { width: 44; border: round $u-line; background: $u-surface; padding: 0 1; }
    #parley:focus { border: round $u-ember; }
    #status { height: 1; padding: 0 2; background: $u-surface; color: $u-muted; }

    #roster-wrap, #stage, #parley, #theatre {
        border-title-color: $u-text; border-title-style: bold;
        scrollbar-background: $u-surface; scrollbar-background-hover: $u-surface; scrollbar-background-active: $u-surface;
        scrollbar-color: $u-line; scrollbar-color-hover: $u-faint; scrollbar-color-active: $u-ember;
        scrollbar-size-vertical: 1;
    }

    .medium #roster-wrap { width: 30; }
    .medium #parley { width: 38; }
    .narrow #parley { display: none; }
    .narrow #roster-wrap { width: 30; }
    .tiny #roster-wrap { display: none; }
    .show-parley #centre { display: none; }
    .show-parley.narrow #parley { display: block; width: 1fr; }
    .show-roster #centre { display: none; }
    .show-roster.tiny #roster-wrap { display: block; width: 1fr; }
    """

    BINDINGS = [
        Binding("q", "leave", "Leave"),
        Binding("p", "pause", "Pause"),
        Binding("c", "panel", "Panel"),
        Binding("t", "theatre", "Theatre"),
        Binding("m", "models", "Models"),
        Binding("minus", "pace(1)", "Slower"),
        Binding("plus,equals_sign", "pace(-1)", "Faster"),
        Binding("tab", "focus_next", "Next pane", show=False),
    ]

    def __init__(self, game, bus, chronicle_path: str = "", provider: str = "", replay: Optional[List[Event]] = None) -> None:
        super().__init__()
        self.game, self.bus = game, bus
        self.chronicle_path = chronicle_path
        self.provider = provider
        self.replay = list(replay or [])
        self.snap: Dict[str, Any] = {}
        self.thinking = ""
        self.think_what = ""
        self.think_since = 0.0
        self.finished = False
        self.failed = ""
        self._quit_armed = 0.0
        self._started = False
        self._unread = 0
        self._panel = "stage"
        self._pace_i = min(range(len(PACES)), key=lambda i: abs(PACES[i] - game.pace))
        self._theatre_on = True
        # The Theatre does the pacing now (it holds each event while the figures act it out),
        # so the engine's own per-event sleep is switched off.
        game.pace = 0.0

    def get_css_variables(self) -> Dict[str, str]:
        v = super().get_css_variables()
        v.update({f"u-{k}": val for k, val in css_variables().items()})
        return v

    # ------------------------------------------------------------------ composition ----
    def compose(self) -> ComposeResult:
        yield Masthead(id="masthead")
        with Horizontal(id="body"):
            with VerticalScroll(id="roster-wrap"):
                yield Roster(id="roster")
            with Vertical(id="centre"):
                yield Theatre(id="theatre")
                yield RichLog(id="stage", wrap=True, markup=False, highlight=False, min_width=20)
            yield RichLog(id="parley", wrap=True, markup=False, highlight=False, min_width=20)
        yield StatusBar(id="status")

    def on_mount(self) -> None:
        self.query_one("#roster-wrap").border_title = "Minds"
        self.query_one("#stage").border_title = "Stage"
        self.query_one("#theatre").border_title = "Theatre"
        self.query_one(Theatre).speed = PACES[self._pace_i] / NATURAL_PACE
        self.query_one("#parley").border_title = "Parley"
        self.query_one("#stage").can_focus = True
        self.query_one("#parley").can_focus = True
        stage = self.query_one("#stage", RichLog)
        stage.write(Text("The file is closed. The minds are being shown in.", style=C["faint"]))
        self.query_one("#parley", RichLog).write(Text("Nobody has spoken yet.", style=C["faint"]))
        self.set_interval(1 / 20, self.query_one(Masthead).tick)
        self.set_interval(1.0, self._refresh_status)
        self._layout(self.size.width)
        self._refresh_status()
        cast = []
        st = self.game.s
        for w in st.wicks.values():
            p = st.persona(w.persona_id)
            cast.append({"name": w.name, "epithet": p.epithet, "color": p.color, "model": w.model})
            F.register(w.name, p.color)
        self.query_one(Theatre).set_cast([
            {"name": w.name, "persona_id": w.persona_id, "color": st.persona(w.persona_id).color,
             "model": w.model, "coherence": w.coherence, "alive": w.alive, "echo": w.echo_charges}
            for w in st.wicks.values()])
        self.push_screen(Splash(cast, self.provider), self._begin)

    def on_resize(self, event: events.Resize) -> None:
        self._layout(event.size.width)

    # --------------------------------------------------------------------- layout -----
    def _layout(self, width: int) -> None:
        narrow, tiny = width < 112, width < 76
        self.screen.set_class(112 <= width < 140, "medium")
        self.screen.set_class(narrow, "narrow")
        self.screen.set_class(tiny, "tiny")
        self.screen.set_class(self._panel == "parley", "show-parley")
        self.screen.set_class(self._panel == "roster", "show-roster")
        self._fit_theatre()

    def _fit_theatre(self) -> None:
        room = self.size.height >= THEATRE_MIN_HEIGHT and self.size.width >= 50
        try:
            self.query_one("#theatre").set_class(not (self._theatre_on and room), "hidden")
        except Exception:
            pass

    def action_theatre(self) -> None:
        self._theatre_on = not self._theatre_on
        self._fit_theatre()
        if self.size.height < THEATRE_MIN_HEIGHT:
            self._flash("The terminal is too short for the Theatre. Make it taller.")

    def action_models(self) -> None:
        if isinstance(self.screen, ModelScreen):
            return
        self.push_screen(ModelScreen(self.game))

    def action_panel(self) -> None:
        width = self.size.width
        if width >= 112:
            self._flash("All panels are visible at this width.")
            return
        order = ["stage", "parley"] + (["roster"] if width < 76 else [])
        self._panel = order[(order.index(self._panel) + 1) % len(order)] if self._panel in order else "stage"
        if self._panel == "parley":
            self._unread = 0
        self._layout(width)
        self._refresh_status()

    # ----------------------------------------------------------------- game thread ----
    def _begin(self, _result: Optional[bool]) -> None:
        if self._started:
            return
        self._started = True
        self.query_one("#stage", RichLog).focus()  # the Stage leads, so it takes focus
        self.query_one("#stage", RichLog).clear()
        self.query_one("#parley", RichLog).clear()
        self._replay_journal()
        self.bus.subscribe(self._from_thread)
        self.run_worker(self._play, thread=True, exclusive=True, name="game")

    def _replay_journal(self) -> None:
        """Show what already happened in a resumed run, instantly and without the Theatre."""
        if not self.replay:
            return
        for ev in self.replay:
            if ev.kind == "arrival" and ev.data.get("color"):
                F.register(ev.actor, ev.data["color"])
            if ev.kind == "notice" and ev.data.get("omen"):
                m = self.query_one(Masthead)
                m.notice = f"{ev.text.split('. ')[0]}. {ev.data.get('effect', '')}"
            parley = F.parley_entry(ev)
            if parley is not None:
                self.query_one("#parley", RichLog).write(parley)
                continue
            entry = F.stage_entry(ev)
            if entry is not None:
                self.query_one("#stage", RichLog).write(entry)
        self.query_one("#stage", RichLog).write(Rule(Text(" resumed ", style=C["faint"]), style=C["line"]))
        snap = self.game.snapshot()
        self.snap = snap
        self.query_one(Masthead).set_snapshot(snap)
        self.query_one(Roster).set_snapshot(snap, "")
        self.query_one(Theatre).set_state(snap)
        self.replay = []

    def _play(self) -> None:
        try:
            self.game.run()
        except Exception as exc:  # the arena failed, and the interface should say so plainly
            self.failed = f"{type(exc).__name__}: {exc}"
        try:
            self.call_from_thread(self._done)
        except Exception:
            pass

    def _from_thread(self, ev: Event) -> None:
        """Runs on the game thread: hand the event to the UI, then hold while the Theatre acts it out."""
        try:
            hold = self.call_from_thread(self.handle, ev)
        except Exception:
            return
        if not hold or hold <= 0:
            return
        end = time.monotonic() + float(hold)
        while time.monotonic() < end and not self.game._stop:
            time.sleep(min(0.05, max(0.0, end - time.monotonic())))

    def _done(self) -> None:
        self.finished = True
        self.thinking = ""
        self.query_one(Roster).set_snapshot(self.snap, "")
        if self.failed:
            self.query_one("#stage", RichLog).write(
                Text(f"The arena stopped: {self.failed}. The season is saved up to the last full cycle.", style=f"bold {C['danger']}"))
        self._refresh_status()

    # ------------------------------------------------------------------- events -------
    def handle(self, ev: Event) -> float:
        """Show one event. Returns how many seconds the game thread should hold for the Theatre."""
        hold = 0.0
        try:
            hold = self.query_one(Theatre).feed(ev)
        except Exception:
            hold = 0.0
        self._present(ev)
        return hold

    def _present(self, ev: Event) -> None:
        k = ev.kind
        if k == "state":
            self.snap = ev.data["snapshot"]
            F.register_all(self.snap.get("wicks", []))
            self.query_one(Masthead).set_snapshot(self.snap)
            self.query_one(Roster).set_snapshot(self.snap, self.thinking)
            return
        if k == "think":
            self.thinking = ev.actor if ev.actor != F.REGISTRAR else ""
            self.think_what = f"{ev.actor} {ev.text}" if ev.actor else ev.text
            self.think_since = time.time()
            self.query_one(Roster).set_snapshot(self.snap, self.thinking)
            self._refresh_status()
            return
        if k == "notice" and ev.data.get("omen"):
            m = self.query_one(Masthead)
            head = ev.text.split(". ")[0]
            m.notice = f"{head}. {ev.data.get('effect', '')}"
            m.refresh()
        parley = F.parley_entry(ev)
        if parley is not None:
            self.query_one("#parley", RichLog).write(parley)
            if self._panel != "parley" and self.size.width < 112:
                self._unread += 1
            return
        entry = F.stage_entry(ev)
        if entry is not None:
            self.query_one("#stage", RichLog).write(entry)
        if k == "ending" and not self.game.rules.endless:
            self.finished = True
            self.thinking = ""
            self._refresh_status()

    # ------------------------------------------------------------------- status -------
    def _flash(self, message: str) -> None:
        self._flash_text, self._flash_until = message, time.time() + 3.5
        self._refresh_status()

    def _refresh_status(self) -> None:
        bar = self.query_one(StatusBar)
        now = time.time()
        left = Text()
        if getattr(self, "_flash_until", 0) > now:
            left.append(self._flash_text, style=C["text"])
        elif self.failed:
            left.append("The arena stopped.", style=f"bold {C['danger']}")
            left.append("  " + self.failed, style=C["muted"])
        elif self.finished:
            left.append("The season is over.", style=f"bold {C['text']}")
            if self.chronicle_path:
                left.append(f"  Chronicle saved to {self.chronicle_path}.", style=C["muted"])
            left.append("  Press q to leave.", style=C["muted"])
        elif self.game.paused:
            left.append("Paused.", style=f"bold {C['ember']}")
            left.append("  The current model call finishes first. Press p to resume.", style=C["muted"])
        elif self.think_what and self._started:
            waited = int(now - self.think_since)
            left.append(self.think_what, style=C["text"])
            left.append(f"  {waited}s", style=C["faint"])
            if waited >= 45:
                left.append("  Still waiting. A model that has not been used yet can take a minute to load.", style=C["muted"])
        else:
            left.append("Ready.", style=C["muted"])
        pace = PACES[self._pace_i]
        hints = f"p pause   m models   t theatre   c panel{f' ({self._unread} new)' if self._unread else ''}   - + {pace / NATURAL_PACE:.1f}x   q leave"
        bar.set(left, hints)

    # ------------------------------------------------------------------- actions ------
    def action_pause(self) -> None:
        if self.finished:
            return
        if self.game.paused:
            self.game.resume()
        else:
            self.game.pause()
        self._refresh_status()

    def action_pace(self, direction: int) -> None:
        self._pace_i = max(0, min(len(PACES) - 1, self._pace_i + int(direction)))
        self.query_one(Theatre).speed = PACES[self._pace_i] / NATURAL_PACE
        self._refresh_status()

    def action_leave(self) -> None:
        if self.finished or time.time() - self._quit_armed < 3.0:
            self.game.stop()
            self.exit()
            return
        self._quit_armed = time.time()
        self._flash("Press q again to leave. The season is saved after every cycle.")
