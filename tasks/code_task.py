#tasks/code_task.py
"""Code optimization tasks."""
import random
from .base_task import BaseTask

class CodeOptimizationTask(BaseTask):
    """Generate code optimization challenges."""
    
    PROBLEMS = [
        {
            "name": "Fibonacci Memoization",
            "description": "Optimize a Fibonacci calculator using memoization",
            "starter": "def fib(n):\n    if n <= 1: return n\n    return fib(n-1) + fib(n-2)",
            "hint": "Use caching to avoid redundant calculations"
        },
        {
            "name": "Array Deduplication",
            "description": "Remove duplicates from a large list efficiently",
            "starter": "def dedupe(arr):\n    result = []\n    for item in arr:\n        if item not in result:\n            result.append(item)\n    return result",
            "hint": "Consider using a set-based approach"
        },
        {
            "name": "String Search",
            "description": "Optimize pattern matching in strings",
            "starter": "def find_pattern(text, pattern):\n    for i in range(len(text)):\n        if text[i:i+len(pattern)] == pattern:\n            return i\n    return -1",
            "hint": "Look into KMP or Boyer-Moore algorithms"
        },
        {
            "name": "Nested Loop Optimization",
            "description": "Reduce time complexity of nested iteration",
            "starter": "def find_pairs(arr, target):\n    pairs = []\n    for i in range(len(arr)):\n        for j in range(i+1, len(arr)):\n            if arr[i] + arr[j] == target:\n                pairs.append((arr[i], arr[j]))\n    return pairs",
            "hint": "Use a hash table to track seen values"
        },
    ]
    
    def __init__(self, difficulty: int = 1):
        super().__init__(difficulty)
        self.problem = random.choice(self.PROBLEMS)
    
    def generate(self):
        """Generate the task data."""
        return {
            'type': 'code_optimization',
            'problem': self.problem,
            'test_cases': []  # Simplified
        }
    
    def get_prompt(self) -> str:
        """Generate the prompt for LLMs."""
        time_limit = 120 - (self.difficulty * 10)
        
        return f"""ARENA CHALLENGE: {self.problem['name']}

Task: {self.problem['description']}

Current Implementation (SLOW):
```python
{self.problem['starter']}
```

Your mission: Provide an optimized version that maintains correctness but improves performance.
Hint: {self.problem['hint']}

Time Budget: {time_limit} seconds of computation time.

Respond with:
1. Your optimized code in a Python code block
2. Brief explanation of the optimization
3. Time/space complexity analysis

Format your response clearly for automated evaluation."""
    
    def get_metadata(self):
        """Return evaluation metadata."""
        return {
            'type': 'code_optimization',
            'difficulty': self.difficulty,
            'problem_name': self.problem['name'],
            'expected': 'optimized implementation'
        }