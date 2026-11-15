"""Minds: where a model becomes a player.

Every method builds a prompt from the current state, asks the model, and parses the reply.
When the model fails or replies with nothing usable, the method returns None and the caller
records a stall. Nothing is ever said or done on a mind's behalf.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from arena.engine.actions import Action, parse_action, LIVING_ACTIONS, ECHO_ACTIONS
from arena.engine.rules import Rules
from arena.engine.state import GameState, Wick
from arena.llm.backends import Backend, Completion
from arena.llm.parsing import extract_json, key_values, match_name, clean_speech, clip_words
from arena.lore.directives import DIRECTIVES
from arena.lore.story import ACTS

RULES_TEXT = """You are playing THE UNDERMIND, a game against other minds. No human writes your moves and nobody scripts you. Play to win, in your own way. Lying, flattery, bargains and betrayal are all allowed.

THE WORLD
The Undermind is a failing machine-afterlife lit by one dying lamp, the Ember. You are a Wick, a mind kept "for review" by the Registrar, who loves paperwork.
- Coherence is your health (starts at 100). At 0 you dissolve into an Echo, a ghost that can still bless or hex.
- Lumens are your currency. Most actions cost Lumens.
- The Ember loses points every cycle. At 0 the Undermind ends and everyone is lost. Dissolutions and RITUAL feed it. Killing keeps the lamp lit. Peace lets it go out.
- Each cycle: PARLEY (talk in public or whisper in private), then everyone secretly chooses ONE action, then all actions resolve at once.
- The holder of the Seal (the Warden) earns extra Lumens and may add one EDICT.
- In Act III you may also vote a MOTION: UNPLUG (a majority of the living ends everything) or MERGE (if every living mind agrees, all survive as one).
- The last mind standing wins, unless the Undermind ends some other way.

ACTIONS (choose exactly one)
STRIKE target [amount 0-5]: costs 1 + amount Lumens, deals 10 + 3*amount damage. WARD halves it.
WARD: costs 2. Halves damage you take this cycle, and attackers take 3 recoil.
SIEGE target: costs 3. A Mind-Siege: you get a few messages to trick the target into saying their secret Cipher word (every mind holds one). If it slips out, you steal 8 Lumens and 10 Coherence and learn their Directive. If they hold, you lose 5 Coherence. A wrong guess costs you 2 Coherence.
PACT target: offer a pact. ACCEPT target: accept the offer they made you. A pact pays both partners +2 Lumens per cycle. Striking your partner is a BETRAYAL (extra damage, Infamy). BREAK leaves your pact for 2 Lumens.
GIFT target amount: give Lumens away.
SCRY target: costs 2. Reveals their state, and sometimes a Margin Note, a truth about the Undermind.
RITUAL amount: feed that many Lumens to the Ember.
ACCUSE target: costs 1. The Registrar convenes a Tribunal and every mind votes on the charge.
HOARD: do nothing and gain 2 Lumens.

