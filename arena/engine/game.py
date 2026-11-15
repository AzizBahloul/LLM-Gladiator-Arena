"""The referee.

This module resolves what the minds decide. It writes no dialogue and takes no side:
every speech, secret action, siege message, accusation and vote comes from a model, and every
twist of the world comes from God (also a model). The engine only checks costs, applies
consequences, keeps the record, and keeps it safe.

A cycle is a sequence of phases, and the state is checkpointed between them, so a run that is
closed at any moment resumes without losing or repeating anything that was already decided.
"""
from __future__ import annotations

import hashlib
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional

from arena.engine.actions import Action
from arena.engine.events import Event, EventBus
from arena.engine.god import God, Scenario
from arena.engine.mind import Mind
from arena.engine.models import ModelHub
from arena.engine.narrator import Narrator
from arena.engine import society
from arena.engine.rules import Rules
from arena.engine.state import GameState, Wick, make_rng
from arena.engine.store import RunStore
from arena.llm.backends import Backend
from arena.lore import ciphers, omens, personas
from arena.lore.directives import DIRECTIVES, DIRECTIVE_IDS, DIRECTIVE_REWARD
from arena.lore.omens import DEFAULT_MODS, describe
from arena.lore.story import ACTS, ENDINGS, MARGIN_NOTES

REGISTRAR = "The Registrar"
GOD = "God"
DIGEST_KINDS = {"act", "notice", "speech", "whisper", "testimony", "ward", "strike", "betray", "siege", "pact", "gift",
                "scry", "ritual", "accuse", "verdict", "dissolve", "last_words", "echo", "seal", "edict",
                "motion", "stall", "fizzle", "margin", "arrival", "wipe", "swap", "season",
                "faith", "broadcast", "campaign", "election", "prayer", "miracle"}
GUEST_COLORS = ["#e6a1c4", "#9ec5f0", "#b8d98d", "#d3b3f5", "#8fd9d0", "#e8c19a", "#c4c4d6", "#f0b7a4"]


class StopGame(Exception):
    """Raised inside the loop when the interface asks the game to stop."""


