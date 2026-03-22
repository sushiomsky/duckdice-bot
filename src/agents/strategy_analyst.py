"""Strategy Analyst Agent — evaluates, ranks, prunes, and optimizes strategies.

Responsibilities:
- Evaluate all registered strategies via multi-seed simulation
- Rank strategies by composite score
- Prune underperformers (negative EV, high risk of ruin, etc.)
- Grid-search parameter optimization
- Maintain a hall of fame of best performers
"""

from __future__ import annotations

import itertools
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from .metrics import StrategyMetricsReport, compute_metrics
from .simulation import StrategySimulator

try:
    from ..betbot_strategies import get_strategy, list_strategies
except ImportError:
    import sys

    _src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _src not in sys.path:
        sys.path.insert(0, _src)
    from betbot_strategies import get_strategy, list_strategies

logger = logging.getLogger(__name__)


def _default_params(strategy_name: str) -> Dict[str, Any]:
    """Extract default parameters from a strategy's schema."""
    try:
        cls = get_strategy(strategy_name)
        schema = cls.schema() if hasattr(cls, "schema") else []
        return {p["key"]: p.get("default") for p in schema if "key" in p}
    except Exception:
        return {}


class StrategyAnalyst:
    """Evaluates, ranks, prunes, and optimizes strategies."""

    def __init__(
        self,
        simulator: Optional[StrategySimulator] = None,
        data_dir: str = "data/agents",
    ) -> None:
        self._sim = simulator or StrategySimulator()
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_strategy(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        rounds: int = 1000,
        num_seeds: int = 20,
        starting_balance: float = 100.0,
        symbol: str = "BTC",
    ) -> StrategyMetricsReport:
        """Evaluate a single strategy with multi-seed simulation."""
        if params is None:
            params = _default_params(name)

        sim_results = self._sim.simulate_multi_seed(
            strategy_name=name,
            params=params,
            rounds=rounds,
            starting_balance=starting_balance,
            symbol=symbol,
            num_seeds=num_seeds,
        )

        report = compute_metrics(
            strategy_name=name,
            params=params,
            sim_results=sim_results,
            rounds_per_sim=rounds,
        )
        logger.info(
            "Evaluated %s: composite=%.4f EV=%.6f survival=%.2f%%",
            name,
            report.composite_score,
            report.expected_value,
            report.survival_rate * 100,
        )
        return report

    def evaluate_all(
        self,
        rounds: int = 500,
        num_seeds: int = 10,
        starting_balance: float = 100.0,
        exclude: Optional[set] = None,
    ) -> List[StrategyMetricsReport]:
        """Evaluate all registered strategies with default params.

        Returns reports sorted by composite_score descending.
        """
        exclude = exclude or set()
        reports: List[StrategyMetricsReport] = []

        for entry in list_strategies():
            name = entry["name"]
            if name in exclude:
                continue
            try:
                report = self.evaluate_strategy(
                    name=name,
                    rounds=rounds,
                    num_seeds=num_seeds,
                    starting_balance=starting_balance,
                )
                reports.append(report)
            except Exception:
                logger.exception("Failed to evaluate strategy %s", name)

        return self.rank(reports)

    # ------------------------------------------------------------------
    # Ranking and pruning
    # ------------------------------------------------------------------

    @staticmethod
    def rank(reports: List[StrategyMetricsReport]) -> List[StrategyMetricsReport]:
        """Sort reports by composite_score descending."""
        return sorted(reports, key=lambda r: r.composite_score, reverse=True)

    @staticmethod
    def prune(
        reports: List[StrategyMetricsReport],
        ev_min: float = 0.0,
        ruin_max: float = 0.50,
        drawdown_max: float = 0.95,
    ) -> Tuple[List[StrategyMetricsReport], List[StrategyMetricsReport]]:
        """Split reports into (kept, pruned) based on quality thresholds."""
        kept: List[StrategyMetricsReport] = []
        pruned: List[StrategyMetricsReport] = []

        for r in reports:
            if (
                r.expected_value < ev_min
                or r.risk_of_ruin > ruin_max
                or r.max_drawdown > drawdown_max
            ):
                pruned.append(r)
                logger.debug(
                    "Pruned %s: EV=%.6f ruin=%.2f dd=%.2f",
                    r.strategy_name,
                    r.expected_value,
                    r.risk_of_ruin,
                    r.max_drawdown,
                )
            else:
                kept.append(r)

        return kept, pruned

    # ------------------------------------------------------------------
    # Parameter optimization (grid search)
    # ------------------------------------------------------------------

    def optimize_params(
        self,
        name: str,
        base_params: Dict[str, Any],
        param_grid: Dict[str, List[Any]],
        rounds: int = 500,
        num_seeds: int = 10,
        starting_balance: float = 100.0,
    ) -> Tuple[Dict[str, Any], StrategyMetricsReport]:
        """Grid search over parameter combinations for a strategy.

        Args:
            name: Strategy name.
            base_params: Base parameters (non-grid keys stay fixed).
            param_grid: ``{key: [val1, val2, ...]}`` of parameters to search.
            rounds: Simulation rounds per evaluation.
            num_seeds: Seeds per evaluation.
            starting_balance: Starting balance.

        Returns:
            ``(best_params, best_report)``
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combos = list(itertools.product(*values))

        logger.info(
            "Grid search for %s: %d combinations (%s)",
            name,
            len(combos),
            ", ".join(keys),
        )

        best_report: Optional[StrategyMetricsReport] = None
        best_params: Dict[str, Any] = dict(base_params)

        for combo in combos:
            trial_params = dict(base_params)
            for k, v in zip(keys, combo):
                trial_params[k] = v

            try:
                report = self.evaluate_strategy(
                    name=name,
                    params=trial_params,
                    rounds=rounds,
                    num_seeds=num_seeds,
                    starting_balance=starting_balance,
                )
                if best_report is None or report.composite_score > best_report.composite_score:
                    best_report = report
                    best_params = trial_params
            except Exception:
                logger.exception("Grid search failed for %s with %s", name, trial_params)

        if best_report is None:
            best_report = self.evaluate_strategy(name=name, params=base_params)

        logger.info(
            "Best params for %s: score=%.4f params=%s",
            name,
            best_report.composite_score,
            best_params,
        )
        return best_params, best_report

    # ------------------------------------------------------------------
    # Hall of fame
    # ------------------------------------------------------------------

    def hall_of_fame(self) -> List[dict]:
        """Return stored hall of fame entries."""
        path = os.path.join(self._data_dir, "hall_of_fame.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def update_hall_of_fame(
        self,
        report: StrategyMetricsReport,
        max_entries: int = 20,
    ) -> None:
        """Add a strategy to the hall of fame if it qualifies."""
        entries = self.hall_of_fame()
        entry = {
            "strategy_name": report.strategy_name,
            "params": report.params,
            "composite_score": report.composite_score,
            "expected_value": report.expected_value,
            "profit_factor": report.profit_factor,
            "avg_roi": report.avg_roi,
            "max_drawdown": report.max_drawdown,
            "risk_of_ruin": report.risk_of_ruin,
            "sharpe_ratio": report.sharpe_ratio,
            "survival_rate": report.survival_rate,
            "timestamp": time.time(),
        }

        entries.append(entry)
        entries.sort(key=lambda e: e.get("composite_score", 0), reverse=True)
        entries = entries[:max_entries]

        path = os.path.join(self._data_dir, "hall_of_fame.json")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(entries, fh, indent=2)
            logger.info("Hall of fame updated (%d entries)", len(entries))
        except OSError:
            logger.exception("Failed to save hall of fame")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_results(
        self,
        reports: List[StrategyMetricsReport],
        filename: str = "evaluation_results.json",
    ) -> None:
        """Save evaluation results to JSON."""
        path = os.path.join(self._data_dir, filename)
        data = []
        for r in reports:
            data.append({
                "strategy_name": r.strategy_name,
                "params": r.params,
                "composite_score": r.composite_score,
                "expected_value": r.expected_value,
                "profit_factor": r.profit_factor,
                "avg_roi": r.avg_roi,
                "median_roi": r.median_roi,
                "max_drawdown": r.max_drawdown,
                "risk_of_ruin": r.risk_of_ruin,
                "sharpe_ratio": r.sharpe_ratio,
                "survival_rate": r.survival_rate,
                "worst_loss_streak": r.worst_loss_streak,
                "avg_total_wagered": r.avg_total_wagered,
                "num_simulations": r.num_simulations,
                "rounds_per_sim": r.rounds_per_sim,
                "timestamp": time.time(),
            })
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            logger.info("Saved %d evaluation results to %s", len(data), path)
        except OSError:
            logger.exception("Failed to save results to %s", path)

    def load_results(
        self,
        filename: str = "evaluation_results.json",
    ) -> List[dict]:
        """Load previously saved evaluation results."""
        path = os.path.join(self._data_dir, filename)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    # ------------------------------------------------------------------
    # Strategy evolution (mutation)
    # ------------------------------------------------------------------

    def mutate_params(
        self,
        params: Dict[str, Any],
        mutation_rate: float = 0.3,
        mutation_strength: float = 0.2,
        rng: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Mutate numeric parameters by a random factor.

        Each numeric parameter has ``mutation_rate`` probability of being
        mutated by ±``mutation_strength`` fraction of its current value.
        """
        import random as _random

        r = rng or _random
        mutated = dict(params)
        for key, val in mutated.items():
            if not isinstance(val, (int, float)):
                continue
            if r.random() < mutation_rate:
                factor = 1.0 + r.uniform(-mutation_strength, mutation_strength)
                new_val = val * factor
                mutated[key] = type(val)(new_val) if isinstance(val, int) else round(new_val, 10)
        return mutated

    def evolve(
        self,
        top_reports: List[StrategyMetricsReport],
        mutations_per_strategy: int = 3,
        rounds: int = 500,
        num_seeds: int = 10,
        starting_balance: float = 100.0,
    ) -> List[StrategyMetricsReport]:
        """Evolve top strategies by mutating their parameters.

        For each strategy in ``top_reports``, generate ``mutations_per_strategy``
        mutated variants and evaluate them. Returns all results (originals +
        mutations) sorted by composite score.
        """
        import random as _random

        all_reports: List[StrategyMetricsReport] = list(top_reports)
        rng = _random.Random(int(time.time()))

        for report in top_reports:
            for i in range(mutations_per_strategy):
                mutated = self.mutate_params(report.params, rng=rng)
                try:
                    mr = self.evaluate_strategy(
                        name=report.strategy_name,
                        params=mutated,
                        rounds=rounds,
                        num_seeds=num_seeds,
                        starting_balance=starting_balance,
                    )
                    all_reports.append(mr)
                    logger.info(
                        "Mutation %d of %s: score=%.4f (original=%.4f)",
                        i + 1,
                        report.strategy_name,
                        mr.composite_score,
                        report.composite_score,
                    )
                except Exception:
                    logger.exception("Mutation %d of %s failed", i + 1, report.strategy_name)

        return self.rank(all_reports)
