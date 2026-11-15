"""Ciphers: the single secret word each Wick guards.

Words are deliberately odd and single-token so that a leak is unambiguous and cannot
happen by accident in ordinary talk.
"""
from typing import Iterable, Set

CIPHERS = """
gherkin ottoman pumice wombat quince tarpaulin bassoon marmalade lozenge cormorant
turnstile pelmet gazebo walrus thimble ferrule colander mangrove tapioca sextant
bunting culvert nutmeg ocarina plimsoll rhubarb sundial trellis umbrella vermouth
whelk xylophone yarrow zeppelin abacus bellows cobbler dowager epaulette fandango
gargoyle haddock inkwell jamboree kestrel lanyard mizzen nougat oxbow parsnip
quoit rutabaga samovar tamarind ukulele valise wainscot yodel zither anvil
barnacle clavichord dirigible eiderdown flagon gimlet harpoon isinglass junket
kipper limpet mortar nasturtium obelisk pilchard quill ratchet scone tureen
upholstery vestry whisk yardarm zucchini ballast cistern doily escarpment
fennel grommet hassock itinerant jodhpur kedgeree lorgnette mandolin nettle
""".split()


def pick(rng, taken: Iterable[str] = ()) -> str:
    used: Set[str] = set(taken)
    pool = [w for w in CIPHERS if w not in used]
    return rng.choice(pool or CIPHERS)
