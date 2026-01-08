from __future__ import annotations
"""
Labouchere (Cancellation) Strategy
- Create a sequence of numbers (e.g., [1,2,3,4])
- Bet sum of first and last numbers
- On win: cancel those numbers
- On loss: add the bet amount to end of sequence
- Popular among professional gamblers
"""
from decimal import Decimal
from typing import Any, Dict, Optional, List

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("labouchere")
class Labouchere:
    """Labouchere cancellation system with sequence management."""

    @classmethod
    def name(cls) -> str:
        return "labouchere"

    @classmethod
    def describe(cls) -> str:
        return "Cancellation system: bet sum of sequence ends, cancel on win, append on loss."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Moderate",
            recommended_for="Advanced",
            pros=[
                "Flexible sequence allows customization",
                "Can end profitably even with more losses than wins",
                "Mathematical elegance for strategic minds",
                "Completing sequence guarantees profit",
                "Good control over bet sizing"
            ],
            cons=[
                "Sequence can grow long during losing streaks",
                "Complex to track and manage mentally",
                "Not intuitive for beginners",
                "Can lead to large bets if unlucky"
            ],
            best_use_case="For experienced players who enjoy strategic depth. Works well for patient grinders.",
            tips=[
                "Start with short sequences [1,2,3] or [1,2,2,1]",
                "Longer sequences = more risk but slower growth",
                "Track your sequence carefully during play",
                "Consider max sequence length limit (e.g., 10 numbers)",
                "Works best with 48-50% win rate",
                "Take breaks when sequence gets long (5+ numbers)"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_unit": {"type": "str", "default": "0.000001", "desc": "Base unit for sequence"},
            "sequence": {"type": "str", "default": "1,2,3,4", "desc": "Initial sequence (comma-separated)"},
            "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High or Low"},
            "reset_on_complete": {"type": "bool", "default": True, "desc": "Reset to initial sequence when complete"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_unit = Decimal(str(params.get("base_unit", "0.000001")))
        seq_str = str(params.get("sequence", "1,2,3,4"))
        self.initial_sequence = [int(x.strip()) for x in seq_str.split(",") if x.strip()]
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.reset_on_complete = bool(params.get("reset_on_complete", True))

        self._sequence: List[int] = []

    def on_session_start(self) -> None:
        self._sequence = self.initial_sequence.copy()

    def next_bet(self) -> Optional[BetSpec]:
        if not self._sequence:
            if self.reset_on_complete:
                self._sequence = self.initial_sequence.copy()
            else:
                # Sequence complete, use base unit
                return {
                    "game": "dice",
                    "amount": format(self.base_unit, 'f'),
                    "chance": self.chance,
                    "is_high": self.is_high,
                    "faucet": self.ctx.faucet,
                }

        if len(self._sequence) == 1:
            bet_units = self._sequence[0]
        else:
            bet_units = self._sequence[0] + self._sequence[-1]

        amount = self.base_unit * Decimal(str(bet_units))
        return {
            "game": "dice",
            "amount": format(amount, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = bool(result.get("win"))
        
        if not self._sequence:
            self.ctx.recent_results.append(result)
            return

        if win:
            # Cancel first and last
            if len(self._sequence) == 1:
                self._sequence = []
            elif len(self._sequence) == 2:
                self._sequence = []
            else:
                self._sequence = self._sequence[1:-1]
        else:
            # Append the bet units
            if len(self._sequence) == 1:
                bet_units = self._sequence[0]
            else:
                bet_units = self._sequence[0] + self._sequence[-1]
            self._sequence.append(bet_units)

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
