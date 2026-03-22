"""High-performance strategy simulation engine.

Runs strategies through a fast dry-run loop using the actual strategy interface
(next_bet / on_bet_result) with provably-fair dice simulation.

Supports:
- Single strategy evaluation over N rounds
- Multi-seed parallel evaluation
- Batch evaluation across parameter grids
"""

from __future__ import annotations

import os
import random
import time
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from .metrics import SingleSimResult

try:
    from ..betbot_strategies import get_strategy
    from ..betbot_strategies.base import (
        BetResult,
        BetSpec,
        SessionLimits,
        StrategyContext,
    )
except ImportError:
    import os
    import sys

    _src = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _src not in sys.path:
        sys.path.insert(0, _src)
    from betbot_strategies import get_strategy
    from betbot_strategies.base import (
        BetResult,
        BetSpec,
        SessionLimits,
        StrategyContext,
    )


# ---------------------------------------------------------------------------
# Dice simulation helpers
# ---------------------------------------------------------------------------

def _simulate_dice_roll(rng: random.Random) -> float:
    """Generate a provably-fair dice roll in [0.00, 99.99]."""
    return round(rng.uniform(0.0, 99.99), 2)


def _dice_win(roll: float, chance: float, is_high: bool) -> bool:
    if is_high:
        return roll >= (100.0 - chance)
    return roll < chance


def _range_dice_win(roll_int: int, lo: int, hi: int, is_in: bool) -> bool:
    inside = lo <= roll_int <= hi
    return inside if is_in else not inside


def _payout_for_chance(chance: float, house_edge: float = 1.0) -> float:
    """Compute payout multiplier for a given win chance (percent)."""
    if chance <= 0:
        return 0.0
    return (100.0 - house_edge) / chance


# ---------------------------------------------------------------------------
# Minimal API stub for simulation contexts
# ---------------------------------------------------------------------------

class _SimAPI:
    """Lightweight API stub for strategy contexts during simulation."""

    def __init__(self, symbol: str, balance: str):
        self._symbol = symbol.upper()
        self._balance = str(balance)

    def get_user_info(self) -> Dict[str, Any]:
        return {
            "username": "sim_user",
            "hash": "sim",
            "balances": [
                {"currency": self._symbol, "main": self._balance, "faucet": "0"}
            ],
        }


# ---------------------------------------------------------------------------
# Core simulator
# ---------------------------------------------------------------------------

