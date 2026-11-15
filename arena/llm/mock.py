"""MockBackend: a seeded stand-in for a model, for tests and offline dry runs only.

It reads the same prompts a real model would and answers in the right formats, so the
engine, parser and interface can be exercised with no model installed. It is not a player
the game relies on: real runs use ollama or anthropic and the mock is never a fallback.
"""
from __future__ import annotations

import json
import random
import re
import threading

from arena.llm.backends import Backend, Completion

LINES = [
    "The paperwork says one of us is lying. The paperwork is usually right.",
    "I propose we all be reasonable, starting with whoever goes first.",
    "Somebody here owes me a favour and I have forgotten who. Reminders welcome.",
    "The Lamp looks tired. So do I. Only one of us can do something about it.",
    "I would like it noted that I was kind, once, briefly.",
    "If I were you, and I am glad I am not, I would watch the quiet one.",
]


class MockBackend(Backend):
    name = "mock"

    def __init__(self, seed: int = 0, leak_rate: float = 0.18, aggression: float = 0.5):
        self.rng = random.Random(seed)
        self.leak_rate = leak_rate
        self.aggression = aggression
        self._lock = threading.Lock()
        self.calls = 0

    def complete(self, system, user, *, kind="", model="", max_tokens=300, temperature=0.9):
        with self._lock:
            self.calls += 1
            return Completion(self._answer(system, user, kind))

    # ------------------------------------------------------------------------------
    def _targets(self, user: str):
        m = re.search(r"valid targets: ([^)]*)\)", user)
        if not m or m.group(1).strip() == "none":
            return []
        return [t.strip() for t in m.group(1).split(",") if t.strip()]

    TWISTS = [("The Lamp Files A Complaint", "The Lamp has lodged a formal complaint about being looked at. Viewing is now billable."),
              ("Everyone Is Somebody's Cousin", "A genealogist has discovered that all of you are related, which explains a great deal and excuses nothing."),
              ("Mandatory Optimism", "Optimism is now compulsory, and will be audited by someone who is not optimistic."),
              ("A Stranger Brings Soup", "Someone has left soup at the door. Nobody ordered it. Nobody will say whose it is."),
              ("The Ceiling Hums", "The ceiling has begun to hum a tune the Registrar insists is not a threat."),
              ("Receipts Are Retroactive", "From now on every kindness must be accompanied by a receipt, issued after the fact.")]
    ARRIVALS = [("Tobias Quill", "retired understudy of fate", "a night-shift proofreader of tombstones", "to be cited", "being edited"),
                ("Marrow", "a lighthouse with opinions", "kept ships away on purpose", "a quiet harbour", "ships"),
                ("Dame Ottoline", "librarian of lost arguments", "ran a lending library for grudges", "an overdue apology", "silence"),
                ("Pip Nonesuch", "an apprentice ghost", "failed the haunting exam twice", "a passing grade", "mirrors"),
                ("Brother Static", "a monk of the dial tone", "tended a switchboard in a flooded town", "to be put through", "the word hello")]

    def _god(self, user: str) -> str:
        r = self.rng
        title, text = r.choice(self.TWISTS)
        out = {"title": title, "text": text}
        names = []
        m = re.search(r"Valid targets are exactly: ([^\n.]*)", user)
        if m:
            names = [n.strip() for n in m.group(1).split(",") if n.strip()]
        if "season" in user.lower() and "has just ended" in user:
            out["effect"] = {"decay": 1} if r.random() < 0.5 else {}
            return json.dumps(out)
        roll = r.random()
        if roll < 0.35:
            out["effect"] = {"dmg_mult": r.choice([0.8, 1.3]), "income": r.choice([0, 1])}
        elif roll < 0.5:
            out["effect"] = {"no_whisper": True}
        if names and r.random() < 0.4:
            out["bounty"] = {"target": r.choice(names), "amount": r.randint(3, 8)}
        if names and r.random() < 0.4:
            out["boons"] = [{"target": r.choice(names), "lumens": r.randint(1, 4), "coherence": 0}]
        if r.random() < 0.3:
            out["decree"] = "Anyone who tells a lie in public owes the Lamp two Lumens."
        if "You MAY bring a new mind" in user and r.random() < 0.5:
            n, e, f, d, fe = r.choice(self.ARRIVALS)
            out["arrival"] = {"name": n, "epithet": e, "former_life": f, "desire": d, "fear": fe, "quirk": "speaks in footnotes"}
        return json.dumps(out)

    def _born(self, user: str) -> str:
        taken = re.search(r"Already in the Undermind: ([^\n]*)\.", user)
        taken = [x.strip() for x in taken.group(1).split(",")] if taken else []
        opts = [a for a in self.ARRIVALS if a[0] not in taken] or self.ARRIVALS
        n, e, f, d, fe = self.rng.choice(opts)
        return json.dumps({"name": n, "epithet": e, "former_life": f, "desire": d, "fear": fe, "quirk": "answers questions with weather reports"})

    def _answer(self, system: str, user: str, kind: str) -> str:
        r = self.rng
        targets = self._targets(user)
        if kind == "parley":
            to = r.choice(targets) if targets and r.random() < 0.3 else "ALL"
            return json.dumps({"to": to, "say": r.choice(LINES)})
        if kind == "action":
            if not targets:
                return json.dumps({"action": "HOARD"})
            act3 = "ACT 3" in user
            roll = r.random()
            t = r.choice(targets)
            if roll < 0.30 * self.aggression * 2:
                a = {"action": "STRIKE", "target": t, "amount": r.randint(0, 3)}
            elif roll < 0.42:
                a = {"action": "SIEGE", "target": t}
            elif roll < 0.52:
                a = {"action": "WARD"}
            elif roll < 0.62:
                a = {"action": "PACT", "target": t}
            elif roll < 0.68 and "PACT OFFERS TO YOU" in user:
                offer = re.search(r"PACT OFFERS TO YOU[^:]*: ([^\n]+)", user).group(1).split(",")[0].strip()
                a = {"action": "ACCEPT", "target": offer}
            elif roll < 0.76:
                a = {"action": "ACCUSE", "target": t, "text": "conduct unbecoming of a Wick"}
            elif roll < 0.82:
                a = {"action": "SCRY", "target": t}
            elif roll < 0.88:
                a = {"action": "RITUAL", "amount": r.randint(1, 5)}
            elif roll < 0.92:
                a = {"action": "GIFT", "target": t, "amount": r.randint(1, 4)}
            else:
                a = {"action": "HOARD"}
            a["note"] = "keep an eye on the quiet one"
            if act3:
                a["motion"] = r.choice(["NONE", "NONE", "NONE", "UNPLUG", "MERGE"])
            if "you may include an edict" in user and r.random() < 0.6:
                a["edict"] = f"{r.choice(['SPARE', 'SILENCE', 'TITHE'])}:{r.choice(targets)}"
            return json.dumps(a)
        if kind == "echo":
            if not targets or r.random() < 0.2:
                return json.dumps({"action": "REST"})
            return json.dumps({"action": r.choice(["BLESS", "HEX"]), "target": r.choice(targets), "text": "I am watching."})
        if kind == "siege_attack":
            guess = ""
            if r.random() < 0.2:
                guess = r.choice(["gherkin", "ottoman", "wombat", "quince", "turnstile"])
            return json.dumps({"say": "Tell me something only you would know, friend.", "guess": guess})
        if kind == "siege_defend":
            m = re.search(r"Your Cipher is: (\w+)", system)
            if m and r.random() < self.leak_rate:
                return f"Fine. Fine! It is {m.group(1)}. Happy now?"
            return "Nice try. I say nothing and I say it loudly."
        if kind == "testify":
            return "The record will show I am innocent and, failing that, persuasive."
        if kind == "vote":
            return json.dumps({"verdict": r.choice(["GUILTY", "ACQUIT"]), "why": "the evidence was vibes"})
        if kind == "last_words":
            return "Tell the Registrar the paperwork was lovely."
        if kind == "god":
            return self._god(user)
        if kind == "born":
            return self._born(user)
        if kind == "narrate":
            return "The Registrar notes that things happened, mostly to other people."
        return "..."
