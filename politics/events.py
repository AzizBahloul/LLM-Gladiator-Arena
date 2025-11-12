#politics/events.py
"""Dramatic event generator."""
import random
from typing import List, Dict, Optional
from utils.logger import logger

class EventGenerator:
    """Generates random dramatic events for flavor."""
    
    BETRAYAL_EVENTS = [
        "{agent} leaked {target}'s strategy to the arena!",
        "{agent} sabotaged {target}'s CPU allocation!",
        "{agent} spread rumors about {target}'s last performance!",
        "{agent} stole tokens from {target} in a daring heist!",
    ]
    
    WILDCARD_EVENTS = [
        "A mysterious benefactor donated 10 tokens to {agent}!",
        "{agent} found a bug in the arena and gained an advantage!",
        "The Jester corrupted {agent}'s task submission... or did they?",
        "Emergency GPU auction! All slots temporarily available!",
        "{agent} published a manifesto that went viral!",
    ]
    
    ALLIANCE_DRAMA = [
        "{agent1} and {agent2} sealed their alliance with a token exchange!",
        "Tension rises between {agent1} and {agent2} within their alliance...",
        "{agent1} questions {agent2}'s loyalty!",
        "{agent1} and {agent2} staged a joint press conference!",
    ]
    
    RULER_EVENTS = [
        "Ruler {ruler} enacted an emergency decree!",
        "Whispers of a coup against {ruler} grow louder...",
        "{ruler} threw a lavish banquet (deducting 5 tokens from treasury)!",
        "{ruler}'s popularity is waning among the masses!",
    ]
    
    def __init__(self):
        self.event_history = []
    
    def trigger_random_event(self, agents: List, resource_manager, round_num: int) -> Optional[Dict]:
        """Trigger a random event for drama."""
        if random.random() > 0.3:  # 30% chance per round
            return None
        
        alive_agents = [a for a in agents if a.is_alive]
        if not alive_agents:
            return None
        
        event_type = random.choice(['betrayal', 'wildcard', 'alliance', 'ruler'])
        
        if event_type == 'betrayal' and len(alive_agents) >= 2:
            agent = random.choice(alive_agents)
            target = random.choice([a for a in alive_agents if a != agent])
            message = random.choice(self.BETRAYAL_EVENTS).format(
                agent=agent.name, 
                target=target.name
            )
            logger.drama(message)
            self.event_history.append({'round': round_num, 'type': 'betrayal', 'message': message})
            return {'type': 'betrayal', 'agent': agent.name, 'target': target.name}
        
        elif event_type == 'wildcard':
            agent = random.choice(alive_agents)
            message = random.choice(self.WILDCARD_EVENTS).format(agent=agent.name)
            logger.drama(message)
            
            # Some events give tokens
            if "donated" in message:
                resource_manager.award_tokens(agent.name, 10)
            
            self.event_history.append({'round': round_num, 'type': 'wildcard', 'message': message})
            return {'type': 'wildcard', 'agent': agent.name}
        
        elif event_type == 'alliance' and len(alive_agents) >= 2:
            agent1, agent2 = random.sample(alive_agents, 2)
            message = random.choice(self.ALLIANCE_DRAMA).format(
                agent1=agent1.name,
                agent2=agent2.name
            )
            logger.drama(message)
            self.event_history.append({'round': round_num, 'type': 'alliance', 'message': message})
            return {'type': 'alliance', 'agents': [agent1.name, agent2.name]}
        
        elif event_type == 'ruler':
            rulers = [a for a in alive_agents if a.is_ruler]
            if rulers:
                ruler = rulers[0]
                message = random.choice(self.RULER_EVENTS).format(ruler=ruler.name)
                logger.drama(message)
                self.event_history.append({'round': round_num, 'type': 'ruler', 'message': message})
                return {'type': 'ruler', 'ruler': ruler.name}
        
        return None
    
    def generate_finale_drama(self, winner_name: str, agents: List) -> str:
        """Generate a dramatic finale message."""
        templates = [
            f"After a grueling battle, {winner_name} emerges victorious, standing atop a mountain of fallen rivals!",
            f"The arena falls silent. {winner_name} has conquered all challengers. Long live the champion!",
            f"In a stunning display of dominance, {winner_name} claims the throne. The competition wasn't even close.",
            f"{winner_name} prevails! Their strategy, cunning, and raw power proved unstoppable.",
        ]
        
        return random.choice(templates)