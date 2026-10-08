from __future__ import annotations

import csv
import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, IntEnum, unique
from itertools import combinations
from pathlib import Path

from utils.naming import CSV_NAME, new_simulation_dir, timestamp, write_info


# ==============
# ENUMS
# ==============

@unique
class Suits(Enum):
    HEARTS = "H"
    DIAMONDS = "D"
    CLUBS = "C"
    SPADES = "S"


@unique
class Ranks(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


@unique
class Points(IntEnum):
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


# ==============
# DATA-CLASSES
# ==============

@dataclass(frozen=True)
class Card:
    rank: Ranks
    suit: Suits

    def __str__(self) -> str:
        symbols = {10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}
        return f"{symbols.get(int(self.rank), int(self.rank))}{self.suit.value}"

    __repr__ = __str__


# ==============
# CLASSES
# ==============

class ScoreEvaluator:
    def __init__(self, cards: list[Card]):
        if len(cards) != 5:
            raise ValueError("Need exactly 5 cards")
        self.cards = sorted(cards, key=lambda c: c.rank)
        self.ranks = [int(c.rank) for c in self.cards]
        self.rank_counts = Counter(self.ranks)
        self.counts = sorted(self.rank_counts.values(), reverse=True)

    def _is_flush(self) -> bool:
        return len({c.suit for c in self.cards}) == 1

    def _is_ace_low(self) -> bool:
        return self.ranks == [2, 3, 4, 5, 14]

    def _is_straight(self) -> bool:
        if self._is_ace_low():
            return True
        return len(set(self.ranks)) == 5 and self.ranks[4] - self.ranks[0] == 4

    def run(self) -> Points:
        flush, straight = self._is_flush(), self._is_straight()
        if flush and straight:
            return Points.ROYAL_FLUSH if self.ranks[0] == Ranks.TEN else Points.STRAIGHT_FLUSH
        if self.counts == [4, 1]:
            return Points.FOUR_OF_A_KIND
        if self.counts == [3, 2]:
            return Points.FULL_HOUSE
        if flush:
            return Points.FLUSH
        if straight:
            return Points.STRAIGHT
        if self.counts == [3, 1, 1]:
            return Points.THREE_OF_A_KIND
        if self.counts == [2, 2, 1]:
            return Points.TWO_PAIR
        if self.counts == [2, 1, 1, 1]:
            return Points.ONE_PAIR
        return Points.HIGH_CARD

    def tiebreak(self) -> list[int]:
        if self._is_ace_low():
            return [5, 4, 3, 2, 1]
        # Order by group size first, then rank (e.g. full house: trips, then pair)
        return sorted(self.rank_counts, key=lambda r: (self.rank_counts[r], r), reverse=True)


class Hand:
    def __init__(self, cards: list[Card]):
        if len(cards) != 5:
            raise ValueError("Need exactly 5 cards")
        evaluator = ScoreEvaluator(cards)
        self.cards = list(cards)
        self.score = evaluator.run()
        self.tiebreak = evaluator.tiebreak()

    def key(self) -> tuple[int, list[int]]:
        return (int(self.score), self.tiebreak)

    def compare(self, other: Hand) -> int:
        """Returns 1 if self wins, -1 if other wins, 0 on tie."""
        a, b = self.key(), other.key()
        return (a > b) - (a < b)

    def is_better_than(self, other: Hand) -> bool:
        return self.key() > other.key()

    def __str__(self) -> str:
        return f"{' '.join(map(str, self.cards))} -> {self.score.name}"


def best_hand(cards: list[Card]) -> Hand:
    """Best 5-card hand from 5 or more cards (e.g. 7 in Texas Hold'em)."""
    if len(cards) < 5:
        raise ValueError("Need at least 5 cards")
    return max((Hand(list(c)) for c in combinations(cards, 5)), key=Hand.key)


# ---- Fast 7-card evaluator -------------------------------------------------
# Scores a hand of 5+ cards in a single pass, with no 5-card combinations.
# Returns an int: category in the top bits, then the tiebreak ranks (4 bits each).
# It ranks hands exactly like best_hand() (checked in test_poker.py), so
# a higher int always means a better hand.

_SUIT_INDEX = {suit: i for i, suit in enumerate(Suits)}
_RANKS_DESC = range(14, 1, -1)


def _pack(category: int, ranks: list[int]) -> int:
    score = category << 20
    for i, r in enumerate(ranks):
        score |= r << (16 - 4 * i)
    return score


def _straight_high(mask: int) -> int:
    """Highest card of the best straight in a rank bitmask, or 0 (ace counts low too)."""
    if mask & (1 << 14):
        mask |= 1 << 1
    run = mask & (mask >> 1) & (mask >> 2) & (mask >> 3) & (mask >> 4)
    return run.bit_length() + 3 if run else 0


def fast_score(cards: list[Card]) -> int:
    counts = [0] * 15
    suit_masks = [0, 0, 0, 0]
    for c in cards:
        counts[c.rank] += 1
        suit_masks[_SUIT_INDEX[c.suit]] |= 1 << c.rank

    flush_mask = 0
    for m in suit_masks:
        if m.bit_count() >= 5:
            flush_mask = m
            break

    if flush_mask:
        high = _straight_high(flush_mask)
        if high:
            return _pack(10 if high == 14 else 9, [high])

    fours, threes, pairs, singles = [], [], [], []
    rank_mask = 0
    for r in _RANKS_DESC:
        n = counts[r]
        if n:
            rank_mask |= 1 << r
            if n == 4:
                fours.append(r)
            elif n == 3:
                threes.append(r)
            elif n == 2:
                pairs.append(r)
            else:
                singles.append(r)

    if fours:
        rest = threes[:1] + pairs[:1] + singles[:1]
        return _pack(8, [fours[0], max(rest)])

    if threes and (len(threes) > 1 or pairs):
        second = max(threes[1] if len(threes) > 1 else 0, pairs[0] if pairs else 0)
        return _pack(7, [threes[0], second])

    if flush_mask:
        top5 = [r for r in _RANKS_DESC if flush_mask >> r & 1][:5]
        return _pack(6, top5)

    high = _straight_high(rank_mask)
    if high:
        return _pack(5, [high])

    if threes:
        return _pack(4, [threes[0]] + sorted(pairs + singles, reverse=True)[:2])

    if len(pairs) >= 2:
        leftover = max(pairs[2] if len(pairs) > 2 else 0, singles[0] if singles else 0)
        return _pack(3, [pairs[0], pairs[1], leftover])

    if pairs:
        return _pack(2, [pairs[0]] + singles[:3])

    return _pack(1, singles[:5])



class CardDeck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in Suits for rank in Ranks]

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def deal(self, n: int = 1) -> list[Card]:
        if n > len(self.cards):
            raise ValueError("Not enough cards in deck")
        dealt, self.cards = self.cards[:n], self.cards[n:]
        return dealt

    def __len__(self) -> int:
        return len(self.cards)


