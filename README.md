# Poker Starting-Hand Simulator

A Monte Carlo simulator for Texas Hold'em that measures **how often each starting hand wins**, and how a hand's prospects evolve from the flop to the turn to the river. Every run is saved in its own folder with the raw data, heatmaps, a summary chart and an `info.md` describing the simulation.

## Table of Contents

- [What the program does](#what-the-program-does)
- [Hand notation](#hand-notation)
- [Project structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Output](#output)
- [Running the tests](#running-the-tests)
- [Design notes and limitations](#design-notes-and-limitations)
- [Acknowledgements](#acknowledgements)

## What the program does

Each simulated round follows the standard Texas Hold'em deal, without betting:

1. A fresh 52-card deck is shuffled.
2. Every player receives two hole cards.
3. The board is dealt: flop (3 cards), turn (1) and river (1), with a burn card before each.
4. After the flop, the turn and the river, every player's best hand is evaluated and the **leader** is recorded: the player (or players, on a tie) holding the best hand given the cards on the table at that point.
5. After the river, the leader is the winner.

Over many rounds, the program counts for each of the 169 distinct starting hands how many times it was dealt, how many times it was leading after each street, and how many times it won. From these counts it produces:

- **Win rate:** how often a starting hand wins.
- **Lead rate:** how often a starting hand is leading after the flop and after the turn.
- **Lead conversion:** of the players leading after the flop (or the turn), the share who go on to win the hand.

Heatmaps use rates rather than raw win counts because hands are dealt with very different frequencies: an offsuit hand is dealt three times as often as its suited counterpart, so it collects more wins even though it is statistically weaker. The raw counts are kept in `raw_data.csv`.

## Hand notation

Starting hands are grouped using standard poker notation:

| Notation | Meaning | Example |
|----------|---------|---------|
| `AA`, `77` | Pocket pair | Two aces |
| `AKs` | **s**uited: both cards share the same suit | A♥ K♥ |
| `AKo` | **o**ffsuit: the cards have different suits | A♥ K♣ |

In the heatmaps, pairs sit on the diagonal, suited hands above it and offsuit hands below it.

## Project structure

```
poker/
├── main.py              # Command-line entry point
├── core/
│   └── poker.py         # Cards, deck, hand evaluators, players, game simulation
├── utils/
│   ├── naming.py        # Output folders, info.md, labels
│   └── plot_hands.py    # Heatmaps and lead-conversion chart
├── tests/
│   └── test.py          # Evaluator, game, output and naming tests
├── requirements.txt     # Python dependencies
└── output/              # Created automatically on the first run
    └── simulations/
```

## Requirements

- Python 3.10 or newer
- The packages listed in `requirements.txt`

## Installation

**1. Get the project and open a terminal in its folder**

```bash
git clone <repository-url>
cd poker
```

**2. Create a virtual environment**

```bash
python -m venv .venv
```

**3. Activate it**

| Platform | Command |
|----------|---------|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

When the environment is active, the terminal prompt is prefixed with `(.venv)`.

> **PowerShell tip:** if activation is blocked by the execution policy, run
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and try again. This only affects the current terminal session.

**4. Install the dependencies**

```bash
pip install -r requirements.txt
```

To leave the environment later, run `deactivate`.

## Usage

Run all commands from the project root, with the virtual environment active.

```bash
python main.py                    # interactive: asks for players and rounds
python main.py -p 6 -r 100000     # fully specified, no prompts
python main.py -r 1000000         # asks only for the number of players
python main.py --test             # runs the test suite instead of a simulation
python main.py --help             # shows all options
```

| Argument | Description |
|----------|-------------|
| `-p`, `--players N` | Number of players at the table (2-9). Prompted if omitted; defaults to 6. |
| `-r`, `--rounds N` | Number of rounds to simulate. Prompted if omitted. |
| `--test` | Run the test file instead of the simulation. |

**Parallelism.** The simulation is distributed across CPU cores automatically. The program uses all available cores (leaving one free on machines with more than two), and never more workers than the workload justifies, so small runs do not pay process start-up costs. Throughput is on the order of 5,000 to 10,000 rounds per second per core.

## Output

Every run creates a new folder named with a random UUID (version 4), so previous results are never overwritten:

```
output/
└── simulations/
    └── 3f2b8c1e-5a47-4d0e-9b6a-1c8d2e7f4a90/
        ├── info.md
        ├── raw_data.csv
        ├── heatmap_win_rate_river.png
        ├── heatmap_flop.png
        ├── heatmap_turn.png
        └── lead_conversion.png
```

| File | Content |
|------|---------|
| `info.md` | When the simulation was run, number of players, number of rounds, hands dealt, CPU cores used and simulation time. |
| `raw_data.csv` | The counts and rates for each of the 169 starting hands (columns below). |
| `heatmap_win_rate_river.png` | Win rate per starting hand (leading after the river is winning). |
| `heatmap_flop.png`, `heatmap_turn.png` | How often each starting hand is leading after the flop / the turn. |
| `lead_conversion.png` | Bar chart of lead conversion after the flop and after the turn, for all hands and split into pairs, suited and offsuit hands. |

The three heatmaps share the same colour scale, so they can be compared directly: the colour of a hand's cell shows how its prospects change from street to street. Chart titles state the number of players and simulations.

**`raw_data.csv` columns**

| Column | Description |
|--------|-------------|
| `hand` | Starting hand in standard notation (`AA`, `AKs`, `AKo`, ...) |
| `times_dealt` | Number of times the hand was dealt |
| `wins` | Times the hand won (ties count as a win for each tied player) |
| `win_rate` | `wins / times_dealt` |
| `lead_flop`, `lead_turn` | Times the hand was leading after the flop / the turn (ties included) |
| `lead_rate_flop`, `lead_rate_turn` | `lead_* / times_dealt` |
| `flop_lead_won`, `turn_lead_won` | Times a flop / turn lead went on to win the hand |
| `conv_rate_flop`, `conv_rate_turn` | `*_lead_won / lead_*` (0 if the hand never led) |

Rows are ordered from the strongest-looking hands to the weakest (`AA, AKs, AKo, AQs, ... 32o, 22`).

**Lead conversion** is measured only after the flop and the turn. After the river, leading and winning are the same thing, so the value would always be 100% and carries no information.

The graphs of an existing simulation can be regenerated with:

```bash
python -m utils.plot_hands                      # the most recent simulation
python -m utils.plot_hands path/to/simulation   # a specific simulation folder
```

## Running the tests

```bash
python main.py --test
```

The suite verifies hand classification for every category (including the ace-low straight), hand comparison and tie-breaking, the deck, starting-hand labelling and ordering, that the optimised evaluator ranks hands identically to the reference evaluator on randomly generated hands, that the per-street leaders match the reference evaluator, and that a full run produces the expected folder (UUID name, files, `info.md` and CSV contents).

## Design notes and limitations

- **No betting.** Players never fold, so every hand reaches showdown. A starting hand's win rate therefore estimates its strength against opponents who always play to the end. It is not a measure of profit in real play.
- **Two evaluators.** `best_hand` is a readable reference implementation that checks all 21 five-card combinations. `fast_score` evaluates up to seven cards in a single pass and is used by the simulation. The test suite checks that the two always agree.
- **Statistical noise.** Each of the 169 starting hands needs many samples to produce stable estimates. With 6 players, a run of 100,000 rounds deals each hand a few thousand times; use 1 million rounds or more for smoother results.
- **Ties.** A tied hand counts as a win and as a lead for every tied player, so win rates can sum to slightly more than 100% across all players in a round.

## Acknowledgements

This project was built with the help of AI. Claude (by Anthropic) was used to polish and optimise the code, including the fast hand evaluator, the multiprocessing, and the plotting. The code is covered by automated tests, but as with any AI-assisted work, it is worth reviewing and testing against your own expectations before relying on it.