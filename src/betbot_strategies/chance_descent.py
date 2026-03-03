from __future__ import annotations
"""
Chance Descent — Win-Driven Chance Compression

Starts at a configurable chance (default 1%). Every win lowers the chance by a
multiplicative factor, compounding the edge toward rarer, higher-payout hits.
On any loss the chance resets to the starting value.

Loss recovery: optional martingale multiplier on consecutive losses (default 1×,
i.e. flat bet). Set ``loss_mult > 1`` to recover losses before the next win cycle.

Example at default settings (start_chance=1%, chance_mult=0.90, flat bet):
  Win  → chance: 1.00% → 0.90% → 0.81% → 0.73% → ...
  Loss → chance resets to 1.00%, bet resets to base
"""
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_QUANT = Decimal("0.00000001")


@register("chance-descent")
class ChanceDescent:
    """Start at 1%, lower chance on every win; reset on loss."""

    @classmethod
    def name(cls) -> str:
        return "chance-descent"

    @classmethod
    def describe(cls) -> str:
        return (
            "Starts at a base chance (default 1%). Every win multiplies chance "
            "by chance_mult (<1) to hunt progressively rarer payouts. "
            "Any loss resets chance to start_chance."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            display_name="Chance Descent",
            description=cls.describe(),
            tags=["dice", "low-chance", "win-streak"],
            risk_level="medium",
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "start_chance": {
                "type": "float",
                "default": 1.0,
                "min": 0.01,
                "max": 98.0,
                "description": "Starting win chance % (default 1%)",
            },
            "min_chance": {
                "type": "float",
                "default": 0.01,
                "min": 0.01,
                "max": 98.0,
                "description": "Minimum chance floor in % (default 0.01%)",
            },
            "chance_mult": {
                "type": "float",
                "default": 0.90,
                "min": 0.01,
                "max": 0.9999,
                "description": "Multiply chance by this factor on each win (default 0.90 = −10%)",
            },
            "base_bet": {
                "type": "float",
                "default": 0.0001,
                "min": 0.0,
                "description": "Fixed base bet amount. 0 = use base_bet_pct instead",
            },
            "base_bet_pct": {
                "type": "float",
                "default": 0.01,
                "min": 0.0001,
                "max": 100.0,
                "description": "Bet as % of balance when base_bet=0 (default 0.01%)",
            },
            "loss_mult": {
                "type": "float",
                "default": 1.0,
                "min": 1.0,
                "max": 10.0,
                "description": "Multiply bet by this on each consecutive loss for recovery (default 1 = flat)",
            },
        }

    # ------------------------------------------------------------------

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self._ctx = ctx
        self._start_chance = float(params.get("start_chance", 1.0))
        self._min_chance = float(params.get("min_chance", 0.01))
        self._chance_mult = float(params.get("chance_mult", 0.90))
        self._base_bet = Decimal(str(params.get("base_bet", 0.0001)))
        self._base_bet_pct = float(params.get("base_bet_pct", 0.01))
        self._loss_mult = float(params.get("loss_mult", 1.0))

        self._chance: float = self._start_chance
        self._current_bet: Decimal = self._base_bet
        self._consec_losses: int = 0

    def on_session_start(self) -> None:
        self._chance = self._start_chance
        self._current_bet = self._resolve_base_bet()
        self._consec_losses = 0

    def _resolve_base_bet(self) -> Decimal:
        if self._base_bet > 0:
            return self._base_bet
        balance = Decimal(self._ctx.current_balance_str())
        return (balance * Decimal(str(self._base_bet_pct)) / 100).quantize(
            _QUANT, rounding=ROUND_DOWN
        )

    def next_bet(self) -> BetSpec:
        return {
            "game": "dice",
            "amount": str(self._current_bet.quantize(_QUANT, rounding=ROUND_DOWN)),
            "chance": f"{self._chance:.4f}",
            "is_high": False,
            "faucet": False,
        }

    def on_bet_result(self, result: BetResult) -> None:
        if result["win"]:
            # Lower chance — compound into rarer territory
            self._chance = max(self._chance * self._chance_mult, self._min_chance)
            # Reset bet to base on win
            self._current_bet = self._resolve_base_bet()
            self._consec_losses = 0
        else:
            # Reset chance back to start
            self._chance = self._start_chance
            self._consec_losses += 1
            if self._loss_mult > 1.0:
                self._current_bet = (
                    self._resolve_base_bet()
                    * Decimal(str(self._loss_mult ** self._consec_losses))
                ).quantize(_QUANT, rounding=ROUND_DOWN)
            else:
                self._current_bet = self._resolve_base_bet()

    def on_session_end(self, reason: str) -> None:
        pass
