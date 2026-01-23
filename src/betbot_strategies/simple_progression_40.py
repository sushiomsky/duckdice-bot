from __future__ import annotations
"""
Simple Progression Strategy - 40% Chance with Win Progression

A straightforward reverse martingale strategy that increases bet by 45% on wins
and resets to base bet on losses.

Strategy:
- Fixed 40% win chance
- Base bet: 1/100 of balance (1%)
- On win: Increase bet by 45%
- On loss: Reset to base bet
- Bet high (target > 60)

Characteristics:
- Low risk on losses (always reset to small base)
- Capitalizes on win streaks
- Simple and predictable
- Good risk/reward balance
"""
from typing import Any, Dict, Optional
from decimal import Decimal, getcontext

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

getcontext().prec = 28


@register("simple-progression-40")
class SimpleProgression40Strategy:
    """
    Simple progression strategy with 40% win chance.
    
    Increases bet by 45% on wins, resets to 1% of balance on losses.
    Designed for capitalizing on win streaks while minimizing loss impact.
    """
    
    @classmethod
    def name(cls) -> str:
        return "simple-progression-40"
    
    @classmethod
    def describe(cls) -> str:
        return (
            "40% chance, 45% increase on win, reset on loss. "
            "Base bet 1% of balance. Simple win streak capitalizer."
        )
    
    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="Quick",
            recommended_for="Beginners",
            pros=[
                "Simple and easy to understand",
                "Low risk on losses (always reset to 1%)",
                "Capitalizes on win streaks",
                "Predictable bet sizing",
                "Good risk/reward balance",
                "Fast profit potential on streaks"
            ],
            cons=[
                "Single loss erases win streak progress",
                "Requires win streaks for significant profit",
                "40% chance means ~60% loss rate",
                "Can be frustrating with alternating results",
                "No drawdown protection",
                "Not optimal for long sessions without streaks"
            ],
            best_use_case="Short to medium sessions hoping to catch win streaks. Good for learning progression mechanics.",
            tips=[
                "Set take-profit to lock in win streak gains",
                "Use max-bets limit to prevent overexposure",
                "Best in calm market conditions",
                "Exit after 3+ win streak if target met",
                "Adjust win_increase for risk tolerance",
                "Consider stopping after big loss streak",
                "Works well with small base_bet_pct for safety"
            ]
        )
    
    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_pct": {
                "type": "float",
                "default": 0.01,
                "desc": "Base bet as % of balance (1% = 0.01)",
            },
            "win_chance": {
                "type": "str",
                "default": "40",
                "desc": "Win chance percentage (40%)",
            },
            "win_increase": {
                "type": "float",
                "default": 0.45,
                "desc": "Increase % on win (45% = 0.45)",
            },
            "max_bet_multiplier": {
                "type": "float",
                "default": 10.0,
                "desc": "Max bet as multiplier of base bet (10x)",
            },
            "bet_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet high (True) or low (False)",
            },
        }
    
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext):
        self.params = params
        self.ctx = ctx
        
        # Parse parameters
        self.base_bet_pct = Decimal(str(params.get('base_bet_pct', 0.01)))
        self.win_chance = Decimal(str(params.get('win_chance', '40')))
        self.win_increase = Decimal(str(params.get('win_increase', 0.45)))
        self.max_bet_multiplier = Decimal(str(params.get('max_bet_multiplier', 10.0)))
        self.bet_high = params.get('bet_high', True)
        
        # State
        self.current_bet_multiplier = Decimal(1)  # Starts at 1x base
        self.win_streak = 0
        self.total_wins = 0
        self.total_losses = 0
    
    def on_session_start(self):
        """Called when session starts."""
        pass
    
    def on_bet_result(self, result: BetResult):
        """Called after each bet result."""
        if result.get('win', False):
            # Win: Increase bet
            self.win_streak += 1
            self.total_wins += 1
            self.current_bet_multiplier *= (Decimal(1) + self.win_increase)
            
            # Cap at max multiplier
            if self.current_bet_multiplier > self.max_bet_multiplier:
                self.current_bet_multiplier = self.max_bet_multiplier
        else:
            # Loss: Reset to base
            self.win_streak = 0
            self.total_losses += 1
            self.current_bet_multiplier = Decimal(1)
    
    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet."""
        # Get current balance
        balance = Decimal(str(self.ctx.current_balance_str()))
        
        # Check minimum balance
        if balance < Decimal("0.00000001"):
            return None
        
        # Calculate bet amount
        base_bet = balance * self.base_bet_pct
        bet_amount = base_bet * self.current_bet_multiplier
        
        # Safety caps
        max_bet = balance * Decimal("0.25")  # Never bet more than 25% of balance
        bet_amount = min(bet_amount, max_bet)
        bet_amount = max(bet_amount, Decimal("0.00000001"))  # Minimum
        
        # Quantize to 8 decimal places
        bet_amount = bet_amount.quantize(Decimal("0.00000001"))
        
        return {
            "game": "dice",
            "amount": str(bet_amount),
            "chance": str(self.win_chance),
            "is_high": self.bet_high,
        }
    
    def on_session_end(self, reason: str):
        """Called when session ends."""
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """Get current strategy state for logging/debugging."""
        return {
            "current_multiplier": float(self.current_bet_multiplier),
            "win_streak": self.win_streak,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "next_bet_pct": float(self.base_bet_pct * self.current_bet_multiplier * 100),
        }
