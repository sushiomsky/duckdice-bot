"""
Simulator package for DuckDice Bot.

Provides simulation engine, backtesting, and risk analysis tools.
"""

from .models import (
    SimulationConfig,
    SimulatedBet,
    SimulationResult,
    PerformanceMetrics,
    RiskAnalysis,
)
from .simulation_engine import SimulationEngine, VirtualBalance, OutcomeGenerator
from .performance_metrics import MetricsCalculator
from .risk_analyzer import RiskAnalyzer, DrawdownTracker
from .backtest_engine import (
    BacktestEngine,
    HistoricalDataLoader,
    HistoricalOutcomeGenerator,
)

__all__ = [
    'SimulationConfig',
    'SimulatedBet',
    'SimulationResult',
    'PerformanceMetrics',
    'RiskAnalysis',
    'SimulationEngine',
    'VirtualBalance',
    'OutcomeGenerator',
    'MetricsCalculator',
    'RiskAnalyzer',
    'DrawdownTracker',
    'BacktestEngine',
    'HistoricalDataLoader',
    'HistoricalOutcomeGenerator',
]
