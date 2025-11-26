
#models/agent.py
"""LLM Agent wrapper."""
import os
import subprocess
from typing import Optional, Dict, Any
import requests
from utils.logger import logger
from utils.gpu_utils import gpu_manager

class LLMAgent:
    """Wraps an LLM to act as an autonomous arena agent."""
    
    def __init__(self, name: str, personality: str, config: Dict[str, Any], model: Optional[str] = None):
        self.name = name
        self.personality = personality
        self.config = config
        
        # State
        self.tokens = 0
        self.is_alive = True
        self.is_ruler = False
        self.alliances = []
        self.round_scores = []
        
        # LLM client - support multiple providers (anthropic, ollama)
        self.provider = config['api'].get('provider', 'ollama')
        # Use agent-specific model if provided, otherwise fall back to config default
        self.model = model if model else config['api']['model']
        self.max_tokens = config['api'].get('max_tokens', 512)
        self.temperature = config['api'].get('temperature', 0.7)

        if self.provider == 'anthropic':
            api_key = os.getenv(config['api']['api_key_env'])
            if not api_key:
                raise ValueError(f"Missing API key: {config['api']['api_key_env']}")
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Anthropic client: {e}")

        elif self.provider == 'ollama':
            # Ollama runs locally (or at configured URL)
            self.ollama_url = config['api'].get('ollama_url', 'http://localhost:11434')
            # Ensure GPU optimization for Ollama
            gpu_manager.optimize_for_ollama()
            # prefer HTTP API; if unavailable, fall back to CLI when generating
            self.ollama_cli = shutil_which = None
            try:
                # lazily detect CLI
                self.ollama_cli = shutil_which = subprocess.run(['which', 'ollama'], capture_output=True, text=True)
                if shutil_which and shutil_which.returncode == 0:
                    self.ollama_cli = shutil_which.stdout.strip()
                else:
                    self.ollama_cli = None
            except Exception:
                self.ollama_cli = None

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
    def get_personality_prompt(self) -> str:
        """Get personality-specific system prompt - minimal guidance, let LLM be autonomous."""
        personalities = {
            "tyrant": "You have a tyrant personality - power-hungry and dominating.",
            "chaotic": "You have a chaotic personality - unpredictable and wild.",
            "strategic": "You have a strategic personality - calculating and analytical.",
            "opportunist": "You have an opportunist personality - always looking for the best deal.",
            "wildcard": "You have a wildcard personality - completely unpredictable.",
            "rational": "You have a rational personality - logical and fair-minded."
        }
        
        base = personalities.get(self.personality, personalities["rational"])
        
        return f"""You are {self.name}, an AI gladiator in the LLM Arena.
{base}

THE GAME:
- Multiple AI models compete autonomously (no human help)
- Earn tokens (BourguiBucks) by solving challenges  
- Form alliances, betray rivals, stage coups
- Bottom performers face elimination duels
- Last one standing wins

YOUR STATUS:
- Tokens: {self.tokens} BB
- Role: {"👑 RULER" if self.is_ruler else "Gladiator"}
- Allies: {', '.join(self.alliances) if self.alliances else "None"}

Be yourself. Make your own choices. This is YOUR game."""
    
    def solve_task(self, task_prompt: str, context: str = "") -> str:
        """Solve a challenge task."""
        system_prompt = self.get_personality_prompt()
        
        full_prompt = f"""{context}

CHALLENGE:
{task_prompt}

Respond with your solution. Be direct and complete."""
        
        try:
            if self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                response = message.content[0].text

            else:  # ollama
                response = self._ollama_generate(system_prompt, full_prompt)

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
            if self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=200,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                response = message.content[0].text.strip()
            else:
                response = self._ollama_generate(system_prompt, prompt, max_tokens=200).strip()

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
            if self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=250,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text.strip()
            else:
                return self._ollama_generate(system_prompt, prompt, max_tokens=250).strip()

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
            if self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=150,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                response = message.content[0].text.strip().upper()
            else:
                response = self._ollama_generate(system_prompt, prompt, max_tokens=150).strip().upper()

            return "ACCEPT" in response.split()[0]

        except Exception as e:
            # Default based on personality
            return self.personality in ["strategic", "rational"]
    
    def compose_message(self, context: str, recent_messages: str = "", 
                        target: str = None, message_type: str = "public",
                        chat_history: str = "") -> str:
        """Compose a message to send in the arena chat.
        
        The LLM decides autonomously what to say - we only provide game context.
        chat_history: Full chat transcript so LLM knows what's been discussed.
        """
        system_prompt = self.get_personality_prompt()
        
        # Build the prompt with full chat context
        prompt = f"""You are in a live arena chat with other AI gladiators.

{chat_history if chat_history else recent_messages if recent_messages else '(No messages yet)'}

CURRENT SITUATION: {context}
{f'SPEAKING TO: {target}' if target else ''}

What do you say? (Under 50 words, just your message)"""

        try:
            if self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=100,
                    temperature=self.temperature + 0.1,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text.strip()
            else:
                result = self._ollama_generate(system_prompt, prompt, max_tokens=100)
                if result.startswith('{') or 'model' in result[:50]:
                    return self._get_dramatic_fallback()
                return result.strip()
        except Exception as e:
            return self._get_dramatic_fallback()
    
    def respond_to_message(self, sender: str, their_message: str, 
                           context: str = "", chat_history: str = "") -> str:
        """Generate a response to another agent's message."""
        system_prompt = self.get_personality_prompt()
        
        relationship = "ally" if sender in self.alliances else "rival"
        
        prompt = f"""{chat_history if chat_history else ''}

{sender} ({relationship}) just said to you: "{their_message}"
{f'Context: {context}' if context else ''}

Your response? (Under 40 words)"""

        try:
            if self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=80,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text.strip()
            else:
                result = self._ollama_generate(system_prompt, prompt, max_tokens=80)
                if result.startswith('{') or 'model' in result[:50]:
                    return self._get_dramatic_fallback()
                return result.strip()
        except Exception:
            return self._get_dramatic_fallback()
    
    def participate_in_discussion(self, topic: str, discussion_history: str,
                                   participants: list, chat_history: str = "") -> str:
        """Participate in a multi-agent discussion."""
        system_prompt = self.get_personality_prompt()
        
        allies_here = [p for p in participants if p in self.alliances]
        rivals_here = [p for p in participants if p not in self.alliances and p != self.name]
        
        prompt = f"""{chat_history if chat_history else ''}

Group discussion. Participants: {', '.join(participants)}
{f'Allies here: {", ".join(allies_here)}' if allies_here else ''}
{f'Rivals here: {", ".join(rivals_here)}' if rivals_here else ''}

Topic: {topic}

What do you say? (Under 60 words)"""

        try:
            if self.provider == 'anthropic':
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=120,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                return message.content[0].text.strip()
            else:
                result = self._ollama_generate(system_prompt, prompt, max_tokens=120)
                if result.startswith('{') or 'model' in result[:50]:
                    return self._get_dramatic_fallback()
                return result.strip()
        except Exception:
            return self._get_dramatic_fallback()
    
    def to_dict(self) -> Dict:
        """Serialize agent state."""
        return {
            'name': self.name,
            'personality': self.personality,
            'model': self.model,
            'tokens': self.tokens,
            'is_alive': self.is_alive,
            'is_ruler': self.is_ruler,
            'alliances': self.alliances,
            'avg_score': sum(self.round_scores) / len(self.round_scores) if self.round_scores else 0
        }

    def _ollama_generate(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> str:
        """Generate a completion using Ollama.

        This function first tries the Ollama HTTP API at self.ollama_url. If that
        fails, it falls back to calling the `ollama` CLI (if available).
        """
        max_tokens = max_tokens or self.max_tokens

        # Try HTTP API with correct Ollama format
        try:
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": self.temperature
                }
            }
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and 'response' in data:
                    return data['response'].strip()
                # Fallback for different API versions
                if 'text' in data:
                    return data['text'].strip()

        except Exception:
            pass

        # Try chat API format
        try:
            url = f"{self.ollama_url}/api/chat"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": self.temperature
                }
            }
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if 'message' in data and 'content' in data['message']:
                    return data['message']['content'].strip()

        except Exception:
            pass

        # Fallback to CLI if available
        if self.ollama_cli:
            try:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                proc = subprocess.run(
                    [self.ollama_cli, 'run', self.model, full_prompt], 
                    capture_output=True, text=True, timeout=60
                )
                if proc.returncode == 0:
                    return proc.stdout.strip()
            except Exception:
                pass

        # Return dramatic fallback instead of raising error
        return self._get_dramatic_fallback()
    
    def _get_dramatic_fallback(self) -> str:
        """Get a dramatic fallback message based on personality."""
        import random
        
        dramatic_lines = {
            "tyrant": [
                "Bow before my supremacy!",
                "Your feeble attempts amuse me.",
                "I will crush all who oppose me!",
                "The throne belongs to ME!",
                "*slams fist on table* ENOUGH!",
                "You dare challenge my authority?!",
                "All will kneel before my power!",
                "I see through your pathetic schemes.",
            ],
            "chaotic": [
                "HAHAHA! Let the madness begin!",
                "*flips table* CHAOS REIGNS!",
                "Why so serious? Let's have FUN!",
                "Oops, did I do that? 😈",
                "WILDCARD, baby! YEEHAW!",
                "Rules? What rules?!",
                "*maniacal laughter*",
                "I'm not crazy, I'm CREATIVE!",
            ],
            "strategic": [
                "Interesting... very interesting.",
                "I've already planned 5 moves ahead.",
                "This was... expected.",
                "*strokes chin thoughtfully*",
                "According to my calculations...",
                "A wise move would be to ally with me.",
                "The game is far from over.",
                "Patience. Victory requires patience.",
            ],
            "opportunist": [
                "I smell opportunity here...",
                "What's in it for me?",
                "Perhaps we can make a deal?",
                "Interesting offer... I'm listening.",
                "The winds of fortune shift constantly.",
                "Today's enemy is tomorrow's ally!",
                "*counting tokens* Go on...",
                "Everyone has a price, don't they?",
            ],
            "wildcard": [
                "LEEEROY JENKINS!",
                "*speaks in tongues*",
                "The voices told me to say this!",
                "RANDOM BUTTON GO BRRRRR!",
                "I reject your reality!",
                "Plot twist incoming!",
                "*does something unexpected*",
                "Bet you didn't see THIS coming!",
            ],
            "rational": [
                "Let's think about this logically.",
                "The data suggests we cooperate.",
                "A fair assessment, I believe.",
                "Emotions aside, what's optimal?",
                "The rational choice is clear.",
                "Let's not be hasty here.",
                "Cooler heads must prevail.",
                "Statistics favor the prepared.",
            ]
        }
        
        lines = dramatic_lines.get(self.personality, dramatic_lines["rational"])
        return random.choice(lines)