"""Output folders, run metadata (info.md) and labels shared by the other modules."""
import re
import uuid
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
SIMULATIONS_DIR = OUTPUT_DIR / "simulations"
CSV_NAME = "raw_data.csv"
INFO_NAME = "info.md"

_UNITS = ((1_000, "k"), (1_000_000, "mln"), (1_000_000_000, "bln"))


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_count(n: int) -> str:
    """Short, rounded label: 950 -> '950', 1400 -> '1k', 100_000 -> '100k',
    2_300_000 -> '2mln', 3_000_000_000 -> '3bln'."""
    if n < 1_000:
        return str(n)
    i = max(i for i, (unit, _) in enumerate(_UNITS) if n >= unit)
    unit, suffix = _UNITS[i]
    value = (2 * n + unit) // (2 * unit)  # round half up
    if value >= 1_000 and i + 1 < len(_UNITS):  # e.g. 999_600 -> 1000k -> 1mln
        value, suffix = 1, _UNITS[i + 1][1]
    return f"{value}{suffix}"


def new_simulation_dir() -> Path:
    """Creates and returns output/simulations/<uuid4>/ for a new simulation."""
    folder = SIMULATIONS_DIR / str(uuid.uuid4())
    folder.mkdir(parents=True)
    return folder


def write_info(folder: Path, *, run_at: str, players: int, rounds: int,
               cores: int, seconds: float) -> Path:
    """Writes info.md with the data of the simulation."""
    text = f"""# Simulation {folder.name}

| Field | Value |
|-------|-------|
| Run at | {run_at} |
| Players | {players} |
| Rounds | {rounds:,} |
| Hands dealt | {rounds * players:,} |
| CPU cores used | {cores} |
| Simulation time | {seconds:.1f} s |

## Contents

- `raw_data.csv`: wins, win rate, lead counts and lead conversion for each of the 169 starting hands
- `heatmap_win_rate_river.png`: win rate per starting hand (leading after the river)
- `heatmap_flop.png`: how often each starting hand leads after the flop
- `heatmap_turn.png`: how often each starting hand leads after the turn
- `lead_conversion.png`: of the players leading after the flop / the turn, the share who go on to win the hand
"""
    path = folder / INFO_NAME
    path.write_text(text, encoding="utf-8")
    return path


def read_info(folder: Path) -> dict[str, int]:
    """Reads the players and rounds back from a simulation's info.md."""
    text = (Path(folder) / INFO_NAME).read_text(encoding="utf-8")
    values = {}
    for key, field in (("players", "Players"), ("rounds", "Rounds")):
        match = re.search(rf"\|\s*{field}\s*\|\s*([\d,]+)\s*\|", text)
        if not match:
            raise ValueError(f"'{field}' not found in {Path(folder) / INFO_NAME}")
        values[key] = int(match.group(1).replace(",", ""))
    return values