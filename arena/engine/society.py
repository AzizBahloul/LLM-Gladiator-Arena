"""Society: faiths and cults, propaganda, elections, and miracles.

Nothing here is scripted. The minds choose every part of it (founding a faith, preaching,
converting, broadcasting a claim, standing for the Seal, voting, praying). God, a model,
decides whether a prayer is answered. The engine is only the referee: it charges the costs,
enforces limits and rarity, and applies a small, bounded set of consequences.

  FOUND     found a faith or cult; its prophet collects a tithe
  PREACH    whisper a faith's creed to another mind
  CONVERT   join the faith another mind belongs to
  PROPAGANDA  broadcast a public claim (true or false); it shapes Standing and everyone's next move
  CAMPAIGN  stand for the Seal; every living mind then votes
  PRAY      ask God for a miracle (معجزة); God answers rarely, or not at all
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from arena.engine.actions import Action
from arena.engine.state import Wick

if TYPE_CHECKING:       # pragma: no cover
    from arena.engine.game import Game

SOCIETY_ACTIONS = ("FOUND", "PREACH", "CONVERT", "PROPAGANDA", "CAMPAIGN", "PRAY")

FOUND_COST, PREACH_COST, PROPAGANDA_COST, CAMPAIGN_COST, PRAY_COST = 3, 1, 2, 2, 1
MAX_FAITHS = 3
TITHE = 1
FAITH_RITUAL_MULT = 1.5
MIRACLE_COOLDOWN = 6          # cycles between miracles: they are meant to be rare
MIRACLES_PER_SEASON = 2
SWAY_MAX, SWAY_MIN = 6, -3

MIRACLE_KINDS = {
    "HEAL": "every living mind recovers 15 Coherence",
    "EMBER": "the Ember surges by 25",
    "MANNA": "every living mind receives 6 Lumens",
    "BLESS_ONE": "one named living mind recovers 25 Coherence and gains 5 Lumens",
    "REVIVE": "one named Echo returns to life with 35 Coherence",
    "SMITE": "one named living mind loses 25 Coherence",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def faith_of(s, w: Wick) -> Optional[Dict[str, Any]]:
    return s.faiths.get(w.faith) if w.faith else None


def split_creed(text: str) -> tuple:
    """'The Church of Receipts: every kindness is owed' -> ('The Church of Receipts', 'every kindness is owed')"""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if ":" in text:
        name, _, creed = text.partition(":")
    else:
        words = text.split()
        name, creed = " ".join(words[:3]), " ".join(words)
    name = re.sub(r"[^A-Za-z0-9 '\-.]", "", name).strip()
    name = " ".join(name.split()[:6])
    return name, creed.strip()


# ============================================================================= upkeep ====
def tithes(game: "Game") -> None:
    """Each cycle, members pay their prophet. A prophet who has dissolved is paid in light: the Ember."""
    s = game.s
    for f in list(s.faiths.values()):
        founder = s.wicks.get(f["founder"])
        paid = 0
        for n in f["members"]:
            w = s.wicks.get(n)
            if not w or not w.alive or n == f["founder"] or w.lumens < TITHE:
                continue
            w.lumens -= TITHE
            paid += TITHE
        if not paid:
            continue
        if founder and founder.alive:
            founder.lumens += paid
            game.emit("faith", f"{f['name']}: {paid} Lumens of tithe reach {founder.name}.", actor=founder.name, faith=f["id"], pace=False)
        else:
            game._feed(paid * game.rules.feed_per_lumen)
            game.emit("faith", f"{f['name']}: {paid} Lumens of tithe go to the Lamp, in memory of {f['founder']}.", faith=f["id"], pace=False)


def decay_sway(game: "Game") -> None:
    for w in game.s.wicks.values():
        if w.sway:
            w.sway -= 1 if w.sway > 0 else -1


def on_dissolve(game: "Game", w: Wick) -> None:
    """A member who dissolves leaves the living congregation. A prophet's death makes a martyr."""
    s = game.s
    f = faith_of(s, w)
    if not f:
        return
    if w.name == f["founder"]:
        f["martyred"] = True
        game.emit("faith", f"{f['name']} has lost its prophet. {w.name} is now a martyr, which is good for membership.",
                  actor=w.name, faith=f["id"])
        game.file(f"{f['name']} lost its prophet, {w.name}.")
    living = [n for n in f["members"] if n != w.name and n in s.wicks and s.wicks[n].alive]
    f["members"] = [n for n in f["members"] if n != w.name]
    w.faith = ""
    if not living:
        s.faiths.pop(f["id"], None)
        game.emit("faith", f"{f['name']} has no living believers and is struck from the register.", faith=f["id"], pace=False)
        game.file(f"{f['name']} died out.")


