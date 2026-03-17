from __future__ import annotations
"""
TLE Wager Farming Strategy
==========================
Wager-first dice strategy for time-limited events.

The objective is not profit maximization. Instead, it aims to:
- maximize total session wager
- keep the bankroll alive as long as possible
- progress TLE reward milestones through sustained play

Core behavior:
- 49.5% win chance on standard dice
- micro-Paroli ladder on wins
- reset to base on losses
- reduce sizing during sustained losses and drawdown
- stop only when bankroll falls below a hard floor
"""

import time
from decimal import Decimal, getcontext
from typing import Any, Dict, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

getcontext().prec = 28


@register("tle-wager-farming")
class TLEWagerFarmingStrategy:
    """Wager-focused TLE grinder with micro-Paroli ladder and bankroll protection."""

    @classmethod
    def name(cls) -> str:
        return "tle-wager-farming"

    @classmethod
    def describe(cls) -> str:
        return (
            "Wager-first TLE farming strategy: 49.5% dice, micro-Paroli wins, "
            "loss/drawdown reductions, and long-session bankroll preservation."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="Slow",
            recommended_for="Advanced",
            pros=[
                "Prioritizes total wager instead of short-term profit",
                "Micro-Paroli ladder compounds wins without extreme escalation",
                "Loss-streak reduction softens bad runs",
                "Drawdown sizing reduction helps extend sessions",
                "Detailed wager and average-bet metrics support TLE grinding",
            ],
            cons=[
                "Not optimized for profit",
                "Can slowly bleed bankroll during long neutral/down stretches",
                "Long sessions may still stop well below starting balance",
                "Requires discipline to keep stop floor intact",
                "Moderate volatility remains due to win laddering",
            ],
            best_use_case=(
                "Grinding wagering-based event rewards where longevity and total "
                "action matter more than maximizing ROI."
            ),
            tips=[
                "Use this primarily in TLE sessions, not general profit-hunting runs",
                "Keep base_bet_fraction conservative if bankroll is limited",
                "A lower stop_bankroll_ratio extends sessions but increases risk",
                "Monitor average bet size to ensure drawdown reductions are working",
                "Pair with live-tle mode so session wager counts toward the event",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_fraction": {
                "type": "float",
                "default": 0.04,
                "desc": "Base bet as fraction of current bankroll",
            },
            "win_chance": {
                "type": "str",
                "default": "49.5",
                "desc": "Dice win chance percentage",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet high if True, low if False",
            },
            "multiplier": {
                "type": "float",
                "default": 1.5,
                "desc": "Micro-Paroli win-step multiplier",
            },
            "max_ladder_depth": {
                "type": "int",
                "default": 3,
                "desc": "Maximum micro-Paroli ladder depth",
            },
            "loss_streak_threshold": {
                "type": "int",
                "default": 3,
                "desc": "Reduce bet sizing once this many losses occur in a row",
            },
            "loss_reduction_factor": {
                "type": "float",
                "default": 0.6,
                "desc": "Bet reduction multiplier after the loss streak threshold is reached",
            },
            "drawdown_threshold": {
                "type": "float",
                "default": 0.2,
                "desc": "Drawdown fraction that activates defensive bet sizing",
            },
            "drawdown_bet_reduction": {
                "type": "float",
                "default": 0.7,
                "desc": "Multiplier applied to base bet while in drawdown mode",
            },
            "stop_bankroll_ratio": {
                "type": "float",
                "default": 0.4,
                "desc": "Stop when bankroll falls to start_bankroll * this ratio",
            },
            "min_amount": {
                "type": "str",
                "default": "0.000001",
                "desc": "Absolute minimum bet amount floor",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_bet_fraction = float(params.get("base_bet_fraction", 0.04))
        self.win_chance = str(params.get("win_chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))
        self.multiplier = float(params.get("multiplier", 1.5))
        self.max_ladder_depth = max(1, int(params.get("max_ladder_depth", 3)))
        self.loss_streak_threshold = max(1, int(params.get("loss_streak_threshold", 3)))
        self.loss_reduction_factor = float(params.get("loss_reduction_factor", 0.6))
        self.drawdown_threshold = float(params.get("drawdown_threshold", 0.2))
        self.drawdown_bet_reduction = float(params.get("drawdown_bet_reduction", 0.7))
        self.stop_bankroll_ratio = float(params.get("stop_bankroll_ratio", 0.4))
        self.min_amount = Decimal(str(params.get("min_amount", "0.000001")))

        self._start_bankroll = Decimal("0")
        self._bankroll = Decimal("0")
        self._win_streak = 0
        self._loss_streak = 0
        self._ladder_step = 0
        self._last_bet_amount = Decimal("0")
        self._total_wager = Decimal("0")
        self._bets_count = 0
        self._session_started_at = 0.0
        self._should_stop = False

    def on_session_start(self) -> None:
        self._start_bankroll = self._current_bankroll()
        self._bankroll = self._start_bankroll
        self._win_streak = 0
        self._loss_streak = 0
        self._ladder_step = 0
        self._last_bet_amount = Decimal("0")
        self._total_wager = Decimal("0")
        self._bets_count = 0
        self._session_started_at = time.time()
        self._should_stop = False
        self.ctx.printer(
            "[tle-wager-farming] session started | "
            f"bankroll={self._bankroll:.8f} stop_floor={self._stop_floor():.8f}"
        )

    def next_bet(self) -> Optional[BetSpec]:
        if self.should_stop():
            return None

        bankroll = self._current_bankroll()
        base_bet = self.calculate_base_bet(bankroll)
        amount = self.calculate_next_bet(base_bet)
        amount = self._clamp_bet(amount, bankroll)
        self._last_bet_amount = amount
        avg_bet = self.average_bet_size()
        self.ctx.printer(
            "[tle-wager-farming] "
            f"bankroll={bankroll:.8f} total_wager={self._total_wager:.8f} "
            f"bets={self._bets_count} avg_bet={avg_bet:.8f} "
            f"win_streak={self._win_streak} loss_streak={self._loss_streak} "
            f"ladder_step={self._ladder_step + 1}/{self.max_ladder_depth} "
            f"bet={amount:.8f}"
        )
        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.win_chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)
        self._bets_count += 1
        self._total_wager += self._last_bet_amount

        try:
            self._bankroll = Decimal(str(result.get("balance", self._bankroll)))
        except Exception:
            pass

        if bool(result.get("win", False)):
            self._win_streak += 1
            self._loss_streak = 0
            if self._ladder_step + 1 >= self.max_ladder_depth:
                self._ladder_step = 0
            else:
                self._ladder_step += 1
        else:
            self._win_streak = 0
            self._loss_streak += 1
            self._ladder_step = 0

        self._should_stop = self._bankroll <= self._stop_floor()

    def on_session_end(self, reason: str) -> None:
        self.ctx.printer(
            "[tle-wager-farming] session ended | "
            f"reason={reason} bankroll={self._bankroll:.8f} "
            f"total_wager={self._total_wager:.8f} bets={self._bets_count} "
            f"avg_bet={self.average_bet_size():.8f} "
            f"duration_sec={self.session_duration():.2f}"
        )

    def should_stop(self) -> bool:
        return self._should_stop or self._current_bankroll() <= self._stop_floor()

    def calculate_base_bet(self, bankroll: Decimal) -> Decimal:
        amount = bankroll * Decimal(str(self.base_bet_fraction))
        if bankroll <= self._drawdown_floor():
            amount *= Decimal(str(self.drawdown_bet_reduction))
        return amount

    def calculate_next_bet(self, base_bet: Decimal) -> Decimal:
        amount = base_bet * (Decimal(str(self.multiplier)) ** self._ladder_step)
        if self._loss_streak >= self.loss_streak_threshold:
            amount *= Decimal(str(self.loss_reduction_factor))
        return amount

    def average_bet_size(self) -> Decimal:
        if self._bets_count <= 0:
            return Decimal("0")
        return self._total_wager / Decimal(self._bets_count)

    def session_duration(self) -> float:
        if self._session_started_at <= 0:
            return 0.0
        return max(0.0, time.time() - self._session_started_at)

    def _current_bankroll(self) -> Decimal:
        if self._bankroll > 0:
            return self._bankroll
        try:
            bal = Decimal(self.ctx.current_balance_str())
            if bal > 0:
                return bal
        except Exception:
            pass
        try:
            bal = Decimal(str(self.ctx.starting_balance or "0"))
            if bal > 0:
                return bal
        except Exception:
            pass
        return self.min_amount * Decimal("1000")

    def _clamp_bet(self, amount: Decimal, bankroll: Decimal) -> Decimal:
        capped = max(self.min_amount, amount)
        if capped > bankroll:
            capped = bankroll
        return max(self.min_amount, capped)

    def _stop_floor(self) -> Decimal:
        return self._start_bankroll * Decimal(str(self.stop_bankroll_ratio))

    def _drawdown_floor(self) -> Decimal:
        return self._start_bankroll * Decimal(str(1.0 - self.drawdown_threshold))
