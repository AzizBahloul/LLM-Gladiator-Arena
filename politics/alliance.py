#politics/alliance.py
"""Alliance and team mechanics."""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from utils.logger import logger

@dataclass
class Alliance:
    """Represents a coalition of agents."""
    id: str
    members: List[str] = field(default_factory=list)
    pooled_tokens: int = 0
    formed_round: int = 0
    active: bool = True
    
    def add_member(self, agent_name: str):
        """Add an agent to the alliance."""
        if agent_name not in self.members:
            self.members.append(agent_name)
            logger.drama(f"{agent_name} joined alliance '{self.id}'")
    
    def remove_member(self, agent_name: str):
        """Remove an agent from the alliance."""
        if agent_name in self.members:
            self.members.remove(agent_name)
            logger.drama(f"{agent_name} left alliance '{self.id}'")
            
            if len(self.members) < 2:
                self.active = False
                logger.drama(f"Alliance '{self.id}' dissolved")
    
    def is_member(self, agent_name: str) -> bool:
        """Check if an agent is in this alliance."""
        return agent_name in self.members
    
    def get_power(self, resource_manager) -> float:
        """Calculate alliance's total power (token percentage)."""
        total_tokens = sum(resource_manager.get_agent_tokens(m) for m in self.members)
        total_circulating = resource_manager.get_total_circulating()
        return total_tokens / total_circulating if total_circulating > 0 else 0


class AllianceManager:
    """Manages all alliances in the arena."""
    
    def __init__(self):
        self.alliances: Dict[str, Alliance] = {}
        self.alliance_counter = 0
    
    def create_alliance(self, founding_members: List[str], round_num: int) -> str:
        """Create a new alliance."""
        self.alliance_counter += 1
        alliance_id = f"alliance_{self.alliance_counter}"
        
        alliance = Alliance(
            id=alliance_id,
            members=founding_members.copy(),
            formed_round=round_num
        )
        
        self.alliances[alliance_id] = alliance
        logger.alliance_formed(founding_members)
        
        return alliance_id
    
    def dissolve_alliance(self, alliance_id: str):
        """Dissolve an alliance."""
        if alliance_id in self.alliances:
            self.alliances[alliance_id].active = False
            logger.drama(f"Alliance {alliance_id} has been dissolved")
    
    def get_agent_alliance(self, agent_name: str) -> Optional[Alliance]:
        """Find which alliance an agent belongs to."""
        for alliance in self.alliances.values():
            if alliance.active and alliance.is_member(agent_name):
                return alliance
        return None
    
    def remove_agent_from_all(self, agent_name: str):
        """Remove an eliminated agent from all alliances."""
        for alliance in self.alliances.values():
            if alliance.active and alliance.is_member(agent_name):
                alliance.remove_member(agent_name)
    
    def get_strongest_alliance(self, resource_manager) -> Optional[Alliance]:
        """Find the most powerful alliance."""
        active = [a for a in self.alliances.values() if a.active]
        if not active:
            return None
        
        return max(active, key=lambda a: a.get_power(resource_manager))
    
    def propose_random_alliances(self, agents: List, resource_manager) -> List[tuple]:
        """Generate random alliance proposals for drama."""
        import random
        
        proposals = []
        available = [a for a in agents if a.is_alive and not self.get_agent_alliance(a.name)]
        
        if len(available) >= 2:
            # Create 1-2 random alliance proposals
            for _ in range(random.randint(1, 2)):
                if len(available) >= 2:
                    proposer = random.choice(available)
                    target = random.choice([a for a in available if a != proposer])
                    proposals.append((proposer, target))
                    available = [a for a in available if a not in [proposer, target]]
        
        return proposals