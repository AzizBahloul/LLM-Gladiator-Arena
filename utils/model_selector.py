# utils/model_selector.py
"""Interactive model selector with arrow key navigation for Ollama models."""
import sys
import tty
import termios
from typing import List, Dict, Any, Tuple

# Comprehensive Ollama model database with memory requirements (based on official Ollama library)
# Memory estimates based on parameter count and quantization (typically Q4_K_M for Ollama)
MODEL_DATABASE = {
    # === TINY MODELS (< 1GB VRAM) ===
    "smollm2:135m": {"size": "135M", "ram_gb": 0.3, "category": "tiny", "type": "general", "quality": 2},
    "smollm:135m": {"size": "135M", "ram_gb": 0.3, "category": "tiny", "type": "general", "quality": 2},
    "smollm2:360m": {"size": "360M", "ram_gb": 0.5, "category": "tiny", "type": "general", "quality": 3},
    "smollm:360m": {"size": "360M", "ram_gb": 0.5, "category": "tiny", "type": "general", "quality": 3},
    "qwen2.5:0.5b": {"size": "0.5B", "ram_gb": 0.7, "category": "tiny", "type": "general", "quality": 4},
    
    # === SMALL MODELS (1-2GB VRAM) ===
    "tinyllama:1.1b": {"size": "1.1B", "ram_gb": 1.0, "category": "small", "type": "general", "quality": 4},
    "tinydolphin:1.1b": {"size": "1.1B", "ram_gb": 1.0, "category": "small", "type": "general", "quality": 4},
    "llama3.2:1b": {"size": "1B", "ram_gb": 1.0, "category": "small", "type": "general", "quality": 6},
    "qwen2.5:1.5b": {"size": "1.5B", "ram_gb": 1.3, "category": "small", "type": "general", "quality": 5},
    "qwen2.5-coder:1.5b": {"size": "1.5B", "ram_gb": 1.3, "category": "small", "type": "code", "quality": 6},
    "deepseek-r1:1.5b": {"size": "1.5B", "ram_gb": 1.4, "category": "small", "type": "reasoning", "quality": 7},
    "deepscaler:1.5b": {"size": "1.5B", "ram_gb": 1.4, "category": "small", "type": "reasoning", "quality": 7},
    "opencoder:1.5b": {"size": "1.5B", "ram_gb": 1.3, "category": "small", "type": "code", "quality": 6},
    "deepcoder:1.5b": {"size": "1.5B", "ram_gb": 1.3, "category": "small", "type": "code", "quality": 6},
    "stablelm2:1.6b": {"size": "1.6B", "ram_gb": 1.4, "category": "small", "type": "general", "quality": 5},
    "smollm2:1.7b": {"size": "1.7B", "ram_gb": 1.5, "category": "small", "type": "general", "quality": 5},
    "smollm:1.7b": {"size": "1.7B", "ram_gb": 1.5, "category": "small", "type": "general", "quality": 5},
    "qwen:1.8b": {"size": "1.8B", "ram_gb": 1.5, "category": "small", "type": "general", "quality": 5},
    "moondream:1.8b": {"size": "1.8B", "ram_gb": 1.6, "category": "small", "type": "vision", "quality": 5},
    
    # === MEDIUM-SMALL MODELS (2-3GB VRAM) ===
    "gemma2:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "general", "quality": 7},
    "gemma:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "general", "quality": 6},
    "granite3.3:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "general", "quality": 7},
    "granite3.2:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "general", "quality": 7},
    "granite3-dense:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "general", "quality": 7},
    "granite3.1-dense:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "general", "quality": 7},
    "codegemma:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "code", "quality": 6},
    "qwen3:2b": {"size": "2B", "ram_gb": 1.8, "category": "medium-small", "type": "general", "quality": 7},
    "phi:2.7b": {"size": "2.7B", "ram_gb": 2.2, "category": "medium-small", "type": "general", "quality": 7},
    "dolphin-phi:2.7b": {"size": "2.7B", "ram_gb": 2.2, "category": "medium-small", "type": "general", "quality": 7},
    
    # === MEDIUM MODELS (3-5GB VRAM) ===
    "llama3.2:3b": {"size": "3B", "ram_gb": 2.5, "category": "medium", "type": "general", "quality": 8},
    "qwen2.5:3b": {"size": "3B", "ram_gb": 2.5, "category": "medium", "type": "general", "quality": 8},
    "qwen2.5-coder:3b": {"size": "3B", "ram_gb": 2.5, "category": "medium", "type": "code", "quality": 8},
    "qwen3:4b": {"size": "4B", "ram_gb": 3.0, "category": "medium", "type": "reasoning", "quality": 8},
    "gemma3:4b": {"size": "4B", "ram_gb": 3.0, "category": "medium", "type": "general", "quality": 8},
    "granite-code:3b": {"size": "3B", "ram_gb": 2.5, "category": "medium", "type": "code", "quality": 7},
    "stable-code:3b": {"size": "3B", "ram_gb": 2.5, "category": "medium", "type": "code", "quality": 7},
    "starcoder2:3b": {"size": "3B", "ram_gb": 2.5, "category": "medium", "type": "code", "quality": 7},
    "phi3:mini": {"size": "3.8B", "ram_gb": 3.0, "category": "medium", "type": "general", "quality": 8},
    "phi3.5:3.8b": {"size": "3.8B", "ram_gb": 3.0, "category": "medium", "type": "general", "quality": 8},
    "phi4-mini:3.8b": {"size": "3.8B", "ram_gb": 3.0, "category": "medium", "type": "general", "quality": 8},
    "nemotron-mini:4b": {"size": "4B", "ram_gb": 3.0, "category": "medium", "type": "general", "quality": 8},
    
    # === LARGE MODELS (5-8GB VRAM) ===
    "mistral:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 9},
    "llama3.1:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "general", "quality": 9},
    "llama3:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "general", "quality": 9},
    "qwen2.5:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 9},
    "qwen2:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 8},
    "qwen:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 8},
    "qwen2.5-coder:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "code", "quality": 9},
    "codellama:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "code", "quality": 8},
    "deepseek-r1:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "reasoning", "quality": 9},
    "deepseek-coder:6.7b": {"size": "6.7B", "ram_gb": 4.3, "category": "large", "type": "code", "quality": 8},
    "gemma2:9b": {"size": "9B", "ram_gb": 5.5, "category": "large", "type": "general", "quality": 9},
    "gemma:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 8},
    "codegemma:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "code", "quality": 8},
    "dolphin-mistral:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 8},
    "dolphin-llama3:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "general", "quality": 9},
    "dolphin3:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "general", "quality": 9},
    "neural-chat:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 8},
    "openchat:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 8},
    "yi:6b": {"size": "6B", "ram_gb": 4.0, "category": "large", "type": "general", "quality": 8},
    "yi-coder:9b": {"size": "9B", "ram_gb": 5.5, "category": "large", "type": "code", "quality": 9},
    "granite-code:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "code", "quality": 8},
    "granite3.3:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "general", "quality": 9},
    "granite3-dense:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "general", "quality": 9},
    "starcoder2:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "code", "quality": 8},
    "starcoder:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "code", "quality": 7},
    "openthinker:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "reasoning", "quality": 8},
    "llama2:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 7},
    "orca-mini:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 7},
    "vicuna:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 7},
    "nous-hermes:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "general", "quality": 8},
    "hermes3:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "general", "quality": 9},
    "qwen3:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "reasoning", "quality": 9},
    "deepseek-r1:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "reasoning", "quality": 9},
    "opencoder:8b": {"size": "8B", "ram_gb": 5.0, "category": "large", "type": "code", "quality": 8},
    "marco-o1:7b": {"size": "7B", "ram_gb": 4.5, "category": "large", "type": "reasoning", "quality": 8},
    
    # === XLARGE MODELS (8-16GB VRAM) ===
    "mistral-nemo:12b": {"size": "12B", "ram_gb": 7.5, "category": "xlarge", "type": "general", "quality": 9},
    "phi3:14b": {"size": "14B", "ram_gb": 8.5, "category": "xlarge", "type": "general", "quality": 9},
    "phi4:14b": {"size": "14B", "ram_gb": 8.5, "category": "xlarge", "type": "general", "quality": 10},
    "qwen2.5:14b": {"size": "14B", "ram_gb": 8.5, "category": "xlarge", "type": "general", "quality": 9},
    "qwen2.5-coder:14b": {"size": "14B", "ram_gb": 8.5, "category": "xlarge", "type": "code", "quality": 9},
    "deepseek-r1:14b": {"size": "14B", "ram_gb": 8.5, "category": "xlarge", "type": "reasoning", "quality": 9},
    "deepcoder:14b": {"size": "14B", "ram_gb": 8.5, "category": "xlarge", "type": "code", "quality": 9},
    "starcoder2:15b": {"size": "15B", "ram_gb": 9.0, "category": "xlarge", "type": "code", "quality": 9},
    "codellama:13b": {"size": "13B", "ram_gb": 8.0, "category": "xlarge", "type": "code", "quality": 8},
    "llama2:13b": {"size": "13B", "ram_gb": 8.0, "category": "xlarge", "type": "general", "quality": 8},
    "orca-mini:13b": {"size": "13B", "ram_gb": 8.0, "category": "xlarge", "type": "general", "quality": 8},
    "vicuna:13b": {"size": "13B", "ram_gb": 8.0, "category": "xlarge", "type": "general", "quality": 8},
    "granite-code:20b": {"size": "20B", "ram_gb": 12.0, "category": "xlarge", "type": "code", "quality": 9},
    "mistral-small:22b": {"size": "22B", "ram_gb": 13.0, "category": "xlarge", "type": "general", "quality": 10},
    "codestral:22b": {"size": "22B", "ram_gb": 13.0, "category": "xlarge", "type": "code", "quality": 10},
    "mistral-small3.2:24b": {"size": "24B", "ram_gb": 14.0, "category": "xlarge", "type": "general", "quality": 10},
    "mistral-small3.1:24b": {"size": "24B", "ram_gb": 14.0, "category": "xlarge", "type": "general", "quality": 10},
    "devstral:24b": {"size": "24B", "ram_gb": 14.0, "category": "xlarge", "type": "code", "quality": 10},
    "magistral:24b": {"size": "24B", "ram_gb": 14.0, "category": "xlarge", "type": "reasoning", "quality": 10},
    "gemma2:27b": {"size": "27B", "ram_gb": 16.0, "category": "xxlarge", "type": "general", "quality": 10},
    "qwen3:30b": {"size": "30B", "ram_gb": 18.0, "category": "xxlarge", "type": "reasoning", "quality": 10},
    "qwen2.5:32b": {"size": "32B", "ram_gb": 19.0, "category": "xxlarge", "type": "general", "quality": 10},
    "qwen2.5-coder:32b": {"size": "32B", "ram_gb": 19.0, "category": "xxlarge", "type": "code", "quality": 10},
    "deepseek-r1:32b": {"size": "32B", "ram_gb": 19.0, "category": "xxlarge", "type": "reasoning", "quality": 10},
    "openthinker:32b": {"size": "32B", "ram_gb": 19.0, "category": "xxlarge", "type": "reasoning", "quality": 10},
    "qwq:32b": {"size": "32B", "ram_gb": 19.0, "category": "xxlarge", "type": "reasoning", "quality": 10},
    "codellama:34b": {"size": "34B", "ram_gb": 20.0, "category": "xxlarge", "type": "code", "quality": 9},
    "granite-code:34b": {"size": "34B", "ram_gb": 20.0, "category": "xxlarge", "type": "code", "quality": 9},
    
    # === XXLARGE MODELS (16GB+ VRAM) ===
    "llama3.1:70b": {"size": "70B", "ram_gb": 40.0, "category": "massive", "type": "general", "quality": 10},
    "llama3:70b": {"size": "70B", "ram_gb": 40.0, "category": "massive", "type": "general", "quality": 10},
    "llama3.3:70b": {"size": "70B", "ram_gb": 40.0, "category": "massive", "type": "general", "quality": 10},
    "qwen2.5:72b": {"size": "72B", "ram_gb": 42.0, "category": "massive", "type": "general", "quality": 10},
    "deepseek-r1:70b": {"size": "70B", "ram_gb": 40.0, "category": "massive", "type": "reasoning", "quality": 10},
    "codellama:70b": {"size": "70B", "ram_gb": 40.0, "category": "massive", "type": "code", "quality": 9},
    "llama2:70b": {"size": "70B", "ram_gb": 40.0, "category": "massive", "type": "general", "quality": 9},
    "mistral-large:123b": {"size": "123B", "ram_gb": 70.0, "category": "massive", "type": "general", "quality": 10},
}


