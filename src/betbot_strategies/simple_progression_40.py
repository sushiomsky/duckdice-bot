from __future__ import annotations
"""
Simple Progression Strategy - 40% Chance with Decreasing Win Progression

A reverse martingale strategy with smart progression that decreases increases
over time to manage risk during long win streaks.

Strategy:
- Fixed 40% win chance
- Base bet: Always recalculated as % of current balance (default 1%)
- On win: Increase bet by decreasing amounts
  * 1st win: +50% (1.50x previous)
  * 2nd win: +40% (1.40x previous)
  * 3rd win: +30% (1.30x previous)
  * 4th+ wins: +20% (1.20x previous)
- On loss: Reset to base bet (recalculated from current balance)
- Bet high (target > 60)

Characteristics:
- Base bet automatically adjusts to balance changes
- Low risk on losses (always reset to small % of current balance)
- Capitalizes on win streaks with managed growth
- Progressive risk reduction on longer streaks
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
            "40% chance with decreasing progression: +50%→+40%→+30%→+20%. "
            "Base bet always 1% of current balance. Smart win streak capitalizer."
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
                "Base bet auto-adjusts to balance changes",
                "Low risk on losses (always reset to 1% of balance)",
                "Decreasing progression reduces long streak risk",
                "Capitalizes on win streaks intelligently",
                "Predictable bet sizing with safety built-in",
                "Good risk/reward balance",
                "Fast profit potential on short streaks"
            ],
            cons=[
                "Single loss erases win streak progress",
                "Requires win streaks for significant profit",
                "40% chance means ~60% loss rate",
                "Can be frustrating with alternating results",
                "Slower growth on long streaks vs fixed increase",
                "Not optimal for long sessions without streaks"
            ],
            best_use_case="Short to medium sessions hoping to catch win streaks. Base bet automatically scales with balance changes.",
            tips=[
                "Set take-profit to lock in win streak gains",
                "Use max-bets limit to prevent overexposure",
                "Best in calm market conditions",
                "Exit after 3+ win streak if target met",
                "Adjust base_bet_pct for risk tolerance (0.5-2%)",
                "Adjust progression rates for different risk profiles",
                "Consider stopping after big loss streak",
                "Decreasing progression protects on 4+ win streaks"
            ]
        )
    
    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_pct": {
                "type": "float",
                "default": 0.01,
                "desc": "Base bet as % of current balance (1% = 0.01, recalculated each bet)",
            },
            "win_chance": {
                "type": "str",
                "default": "40",
                "desc": "Win chance percentage (40%)",
            },
            "first_win_increase": {
                "type": "float",
                "default": 0.50,
                "desc": "1st win increase % (50% = 0.50, makes bet 1.5x)",
            },
            "second_win_increase": {
                "type": "float",
                "default": 0.40,
                "desc": "2nd win increase % (40% = 0.40, makes bet 1.4x)",
            },
            "third_win_increase": {
                "type": "float",
                "default": 0.30,
                "desc": "3rd win increase % (30% = 0.30, makes bet 1.3x)",
            },
            "fourth_plus_win_increase": {
                "type": "float",
                "default": 0.20,
                "desc": "4th+ win increase % (20% = 0.20, makes bet 1.2x)",
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
        self.first_win_increase = Decimal(str(params.get('first_win_increase', 0.50)))
        self.second_win_increase = Decimal(str(params.get('second_win_increase', 0.40)))
        self.third_win_increase = Decimal(str(params.get('third_win_increase', 0.30)))
        self.fourth_plus_win_increase = Decimal(str(params.get('fourth_plus_win_increase', 0.20)))
        self.max_bet_multiplier = Decimal(str(params.get('max_bet_multiplier', 10.0)))
        self.bet_high = params.get('bet_high', True)
        
        # State
        self.current_bet_multiplier = Decimal(1)  # Starts at 1x base
        self.current_balance = Decimal(str(ctx.starting_balance))  # Track balance ourselves
        self.win_streak = 0
        self.total_wins = 0
        self.total_losses = 0
        self.last_bet_amount = Decimal(0)  # Track for progression calculation
    
    def _get_win_increase_for_streak(self) -> Decimal:
        """Get the increase percentage based on current win streak."""
        if self.win_streak == 0:
            return self.first_win_increase
        elif self.win_streak == 1:
            return self.second_win_increase
        elif self.win_streak == 2:
            return self.third_win_increase
        else:  # 3+
            return self.fourth_plus_win_increase
    
    def on_session_start(self):
        """Called when session starts."""
        pass
    
    def on_bet_result(self, result: BetResult):
        """Called after each bet result."""
        # Update balance from result
        self.current_balance = Decimal(str(result.get('balance', '0')))
        
        if result.get('win', False):
            # Win: Increase bet using decreasing progression
            increase_pct = self._get_win_increase_for_streak()
            self.win_streak += 1
            self.total_wins += 1
            self.current_bet_multiplier *= (Decimal(1) + increase_pct)
            
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
        # Use our tracked balance (updated in on_bet_result)
        balance = self.current_balance
        
        # Check minimum balance
        if balance < Decimal("0.00000001"):
            return None
        
        # Calculate bet amount - base bet recalculates from current balance every time
        base_bet = balance * self.base_bet_pct
        bet_amount = base_bet * self.current_bet_multiplier
        
        # Safety caps
        max_bet = balance * Decimal("0.25")  # Never bet more than 25% of balance
        bet_amount = min(bet_amount, max_bet)
        bet_amount = max(bet_amount, Decimal("0.00000001"))  # Minimum
        
        # Quantize to 8 decimal places
        bet_amount = bet_amount.quantize(Decimal("0.00000001"))
        
        # Store for tracking
        self.last_bet_amount = bet_amount
        
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
