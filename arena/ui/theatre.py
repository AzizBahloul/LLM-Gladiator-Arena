"""The Theatre: animated 2D pixel figures that act out what the minds do.

Everything on screen is a pure function of (scene state, time t): figures are built from a
procedural pixel skeleton, posed from the queue of "beats" (one per engine event), and drawn
with the half-block technique (each terminal cell is two vertical pixels: the upper half-block
glyph with the upper pixel as foreground and the lower pixel as background).

Colour comes only from arena.ui.theme plus each mind's own persona colour.
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from rich.style import Style
from rich.cells import cell_len
from rich.text import Text
from textual.widget import Widget

from arena.engine.events import Event
from arena.ui.format import coherence_color
from arena.ui.theme import TOKENS as C

RGB = Tuple[int, int, int]
MIN_COLS, MIN_ROWS = 44, 12


# ============================================================================ colour ====
def hx(s: str) -> RGB:
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def to_hex(c: RGB) -> str:
    return "#%02x%02x%02x" % (max(0, min(255, c[0])), max(0, min(255, c[1])), max(0, min(255, c[2])))


def mix(a: RGB, b: RGB, t: float) -> RGB:
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


BG, SURFACE, RAISED, LINE = hx(C["bg"]), hx(C["surface"]), hx(C["raised"]), hx(C["line"])
TEXT, MUTED, FAINT = hx(C["text"]), hx(C["muted"]), hx(C["faint"])
EMBER, EMBER_LOW, DANGER, OK, TRACK = hx(C["ember"]), hx(C["ember_low"]), hx(C["danger"]), hx(C["ok"]), hx(C["track"])
BLACK = (0, 0, 0)
SKIN = (208, 184, 156)
PALE = (232, 222, 200)
METAL = (74, 68, 58)
GHOST_TINT = (176, 168, 214)


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def smooth(x: float) -> float:
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def hash01(*vals: int) -> float:
    h = 2166136261
    for v in vals:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFF) / 65535.0


def name_hash(name: str) -> int:
    h = 0
    for ch in name:
        h = (h * 131 + ord(ch)) & 0xFFFFFF
    return h


# ============================================================================== model ====
@dataclass
class Figure:
    name: str
    persona_id: str = ""
    color: str = "#c8b88a"
    model: str = ""
    coherence: int = 100
    alive: bool = True
    echo: int = 0
    ward: bool = False
    partner: Optional[str] = None
    warden: bool = False
    faded_at: Optional[float] = None
    born_at: float = -1e9
    slot: int = 0


@dataclass
class Beat:
    kind: str
    start: float
    dur: float
    actor: str = ""
    target: str = ""
    text: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def end(self) -> float:
        return self.start + self.dur


# How long each kind of event holds the screen, in seconds at speed 1.0.
def hold_time(ev: Event) -> float:
    k, n = ev.kind, len(ev.text or "")
    if k == "speech":
        return max(1.2, min(2.4, 1.0 + n * 0.022))
    if k == "whisper":
        return max(1.0, min(1.8, 0.9 + n * 0.018))
    if k in ("strike",):
        return 1.4
    if k == "betray":
        return 1.6
    if k == "siege_say":
        return max(1.2, min(1.8, 1.0 + n * 0.02))
    if k == "testimony":
        return max(1.2, min(2.0, 1.0 + n * 0.02))
    if k == "last_words":
        return max(1.4, min(2.2, 1.2 + n * 0.02))
    return {
        "ward": 0.8, "siege": 1.0, "pact": 1.2, "gift": 1.0, "scry": 1.0, "ritual": 1.4, "accuse": 1.4,
        "vote": 0.5, "verdict": 1.4, "dissolve": 2.4, "echo": 1.2, "edict": 1.2, "motion": 1.2, "seal": 0.6,
        "act": 1.6, "notice": 0.5, "ending": 3.0, "chronicle": 0.8, "epilogue": 0.6, "margin": 0.5,
        "directive": 0.3, "stall": 0.6, "fizzle": 0.6, "ember": 0.3,
        "arrival": 2.0, "wipe": 2.2, "swap": 1.4, "season": 2.4,
        "faith": 1.3, "broadcast": 1.5, "campaign": 1.1, "ballot": 0.4, "election": 1.8, "prayer": 1.2, "miracle": 3.2,
    }.get(k, 0.0)


DROPPABLE_FIRST = ("vote", "ballot", "stall", "fizzle", "margin", "directive", "ember", "seal", "scry", "gift", "edict", "prayer")
DROPPABLE_THEN = ("speech", "whisper", "siege_say", "testimony", "pact", "ward", "echo", "motion", "faith", "broadcast", "campaign")
NEVER_DROP = ("dissolve", "ending", "act", "arrival", "wipe", "season", "miracle", "election")
UNQUEUED = ("think", "state", "cycle", "income", "system", "title")
MAX_PENDING = 10


class Scene:
    """Everything the Theatre needs to draw a frame. No Textual types in here."""

    def __init__(self) -> None:
        self.figures: Dict[str, Figure] = {}
        self.order: List[str] = []
        self.ember = 100.0
        self.act = 1
        self.omen = ""
        self.ending: Optional[Tuple[str, float, List[str]]] = None
        self.beats: List[Beat] = []
        self.now = 0.0
        self.speed = 1.0
        self.thinking: Optional[Tuple[str, float]] = None
        self.last_speaker: Optional[Tuple[str, str, float]] = None
        self._tail = 0.0
        self.dropped = 0

    # -- cast and state --------------------------------------------------------------
    def set_cast(self, wicks: Iterable[Dict[str, Any]]) -> None:
        self.set_state({"wicks": list(wicks)})

    def set_state(self, snap: Dict[str, Any]) -> None:
        if "ember" in snap:
            self.ember = float(snap["ember"])
        if "act" in snap:
            self.act = int(snap["act"])
        if "omen" in snap:
            self.omen = snap.get("omen") or ""
        if snap.get("ending") and not self.ending:
            self.ending = (snap["ending"], -1e9, [])
        first = not self.figures
        for i, w in enumerate(snap.get("wicks", [])):
            f = self.figures.get(w["name"])
            if f is None:
                f = Figure(w["name"], born_at=-1e9 if first else self.now)
                self.figures[f.name] = f
                self.order.append(f.name)
            was_faded = (not f.alive) and f.echo == 0
            f.persona_id = w.get("persona_id") or f.persona_id
            f.color = w.get("color") or f.color
            f.model = w.get("model", f.model)
            f.coherence = int(w.get("coherence", f.coherence))
            f.alive = bool(w.get("alive", f.alive))
            f.echo = int(w.get("echo", f.echo))
            f.ward = bool(w.get("ward", f.ward))
            f.partner = w.get("partner")
            f.warden = bool(w.get("warden", f.warden))
            f.slot = i
            if not f.alive and f.echo == 0 and not was_faded and f.faded_at is None and not first:
                f.faded_at = self.now
        if snap.get("wicks") and not first:
            gone = [n for n in self.figures if n not in {w["name"] for w in snap["wicks"]}]
            for n in gone:                # a mind removed between seasons leaves the stage for good
                del self.figures[n]
                self.order.remove(n)

    # -- events ----------------------------------------------------------------------
    def on_event(self, ev: Event) -> float:
        """Record an event as a beat and return how long it should hold the screen."""
        k = ev.kind
        if k == "think":
            self.thinking = (ev.actor, self.now) if ev.actor and ev.actor in self.figures else None
            return 0.0
        if k == "state":
            if ev.data.get("snapshot"):
                self.set_state(ev.data["snapshot"])
            return 0.0
        if k in ("speech", "whisper") and ev.actor in self.figures:
            self.last_speaker = (ev.actor, self.figures[ev.actor].color, self.now)
        if self.thinking and ev.actor == self.thinking[0]:
            self.thinking = None
        dur = hold_time(ev) * self.speed
        if k in UNQUEUED:
            return 0.0
        if k == "season":
            self.ending = None            # an endless run carries on after an ending
        if k == "ending":
            data = dict(ev.data)
            self.ending = (str(data.get("ending", "")), max(self.now, self._tail), list(data.get("victors") or []))
        beat = Beat(k, 0.0, max(dur, 0.05), ev.actor, ev.target, ev.text, dict(ev.data))
        beat.data["_act"] = ev.act
        beat.start = max(self.now, self._tail)
        self.beats.append(beat)
        self._tail = beat.end
        self._cap()
        self.beats = [b for b in self.beats if b.end > self.now - 60.0]
        return dur

    def _pending(self) -> List[Beat]:
        return [b for b in self.beats if b.start > self.now]

    def _cap(self) -> None:
        for kinds in (DROPPABLE_FIRST, DROPPABLE_THEN):
            while len(self._pending()) > MAX_PENDING:
                victim = next((b for b in self._pending() if b.kind in kinds), None)
                if victim is None:
                    break
                self.beats.remove(victim)
                self.dropped += 1
                self._retime()
        # a hard ceiling: drop the oldest pending beat that is not protected
        while len(self._pending()) > MAX_PENDING * 2:
            victim = next((b for b in self._pending() if b.kind not in NEVER_DROP), None)
            if victim is None:
                break
            self.beats.remove(victim)
            self.dropped += 1
            self._retime()

    def _retime(self) -> None:
        running_end = max([b.end for b in self.beats if b.start <= self.now] + [self.now])
        for b in self.beats:
            if b.start > self.now:
                b.start = running_end
                running_end = b.end
        self._tail = running_end


# ============================================================================= canvas ====
class Canvas:
    def __init__(self, base: List[List[RGB]]):
        self.px = [row[:] for row in base]
        self.h = len(self.px)
        self.w = len(self.px[0]) if self.px else 0

    def put(self, x: int, y: int, c: RGB, a: float = 1.0) -> None:
        if 0 <= x < self.w and 0 <= y < self.h and a > 0:
            self.px[y][x] = c if a >= 1.0 else mix(self.px[y][x], c, a)

    def rect(self, x0: int, y0: int, x1: int, y1: int, c: RGB, a: float = 1.0) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, c, a)

    def line(self, x0: int, y0: int, x1: int, y1: int, c: RGB, a: float = 1.0) -> None:
        for x, y in line_pts(x0, y0, x1, y1):
            self.put(x, y, c, a)

    def tint(self, c: RGB, a: float) -> None:
        for y in range(self.h):
            row = self.px[y]
            for x in range(self.w):
                row[x] = mix(row[x], c, a)

    def dim(self, f: float, keep: Optional[Tuple[int, int, int]] = None) -> None:
        """Darken everything; keep=(cx, cy, r) leaves a lit circle undimmed."""
        for y in range(self.h):
            row = self.px[y]
            for x in range(self.w):
                k = f
                if keep:
                    d = math.hypot(x - keep[0], y - keep[1])
                    if d < keep[2]:
                        k = f + (1 - f) * (1 - d / keep[2])
                row[x] = (int(row[x][0] * k), int(row[x][1] * k), int(row[x][2] * k))


def line_pts(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    for _ in range(400):
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


_BG_CACHE: Dict[Tuple[int, int], List[List[RGB]]] = {}


def background(cols: int, rows: int) -> List[List[RGB]]:
    """The archive: a back wall of cabinets and a dark floor strip. Cached per size."""
    key = (cols, rows)
    if key in _BG_CACHE:
        return _BG_CACHE[key]
    P = rows * 2
    floor_y = P - 4
    wall = mix(BG, SURFACE, 0.9)
    cab = mix(wall, LINE, 0.42)
    cab_hi = mix(cab, LINE, 0.55)
    floor = mix(BG, BLACK, 0.35)
    px = [[wall] * cols for _ in range(P)]
    for y in range(P):
        k = 0.78 + 0.22 * (y / max(1, floor_y))
        for x in range(cols):
            px[y][x] = mix(BLACK, wall, k) if y < floor_y else wall
    x, i = 0, 0
    while x < cols:
        w = 7 + (i * 5) % 5
        h = int(floor_y * (0.5 + 0.36 * hash01(i, 7)))
        top = floor_y - h
        for xx in range(x, min(cols, x + w - 1)):
            for yy in range(top, floor_y):
                c = cab
                if (yy - top) % 5 == 0:
                    c = cab_hi
                elif xx == x or xx == x + w - 2:
                    c = mix(cab, BLACK, 0.25)
                px[yy][xx] = c
            if top > 0 and x + w // 2 - 1 <= xx <= x + w // 2:
                pass
        hx_ = x + (w - 1) // 2
        for yy in range(top + 2, floor_y, 5):
            if hx_ < cols:
                px[yy][hx_] = FAINT if hash01(i, yy) > 0.6 else cab_hi
        x += w
        i += 1
    for y in range(floor_y, P):
        for x in range(cols):
            c = floor
            if y == floor_y:
                c = mix(LINE, floor, 0.35)
            elif (x + y * 3) % 17 == 0:
                c = mix(floor, LINE, 0.25)
            px[y][x] = c
    _BG_CACHE[key] = px
    return px


# ============================================================================= layout ====
@dataclass
class Layout:
    cols: int
    rows: int
    P: int
    cx: int
    feet_y: int
    floor_y: int
    lamp_y: int
    home: Dict[str, int]
    arc: Dict[str, int]
    room: Dict[str, int]  # horizontal room (columns) available for each name tag


def compute_layout(cols: int, rows: int, names: List[str]) -> Layout:
    P = rows * 2
    cx = cols // 2
    n = len(names)
    left_n, right_n = (n + 1) // 2, n // 2
    gap = 7 if n <= 6 else 3
    pad = 3
    home: Dict[str, int] = {}

    def place(group: List[str], lo: int, hi: int) -> None:
        k = len(group)
        for j, nm in enumerate(group):
            home[nm] = int(lo + (hi - lo) * ((j + 0.5) / k)) if k else lo

    place(names[:left_n], pad + 4, cx - gap)
    place(names[left_n:], cx + gap, cols - pad - 4)
    xs = sorted(home.values())
    arc: Dict[str, int] = {}
    room: Dict[str, int] = {}
    # when minds stand closer than a sprite is wide, every other one steps back a row
    ordered = sorted(home, key=lambda n: home[n])
    tight = len(xs) > 1 and min(b_ - a_ for a_, b_ in zip(xs, xs[1:])) < 7 and rows >= 14
    back = {nm for j, nm in enumerate(ordered) if tight and j % 2 == 1}
    for nm, x in home.items():
        u = abs(x - cx) / max(1, cx)
        arc[nm] = int(round(2 * u * u)) + (3 if nm in back else 0)
        neigh = [abs(x - o) for o in xs if o != x]
        room[nm] = max(3, min(neigh) - 1) if neigh else 14
    lamp_y = max(6, min(16, int(P * 0.28)))
    return Layout(cols, rows, P, cx, P - 5, P - 4, lamp_y, home, arc, room)


# =============================================================================== poses ====
@dataclass
class FS:
    x: float
    y: float = 0.0
    bob: int = 0
    lean: int = 0
    hdx: int = 0
    armL: float = 8.0
    armR: float = 8.0
    mouth: bool = False
    walk: int = -1
    shrug: bool = False
    flash: float = 0.0
    shield: float = 0.0
    alpha: float = 1.0
    spot: bool = False
    hit_dx: float = 0.0


KNOWN = ("vellum", "glitchwick", "aurelia", "rictus", "jester9", "sage", "rust", "understudy")
ACC_TOP = {"vellum": 4, "glitchwick": 2, "aurelia": 1, "rictus": 0, "jester9": 4, "sage": 0, "rust": 0,
           "understudy": 0, "guest": 2}


def persona_key(f: Figure) -> str:
    return f.persona_id if f.persona_id in KNOWN else "guest"


def walk_frac(p: float, t_in: float, t_hold_end: float, t_back_end: float = 1.0) -> float:
    """0 -> 1 over [0, t_in], hold until t_hold_end, then 1 -> 0 by t_back_end."""
    if p < t_in:
        return smooth(p / t_in)
    if p < t_hold_end:
        return 1.0
    return 1.0 - smooth((p - t_hold_end) / max(1e-6, t_back_end - t_hold_end))


@dataclass
class Fx:
    """Effects collected while posing, drawn after the figures."""
    items: List[Tuple[str, Any]] = field(default_factory=list)

    def add(self, kind: str, *args: Any) -> None:
        self.items.append((kind, args))


class Poser:
    def __init__(self, scene: Scene, lay: Layout, t: float):
        self.scene, self.lay, self.t = scene, lay, t
        self.fx = Fx()
        self.diss: Dict[str, float] = {}
        for b in scene.beats:
            if b.kind == "dissolve" and b.actor:
                self.diss[b.actor] = b.start
        self.siege = self._siege_state()
        self.trial = self._trial_state()

    # engaged states derived from the beat list -----------------------------------------
    def _siege_state(self) -> Optional[Dict[str, Any]]:
        t = self.t
        st = None
        for b in self.scene.beats:
            if b.start > t:
                break
            if b.kind != "siege":
                continue
            low = b.text
            if "lays siege" in low:
                st = {"a": b.actor, "d": b.target, "since": b.start, "end": None, "result": None, "cracked": None}
            elif st and (low.startswith("BREACH") or " held." in low):
                st["end"] = b.start + b.dur
                st["result"] = "breach" if low.startswith("BREACH") else "held"
            elif st and ("outright" in low or "aloud" in low):
                st["cracked"] = b.start
        if st and st["end"] is not None and t > st["end"] + 0.2:
            return None
        if st and st["end"] is None and t - st["since"] > 90:
            return None
        return st

    def _trial_state(self) -> Optional[Dict[str, Any]]:
        t = self.t
        st = None
        for b in self.scene.beats:
            if b.start > t:
                break
            if b.kind == "accuse":
                st = {"acc": b.actor, "dfn": b.target, "since": b.start, "end": None, "votes": {}, "speaker": None}
            elif st and b.kind == "testimony":
                st["speaker"] = b.actor
            elif st and b.kind == "vote":
                st["votes"][b.actor] = ("G" if "GUILTY" in b.text else "A")
            elif st and b.kind == "verdict":
                st["end"] = b.start + b.dur
        if st and st["end"] is not None and t > st["end"]:
            return None
        return st

    # visual life ------------------------------------------------------------------------
    def visually_alive(self, f: Figure) -> bool:
        if f.alive:
            return True
        s = self.diss.get(f.name)
        return s is not None and self.t < s

    def pose(self, f: Figure, idx: int) -> FS:
        t, lay, scene = self.t, self.lay, self.scene
        home = lay.home.get(f.name, lay.cx)
        ph = (idx * 1.7) % 6.28
        fs = FS(float(home))
        fs.armL = 8 + 5 * math.sin(t * 1.7 + ph)
        fs.armR = 8 + 5 * math.sin(t * 1.9 + ph + 1.1)
        fs.bob = 1 if math.sin(t * 2.2 + ph) > 0.55 else 0
        sgn = 1 if home < lay.cx else -1
        frozen = bool(scene.ending and scene.ending[0] in ("clerical", "backlog") and t >= scene.ending[1] + 0.8)
        if frozen:
            fs.armL = fs.armR = 8
            fs.bob = 0
        if not self.visually_alive(f):
            self._ghost_pose(f, fs, home)
            return fs

        # engaged: a siege holds both minds face to face for as long as it lasts
        if self.siege and f.name in (self.siege["a"], self.siege["d"]):
            a, d = self.siege["a"], self.siege["d"]
            ax, dx_ = lay.home.get(a, home), lay.home.get(d, home)
            towards = 1 if dx_ > ax else -1
            if f.name == a:
                dest = dx_ - towards * 15
                fs.x = home + (dest - home) * smooth((t - self.siege["since"]) / 0.5)
                fs.lean = towards
                fs.armR = 70
            else:
                fs.x = home + (-towards * 0) * 0
                fs.lean = -towards
                fs.armL = 50
            if self.siege["end"] is not None:
                back = smooth((t - self.siege["end"]) / 0.6)
                if f.name == a:
                    fs.x = home + (fs.x - home) * (1 - back)
        # engaged: a trial spotlights the accuser and the accused
        if self.trial and f.name in (self.trial["acc"], self.trial["dfn"]):
            mid = lay.cx + (-10 if f.name == self.trial["acc"] else 10)
            k = smooth((t - self.trial["since"]) / 0.5)
            fs.x = home + (mid - home) * k
            fs.spot = True
            if self.trial["speaker"] == f.name:
                fs.armR = 60 + 25 * math.sin(t * 6)
                fs.mouth = math.sin(t * 15) > 0
        elif self.trial and self.trial["speaker"]:
            sp = lay.home.get(self.trial["speaker"], lay.cx)
            fs.hdx = 1 if sp > fs.x else -1

        for b in scene.beats:
            if b.start - 0.02 > t:
                break
            if t > b.end + 0.5:
                continue
            p = (t - b.start) / b.dur
            if f.name == b.actor:
                self._actor(f, fs, b, p, home, sgn)
            if f.name == b.target:
                self._target(f, fs, b, p, home, sgn)
            if b.kind == "motion" and 0 <= p <= 1.2:
                fs.armL = fs.armR = 150
            if b.kind == "miracle" and 0.05 <= p <= 1.0:
                fs.armL = fs.armR = 170 + 6 * math.sin(t * 4 + idx)      # everyone looks up
                fs.y = -1 * smooth(math.sin(math.pi * clamp01(p)))
        if self.trial and f.name in self.trial["votes"]:
            self.fx.add("vote", f.name, self.trial["votes"][f.name])
        if f.ward and not fs.shield:
            fs.shield = 0.45
        if fs.walk == -1 and abs(fs.x - home) > 0.6 and not (self.siege and f.name == self.siege["d"]):
            fs.walk = int(t * 9) % 4
        return fs

    def _ghost_pose(self, f: Figure, fs: FS, home: int) -> None:
        t = self.t
        for b in self.scene.beats:
            if b.start - 0.02 > t or t > b.end + 0.3:
                continue
            p = (t - b.start) / b.dur
            if b.kind == "echo" and b.actor == f.name:
                tx = self.lay.home.get(b.target, home)
                fs.x = home + (tx - (8 if tx > home else -8) - home) * walk_frac(p, 0.4, 0.7)
                self.fx.add("echo", f.name, b.target, p, "BLESS" if "blesses" in b.text else "HEX")
            if b.kind == "last_words" and b.actor == f.name:
                fs.y = -3 * smooth(p * 2)

    # per-kind acting -------------------------------------------------------------------
    def _actor(self, f: Figure, fs: FS, b: Beat, p: float, home: int, sgn: int) -> None:
        t, lay = self.t, self.lay
        k = b.kind
        tx = lay.home.get(b.target, lay.cx)
        toward = 1 if tx > home else -1
        if k in ("speech", "testimony", "last_words"):
            fs.mouth = p < 0.88 and math.sin(t * 16) > 0
            fs.armR = 40 + 30 * math.sin(t * 6)
        elif k == "siege_say":
            fs.mouth = p < 0.88 and math.sin(t * 16) > 0
            fs.armR = 60 + 25 * math.sin(t * 7)
        elif k == "whisper":
            fr = walk_frac(p, 0.3, 0.75)
            fs.x = home + (tx - toward * 7 - home) * fr
            fs.lean = toward if 0.3 < p < 0.75 else 0
            fs.mouth = 0.3 < p < 0.75 and math.sin(t * 12) > 0
            if 0 < fr < 1:
                fs.walk = int(t * 9) % 4
        elif k in ("strike", "betray"):
            if p < 0.32:
                fr = smooth(p / 0.32)
            elif p < 0.70:
                fr = 1.0
            else:
                fr = 1 - smooth((p - 0.70) / 0.30)
            fs.x = home + (tx - toward * 8 - home) * fr
            if 0 < fr < 1:
                fs.walk = int(t * 9) % 4
            if 0.32 <= p < 0.42:
                fs.armR = 160
                fs.lean = -toward
            elif 0.42 <= p < 0.62:
                fs.armR = 100
                fs.lean = toward
                fs.x += toward * 2
                if p < 0.5:
                    self.fx.add("flash", f.name, b.target, (p - 0.42) / 0.08)
            fs.mouth = 0.42 <= p < 0.6
        elif k == "ward":
            fs.armL, fs.armR = 150, 150
            fs.shield = max(fs.shield, 1.0 - 0.5 * smooth(p))
        elif k == "pact":
            if "register" in b.text:
                fr = walk_frac(p, 0.4, 1.0, 1.0)
                fs.x = home + (tx - toward * 9 - home) * fr
                if 0 < fr < 1:
                    fs.walk = int(t * 9) % 4
                fs.armR = 80 if p > 0.4 else fs.armR
            elif "offers" in b.text:
                fs.armR = 85
                fs.lean = toward
            elif "leaves" in b.text:
                fs.armL = 120
                fs.lean = -toward
        elif k == "gift":
            fs.armR = 90 if p < 0.7 else 20
            fs.lean = toward if p < 0.6 else 0
            self.fx.add("coins", f.name, b.target, p)
        elif k == "scry":
            fs.lean = toward
            fs.armR = 130
        elif k == "ritual":
            lampx = lay.cx
            stop = lampx - (10 if home < lampx else -10)
            fr = walk_frac(p, 0.35, 0.65)
            fs.x = home + (stop - home) * fr
            if 0 < fr < 1:
                fs.walk = int(t * 9) % 4
            if 0.35 <= p < 0.65:
                fs.armR = 130 + 25 * math.sin(t * 9)
                fs.armL = 130
                self.fx.add("sparks", f.name, (p - 0.35) / 0.3)
        elif k == "accuse":
            fs.armR = 100
            fs.mouth = math.sin(t * 15) > 0
        elif k == "verdict":
            pass
        elif k == "dissolve":
            pass
        elif k == "echo":
            pass
        elif k == "edict":
            fs.armR = 160
            self.fx.add("seal", f.name, p)
        elif k in ("stall", "fizzle"):
            fs.shrug = p < 0.9
            fs.armL, fs.armR = 70, 70
        elif k == "margin":
            self.fx.add("page", f.name, p)
        elif k == "directive":
            self.fx.add("glint", f.name, p)
        elif k == "seal":
            self.fx.add("glint", f.name, p)
        elif k == "prayer":
            fs.armL = fs.armR = 165 + 8 * math.sin(t * 5)
            fs.lean = 0
        elif k in ("broadcast", "campaign"):
            fs.armR = 100 + 20 * math.sin(t * 7)
            fs.mouth = p < 0.9 and math.sin(t * 15) > 0
        elif k == "faith":
            fs.armR = 150
            if "founds" in b.text:
                fs.armL = 150
            fs.mouth = p < 0.9 and math.sin(t * 11) > 0
            self.fx.add("glint", f.name, p)
        elif k == "chronicle":
            pass

    def _target(self, f: Figure, fs: FS, b: Beat, p: float, home: int, sgn: int) -> None:
        k = b.kind
        ax = self.lay.home.get(b.actor, self.lay.cx)
        away = 1 if home > ax else -1
        if k in ("strike", "betray"):
            if 0.5 <= p < 0.85:
                q = (p - 0.5) / 0.35
                fs.flash = max(fs.flash, 1 - q)
                fs.hit_dx = away * 2 * (1 - q)
                fs.x += fs.hit_dx
                fs.hdx = away
                dmg = b.data.get("damage")
                if dmg is None:
                    m = re.search(r"for (\d+)", b.text)
                    dmg = int(m.group(1)) if m else 0
                self.fx.add("damage", f.name, int(dmg), q)
                if "warded" in b.text or f.ward:
                    fs.shield = max(fs.shield, 1.0)
            if k == "betray" and 0.3 < p < 0.9:
                self.fx.add("snap", b.actor, f.name, p)
        elif k == "whisper":
            if 0.3 < p < 0.75:
                fs.hdx = -1 if home > ax else 1
        elif k == "scry":
            self.fx.add("eye", f.name, p)
        elif k == "gift":
            pass
        elif k == "echo":
            if "hexes" in b.text and 0.4 < p < 1.0:
                fs.flash = max(fs.flash, 0.5)
                fs.shrug = True
            if "blesses" in b.text and 0.4 < p < 1.0:
                self.fx.add("glint", f.name, p)
        elif k == "edict":
            self.fx.add("mark", f.name, p)


# ============================================================================== sprites ====
@dataclass
class Sprite:
    px: Dict[Tuple[int, int], Tuple[RGB, float]]
    glows: List[Tuple[int, int, int, RGB, float]]
    top: int


def build_sprite(f: Figure, fs: FS, t: float, mimic: Optional[Tuple[RGB, float]] = None) -> Sprite:
    key = persona_key(f)
    col = hx(f.color)
    if key == "understudy" and mimic:
        col = mix(col, mimic[0], mimic[1])
    cloak = mix(col, BG, 0.42)
    trim = mix(col, TEXT, 0.30)
    dark = mix(col, BG, 0.74)
    skin = SKIN
    sp: Dict[Tuple[int, int], Tuple[RGB, float]] = {}
    glows: List[Tuple[int, int, int, RGB, float]] = []

    def P(x: int, y: int, c: RGB, a: float = 1.0) -> None:
        sp[(x, y)] = (c, a)

    def R(x0: int, y0: int, x1: int, y1: int, c: RGB, a: float = 1.0) -> None:
        for yy in range(y0, y1 + 1):
            for xx in range(x0, x1 + 1):
                P(xx, yy, c, a)

    b = fs.bob
    lean = fs.lean
    hxo = lean + fs.hdx
    hy = b + (1 if fs.shrug else 0)
    gh = hash01(name_hash(f.name))
    robe = key in ("vellum",)
    thin = key == "rictus"

    # wings sit behind everything
    if key == "aurelia":
        w = 2 + int(2.5 + 2.5 * math.sin(t * 9))
        wc = mix(col, TEXT, 0.35)
        for k in range(1, w + 1):
            for y in range(3 + k // 2, 10 - k // 2):
                P(1 - k + lean, y + b, wc, 0.42 if k < w else 0.25)
                P(7 + k + lean, y + b, wc, 0.42 if k < w else 0.25)

    # legs (planted unless walking)
    ph = fs.walk
    lift_l, lift_r = ph == 1, ph == 3
    if robe:
        for y, (x0, x1) in zip(range(10, 15), [(2, 6), (1, 7), (1, 7), (1, 7), (1, 7)]):
            R(x0 + lean, y + b if y < 12 else y, x1 + lean, y + b if y < 12 else y, cloak if y < 14 else dark)
        R(2 + (-1 if lift_l else 0), 15, 3, 15, skin if lift_l else dark)
        R(5, 15, 6 + (1 if lift_r else 0), 15, skin if lift_r else dark)
    else:
        lw = 1 if thin else 2
        lc = mix(cloak, BG, 0.45)
        lx = (3, 3) if thin else (2, 3)
        rx = (5, 5) if thin else (5, 6)
        R(lx[0] - (1 if lift_l else 0), 11, lx[1] - (1 if lift_l else 0), 14 if lift_l else 15, lc)
        R(rx[0] + (1 if lift_r else 0), 11, rx[1] + (1 if lift_r else 0), 14 if lift_r else 15, lc)
        P(lx[0] - (1 if lift_l else 0), 14 if lift_l else 15, trim if not lift_l else lc)
        P(rx[1] + (1 if lift_r else 0), 14 if lift_r else 15, trim if not lift_r else lc)

    # torso
    tx0, tx1 = (3, 5) if thin else (2, 6)
    if key == "rust":
        tx0, tx1 = 1, 7
    for y in range(5, 11):
        for x in range(tx0, tx1 + 1):
            c = cloak
            if y == 5:
                c = trim
            if y == 9:
                c = dark
            if key == "jester9":
                c = col if (x + y) % 2 == 0 else dark
            if key == "rust" and y >= 7:
                c = mix(METAL, BLACK, 0.2) if 2 <= x <= 6 else cloak
            if key == "sage" and 3 <= x <= 5 and 6 <= y <= 8:
                continue
            P(x + lean, y + b, c)
    if key == "sage":
        for x in range(3, 6):
            for y in range(6, 9):
                P(x + lean, y + b, col, 0.22)
    if key == "rictus":
        P(2 + lean, 10 + b, mix(EMBER, BLACK, 0.2))
        P(3 + lean, 9 + b, mix(EMBER, BLACK, 0.1))
        P(2 + lean, 9 + b, EMBER)

    # arms: a shoulder angle sweeps the hand around the shoulder (0 = hanging, 90 = out, 180 = up)
    for side, ang in ((-1, fs.armL), (1, fs.armR)):
        sx = (2 if thin else 1) + lean if side < 0 else (6 if thin else 7) + lean
        sy = 5 + b
        r = math.radians(max(0.0, min(180.0, ang)))
        L = 5
        hx_ = sx + side * int(round(L * math.sin(r)))
        hy_ = sy + int(round(L * math.cos(r)))
        for (px_, py_) in line_pts(sx, sy, hx_, hy_)[:-1]:
            P(px_, py_, cloak if (px_, py_) != (sx, sy) else trim)
        P(hx_, hy_, skin)

    # head
    head_skin = skin
    if key == "understudy":
        head_skin = (206, 206, 218)
    if key == "rictus":
        head_skin = (92, 82, 72)
    R(2 + hxo, hy, 6 + hxo, hy + 4, head_skin)
    top = hy
    eye_c = (28, 22, 18)
    blink = (t + gh * 7) % 3.7 < 0.12
    if key == "glitchwick":
        R(2 + hxo, hy, 6 + hxo, hy + 4, METAL)
        glass = mix(EMBER, TEXT, 0.35 + 0.15 * math.sin(t * 11))
        R(3 + hxo, hy + 1, 5 + hxo, hy + 3, glass)
        R(3 + hxo, hy + 3, 5 + hxo, hy + 3, mix(BG, BLACK, 0.5))
        P(2 + hxo, hy + 3, METAL)
        P(6 + hxo, hy + 3, METAL)
        P(3 + hxo, hy - 1, METAL)
        P(5 + hxo, hy - 1, METAL)
        P(4 + hxo, hy - 2, METAL)
        top = hy - 2
        glows.append((4 + hxo, hy + 2, 5, EMBER, 0.20))
    elif key == "rictus":
        R(2 + hxo, hy, 6 + hxo, hy + 4, PALE)
        P(3 + hxo, hy + 2, eye_c)
        P(5 + hxo, hy + 2, eye_c)
        for (x_, y_) in ((2, 3), (3, 4), (4, 4), (5, 4), (6, 3)):
            P(x_ + hxo, hy + y_, eye_c)
        P(7 + lean, 6 + b, METAL)
    elif key == "understudy" and not mimic:
        pass
    else:
        if blink:
            R(3 + hxo, hy + 2, 5 + hxo, hy + 2, mix(head_skin, eye_c, 0.5))
        elif key != "understudy" or mimic:
            P(3 + hxo, hy + 2, eye_c)
            P(5 + hxo, hy + 2, eye_c)
        if key != "understudy" or mimic:
            if fs.mouth:
                R(3 + hxo, hy + 3, 5 + hxo, hy + 3, eye_c)
                P(4 + hxo, hy + 4, mix(eye_c, head_skin, 0.4))
            else:
                R(4 + hxo, hy + 3, 4 + hxo, hy + 3, mix(eye_c, head_skin, 0.35))
        R(2 + hxo, hy, 6 + hxo, hy, cloak if key not in ("jester9", "vellum") else col)

    # accessories and silhouettes
    if key == "vellum":
        for i in range(4):
            y = hy - 1 - i
            xo = (1 if i % 2 else 0)
            R(2 + hxo + xo, y, 5 + hxo + xo, y, PALE if i % 2 == 0 else mix(PALE, col, 0.45))
        top = hy - 4
    elif key == "jester9":
        for (x_, y_, c_) in ((1, -1, col), (0, 0, dark), (0, 1, col), (7, -1, dark), (8, 0, col), (8, 1, dark),
                             (4, -1, col), (4, -2, dark), (5, -3, col), (6, -3, dark)):
            P(x_ + hxo, hy + y_, c_)
        jig = int(round(math.sin(t * 8 + gh * 6)))
        for (x_, y_) in ((0, 2), (8, 2), (6, -4)):
            P(x_ + hxo, hy + y_ + jig, EMBER)
        top = hy - 4
    elif key == "aurelia":
        P(2 + hxo, hy - 1, mix(col, TEXT, 0.5))
        P(6 + hxo, hy - 1, mix(col, TEXT, 0.5))
        top = hy - 1
    elif key == "rust":
        cog = (0, 1) if int(t * 3) % 2 else (1, 0)
        gc = mix(METAL, TEXT, 0.3)
        for (x_, y_) in ((8, 3), (8, 5), (7, 4), (9, 4), (8, 4)):
            P(x_ + lean, y_ + b, gc)
        for (dx_, dy_) in (cog, (-cog[0], -cog[1])):
            P(8 + dx_ + lean, 4 + dy_ + b, gc)
        R(2 + hxo, hy, 6 + hxo, hy, mix(cloak, TEXT, 0.15))
    elif key == "guest":
        kind = name_hash(f.name) % 5
        if kind == 0:
            R(1 + hxo, hy - 1, 7 + hxo, hy - 1, dark)
            R(1 + hxo, hy, 1 + hxo, hy + 3, dark)
            R(7 + hxo, hy, 7 + hxo, hy + 3, dark)
            top = hy - 1
        elif kind == 1:
            for (x_, y_) in ((2, -1), (2, -2), (6, -1), (6, -2)):
                P(x_ + hxo, hy + y_, trim)
            top = hy - 2
        elif kind == 2:
            P(4 + hxo, hy - 1, trim)
            P(4 + hxo, hy - 2, trim)
            P(4 + hxo, hy - 3, EMBER)
            top = hy - 3
        elif kind == 3:
            R(2 + hxo, hy - 2, 6 + hxo, hy - 2, EMBER)
            P(2 + hxo, hy - 1, EMBER)
            P(6 + hxo, hy - 1, EMBER)
            top = hy - 2
        else:
            R(2 + lean, 5 + b, 6 + lean, 5 + b, trim)
            P(7 + lean, 6 + b, trim)
            P(7 + lean, 7 + b, trim)
    if f.warden:
        cy = top - 3
        for (x_, y_) in ((2, 0), (4, 0), (6, 0), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1)):
            P(x_ + hxo, cy + y_, EMBER)
        top = cy
    return Sprite(sp, glows, top)


# =============================================================================== drawing ====
FIG_SCALE = 0.6          # figures are drawn small: sprites are authored 9x16 and shrunk about their feet


def tx(x: float, y: float) -> Tuple[int, int]:
    """Sprite coordinates to drawn coordinates. The feet (4, 15) stay where they are, the rest closes in on them."""
    return 4 + int(round((x - 4) * FIG_SCALE)), 15 - int(round((15 - y) * FIG_SCALE))


def shrink(px: Dict[Tuple[int, int], Tuple[RGB, float]]) -> Dict[Tuple[int, int], Tuple[RGB, float]]:
    out: Dict[Tuple[int, int], Tuple[RGB, float]] = {}
    for (x, y), v in px.items():      # later pixels (eyes, mouth, accessories) win, so faces survive
        out[tx(x, y)] = v
    return out


def draw_sprite(cv: Canvas, spr: Sprite, ox: int, oy: int, alpha: float = 1.0, tint: Optional[RGB] = None,
                tint_a: float = 0.0, ghost: bool = False) -> None:
    for (x, y), (c, a) in shrink(spr.px).items():
        if tint is not None and tint_a > 0:
            c = mix(c, tint, tint_a)
        if ghost:
            c = mix(c, GHOST_TINT, 0.55)
        cv.put(ox + x, oy + y, c, a * alpha)


def draw_scatter(cv: Canvas, spr: Sprite, ox: int, oy: int, tau: float, seed: int) -> None:
    for (x, y), (c, a) in shrink(spr.px).items():
        u1, u2 = hash01(x, y, seed), hash01(y, x, seed + 9)
        dx = (u1 - 0.5) * 10 * tau
        dy = -(1 + u2 * 8) * tau
        cv.put(int(round(ox + x + dx)), int(round(oy + y + dy)), mix(c, GHOST_TINT, tau * 0.6), a * (1 - tau) ** 0.8)


def draw_lamp(cv: Canvas, lay: Layout, scene: Scene, t: float, flare: float) -> Tuple[float, RGB]:
    """Chain, lantern and glow. Returns the flame brightness and colour for other effects."""
    cx, ly = lay.cx, lay.lamp_y
    ember = max(0.0, scene.ember)
    b = min(1.25, ember / 100.0)
    end = scene.ending
    if end:
        eid, s0 = end[0], end[1]
        if eid == "unplug" and t >= s0 + 0.15:
            b = 0.0
        elif eid == "long_dark":
            q = clamp01((t - s0) / 3.0)
            b *= (1 - q) * (0.75 + 0.25 * math.sin(t * 22 * (1 + q)) ** 2)
    flick = 1 + 0.07 * math.sin(t * 13) + 0.05 * math.sin(t * 29 + 1.3)
    if ember < 30 and b > 0:
        flick = 1 + 0.18 * math.sin(t * 21) * math.sin(t * 5.3)
    b = max(0.0, b * flick + flare * 0.5)
    low = ember < 30
    tone = DANGER if low else (EMBER_LOW if ember < 50 else EMBER)
    for y in range(0, ly - 3):
        cv.put(cx, y, METAL, 0.9)
    # lantern body 5 wide x 6 tall
    cv.rect(cx - 2, ly - 3, cx + 2, ly - 3, METAL)
    cv.rect(cx - 2, ly + 2, cx + 2, ly + 2, METAL)
    cv.rect(cx - 2, ly - 2, cx - 2, ly + 1, METAL)
    cv.rect(cx + 2, ly - 2, cx + 2, ly + 1, METAL)
    cv.rect(cx - 1, ly - 2, cx + 1, ly + 1, mix(BG, tone, 0.18 + 0.2 * min(1.0, b)))
    if b > 0.02:
        fh = 1 + int(round(min(1.4, b) * 2))
        flame = mix(tone, TEXT, 0.35 * min(1.0, b))
        for i in range(fh):
            w = 1 if i == fh - 1 and fh > 1 else 1
            cv.put(cx, ly + 1 - i, flame)
            if i < fh - 1:
                cv.put(cx - 1, ly + 1 - i, mix(tone, BG, 0.35))
                cv.put(cx + 1, ly + 1 - i, mix(tone, BG, 0.35))
        R_ = 4 + int(14 * min(1.2, b))
        gy = ly
        for y in range(max(0, gy - R_), min(cv.h, gy + R_ + 1)):
            for x in range(max(0, cx - R_), min(cv.w, cx + R_ + 1)):
                d = math.hypot(x - cx, y - gy)
                if d < R_:
                    a = 0.34 * min(1.0, b) * (1 - d / R_) ** 2
                    cv.px[y][x] = mix(cv.px[y][x], tone, a)
    return b, tone


def draw_door(cv: Canvas, lay: Layout, scene: Scene, t: float) -> None:
    if scene.act < 3:
        return
    cx = lay.cx
    base = lay.floor_y - 1
    h = min(13, base - (lay.lamp_y + 6) - 2)
    knocking = scene.omen == "doorbell" or any(b.kind == "motion" and b.start <= t <= b.end + 0.5 for b in scene.beats)
    shake = 0
    if knocking and (t % 1.5) < 0.3:
        shake = int(round(math.sin(t * 60)))
    if h < 6:
        seam = mix(BG, EMBER_LOW, 0.55)
        cv.rect(cx - 3, base, cx + 3, base, seam, 0.8)
        return
    w = 7
    x0 = cx - w // 2 + shake
    frame = mix(LINE, BG, 0.15)
    cv.rect(x0, base - h + 1, x0 + w - 1, base, frame)
    cv.rect(x0 + 1, base - h + 2, x0 + w - 2, base, mix(BG, BLACK, 0.45))
    width = 1 + (2 if knocking else 0) + (1 if scene.act == 3 else 0)
    seam = mix(EMBER_LOW, TEXT, 0.25)
    cv.rect(x0 + w - 2 - width + 1, base - h + 3, x0 + w - 2, base, seam, 0.85)
    cv.put(x0 + w - 3, base - h // 2, EMBER, 0.9)


def eased(p: float) -> float:
    return smooth(p)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ================================================================================ frame ====
def wrap_bubble(text: str, width: int = 22, lines: int = 3) -> List[str]:
    words = (text or "").split()
    out: List[str] = []
    cur = ""
    for w in words:
        if len(w) > width:
            w = w[: width - 1] + "…"
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = (out[-1][: width - 1].rstrip() + "…") if not out[-1].endswith("…") else out[-1]
    return out or [""]


@dataclass
class Cell:
    ch: str
    fg: Optional[RGB]
    bg: Optional[RGB]
    bold: bool = False
    italic: bool = False


def put_text(layer: Dict[Tuple[int, int], Cell], cols: int, rows: int, col: int, row: int, s: str,
             fg: RGB, bg: Optional[RGB] = None, bold: bool = False, italic: bool = False) -> None:
    s = "".join(ch if cell_len(ch) == 1 else "?" for ch in s)       # wide, zero-width and control characters would shift the row
    for i, ch in enumerate(s):
        c = col + i
        if 0 <= c < cols and 0 <= row < rows:
            layer[(c, row)] = Cell(ch, fg, bg, bold, italic)


def bar_text(value: int, width: int) -> List[Tuple[str, RGB, RGB]]:
    col = hx(coherence_color(value))
    eighths = int(round(max(0, min(100, value)) / 100 * width * 8))
    full, rem = divmod(eighths, 8)
    cells: List[Tuple[str, RGB, RGB]] = []
    for i in range(width):
        if i < full:
            cells.append(("█", col, TRACK))
        elif i == full and rem:
            cells.append((" ▏▎▍▌▋▊▉"[rem], col, TRACK))
        else:
            cells.append((" ", col, TRACK))
    return cells


def _scene_of(obj: Any) -> Scene:
    return getattr(obj, "scene", obj)


def render_frame(scene_or_widget: Any, t: float, cols: int, rows: int) -> Text:
    scene = _scene_of(scene_or_widget)
    if cols < MIN_COLS or rows < MIN_ROWS:
        return Text("The Theatre needs at least 44 columns and 12 rows.", style=C["faint"], no_wrap=True)
    names = [n for n in scene.order if n in scene.figures]
    lay = compute_layout(cols, rows, names)
    cv = Canvas(background(cols, rows))
    poser = Poser(scene, lay, t)

    # lamp flare from recent ritual / dissolve beats
    flare = 0.0
    for b in scene.beats:
        if b.kind in ("ritual", "dissolve", "miracle") and b.start <= t <= b.end:
            q = (t - b.start) / b.dur
            flare = max(flare, math.sin(math.pi * clamp01(q)) * (0.7 if b.kind == "ritual" else 1.0))
    draw_door(cv, lay, scene, t)
    flame_b, tone = draw_lamp(cv, lay, scene, t, flare)

    # registrar indicator
    reg_active = any(b.kind in ("chronicle", "epilogue") and b.start <= t <= b.end for b in scene.beats) or \
        (scene.thinking is None and False)
    cv.rect(2, 3, 8, 3, METAL)
    cv.rect(3, 4, 3, 5, METAL)
    cv.rect(7, 4, 7, 5, METAL)
    pen_x = 5 + (int(t * 8) % 3 if reg_active else 0)
    cv.put(pen_x, 2, EMBER if reg_active else FAINT)
    cv.put(pen_x, 1, EMBER if reg_active else FAINT, 0.8)

    # mimic colour for the Understudy
    mimic = None
    if scene.last_speaker and t - scene.last_speaker[2] < 4.0:
        mimic = (hx(scene.last_speaker[1]), 0.55 * (1 - (t - scene.last_speaker[2]) / 4.0))

    # pose everyone
    states: List[Tuple[Figure, FS, int]] = []
    for i, nm in enumerate(names):
        f = scene.figures[nm]
        states.append((f, poser.pose(f, i), i))
    # pact threads first, so bodies sit in front of them
    drawn_pairs = set()
    centers: Dict[str, Tuple[int, int]] = {}
    for f, fs, i in states:
        centers[f.name] = (int(round(fs.x)), lay.feet_y - lay.arc.get(f.name, 0) + int(fs.y) - 15 + int(round(8 - 8 * FIG_SCALE)))
    for f, fs, i in states:
        if f.partner and f.partner in centers and poser.visually_alive(f) and poser.visually_alive(scene.figures[f.partner]):
            pair = tuple(sorted((f.name, f.partner)))
            if pair in drawn_pairs:
                continue
            drawn_pairs.add(pair)
            (x0, y0), (x1, y1) = centers[pair[0]], centers[pair[1]]
            for k in range(0, 21):
                u = k / 20
                px = lerp(x0, x1, u)
                py = lerp(y0, y1, u) - 4 - 5 * math.sin(math.pi * u) + 0.6 * math.sin(t * 6 + u * 9)
                cv.put(int(round(px)), int(round(py)), mix(EMBER, TEXT, 0.2), 0.55 if int(u * 20 + t * 8) % 3 else 0.25)

    # trial spotlight and siege particles sit behind the figures too
    if poser.trial:
        for nm in (poser.trial["acc"], poser.trial["dfn"]):
            if nm in centers:
                sx = centers[nm][0]
                for y in range(0, lay.floor_y):
                    half = 3 + int(y * 0.14)
                    for x in range(sx - half, sx + half + 1):
                        cv.put(x, y, TEXT, 0.10)
    order_idx = sorted(states, key=lambda s: (lay.feet_y - lay.arc.get(s[0].name, 0) + int(s[1].y), s[1].x != lay.home.get(s[0].name, 0)))
    anchors: Dict[str, Tuple[int, int]] = {}
    for f, fs, i in order_idx:
        ox = int(round(fs.x)) - 4
        oy = lay.feet_y - lay.arc.get(f.name, 0) + int(fs.y) - 15
        key = persona_key(f)
        arrive = clamp01(t - f.born_at)
        if arrive <= 0:
            continue
        spr = build_sprite(f, fs, t, mimic)
        anchors[f.name] = (ox + 4, oy + tx(0, spr.top)[1])
        if poser.visually_alive(f):
            tint, ta = (DANGER, 0.65 * fs.flash) if fs.flash > 0 else (None, 0.0)
            if scene.ending and scene.ending[0] == "pen" and f.name in scene.ending[2]:
                pass
            draw_sprite(cv, spr, ox, oy, arrive, tint, ta)
            for gx0, gy0, gr0, gc, ga in spr.glows:
                gx, gy = tx(gx0, gy0)
                gr = max(2, int(round(gr0 * FIG_SCALE)))
                for yy in range(gy - gr, gy + gr + 1):
                    for xx in range(gx - gr, gx + gr + 1):
                        d = math.hypot(xx - gx, yy - gy)
                        if d < gr:
                            cv.put(ox + xx, oy + yy, gc, ga * (1 - d / gr))
        else:
            s0 = poser.diss.get(f.name)
            tau = clamp01((t - s0) / 1.8) if s0 is not None else 1.0
            if s0 is not None and t < s0 + 1.8:
                draw_scatter(cv, spr, ox, oy, tau, name_hash(f.name))
            ghost_a = 0.0
            if f.echo > 0:
                ghost_a = 0.38 * (smooth((tau - 0.55) / 0.45) if s0 is not None and tau < 1 else 1.0)
            elif f.faded_at is not None:
                ghost_a = 0.38 * (1 - clamp01((t - f.faded_at) / 3.0))
            if ghost_a > 0.01:
                bobg = int(round(1.4 * math.sin(t * 1.6 + i)))
                # an Echo has no legs: a wavy tail instead
                gspr = Sprite({k: v for k, v in spr.px.items() if k[1] <= 10}, [], spr.top)
                for r_ in range(11, 15):
                    wob = int(round(math.sin(t * 3 + r_ + i) * (r_ - 10) * 0.35))
                    for x_ in range(3 + (r_ - 10) // 3, 6 - (r_ - 10) // 3):
                        gspr.px[(x_ + wob, r_)] = (mix(hx(f.color), BG, 0.5), 0.8)
                draw_sprite(cv, gspr, ox, oy + bobg, ghost_a, ghost=True)
                ex0, ey0 = tx(3, spr.top + 2)
                ex1, _ = tx(5, spr.top + 2)
                cv.put(ox + ex0, oy + bobg + ey0, TEXT, ghost_a + 0.2)
                cv.put(ox + max(ex1, ex0 + 1), oy + bobg + ey0, TEXT, ghost_a + 0.2)
        if fs.shield > 0:
            cx_, cy_ = ox + 4, oy + tx(4, 8)[1]
            ring = 5
            for ang in range(-80, 81, 6):
                a_ = math.radians(ang)
                side = 1 if fs.x < lay.cx else -1
                px = cx_ + side * int(round(ring * math.cos(a_)))
                py = cy_ + int(round(ring * math.sin(a_)))
                if (ang // 6 + int(t * 10)) % 3:
                    cv.put(px, py, (200, 216, 232), 0.65 * fs.shield)

    # the siege: shots of light cross between the two minds, with the lock between them
    if poser.siege and poser.siege["a"] in centers and poser.siege["d"] in centers:
        (ax, ay), (dx_, dy_) = centers[poser.siege["a"]], centers[poser.siege["d"]]
        for k in range(7):
            u = ((t * 1.4) + k / 7) % 1.0
            cv.put(int(round(lerp(ax, dx_, u))), int(round(lerp(ay + 8, dy_ + 8, u) - 3 * math.sin(math.pi * u))), EMBER, 0.85)
        mx, my = (ax + dx_) // 2 + 4, min(ay, dy_) + 4
        cracked = poser.siege["cracked"] is not None or poser.siege["result"] == "breach"
        held = poser.siege["result"] == "held"
        lc = EMBER if cracked else (TEXT if held else MUTED)
        cv.rect(mx - 2, my, mx + 2, my + 3, lc)
        cv.put(mx, my + 1, BG)
        sh = 1 if not cracked else -1
        for (x_, y_) in ((-1, -1), (-1, -2), (0, -3), (1, -2), (1, -1)):
            cv.put(mx + x_ + (2 if cracked else 0), my + y_ + sh * 0 - (1 if cracked else 0), lc)
        if cracked:
            for k in range(3):
                cv.put(mx + 3 + k, my - 2 - k, EMBER, 0.8)

    # effects drawn over the figures
    for kind, args in poser.fx.items:
        _draw_fx(cv, kind, args, centers, anchors, lay, t, tone)

    # a stamp or a darkness for the endings
    end = scene.ending
    if end:
        eid, s0, winners = end
        q = clamp01((t - s0) / 1.4)
        if eid in ("unplug", "long_dark"):
            cv.dim(1 - 0.72 * q)
        if eid == "pen" and winners and winners[0] in centers:
            wx = centers[winners[0]][0]
            cv.rect(wx - 5, lay.feet_y - 4, wx + 5, lay.feet_y - 1, mix(METAL, BLACK, 0.2))
            cv.rect(wx - 5, lay.feet_y - 5, wx + 5, lay.feet_y - 5, mix(METAL, TEXT, 0.15))

    # to text
    layer: Dict[Tuple[int, int], Cell] = {}
    _overlays(layer, scene, poser, lay, anchors, centers, t, cols, rows)
    return compose(cv, layer, cols, rows)


def _draw_fx(cv: Canvas, kind: str, args: Tuple[Any, ...], centers, anchors, lay: Layout, t: float, tone: RGB) -> None:
    def head(name: str) -> Optional[Tuple[int, int]]:
        return anchors.get(name)

    if kind == "flash":
        actor, target, q = args
        if actor in centers and target in centers:
            ax, ay = centers[actor]
            tx, ty = centers[target]
            cv.line(ax + (4 if tx > ax else -4), ay + 7, tx, ty + 7, TEXT, 0.9)
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                cv.put(tx + dx, ty + 7 + dy, EMBER, 0.95)
    elif kind == "damage":
        name, dmg, q = args
        h = head(name)
        if h and dmg:
            cv.put(0, 0, BG, 0)
    elif kind == "snap":
        a, b, p = args
        if a in centers and b in centers:
            (x0, y0), (x1, y1) = centers[a], centers[b]
            mx = (x0 + x1) // 2
            gapw = int(2 + 6 * smooth(p))
            for k in range(0, 6):
                cv.put(mx - gapw - k, y0 - 3 + (k % 2), EMBER, 0.7 - k * 0.1)
                cv.put(mx + gapw + k, y0 - 3 - (k % 2), EMBER, 0.7 - k * 0.1)
    elif kind == "coins":
        giver, taker, p = args
        if giver in centers and taker in centers:
            (x0, y0), (x1, y1) = centers[giver], centers[taker]
            for i in range(5):
                u = clamp01((p - 0.08 * i - 0.1) / 0.6)
                if 0 < u < 1:
                    px = lerp(x0, x1, u)
                    py = lerp(y0 + 6, y1 + 4, u) - 7 * math.sin(math.pi * u)
                    cv.put(int(round(px)), int(round(py)), EMBER, 1.0)
                    cv.put(int(round(px)) + 1, int(round(py)), mix(EMBER, TEXT, 0.4), 0.8)
    elif kind == "sparks":
        name, q = args
        if name in centers:
            x0, y0 = centers[name]
            for i in range(9):
                u = clamp01(q * 1.2 - i * 0.05)
                px = lerp(x0 + 4, lay.cx, u)
                py = lerp(y0 + 2, lay.lamp_y, u) - 5 * math.sin(math.pi * u) * (0.4 + 0.6 * hash01(i, 3))
                cv.put(int(round(px)), int(round(py + (hash01(i, 5) - 0.5) * 3)), mix(EMBER, TEXT, 0.4), 0.9)
    elif kind == "eye":
        name, p = args
        h = head(name)
        if h:
            x, y = h[0], h[1] - 5
            lid = smooth(p * 4)
            rows = [(2, 4)] if lid < 0.3 else [(2, 4), (0, 6), (2, 4)] if lid < 0.8 else [(2, 4), (0, 6), (0, 6), (2, 4)]
            for j, (a, b) in enumerate(rows):
                for xx in range(a, b + 1):
                    cv.put(x - 3 + xx, y + j, PALE, 0.95)
            if lid >= 0.3:
                cv.put(x + int(round(math.sin(t * 5))), y + 1, DANGER if p > 0.5 else EMBER)
    elif kind == "seal":
        name, p = args
        h = head(name)
        if h:
            x, y = h[0] + 7, h[1] - 3
            cv.rect(x - 1, y - 1, x + 1, y + 1, EMBER, 0.9)
            cv.put(x, y, BG, 0.9)
    elif kind == "mark":
        name, p = args
        h = head(name)
        if h:
            cv.put(h[0], h[1] - 4, EMBER, 0.9)
            cv.put(h[0] - 1, h[1] - 5, EMBER, 0.6)
            cv.put(h[0] + 1, h[1] - 5, EMBER, 0.6)
    elif kind == "page":
        name, p = args
        h = head(name)
        if h:
            x, y = h[0] - 2, h[1] - 6
            cv.rect(x, y, x + 4, y + 3, PALE)
            cv.line(x + 1, y + 1, x + 3, y + 1, FAINT)
            cv.line(x + 1, y + 2, x + 3, y + 2, FAINT)
    elif kind == "glint":
        name, p = args
        h = head(name)
        if h:
            for i in range(5):
                a_ = i * 1.26 + p * 4
                cv.put(int(h[0] + 6 * math.cos(a_) * (0.4 + p)), int(h[1] - 1 + 4 * math.sin(a_) * (0.4 + p)), EMBER, 1 - 0.7 * p)
    elif kind == "echo":
        name, target, p, mode = args
        if target in centers and 0.3 < p < 1.0:
            tx, ty = centers[target]
            for i in range(7):
                u = (p * 2 + i / 7) % 1.0
                if mode == "BLESS":
                    cv.put(int(tx + 4 + 5 * math.cos(i * 1.7)), int(ty + 12 - u * 12), OK, 1 - u)
                else:
                    cv.put(int(tx + 4 + 4 * math.cos(i * 1.7)), int(ty + u * 12), mix(BG, DANGER, 0.5), 1 - 0.5 * u)
    elif kind == "vote":
        name, v = args
        h = head(name)
        if h:
            x, y = h[0] + 6, h[1] - 1
            col = DANGER if v == "G" else TEXT
            if v == "A":
                cv.rect(x, y - 3, x, y, col)
                cv.put(x + 1, y - 3, col)
                cv.put(x - 1, y - 3, col)
            else:
                cv.rect(x, y - 3, x, y, col)
                cv.put(x + 1, y, col)
                cv.put(x - 1, y, col)


def unique_prefix_len(names: List[str]) -> int:
    """Shortest first-word prefix length at which no two minds share a label ("Mag" and "Mar", not "Ma" twice)."""
    firsts = [n.split()[0] for n in names if n.split()]
    for k in range(1, 12):
        if len({f[:k] for f in firsts}) == len(set(firsts)):
            return k
    return 12


def short_label(name: str, room: int, uniq: int) -> str:
    if len(name) <= room:
        return name
    first = (name.split() or [name])[0]
    if len(first) <= room:
        return first
    keep = max(1, min(room - 1, max(uniq, 3)))
    return first[:keep] + "…"


def _overlays(layer: Dict[Tuple[int, int], Cell], scene: Scene, poser: Poser, lay: Layout, anchors, centers,
              t: float, cols: int, rows: int) -> None:
    # names and Coherence under each figure's home slot
    uniq = unique_prefix_len(list(scene.figures))
    banner_on = any((b.kind == "notice" and b.data.get("omen") and b.start <= t <= b.end + 1.6)
                    or (b.kind in ("miracle", "election") and b.start <= t <= b.end + 0.8) for b in scene.beats)
    for nm, f in scene.figures.items():
        hxp = lay.home.get(nm)
        if hxp is None:
            continue
        room = lay.room.get(nm, 10)
        label = short_label(nm, room, uniq)
        if len(label) > room:
            label = label[:room]
        col = hx(f.color)
        floor = mix(BG, BLACK, 0.35)
        start = max(0, hxp - len(label) // 2)
        if poser.visually_alive(f):
            put_text(layer, cols, rows, start, rows - 2, label, col, floor, bold=True)
            bw = max(3, min(9, room))
            for j, (ch, fg, bg) in enumerate(bar_text(f.coherence, bw)):
                c = hxp - bw // 2 + j
                if 0 <= c < cols:
                    layer[(c, rows - 1)] = Cell(ch, fg, bg)
        else:
            tag = label if f.echo > 0 else ""
            put_text(layer, cols, rows, start, rows - 2, tag, mix(FAINT, floor, 0.0), floor, italic=True)
            if f.echo > 0:
                s = f"echo x{f.echo}" if room >= 7 else f"x{f.echo}"
                put_text(layer, cols, rows, max(0, hxp - len(s) // 2), rows - 1, s, FAINT, floor)

    # bubbles
    bubbles: Dict[str, Tuple[List[str], str, float, Beat]] = {}
    for b in scene.beats:
        if b.start - 0.02 > t:
            break
        if t > b.end + 0.25:
            continue
        if b.kind in ("speech", "whisper", "testimony", "siege_say", "last_words") and b.actor in anchors:
            style = "whisper" if b.kind == "whisper" else ("ghost" if b.kind == "last_words" else "say")
            bubbles[b.actor] = (wrap_bubble(b.text), style, (t - b.start) / b.dur, b)
    for nm, (lines, style, p, b) in bubbles.items():
        ax, ay = anchors[nm]
        shown_chars = int(math.ceil(sum(len(x) for x in lines) * min(1.0, p / 0.6)))
        wmax = max(len(x) for x in lines)
        w = wmax + 2
        left = max(0, min(cols - w, ax - w // 2))
        n = len(lines)
        head_row = max(0, ay // 2)
        floor_row = 2 if banner_on else 0            # rows 0-1 belong to the Notice banner while it shows
        avail = max(1, head_row - 1 - floor_row)
        if n > avail:
            lines = lines[:avail]
            lines[-1] = lines[-1][: max(0, wmax - 1)] + "…" if not lines[-1].endswith("…") else lines[-1]
            n = len(lines)
        top_row = max(floor_row, head_row - n - 1)
        if style == "whisper":
            bg, fg = SURFACE, MUTED
        elif style == "ghost":
            bg, fg = mix(SURFACE, GHOST_TINT, 0.15), mix(TEXT, GHOST_TINT, 0.4)
        else:
            bg, fg = RAISED, TEXT
        used = 0
        for j, ln in enumerate(lines):
            row = top_row + j
            if row >= rows:
                break
            vis = ln[: max(0, shown_chars - used)]
            used += len(ln)
            put_text(layer, cols, rows, left, row, " " * w, fg, bg)
            put_text(layer, cols, rows, left + 1, row, vis, fg, bg, italic=(style != "say"))
        tail_row = top_row + len(lines)
        if tail_row < rows:
            put_text(layer, cols, rows, max(0, min(cols - 1, ax)), tail_row, "▼", bg, None)

    # thinking dots over a mind that has not yet acted
    if scene.thinking and scene.thinking[0] in anchors and scene.thinking[0] not in bubbles:
        nm = scene.thinking[0]
        ax, ay = anchors[nm]
        step = int(t * 3) % 4
        dots = "".join("•" if i < step else "·" for i in range(3))
        put_text(layer, cols, rows, ax - 1, max(0, ay // 2 - 1), dots, EMBER, None, bold=True)

    # floating damage
    for kind, args in poser.fx.items:
        if kind == "damage":
            name, dmg, q = args
            if name in anchors and dmg:
                ax, ay = anchors[name]
                row = int(ay // 2 + 1 - q * 3)
                put_text(layer, cols, rows, ax + 3, max(0, row), f"-{dmg}", DANGER, None, bold=True)

    # act title card and Notice banner
    live_notice = [b for b in scene.beats if b.kind == "notice" and b.data.get("omen") and b.start <= t <= b.end + 1.6]
    newest_notice = live_notice[-1] if live_notice else None          # banners never stack, even at the fastest pace
    for b in scene.beats:
        if b.kind == "act" and b.start <= t <= b.end + 0.3:
            q = (t - b.start) / max(0.1, b.dur)
            fade = smooth(q * 4) * (1 - smooth((q - 0.75) * 4))
            title = f"ACT {['I', 'II', 'III'][min(2, max(0, b.data.get('_act', 1) - 1))]}  {b.data.get('act_title', '')}".strip()
            bgc = mix(BG, SURFACE, 0.9)
            put_text(layer, cols, rows, max(0, (cols - len(title)) // 2), 0, title, mix(bgc, EMBER, fade), bgc, bold=True)
        if b is newest_notice:
            head = b.text.split(". ")[0]
            q = clamp01(1 - (t - b.start - b.dur) / 1.6)
            put_text(layer, cols, rows, 0, 1, " " * cols, TEXT, RAISED)
            put_text(layer, cols, rows, max(0, (cols - len(head)) // 2), 1, head[:cols], mix(RAISED, TEXT, min(1.0, q + 0.3)), RAISED)
        if b.kind == "miracle" and b.start <= t <= b.end + 0.8:
            q = clamp01(1 - max(0.0, t - b.end) / 0.8)
            label = " MIRACLE "
            put_text(layer, cols, rows, max(0, (cols - len(label)) // 2), 1, label, mix(RAISED, EMBER, q), RAISED, bold=True)
        if b.kind == "election" and b.start <= t <= b.end:
            label = " ELECTION "
            put_text(layer, cols, rows, max(0, (cols - len(label)) // 2), 1, label, TEXT, RAISED, bold=True)
        if b.kind == "verdict" and b.start <= t <= b.end:
            q = (t - b.start) / b.dur
            if 0.15 < q < 0.7:
                row = 2 + (1 if q > 0.4 else 0)
                put_text(layer, cols, rows, lay.cx - 2, row, "[T]", TEXT, None, bold=True)
    if scene.ending and scene.ending[0] in ("clerical", "backlog") and t >= scene.ending[1] + 0.8:
        s = " PENDING "
        put_text(layer, cols, rows, lay.cx - len(s) // 2, max(2, lay.lamp_y // 2 + 3), s, DANGER, BG, bold=True)
    if scene.ending and scene.ending[0] == "committee" and t >= scene.ending[1]:
        pass


# ================================================================================ output ====
_STYLE_CACHE: Dict[Tuple, Style] = {}


def _style(fg: Optional[RGB], bg: Optional[RGB], bold: bool = False, italic: bool = False) -> Style:
    key = (fg, bg, bold, italic)
    st = _STYLE_CACHE.get(key)
    if st is None:
        st = Style(color=to_hex(fg) if fg else None, bgcolor=to_hex(bg) if bg else None, bold=bold or None, italic=italic or None)
        _STYLE_CACHE[key] = st
    return st


def compose(cv: Canvas, layer: Dict[Tuple[int, int], Cell], cols: int, rows: int) -> Text:
    out = Text(no_wrap=True, overflow="crop")
    for r in range(rows):
        top, bot = cv.px[2 * r], cv.px[2 * r + 1]
        run = ""
        run_key: Optional[Tuple] = None
        for c in range(cols):
            cell = layer.get((c, r))
            if cell is not None:
                bg = cell.bg if cell.bg is not None else mix(top[c], bot[c], 0.5)
                ch, key = cell.ch, (cell.fg, bg, cell.bold, cell.italic)
            elif top[c] == bot[c]:
                ch, key = " ", (None, top[c], False, False)
            else:
                ch, key = "▀", (top[c], bot[c], False, False)
            if key != run_key:
                if run:
                    out.append(run, _style(*run_key))
                run, run_key = ch, key
            else:
                run += ch
        if run:
            out.append(run, _style(*run_key))
        if r < rows - 1:
            out.append("\n")
    return out


# ================================================================================ widget ====
class Theatre(Widget):
    """The Textual widget that owns a Scene and redraws it at 12 frames per second."""

    DEFAULT_CSS = "Theatre { height: 1fr; }"

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self.scene = Scene()
        self._t0 = time.monotonic()
        self.beat_count = 0

    @property
    def speed(self) -> float:
        return self.scene.speed

    @speed.setter
    def speed(self, v: float) -> None:
        self.scene.speed = max(0.0, float(v))

    def on_mount(self) -> None:
        self.set_interval(1 / 12, self._tick)

    def _tick(self) -> None:
        self.scene.now = time.monotonic() - self._t0
        if self.display:
            self.refresh()

    def set_cast(self, wicks: List[Dict[str, Any]]) -> None:
        self.scene.set_cast(wicks)

    def set_state(self, snap: Dict[str, Any]) -> None:
        self.scene.set_state(snap)

    def feed(self, ev: Event) -> float:
        self.scene.now = time.monotonic() - self._t0
        dur = self.scene.on_event(ev)
        if ev.kind not in UNQUEUED:
            self.beat_count += 1
        return dur

    def render(self) -> Text:
        size = self.size
        return render_frame(self.scene, self.scene.now, size.width, size.height)
