#!/usr/bin/env python3
"""
GUI Launcher for LLM Gladiator Arena
Run the arena with the terminal GUI interface.
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gui.arena_gui import ArenaGUI
from core.orchestrator import ArenaOrchestrator
import yaml

def load_config():
    """Load the configuration file."""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def main():
    """Launch the GUI version of the arena."""
    try:
        from textual.app import App
    except ImportError:
        print("❌ Textual library not installed.")
        print("   Install with: pip install textual")
        sys.exit(1)
    
    print("🏛️  Loading LLM Gladiator Arena GUI...")
    
    # Load configuration
    config = load_config()
    
    # Create GUI app
    app = ArenaGUI()
    
    # The orchestrator will be created after GUI starts
    # and will run in the background
    print("✓ GUI ready. Starting...")
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  GUI closed by user")
    except Exception as e:
        print(f"\n\n❌ GUI error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
