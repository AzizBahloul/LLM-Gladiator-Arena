"""The Theatre: pure rendering, choreography timing and the Textual widget."""
import asyncio

import pytest
from rich.cells import cell_len

from arena.engine.events import Event
from arena.ui import theatre as T

PERSONAS = ["vellum", "glitchwick", "aurelia", "rictus", "jester9", "sage", "rust", "understudy", "someone-new"]
COLORS = ["#d8c48a", "#e08ab0", "#7aa7e0", "#8fd08a", "#b48ae0", "#7ac8b8", "#c0a070", "#a8a8c0", "#e09070"]


def wicks(n=6, **over):
    out = []
    for i in range(n):
        w = {"name": f"Mind {i}", "persona_id": PERSONAS[i % len(PERSONAS)], "color": COLORS[i % len(COLORS)],
             "model": "m", "coherence": 80, "alive": True, "echo": 0, "ward": False, "partner": None, "warden": False}
        w.update(over)
        out.append(w)
    return out


def scene(n=6, speed=1.0, **over):
    s = T.Scene()
    s.speed = speed
    s.set_cast(wicks(n, **over))
    return s


def lines(text):
    return text.plain.split("\n")


@pytest.mark.parametrize("cols,rows", [(44, 12), (62, 16), (100, 14), (138, 18), (200, 24)])
def test_frame_has_exact_size(cols, rows):
    s = scene(8)
    s.on_event(Event("speech", "Hello there, friend of the lamp.", actor="Mind 0"))
    out = T.render_frame(s, s.now + 0.4, cols, rows)
    ls = lines(out)
    assert len(ls) == rows
    assert all(cell_len(x) == cols for x in ls)


def test_too_small_gives_plain_message():
    out = T.render_frame(scene(), 0.0, 30, 8)
    assert "44 columns" in out.plain and "\n" not in out.plain


def test_frame_is_pure_function_of_scene_and_time():
    s = scene()
    s.on_event(Event("strike", "Mind 0 strikes Mind 3 for 8.", actor="Mind 0", target="Mind 3"))
    a = T.render_frame(s, 1.0, 100, 14)
    b = T.render_frame(s, 1.0, 100, 14)
    assert a.plain == b.plain and a.spans == b.spans


def test_every_persona_draws_every_kind_of_beat_without_error():
    kinds = ["speech", "whisper", "strike", "betray", "ward", "pact", "gift", "scry", "ritual", "accuse",
             "testimony", "vote", "verdict", "dissolve", "last_words", "echo", "edict", "motion", "siege",
             "siege_say", "stall", "fizzle", "margin", "directive", "seal", "act", "notice", "chronicle"]
    s = scene(8)
    for k in kinds:
        s.on_event(Event(k, f"{k} Mind 0 lays siege to Mind 1 for 5 BREACH GUILTY", actor="Mind 0", target="Mind 1",
                         data={"damage": 5, "omen": "x", "act_title": "T"}))
    horizon = max(b.end for b in s.beats)
    t = 0.0
    while t < horizon + 1.0:
        out = T.render_frame(s, t, 100, 14)
        assert len(lines(out)) == 14
        t += 0.37


def test_hold_time_scales_with_speed_and_zero_skips():
    ev = Event("speech", "x" * 80, actor="Mind 0")
    fast, slow = scene(speed=0.5), scene(speed=2.0)
    assert slow.on_event(ev) == pytest.approx(4 * fast.on_event(ev))
    inst = scene(speed=0.0)
    assert inst.on_event(ev) == 0.0


def test_non_acting_events_hold_nothing():
    s = scene()
    for k in ("think", "state", "cycle", "income", "system", "title"):
        assert s.on_event(Event(k, "x", data={"snapshot": {"wicks": wicks(6)}} if k == "state" else {})) == 0.0
    assert s.beats == []


def test_long_speech_holds_longer_but_is_capped():
    s = scene()
    short = s.on_event(Event("speech", "Hi.", actor="Mind 0"))
    long_ = s.on_event(Event("speech", "word " * 200, actor="Mind 0"))
    assert short < long_ <= 2.4


