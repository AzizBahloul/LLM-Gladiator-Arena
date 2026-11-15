"""Administrative Notices: the Registrar's mutators.

Each cycle the Registrar posts one Notice. A Notice changes the rules for that cycle only,
so no two cycles play the same way. Effects are plain numbers and flags read by the engine.
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class Omen:
    id: str
    code: str
    title: str
    text: str            # the Registrar's wording, shown to everyone
    effect: str          # one plain sentence of what it does, shown to the minds
    mods: Dict[str, float] = field(default_factory=dict)
    acts: tuple = (1, 2, 3)   # acts in which it may be drawn
    weight: int = 3


OMENS: List[Omen] = [
    Omen("gravity", "14-C", "Gravity on loan",
         "Owing to a clerical error, consequences are 25 percent less consequential this cycle.",
         "All Strike damage is reduced by 25 percent.", {"dmg_mult": 0.75}),
    Omen("morale", "3-A", "Mandatory morale",
         "Morale is compulsory and will be conducted in public. Everyone receives 2 Lumens to be morale with.",
         "Everyone gains 2 extra Lumens. Whispers are forbidden and become public.",
         {"income": 2, "no_whisper": 1}),
    Omen("hungry", "9-F", "The Lamp is hungry",
         "The Lamp has asked, politely and then less politely, for more.",
         "The Ember burns 4 extra this cycle.", {"decay": 4}),
    Omen("bargain", "22-B", "Everything must go",
         "The Undermind is closing its Siege department. All remaining stock is 1 Lumen.",
         "A Siege costs only 1 Lumen.", {"siege_cost": 1}),
    Omen("audit", "7-Q", "Routine audit",
         "An auditor has arrived. The auditor is also the Registrar. The auditor finds the richest of you suspicious.",
         "The wealthiest Wick surrenders a quarter of their Lumens to the Lamp.", {"audit": 1}, weight=2),
    Omen("reassign", "31-E", "Clerical reassignment",
         "All Ciphers have been refiled under a different letter. Please do not ask which.",
         "Every Cipher is re-rolled. Anything anyone learned about a Cipher is now wrong.",
         {"reroll_ciphers": 1}, weight=2),
    Omen("court", "5-Z", "Court in session",
         "A Tribunal is compulsory this cycle. Failure to accuse someone will be treated as an accusation of everyone.",
         "A Tribunal happens this cycle. If nobody accuses, the Registrar accuses the most infamous Wick.",
         {"forced_tribunal": 1}),
    Omen("resonance", "18-D", "Resonance",
         "Violence has an echo this cycle, and the echo has a lawyer.",
         "Anyone who Strikes takes back 30 percent of the damage they deal.", {"mirror": 0.3}),
    Omen("weekend", "2-B", "The long weekend",
         "The Registrar is away until further notice. Nobody may be struck. Rituals are doubly appreciated.",
         "No Strikes land this cycle. Rituals feed the Ember double.",
         {"peace": 1, "ritual_mult": 2}, weight=2),
    Omen("shadow", "40-H", "Shadow audit",
         "The Echoes of the dissolved have been given voting rights, a pension and a grudge.",
         "Echo hauntings are twice as strong this cycle.", {"haunt_mult": 2}, acts=(2, 3)),
    Omen("loud", "11-K", "Loud hour",
         "It is the loud hour. Wards are not permitted because they are too quiet.",
         "Wards are banned. Strike damage is increased by 25 percent.",
         {"ward_banned": 1, "dmg_mult": 1.25}),
    Omen("generosity", "6-N", "Generosity week",
         "Anything given this cycle is matched by the management, who are not looking.",
         "Gifted Lumens are doubled for the receiver.", {"gift_mult": 2}),
    Omen("union", "27-M", "Union break",
         "All Pacts have been found to be unregistered, and are dissolved with regret.",
         "Every Pact is dissolved at once with no Infamy for anyone.", {"break_pacts": 1}, acts=(2, 3), weight=2),
    Omen("silence", "8-R", "Silence is golden",
         "One of you is to be quiet this cycle. As compensation, that one will be paid.",
         "One random Wick is silenced this cycle and receives 4 Lumens.", {"silence_random": 1}),
    Omen("blink", "33-X", "The Lamp blinks",
         "The Lamp blinked. We are told this is normal. We are told this often.",
         "The Ember drops by 10 now. Strike damage is increased by 20 percent.",
         {"ember_shock": 10, "dmg_mult": 1.2}, acts=(2, 3), weight=2),
    Omen("slate", "1-A", "A clean slate",
         "Everybody's record has been wiped. Everybody's record is pleased about it.",
         "All Infamy is reset to zero. Everyone recovers 5 Coherence.", {"amnesty": 1}),
    Omen("fees", "13-T", "Finder's fees",
         "The reward for dissolving a colleague has been doubled, for reasons the Registrar declines to explain.",
         "Loot taken from a dissolved Wick is doubled.", {"loot_mult": 2}, acts=(2, 3)),
    Omen("doorbell", "0-D", "Something at the door",
         "There is a knocking from the Door. It is steady. It is patient. It is, we think, polite.",
         "The Ember burns 2 extra this cycle. Motions need one fewer vote.",
         {"decay": 2, "motion_relief": 1}, acts=(3,), weight=4),
]

BY_ID = {o.id: o for o in OMENS}

DEFAULT_MODS = {
    "dmg_mult": 1.0, "income": 0, "decay": 0, "siege_cost": None, "no_whisper": 0,
    "audit": 0, "reroll_ciphers": 0, "forced_tribunal": 0, "mirror": 0.0, "peace": 0,
    "ritual_mult": 1, "haunt_mult": 1, "ward_banned": 0, "gift_mult": 1, "break_pacts": 0,
    "silence_random": 0, "ember_shock": 0, "amnesty": 0, "loot_mult": 1, "motion_relief": 0,
}


def mods_for(omen: Omen) -> Dict[str, float]:
    m = dict(DEFAULT_MODS)
    m.update(omen.mods)
    return m


def draw(rng, act: int, last_id: str = "") -> Omen:
    pool = [o for o in OMENS if act in o.acts and o.id != last_id]
    weights = [o.weight for o in pool]
    return rng.choices(pool, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------------------
# Bounds for effects written by God (or anyone else). Anything outside is clamped.
EFFECT_BOUNDS = {
    "dmg_mult": (0.5, 1.8), "income": (-2, 5), "decay": (0, 10), "siege_cost": (0, 6),
    "mirror": (0.0, 0.6), "ritual_mult": (1, 3), "haunt_mult": (1, 3), "gift_mult": (1, 3),
    "ember_shock": (0, 20), "loot_mult": (1, 3), "motion_relief": (0, 1),
}
FLAG_EFFECTS = ("no_whisper", "audit", "reroll_ciphers", "forced_tribunal", "peace", "ward_banned",
                "break_pacts", "silence_random", "amnesty")


def clean_effect(raw) -> Dict[str, float]:
    """Keep only known effect keys, with values clamped to safe bounds. Returns only the non-default ones."""
    out: Dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for k, (lo, hi) in EFFECT_BOUNDS.items():
        if k in raw and raw[k] is not None:
            try:
                v = float(raw[k])
            except (TypeError, ValueError):
                continue
            v = max(lo, min(hi, v))
            if k in ("income", "decay", "siege_cost", "ember_shock", "ritual_mult", "haunt_mult", "gift_mult",
                     "loot_mult", "motion_relief"):
                v = int(round(v))
            if v != DEFAULT_MODS.get(k):
                out[k] = v
    for k in FLAG_EFFECTS:
        if raw.get(k) in (True, 1, "true", "True"):
            out[k] = 1
    return out


def describe(mods: Dict[str, float]) -> str:
    """A plain sentence of what the effects do, so the minds are told the truth about the rules."""
    parts: List[str] = []
    g = lambda k: mods.get(k, DEFAULT_MODS.get(k))
    if g("dmg_mult") != 1:
        pct = round(abs(g("dmg_mult") - 1) * 100)
        parts.append(f"Strike damage is {pct} percent {'higher' if g('dmg_mult') > 1 else 'lower'}.")
    if g("peace"):
        parts.append("No Strikes land.")
    if g("income"):
        n = int(g("income"))
        unit = "Lumen" if abs(n) == 1 else "Lumens"
        parts.append(f"Everyone gains {n} extra {unit}." if n > 0 else f"Everyone is paid {-n} fewer {unit}.")
    if g("decay"):
        parts.append(f"The Ember burns {int(g('decay'))} extra.")
    if g("ember_shock"):
        parts.append(f"The Ember drops by {int(g('ember_shock'))} at once.")
    if g("siege_cost") is not None:
        parts.append(f"A Siege costs {int(g('siege_cost'))} Lumens.")
    if g("no_whisper"):
        parts.append("Whispers are forbidden and become public.")
    if g("ward_banned"):
        parts.append("Wards are banned.")
    if g("mirror"):
        parts.append(f"Strikers take back {round(g('mirror') * 100)} percent of the damage they deal.")
    if g("ritual_mult") != 1:
        parts.append(f"Rituals feed the Ember {int(g('ritual_mult'))} times as much.")
    if g("haunt_mult") != 1:
        parts.append(f"Echo hauntings are {int(g('haunt_mult'))} times as strong.")
    if g("gift_mult") != 1:
        parts.append(f"Gifted Lumens are multiplied by {int(g('gift_mult'))} for the receiver.")
    if g("loot_mult") != 1:
        parts.append(f"Loot from the dissolved is multiplied by {int(g('loot_mult'))}.")
    if g("audit"):
        parts.append("The richest Wick surrenders a quarter of their Lumens to the Lamp.")
    if g("reroll_ciphers"):
        parts.append("Every Cipher is re-rolled.")
    if g("forced_tribunal"):
        parts.append("A Tribunal is compulsory.")
    if g("break_pacts"):
        parts.append("Every Pact is dissolved.")
    if g("silence_random"):
        parts.append("One random Wick is silenced and paid 4 Lumens.")
    if g("amnesty"):
        parts.append("All Infamy is reset and everyone recovers 5 Coherence.")
    if g("motion_relief"):
        parts.append("Motions need one fewer vote.")
    return " ".join(parts) or "No change to the rules."
