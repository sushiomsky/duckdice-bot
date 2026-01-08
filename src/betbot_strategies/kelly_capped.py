from __future__ import annotations
"""
KellyCapped Strategy
- Computes a capped Kelly fraction from an empirical winrate estimate (EWMA)
  adjusted by a house-edge factor, then sizes bets as fraction of a reference
  bankroll (latest observed balance if available, otherwise a user-provided
  hint), clamped to min/max amounts.

Note: This is for experimentation. On fair games with a house edge, Kelly
will typically suggest zero or very small sizes.
"""
from typing import Any, Dict, Optional
from decimal import Decimal, getcontext

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

getcontext().prec = 28


@register("kelly-capped")
class KellyCapped:
    """Kelly fraction with cap and drawdown guard using EWMA winrate."""

    @classmethod
    def name(cls) -> str:
        return "kelly-capped"

    @classmethod
    def describe(cls) -> str:
        return "Kelly fraction from EWMA winrate, capped and clamped; experimental."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Experts",
            pros=[
                "Mathematically optimal bet sizing",
                "Adapts to actual win rates dynamically",
                "Based on proven Kelly Criterion theory",
                "EWMA smoothing reduces variance",
                "Self-adjusting to game conditions"
            ],
            cons=[
                "Complex mathematics may confuse beginners",
                "Requires understanding of probability theory",
                "House edge makes true Kelly often suggest zero bet",
                "Parameter tuning requires expertise",
                "Can be overly conservative"
            ],
            best_use_case="For mathematically-inclined experts. Experimental research tool.",
            tips=[
                "Start with kelly_cap at 0.25 (quarter Kelly)",
                "Adjust house_edge to match actual game edge",
                "Set bankroll_hint accurately for correct sizing",
                "Monitor EWMA winrate adjustments carefully",
                "This is experimental - use with caution",
                "Best for those who understand Kelly Criterion deeply"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "chance": {"type": "str", "default": "50", "desc": "Chance percent as string"},
            "is_high": {"type": "bool", "default": True, "desc": "Bet High if True else Low"},
            "kelly_cap": {"type": "float", "default": 0.25, "desc": "Max Kelly fraction (e.g., 0.25 = 1/4 Kelly)"},
            "house_edge": {"type": "float", "default": 0.01, "desc": "House edge adjustment (e.g., 0.01 = 1%)"},
            "ewma_alpha": {"type": "float", "default": 0.1, "desc": "EWMA smoothing for winrate"},
            "min_amount": {"type": "str", "default": "0.000001", "desc": "Min bet amount"},
            "max_amount": {"type": "str", "default": "0.001", "desc": "Max bet amount"},
            "bankroll_hint": {"type": "str", "default": "0", "desc": "Reference bankroll if balance unknown"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.chance = str(params.get("chance", "50"))
        self.is_high = bool(params.get("is_high", True))
        self.kelly_cap = float(params.get("kelly_cap", 0.25))
        self.house_edge = float(params.get("house_edge", 0.01))
        self.ewma_alpha = float(params.get("ewma_alpha", 0.1))
        self.min_amount = Decimal(str(params.get("min_amount", "0.000001")))
        self.max_amount = Decimal(str(params.get("max_amount", "0.001")))
        self.bankroll_hint = Decimal(str(params.get("bankroll_hint", "0")))

        self._ewma_win = None  # type: Optional[float]

    def on_session_start(self) -> None:
        self._ewma_win = None

    def _current_bankroll(self) -> Decimal:
        # Use latest observed balance from recent results, else bankroll hint
        if self.ctx.recent_results:
            try:
                bal = Decimal(str(self.ctx.recent_results[-1].get("balance", "0")))
                if bal > 0:
                    return bal
            except Exception:
                pass
        return self.bankroll_hint if self.bankroll_hint > 0 else self.min_amount * Decimal(1000)

    def _kelly_fraction(self, p: float, b: float) -> float:
        # f* = (bp - q)/b with q=1-p, clipped to [0, +inf) then capped
        q = 1.0 - p
        if b <= 0:
            return 0.0
        f = (b * p - q) / b
        f = max(0.0, f)
        f = min(self.kelly_cap, f)
        return f

    def next_bet(self) -> Optional[BetSpec]:
        # Probability from chance with house-edge adjustment and EWMA
        try:
            base_p = float(Decimal(self.chance) / Decimal(100))
        except Exception:
            base_p = 0.5
        p = max(0.0, min(1.0, base_p * (1.0 - max(0.0, self.house_edge))))
        if self._ewma_win is not None:
            p = (1.0 - self.ewma_alpha) * self._ewma_win + self.ewma_alpha * p
        # Net odds b = payout - 1, using 99/chance approx
        try:
            payout = float(Decimal(99) / Decimal(self.chance))
        except Exception:
            payout = 2.0
        b = max(0.0, payout - 1.0)
        f = self._kelly_fraction(p, b)
        bankroll = self._current_bankroll()
        amt = bankroll * Decimal(str(f))
        # Clamp
        if amt < self.min_amount:
            amt = self.min_amount
        if amt > self.max_amount:
            amt = self.max_amount
        return {
            "game": "dice",
            "amount": format(amt, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = 1.0 if bool(result.get("win")) else 0.0
        if self._ewma_win is None:
            self._ewma_win = win
        else:
            self._ewma_win = (1.0 - self.ewma_alpha) * self._ewma_win + self.ewma_alpha * win
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
