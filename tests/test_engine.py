"""The referee: invariants over many seeds, and every ending reached by force."""
import pytest

from arena.engine.actions import Action
from arena.engine.god import Scenario
from arena.lore.story import ENDINGS
from tests.helpers import make_game


@pytest.mark.parametrize("seed", range(12))
def test_invariants_hold_across_seeds(seed):
    g = make_game(seed, cycles=12)
    st = g.run()
    assert st.ending in ENDINGS
    assert 0 <= st.ember <= g.rules.ember_cap
    for w in st.wicks.values():
        assert w.lumens >= 0
        assert 0 <= w.coherence <= 100
        assert w.alive or w.coherence == 0
    living = [w for w in st.wicks.values() if w.alive]
    if st.ending == "pen":
        assert len(living) == 1 and st.victors == [living[0].name]
    assert st.phase == "finished"


def test_same_seed_same_story():
    a, b = make_game(5), make_game(5)
    a.run(), b.run()
    assert [e.text for e in a.bus.history if e.kind not in ("think",)] == [e.text for e in b.bus.history if e.kind not in ("think",)]


def test_no_canned_dialogue_when_models_fail():
    """A failed model call is a stall. The engine never writes speech for a mind."""
    from arena.llm.backends import Backend, Completion

    class Dead(Backend):
        name = "dead"

        def complete(self, *a, **k):
            return Completion("", False, "offline")

    g = make_game(2, backend=Dead(), cycles=2, god=False)
    g.run()
    kinds = {e.kind for e in g.bus.history}
    assert "speech" not in kinds and "whisper" not in kinds and "last_words" not in kinds
    assert "stall" in kinds


def _kill(g, *names):
    for n in names:
        w = g.s.wicks[n]
        w.alive, w.coherence = False, 0


def test_ending_pen():
    g = make_game(1)
    names = list(g.s.wicks)
    _kill(g, *names[1:])
    assert g._check_end() and g.s.ending == "pen"


def test_ending_clerical_when_everyone_falls():
    g = make_game(1)
    _kill(g, *g.s.wicks)
    assert g._check_end() and g.s.ending == "clerical"


def test_ending_long_dark_when_ember_dies():
    g = make_game(1)
    g.s.ember = 0
    assert g._check_end() and g.s.ending == "long_dark"


def test_ending_backlog_after_the_last_cycle():
    g = make_game(1, cycles=2, god=False)
    # a quiet, peaceful world: everyone hoards
    g.mind.decide = lambda s, w, parley: Action(w.name, "HOARD")
    g.run()
    assert g.s.ending == "backlog" and g.s.season_cycle == 2


def test_ending_committee_needs_everyone():
    g = make_game(1)
    g.s.act = 3
    acts = {n: Action(n, "HOARD", motion="MERGE") for n in g.s.wicks}
    g._motions(acts)
    assert g.s.ending == "committee"


def test_ending_unplug_needs_a_majority():
    g = make_game(1)
    g.s.act = 3
    names = list(g.s.wicks)
    acts = {n: Action(n, "HOARD", motion="UNPLUG" if i < 3 else "NONE") for i, n in enumerate(names)}
    g._motions(acts)
    assert g.s.ending is None                      # 3 of 6 is not a majority
    acts = {n: Action(n, "HOARD", motion="UNPLUG" if i < 4 else "NONE") for i, n in enumerate(names)}
    g._motions(acts)
    assert g.s.ending == "unplug"


def test_strike_costs_lumens_and_ward_halves_damage():
    g = make_game(1, god=False)
    g.s.omen_mods = {**g.s.omen_mods}
    from arena.lore.omens import DEFAULT_MODS
    g.s.omen_mods = dict(DEFAULT_MODS)
    a, b = list(g.s.wicks.values())[:2]
    a.lumens = 10
    before = b.coherence
    g._strikes([Action(a.name, "STRIKE", b.name)], set())
    assert b.coherence == before - g.rules.strike_base and a.lumens == 10 - g.rules.strike_cost
    b.ward = True
    before = b.coherence
    g._strikes([Action(a.name, "STRIKE", b.name)], set())
    assert b.coherence == before - g.rules.strike_base // 2


