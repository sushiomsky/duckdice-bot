import os
import random
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from betbot_engine.strategy_manager import StrategyManager
from betbot_strategies import get_strategy, list_strategies
from betbot_strategies.adaptive_hunt import AdaptiveHuntStrategy
from betbot_strategies.base import SessionLimits, StrategyContext
from betbot_strategies.multi_strategy_system import MultiStrategySystem


DEFAULT_PARAMS = {
    "base_bet_percent": 0.001,
    "max_bet_percent": 0.03,
    "stop_loss_percent": 0.15,
    "take_profit_percent": 0.30,
    "loss_trigger": 0.05,
    "profit_trigger": 0.10,
    "wager_focus": True,
    "bet_high": True,
}


def _make_ctx(starting_balance: str = "100") -> StrategyContext:
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


def _result(win: bool, balance: str) -> dict:
    return {"win": win, "balance": balance}


class TestRegistration:
    def test_registered(self):
        assert get_strategy("multi-strategy-system") is MultiStrategySystem

    def test_listed(self):
        assert "multi-strategy-system" in [s["name"] for s in list_strategies()]


class TestAdaptiveHunt:
    def test_state_transitions(self):
        strategy = AdaptiveHuntStrategy(StrategyManager(DEFAULT_PARAMS, random.Random(1)).config)
        for _ in range(50):
            strategy.on_loss()
        assert strategy.state == strategy.PRE_HUNT
        for _ in range(70):
            strategy.on_loss()
        assert strategy.state == strategy.HUNT
        for _ in range(130):
            strategy.on_loss()
        assert strategy.state == strategy.SNIPE

    def test_snipe_cycle_resets_to_farm(self):
        strategy = AdaptiveHuntStrategy(StrategyManager(DEFAULT_PARAMS, random.Random(1)).config)
        for _ in range(250):
            strategy.on_loss()
        for _ in range(5):
            strategy.get_bet(Decimal("100"))
        strategy.get_bet(Decimal("100"))
        assert strategy.state == strategy.FARM
        assert strategy.losing_streak == 0


class TestStrategyManager:
    def test_wager_focus_prefers_grinder(self):
        manager = StrategyManager(DEFAULT_PARAMS, random.Random(42))
        manager.initialize(Decimal("100"))
        amount, chance = manager.get_bet(Decimal("100"))
        assert manager.active_strategy_name == "wager-grinder"
        assert Decimal("20") <= chance <= Decimal("40")
        assert amount > Decimal("0")

    def test_loss_switches_to_recovery(self):
        manager = StrategyManager(DEFAULT_PARAMS, random.Random(42))
        manager.initialize(Decimal("100"))
        manager.get_bet(Decimal("100"))
        manager.record_result(False, Decimal("94"))
        assert manager.active_strategy_name == "recovery"

    def test_profit_switches_to_hunt(self):
        manager = StrategyManager(DEFAULT_PARAMS, random.Random(42))
        manager.initialize(Decimal("100"))
        manager.get_bet(Decimal("100"))
        manager.record_result(True, Decimal("111"))
        assert manager.active_strategy_name == "adaptive-hunt"

    def test_stop_floor_triggers(self):
        manager = StrategyManager(DEFAULT_PARAMS, random.Random(42))
        manager.initialize(Decimal("100"))
        manager.update_bankroll(Decimal("85"))
        assert manager.should_stop() is True


class TestWrapperStrategy:
    def test_next_bet_returns_dice_spec(self):
        strategy = MultiStrategySystem(DEFAULT_PARAMS, _make_ctx())
        strategy.on_session_start()
        spec = strategy.next_bet()
        assert spec is not None
        assert spec["game"] == "dice"
        assert Decimal(spec["amount"]) > Decimal("0")
        assert Decimal(spec["chance"]) > Decimal("0")

    def test_wrapper_updates_wager_and_strategy(self):
        strategy = MultiStrategySystem(DEFAULT_PARAMS, _make_ctx())
        strategy.on_session_start()
        strategy.next_bet()
        strategy.on_bet_result(_result(False, "94"))
        state = strategy.get_state()
        assert state["active_strategy"] == "recovery"
        assert Decimal(state["wagered_total"]) > Decimal("0")

    def test_wrapper_stops_at_floor(self):
        strategy = MultiStrategySystem(DEFAULT_PARAMS, _make_ctx())
        strategy.on_session_start()
        strategy.next_bet()
        strategy.on_bet_result(_result(False, "84.9"))
        assert strategy.next_bet() is None
