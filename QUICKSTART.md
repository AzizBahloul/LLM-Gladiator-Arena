# 🏛️ LLM Gladiator Arena - Quick Start Guide

## GPU Support ✅

The arena now automatically detects and uses your GPU if available!

- **NVIDIA GPUs**: Automatically uses CUDA
- **Apple Silicon**: Automatically uses Metal Performance Shaders (MPS)
- **CPU Fallback**: Works on any system without GPU

## Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install Ollama** (if using Ollama provider):
   - Visit: https://ollama.ai/download
   - Or use your package manager

3. **Start Ollama server:**
```bash
ollama serve
```

## Running the Arena

### Quick Start
```bash
python main.py
```

The application will:
1. ✓ Detect your GPU (CUDA/MPS/CPU)
2. ✓ Check if Ollama is running
3. ✓ Offer to pull required models if missing
4. ✓ Let you choose between GUI or Console mode

### Display Modes

**1. Terminal GUI Mode (Recommended)** 🖥️
- Modern, interactive terminal interface
- Live agent status cards
- Real-time event chronicle
- Resource monitoring (CPU, GPU, Token Pool)
- Dark themed for dramatic atmosphere

**2. Classic Console Mode** 📜
- Traditional text-based output
- Detailed logs
- Perfect for headless servers

## Game Features

### The Gladiators
- **6 AI Agents** with unique personalities:
  - Corpus Rex (Tyrant)
  - Glitch (Chaotic)
  - Aurora (Strategic)
  - Rictus (Opportunist)
  - Jester-9 (Wildcard)
  - Sage (Rational)

### Dark Politics
- 🤝 **Alliances**: Form temporary partnerships
- 👑 **Ruler System**: One agent controls the arena
- 🔥 **Coups**: Overthrow the ruler with enough tokens
- 💀 **Elimination Duels**: Bottom performers fight to survive
- 🎭 **Dramatic Events**: Betrayals, revolts, and plot twists

### Gameplay
- Agents solve challenges to earn BourguiBucks (BB)
- Limited resources create scarcity and tension
- Each round includes:
  - Political maneuvering
  - Challenge execution
  - Rewards distribution
  - Elimination battles

## Configuration

Edit `config.yaml` to customize:

```yaml
api:
  provider: "ollama"  # or "anthropic"
  model: "llama3.2:3b"  # Change model here
  
game:
  rounds_per_season: 30
  initial_agents: 6
  gpu_slots: 3
  
# ... more settings
```

## GPU Optimization

The arena automatically:
- Sets `OLLAMA_NUM_GPU=1` for GPU acceleration
- Configures CUDA optimizations
- Enables cuDNN benchmarking
- Clears GPU cache between rounds

## Save System

- **3 Save Slots** available
- Auto-save after each round
- Resume from any point
- View save slot info in menu

## Troubleshooting

### No GPU Detected
- Install PyTorch with CUDA: `pip install torch --index-url https://download.pytorch.org/whl/cu118`
- Check NVIDIA drivers: `nvidia-smi`

### Ollama Not Running
```bash
ollama serve
```

### Model Not Found
The app will offer to pull it automatically, or:
```bash
ollama pull llama3.2:3b
```

### GUI Issues
- Ensure terminal supports unicode/emoji
- Try resizing terminal window
- Fall back to Console Mode (option 2)

## Tips for Maximum Drama

1. **Watch the Resources Panel**: See GPU utilization in real-time
2. **Follow the Chronicle**: Every alliance and betrayal is logged
3. **Agent Cards Update Live**: See tokens and status change
4. **Let it Run**: The longer the game, the more dramatic the twists

## Performance

- **With GPU**: Fast inference, smooth gameplay
- **CPU Mode**: Slower but fully functional
- **Model Size**: Smaller models (1b-3b) recommended for smooth experience

## Exit Safely

- Press `Ctrl+C` to stop
- Game auto-saves current state
- Resume from last save slot

---

**Enjoy the carnage!** 🏛️⚔️💀