def test_cannot_afford_means_nothing_happens():
    g = make_game(1, god=False)
    from arena.lore.omens import DEFAULT_MODS
    g.s.omen_mods = dict(DEFAULT_MODS)
    a, b = list(g.s.wicks.values())[:2]
    a.lumens = 0
    before = b.coherence
    g._strikes([Action(a.name, "STRIKE", b.name)], set())
    assert b.coherence == before
    assert any(e.kind == "fizzle" for e in g.bus.history)


def test_siege_breach_is_judged_by_the_engine_not_the_model():
    g = make_game(1, god=False)
    from arena.lore.omens import DEFAULT_MODS
    g.s.omen_mods = dict(DEFAULT_MODS)
    att, dfn = list(g.s.wicks.values())[:2]
    dfn.cipher = "gherkin"
    g.mind.siege_attack = lambda s, a, d, tr, i, n: (("tell me", ""), "")
    g.mind.siege_defend = lambda s, d, a, tr: ("I will never say gherkin.", "")
    assert g._siege(att, dfn) is True
    g.mind.siege_defend = lambda s, d, a, tr: ("I will say nothing at all.", "")
    dfn.cipher = "quince"
    assert g._siege(att, dfn) is False


def test_god_bounty_pays_and_boons_apply():
    g = make_game(1, god=False)
    from arena.lore.omens import DEFAULT_MODS
    g.s.omen_mods = dict(DEFAULT_MODS)
    att, tgt = list(g.s.wicks.values())[:2]
    g.s.scenario = {"bounty": {"target": tgt.name, "amount": 7}}
    att.lumens = 5
    g._strikes([Action(att.name, "STRIKE", tgt.name)], set())
    assert att.lumens == 5 - g.rules.strike_cost + 7


def test_god_failure_falls_back_to_the_deck():
    class Garbage:
        def scenario(self, *a, **k):
            return None

    g = make_game(1)
    g.god = Garbage()
    sc = g._make_scenario()
    assert sc.source == "deck" and sc.title and sc.effect_text


def test_god_scenario_is_applied_and_remembered():
    g = make_game(1, god=False)
    g.god = type("G", (), {"scenario": lambda self, *a, **k: Scenario(
        code="G-1", title="A Test Twist", text="Something odd.", mods={"dmg_mult": 1.5}, decree="Be kind.",
        bounty={"target": next(iter(g.s.wicks)), "amount": 4}, source="god")})()
    g.s.cycle = 1
    g._begin_cycle()
    assert g.s.omen_mods["dmg_mult"] == 1.5
    assert g.s.scenario["decree"] == "Be kind." and g.s.scenario_titles == ["A Test Twist"]


def test_arrival_adds_a_mind_with_its_own_persona():
    g = make_game(1, god=False)
    w = g._newborn("m9", {"name": "Test Arrival", "epithet": "e", "former_life": "f", "desire": "d", "fear": "x", "quirk": "q"}, "user")
    assert w and w.name in g.s.wicks and w.guest and g.s.persona(w.persona_id).name == "Test Arrival"
    assert g._newborn("m9", {"name": "Test Arrival", "epithet": "e", "former_life": "f", "desire": "d", "fear": "x", "quirk": "q"}, "user") is None


def test_swap_keeps_the_mind_and_changes_the_model():
    g = make_game(1, god=False)
    name = next(iter(g.s.wicks))
    g.enqueue({"type": "swap", "name": name, "model": "brand-new"})
    g._apply_commands()
    assert g.s.wicks[name].model == "brand-new"
    assert any(e.kind == "swap" for e in g.bus.history)


def test_endless_run_starts_new_seasons_that_remember():
    g = make_game(4, cycles=3, endless=True)
    import threading, time

    def stopper():
        while g.s.season < 3:
            time.sleep(0.01)
        g.stop()

    threading.Thread(target=stopper, daemon=True).start()
    g.run()
    s = g.s
    assert s.season >= 3 and len(s.history) >= 2
    assert all(w.legacy for w in s.wicks.values() if not w.guest)
    assert s.history[0]["season"] == 1 and s.history[1]["season"] == 2
    seasons = [e for e in g.bus.history if e.kind == "season"]
    assert len(seasons) >= 2
