from __future__ import annotations
"""
Classic Martingale Strategy
- Double bet on loss, reset on win
- Most popular (and risky!) betting strategy
- Use with extreme caution and low base amounts
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("classic-martingale")
class ClassicMartingale:
    """Classic martingale: double on loss, reset on win."""

    @classmethod
    def name(cls) -> str:
        return "classic-martingale"

    @classmethod
    def describe(cls) -> str:
        return "Double bet on loss, reset on win. High risk, requires large bankroll."

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Very Large",
            volatility="Very High",
            time_to_profit="Quick",
            recommended_for="Advanced",
            pros=[
                "Theoretically guarantees profit if bankroll unlimited",
                "Simple to understand and implement",
                "Quick recovery from losses with single win",
                "Works well for short sessions"
            ],
            cons=[
                "Exponential bet growth can drain bankroll rapidly",
                "Table limits prevent indefinite doubling",
                "Single long losing streak = catastrophic loss",
                "House edge still applies to every bet",
                "Extremely dangerous without strict loss limits"
            ],
            best_use_case="Short-term sessions with large bankroll and strict max-streak limits. NOT recommended for beginners.",
            tips=[
                "NEVER use without max_streak limit (recommend 6-8)",
                "Start with tiny base_amount (0.1-1% of bankroll)",
                "Set strict stop-loss at 20-30% of bankroll",
                "Best with 49.5% chance or higher",
                "Exit immediately after profit target hit",
                "Consider 'modified martingale' with 1.5x multiplier instead of 2x"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet amount"},
            "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High (True) or Low (False)"},
            "multiplier": {"type": "float", "default": 2.0, "desc": "Multiplier on loss (typically 2.0)"},
            "max_streak": {"type": "int", "default": 10, "desc": "Max loss streak before reset"},
            "reset_on_win": {"type": "bool", "default": True, "desc": "Reset to base on win"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.multiplier = float(params.get("multiplier", 2.0))
        self.max_streak = int(params.get("max_streak", 10))
        self.reset_on_win = bool(params.get("reset_on_win", True))

        self._current_amount = self.base_amount
        self._loss_streak = 0

    def on_session_start(self) -> None:
        self._current_amount = self.base_amount
        self._loss_streak = 0

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
            if self.reset_on_win:
                self._current_amount = self.base_amount
                self._loss_streak = 0
        else:
            self._loss_streak += 1
            if self._loss_streak >= self.max_streak:
                # Reset to avoid catastrophic loss
                self._current_amount = self.base_amount
                self._loss_streak = 0
            else:
                self._current_amount = self._current_amount * Decimal(str(self.multiplier))

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
