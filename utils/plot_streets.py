"""Plots for the street-by-street analysis (flop -> turn -> river).

Reads a streets_<N>players_<samples>_<timestamp>.csv and saves four graphs:
  * lead conversion line chart: of the players leading after each street, how many go on to win
  * lead-rate heatmaps (flop, turn, river): how often each starting hand is leading after that
    street, on a shared colour scale so the evolution is directly comparable

Usage:
    python -m utils.plot_streets [path_to_csv]

With no argument, the most recently modified streets_*.csv in output/raw_data is used.
"""
import csv
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from utils.naming import RAW_DIR, analysis_dir
from utils.plot_hands import RANKS, cell

STREETS = ("flop", "turn", "river")
COUNT_COLUMNS = ("times_dealt", "lead_flop", "lead_turn", "lead_river", "flop_lead_won", "turn_lead_won")

# hand groups shown as separate lines in the conversion chart
GROUPS = {
    "All hands": lambda label: True,
    "Pairs": lambda label: len(label) == 2,
    "Suited": lambda label: label.endswith("s"),
    "Offsuit": lambda label: label.endswith("o"),
}


def find_csv(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    files = sorted(RAW_DIR.glob("streets_*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        sys.exit(f"No streets_*.csv found in {RAW_DIR}. Run `python main.py --streets` first.")
    return files[-1]


def load(path: Path) -> dict[str, dict[str, int]]:
    with open(path, newline="") as f:
        return {row["hand"]: {c: int(row[c]) for c in COUNT_COLUMNS} for row in csv.DictReader(f)}


def lead_rate(data: dict, street: str) -> dict[str, float]:
    """Share of deals in which each hand is leading (ties included) after `street`."""
    return {h: d[f"lead_{street}"] / d["times_dealt"] for h, d in data.items() if d["times_dealt"]}


def conversion(data: dict, group, street: str) -> float:
    """Of the players leading after `street`, the share who win the hand.
    After the river the leader is the winner, so it is 100% by definition."""
    if street == "river":
        return 1.0
    won = sum(d[f"{street}_lead_won"] for h, d in data.items() if group(h))
    led = sum(d[f"lead_{street}"] for h, d in data.items() if group(h))
    return won / led if led else float("nan")


def plot_lead_conversion(data: dict, title: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    x = range(len(STREETS))
    for name, group in GROUPS.items():
        ys = [conversion(data, group, s) for s in STREETS]
        main = name == "All hands"
        # exact values go in the legend: the groups are too close to label on the lines
        label = f"{name}: {ys[0]:.1%} \u2192 {ys[1]:.1%} \u2192 {ys[2]:.0%}"
        ax.plot(x, [y * 100 for y in ys], marker="o", linewidth=3 if main else 1.8,
                color="black" if main else None, label=label)
        if main:
            for xi, y in zip(x[:-1], ys[:-1]):
                ax.annotate(f"{y:.1%}", (xi, y * 100), textcoords="offset points",
                            xytext=(0, -18), ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(x, ["After flop", "After turn", "After river"])
    ax.set_ylabel("Leaders who win the hand (%)")
    ax.set_ylim(40, 103)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left", title="flop \u2192 turn \u2192 river")
    ax.set_title(f"{title}\nshare of players leading after each street who win the hand")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_lead_heatmap(rates: dict[str, float], street: str, vmin: float, vmax: float,
                      title: str, out: Path) -> None:
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
    cbar = fig.colorbar(im, ax=ax, label=f"Leading after the {street} (% of deals)", shrink=0.8)
    cbar.ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_streets_csv(path: Path, players: int | str | None = None) -> list[Path]:
    """Saves the conversion chart and the three lead-rate heatmaps. Returns the PNG paths."""
    path = Path(path)
    if players is None:
        m = re.search(r"(\d+)players", path.name)
        if not m:
            raise ValueError(f"Can't tell the number of players from '{path.name}'")
        players = m.group(1)
    players = int(players)

    data = load(path)
    rounds = sum(d["times_dealt"] for d in data.values()) // players  # one hand per player per round
    info = f"{players} players, {rounds:,} simulations"

    out_dir = analysis_dir(players, rounds)
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    out = out_dir / f"{path.stem}_lead_conversion.png"
    plot_lead_conversion(data, f"Lead conversion by street ({info})", out)
    outputs.append(out)

    rates = {s: lead_rate(data, s) for s in STREETS}
    values = [v for r in rates.values() for v in r.values()]
    vmin, vmax = min(values), max(values)  # same colour scale for all three streets
    for street in STREETS:
        suffix = " (= win rate)" if street == "river" else ""
        out = out_dir / f"{path.stem}_lead_rate_{street}.png"
        plot_lead_heatmap(rates[street], street, vmin, vmax,
                          f"Starting hands leading after the {street}{suffix} ({info})", out)
        outputs.append(out)
    return outputs


if __name__ == "__main__":
    for png in plot_streets_csv(find_csv(sys.argv[1] if len(sys.argv) > 1 else None)):
        print(f"Saved {png}")