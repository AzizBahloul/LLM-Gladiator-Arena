"""Permadeath deletes models, so these tests never let a real `ollama rm` near anything."""
from arena.engine.actions import Action
from tests.helpers import make_game, make_hub

MODELS = {"old-model:latest": 4.0, "m1": 2.0, "m2": 2.0, "m3": 2.0, "narr": 4.0}


def game_with_hub(**kw):
    hub, admin, ledger = make_hub(MODELS, protected=["old-model:latest"], **kw)
    g = make_game(1, hub=hub, god=False)
    return g, hub, admin, ledger


def dissolve(g, name):
    w = g.s.wicks[name]
    w.coherence = 0
    g._process_deaths()
    return w


def test_a_dissolved_minds_model_is_deleted():
    g, hub, admin, ledger = game_with_hub()
    # give vellum a model nobody else uses
    names = list(g.s.wicks)
    g.s.wicks[names[0]].model = "m1"
    for n in names[1:]:
        g.s.wicks[n].model = "m2"
    w = dissolve(g, names[0])
    assert admin.removed == ["m1"] and w.wiped
    assert "m1" in ledger.data["wiped"]
    assert any(e.kind == "wipe" for e in g.bus.history)


def test_a_model_still_used_by_a_living_mind_is_kept():
    g, hub, admin, ledger = game_with_hub()
    names = list(g.s.wicks)
    for n in names:
        g.s.wicks[n].model = "m1"
    dissolve(g, names[0])
    assert admin.removed == []


def test_the_registrar_and_gods_model_is_never_deleted():
    g, hub, admin, ledger = game_with_hub()
    name = next(iter(g.s.wicks))
    g.s.wicks[name].model = "narr"
    for n in list(g.s.wicks)[1:]:
        g.s.wicks[n].model = "m2"
    dissolve(g, name)
    assert admin.removed == []


def test_models_installed_before_the_arena_ran_are_protected():
    g, hub, admin, ledger = game_with_hub()
    name = next(iter(g.s.wicks))
    g.s.wicks[name].model = "old-model:latest"
    for n in list(g.s.wicks)[1:]:
        g.s.wicks[n].model = "m2"
    dissolve(g, name)
    assert admin.removed == [] and "old-model:latest" in admin.models


def test_include_preexisting_puts_them_at_stake():
    g, hub, admin, ledger = game_with_hub(include_preexisting=True)
    name = next(iter(g.s.wicks))
    g.s.wicks[name].model = "old-model:latest"
    for n in list(g.s.wicks)[1:]:
        g.s.wicks[n].model = "m2"
    dissolve(g, name)
    assert admin.removed == ["old-model:latest"]


def test_permadeath_off_deletes_nothing():
    g, hub, admin, ledger = game_with_hub(enabled=False)
    name = next(iter(g.s.wicks))
    g.s.wicks[name].model = "m1"
    for n in list(g.s.wicks)[1:]:
        g.s.wicks[n].model = "m2"
    dissolve(g, name)
    assert admin.removed == []


def test_rules_can_switch_permadeath_off_too():
    hub, admin, ledger = make_hub(MODELS, protected=[])
    g = make_game(1, hub=hub, god=False, permadeath=False)
    name = next(iter(g.s.wicks))
    g.s.wicks[name].model = "m1"
    dissolve(g, name)
    assert admin.removed == []


def test_a_wiped_minds_echo_still_speaks_through_the_fallback_model():
    g, hub, admin, ledger = game_with_hub()
    names = list(g.s.wicks)
    g.s.wicks[names[0]].model = "m1"
    for n in names[1:]:
        g.s.wicks[n].model = "m2"
    w = dissolve(g, names[0])
    assert w.wiped and w.haunting
    used = []
    real = g.backend.complete
    g.backend.complete = lambda s, u, **k: (used.append(k.get("model")) or real(s, u, **k))
    g.mind.decide(g.s, w, [])
    assert used and set(used) == {g.narrator_model}


def test_wiped_minds_leave_the_roster_between_seasons_and_are_remembered():
    g, hub, admin, ledger = game_with_hub()
    g.rules.endless = True
    names = list(g.s.wicks)
    g.s.wicks[names[0]].model = "m1"
    for n in names[1:]:
        g.s.wicks[n].model = "m2"
    dissolve(g, names[0])
    g.s.ending = "backlog"
    g._finish()
    g._next_season()
    assert names[0] not in g.s.wicks
    assert g.s.history[-1]["standings"][0]["wiped"] is True
    assert len(g.s.wicks) >= g.rules.min_minds          # newborns refilled the roster
