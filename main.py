# main.py
"""Enhanced entry point with full state restoration and Ollama support.

This file now performs two convenience tasks at startup:
 - Ensures Python dependencies from `requirements.txt` are installed into
     the currently active Python interpreter/virtualenv.
 - Provides improved checks for the Ollama server and will attempt to
     start `ollama serve` automatically if the `ollama` binary exists.

The approach is conservative: package installation uses the active
interpreter (sys.executable -m pip install -r requirements.txt). System
package installs (like the Ollama binary) are not attempted automatically
because they require elevated privileges and platform-specific steps.
"""

import os
import sys
import subprocess
import shutil
import platform
import time
from pathlib import Path
from typing import Dict, Any, List
from utils.logger import logger
from utils.storage import storage
from utils.gpu_utils import gpu_manager
from utils.model_selector import select_models_cli, get_models_for_gpu

def pull_multiple_models(models: List[str], ollama_url: str = 'http://localhost:11434', auto_pull: bool = False):
    """Pull multiple models, showing which ones need to be downloaded.
    
    Args:
        models: List of model names to check/pull
        ollama_url: Ollama server URL
        auto_pull: If True, skip confirmation prompt
    """
    import requests
    
    # Check which models are already installed
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        installed_models = []
        if response.status_code == 200:
            model_list = response.json().get('models', [])
            installed_models = [m['name'] for m in model_list]
    except:
        installed_models = []
    
    # Filter to only models that need pulling
    models_to_pull = [m for m in models if m not in installed_models]
    
    if not models_to_pull:
        print("\n✓ All required models are already installed!")
        return True
    
    print(f"\n📥 Need to pull {len(models_to_pull)} model(s):")
    for model in models_to_pull:
        print(f"   - {model}")
    
    # Always ask for confirmation unless auto_pull is explicitly True
    if not auto_pull:
        print("\n⚠️  This may take several minutes depending on model sizes...")
        print(f"    Total models to download: {len(models_to_pull)}")
        choice = input("\nProceed with download? (y/n): ").strip().lower()
        
        if choice != 'y':
            print("\n❌ Cannot start without required models")
            print("\n💡 Pull them manually with:")
            for model in models_to_pull:
                print(f"   ollama pull {model}")
            return False
    
    # Pull each model
    print("\n" + "="*70)
    print("📦 DOWNLOADING MODELS")
    print("="*70 + "\n")
    
    for i, model in enumerate(models_to_pull, 1):
        print(f"[{i}/{len(models_to_pull)}] Pulling {model}...")
        if not pull_ollama_model(model, ollama_url):
            print(f"\n❌ Failed to pull {model}")
            return False
        print()  # Add spacing between downloads
    
    print("="*70)
    print("✓ All models downloaded successfully!")
    print("="*70 + "\n")
    return True


def pull_ollama_model(model_name: str, ollama_url: str = 'http://localhost:11434') -> bool:
    """Pull an Ollama model if not already present with progress display."""
    import requests
    import json
    
    try:
        # Use the pull API endpoint
        response = requests.post(
            f"{ollama_url}/api/pull",
            json={"name": model_name},
            stream=True,
            timeout=600  # 10 minute timeout for large models
        )
        
        if response.status_code == 200:
            last_status = ""
            # Stream the progress
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        status = data.get('status', '')
                        
                        # Show download progress with better formatting
                        if 'total' in data and 'completed' in data:
                            total = data['total']
                            completed = data['completed']
                            percent = (completed / total * 100) if total > 0 else 0
                            
                            # Convert to MB/GB for readability
                            completed_mb = completed / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            
                            if total_mb > 1024:
                                # Show in GB
                                completed_gb = completed_mb / 1024
                                total_gb = total_mb / 1024
                                print(f"\r   Progress: {percent:.1f}% ({completed_gb:.2f}/{total_gb:.2f} GB)", end='', flush=True)
                            else:
                                # Show in MB
                                print(f"\r   Progress: {percent:.1f}% ({completed_mb:.1f}/{total_mb:.1f} MB)", end='', flush=True)
                        elif status and status != last_status:
                            print(f"\r   {status}...".ljust(70), end='', flush=True)
                            last_status = status
                    except:
                        pass
            
            print(f"\r   ✓ {model_name} downloaded successfully!".ljust(70))
            return True
        else:
            print(f"\n   ❌ Failed to pull model. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n   ❌ Error pulling model: {e}")
        return False