def get_models_for_gpu(gpu_memory_gb: float, num_models: int = 6) -> List[str]:
    """Get recommended models based on GPU memory and number needed.
    
    Returns models categorized by GPU VRAM capacity:
    - < 4GB: Tiny/Small models (135M - 2B)
    - 4-8GB: Small/Medium models (1B - 7B)
    - 8-12GB: Medium/Large models (3B - 14B)
    - 12-16GB: Large models (7B - 24B)
    - 16-24GB: XLarge models (14B - 32B)
    - 24GB+: All models including 70B+
    """
    
    # Calculate memory per model (conservative buffer of 20%)
    memory_per_model = (gpu_memory_gb * 0.75) / num_models
    
    # Define quality tiers based on GPU capacity
    if gpu_memory_gb < 4:
        max_quality = 6  # Prioritize tiny/small models
        preferred_categories = ["tiny", "small"]
    elif gpu_memory_gb < 8:
        max_quality = 8
        preferred_categories = ["small", "medium-small", "medium"]
    elif gpu_memory_gb < 12:
        max_quality = 9
        preferred_categories = ["medium", "large"]
    elif gpu_memory_gb < 16:
        max_quality = 10
        preferred_categories = ["large", "xlarge"]
    elif gpu_memory_gb < 24:
        max_quality = 10
        preferred_categories = ["xlarge", "xxlarge"]
    else:
        max_quality = 10
        preferred_categories = ["xlarge", "xxlarge", "massive"]
    
    # Filter models that fit in memory
    suitable_models = []
    for model_name, info in MODEL_DATABASE.items():
        if info['ram_gb'] <= memory_per_model and info['category'] in preferred_categories:
            # Add score based on quality and fit
            fit_score = info['quality'] * (1 - abs(info['ram_gb'] - memory_per_model * 0.8) / memory_per_model)
            suitable_models.append((model_name, info, fit_score))
    
    # Sort by fit score (quality + how well it fits memory)
    suitable_models.sort(key=lambda x: x[2], reverse=True)
    
    # Ensure diversity: mix of general, code, and reasoning models
    final_selection = []
    type_counts = {"general": 0, "code": 0, "reasoning": 0, "vision": 0}
    max_per_type = max(2, num_models // 2)
    
    for model_name, info, score in suitable_models:
        model_type = info['type']
        if type_counts[model_type] < max_per_type:
            final_selection.append(model_name)
            type_counts[model_type] += 1
        
        if len(final_selection) >= num_models * 3:  # Return 3x requested for user choice
            break
    
    # If we don't have enough, add more without type restriction
    if len(final_selection) < num_models * 2:
        for model_name, info, score in suitable_models:
            if model_name not in final_selection:
                final_selection.append(model_name)
            if len(final_selection) >= num_models * 3:
                break
    
    return final_selection[:num_models * 3]  # Return 3x for user selection


def get_getch():
    """Get a single character from stdin without echo."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        
        # Handle arrow keys and special keys
        if ch == '\x1b':  # ESC sequence
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                return '\x1b[' + ch3
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_model_selector(available_models: List[str], num_to_select: int = 6) -> List[str]:
    """Interactive model selector with number-based selection (most reliable).
    
    Models are displayed in order and user selects exactly num_to_select models.
    They will speak in the order they're selected.
    """
    
    if len(available_models) == 0:
        print("❌ No suitable models found for your GPU")
        return []
    
    selected = []  # List to maintain order
    selected_set = set()  # For fast lookup
    
    # Add model info to display
    models_with_info = []
    for i, model in enumerate(available_models):
        info = MODEL_DATABASE.get(model, {"size": "?", "ram_gb": 0, "type": "general", "quality": 5})
        models_with_info.append({
            'name': model,
            'size': info['size'],
            'ram_gb': info['ram_gb'],
            'type': info['type'],
            'quality': info.get('quality', 5)
        })
    
    print("\n" + "="*80)
    print("🎮  SELECT MODELS FOR YOUR GLADIATORS")
    print("="*80)
    print(f"\n📝 How to select models:")
    print(f"   • Enter numbers (1-{len(models_with_info)}) to select models")
    print(f"   • Enter multiple numbers separated by space: 1 3 5 7 2 4")
    print(f"   • Or enter 'auto' to automatically select top {num_to_select} models")
    print(f"   • Need to select exactly {num_to_select} models")
    print(f"\n💡 Tip: Models speak in the order you select them!")
    print(f"{'─'*80}\n")
    
    # Display all available models
    print("Available Models:\n")
    for i, model_info in enumerate(models_with_info, 1):
        name = model_info['name']
        size = model_info['size']
        ram = f"{model_info['ram_gb']:.1f}GB"
        type_tag = model_info['type'].upper()
        quality = model_info['quality']
        stars = "★" * quality
        
        print(f"  {i:2d}. {name:28s} │ {size:6s} │ {ram:7s} │ {type_tag:10s} │ {stars}")
    
    print(f"\n{'─'*80}")
    
    # Simple text-based selection loop
    while len(selected) < num_to_select:
        remaining = num_to_select - len(selected)
        
        if len(selected) > 0:
            print(f"\n✓ Selected ({len(selected)}/{num_to_select}): " + 
                  ", ".join([f"{i+1}.{m.split(':')[0]}" for i, m in enumerate(selected)]))
        
        print(f"\n👉 Select {remaining} more model(s)")
        print(f"   Enter number(s) 1-{len(models_with_info)} (space-separated)")
        print(f"   Or type 'auto' for automatic selection")
        print(f"   Or type 'restart' to clear and start over")
        
        choice = input(f"\nYour choice: ").strip().lower()
        
        if choice == 'auto':
            # Auto-select remaining models
            for model_info in models_with_info:
                if model_info['name'] not in selected_set and len(selected) < num_to_select:
                    selected.append(model_info['name'])
                    selected_set.add(model_info['name'])
            break
        
        elif choice == 'restart':
            selected.clear()
            selected_set.clear()
            print("\n🔄 Selection cleared!")
            continue
        
        elif choice in ['q', 'quit', 'exit']:
            print("\n❌ Selection cancelled")
            return []
        
        else:
            # Parse number inputs
            try:
                numbers = [int(n.strip()) for n in choice.split()]
                for num in numbers:
                    if 1 <= num <= len(models_with_info):
                        model_name = models_with_info[num - 1]['name']
                        if model_name not in selected_set and len(selected) < num_to_select:
                            selected.append(model_name)
                            selected_set.add(model_name)
                            print(f"   ✓ Added: {model_name}")
                        elif model_name in selected_set:
                            print(f"   ⚠️  Already selected: {model_name}")
                        else:
                            print(f"   ⚠️  Already have {num_to_select} models")
                    else:
                        print(f"   ❌ Invalid number: {num} (must be 1-{len(models_with_info)})")
            except ValueError:
                print(f"   ❌ Invalid input. Please enter numbers separated by spaces")
                continue
    
    # Final display with speaking order
    print("\033[2J\033[H", end='')
    print("\n" + "="*80)
    print("✅  MODELS SELECTED SUCCESSFULLY!")
    print("="*80)
    print(f"\n🎭 Your Gladiators (in speaking order):\n")
    
    for i, model in enumerate(selected, 1):
        info = MODEL_DATABASE.get(model, {})
        quality_stars = "★" * info.get('quality', 5)
        print(f"   {i}. {model:28s} │ {info.get('size', '?'):6s} │ " + 
              f"{info.get('type', 'general').upper():10s} │ {quality_stars}")
    
    print(f"\n{'─'*80}")
    print("🎮 Starting arena setup...\n")
    
    return selected


def select_models_cli(gpu_memory_gb: float, num_agents: int = 6) -> List[str]:
    """Main entry point for model selection with GPU-based filtering.
    
    This function:
    1. Analyzes GPU memory capacity
    2. Lists only models that can run on the graphics card
    3. Allows user to select exactly num_agents models using arrow keys
    4. Returns models in speaking order
    """
    
    print("\n" + "="*80)
    print("🔍  ANALYZING YOUR SYSTEM")
    print("="*80)
    print(f"\n� GPU Memory Available: {gpu_memory_gb:.1f} GB")
    print(f"🎮 Gladiators Needed: {num_agents}")
    
    # Determine GPU tier
    if gpu_memory_gb < 4:
        tier = "Entry Level (Integrated/Low-end GPU)"
        emoji = "🔵"
    elif gpu_memory_gb < 8:
        tier = "Budget Gaming (GTX 1650-1660 Ti, RTX 3050)"
        emoji = "🟢"
    elif gpu_memory_gb < 12:
        tier = "Mid-Range (RTX 3060, RTX 4060)"
        emoji = "🟡"
    elif gpu_memory_gb < 16:
        tier = "High-End (RTX 3060 Ti, RTX 4060 Ti)"
        emoji = "🟠"
    elif gpu_memory_gb < 24:
        tier = "Enthusiast (RTX 3080, RTX 4070 Ti)"
        emoji = "🔴"
    else:
        tier = "Professional (RTX 4090, A100, H100)"
        emoji = "🟣"
    
    print(f"{emoji} GPU Tier: {tier}")
    
    # Get suitable models
    available_models = get_models_for_gpu(gpu_memory_gb, num_agents)
    
    if not available_models:
        print("\n⚠️  Limited GPU memory detected.")
        print("   Showing smallest available models...\n")
        # Fallback: show the smallest models available
        all_models = sorted(MODEL_DATABASE.items(), key=lambda x: x[1]['ram_gb'])
        available_models = [m[0] for m in all_models[:num_agents * 3]]
    
    print(f"\n✅ Found {len(available_models)} compatible models for your GPU")
    
    if gpu_memory_gb < 6:
        print("\n⚠️  Note: Running multiple models may be slower with limited VRAM")
        print("   Consider using the same model for all gladiators for better performance")
    
    print(f"{'─'*80}\n")
    
    time.sleep(0.5)  # Brief pause for user to read
    
    try:
        selected = interactive_model_selector(available_models, num_agents)
        
        if not selected:
            return []
        
        # Verify selection
        total_ram = sum(MODEL_DATABASE.get(m, {}).get('ram_gb', 0) for m in selected)
        print(f"\n📊 Total VRAM usage: {total_ram:.1f}GB / {gpu_memory_gb:.1f}GB ({total_ram/gpu_memory_gb*100:.1f}%)")
        
        return selected
        
    except KeyboardInterrupt:
        print("\n\n❌ Selection cancelled by user (Ctrl+C)")
        return []
    except Exception as e:
        print(f"\n❌ Selection failed: {e}")
        print("   Falling back to automatic selection...")
        auto_selected = available_models[:num_agents]
        print("\n🤖 Auto-selected models:")
        for i, model in enumerate(auto_selected, 1):
            info = MODEL_DATABASE.get(model, {})
            print(f"   {i}. {model} ({info.get('size', '?')})")
        return auto_selected


def get_model_info(model_name: str) -> Dict[str, Any]:
    """Get information about a specific model."""
    return MODEL_DATABASE.get(model_name, {
        "size": "Unknown",
        "ram_gb": 0,
        "category": "unknown",
        "type": "general",
        "quality": 5
    })


def list_all_models_by_category() -> Dict[str, List[str]]:
    """List all available models grouped by category."""
    categories = {}
    for model_name, info in MODEL_DATABASE.items():
        category = info['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(model_name)
    return categories


# Time import for pause
import time