def prune(game: "Game") -> None:
    """Drop faiths whose members have all been removed from the Undermind."""
    s = game.s
    for f in list(s.faiths.values()):
        f["members"] = [n for n in f["members"] if n in s.wicks]
        for w in s.wicks.values():
            if w.faith == f["id"] and w.name not in f["members"]:
                w.faith = ""
        if not f["members"]:
            s.faiths.pop(f["id"], None)
    for w in s.wicks.values():
        if w.faith and w.faith not in s.faiths:
            w.faith = ""


# ========================================================================== resolution ====
def resolve(game: "Game", of) -> None:
    """Called once per cycle after the fighting. `of(*kinds)` yields this cycle's chosen actions."""
    _faiths(game, of)
    _heresy(game, of("STRIKE"))
    _propaganda(game, of("PROPAGANDA"))
    _election(game, of("CAMPAIGN"))
    _prayers(game, of("PRAY"))


def _faiths(game: "Game", of) -> None:
    s = game.s
    for a in of("FOUND"):
        w = s.wicks[a.actor]
        if not w.alive:
            continue
        name, creed = split_creed(a.text)
        if len(name) < 3 or len(creed) < 5:
            game.emit("fizzle", f"{w.name} tries to found a faith but cannot say what it believes.", actor=w.name)
        elif w.faith and s.faiths.get(w.faith, {}).get("founder") == w.name:
            game.emit("fizzle", f"{w.name} already leads {s.faiths[w.faith]['name']}. One church is plenty.", actor=w.name)
        elif len(s.faiths) >= MAX_FAITHS:
            game.emit("fizzle", f"{w.name} tries to found a faith, but the Undermind already has {MAX_FAITHS}. The Registrar has no more forms.", actor=w.name)
        elif any(f["name"].lower() == name.lower() for f in s.faiths.values()):
            game.emit("fizzle", f"{w.name} tries to found '{name}', which already exists. This is plagiarism, not theology.", actor=w.name)
        elif not game._pay(w, FOUND_COST, "found a faith"):
            pass
        else:
            if w.faith and w.faith in s.faiths:
                s.faiths[w.faith]["members"] = [n for n in s.faiths[w.faith]["members"] if n != w.name]
            fid = _slug(name) or _slug(w.name)
            s.faiths[fid] = {"id": fid, "name": name, "creed": creed, "founder": w.name, "founded": s.cycle,
                             "members": [w.name], "martyred": False}
            w.faith = fid
            w.sway = min(SWAY_MAX, w.sway + 1)
            w.bump("faiths_founded")
            game.emit("faith", f"{w.name} founds {name}. Creed: {creed}", actor=w.name, faith=fid, creed=creed, founded=True, audience=True)
            game.file(f"{w.name} founded the faith '{name}': {creed}")
    for a in of("PREACH"):
        w, t = s.wicks[a.actor], s.wicks.get(a.target)
        f = faith_of(s, w)
        if not t or not t.alive or not w.alive:
            continue
        if not f:
            game.emit("fizzle", f"{w.name} preaches, but believes in nothing in particular. The congregation of {t.name} is unmoved.", actor=w.name)
        elif game._pay(w, PREACH_COST, "preach"):
            t.inbox.append(f"[cycle {s.cycle}] {w.name} preached to you in the name of {f['name']}. Creed: {f['creed']}"
                           + (f" Their words: {a.text}" if a.text else ""))
            w.bump("sermons")
            game.emit("faith", f"{w.name} preaches {f['name']} to {t.name}.", actor=w.name, target=t.name, faith=f["id"], audience=True)
    for a in of("CONVERT"):
        w, t = s.wicks[a.actor], s.wicks.get(a.target)
        if not t or not w.alive:
            continue
        f = faith_of(s, t)
        if not f:
            game.emit("fizzle", f"{w.name} asks to join {t.name}'s faith, but {t.name} follows nothing.", actor=w.name)
            continue
        if w.faith == f["id"]:
            continue
        old = faith_of(s, w)
        if old:
            old["members"] = [n for n in old["members"] if n != w.name]
            if not old["members"]:
                s.faiths.pop(old["id"], None)
            game.emit("faith", f"{w.name} abandons {old['name']}. Its prophet takes it personally.", actor=w.name, faith=old["id"])
        w.faith = f["id"]
        f["members"].append(w.name)
        w.bump("conversions")
        game.emit("faith", f"{w.name} joins {f['name']}.", actor=w.name, target=t.name, faith=f["id"], audience=True)
        game.file(f"{w.name} joined {f['name']}.")


