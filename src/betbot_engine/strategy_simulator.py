from __future__ import annotations
"""
Strategy simulator: runs any registered strategy in pure-Python simulation mode.

No API calls, no sleeps, no UI. Suitable for Monte Carlo batch runs across all
strategies to produce comparative performance data.
"""

import math
import random
import statistics
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from betbot_strategies.base import BetResult, BetSpec, SessionLimits, StrategyContext


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    """Results from a single simulation run (one strategy, one seed)."""
    bets: int
    wins: int
    losses: int
    starting_balance: float
    final_balance: float
    min_balance: float
    max_balance: float
    total_wagered: float
    equity_curve: List[float]           # balance after each bet
    max_win_streak: int
    max_loss_streak: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.bets if self.bets else 0.0

    @property
    def roi(self) -> float:
        if self.starting_balance <= 0:
            return 0.0
        return (self.final_balance - self.starting_balance) / self.starting_balance * 100

    @property
    def max_drawdown(self) -> float:
        """Peak-to-trough as a fraction (0–1)."""
        curve = self.equity_curve
        if len(curve) < 2:
            return 0.0
        peak = curve[0]
        max_dd = 0.0
        for v in curve[1:]:
            if v > peak:
                peak = v
            elif peak > 0:
                dd = (peak - v) / peak
                max_dd = max(max_dd, dd)
        return max_dd

    @property
    def sharpe_ratio(self) -> float:
        curve = self.equity_curve
        if len(curve) < 3:
            return 0.0
        returns = [
            (curve[i] - curve[i - 1]) / curve[i - 1]
            for i in range(1, len(curve))
            if curve[i - 1] > 0
        ]
        if len(returns) < 2:
            return 0.0
        mu = statistics.mean(returns)
        sigma = statistics.stdev(returns)
        return (mu / sigma * math.sqrt(len(returns))) if sigma > 0 else 0.0

    @property
    def profit(self) -> float:
        return self.final_balance - self.starting_balance


@dataclass
class StrategySimResult:
    """Aggregated results across N Monte Carlo runs for one strategy."""
    strategy_name: str
    n_runs: int
    bets_per_run: int
    starting_balance: float

    # Distribution across runs
    roi_values: List[float]             # one per run
    final_balance_values: List[float]
    win_rate_values: List[float]
    max_drawdown_values: List[float]
    sharpe_values: List[float]
    max_loss_streak_values: List[int]

    # Representative equity curves (downsampled to ~200 pts each)
    equity_curves: List[List[float]]    # all runs (downsampled)

    # Aggregated equity band (p10, mean, p90 per step)
    band_p10: List[float] = field(default_factory=list)
    band_mean: List[float] = field(default_factory=list)
    band_p90: List[float] = field(default_factory=list)

    @property
    def roi_mean(self) -> float:
        return statistics.mean(self.roi_values) if self.roi_values else 0.0

    @property
    def roi_median(self) -> float:
        return statistics.median(self.roi_values) if self.roi_values else 0.0

    @property
    def roi_std(self) -> float:
        return statistics.stdev(self.roi_values) if len(self.roi_values) > 1 else 0.0

    @property
    def win_rate_mean(self) -> float:
        return statistics.mean(self.win_rate_values) if self.win_rate_values else 0.0

    @property
    def max_drawdown_mean(self) -> float:
        return statistics.mean(self.max_drawdown_values) if self.max_drawdown_values else 0.0

    @property
    def max_drawdown_worst(self) -> float:
        return max(self.max_drawdown_values) if self.max_drawdown_values else 0.0

    @property
    def sharpe_mean(self) -> float:
        return statistics.mean(self.sharpe_values) if self.sharpe_values else 0.0

    @property
    def profitable_run_pct(self) -> float:
        if not self.roi_values:
            return 0.0
        return sum(1 for r in self.roi_values if r > 0) / len(self.roi_values) * 100

    @property
    def ruin_pct(self) -> float:
        """Percentage of runs that lost 80%+ of starting balance."""
        if not self.final_balance_values:
            return 0.0
        ruin_threshold = self.starting_balance * 0.2
        return sum(1 for b in self.final_balance_values if b <= ruin_threshold) / len(self.final_balance_values) * 100

    @property
    def avg_loss_streak(self) -> float:
        return statistics.mean(self.max_loss_streak_values) if self.max_loss_streak_values else 0.0


