from __future__ import annotations
"""
Fibonacci Strategy
- Follow Fibonacci sequence on losses: 1,1,2,3,5,8,13,21...
- Move forward two steps on loss, back two steps on win
- Gentler than martingale, popular for risk management
"""
from decimal import Decimal
from typing import Any, Dict, Optional, List

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("fibonacci")
class Fibonacci:
    """Fibonacci progression betting system."""

    @classmethod
    def name(cls) -> str:
        return "fibonacci"

    @classmethod
    def describe(cls) -> str:
        return "Follow Fibonacci sequence: advance on loss, retreat on win. Moderate risk."

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Slower bet progression than Martingale",
                "Better bankroll preservation",
                "Mathematical elegance appeals to analytical minds",
                "Natural sequence provides predictable bet sizing",
                "Win after losses still recovers some profit"
            ],
            cons=[
                "Can still lead to large bets after extended losses",
                "Requires more wins to recover from losing streaks",
                "Complexity in tracking position in sequence",
                "House edge still affects long-term outcomes"
            ],
            best_use_case="Medium-term sessions with moderate bankroll. Good balance of aggression and safety.",
            tips=[
                "Keep max_level at 12-15 to prevent exponential growth",
                "Works best with 48-50% win probability",
                "Consider resetting after 2-3 consecutive wins",
                "Track your Fibonacci level - reset if too high",
                "Combine with stop-loss at 25% bankroll",
                "Best for players who understand mathematical patterns"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet amount (1 unit)"},
            "chance": {"type": "str", "default": "49.5", "desc": "Win chance percent"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet on High or Low"},
            "max_level": {"type": "int", "default": 15, "desc": "Maximum Fibonacci level"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.max_level = int(params.get("max_level", 15))

        # Generate Fibonacci sequence
        self._fib_sequence = self._generate_fibonacci(self.max_level)
        self._current_level = 0

    def _generate_fibonacci(self, n: int) -> List[int]:
        """Generate first n Fibonacci numbers."""
        if n <= 0:
            return [1]
        elif n == 1:
            return [1]
        
        fib = [1, 1]
        for i in range(2, n):
            fib.append(fib[i-1] + fib[i-2])
        return fib

    def on_session_start(self) -> None:
        self._current_level = 0

    def next_bet(self) -> Optional[BetSpec]:
        multiplier = self._fib_sequence[min(self._current_level, len(self._fib_sequence) - 1)]
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
            # Move back 2 steps (or to 0)
            self._current_level = max(0, self._current_level - 2)
        else:
            # Move forward 1 step
            self._current_level = min(len(self._fib_sequence) - 1, self._current_level + 1)

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
