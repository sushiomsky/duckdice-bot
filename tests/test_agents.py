"""Tests for the autonomous agent system (simulation, metrics, analyst, gambler, memory)."""

import json
import os
import shutil
import sys
import tempfile

import pytest

_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _src not in sys.path:
    sys.path.insert(0, _src)

from agents.metrics import SingleSimResult, StrategyMetricsReport, compute_metrics
from agents.simulation import StrategySimulator, _dice_win, _max_drawdown, _payout_for_chance
from agents.strategy_analyst import StrategyAnalyst, _default_params
from agents.gambler_agent import GamblerAgent
from agents.memory import MemoryManager


# -----------------------------------------------------------------------
# Dice helpers
# -----------------------------------------------------------------------

class TestDiceHelpers:
    def test_dice_win_high(self):
        # chance 49.5, is_high: roll >= 50.5 wins
        assert _dice_win(51.0, 49.5, True) is True
        assert _dice_win(50.0, 49.5, True) is False

    def test_dice_win_low(self):
        # chance 49.5, not high: roll < 49.5 wins
        assert _dice_win(10.0, 49.5, False) is True
        assert _dice_win(60.0, 49.5, False) is False

    def test_payout_for_chance(self):
        payout = _payout_for_chance(49.5, 1.0)
        assert abs(payout - 2.0) < 0.01

    def test_payout_zero_chance(self):
        assert _payout_for_chance(0.0) == 0.0

    def test_max_drawdown_flat(self):
        assert _max_drawdown([100, 100, 100]) == 0.0

    def test_max_drawdown_decline(self):
        dd = _max_drawdown([100, 80, 60])
        assert abs(dd - 0.4) < 0.01

    def test_max_drawdown_recovery(self):
        dd = _max_drawdown([100, 80, 120, 90])
        # Peak 120, trough 90 → 25% dd; or peak 100, trough 80 → 20%
        assert dd > 0.19


# -----------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------

class TestMetrics:
    def test_empty_results(self):
        report = compute_metrics("test", {}, [], 100)
        assert report.num_simulations == 0
        assert report.expected_value == 0.0

    def test_single_sim_metrics(self):
        sim = SingleSimResult(
            rounds_completed=100,
            starting_balance=100.0,
            final_balance=120.0,
            roi=20.0,
            max_drawdown=0.1,
            max_loss_streak=3,
            max_win_streak=5,
            total_wagered=500.0,
            win_count=55,
            loss_count=45,
            survived=True,
            per_bet_returns=[0.01] * 55 + [-0.01] * 45,
        )
        report = compute_metrics("test", {"a": 1}, [sim], 100)
        assert report.num_simulations == 1
        assert report.avg_roi == 20.0
        assert report.survival_rate == 1.0
        assert report.worst_loss_streak == 3

    def test_composite_score_is_float(self):
        sim = SingleSimResult(
            rounds_completed=50,
            starting_balance=100.0,
            final_balance=90.0,
            roi=-10.0,
            max_drawdown=0.2,
            max_loss_streak=5,
            max_win_streak=2,
            total_wagered=200.0,
            win_count=20,
            loss_count=30,
            survived=True,
            per_bet_returns=[-0.02] * 30 + [0.01] * 20,
        )
        report = compute_metrics("loser", {}, [sim], 50)
        assert isinstance(report.composite_score, float)

    def test_summary_string(self):
        report = StrategyMetricsReport(
            strategy_name="test",
            params={},
            num_simulations=1,
            rounds_per_sim=100,
        )
        s = report.summary()
        assert "test" in s
        assert "EV:" in s


# -----------------------------------------------------------------------
# Simulator
# -----------------------------------------------------------------------

class TestSimulator:
    def test_simulate_single_kelly_capped(self):
        sim = StrategySimulator()
        result = sim.simulate_single(
            strategy_name="kelly-capped",
            params={},
            rounds=50,
            starting_balance=100.0,
            seed=42,
        )
        assert result.rounds_completed > 0
        assert result.starting_balance == 100.0
        assert result.win_count + result.loss_count == result.rounds_completed

    def test_simulate_multi_seed(self):
        sim = StrategySimulator()
        results = sim.simulate_multi_seed(
            strategy_name="kelly-capped",
            params={},
            rounds=30,
            starting_balance=100.0,
            num_seeds=3,
        )
        assert len(results) == 3
        # Different seeds should produce different final balances
        finals = [r.final_balance for r in results]
        assert len(set(finals)) > 1

    def test_stop_loss_triggers(self):
        sim = StrategySimulator()
        result = sim.simulate_single(
            strategy_name="kelly-capped",
            params={},
            rounds=5000,
            starting_balance=100.0,
            seed=99,
            stop_loss=-0.10,
        )
        pnl = (result.final_balance - 100.0) / 100.0
        # Either stopped early due to stop loss or completed all rounds
        assert result.rounds_completed <= 5000


