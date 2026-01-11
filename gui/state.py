"""
Global application state for the NiceGUI interface.
Thread-safe reactive state management.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from threading import Lock
from datetime import datetime


@dataclass
class BetRecord:
    """Single bet record for history tracking"""
    timestamp: datetime
    amount: float
    target: float
    roll: float
    won: bool
    profit: float
    balance: float
    strategy: str


@dataclass
class AppState:
    """Global application state - single source of truth"""
    
    # Bot status
    running: bool = False
    paused: bool = False
    simulation_mode: bool = True  # Safe default: always start in simulation
    
    # Connection
    api_key: str = ""
    api_connected: bool = False
    currency: str = "btc"
    
    # Balance & Profit
    balance: float = 0.0
    starting_balance: float = 0.0
    profit: float = 0.0
    profit_percent: float = 0.0
    
    # Betting stats
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    current_streak: int = 0
    streak_type: str = ""  # "win" or "loss"
    
    # Strategy
    strategy_name: str = "martingale"  # For strategies_ui compatibility
    current_strategy: str = "Flat Betting"  # Legacy field
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    # Stop conditions
    stop_profit_pct: Optional[float] = None  # Percent profit target
    stop_loss_pct: Optional[float] = None  # Percent loss limit
    stop_profit: Optional[float] = 0.1  # Legacy: 10% profit
    stop_loss: Optional[float] = -0.05  # Legacy: -5% loss
    max_bets: Optional[int] = None
    min_balance: Optional[float] = None
    bet_delay: float = 1.0  # Delay between bets in seconds
    
    # History
    bet_history: List[BetRecord] = field(default_factory=list)
    
    # Error state
    last_error: str = ""
    error_count: int = 0
    stop_reason: str = ""  # Reason why bot stopped (if applicable)
    
    # Thread safety
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)
    
    def update(self, **kwargs):
        """Thread-safe state update"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    def get(self, key: str, default=None):
        """Thread-safe state read"""
        with self._lock:
            return getattr(self, key, default)
    
    def add_bet(self, bet: BetRecord):
        """Add bet to history (thread-safe)"""
        with self._lock:
            self.bet_history.append(bet)
            if len(self.bet_history) > 10000:  # Limit history size
                self.bet_history = self.bet_history[-10000:]
    
    def clear_history(self):
        """Clear bet history"""
        with self._lock:
            self.bet_history.clear()
            self.total_bets = 0
            self.wins = 0
            self.losses = 0
            self.current_streak = 0
            self.streak_type = ""
    
    def reset_session(self):
        """Reset session stats (keep history)"""
        with self._lock:
            self.starting_balance = self.balance
            self.profit = 0.0
            self.profit_percent = 0.0
            self.total_bets = 0
            self.wins = 0
            self.losses = 0
            self.current_streak = 0
            self.streak_type = ""
            self.last_error = ""
            self.error_count = 0


# Global singleton instance
app_state = AppState()
