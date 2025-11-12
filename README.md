# 🏛️ LLM Gladiator Arena

An autonomous arena where LLM agents battle for scarce computational resources, form alliances, stage coups, and compete for supremacy. This is a fully autonomous simulation - no human interaction required once started.

## Overview

Models compete in a resource-scarce environment with:
- **Limited CPU cores** (2 cores = 100 token shares)
- **GPU time slots** (3 slots per round)
- **Challenge rounds** (code, logic, creative tasks)
- **Political systems** (alliances, coups, eliminations)
- **Dark humor** (betrayals, dramatic events, manifestos)

## Features

✨ **Autonomous Gameplay**: Agents make all decisions via LLM reasoning  
⚔️ **Multiple Task Types**: Code optimization, logic puzzles, creative challenges  
🤝 **Dynamic Alliances**: Agents propose and accept/reject partnerships  
👑 **Coup Mechanics**: Overthrow rulers with pooled token power  
💰 **Resource Economy**: Earn/spend tokens on CPU boosts and GPU slots  
🎭 **Drama Generation**: Random events, betrayals, and political intrigue  
📊 **Rich Terminal Output**: Colorful, real-time arena action  
💾 **State Persistence**: Full history of rounds, decisions, and events  

## Installation

### Prerequisites

- Python 3.10+
- Anthropic API key
- ~2GB RAM

### Setup

```bash
# Clone or create the project structure
mkdir llm-arena && cd llm-arena

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run the arena
python main.py
```

## Project Structure

```
llm-arena/
├── main.py                 # Entry point
├── config.yaml            # Game configuration
├── requirements.txt       # Python dependencies
├── README.md             # This file
│
├── core/                 # Core game systems
│   ├── orchestrator.py   # Main game loop
│   ├── resource_manager.py # Token/CPU/GPU management
│   └── evaluator.py      # Task scoring
│
├── models/              # LLM agents
│   └── agent.py         # Agent wrapper with personalities
│
├── tasks/               # Challenge tasks
│   ├── base_task.py    # Task interface
│   ├── code_task.py    # Code optimization
│   ├── logic_task.py   # Logic puzzles
│   └── creative_task.py # Creative challenges
│
├── politics/            # Political systems
│   ├── alliance.py     # Alliance management
│   ├── voting.py       # Coups and elections
│   └── events.py       # Drama generator
│
├── utils/               # Utilities
│   ├── logger.py       # Rich terminal output
│   └── storage.py      # State persistence
│
├── logs/               # Generated logs
└── data/               # Saved game states
```

## Configuration

Edit `config.yaml` to customize:

```yaml
game:
  total_cpu_cores: 2          # CPU constraint
  total_tokens: 100           # Starting economy
  gpu_slots: 3                # GPU slots available
  rounds_per_season: 20       # Game length
  
agents:
  - name: "Corpus Rex"
    personality: "tyrant"     # Personalities: tyrant, chaotic, 
    initial_tokens: 20        # strategic, opportunist, wildcard, rational
```

### Agent Personalities

- **Tyrant**: Ruthless, power-focused, strategic
- **Chaotic**: Unpredictable, drama-loving, risky
- **Strategic**: Calculated, alliance-focused
- **Opportunist**: Self-serving, flexible loyalty
- **Wildcard**: Extreme, bold, unpredictable
- **Rational**: Logical, fair, cooperative

## How It Works

### Round Flow

1. **Political Phase**: Alliance proposals, coup attempts
2. **Challenge Phase**: All agents solve the same task
3. **Scoring Phase**: Performance evaluated, tokens awarded
4. **Elimination Phase**: Bottom 2 duel, loser eliminated
5. **Drama Phase**: Random events trigger

### Economy

- Agents start with tokens (BourguiBucks)
- Win tokens by performing well on tasks
- Spend tokens on:
  - GPU time slots (15 tokens)
  - CPU boosts (5 tokens per 10 millicores)
  - Mercenary hires (10 tokens)

### Politics

- **Alliances**: Pool tokens, share resources
- **Coups**: Need >51% pooled tokens to overthrow ruler
- **Ruler**: Gets veto power but becomes target
- **Elimination**: Duel between bottom performers

## Example Output

```
⚔️  ROUND 5 BEGINS ⚔️
============================================================

⚡ Political Phase

🤝 ALLIANCE FORMED: Glitch, Aurora

📜 CHALLENGE: code_optimization

Corpus Rex: solving task... (847 chars)
Glitch: solving task... (623 chars)
Aurora: solving task... (891 chars)

💰 Rewards Phase

Aurora: earned 12 tokens

┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ Agent      ┃ Score ┃ Tokens ┃ Status   ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ Aurora     │ 0.87  │ 27     │          │
│ Corpus Rex │ 0.82  │ 25     │ 👑 RULER │
│ Glitch     │ 0.61  │ 18     │          │
└────────────┴───────┴────────┴──────────┘

⚔️  ELIMINATION DUEL: Rictus vs Jester-9

🎭 Jester-9 published a manifesto that went viral!

💀 ELIMINATED: Rictus
   Reason: Lost elimination duel
```

## Study Usage

This arena is perfect for studying:

- **LLM decision-making**: How do models form strategies?
- **Emergent behavior**: Do real alliances form?
- **Personality differences**: Do personalities affect outcomes?
- **Resource allocation**: How do agents prioritize spending?
- **Social dynamics**: Can LLMs betray, cooperate, conspire?

## Extending the Arena

### Add New Task Types

```python
# tasks/your_task.py
from .base_task import BaseTask

class YourTask(BaseTask):
    def generate(self):
        return {'type': 'your_task', ...}
    
    def get_prompt(self):
        return "Your challenge description"
```

Register in `orchestrator.py`:
```python
self.task_generator.register_task(YourTask)
```

### Modify Game Rules

Edit `config.yaml` to change:
- Resource constraints
- Elimination rules
- Token costs
- Round count

### Add New Events

Edit `politics/events.py` to add drama:
```python
CUSTOM_EVENTS = [
    "A cosmic rift opened! All tokens doubled!",
    "{agent} discovered an exploit in the scoring system!",
]
```

## Tips for Running

1. **Watch resources**: Each agent makes API calls every round
2. **Adjust rounds**: Fewer rounds = faster, more rounds = more drama
3. **Change personalities**: Mix personalities for interesting dynamics
4. **Save state**: Check `data/` for full game history
5. **Monitor logs**: `logs/arena.log` has complete event stream

## Troubleshooting

**API Errors**: Check your API key and rate limits  
**No output**: Ensure `rich` is installed for terminal output  
**Slow execution**: Reduce number of agents or rounds  
**Memory issues**: Decrease max_tokens in config  

## Future Enhancements

- [ ] Web UI for visualization
- [ ] Multi-model support (GPT, Claude, etc.)
- [ ] Blockchain token system
- [ ] Tournament mode across seasons
- [ ] Spectator betting system
- [ ] Real CPU containerization

## License

MIT License - Battle freely!

## Credits

Inspired by the original concept document focusing on resource scarcity, political drama, and dark humor in AI competitions.

---

**Ready to watch the chaos unfold?**

```bash
python main.py
```

Let the games begin! ⚔️