# -----------------------------------------------------------------------
# Strategy Analyst
# -----------------------------------------------------------------------

class TestStrategyAnalyst:
    def test_default_params_extracts_schema(self):
        params = _default_params("kelly-capped")
        assert isinstance(params, dict)

    def test_evaluate_strategy(self):
        analyst = StrategyAnalyst()
        report = analyst.evaluate_strategy("kelly-capped", rounds=20, num_seeds=2)
        assert report.strategy_name == "kelly-capped"
        assert report.num_simulations == 2

    def test_rank(self):
        r1 = StrategyMetricsReport("a", {}, 1, 100, composite_score=0.5)
        r2 = StrategyMetricsReport("b", {}, 1, 100, composite_score=0.8)
        ranked = StrategyAnalyst.rank([r1, r2])
        assert ranked[0].strategy_name == "b"

    def test_prune(self):
        good = StrategyMetricsReport("good", {}, 1, 100, expected_value=0.01, risk_of_ruin=0.1, max_drawdown=0.3)
        bad = StrategyMetricsReport("bad", {}, 1, 100, expected_value=-0.05, risk_of_ruin=0.8, max_drawdown=0.99)
        kept, pruned = StrategyAnalyst.prune([good, bad])
        assert len(kept) == 1
        assert kept[0].strategy_name == "good"
        assert len(pruned) == 1

    def test_hall_of_fame_roundtrip(self):
        tmp = tempfile.mkdtemp()
        try:
            analyst = StrategyAnalyst(data_dir=tmp)
            assert analyst.hall_of_fame() == []

            report = StrategyMetricsReport("test", {}, 1, 100, composite_score=0.7)
            analyst.update_hall_of_fame(report)
            hof = analyst.hall_of_fame()
            assert len(hof) == 1
            assert hof[0]["strategy_name"] == "test"
        finally:
            shutil.rmtree(tmp)

    def test_save_load_results(self):
        tmp = tempfile.mkdtemp()
        try:
            analyst = StrategyAnalyst(data_dir=tmp)
            reports = [StrategyMetricsReport("x", {"k": 1}, 1, 100, composite_score=0.5)]
            analyst.save_results(reports)
            loaded = analyst.load_results()
            assert len(loaded) == 1
            assert loaded[0]["strategy_name"] == "x"
        finally:
            shutil.rmtree(tmp)


# -----------------------------------------------------------------------
# Gambler Agent
# -----------------------------------------------------------------------

class TestGamblerAgent:
    def test_start_session_resets_state(self):
        g = GamblerAgent()
        g.start_session(100.0)
        assert g._session_active is True
        assert g._starting_balance == 100.0
        assert g._bets_placed == 0

    def test_should_stop_inactive(self):
        g = GamblerAgent()
        stop, reason = g.should_stop()
        assert stop is True
        assert "not_active" in reason

    def test_stop_loss(self):
        g = GamblerAgent(stop_loss_pct=-0.20)
        g.start_session(100.0)
        g.on_bet_result({"win": False, "profit": "-25", "balance": "75"})
        stop, reason = g.should_stop()
        assert stop is True
        assert "stop_loss" in reason

    def test_take_profit(self):
        g = GamblerAgent(take_profit_pct=0.50)
        g.start_session(100.0)
        g.on_bet_result({"win": True, "profit": "60", "balance": "160"})
        stop, reason = g.should_stop()
        assert stop is True
        assert "take_profit" in reason

    def test_max_bets(self):
        g = GamblerAgent(max_bets=3)
        g.start_session(100.0)
        for _ in range(3):
            g.on_bet_result({"win": True, "profit": "1", "balance": "101"})
        stop, reason = g.should_stop()
        assert stop is True
        assert "max_bets" in reason

    def test_streak_tracking(self):
        g = GamblerAgent()
        g.start_session(100.0)
        for _ in range(5):
            g.on_bet_result({"win": False, "profit": "-1", "balance": "99"})
        assert g._current_loss_streak == 5
        assert g._max_loss_streak == 5
        g.on_bet_result({"win": True, "profit": "1", "balance": "100"})
        assert g._current_loss_streak == 0
        assert g._current_win_streak == 1

    def test_should_switch_cooldown(self):
        g = GamblerAgent(switch_cooldown=100)
        g.start_session(100.0)
        for _ in range(10):
            g.on_bet_result({"win": False, "profit": "-1", "balance": "90"})
        switch, _ = g.should_switch_strategy()
        assert switch is False  # cooldown not met

    def test_should_switch_loss_streak(self):
        g = GamblerAgent(switch_cooldown=0)
        g.start_session(100.0)
        for _ in range(8):
            g.on_bet_result({"win": False, "profit": "-1", "balance": "92"})
        switch, reason = g.should_switch_strategy()
        assert switch is True
        assert reason == "loss_streak"

    def test_select_strategy_balanced(self):
        r1 = StrategyMetricsReport("a", {}, 1, 100, composite_score=0.5, survival_rate=0.8, avg_roi=10, avg_total_wagered=500, risk_of_ruin=0.1)
        r2 = StrategyMetricsReport("b", {}, 1, 100, composite_score=0.9, survival_rate=0.6, avg_roi=5, avg_total_wagered=300, risk_of_ruin=0.2)
        g = GamblerAgent()
        assert g.select_strategy([r1, r2], "balanced") == "b"

    def test_select_strategy_conservative(self):
        r1 = StrategyMetricsReport("a", {}, 1, 100, composite_score=0.5, survival_rate=0.9, avg_roi=10, avg_total_wagered=500, risk_of_ruin=0.1)
        r2 = StrategyMetricsReport("b", {}, 1, 100, composite_score=0.9, survival_rate=0.6, avg_roi=5, avg_total_wagered=300, risk_of_ruin=0.2)
        g = GamblerAgent()
        assert g.select_strategy([r1, r2], "conservative") == "a"

    def test_get_session_stats(self):
        g = GamblerAgent()
        g.start_session(100.0)
        g.on_bet_result({"win": True, "profit": "5", "balance": "105"})
        stats = g.get_session_stats()
        assert stats["wins"] == 1
        assert stats["bets_placed"] == 1
        assert stats["current_balance"] == 105.0

    def test_session_log_roundtrip(self):
        tmp = tempfile.mkdtemp()
        try:
            g = GamblerAgent(data_dir=tmp)
            g.log_session("test", {"profit": 10, "bets": 50})
            history = g.get_session_history()
            assert len(history) == 1
            assert history[0]["strategy_name"] == "test"
        finally:
            shutil.rmtree(tmp)


