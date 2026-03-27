from __future__ import annotations
"""
Oscar's Grind Strategy
- Increase bet by 1 unit after win, keep same after loss
- Reset to base when profit target reached
- Conservative, grinds out small consistent profits
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("oscars-grind")
class OscarsGrind:
    """Oscar's Grind: conservative progression aiming for 1-unit profit per cycle."""

    @classmethod
    def name(cls) -> str:
        return "oscars-grind"

    @classmethod
    def describe(cls) -> str:
        return "Conservative system: increase bet after wins, target small consistent profits."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Low",
            time_to_profit="Slow",
            recommended_for="Beginners",
            pros=[
                "Extremely conservative approach",
                "Named after legendary gambler Oscar",
                "Only increases bet after wins",
                "Small consistent profits per cycle",
                "Very low risk of ruin"
            ],
            cons=[
                "Painfully slow profit accumulation",
                "Requires extreme patience",
                "Multiple sessions needed for meaningful profit",
                "Can be frustrating during losing streaks"
            ],
            best_use_case="Perfect for ultra-conservative players. Great for learning betting systems.",
            tips=[
                "Set profit_target at 1-2x base_amount for quick cycles",
                "Extremely safe for bankroll preservation",
                "Combine with 48-50% win probability",
                "Great for building confidence with new strategies",
                "Max bet should be 10-20x base amount",
                "Perfect for multi-session long-term play"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet (1 unit)"},
            "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High or Low"},
            "profit_target": {"type": "str", "default": "0.000001", "desc": "Profit target per cycle"},
            "max_bet": {"type": "str", "default": "0.0001", "desc": "Maximum bet cap"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.profit_target = Decimal(str(params.get("profit_target", "0.000001")))
        self.max_bet = Decimal(str(params.get("max_bet", "0.0001")))

        self._current_amount = self.base_amount
        self._cycle_profit = Decimal("0")
        self._cycle_start_balance = Decimal("0")

    def on_session_start(self) -> None:
        self._current_amount = self.base_amount
        self._cycle_profit = Decimal("0")
        # Get starting balance
        balance_str = self.ctx.starting_balance or "0"
        self._cycle_start_balance = Decimal(balance_str)

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
        profit = Decimal(str(result.get("profit", "0")))
        
        self._cycle_profit += profit

        if self._cycle_profit >= self.profit_target:
            # Target reached, reset cycle
            balance_str = result.get("balance", "0")
            self._cycle_start_balance = Decimal(str(balance_str))
            self._cycle_profit = Decimal("0")
            self._current_amount = self.base_amount
        elif win:
            # Increase bet by 1 unit
            self._current_amount = min(self.max_bet, self._current_amount + self.base_amount)
        # On loss, keep the same bet

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
