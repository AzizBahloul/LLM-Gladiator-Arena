#main.py
"""
LLM Gladiator Arena - Main Entry Point

An autonomous arena where LLM agents compete for resources, form alliances,
stage coups, and battle for supremacy. No human interaction required - 
just watch the drama unfold.
"""

import os
import sys
import yaml
from pathlib import Path

def check_environment():
    """Verify environment is properly configured."""
    required_env = ['ANTHROPIC_API_KEY']
    
    missing = []
    for env_var in required_env:
        if not os.getenv(env_var):
            missing.append(env_var)
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set them:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("\nOr create a .env file in the project root.")
        sys.exit(1)
    
    print("✅ Environment configured correctly")

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML."""
    path = Path(config_path)
    
    if not path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"✅ Configuration loaded from {config_path}")
    return config

def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("🏛️  LLM GLADIATOR ARENA  🏛️")
    print("Where AI agents fight for tokens, glory, and survival")
    print("="*70 + "\n")
    
    # Setup
    check_environment()
    config = load_config()
    
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    print("\n🔧 Initializing arena systems...")
    
    # Import here to avoid loading before env check
    from core.orchestrator import ArenaOrchestrator
    
    # Create orchestrator
    arena = ArenaOrchestrator(config)
    
    print("✅ Arena ready!\n")
    print("🎬 Starting autonomous season...")
    print("   (No user interaction needed - sit back and watch)")
    print("\n" + "="*70 + "\n")
    
    # Run the show
    try:
        arena.run_season()
    except KeyboardInterrupt:
        print("\n\n⚠️  Arena interrupted by user")
        print("Saving current state...")
        arena._save_round_state()
    except Exception as e:
        print(f"\n\n❌ Arena error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n" + "="*70)
        print("Arena session ended. Check logs/ for full history.")
        print("="*70 + "\n")

if __name__ == "__main__":
    main()