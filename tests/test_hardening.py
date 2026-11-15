"""Hostile model output and awkward input: nothing a model writes may break the screen, the disk or the run."""
import asyncio
import json

from rich.cells import cell_len

from arena.engine.events import Event
from arena.llm.parsing import clean_speech, scrub
from tests.helpers import make_game, tmp_store


def test_terminal_escapes_and_lone_surrogates_are_scrubbed():
    evil = "hi \x1b]0;PWNED\x07 \x1b[2J\x1b[31mred \ud83d end"
    out = scrub(evil)
    assert "\x1b" not in out and "\x07" not in out and "\ud83d" not in out
    assert "\x1b" not in clean_speech(evil, "A")
    ev = Event("speech", evil, actor="A\x1b[2J", data={"x": ["\x1b[31m"]})
    assert "\x1b" not in ev.text and "\x1b" not in ev.actor and "\x1b" not in json.dumps(ev.data)


def test_surrogates_do_not_drop_journal_lines():
    store = tmp_store(3)
    g = make_game(3, store=store, cycles=2)
    g.emit("speech", "bad \ud83d text", actor="A")
    g.emit("speech", "good text", actor="A")
    lines = [json.loads(x) for x in open(store.journal_path, encoding="utf-8") if x.strip()]
    assert [e["text"] for e in lines if e["kind"] == "speech"][-1] == "good text"
    assert len(lines) >= 2


def test_a_huge_integer_in_gods_effect_is_ignored():
    from arena.lore.omens import clean_effect
    assert clean_effect({"income": int("9" * 400), "decay": float("nan")}) == {}


def test_two_names_with_the_same_slug_stay_two_people():
    g = make_game(1, god=False)
    base = {"epithet": "e", "former_life": "f", "desire": "d", "fear": "x", "quirk": "q"}
    a = g._newborn("m1", dict(base, name="Mr. Xavier"), "test")
    b = g._newborn("m2", dict(base, name="Mr Xavierr"), "test")
    assert a is not None
    if b is not None:
        assert a.persona_id != b.persona_id
        assert g.s.persona(a.persona_id).name == "Mr. Xavier"


def test_wide_and_zero_width_text_never_shifts_theatre_rows():
    from arena.ui import theatre as T
    from tests.test_theatre import scene
    s = scene(6)
    s.on_event(Event("speech", "\u6f22\u5b57 \u200b \u00e9 \U0001F600 hello \x1b[2J there", actor="Mind 0"))
    for cols in (62, 100):
        out = T.render_frame(s, s.now + 0.5, cols, 14)
        assert all(cell_len(line) == cols for line in out.plain.split("\n"))


def test_ctrl_q_stops_the_game():
    from arena.ui.tui import UndermindApp
    g = make_game(1, cycles=2)
    from arena.engine.events import EventBus

    async def go():
        app = UndermindApp(g, g.bus, provider="mock")
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await app.action_quit()
        assert g._stop is True
    asyncio.run(go())


def test_picker_survives_a_narrow_terminal_and_explains_an_empty_pick():
    from arena.ui.models_screen import ModelScreen
    from arena.ui.tui import UndermindApp
    g = make_game(1, cycles=2)

    async def go():
        app = UndermindApp(g, g.bus, provider="mock")
        async with app.run_test(size=(50, 20)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause(0.3)
            g.pause()
            await pilot.press("m")
            await pilot.pause(0.3)
            assert isinstance(app.screen, ModelScreen)
            await pilot.press("escape")
            await pilot.pause(0.2)
            g.resume()
            g.stop()
    asyncio.run(go())
