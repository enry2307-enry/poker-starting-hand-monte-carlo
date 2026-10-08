"""Output folders and file names shared by poker.py and plot_hands.py."""
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RAW_DIR = OUTPUT_DIR / "raw_data"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"

_UNITS = ((1_000, "k"), (1_000_000, "mln"), (1_000_000_000, "bln"))


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


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


def csv_path(players: int, rounds: int, stamp: str) -> Path:
    return RAW_DIR / f"starting_hands_{players}players_{format_count(rounds)}_{stamp}.csv"


def analysis_dir(players: int, rounds: int) -> Path:
    return ANALYSIS_DIR / f"{players}players" / format_count(rounds)