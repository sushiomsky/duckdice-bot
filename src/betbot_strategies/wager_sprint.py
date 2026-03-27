from __future__ import annotations
"""
Wager Sprint Strategy

Maximises total wager volume for event rewards and wager races.
Tuned for 3% house edge environments.

Core design:
  - 49.5% chance (lowest house edge per unit wagered)
  - Conservative 3% base bet for survival between streaks
  - Aggressive 4-step Paroli boost (2.5× per step) — a lucky 4-win
    streak wagers ~76% of balance in just 4 bets
  - Proportional survival scaling below drawdown threshold
  - Low bankroll floor (25%) squeezes maximum lifetime from small balances
  - Luck-dependent: average sessions grind ~20×, lucky ones hit 50×+
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_QUANT = Decimal("0.00000001")


@register("wager-sprint")
class WagerSprint:
    """High-throughput wager maximiser with Paroli boost and survival scaling."""

    @classmethod
    def name(cls) -> str:
        return "wager-sprint"

    @classmethod
    def describe(cls) -> str:
        return (
            "Maximises wager volume at 49.5% chance with 8% base bet. "
            "3-step Paroli boost on win streaks inflates wager using house money. "
            "Proportional survival scaling on drawdown."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="N/A (wager-focused)",
            recommended_for="Intermediate",
            pros=[
                "Highest wager throughput per unit time",
                "Aggressive Paroli (4-step, 2.5×) explodes wager on lucky streaks",
                "49.5% chance = minimal house edge per wager unit",
                "Conservative base bet preserves bankroll between streaks",
                "Low starting balance viable — one hot streak changes everything",
            ],
            cons=[
                "3% house edge drains bankroll steadily between streaks",
                "Needs win streaks to outperform flat betting on wager",
                "Paroli resets on every loss",
                "High variance in session wager totals",
            ],
            best_use_case=(
                "Wager races, TLE event milestones, and any scenario where "
                "total volume wagered matters more than profit. Especially "
                "effective with low starting balances where luck can multiply output."
            ),
            tips=[
                "4-step Paroli chain wagers ~76% of balance in 4 bets (vs 12% flat)",
                "A lucky session can wager 50×+ your bankroll; unlucky ones ~15×",
                "Lower bankroll_floor to 0.15 for maximum aggression in short races",
                "Raise paroli_max_steps to 5 for even more luck-dependent output",
                "Combine with session stop-loss as a hard safety net",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "chance": {
                "type": "str", "default": "49.5",
                "desc": "Win chance percent (49.5 = optimal for wager)",
            },
            "base_bet_pct": {
                "type": "str", "default": "3",
                "desc": "Base bet as % of current balance",
            },
            "is_high": {
                "type": "bool", "default": True,
                "desc": "Bet on High or Low",
            },
            "paroli_multiplier": {
                "type": "str", "default": "2.5",
                "desc": "Bet multiplier on each consecutive win",
            },
            "paroli_max_steps": {
                "type": "int", "default": 4,
                "desc": "Max consecutive win-boosts before reset",
            },
            "survival_threshold": {
                "type": "str", "default": "0.50",
                "desc": "Below this ratio of starting balance, scale bets down",
            },
            "survival_min_pct": {
                "type": "str", "default": "1.5",
                "desc": "Minimum bet % in deep survival mode",
            },
            "bankroll_floor": {
                "type": "str", "default": "0.25",
                "desc": "Stop betting below this ratio of starting balance",
            },
        }

    # ── init ────────────────────────────────────────────────────────────
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.chance = str(params.get("chance", "49.5"))
        self.base_bet_pct = Decimal(str(params.get("base_bet_pct", "3")))
        self.is_high = bool(params.get("is_high", True))

        self.paroli_multiplier = Decimal(str(params.get("paroli_multiplier", "2.5")))
        self.paroli_max_steps = max(1, int(params.get("paroli_max_steps", 4)))

        self.survival_threshold = Decimal(str(params.get("survival_threshold", "0.50")))
        self.survival_min_pct = Decimal(str(params.get("survival_min_pct", "1.5")))
        self.bankroll_floor = Decimal(str(params.get("bankroll_floor", "0.25")))

        self._starting_balance = Decimal(str(ctx.starting_balance))
        self._current_balance = self._starting_balance
        self._win_streak = 0
        self._paroli_step = 0
        self._total_wagered = _ZERO

    # ── lifecycle ───────────────────────────────────────────────────────
    def on_session_start(self) -> None:
        self._starting_balance = Decimal(str(self.ctx.starting_balance))
        self._current_balance = self._starting_balance
        self._win_streak = 0
        self._paroli_step = 0
        self._total_wagered = _ZERO

    # ── next_bet ────────────────────────────────────────────────────────
    def next_bet(self) -> Optional[BetSpec]:
        # Hard floor — stop if bankroll too low
        floor = (self._starting_balance * self.bankroll_floor).quantize(_QUANT)
        if self._current_balance <= floor:
            return None

        bet_pct = self._effective_bet_pct()

        # Base amount from balance
        base_amount = (self._current_balance * bet_pct / _HUNDRED).quantize(_QUANT)

        # Paroli boost: multiply on consecutive wins
        amount = base_amount
        if self._paroli_step > 0:
            boost = self.paroli_multiplier ** self._paroli_step
            amount = (base_amount * boost).quantize(_QUANT)

        # Cap at 50% of current balance to prevent single-bet wipeout
        max_bet = (self._current_balance * Decimal("50") / _HUNDRED).quantize(_QUANT)
        amount = min(amount, max_bet)

        if amount <= _ZERO:
            return None

        self._total_wagered += amount

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _effective_bet_pct(self) -> Decimal:
        """Proportional survival scaling: smoothly reduce bet % as balance drops."""
        ratio = self._current_balance / self._starting_balance if self._starting_balance > _ZERO else _ONE

        if ratio >= self.survival_threshold:
            return self.base_bet_pct

        # Linear interpolation from base_bet_pct → survival_min_pct
        # across the range [bankroll_floor, survival_threshold]
        span = self.survival_threshold - self.bankroll_floor
        if span <= _ZERO:
            return self.survival_min_pct

        t = (ratio - self.bankroll_floor) / span  # 0.0 at floor, 1.0 at threshold
        t = max(_ZERO, min(_ONE, t))
        return self.survival_min_pct + t * (self.base_bet_pct - self.survival_min_pct)

    # ── result handling ─────────────────────────────────────────────────
    def on_bet_result(self, result: BetResult) -> None:
        self._current_balance = Decimal(str(result.get("balance", "0")))
        won = bool(result.get("win"))

        if won:
            self._win_streak += 1
            if self._paroli_step < self.paroli_max_steps:
                self._paroli_step += 1
            else:
                self._paroli_step = 0  # reset after max steps reached
        else:
            self._win_streak = 0
            self._paroli_step = 0

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
