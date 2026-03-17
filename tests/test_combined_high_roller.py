"""
Tests for CombinedHighRollerStrategy.

Covers:
- Registration and discovery
- All three bet-size calculators
- Mode transitions (Kelly → Harvest, Kelly → Breakout, back to Kelly)
- Stop-loss and profit-target protection rules
- Max-bet-fraction cap
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
    """Build a minimal StrategyContext for testing."""
    limits = SessionLimits(symbol="btc")
    return StrategyContext(
        api=None,  # not needed for unit tests
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


def _result(win: bool, balance: str) -> dict:
    return {"win": win, "balance": balance}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_registered_in_registry(self):
        strat_cls = get_strategy("combined-high-roller")
        assert strat_cls is CombinedHighRollerStrategy

    def test_listed_in_strategies(self):
        names = [s["name"] for s in list_strategies()]
        assert "combined-high-roller" in names

    def test_describe_returns_string(self):
        assert isinstance(CombinedHighRollerStrategy.describe(), str)
        assert len(CombinedHighRollerStrategy.describe()) > 10

    def test_schema_has_required_keys(self):
        schema = CombinedHighRollerStrategy.schema()
        required = {
            "chance", "is_high", "base_bet_fraction", "max_bet_fraction",
            "multiplier", "max_ladder_depth", "stop_loss", "profit_target",
            "history_window", "streak_trigger", "volatility_trigger", "min_bet",
        }
        assert required.issubset(schema.keys())


# ---------------------------------------------------------------------------
# Bet-size calculators
# ---------------------------------------------------------------------------

class TestKellyBet:
    def test_streak_0_returns_base_fraction(self):
        s = _make_strategy()
        s._win_streak = 0
        bet = s.calculate_kelly_bet()
        assert bet == Decimal("100") * Decimal("0.08")

    def test_streak_1_returns_base_fraction(self):
        s = _make_strategy()
        s._win_streak = 1
        bet = s.calculate_kelly_bet()
        assert bet == Decimal("100") * Decimal("0.08")

    def test_streak_2_returns_12_percent(self):
        s = _make_strategy()
        s._win_streak = 2
        bet = s.calculate_kelly_bet()
        assert bet == Decimal("100") * Decimal("0.12")

    def test_streak_3_returns_18_percent(self):
        s = _make_strategy()
        s._win_streak = 3
        bet = s.calculate_kelly_bet()
        assert bet == Decimal("100") * Decimal("0.18")

    def test_streak_10_still_returns_18_percent(self):
        s = _make_strategy()
        s._win_streak = 10
        bet = s.calculate_kelly_bet()
        assert bet == Decimal("100") * Decimal("0.18")


class TestStreakHarvesterBet:
    def test_step_0_equals_base_fraction(self):
        s = _make_strategy()
        s._mode = _HARVEST
        s._ladder_step = 0
        bet = s.calculate_streak_harvester_bet()
        assert bet == Decimal("100") * Decimal("0.08")

    def test_step_1_doubles(self):
        s = _make_strategy()
        s._mode = _HARVEST
        s._ladder_step = 1
        bet = s.calculate_streak_harvester_bet()
        expected = Decimal("100") * Decimal("0.08") * Decimal("2")
        assert bet == expected

    def test_step_2_caps_at_max_bet_fraction(self):
        """Step 2 = 32% but cap is 20%, so result should be 20."""
        s = _make_strategy()
        s._mode = _HARVEST
        s._ladder_step = 2
        bet = s.calculate_streak_harvester_bet()
        assert bet == Decimal("100") * Decimal("0.20")


class TestBreakoutBet:
    def test_step_0_is_10_percent(self):
        s = _make_strategy()
        s._mode = _BREAKOUT
        s._ladder_step = 0
        bet = s.calculate_breakout_bet()
        assert bet == Decimal("100") * Decimal("0.10")

    def test_step_1_is_15_percent(self):
        s = _make_strategy()
        s._mode = _BREAKOUT
        s._ladder_step = 1
        bet = s.calculate_breakout_bet()
        assert bet == Decimal("100") * Decimal("0.15")

    def test_step_2_capped_at_20_percent(self):
        """22% > 20% cap → should be 20%."""
        s = _make_strategy()
        s._mode = _BREAKOUT
        s._ladder_step = 2
        bet = s.calculate_breakout_bet()
        assert bet == Decimal("100") * Decimal("0.20")


# ---------------------------------------------------------------------------
# Mode transitions
# ---------------------------------------------------------------------------

class TestModeTransitions:
    def test_initial_mode_is_kelly(self):
        s = _make_strategy()
        assert s._mode == _KELLY

    def test_kelly_to_harvest_on_streak(self):
        """After streak_trigger=2 consecutive wins, mode must switch to HARVEST."""
        s = _make_strategy()
        bal = Decimal("100")
        for _ in range(2):
            s.next_bet()
            bal += Decimal("2")
            s.on_bet_result(_result(True, str(bal)))
        assert s._mode == _HARVEST
        assert s._ladder_step == 0

    def test_harvest_loss_returns_to_kelly(self):
        s = _make_strategy()
        bal = Decimal("100")
        # Enter HARVEST
        for _ in range(2):
            s.next_bet()
            bal += Decimal("2")
            s.on_bet_result(_result(True, str(bal)))
        assert s._mode == _HARVEST
        # One loss
        s.next_bet()
        bal -= Decimal("8")
        s.on_bet_result(_result(False, str(bal)))
        assert s._mode == _KELLY
        assert s._ladder_step == 0

    def test_harvest_win_advances_ladder(self):
        s = _make_strategy()
        bal = Decimal("100")
        # Enter HARVEST with 2 wins
        for _ in range(2):
            s.next_bet()
            bal += Decimal("2")
            s.on_bet_result(_result(True, str(bal)))
        assert s._mode == _HARVEST
        assert s._ladder_step == 0
        # One more win → step 1
        s.next_bet()
        bal += Decimal("8")
        s.on_bet_result(_result(True, str(bal)))
        assert s._ladder_step == 1

    def test_harvest_full_ladder_returns_to_kelly(self):
        """Winning all max_ladder_depth steps should return to Kelly."""
        s = _make_strategy({"max_ladder_depth": 3, "streak_trigger": 2})
        bal = Decimal("100")
        # 2 wins → enter HARVEST at step 0
        for _ in range(2):
            s.next_bet(); bal += Decimal("2")
            s.on_bet_result(_result(True, str(bal)))
        assert s._mode == _HARVEST
        # Win through full 3-step ladder (steps 0 → 1 → 2 → done)
        for _ in range(3):
            s.next_bet(); bal += Decimal("5")
            s.on_bet_result(_result(True, str(bal)))
        assert s._mode == _KELLY

    def test_kelly_to_breakout_on_volatility(self):
        """history_window=6, volatility_trigger=4: 5 wins + 1 loss → imbalance=4."""
        s = _make_strategy({"history_window": 6, "volatility_trigger": 4, "streak_trigger": 99})
        bal = Decimal("100")
        wins   = [True, True, True, True, True]
        losses = [False]
        for w in wins + losses:
            s.next_bet(); bal += Decimal("2") if w else Decimal("-8")
            s.on_bet_result(_result(w, str(bal)))
        assert s._mode == _BREAKOUT

    def test_breakout_loss_returns_to_kelly(self):
        s = _make_strategy({"history_window": 6, "volatility_trigger": 4, "streak_trigger": 99})
        bal = Decimal("100")
        # Trigger breakout
        for w in [True, True, True, True, True, False]:
            s.next_bet(); bal += Decimal("2") if w else Decimal("-8")
            s.on_bet_result(_result(w, str(bal)))
        assert s._mode == _BREAKOUT
        # Enter breakout bet, then lose
        s.next_bet(); bal -= Decimal("10")
        s.on_bet_result(_result(False, str(bal)))
        assert s._mode == _KELLY

    def test_breakout_win_advances_step(self):
        s = _make_strategy({"history_window": 6, "volatility_trigger": 4, "streak_trigger": 99})
        bal = Decimal("100")
        for w in [True, True, True, True, True, False]:
            s.next_bet(); bal += Decimal("2") if w else Decimal("-8")
            s.on_bet_result(_result(w, str(bal)))
        assert s._mode == _BREAKOUT and s._ladder_step == 0
        s.next_bet(); bal += Decimal("10")
        s.on_bet_result(_result(True, str(bal)))
        assert s._ladder_step == 1

    def test_win_streak_resets_on_loss(self):
        s = _make_strategy()
        bal = Decimal("100")
        for _ in range(3):
            s.next_bet(); bal += Decimal("2")
            s.on_bet_result(_result(True, str(bal)))
        assert s._win_streak == 3
        s.next_bet(); bal -= Decimal("18")
        s.on_bet_result(_result(False, str(bal)))
        assert s._win_streak == 0


# ---------------------------------------------------------------------------
# Bankroll protection
# ---------------------------------------------------------------------------

class TestBankrollProtection:
    def test_stop_loss_fires(self):
        s = _make_strategy({"stop_loss": 0.35})
        # start=100, floor=65; set bankroll to 64
        s._bankroll = Decimal("64")
        assert s.apply_bankroll_protection() is True
        assert s._should_stop is False  # not yet called via on_bet_result

    def test_stop_loss_does_not_fire_at_threshold(self):
        s = _make_strategy({"stop_loss": 0.35})
        s._bankroll = Decimal("65.1")
        assert s.apply_bankroll_protection() is False

    def test_profit_target_fires(self):
        s = _make_strategy({"profit_target": 2.0})
        s._bankroll = Decimal("200")
        assert s.apply_bankroll_protection() is True

    def test_profit_target_does_not_fire_below_target(self):
        s = _make_strategy({"profit_target": 2.0})
        s._bankroll = Decimal("199.99")
        assert s.apply_bankroll_protection() is False

    def test_next_bet_returns_none_after_stop(self):
        s = _make_strategy({"stop_loss": 0.35})
        # Drive balance below stop floor via on_bet_result
        s._bankroll = Decimal("64")
        s.on_bet_result(_result(False, "64"))
        assert s.should_stop() is True
        assert s.next_bet() is None

    def test_stop_triggered_through_full_flow(self):
        """Loss that crosses stop-loss floor must halt the session."""
        s = _make_strategy({"stop_loss": 0.35})
        # start=100, floor=65
        s.next_bet()
        s.on_bet_result(_result(False, "60"))
        assert s.should_stop() is True
        assert s.next_bet() is None


# ---------------------------------------------------------------------------
# Max bet fraction cap
# ---------------------------------------------------------------------------

class TestMaxBetCap:
    def test_bet_never_exceeds_cap(self):
        params = {
            "base_bet_fraction": 0.50,  # absurdly large
            "max_bet_fraction": 0.20,
        }
        s = _make_strategy(params)
        spec = s.next_bet()
        bet = Decimal(spec["amount"])
        cap = Decimal("100") * Decimal("0.20")
        assert bet <= cap

    def test_breakout_step2_capped(self):
        s = _make_strategy({"max_bet_fraction": 0.20})
        s._mode = _BREAKOUT
        s._ladder_step = 2  # 22% → must be capped to 20%
        bet = s.calculate_breakout_bet()
        assert bet == Decimal("100") * Decimal("0.20")


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------

class TestConvenienceAPI:
    def test_initialize_resets_state(self):
        s = _make_strategy()
        # Dirty state
        s._win_streak = 5
        s._mode = _HARVEST
        s._should_stop = True

        s.initialize(200.0)
        assert s._start_bankroll == Decimal("200")
        assert s._bankroll       == Decimal("200")
        assert s._win_streak     == 0
        assert s._mode           == _KELLY
        assert s._should_stop    is False

    def test_on_roll_result_win_increases_bankroll(self):
        s = _make_strategy()
        before = s._bankroll
        s.get_next_bet()         # sets _last_bet_amount
        s.on_roll_result(True)
        assert s._bankroll > before

    def test_on_roll_result_loss_decreases_bankroll(self):
        s = _make_strategy()
        before = s._bankroll
        s.get_next_bet()
        s.on_roll_result(False)
        assert s._bankroll < before

    def test_get_next_bet_returns_float(self):
        s = _make_strategy()
        bet = s.get_next_bet()
        assert isinstance(bet, float)
        assert bet > 0.0

    def test_get_next_bet_returns_zero_when_stopped(self):
        s = _make_strategy()
        s._should_stop = True
        assert s.get_next_bet() == 0.0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_rolls_produce_same_bets(self):
        rolls = [True, False, True, True, False, True, True, True]
        bets_a = _simulate_rolls(rolls)
        bets_b = _simulate_rolls(rolls)
        assert bets_a == bets_b

    def test_different_rolls_produce_different_bets(self):
        rolls_a = [True, True, True, True]
        rolls_b = [False, False, False, False]
        bets_a = _simulate_rolls(rolls_a)
        bets_b = _simulate_rolls(rolls_b)
        assert bets_a != bets_b


def _simulate_rolls(rolls: list) -> list:
    """Run a sequence of rolls through the strategy and collect bet amounts."""
    s = _make_strategy()
    bets = []
    for win in rolls:
        spec = s.next_bet()
        if spec is None:
            break
        bets.append(spec["amount"])
        payout = Decimal("99") / Decimal(s.chance)
        profit = Decimal(spec["amount"]) * (payout - 1) if win else -Decimal(spec["amount"])
        new_bal = s._bankroll + profit
        s.on_bet_result(_result(win, str(new_bal)))
    return bets


# ---------------------------------------------------------------------------
# Next-bet returns a valid BetSpec
# ---------------------------------------------------------------------------

class TestBetSpec:
    def test_bet_spec_keys(self):
        s = _make_strategy()
        spec = s.next_bet()
        assert spec is not None
        for key in ("game", "amount", "chance", "is_high", "faucet"):
            assert key in spec

    def test_game_is_dice(self):
        s = _make_strategy()
        assert s.next_bet()["game"] == "dice"

    def test_amount_is_string_decimal(self):
        s = _make_strategy()
        amount_str = s.next_bet()["amount"]
        assert isinstance(amount_str, str)
        Decimal(amount_str)  # must not raise
