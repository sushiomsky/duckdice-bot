from __future__ import annotations
"""
Range50Random Strategy
- Range Dice with exactly 50% chance per bet (range width 5000 over 0..9999)
- Random contiguous range each bet (In-range by default; optional Out)
- Stake sized dynamically as a random fraction of current balance between
  min_frac and max_frac (defaults: 1/20 to 1/5), clamped by optional
  absolute min_amount/max_amount and engine max_bet.
"""
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("range-50-random")
class Range50Random:
    """50/50 Range Dice with random range window and balance-based sizing."""

    @classmethod
    def name(cls) -> str:
        return "range-50-random"

    @classmethod
    def describe(cls) -> str:
        return "Range-dice at 50% chance: pick a random 5000-wide window each bet; stake = U[min_frac,max_frac] of balance."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Small",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Uses Range Dice for 50/50 odds",
                "Randomization adds unpredictability",
                "Different game type provides variety",
                "True 50% probability",
                "Good for breaking patterns"
            ],
            cons=[
                "Randomness doesn't improve odds",
                "Still subject to house edge",
                "No mathematical advantage",
                "Complexity doesn't add value",
                "May confuse bet tracking"
            ],
            best_use_case="For variety and testing Range Dice. No real advantage over standard play.",
            tips=[
                "Understand this is experimental/fun",
                "No proven edge over simple betting",
                "Good for exploring Range Dice",
                "Use conservative bet sizing",
                "Mainly for entertainment/variety",
                "Track results vs simple strategies"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "min_frac": {"type": "float", "default": 0.05, "desc": "Minimum fraction of balance per bet (e.g., 0.05 = 1/20)"},
            "max_frac": {"type": "float", "default": 0.20, "desc": "Maximum fraction of balance per bet (e.g., 0.20 = 1/5)"},
            "min_amount": {"type": "str", "default": "", "desc": "Absolute minimum bet amount (decimal string)"},
            "max_amount": {"type": "str", "default": "", "desc": "Absolute maximum bet amount (decimal string)"},
            "use_out": {"type": "bool", "default": False, "desc": "Bet Out-of-range instead of In"},
            "granularity": {"type": "int", "default": 1, "desc": "Align window start to this step (e.g., 10)"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.min_frac = float(params.get("min_frac", 0.05))
        self.max_frac = float(params.get("max_frac", 0.20))
        if self.max_frac < self.min_frac:
            self.max_frac, self.min_frac = self.min_frac, self.max_frac
        self.min_amount = str(params.get("min_amount", "") or "") or None
        self.max_amount = str(params.get("max_amount", "") or "") or None
        self.use_out = bool(params.get("use_out", False))
        self.granularity = max(1, int(params.get("granularity", 1) or 1))

        # constants
        self.domain_min = 0
        self.domain_max = 9999
        self.width = 5000  # exactly 50%

    def on_session_start(self) -> None:
        pass

    def _current_balance_dec(self) -> Decimal:
        from decimal import Decimal
        bal_s = self.ctx.current_balance_str() or self.ctx.starting_balance or "0"
        try:
            return Decimal(str(bal_s))
        except Exception:
            return Decimal(0)

    def _clamp_amount(self, amt: Decimal) -> Decimal:
        from decimal import Decimal
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
        # Engine max_bet is also enforced upstream; we leave it to engine
        return a

    def _random_window(self) -> Tuple[int, int]:
        start_min = self.domain_min
        start_max = self.domain_max - self.width + 1
        # align to granularity
        step = self.granularity
        choices = ((start_max - start_min) // step) + 1
        k = self.ctx.rng.randrange(choices)
        start = start_min + k * step
        if start > start_max:
            start = start_max
        end = start + self.width - 1
        return (start, end)

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._current_balance_dec()
        if bal <= 0:
            return None
        frac = self.ctx.rng.uniform(self.min_frac, self.max_frac)
        amt = self._clamp_amount(bal * Decimal(str(frac)))
        if amt <= 0:
            return None
        r = self._random_window()
        bet: BetSpec = {
            "game": "range-dice",
            "amount": format(amt, 'f'),
            "range": (int(r[0]), int(r[1])),
            "is_in": (not self.use_out),
            "faucet": self.ctx.faucet,
        }
        # Log a debug record
        self.ctx.logger({
            "event": "strategy_info",
            "strategy": self.name(),
            "note": "range50 params",
            "range": r,
            "fraction": frac,
            "amount": format(amt, 'f'),
        })
        return bet

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
