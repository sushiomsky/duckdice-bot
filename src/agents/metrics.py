"""Strategy performance metrics computation.

Computes comprehensive evaluation metrics from simulation results:
- Expected Value (EV)
- Profit Factor
- Max Drawdown
- Risk of Ruin
- Volatility (std of returns)
- Sharpe Ratio
- Longest losing streak
- Bankroll survival rate
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StrategyMetricsReport:
    """Complete metrics report for a strategy evaluation."""

    strategy_name: str
    params: dict
    num_simulations: int
    rounds_per_sim: int

    # Core metrics (averaged across simulations)
    expected_value: float = 0.0
    profit_factor: float = 0.0
    avg_roi: float = 0.0
    median_roi: float = 0.0

    # Risk metrics
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    risk_of_ruin: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0

    # Streak metrics
    avg_max_loss_streak: float = 0.0
    worst_loss_streak: int = 0
    avg_max_win_streak: float = 0.0

    # Survival
    survival_rate: float = 0.0
    avg_survival_rounds: float = 0.0

    # Balance distribution
    avg_final_balance: float = 0.0
    median_final_balance: float = 0.0
    p5_final_balance: float = 0.0
    p95_final_balance: float = 0.0

    # Wager metrics
    avg_total_wagered: float = 0.0

    # Composite score (higher = better)
    composite_score: float = 0.0

    # Per-simulation details
    sim_results: List[SingleSimResult] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Strategy: {self.strategy_name}",
            f"Simulations: {self.num_simulations} × {self.rounds_per_sim} rounds",
            f"{'─' * 50}",
            f"EV:              {self.expected_value:+.6f}",
            f"Profit Factor:   {self.profit_factor:.4f}",
            f"Avg ROI:         {self.avg_roi:+.2f}%",
            f"Median ROI:      {self.median_roi:+.2f}%",
            f"Max Drawdown:    {self.max_drawdown:.2%}",
            f"Risk of Ruin:    {self.risk_of_ruin:.2%}",
            f"Volatility:      {self.volatility:.6f}",
            f"Sharpe Ratio:    {self.sharpe_ratio:.4f}",
            f"Survival Rate:   {self.survival_rate:.2%}",
            f"Worst L-Streak:  {self.worst_loss_streak}",
            f"Composite Score: {self.composite_score:.4f}",
        ]
        return "\n".join(lines)


@dataclass
class SingleSimResult:
    """Results from a single simulation run."""

    rounds_completed: int
    starting_balance: float
    final_balance: float
    roi: float
    max_drawdown: float
    max_loss_streak: int
    max_win_streak: int
    total_wagered: float
    win_count: int
    loss_count: int
    survived: bool
    equity_curve: List[float] = field(default_factory=list)
    per_bet_returns: List[float] = field(default_factory=list)


def compute_metrics(
    strategy_name: str,
    params: dict,
    sim_results: List[SingleSimResult],
    rounds_per_sim: int,
    ruin_threshold: float = 0.05,
) -> StrategyMetricsReport:
    """Compute aggregate metrics from multiple simulation runs.

    Args:
        strategy_name: Strategy identifier.
        params: Strategy parameters used.
        sim_results: List of per-simulation results.
        rounds_per_sim: Target rounds per simulation.
        ruin_threshold: Balance fraction below which counts as ruin (e.g. 5%).
    """
    n = len(sim_results)
    if n == 0:
        return StrategyMetricsReport(
            strategy_name=strategy_name,
            params=params,
            num_simulations=0,
            rounds_per_sim=rounds_per_sim,
        )

    rois = [s.roi for s in sim_results]
    finals = [s.final_balance for s in sim_results]
    drawdowns = [s.max_drawdown for s in sim_results]
    loss_streaks = [s.max_loss_streak for s in sim_results]
    win_streaks = [s.max_win_streak for s in sim_results]
    wagered = [s.total_wagered for s in sim_results]
    survivals = [s.survived for s in sim_results]
    rounds_completed = [s.rounds_completed for s in sim_results]

    total_wins = sum(s.win_count for s in sim_results)
    total_losses = sum(s.loss_count for s in sim_results)

    # Collect all per-bet returns across all sims for EV/volatility
    all_returns: List[float] = []
    for s in sim_results:
        all_returns.extend(s.per_bet_returns)

    # Expected Value: average per-bet return
    ev = statistics.mean(all_returns) if all_returns else 0.0

    # Profit Factor: gross wins / gross losses
    gross_wins = sum(r for r in all_returns if r > 0)
    gross_losses = abs(sum(r for r in all_returns if r < 0))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else float("inf") if gross_wins > 0 else 0.0

    # ROI statistics
    avg_roi = statistics.mean(rois)
    median_roi = statistics.median(rois)

    # Risk metrics
    max_dd = max(drawdowns) if drawdowns else 0.0
    avg_dd = statistics.mean(drawdowns) if drawdowns else 0.0
    vol = statistics.stdev(all_returns) if len(all_returns) > 1 else 0.0

    # Risk of Ruin: fraction of sims where final balance fell below threshold
    starting = sim_results[0].starting_balance if sim_results else 100.0
    ruin_count = sum(1 for s in sim_results if s.final_balance <= starting * ruin_threshold)
    risk_of_ruin = ruin_count / n

    # Sharpe Ratio
    sharpe = (ev / vol) if vol > 0 else 0.0

    # Streaks
    avg_max_ls = statistics.mean(loss_streaks) if loss_streaks else 0.0
    worst_ls = max(loss_streaks) if loss_streaks else 0
    avg_max_ws = statistics.mean(win_streaks) if win_streaks else 0.0

    # Survival
    survival_rate = sum(1 for s in survivals if s) / n
    avg_surv_rounds = statistics.mean(rounds_completed) if rounds_completed else 0.0

    # Balance distribution
    sorted_finals = sorted(finals)
    avg_final = statistics.mean(finals)
    median_final = statistics.median(finals)
    p5_idx = max(0, int(n * 0.05))
    p95_idx = min(n - 1, int(n * 0.95))
    p5_final = sorted_finals[p5_idx]
    p95_final = sorted_finals[p95_idx]

    # Wager
    avg_wagered = statistics.mean(wagered) if wagered else 0.0

    # Composite score: weighted combination
    composite = _compute_composite_score(
        ev=ev,
        profit_factor=profit_factor,
        avg_roi=avg_roi,
        max_drawdown=max_dd,
        risk_of_ruin=risk_of_ruin,
        sharpe=sharpe,
        survival_rate=survival_rate,
        volatility=vol,
    )

    return StrategyMetricsReport(
        strategy_name=strategy_name,
        params=params,
        num_simulations=n,
        rounds_per_sim=rounds_per_sim,
        expected_value=ev,
        profit_factor=profit_factor,
        avg_roi=avg_roi,
        median_roi=median_roi,
        max_drawdown=max_dd,
        avg_drawdown=avg_dd,
        risk_of_ruin=risk_of_ruin,
        volatility=vol,
        sharpe_ratio=sharpe,
        avg_max_loss_streak=avg_max_ls,
        worst_loss_streak=worst_ls,
        avg_max_win_streak=avg_max_ws,
        survival_rate=survival_rate,
        avg_survival_rounds=avg_surv_rounds,
        avg_final_balance=avg_final,
        median_final_balance=median_final,
        p5_final_balance=p5_final,
        p95_final_balance=p95_final,
        avg_total_wagered=avg_wagered,
        composite_score=composite,
        sim_results=sim_results,
    )


def _compute_composite_score(
    *,
    ev: float,
    profit_factor: float,
    avg_roi: float,
    max_drawdown: float,
    risk_of_ruin: float,
    sharpe: float,
    survival_rate: float,
    volatility: float,
) -> float:
    """Compute a single composite score for ranking strategies.

    Higher is better. Penalizes high risk, rewards stable profitability.
    """
    # Normalize components to roughly [0, 1] or bounded range
    ev_score = math.tanh(ev * 1000)  # scale small EV values
    pf_score = min(profit_factor / 2.0, 1.0) if profit_factor < float("inf") else 1.0
    roi_score = math.tanh(avg_roi / 50.0)
    dd_penalty = max_drawdown  # 0 to 1
    ruin_penalty = risk_of_ruin  # 0 to 1
    sharpe_score = math.tanh(sharpe)
    surv_score = survival_rate

    score = (
        0.20 * ev_score
        + 0.15 * pf_score
        + 0.15 * roi_score
        + 0.20 * sharpe_score
        + 0.15 * surv_score
        - 0.10 * dd_penalty
        - 0.15 * ruin_penalty
    )
    return score