class StrategySimulator:
    """Run strategies through fast dry-run simulation."""

    def __init__(
        self,
        house_edge: float = 1.0,
        ruin_balance_fraction: float = 0.001,
    ) -> None:
        self.house_edge = house_edge
        self.ruin_balance_fraction = ruin_balance_fraction

    def simulate_single(
        self,
        strategy_name: str,
        params: Dict[str, Any],
        rounds: int = 1000,
        starting_balance: float = 100.0,
        symbol: str = "BTC",
        seed: Optional[int] = None,
        stop_loss: float = -0.99,
        take_profit: Optional[float] = None,
    ) -> SingleSimResult:
        """Run a single simulation of a strategy.

        Instantiates the real strategy class and drives it through
        next_bet() / on_bet_result() for `rounds` iterations.
        """
        rng = random.Random(seed)
        strategy_class = get_strategy(strategy_name)

        balance = Decimal(str(starting_balance))
        start_bal = balance
        ruin_floor = start_bal * Decimal(str(self.ruin_balance_fraction))

        limits = SessionLimits(symbol=symbol, stop_loss=stop_loss)
        if take_profit is not None:
            limits.take_profit = take_profit

        ctx = StrategyContext(
            api=_SimAPI(symbol, str(balance)),
            symbol=symbol,
            faucet=False,
            dry_run=True,
            rng=rng,
            logger=lambda _: None,
            limits=limits,
            starting_balance=str(balance),
            printer=lambda _: None,
        )

        strat = strategy_class(params, ctx)
        strat.on_session_start()

        equity: List[float] = [float(balance)]
        per_bet_returns: List[float] = []
        win_count = 0
        loss_count = 0
        total_wagered = Decimal("0")

        win_streak = 0
        loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0

        rounds_done = 0

        for _ in range(rounds):
            if balance <= ruin_floor:
                break

            # Stop-loss check
            profit_pct = float((balance - start_bal) / start_bal) if start_bal > 0 else 0.0
            if profit_pct <= stop_loss:
                break
            if take_profit is not None and profit_pct >= take_profit:
                break

            bet_spec = strat.next_bet()
            if bet_spec is None:
                break

            # Parse bet
            try:
                amount = Decimal(str(bet_spec.get("amount", "0")))
            except (InvalidOperation, TypeError):
                amount = Decimal("0")

            if amount <= 0 or amount > balance:
                amount = min(balance, Decimal("0.00000001"))

            total_wagered += amount
            game = str(bet_spec.get("game", "dice"))

            # Simulate outcome
            roll = _simulate_dice_roll(rng)
            roll_int = int(roll * 100)

            if game == "range-dice":
                range_val = bet_spec.get("range", (0, 4999))
                is_in = bool(bet_spec.get("is_in", True))
                lo, hi = int(range_val[0]), int(range_val[1])
                win = _range_dice_win(roll_int, lo, hi, is_in)
                # Chance for range dice
                span = hi - lo + 1
                chance_pct = (span / 10000.0) * 100.0
                if not is_in:
                    chance_pct = 100.0 - chance_pct
            else:
                chance_str = str(bet_spec.get("chance", "49.5"))
                try:
                    chance_pct = float(chance_str)
                except (ValueError, TypeError):
                    chance_pct = 49.5
                is_high = bool(bet_spec.get("is_high", True))
                win = _dice_win(roll, chance_pct, is_high)

            payout_mult = _payout_for_chance(chance_pct, self.house_edge)

            if win:
                profit = amount * Decimal(str(payout_mult - 1.0))
                balance += profit
                win_count += 1
                win_streak += 1
                loss_streak = 0
            else:
                profit = -amount
                balance += profit
                loss_count += 1
                loss_streak += 1
                win_streak = 0

            max_win_streak = max(max_win_streak, win_streak)
            max_loss_streak = max(max_loss_streak, loss_streak)

            bal_float = float(balance)
            equity.append(bal_float)
            per_bet_returns.append(float(profit) / float(start_bal) if start_bal > 0 else 0.0)

            # Feed result back to strategy
            result: BetResult = {
                "win": win,
                "profit": str(profit),
                "balance": str(balance),
                "number": roll_int,
                "simulated": True,
                "timestamp": time.time(),
            }
            ctx.recent_results.append(result)
            strat.on_bet_result(result)
            rounds_done += 1

        strat.on_session_end("simulation_complete")

        final_bal = float(balance)
        roi = ((final_bal - starting_balance) / starting_balance * 100) if starting_balance > 0 else 0.0

        # Compute max drawdown from equity curve
        max_dd = _max_drawdown(equity)

        survived = balance > ruin_floor and rounds_done >= rounds

        return SingleSimResult(
            rounds_completed=rounds_done,
            starting_balance=starting_balance,
            final_balance=final_bal,
            roi=roi,
            max_drawdown=max_dd,
            max_loss_streak=max_loss_streak,
            max_win_streak=max_win_streak,
            total_wagered=float(total_wagered),
            win_count=win_count,
            loss_count=loss_count,
            survived=survived,
            equity_curve=equity,
            per_bet_returns=per_bet_returns,
        )

    def simulate_multi_seed(
        self,
        strategy_name: str,
        params: Dict[str, Any],
        rounds: int = 1000,
        starting_balance: float = 100.0,
        symbol: str = "BTC",
        num_seeds: int = 50,
        base_seed: int = 42,
        stop_loss: float = -0.99,
        take_profit: Optional[float] = None,
        parallel: bool = True,
        max_workers: Optional[int] = None,
    ) -> List[SingleSimResult]:
        """Run simulation across multiple seeds for statistical robustness.

        When ``parallel=True``, uses a process pool for concurrent execution.
        """
        seeds = [base_seed + i for i in range(num_seeds)]
        kw = dict(
            strategy_name=strategy_name,
            params=params,
            rounds=rounds,
            starting_balance=starting_balance,
            symbol=symbol,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        if parallel and num_seeds > 1:
            return self._run_parallel(seeds, kw, max_workers)

        results = []
        for seed in seeds:
            results.append(self.simulate_single(seed=seed, **kw))
        return results

    def batch_simulate(
        self,
        strategy_specs: List[Tuple[str, Dict[str, Any]]],
        rounds: int = 1000,
        starting_balance: float = 100.0,
        symbol: str = "BTC",
        num_seeds: int = 20,
        base_seed: int = 42,
        stop_loss: float = -0.99,
        take_profit: Optional[float] = None,
        parallel: bool = True,
        max_workers: Optional[int] = None,
    ) -> Dict[str, List[SingleSimResult]]:
        """Evaluate multiple strategies at once.

        Args:
            strategy_specs: List of ``(strategy_name, params)`` tuples.

        Returns:
            ``{strategy_name: [SingleSimResult, ...]}``
        """
        results: Dict[str, List[SingleSimResult]] = {}
        for name, params in strategy_specs:
            try:
                res = self.simulate_multi_seed(
                    strategy_name=name,
                    params=params,
                    rounds=rounds,
                    starting_balance=starting_balance,
                    symbol=symbol,
                    num_seeds=num_seeds,
                    base_seed=base_seed,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    parallel=parallel,
                    max_workers=max_workers,
                )
                results[name] = res
            except Exception:
                import logging
                logging.getLogger(__name__).exception("batch_simulate failed for %s", name)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_parallel(
        self,
        seeds: List[int],
        kw: Dict[str, Any],
        max_workers: Optional[int],
    ) -> List[SingleSimResult]:
        """Execute simulations across seeds using a process pool."""
        from concurrent.futures import ProcessPoolExecutor, as_completed

        workers = max_workers or min(len(seeds), os.cpu_count() or 4)
        args_list = [(self.house_edge, self.ruin_balance_fraction, seed, kw) for seed in seeds]

        results: List[Optional[SingleSimResult]] = [None] * len(seeds)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {
                executor.submit(_simulate_worker, a): i
                for i, a in enumerate(args_list)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()

        return [r for r in results if r is not None]


def _max_drawdown(equity: List[float]) -> float:
    """Compute max drawdown as a fraction (0 to 1)."""
    if len(equity) < 2:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for val in equity[1:]:
        if val > peak:
            peak = val
        elif peak > 0:
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _simulate_worker(args: tuple) -> SingleSimResult:
    """Top-level worker for ProcessPoolExecutor (must be picklable)."""
    house_edge, ruin_frac, seed, kw = args
    sim = StrategySimulator(house_edge=house_edge, ruin_balance_fraction=ruin_frac)
    return sim.simulate_single(seed=seed, **kw)
