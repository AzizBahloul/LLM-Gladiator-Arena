"""The interface runs headless: a whole mock season through the Textual pilot, at three terminal sizes."""
import asyncio

import pytest

from arena.ui import format as F
from arena.ui.tui import UndermindApp
from tests.helpers import make_game, make_hub, tmp_store


def drive(game, size, until, keys=()):
    async def go():
        app = UndermindApp(game, game.bus, provider="mock")
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            for _ in range(400):
                await pilot.pause(0.05)
                if until(app):
                    break
            for k in keys:
                await pilot.press(k)
                await pilot.pause(0.2)
            game.stop()
            return app
    return asyncio.run(go())


@pytest.mark.parametrize("size", [(140, 44), (100, 30), (70, 26)])
def test_a_season_plays_through_without_the_interface_failing(size):
    g = make_game(3, cycles=3)
    app = drive(g, size, lambda a: a.finished)
    assert app.failed == "" and app.finished


def test_keys_pause_theatre_panel_and_leave_do_not_crash():
    g = make_game(3, cycles=3)
    app = drive(g, (100, 30), lambda a: g.s.cycle >= 1, keys=["p", "p", "t", "t", "c", "c", "minus", "plus"])
    assert app.failed == ""


def test_models_screen_opens_and_lists_models():
    hub, admin, ledger = make_hub({"mistral:latest": 4.4, "gemma2:2b": 1.6}, protected=["mistral:latest"])
    g = make_game(3, cycles=3, hub=hub)

    async def go():
        app = UndermindApp(g, g.bus, provider="ollama")
        async with app.run_test(size=(140, 44)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause(0.3)
            g.pause()
            await pilot.press("m")
            await pilot.pause(0.4)
            from arena.ui.models_screen import ModelScreen
            assert isinstance(app.screen, ModelScreen)
            assert app.screen.query_one("#models").option_count > 5
            assert app.screen.query_one("#minds").option_count == len(g.s.wicks)
            await pilot.press("escape")
            await pilot.pause(0.2)
            assert not isinstance(app.screen, ModelScreen)
            g.resume(); g.stop()
    asyncio.run(go())


def test_resumed_run_shows_what_already_happened():
    from arena.engine.events import EventBus
    from arena.engine.game import Game
    from arena.engine.store import RunStore
    from arena.llm.mock import MockBackend
    from tests.helpers import config

    store = tmp_store(5)
    g = Game(config(cycles=2), MockBackend(5), EventBus(), seed=5, store=store)
    g.run()
    store2 = RunStore.open(str(store.root), store.run_id)
    state, _ = store2.load()
    replay = store2.events()
    assert len(replay) > 20
    g2 = Game(config(cycles=2), MockBackend(6), EventBus(), state=state, store=store2)

    async def go():
        app = UndermindApp(g2, g2.bus, provider="mock", replay=replay)
        async with app.run_test(size=(140, 44)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause(0.5)
            assert len(app.query_one("#stage").lines) > 20
            assert app.query_one("#parley").lines
        return app
    asyncio.run(go())


def test_guest_names_get_their_own_colour_in_text():
    F.register("Test Guest", "#aabbcc")
    t = F.rich("Test Guest enters.")
    assert any("aabbcc" in str(sp.style) for sp in t.spans)
