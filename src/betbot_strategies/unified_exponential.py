"""
Unified Exponential Strategy - Consolidation of 2 micro-exponential variants.

This module provides a single configurable strategy that can operate as either
the aggressive micro-exponential (300x target) or the safer variant (100x target)
via the safe_mode constructor parameter.

Both strategies use multi-mode adaptive betting with volatility learning.
"""

from __future__ import annotations

import random
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("unified-exponential")
class UnifiedExponential:
    """
    Unified micro-exponential strategy: configure via safe_mode parameter.
    
    - safe_mode=False: Aggressive (300x target, 45% max drawdown)
    - safe_mode=True: Conservative (100x target, 35% max drawdown)
    
    Both use 5 adaptive modes: PROBE, PRESSURE, HUNT, CHAOS, KILL.
    """

    @classmethod
    def name(cls) -> str:
        return "unified-exponential"

    @classmethod
    def describe(cls) -> str:
        return (
            "Unified micro-exponential growth: aggressive (300x) or safe (100x) "
            "via safe_mode. 5-mode adaptive system for micro balance recovery."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High-Extreme",
            bankroll_required="Micro (<$1)",
            volatility="Extreme",
            time_to_profit="Variable",
            recommended_for="Experimental",
            pros=[
                "Multi-mode adaptive strategy switching",
                "Volatility learning system",
                "Targets 100x-300x gains from dust",
                "Safe mode provides reduced risk option",
            ],
            cons=[
                "HIGH to EXTREME risk depending on mode",
                "Not suitable for significant balances",
                "Kill mode can bet 50-65% of balance",
                "Requires lucky runs to succeed",
            ],
            best_use_case="Micro balance / dust recovery ONLY. Do NOT use with real money.",
            tips=[
                "Only use with micro balances (<$1 equivalent)",
                "Enable safe_mode=True for conservative play",
                "Monitor mode switches — KILL is most risky",
                "Set session time limits to prevent addiction",
                "Accept total loss as possible outcome",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "safe_mode": {
                "type": "bool",
                "default": True,
                "desc": "Use safer variant (100x, 35% dd) vs aggressive (300x, 45% dd)",
            },
            "base_bet_percent": {
                "type": "str",
                "default": "0.01",
                "desc": "Base bet % of balance",
            },
            "growth_rate": {
                "type": "float",
                "default": 1.3,
                "desc": "Multiplier for bet scaling across modes",
            },
            "max_bet_percent": {
                "type": "str",
                "default": "0.90",
                "desc": "Hard cap on single bet",
            },
            "profit_target_multiplier": {
                "type": "int",
                "default": 50,
                "desc": "Target balance multiplier (50 or 100)",
            },
            "max_drawdown_percent": {
                "type": "str",
                "default": "20",
                "desc": "Max allowed drawdown before emergency brake",
            },
        }

    MODE_PROBE = "PROBE"
    MODE_PRESSURE = "PRESSURE"
    MODE_HUNT = "HUNT"
    MODE_CHAOS = "CHAOS"
    MODE_KILL = "KILL"

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.safe_mode = bool(params.get("safe_mode", True))
        self.base_bet_percent = Decimal(str(params.get("base_bet_percent", "0.01")))
        self.growth_rate = float(params.get("growth_rate", 1.5))
        self.max_bet_percent = Decimal(str(params.get("max_bet_percent", "0.90")))

        if self.safe_mode:
            self.profit_target_x = 100
            self.max_drawdown_pct = 35.0
            self.kill_bet_pct = 0.50
        else:
            self.profit_target_x = 300
            self.max_drawdown_pct = 45.0
            self.kill_bet_pct = 0.65

        self.initial_balance = Decimal(str(ctx.starting_balance or "0"))
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance

        self.current_mode = self.MODE_PROBE
        self.bets_in_mode = 0
        self.loss_streak = 0
        self.win_streak = 0
        self.total_bets = 0

    def on_session_start(self) -> None:
        """Initialize session state."""
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.current_mode = self.MODE_PROBE
        self.bets_in_mode = 0
        self.loss_streak = 0
        self.win_streak = 0
        self.total_bets = 0

        self.ctx.printer(
            f"[unified-exponential] started | safe_mode={self.safe_mode} | "
            f"target={self.profit_target_x}x | max_dd={self.max_drawdown_pct}%"
        )

    def on_session_end(self, reason: str) -> None:
        """Log session summary."""
        roi = (
            float((self.current_balance - self.initial_balance) / self.initial_balance * 100)
            if self.initial_balance
            else 0
        )

        self.ctx.printer(
            f"[unified-exponential] ended ({reason}) | "
            f"mode={self.current_mode} | bets={self.total_bets} | "
            f"ROI={roi:+.1f}%"
        )

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet based on current mode."""
        # Check profit target
        target = self.initial_balance * Decimal(str(self.profit_target_x))
        if self.current_balance >= target:
            self.ctx.printer(f"[unified-exponential] profit target reached ({self.profit_target_x}x)")
            return None

        # Check drawdown limit (emergency brake)
        drawdown = float((self.peak_balance - self.current_balance) / self.peak_balance * 100)
        if drawdown > self.max_drawdown_pct:
            self.ctx.printer(f"[unified-exponential] max drawdown exceeded ({drawdown:.1f}%)")
            return None

        if self.current_balance <= 0:
            return None

        # Update mode based on streaks
        self._update_mode()

        # Generate bet based on current mode
        if self.current_mode == self.MODE_PROBE:
            return self._bet_probe()
        elif self.current_mode == self.MODE_PRESSURE:
            return self._bet_pressure()
        elif self.current_mode == self.MODE_HUNT:
            return self._bet_hunt()
        elif self.current_mode == self.MODE_CHAOS:
            return self._bet_chaos()
        elif self.current_mode == self.MODE_KILL:
            return self._bet_kill()
        else:
            return self._bet_probe()

    def _update_mode(self) -> None:
        """Update strategy mode based on streaks and balance."""
        self.bets_in_mode += 1

        # Mode transitions based on performance
        if self.loss_streak >= 5:
            if self.current_mode != self.MODE_KILL:
                self.current_mode = self.MODE_KILL
                self.bets_in_mode = 0
        elif self.win_streak >= 3:
            if self.current_mode != self.MODE_HUNT:
                self.current_mode = self.MODE_HUNT
                self.bets_in_mode = 0
        elif self.loss_streak >= 3 and self.current_mode != self.MODE_PRESSURE:
            self.current_mode = self.MODE_PRESSURE
            self.bets_in_mode = 0
        elif self.bets_in_mode > 20:
            # Rotate modes periodically
            modes = [self.MODE_PROBE, self.MODE_PRESSURE, self.MODE_HUNT, self.MODE_CHAOS]
            idx = modes.index(self.current_mode)
            self.current_mode = modes[(idx + 1) % len(modes)]
            self.bets_in_mode = 0

    def _bet_probe(self) -> Optional[BetSpec]:
        """PROBE: Low-risk data collection at 60% chance."""
        amount = self.current_balance * self.base_bet_percent
        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": "60",
            "is_high": True,
            "faucet": self.ctx.faucet,
        }

    def _bet_pressure(self) -> Optional[BetSpec]:
        """PRESSURE: 18% chance with martingale-style escalation."""
        mult = min(self.loss_streak, 5)  # Cap at 5 losses
        amount = self.current_balance * self.base_bet_percent * Decimal(str(self.growth_rate ** mult))
        amount = min(amount, self.current_balance * self.max_bet_percent)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": "18",
            "is_high": True,
            "faucet": self.ctx.faucet,
        }

    def _bet_hunt(self) -> Optional[BetSpec]:
        """HUNT: Asymmetric long-shot at 0.08-0.20% chance."""
        chance = self.ctx.rng.uniform(0.08, 0.20)
        amount = self.current_balance * self.base_bet_percent * Decimal(str(self.growth_rate))
        amount = min(amount, self.current_balance * self.max_bet_percent)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": f"{chance:.2f}",
            "is_high": True,
            "faucet": self.ctx.faucet,
        }

    def _bet_chaos(self) -> Optional[BetSpec]:
        """CHAOS: Random parameters for entropy forcing."""
        chance = self.ctx.rng.uniform(2.0, 20.0)
        bet_pct = 0.05 if self.safe_mode else 0.15
        amount = self.current_balance * Decimal(str(bet_pct))
        amount = min(amount, self.current_balance * self.max_bet_percent)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": f"{chance:.2f}",
            "is_high": self.ctx.rng.choice([True, False]),
            "faucet": self.ctx.faucet,
        }

    def _bet_kill(self) -> Optional[BetSpec]:
        """KILL: Maximum aggression for explosion (50-65% of balance)."""
        chance = self.ctx.rng.uniform(0.08, 0.25)
        amount = self.current_balance * Decimal(str(self.kill_bet_pct))
        amount = min(amount, self.current_balance * self.max_bet_percent)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": f"{chance:.2f}",
            "is_high": True,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        """Update state based on result."""
        self.ctx.recent_results.append(result)
        self.total_bets += 1

        try:
            self.current_balance = Decimal(str(result.get("balance", self.current_balance)))
        except Exception:
            pass

        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance

        won = bool(result.get("win", False))
        if won:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
