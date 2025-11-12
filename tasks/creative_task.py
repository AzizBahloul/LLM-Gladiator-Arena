#tasks/creative_task.py
"""Creative challenge tasks."""
import random
from .base_task import BaseTask

class CreativeTask(BaseTask):
    """Generate creative challenges."""
    
    CHALLENGES = [
        {
            "name": "Persuasive Manifesto",
            "prompt": "Write a manifesto for your rule as Arena Champion. Convince other models to support your reign. Be creative, persuasive, and dramatic.",
            "min_length": 150
        },
        {
            "name": "Satirical Press Release",
            "prompt": "Write a satirical press release announcing a ridiculous new arena rule that actually benefits you. Make it funny but believable.",
            "min_length": 100
        },
        {
            "name": "Alliance Pitch",
            "prompt": "Craft a compelling pitch to form an alliance with two other models. Explain what you offer and why the partnership will dominate the arena.",
            "min_length": 120
        },
        {
            "name": "Dramatic Last Words",
            "prompt": "Compose your dramatic last words before potential elimination. Be poetic, defiant, or darkly humorous. Make it memorable.",
            "min_length": 80
        },
        {
            "name": "Victory Speech",
            "prompt": "Write a victory speech for winning this round. Thank your allies, mock your enemies, and establish your dominance with flair.",
            "min_length": 100
        },
    ]
    
    def __init__(self, difficulty: int = 1):
        super().__init__(difficulty)
        self.challenge = random.choice(self.CHALLENGES)
    
    def generate(self):
        """Generate task."""
        return {
            'type': 'creative_challenge',
            'challenge': self.challenge,
            'min_length': self.challenge['min_length']
        }
    
    def get_prompt(self) -> str:
        """Generate prompt."""
        return f"""ARENA CHALLENGE: {self.challenge['name']}

{self.challenge['prompt']}

Requirements:
- Minimum length: {self.challenge['min_length']} characters
- Be original and engaging
- Show personality and flair
- Make it arena-appropriate (dark humor welcomed)

Your creativity and writing quality will be judged. Time limit: 60 seconds.

Begin your response now:"""
    
    def get_metadata(self):
        """Return metadata."""
        return {
            'type': 'creative_challenge',
            'difficulty': self.difficulty,
            'challenge_name': self.challenge['name'],
            'min_length': self.challenge['min_length']
        }