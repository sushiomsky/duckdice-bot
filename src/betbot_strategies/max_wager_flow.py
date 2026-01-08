from __future__ import annotations
"""
MaxWagerFlow Strategy
- Objective: maximize total wagered amount per unit time within safety limits
- Defaults to Original Dice at 50% chance; random High/Low each bet
- Stake is a fixed fraction of current balance with absolute caps
- Honors engine delay/jitter by default (burst mode is a later enhancement)
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("max-wager-flow")
class MaxWagerFlow:
    """High-throughput wagering at ~50% odds with balance-based sizing."""

    @classmethod
    def name(cls) -> str:
        return "max-wager-flow"

    @classmethod
    def describe(cls) -> str:
        return "Maximize wagering throughput using ~50% odds and fraction-of-balance sizing."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Large",
            volatility="Very High",
            time_to_profit="Quick",
            recommended_for="Experts",
            pros=[
                "Aggressive profit targeting",
                "Can generate quick wins",
                "Maximum utilization of bankroll",
                "Exciting high-action play",
                "Good for bonus clearing"
            ],
            cons=[
                "Very high risk of ruin",
                "Not for risk-averse players",
                "Can lose bankroll quickly",
                "Requires nerves of steel",
                "House edge amplified by bet size"
            ],
            best_use_case="High-risk/high-reward play. Only for experienced players with large bankrolls.",
            tips=[
                "Set very strict stop-loss (10-20% max)",
                "Use only with money you can afford to lose",
                "Exit immediately on profit target",
                "Not recommended for beginners",
                "Consider as entertainment expense",
                "Know when to walk away"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "fraction": {"type": "float", "default": 0.15, "desc": "Stake as fraction of balance (e.g., 0.15)"},
            "min_amount": {"type": "str", "default": "", "desc": "Absolute minimum bet amount (decimal string)"},
            "max_amount": {"type": "str", "default": "", "desc": "Absolute maximum bet amount (decimal string)"},
            "prefer_game": {"type": "str", "default": "dice", "desc": "dice|range-dice|auto"},
            "chance": {"type": "float", "default": 50.0, "desc": "Chance percent for dice"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.fraction = max(0.0, float(params.get("fraction", 0.15)))
        self.min_amount = str(params.get("min_amount", "") or "") or None
        self.max_amount = str(params.get("max_amount", "") or "") or None
        self.prefer_game = str(params.get("prefer_game", "dice") or "dice").lower()
        self.chance = float(params.get("chance", 50.0))

    def on_session_start(self) -> None:
        pass

    def _current_balance_dec(self) -> Decimal:
        bal_s = self.ctx.current_balance_str() or self.ctx.starting_balance or "0"
        try:
            return Decimal(str(bal_s))
        except Exception:
            return Decimal(0)

    def _clamp_amount(self, amt: Decimal) -> Decimal:
        a = amt
        if self.min_amount:
            try:
                a = max(a, Decimal(str(self.min_amount)))
            except Exception:
                pass
        if self.max_amount:
            try:
                a = min(a, Decimal(str(self.max_amount)))
            except Exception:
                pass
        return a

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._current_balance_dec()
        if bal <= 0 or self.fraction <= 0:
            return None
        amt = self._clamp_amount(bal * Decimal(str(self.fraction)))
        if amt <= 0:
            return None

        # Choose game
        game = self.prefer_game
        if game not in ("dice", "range-dice", "auto"):
            game = "dice"
        if game == "auto":
            # keep it simple: use dice by default
            game = "dice"

        if game == "dice":
            is_high = bool(self.ctx.rng.random() < 0.5)
            bet: BetSpec = {
                "game": "dice",
                "amount": format(amt, 'f'),
                "chance": str(self.chance),
                "is_high": is_high,
                "faucet": self.ctx.faucet,
            }
            return bet
        else:
            # range-dice at ~50%: use window width 5000; random start
            start_max = 9999 - 5000 + 1
            start = int(self.ctx.rng.randrange(start_max))
            r = (start, start + 5000 - 1)
            bet = {
                "game": "range-dice",
                "amount": format(amt, 'f'),
                "range": (int(r[0]), int(r[1])),
                "is_in": True,
                "faucet": self.ctx.faucet,
            }
            return bet

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
