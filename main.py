import argparse
import runpy
from pathlib import Path

from core.poker import NoChipsGameSimulation, auto_workers
from utils.naming import format_count


def ask_int(prompt: str, low: int, high: int | None = None, default: int | None = None) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
            if value >= low and (high is None or value <= high):
                return value
        except ValueError:
            pass
        print(f"Please enter a whole number >= {low}" + (f" and <= {high}." if high else "."))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poker starting-hand simulation")
    parser.add_argument(
        "-p", "--players", type=int, metavar="N",
        choices=range(NoChipsGameSimulation.min_players, NoChipsGameSimulation.max_players + 1),
        help=f"number of players ({NoChipsGameSimulation.min_players}-{NoChipsGameSimulation.max_players})",
    )
    parser.add_argument("-r", "--rounds", type=int, help="number of rounds to simulate")
    parser.add_argument("--test", action="store_true",
                        help="run the test file instead of the simulation")
    args = parser.parse_args()
    if args.rounds is not None and args.rounds < 1:
        parser.error("--rounds must be a positive number")
    return args


def run_tests() -> None:
    """Runs tests/test.py as if called with `python test.py`, keeping the project root on the import path."""
    runpy.run_path(str(Path(__file__).resolve().parent / "tests" / "test.py"),
                   run_name="__main__")


def main() -> None:
    args = parse_args()
    if args.test:
        run_tests()
        return

    # Use the command-line values if given, otherwise ask.
    players = args.players or ask_int(
        f"How many players ({NoChipsGameSimulation.min_players}-{NoChipsGameSimulation.max_players}) [6]? ",
        NoChipsGameSimulation.min_players, NoChipsGameSimulation.max_players, default=6,
    )
    rounds = args.rounds or ask_int("How many rounds to simulate? ", 1)

    workers = auto_workers(rounds)
    print(f"Using {workers} core(s)...")
    folder = NoChipsGameSimulation(number_of_players=players).simulate_and_save(rounds, workers)

    print(f"Done ({format_count(rounds)} rounds). Saved to:\n  {folder}")
    for item in sorted(folder.iterdir()):
        print(f"    {item.name}")


if __name__ == "__main__":  # required: worker processes re-import this module
    main()