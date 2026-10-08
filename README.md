# Poker Starting-Hand Simulator

A Monte Carlo simulator for Texas Hold'em that measures **how often each starting hand wins**. It plays a large number of hands, records the outcome for every pair of hole cards, and produces a CSV file plus two heatmaps (total wins and win rate) for analysis.

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
4. At showdown, each player's best five-card hand is evaluated from their seven available cards.
5. The winner is determined. Ties count as a win for every tied player.

Over many rounds, the program counts, for each of the 169 distinct starting hands, how many times it was dealt and how many times it won. The results are saved as a CSV file and visualised as two 13×13 heatmaps.

**Why two graphs?** Raw win counts are dominated by how often a hand is dealt: an offsuit hand can be dealt three times as often as its suited counterpart, so it accumulates more wins even though it is statistically weaker. The *win rate* graph removes this effect. Reading the two side by side shows both how often a hand wins and how strong it actually is.

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
│   ├── naming.py        # Output folders, timestamps, file-name labels
│   └── plot_hands.py    # Heatmap generation
├── tests/
│   └── test.py          # Evaluator, game and naming tests
├── requirements.txt     # Python dependencies
└── output/              # Created automatically on the first run
    ├── raw_data/
    └── analysis/
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
| `-p`, `--players N` | Number of players at the table (2–9). Prompted if omitted; defaults to 6. |
| `-r`, `--rounds N` | Number of rounds to simulate. Prompted if omitted. |
| `--test` | Run the test file instead of the simulation. |

**Parallelism.** The simulation is distributed across CPU cores automatically. The program uses all available cores (leaving one free on machines with more than two), and never more workers than the workload justifies, so small runs do not pay process start-up costs. Throughput is on the order of 10,000 rounds per second per core.

## Output

Every run creates new, timestamped files, so previous results are never overwritten.

```
output/
├── raw_data/
│   └── starting_hands_6players_100k_20261008_042321.csv
└── analysis/
    └── 6players/
        └── 100k/
            ├── starting_hands_6players_100k_20261008_042321_wins.png
            └── starting_hands_6players_100k_20261008_042321_win_rate.png
```

**File names** follow the pattern `starting_hands_<players>players_<rounds>_<YYYYMMDD_HHMMSS>`.
The round count is abbreviated and rounded: `1k`, `100k`, `2mln`, `3bln`. Runs whose counts round to the same label (for example 1,000 and 1,400) share a folder; the timestamp keeps their files distinct.

**CSV columns**

| Column | Description |
|--------|-------------|
| `hand` | Starting hand in standard notation (`AA`, `AKs`, `AKo`, ...) |
| `wins` | Number of times the hand won (ties count for each tied player) |
| `times_dealt` | Number of times the hand was dealt |
| `win_rate` | `wins / times_dealt` |

Rows are ordered from the strongest-looking hands to the weakest (`AA, AKs, AKo, AQs, ... 32o, 22`).

**Graphs**

- `*_wins.png`: total number of wins per starting hand.
- `*_win_rate.png`: win rate per starting hand.

Both titles state the number of players and simulations.

The graphs can also be regenerated from an existing CSV:

```bash
python -m utils.plot_hands                   # latest CSV in output/raw_data
python -m utils.plot_hands path/to/file.csv  # a specific CSV
```

## Running the tests

```bash
python main.py --test
```

The suite verifies hand classification for every category (including the ace-low straight), hand comparison and tie-breaking, the deck, starting-hand labelling, output file-name formatting, and that the optimised evaluator ranks hands identically to the reference evaluator on randomly generated hands.

## Design notes and limitations

- **No betting.** Players never fold, so every hand reaches showdown. A starting hand's win rate therefore estimates its strength against opponents who always play to the end. It is not a measure of profit in real play.
- **Two evaluators.** `best_hand` is a readable reference implementation that checks all 21 five-card combinations. `fast_score` evaluates seven cards in a single pass and is used by the simulation, giving roughly a tenfold speed-up. The test suite checks that the two always agree.
- **Statistical noise.** Each of the 169 starting hands needs many samples to produce stable estimates. With 6 players, a run of 100,000 rounds deals each hand a few thousand times; use 1 million rounds or more for smoother results.
- **Ties.** A tied hand counts as a win for every tied player, so win rates can sum to slightly more than 100% across all players in a round.

## Acknowledgements

This project was built with the help of AI. Claude (by Anthropic) was used to polish and optimise the code, including the fast hand evaluator, the multiprocessing, and the plotting. The code is covered by automated tests, but as with any AI-assisted work, it is worth reviewing and testing against your own expectations before relying on it.