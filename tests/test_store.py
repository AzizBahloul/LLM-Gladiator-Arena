"""Durability: closing at any moment loses nothing and repeats nothing."""
import json
from collections import Counter

import pytest

from arena.engine.events import EventBus
from arena.engine.game import Game
from arena.engine.state import GameState
from arena.engine.store import RunStore
from arena.llm.mock import MockBackend
from tests.helpers import config, make_game, tmp_store


class StopAfter(MockBackend):
    """A model that asks the game to stop after N calls, to land the close at an arbitrary moment."""

    def __init__(self, seed, n, game_ref):
        super().__init__(seed)
        self.n, self.ref = n, game_ref

    def complete(self, *a, **k):
        if self.calls >= self.n and self.ref:
            self.ref[0].stop()
        return super().complete(*a, **k)


def run_until(n, seed=9, cycles=6):
    store = tmp_store(seed)
    ref = []
    be = StopAfter(seed, n, ref)
    g = Game(config(cycles=cycles), be, EventBus(), seed=seed, store=store)
    ref.append(g)
    g.run()
    return store, g


def finish(store, seed=10, cycles=6):
    store2 = RunStore.open(str(store.root), store.run_id)
    state, cut = store2.load()
    g2 = Game(config(cycles=cycles), MockBackend(seed), EventBus(), state=state, store=store2)
    g2.run()
    return store2, g2, cut


@pytest.mark.parametrize("n", [3, 15, 40, 77, 120])
def test_resume_lands_cleanly_and_never_repeats(n):
    store, g = run_until(n)
    store2, g2, _ = finish(store)
    assert g2.s.ending == "backlog" and g2.s.cycle == 6
    evs = store2.events()
    c = Counter((e.cycle, e.kind) for e in evs if e.kind in ("chronicle", "ending", "epilogue", "cycle"))
    assert {k: v for k, v in c.items() if v > 1} == {}, "an entry was written twice after resuming"
    assert sum(1 for e in evs if e.kind == "act") == len({e.act for e in evs if e.kind == "act"})


def test_unfinished_work_is_set_aside_not_lost_or_replayed():
    store, g = run_until(40)
    seq_before = store.seq
    store2 = RunStore.open(str(store.root), store.run_id)
    state, cut = store2.load()
    assert store2.seq <= seq_before
    if cut:
        parts = list((store.dir / "partial").glob("journal-*.jsonl"))
        assert parts and sum(1 for _ in open(parts[0], encoding="utf-8")) == cut
    rows = [json.loads(l) for l in open(store.journal_path, encoding="utf-8")]
    assert [r["seq"] for r in rows] == list(range(1, len(rows) + 1))   # contiguous, no gaps, no duplicates


def _closed_in_phase(phase, seed=9):
    """Search for a stop point that leaves the saved run in a given phase of a cycle."""
    for n in range(2, 200, 3):
        store, _ = run_until(n, seed=seed)
        state, _ = RunStore.open(str(store.root), store.run_id).load()
        if state.phase == phase:
            return store
    raise AssertionError(f"no stop point landed in phase {phase!r}")


def _resume_counting(store, kinds):
    """Resume, let the interrupted cycle finish, and count model calls of the given kinds made inside it."""
    store2 = RunStore.open(str(store.root), store.run_id)
    state, _ = store2.load()
    first = state.cycle
    asked = {k: 0 for k in kinds}
    ref = []

    class Counting(MockBackend):
        def complete(self, system, user, **k):
            g = ref[0]
            if g.s.cycle > first:
                g.stop()
            elif k.get("kind") in asked:
                asked[k["kind"]] += 1
            return super().complete(system, user, **k)

    g2 = Game(config(cycles=6), Counting(1), EventBus(), state=state, store=store2)
    ref.append(g2)
    g2.run()
    return asked


def test_resume_after_everyone_chose_does_not_ask_for_choices_again():
    store = _closed_in_phase("acted")
    asked = _resume_counting(store, ["parley", "action"])
    assert asked == {"parley": 0, "action": 0}


def test_resume_after_parley_does_not_repeat_the_parley():
    store = _closed_in_phase("parleyed")
    asked = _resume_counting(store, ["parley"])
    assert asked["parley"] == 0


def test_snapshot_is_written_atomically_and_round_trips():
    store = tmp_store()
    g = make_game(3, store=store)
    g.s.phase = "begun"
    g.checkpoint()
    assert not list(store.dir.glob("*.tmp"))
    state, cut = RunStore.open(str(store.root), store.run_id).load()
    assert cut == 0 and state.phase == "begun" and set(state.wicks) == set(g.s.wicks)
    assert state.rng_state is not None


def test_season_history_is_written_once():
    store = tmp_store()
    summary = {"season": 1, "ending": "pen"}
    assert store.append_season(summary) is True
    assert store.append_season(summary) is False
    assert len(open(store.seasons_path).read().splitlines()) == 1


def test_a_torn_last_journal_line_is_ignored():
    store, g = run_until(10_000, cycles=2)
    with open(store.journal_path, "a", encoding="utf-8") as f:
        f.write('{"kind": "speech", "text": "cut off mid-wri')
    store2 = RunStore.open(str(store.root), store.run_id)
    store2.load()
    for ln in open(store2.journal_path, encoding="utf-8"):
        json.loads(ln)


def test_closing_the_ui_does_not_checkpoint_a_half_resolved_cycle():
    """StopGame must not save: the last checkpoint stands, and the cycle is redone from its phase."""
    store, g = run_until(30)
    snap = json.loads(store.snapshot_path.read_text(encoding="utf-8"))
    assert snap["state"]["phase"] in ("", "begun", "parleyed", "acted", "finished")
    state, _ = RunStore.open(str(store.root), store.run_id).load()
    assert state.cycle <= g.s.cycle


def test_endless_resume_does_not_replay_the_season_change():
    store = tmp_store(4)
    ref = []

    class Stopper(MockBackend):
        def complete(self, *a, **k):
            if ref and ref[0].s.season >= 2 and ref[0].s.season_cycle >= 1:
                ref[0].stop()
            return super().complete(*a, **k)

    g = Game(config(cycles=2, endless=True), Stopper(4), EventBus(), seed=4, store=store)
    ref.append(g)
    g.run()
    n_seasons = len([e for e in store.events() if e.kind == "season"])
    store2 = RunStore.open(str(store.root), store.run_id)
    state, _ = store2.load()
    g2 = Game(config(cycles=2, endless=True), MockBackend(5), EventBus(), state=state, store=store2)
    ref.clear(); ref.append(g2)
    g2.stop = lambda: None

    import threading, time
    t = threading.Thread(target=g2.run, daemon=True)
    t.start()
    time.sleep(0.5)
    g2._stop = True
    t.join(5)
    seasons = [e.data.get("season") for e in store2.events() if e.kind == "season"]
    assert len(seasons) == len(set(seasons)) and seasons[:n_seasons] == seasons[:n_seasons]
    hist = [h["season"] for h in state.history]
    assert hist == sorted(set(hist))
