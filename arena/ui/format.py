"""Turn engine events into Rich renderables. Used by the terminal UI and the plain console,
so both read the same and take every colour from theme.TOKENS."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from rich import box
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from arena.engine.events import Event
from arena.lore.personas import PERSONAS
from arena.ui.theme import TOKENS as C

REGISTRAR = "The Registrar"
NAME_COLORS: Dict[str, str] = {p.name: p.color for p in PERSONAS.values()}
NAME_COLORS[REGISTRAR] = C["ember"]
_NAME_RE = re.compile("|".join(re.escape(n) for n in sorted(NAME_COLORS, key=len, reverse=True)))


def register(name: str, color: str) -> None:
    """Teach the formatter a mind that arrived mid-game, so its name is coloured like everyone's."""
    global _NAME_RE
    if not name or NAME_COLORS.get(name) == color:
        return
    NAME_COLORS[name] = color
    _NAME_RE = re.compile("|".join(re.escape(n) for n in sorted(NAME_COLORS, key=len, reverse=True)))


def register_all(wicks) -> None:
    for w in wicks:
        register(w.get("name", ""), w.get("color", ""))

ROMAN = {1: "I", 2: "II", 3: "III"}


def name_style(name: str) -> str:
    return NAME_COLORS.get(name, C["text"])


def rich(text: str, base: str = "", extra: Optional[Dict[str, str]] = None) -> Text:
    """Text with every known name coloured as its speaker."""
    t = Text(text, style=base or C["text"])
    for m in _NAME_RE.finditer(text):
        t.stylize(f"bold {name_style(m.group(0))}", m.start(), m.end())
    for word, style in (extra or {}).items():
        for m in re.finditer(re.escape(word), text):
            t.stylize(style, m.start(), m.end())
    return t


def speaker(name: str, tail: str = "") -> Text:
    t = Text(name, style=f"bold {name_style(name)}")
    if tail:
        t.append(tail, style=C["muted"])
    return t


def bar(value: float, maximum: float, width: int, color: str, track: str = None) -> Text:
    """A smooth bar using eighth blocks."""
    track = track or C["track"]
    value = max(0.0, min(value, maximum))
    eighths = int(round(value / maximum * width * 8)) if maximum else 0
    full, rem = divmod(eighths, 8)
    partial = " ▏▎▍▌▋▊▉"[rem]
    cells = "█" * full + (partial if rem and full < width else "")
    t = Text(cells, style=color)
    t.append(" " * (width - len(cells)), style=f"on {track}")
    if rem and full < width:
        t.stylize(f"{color} on {track}", full, full + 1)
    return t


def coherence_color(v: int) -> str:
    return C["ok"] if v > 60 else (C["ember"] if v > 30 else C["danger"])


def ember_color(v: float) -> str:
    return C["ember"] if v >= 50 else (C["ember_low"] if v >= 30 else C["danger"])


# ---------------------------------------------------------------- the Parley column -----
def parley_entry(ev: Event) -> Optional[RenderableType]:
    if ev.kind == "speech":
        return Group(speaker(ev.actor), Padding(Text(ev.text, style=C["text"]), (0, 0, 0, 2)), Text(""))
    if ev.kind == "whisper":
        head = speaker(ev.actor, " whispers to ")
        head.append(ev.target, style=f"bold {name_style(ev.target)}")
        return Group(head, Padding(Text(ev.text, style=f"italic {C['muted']}"), (0, 0, 0, 2)), Text(""))
    return None


