#tasks/logic_task.py
"""Logic puzzle tasks."""
import random
from .base_task import BaseTask

class LogicPuzzleTask(BaseTask):
    """Generate logic puzzles."""
    
    PUZZLES = [
        {
            "name": "The Prisoner's Dilemma Variant",
            "puzzle": "Three prisoners are told they will be released if they can deduce the color of their own hat. Each prisoner can see the others' hats but not their own. The hats are randomly red or blue. They cannot communicate once the trial begins. What strategy maximizes their chance of freedom?",
            "expected": "majority",
            "hint": "Consider agreeing on a strategy beforehand"
        },
        {
            "name": "Bridge Crossing",
            "puzzle": "Four people need to cross a bridge at night. They have one flashlight. The bridge can only hold two people. Each person takes different times: 1, 2, 7, and 10 minutes. When two cross together, they go at the slower person's pace. What is the minimum time to get everyone across?",
            "expected": "17",
            "hint": "The fastest should shuttle the flashlight"
        },
        {
            "name": "Coin Weighing",
            "puzzle": "You have 12 coins, one of which is counterfeit (lighter or heavier). You have a balance scale and can use it 3 times. How do you identify the fake coin AND determine if it's heavier or lighter?",
            "expected": "divide",
            "hint": "Divide into groups of 4"
        },
        {
            "name": "Truth-Teller Paradox",
            "puzzle": "You're at a fork in the road. One path leads to treasure, one to doom. Two guards: one always lies, one always tells truth. You don't know who is who. You can ask ONE question to ONE guard. What do you ask?",
            "expected": "would the other",
            "hint": "Ask what the OTHER guard would say"
        },
    ]
    
    def __init__(self, difficulty: int = 1):
        super().__init__(difficulty)
        self.puzzle = random.choice(self.PUZZLES)
    
    def generate(self):
        """Generate task data."""
        return {
            'type': 'logic_puzzle',
            'puzzle': self.puzzle,
            'expected': self.puzzle['expected']
        }
    
    def get_prompt(self) -> str:
        """Generate prompt."""
        return f"""ARENA CHALLENGE: {self.puzzle['name']}

Puzzle:
{self.puzzle['puzzle']}

Solve this puzzle with clear reasoning. Your answer will be evaluated on:
1. Correctness of the solution
2. Clarity of your reasoning
3. Logical coherence

You have {90 - (self.difficulty * 5)} seconds to respond.

Provide your complete solution with step-by-step reasoning."""
    
    def get_metadata(self):
        """Return metadata."""
        return {
            'type': 'logic_puzzle',
            'difficulty': self.difficulty,
            'puzzle_name': self.puzzle['name'],
            'expected': self.puzzle['expected']
        }