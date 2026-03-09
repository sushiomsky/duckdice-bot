"""
Unified Martingale Strategy - Consolidation of 2 martingale variants.

This module provides a single configurable strategy that can operate as either
the classic martingale (double on loss) or anti-martingale (multiply on win) via
constructor parameters.

Both strategies use exponential multiplier growth, but in opposite directions.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("unified-martingale")
class UnifiedMartingale:
    """
    Unified martingale strategy: configure via martingale_type parameter.
    
    martingale_type options:
    - 'classic': Double bet on loss, reset on win
    - 'anti': Multiply bet on win, reset on loss (reverse martingale)
    """

    @classmethod
    def name(cls) -> str:
        return "unified-martingale"

    @classmethod
    def describe(cls) -> str:
        return (
            "Unified martingale strategy: classic (double on loss) or anti (multiply on win) "
            "via martingale_type config. High-risk, quick-profit strategies."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Large",
            volatility="Very High",
            time_to_profit="Quick",
            recommended_for="Expert",
            pros=[
                "Classic guaranteed to win if bankroll unlimited",
                "Anti exploits winning streaks for fast gains",
                "Simple, easy-to-understand mechanics",
                "Quick recovery from losses (classic) or streak capture (anti)",
            ],
            cons=[
                "Exponential bet growth can drain bankroll rapidly",
                "Single extended losing streak (classic) or loss (anti) = catastrophic",
                "House edge still applies",
                "Requires large initial bankroll",
                "High stress during unfavorable runs",
            ],
            best_use_case=(
                "Short sessions with large bankroll and strict limits. "
                "NOT recommended for inexperienced players or long-term play."
            ),
            tips=[
                "ALWAYS set max_multiplier to limit escalation",
                "Use tiny base_amount (0.1% of bankroll minimum)",
                "Set aggressive stop-loss (15-20% max drawdown)",
                "Classic: limit to 6-8 max loss streak",
                "Anti: lock in profits after 2-3 win streaks",
                "Exit immediately when profit target hit",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "martingale_type": {
                "type": "str",
                "default": "classic",
                "desc": "Type: classic|anti",
            },
            "base_bet": {
                "type": "str",
                "default": "0.000001",
                "desc": "Base bet amount",
            },
            "multiplier": {
                "type": "float",
                "default": 1.5,
                "desc": "Multiplier per loss (classic) or win (anti)",
            },
            "max_multiplier": {
                "type": "float",
                "default": 128.0,
                "desc": "Hard cap on accumulated multiplier",
            },
            "chance": {
                "type": "str",
                "default": "49.5",
                "desc": "Win chance percent",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet on High (True) or Low (False)",
            },
            "reset_condition": {
                "type": "str",
                "default": "opposite",
                "desc": "When to reset multiplier: opposite|never|after_n_bets",
            },
            "profit_target_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Stop when profit ≥ this % of starting balance",
            },
            "loss_limit_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Stop when loss ≥ this % of starting balance",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.martingale_type = str(params.get("martingale_type", "classic")).lower()
        self.base_bet = Decimal(str(params.get("base_bet", "0.000001")))
        self.multiplier = float(params.get("multiplier", 2.0))
        self.max_multiplier = float(params.get("max_multiplier", 64.0))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.reset_condition = str(params.get("reset_condition", "opposite")).lower()
        self.profit_target_pct = float(params.get("profit_target_pct", 0.0))
        self.loss_limit_pct = float(params.get("loss_limit_pct", 0.0))

        self._current_multiplier = 1.0
        self._starting_balance = Decimal("0")
        self._current_balance = Decimal("0")
        self._total_bets = 0
        self._total_wins = 0
        self._streak_length = 0  # Positive for wins, negative for losses

    def on_session_start(self) -> None:
        """Initialize session state."""
        bal = Decimal(str(self.ctx.starting_balance or "0"))
        self._starting_balance = bal
        self._current_balance = bal
        self._current_multiplier = 1.0
        self._total_bets = 0
        self._total_wins = 0
        self._streak_length = 0

        self.ctx.printer(
            f"[unified-martingale] started | type={self.martingale_type} | "
            f"base_bet={self.base_bet} | multiplier={self.multiplier}x | "
            f"max={self.max_multiplier}x"
        )

    def on_session_end(self, reason: str) -> None:
        """Log session summary."""
        pnl = self._current_balance - self._starting_balance
        pnl_pct = (
            float(pnl / self._starting_balance * 100)
            if self._starting_balance
            else 0
        )
        sign = "+" if pnl >= 0 else ""

        self.ctx.printer(
            f"[unified-martingale] ended ({reason}) | "
            f"bets={self._total_bets} | wins={self._total_wins} | "
            f"PnL={sign}{pnl:.8f} ({sign}{pnl_pct:.2f}%) | "
            f"multiplier={self._current_multiplier:.1f}x"
        )

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet."""
        # Check profit target
        if self.profit_target_pct > 0:
            target = self._starting_balance * Decimal(
                str(1 + self.profit_target_pct / 100)
            )
            if self._current_balance >= target:
                self.ctx.printer(
                    f"[unified-martingale] profit target reached — stopping"
                )
                return None

        # Check loss limit
        if self.loss_limit_pct > 0:
            limit = self._starting_balance * Decimal(str(1 - self.loss_limit_pct / 100))
            if self._current_balance <= limit:
                self.ctx.printer(f"[unified-martingale] loss limit hit — stopping")
                return None

        if self._current_balance <= 0:
            return None

        # Calculate bet amount
        amount = self.base_bet * Decimal(str(self._current_multiplier))
        amount = min(amount, self._current_balance)  # Never bet more than balance

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        """Update state based on result."""
        self.ctx.recent_results.append(result)

        self._total_bets += 1

        try:
            self._current_balance = Decimal(str(result.get("balance", self._current_balance)))
        except Exception:
            pass

        won = bool(result.get("win", False))

        if self.martingale_type == "classic":
            self._handle_classic(won)
        elif self.martingale_type == "anti":
            self._handle_anti(won)

    def _handle_classic(self, won: bool) -> None:
        """Handle classic martingale: double on loss, reset on win."""
        if won:
            self._total_wins += 1
            self._streak_length = 1
            self._current_multiplier = 1.0
        else:
            self._streak_length -= 1 if self._streak_length > 0 else -1
            # Double on loss (up to max)
            self._current_multiplier = min(
                self._current_multiplier * self.multiplier, self.max_multiplier
            )

    def _handle_anti(self, won: bool) -> None:
        """Handle anti-martingale: multiply on win, reset on loss."""
        if won:
            self._total_wins += 1
            self._streak_length += 1
            # Multiply on win (up to max)
            self._current_multiplier = min(
                self._current_multiplier * self.multiplier, self.max_multiplier
            )
        else:
            self._streak_length = -1
            # Reset on loss
            self._current_multiplier = 1.0
