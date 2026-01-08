from __future__ import annotations
"""
AntiMartingaleStreak Strategy
- Reverse martingale: increase stake on wins by a multiplier up to a cap
- Reset on loss
- Constant chance and side (High/Low) for Original Dice
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("anti-martingale-streak")
class AntiMartingaleStreak:
    """Reverse martingale that scales on win streaks and resets on losses."""

    @classmethod
    def name(cls) -> str:
        return "anti-martingale-streak"

    @classmethod
    def describe(cls) -> str:
        return "Reverse martingale: multiply stake on each win up to a cap; reset on loss."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Quick",
            recommended_for="Intermediate",
            pros=[
                "Capitalizes on winning streaks",
                "Limited downside on losses",
                "Exciting during hot streaks",
                "Base bet stays constant on losses",
                "Better risk profile than Martingale"
            ],
            cons=[
                "Requires winning streaks to profit",
                "Loses all streak progress on single loss",
                "Highly dependent on luck/variance",
                "Frustrating when streaks break early"
            ],
            best_use_case="For players who want to ride winning streaks. Good for short burst sessions.",
            tips=[
                "Set realistic streak_target (3-5 is optimal)",
                "Exit after hitting 1-2 max streaks",
                "Works best with 45-50% win probability",
                "Consider 'partial reset' after breaking streak",
                "Great for bonus hunting strategies",
                "Use strict session time limits"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet amount (decimal string)"},
            "chance": {"type": "str", "default": "50", "desc": "Chance percent as string (e.g., '50')"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High (True) or Low (False)"},
            "win_mult": {"type": "float", "default": 2.0, "desc": "Multiplier applied after each win"},
            "max_mult": {"type": "float", "default": 8.0, "desc": "Maximum multiplier cap"},
            "cooldown_after_loss": {"type": "int", "default": 0, "desc": "Bets to skip after a loss (cooldown)"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "50"))
        self.is_high = bool(params.get("is_high", True))
        self.win_mult = float(params.get("win_mult", 2.0))
        self.max_mult = float(params.get("max_mult", 8.0))
        self.cooldown_after_loss = int(params.get("cooldown_after_loss", 0))

        self._mult = 1.0
        self._cooldown = 0

    def on_session_start(self) -> None:
        self._mult = 1.0
        self._cooldown = 0

    def next_bet(self) -> Optional[BetSpec]:
        if self._cooldown > 0:
            self._cooldown -= 1
            return {
                "game": "dice",
                "amount": str(self.base_amount),
                "chance": self.chance,
                "is_high": self.is_high,
                "faucet": self.ctx.faucet,
            }
        amt = self.base_amount * Decimal(str(self._mult))
        return {
            "game": "dice",
            "amount": format(amt, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = bool(result.get("win"))
        if win:
            self._mult = min(self.max_mult, self._mult * max(1.0, float(self.win_mult)))
        else:
            self._mult = 1.0
            self._cooldown = max(self._cooldown, self.cooldown_after_loss)
        # store recent
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
