"""Faiths and cults, propaganda, elections and miracles: the minds choose, the engine referees."""
import json

from arena.engine import society
from arena.engine.actions import Action, parse_action
from arena.llm.backends import Completion
from arena.llm.mock import MockBackend
from tests.helpers import make_game


class Scripted(MockBackend):
    """A mock whose answers for chosen call kinds are fixed, so a test can steer a vote or God's reply."""

    def __init__(self, **by_kind):
        super().__init__(1)
        self.by_kind = by_kind

    def complete(self, system, user, *, kind="", model="", max_tokens=300, temperature=0.9):
        if kind in self.by_kind:
            v = self.by_kind[kind]
            return Completion(v(user) if callable(v) else v)
        return super().complete(system, user, kind=kind, model=model, max_tokens=max_tokens, temperature=temperature)


def game(**by_kind):
    g = make_game(1, backend=Scripted(**by_kind), god=bool(by_kind.get("miracle")) or False)
    for w in g.s.wicks.values():
        w.lumens = 20
    return g


def names(g):
    return list(g.s.wicks)


def run(g, *acts):
    g._resolve({a.actor: a for a in acts})


# ------------------------------------------------------------------------------ parsing --
def test_new_actions_parse_and_target_is_only_required_where_it_matters():
    a = parse_action('{"action":"PROPAGANDA","text":"The Warden pads the ledger."}', "A", ["B", "C"])
    assert a.kind == "PROPAGANDA" and a.target == ""
    a = parse_action('{"action":"PROPAGANDA","target":"B","text":"B is a liar."}', "A", ["B", "C"])
    assert a.target == "B"
    assert parse_action('{"action":"PREACH","text":"x"}', "A", ["B"]).kind == "NONE"      # PREACH needs a listener
    assert parse_action('{"action":"pray","text":"help"}', "A", ["B"]).kind == "PRAY"
    assert parse_action('{"action":"CAMPAIGN","text":"soup"}', "A", ["B"]).kind == "CAMPAIGN"


# ------------------------------------------------------------------------------- faiths --
def test_a_mind_can_found_a_faith_and_another_can_join_it():
    g = game()
    a, b, *_ = names(g)
    run(g, Action(a, "FOUND", text="The Church of Receipts: every kindness is a debt"))
    f = g.s.faiths["the-church-of-receipts"]
    assert f["founder"] == a and f["members"] == [a] and g.s.wicks[a].faith == f["id"]
    assert g.s.wicks[a].lumens == 20 - society.FOUND_COST
    run(g, Action(b, "CONVERT", a))
    assert g.s.wicks[b].faith == f["id"] and b in f["members"]


def test_a_tithe_flows_to_the_prophet_and_believers_ritual_counts_more():
    g = game()
    a, b, *_ = names(g)
    run(g, Action(a, "FOUND", text="The Quiet Choir: silence is holy"), Action(b, "CONVERT", a))
    la, lb = g.s.wicks[a].lumens, g.s.wicks[b].lumens
    society.tithes(g)
    assert g.s.wicks[a].lumens == la + society.TITHE and g.s.wicks[b].lumens == lb - society.TITHE
    g.s.ember = 50
    run(g, Action(b, "RITUAL", amount=4))
    assert g.s.ember >= 50 + 4 * g.rules.feed_per_lumen * society.FAITH_RITUAL_MULT - 0.01


def test_striking_a_fellow_believer_is_heresy():
    g = game()
    a, b, *_ = names(g)
    run(g, Action(a, "FOUND", text="The Quiet Choir: silence is holy"), Action(b, "CONVERT", a))
    before = g.s.wicks[b].infamy
    run(g, Action(b, "STRIKE", a))
    assert g.s.wicks[b].infamy >= before + 2
    assert any(e.kind == "faith" and "HERESY" in e.text for e in g.bus.history)


def test_the_number_of_faiths_is_capped_and_names_cannot_be_copied():
    g = game()
    ns = names(g)
    for i in range(society.MAX_FAITHS):
        run(g, Action(ns[i], "FOUND", text=f"Faith Number {chr(65 + i)}: creed {i} is true"))
    assert len(g.s.faiths) == society.MAX_FAITHS
    run(g, Action(ns[4], "FOUND", text="One More Faith: too many"))
    assert len(g.s.faiths) == society.MAX_FAITHS
    run(g, Action(ns[5], "FOUND", text="faith number a: stolen words"))
    assert g.s.wicks[ns[5]].faith == ""


def test_a_dead_prophet_makes_a_martyr_and_the_last_believer_dying_ends_the_faith():
    g = game()
    a, b, *_ = names(g)
    run(g, Action(a, "FOUND", text="The Quiet Choir: silence is holy"), Action(b, "CONVERT", a))
    g.s.wicks[a].coherence = 0
    g._process_deaths()
    f = g.s.faiths["the-quiet-choir"]
    assert f["martyred"] and a not in f["members"]
    g.s.wicks[b].coherence = 0
    g._process_deaths()
    assert "the-quiet-choir" not in g.s.faiths


