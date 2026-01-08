from __future__ import annotations
"""
Paroli Strategy (Reverse Martingale)
- Double bet on wins up to a target streak
- Reset to base on loss or after reaching target
- Positive progression system, limits losses
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("paroli")
class Paroli:
    """Paroli system: double on wins up to target, reset on loss."""

    @classmethod
    def name(cls) -> str:
        return "paroli"

    @classmethod
    def describe(cls) -> str:
        return "Double on wins up to target streak, reset on loss. Limits downside risk."

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Medium",
            time_to_profit="Quick",
            recommended_for="Beginners",
            pros=[
                "Losses are always limited to base bet",
                "Winning streaks can generate exponential profit",
                "Easy to understand positive progression",
                "Low risk to bankroll",
                "Great risk/reward ratio"
            ],
            cons=[
                "Needs winning streaks to profit significantly",
                "Most sessions end near breakeven",
                "Frustrating when losing on final target bet",
                "Requires patience for streak opportunities"
            ],
            best_use_case="Excellent for risk-averse players hunting winning streaks. Very beginner-friendly.",
            tips=[
                "Classic target_streak is 3 (recommended)",
                "With 49.5% chance, 3-streak happens ~12.5% of time",
                "Consider lowering to 2-streak for more frequent wins",
                "4+ streaks are rare - not recommended",
                "Perfect for 'hit and run' short sessions",
                "Exit immediately after hitting 2-3 target streaks"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet amount"},
            "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High or Low"},
            "target_streak": {"type": "int", "default": 3, "desc": "Win streak target before reset"},
            "multiplier": {"type": "float", "default": 2.0, "desc": "Multiplier on win"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.target_streak = int(params.get("target_streak", 3))
        self.multiplier = float(params.get("multiplier", 2.0))

        self._current_amount = self.base_amount
        self._win_streak = 0

    def on_session_start(self) -> None:
        self._current_amount = self.base_amount
        self._win_streak = 0

    def next_bet(self) -> Optional[BetSpec]:
        return {
            "game": "dice",
            "amount": format(self._current_amount, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = bool(result.get("win"))
        
        if win:
            self._win_streak += 1
            if self._win_streak >= self.target_streak:
                # Target reached, reset
                self._current_amount = self.base_amount
                self._win_streak = 0
            else:
                # Continue progression
                self._current_amount = self._current_amount * Decimal(str(self.multiplier))
        else:
            # Reset on loss
            self._current_amount = self.base_amount
            self._win_streak = 0

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
