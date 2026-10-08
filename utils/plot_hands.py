"""Graphs for one simulation, saved into that simulation's folder.

Reads <simulation folder>/raw_data.csv and saves:
  heatmap_win_rate_river.png   win rate per starting hand (= leading after the river)
  heatmap_flop.png             how often each starting hand leads after the flop
  heatmap_turn.png             how often each starting hand leads after the turn
  lead_conversion.png          of the players leading after the flop / the turn, the share who go on to win

The three heatmaps share one colour scale, so the evolution flop -> turn -> river
can be compared directly.

Usage:
    python -m utils.plot_hands [simulation_folder]

With no argument, the most recently created folder in output/simulations is used.
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from utils.naming import CSV_NAME, SIMULATIONS_DIR, read_info

RANKS = "AKQJT98765432"  # top-to-bottom / left-to-right
STREETS = ("flop", "turn", "river")
COUNT_COLUMNS = ("times_dealt", "wins", "lead_flop", "lead_turn", "flop_lead_won", "turn_lead_won")

HEATMAP_FILES = {
    "river": "heatmap_win_rate_river.png",
    "flop": "heatmap_flop.png",
    "turn": "heatmap_turn.png",
}
CONVERSION_FILE = "lead_conversion.png"

# hand groups shown as separate lines in the conversion chart
GROUPS = {
    "All hands": lambda label: True,
    "Pairs": lambda label: len(label) == 2,
    "Suited": lambda label: label.endswith("s"),
    "Offsuit": lambda label: label.endswith("o"),
}


def find_simulation(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    folders = [p for p in SIMULATIONS_DIR.glob("*") if (p / CSV_NAME).exists()]
    if not folders:
        sys.exit(f"No simulations found in {SIMULATIONS_DIR}. Run `python main.py` first.")
    return max(folders, key=lambda p: p.stat().st_mtime)


def load(folder: Path) -> dict[str, dict[str, int]]:
    with open(Path(folder) / CSV_NAME, newline="") as f:
        return {row["hand"]: {c: int(row[c]) for c in COUNT_COLUMNS} for row in csv.DictReader(f)}


def cell(label: str) -> tuple[int, int]:
    """Grid position: pairs on the diagonal, suited above it, offsuit below it."""
    r1, r2 = RANKS.index(label[0]), RANKS.index(label[1])
    if label[-1] == "o":
        return r2, r1
    return r1, r2


def lead_count(d: dict[str, int], street: str) -> int:
    """Times a hand was leading after `street`. After the river, leading means winning."""
    return d["wins"] if street == "river" else d[f"lead_{street}"]


def lead_rate(data: dict, street: str) -> dict[str, float]:
    """Share of deals in which each hand is leading (ties included) after `street`."""
    return {h: lead_count(d, street) / d["times_dealt"] for h, d in data.items() if d["times_dealt"]}


def conversion(data: dict, group, street: str) -> float:
    """Of the players leading after `street` (flop or turn), the share who go on to win the hand.
    The river is left out: leading after the river *is* winning, so it would always be 100%."""
    won = sum(d[f"{street}_lead_won"] for h, d in data.items() if group(h))
    led = sum(d[f"lead_{street}"] for h, d in data.items() if group(h))
    return won / led if led else float("nan")


def plot_heatmap(rates: dict[str, float], vmin: float, vmax: float,
                 title: str, colorbar_label: str, out: Path) -> None:
    n = len(RANKS)
    grid = np.zeros((n, n))
    names = [[""] * n for _ in range(n)]
    for label, value in rates.items():
        r, c = cell(label)
        grid[r, c] = value
        names[r][c] = label

    fig, ax = plt.subplots(figsize=(14, 12))
    im = ax.imshow(grid, cmap="YlGnBu", vmin=vmin, vmax=vmax)
    for r in range(n):
        for c in range(n):
            color = "white" if im.norm(grid[r, c]) > 0.6 else "black"
            ax.text(c, r, f"{names[r][c]}\n{grid[r, c]:.1%}", ha="center", va="center",
                    fontsize=8, color=color)
    ax.set_xticks(range(n), RANKS)
    ax.set_yticks(range(n), RANKS)
    ax.xaxis.tick_top()
    ax.set_title(f"{title}\npairs on diagonal, suited above, offsuit below", pad=40)
    cbar = fig.colorbar(im, ax=ax, label=colorbar_label, shrink=0.8)
    cbar.ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_lead_conversion(data: dict, title: str, out: Path) -> None:
    streets = ("flop", "turn")
    colors = ["#333333", "tab:blue", "tab:orange", "tab:green"]
    fig, ax = plt.subplots(figsize=(9, 6))
    width = 0.8 / len(GROUPS)
    for i, ((name, group), color) in enumerate(zip(GROUPS.items(), colors)):
        values = [conversion(data, group, s) * 100 for s in streets]
        xs = [j + (i - (len(GROUPS) - 1) / 2) * width for j in range(len(streets))]
        bars = ax.bar(xs, values, width, label=name, color=color)
        ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], padding=3, fontsize=9)
    ax.set_xticks(range(len(streets)), ["After the flop", "After the turn"])
    ax.set_ylabel("Leaders who go on to win the hand (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")
    ax.set_title(f"{title}\nshare of players leading after each street who go on to win the hand")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_simulation(folder: Path, players: int, rounds: int) -> list[Path]:
    """Saves the three heatmaps and the conversion chart into `folder`. Returns the PNG paths."""
    folder = Path(folder)
    data = load(folder)
    info = f"{players} players, {rounds:,} simulations"
    outputs = []

    rates = {s: lead_rate(data, s) for s in STREETS}
    values = [v for r in rates.values() for v in r.values()]
    vmin, vmax = min(values), max(values)  # same colour scale for all three streets

    titles = {
        "river": (f"Win rate per starting hand, after the river ({info})", "Win rate (% of deals)"),
        "flop": (f"Starting hands leading after the flop ({info})", "Leading after the flop (% of deals)"),
        "turn": (f"Starting hands leading after the turn ({info})", "Leading after the turn (% of deals)"),
    }
    for street in ("river", "flop", "turn"):
        out = folder / HEATMAP_FILES[street]
        title, label = titles[street]
        plot_heatmap(rates[street], vmin, vmax, title, label, out)
        outputs.append(out)

    out = folder / CONVERSION_FILE
    plot_lead_conversion(data, f"Lead conversion by street ({info})", out)
    outputs.append(out)
    return outputs


if __name__ == "__main__":
    folder = find_simulation(sys.argv[1] if len(sys.argv) > 1 else None)
    info = read_info(folder)
    for png in plot_simulation(folder, info["players"], info["rounds"]):
        print(f"Saved {png}")