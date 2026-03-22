from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from betbot_engine.strategy_manager import StrategyManager
from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata


@register("multi-strategy-system")
class MultiStrategySystem:
    """Manager-backed strategy that switches between grind, recovery, and hunt modes."""

    @classmethod
    def name(cls) -> str:
        return "multi-strategy-system"

    @classmethod
    def describe(cls) -> str:
        return (
            "Automatic multi-strategy manager that rotates between a wager grinder, "
            "high-chance recovery, and adaptive low-chance hunt phases."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium-High",
            bankroll_required="Medium",
            volatility="Variable",
            time_to_profit="Moderate",
            recommended_for="Advanced",
            pros=[
                "Automatic switching between wager, recovery, and hunt modes",
                "Built-in stop-loss floor based on the starting bankroll",
                "Wager-focused optimization prefers safer volume generation",
                "Detailed runtime state for logging and inspection",
                "Works with the existing engine as a single registered strategy",
            ],
            cons=[
                "Contains multiple moving parts and state transitions",
                "Low-chance hunt mode is inherently high variance",
                "Wager focus can still slowly bleed during long neutral sessions",
                "Requires enough bankroll to survive strategy transitions",
            ],
            best_use_case=(
                "Sessions that need automatic tactical switching instead of committing "
                "to a single static strategy profile."
            ),
            tips=[
                "Keep base_bet_percent conservative when enabling wager-focused runs",
                "Use simulation first to inspect switch behavior for your bankroll",
                "Monitor the active state log lines to understand phase transitions",
                "Combine with engine-level max_bets or max_duration if you want hard session limits",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_percent": {
                "type": "float",
                "default": 0.001,
                "desc": "Base bet as a fraction of current bankroll.",
            },
            "max_bet_percent": {
                "type": "float",
                "default": 0.03,
                "desc": "Hard bet cap as a fraction of current bankroll.",
            },
            "stop_loss_percent": {
                "type": "float",
                "default": 0.15,
                "desc": "Stop session once bankroll falls this far below the start.",
            },
            "take_profit_percent": {
                "type": "float",
                "default": 0.30,
                "desc": "Reference take-profit level for state reporting.",
            },
            "loss_trigger": {
                "type": "float",
                "default": 0.05,
                "desc": "Switch to recovery when session profit falls below -this fraction.",
            },
            "profit_trigger": {
                "type": "float",
                "default": 0.10,
                "desc": "Switch to adaptive hunt when session profit rises above this fraction.",
            },
            "wager_focus": {
                "type": "bool",
                "default": True,
                "desc": "Prefer the wager grinder while session profit stays near flat.",
            },
            "bet_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet high if True, low if False.",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.params = params
        self.bet_high = bool(params.get("bet_high", True))
        self.manager = StrategyManager(params, ctx.rng)
        self._session_started = False
        self._last_balance = Decimal(str(ctx.starting_balance or "0"))

    def on_session_start(self) -> None:
        bankroll = self._current_bankroll()
        self._last_balance = bankroll
        self.manager.initialize(bankroll)
        self._session_started = True
        self.ctx.printer(
            "[multi-strategy-system] session started | "
            f"bankroll={bankroll:.8f} stop_floor={self._stop_floor():.8f}"
        )

    def next_bet(self) -> Optional[BetSpec]:
        if not self._session_started:
            self.on_session_start()
        bankroll = self._current_bankroll()
        self.manager.update_bankroll(bankroll)
        if self.manager.should_stop():
            self.ctx.printer(
                "[multi-strategy-system] stop-loss reached | "
                f"bankroll={bankroll:.8f} floor={self._stop_floor():.8f}"
            )
            return None

        amount, chance = self.manager.get_bet(bankroll)
        snapshot = self.manager.snapshot()
        self.ctx.printer(
            "[multi-strategy-system] "
            f"strategy={snapshot['active_strategy']} "
            f"state={snapshot['active_state']} "
            f"losing_streak={snapshot['losing_streak']} "
            f"bet={Decimal(snapshot['last_bet_amount']):.8f} "
            f"chance={Decimal(snapshot['last_chance']):.4f} "
            f"profit_pct={snapshot['profit_percent_display']:.4f} "
            f"wagered_total={Decimal(snapshot['wagered_total']):.8f}"
        )
        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": format(chance, "f"),
            "is_high": self.bet_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        balance = Decimal(str(result.get("balance", self._current_bankroll())))
        self._last_balance = balance
        self.manager.record_result(bool(result.get("win", False)), balance)

    def on_session_end(self, reason: str) -> None:
        snapshot = self.manager.snapshot()
        self.ctx.printer(
            "[multi-strategy-system] session ended | "
            f"reason={reason} strategy={snapshot['active_strategy']} "
            f"profit_pct={snapshot['profit_percent_display']:.4f} "
            f"wagered_total={Decimal(snapshot['wagered_total']):.8f}"
        )

    def get_state(self) -> Dict[str, Any]:
        return self.manager.snapshot()

    def _current_bankroll(self) -> Decimal:
        if self._last_balance > 0:
            return self._last_balance
        balance_str = self.ctx.current_balance_str() or self.ctx.starting_balance or "0"
        try:
            return Decimal(str(balance_str))
        except Exception:
            return Decimal("0")

    def _stop_floor(self) -> Decimal:
        start = Decimal(str(self.ctx.starting_balance or "0"))
        return start * (Decimal("1") - Decimal(str(self.params.get("stop_loss_percent", 0.15))))