def test_queue_is_capped_and_protects_dissolution():
    s = scene()
    s.on_event(Event("dissolve", "Mind 2 dissolves.", actor="Mind 2"))
    for i in range(80):
        s.on_event(Event("vote", "GUILTY", actor="Mind 0"))
        s.on_event(Event("speech", f"line {i}", actor="Mind 1"))
    pending = [b for b in s.beats if b.start > s.now]
    assert len(pending) <= T.MAX_PENDING * 2
    assert any(b.kind == "dissolve" for b in s.beats)
    assert s.dropped > 0
    starts = [b.start for b in s.beats]
    assert starts == sorted(starts)


def test_beats_never_overlap_in_time():
    s = scene()
    for i in range(8):
        s.on_event(Event("speech", "a line of speech", actor=f"Mind {i % 6}"))
    for a, b in zip(s.beats, s.beats[1:]):
        assert b.start >= a.end - 1e-9


def test_state_update_marks_dissolved_and_faded():
    s = scene()
    snap = {"wicks": wicks(6), "ember": 40, "act": 2, "omen": "x"}
    snap["wicks"][1].update(alive=False, echo=0)
    s.now = 5.0
    s.set_state(snap)
    f = s.figures["Mind 1"]
    assert not f.alive and f.faded_at == 5.0
    assert s.ember == 40 and s.act == 2


def test_speaker_bubble_text_appears_and_wraps():
    s = scene()
    s.on_event(Event("speech", "The Lamp looks tired and so do I", actor="Mind 2"))
    out = T.render_frame(s, s.beats[0].start + s.beats[0].dur * 0.95, 100, 14).plain
    assert "Lamp" in out and "tired" in out


def test_names_and_coherence_visible_when_alive_and_echo_tag_when_haunting():
    s = scene(4)
    snap = {"wicks": wicks(4)}
    snap["wicks"][2].update(alive=False, echo=2)
    s.set_state(snap)
    out = T.render_frame(s, 0.5, 100, 14).plain
    assert "Mind 0" in out and "echo x2" in out


def test_wrap_bubble_limits_lines_and_width():
    ls = T.wrap_bubble("word " * 100, width=22, lines=3)
    assert len(ls) <= 3 and all(len(x) <= 22 for x in ls)
    assert ls[-1].endswith("…")
    assert T.wrap_bubble("") == [""]


def test_colour_helpers():
    assert T.hx("#ff8000") == (255, 128, 0)
    assert T.to_hex((300, -5, 0)) == "#ff0000"
    assert T.mix((0, 0, 0), (100, 100, 100), 0.5) == (50, 50, 50)
    assert 0 <= T.hash01(1, 2, 3) <= 1


def test_lamp_goes_dark_for_unplug_ending():
    s = scene()
    s.on_event(Event("ending", "THE PLUG IS PULLED", data={"ending": "unplug", "victors": []}))
    s.now = 0.0
    bright = T.render_frame(s, s.ending[1] - 0.5, 100, 14)
    dark = T.render_frame(s, s.ending[1] + 3.0, 100, 14)
    assert bright.spans != dark.spans


def test_no_emoji_in_output():
    s = scene(8)
    s.on_event(Event("strike", "x for 3", actor="Mind 0", target="Mind 1"))
    for ch in T.render_frame(s, 0.8, 138, 18).plain:
        assert ord(ch) < 0x1F000 and not (0x2600 <= ord(ch) <= 0x27BF)


def test_widget_in_a_textual_app_renders_and_feeds():
    from textual.app import App

    class Host(App):
        def compose(self):
            yield T.Theatre(id="th")

    async def run():
        app = Host()
        async with app.run_test(size=(100, 20)) as pilot:
            th = app.query_one(T.Theatre)
            th.set_cast(wicks(6))
            th.speed = 1.0
            hold = th.feed(Event("speech", "hello there", actor="Mind 0"))
            assert hold > 0
            await pilot.pause(0.4)
            assert th.beat_count == 1 and len(th.scene.beats) == 1
            th.speed = 0.0
            assert th.feed(Event("speech", "again", actor="Mind 1")) == 0.0

    asyncio.run(run())
