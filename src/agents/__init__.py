"""Autonomous dice strategy intelligence system.

Provides:
- High-performance simulation engine for strategy evaluation
- Metrics computation (EV, drawdown, risk of ruin, Sharpe, etc.)
- Strategy analyst agent (ranking, pruning, optimization, evolution)
- Gambler execution agent (adaptive switching, risk management)
- Persistent memory manager for user ecosystem knowledge
"""

from .gambler_agent import GamblerAgent
from .memory import MemoryManager
from .metrics import StrategyMetricsReport, compute_metrics
from .simulation import StrategySimulator
from .strategy_analyst import StrategyAnalyst

__all__ = [
    "StrategySimulator",
    "StrategyMetricsReport",
    "compute_metrics",
    "StrategyAnalyst",
    "GamblerAgent",
    "MemoryManager",
]
