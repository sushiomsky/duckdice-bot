from __future__ import annotations
"""
D'Alembert Strategy
- Increase bet by fixed amount on loss
- Decrease bet by fixed amount on win
- Less aggressive than martingale, more balanced
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("dalembert")
class DAlembert:
    """D'Alembert betting system: linear progression on losses."""

    @classmethod
    def name(cls) -> str:
        return "dalembert"

    @classmethod
    def describe(cls) -> str:
        return "Increase bet by fixed amount on loss, decrease on win. Balanced approach."

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Low",
            time_to_profit="Moderate",
            recommended_for="Beginners",
            pros=[
                "Linear progression is gentle on bankroll",
                "Simple to understand for beginners",
                "Lower variance than Martingale/Fibonacci",
                "Bets stay manageable even during losing streaks",
                "Good for conservative players"
            ],
            cons=[
                "Slower profit accumulation",
                "Still vulnerable to extended losing streaks",
                "Requires multiple wins to recover losses",
                "Can be boring for action-seekers"
            ],
            best_use_case="Perfect for beginners and conservative players. Long-term grinding strategy.",
            tips=[
                "Set increment to 2-5% of base_amount",
                "Keep max_bet at 10-20x base_amount",
                "Works well with 45-50% win probability",
                "Be patient - profits come slowly but steadily",
                "Consider stopping after 3-4 consecutive level increases",
                "Great for learning betting psychology"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet amount"},
            "increment": {"type": "str", "default": "0.000001", "desc": "Amount to add/subtract"},
            "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High or Low"},
            "max_bet": {"type": "str", "default": "0.0001", "desc": "Maximum bet cap"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.increment = Decimal(str(params.get("increment", "0.000001")))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.max_bet = Decimal(str(params.get("max_bet", "0.0001")))

        self._current_amount = self.base_amount

    def on_session_start(self) -> None:
        self._current_amount = self.base_amount

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
            # Decrease bet
            self._current_amount = max(self.base_amount, self._current_amount - self.increment)
        else:
            # Increase bet
            self._current_amount = min(self.max_bet, self._current_amount + self.increment)

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