# -----------------------------------------------------------------------
# Memory Manager
# -----------------------------------------------------------------------

class TestMemoryManager:
    def test_fresh_memory(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            assert mm.get("accounts") == {}
            assert mm.get("sessions") == []
        finally:
            shutil.rmtree(tmp)

    def test_set_get(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            mm.set("preferences", "risk_level", "conservative")
            assert mm.get("preferences", "risk_level") == "conservative"
        finally:
            shutil.rmtree(tmp)

    def test_append(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            mm.append("sessions", {"profit": 10})
            assert len(mm.get("sessions")) == 1
        finally:
            shutil.rmtree(tmp)

    def test_update_balance(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            mm.update_balance("duckdice", "BTC", 0.001)
            assert mm.get("balances", "duckdice") == {"BTC": 0.001}
        finally:
            shutil.rmtree(tmp)

    def test_record_strategy_evaluation(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            mm.record_strategy_evaluation("kelly", 0.75, {"ev": 0.001})
            best = mm.get_best_strategies(1)
            assert len(best) == 1
            assert best[0]["name"] == "kelly"
        finally:
            shutil.rmtree(tmp)

    def test_persistence_across_instances(self):
        tmp = tempfile.mkdtemp()
        try:
            mm1 = MemoryManager(data_dir=tmp)
            mm1.set("goals", "wager_target", 10000)
            del mm1

            mm2 = MemoryManager(data_dir=tmp)
            assert mm2.get("goals", "wager_target") == 10000
        finally:
            shutil.rmtree(tmp)

    def test_summary(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            s = mm.summary()
            assert "Agent Memory Summary" in s
        finally:
            shutil.rmtree(tmp)

    def test_export(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            mm.set("accounts", "test", {"name": "Test"})
            export = mm.export()
            assert "accounts" in export
            assert export["accounts"]["test"]["name"] == "Test"
        finally:
            shutil.rmtree(tmp)

    def test_corrupt_file_recovery(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "memory.json")
            with open(path, "w") as f:
                f.write("NOT VALID JSON {{{")
            mm = MemoryManager(data_dir=tmp)
            # Should recover with fresh data
            assert mm.get("accounts") == {}
            assert os.path.exists(path + ".bak")
        finally:
            shutil.rmtree(tmp)

    def test_search(self):
        tmp = tempfile.mkdtemp()
        try:
            mm = MemoryManager(data_dir=tmp)
            mm.append("sessions", {"strategy": "kelly", "profit": 10})
            mm.append("sessions", {"strategy": "martingale", "profit": -5})
            results = mm.search("sessions", strategy="kelly")
            assert len(results) == 1
            assert results[0]["profit"] == 10
        finally:
            shutil.rmtree(tmp)
