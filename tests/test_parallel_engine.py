import os
import sys
import time
import threading
from decimal import Decimal
from queue import Queue

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from betbot_engine.engine import EngineConfig  # noqa: E402
from betbot_engine.parallel_engine import ParallelBettingEngine  # noqa: E402


class _DummyAPI:
    def get_user_info(self):
        return {"balances": [{"currency": "BTC", "main": "100.0"}]}


class _SimpleLimits:
    def __init__(self, max_bets=None, max_duration_sec=None):
        self.max_bets = max_bets
        self.max_duration_sec = max_duration_sec


class _SimpleCtx:
    def __init__(self, limits):
        self.limits = limits


class _SimpleStrategy:
    def __init__(self, max_bets=5, session_max_bets=None):
        self.ctx = _SimpleCtx(_SimpleLimits(max_bets=session_max_bets))
        self.generated = 0
        self.max_bets = max_bets
        self.received = []
        self.end_reason = None

    def on_session_start(self):
        pass

    def next_bet(self):
        if self.generated >= self.max_bets:
            return None
        self.generated += 1
        return {
            "game": "dice",
            "amount": "0.00000001",
            "chance": "49.5",
            "is_high": True,
            "faucet": False,
        }

    def on_bet_result(self, result):
        self.received.append(result)

    def on_session_end(self, reason):
        self.end_reason = reason


def _build_engine(max_concurrent=3):
    cfg = EngineConfig(
        symbol="BTC",
        dry_run=False,
        delay_ms=0,
        jitter_ms=0,
    )
    return ParallelBettingEngine(_DummyAPI(), cfg, max_concurrent=max_concurrent)


def test_parallel_engine_processes_out_of_order_results_deterministically():
    engine = _build_engine(max_concurrent=3)
    strategy = _SimpleStrategy(max_bets=3)
    submitted = Queue()

    def fake_worker():
        while not engine.stop_event.is_set():
            try:
                req = engine.bet_queue.get(timeout=0.1)
            except Exception:
                continue
            submitted.put(req.bet_id)
            if req.bet_id == 0:
                time.sleep(0.06)  # force 1 and 2 to complete first
            result = {
                "bet": {
                    "result": True,
                    "profit": Decimal("0.1"),
                    "amount": Decimal("0.00000001"),
                    "chance": Decimal("49.5"),
                    "multiplier": Decimal("2.0"),
                },
                "user": {"balance": Decimal("100.0") + Decimal(req.bet_id)},
            }
            engine.result_queue.put(
                type("R", (), {
                    "bet_id": req.bet_id,
                    "success": True,
                    "data": result,
                    "error": None,
                    "timestamp": time.time(),
                })()
            )
            engine.bet_queue.task_done()

    engine.submit_bet_worker = fake_worker

    sink_rows = []
    summary = engine.run(strategy=strategy, json_sink=lambda row: sink_rows.append(row))

    assert summary["bets_placed"] == 3
    assert strategy.end_reason == "strategy_complete"
    assert len(strategy.received) == 3
    balances = [Decimal(str(r["balance"])) for r in strategy.received]
    assert balances == [Decimal("100.0"), Decimal("101.0"), Decimal("102.0")]
    assert len(sink_rows) == 3


def test_parallel_engine_stops_on_checker_without_extra_submissions():
    engine = _build_engine(max_concurrent=2)
    strategy = _SimpleStrategy(max_bets=50)
    calls = {"n": 0}

    def stop_checker():
        calls["n"] += 1
        return calls["n"] > 4

    summary = engine.run(strategy=strategy, stop_checker=stop_checker)

    assert summary["stop_reason"] == "user_stop"
    assert summary["bets_placed"] <= 4


def test_parallel_engine_stops_on_insufficient_balance_error():
    engine = _build_engine(max_concurrent=2)
    strategy = _SimpleStrategy(max_bets=3)
    counter = {"n": 0}

    def fake_worker():
        while not engine.stop_event.is_set():
            try:
                req = engine.bet_queue.get(timeout=0.1)
            except Exception:
                continue
            counter["n"] += 1
            if req.bet_id == 0:
                engine.result_queue.put(
                    type("R", (), {
                        "bet_id": req.bet_id,
                        "success": False,
                        "data": None,
                        "error": "422 insufficient funds",
                        "timestamp": time.time(),
                    })()
                )
            else:
                engine.result_queue.put(
                    type("R", (), {
                        "bet_id": req.bet_id,
                        "success": True,
                        "data": {
                            "bet": {"result": True, "profit": 0, "amount": 0, "chance": 49.5, "multiplier": 2.0},
                            "user": {"balance": 100},
                        },
                        "error": None,
                        "timestamp": time.time(),
                    })()
                )
            engine.bet_queue.task_done()

    engine.submit_bet_worker = fake_worker
    summary = engine.run(strategy=strategy)

    assert summary["stop_reason"] == "insufficient_balance"
    assert strategy.end_reason == "insufficient_balance"
    assert counter["n"] >= 1
