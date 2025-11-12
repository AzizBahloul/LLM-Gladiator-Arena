#core/evaluator.py

"""Task evaluation and scoring."""
import re
from typing import Dict, Any
from utils.logger import logger

class TaskEvaluator:
    """Evaluates task performance and assigns scores."""
    
    def __init__(self):
        self.round_scores = {}
    
    def evaluate_code_task(self, response: str, test_cases: list) -> float:
        """Evaluate code optimization task."""
        score = 0.0
        
        # Extract code from response
        code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        if not code_match:
            # Try without python tag
            code_match = re.search(r'```\n(.*?)\n```', response, re.DOTALL)
        
        if not code_match:
            return 0.0
        
        code = code_match.group(1)
        
        # Check for basic structure (simplified evaluation)
        if 'def ' in code:
            score += 0.3
        if 'return' in code:
            score += 0.2
        
        # Check complexity (naive)
        if len(code) < 500:  # Bonus for concise solutions
            score += 0.2
        
        # Check for optimization indicators
        if any(keyword in code.lower() for keyword in ['cache', 'memo', 'optimize', 'efficient']):
            score += 0.3
        
        return min(score, 1.0)
    
    def evaluate_logic_task(self, response: str, expected_pattern: str) -> float:
        """Evaluate logic puzzle solution."""
        score = 0.0
        
        # Check for answer format
        if expected_pattern.lower() in response.lower():
            score += 0.5
        
        # Check for reasoning
        reasoning_indicators = ['because', 'therefore', 'thus', 'so', 'since']
        if any(indicator in response.lower() for indicator in reasoning_indicators):
            score += 0.3
        
        # Check for completeness
        if len(response) > 100:  # Detailed answer
            score += 0.2
        
        return min(score, 1.0)
    
    def evaluate_creative_task(self, response: str, min_length: int = 50) -> float:
        """Evaluate creative challenge."""
        score = 0.0
        
        # Length check
        if len(response) >= min_length:
            score += 0.3
        
        # Creativity indicators (very simplified)
        creative_words = ['imagine', 'unique', 'innovative', 'novel', 'creative']
        if any(word in response.lower() for word in creative_words):
            score += 0.2
        
        # Structure
        if '\n\n' in response:  # Multiple paragraphs
            score += 0.2
        
        # Engagement
        if any(punct in response for punct in ['!', '?', '—']):
            score += 0.3
        
        return min(score, 1.0)
    
    def evaluate(self, task_type: str, response: str, task_data: Dict[str, Any]) -> float:
        """Main evaluation router."""
        if task_type == "code_optimization":
            score = self.evaluate_code_task(response, task_data.get('test_cases', []))
        elif task_type == "logic_puzzle":
            score = self.evaluate_logic_task(response, task_data.get('expected', ''))
        elif task_type == "creative_challenge":
            score = self.evaluate_creative_task(response, task_data.get('min_length', 50))
        else:
            score = 0.5  # Default
        
        # Add randomness for drama (±20%)
        import random
        score = max(0, min(1.0, score + random.uniform(-0.15, 0.15)))
        
        return round(score, 2)
    
    def calculate_round_rewards(self, scores: Dict[str, float], total_tokens: int = 30) -> Dict[str, int]:
        """Calculate token rewards based on scores."""
        if not scores:
            return {}
        
        # Top performer gets 40%, second gets 30%, rest split remaining
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        rewards = {}
        
        if len(sorted_agents) >= 1:
            rewards[sorted_agents[0][0]] = int(total_tokens * 0.4)
        if len(sorted_agents) >= 2:
            rewards[sorted_agents[1][0]] = int(total_tokens * 0.3)
        
        # Split remaining among others
        remaining = total_tokens - sum(rewards.values())
        other_agents = sorted_agents[2:]
        if other_agents:
            per_agent = remaining // len(other_agents)
            for agent, _ in other_agents:
                rewards[agent] = per_agent
        
        return rewards
    
    def identify_bottom_performers(self, scores: Dict[str, float], count: int = 2) -> list:
        """Find agents for elimination round."""
        sorted_agents = sorted(scores.items(), key=lambda x: x[1])
        return [agent for agent, _ in sorted_agents[:count]]

evaluator = TaskEvaluator()