class CardHolder:
    max_cards: int

    def __init__(self):
        self.cards: list[Card] = []

    def receive(self, cards: list[Card]) -> None:
        if len(self.cards) + len(cards) > self.max_cards:
            raise ValueError(f"Cannot hold more than {self.max_cards} cards")
        self.cards.extend(cards)

    def give_all(self) -> list[Card]:
        cards, self.cards = self.cards, []
        return cards


class Player(CardHolder):
    max_cards = 2

    def __init__(self, name: str, chips: int = 1000):
        super().__init__()
        self.name = name
        self.chips = chips

    def __str__(self) -> str:
        return self.name


class Table(CardHolder):
    max_cards = 5


class GameStep(Enum):
    NOT_STARTED = 0
    PRE_FLOP = 1
    FLOP = 2
    TURN = 3
    RIVER = 4
    SHOWDOWN = 5


@dataclass
class Winner:
    player: Player
    cards: list[Card]  # the player's 2 hole cards
    hand: Hand         # best 5-card hand

    def __str__(self) -> str:
        return f"{self.player} with {' '.join(map(str, self.cards))} ({self.hand.score.name})"


def hand_label(cards: list[Card]) -> str:
    """Canonical 2-card label: 'AA' (pair), 'AKs' (suited), 'AKo' (offsuit)."""
    sym = {10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}
    a, b = sorted(cards, key=lambda c: c.rank, reverse=True)
    r1, r2 = (sym.get(int(c.rank), str(int(c.rank))) for c in (a, b))
    if a.rank == b.rank:
        return r1 + r2
    return r1 + r2 + ("s" if a.suit == b.suit else "o")


