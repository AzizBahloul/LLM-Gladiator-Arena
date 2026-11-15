# Design

The interface is a terminal app (Textual and Rich). It replaces an earlier GUI that was dropped as visually weak. This page records what the new one is for and the rules it follows.

## Brief

| | |
|---|---|
| Domain | A spectator tool for a live, unscripted multi-model game. Part dashboard, part film. |
| Audience | One person watching for minutes to hours, who wants to follow who said what to whom and why it matters, and to step in occasionally (pause, swap a model). |
| Mood | **Candle-lit and bureaucratic.** A failing archive lit by one lamp. Warm near-black, paper-warm text, one amber accent. |
| Motion | Expressive in the Theatre (figures walk, strike, flinch), restrained everywhere else. The Ember gauge eases rather than jumps. |
| Layout | Stage leads and takes the remaining width. Minds are a narrow column. Parley sits beside the Stage. The Theatre sits above the Stage. |
| Constraint | A terminal: no images, no hover, 80 to 200 columns. Colour comes from half-block pixels and text styles only. |

Assumption to flag: the design brief was inferred from the game itself rather than gathered in an interview with you. If you want the look pushed somewhere else, the tokens below are the one place to change.

## Rules the interface follows

- **One accent, one danger.** Amber (`ember`) is used for the Ember, the Registrar and the Seal. A red (`danger`) is used only for lost Coherence, dissolution and deleted models. Nothing else is coloured for emphasis.
- **Speaker hues are for telling voices apart**, taken from each persona, deliberately moved away from amber and red so they never read as status.
- **No emoji.** Status is words ("warded", "silenced", "Echo, 2 hauntings left"), not icons or colour alone. A test fails the build if one appears.
- **No coloured one-sided borders.** Panels use a full hairline border. The focused panel's border turns amber.
- **Contrast is measured.** Every text pair in `arena/ui/theme.py` is checked in `tests/test_design.py` at 4.5:1 or better.
- **It collapses by width, not by shrinking.** At 112 columns or more everything shows. Under 112 the Parley panel hides and `c` cycles to it. Under 76 the roster hides too. Under 30 rows the Theatre hides, and `t` toggles it.
- **Plain language for state.** "The current model call finishes first. Press p to resume." not "Pausing...". "Still waiting. A model that has not been used yet can take a minute to load." after 45 seconds.

## Tokens

All in `arena/ui/theme.py`, exposed to Textual CSS as `$u-<name>`.

| Token | Value | Use |
|---|---|---|
| `bg` | `#14120f` | Screen |
| `surface` | `#1b1814` | Panels |
| `raised` | `#26221b` | Selected and hovered rows |
| `line` | `#3f382c` | Hairlines |
| `text` | `#ece4d3` | Primary text |
| `muted` | `#a69d8a` | Secondary text |
| `faint` | `#8a8272` | Tertiary text, still legible |
| `ember` | `#f2a550` | The one accent |
| `ember_low` | `#c9782a` | Ember gauge under half |
| `danger` | `#e8695c` | Lost Coherence, dissolution, deletion |
| `ok` | `#9cbf8f` | Healthy Coherence bars only |
| `track` | `#322d24` | Bar track |

Measured contrast: text on surface 13.98, muted 6.58, faint 4.65, ember 8.65, danger 5.56, and every persona colour at least 7.1 on both `bg` and `surface`.

## The Theatre

`arena/ui/theatre.py` renders the cast as procedural pixel figures with half-block characters (two pixels per cell). Each persona has its own silhouette and palette, and guest minds get a generic figure in their own colour. Events become beats: speech opens a bubble over the speaker, strikes show a damage number, sieges send the attacker across the stage to the defender, minds carry Coherence bars, and the lamp on the back wall dims as the Ember falls. Dissolved minds fade, and Echoes remain as ghosts.

The Theatre also does the pacing. It holds each event while the figures act it out, then lets the game continue. Pending beats are capped so a fast game cannot queue up a backlog, and votes, stalls and margin notes are dropped first. The `-` and `+` keys scale the hold times, and at the fastest setting the holds are skipped.

Known limits: with eight minds the figures stagger into two rows and can touch, and during a siege the attacker walks through any bystander standing between the pair.

## The model picker

`m` opens a modal over the run: minds on the left (name, current model, "protected" or "at stake"), a filter box and model list on the right (installed first, then the catalog with size and a one-line description), and three buttons. It is keyboard-reachable end to end. Escape closes it.
