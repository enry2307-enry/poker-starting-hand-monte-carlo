import random

from utils.naming import format_count
from core.poker import (
    Card, CardDeck, Hand, NoChipsGameSimulation, Points, Ranks, Suits,
    best_hand, hand_label, fast_score,
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("All tests passed.")