_RANK_ORDER = "23456789TJQKA"


def hand_sort_key(label: str) -> tuple[int, int, bool]:
    """Orders hands high card first, then low card; suited before offsuit (AA, AKs, AKo, AQs, ...)."""
    return (-_RANK_ORDER.index(label[0]), -_RANK_ORDER.index(label[1]), label[-1] != "s")


STREETS = ("flop", "turn", "river")


@dataclass
class StreetCounts:
    """Per starting hand: how often it was dealt, how often it was leading after each
    street, and how often a flop/turn lead went on to win the hand."""
    dealt: Counter = field(default_factory=Counter)
    lead: dict = field(default_factory=lambda: {s: Counter() for s in STREETS})
    converted: dict = field(default_factory=lambda: {s: Counter() for s in STREETS[:2]})

    def merge(self, other: StreetCounts) -> None:
        self.dealt.update(other.dealt)
        for street in STREETS:
            self.lead[street].update(other.lead[street])
        for street in self.converted:
            self.converted[street].update(other.converted[street])


class NoChipsGameSimulation:
    min_players = 2
    max_players = 9

    def __init__(self, number_of_players: int = 6):
        if not self.min_players <= number_of_players <= self.max_players:
            raise ValueError(
                f"Players must be between {self.min_players} and {self.max_players}"
            )
        self.game_step = GameStep.NOT_STARTED
        self.players = [Player(f"Player {i + 1}") for i in range(number_of_players)]
        self.table = Table()
        self.deck = CardDeck()
        self.leaders: dict[str, list[Player]] = {}  # filled by _play(track_streets=True)

    def _reset(self) -> None:
        for p in self.players:
            p.give_all()
        self.table.give_all()
        self.deck = CardDeck()
        self.deck.shuffle()
        self.game_step = GameStep.NOT_STARTED

    def _deal_to_table(self, n: int) -> None:
        self.deck.deal(1)  # burn card
        self.table.receive(self.deck.deal(n))

    def _leaders(self) -> list[Player]:
        """Player(s) with the best hand given the cards on the table right now (ties included)."""
        board = self.table.cards
        scores = [fast_score(p.cards + board) for p in self.players]
        top = max(scores)
        return [p for p, sc in zip(self.players, scores) if sc == top]

    def _play(self, track_streets: bool = False) -> list[Player]:
        """Plays one full hand using the fast evaluator. Returns the winning player(s).
        With track_streets=True, `self.leaders` also holds who was ahead after the
        flop, turn and river."""
        self._reset()
        self.leaders = {}

        self.game_step = GameStep.PRE_FLOP
        for p in self.players:
            p.receive(self.deck.deal(2))

        self.game_step = GameStep.FLOP
        self._deal_to_table(3)
        if track_streets:
            self.leaders["flop"] = self._leaders()
        self.game_step = GameStep.TURN
        self._deal_to_table(1)
        if track_streets:
            self.leaders["turn"] = self._leaders()
        self.game_step = GameStep.RIVER
        self._deal_to_table(1)

        self.game_step = GameStep.SHOWDOWN
        winners = self._leaders()
        if track_streets:
            self.leaders["river"] = winners
        return winners

    def play_round(self) -> list[Winner]:
        """Plays one full hand. Returns the winner(s) with their best 5-card hand; several on a tie."""
        return [
            Winner(p, list(p.cards), best_hand(p.cards + self.table.cards))
            for p in self._play()
        ]

    def simulate(self, rounds: int) -> Counter:
        """Runs many rounds; returns wins per player name (ties count for each)."""
        wins: Counter = Counter()
        for _ in range(rounds):
            for p in self._play():
                wins[p.name] += 1
        return wins

    def _count_streets(self, rounds: int) -> StreetCounts:
        """Plays `rounds` hands tracking who leads after each street, per starting hand."""
        counts = StreetCounts()
        for _ in range(rounds):
            winners = set(self._play(track_streets=True))
            labels = {p: hand_label(p.cards) for p in self.players}
            for p in self.players:
                counts.dealt[labels[p]] += 1
            for street in STREETS:
                for p in self.leaders[street]:
                    counts.lead[street][labels[p]] += 1
                    if street != "river" and p in winners:
                        counts.converted[street][labels[p]] += 1
        return counts

    @staticmethod
    def _resolve_workers(rounds: int, workers: int | None) -> int:
        return max(1, min(workers or auto_workers(rounds), rounds))

    def _distribute(self, rounds: int, workers: int, worker) -> list:
        """Splits `rounds` across `workers` processes; returns each process's result."""
        if workers == 1:
            return [worker(len(self.players), rounds)]
        base, extra = divmod(rounds, workers)
        chunks = [base + (i < extra) for i in range(workers)]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(worker, [len(self.players)] * workers, chunks))

    @staticmethod
    def _write_csv(total: StreetCounts, path: Path) -> None:
        def rate(num: int, den: int) -> float:
            return round(num / den, 4) if den else 0.0

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "hand", "times_dealt", "wins", "win_rate",
                "lead_flop", "lead_turn", "lead_rate_flop", "lead_rate_turn",
                "flop_lead_won", "turn_lead_won", "conv_rate_flop", "conv_rate_turn",
            ])
            for label in sorted(total.dealt, key=hand_sort_key):
                d = total.dealt[label]
                wins = total.lead["river"][label]  # leading after the river = winning
                lf, lt = total.lead["flop"][label], total.lead["turn"][label]
                fw, tw = total.converted["flop"][label], total.converted["turn"][label]
                writer.writerow([
                    label, d, wins, rate(wins, d),
                    lf, lt, rate(lf, d), rate(lt, d),
                    fw, tw, rate(fw, lf), rate(tw, lt),
                ])

    def simulate_and_save(self, rounds: int, workers: int | None = None) -> Path:
        """Runs `rounds` hands (in parallel) and saves everything for the simulation into
        its own folder, output/simulations/<uuid4>/:
        raw_data.csv, the heatmaps (win rate / flop / turn), the lead-conversion chart and info.md.
        `workers=None` picks the core count automatically. Returns the folder path.

        Ties count as a win (and as a lead) for each tied player."""
        run_at = timestamp()
        workers = self._resolve_workers(rounds, workers)

        started = time.perf_counter()
        total = StreetCounts()
        for part in self._distribute(rounds, workers, _street_worker):
            total.merge(part)
        seconds = time.perf_counter() - started

        folder = new_simulation_dir()
        self._write_csv(total, folder / CSV_NAME)

        # lazy import: matplotlib is only needed here
        from utils.plot_hands import plot_simulation
        plot_simulation(folder, len(self.players), rounds)

        write_info(folder, run_at=run_at, players=len(self.players), rounds=rounds,
                   cores=workers, seconds=seconds)
        return folder


MIN_ROUNDS_PER_WORKER = 2_000  # below this, process start-up costs more than it saves


def auto_workers(rounds: int) -> int:
    """Cores to use: all available (one left free if >2), but never more than
    the workload justifies."""
    try:
        cpus = len(os.sched_getaffinity(0))  # respects container/CPU limits
    except AttributeError:
        cpus = os.cpu_count() or 1
    if cpus > 2:
        cpus -= 1  # keep one core free for the OS / terminal
    return max(1, min(cpus, rounds // MIN_ROUNDS_PER_WORKER))


def _street_worker(number_of_players: int, rounds: int) -> StreetCounts:
    random.seed()
    return NoChipsGameSimulation(number_of_players)._count_streets(rounds)