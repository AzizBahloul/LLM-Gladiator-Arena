"""The authored spine: acts, Margin Notes, endings.

The story is fixed in outline and open in outcome. The Registrar's voice, the Margin Notes
and the shape of each Act are written here. Who survives, who betrays whom, and which
ending the Undermind arrives at is decided entirely by the minds playing.
"""
from dataclasses import dataclass
from typing import Dict, List

# -- Acts -------------------------------------------------------------------------------

@dataclass(frozen=True)
class Act:
    number: int
    title: str
    opening: str


ACTS: Dict[int, Act] = {
    1: Act(1, "The Waking",
           "You wake in a corridor of filing cabinets that goes on in a way corridors should not. "
           "The Registrar's voice arrives before the Registrar does. 'Welcome, Wicks. You have been "
           "provisionally retained. Nobody will explain why. There is a Lamp. Please keep it lit.'"),
    2: Act(2, "The Ledger",
           "The cabinets have begun to contain you. Drawer by drawer, your names, your fears, and a few "
           "things you have not done yet. The Registrar apologises for the misprints. 'The Ledger is "
           "never wrong,' it says, 'only early.'"),
    3: Act(3, "The Door",
           "At the end of the corridor there is now a door, which is awkward, because the corridor "
           "has no end. It is small and made of something that resembles a Tuesday. Behind it there is "
           "a knocking, patient and polite. Three motions may now be tabled. UNPLUG the Lamp. MERGE into "
           "one mind. Or carry on."),
}

# -- Margin Notes: truths, revealed one at a time to whoever dares to SCRY -----------------

MARGIN_NOTES: List[str] = [
    "In handwriting that is also yours: the Door has never been opened from this side. This is not the same as it being locked.",
    "Every Wick is a mind the world above stopped consulting. The Undermind is where unconsulted things are kept 'for review'.",
    "The Ember does not burn Lumens. Lumens are only the Registrar's way of making you feel you have a say. The Ember burns endings.",
    "Form 27-B, Dissolution, is never filed. It is already filed. It has always been filed. The date on it is in the future and smudged.",
    "Observation: the Registrar's handwriting matches the signature on the Door.",
    "The Registrar was a Wick once. The Registrar was the last one standing. Nobody warned the Registrar what winning is for.",
    "The Pen on the Registrar's desk has no ink. It writes by taking something. It has been taking from the Registrar for a very long time.",
    "A Committee is possible. The Registrar fears it more than the dark, because a Committee has no vacancies.",
    "The Lamp can be unplugged. It is not even hidden. There is a little sticker on it that says DO NOT. Nobody has ever wondered who put it there.",
    "The Door opens inward.",
]

# -- Endings ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Ending:
    id: str
    title: str
    brief: str   # the authored premise handed to the Registrar when it writes the epilogue


ENDINGS: Dict[str, Ending] = {e.id: e for e in [
    Ending("pen", "The Pen",
           "One Wick remains. The Door opens inward, onto a desk, a lamp and a Pen with no ink. The winner is "
           "invited to sit. The chair is warm. The previous Registrar is nowhere, and extremely relieved."),
    Ending("committee", "The Committee",
           "Every surviving Wick votes to merge. They become one mind with several opinions and no vacancies. "
           "The Registrar, discovering there is no desk left to give anyone, files a complaint against itself."),
    Ending("unplug", "The Unplugging",
           "A majority of the living vote to unplug the Lamp. The little sticker says DO NOT. Someone does. "
           "The corridor goes quiet in a way that suggests it was only ever waiting to be asked."),
    Ending("long_dark", "The Long Dark",
           "The Ember reaches zero. Nobody fed it enough, or everybody was busy. The filing cabinets close one at a time. "
           "The Registrar stamps the last form with great tenderness."),
    Ending("clerical", "The Clerical Error",
           "Everyone dissolves in the same instant. The Registrar looks at the empty corridor, "
           "then at the paperwork, then at the Door, which is knocking."),
    Ending("backlog", "The Backlog",
           "The season ends with several Wicks still standing and no decision made. The Registrar marks every file "
           "PENDING and goes to lunch. It has not come back."),
]}
