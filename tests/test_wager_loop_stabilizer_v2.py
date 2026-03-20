import os
import random
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from betbot_strategies import get_strategy, list_strategies
from betbot_strategies.base import SessionLimits, StrategyContext
from betbot_strategies.wager_loop_stabilizer_v2 import WagerLoopStabilizerV2


def _ctx(starting_balance: str = "100.0") -> StrategyContext:
    return StrategyContext(
        api=None,
        symbol="btc",
        faucet=False,
        dry_run=True,
        rng=random.Random(123),
        logger=lambda _: None,
        limits=SessionLimits(symbol="btc"),
        starting_balance=starting_balance,
        printer=lambda _: None,
    )


def _strat(params=None, start="100.0") -> WagerLoopStabilizerV2:
    s = WagerLoopStabilizerV2(params or {}, _ctx(start))
    s.on_session_start()
    return s


def _result(win: bool, balance: str):
    return {"win": win, "balance": balance}


class TestRegistration:
    def test_registered(self):
        assert get_strategy("wager-loop-stabilizer-v2") is WagerLoopStabilizerV2

    def test_listed(self):
        assert "wager-loop-stabilizer-v2" in [x["name"] for x in list_strategies()]


class TestZones:
    def test_zone_high(self):
        s = _strat()
        assert s._resolve_zone(Decimal("121")) == "HIGH"

    def test_zone_mid(self):
        s = _strat()
        assert s._resolve_zone(Decimal("100")) == "MID"
        assert s._resolve_zone(Decimal("80")) == "MID"
        assert s._resolve_zone(Decimal("120")) == "MID"

    def test_zone_low(self):
        s = _strat()
        assert s._resolve_zone(Decimal("79.999")) == "LOW"


class TestDynamicFactor:
    def test_mid_factor_range(self):
        s = _strat()
        f = s._dynamic_factor("MID", Decimal("100"))
        assert 0.04 <= f <= 0.06

    def test_high_factor_range(self):
        s = _strat()
        f = s._dynamic_factor("HIGH", Decimal("130"))
        assert 0.02 <= f <= 0.03

    def test_low_factor_range(self):
        s = _strat()
        f = s._dynamic_factor("LOW", Decimal("70"))
        assert 0.02 <= f <= 0.04


class TestLadderBehavior:
    def test_mid_ladder_depth_two(self):
        s = _strat()
        s.next_bet()
        s.on_bet_result(_result(True, "102"))
        assert s._ladder_step == 1
        s.next_bet()
        s.on_bet_result(_result(True, "104"))
        # depth=2 resets after second win
        assert s._ladder_step == 0

    def test_high_zone_no_ladder(self):
        s = _strat()
        s.on_bet_result(_result(True, "130"))  # move to high
        s.next_bet()
        s.on_bet_result(_result(True, "131"))
        assert s._zone == "HIGH"
        assert s._ladder_step == 0

    def test_loss_resets_ladder(self):
        s = _strat()
        s.next_bet()
        s.on_bet_result(_result(True, "102"))
        assert s._ladder_step == 1
        s.next_bet()
        s.on_bet_result(_result(False, "98"))
        assert s._ladder_step == 0
        assert s._win_streak == 0
        assert s._loss_streak == 1


class TestProtections:
    def test_stops_only_when_no_balance_left(self):
        s = _strat()
        s.on_bet_result(_result(False, "39"))  # no longer a hard stop
        assert s.should_stop() is False
        s.on_bet_result(_result(False, "0"))
        assert s.should_stop() is True
        assert s.next_bet() is None

    def test_low_zone_loss_streak_reduction(self):
        s = _strat()
        s.on_bet_result(_result(False, "79"))
        s.on_bet_result(_result(False, "75"))
        spec = s.next_bet()
        amt = Decimal(spec["amount"])
        s2 = _strat({"loss_reduction_factor": 1.0})
        s2.on_bet_result(_result(False, "79"))
        s2.on_bet_result(_result(False, "75"))
        amt2 = Decimal(s2.next_bet()["amount"])
        assert amt < amt2

    def test_recovery_boost_below_90pct(self):
        s = _strat()
        s.on_bet_result(_result(False, "89"))
        amt = Decimal(s.next_bet()["amount"])
        s2 = _strat({"recovery_boost": 1.0})
        s2.on_bet_result(_result(False, "89"))
        amt2 = Decimal(s2.next_bet()["amount"])
        assert amt > amt2


class TestAntiVolatility:
    def test_alternating_pattern_detected(self):
        s = _strat()
        for win in [True, False, True, False, True, False]:
            s._roll_history.append(win)
        assert s._is_alternating_pattern() is True

    def test_alternating_pattern_reduces_bet(self):
        s = _strat()
        for w in [True, False, True, False, True, False]:
            s._roll_history.append(w)
        amt = Decimal(s.next_bet()["amount"])
        s2 = _strat({"alternating_reduction": 1.0})
        for w in [True, False, True, False, True, False]:
            s2._roll_history.append(w)
        amt2 = Decimal(s2.next_bet()["amount"])
        assert amt < amt2


class TestMetricsAndInterface:
    def test_tracks_total_wager(self):
        s = _strat()
        a = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(False, "95"))
        b = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(True, "98"))
        assert s._total_wager == a + b

    def test_average_bet_size(self):
        s = _strat()
        a = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(False, "95"))
        b = Decimal(s.next_bet()["amount"])
        s.on_bet_result(_result(True, "98"))
        assert s.average_bet_size() == (a + b) / Decimal("2")

    def test_get_next_bet(self):
        s = _strat()
        v = s.get_next_bet()
        assert isinstance(v, float)
        assert v > 0

    def test_initialize(self):
        s = _strat()
        s.initialize(200.0)
        assert s._start_bankroll == Decimal("200.0")
        assert s._bankroll == Decimal("200.0")
        assert s._zone == "MID"

    def test_on_roll_result_method(self):
        s = _strat()
        before = s._bankroll
        s.get_next_bet()
        s.on_roll_result(False)
        assert s._bankroll < before

    def test_bet_spec_shape(self):
        s = _strat()
        spec = s.next_bet()
        assert spec["game"] == "dice"
        assert spec["chance"] == "49.5"
        assert "amount" in spec
        assert "is_high" in spec