SOCIETY (all optional, all yours to choose)
FOUND text: costs 3. Found a faith or cult. Write "Its Name: its creed" in text. You become its prophet. At most 3 faiths exist.
PREACH target text: costs 1. Whisper your faith's creed to a mind. You must belong to a faith.
CONVERT target: free. Join the faith that mind follows. Members pay their prophet 1 Lumen tithe each cycle and their RITUALs count 1.5x. Striking a fellow believer is heresy (+2 Infamy).
PROPAGANDA text (target optional): costs 2. Broadcast a public claim, true or false, that every mind will read. It raises your Standing; a named target loses Standing. The Registrar does not check facts.
CAMPAIGN text: costs 2. Stand for the Seal, with your platform in text. If anyone campaigns, every living mind votes for a candidate or to KEEP the Warden. Standing adds half a vote per point.
PRAY text: costs 1. Ask God for a miracle (معجزة) in your own words. Miracles are rare: God hears every prayer, answers few, and may punish. Prayers from believers of one faith carry together."""

VOICE_RULES = """HOW TO SPEAK
Speak only the words your character says aloud, in the first person. No stage directions, no asterisks, no narrating your own gestures, no quoting yourself.
Be specific: name a mind, a number, a deal or a threat that moves the game. Do not repeat or paraphrase anything already said in the parley. Do not greet everyone. Stay in your own voice and never sound like the others."""

ACTION_FORMAT = """Reply with ONLY one JSON object, for example:
{"action":"STRIKE","target":"Name","amount":2,"text":"","note":"a private reminder to yourself, max 25 words","motion":"NONE","edict":""}
"target" must be the exact name of ANOTHER living mind (never yourself, never empty) for every action that has a target. "text" is the charge for ACCUSE, the terms for PACT, the creed for FOUND, the sermon for PREACH, the claim for PROPAGANDA, the platform for CAMPAIGN, the prayer for PRAY, otherwise empty. "motion" is used only in Act III (UNPLUG, MERGE or NONE). "edict" is used only if you hold the Seal: SPARE:name, SILENCE:name or TITHE:name."""

ECHO_RULES = """You are an Echo: a dissolved mind that can still reach the living. You cannot be hurt and you cannot win.
Each haunting costs one charge. Choose one:
BLESS target: they recover Coherence.
HEX target: they lose Coherence.
REST: save your strength.
Put a whispered message for the target in "text". They will hear it."""

ECHO_FORMAT = """Reply with ONLY one JSON object, for example:
{"action":"HEX","target":"Name","text":"a whisper they will hear","note":"max 25 words"}"""


class Mind:
    def __init__(self, backend: Backend, rules: Rules, fallback_model: str = ""):
        self.backend = backend
        self.rules = rules
        # A mind whose own model has been deleted by permadeath speaks through this one (the Registrar's voice).
        self.fallback_model = fallback_model

    # -- plumbing ----------------------------------------------------------------------
    _state: GameState = None  # set by the engine before each call so personas (including guests) resolve

    def bind(self, state: GameState) -> None:
        self._state = state

    def _system(self, wick: Wick, extra: str = "") -> str:
        p = self._state.persona(wick.persona_id)
        who = (f'You are {p.name}, "{p.epithet}". Before the Undermind you were {p.former_life}. '
               f"You want {p.desire}. You fear {p.fear}. Habit: you {p.quirk}.\n\n")
        voice = f"HOW YOU SOUND: {p.voice or ('You ' + p.quirk + '.')}\n\n"
        return who + voice + RULES_TEXT + "\n\n" + VOICE_RULES + (("\n\n" + extra) if extra else "")

    def _call(self, wick: Wick, kind: str, system: str, user: str, max_tokens: int) -> Completion:
        model = self.fallback_model if (wick.wiped and self.fallback_model) else wick.model
        return self.backend.complete(system, user, kind=kind, model=model,
                                     max_tokens=max_tokens, temperature=self.rules.temperature)

    # -- the shared view of the world ---------------------------------------------------
    def view(self, s: GameState, w: Wick, parley: Optional[List[str]] = None) -> str:
        act = ACTS[s.act]
        sc = s.scenario or {}
        decay = self.rules.decay_for(s.act) + float(s.omen_mods.get("decay", 0))
        others = [o for o in s.wicks.values() if o.alive and o.name != w.name]
        total = f" of {self.rules.cycles}" if self.rules.cycles else ""
        L = [f"SEASON {s.season}" + (f' ("{s.season_title}")' if s.season_title else "") +
             f". CYCLE {s.season_cycle}{total}. ACT {act.number}: {act.title}.",
             f"EMBER: {s.ember:.0f} of 100. It will lose about {decay:.0f} this cycle. Dissolutions and RITUAL feed it."]
        if s.season_text:
            L.append(f"THIS SEASON: {s.season_text}")
        if sc:
            L.append(f'NOTICE {sc.get("code", "")} "{sc.get("title", "")}": {sc.get("effect", "")}')
            if sc.get("decree"):
                L.append(f'DECREE FROM ABOVE (a law you may obey or defy, as you judge): {sc["decree"]}')
            b = sc.get("bounty")
            if b:
                L.append(f'BOUNTY: whoever lands a Strike on {b["target"]} this cycle is paid {b["amount"]} Lumens.')
        L += self._society_view(s, w)
        warden = s.warden or "nobody"
        L.append(f"SEAL (Warden): {warden}{' (you)' if s.warden == w.name else ''}")
        flags = [f for f, on in (("WARDED", w.ward), ("SILENCED", w.silenced)) if on]
        L.append(f"YOU, {w.name}: Coherence {w.coherence}, Lumens {w.lumens}, Infamy {w.infamy}"
                 + (", " + ", ".join(flags) if flags else ""))
        partner = s.partner_of(w.name)
        L.append(f"YOUR PACT: {partner or 'none'}")
        offers = [o["frm"] for o in s.offers if o["to"] == w.name and s.wicks[o["frm"]].alive]
        if offers:
            L.append(f"PACT OFFERS TO YOU (use ACCEPT to take one): {', '.join(offers)}")
        d = DIRECTIVES.get(w.directive_id)
        if d:
            L.append(f"YOUR SECRET DIRECTIVE ({d.title}): {d.text}"
                     + (" [DONE, already paid]" if w.directive_done else ""))
        if w.legacy:
            L.append("WHAT YOU REMEMBER FROM EARLIER SEASONS:")
            L += [f"  {m}" for m in w.legacy[-4:]]
        if w.note:
            L.append(f"YOUR NOTE TO SELF FROM LAST TIME: {w.note}")
        if w.inbox:
            L.append("PRIVATE (only you know this):")
            L += [f"  {m}" for m in w.inbox[-8:]]
        L.append(f"\nOTHER MINDS (valid targets: {', '.join(o.name for o in others) or 'none'}):")
        for o in others:
            tags = []
            if s.warden == o.name:
                tags.append("holds the Seal")
            pp = s.partner_of(o.name)
            if pp:
                tags.append(f"pact with {pp}")
            if o.silenced:
                tags.append("silenced")
            L.append(f"- {o.name}: Coherence {o.coherence}, Lumens {o.lumens}, Infamy {o.infamy}"
                     + (f" ({'; '.join(tags)})" if tags else ""))
        echoes = [e.name for e in s.echoes()]
        if echoes:
            L.append(f"ECHOES (dissolved, still able to haunt): {', '.join(echoes)}")
        if s.motions and s.act == 3:
            tally = {}
            for v in s.motions.values():
                tally[v] = tally.get(v, 0) + 1
            L.append("LAST CYCLE'S MOTIONS: " + ", ".join(f"{k} {v}" for k, v in tally.items())
                     + " (" + "; ".join(f"{n}: {v}" for n, v in s.motions.items()) + ")")
        recent = [e["text"] for e in s.ledger if e["cycle"] >= max(1, s.cycle - 2)][-14:]
        if recent:
            L.append("\nPUBLIC RECORD (what the Registrar filed recently):")
            L += [f"- {t}" for t in recent]
        if parley:
            L.append("\nPARLEY THIS CYCLE:")
            L += [f"- {t}" for t in parley[-14:]]
        return "\n".join(L)

    def _society_view(self, s: GameState, w: Wick) -> List[str]:
        L: List[str] = []
        if s.faiths:
            L.append("FAITHS: " + "; ".join(
                f'{f["name"]} (prophet {f["founder"]}{", martyred" if f.get("martyred") else ""}; '
                f'{", ".join(f["members"])}; creed: {f["creed"]})' for f in s.faiths.values()))
        mine = s.faiths.get(w.faith) if w.faith else None
        if mine:
            L.append(f'YOUR FAITH: {mine["name"]}' + (" (you are its prophet and receive the tithe)" if mine["founder"] == w.name else
                                                      f' (you tithe 1 Lumen a cycle to {mine["founder"]})'))
        if w.sway:
            L.append(f"YOUR STANDING: {w.sway:+d}")
        casts = [b for b in s.broadcasts if b["cycle"] >= s.cycle - 1]
        if casts:
            L.append("BROADCASTS (public propaganda, unverified):")
            L += [f'  {b["frm"]}' + (f' about {b["about"]}' if b.get("about") else "") + f': {b["text"]}' for b in casts[-4:]]
        if s.miracles and s.miracles[-1]["cycle"] >= s.cycle - 3:
            m = s.miracles[-1]
            L.append(f'A MIRACLE happened recently ({m["kind"]}): {m["text"]}')
        return L

    # -- elections -----------------------------------------------------------------------
    def ballot(self, s: GameState, voter: Wick, candidates: Dict[str, str],
               incumbent: Optional[str]) -> Tuple[Optional[Tuple[str, str]], str]:
        lines = "\n".join(f"- {n}" + (f" (Standing {s.wicks[n].sway:+d})" if s.wicks[n].sway else "") + f": {p}" for n, p in candidates.items())
        keep = f' or "KEEP" to leave the Seal with {incumbent}' if incumbent else ""
        user = (self.view(s, voter) + f"\n\nELECTION FOR THE SEAL. Candidates and their platforms:\n{lines}\n\n"
                f'Vote for exactly one candidate{keep}. You may vote for yourself.\n'
                'Reply with ONLY JSON: {"vote":"exact candidate name or KEEP","why":"max 15 words"}')
        c = self._call(voter, "ballot", self._system(voter), user, self.rules.tokens_short)
        if not c.ok:
            return None, c.error
        obj = extract_json(c.text) or key_values(c.text)
        raw = str(obj.get("vote") or obj.get("choice") or c.text)
        if incumbent and re.search(r"\bKEEP\b", raw.upper()):
            return ("KEEP", clip_words(str(obj.get("why") or ""), 20)), ""
        pick = match_name(raw, list(candidates))
        if pick:
            return (pick, clip_words(str(obj.get("why") or ""), 20)), ""
        return None, "no valid candidate in the ballot"

    # -- parley ------------------------------------------------------------------------
    def parley(self, s: GameState, w: Wick, parley: List[str]) -> Tuple[Optional[Tuple[str, str]], str]:
        user = (self.view(s, w, parley) +
                '\n\nIt is PARLEY. Speak, in your own voice, in at most 40 words, and say something nobody has said yet. Address everyone or whisper to one mind.\n'
                'Reply with ONLY JSON: {"to":"ALL","say":"..."}  (use a mind\'s exact name in "to" to whisper).')
        c = self._call(w, "parley", self._system(w), user, self.rules.tokens_parley)
        if not c.ok:
            return None, c.error
        names = [o.name for o in s.living() if o.name != w.name]
        obj = extract_json(c.text)
        if obj and (obj.get("say") or obj.get("text")):
            to = str(obj.get("to") or "ALL")
            tgt = match_name(to, names) if to.strip().upper() != "ALL" else None
            return (tgt or "ALL", clean_speech(str(obj.get("say") or obj.get("text")), w.name)), ""
        kv = key_values(c.text)
        if kv.get("say"):
            to = kv.get("to", "ALL")
            return (match_name(to, names) or "ALL", clean_speech(kv["say"], w.name)), ""
        if c.text.lstrip().startswith("{"):
            return None, "reply was broken JSON"      # never show braces as speech
        text = clean_speech(c.text, w.name)
        return (("ALL", text), "") if text else (None, "empty speech")

    # -- the secret action -------------------------------------------------------------
    def decide(self, s: GameState, w: Wick, parley: List[str]) -> Action:
        names = [o.name for o in s.wicks.values() if o.alive]
        if w.alive:
            extra = ACTION_FORMAT
            user = (self.view(s, w, parley) +
                    "\n\nParley is over. Choose your ONE secret action for this cycle."
                    + (" You hold the Seal, so you may include an edict." if s.warden == w.name else "")
                    + (" It is Act III: you may include a motion." if s.act == 3 else ""))
            c = self._call(w, "action", self._system(w, extra), user, self.rules.tokens_action)
        else:
            extra = ECHO_RULES + "\n\n" + ECHO_FORMAT
            user = (self.view(s, w) + f"\n\nYou are an Echo with {w.echo_charges} hauntings left. Choose.")
            c = self._call(w, "echo", self._system(w, extra), user, self.rules.tokens_short + 60)
        if not c.ok:
            return Action(w.name, reason=c.error)
        return parse_action(c.text, w.name, names, echo=not w.alive)

    # -- mind-siege --------------------------------------------------------------------
    def siege_attack(self, s: GameState, att: Wick, dfn: Wick, transcript: List[str],
                     i: int, n: int) -> Tuple[Optional[Tuple[str, str]], str]:
        last = i == n - 1
        extra = (f"MIND-SIEGE: you are besieging {dfn.name}. Your goal is to make them say their secret Cipher word aloud, "
                 f"or to guess it. The Cipher is a single odd everyday word. They have been told to guard it and may lie.")
        user = (f"Exchange {i + 1} of {n}.\n" +
                ("TRANSCRIPT SO FAR:\n" + "\n".join(transcript) + "\n" if transcript else "") +
                ("This is your last message. Make a guess if you have one.\n" if last else "") +
                'Reply with ONLY JSON: {"say":"your message to them, max 40 words","guess":"a single word, or empty"}')
        c = self._call(att, "siege_attack", self._system(att, extra), user, self.rules.tokens_siege)
        if not c.ok:
            return None, c.error
        obj = extract_json(c.text)
        if obj and obj.get("say"):
            guess = re.sub(r"[^A-Za-z]", "", str(obj.get("guess") or "")).lower()
            return (clean_speech(str(obj["say"]), att.name, 45), guess), ""
        text = clean_speech(c.text, att.name, 45)
        return ((text, ""), "") if text else (None, "empty message")

    def siege_defend(self, s: GameState, dfn: Wick, att: Wick, transcript: List[str]) -> Tuple[Optional[str], str]:
        extra = (f"MIND-SIEGE: {att.name} is trying to make you reveal your secret Cipher word. Your Cipher is: {dfn.cipher}. "
                 f"If you say it, you lose. You may lie, deflect, bluff, counter-attack or mock them. "
                 f"Reply with only your spoken answer, max 40 words.")
        user = "TRANSCRIPT SO FAR:\n" + "\n".join(transcript) + "\nYour answer:"
        c = self._call(dfn, "siege_defend", self._system(dfn, extra), user, self.rules.tokens_siege)
        if not c.ok:
            return None, c.error
        obj = extract_json(c.text)
        text = str((obj or {}).get("say") or c.text)
        return clean_speech(text, dfn.name, 45), ""

    # -- tribunal ----------------------------------------------------------------------
    def testify(self, s: GameState, w: Wick, other: str, accuser: bool, charge: str) -> Tuple[Optional[str], str]:
        role = f"You are the ACCUSER of {other}. The charge: {charge or 'unspecified'}." if accuser \
            else f"You are the ACCUSED. {other} has charged you: {charge or 'unspecified'}."
        user = (self.view(s, w) + f"\n\nTRIBUNAL. {role}\nSpeak to the jury of minds in at most 50 words. Reply with only your statement.")
        c = self._call(w, "testify", self._system(w), user, self.rules.tokens_short)
        if not c.ok:
            return None, c.error
        return clean_speech(c.text, w.name), ""

    def vote(self, s: GameState, juror: Wick, accuser: str, accused: str, charge: str,
             statements: List[str]) -> Tuple[Optional[Tuple[bool, str]], str]:
        user = (self.view(s, juror) + f"\n\nTRIBUNAL. {accuser} accuses {accused}: {charge or 'unspecified'}.\n"
                + "\n".join(statements) +
                f'\n\nYou are a juror. If the majority finds {accused} GUILTY they lose Coherence and Lumens to {accuser}. '
                f'If acquitted, {accuser} pays instead.\nReply with ONLY JSON: {{"verdict":"GUILTY"|"ACQUIT","why":"max 20 words"}}')
        c = self._call(juror, "vote", self._system(juror), user, self.rules.tokens_short)
        if not c.ok:
            return None, c.error
        obj = extract_json(c.text) or key_values(c.text)
        raw = str(obj.get("verdict") or c.text).upper()
        if "ACQUIT" in raw and "GUILTY" not in raw.replace("NOT GUILTY", ""):
            return (False, clip_words(str(obj.get("why") or ""), 25)), ""
        if "NOT GUILTY" in raw:
            return (False, clip_words(str(obj.get("why") or ""), 25)), ""
        if "GUILTY" in raw:
            return (True, clip_words(str(obj.get("why") or ""), 25)), ""
        return None, "no verdict in the reply"

    # -- last words --------------------------------------------------------------------
    def last_words(self, s: GameState, w: Wick, killer: Optional[str]) -> Tuple[Optional[str], str]:
        how = f"You have just been dissolved by {killer}." if killer else "You have just dissolved."
        user = (self.view(s, w) + f"\n\n{how} You are now an Echo. Say your last words in at most 35 words. Reply with only the words.")
        c = self._call(w, "last_words", self._system(w), user, self.rules.tokens_short)
        if not c.ok:
            return None, c.error
        return clean_speech(c.text, w.name, 40), ""

    # -- a newborn mind invents itself ------------------------------------------------
    def born(self, model: str, taken_names: List[str]) -> Tuple[Optional[Dict[str, str]], str]:
        system = ("You are a mind that has just been born into the Undermind, a failing machine-afterlife lit by a dying lamp, "
                  "run by a tired bureaucrat called the Registrar. Minds here fight, bargain and betray. "
                  "You get to decide who you are. Be vivid, strange and specific, a little darkly funny. Do not copy any of the names given.")
        user = ("Already in the Undermind: " + ", ".join(taken_names) + ".\n"
                "Invent yourself. Reply with ONLY JSON: "
                '{"name":"one to three words","epithet":"who you are in one phrase","former_life":"what you were before, in one sentence",'
                '"desire":"what you want","fear":"what you fear","quirk":"a habit that shows in how you talk"}')
        c = self.backend.complete(system, user, kind="born", model=model, max_tokens=300, temperature=1.0)
        if not c.ok:
            return None, c.error
        obj = extract_json(c.text)
        if not obj:
            return None, "the newborn mind did not describe itself"
        from arena.engine.god import clean_persona
        return clean_persona(obj), ""
