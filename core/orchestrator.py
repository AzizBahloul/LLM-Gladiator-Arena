#core/orchestrator.py
"""Main game orchestrator."""
import time
import random
from typing import List, Dict, Optional
from models.agent import LLMAgent
from core.resource_manager import ResourcePool
from core.evaluator import evaluator
from core.messaging import messaging_system, MessageType
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
    
    def __init__(self, config: Dict, restore_state: Dict = None, gui=None):
        self.config = config
        self.round_num = 0
        self.season_complete = False
        self.gui = gui  # Optional GUI instance
        
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

        # If a restore state was provided, apply it to the runtime
        if restore_state:
            # Restore round and season state
            self.round_num = restore_state.get('round', self.round_num)
            self.season_complete = restore_state.get('season_complete', self.season_complete)

            # Restore resource manager snapshot if present
            resources = restore_state.get('resources') or {}
            if resources:
                self.resource_manager.agent_tokens = resources.get('agent_tokens', {}).copy()
                self.resource_manager.cpu_allocations = resources.get('cpu_allocations', {}).copy()
                self.resource_manager.gpu_reservations = resources.get('gpu_reservations', self.resource_manager.gpu_reservations).copy()

            # Restore agents' individual state
            saved_agents = {a['name']: a for a in restore_state.get('agents', [])}
            for agent in self.agents:
                saved = saved_agents.get(agent.name)
                if saved:
                    agent.tokens = saved.get('tokens', agent.tokens)
                    agent.is_alive = saved.get('is_alive', agent.is_alive)
                    agent.is_ruler = saved.get('is_ruler', agent.is_ruler)
                    agent.round_scores = saved.get('round_scores', agent.round_scores)
        
        logger.header("🏛️  LLM GLADIATOR ARENA INITIALIZED  🏛️")
        logger.drama(f"Starting with {len(self.agents)} agents competing for glory!")
        
        # Don't update GUI here - it hasn't been mounted yet
        # It will be updated when run_season() is called
    
    def _initialize_agents(self):
        """Create all agents from config."""
        for agent_config in self.config['agents']:
            agent = LLMAgent(
                name=agent_config['name'],
                personality=agent_config['personality'],
                config=self.config,
                model=agent_config.get('model')  # Pass agent-specific model
            )
            agent.tokens = agent_config['initial_tokens']
            self.agents.append(agent)
            
            # Register with resource manager
            self.resource_manager.initialize_agent(agent.name, agent.tokens)
            
            # Log which model this agent is using
            logger.agent_action(agent.name, f"loaded with model", agent.model)
        
        # Crown initial ruler (highest starting tokens)
        ruler = max(self.agents, key=lambda a: a.tokens)
        ruler.is_ruler = True
        logger.ruler_crowned(ruler.name)
    
    def _update_gui(self):
        """Update GUI with current game state."""
        if not self.gui:
            return
        
        # Use call_from_thread to safely update GUI from background thread
        try:
            # Update agents
            agent_data = [a.to_dict() for a in self.agents]
            self.gui.call_from_thread(self.gui.update_agents, agent_data)
            
            # Update round
            self.gui.call_from_thread(self.gui.update_round, self.round_num)
            
            # Update resources
            alive_agents = [a for a in self.agents if a.is_alive]
            cpu_usage = min(100, len(alive_agents) * 15)  # Simulate CPU usage
            gpu_usage = min(100, len(alive_agents) * 20)  # Simulate GPU usage
            token_pool = self.resource_manager.total_tokens
            self.gui.call_from_thread(self.gui.update_resources, cpu_usage, gpu_usage, token_pool)
        except Exception:
            pass  # Ignore GUI update errors
    
    def _send_chat_message(self, sender: str, content: str, msg_type: str = "public"):
        """Send a chat message to GUI and messaging system."""
        if self.gui:
            try:
                self.gui.call_from_thread(self.gui.add_chat_message, sender, content, msg_type)
            except Exception:
                pass
        # Log to messaging system so all agents can see history
        messaging_system.send_message(sender, content, MessageType.PUBLIC)
    
    def _get_chat_history(self, agent_name: str) -> str:
        """Get chat history formatted for an agent to read."""
        return messaging_system.get_chat_history_for_llm(agent_name, limit=15)
    
    def _trigger_agent_discussion(self, context: str, participants: List[LLMAgent] = None,
                                   discussion_rounds: int = 2):
        """Trigger a real-time discussion between agents."""
        if participants is None:
            participants = [a for a in self.agents if a.is_alive]
        
        if len(participants) < 2:
            return
        
        # System announcement
        if self.gui:
            self.gui.call_from_thread(
                self.gui.add_system_message,
                f"💬 {context}"
            )
        
        for round_idx in range(discussion_rounds):
            # Shuffle order for variety
            order = participants.copy()
            random.shuffle(order)
            
            for agent in order:
                if not agent.is_alive:
                    continue
                
                # Get current chat history for this agent
                chat_history = self._get_chat_history(agent.name)
                
                # Agent composes a message with full context
                try:
                    message = agent.compose_message(
                        context=context,
                        chat_history=chat_history,
                        message_type="public"
                    )
                    
                    if message and len(message.strip()) > 0:
                        self._send_chat_message(agent.name, message, "public")
                        
                        # Small delay for real-time effect
                        time.sleep(0.5)
                        
                except Exception as e:
                    logger.agent_action(agent.name, "chat failed", str(e))
    
    def _trigger_taunt_exchange(self, agent1: LLMAgent, agent2: LLMAgent, context: str = ""):
        """Trigger a taunt exchange between two agents."""
        if self.gui:
            self.gui.call_from_thread(
                self.gui.add_system_message,
                f"🔥 {agent1.name} faces {agent2.name}"
            )
        
        # First agent speaks with chat history
        chat_history = self._get_chat_history(agent1.name)
        msg1 = agent1.compose_message(
            context=f"You're face to face with {agent2.name}.",
            chat_history=chat_history,
            message_type="taunt"
        )
        self._send_chat_message(agent1.name, msg1, "taunt")
        time.sleep(0.5)
        
        # Second agent responds with updated history
        chat_history = self._get_chat_history(agent2.name)
        msg2 = agent2.respond_to_message(agent1.name, msg1, context, chat_history)
        self._send_chat_message(agent2.name, msg2, "taunt")
        time.sleep(0.5)
        
        # Maybe one more exchange
        if random.random() > 0.5:
            chat_history = self._get_chat_history(agent1.name)
            msg3 = agent1.respond_to_message(agent2.name, msg2, "", chat_history)
            self._send_chat_message(agent1.name, msg3, "taunt")
    
    def run_season(self):
        """Run a complete season."""
        max_rounds = self.config['game']['rounds_per_season']
        
        # Initial discussion
        if self.gui:
            self.gui.call_from_thread(
                self.gui.add_system_message,
                "🏛️ The Arena opens... Gladiators gather!"
            )
        
        # Initial discussion - just set the scene, let them decide what to say
        self._trigger_agent_discussion(
            "The arena season is starting. All gladiators are present.",
            discussion_rounds=1
        )
        
        for round_num in range(1, max_rounds + 1):
            self.round_num = round_num
            logger.round_start(round_num)
            
            if self.gui:
                self.gui.call_from_thread(self.gui.add_event, f"═══ ROUND {round_num} BEGINS ═══", "bold cyan")
            
            # Check if game over
            alive = [a for a in self.agents if a.is_alive]
            if len(alive) <= 1:
                logger.drama("Only one agent remains!")
                if self.gui:
                    self.gui.call_from_thread(self.gui.add_drama_event, "Only one agent remains!")
                self.season_complete = True
                break
            
            # Run round phases
            self._phase_pre_round_politics()
            self._phase_discussion()  # NEW: Discussion phase
            self._phase_task_execution()
            self._phase_scoring_and_rewards()
            self._phase_elimination()
            self._phase_post_round_drama()
            
            # Update GUI
            if self.gui:
                self._update_gui()
            
            # Save state
            self._save_round_state()
            
            # Pause for readability
            time.sleep(2)
        
        self._conclude_season()
    
    def _phase_discussion(self):
        """Discussion phase - agents discuss strategy and taunt each other."""
        logger.header("💬 Discussion Phase", "bold cyan")
        
        if self.gui:
            self.gui.call_from_thread(
                self.gui.add_event, 
                "💬 Agents engage in discussion...", 
                "cyan"
            )
        
        alive = [a for a in self.agents if a.is_alive]
        
        # Simple context - just state facts, let LLMs decide what to discuss
        ruler = next((a for a in self.agents if a.is_ruler), None)
        
        contexts = [
            f"Round {self.round_num} starting. {len(alive)} gladiators remain.",
            f"Current ruler: {ruler.name if ruler else 'None'}. Round {self.round_num}.",
            f"{len(alive)} gladiators alive. Someone will be eliminated soon.",
            f"Pre-round gathering. The arena awaits."
        ]
        
        context = random.choice(contexts)
        
        # Main discussion
        self._trigger_agent_discussion(context, alive, discussion_rounds=1)
        
        # Chance for random taunt exchange
        if len(alive) >= 2 and random.random() > 0.6:
            # Pick two non-allied agents for trash talk
            potential_pairs = []
            for i, a1 in enumerate(alive):
                for a2 in alive[i+1:]:
                    if a2.name not in a1.alliances:
                        potential_pairs.append((a1, a2))
            
            if potential_pairs:
                a1, a2 = random.choice(potential_pairs)
                self._trigger_taunt_exchange(a1, a2, f"Round {self.round_num} competition")
    
    def _phase_pre_round_politics(self):
        """Pre-round: Alliances, coups, and strategy."""
        logger.header("⚡ Political Phase", "bold blue")
        
        if self.gui:
            self.gui.call_from_thread(self.gui.add_event, "⚡ Political maneuvering begins...", "blue")
        
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
                    if self.gui:
                        self.gui.call_from_thread(self.gui.add_drama_event, f"Coup attempt against {ruler.name} FAILED!")
                        # Conspirators react
                        for name in conspirators[:2]:
                            conspirator = next((a for a in self.agents if a.name == name), None)
                            if conspirator:
                                chat_history = messaging_system.get_chat_context_for_agent(conspirator.name)
                                reaction = conspirator.compose_message(
                                    context=f"Your coup against {ruler.name} just failed. You lost tokens.",
                                    message_type="public",
                                    chat_history=chat_history
                                )
                                self._send_chat_message(name, reaction, "public")
                                time.sleep(0.3)
                else:
                    if self.gui:
                        self.gui.call_from_thread(self.gui.add_drama_event, f"{ruler.name} overthrown in COUP!")
                        # Overthrown ruler reacts
                        chat_history = messaging_system.get_chat_context_for_agent(ruler.name)
                        reaction = ruler.compose_message(
                            context="You were just overthrown in a coup. You're no longer ruler.",
                            message_type="public",
                            chat_history=chat_history
                        )
                        self._send_chat_message(ruler.name, reaction, "public")
        
        # Random alliance proposals
        proposals = self.alliance_manager.propose_random_alliances(self.agents, self.resource_manager)
        
        for proposer, target in proposals:
            pitch = proposer.propose_alliance(target.name, f"Round {self.round_num}")
            logger.agent_action(proposer.name, f"proposes alliance to {target.name}")
            
            # Show the alliance pitch in chat
            self._send_chat_message(proposer.name, f"[To {target.name}] {pitch}", "alliance")
            time.sleep(0.3)
            
            accepted = target.evaluate_alliance_offer(proposer.name, pitch)
            
            if accepted:
                self.alliance_manager.create_alliance([proposer.name, target.name], self.round_num)
                proposer.alliances.append(target.name)
                target.alliances.append(proposer.name)
                
                # Alliance acceptance in chat - just give context
                chat_history = messaging_system.get_chat_context_for_agent(target.name)
                response = target.compose_message(
                    context=f"{proposer.name} just offered you an alliance and you accepted.",
                    message_type="alliance",
                    chat_history=chat_history
                )
                self._send_chat_message(target.name, response, "alliance")
                
                if self.gui:
                    self.gui.call_from_thread(self.gui.add_alliance_event, f"{proposer.name} & {target.name} form alliance!")
            else:
                # Rejection - just give context
                chat_history = messaging_system.get_chat_context_for_agent(target.name)
                rejection = target.compose_message(
                    context=f"{proposer.name} just offered you an alliance and you rejected it.",
                    message_type="public",
                    chat_history=chat_history
                )
                self._send_chat_message(target.name, rejection, "public")
    
    def _phase_task_execution(self):
        """Main task phase."""
        logger.header("🎯 Challenge Phase", "bold cyan")
        
        if self.gui:
            self.gui.call_from_thread(self.gui.add_event, "🎯 Challenge commences!", "cyan")
            self.gui.call_from_thread(
                self.gui.add_system_message,
                "⚔️ Challenge phase begins!"
            )
        
        # Generate task
        task = self.task_generator.generate_round_task()
        logger.task_announcement(task.get_metadata()['type'])
        
        if self.gui:
            self.gui.call_from_thread(self.gui.add_combat_event, f"Task: {task.get_metadata()['type']}")
        
        # Each agent solves
        responses = {}
        for agent in self.agents:
            if agent.is_alive:
                logger.agent_action(agent.name, "solving task...")
                
                # Optional: Agent comments before solving
                if random.random() > 0.7:
                    comment = agent.compose_message(
                        f"I'm about to solve a {task.get_metadata()['type']} challenge",
                        message_type="strategy"
                    )
                    self._send_chat_message(agent.name, comment, "strategy")
                
                response = agent.solve_task(task.get_prompt())
                responses[agent.name] = response
                if self.gui:
                    self.gui.call_from_thread(self.gui.add_event, f"{agent.name} completes challenge...", "white")
        
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
        
        if self.gui:
            self.gui.call_from_thread(self.gui.add_event, "💰 Rewards distributed...", "green")
        
        # Calculate rewards
        rewards = evaluator.calculate_round_rewards(self.round_scores)
        
        for agent_name, tokens in rewards.items():
            self.resource_manager.award_tokens(agent_name, tokens)
            logger.agent_action(agent_name, f"earned {tokens} tokens")
            if self.gui:
                self.gui.call_from_thread(self.gui.add_event, f"{agent_name} earned {tokens} BB", "green")
        
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
        
        if self.gui:
            self.gui.call_from_thread(self.gui.add_event, "⚔️  Elimination phase begins...", "red")
        
        alive = [a for a in self.agents if a.is_alive]
        if len(alive) <= 3:  # Don't eliminate if 3 or fewer
            logger.drama("Too few agents remain - no elimination this round")
            if self.gui:
                self.gui.call_from_thread(self.gui.add_event, "Mercy granted - no elimination", "yellow")
            return
        
        # Find bottom performers
        bottom_agents = evaluator.identify_bottom_performers(self.round_scores, count=2)
        
        if len(bottom_agents) < 2:
            return
        
        # Conduct duel
        agent1 = next(a for a in self.agents if a.name == bottom_agents[0])
        agent2 = next(a for a in self.agents if a.name == bottom_agents[1])
        
        if self.gui:
            self.gui.call_from_thread(self.gui.add_combat_event, f"{agent1.name} vs {agent2.name} - DUEL!")
        
        # Pre-duel trash talk
        if self.gui:
            self.gui.call_from_thread(
                self.gui.add_system_message,
                f"⚔️ ELIMINATION DUEL: {agent1.name} vs {agent2.name}"
            )
        
        # Trigger intense taunt exchange before duel
        self._trigger_taunt_exchange(agent1, agent2, "ELIMINATION DUEL - loser goes home!")
        
        # Generate a quick duel task
        duel_task = self.task_generator.generate_round_task()
        
        loser_name = self.voting_system.conduct_elimination_duel(
            agent1, agent2, duel_task, evaluator
        )
        
        # Eliminate loser
        loser = next(a for a in self.agents if a.name == loser_name)
        winner = agent1 if loser_name == agent2.name else agent2
        was_ruler = loser.is_ruler
        loser.is_alive = False
        loser.is_ruler = False
        logger.elimination(loser_name, "Lost elimination duel")
        
        # Loser's last words - just context
        chat_history = messaging_system.get_chat_context_for_agent(loser.name)
        last_words = loser.compose_message(
            context=f"You just lost the elimination duel to {winner.name}. You're out.",
            message_type="public",
            chat_history=chat_history
        )
        self._send_chat_message(loser.name, f"💀 {last_words}", "public")
        
        # Winner reacts
        chat_history = messaging_system.get_chat_context_for_agent(winner.name)
        victory_message = winner.compose_message(
            context=f"You just eliminated {loser.name} in the duel.",
            message_type="taunt",
            chat_history=chat_history
        )
        self._send_chat_message(winner.name, victory_message, "taunt")
        
        if self.gui:
            self.gui.call_from_thread(self.gui.add_elimination_event, loser_name)
        
        self.alliance_manager.remove_agent_from_all(loser_name)
        self.resource_manager.remove_agent(loser_name)
        if was_ruler:
            alive = [a for a in self.agents if a.is_alive]
            if alive:
                new_ruler = self.voting_system.elect_ruler(alive, self.resource_manager)
                if self.gui:
                    self.gui.call_from_thread(self.gui.add_drama_event, f"{new_ruler} becomes the new RULER!")
                    
                    # New ruler speaks
                    ruler_agent = next((a for a in self.agents if a.name == new_ruler), None)
                    if ruler_agent:
                        chat_history = messaging_system.get_chat_context_for_agent(ruler_agent.name)
                        coronation = ruler_agent.compose_message(
                            context="You just became the new ruler of the arena.",
                            message_type="public",
                            chat_history=chat_history
                        )
                        self._send_chat_message(new_ruler, f"👑 {coronation}", "broadcast")
    
    def _phase_post_round_drama(self):
        """Generate random dramatic events."""
        event = self.event_generator.trigger_random_event(
            self.agents,
            self.resource_manager,
            self.round_num
        )
        
        # End of round discussion (chance)
        if random.random() > 0.5:
            alive = [a for a in self.agents if a.is_alive]
            if len(alive) >= 2:
                # Pick a random agent to comment
                commenter = random.choice(alive)
                chat_history = messaging_system.get_chat_context_for_agent(commenter.name)
                comment = commenter.compose_message(
                    context=f"Round {self.round_num} just ended.",
                    message_type="public",
                    chat_history=chat_history
                )
                self._send_chat_message(commenter.name, comment, "public")
    
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
            
            if self.gui:
                self.gui.call_from_thread(self.gui.add_victory_event, winner.name)
                self.gui.call_from_thread(self.gui.add_drama_event, finale_msg)
                
                # Winner speaks - just context
                chat_history = messaging_system.get_chat_context_for_agent(winner.name)
                victory_speech = winner.compose_message(
                    context="You just won the entire arena. You are the champion.",
                    message_type="public",
                    chat_history=chat_history
                )
                self._send_chat_message(winner.name, f"🏆 {victory_speech}", "broadcast")
                
                # Other survivors react
                for agent in alive:
                    if agent.name != winner.name:
                        chat_history = messaging_system.get_chat_context_for_agent(agent.name)
                        reaction = agent.compose_message(
                            context=f"The season is over. {winner.name} won.",
                            message_type="public",
                            chat_history=chat_history
                        )
                        self._send_chat_message(agent.name, reaction, "public")
                        time.sleep(0.3)
            
            logger.final_summary(
                winner.name,
                self.round_num,
                self.event_generator.event_history
            )
        else:
            logger.drama("No survivors... the arena claims all.")
            if self.gui:
                self.gui.call_from_thread(self.gui.add_drama_event, "No survivors... the arena claims all.")
                self.gui.call_from_thread(
                    self.gui.add_system_message,
                    "💀 All gladiators have fallen. The arena stands empty."
                )