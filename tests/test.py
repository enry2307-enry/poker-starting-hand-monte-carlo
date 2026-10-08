import csv
import random
import tempfile
import uuid
from pathlib import Path

import utils.naming as naming
from utils.naming import format_count
from core.poker import (
    Card, CardDeck, Hand, NoChipsGameSimulation, Points, Ranks, Suits,
    best_hand, hand_label, fast_score, hand_sort_key, STREETS,
)


def _parse(s: str) -> list[Card]:
    r = {"T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
    return [Card(Ranks(r.get(t[0]) or int(t[0])), Suits(t[1])) for t in s.split()]


def test_deck():
    deck = CardDeck()
    assert len(deck) == 52 and len(set(deck.cards)) == 52


def test_hand_scores():
    cases = {
        "TH JH QH KH AH": Points.ROYAL_FLUSH,
        "9H TH JH QH KH": Points.STRAIGHT_FLUSH,
        "AH 2H 3H 4H 5H": Points.STRAIGHT_FLUSH,
        "9H 9D 9C 9S 2H": Points.FOUR_OF_A_KIND,
        "9H 9D 9C 2S 2H": Points.FULL_HOUSE,
        "2H 5H 9H JH KH": Points.FLUSH,
        "AH 2D 3C 4S 5H": Points.STRAIGHT,
        "9H 9D 9C 2S 5H": Points.THREE_OF_A_KIND,
        "9H 9D 2C 2S 5H": Points.TWO_PAIR,
        "9H 9D 2C 3S 5H": Points.ONE_PAIR,
        "9H JD 2C 3S 5H": Points.HIGH_CARD,
    }
    for text, expected in cases.items():
        assert Hand(_parse(text)).score == expected, text


def test_comparisons():
    assert Hand(_parse("6H 5D 4C 3S 2H")).is_better_than(Hand(_parse("AH 2D 3C 4S 5H")))
    assert Hand(_parse("KH KD 2C 2S 5H")).compare(Hand(_parse("QH QD JC JS 5H"))) == 1
    assert Hand(_parse("9H 9D 9C 2S 2H")).compare(Hand(_parse("9H 9D 9C 2S 2H"))) == 0


def test_best_hand_of_seven():
    assert best_hand(_parse("AH KH QH JH TH 2D 3C")).score == Points.ROYAL_FLUSH


def test_hand_label():
    assert hand_label(_parse("AH KH")) == "AKs"
    assert hand_label(_parse("KD AH")) == "AKo"
    assert hand_label(_parse("7H 7C")) == "77"


def test_round_has_winner():
    winners = NoChipsGameSimulation(6).play_round()
    assert winners and all(len(w.cards) == 2 for w in winners)


def _random_hands(n: int, seed: int = 1) -> list[list[Card]]:
    """7-card hands; a third use few ranks/suits so rare categories (quads, flushes...) show up."""
    rng = random.Random(seed)
    full = CardDeck().cards
    hands = []
    for i in range(n):
        pool = full
        if i % 3 == 1:
            ranks = rng.sample(list(Ranks), rng.randint(5, 8))
            pool = [c for c in full if c.rank in ranks]
        elif i % 3 == 2:
            suits = rng.sample(list(Suits), 2)
            pool = [c for c in full if c.suit in suits]
        hands.append(rng.sample(pool, 7))
    return hands


def test_fast_score_matches_best_hand():
    scored = []
    for cards in _random_hands(1500):
        ref = best_hand(cards)
        fast = fast_score(cards)
        assert fast >> 20 == int(ref.score), cards  # same category
        scored.append((fast, ref.key()))

    # same ordering: sorted by fast score => reference keys never decrease,
    # equal fast score <=> equal reference key
    scored.sort(key=lambda x: x[0])
    for (f1, k1), (f2, k2) in zip(scored, scored[1:]):
        assert (f1 == f2) == (k1 == k2), (f1, k1, f2, k2)
        assert k1 <= k2


def test_fast_score_special_cases():
    assert fast_score(_parse("AH 2D 3C 4S 5H 9D KC")) >> 20 == Points.STRAIGHT
    assert fast_score(_parse("6H 5D 4C 3S 2H AD KC")) > fast_score(_parse("AH 2D 3C 4S 5H 9D KC"))
    assert fast_score(_parse("9H 9D 9C 2S 2H 2D KC")) >> 20 == Points.FULL_HOUSE  # two trips
    assert fast_score(_parse("9H 9D 5C 5S 2H 2D KC")) >> 20 == Points.TWO_PAIR    # three pairs
    assert fast_score(_parse("AH 2H 3H 4H 5H 9D KC")) >> 20 == Points.STRAIGHT_FLUSH
    assert fast_score(_parse("TH JH QH KH AH 2D 3C")) >> 20 == Points.ROYAL_FLUSH


def test_format_count():
    cases = {
        1: "1", 999: "999", 1_000: "1k", 1_400: "1k", 1_500: "2k", 100_000: "100k",
        999_400: "999k", 999_500: "1mln", 1_000_000: "1mln", 2_300_000: "2mln",
        999_600_000: "1bln", 3_000_000_000: "3bln", 2_500_000_000_000: "2500bln",
    }
    for n, label in cases.items():
        assert format_count(n) == label, (n, format_count(n), label)


def test_hand_sort_key():
    labels = ["22", "AKo", "AA", "AKs", "KQs", "A2s"]
    assert sorted(labels, key=hand_sort_key) == ["AA", "AKs", "AKo", "A2s", "KQs", "22"]


def test_street_leaders_match_reference():
    """Leaders after the flop / turn / river must match the slow reference evaluator."""
    sim = NoChipsGameSimulation(5)
    for _ in range(150):
        winners = sim._play(track_streets=True)
        board = sim.table.cards
        assert list(sim.leaders) == list(STREETS)
        assert sim.leaders["river"] == winners
        for street, n_board in zip(STREETS, (3, 4, 5)):
            keys = {p.name: best_hand(p.cards + board[:n_board]).key() for p in sim.players}
            top = max(keys.values())
            expected = {name for name, k in keys.items() if k == top}
            assert {p.name for p in sim.leaders[street]} == expected, street


def test_street_counts_invariants():
    rounds, players = 400, 4
    counts = NoChipsGameSimulation(players)._count_streets(rounds)
    assert sum(counts.dealt.values()) == rounds * players
    for street in STREETS:
        assert sum(counts.lead[street].values()) >= rounds  # at least one leader per round
        for label, n in counts.lead[street].items():
            assert n <= counts.dealt[label]
    for street in ("flop", "turn"):
        for label, n in counts.converted[street].items():
            assert n <= counts.lead[street][label]
    # more cards seen -> a lead is more likely to hold: turn conversion >= flop conversion overall
    flop = sum(counts.converted["flop"].values()) / sum(counts.lead["flop"].values())
    turn = sum(counts.converted["turn"].values()) / sum(counts.lead["turn"].values())
    assert 0 < flop <= turn <= 1


def test_info_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        naming.write_info(folder, run_at="2026-10-08 12:00:00", players=6,
                          rounds=1_250_000, cores=4, seconds=12.34)
        assert naming.read_info(folder) == {"players": 6, "rounds": 1_250_000}
        text = (folder / naming.INFO_NAME).read_text(encoding="utf-8")
        assert "2026-10-08 12:00:00" in text and "1,250,000" in text


def test_simulation_folder_layout():
    """One run -> one uuid4 folder with the CSV, the 4 graphs and info.md (and no wins heatmap)."""
    original = naming.SIMULATIONS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        naming.SIMULATIONS_DIR = Path(tmp)
        try:
            folder = NoChipsGameSimulation(3).simulate_and_save(300, workers=1)
        finally:
            naming.SIMULATIONS_DIR = original

        assert folder.parent == Path(tmp)
        assert uuid.UUID(folder.name).version == 4
        assert {p.name for p in folder.iterdir()} == {
            "info.md", "raw_data.csv", "heatmap_win_rate_river.png",
            "heatmap_flop.png", "heatmap_turn.png", "lead_conversion.png",
        }
        assert naming.read_info(folder) == {"players": 3, "rounds": 300}

        with open(folder / "raw_data.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        assert sum(int(r["times_dealt"]) for r in rows) == 300 * 3
        assert sum(int(r["wins"]) for r in rows) >= 300  # at least one winner per round
        for r in rows:
            assert int(r["wins"]) <= int(r["times_dealt"])
            assert abs(float(r["win_rate"]) - int(r["wins"]) / int(r["times_dealt"])) < 1e-3


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All tests passed.")