from __future__ import annotations
"""
1-3-2-6 Strategy
- Fixed sequence betting: 1, 3, 2, 6 units
- Advance on wins, reset on loss
- Popular in Baccarat, works for dice
"""
from decimal import Decimal
from typing import Any, Dict, Optional, List

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("one-three-two-six")
class OneThreeTwoSix:
    """1-3-2-6 betting system with fixed sequence."""

    @classmethod
    def name(cls) -> str:
        return "one-three-two-six"

    @classmethod
    def describe(cls) -> str:
        return "Fixed sequence (1,3,2,6): advance on wins, reset on loss. Controlled risk."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Medium",
            time_to_profit="Quick",
            recommended_for="Beginners",
            pros=[
                "Fixed simple sequence: 1-3-2-6 units",
                "Easy to understand and follow",
                "Limited risk with profit lock-in",
                "Completing sequence = 12 units profit",
                "Great for beginners learning progressions"
            ],
            cons=[
                "Requires 4 consecutive wins for full profit",
                "Any loss resets to start",
                "4-win streaks are rare (~6% at 49.5%)",
                "Can be frustrating with bad timing"
            ],
            best_use_case="Perfect introduction to positive progression systems. Beginner-friendly.",
            tips=[
                "Classic sequence is 1-3-2-6 (don't modify)",
                "Lock in profit after completing sequence",
                "With 49.5% chance, expect 1 complete per ~16 attempts",
                "Celebrate full sequence completions!",
                "Consider stopping after 1-2 completions",
                "Great for understanding positive progressions"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet (1 unit)"},
            "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High or Low"},
            "sequence": {"type": "str", "default": "1,3,2,6", "desc": "Betting sequence"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        
        seq_str = str(params.get("sequence", "1,3,2,6"))
        self.sequence = [int(x.strip()) for x in seq_str.split(",") if x.strip()]
        
        self._current_step = 0

    def on_session_start(self) -> None:
        self._current_step = 0

    def next_bet(self) -> Optional[BetSpec]:
        multiplier = self.sequence[self._current_step]
        amount = self.base_amount * Decimal(str(multiplier))
        
        return {
            "game": "dice",
            "amount": format(amount, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = bool(result.get("win"))
        
        if win:
            # Advance to next step
            self._current_step += 1
            if self._current_step >= len(self.sequence):
                # Completed sequence, reset
                self._current_step = 0
        else:
            # Reset on loss
            self._current_step = 0

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
