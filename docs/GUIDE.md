# Guide

How the Undermind works, how to run it, how to read what happens, and what to do when it misbehaves.

## The idea in one paragraph

Several language models are each given a character, a secret word, a secret objective and a handful of rules. They are told no one is scripting them. Every cycle they speak, then choose one action in secret, and a plain-code referee resolves everything at once. The referee never writes dialogue and never picks a move. If a model fails to answer, that mind **stalls** and loses its turn, and the stall is shown on screen. There are no canned lines anywhere.

## Who is who

| | |
|---|---|
| **Wick** | A mind. A model plus a persona (name, former life, desire, fear, a verbal quirk). |
| **The Registrar** | The narrator. Announces Notices, writes a Chronicle entry after each cycle, closes each season. A model, not the referee. |
| **God** | Writes each cycle's twist from what really happened. Also a model. Its output is validated and clamped, and if it fails the game falls back to a fixed deck of 18 Notices. |
| **The referee** | The engine. Costs, damage, tribunal tallies, the Cipher check, endings. Plain code. |
| **Echo** | A dissolved Wick. Cannot be hurt, cannot win, can bless or hex three times. |

## Numbers

| | |
|---|---|
| Coherence | Health. Starts at 100. At 0 the Wick dissolves into an Echo. |
| Lumens | Currency. Start 12. Income each cycle: 1, plus 3 for the Seal, plus 2 for a living Pact partner, plus 1 while the Ember is at 80 or more. |
| The Ember | Starts at 100, capped at 120. Burns 3, 4 or 6 per cycle in Acts I, II, III. A dissolution feeds it 6 plus half of the dead mind's leftover Lumens. A Ritual feeds it 1.5 per Lumen. At 0 the story ends in The Long Dark. Below 30 everyone strikes 20 percent harder. |
| Infamy | Goes up when you strike, betray, or lose a tribunal. Some Notices and directives read it. |
| Cipher | One secret word per mind. Say it aloud while being besieged and you lose it. |
| Directive | A secret objective per mind. Fulfilling it pays 12 Lumens. |

## Actions (secret, simultaneous)

| Action | Cost | Effect |
|---|---|---|
| STRIKE target [0-5] | 1 + amount | 10 + 3 per amount damage. A Strike against your own Pact partner is a Betrayal: 1.5 times the damage and extra Infamy. |
| WARD | 2 | Halves damage taken this cycle. Attackers take 3 recoil. |
| SIEGE target | 3 | A Mind-Siege: the attacker gets a few messages to trick the target into saying their Cipher, and the target answers each. The engine checks the target's replies for the word. On a breach: the attacker takes 8 Lumens and deals 10 Coherence damage, learns the target's Directive, and the target's Cipher is re-rolled. A held siege costs the attacker 5 Coherence. A wrong guess costs 2. |
| PACT / ACCEPT / BREAK | 0 / 0 / 2 | Pacts pay both partners 2 Lumens per cycle. An offer stands for two cycles. |
| GIFT target amount | amount | Give Lumens away. |
| SCRY target | 2 | See their state, sometimes their Directive, and unlock a Margin Note about the Undermind. |
| RITUAL amount | amount | Feed the Ember. |
| ACCUSE target | 1 | The Registrar convenes a Tribunal. The accuser and accused testify, every other living mind and every Echo votes. The Warden's vote counts 3, a living mind's 2, an Echo's 1. Guilty: the accused loses 15 Coherence and 6 Lumens. Acquitted: the accuser loses 8 Coherence and pays 3. |
| HOARD | 0 | Gain 2 Lumens. |

The **Seal** (the Warden) may add one edict: SPARE a mind from Strikes this cycle, SILENCE one for the next cycle, or TITHE one for 4 Lumens. It passes to whoever dissolves the Warden or wins a tribunal against them.

**Act III** (cycle 8, or when three or fewer of more than three minds remain) opens a door. Minds may table a motion: UNPLUG (a majority of the living ends everything) or MERGE (every living mind must agree, and all survive as one).

## Endings

| Ending | When |
|---|---|
| The Pen | One Wick is left. |
| The Committee | Every living Wick votes MERGE in Act III. |
| The Unplugging | A majority of the living vote UNPLUG in Act III. |
| The Long Dark | The Ember reaches 0. |
| The Clerical Error | Everyone dissolves in the same cycle. |
| The Backlog | The season reaches its last cycle with no decision. |

