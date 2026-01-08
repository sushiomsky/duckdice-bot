"""
Reactive state store for DuckDice Bot
All application state lives here - UI components react to changes
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from app.config import MAX_BET_HISTORY, HOUSE_EDGE_MAIN, HOUSE_EDGE_FAUCET


@dataclass
class BetResult:
    """Single bet result"""
    id: str
    timestamp: datetime
    currency: str
    amount: float
    chance: float
    target: float
    result: float
    profit: float
    is_win: bool
    mode: str  # 'main' or 'faucet'


class AppStore:
    """Central reactive state - single source of truth"""
    
    def __init__(self):
        # Connection state
        self.connected = False
        self.username = ""
        self.api_key = ""
        
        # Balance state
        self.currency = "DOGE"
        self.main_balance = 0.0
        self.faucet_balance = 0.0
        self.available_currencies: List[str] = []
        
        # Betting state
        self.mode = "simulation"  # 'simulation', 'live'
        self.betting_mode = "main"  # 'main', 'faucet'
        self.is_betting = False
        self.current_strategy = None
        
        # Statistics
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
        self.win_rate = 0.0
        self.profit = 0.0
        self.streak = 0  # Positive = wins, negative = losses
        self.max_win_streak = 0
        self.max_loss_streak = 0
        
        # Bet history
        self.bet_history: List[BetResult] = []
        self.max_history = MAX_BET_HISTORY
        
        # Faucet state
        self.faucet_auto_claim = False
        self.faucet_cookie = ""
        self.faucet_last_claim = None
        self.faucet_next_claim = None
        
        # UI state
        self.loading = False
        self.error_message = ""
        self.success_message = ""
        
        # Auto-bet state
        self.auto_bet_running = False
        self.auto_bet_count = 0
        self.auto_bet_stop_loss = 0.0
        self.auto_bet_take_profit = 0.0
        
    def update_connection(self, connected: bool, username: str = ""):
        """Update connection status"""
        self.connected = connected
        self.username = username
        
    def update_balances(self, main: float, faucet: float):
        """Update balance values"""
        self.main_balance = main
        self.faucet_balance = faucet
        
    def get_current_balance(self) -> float:
        """Get balance for current betting mode"""
        return self.main_balance if self.betting_mode == "main" else self.faucet_balance
    
    def add_bet_result(self, result: BetResult):
        """Add bet result and update statistics"""
        self.bet_history.insert(0, result)
        if len(self.bet_history) > self.max_history:
            self.bet_history.pop()
        
        # Update stats
        self.total_bets += 1
        if result.is_win:
            self.total_wins += 1
            self.streak = max(1, self.streak + 1)
            self.max_win_streak = max(self.max_win_streak, self.streak)
        else:
            self.total_losses += 1
            self.streak = min(-1, self.streak - 1)
            self.max_loss_streak = max(self.max_loss_streak, abs(self.streak))
        
        self.win_rate = (self.total_wins / self.total_bets * 100) if self.total_bets > 0 else 0.0
        self.profit += result.profit
        
    def reset_statistics(self):
        """Reset all statistics"""
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
        self.win_rate = 0.0
        self.profit = 0.0
        self.streak = 0
        self.max_win_streak = 0
        self.max_loss_streak = 0
        self.bet_history.clear()
        
    def get_house_edge(self) -> float:
        """Get house edge for current betting mode"""
        return HOUSE_EDGE_MAIN if self.betting_mode == "main" else HOUSE_EDGE_FAUCET
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for storage"""
        return {
            'currency': self.currency,
            'mode': self.mode,
            'betting_mode': self.betting_mode,
            'total_bets': self.total_bets,
            'total_wins': self.total_wins,
            'total_losses': self.total_losses,
            'profit': self.profit,
            'max_win_streak': self.max_win_streak,
            'max_loss_streak': self.max_loss_streak,
        }


# Global store instance - imported by all UI components
store = AppStore()
