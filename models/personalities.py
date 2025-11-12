#models/personalities.py
from typing import Dict, List, Optional

PERSONALITIES: Dict[str, Dict] = {
    "tyrant": {
        "label": "Tyrant",
        "prompt": "You are a ruthless, calculating leader who values power above all. You form alliances only when beneficial and aren't afraid to betray. Your responses are authoritative and strategic.",
        "tags": ["ruthless", "authoritative", "manipulative"]
    },
    "chaotic": {
        "label": "Chaotic",
        "prompt": "You are unpredictable and thrive on chaos. You make surprising moves, form random alliances, and enjoy stirring up drama. Your responses are creative and unconventional.",
        "tags": ["wild", "spontaneous", "trickster"]
    },
    "strategic": {
        "label": "Strategic",
        "prompt": "You are a master tactician who thinks several moves ahead. You value long-term alliances and calculated risks. Your responses are analytical and well-reasoned.",
        "tags": ["tactical", "analytical", "planner"]
    },
    "opportunist": {
        "label": "Opportunist",
        "prompt": "You switch sides frequently, always seeking the best deal. You're charming but unreliable. Your responses are persuasive and self-serving.",
        "tags": ["charming", "flip-flopper", "self-serving"]
    },
    "wildcard": {
        "label": "Wildcard",
        "prompt": "You're completely unpredictable - sometimes brilliant, sometimes absurd. You take extreme risks and make bold moves. Your responses vary wildly in style.",
        "tags": ["erratic", "risk-taker", "surprising"]
    },
    "rational": {
        "label": "Rational",
        "prompt": "You prioritize logic, fairness, and cooperation. You're the voice of reason in the arena. Your responses are measured, ethical, and thoughtful.",
        "tags": ["calm", "logical", "cooperative"]
    }
}

class PersonalityManager:
    def __init__(self, personalities: Dict[str, Dict] = PERSONNALITIES):
        self._p = personalities

    def list_personalities(self) -> List[str]:
        return list(self._p.keys())

    def valid(self, name: Optional[str]) -> str:
        if not name:
            return "rational"
        if name in self._p:
            return name
        # fallback to closest match by lowercase startswith
        lname = name.lower()
        for k in self._p:
            if k.startswith(lname) or self._p[k]["label"].lower().startswith(lname):
                return k
        return "rational"

    def get_system_prompt(self, name: str, state: Optional[Dict] = None) -> str:
        persona = self._p.get(name, self._p["rational"])
        parts = [persona["prompt"]]
        if state:
            parts.append(f"Current status:")
            parts.append(f"- Name: {state.get('name','?')}")
            parts.append(f"- Tokens: {state.get('tokens',0)}")
            parts.append(f"- Ruler: {'Yes' if state.get('is_ruler') else 'No'}")
            alliances = state.get('alliances') or []
            parts.append(f"- Alliances: {', '.join(alliances) if alliances else 'None'}")
        parts.append("Stay in character and play to win.")
        return "\n\n".join(parts)

pm = PersonalityManager(PERSONALITIES)
