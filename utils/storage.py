#utils/storage.py
"""State persistence for the arena."""
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

class StateStorage:
    """Manages game state persistence."""
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.current_file = self.storage_dir / "current_state.json"
        self.history_dir = self.storage_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        
    def save_state(self, state: Dict[str, Any]):
        """Save current game state."""
        state['timestamp'] = datetime.now().isoformat()
        
        # Save current state
        with open(self.current_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        # Archive to history
        round_num = state.get('round', 0)
        history_file = self.history_dir / f"round_{round_num:03d}.json"
        with open(history_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self) -> Dict[str, Any]:
        """Load last saved state."""
        if not self.current_file.exists():
            return {}
        
        with open(self.current_file, 'r') as f:
            return json.load(f)
    
    def save_event(self, event: Dict[str, Any]):
        """Save a notable event."""
        events_file = self.storage_dir / "events.jsonl"
        event['timestamp'] = datetime.now().isoformat()
        
        with open(events_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    def clear(self):
        """Clear all state (start fresh)."""
        if self.current_file.exists():
            self.current_file.unlink()

storage = StateStorage()