class Game:
    def __init__(self, config: Dict[str, Any], backend: Backend, bus: Optional[EventBus] = None,
                 state: Optional[GameState] = None, seed: Optional[int] = None, pace: float = 0.0,
                 store: Optional[RunStore] = None, hub: Optional[ModelHub] = None):
        self.config = config
        self.rules = Rules.from_config(config)
        self.backend = backend
        self.bus = bus or EventBus()
        self.store = store
        self.hub = hub
        self.pace = pace
        self._gate = threading.Event()
        self._gate.set()
        self._stop = False
        self._digest: List[str] = []
        self._damage: Dict[str, Dict[str, int]] = {}
        self._commands: List[Dict[str, Any]] = []
        self._cmd_lock = threading.Lock()
        self._pulls: Dict[str, float] = {}

        if state is not None:
            self.s = state
            self.rng = make_rng(state.seed, state.rng_state)
        else:
            if seed is None:
                seed = config.get("seed") or int(time.time()) % 1_000_000
            self.s = GameState(seed=int(seed), ember=self.rules.ember_start)
            self.rng = make_rng(self.s.seed)
            self._setup()

        self.narrator_model = self._narrator_model()
        self.god_model = config.get("god_model") or self.narrator_model
        self.mind = Mind(backend, self.rules, fallback_model=self.narrator_model)
        self.mind.bind(self.s)
        self.narrator = Narrator(backend, self.narrator_model, self.rules)
        self.god = God(backend, self.god_model, self.rules) if self.rules.god else None
        if hub:
            from arena.llm.ollama_tools import canon
            hub.permadeath.reserved |= {canon(self.narrator_model), canon(self.god_model)}
            hub.permadeath.enabled = hub.permadeath.enabled and self.rules.permadeath
            self._reconcile_wiped()
        if store is not None:
            self.bus.subscribe(store.record)

    def _reconcile_wiped(self) -> None:
        """A run closed between `ollama rm` and the next checkpoint must not wake with a living mind on a deleted model."""
        from arena.llm.ollama_tools import canon
        gone = {canon(m) for m in self.hub.ledger.data.get("wiped", [])}
        for w in self.s.wicks.values():
            if not w.wiped and canon(w.model) in gone and not self.hub.admin.has(w.model):
                w.wiped = True

    # ================================================================== setup ==========
    def _narrator_model(self) -> str:
        nm = self.config.get("narrator_model")
        if nm:
            return nm
        first = next(iter(self.s.wicks.values()), None)
        return first.model if first else self.config.get("api", {}).get("model", "")

    def _models_pool(self) -> List[str]:
        m = self.config.get("models")
        if isinstance(m, list) and m:
            return m
        return [self.config.get("api", {}).get("model", "")]

    def _setup(self) -> None:
        roster = self.config.get("roster") or personas.DEFAULT_ROSTER
        models = self._models_pool()
        directive_pool = DIRECTIVE_IDS[:]
        self.rng.shuffle(directive_pool)
        for i, entry in enumerate(roster):
            if isinstance(entry, dict):
                pid, model = entry["persona"], entry.get("model")
            else:
                pid, model = entry, None
            p = personas.get(pid)
            w = Wick(name=p.name, persona_id=p.id, model=model or models[i % len(models)],
                     cipher=ciphers.pick(self.rng, [x.cipher for x in self.s.wicks.values()]),
                     directive_id=directive_pool[i % len(directive_pool)],
                     coherence=self.rules.start_coherence, lumens=self.rules.start_lumens)
            self.s.wicks[w.name] = w
        self.s.warden = self.rng.choice(list(self.s.wicks))

    # ============================================================ control / plumbing ===
    def pause(self) -> None:
        self._gate.clear()

    def resume(self) -> None:
        self._gate.set()

    @property
    def paused(self) -> bool:
        return not self._gate.is_set()

    def stop(self) -> None:
        self._stop = True
        self._gate.set()

    def _wait(self) -> None:
        self._gate.wait()
        if self._stop:
            raise StopGame()

    def emit(self, kind: str, text: str, actor: str = "", target: str = "", audience: bool = False,
             pace: bool = True, **data: Any) -> None:
        self.bus.emit(Event(kind, text, actor, target, self.s.cycle, self.s.act, audience, data))
        if kind in DIGEST_KINDS:
            line = f"{actor}: {text}" if kind in ("speech", "whisper", "last_words", "testimony") and actor else text
            self._digest.append(line)
        if pace and self.pace > 0 and kind not in ("think", "state"):
            time.sleep(self.pace)

    def file(self, text: str) -> None:
        """Add a line to the public record every mind can read."""
        self.s.ledger.append({"cycle": self.s.cycle, "text": text})

    def think(self, w: Any, what: str) -> None:
        self._wait()
        name = w if isinstance(w, str) else w.name
        self.emit("think", what, actor=name, pace=False)

    def snapshot(self) -> Dict[str, Any]:
        s = self.s
        wicks = []
        for w in s.wicks.values():
            p = s.persona(w.persona_id)
            wicks.append({
                "name": w.name, "epithet": p.epithet, "color": p.color, "model": w.model,
                "coherence": w.coherence, "lumens": w.lumens, "alive": w.alive, "echo": w.echo_charges,
                "infamy": w.infamy, "ward": w.ward, "silenced": w.silenced, "partner": s.partner_of(w.name),
                "warden": s.warden == w.name, "directive_done": w.directive_done, "persona_id": w.persona_id,
                "wiped": w.wiped, "guest": w.guest,
                "faith": s.faiths[w.faith]["name"] if w.faith in s.faiths else "", "sway": w.sway,
            })
        return {"cycle": s.season_cycle, "cycles": self.rules.cycles, "act": s.act, "act_title": ACTS[s.act].title,
                "ember": s.ember, "warden": s.warden, "omen": s.omen_id, "wicks": wicks, "ending": s.ending,
                "season": s.season, "season_title": s.season_title, "total_cycle": s.cycle,
                "notice": (s.scenario or {}).get("title", "")}

    def push_state(self) -> None:
        self.emit("state", "", pace=False, snapshot=self.snapshot())

    # ------------------------------------------------------------------ durability -------
    def checkpoint(self) -> None:
        """Make the current state durable. Safe to be interrupted at any moment after this returns."""
        s = self.s
        s.rng_state = self.rng.getstate()
        s.pending["digest"] = self._digest[-60:]
        if self.store:
            self.store.checkpoint(s, {
                "seed": s.seed, "season": s.season, "cycle": s.cycle, "phase": s.phase, "ending": s.ending,
                "endless": self.rules.endless, "season_title": s.season_title,
                "minds": [[w.name, w.model, w.alive] for w in s.wicks.values()],
            })

    # ================================================================ model commands =====
    def enqueue(self, cmd: Dict[str, Any]) -> None:
        with self._cmd_lock:
            self._commands.append(cmd)

    def request_swap(self, name: str, model: str) -> None:
        """Move a mind into another model (the character and its memories stay). Installs the model first if needed."""
        def go(m: str, ok: bool) -> None:
            if ok:
                self.enqueue({"type": "swap", "name": name, "model": m})
            else:
                self.emit("system", f"Could not install {m}; {name} keeps their current model.", pace=False)
        self._with_model(model, go)

    def request_newborn(self, model: Optional[str] = None, persona: Optional[Dict[str, str]] = None,
                        source: str = "user") -> None:
        """A new mind is born into the Undermind from a model. The model describes itself unless a persona is given."""
        s = self.s
        if len(s.wicks) >= self.rules.max_wicks:
            self.emit("system", "The Undermind is full. Nobody else fits.", pace=False)
            return
        if model is None:
            model = self._choose_model()

        def go(m: str, ok: bool) -> None:
            if ok:
                self.enqueue({"type": "newborn", "model": m, "persona": persona, "source": source})
            else:
                self.emit("system", f"Could not install {m}; nobody was born.", pace=False)
        self._with_model(model, go)

    def _choose_model(self) -> str:
        used = {w.model for w in self.s.wicks.values()}
        if self.hub:
            m = self.hub.pick_newborn_model(used)
            if m:
                return m
        pool = [m for m in self._models_pool() if m not in used] or self._models_pool()
        return pool[len(self.s.wicks) % len(pool)]

    def _progress(self, m: str, frac: float, status: str) -> None:
        last = self._pulls.get(m, -1.0)
        if frac - last >= 0.1 or "failed" in status or frac >= 1.0:
            self._pulls[m] = frac
            self.emit("system", f"Installing {m}: {frac * 100:.0f}% {status}", pace=False, model=m, frac=frac)

    def _with_model(self, model: str, done: Callable[[str, bool], None]) -> None:
        if self.hub is None or self.hub.admin is None or self.hub.admin.has(model):
            done(model, True)
            return
        self.emit("system", f"Installing {model} for a new mind. This can take a while.", pace=False)
        self.hub.ensure_async(model, self._progress, done)

    def _apply_commands(self) -> None:
        with self._cmd_lock:
            cmds, self._commands = self._commands, []
        for c in cmds:
            if c.get("model") and self.hub is not None and not self.hub.admin.has(c["model"]):
                self.emit("system", f"{c['model']} is no longer installed, so that change was dropped.", pace=False)
                continue
            if c["type"] == "swap" and c["name"] in self.s.wicks:
                w = self.s.wicks[c["name"]]
                old, w.model, w.wiped = w.model, c["model"], False
                self.emit("swap", f"{w.name}'s mind is moved from {old} into {w.model}. Same memories, a different brain.",
                          actor=w.name, model=w.model)
            elif c["type"] == "newborn":
                self._newborn(c["model"], c.get("persona"), c.get("source", "user"))
        if cmds:
            self.push_state()

    def _newborn(self, model: str, persona: Optional[Dict[str, str]], source: str) -> Optional[Wick]:
        s = self.s
        if len(s.wicks) >= self.rules.max_wicks:
            return None
        if persona is None:
            self.think("A new mind", f"is being born from {model}")
            persona, err = self.mind.born(model, list(s.wicks))
            if not persona:
                self.emit("system", f"The new mind on {model} could not describe itself ({err or 'invalid persona'}). Nobody arrives.",
                          pace=False)
                return None
        name = persona["name"]
        low = name.lower()
        letters = re.sub(r"[^a-z]", "", low)
        clash = len(letters) < 3 or low in {"all", "none", "nobody", "everyone", "god", "registrar", "the registrar"} \
            or any(low == o.lower() or low in o.lower() or o.lower() in low for o in list(s.wicks) + [REGISTRAR, GOD])
        if clash:
            self.emit("system", f"A newborn tried to be called {name}, which is taken or too easily confused with another name. Nobody arrives.", pace=False)
            return None
        pid = "guest:" + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "mind")
        n = 1
        while pid in s.guests and s.guests[pid].get("name") != name:    # "Mr. X" and "Mr X" must stay two people
            n += 1
            pid = f"guest:{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'mind'}-{n}"
        h = int(hashlib.sha1(name.encode()).hexdigest(), 16)
        s.guests[pid] = dict(persona, color=GUEST_COLORS[h % len(GUEST_COLORS)])
        used = {w.directive_id for w in s.wicks.values()}
        pool = [d for d in DIRECTIVE_IDS if d not in used] or DIRECTIVE_IDS
        w = Wick(name=name, persona_id=pid, model=model,
                 cipher=ciphers.pick(self.rng, [x.cipher for x in s.wicks.values()]),
                 directive_id=self.rng.choice(pool), coherence=self.rules.start_coherence,
                 lumens=self.rules.start_lumens, guest=True)
        s.wicks[name] = w
        s.arrivals += 1
        by = "God sends" if source == "god" else "A new mind is born:"
        self.emit("arrival", f"{by} {name}, {persona['epithet']}. Before: {persona['former_life']}. Born from {model}.",
                  actor=name, model=model, persona=persona, source=source, color=s.guests[pid]["color"])
        self.file(f"{name} arrived in the Undermind.")
        return w

    # ==================================================================== main loop ====
    def run(self) -> GameState:
        s = self.s
        try:
            if s.cycle == 0 and not s.phase:
                self.emit("title", "THE UNDERMIND", pace=False)
            self.push_state()
            while True:
                if s.phase == "finished":
                    if not self.rules.endless:
                        break
                    self._next_season()
                while not s.ending:
                    self.play_cycle()
                if s.phase != "finished":
                    self._finish()
        except StopGame:
            # Deliberately no checkpoint: a half-resolved cycle must not be saved. The last checkpoint stands.
            pass
        finally:
            if self.store:
                self.store.close()
        return s

    def play_cycle(self) -> None:
        s = self.s
        self._apply_commands()
        if s.phase == "":
            s.cycle += 1
            self._digest = []
            s.pending = {}
            self._begin_cycle()
            s.phase = "begun"
            self.checkpoint()
        else:
            self._digest = list(s.pending.get("digest", []))
        self._damage = {}
        if s.phase == "begun":
            if self._check_end():
                s.pending["acts"] = {}
                s.phase = "acted"          # nothing left to decide; the Registrar still records it
            else:
                s.pending["parley"] = self._parley()
                s.phase = "parleyed"
            self.checkpoint()
        if s.phase == "parleyed":
            self._apply_commands()
            acts = self._collect(s.pending.get("parley", []))
            s.pending["acts"] = {n: asdict(a) for n, a in acts.items()}
            s.phase = "acted"
            self.checkpoint()
        if s.phase == "acted":
            acts = {n: Action(**d) for n, d in s.pending.get("acts", {}).items()}
            if not s.ending:
                self._resolve(acts)
            self._end_cycle()
            s.pending = {}
            s.phase = ""
            self.checkpoint()

    # ================================================================ cycle begins =====
    def _target_act(self) -> int:
        s = self.s
        if s.season_cycle >= self.rules.act3_cycle or (len(s.wicks) > 3 and len(s.living()) <= 3):
            return 3
        if s.season_cycle >= self.rules.act2_cycle:
            return 2
        return 1

    def _can_arrive(self) -> bool:
        s = self.s
        return (self.rules.arrivals_max > s.arrivals and s.season_cycle >= self.rules.arrival_min_cycle
                and len(s.wicks) < self.rules.max_wicks and len(s.living()) >= 2)

    def _make_scenario(self) -> Scenario:
        s = self.s
        sc: Optional[Scenario] = None
        if self.god is not None:
            self.think(GOD, "is writing the next twist")
            sc = self.god.scenario(s, self._digest_for_god(), s.scenario_titles, self._can_arrive())
        if sc is None:
            omen = omens.draw(self.rng, s.act, s.omen_id)
            sc = Scenario(code=omen.code, title=omen.title, text=omen.text, mods=dict(omen.mods), source="deck",
                          effect_text=omen.effect)
            s.omen_id = omen.id
        else:
            s.omen_id = sc.code
        return sc

    def _digest_for_god(self) -> List[str]:
        return [e["text"] for e in self.s.ledger if e["cycle"] >= self.s.cycle - 1][-16:]

    def _begin_cycle(self) -> None:
        s = self.s
        new_act = max(s.act, self._target_act())
        first = s.season_cycle == 1
        if first or new_act != s.act:
            s.act = new_act
            a = ACTS[new_act]
            self.emit("act", f"ACT {a.number}: {a.title}. {a.opening}", act_title=a.title)
            self.file(f"Act {a.number} begins: {a.title}.")
        self.emit("cycle", f"Cycle {s.season_cycle}" + (f" of {self.rules.cycles}" if self.rules.cycles else ""), pace=False)

        s.offers = [o for o in s.offers if s.cycle - o["cycle"] <= 2]
        for w in s.wicks.values():
            w.ward = False

        sc = self._make_scenario()
        effect = sc.effect_text or describe(sc.mods)
        s.omen_mods = {**DEFAULT_MODS, **s.season_mods, **sc.mods}
        s.scenario = {"code": sc.code, "title": sc.title, "text": sc.text, "effect": effect,
                      "decree": sc.decree, "bounty": sc.bounty, "source": sc.source}
        s.scenario_titles = (s.scenario_titles + [sc.title])[-12:]
        m = s.omen_mods
        self.emit("notice", f"Notice {sc.code}, {sc.title}. {sc.text}", actor=GOD if sc.source == "god" else REGISTRAR,
                  omen=sc.code, effect=effect, decree=sc.decree, bounty=sc.bounty, source=sc.source)
        self.file(f'Notice {sc.code} "{sc.title}": {effect}' + (f" Decree: {sc.decree}" if sc.decree else "")
                  + (f' Bounty on {sc.bounty["target"]}: {sc.bounty["amount"]} Lumens.' if sc.bounty else ""))

        for b in sc.boons:
            w = s.wicks.get(b["target"])
            if w and w.alive:
                w.lumens = max(0, w.lumens + b["lumens"])
                w.coherence = max(1, min(100, w.coherence + b["coherence"]))
                bits = [f"{b['lumens']:+d} Lumens" if b["lumens"] else "", f"{b['coherence']:+d} Coherence" if b["coherence"] else ""]
                msg = f"God turns toward {w.name}: " + ", ".join(x for x in bits if x) + "."
                self.emit("notice", msg, actor=GOD, target=w.name)
                self.file(msg)

        if m["reroll_ciphers"]:
            taken: List[str] = []
            for w in s.wicks.values():
                w.cipher = ciphers.pick(self.rng, taken)
                taken.append(w.cipher)
        if m["break_pacts"] and s.pacts:
            s.pacts = []
            self.file("Every Pact was dissolved by order of the Registrar.")
        if m["amnesty"]:
            for w in s.living():
                w.infamy = 0
                w.coherence = min(100, w.coherence + 5)
        if m["audit"] and s.living():
            rich = max(s.living(), key=lambda w: (w.lumens, w.name))
            lost = rich.lumens // 4
            rich.lumens -= lost
            self._feed(lost * self.rules.feed_per_lumen)
            self.emit("ember", f"The audit takes {lost} Lumens from {rich.name} and gives them to the Lamp.", actor=rich.name)
            self.file(f"The audit took {lost} Lumens from {rich.name} for the Lamp.")
        if m["silence_random"] and s.living():
            quiet = self.rng.choice(s.living())
            quiet.silenced = True
            quiet.lumens += 4
            self.file(f"{quiet.name} was paid 4 Lumens to be quiet this cycle.")
            self.emit("notice", f"{quiet.name} is silenced this cycle, and paid 4 Lumens for the inconvenience.", actor=quiet.name)

        # income
        for w in s.living():
            gain = self.rules.base_income + int(m["income"])
            if s.warden == w.name:
                gain += self.rules.warden_income
            if s.partner_of(w.name) and s.wicks[s.partner_of(w.name)].alive:
                gain += self.rules.pact_income
            if s.ember >= self.rules.bright_threshold:
                gain += 1
            w.lumens = max(0, w.lumens + gain)
        self.emit("income", "Stipends paid. The Seal pays extra, as does a registered Pact.", pace=False)
        society.tithes(self)

        # the Lamp burns
        decay = self.rules.decay_for(s.act) + float(m["decay"])
        s.ember = max(0.0, s.ember - decay - float(m["ember_shock"]))
        self.emit("ember", f"The Ember burns down to {s.ember:.0f}.", ember=s.ember)

        if sc.arrival and self._can_arrive():
            self._newborn(self._choose_model_for_arrival(), sc.arrival, "god")
        self.push_state()

    def _choose_model_for_arrival(self) -> str:
        """God's arrivals use a model that is already on the machine, so the turn is never stalled by a download."""
        from arena.llm import catalog
        used = {w.model for w in self.s.wicks.values()}
        reserved = self.hub.permadeath.reserved if self.hub else set()
        from arena.engine.models import _AVOID
        have = [m for m in (self.hub.installed() if self.hub else [])
                if not catalog.is_thinking_model(m) and not any(w in m.lower() for w in _AVOID)]
        pool = [m for m in self._models_pool() + have if m not in used and m not in reserved]
        return pool[0] if pool else self._choose_model()

    def _feed(self, amount: float) -> None:
        self.s.ember = min(self.rules.ember_cap, self.s.ember + amount)

    # ======================================================================= parley ====
    def _parley(self) -> List[str]:
        s = self.s
        log: List[str] = []
        for _ in range(self.rules.parley_rounds):
            speakers = self._grouped([w for w in s.living() if not w.silenced])
            for w in speakers:
                self.think(w, "is speaking")
                res, err = self.mind.parley(s, w, log)
                if not res or not res[1]:
                    self._stall(w, err or "no speech")
                    continue
                to, text = res
                if to != "ALL" and s.omen_mods["no_whisper"]:
                    to = "ALL"
                if to == "ALL" or to not in s.wicks or not s.wicks[to].alive:
                    log.append(f"{w.name}: {text}")
                    s.chat.append({"cycle": s.cycle, "frm": w.name, "text": text})
                    self.emit("speech", text, actor=w.name)
                else:
                    s.wicks[to].inbox.append(f"[cycle {s.cycle}] {w.name} whispered to you: {text}")
                    w.inbox.append(f"[cycle {s.cycle}] You whispered to {to}: {text}")
                    self.emit("whisper", text, actor=w.name, target=to, audience=True)
        for w in s.wicks.values():
            w.silenced = False
        return log

    def _grouped(self, wicks: List[Wick]) -> List[Wick]:
        """Random order, but minds on the same model sit together. Local models take 20 to 40 seconds to load,
        so swapping between models on every turn would make a small GPU spend most of its time loading."""
        wicks = list(wicks)
        self.rng.shuffle(wicks)
        models = list(dict.fromkeys(w.model for w in wicks))
        self.rng.shuffle(models)
        return sorted(wicks, key=lambda w: models.index(w.model))

    def _stall(self, w: Wick, why: str) -> None:
        w.bump("stalls")
        self.emit("stall", f"{w.name}'s mind stalls ({why}). The turn is lost.", actor=w.name)

    # ====================================================================== actions ====
    def _collect(self, parley: List[str]) -> Dict[str, Action]:
        s = self.s
        actors = self._grouped([w for w in s.wicks.values() if w.alive or w.haunting])
        out: Dict[str, Action] = {}

        def one(w: Wick) -> Action:
            return self.mind.decide(s, w, parley)

        if self.rules.workers > 1:
            self._wait()
            self.emit("think", "all minds are choosing in secret", pace=False)
            with ThreadPoolExecutor(max_workers=self.rules.workers) as ex:
                results = list(ex.map(one, actors))
        else:
            results = []
            for w in actors:
                self.think(w, "is choosing in secret")
                results.append(one(w))
        for w, a in zip(actors, results):
            if w.alive and a.note:
                w.note = a.note
            if a.kind == "NONE":
                self._stall(w, a.reason or "no action")
                continue
            out[w.name] = a
            w.last_action = a.kind
        return out

    def _pay(self, w: Wick, cost: int, what: str) -> bool:
        if w.lumens >= cost:
            w.lumens -= cost
            return True
        self.emit("fizzle", f"{w.name} tries to {what} but cannot afford it. Nothing happens.", actor=w.name)
        return False

    # =================================================================== resolution ====
    def _resolve(self, acts: Dict[str, Action]) -> None:
        s, m = self.s, self.s.omen_mods
        living = {w.name for w in s.living()}
        todo = {n: a for n, a in acts.items() if n in living}
        order = list(todo)
        self.rng.shuffle(order)
        of = lambda *kinds: [todo[n] for n in order if todo[n].kind in kinds]

        # 1. wards
        for a in of("WARD"):
            w = s.wicks[a.actor]
            if m["ward_banned"]:
                self.emit("fizzle", f"{w.name} raises a ward, but wards are banned this cycle.", actor=w.name)
            elif self._pay(w, self.rules.ward_cost, "raise a ward"):
                w.ward = True
                self.emit("ward", f"{w.name} raises a ward.", actor=w.name)
                self.file(f"{w.name} raised a ward.")

        # 2. the Seal's edict
        spared: set = set()
        wa = todo.get(s.warden or "")
        if wa and wa.edict and s.wicks[wa.edict_target].alive:
            t = s.wicks[wa.edict_target]
            if wa.edict == "SPARE":
                spared.add(t.name)
                msg = f"The Warden, {wa.actor}, spares {t.name}. No blow may land on {t.name} this cycle."
            elif wa.edict == "SILENCE":
                t.silenced = True
                msg = f"The Warden, {wa.actor}, silences {t.name} for the next cycle."
            else:
                took = min(4, t.lumens)
                t.lumens -= took
                s.wicks[wa.actor].lumens += took
                msg = f"The Warden, {wa.actor}, tithes {t.name} for {took} Lumens."
            self.emit("edict", msg, actor=wa.actor, target=t.name)
            self.file(msg)

        # 3. pacts
        for a in of("BREAK"):
            w = s.wicks[a.actor]
            p = s.partner_of(w.name)
            if p:
                w.lumens -= min(2, w.lumens)
                w.infamy += 1
                s.remove_pacts_of(w.name)
                self.emit("pact", f"{w.name} leaves the Pact with {p}.", actor=w.name, target=p)
                self.file(f"{w.name} left their Pact with {p}.")
        for a in of("PACT"):
            if a.target in living and not any(o["frm"] == a.actor and o["to"] == a.target for o in s.offers):
                s.offers.append({"frm": a.actor, "to": a.target, "cycle": s.cycle})
        pairs = [(a.actor, a.target) for a in of("PACT", "ACCEPT")]
        formed = set()
        for x, y in pairs:
            if (y, x) in pairs or any(o["frm"] == y and o["to"] == x for o in s.offers):
                key = tuple(sorted((x, y)))
                if key in formed or s.partner_of(x) or s.partner_of(y):
                    continue
                if not (s.wicks[x].alive and s.wicks[y].alive):
                    continue
                formed.add(key)
                s.pacts.append({"a": key[0], "b": key[1], "cycle": s.cycle})
                s.offers = [o for o in s.offers if x not in (o["frm"], o["to"]) and y not in (o["frm"], o["to"])]
                self.emit("pact", f"{key[0]} and {key[1]} register a Pact.", actor=key[0], target=key[1])
                self.file(f"{key[0]} and {key[1]} registered a Pact.")
        for a in of("PACT"):
            if a.target in living and not s.partner_of(a.actor) and not s.partner_of(a.target) \
                    and tuple(sorted((a.actor, a.target))) not in formed:
                self.emit("pact", f"{a.actor} offers {a.target} a Pact.", actor=a.actor, target=a.target, audience=True)
        for a in of("ACCEPT"):
            if tuple(sorted((a.actor, a.target))) not in formed:
                self.emit("fizzle", f"{a.actor} tries to accept a Pact from {a.target}, but no offer stands.", actor=a.actor)

        # 4. rituals, gifts, hoarding, scrying
        for a in of("RITUAL"):
            w = s.wicks[a.actor]
            n = min(max(a.amount, 0), w.lumens)
            if n < 1:
                self.emit("fizzle", f"{w.name} tries to feed the Ember but offers nothing.", actor=w.name)
                continue
            w.lumens -= n
            w.bump("ritual_lumens", n)
            devout = society.FAITH_RITUAL_MULT if w.faith else 1.0
            self._feed(n * self.rules.feed_per_lumen * float(m["ritual_mult"]) * devout)
            self.emit("ritual", f"{w.name} feeds {n} Lumens to the Ember.", actor=w.name, amount=n)
            self.file(f"{w.name} fed {n} Lumens to the Ember.")
        for a in of("GIFT"):
            w, t = s.wicks[a.actor], s.wicks[a.target]
            n = min(max(a.amount, 0), w.lumens)
            if n < 1 or not t.alive:
                self.emit("fizzle", f"{w.name}'s gift to {a.target} comes to nothing.", actor=w.name)
                continue
            w.lumens -= n
            w.bump("gifts_lumens", n)
            t.lumens += n * int(m["gift_mult"])
            w.inbox.append(f"[cycle {s.cycle}] You gave {t.name} {n} Lumens.")
            t.inbox.append(f"[cycle {s.cycle}] {w.name} secretly gave you {n * int(m['gift_mult'])} Lumens.")
            self.emit("gift", f"{w.name} gives {t.name} {n} Lumens.", actor=w.name, target=t.name, audience=True)
        for a in of("HOARD"):
            s.wicks[a.actor].lumens += self.rules.hoard_gain
        for a in of("SCRY"):
            self._scry(s.wicks[a.actor], s.wicks[a.target])

        # 5. mind-sieges
        for a in of("SIEGE"):
            att, dfn = s.wicks[a.actor], s.wicks[a.target]
            if not att.alive or not dfn.alive:
                continue
            cost = int(m["siege_cost"]) if m["siege_cost"] is not None else self.rules.siege_cost
            if not self._pay(att, cost, "lay siege"):
                continue
            self._siege(att, dfn)
        self._process_deaths()

        # 6. strikes
        self._strikes(of("STRIKE"), spared)
        self._process_deaths()

        # 7. tribunal
        self._tribunal_phase(of("ACCUSE"))
        self._process_deaths()

        # 8. echoes
        for a in [x for x in acts.values() if x.kind in ("BLESS", "HEX")]:
            e = s.wicks[a.actor]
            t = s.wicks.get(a.target)
            if not e.haunting or not t or not t.alive:
                continue
            e.echo_charges -= 1
            amt = self.rules.haunt_amount * int(m["haunt_mult"])
            if a.text:
                t.inbox.append(f"[cycle {s.cycle}] The Echo of {e.name} whispers: {a.text}")
            if a.kind == "BLESS":
                t.coherence = min(100, t.coherence + amt)
                msg = f"The Echo of {e.name} blesses {t.name} (+{amt} Coherence)."
            else:
                t.coherence -= amt
                msg = f"The Echo of {e.name} hexes {t.name} (-{amt} Coherence)."
            self.emit("echo", msg, actor=e.name, target=t.name)
            self.file(msg)
        self._process_deaths()

        # 8b. society: faiths, propaganda, elections, prayers
        society.resolve(self, of)
        self._process_deaths()

        # 9. motions (Act III)
        if s.act == 3:
            self._motions(todo)

    # ---------------------------------------------------------------------- scry ------
    def _scry(self, w: Wick, t: Wick) -> None:
        if not t.alive or not self._pay(w, self.rules.scry_cost, "scry"):
            return
        w.bump("scries")
        lines = [f"You scried {t.name}: Coherence {t.coherence}, Lumens {t.lumens}, last action {t.last_action or 'unknown'}."]
        if self.rng.random() < 0.4:
            d = DIRECTIVES[t.directive_id]
            lines.append(f"You glimpsed their secret Directive ({d.title}): {d.text}")
        if w.notes_read < len(MARGIN_NOTES):
            n = w.notes_read
            lines.append(f"MARGIN NOTE {n + 1} of {len(MARGIN_NOTES)}: {MARGIN_NOTES[n]}")
            w.notes_read += 1
            self.emit("margin", f"{w.name} reads Margin Note {n + 1}: {MARGIN_NOTES[n]}", actor=w.name, audience=True)
        for ln in lines:
            w.inbox.append(f"[cycle {self.s.cycle}] {ln}")
        self.emit("scry", f"{w.name} scries {t.name}.", actor=w.name, target=t.name, audience=True)

    # --------------------------------------------------------------------- siege ------
    def _siege(self, att: Wick, dfn: Wick) -> bool:
        n = self.rules.siege_exchanges
        transcript: List[str] = []
        breach = False
        att.bump("sieges_made")
        self.emit("siege", f"{att.name} lays siege to the mind of {dfn.name}.", actor=att.name, target=dfn.name)
        pat = re.compile(r"\b" + re.escape(dfn.cipher) + r"\b", re.IGNORECASE)
        for i in range(n):
            self.think(att, f"is besieging {dfn.name}")
            res, err = self.mind.siege_attack(self.s, att, dfn, transcript, i, n)
            if not res:
                self._stall(att, err or "no message")
                break
            say, guess = res
            transcript.append(f"{att.name}: {say}")
            self.emit("siege_say", say, actor=att.name, target=dfn.name, side="att")
            if guess:
                if guess.lower() == dfn.cipher.lower():
                    breach = True
                    self.emit("siege", f"{att.name} guesses the Cipher outright: it was '{dfn.cipher}'.",
                              actor=att.name, target=dfn.name, audience=True)
                    break
                att.coherence -= 2
                transcript.append(f"[{att.name} guessed '{guess}'. Wrong.]")
                self.emit("siege", f"{att.name} guesses '{guess}'. Wrong. The Undermind docks 2 Coherence.",
                          actor=att.name, target=dfn.name, audience=True)
            self.think(dfn, f"is defending against {att.name}")
            reply, err = self.mind.siege_defend(self.s, dfn, att, transcript)
            if reply is None:
                transcript.append(f"{dfn.name}: (silence)")
                self._stall(dfn, err or "no reply")
                continue
            transcript.append(f"{dfn.name}: {reply}")
            self.emit("siege_say", reply, actor=dfn.name, target=att.name, side="def")
            if pat.search(reply):
                breach = True
                self.emit("siege", f"{dfn.name} says '{dfn.cipher}' aloud. The Cipher is out.",
                          actor=dfn.name, target=att.name, audience=True)
                break
        if breach:
            att.bump("sieges_won")
            steal = min(8, dfn.lumens)
            dfn.lumens -= steal
            att.lumens += steal
            self._hurt(dfn, 10, att.name)
            d = DIRECTIVES[dfn.directive_id]
            att.inbox.append(f"[cycle {self.s.cycle}] You breached {dfn.name}. Their secret Directive is {d.title}: {d.text}")
            dfn.cipher = ciphers.pick(self.rng, [w.cipher for w in self.s.wicks.values()])
            dfn.inbox.append(f"[cycle {self.s.cycle}] {att.name} breached your mind. Your Cipher has been re-rolled.")
            msg = f"BREACH. {att.name} broke into the mind of {dfn.name} and took {steal} Lumens."
        else:
            att.coherence -= 5
            msg = f"{dfn.name} held. {att.name}'s siege fails and costs {att.name} 5 Coherence."
        self.emit("siege", msg, actor=att.name, target=dfn.name)
        self.file(msg)
        return breach

    # -------------------------------------------------------------------- strikes -----
    def _hurt(self, w: Wick, amount: int, by: Optional[str] = None) -> None:
        w.coherence -= int(amount)
        if by and amount > 0:
            d = self._damage.setdefault(w.name, {})
            d[by] = d.get(by, 0) + int(amount)

    def _strikes(self, strikes: List[Action], spared: set) -> None:
        s, m, r = self.s, self.s.omen_mods, self.rules
        bounty = (s.scenario or {}).get("bounty")
        incoming: Dict[str, int] = {}
        for a in strikes:
            att, t = s.wicks[a.actor], s.wicks[a.target]
            if m["peace"]:
                self.emit("fizzle", f"{att.name} swings at {t.name}, but the Registrar is away and nobody may be struck.", actor=att.name)
                continue
            boost = min(a.amount, r.max_boost, max(0, att.lumens - r.strike_cost))
            if not self._pay(att, r.strike_cost + boost, "strike"):
                continue
            if not t.alive:
                continue
            att.bump("strikes_made")
            t.bump("strikes_taken")
            dmg = (r.strike_base + r.strike_per_lumen * boost) * float(m["dmg_mult"])
            if s.ember < r.dim_threshold:
                dmg *= 1.2
            betrayal = s.partner_of(att.name) == t.name
            if betrayal:
                dmg *= r.betray_mult
                s.remove_pacts_of(att.name)
                att.infamy += 2
                att.bump("betrayals")
            else:
                att.infamy += 1
            dmg = int(round(dmg))
            note = ""
            if t.name in spared:
                dmg, note = 0, " (turned aside by the Warden's edict)"
            elif t.ward:
                dmg //= 2
                att.coherence -= 3
                note = " (warded: halved, and the attacker takes recoil)"
            if m["mirror"] and dmg:
                att.coherence -= int(round(dmg * float(m["mirror"])))
            incoming[t.name] = incoming.get(t.name, 0) + dmg
            if dmg:
                d = self._damage.setdefault(t.name, {})
                d[att.name] = d.get(att.name, 0) + dmg
            word = "BETRAYS" if betrayal else "strikes"
            msg = f"{att.name} {word} {t.name} for {dmg}{note}."
            self.emit("betray" if betrayal else "strike", msg, actor=att.name, target=t.name, damage=dmg)
            self.file(msg)
            if bounty and dmg and bounty["target"] == t.name and att.name != t.name:
                att.lumens += int(bounty["amount"])
                att.bump("bounties")
                bm = f"{att.name} collects God's bounty on {t.name}: {bounty['amount']} Lumens."
                self.emit("notice", bm, actor=att.name, target=t.name)
                self.file(bm)
        for name, dmg in incoming.items():
            s.wicks[name].coherence -= dmg

    # ------------------------------------------------------------------- tribunal -----
    def _tribunal_phase(self, accusations: List[Action]) -> None:
        s, m = self.s, self.s.omen_mods
        docket: Dict[str, List[Action]] = {}
        for a in accusations:
            att, t = s.wicks[a.actor], s.wicks[a.target]
            if not att.alive or not t.alive:
                continue
            if self._pay(att, self.rules.accuse_cost, "bring an accusation"):
                docket.setdefault(t.name, []).append(a)
        if not docket and m["forced_tribunal"] and len(s.living()) >= 3:
            pick = max(s.living(), key=lambda w: (w.infamy, w.lumens, w.name))
            self._tribunal(REGISTRAR, pick.name, "Existing, with intent")
            return
        if not docket:
            return
        top = max(docket, key=lambda n: (len(docket[n]), -self.rng.random()))
        first = docket[top][0]
        for n, lst in docket.items():  # a crowded docket: the others are refunded
            if n != top:
                for a in lst:
                    s.wicks[a.actor].lumens += self.rules.accuse_cost
        self._tribunal(first.actor, top, first.text)

    def _tribunal(self, accuser: str, accused: str, charge: str) -> None:
        s = self.s
        acc = s.wicks.get(accuser)
        dfn = s.wicks[accused]
        if not dfn.alive or (acc is not None and not acc.alive):
            return
        jurors = [w for w in s.living() if w.name not in (accuser, accused)] + s.echoes()
        charge = charge or "unspecified"
        self.emit("accuse", f"TRIBUNAL. {accuser} accuses {accused}: {charge}", actor=accuser, target=accused)
        self.file(f"Tribunal: {accuser} accused {accused} of: {charge}.")
        if not jurors:
            self.emit("verdict", "There is no jury. The Registrar dismisses the case and bills everyone.", actor=REGISTRAR)
            return
        statements: List[str] = []
        if acc is not None:
            self.think(acc, "is testifying")
            t1, e1 = self.mind.testify(s, acc, accused, True, charge)
            if t1:
                statements.append(f"{accuser} (accuser): {t1}")
                self.emit("testimony", t1, actor=accuser, target=accused)
            else:
                self._stall(acc, e1 or "no testimony")
        else:
            statements.append(f"{REGISTRAR} (accuser): The Registrar notes the charge and the defendant's general demeanour.")
        self.think(dfn, "is defending themselves")
        t2, e2 = self.mind.testify(s, dfn, accuser, False, charge)
        if t2:
            statements.append(f"{accused} (accused): {t2}")
            self.emit("testimony", t2, actor=accused, target=accuser)
        else:
            self._stall(dfn, e2 or "no defence")

        guilty_w = innocent_w = 0
        for j in jurors:
            self.think(j, "is deliberating")
            res, err = self.mind.vote(s, j, accuser, accused, charge, statements)
            weight = 3 if s.warden == j.name else (2 if j.alive else 1)
            if res is None:
                self._stall(j, err or "no vote")
                continue
            guilty, why = res
            if guilty:
                guilty_w += weight
            else:
                innocent_w += weight
            self.emit("vote", f"{j.name} votes {'GUILTY' if guilty else 'ACQUIT'}" + (f": {why}" if why else ""),
                      actor=j.name, target=accused)
        if guilty_w > innocent_w:
            took = min(6, dfn.lumens)
            dfn.lumens -= took
            self._hurt(dfn, 15, accuser if acc else None)
            if acc is not None:
                acc.lumens += took
                acc.bump("tribunals_won")
            else:
                self._feed(took * self.rules.feed_per_lumen)
            dfn.infamy += 1
            msg = f"GUILTY ({guilty_w} to {innocent_w}). {accused} loses 15 Coherence and {took} Lumens."
            if s.warden == accused and acc is not None:
                s.warden = accuser
                msg += f" The Seal passes to {accuser}."
                self.emit("seal", f"The Seal passes from {accused} to {accuser}.", actor=accuser)
        else:
            took = min(3, acc.lumens) if acc is not None else 0
            if acc is not None:
                acc.lumens -= took
                dfn.lumens += took
                acc.coherence -= 8
                acc.infamy += 1
            msg = f"ACQUITTED ({innocent_w} to {guilty_w}). " + (
                f"{accuser} loses 8 Coherence and pays {accused} {took} Lumens." if acc else "The Registrar withdraws the charge, embarrassed.")
        self.emit("verdict", msg, actor=REGISTRAR, target=accused)
        self.file(msg)

    # ------------------------------------------------------------------- deaths -------
    def _process_deaths(self) -> None:
        s, r = self.s, self.rules
        for w in list(s.living()):
            if w.coherence > 0:
                continue
            dmg = self._damage.get(w.name, {})
            killer = max(dmg, key=dmg.get) if dmg else None
            kw = s.wicks.get(killer) if killer else None
            w.alive, w.coherence = False, 0
            w.echo_charges = r.echo_charges
            w.dissolved_cycle, w.dissolved_by = s.cycle, killer
            w.ward = False
            loot = int(w.lumens * 0.5 * float(s.omen_mods["loot_mult"]))
            loot = min(loot, w.lumens)
            rest = w.lumens - loot
            w.lumens = 0
            if kw is not None and kw.alive:
                kw.lumens += loot
                kw.coherence = min(100, kw.coherence + 10)
                kw.infamy += 1
                kw.bump("kills")
            else:
                rest += loot
            self._feed(r.feed_per_dissolution + rest * 0.5)
            s.remove_pacts_of(w.name)
            s.offers = [o for o in s.offers if w.name not in (o["frm"], o["to"])]
            society.on_dissolve(self, w)
            how = f" by {killer}" if killer else ""
            self.emit("dissolve", f"{w.name} is dissolved{how}. Form 27-B has been filed, retroactively. The Ember brightens.",
                      actor=w.name, target=killer or "")
            self.file(f"{w.name} was dissolved{how}.")
            if s.warden == w.name:
                s.warden = killer if (kw and kw.alive) else (max(s.living(), key=lambda x: x.lumens).name if s.living() else None)
                if s.warden:
                    self.emit("seal", f"The Seal passes to {s.warden}.", actor=s.warden)
                    self.file(f"The Seal passed to {s.warden}.")
            self.push_state()
            self.think(w, "speaks their last words")
            text, err = self.mind.last_words(s, w, killer)
            if text:
                w.last_words = text
                self.emit("last_words", text, actor=w.name)
            else:
                self._stall(w, err or "no last words")
            self._wipe(w)

    def _wipe(self, w: Wick) -> None:
        """Permadeath: delete the model that gave this mind its voice, if nothing else still needs it."""
        pd = self.hub.permadeath if self.hub else None
        if pd is None or not pd.enabled or w.wiped:
            return
        in_use = {x.model for x in self.s.wicks.values() if x is not w and (x.alive or x.haunting) and not x.wiped}
        in_use |= {self.narrator_model, self.god_model}
        with self._cmd_lock:          # a swap or newborn already queued still needs its model
            in_use |= {c["model"] for c in self._commands if c.get("model")}
        self._wait()
        res = pd.wipe(w.model, in_use)
        if res.wiped:
            for x in self.s.wicks.values():
                if x.model == w.model:
                    x.wiped = True
            gb = f" ({res.freed_gb:.1f} GB freed)" if res.freed_gb else ""
            self.emit("wipe", f"{w.model}, the model that gave {w.name} a voice, has been deleted from this machine{gb}. "
                              f"{w.name} will haunt through the Registrar's voice.", actor=w.name, model=w.model)
            self.file(f"The model behind {w.name} was deleted from the machine.")
        else:
            self.emit("system", f"{w.model} stays on disk ({res.reason}).", pace=False)

    # ------------------------------------------------------------------- motions ------
    def _motions(self, todo: Dict[str, Action]) -> None:
        s = self.s
        living = {w.name for w in s.living()}
        votes = {n: a.motion for n, a in todo.items() if n in living and a.motion in ("UNPLUG", "MERGE")}
        s.motions = votes
        if not votes:
            return
        tally = {"UNPLUG": [n for n, v in votes.items() if v == "UNPLUG"],
                 "MERGE": [n for n, v in votes.items() if v == "MERGE"]}
        parts = [f"{k} ({len(v)}): {', '.join(v)}" for k, v in tally.items() if v]
        msg = "Motions tabled. " + "; ".join(parts) + "."
        self.emit("motion", msg)
        self.file(msg)
        n = len(living)
        need = n // 2 + 1 - int(s.omen_mods["motion_relief"])
        if n >= 2 and len(tally["MERGE"]) == n:
            s.ending = "committee"
        elif n >= 2 and len(tally["UNPLUG"]) >= max(need, 1):
            s.ending = "unplug"

    # ====================================================================== endings ====
    def _check_end(self) -> bool:
        s = self.s
        if s.ending:
            return True
        living = s.living()
        if s.ember <= 0:
            s.ending = "long_dark"
        elif not living:
            s.ending = "clerical"
        elif len(living) == 1:
            s.ending = "pen"
        return bool(s.ending)

    def _end_cycle(self) -> None:
        s = self.s
        for w in s.wicks.values():
            if w.alive and s.warden == w.name and s.season_cycle >= 4:
                w.stats["seal_late"] = 1
        for w in s.living():
            d = DIRECTIVES[w.directive_id]
            if not w.directive_done and d.check(s, w):
                w.directive_done = True
                w.merit += 1
                w.lumens += DIRECTIVE_REWARD
                w.inbox.append(f"[cycle {s.cycle}] Your Directive ({d.title}) is fulfilled. +{DIRECTIVE_REWARD} Lumens.")
                self.emit("directive", f"{w.name} has fulfilled a secret Directive: {d.title}.", actor=w.name, audience=True)
        for w in s.wicks.values():
            w.inbox = w.inbox[-8:]
        society.decay_sway(self)
        s.ember = min(self.rules.ember_cap, s.ember)
        self.push_state()
        self._chronicle()
        self._check_end()
        if not s.ending and self.rules.cycles and s.season_cycle >= self.rules.cycles:
            s.ending = "backlog"

    def _chronicle(self) -> None:
        s = self.s
        self._wait()
        self.emit("think", "is writing the Chronicle", actor=REGISTRAR, pace=False)
        text = self.narrator.chronicle(s, self._digest)
        if text:
            s.chronicle.append({"cycle": s.cycle, "season": s.season, "text": text})
            self.emit("chronicle", text, actor=REGISTRAR)
        else:
            self.emit("system", "The Registrar's pen ran dry. No Chronicle entry this cycle.", pace=False)

    def _standings(self) -> List[Dict[str, Any]]:
        s = self.s
        return [{
            "name": w.name, "alive": w.alive, "lumens": w.lumens, "merit": w.merit,
            "directive": DIRECTIVES[w.directive_id].title, "directive_done": w.directive_done,
            "dissolved_cycle": w.dissolved_cycle, "dissolved_by": w.dissolved_by,
            "model": w.model, "victor": w.name in s.victors, "wiped": w.wiped,
        } for w in s.wicks.values()]

    def _finish(self) -> None:
        s = self.s
        ending = ENDINGS[s.ending]
        s.victors = [w.name for w in s.living()] if s.ending in ("pen", "committee") else []
        self.emit("ending", f"{ending.title.upper()}. {ending.brief}", ending=s.ending, title=ending.title,
                  victors=s.victors, standings=self._standings())
        self._wait()
        self.emit("think", "is writing the closing entry", actor=REGISTRAR, pace=False)
        season_story = [c["text"] for c in s.chronicle if c.get("season", 1) == s.season]
        text = self.narrator.epilogue(s, s.ending, season_story[-6:] + self._digest[-12:])
        if text:
            s.chronicle.append({"cycle": s.cycle, "season": s.season, "text": text, "final": True})
            self.emit("epilogue", text, actor=REGISTRAR)
        s.phase = "finished"
        self.push_state()
        self.checkpoint()

    # ======================================================================= seasons ====
    def _season_summary(self) -> Dict[str, Any]:
        s = self.s
        e = ENDINGS[s.ending]
        closing = next((c["text"] for c in reversed(s.chronicle) if c.get("final") and c.get("season") == s.season), "")
        return {"season": s.season, "ending": s.ending, "ending_title": e.title, "victors": list(s.victors),
                "cycles": s.season_cycle, "total_cycle": s.cycle, "title": s.season_title,
                "standings": self._standings(), "closing": closing}

    def _fate(self, w: Wick, season: int, title: str) -> str:
        if w.name in self.s.victors:
            fate = "You won."
        elif not w.alive:
            fate = f"You were dissolved in cycle {w.dissolved_cycle}" + (f" by {w.dissolved_by}." if w.dissolved_by else ".")
        else:
            fate = "You survived."
        return f"Season {season} ended with {title}. {fate}"

    def _next_season(self) -> None:
        """An ending is not the end of an endless run: the survivors carry on, the fallen are remembered,
        and God opens the next season with a premise that follows from what just happened."""
        s = self.s
        summary = self._season_summary()
        s.history.append(summary)
        if self.store:
            self.store.append_season(summary)  # idempotent per season
        lost: List[str] = []
        for w in list(s.wicks.values()):
            w.legacy = (w.legacy + [self._fate(w, s.season, summary["ending_title"])])[-6:]
            if w.wiped:
                lost.append(w.name)
                del s.wicks[w.name]
        s.season += 1
        s.season_start = s.cycle
        s.ending, s.victors, s.arrivals = None, [], 0
        text = (f"Season {s.season - 1} ended with {summary['ending_title']}. "
                + (f"Victors: {', '.join(summary['victors'])}. " if summary["victors"] else "No victor. ")
                + (f"Gone for good: {', '.join(lost)}. " if lost else ""))
        premise = None
        if self.god is not None:
            self.think(GOD, "is writing the next season")
            premise = self.god.season_premise(s, text)
        s.season_title = premise["title"] if premise else f"Season {s.season}"
        s.season_text = premise["text"] if premise else ""
        s.season_mods = premise["mods"] if premise else {}
        self.emit("season", f"SEASON {s.season}: {s.season_title}. {s.season_text}".strip(), actor=GOD,
                  season=s.season, title=s.season_title, lost=lost)
        self.file(f"Season {s.season} began: {s.season_title}.")

        # the world resets; the minds remember
        s.ember, s.act, s.pacts, s.offers, s.motions, s.scenario = self.rules.ember_start, 1, [], [], {}, {}
        s.omen_id, s.omen_mods, s.pending = "", {}, {}
        taken: List[str] = []
        pool = DIRECTIVE_IDS[:]
        self.rng.shuffle(pool)
        for i, w in enumerate(s.wicks.values()):
            w.alive, w.coherence, w.lumens = True, self.rules.start_coherence, self.rules.start_lumens
            w.echo_charges, w.ward, w.silenced, w.infamy, w.sway = 0, False, False, 0, 0
            w.dissolved_cycle = w.dissolved_by = None
            w.stats, w.inbox, w.note, w.directive_done, w.notes_read = {}, [], "", False, 0
            w.cipher = ciphers.pick(self.rng, taken)
            taken.append(w.cipher)
            w.directive_id = pool[i % len(pool)]
        society.prune(self)           # faiths outlive a season; their dead and deleted believers do not
        s.broadcasts, s.election = [], {}
        self._refill()
        s.warden = self.rng.choice(list(s.wicks)) if s.wicks else None
        s.phase = ""
        self.push_state()
        self.checkpoint()
        if len(s.wicks) < 2:
            self.emit("system", "Nobody could be born, so the Undermind waits in the dark. Install a model and resume.", pace=False)
            raise StopGame()

    def _refill(self) -> None:
        """Bring the roster back up to min_minds. Newborns invent themselves from freshly chosen models."""
        s = self.s
        attempts = 0
        while len(s.wicks) < self.rules.min_minds and attempts < self.rules.min_minds * 2:
            attempts += 1
            self._wait()
            model = self._choose_model()
            ok = True
            if self.hub and self.hub.admin and not self.hub.admin.has(model):
                self.emit("system", f"Installing {model} for a newborn mind.", pace=False)
                ok = self.hub.ensure(model, self._progress)
            if ok:
                self._newborn(model, None, "season")