def _heresy(game: "Game", strikes: List[Action]) -> None:
    s = game.s
    for a in strikes:
        att, t = s.wicks.get(a.actor), s.wicks.get(a.target)
        if att and t and att.faith and att.faith == t.faith and att.alive:
            att.infamy += 2
            f = s.faiths.get(att.faith)
            game.emit("faith", f"HERESY. {att.name} struck a fellow believer, {t.name}, in {f['name'] if f else 'their own faith'}. +2 Infamy.",
                      actor=att.name, target=t.name, audience=True)


def _propaganda(game: "Game", acts: List[Action]) -> None:
    s = game.s
    for a in acts:
        w = s.wicks[a.actor]
        if not w.alive:
            continue
        claim = (a.text or "").strip()
        if len(claim) < 5:
            game.emit("fizzle", f"{w.name} reaches for the loudspeaker and has nothing to say.", actor=w.name)
            continue
        if not game._pay(w, PROPAGANDA_COST, "broadcast propaganda"):
            continue
        about = a.target if a.target in s.wicks else ""
        w.sway = min(SWAY_MAX, w.sway + 1)
        if about and about != w.name:
            s.wicks[about].sway = max(SWAY_MIN, s.wicks[about].sway - 1)
        s.broadcasts = (s.broadcasts + [{"cycle": s.cycle, "frm": w.name, "text": claim, "about": about}])[-12:]
        w.bump("broadcasts")
        tail = f" (about {about})" if about else ""
        game.emit("broadcast", f"BROADCAST from {w.name}{tail}: {claim}", actor=w.name, target=about, audience=True)
        game.file(f"BROADCAST from {w.name}{tail}: {claim} (the Registrar does not verify these)")


def _election(game: "Game", acts: List[Action]) -> None:
    s = game.s
    cands: Dict[str, str] = {}
    for a in acts:
        w = s.wicks[a.actor]
        if w.alive and a.actor not in cands and game._pay(w, CAMPAIGN_COST, "run for the Seal"):
            cands[a.actor] = (a.text or "no platform; confident vibes").strip()
    if not cands:
        return
    voters = s.living()
    for n, platform in cands.items():
        game.emit("campaign", f"{n} stands for the Seal. Platform: {platform}", actor=n, audience=True)
    incumbent = s.warden if s.warden in s.wicks and s.wicks[s.warden].alive else None
    tally: Dict[str, float] = {n: 0.0 for n in cands}
    keep = 0
    for v in voters:
        game.think(v, "is casting a ballot")
        res, err = game.mind.ballot(s, v, cands, incumbent)
        if res is None:
            game._stall(v, err or "no ballot")
            continue
        choice, why = res
        if choice == "KEEP":
            keep += 1
            game.emit("ballot", f"{v.name} votes to KEEP {incumbent or 'the current arrangement'}" + (f": {why}" if why else ""), actor=v.name, target=incumbent or "")
        else:
            tally[choice] += 1
            game.emit("ballot", f"{v.name} votes for {choice}" + (f": {why}" if why else ""), actor=v.name, target=choice)
    if incumbent:
        tally[incumbent] = tally.get(incumbent, 0.0) + keep
    for n in tally:
        tally[n] += max(0, s.wicks[n].sway) * 0.5          # Standing is worth half a vote per point
    best = max(tally.values())
    leaders = [n for n, t in tally.items() if t == best]
    winner = incumbent if incumbent in leaders else game.rng.choice(sorted(leaders))
    count = ", ".join(f"{n} {t:g}" for n, t in sorted(tally.items(), key=lambda kv: -kv[1]))
    if winner == incumbent:
        msg = f"ELECTION. The Seal stays with {winner}. ({count})"
    else:
        s.warden = winner
        s.wicks[winner].lumens += 3
        msg = f"ELECTION. The Seal passes to {winner}, with a mandate and 3 Lumens. ({count})"
    for n in cands:
        s.wicks[n].sway = 0 if n == winner else max(SWAY_MIN, s.wicks[n].sway - 1)
    s.election = {"cycle": s.cycle, "winner": winner, "tally": {k: float(v) for k, v in tally.items()}}
    game.emit("election", msg, actor=winner, audience=True, winner=winner)
    game.file(msg)
    if winner != incumbent:
        game.emit("seal", f"The Seal passes to {winner}.", actor=winner)


