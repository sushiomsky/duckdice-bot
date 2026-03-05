"""
Unified Faucet Strategy - Consolidation of 2 faucet variants.

This module provides a single configurable strategy for playing with free faucet
balances, selectable between 'cashout' mode (gradual USD-target grinding) or
'grind' mode (all-in betting to $20 target).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional
import time

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("unified-faucet")
class UnifiedFaucet:
    """
    Unified faucet strategy: configure via faucet_mode parameter.
    
    faucet_mode options:
    - 'cashout': Staged growth with conservative bet fractions to reach USD target
    - 'grind': All-in betting to reach $20 target quickly
    
    Perfect for free faucet play without depositing real money.
    """

    @classmethod
    def name(cls) -> str:
        return "unified-faucet"

    @classmethod
    def describe(cls) -> str:
        return (
            "Unified faucet strategy: 'cashout' (staged conservative) or 'grind' (all-in) "
            "modes for free faucet balance building."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="None (Free)",
            volatility="Low-Medium",
            time_to_profit="Slow",
            recommended_for="Beginners-Intermediate",
            pros=[
                "Zero risk — uses free faucet only",
                "Perfect for learning without deposit",
                "Two modes: safe grinding or aggressive push",
                "Can build real withdrawal balance",
                "Great for testing platform mechanics",
            ],
            cons=[
                "Extremely slow progress in cashout mode",
                "Grind mode is all-or-nothing",
                "Faucet claim limits apply",
                "Not a realistic profit strategy",
                "Requires patience and discipline",
            ],
            best_use_case=(
                "Learning tool for new players. Build faucet balance risk-free. "
                "Combine with actual betting when comfortable."
            ),
            tips=[
                "Cashout mode: safe, guaranteed slow progress",
                "Grind mode: faster but riskier",
                "Set realistic USD target for your coin",
                "Monitor faucet claim cooldowns",
                "Be patient — this is a long-term grind",
                "Use to learn platform features first",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "faucet_mode": {
                "type": "str",
                "default": "cashout",
                "desc": "Faucet mode: cashout|grind",
            },
            "target_profit": {
                "type": "float",
                "default": 20.0,
                "desc": "Target USD equivalent (default $20)",
            },
            "win_threshold": {
                "type": "float",
                "default": 0.5,
                "desc": "Per-bet target multiplier on wins",
            },
            "bet_fraction_min": {
                "type": "str",
                "default": "0.02",
                "desc": "Min fraction of balance to bet (cashout mode)",
            },
            "bet_fraction_max": {
                "type": "str",
                "default": "0.10",
                "desc": "Max fraction of balance to bet (cashout mode)",
            },
            "chance_percent": {
                "type": "str",
                "default": "50",
                "desc": "Target win chance %",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.faucet_mode = str(params.get("faucet_mode", "cashout")).lower()
        self.target_profit = float(params.get("target_profit", 20.0))
        self.win_threshold = float(params.get("win_threshold", 0.5))
        self.bet_fraction_min = Decimal(str(params.get("bet_fraction_min", "0.02")))
        self.bet_fraction_max = Decimal(str(params.get("bet_fraction_max", "0.10")))
        self.chance_percent = str(params.get("chance_percent", "50"))

        # State
        self._starting_balance = Decimal("0")
        self._current_balance = Decimal("0")
        self._total_bets = 0
        self._total_wins = 0

        # Faucet claim tracking (if applicable)
        self._last_claim_time = time.time()
        self._claim_cooldown_seconds = 3600  # 1 hour typical

    def on_session_start(self) -> None:
        """Initialize session state."""
        bal = Decimal(str(self.ctx.starting_balance or "0"))
        self._starting_balance = bal
        self._current_balance = bal
        self._total_bets = 0
        self._total_wins = 0

        self.ctx.printer(
            f"[unified-faucet] started | mode={self.faucet_mode} | "
            f"target=${self.target_profit} | balance={bal}"
        )

    def on_session_end(self, reason: str) -> None:
        """Log session summary."""
        profit = self._current_balance - self._starting_balance
        profit_pct = (
            float(profit / self._starting_balance * 100)
            if self._starting_balance
            else 0
        )
        sign = "+" if profit >= 0 else ""

        self.ctx.printer(
            f"[unified-faucet] ended ({reason}) | "
            f"bets={self._total_bets} | wins={self._total_wins} | "
            f"profit={sign}{profit:.8f} ({sign}{profit_pct:.2f}%)"
        )

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet based on faucet_mode."""
        # Check if target reached
        if self._current_balance >= Decimal(str(self.target_profit)):
            self.ctx.printer(
                f"[unified-faucet] target reached (${self._current_balance:.2f})"
            )
            return None

        if self._current_balance <= 0:
            return None

        if self.faucet_mode == "cashout":
            return self._next_bet_cashout()
        elif self.faucet_mode == "grind":
            return self._next_bet_grind()
        else:
            return self._next_bet_cashout()

    def _next_bet_cashout(self) -> Optional[BetSpec]:
        """Cashout mode: staged conservative betting."""
        bal = self._current_balance

        # Determine bet fraction based on balance stage
        if bal < Decimal("0.25"):
            frac = self.bet_fraction_min
        elif bal < Decimal("5.00"):
            frac = (self.bet_fraction_min + self.bet_fraction_max) / Decimal("2")
        else:
            frac = self.bet_fraction_max

        amount = bal * frac
        amount = max(Decimal("0.00000001"), amount)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.chance_percent,
            "is_high": True,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_grind(self) -> Optional[BetSpec]:
        """Grind mode: all-in push to target."""
        bal = self._current_balance
        
        # Calculate required multiplier to reach target
        target = Decimal(str(self.target_profit))
        mult_needed = target / bal if bal > 0 else Decimal("1")

        # Convert multiplier to chance: 99 / chance = multiplier
        chance_val = 99.0 / float(mult_needed)
        chance_val = max(0.01, min(99.0, chance_val))

        amount = bal * Decimal("0.95")  # Bet 95% (leave small dust)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": f"{chance_val:.2f}",
            "is_high": True,
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
        if won:
            self._total_wins += 1
