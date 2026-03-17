import os
import random
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from betbot_strategies import get_strategy, list_strategies
from betbot_strategies.base import SessionLimits, StrategyContext
from betbot_strategies.tle_wager_farming import TLEWagerFarmingStrategy


def _make_ctx(starting_balance: str = "100.0") -> StrategyContext:
    return StrategyContext(
        api=None,
        symbol="btc",
        faucet=False,
        dry_run=True,
        rng=random.Random(42),
        logger=lambda _: None,
        limits=SessionLimits(symbol="btc"),
        starting_balance=starting_balance,
        printer=lambda _: None,
    )


def _make_strategy(params=None, starting_balance: str = "100.0") -> TLEWagerFarmingStrategy:
    strat = TLEWagerFarmingStrategy(params or {}, _make_ctx(starting_balance))
    strat.on_session_start()
    return strat


def _result(win: bool, balance: str) -> dict:
    return {"win": win, "balance": balance}


class TestRegistration:
    def test_registered(self):
        assert get_strategy("tle-wager-farming") is TLEWagerFarmingStrategy

    def test_listed(self):
        assert "tle-wager-farming" in [s["name"] for s in list_strategies()]


class TestBaseSizing:
    def test_base_bet_fraction(self):
        s = _make_strategy()
        assert s.calculate_base_bet(Decimal("100")) == Decimal("4.0")

    def test_drawdown_reduces_base_bet(self):
        s = _make_strategy()
        # 20% drawdown threshold => 80 bankroll floor
        assert s.calculate_base_bet(Decimal("80")) == Decimal("80") * Decimal("0.04") * Decimal("0.7")

    def test_below_drawdown_reduces_base_bet(self):
        s = _make_strategy()
        assert s.calculate_base_bet(Decimal("70")) == Decimal("70") * Decimal("0.04") * Decimal("0.7")


class TestMicroParoli:
    def test_step1_is_base(self):
        s = _make_strategy()
        spec = s.next_bet()
        assert Decimal(spec["amount"]) == Decimal("4.0")

    def test_win_advances_to_step2(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "104"))
        spec = s.next_bet()
        assert Decimal(spec["amount"]) == Decimal("104") * Decimal("0.04") * Decimal("1.5")

    def test_second_win_advances_to_step3(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "104"))
        s.next_bet()
        s.on_bet_result(_result(True, "110"))
        spec = s.next_bet()
        expected = Decimal("110") * Decimal("0.04") * (Decimal("1.5") ** 2)
        assert Decimal(spec["amount"]) == expected

    def test_after_step3_win_ladder_resets(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "104"))
        s.next_bet()
        s.on_bet_result(_result(True, "110"))
        s.next_bet()
        s.on_bet_result(_result(True, "120"))
        assert s._ladder_step == 0
        spec = s.next_bet()
        assert Decimal(spec["amount"]) == Decimal("120") * Decimal("0.04")

    def test_loss_resets_ladder_and_win_streak(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "104"))
        s.next_bet()
        s.on_bet_result(_result(False, "98"))
        assert s._ladder_step == 0
        assert s._win_streak == 0
        assert s._loss_streak == 1


class TestLossProtection:
    def test_loss_streak_threshold_reduces_bet(self):
        s = _make_strategy()
        for bal in ("96", "92", "88"):
            s.next_bet()
            s.on_bet_result(_result(False, bal))
        spec = s.next_bet()
        expected = Decimal("88") * Decimal("0.04") * Decimal("0.6")
        assert Decimal(spec["amount"]) == expected

    def test_loss_reduction_stacks_with_drawdown_reduction(self):
        s = _make_strategy()
        for bal in ("96", "92", "78"):
            s.next_bet()
            s.on_bet_result(_result(False, bal))
        spec = s.next_bet()
        expected = Decimal("78") * Decimal("0.04") * Decimal("0.7") * Decimal("0.6")
        assert Decimal(spec["amount"]) == expected


class TestStopControl:
    def test_does_not_stop_on_profit(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(True, "150"))
        assert s.should_stop() is False

    def test_stops_at_bankroll_floor(self):
        s = _make_strategy()
        s.next_bet()
        s.on_bet_result(_result(False, "39"))
        assert s.should_stop() is True
        assert s.next_bet() is None


class TestMetrics:
    def test_total_wager_accumulates(self):
        s = _make_strategy()
        first = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(False, "96"))
        second = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(False, "92"))
        assert s._total_wager == first + second

    def test_average_bet_size(self):
        s = _make_strategy()
        first = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(False, "96"))
        second = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(False, "92"))
        assert s.average_bet_size() == (first + second) / Decimal("2")

    def test_session_duration_non_negative(self):
        s = _make_strategy()
        assert s.session_duration() >= 0.0


class TestBetSpec:
    def test_bet_spec_fields(self):
        s = _make_strategy()
        spec = s.next_bet()
        assert spec["game"] == "dice"
        assert spec["chance"] == "49.5"
        assert spec["is_high"] is True
        assert spec["faucet"] is False