# ── Simulator core ────────────────────────────────────────────────────────────

_SILENT: Callable[[Any], None] = lambda _: None
_MIN_BALANCE = Decimal("0.00000001")


def _make_context(starting_balance: float, seed: int) -> StrategyContext:
    """Build a minimal StrategyContext for simulation (no API, no sleep)."""
    return StrategyContext(
        api=None,  # type: ignore[arg-type]
        symbol="USD",
        faucet=False,
        dry_run=True,
        rng=random.Random(seed),
        logger=_SILENT,
        limits=SessionLimits(symbol="USD"),
        delay_ms=0,
        jitter_ms=0,
        starting_balance=str(starting_balance),
        printer=_SILENT,
    )


def _resolve_bet(spec: BetSpec, balance: Decimal, rng: random.Random) -> Tuple[bool, Decimal, Decimal]:
    """
    Resolve a BetSpec to (win, profit, actual_amount).
    Returns (win, profit, amount_placed).
    """
    try:
        amount = Decimal(str(spec.get("amount", "0.1")))
    except Exception:
        amount = Decimal("0.1")

    amount = max(amount, _MIN_BALANCE)
    amount = min(amount, balance)

    if spec.get("game", "dice") == "range-dice":
        r = spec.get("range") or (0, 0)
        is_in = bool(spec.get("is_in", True))
        size = max(0, (r[1] - r[0] + 1))
        prob = size / 10000.0
        win_prob = prob if is_in else (1.0 - prob)
        payout_mult = 0.99 / max(1e-9, win_prob)
    else:
        try:
            chance = float(spec.get("chance", "50"))
        except (ValueError, TypeError):
            chance = 50.0
        chance = max(0.01, min(98.0, chance))
        win_prob = chance / 100.0
        payout_mult = 99.0 / chance

    win = rng.random() < win_prob
    profit = amount * Decimal(str(payout_mult - 1)) if win else -amount
    return win, profit, amount


def _downsample(curve: List[float], target: int = 200) -> List[float]:
    """Reduce equity curve to at most `target` points."""
    if len(curve) <= target:
        return curve
    step = len(curve) / target
    return [curve[int(i * step)] for i in range(target)] + [curve[-1]]


def run_single(
    strategy_cls: Type,
    params: Dict[str, Any],
    n_bets: int,
    starting_balance: float,
    seed: int,
) -> RunResult:
    """Run one strategy for up to n_bets bets. Returns RunResult."""
    ctx = _make_context(starting_balance, seed)
    strategy = strategy_cls(params, ctx)
    strategy.on_session_start()

    balance = Decimal(str(starting_balance))
    equity: List[float] = [float(balance)]
    wins = losses = 0
    total_wagered = Decimal("0")
    min_bal = max_bal = float(balance)
    win_streak = loss_streak = 0
    max_win_streak = max_loss_streak = 0

    for _ in range(n_bets):
        if balance <= _MIN_BALANCE:
            break

        spec = strategy.next_bet()
        if spec is None:
            break

        win, profit, amount_placed = _resolve_bet(spec, balance, ctx.rng)
        balance += profit
        total_wagered += amount_placed

        if balance < _MIN_BALANCE:
            balance = Decimal("0")

        result: BetResult = {
            "win": win,
            "profit": format(profit, "f"),
            "balance": format(balance, "f"),
            "number": ctx.rng.randint(0, 9999),
            "payout": "",
            "chance": str(spec.get("chance", "")),
            "is_high": spec.get("is_high"),
            "range": spec.get("range"),
            "is_in": spec.get("is_in"),
            "api_raw": {"simulated": True},
            "simulated": True,
            "timestamp": 0.0,
        }
        strategy.on_bet_result(result)

        if win:
            wins += 1
            win_streak += 1
            loss_streak = 0
        else:
            losses += 1
            loss_streak += 1
            win_streak = 0
        max_win_streak = max(max_win_streak, win_streak)
        max_loss_streak = max(max_loss_streak, loss_streak)

        b = float(balance)
        equity.append(b)
        if b < min_bal:
            min_bal = b
        if b > max_bal:
            max_bal = b

    total_bets = wins + losses
    strategy.on_session_end("simulation complete")

    return RunResult(
        bets=total_bets,
        wins=wins,
        losses=losses,
        starting_balance=starting_balance,
        final_balance=float(balance),
        min_balance=min_bal,
        max_balance=max_bal,
        total_wagered=float(total_wagered),
        equity_curve=equity,
        max_win_streak=max_win_streak,
        max_loss_streak=max_loss_streak,
    )


