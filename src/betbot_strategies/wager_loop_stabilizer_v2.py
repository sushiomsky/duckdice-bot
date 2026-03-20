from __future__ import annotations
"""
Wager Loop Stabilizer V2
========================
Zone-based wager-focused strategy prioritizing bankroll survival and session
length over profit extraction.

Priority:
  SURVIVAL > STABILITY > WAGER > PROFIT
"""

import time
from collections import deque
from decimal import Decimal, getcontext
from typing import Any, Deque, Dict, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

getcontext().prec = 28


@register("wager-loop-stabilizer-v2")
class WagerLoopStabilizerV2:
    """Zone-driven wager grinder with anti-volatility and layered protections."""

    @classmethod
    def name(cls) -> str:
        return "wager-loop-stabilizer-v2"

    @classmethod
    def describe(cls) -> str:
        return (
            "Zone-based survival wager strategy: dynamic sizing by bankroll zone, "
            "anti-volatility dampening and recovery boost."
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
                "Balances wager throughput with longevity focus",
                "Adaptive zone sizing responds to bankroll regime changes",
                "Alternating-pattern dampener reduces churn volatility",
                "No internal lottery logic; works cleanly with engine-level lottery mode",
                "Detailed wager and streak logging for session tuning",
            ],
            cons=[
                "Not tuned for direct profit maximization",
                "Can underperform in strong trending win environments",
                "Low-zone exposure still carries meaningful risk",
                "Recovery boost can increase short-term variance",
                "Requires discipline to respect stop floor behavior",
            ],
            best_use_case=(
                "Long wagering sessions where maintaining bankroll runway and "
                "accumulating large total wager are primary objectives."
            ),
            tips=[
                "Use stable speed settings to reduce execution noise",
                "Keep base factors near defaults for balanced oscillation",
                "Monitor average bet vs bankroll to avoid creeping risk",
                "If sessions end too quickly, lower low-zone factor ceiling",
                "If wagering is too slow, increase mid-zone factor modestly",
                "Enable --lottery at engine level for periodic low-chance shots",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "win_chance": {
                "type": "str",
                "default": "49.5",
                "desc": "Dice chance percentage",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet high if True, low otherwise",
            },
            "mid_factor_min": {
                "type": "float",
                "default": 0.04,
                "desc": "MID zone min bankroll fraction",
            },
            "mid_factor_max": {
                "type": "float",
                "default": 0.06,
                "desc": "MID zone max bankroll fraction",
            },
            "high_factor_min": {
                "type": "float",
                "default": 0.02,
                "desc": "HIGH zone min bankroll fraction",
            },
            "high_factor_max": {
                "type": "float",
                "default": 0.03,
                "desc": "HIGH zone max bankroll fraction",
            },
            "low_factor_min": {
                "type": "float",
                "default": 0.02,
                "desc": "LOW zone min bankroll fraction",
            },
            "low_factor_max": {
                "type": "float",
                "default": 0.04,
                "desc": "LOW zone max bankroll fraction",
            },
            "mid_multiplier": {
                "type": "float",
                "default": 1.35,
                "desc": "MID zone ladder multiplier",
            },
            "high_multiplier": {
                "type": "float",
                "default": 1.2,
                "desc": "HIGH zone flattening multiplier (no ladder)",
            },
            "low_multiplier": {
                "type": "float",
                "default": 1.25,
                "desc": "LOW zone ladder multiplier",
            },
            "mid_ladder_depth": {
                "type": "int",
                "default": 2,
                "desc": "MID zone max ladder depth",
            },
            "low_ladder_depth": {
                "type": "int",
                "default": 2,
                "desc": "LOW zone max ladder depth",
            },
            "loss_streak_threshold": {
                "type": "int",
                "default": 2,
                "desc": "LOW zone threshold to apply loss reduction",
            },
            "loss_reduction_factor": {
                "type": "float",
                "default": 0.7,
                "desc": "LOW zone reduction when loss streak threshold hit",
            },
            "alternating_reduction": {
                "type": "float",
                "default": 0.75,
                "desc": "Bet multiplier under WLWLWL anti-volatility pattern",
            },
            "recovery_trigger_ratio": {
                "type": "float",
                "default": 0.9,
                "desc": "Enable recovery boost below this bankroll ratio",
            },
            "recovery_boost": {
                "type": "float",
                "default": 1.12,
                "desc": "Recovery multiplier (1.10-1.15 recommended)",
            },
            "history_window": {
                "type": "int",
                "default": 10,
                "desc": "Recent result history length",
            },
            "min_amount": {
                "type": "str",
                "default": "0.000001",
                "desc": "Absolute minimum bet amount",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.win_chance = str(params.get("win_chance", "49.5"))
        self.is_high = bool(params.get("is_high", True))

        self.mid_factor_min = float(params.get("mid_factor_min", 0.04))
        self.mid_factor_max = float(params.get("mid_factor_max", 0.06))
        self.high_factor_min = float(params.get("high_factor_min", 0.02))
        self.high_factor_max = float(params.get("high_factor_max", 0.03))
        self.low_factor_min = float(params.get("low_factor_min", 0.02))
        self.low_factor_max = float(params.get("low_factor_max", 0.04))

        self.mid_multiplier = float(params.get("mid_multiplier", 1.35))
        self.high_multiplier = float(params.get("high_multiplier", 1.2))
        self.low_multiplier = float(params.get("low_multiplier", 1.25))
        self.mid_ladder_depth = max(1, int(params.get("mid_ladder_depth", 2)))
        self.low_ladder_depth = max(1, int(params.get("low_ladder_depth", 2)))

        self.loss_streak_threshold = max(1, int(params.get("loss_streak_threshold", 2)))
        self.loss_reduction_factor = float(params.get("loss_reduction_factor", 0.7))

        self.alternating_reduction = float(params.get("alternating_reduction", 0.75))
        self.recovery_trigger_ratio = float(params.get("recovery_trigger_ratio", 0.9))
        self.recovery_boost = float(params.get("recovery_boost", 1.12))

        self.history_window = max(4, int(params.get("history_window", 10)))
        self.min_amount = Decimal(str(params.get("min_amount", "0.000001")))

        self._start_bankroll = Decimal("0")
        self._bankroll = Decimal("0")
        self._zone = "MID"
        self._win_streak = 0
        self._loss_streak = 0
        self._roll_history: Deque[bool] = deque(maxlen=self.history_window)
        self._ladder_step = 0
        self._total_wager = Decimal("0")
        self._bets_count = 0
        self._last_bet_amount = Decimal("0")
        self._session_started_at = 0.0
        self._should_stop = False

    def on_session_start(self) -> None:
        self.initialize(float(self._current_bankroll()))
        self.ctx.printer(
            "[wls-v2] session started | "
            f"bankroll={self._bankroll:.8f} stop_when_empty=True"
        )

    def on_session_end(self, reason: str) -> None:
        self.ctx.printer(
            "[wls-v2] session ended | "
            f"reason={reason} bankroll={self._bankroll:.8f} "
            f"total_wager={self._total_wager:.8f} bets={self._bets_count} "
            f"avg_bet={self.average_bet_size():.8f} duration_sec={self.session_duration():.2f}"
        )

    def initialize(self, start_bankroll: float) -> None:
        self._start_bankroll = Decimal(str(start_bankroll))
        self._bankroll = self._start_bankroll
        self._zone = "MID"
        self._win_streak = 0
        self._loss_streak = 0
        self._roll_history = deque(maxlen=self.history_window)
        self._ladder_step = 0
        self._total_wager = Decimal("0")
        self._bets_count = 0
        self._last_bet_amount = Decimal("0")
        self._session_started_at = time.time()
        self._should_stop = False

    def next_bet(self) -> Optional[BetSpec]:
        if self.should_stop():
            return None

        bankroll = self._current_bankroll()
        self._zone = self._resolve_zone(bankroll)
        dynamic_factor = self._dynamic_factor(self._zone, bankroll)
        amount = bankroll * Decimal(str(dynamic_factor))

        multiplier, ladder_depth = self._zone_multiplier_and_depth(self._zone)
        amount *= Decimal(str(multiplier)) ** self._ladder_step

        if self._zone == "LOW" and self._loss_streak >= self.loss_streak_threshold:
            amount *= Decimal(str(self.loss_reduction_factor))

        if self._is_alternating_pattern():
            amount *= Decimal(str(self.alternating_reduction))

        if bankroll < self._start_bankroll * Decimal(str(self.recovery_trigger_ratio)):
            amount *= Decimal(str(self.recovery_boost))

        amount = self._clamp_bet(amount, bankroll)
        self._last_bet_amount = amount
        self.ctx.printer(
            "[wls-v2] "
            f"zone={self._zone} bankroll={bankroll:.8f} bet={amount:.8f} "
            f"total_wager={self._total_wager:.8f} win_streak={self._win_streak} "
            f"loss_streak={self._loss_streak} ladder={self._ladder_step + 1}/{ladder_depth}"
        )
        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.win_chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def get_next_bet(self) -> float:
        spec = self.next_bet()
        return float(spec["amount"]) if spec else 0.0

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)
        self._bets_count += 1
        self._total_wager += self._last_bet_amount
        try:
            self._bankroll = Decimal(str(result.get("balance", self._bankroll)))
        except Exception:
            pass

        win = bool(result.get("win", False))
        self._roll_history.append(win)
        self._zone = self._resolve_zone(self._bankroll)

        if win:
            self._win_streak += 1
            self._loss_streak = 0
            _, depth = self._zone_multiplier_and_depth(self._zone)
            if depth <= 1:
                self._ladder_step = 0
            elif self._ladder_step + 1 >= depth:
                self._ladder_step = 0
            else:
                self._ladder_step += 1
        else:
            self._win_streak = 0
            self._loss_streak += 1
            self._ladder_step = 0

        self._should_stop = self._bankroll <= Decimal("0")

    def on_roll_result(self, win: bool) -> None:
        bet = self._last_bet_amount if self._last_bet_amount > 0 else self.min_amount
        if win:
            p = max(0.0001, min(0.9999, float(Decimal(self.win_chance) / Decimal("100"))))
            payout = Decimal(str(0.99 / p))
            profit = bet * (payout - Decimal("1"))
        else:
            profit = -bet
        self.on_bet_result({"win": win, "balance": str(self._bankroll + profit)})

    def should_stop(self) -> bool:
        return self._should_stop or self._current_bankroll() <= Decimal("0")

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

    def _resolve_zone(self, bankroll: Decimal) -> str:
        if bankroll > self._start_bankroll * Decimal("1.2"):
            return "HIGH"
        if bankroll < self._start_bankroll * Decimal("0.8"):
            return "LOW"
        return "MID"

    def _dynamic_factor(self, zone: str, bankroll: Decimal) -> float:
        if self._start_bankroll <= 0:
            return self.mid_factor_min
        ratio = float(bankroll / self._start_bankroll)
        if zone == "HIGH":
            span = self.high_factor_max - self.high_factor_min
            mapped = self.high_factor_max - min(1.0, max(0.0, ratio - 1.2)) * span
            return max(self.high_factor_min, min(self.high_factor_max, mapped))
        if zone == "LOW":
            # lower bankroll => closer to low_factor_min; near 0.8 => closer to max
            rel = min(1.0, max(0.0, ratio / 0.8))
            mapped = self.low_factor_min + rel * (self.low_factor_max - self.low_factor_min)
            return max(self.low_factor_min, min(self.low_factor_max, mapped))
        # MID: linear from min at 0.8 to max at 1.2
        rel = min(1.0, max(0.0, (ratio - 0.8) / 0.4))
        mapped = self.mid_factor_min + rel * (self.mid_factor_max - self.mid_factor_min)
        return max(self.mid_factor_min, min(self.mid_factor_max, mapped))

    def _zone_multiplier_and_depth(self, zone: str) -> tuple[float, int]:
        if zone == "HIGH":
            return self.high_multiplier, 1
        if zone == "LOW":
            return self.low_multiplier, self.low_ladder_depth
        return self.mid_multiplier, self.mid_ladder_depth

    def _is_alternating_pattern(self) -> bool:
        # Detect trailing WLWLWL / LWLWLW (length 6) pattern.
        if len(self._roll_history) < 6:
            return False
        tail = list(self._roll_history)[-6:]
        return all(tail[i] != tail[i - 1] for i in range(1, len(tail)))

    def _clamp_bet(self, amount: Decimal, bankroll: Decimal) -> Decimal:
        if bankroll <= 0:
            return Decimal("0")
        capped = min(amount, bankroll)
        if bankroll >= self.min_amount:
            capped = max(self.min_amount, capped)
        else:
            capped = bankroll
        return capped
