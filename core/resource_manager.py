#core/resource_manager.py

"""Resource and token management."""
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from utils.logger import logger

@dataclass
class ResourcePool:
    """Manages CPU/GPU resources and tokens."""
    total_tokens: int
    gpu_slots: int
    cpu_millicores: int
    
    agent_tokens: Dict[str, int] = field(default_factory=dict)
    gpu_reservations: List[Optional[str]] = field(default_factory=list)
    cpu_allocations: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        self.gpu_reservations = [None] * self.gpu_slots
    
    def initialize_agent(self, agent_name: str, initial_tokens: int):
        """Give an agent their starting tokens."""
        self.agent_tokens[agent_name] = initial_tokens
        total_agents = len(self.agent_tokens)
        if total_agents > 0:
            per_agent = max(1, self.cpu_millicores // total_agents)
            for a in self.agent_tokens:
                self.cpu_allocations[a] = per_agent
    
    def transfer_tokens(self, from_agent: str, to_agent: str, amount: int) -> bool:
        """Transfer tokens between agents."""
        if self.agent_tokens.get(from_agent, 0) < amount:
            return False
        
        self.agent_tokens[from_agent] -= amount
        self.agent_tokens[to_agent] = self.agent_tokens.get(to_agent, 0) + amount
        logger.agent_action(from_agent, f"transferred {amount} tokens to {to_agent}")
        return True
    
    def pool_tokens(self, agents: List[str]) -> int:
        """Calculate pooled tokens for a coalition."""
        return sum(self.agent_tokens.get(agent, 0) for agent in agents)
    
    def buy_gpu_slot(self, agent_name: str, cost: int) -> Optional[int]:
        """Purchase a GPU time slot."""
        if self.agent_tokens.get(agent_name, 0) < cost:
            return None
        
        # Find free slot
        for i, slot in enumerate(self.gpu_reservations):
            if slot is None:
                self.gpu_reservations[i] = agent_name
                self.agent_tokens[agent_name] -= cost
                logger.agent_action(agent_name, f"bought GPU slot {i}", f"{cost} tokens")
                return i
        
        return None
    
    def buy_cpu_boost(self, agent_name: str, millicores: int, cost: int) -> bool:
        """Purchase additional CPU allocation."""
        if self.agent_tokens.get(agent_name, 0) < cost:
            return False
        
        self.cpu_allocations[agent_name] += millicores
        self.agent_tokens[agent_name] -= cost
        logger.agent_action(agent_name, f"bought {millicores}mc CPU boost", f"{cost} tokens")
        return True
    
    def release_gpu_slots(self):
        """Clear GPU reservations after round."""
        self.gpu_reservations = [None] * self.gpu_slots
    
    def award_tokens(self, agent_name: str, amount: int):
        """Award tokens for performance."""
        self.agent_tokens[agent_name] = self.agent_tokens.get(agent_name, 0) + amount
    
    def remove_agent(self, agent_name: str):
        """Remove eliminated agent from resources."""
        self.agent_tokens.pop(agent_name, None)
        self.cpu_allocations.pop(agent_name, None)
    
    def get_agent_tokens(self, agent_name: str) -> int:
        """Get agent's current tokens."""
        return self.agent_tokens.get(agent_name, 0)
    
    def get_total_circulating(self) -> int:
        """Total tokens in circulation."""
        return sum(self.agent_tokens.values())
    
    def snapshot(self) -> Dict:
        """Get current resource state."""
        return {
            'agent_tokens': self.agent_tokens.copy(),
            'cpu_allocations': self.cpu_allocations.copy(),
            'gpu_reservations': self.gpu_reservations.copy(),
            'total_circulating': self.get_total_circulating()
        }