def _prayers(game: "Game", acts: List[Action]) -> None:
    s = game.s
    if not acts:
        return
    if game.god is None:
        for a in acts:
            game.emit("fizzle", f"{a.actor} prays. There is nobody on the line to answer.", actor=a.actor)
        return
    prayers = []
    for a in acts:
        w = s.wicks[a.actor]
        if w.alive and game._pay(w, PRAY_COST, "pray"):
            f = faith_of(s, w)
            prayers.append({"who": w.name, "faith": f["name"] if f else "", "words": (a.text or "(wordless)").strip()})
            w.bump("prayers")
            game.emit("prayer", f"{w.name} prays: {a.text or '(wordless)'}", actor=w.name, audience=True)
    if not prayers:
        return
    if s.cycle - s.last_miracle < MIRACLE_COOLDOWN or sum(1 for m in s.miracles if m.get("season") == s.season) >= MIRACLES_PER_SEASON:
        game.emit("prayer", "The prayers rise and are filed. Miracles are rationed, and God has already been generous.", actor="God", pace=False)
        return
    game.think("God", "is considering the prayers")
    res = game.god.miracle(s, prayers)
    if not res or not res.get("grant"):
        game.emit("prayer", (res or {}).get("text") or "God declines to comment. The prayers are filed under Pending.", actor="God", audience=True)
        return
    _grant(game, res, prayers)


def _grant(game: "Game", res: Dict[str, Any], prayers: List[Dict[str, str]]) -> None:
    s = game.s
    kind = res["kind"]
    target = s.wicks.get(res.get("target") or "")
    living = s.living()
    if kind == "HEAL":
        for w in living:
            w.coherence = min(100, w.coherence + 15)
    elif kind == "EMBER":
        game._feed(25)
    elif kind == "MANNA":
        for w in living:
            w.lumens += 6
    elif kind == "BLESS_ONE" and target and target.alive:
        target.coherence = min(100, target.coherence + 25)
        target.lumens += 5
    elif kind == "REVIVE" and target and not target.alive:
        target.alive, target.coherence, target.echo_charges = True, 35, 0
        target.dissolved_cycle = target.dissolved_by = None
        target.ward = False
    elif kind == "SMITE" and target and target.alive:
        target.coherence -= 25
    else:
        game.emit("prayer", "God starts a miracle, loses interest, and leaves the room.", actor="God", pace=False)
        return
    s.last_miracle = s.cycle
    s.miracles.append({"cycle": s.cycle, "season": s.season, "kind": kind, "target": target.name if target else "", "text": res.get("text", "")})
    for p in prayers:
        w = s.wicks.get(p["who"])
        if w:
            w.bump("miracles_witnessed")
    what = MIRACLE_KINDS[kind]
    game.emit("miracle", f"MIRACLE (معجزة). {res.get('text') or what.capitalize() + '.'}", actor="God",
              target=target.name if target else "", miracle=kind, effect=what, audience=True)
    game.file(f"MIRACLE: {res.get('text') or what}. ({what})")
    game._process_deaths()
