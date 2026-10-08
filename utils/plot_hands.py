"""Reads a starting_hands_<N>players.csv and plots two graphs: wins and win rate per starting hand.

Usage:
    python plot_hands.py [path_to_csv]

With no argument, the most recently modified starting_hands_*players.csv is used.
PNGs are saved to output/analysis/<N>players/<samples>/ as <csv_name>_wins.png and <csv_name>_win_rate.png
(the CSV name already carries the players, samples and timestamp).
"""
import csv
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .naming import RAW_DIR, analysis_dir

RANKS = "AKQJT98765432"  # top-to-bottom / left-to-right


def find_csv(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    files = sorted(RAW_DIR.glob("starting_hands_*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        sys.exit(f"No starting_hands_*.csv found in {RAW_DIR}. Run poker.py first.")
    return files[-1]


def load(path: Path) -> dict[str, dict]:
    with open(path, newline="") as f:
        return {
            row["hand"]: {"wins": int(row["wins"]), "dealt": int(row["times_dealt"]),
                          "win_rate": float(row["win_rate"])}
            for row in csv.DictReader(f)
        }


def cell(label: str) -> tuple[int, int]:
    """Grid position: pairs on the diagonal, suited above it, offsuit below it."""
    r1, r2 = RANKS.index(label[0]), RANKS.index(label[1])
    if label[-1] == "o":
        return r2, r1
    return r1, r2


def plot(data: dict[str, dict], metric: str, title: str, out: Path) -> None:
    """metric: 'wins' or 'win_rate'."""
    n = len(RANKS)
    grid = np.zeros((n, n))
    names = [[""] * n for _ in range(n)]
    for label, d in data.items():
        r, c = cell(label)
        grid[r, c] = d[metric]
        names[r][c] = label

    is_rate = metric == "win_rate"
    fig, ax = plt.subplots(figsize=(14, 12))
    im = ax.imshow(grid, cmap="YlGnBu" if is_rate else "YlOrRd")
    for r in range(n):
        for c in range(n):
            value = f"{grid[r, c]:.1%}" if is_rate else f"{int(grid[r, c])}"
            color = "white" if im.norm(grid[r, c]) > 0.6 else "black"
            ax.text(c, r, f"{names[r][c]}\n{value}", ha="center", va="center",
                    fontsize=8, color=color)

    ax.set_xticks(range(n), RANKS)
    ax.set_yticks(range(n), RANKS)
    ax.xaxis.tick_top()
    ax.set_title(f"{title}\npairs on diagonal, suited above, offsuit below", pad=40)
    cbar = fig.colorbar(im, ax=ax, label="Win rate" if is_rate else "Wins", shrink=0.8)
    if is_rate:
        cbar.ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_csv(path: Path, players: int | str | None = None) -> list[Path]:
    """Saves the wins graph and the win-rate graph for a CSV. Returns the PNG paths."""
    path = Path(path)
    if players is None:
        m = re.search(r"(\d+)players", path.name)
        if not m:
            raise ValueError(f"Can't tell the number of players from '{path.name}'")
        players = m.group(1)
    players = int(players)

    data = load(path)
    # every round deals one hand to each player
    rounds = sum(d["dealt"] for d in data.values()) // players
    info = f"{players} players, {rounds:,} simulations"

    out_dir = analysis_dir(players, rounds)
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs = []
    for metric, label in (("wins", "Wins"), ("win_rate", "Win rate")):
        out = out_dir / f"{path.stem}_{metric}.png"
        plot(data, metric, f"{label} per starting hand ({info})", out)
        outputs.append(out)
    return outputs


if __name__ == "__main__":
    for png in plot_csv(find_csv(sys.argv[1] if len(sys.argv) > 1 else None)):
        print(f"Saved {png}")