def simulate_strategy(
    strategy_cls: Type,
    params: Dict[str, Any],
    n_bets: int = 500,
    n_runs: int = 30,
    starting_balance: float = 100.0,
    base_seed: int = 42,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> StrategySimResult:
    """
    Run Monte Carlo simulation for one strategy.

    Args:
        strategy_cls:    Strategy class (registered AutoBetStrategy)
        params:          Strategy params dict (defaults used if not specified)
        n_bets:          Number of bets per run
        n_runs:          Number of independent Monte Carlo runs
        starting_balance: Starting balance in USD
        base_seed:       Base random seed (each run uses base_seed + run_index)
        progress_cb:     Optional callback(run_index, total_runs)

    Returns:
        StrategySimResult with aggregated statistics
    """
    roi_vals: List[float] = []
    final_bals: List[float] = []
    win_rates: List[float] = []
    max_dds: List[float] = []
    sharpes: List[float] = []
    loss_streaks: List[int] = []
    all_curves: List[List[float]] = []

    for i in range(n_runs):
        if progress_cb:
            progress_cb(i, n_runs)
        try:
            run = run_single(strategy_cls, params, n_bets, starting_balance, base_seed + i)
        except Exception:
            # Strategy crashed — treat as a total loss run
            run = RunResult(
                bets=0, wins=0, losses=0,
                starting_balance=starting_balance, final_balance=0.0,
                min_balance=0.0, max_balance=starting_balance,
                total_wagered=0.0,
                equity_curve=[starting_balance, 0.0],
                max_win_streak=0, max_loss_streak=0,
            )

        roi_vals.append(run.roi)
        final_bals.append(run.final_balance)
        win_rates.append(run.win_rate)
        max_dds.append(run.max_drawdown)
        sharpes.append(run.sharpe_ratio)
        loss_streaks.append(run.max_loss_streak)
        all_curves.append(_downsample(run.equity_curve, 200))

    # Build equity band (p10 / mean / p90) per time step
    band_len = max(len(c) for c in all_curves) if all_curves else 0
    # Pad short curves with their final value
    padded = [c + [c[-1]] * (band_len - len(c)) if c else [starting_balance] * band_len
              for c in all_curves]
    band_p10 = band_mean = band_p90 = []
    if padded and band_len:
        band_p10 = [_percentile([run[t] for run in padded], 10) for t in range(band_len)]
        band_mean = [statistics.mean([run[t] for run in padded]) for t in range(band_len)]
        band_p90 = [_percentile([run[t] for run in padded], 90) for t in range(band_len)]

    name = strategy_cls.name() if hasattr(strategy_cls, "name") else str(strategy_cls)

    result = StrategySimResult(
        strategy_name=name,
        n_runs=n_runs,
        bets_per_run=n_bets,
        starting_balance=starting_balance,
        roi_values=roi_vals,
        final_balance_values=final_bals,
        win_rate_values=win_rates,
        max_drawdown_values=max_dds,
        sharpe_values=sharpes,
        max_loss_streak_values=loss_streaks,
        equity_curves=all_curves,
        band_p10=band_p10,
        band_mean=band_mean,
        band_p90=band_p90,
    )
    return result


def _percentile(data: List[float], pct: int) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = (len(s) - 1) * pct / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def default_params(strategy_cls: Type) -> Dict[str, Any]:
    """Return default params from a strategy's schema."""
    try:
        schema = strategy_cls.schema()
        return {k: v.get("default") for k, v in schema.items() if "default" in v}
    except Exception:
        return {}
