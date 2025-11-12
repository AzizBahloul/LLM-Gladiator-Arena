#politics/voting.py
"""Voting and coup mechanics."""
import random
from typing import List, Optional
from utils.logger import logger

class VotingSystem:
    """Handles coups, elections, and political drama."""
    
    def __init__(self, config: dict):
        self.coup_threshold = config['politics']['coup_threshold']
        self.revolt_base_prob = config['politics']['revolt_probability_base']
        self.revolt_increase = config['politics']['revolt_increase_per_dictatorship']
        self.dictatorships_count = 0
    
    def check_coup_possible(self, agents: List, resource_manager, ruler_name: str) -> Optional[List[str]]:
        """Check if any coalition has enough power for a coup."""
        if not ruler_name:
            return None
        
        # Check each potential coalition
        conspirators = []
        total_circulating = resource_manager.get_total_circulating()
        
        # Get all agents except ruler
        non_rulers = [a.name for a in agents if a.is_alive and a.name != ruler_name]
        
        # Calculate if top agents together exceed threshold
        agent_tokens = [(a.name, resource_manager.get_agent_tokens(a.name)) for a in agents if a.is_alive and a.name != ruler_name]
        agent_tokens.sort(key=lambda x: x[1], reverse=True)
        
        pooled = 0
        for name, tokens in agent_tokens:
            conspirators.append(name)
            pooled += tokens
            power = pooled / total_circulating if total_circulating > 0 else 0
            
            if power > self.coup_threshold and len(conspirators) >= 2:
                return conspirators
        
        return None
    
    def attempt_coup(self, conspirators: List[str], ruler_name: str, agents: List) -> bool:
        """Execute a coup attempt."""
        logger.coup_attempt(conspirators, ruler_name)
        
        # Coup success based on numbers and chance
        base_success = 0.6 if len(conspirators) >= 3 else 0.4
        
        # Add randomness
        success = random.random() < base_success
        
        if success:
            logger.drama(f"COUP SUCCEEDED! {ruler_name} has been overthrown!")
            
            # Pick new ruler from conspirators
            new_ruler = random.choice(conspirators)
            logger.ruler_crowned(new_ruler)
            
            # Update ruler status
            for agent in agents:
                if agent.name == ruler_name:
                    agent.is_ruler = False
                elif agent.name == new_ruler:
                    agent.is_ruler = True
            
            return True
        else:
            logger.drama(f"Coup FAILED! {ruler_name} maintains power!")
            # Failed coup might have consequences
            return False
    
    def check_spontaneous_revolt(self) -> bool:
        """Check if a spontaneous revolt occurs."""
        prob = self.revolt_base_prob + (self.dictatorships_count * self.revolt_increase)
        return random.random() < prob
    
    def record_dictatorship(self):
        """Track dictatorial actions."""
        self.dictatorships_count += 1
    
    def conduct_elimination_duel(self, agent1, agent2, task, evaluator) -> str:
        """Conduct a sudden-death duel between two agents."""
        logger.drama(f"⚔️  ELIMINATION DUEL: {agent1.name} vs {agent2.name}")
        
        # Both solve the same task
        response1 = agent1.solve_task(task.get_prompt())
        response2 = agent2.solve_task(task.get_prompt())
        
        # Evaluate
        score1 = evaluator.evaluate(task.get_metadata()['type'], response1, task.get_metadata())
        score2 = evaluator.evaluate(task.get_metadata()['type'], response2, task.get_metadata())
        
        logger.agent_action(agent1.name, "duel score", f"{score1:.2f}")
        logger.agent_action(agent2.name, "duel score", f"{score2:.2f}")
        
        # Winner stays
        if score1 > score2:
            loser = agent2.name
        elif score2 > score1:
            loser = agent1.name
        else:
            # Tie - random elimination
            loser = random.choice([agent1.name, agent2.name])
            logger.drama("Duel ended in a TIE! Random elimination...")
        
        return loser
    
    def elect_ruler(self, agents: List, resource_manager) -> str:
        """Elect a new ruler based on tokens and performance."""
        candidates = [(a.name, resource_manager.get_agent_tokens(a.name)) for a in agents if a.is_alive]
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            winner = candidates[0][0]
            logger.ruler_crowned(winner)
            
            for agent in agents:
                agent.is_ruler = (agent.name == winner)
            
            return winner
        
        return ""