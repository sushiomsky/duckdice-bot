"""
Unified Progression Strategy - Consolidation of 3 progression variants.

This module provides a single configurable strategy that can operate as any of
the original progression strategies (fibonacci, dalembert, labouchere) via 
constructor parameters.

All three share the concept of modifying bet sizing based on win/loss history
in a mathematical progression.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional, List

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("unified-progression")
class UnifiedProgression:
    """
    Unified progression strategy: configure via progression_type parameter.
    
    progression_type options:
    - 'fibonacci': Fibonacci sequence progression (1,1,2,3,5,8,...)
    - 'dalembert': Linear progression (+/- fixed amount)
    - 'labouchere': Cancellation system with sequence management
    """

    @classmethod
    def name(cls) -> str:
        return "unified-progression"

    @classmethod
    def describe(cls) -> str:
        return (
            "Unified progression strategy: Fibonacci, D'Alembert, or Labouchere "
            "via progression_type config. Mathematical bet sizing based on wins/losses."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low-Medium",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Three classic betting progressions in one strategy",
                "Gentler bet growth than martingale",
                "Mathematically elegant bet sizing",
                "Good bankroll preservation",
                "Highly configurable parameters",
            ],
            cons=[
                "Still vulnerable to extended losing streaks",
                "House edge affects long-term outcomes",
                "Requires tracking sequence/level state",
                "Can lead to large bets without proper limits",
            ],
            best_use_case=(
                "Medium-term grinding sessions. Good for learning different "
                "progression systems without maintaining multiple files."
            ),
            tips=[
                "Start with 'dalembert' if new to progressions",
                "Use 'fibonacci' for moderate aggression",
                "Use 'labouchere' for maximum flexibility",
                "Always set max_bet to prevent runaway escalation",
                "Combine with session stop-loss at 25-30%",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "progression_type": {
                "type": "str",
                "default": "dalembert",
                "desc": "Type of progression: fibonacci|dalembert|labouchere",
            },
            "base_bet": {
                "type": "str",
                "default": "0.000001",
                "desc": "Base bet amount (1 unit)",
            },
            "loss_limit": {
                "type": "int",
                "default": 50,
                "desc": "Max loss count before auto-stop (0 = off)",
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
            # Fibonacci specific
            "fib_max_level": {
                "type": "int",
                "default": 15,
                "desc": "Max Fibonacci level before reset",
            },
            # D'Alembert specific
            "dalembert_increment": {
                "type": "str",
                "default": "0.000001",
                "desc": "Amount to add/subtract per loss/win",
            },
            "dalembert_max_bet": {
                "type": "str",
                "default": "0.0001",
                "desc": "Hard cap on D'Alembert bet amount",
            },
            # Labouchere specific
            "labouchere_sequence": {
                "type": "str",
                "default": "1,2,3,4",
                "desc": "Initial Labouchere sequence (comma-separated)",
            },
            "labouchere_reset": {
                "type": "bool",
                "default": True,
                "desc": "Reset to initial sequence when cancelled",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.progression_type = str(params.get("progression_type", "dalembert")).lower()
        self.base_bet = Decimal(str(params.get("base_bet", "0.000001")))
        self.loss_limit = int(params.get("loss_limit", 50))
        self.chance = str(params.get("chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))

        # Fibonacci params
        self.fib_max_level = int(params.get("fib_max_level", 15))

        # D'Alembert params
        self.dalembert_increment = Decimal(str(params.get("dalembert_increment", "0.000001")))
        self.dalembert_max_bet = Decimal(str(params.get("dalembert_max_bet", "0.0001")))

        # Labouchere params
        seq_str = str(params.get("labouchere_sequence", "1,2,3,4"))
        self.labouchere_initial = [int(x.strip()) for x in seq_str.split(",") if x.strip()]
        self.labouchere_reset = bool(params.get("labouchere_reset", True))

        # Common state
        self._loss_count = 0
        self._win_count = 0

        # Progression-specific state
        self._fib_sequence: List[int] = []
        self._fib_level = 0

        self._dalembert_current = self.base_bet

        self._labouchere_sequence: List[int] = []

        self._initialize_progression()

    def _initialize_progression(self) -> None:
        """Initialize progression-specific state."""
        if self.progression_type == "fibonacci":
            self._fib_sequence = self._generate_fibonacci(self.fib_max_level)
            self._fib_level = 0
        elif self.progression_type == "dalembert":
            self._dalembert_current = self.base_bet
        elif self.progression_type == "labouchere":
            self._labouchere_sequence = self.labouchere_initial.copy()

    def _generate_fibonacci(self, n: int) -> List[int]:
        """Generate first n Fibonacci numbers."""
        if n <= 0:
            return [1]
        elif n == 1:
            return [1]

        fib = [1, 1]
        for i in range(2, n):
            fib.append(fib[i - 1] + fib[i - 2])
        return fib

    def on_session_start(self) -> None:
        """Initialize session state."""
        self._loss_count = 0
        self._win_count = 0
        self._initialize_progression()

        self.ctx.printer(
            f"[unified-progression] started | type={self.progression_type} | "
            f"base_bet={self.base_bet} | chance={self.chance}%"
        )

    def on_session_end(self, reason: str) -> None:
        """Log session summary."""
        self.ctx.printer(
            f"[unified-progression] ended ({reason}) | "
            f"wins={self._win_count} | losses={self._loss_count}"
        )

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet based on progression_type."""
        # Check loss limit
        if self.loss_limit > 0 and self._loss_count >= self.loss_limit:
            self.ctx.printer(
                f"[unified-progression] loss limit reached ({self._loss_count}/{self.loss_limit})"
            )
            return None

        if self.progression_type == "fibonacci":
            return self._next_bet_fibonacci()
        elif self.progression_type == "dalembert":
            return self._next_bet_dalembert()
        elif self.progression_type == "labouchere":
            return self._next_bet_labouchere()
        else:
            # Default to dalembert
            return self._next_bet_dalembert()

    def _next_bet_fibonacci(self) -> Optional[BetSpec]:
        """Fibonacci progression bet."""
        if self._fib_level >= len(self._fib_sequence):
            # Cap reached, reset or stay at max
            self._fib_level = len(self._fib_sequence) - 1

        multiplier = self._fib_sequence[self._fib_level]
        amount = self.base_bet * Decimal(str(multiplier))

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_dalembert(self) -> Optional[BetSpec]:
        """D'Alembert progression bet."""
        amount = max(self.base_bet, self._dalembert_current)
        amount = min(amount, self.dalembert_max_bet)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_labouchere(self) -> Optional[BetSpec]:
        """Labouchere cancellation system bet."""
        if not self._labouchere_sequence:
            # Sequence complete, reset if configured
            if self.labouchere_reset:
                self._labouchere_sequence = self.labouchere_initial.copy()
            else:
                # Just use base bet
                amount = self.base_bet
                return {
                    "game": "dice",
                    "amount": format(amount, "f"),
                    "chance": self.chance,
                    "is_high": self.is_high,
                    "faucet": self.ctx.faucet,
                }

        # Bet = sum of first and last elements
        if len(self._labouchere_sequence) == 1:
            bet_units = self._labouchere_sequence[0]
        else:
            bet_units = self._labouchere_sequence[0] + self._labouchere_sequence[-1]

        amount = self.base_bet * Decimal(str(bet_units))

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        """Update progression state based on result."""
        self.ctx.recent_results.append(result)

        won = bool(result.get("win", False))

        if won:
            self._win_count += 1
            self._handle_win()
        else:
            self._loss_count += 1
            self._handle_loss()

    def _handle_win(self) -> None:
        """Progress on win (move backward in sequence)."""
        if self.progression_type == "fibonacci":
            # Move backward 2 steps (or to 0)
            self._fib_level = max(0, self._fib_level - 2)
        elif self.progression_type == "dalembert":
            # Decrease by increment
            self._dalembert_current = max(
                self.base_bet, self._dalembert_current - self.dalembert_increment
            )
        elif self.progression_type == "labouchere":
            # Cancel first and last elements
            if len(self._labouchere_sequence) >= 2:
                self._labouchere_sequence.pop(0)  # Remove first
                self._labouchere_sequence.pop()  # Remove last
            elif len(self._labouchere_sequence) == 1:
                self._labouchere_sequence.pop(0)

    def _handle_loss(self) -> None:
        """Progress on loss (move forward in sequence)."""
        if self.progression_type == "fibonacci":
            # Move forward 2 steps (or to max)
            self._fib_level = min(
                len(self._fib_sequence) - 1, self._fib_level + 2
            )
        elif self.progression_type == "dalembert":
            # Increase by increment
            self._dalembert_current = min(
                self.dalembert_max_bet,
                self._dalembert_current + self.dalembert_increment,
            )
        elif self.progression_type == "labouchere":
            # Add bet amount to end of sequence
            if len(self._labouchere_sequence) >= 1:
                if len(self._labouchere_sequence) == 1:
                    bet_units = self._labouchere_sequence[0]
                else:
                    bet_units = (
                        self._labouchere_sequence[0] + self._labouchere_sequence[-1]
                    )
            else:
                bet_units = 1

            self._labouchere_sequence.append(bet_units)
