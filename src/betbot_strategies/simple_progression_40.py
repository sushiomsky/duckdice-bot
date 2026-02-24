from __future__ import annotations
"""
Simple Progression Strategy - 40% Chance with Decreasing Win Progression

A reverse martingale strategy: bet increases on each consecutive win using
a smooth sliding scale that steps down by win_increase_step per win, from
win_increase_start down to win_increase_floor, then holds steady.

- Base bet: always recalculated as % of current balance
- On win#1: +45%  win#2: +44%  win#3: +43% ... floor at +35%, stays there
- On loss: reset progression, restart from +45% on next win
- Loss streak protection: after N losses in a row, drop to 25% of base bet
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
                "default": 0.005,
                "desc": "Base bet as fraction of current balance (0.5% = 0.005). Recalculated every reset.",
            },
            "win_chance": {
                "type": "str",
                "default": "40",
                "desc": "Win chance percentage (40%)",
            },
            "win_increase_start": {
                "type": "float",
                "default": 0.60,
                "desc": "Bet increase on 1st win (0.60 = +60%). Steps down by win_increase_step each consecutive win.",
            },
            "win_increase_floor": {
                "type": "float",
                "default": 0.35,
                "desc": "Minimum increase per win (floor). Stays here once reached — never goes lower.",
            },
            "win_increase_step": {
                "type": "float",
                "default": 0.01,
                "desc": "How much the increase shrinks per consecutive win (0.01 = 1% per win).",
            },
            "max_bet_multiplier": {
                "type": "float",
                "default": 20.0,
                "desc": "Hard cap on progression multiplier (20x base ≈ 10% of balance).",
            },
            "loss_streak_protection": {
                "type": "int",
                "default": 6,
                "desc": "After this many consecutive losses, drop to 25% of base bet until next win. 0 = disabled.",
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
        
        self.base_bet_pct          = Decimal(str(params.get('base_bet_pct', 0.005)))
        self.win_chance            = Decimal(str(params.get('win_chance', '40')))
        self.win_increase_start    = float(params.get('win_increase_start', 0.60))
        self.win_increase_floor    = float(params.get('win_increase_floor', 0.35))
        self.win_increase_step     = float(params.get('win_increase_step', 0.01))
        self.max_bet_multiplier    = Decimal(str(params.get('max_bet_multiplier', 20.0)))
        self.loss_streak_protection = int(params.get('loss_streak_protection', 6))
        self.bet_high              = params.get('bet_high', True)
        
        self.current_bet_multiplier = Decimal(1)
        self.current_balance        = Decimal(str(ctx.starting_balance))
        self.win_streak             = 0
        self.loss_streak            = 0
        self.total_wins             = 0
        self.total_losses           = 0
        self.last_bet_amount        = Decimal(0)
    
    def _win_increase(self) -> Decimal:
        """Increase factor for the current win position: start → floor, 1% step."""
        inc = max(self.win_increase_floor, self.win_increase_start - self.win_streak * self.win_increase_step)
        return Decimal(str(round(inc, 4)))
    
    def on_session_start(self):
        """Called when session starts."""
        prot = f"after {self.loss_streak_protection} losses → 25% base" if self.loss_streak_protection > 0 else "disabled"
        print(f"\n📈  Simple Progression 40 started")
        print(f"    Base bet      : {float(self.base_bet_pct)*100:.2f}% of balance")
        print(f"    Progression   : +{self.win_increase_start*100:.0f}% → +{self.win_increase_floor*100:.0f}% (−{self.win_increase_step*100:.0f}%/win, holds at floor)")
        print(f"    Max multiplier: {float(self.max_bet_multiplier):.0f}x base")
        print(f"    Loss protection: {prot}\n")
    
    def on_bet_result(self, result: BetResult):
        """Called after each bet result."""
        self.current_balance = Decimal(str(result.get('balance', '0')))
        
        if result.get('win', False):
            increase = self._win_increase()
            self.current_bet_multiplier *= (Decimal(1) + increase)
            if self.current_bet_multiplier > self.max_bet_multiplier:
                self.current_bet_multiplier = self.max_bet_multiplier
            self.win_streak += 1
            self.loss_streak = 0
            self.total_wins += 1
        else:
            self.win_streak = 0
            self.loss_streak += 1
            self.total_losses += 1
            self.current_bet_multiplier = Decimal(1)
    
    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet."""
        balance = self.current_balance
        if balance < Decimal("0.00000001"):
            return None
        
        # Loss streak protection: drop to 25% of base until next win
        effective_base = self.base_bet_pct
        if self.loss_streak_protection > 0 and self.loss_streak >= self.loss_streak_protection:
            effective_base = self.base_bet_pct * Decimal("0.25")

        base_bet = balance * effective_base
        bet_amount = base_bet * self.current_bet_multiplier
        
        max_bet = balance * Decimal("0.25")  # Never bet more than 25% of balance
        bet_amount = min(bet_amount, max_bet)
        bet_amount = max(bet_amount, Decimal("0.00000001"))
        bet_amount = bet_amount.quantize(Decimal("0.00000001"))
        
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
        next_inc = max(self.win_increase_floor, self.win_increase_start - self.win_streak * self.win_increase_step)
        return {
            "current_multiplier": float(self.current_bet_multiplier),
            "win_streak": self.win_streak,
            "loss_streak": self.loss_streak,
            "next_win_increase": round(next_inc, 4),
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "next_bet_pct": float(self.base_bet_pct * self.current_bet_multiplier * 100),
            "protected": self.loss_streak_protection > 0 and self.loss_streak >= self.loss_streak_protection,
        }