def check_environment(config: dict):
    """Check required environment and services."""
    # local import because requests is a third-party package and may be
    # installed at runtime by ensure_requirements_installed()
    import requests

    provider = config['api']['provider']
    
    if provider == "anthropic":
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
    
    elif provider == "ollama":
        # Check if Ollama is running
        ollama_url = config['api'].get('ollama_url', 'http://localhost:11434')
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                # Check available models
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                # Check if required model exists
                required_model = config['api']['model']
                if required_model not in model_names:
                    print(f"\n⚠️  Model '{required_model}' not installed")
                    
                    # Ask user if they want to pull it now
                    print("\nWould you like to pull this model now? (y/n)")
                    choice = input("> ").strip().lower()
                    
                    if choice == 'y':
                        if pull_ollama_model(required_model, ollama_url):
                            pass  # Success message shown by pull function
                        else:
                            print("❌ Failed to pull model. Please pull manually:")
                            print(f"   ollama pull {required_model}")
                            sys.exit(1)
                    else:
                        print(f"   Available models: {', '.join(model_names[:5])}")
                        print("\nYou can pull the model manually with:")
                        print(f"   ollama pull {required_model}")
                        print("\nOr edit config.yaml to use an existing model")
                        sys.exit(1)
            else:
                print(f"\n❌ Ollama server returned status {response.status_code}")
                sys.exit(1)
        
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to Ollama server at {ollama_url}")
            # Try to locate the Ollama binary and offer to start it
            ollama_exec = shutil.which('ollama')
            if ollama_exec:
                print(f"Found Ollama executable at: {ollama_exec}")
                print("Attempting to start `ollama serve` in the background...")
                try:
                    log_path = Path('logs/ollama_serve.log')
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(log_path, 'ab') as f:
                        # Start in background. We don't block the main process.
                        proc = subprocess.Popen([ollama_exec, 'serve'],
                                                stdout=f,
                                                stderr=subprocess.STDOUT,
                                                stdin=subprocess.DEVNULL)
                    # Give it a moment to boot and re-check
                    time.sleep(3)
                    try:
                        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
                        if response.status_code == 200:
                            print("✓ Ollama server started successfully")
                            return
                    except Exception:
                        pass

                    print("Could not verify Ollama after starting it. Check logs/ollama_serve.log")
                    print("If the server failed to start, try: ollama serve")
                    sys.exit(1)

                except Exception as e:
                    print(f"❌ Failed to start Ollama automatically: {e}")
                    print("Please start it manually: ollama serve")
                    sys.exit(1)

            else:
                print("\nPlease ensure Ollama is installed and running:")
                print("  1. Install: https://ollama.ai/download")
                print("     - For Debian/Ubuntu you can use the .deb from the site")
                print("     - For Arch/Alpine/Fedora use the distribution package or the installer")
                print("  2. Start: ollama serve")
                print("  3. Or update 'ollama_url' in config.yaml")
                sys.exit(1)
        
        except Exception as e:
            print(f"❌ Error checking Ollama: {e}")
            sys.exit(1)

