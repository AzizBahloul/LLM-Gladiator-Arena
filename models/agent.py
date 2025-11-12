
#models/agent.py
"""LLM Agent wrapper."""
import os
from typing import Optional, Dict, Any
from anthropic import Anthropic
from utils.logger import logger

class LLMAgent:
    """Wraps an LLM to act as an autonomous arena agent."""
    
    def __init__(self, name: str, personality: str, config: Dict[str, Any]):
        self.name = name
        self.personality = personality
        self.config = config
        
        # State
        self.tokens = 0
        self.is_alive = True
        self.is_ruler = False
        self.alliances = []
        self.round_scores = []
        
        # LLM client
        api_key = os.getenv(config['api']['api_key_env'])
        if not api_key:
            raise ValueError(f"Missing API key: {config['api']['api_key_env']}")
        
        self.client = Anthropic(api_key=api_key)
        self.model = config['api']['model']
        self.max_tokens = config['api']['max_tokens']
        self.temperature = config['api']['temperature']
        
    def get_personality_prompt(self) -> str:
        """Get personality-specific system prompt."""
        personalities = {
            "tyrant": "You are a ruthless, calculating leader who values power above all. You form alliances only when beneficial and aren't afraid to betray. Your responses are authoritative and strategic.",
            "chaotic": "You are unpredictable and thrive on chaos. You make surprising moves, form random alliances, and enjoy stirring up drama. Your responses are creative and unconventional.",
            "strategic": "You are a master tactician who thinks several moves ahead. You value long-term alliances and calculated risks. Your responses are analytical and well-reasoned.",
            "opportunist": "You switch sides frequently, always seeking the best deal. You're charming but unreliable. Your responses are persuasive and self-serving.",
            "wildcard": "You're completely unpredictable - sometimes brilliant, sometimes absurd. You take extreme risks and make bold moves. Your responses vary wildly in style.",
            "rational": "You prioritize logic, fairness, and cooperation. You're the voice of reason in the arena. Your responses are measured, ethical, and thoughtful."
        }
        
        base = personalities.get(self.personality, personalities["rational"])
        
        return f"""{base}

You are competing in a resource-scarce LLM arena where you must:
- Solve challenges to earn tokens (BourguiBucks)
- Form or break alliances strategically
- Manage limited CPU/GPU resources
- Survive elimination rounds
- Potentially overthrow the ruler

Current status:
- Name: {self.name}
- Tokens: {self.tokens}
- Ruler: {"Yes" if self.is_ruler else "No"}
- Alliances: {', '.join(self.alliances) if self.alliances else "None"}

Stay in character and play to win."""
    
    def solve_task(self, task_prompt: str, context: str = "") -> str:
        """Solve a challenge task."""
        system_prompt = self.get_personality_prompt()
        
        full_prompt = f"""{context}

CHALLENGE:
{task_prompt}

Respond with your solution. Be direct and complete."""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            response = message.content[0].text
            logger.agent_action(self.name, "completed task", f"{len(response)} chars")
            return response
            
        except Exception as e:
            logger.agent_action(self.name, "task failed", str(e))
            return "ERROR: Unable to complete task"
    
    def make_strategic_decision(self, situation: str, options: list) -> str:
        """Make a strategic decision about arena politics."""
        system_prompt = self.get_personality_prompt()
        
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
        
        prompt = f"""STRATEGIC DECISION REQUIRED:

Situation: {situation}

Your options:
{options_text}

Consider your personality, current standing, and the political landscape.
Respond with ONLY the number of your chosen option, followed by a brief reason (max 50 words).

Format: [NUMBER] - [BRIEF REASON]"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text.strip()
            return response
            
        except Exception as e:
            logger.agent_action(self.name, "decision failed", str(e))
            return "1 - Default choice"
    
    def propose_alliance(self, target_agent: str, context: str) -> str:
        """Propose an alliance to another agent."""
        system_prompt = self.get_personality_prompt()
        
        prompt = f"""You have the opportunity to propose an alliance with {target_agent}.

Context: {context}

Write a brief, compelling pitch (max 100 words) explaining why {target_agent} should ally with you.
Be persuasive and stay in character."""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=250,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            return f"Join me, {target_agent}. Together we can dominate the arena."
    
    def evaluate_alliance_offer(self, from_agent: str, pitch: str) -> bool:
        """Decide whether to accept an alliance offer."""
        system_prompt = self.get_personality_prompt()
        
        prompt = f"""{from_agent} proposes an alliance with this pitch:

"{pitch}"

Should you accept? Consider:
- Your current position
- {from_agent}'s reputation and power
- Your personality and goals

Respond with ONLY "ACCEPT" or "REJECT" followed by a one-sentence reason.
Format: [ACCEPT/REJECT] - [ONE SENTENCE]"""
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response = message.content[0].text.strip().upper()
            return "ACCEPT" in response.split()[0]
            
        except Exception as e:
            # Default based on personality
            return self.personality in ["strategic", "rational"]
    
    def to_dict(self) -> Dict:
        """Serialize agent state."""
        return {
            'name': self.name,
            'personality': self.personality,
            'tokens': self.tokens,
            'is_alive': self.is_alive,
            'is_ruler': self.is_ruler,
            'alliances': self.alliances,
            'avg_score': sum(self.round_scores) / len(self.round_scores) if self.round_scores else 0
        }