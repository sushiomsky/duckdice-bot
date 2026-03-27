from __future__ import annotations
"""
Lottery Sniper Strategy (v6)

Two modes:
  HUNT    – 1% chance, 0.25% of balance per bet (scales up during droughts).
            Alternates high/low each bet.
  LOTTERY – After each hunt hit, fires 10 lottery bets at 0.1% chance with
            boosted bet size (playing with house money). A lottery hit reloads
            the full burst.
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_QUANT = Decimal("0.00000001")


@register("lottery-sniper")
class LotterySniper:
    """Hunts at 1%, fires boosted lottery bursts after each hit."""

    @classmethod
    def name(cls) -> str:
        return "lottery-sniper"

    @classmethod
    def describe(cls) -> str:
        return (
            "Hunts at 1% chance (0.25% of balance, scaling on drought). "
            "After each hit, fires 10 boosted lottery bets at 0.1% chance. "
            "Lottery hits reload the burst. Alternates high/low."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Slow",
            recommended_for="Intermediate",
            pros=[
                "Lottery hit reloads the full burst – chains moonshots",
                "Boosted lottery bet size plays with house money after a hit",
                "Drought scaling increases hunt bet to capitalise on overdue hits",
                "High/low alternation covers both sides of the roll",
                "Separate smaller lottery bet size preserves capital",
            ],
            cons=[
                "1% base chance means frequent losses",
                "Lottery requires a hunt hit first – long droughts possible",
                "Requires patience and adequate bankroll",
            ],
            best_use_case=(
                "Grinders who want compounding moonshot bursts "
                "triggered by hunt wins."
            ),
            tips=[
                "Each hunt hit at 1% unlocks a burst of 10 lottery bets",
                "Lottery bets fire at 0.1% chance for massive payout potential",
                "A lottery hit reloads the burst – streaks compound",
                "Lottery boost sizes bets at 0.50% of balance (house money)",
                "After 150 dry hunt bets the bet size doubles to capitalise harder",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "chance": {
                "type": "str", "default": "1",
                "desc": "Normal bet win chance percent",
            },
            "bet_pct": {
                "type": "str", "default": "0.25",
                "desc": "Normal bet size as % of current balance",
            },
            "lottery_chance": {
                "type": "str", "default": "0.1",
                "desc": "Lottery bet win chance percent",
            },
            "lottery_bet_pct": {
                "type": "str", "default": "0.10",
                "desc": "Lottery bet size as % of current balance",
            },
            "lottery_boost_pct": {
                "type": "str", "default": "0.50",
                "desc": "Boosted lottery bet size as % of balance (house money)",
            },
            "lottery_count": {
                "type": "int", "default": 10,
                "desc": "Number of lottery bets to fire after each hit",
            },
            "drought_threshold": {
                "type": "int", "default": 150,
                "desc": "Hunt bets without a win before bet size scales up",
            },
            "drought_multiplier": {
                "type": "str", "default": "2.0",
                "desc": "Bet size multiplier applied during a drought",
            },
            "is_high": {
                "type": "bool", "default": True,
                "desc": "Starting bet direction (alternates each bet)",
            },
        }

    # ── init ────────────────────────────────────────────────────────────
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        # Hunt params
        self.chance = str(params.get("chance", "1"))
        self.bet_pct = Decimal(str(params.get("bet_pct", "0.25")))

        # Lottery params
        self.lottery_chance = str(params.get("lottery_chance", "0.1"))
        self.lottery_bet_pct = Decimal(str(params.get("lottery_bet_pct", "0.10")))
        self.lottery_boost_pct = Decimal(str(params.get("lottery_boost_pct", "0.50")))
        self.lottery_count = max(1, int(params.get("lottery_count", 10)))

        # Drought scaling
        self.drought_threshold = max(1, int(params.get("drought_threshold", 150)))
        self.drought_multiplier = Decimal(str(params.get("drought_multiplier", "2.0")))

        # Alternating direction
        self._is_high = bool(params.get("is_high", True))

        # Internal state
        self._current_balance = Decimal(str(ctx.starting_balance))
        self._bet_count = 0
        self._lottery_remaining = 0
        self._hunt_drought = 0            # consecutive hunt losses
        self._last_bet_was_lottery = False
        self._in_boost = False            # using boosted lottery sizing

    # ── lifecycle ───────────────────────────────────────────────────────
    def on_session_start(self) -> None:
        self._current_balance = Decimal(str(self.ctx.starting_balance))
        self._bet_count = 0
        self._lottery_remaining = 0
        self._hunt_drought = 0
        self._last_bet_was_lottery = False
        self._in_boost = False

    # ── next_bet ────────────────────────────────────────────────────────
    def next_bet(self) -> Optional[BetSpec]:
        self._bet_count += 1
        self._is_high = not self._is_high  # alternate high/low

        if self._lottery_remaining > 0:
            self._lottery_remaining -= 1
            return self._lottery_bet()

        return self._normal_bet()

    # ── bet builders ────────────────────────────────────────────────────
    def _normal_bet(self) -> Optional[BetSpec]:
        pct = self.bet_pct
        if self._hunt_drought >= self.drought_threshold:
            pct = (pct * self.drought_multiplier).quantize(_QUANT)

        amount = (self._current_balance * pct / _HUNDRED).quantize(_QUANT)
        if amount <= _ZERO:
            return None
        self._last_bet_was_lottery = False
        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.chance,
            "is_high": self._is_high,
            "faucet": self.ctx.faucet,
        }

    def _lottery_bet(self) -> Optional[BetSpec]:
        pct = self.lottery_boost_pct if self._in_boost else self.lottery_bet_pct
        amount = (self._current_balance * pct / _HUNDRED).quantize(_QUANT)
        if amount <= _ZERO:
            self._last_bet_was_lottery = False
            return self._normal_bet()

        self._last_bet_was_lottery = True
        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.lottery_chance,
            "is_high": self._is_high,
            "faucet": self.ctx.faucet,
        }

    # ── result handling ─────────────────────────────────────────────────
    def on_bet_result(self, result: BetResult) -> None:
        self._current_balance = Decimal(str(result.get("balance", "0")))
        won = bool(result.get("win"))

        if self._last_bet_was_lottery:
            if won:
                # Lottery hit – reload the full burst
                self._lottery_remaining = self.lottery_count
                self._in_boost = True
        else:
            # Hunt result
            if won:
                self._hunt_drought = 0
                self._lottery_remaining = self.lottery_count
                self._in_boost = True   # first burst uses boosted sizing
            else:
                self._hunt_drought += 1

        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