def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration file."""
    path = Path(config_path)
    if not path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    # local import because yaml is a third-party package that may be
    # installed at runtime by ensure_requirements_installed()
    import yaml

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def ensure_requirements_installed(requirements_path: str = 'requirements.txt') -> None:
    """Ensure pip packages from requirements.txt are installed.

    This uses the currently active Python interpreter (sys.executable) to
    run `-m pip install -r requirements.txt`. It's idempotent and safe
    for virtual environments. If installation fails, the function exits
    with non-zero status after printing helpful diagnostics.
    """
    req = Path(requirements_path)
    if not req.exists():
        print(f"⚠️  requirements file not found: {requirements_path}. Skipping package install check.")
        return

    print(f"Checking Python packages from {requirements_path}...", end='', flush=True)

    # Use the same Python interpreter to run pip to target the active venv
    pip_cmd = [sys.executable, '-m', 'pip', 'install', '-q', '-r', str(req)]

    try:
        # Run pip with quiet flag and capture output (don't show unless there's an error)
        proc = subprocess.run(pip_cmd, check=True, capture_output=True, text=True)
        if proc.returncode == 0:
            print(" ✓")
    except subprocess.CalledProcessError as e:
        print(" ❌")
        print("\n❌ Failed to install Python dependencies.")
        if e.stderr:
            print(f"Error: {e.stderr}")
        print("\nYou can try to run the following command manually in your venv:")
        print(f"  {sys.executable} -m pip install -r {requirements_path}")
        sys.exit(1)


def _print_env_summary():
    print(f"Python: {sys.executable} ({platform.system()} {platform.machine()})")
    venv = os.environ.get('VIRTUAL_ENV') or os.environ.get('CONDA_PREFIX')
    if venv:
        print(f"Active virtualenv: {venv}")

def display_banner():
    """Display enhanced ASCII banner."""
    print("\n" + "="*70)
    print("""
 ╔══════════════════════════════════════════════════════════════╗
 ║                                                              ║
 ║             🏛️  LLM GLADIATOR ARENA  🏛️                      ║
 ║                                                              ║
 ║          Where AI Agents Fight for Survival                 ║
 ║                                                              ║
 ║          Tokens. Treachery. Triumph.                        ║
 ║                                                              ║
 ╚══════════════════════════════════════════════════════════════╝
    """)
    print("="*70 + "\n")

def prompt_gui_mode():
    """Ask user if they want to use GUI mode."""
    print("\n" + "="*70)
    print("DISPLAY MODE SELECTION")
    print("="*70)
    print("\n1. 🖥️  Terminal GUI Mode (Recommended)")
    print("   Modern, interactive terminal interface with live updates")
    print("\n2. 📜 Classic Console Mode")
    print("   Traditional text-based output\n")
    
    while True:
        choice = input("Select mode (1 or 2): ").strip()
        if choice == '1':
            return True
        elif choice == '2':
            return False
        else:
            print("Invalid choice. Please enter 1 or 2.")

def main():
    """Main entry point with full state management."""
    display_banner()
    
    # Ensure Python dependencies are installed into the active interpreter/venv
    ensure_requirements_installed('requirements.txt')

    # Load config
    config = load_config()

    # Check environment (will verify Ollama / API keys)
    print("Checking environment...", end='', flush=True)
    check_environment(config)
    print(" ✓")
    
    # Initialize GPU (silent, already detected at import)
    gpu_info = gpu_manager.get_info()
    gpu_capacity = gpu_manager.estimate_model_capacity()
    
    if gpu_info['available']:
        print(f"\n✓ GPU: {gpu_info['name']} ({gpu_info['device']})")
        if gpu_info['memory_gb']:
            print(f"  Memory: {gpu_info['memory_gb']:.2f} GB")
        print(f"  Can run {gpu_capacity['max_models']} models simultaneously")
    else:
        print("\n  Using CPU mode")
        print("  ⚠️  Performance will be limited")
    
    # Model selection for agents
    if config['api']['provider'] == 'ollama':
        print("\n" + "="*70)
        print("🏛️  MODEL ASSIGNMENT FOR GLADIATORS")
        print("="*70)
        
        gpu_memory = gpu_capacity.get('memory_gb', 4.0) if gpu_info['available'] else 4.0
        
        # Interactive model selection with arrow keys
        selected_models = select_models_cli(gpu_memory, config['game']['initial_agents'])
        
        if not selected_models:
            # Fallback: use auto-selected models
            print("\n⚠️  Using automatic model selection...")
            suggested = gpu_capacity.get('suggested_models', ['llama3.2:1b'])
            selected_models = suggested[:config['game']['initial_agents']]
        
        # Assign models to agents in config
        for i, agent_config in enumerate(config['agents']):
            agent_config['model'] = selected_models[i % len(selected_models)]
        
        print("\n📋 Final Agent Model Assignments:")
        for agent_config in config['agents']:
            print(f"   {agent_config['name']:15s} → {agent_config['model']}")
        
        # Pull required models
        print("\n" + "="*70)
        if not pull_multiple_models(selected_models, config['api'].get('ollama_url', 'http://localhost:11434')):
            print("\n❌ Model preparation failed")
            sys.exit(1)
    
    print()
    
    # Create directories
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # Ask for GUI mode
    use_gui = prompt_gui_mode()
    
    # Show intro animation
    logger.show_intro_animation()
    
    # Slot selection loop
    restore_state = None
    while True:
        choice = logger.prompt_slot_menu(storage)
        
        if choice.lower() == 'n':
            # New game, no save
            storage.set_active_slot(None)
            print("✓ Starting new game (no save slot)")
            break
        
        elif choice.lower() == 'q':
            print("\n👋 Goodbye. The arena awaits your return.\n")
            sys.exit(0)
        
        elif choice.startswith('d') and len(choice) == 2 and choice[1].isdigit():
            # Delete slot
            slot = int(choice[1])
            if 1 <= slot <= storage.max_slots:
                storage.delete_slot(slot)
                print(f"✓ Deleted slot {slot}")
            else:
                print(f"❌ Invalid slot: {slot}")
            continue
        
        elif choice.isdigit():
            # Load/start in slot
            slot = int(choice)
            if 1 <= slot <= storage.max_slots:
                saved = storage.load_slot(slot)
                
                if saved:
                    # Restore existing game
                    storage.set_active_slot(slot)
                    restore_state = saved
                    print(f"✓ Loaded slot {slot} (Round {saved.get('round')}, "
                          f"{len([a for a in saved.get('agents', []) if a.get('is_alive')])} alive)")
                    break
                else:
                    # Start new game in this slot
                    print(f"✓ Slot {slot} is empty. Starting new game here.")
                    storage.set_active_slot(slot)
                    break
            else:
                print(f"❌ Invalid slot. Choose 1-{storage.max_slots}")
                continue
        
        else:
            print("❌ Invalid choice. Try again.")
            continue
    
    # Import orchestrator (after config loaded)
    from core.orchestrator import ArenaOrchestrator
    
    # Initialize GUI if requested
    gui_app = None
    if use_gui:
        try:
            from gui.arena_gui import ArenaGUI
            print("\n🖥️  Initializing GUI mode...")
        except ImportError as e:
            print(f"\n⚠️  Failed to load GUI: {e}")
            print("   Falling back to console mode")
            use_gui = False
    
    # Initialize arena
    print("\nInitializing arena...")
    
    if use_gui:
        # Run in GUI mode
        from gui.arena_gui import ArenaGUI
        
        print("✓ Arena ready\n")
        print("="*70)
        print("LAUNCHING GUI - THE GAMES BEGIN")
        print("="*70 + "\n")
        
        # Create GUI and pass config and restore state
        gui_app = ArenaGUI()
        gui_app.config = config
        gui_app.restore_state = restore_state
        
        # Run GUI - it will create the orchestrator after mounting
        try:
            gui_app.run()
        except KeyboardInterrupt:
            print("\n\n⚠️  Arena interrupted by user")
            if hasattr(gui_app, 'orchestrator') and gui_app.orchestrator:
                print("Saving current state...")
                gui_app.orchestrator._save_round_state()
                print("✓ State saved. You can resume from this point.")
    else:
        # Console mode
        arena = ArenaOrchestrator(config, restore_state=restore_state)
        
        print("✓ Arena ready\n")
        print("="*70)
        print("THE GAMES BEGIN")
        print("="*70 + "\n")
        
        # Run the arena
        try:
            arena.run_season()
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Arena interrupted by user")
            print("Saving current state...")
            arena._save_round_state()
            print("✓ State saved. You can resume from this point.")
        
        except Exception as e:
            print(f"\n\n❌ Arena error: {e}")
            print("\nAttempting to save state...")
            try:
                arena._save_round_state()
                print("✓ Emergency save successful")
            except:
                print("❌ Could not save state")
            
            import traceback
            traceback.print_exc()
        
        finally:
            print("\n" + "="*70)
            print("ARENA SESSION ENDED")
            print("="*70)
            
            if storage.active_slot:
                print(f"Game saved to slot {storage.active_slot}")
            
            print("\nCheck logs/ for full history")
            print("Check data/ for save states")
            print("\n👋 Until next time, gladiator.\n")

if __name__ == "__main__":
    main()