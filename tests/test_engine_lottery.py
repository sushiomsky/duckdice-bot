import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from betbot_engine.engine import AutoBetEngine, EngineConfig
from betbot_engine.events import EventType
from betbot_engine.observers import EventEmitter
from betbot_strategies import register


class DummyAPI:
    """Minimal API stub for dry-run engine tests."""

    def get_user_info(self):
        return {"balances": [{"currency": "BTC", "main": "100.0"}]}


def _run_with_collect(config: EngineConfig, strategy: str = "wager-loop-stabilizer-v2"):
    api = DummyAPI()
    engine = AutoBetEngine(api, config)
    rows = []
    summary = engine.run(
        strategy_name=strategy,
        params={},
        json_sink=lambda rec: rows.append(rec),
    )
    return summary, rows


@register("test-static-amount")
class TestStaticAmountStrategy:
    @classmethod
    def name(cls):
        return "test-static-amount"

    @classmethod
    def describe(cls):
        return "Static amount test strategy"

    @classmethod
    def metadata(cls):
        return None

    @classmethod
    def schema(cls):
        return {}

    def __init__(self, params, ctx):
        self.ctx = ctx

    def on_session_start(self):
        pass

    def next_bet(self):
        return {
            "game": "dice",
            "amount": "1.23450000",
            "chance": "49.5",
            "is_high": True,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result):
        pass

    def on_session_end(self, reason: str):
        pass


class TestEngineLottery:
    def test_lottery_changes_chance_into_001_to_1_range(self):
        cfg = EngineConfig(
            symbol="BTC",
            dry_run=True,
            max_bets=6,
            seed=12345,
            lottery_enabled=True,
            lottery_min_gap=1,
            lottery_max_gap=1,
            lottery_min_chance=0.01,
            lottery_max_chance=1.0,
            take_profit=None,
            stop_loss=-0.99,
        )
        _, rows = _run_with_collect(cfg)
        bets = [r for r in rows if r.get("event") == "bet"]
        # at least one lottery-applied bet expected with 1-gap config
        lot = [b for b in bets if b.get("lottery", {}).get("applied")]
        assert lot, "Expected at least one lottery bet"
        for b in lot:
            c = Decimal(str(b["bet"]["chance"]))
            assert Decimal("0.01") <= c <= Decimal("1.0")
            assert b["bet"]["game"] == "dice"

    def test_lottery_keeps_strategy_amount_unchanged(self):
        cfg = EngineConfig(
            symbol="BTC",
            dry_run=True,
            max_bets=6,
            seed=4321,
            lottery_enabled=True,
            lottery_min_gap=1,
            lottery_max_gap=1,
            lottery_min_chance=0.01,
            lottery_max_chance=1.0,
            take_profit=None,
            stop_loss=-0.99,
        )
        _, rows = _run_with_collect(cfg, strategy="test-static-amount")
        bets = [r for r in rows if r.get("event") == "bet"]
        assert bets
        for b in bets:
            assert Decimal(str(b["bet"]["amount"])) == Decimal("1.23450000")

    def test_engine_emits_bet_placed_events_with_amounts(self):
        cfg = EngineConfig(
            symbol="BTC",
            dry_run=True,
            max_bets=5,
            seed=9876,
            lottery_enabled=False,
            take_profit=None,
            stop_loss=-0.99,
        )
        api = DummyAPI()
        engine = AutoBetEngine(api, cfg)
        emitter = EventEmitter()
        captured = []
        emitter.add_callback(lambda ev: captured.append(ev))

        engine.run(
            strategy_name="test-static-amount",
            params={},
            emitter=emitter,
        )

        placed = [ev for ev in captured if ev.event_type == EventType.BET_PLACED]
        assert placed, "Expected BET_PLACED events to be emitted"
        assert len(placed) == 5
        for ev in placed:
            assert Decimal(str(ev.data["amount"])) == Decimal("1.23450000")
            assert float(ev.data["chance"]) > 0
            assert ev.data["prediction"] in ("high", "low", "range")
