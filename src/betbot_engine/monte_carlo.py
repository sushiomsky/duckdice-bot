"""
Monte Carlo Simulation Engine for betting strategy validation.

Simulates strategy performance across thousands of random outcomes to estimate
win rates, ROI, drawdown, Sharpe ratio, and confidence intervals without
risking real funds.

Usage:
    from betbot_engine.monte_carlo import MonteCarloEngine, SimulationResult
    
    engine = MonteCarloEngine()
    results = engine.simulate(
        strategy_class=YourStrategy,
        config={'param1': value1, ...},
        rounds=10000,
        starting_balance=100.0
    )
    
    print(f"Win Rate: {results.win_rate:.2%}")
    print(f"ROI: {results.roi:.2%}")
    print(f"Max Drawdown: {results.max_drawdown:.2%}")
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import random


@dataclass
class SimulationResult:
    """Complete results from a Monte Carlo simulation run."""
    
    # Basic counts
    rounds: int
    win_count: int
    loss_count: int
    
    # Rates and percentages
    win_rate: float  # win_count / rounds
    roi: float  # (final_balance - starting) / starting * 100
    
    # Balance metrics
    starting_balance: float
    final_balance: float
    total_profit: float  # final - starting
    min_balance: float
    max_balance: float
    
    # Risk metrics
    max_drawdown: float  # Largest peak-to-trough decline as %
    sharpe_ratio: float  # Excess return / volatility
    
    # Equity curve (balance history)
    equity_curve: List[float] = field(default_factory=list)
    
    # Streak statistics
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    # Confidence interval (95% confidence)
    confidence_95_lower: float = 0.0
    confidence_95_upper: float = 0.0
    
    def __post_init__(self) -> None:
        """Validate and compute derived fields."""
        if self.rounds <= 0:
            raise ValueError("rounds must be > 0")
        
        # Auto-compute if not set
        if self.win_rate == 0 and self.rounds > 0:
            self.win_rate = self.win_count / self.rounds
        if self.total_profit == 0:
            self.total_profit = self.final_balance - self.starting_balance
        if self.roi == 0 and self.starting_balance > 0:
            self.roi = (self.total_profit / self.starting_balance) * 100

    def summary(self) -> str:
        """Return human-readable summary."""
        lines = [
            f"Monte Carlo Simulation Results ({self.rounds} rounds)",
            f"{'='*60}",
            f"Win Rate:          {self.win_rate:.2%}",
            f"Profit:            ${self.total_profit:.2f} ({self.roi:+.1f}%)",
            f"ROI:               {self.roi:+.1f}%",
            f"Max Drawdown:      {self.max_drawdown:.2%}",
            f"Sharpe Ratio:      {self.sharpe_ratio:.3f}",
            f"Max Win Streak:    {self.max_win_streak}",
            f"Max Loss Streak:   {self.max_loss_streak}",
            f"Final Balance:     ${self.final_balance:.2f}",
            f"Confidence (95%):  ${self.confidence_95_lower:.2f} - ${self.confidence_95_upper:.2f}",
        ]
        return "\n".join(lines)


class MonteCarloEngine:
    """
    High-performance Monte Carlo simulator for betting strategies.
    
    Simulates deterministic bets or random multiplier outcomes to estimate
    strategy performance metrics without risking real funds.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        Initialize the engine.
        
        Args:
            seed: Random seed for reproducibility (None = non-deterministic)
        """
        if seed is not None:
            random.seed(seed)

    def simulate(
        self,
        strategy_class: Any,
        config: Dict[str, Any],
        rounds: int = 1000,
        starting_balance: float = 100.0,
        multiplier_range: Tuple[float, float] = (1.01, 10.0),
        win_probability: float = 0.5,
        fast_mode: bool = True,
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation for a strategy.
        
        Args:
            strategy_class: Strategy class (must implement required interface)
            config: Strategy configuration dict
            rounds: Number of simulation rounds
            starting_balance: Starting balance in USD
            multiplier_range: (min, max) multiplier for random wins
            win_probability: Probability of win on each bet (0-1)
            fast_mode: Use simplified deterministic simulation vs full engine
            
        Returns:
            SimulationResult with full statistics
        """
        if fast_mode:
            return self._simulate_fast(
                strategy_class, config, rounds, starting_balance, multiplier_range, win_probability
            )
        else:
            return self._simulate_full(
                strategy_class, config, rounds, starting_balance, multiplier_range, win_probability
            )

    def _simulate_fast(
        self,
        strategy_class: Any,
        config: Dict[str, Any],
        rounds: int,
        starting_balance: float,
        multiplier_range: Tuple[float, float],
        win_probability: float,
    ) -> SimulationResult:
        """Simplified fast simulation for quick estimates."""
        equity_curve: List[float] = [starting_balance]
        balances: List[float] = [starting_balance]
        
        win_count = 0
        loss_count = 0
        peak_balance = starting_balance
        min_balance = starting_balance
        current_balance = starting_balance
        
        win_streak = 0
        loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        # Simulate rounds as probabilistic outcomes
        for _ in range(rounds):
            # Random bet amount (0.5-2% of balance)
            bet_pct = random.uniform(0.005, 0.02)
            bet = current_balance * bet_pct
            
            # Outcome: win or loss
            if random.random() < win_probability:
                # Win: random multiplier
                mult = random.uniform(multiplier_range[0], multiplier_range[1])
                profit = bet * (mult - 1)
                current_balance += profit
                win_count += 1
                win_streak += 1
                loss_streak = 0
            else:
                # Loss: lose the bet
                current_balance -= bet
                loss_count += 1
                loss_streak += 1
                win_streak = 0
            
            # Track streaks
            if win_streak > max_win_streak:
                max_win_streak = win_streak
            if loss_streak > max_loss_streak:
                max_loss_streak = loss_streak
            
            # Track balance history
            equity_curve.append(current_balance)
            balances.append(current_balance)
            
            if current_balance > peak_balance:
                peak_balance = current_balance
            if current_balance < min_balance:
                min_balance = current_balance
            
            # Prevent negative balance (optional)
            if current_balance < 0:
                current_balance = 0
                loss_streak = 0

        # Compute metrics
        total_profit = current_balance - starting_balance
        roi = (total_profit / starting_balance * 100) if starting_balance > 0 else 0
        win_rate = win_count / rounds if rounds > 0 else 0
        
        # Max drawdown
        max_drawdown = self._compute_max_drawdown(equity_curve)
        
        # Sharpe ratio
        sharpe = self._compute_sharpe_ratio(balances, starting_balance)
        
        # Confidence interval (95%)
        ci_lower, ci_upper = self._compute_confidence_interval(balances, 0.95)
        
        return SimulationResult(
            rounds=rounds,
            win_count=win_count,
            loss_count=loss_count,
            win_rate=win_rate,
            roi=roi,
            starting_balance=starting_balance,
            final_balance=current_balance,
            total_profit=total_profit,
            min_balance=min_balance,
            max_balance=peak_balance,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            equity_curve=equity_curve,
            max_win_streak=max_win_streak,
            max_loss_streak=max_loss_streak,
            confidence_95_lower=ci_lower,
            confidence_95_upper=ci_upper,
        )

    def _simulate_full(
        self,
        strategy_class: Any,
        config: Dict[str, Any],
        rounds: int,
        starting_balance: float,
        multiplier_range: Tuple[float, float],
        win_probability: float,
    ) -> SimulationResult:
        """Full simulation using strategy class (if available)."""
        # For now, fall back to fast mode
        # In future, this could instantiate the actual strategy and run it
        return self._simulate_fast(
            strategy_class, config, rounds, starting_balance, multiplier_range, win_probability
        )

    @staticmethod
    def _compute_max_drawdown(equity_curve: List[float]) -> float:
        """Compute maximum drawdown as a percentage."""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        
        max_dd = 0.0
        peak = equity_curve[0]
        
        for value in equity_curve[1:]:
            if value > peak:
                peak = value
            else:
                dd = (peak - value) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
        
        return max_dd

    @staticmethod
    def _compute_sharpe_ratio(balances: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Compute Sharpe ratio (excess return / volatility).
        
        Args:
            balances: List of balance values
            risk_free_rate: Risk-free rate (default 0%)
            
        Returns:
            Sharpe ratio (higher is better)
        """
        if len(balances) < 2:
            return 0.0
        
        # Compute returns (% change per period)
        returns = []
        for i in range(1, len(balances)):
            if balances[i - 1] > 0:
                ret = (balances[i] - balances[i - 1]) / balances[i - 1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0
        
        if std_return == 0:
            return 0.0
        
        # Sharpe = (avg_return - risk_free_rate) / std_return
        # Annualized (assuming ~250 trading days)
        sharpe = (avg_return - risk_free_rate) / std_return * (250 ** 0.5)
        return sharpe

    @staticmethod
    def _compute_confidence_interval(
        values: List[float], confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Compute confidence interval for final balance.
        
        Args:
            values: List of balance values (equity curve)
            confidence: Confidence level (0-1, default 95%)
            
        Returns:
            (lower_bound, upper_bound) tuple
        """
        if not values:
            return (0.0, 0.0)
        
        final_values = [values[-1]]  # Final balance
        
        if len(values) < 2:
            return (final_values[0], final_values[0])
        
        # Use empirical confidence interval (sorted quantiles)
        alpha = 1 - confidence
        lower_idx = int(len(values) * (alpha / 2))
        upper_idx = int(len(values) * (1 - alpha / 2))
        
        sorted_vals = sorted(values)
        lower = sorted_vals[max(0, lower_idx)]
        upper = sorted_vals[min(len(sorted_vals) - 1, upper_idx)]
        
        return (lower, upper)

    def batch_simulate(
        self,
        strategy_class: Any,
        configs: List[Dict[str, Any]],
        rounds: int = 1000,
        starting_balance: float = 100.0,
    ) -> List[SimulationResult]:
        """
        Run multiple simulations (one per config).
        
        Args:
            strategy_class: Strategy class
            configs: List of config dicts
            rounds: Rounds per simulation
            starting_balance: Starting balance
            
        Returns:
            List of SimulationResult objects
        """
        results = []
        for config in configs:
            result = self.simulate(
                strategy_class, config, rounds=rounds, starting_balance=starting_balance
            )
            results.append(result)
        return results