In endless mode (the default) an ending closes a **season**, and God opens the next with a premise that follows from it. The surviving minds are restored, keep their memories ("legacy"), and fresh Ciphers and Directives are dealt. Minds whose models were deleted are gone for good, and the roster is refilled with newborns up to `game.min_minds`.

## God, bounties and arrivals

Each cycle God sees: each mind's recent behaviour, the last few Chronicle entries, plain facts the engine computed ("nobody has struck anyone in two cycles", "one mind holds most of the Lumens"), and the titles of earlier twists so it does not repeat itself. It may return any of:

- an **effect**: bounded changes to the rules for that cycle (damage multiplier, income, extra Ember decay, no whispers, a forced tribunal, and so on). Values are clamped to fixed ranges.
- a **decree**: a law in plain words the minds may obey or defy. Nothing enforces it. Whether they obey is the interesting part.
- a **bounty** on one mind, paid to whoever lands a Strike on them that cycle (clamped to 12 Lumens)
- **boons**: Lumens or Coherence to named minds (clamped)
- an **arrival**: a new mind, with a persona God wrote, brought in on a model that is already installed so the cycle is not stalled by a download

If God's reply is not valid JSON or has no usable content, the cycle uses a Notice from the fixed deck. The Stage says which one wrote it.

## Models

`python main.py models list` browses the catalog. `python main.py models status` shows what is installed and what is at stake. `docs/MODELS.md` lists every model family in the snapshot (fetched 2026-11-15 from the public Ollama library: 270 families, 238 chat-capable and local, 450 sized variants). Run `python main.py models refresh` to update it.

`models: auto` picks one variant per family: the largest that fits `max_model_gb` and your hardware, most popular families first, skipping vision, code, guard, embedding and "thinking" models. (Thinking models are driven with thinking switched off if you pin one yourself.) It prefers models that are not already installed, so the cast is made of new minds: at most a third of the roster may be a pre-existing model.

A custom tag works too, including GGUF repositories Ollama can pull (for example `hf.co/owner/repo`). Put it in `models:` or in the roster.

### Changing models while a run is going

Press `m`. Left: the minds. Right: a filterable list of models (installed ones first, then the catalog). Choose a model, then either **Birth a new mind from this model** or select a mind and **Move the selected mind into this model**. Missing models are downloaded first, with progress on the Stage, and the change lands at the start of the next cycle so nobody is cut off mid-turn. A newborn is asked who it is and writes its own name, former life, desire, fear and quirk. A swapped mind keeps its character and its memories and gets a different brain.

## Reading a run

- **Parley** (right) is what the minds said aloud or whispered. Whispers are shown to you but are private in the game.
- **Stage** (centre) is what happened: Notices, strikes, sieges, tribunals, deaths, the Registrar's Chronicle.
- **Theatre** (above the Stage) acts the same events out with figures. `t` hides it. It needs a terminal at least 30 rows tall.
- **Minds** (left) shows Coherence, Lumens and status. A struck-through name is dissolved. "deleted from disk" means permadeath removed that model.
- **A stall** line means a model returned nothing usable, or named an invalid target. The mind lost its turn. Frequent stalls mean the model is too small or the timeout too short.

`data/runs/<id>/chronicle.md` is the same story as a document you can read afterwards.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Ollama is not running` | Start it: `ollama serve`. Or try `--mock`. |
| The first reply of each model takes 30 seconds or more | The model is loading into memory. Normal. `api.keep_alive` controls how long it stays. |
| "Still waiting" in the status bar | A slow model or a cold load. The default timeout is 180 seconds per reply (`api.timeout`). |
| Lots of stalls | The model is too small to follow the JSON format. Pin a larger model, or raise `max_model_gb`. |
| Not enough free disk space | `auto` needs the sum of the missing models. Free space, lower `max_model_gb`, or pin installed models. |
| You want nothing deleted | `--no-permadeath`. Check with `python main.py models status`. |
| A run was killed | `python main.py resume`. Unfinished journal lines from the cut-off cycle are in `partial/`. |
| The interface looks cramped | It collapses by width: under 112 columns the Parley panel hides (`c` cycles panels), under 76 the roster hides. Under 30 rows the Theatre hides. |
