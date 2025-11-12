# utils/storage.py
"""Enhanced state storage with full game restoration."""
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

class StateStorage:
    """Manages game state persistence and restoration."""
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.current_file = self.storage_dir / "current_state.json"
        self.history_dir = self.storage_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        self.slots_dir = self.storage_dir / "slots"
        self.slots_dir.mkdir(exist_ok=True)
        self.active_slot: Optional[int] = None
        self.max_slots = 3

    def _timestamp(self) -> str:
        """Generate ISO timestamp."""
        return datetime.now().isoformat()

    def _slot_file(self, slot: int) -> Path:
        """Get file path for a save slot."""
        return self.slots_dir / f"slot_{slot}.json"

    def set_active_slot(self, slot: Optional[int]):
        """Set the currently active save slot."""
        if slot is None:
            self.active_slot = None
        else:
            if not (1 <= slot <= self.max_slots):
                raise ValueError(f"Slot must be between 1 and {self.max_slots}")
            self.active_slot = slot

    def save_state(self, state: Dict[str, Any]):
        """Save current game state."""
        state['timestamp'] = self._timestamp()
        
        # Save to current file
        with open(self.current_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        # Save to history
        round_num = state.get('round', 0)
        history_file = self.history_dir / f"round_{round_num:03d}.json"
        with open(history_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        # Save to active slot if set
        if self.active_slot:
            self.save_slot(self.active_slot, state)

    def load_state(self) -> Dict[str, Any]:
        """Load current game state."""
        if not self.current_file.exists():
            return {}
        with open(self.current_file, 'r') as f:
            return json.load(f)

    def save_slot(self, slot: int, state: Dict[str, Any]):
        """Save state to specific slot."""
        if not (1 <= slot <= self.max_slots):
            raise ValueError(f"Slot must be between 1 and {self.max_slots}")
        
        state['saved_at'] = self._timestamp()
        state['slot'] = slot
        
        slot_file = self._slot_file(slot)
        with open(slot_file, 'w') as f:
            json.dump(state, f, indent=2)

    def load_slot(self, slot: int) -> Dict[str, Any]:
        """Load state from specific slot."""
        if not (1 <= slot <= self.max_slots):
            raise ValueError(f"Slot must be between 1 and {self.max_slots}")
        
        slot_file = self._slot_file(slot)
        if not slot_file.exists():
            return {}
        
        with open(slot_file, 'r') as f:
            return json.load(f)

    def list_slots(self) -> Dict[int, Dict[str, Any]]:
        """List all save slots with metadata."""
        result = {}
        
        for s in range(1, self.max_slots + 1):
            f = self._slot_file(s)
            if f.exists():
                try:
                    with open(f, 'r') as fh:
                        data = json.load(fh)
                    
                    # Extract winner if game complete
                    winner = None
                    if data.get('season_complete'):
                        agents = data.get('agents', [])
                        alive = [a for a in agents if a.get('is_alive')]
                        if alive:
                            winner = max(alive, key=lambda a: a.get('tokens', 0))['name']
                    
                    result[s] = {
                        "exists": True,
                        "saved_at": data.get("saved_at") or data.get("timestamp"),
                        "round": data.get("round"),
                        "total_rounds": data.get("total_rounds"),
                        "winner": winner,
                        "alive_agents": len([a for a in data.get('agents', []) if a.get('is_alive')])
                    }
                except Exception as e:
                    result[s] = {
                        "exists": True,
                        "error": str(e)
                    }
            else:
                result[s] = {"exists": False}
        
        return result

    def delete_slot(self, slot: int):
        """Delete a save slot."""
        f = self._slot_file(slot)
        if f.exists():
            f.unlink()
        
        if self.active_slot == slot:
            self.active_slot = None

    def save_event(self, event: Dict[str, Any]):
        """Append event to event log."""
        events_file = self.storage_dir / "events.jsonl"
        event['timestamp'] = self._timestamp()
        
        with open(events_file, 'a') as f:
            f.write(json.dumps(event) + '\n')

    def load_events(self) -> list:
        """Load all events from log."""
        events_file = self.storage_dir / "events.jsonl"
        if not events_file.exists():
            return []
        
        events = []
        with open(events_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.load(line))
                    except:
                        pass
        
        return events

    def clear(self):
        """Clear current state (not slots)."""
        if self.current_file.exists():
            self.current_file.unlink()

    def export_game_log(self, output_file: str = "game_log.json"):
        """Export complete game history."""
        history_files = sorted(self.history_dir.glob("round_*.json"))
        
        complete_log = {
            "exported_at": self._timestamp(),
            "total_rounds": len(history_files),
            "rounds": []
        }
        
        for hist_file in history_files:
            with open(hist_file, 'r') as f:
                complete_log["rounds"].append(json.load(f))
        
        output_path = self.storage_dir / output_file
        with open(output_path, 'w') as f:
            json.dump(complete_log, f, indent=2)
        
        return output_path

storage = StateStorage()