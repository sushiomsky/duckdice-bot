from __future__ import annotations
"""
Progressive Win-Only Scaling Strategy
- Base Bet: 1/100 of balance
- Start Chance: 4%
- Bet & chance increase ONLY on win
- Full reset on any loss
- Aggressive scaling with defined multiplier tables
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("progressive-win-scaling")
class ProgressiveWinScaling:
    """Progressive Win-Only Scaling: Aggressive scaling on wins, full reset on loss."""

    @classmethod
    def name(cls) -> str:
        return "progressive-win-scaling"

    @classmethod
    def describe(cls) -> str:
        return "Aggressive win-only scaling with 4-24% chance progression. Resets completely on any loss."

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Medium",
            volatility="Extreme",
            time_to_profit="Very Quick or Very Slow",
            recommended_for="Experienced risk-takers",
            pros=[
                "Massive profit potential during winning streaks",
                "Low starting chance (4%) means high multipliers",
                "Scales aggressively on consecutive wins",
                "Full reset limits catastrophic losses",
                "Can turn small balance into large profit quickly"
            ],
            cons=[
                "Single loss destroys all progress",
                "4% starting chance = 96% chance to lose first bet",
                "Requires extremely lucky streaks to profit",
                "Emotionally challenging to lose big bets",
                "Not sustainable long-term",
                "Can drain bankroll quickly"
            ],
            best_use_case="High-risk gambling for thrill-seekers. Best for 'all-or-nothing' sessions with expendable bankroll.",
            tips=[
                "Set strict profit targets and STOP when hit",
                "Expect to lose most sessions - this is normal",
                "Never use more than 5-10% of total bankroll",
                "One 5-win streak can yield 50-100x profit",
                "Consider stopping after 3-4 wins (high chance will reset)",
                "This is a 'lottery ticket' strategy, not investment"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_divisor": {
                "type": "int",
                "default": 100,
                "desc": "Divide balance by this for base bet (default: balance/100)"
            },
            "base_chance": {
                "type": "float",
                "default": 4.0,
                "desc": "Starting win chance percentage"
            },
            "max_chance": {
                "type": "float",
                "default": 24.0,
                "desc": "Maximum win chance percentage (safety cap)"
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet on High or Low"
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_divisor = int(params.get("base_divisor", 100))
        self.base_chance = float(params.get("base_chance", 4.0))
        self.max_chance = float(params.get("max_chance", 24.0))
        self.is_high = bool(params.get("is_high", True))

        # Bet increase table per win streak
        # index = win streak AFTER win
        self.bet_multipliers = {
            1: 4.0,   # +300% on 1st win
            2: 3.4,   # +240% on 2nd win
            3: 2.8,   # +180% on 3rd win
            4: 2.2,   # +120% on 4th win
            5: 1.6    # +60% on 5th win
        }

        # Chance progression per win streak
        self.chance_steps = {
            1: 8.0,
            2: 12.0,
            3: 16.0,
            4: 20.0,
            5: 24.0
        }

        # State
        self._win_streak = 0
        self._base_bet = Decimal("0")
        self._current_bet = Decimal("0")
        self._current_chance = self.base_chance

    def _reset(self) -> None:
        """Reset to base state"""
        self._win_streak = 0
        self._current_bet = self._base_bet
        self._current_chance = self.base_chance

    def _calculate_base_bet(self) -> Decimal:
        """Calculate base bet from current balance"""
        try:
            # Get current balance
            balance = Decimal(self.ctx.recent_results[-1]["balance"]) if self.ctx.recent_results else Decimal("1.0")
            base = balance / Decimal(self.base_divisor)
            
            # Ensure minimum bet (prevent microscopic amounts)
            min_bet = Decimal("0.00000001")  # 1 satoshi for BTC
            return max(base, min_bet)
        except Exception:
            return Decimal("0.00000001")

    def on_session_start(self) -> None:
        self._base_bet = self._calculate_base_bet()
        self._current_bet = self._base_bet
        self._current_chance = self.base_chance
        self._win_streak = 0

    def next_bet(self) -> Optional[BetSpec]:
        # Recalculate base bet before each bet (adapts to balance changes)
        self._base_bet = self._calculate_base_bet()
        
        # Ensure current bet is at least base bet
        if self._current_bet < self._base_bet:
            self._current_bet = self._base_bet

        return {
            "game": "dice",
            "amount": format(self._current_bet, 'f'),
            "chance": str(self._current_chance),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = bool(result.get("win"))
        
        if win:
            # Increment win streak
            self._win_streak += 1

            # Determine step (cap at max defined level)
            step = min(self._win_streak, 5)

            # Apply chance progression
            self._current_chance = self.chance_steps.get(step, self.max_chance)

            # Apply bet multiplier based on last bet
            multiplier = self.bet_multipliers.get(step, 1.6)
            self._current_bet = self._current_bet * Decimal(str(multiplier))

        else:
            # Full reset on any loss
            self._reset()

        # Absolute safety clamps
        if self._current_chance > self.max_chance:
            self._current_chance = self.max_chance

        # Prevent microscopic bets
        if self._current_bet < self._base_bet:
            self._current_bet = self._base_bet

        # Store result
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
