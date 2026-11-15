"""God writes scenarios. Its output is untrusted: it must be validated and clamped."""
import json

from arena.engine.god import God, clean_persona, observations
from arena.engine.rules import Rules
from arena.lore.omens import EFFECT_BOUNDS, clean_effect, describe
from tests.helpers import make_game

NAMES = ["Magister Vellum", "Glitchwick", "Aurelia Null"]


def god():
    return God(None, "m", Rules())


def test_effects_are_clamped_to_safe_bounds():
    e = clean_effect({"dmg_mult": 99, "income": -50, "decay": 1000, "siege_cost": 40, "ritual_mult": 9, "bogus": 1})
    assert e["dmg_mult"] == EFFECT_BOUNDS["dmg_mult"][1]
    assert e["income"] == EFFECT_BOUNDS["income"][0]
    assert e["decay"] == EFFECT_BOUNDS["decay"][1]
    assert "bogus" not in e
    assert clean_effect("not a dict") == {} and clean_effect(None) == {}


def test_flags_accept_only_true_values_and_default_values_are_dropped():
    e = clean_effect({"peace": True, "audit": "false", "dmg_mult": 1.0})
    assert e == {"peace": 1}


def test_describe_tells_the_minds_the_truth():
    assert "percent" in describe({"dmg_mult": 1.5})
    assert describe({}) != ""


def test_parse_valid_scenario():
    text = json.dumps({"title": "The Soup Arrives", "text": "A pot appears.", "effect": {"dmg_mult": 1.3},
                       "decree": "No one may lie before noon.", "bounty": {"target": "glitchwick", "amount": 7},
                       "boons": [{"target": "Aurelia", "lumens": 3, "coherence": 0}]})
    sc = god().parse(text, NAMES, 4, False)
    assert sc.title == "The Soup Arrives" and sc.mods == {"dmg_mult": 1.3}
    assert sc.bounty == {"target": "Glitchwick", "amount": 7}
    assert sc.boons == [{"target": "Aurelia Null", "lumens": 3, "coherence": 0}]


def test_parse_clamps_bounty_boons_and_drops_unknown_targets():
    text = json.dumps({"title": "x", "text": "y", "bounty": {"target": "Glitchwick", "amount": 9999},
                       "boons": [{"target": "Nobody", "lumens": 5}, {"target": "Glitchwick", "lumens": 999, "coherence": -999}]})
    sc = god().parse(text, NAMES, 1, False)
    assert sc.bounty["amount"] <= 12
    assert len(sc.boons) == 1 and sc.boons[0]["lumens"] <= 8 and sc.boons[0]["coherence"] >= -12


def test_parse_rejects_garbage_so_the_deck_takes_over():
    g = god()
    assert g.parse("I am God and I refuse to use JSON.", NAMES, 1, False) is None
    assert g.parse("{}", NAMES, 1, False) is None


def test_arrival_only_when_allowed_and_valid():
    arr = {"name": "Brother Static", "epithet": "monk of the dial tone", "former_life": "ran a switchboard", "desire": "to be put through", "fear": "hello", "quirk": "hums"}
    text = json.dumps({"title": "A Knock", "text": "Someone arrives.", "arrival": arr})
    assert god().parse(text, NAMES, 1, True).arrival["name"] == "Brother Static"
    assert god().parse(text, NAMES, 1, False).arrival is None


def test_persona_validation():
    ok = {"name": "Pip", "epithet": "e", "former_life": "f", "desire": "d", "fear": "x", "quirk": "q"}
    assert clean_persona(ok)["name"] == "Pip"
    assert clean_persona(dict(ok, name="")) is None
    assert clean_persona(dict(ok, name="A Name That Is Far Too Long For Anyone To Say Aloud")) is None
    assert clean_persona({"name": "Pip"}) is None


def test_observations_are_facts_computed_from_the_game():
    g = make_game(1)
    obs = observations(g.s, g.rules)
    assert isinstance(obs, list) and all(isinstance(o, str) for o in obs)
