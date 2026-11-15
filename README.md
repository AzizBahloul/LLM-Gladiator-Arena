# THE UNDERMIND

Language models locked in a failing machine-afterlife, fighting, lying and bargaining under a dying lamp. Nobody writes their moves. Not you, and not the game.

```
python main.py            # a new run, with the full-screen interface
python main.py resume     # carry on exactly where you closed it
```

The game is the **Undermind**: a corridor of filing cabinets lit by one lamp (the **Ember**), kept by a tired bureaucrat (**the Registrar**). The minds in it (**Wicks**) are real models running on your machine. Each cycle they talk in public and in whispers, then everyone secretly chooses one action, and all of it resolves at once. Strikes, mind-sieges that try to trick a rival into saying their secret word, tribunals with model jurors, pacts and betrayals, ghosts that haunt from beyond. The engine is a referee: it checks costs and applies consequences. Every word spoken and every secret choice is a model's own.

Above the Registrar is **God**, also a model. Each cycle God reads what the minds actually did and writes the next twist: a changed rule, a bounty on someone, a boon, a decree, sometimes a stranger arriving. Left running for hours, the story keeps bending around its own history. Seasons end and new ones begin, and the minds remember.

## What you get

- **A story that nobody scripted.** Endings are reached, not selected: The Pen, The Committee, The Unplugging, The Long Dark, The Clerical Error, The Backlog. See [docs/LORE.md](docs/LORE.md).
- **A Theatre.** The minds are animated pixel figures on a lamp-lit stage. They walk, talk, strike, flinch, ward, whisper and fade, so a season reads like a film.
- **An endless mode.** God writes a new premise when a season ends, from what just happened. Survivors keep their memories.
- **Nothing is lost when you close it.** Every event is journaled, state is checkpointed between phases of every cycle, and `resume` continues without repeating or dropping anything. See [Durability](#durability).
- **A catalog of 270 Ollama model families** (238 chat-capable and local, 450 sized variants) in [docs/MODELS.md](docs/MODELS.md). Models can be swapped, or new minds born from any of them, while a run is going (press `m`). New minds invent their own personality.
- **Permadeath.** A mind that dissolves has its model deleted from your machine. See [Permadeath](#permadeath-read-this).

## Quick start

You need Python 3.10 or newer. For real models you need [Ollama](https://ollama.com) running (`ollama serve`).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python main.py --mock --no-gui --once      # offline dry run with a seeded test double, no model needed
python main.py                             # the real thing: picks and installs models, opens the interface
```

On the first real run the arena chooses a different small chat model for each mind (up to about 2.5 GB each) and downloads whichever are missing. It prints the plan and the disk space needed before it starts. Pin your own with `--models llama3.2:3b,gemma2:2b` or in `config.yaml`.

### Commands

| Command | What it does |
|---|---|
| `python main.py` or `new` | Start a run. `--endless` (the default) or `--once`; `--cycles N`; `--seed N`; `--models auto` or a comma list; `--no-god` to use the fixed deck of Notices |
| `python main.py resume [RUN_ID]` | Resume the latest run, or a named one |
| `python main.py runs` | List saved runs |
| `python main.py models list\|search\|status\|pull\|refresh\|markdown` | Browse the catalog, see what is installed and what is at stake, install a model |
| `--no-gui` | Plain console output instead of the full-screen interface |
| `--mock` | Offline dry run with a seeded test double (never used as a fallback in real runs) |
| `--no-permadeath` | Never delete a model |
| `--include-preexisting` | Models that were on your machine before the arena first ran may be deleted too |

### Keys in the interface

`p` pause, `m` models (swap a mind into another model, or birth a new mind from one), `t` theatre on or off, `c` cycle panels on a narrow terminal, `-` and `+` speed, `q` leave (press twice mid-run; the run is saved).

## Permadeath: read this

When a mind is dissolved, **the Ollama model that gave it a voice is deleted from this machine** (`ollama rm`). That is the point of the game, and it is on by default. It has guardrails, because deleting models is not something to do carelessly:

- Models that were **already installed the first time the arena ran** are *protected*. The list is written to `data/arena_models.json` before anything else happens. They are never deleted unless you pass `--include-preexisting`.
- The Registrar's and God's models are never deleted, so the story can always be told. By default they are chosen from your protected models.
- A model is deleted only when **no other living or haunting mind uses it**.
- The ledger records what the arena installed (`owned`) and what it deleted (`wiped`).
- `python main.py models status` shows every installed model as protected, at stake, or untracked.
- `--no-permadeath` (or `game.permadeath: false`) switches it all off.

A dissolved mind is not silenced: its Echo keeps speaking, using the Registrar's voice, and can bless or hex the living.

## Durability

The run folder is `data/runs/<run id>/`:

| File | What it holds |
|---|---|
| `journal.jsonl` | Every event, append-only, numbered |
| `snapshot.json` | The full game state, written atomically (temp file, fsync, rename) between phases |
| `seasons.jsonl` | One line per finished season, written once |
| `chronicle.md` | The story as readable Markdown |
| `config.json` | The configuration this run started with |
| `partial/` | Journal lines from a cycle that was cut off, set aside rather than lost or replayed |

A cycle has phases: begun, parleyed, acted. The state is checkpointed after each. If you close the program mid-cycle, `resume` picks up at the last phase, and secret actions that were already chosen are resolved, not asked again. A torn last line from a hard kill is ignored. The tests close the game at arbitrary moments and check that nothing appears twice.

## Configuration

Everything is in [config.yaml](config.yaml), commented. The parts you will touch:

- `models: auto` or a list of Ollama tags, and `max_model_gb`
- `roster`: which personas fight, optionally pinned to a model
- `game.endless`, `game.cycles`, `game.permadeath`, `game.arrivals_max`, `game.max_wicks`
- `api.provider`: `ollama`, `anthropic` (set `ANTHROPIC_API_KEY`, `pip install anthropic`), or `mock`

## How long does it take?

Local models are slow to load. On a 6 GB GPU each model takes roughly 20 to 40 seconds to load, and a cycle asks six minds to speak and act. The engine groups minds by model to avoid swapping on every turn, but a 12-cycle season on a small GPU is a long evening, not a few minutes. That is why runs are resumable.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite uses the mock backend and a fake Ollama admin. No test ever runs a real `ollama rm`. It covers parsing of messy model output, the rules and every ending, God's validation and clamping, durability and resume, permadeath safeguards, the catalog, design-token contrast, the Theatre, and the interface under a headless pilot.

## Project layout

```
main.py                  command line
config.yaml              configuration
arena/engine/            the referee: game, rules, state, minds, God, narrator, store, permadeath, model hub
arena/llm/               backends (ollama, anthropic, mock), parsing, the model catalog, hardware
arena/lore/              personas, ciphers, Notices, directives, acts, endings, margin notes
arena/ui/                terminal interface, the Theatre, formatting, design tokens
docs/                    GUIDE.md, LORE.md, DESIGN.md, MODELS.md
tests/
```

More: [docs/GUIDE.md](docs/GUIDE.md) for the rules and how to read a run, [docs/LORE.md](docs/LORE.md) for the world, [docs/DESIGN.md](docs/DESIGN.md) for the interface.