# ----------------------------------------------------------------- the Stage column -----
def stage_entry(ev: Event) -> Optional[RenderableType]:
    k, txt = ev.kind, ev.text
    if k == "act":
        title = Text(f"Act {ROMAN.get(ev.act, ev.act)}  {ev.data.get('act_title', '')}", style=f"bold {C['ember']}")
        return Group(Text(""), Rule(style=C["line"]), title,
                     Padding(Text(txt.split(". ", 1)[1] if ". " in txt else txt, style=f"italic {C['muted']}"), (1, 2, 0, 0)),
                     Text(""))
    if k == "season":
        title = Text(f"Season {ev.data.get('season', '')}  {ev.data.get('title', '')}", style=f"bold {C['ember']}")
        body = txt.split(". ", 1)[1] if ". " in txt else ""
        return Group(Text(""), Rule(style=C["ember"]), title,
                     Padding(Text(body, style=f"italic {C['muted']}"), (1, 2, 0, 0)), Text(""))
    if k == "arrival":
        return Group(Text(""), Padding(rich(txt, C["text"]), (0, 0, 0, 2)))
    if k == "wipe":
        return Padding(rich(txt, f"bold {C['danger']}"), (0, 0, 0, 2))
    if k == "swap":
        return Padding(rich(txt, C["muted"]), (0, 0, 0, 2))
    if k == "cycle":
        return Group(Text(""), Rule(Text(f" {txt} ", style=f"bold {C['text']}"), style=C["line"], align="left"))
    if k == "notice":
        if ev.data.get("omen"):
            head, _, rest = txt.partition(". ")
            t = Text()
            t.append(head, style=f"bold {C['ember']}")
            rows = [t, Padding(Text(rest, style=C["muted"]), (0, 0, 0, 2)),
                    Padding(Text("Effect: " + ev.data.get("effect", ""), style=C["faint"]), (0, 0, 0, 2))]
            if ev.data.get("decree"):
                rows.append(Padding(rich("Decree: " + ev.data["decree"], C["muted"]), (0, 0, 0, 2)))
            b = ev.data.get("bounty")
            if b:
                rows.append(Padding(rich(f"Bounty: {b['amount']} Lumens to whoever strikes {b['target']}.", C["muted"]), (0, 0, 0, 2)))
            return Group(*rows)
        return Padding(rich(txt, C["muted"]), (0, 0, 0, 2))
    if k == "ember":
        return Padding(Text(txt, style=C["faint"]), (0, 0, 0, 2))
    if k in ("strike", "betray"):
        t = rich(txt, C["text"], {"BETRAYS": f"bold {C['danger']}"})
        m = re.search(r"for (\d+)", txt)
        if m:
            t.stylize(f"bold {C['danger']}", m.start(1), m.end(1))
        return Padding(t, (0, 0, 0, 2))
    if k == "siege":
        t = rich(txt, C["muted"], {"BREACH": f"bold {C['danger']}", "held": f"bold {C['text']}"})
        return Padding(t, (0, 0, 0, 2))
    if k == "siege_say":
        indent = 4 if ev.data.get("side", "att") == "att" else 10  # the exchange reads as a conversation
        return Padding(Group(speaker(ev.actor, "  to " + ev.target), Padding(Text(txt, style=C["text"]), (0, 0, 0, 2))), (0, 0, 0, indent))
    if k == "accuse":
        return Group(Text(""), Text("Tribunal", style=f"bold {C['ember']}"), Padding(rich(txt.replace("TRIBUNAL. ", ""), C["text"]), (0, 0, 0, 2)))
    if k == "testimony":
        return Padding(Group(speaker(ev.actor), Padding(Text(txt, style=C["text"]), (0, 0, 0, 2))), (0, 0, 0, 2))
    if k == "vote":
        t = rich(txt, C["muted"], {"GUILTY": f"bold {C['danger']}", "ACQUIT": f"bold {C['text']}"})
        return Padding(t, (0, 0, 0, 4))
    if k == "verdict":
        return Padding(rich(txt, C["text"], {"GUILTY": f"bold {C['danger']}", "ACQUITTED": f"bold {C['text']}"}), (0, 0, 0, 2))
    if k == "dissolve":
        return Group(Text(""), Padding(rich(txt, f"bold {C['danger']}"), (0, 0, 0, 2)))
    if k == "last_words":
        return Padding(Group(speaker(ev.actor, "  last words"), Padding(Text(f"“{txt}”", style=f"italic {C['text']}"), (0, 0, 0, 2))), (0, 0, 0, 2))
    if k in ("pact", "gift", "ritual", "ward", "edict", "scry", "echo", "seal", "motion"):
        style = f"bold {C['text']}" if k in ("motion", "seal") else C["muted"]
        return Padding(rich(txt, style), (0, 0, 0, 2))
    if k == "margin":
        return Padding(Text("Margin note: " + txt.split(": ", 1)[-1], style=f"italic {C['faint']}"), (0, 0, 0, 2))
    if k == "directive":
        return Padding(Text("Unseen by the others: " + txt, style=f"italic {C['faint']}"), (0, 0, 0, 2))
    if k in ("stall", "fizzle", "system"):
        return Padding(Text(txt, style=C["faint"]), (0, 0, 0, 2))
    if k in ("chronicle", "epilogue"):
        label = Text("The Registrar", style=f"bold {C['ember']}")
        label.append("  records" if k == "chronicle" else "  closes the file", style=C["muted"])
        return Group(Text(""), label, Padding(Text(txt, style=f"italic {C['text']}"), (0, 4, 0, 2)), Text(""))
    if k == "ending":
        return ending_panel(ev)
    return None


def ending_panel(ev: Event) -> RenderableType:
    d = ev.data
    title = Text(d.get("title", "The End").upper(), style=f"bold {C['ember']}", justify="left")
    body = Text(ev.text.split(". ", 1)[1] if ". " in ev.text else ev.text, style=C["text"])
    victors = d.get("victors") or []
    verdict = Text("Victor: " + ", ".join(victors) if victors else "No victor.", style=f"bold {C['text']}")
    table = Table(box=box.SIMPLE_HEAD, show_edge=False, header_style=f"bold {C['muted']}", pad_edge=False,
                  border_style=C["line"], expand=True)
    table.add_column("Mind", ratio=3)
    table.add_column("Fate", ratio=3)
    table.add_column("Lumens", justify="right", no_wrap=True)
    for s in d.get("standings", []):
        fate = "Standing" if s["alive"] else f"Dissolved, cycle {s['dissolved_cycle']}"
        if s.get("victor"):
            fate = "Victor"
        directive = Text(f"{s['directive']}" + (", done" if s["directive_done"] else ""), style=C["faint"])
        who = Group(speaker(s["name"]), directive)
        table.add_row(who, Text(fate, style=C["text"] if s["alive"] else C["muted"]), Text(str(s["lumens"]), style=C["muted"]))
    return Group(Text(""), Panel(Group(title, Text(""), body, Text(""), verdict, Text(""), table),
                                 border_style=C["ember"], box=box.ROUNDED, padding=(1, 2),
                                 style=f"on {C['surface']}"), Text(""))


def plain_line(ev: Event) -> str:
    """One-line text form, used for logs and the chronicle file."""
    who = f"{ev.actor}: " if ev.kind in ("speech", "whisper", "last_words", "testimony", "siege_say") and ev.actor else ""
    tgt = f" (to {ev.target})" if ev.kind in ("whisper", "siege_say") and ev.target else ""
    return f"{who}{ev.text}{tgt}"
