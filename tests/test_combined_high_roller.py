"""
Tests for CombinedHighRollerStrategy (Range Dice, coldest-window variant).

Covers:
- Registration and discovery
- Bet spec format (game=range-dice, range, is_in)
- All three bet-size calculators
- Mode transitions (Kelly → Harvest, Kelly → Breakout, back to Kelly)
- Stop-loss and profit-target protection rules
- Max-bet-fraction cap
- Cold range selector (_find_coldest_range / _default_range)
- Frequency histogram updates via on_bet_result
- Convenience API (initialize / on_roll_result / get_next_bet)
- Determinism given the same roll sequence
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
from collections import deque
from decimal import Decimal

import pytest

from betbot_strategies import get_strategy, list_strategies
from betbot_strategies.combined_high_roller import (
    CombinedHighRollerStrategy,
    _KELLY, _HARVEST, _BREAKOUT,
)
from betbot_strategies.base import StrategyContext, SessionLimits


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(starting_balance: str = "100.0") -> StrategyContext:
    limits = SessionLimits(symbol="btc")
    return StrategyContext(
        api=None,
        symbol="btc",
        faucet=False,
        dry_run=True,
        rng=random.Random(42),
        logger=lambda _: None,
        limits=limits,
        starting_balance=starting_balance,
        printer=lambda _: None,
    )


def _make_strategy(params: dict = None, starting_balance: str = "100.0"):
    ctx = _make_ctx(starting_balance)
    params = params or {}
    strat = CombinedHighRollerStrategy(params, ctx)
    strat.on_session_start()
    return strat


def _result(win: bool, balance: str, number: int = None) -> dict:
    r = {"win": win, "balance": balance}
    if number is not None:
        r["number"] = number
    return r


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_registered_in_registry(self):
        assert get_strategy("combined-high-roller") is CombinedHighRollerStrategy

    def test_listed_in_strategies(self):
        names = [s["name"] for s in list_strategies()]
        assert "combined-high-roller" in names

    def test_describe_returns_string(self):
        d = CombinedHighRollerStrategy.describe()
        assert isinstance(d, str) and len(d) > 10

    def test_schema_has_required_keys(self):
        schema = CombinedHighRollerStrategy.schema()
        required = {
            "range_size", "base_bet_fraction", "max_bet_fraction",
            "multiplier", "max_ladder_depth", "stop_loss", "profit_target",
            "history_window", "streak_trigger", "volatility_trigger", "min_bet",
        }
        assert required.issubset(schema.keys())

    def test_schema_no_chance_or_is_high(self):
        schema = CombinedHighRollerStrategy.schema()
        assert "chance" not in schema
        assert "is_high" not in schema


# ---------------------------------------------------------------------------
# BetSpec format
# ---------------------------------------------------------------------------

class TestBetSpec:
    def test_game_is_range_dice(self):
        s = _make_strategy()
        assert s.next_bet()["game"] == "range-dice"

    def test_has_range_tuple(self):
        s = _make_strategy()
        spec = s.next_bet()
        assert "range" in spec
        lo, hi = spec["range"]
        assert isinstance(lo, int) and isinstance(hi, int)
        assert 0 <= lo < hi <= 9999

    def test_is_in_true(self):
        s = _make_strategy()
        assert s.next_bet()["is_in"] is True

    def test_no_chance_or_is_high_in_spec(self):
        s = _make_strategy()
        spec = s.next_bet()
        assert "chance" not in spec
        assert "is_high" not in spec

    def test_amount_is_string_decimal(self):
        s = _make_strategy()
        Decimal(s.next_bet()["amount"])   # must not raise

    def test_range_size_equals_range_size_param(self):
        s = _make_strategy({"range_size": 5000})
        lo, hi = s.next_bet()["range"]
        assert hi - lo + 1 == 5000


# ---------------------------------------------------------------------------
# Cold-range selection
# ---------------------------------------------------------------------------

class TestColdRange:
    def test_default_range_is_mid_window(self):
        s = _make_strategy({"range_size": 5000})
        lo, hi = s._default_range()
        assert lo == 2500
        assert hi == 7499
        assert hi - lo + 1 == 5000

    def test_no_history_uses_default(self):
        s = _make_strategy()
        assert s._cold_range == s._default_range()

    def test_find_coldest_range_returns_correct_size(self):
        s = _make_strategy({"range_size": 5000})
        # Add some numbers to frequency
        for n in range(3000):
            s._number_freq[n] = 5          # heat up 0-2999
        lo, hi = s._find_coldest_range()
        assert hi - lo + 1 == 5000

    def test_find_coldest_range_avoids_hot_zone(self):
        """Hot zone 0-2999 → coldest 5000-slot window must start at 3000 or later."""
        s = _make_strategy({"range_size": 5000})
        for n in range(3000):
            s._number_freq[n] = 100
        lo, hi = s._find_coldest_range()
        assert lo >= 3000, f"Expected cold window to start ≥3000, got {lo}"

    def test_range_updates_after_roll(self):
        s = _make_strategy({"range_size": 5000})
        initial = s._cold_range
        # Heat up initial cold range so it shifts
        lo, hi = initial
        for n in range(lo, hi + 1):
            s._number_freq[n] = 99
        # Simulate a bet result with a number in the original cold range
        s.next_bet()
        s.on_bet_result(_result(True, "102", number=lo + 100))
        assert s._cold_range != initial

    def test_frequency_tracks_rolled_numbers(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "102", number=1234))
        assert s._number_freq.get(1234, 0) == 1
        s.next_bet()
        s.on_bet_result(_result(False, "94", number=1234))
        assert s._number_freq.get(1234, 0) == 2

    def test_number_outside_range_ignored(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "102", number=99999))
        assert 99999 not in s._number_freq

    def test_missing_number_does_not_raise(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "102"))   # no 'number' key
        # freq dict stays empty
        assert not s._number_freq


# ---------------------------------------------------------------------------
# Bet-size calculators
# ---------------------------------------------------------------------------

class TestKellyBet:
    def test_streak_0_returns_base_fraction(self):
        s = _make_strategy()
        s._win_streak = 0
        assert s.calculate_kelly_bet() == Decimal("100") * Decimal("0.08")

    def test_streak_2_returns_12_percent(self):
        s = _make_strategy()
        s._win_streak = 2
        assert s.calculate_kelly_bet() == Decimal("100") * Decimal("0.12")

    def test_streak_3_returns_18_percent(self):
        s = _make_strategy()
        s._win_streak = 3
        assert s.calculate_kelly_bet() == Decimal("100") * Decimal("0.18")

    def test_streak_overflow_clamped(self):
        s = _make_strategy()
        s._win_streak = 100
        assert s.calculate_kelly_bet() == Decimal("100") * Decimal("0.18")


class TestStreakHarvesterBet:
    def test_step_0_equals_base(self):
        s = _make_strategy()
        s._mode = _HARVEST; s._ladder_step = 0
        assert s.calculate_streak_harvester_bet() == Decimal("100") * Decimal("0.08")

    def test_step_1_doubles(self):
        s = _make_strategy()
        s._mode = _HARVEST; s._ladder_step = 1
        assert s.calculate_streak_harvester_bet() == Decimal("100") * Decimal("0.08") * 2

    def test_step_2_capped_at_max(self):
        s = _make_strategy()
        s._mode = _HARVEST; s._ladder_step = 2   # 32% → capped 20%
        assert s.calculate_streak_harvester_bet() == Decimal("100") * Decimal("0.20")


class TestBreakoutBet:
    def test_step_0_is_10_percent(self):
        s = _make_strategy()
        s._mode = _BREAKOUT; s._ladder_step = 0
        assert s.calculate_breakout_bet() == Decimal("100") * Decimal("0.10")

    def test_step_1_is_15_percent(self):
        s = _make_strategy()
        s._mode = _BREAKOUT; s._ladder_step = 1
        assert s.calculate_breakout_bet() == Decimal("100") * Decimal("0.15")

    def test_step_2_capped_at_20(self):
        s = _make_strategy()
        s._mode = _BREAKOUT; s._ladder_step = 2
        assert s.calculate_breakout_bet() == Decimal("100") * Decimal("0.20")


# ---------------------------------------------------------------------------
# Mode transitions
# ---------------------------------------------------------------------------

class TestModeTransitions:
    def test_initial_mode_is_kelly(self):
        assert _make_strategy()._mode == _KELLY

    def test_kelly_to_harvest_on_streak(self):
        s = _make_strategy()
        bal = Decimal("100")
        for _ in range(2):
            s.next_bet(); bal += 2
            s.on_bet_result(_result(True, str(bal)))
        assert s._mode == _HARVEST and s._ladder_step == 0

    def test_harvest_loss_returns_to_kelly(self):
        s = _make_strategy()
        bal = Decimal("100")
        for _ in range(2):
            s.next_bet(); bal += 2
            s.on_bet_result(_result(True, str(bal)))
        s.next_bet(); bal -= 8
        s.on_bet_result(_result(False, str(bal)))
        assert s._mode == _KELLY and s._ladder_step == 0

    def test_harvest_win_advances_ladder(self):
        s = _make_strategy()
        bal = Decimal("100")
        for _ in range(2):
            s.next_bet(); bal += 2
            s.on_bet_result(_result(True, str(bal)))
        s.next_bet(); bal += 8
        s.on_bet_result(_result(True, str(bal)))
        assert s._ladder_step == 1

    def test_harvest_full_ladder_returns_to_kelly(self):
        s = _make_strategy({"max_ladder_depth": 3, "streak_trigger": 2})
        bal = Decimal("100")
        for _ in range(2):
            s.next_bet(); bal += 2
            s.on_bet_result(_result(True, str(bal)))
        for _ in range(3):
            s.next_bet(); bal += 5
            s.on_bet_result(_result(True, str(bal)))
        assert s._mode == _KELLY

    def test_kelly_to_breakout_on_volatility(self):
        s = _make_strategy({"history_window": 6, "volatility_trigger": 4, "streak_trigger": 99})
        bal = Decimal("100")
        for w in [True, True, True, True, True, False]:
            s.next_bet(); bal += 2 if w else -8
            s.on_bet_result(_result(w, str(bal)))
        assert s._mode == _BREAKOUT

    def test_breakout_loss_returns_to_kelly(self):
        s = _make_strategy({"history_window": 6, "volatility_trigger": 4, "streak_trigger": 99})
        bal = Decimal("100")
        for w in [True, True, True, True, True, False]:
            s.next_bet(); bal += 2 if w else -8
            s.on_bet_result(_result(w, str(bal)))
        s.next_bet(); bal -= 10
        s.on_bet_result(_result(False, str(bal)))
        assert s._mode == _KELLY

    def test_win_streak_resets_on_loss(self):
        s = _make_strategy()
        bal = Decimal("100")
        for _ in range(3):
            s.next_bet(); bal += 2
            s.on_bet_result(_result(True, str(bal)))
        assert s._win_streak == 3
        s.next_bet(); bal -= 18
        s.on_bet_result(_result(False, str(bal)))
        assert s._win_streak == 0


# ---------------------------------------------------------------------------
# Bankroll protection
# ---------------------------------------------------------------------------

class TestBankrollProtection:
    def test_stop_loss_fires(self):
        s = _make_strategy({"stop_loss": 0.35})
        s._bankroll = Decimal("64")
        assert s.apply_bankroll_protection() is True

    def test_stop_loss_does_not_fire_above_floor(self):
        s = _make_strategy({"stop_loss": 0.35})
        s._bankroll = Decimal("65.1")
        assert s.apply_bankroll_protection() is False

    def test_profit_target_fires(self):
        s = _make_strategy({"profit_target": 2.0})
        s._bankroll = Decimal("200")
        assert s.apply_bankroll_protection() is True

    def test_profit_target_does_not_fire_below(self):
        s = _make_strategy({"profit_target": 2.0})
        s._bankroll = Decimal("199.99")
        assert s.apply_bankroll_protection() is False

    def test_next_bet_returns_none_when_stopped(self):
        s = _make_strategy()
        s._should_stop = True
        assert s.next_bet() is None

    def test_stop_triggered_through_full_flow(self):
        s = _make_strategy({"stop_loss": 0.35})
        s.next_bet()
        s.on_bet_result(_result(False, "60"))
        assert s.should_stop() is True
        assert s.next_bet() is None


# ---------------------------------------------------------------------------
# Max bet cap
# ---------------------------------------------------------------------------

class TestMaxBetCap:
    def test_large_fraction_capped(self):
        s = _make_strategy({"base_bet_fraction": 0.50, "max_bet_fraction": 0.20})
        bet = Decimal(s.next_bet()["amount"])
        assert bet <= Decimal("100") * Decimal("0.20")

    def test_breakout_step2_capped(self):
        s = _make_strategy({"max_bet_fraction": 0.20})
        s._mode = _BREAKOUT; s._ladder_step = 2
        assert s.calculate_breakout_bet() == Decimal("100") * Decimal("0.20")


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------

class TestConvenienceAPI:
    def test_initialize_resets_state(self):
        s = _make_strategy()
        s._win_streak = 5; s._mode = _HARVEST; s._should_stop = True
        s.initialize(200.0)
        assert s._start_bankroll == Decimal("200")
        assert s._win_streak == 0
        assert s._mode == _KELLY
        assert s._should_stop is False
        assert s._number_freq == {}

    def test_on_roll_result_win_increases_bankroll(self):
        s = _make_strategy()
        before = s._bankroll
        s.get_next_bet()
        s.on_roll_result(True)
        assert s._bankroll > before

    def test_on_roll_result_loss_decreases_bankroll(self):
        s = _make_strategy()
        before = s._bankroll
        s.get_next_bet()
        s.on_roll_result(False)
        assert s._bankroll < before

    def test_on_roll_result_with_number_updates_freq(self):
        s = _make_strategy()
        s.get_next_bet()
        s.on_roll_result(True, number=5000)
        assert s._number_freq.get(5000, 0) == 1

    def test_get_next_bet_returns_float(self):
        s = _make_strategy()
        bet = s.get_next_bet()
        assert isinstance(bet, float) and bet > 0.0

    def test_get_next_bet_returns_zero_when_stopped(self):
        s = _make_strategy()
        s._should_stop = True
        assert s.get_next_bet() == 0.0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_rolls_produce_same_bets(self):
        rolls = [(True, 1234), (False, 5678), (True, 2000), (True, 8000),
                 (False, 3000), (True, 4000), (True, 6000), (True, 9000)]
        assert _simulate_rolls(rolls) == _simulate_rolls(rolls)

    def test_different_rolls_produce_different_bets(self):
        wins  = [(True, i * 100) for i in range(5)]
        loses = [(False, i * 100) for i in range(5)]
        assert _simulate_rolls(wins) != _simulate_rolls(loses)


def _simulate_rolls(rolls: list) -> list:
    s = _make_strategy()
    bets = []
    for win, num in rolls:
        spec = s.next_bet()
        if spec is None:
            break
        bets.append((spec["amount"], spec["range"]))
        p   = s.range_size / 10000.0
        pay = Decimal(str(0.99 / p)) if p > 0 else Decimal("2")
        bet = Decimal(spec["amount"])
        profit = bet * (pay - 1) if win else -bet
        new_bal = s._bankroll + profit
        s.on_bet_result(_result(win, str(new_bal), number=num))
    return bets
