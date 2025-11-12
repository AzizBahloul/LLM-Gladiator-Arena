#core/orchestrator.py
"""Main game orchestrator."""
import time
import random
from typing import List, Dict
from models.agent import LLMAgent
from core.resource_manager import ResourcePool
from core.evaluator import evaluator
from tasks.base_task import TaskGenerator
from tasks.code_task import CodeOptimizationTask
from tasks.logic_task import LogicPuzzleTask
from tasks.creative_task import CreativeTask
from politics.alliance import AllianceManager
from politics.voting import VotingSystem
from politics.events import EventGenerator
from utils.logger import logger
from utils.storage import storage

class ArenaOrchestrator:
    """Orchestrates the entire LLM gladiator arena."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.round_num = 0
        self.season_complete = False
        
        # Initialize subsystems
        self.resource_manager = ResourcePool(
            total_tokens=config['game']['total_tokens'],
            gpu_slots=config['game']['gpu_slots'],
            cpu_millicores=config['game']['cpu_millicores']
        )
        
        self.voting_system = VotingSystem(config)
        self.alliance_manager = AllianceManager()
        self.event_generator = EventGenerator()
        
        # Task system
        self.task_generator = TaskGenerator()
        self.task_generator.register_task(CodeOptimizationTask)
        self.task_generator.register_task(LogicPuzzleTask)
        self.task_generator.register_task(CreativeTask)
        
        # Initialize agents
        self.agents: List[LLMAgent] = []
        self._initialize_agents()
        
        logger.header("🏛️  LLM GLADIATOR ARENA INITIALIZED  🏛️")
        logger.drama(f"Starting with {len(self.agents)} agents competing for glory!")
    
    def _initialize_agents(self):
        """Create all agents from config."""
        for agent_config in self.config['agents']:
            agent = LLMAgent(
                name=agent_config['name'],
                personality=agent_config['personality'],
                config=self.config
            )
            agent.tokens = agent_config['initial_tokens']
            self.agents.append(agent)
            
            # Register with resource manager
            self.resource_manager.initialize_agent(agent.name, agent.tokens)
        
        # Crown initial ruler (highest starting tokens)
        ruler = max(self.agents, key=lambda a: a.tokens)
        ruler.is_ruler = True
        logger.ruler_crowned(ruler.name)
    
    def run_season(self):
        """Run a complete season."""
        max_rounds = self.config['game']['rounds_per_season']
        
        for round_num in range(1, max_rounds + 1):
            self.round_num = round_num
            logger.round_start(round_num)
            
            # Check if game over
            alive = [a for a in self.agents if a.is_alive]
            if len(alive) <= 1:
                logger.drama("Only one agent remains!")
                self.season_complete = True
                break
            
            # Run round phases
            self._phase_pre_round_politics()
            self._phase_task_execution()
            self._phase_scoring_and_rewards()
            self._phase_elimination()
            self._phase_post_round_drama()
            
            # Save state
            self._save_round_state()
            
            # Pause for readability
            time.sleep(2)
        
        self._conclude_season()
    
    def _phase_pre_round_politics(self):
        """Pre-round: Alliances, coups, and strategy."""
        logger.header("⚡ Political Phase", "bold blue")
        
        # Check for possible coups
        ruler = next((a for a in self.agents if a.is_ruler), None)
        if ruler:
            conspirators = self.voting_system.check_coup_possible(
                self.agents, 
                self.resource_manager, 
                ruler.name
            )
            
            if conspirators and random.random() < 0.3:  # 30% chance they actually try
                success = self.voting_system.attempt_coup(conspirators, ruler.name, self.agents)
                if not success:
                    # Failed coup might hurt conspirators
                    for name in conspirators:
                        self.resource_manager.agent_tokens[name] = max(0, self.resource_manager.agent_tokens[name] - 5)
        
        # Random alliance proposals
        proposals = self.alliance_manager.propose_random_alliances(self.agents, self.resource_manager)
        
        for proposer, target in proposals:
            pitch = proposer.propose_alliance(target.name, f"Round {self.round_num}")
            logger.agent_action(proposer.name, f"proposes alliance to {target.name}")
            
            accepted = target.evaluate_alliance_offer(proposer.name, pitch)
            
            if accepted:
                self.alliance_manager.create_alliance([proposer.name, target.name], self.round_num)
                proposer.alliances.append(target.name)
                target.alliances.append(proposer.name)
    
    def _phase_task_execution(self):
        """Main task phase."""
        logger.header("🎯 Challenge Phase", "bold cyan")
        
        # Generate task
        task = self.task_generator.generate_round_task()
        logger.task_announcement(task.get_metadata()['type'])
        
        # Each agent solves
        responses = {}
        for agent in self.agents:
            if agent.is_alive:
                logger.agent_action(agent.name, "solving task...")
                response = agent.solve_task(task.get_prompt())
                responses[agent.name] = response
        
        # Evaluate all responses
        self.round_scores = {}
        for agent_name, response in responses.items():
            score = evaluator.evaluate(
                task.get_metadata()['type'],
                response,
                task.get_metadata()
            )
            self.round_scores[agent_name] = score
            
            # Update agent history
            agent = next(a for a in self.agents if a.name == agent_name)
            agent.round_scores.append(score)
    
    def _phase_scoring_and_rewards(self):
        """Award tokens based on performance."""
        logger.header("💰 Rewards Phase", "bold green")
        
        # Calculate rewards
        rewards = evaluator.calculate_round_rewards(self.round_scores)
        
        for agent_name, tokens in rewards.items():
            self.resource_manager.award_tokens(agent_name, tokens)
            logger.agent_action(agent_name, f"earned {tokens} tokens")
        
        # Update agent tokens
        for agent in self.agents:
            if agent.is_alive:
                agent.tokens = self.resource_manager.get_agent_tokens(agent.name)
        
        # Display scoreboard
        scoreboard_data = {}
        for agent in self.agents:
            if agent.is_alive:
                scoreboard_data[agent.name] = {
                    'score': self.round_scores.get(agent.name, 0),
                    'tokens': agent.tokens,
                    'is_ruler': agent.is_ruler,
                    'in_danger': False
                }
        
        logger.scoreboard(scoreboard_data)
    
    def _phase_elimination(self):
        """Eliminate bottom performer(s)."""
        logger.header("⚔️  Elimination Phase", "bold red")
        
        alive = [a for a in self.agents if a.is_alive]
        if len(alive) <= 3:  # Don't eliminate if 3 or fewer
            logger.drama("Too few agents remain - no elimination this round")
            return
        
        # Find bottom performers
        bottom_agents = evaluator.identify_bottom_performers(self.round_scores, count=2)
        
        if len(bottom_agents) < 2:
            return
        
        # Conduct duel
        agent1 = next(a for a in self.agents if a.name == bottom_agents[0])
        agent2 = next(a for a in self.agents if a.name == bottom_agents[1])
        
        # Generate a quick duel task
        duel_task = self.task_generator.generate_round_task()
        
        loser_name = self.voting_system.conduct_elimination_duel(
            agent1, agent2, duel_task, evaluator
        )
        
        # Eliminate loser
        loser = next(a for a in self.agents if a.name == loser_name)
        loser.is_alive = False
        loser.is_ruler = False
        
        logger.elimination(loser_name, "Lost elimination duel")
        
        # Remove from alliances and resources
        self.alliance_manager.remove_agent_from_all(loser_name)
        self.resource_manager.remove_agent(loser_name)
        
        # If ruler was eliminated, elect new ruler
        if loser.is_ruler:
            alive = [a for a in self.agents if a.is_alive]
            if alive:
                new_ruler = self.voting_system.elect_ruler(alive, self.resource_manager)
    
    def _phase_post_round_drama(self):
        """Generate random dramatic events."""
        event = self.event_generator.trigger_random_event(
            self.agents,
            self.resource_manager,
            self.round_num
        )
    
    def _save_round_state(self):
        """Save current state."""
        state = {
            'round': self.round_num,
            'agents': [a.to_dict() for a in self.agents],
            'resources': self.resource_manager.snapshot(),
            'scores': self.round_scores
        }
        storage.save_state(state)
    
    def _conclude_season(self):
        """End of season summary."""
        logger.header("🏆 SEASON FINALE 🏆", "bold gold1")
        
        alive = [a for a in self.agents if a.is_alive]
        
        if alive:
            winner = max(alive, key=lambda a: a.tokens)
            finale_msg = self.event_generator.generate_finale_drama(winner.name, self.agents)
            logger.drama(finale_msg)
            logger.final_summary(
                winner.name,
                self.round_num,
                self.event_generator.event_history
            )
        else:
            logger.drama("No survivors... the arena claims all.")