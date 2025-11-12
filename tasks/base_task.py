#tasks/base_task.py
"""Base task interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import random

class BaseTask(ABC):
    """Base class for all arena tasks."""
    
    def __init__(self, difficulty: int = 1):
        self.difficulty = difficulty
        self.task_type = self.__class__.__name__
    
    @abstractmethod
    def generate(self) -> Dict[str, Any]:
        """Generate a task with prompt and metadata."""
        pass
    
    @abstractmethod
    def get_prompt(self) -> str:
        """Get the prompt to send to LLMs."""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get task metadata for evaluation."""
        return {
            'type': self.task_type,
            'difficulty': self.difficulty
        }


class TaskGenerator:
    """Generates varied tasks for rounds."""
    
    def __init__(self):
        self.task_classes = []
        self.round_count = 0
    
    def register_task(self, task_class):
        """Register a task type."""
        self.task_classes.append(task_class)
    
    def generate_round_task(self) -> BaseTask:
        """Generate a task for the current round."""
        self.round_count += 1
        
        # Increase difficulty every 5 rounds
        difficulty = 1 + (self.round_count // 5)
        
        # Pick random task type
        task_class = random.choice(self.task_classes)
        return task_class(difficulty=difficulty)