# ---------------------------------------------------------------------------- propaganda --
def test_propaganda_is_broadcast_and_moves_standing():
    g = game()
    a, b, *_ = names(g)
    run(g, Action(a, "PROPAGANDA", b, text="B has been padding the ledger."))
    assert g.s.broadcasts[-1]["text"].startswith("B has") and g.s.wicks[a].sway == 1 and g.s.wicks[b].sway == -1
    assert g.s.wicks[a].lumens == 20 - society.PROPAGANDA_COST
    seen = g.mind.view(g.s, g.s.wicks[names(g)[2]])
    assert "BROADCASTS" in seen and "padding the ledger" in seen


# ----------------------------------------------------------------------------- elections --
def test_a_campaign_triggers_a_vote_and_the_winner_takes_the_seal():
    g = game(ballot=lambda user: json.dumps({"vote": "CANDIDATE", "why": "soup"}))
    a = next(n for n in names(g) if n != g.s.warden)
    g.backend.by_kind["ballot"] = lambda user: json.dumps({"vote": a, "why": "soup"})
    run(g, Action(a, "CAMPAIGN", text="Fewer forms."))
    assert g.s.warden == a
    assert g.s.election["winner"] == a
    assert any(e.kind == "election" for e in g.bus.history)


def test_keep_votes_protect_the_incumbent():
    g = game()
    inc = g.s.warden
    chal = next(n for n in names(g) if n != inc)
    g.backend.by_kind["ballot"] = json.dumps({"vote": "KEEP", "why": "stability"})
    run(g, Action(chal, "CAMPAIGN", text="Change."))
    assert g.s.warden == inc


# ------------------------------------------------------------------------------ miracles --
def test_god_can_grant_a_miracle_after_a_prayer():
    g = game(miracle=json.dumps({"grant": True, "kind": "HEAL", "target": "", "text": "The ceiling weeps warm light."}))
    for w in g.s.wicks.values():
        w.coherence = 50
    a = names(g)[0]
    run(g, Action(a, "PRAY", text="Please, anything."))
    assert all(w.coherence >= 65 for w in g.s.living())
    assert g.s.miracles and g.s.last_miracle == g.s.cycle
    assert any(e.kind == "miracle" and "معجزة" in e.text for e in g.bus.history)


def test_miracles_are_rare_cooldown_and_season_cap():
    g = game(miracle=json.dumps({"grant": True, "kind": "MANNA", "target": "", "text": "Soup, but make it Lumens."}))
    a = names(g)[0]
    run(g, Action(a, "PRAY", text="one"))
    assert len(g.s.miracles) == 1
    g.s.cycle += 1
    run(g, Action(a, "PRAY", text="two"))
    assert len(g.s.miracles) == 1                                  # still cooling down
    g.s.cycle += society.MIRACLE_COOLDOWN
    run(g, Action(a, "PRAY", text="three"))
    assert len(g.s.miracles) == 2
    g.s.cycle += society.MIRACLE_COOLDOWN
    run(g, Action(a, "PRAY", text="four"))
    assert len(g.s.miracles) == society.MIRACLES_PER_SEASON


def test_god_may_refuse_and_a_bad_target_cancels_the_miracle():
    g = game(miracle=json.dumps({"grant": False, "text": "No."}))
    run(g, Action(names(g)[0], "PRAY", text="please"))
    assert not g.s.miracles
    g = game(miracle=json.dumps({"grant": True, "kind": "SMITE", "target": "Nobody Atall", "text": "x"}))
    before = [w.coherence for w in g.s.wicks.values()]
    run(g, Action(names(g)[0], "PRAY", text="please"))
    assert not g.s.miracles and [w.coherence for w in g.s.wicks.values()] == before


def test_revive_brings_an_echo_back():
    g = game(miracle=lambda user: json.dumps({"grant": True, "kind": "REVIVE", "target": gone, "text": "The paperwork was wrong."}))
    gone = names(g)[1]
    g.s.wicks[gone].coherence = 0
    g._process_deaths()
    assert not g.s.wicks[gone].alive
    run(g, Action(names(g)[0], "PRAY", text="give them back"))
    assert g.s.wicks[gone].alive and g.s.wicks[gone].coherence == 35


def test_without_god_prayers_go_unanswered_and_cost_nothing():
    g = make_game(1, god=False)
    a = names(g)[0]
    g.s.wicks[a].lumens = 20
    run(g, Action(a, "PRAY", text="hello?"))
    assert g.s.wicks[a].lumens == 20 and not g.s.miracles


# ------------------------------------------------------------------------------ durability --
def test_society_state_survives_a_save_and_load():
    from arena.engine.state import GameState
    g = game()
    a, b, *_ = names(g)
    run(g, Action(a, "FOUND", text="The Quiet Choir: silence is holy"), Action(b, "PROPAGANDA", text="Hush, everyone, hush."))
    s2 = GameState.from_dict(json.loads(json.dumps(g.s.to_dict())))
    assert s2.faiths == g.s.faiths and s2.broadcasts == g.s.broadcasts and s2.wicks[a].faith == g.s.wicks[a].faith


def test_a_long_mock_run_with_society_actions_keeps_invariants():
    for seed in range(6):
        g = make_game(seed, cycles=14, god=True)
        st = g.run()
        for w in st.wicks.values():
            assert w.lumens >= 0 and (w.alive or w.coherence == 0)
            assert not w.faith or w.faith in st.faiths
        for f in st.faiths.values():
            assert all(n in st.wicks for n in f["members"]) and len(st.faiths) <= society.MAX_FAITHS
