"""
Data models for the simulator.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from datetime import datetime


@dataclass
class SimulationConfig:
    """Configuration for simulation."""
    starting_balance: Decimal
    currency: str
    house_edge: float = 3.0  # 0-100 (default 3.0%)
    max_bets: Optional[int] = None
    seed: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.starting_balance <= 0:
            raise ValueError("Starting balance must be positive")
        if not 0 <= self.house_edge <= 100:
            raise ValueError("House edge must be between 0 and 100")


@dataclass
class SimulatedBet:
    """Result of a simulated bet."""
    bet_number: int
    timestamp: datetime
    amount: Decimal
    chance: float
    roll_over: bool
    outcome: float  # 0-100
    won: bool
    profit: Decimal
    balance_after: Decimal
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'bet_number': self.bet_number,
            'timestamp': self.timestamp.isoformat(),
            'amount': str(self.amount),
            'chance': self.chance,
            'roll_over': self.roll_over,
            'outcome': self.outcome,
            'won': self.won,
            'profit': str(self.profit),
            'balance_after': str(self.balance_after),
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for simulation."""
    total_bets: int
    wins: int
    losses: int
    win_rate: float
    total_wagered: Decimal
    profit_loss: Decimal
    roi: float
    max_win_streak: int
    max_loss_streak: int
    avg_bet_size: Decimal
    avg_win_amount: Decimal
    avg_loss_amount: Decimal
    profit_factor: float
    expected_value: float
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'total_bets': self.total_bets,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': self.win_rate,
            'total_wagered': str(self.total_wagered),
            'profit_loss': str(self.profit_loss),
            'roi': self.roi,
            'max_win_streak': self.max_win_streak,
            'max_loss_streak': self.max_loss_streak,
            'avg_bet_size': str(self.avg_bet_size),
            'avg_win_amount': str(self.avg_win_amount),
            'avg_loss_amount': str(self.avg_loss_amount),
            'profit_factor': self.profit_factor,
            'expected_value': self.expected_value,
        }


@dataclass
class RiskAnalysis:
    """Risk analysis metrics."""
    max_drawdown: Decimal
    max_drawdown_pct: float
    current_drawdown: Decimal
    current_drawdown_pct: float
    peak_balance: Decimal
    variance: float
    std_deviation: float
    suggested_bankroll: Decimal
    risk_of_ruin: float  # 0-1
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'max_drawdown': str(self.max_drawdown),
            'max_drawdown_pct': self.max_drawdown_pct,
            'current_drawdown': str(self.current_drawdown),
            'current_drawdown_pct': self.current_drawdown_pct,
            'peak_balance': str(self.peak_balance),
            'variance': self.variance,
            'std_deviation': self.std_deviation,
            'suggested_bankroll': str(self.suggested_bankroll),
            'risk_of_ruin': self.risk_of_ruin,
        }


@dataclass
class SimulationResult:
    """Complete simulation results."""
    config: SimulationConfig
    bets: List[SimulatedBet] = field(default_factory=list)
    metrics: Optional[PerformanceMetrics] = None
    risk_analysis: Optional[RiskAnalysis] = None
    final_balance: Decimal = Decimal('0')
    total_time: float = 0.0  # seconds
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'config': {
                'starting_balance': str(self.config.starting_balance),
                'currency': self.config.currency,
                'house_edge': self.config.house_edge,
                'max_bets': self.config.max_bets,
                'seed': self.config.seed,
            },
            'bets': [bet.to_dict() for bet in self.bets],
            'metrics': self.metrics.to_dict() if self.metrics else None,
            'risk_analysis': self.risk_analysis.to_dict() if self.risk_analysis else None,
            'final_balance': str(self.final_balance),
            'total_time': self.total_time,
        }
