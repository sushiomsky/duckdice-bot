from __future__ import annotations
"""
FibLossCluster Strategy
- Uses Fibonacci bet progression only when current loss streak >= threshold.
- Otherwise reverts to base amount.
"""
from typing import Any, Dict, Optional
from decimal import Decimal

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("fib-loss-cluster")
class FibLossCluster:
    """Fibonacci progression activated during loss clusters; resets on win."""

    @classmethod
    def name(cls) -> str:
        return "fib-loss-cluster"

    @classmethod
    def describe(cls) -> str:
        return "Fibonacci progression when loss streak exceeds threshold; flat otherwise."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Moderate",
            recommended_for="Advanced",
            pros=[
                "Fibonacci with cluster detection",
                "Adapts to losing patterns",
                "More sophisticated than basic Fibonacci",
                "Can reduce damage from bad variance",
                "Good for pattern-aware betting"
            ],
            cons=[
                "Complex logic harder to understand",
                "Cluster detection adds overhead",
                "Still vulnerable to sustained bad luck",
                "Requires parameter tuning",
                "Not proven more effective than basic Fib"
            ],
            best_use_case="For advanced players who believe in pattern detection. Experimental.",
            tips=[
                "Tune cluster_size to game characteristics",
                "Monitor cluster detection effectiveness",
                "Combine with strict stop-loss",
                "Test in simulation mode first",
                "May not outperform basic Fibonacci",
                "For players who enjoy complexity"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {"type": "str", "default": "0.000001", "desc": "Base bet amount (decimal string)"},
            "chance": {"type": "str", "default": "50", "desc": "Chance percent as string"},
            "is_high": {"type": "bool", "default": False, "desc": "Bet High if True else Low"},
            "loss_threshold": {"type": "int", "default": 3, "desc": "Activate Fibonacci when loss streak >= threshold"},
            "fib_max_index": {"type": "int", "default": 10, "desc": "Cap Fibonacci index to avoid explosion"},
            "scale": {"type": "float", "default": 1.0, "desc": "Scale factor applied to Fibonacci number"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "50"))
        self.is_high = bool(params.get("is_high", False))
        self.loss_threshold = int(params.get("loss_threshold", 3))
        self.fib_max_index = int(params.get("fib_max_index", 10))
        self.scale = float(params.get("scale", 1.0))

        self._loss_streak = 0
        self._fib_a = 1
        self._fib_b = 1
        self._fib_index = 1

    def on_session_start(self) -> None:
        self._reset_fib()
        self._loss_streak = 0

    def _reset_fib(self) -> None:
        self._fib_a, self._fib_b, self._fib_index = 1, 1, 1

    def _advance_fib(self) -> int:
        if self._fib_index <= 2:
            self._fib_index += 1
            return 1
        if self._fib_index >= self.fib_max_index:
            return self._fib_b
        self._fib_a, self._fib_b = self._fib_b, self._fib_a + self._fib_b
        self._fib_index += 1
        return self._fib_b

    def next_bet(self) -> Optional[BetSpec]:
        if self._loss_streak >= self.loss_threshold:
            # Use Fibonacci multiple
            mult = self._advance_fib() * max(0.0, self.scale)
            amt = self.base_amount * Decimal(str(mult))
        else:
            amt = self.base_amount
        return {
            "game": "dice",
            "amount": format(amt, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        if result.get("win"):
            self._loss_streak = 0
            self._reset_fib()
        else:
            self._loss_streak += 1
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
