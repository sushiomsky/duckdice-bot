from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Any, Dict, Optional
import random


_DECIMAL_EIGHT_PLACES = Decimal("0.00000001")
_MIN_BET_AMOUNT = Decimal("0.00000001")
_SAFE_WAGER_BOOST = Decimal("1.05")


class BaseStrategy(ABC):
    """Minimal interface used by the multi-strategy manager."""

    @abstractmethod
    def get_bet(self, bankroll: Decimal) -> tuple[Decimal, Decimal]:
        raise NotImplementedError

    @abstractmethod
    def on_win(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def on_loss(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    def state(self) -> str:
        return self.name

    @property
    def losing_streak(self) -> int:
        return 0

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "losing_streak": self.losing_streak,
        }


@dataclass(frozen=True)
class StrategySwitchConfig:
    loss_trigger: Decimal
    profit_trigger: Decimal
    wager_focus: bool = True


@dataclass(frozen=True)
class MultiStrategyConfig:
    base_bet_percent: Decimal
    max_bet_percent: Decimal
    stop_loss_percent: Decimal
    take_profit_percent: Decimal
    strategy_switch: StrategySwitchConfig

    @classmethod
    def from_params(cls, params: Dict[str, Any]) -> "MultiStrategyConfig":
        def dec(key: str, default: str) -> Decimal:
            value = params.get(key, default)
            try:
                return Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError(f"Invalid decimal value for {key}: {value}") from exc

        return cls(
            base_bet_percent=dec("base_bet_percent", "0.001"),
            max_bet_percent=dec("max_bet_percent", "0.03"),
            stop_loss_percent=dec("stop_loss_percent", "0.15"),
            take_profit_percent=dec("take_profit_percent", "0.30"),
            strategy_switch=StrategySwitchConfig(
                loss_trigger=dec("loss_trigger", "0.05"),
                profit_trigger=dec("profit_trigger", "0.10"),
                wager_focus=bool(params.get("wager_focus", True)),
            ),
        )


class WagerOptimizer:
    """Applies final safety caps and wager-focus tuning to a raw stake."""

    def __init__(self, config: MultiStrategyConfig) -> None:
        self._config = config

    def optimize_amount(
        self,
        strategy_name: str,
        bankroll: Decimal,
        raw_amount: Decimal,
        profit_percent: Decimal,
    ) -> Decimal:
        amount = raw_amount
        if (
            self._config.strategy_switch.wager_focus
            and strategy_name == "wager-grinder"
            and profit_percent > -self._config.strategy_switch.loss_trigger
            and profit_percent < self._config.strategy_switch.profit_trigger
        ):
            amount *= _SAFE_WAGER_BOOST
        return _clamp_amount(amount, bankroll, self._config.max_bet_percent)


class StrategyManager:
    """Coordinates strategy selection, wager tracking, and stop checks."""

    def __init__(self, params: Dict[str, Any], rng: Optional[random.Random] = None) -> None:
        self.config = MultiStrategyConfig.from_params(params)
        self.rng = rng or random.Random()
        self.optimizer = WagerOptimizer(self.config)

        from betbot_strategies.adaptive_hunt import AdaptiveHuntStrategy
        from betbot_strategies.recovery import RecoveryStrategy
        from betbot_strategies.wager_grinder import WagerGrinderStrategy

        self.adaptive_hunt = AdaptiveHuntStrategy(self.config)
        self.wager_grinder = WagerGrinderStrategy(self.config, self.rng)
        self.recovery = RecoveryStrategy(self.config, self.rng)

        self.start_bankroll = Decimal("0")
        self.current_bankroll = Decimal("0")
        self.profit_percent = Decimal("0")
        self.wagered_total = Decimal("0")
        self.last_bet_amount = Decimal("0")
        self.last_chance = Decimal("0")
        self.last_strategy_name = self.wager_grinder.name
        self.last_result_win: Optional[bool] = None
        self._active_strategy: BaseStrategy = self.wager_grinder
        self._bet_strategy: BaseStrategy = self.wager_grinder

    def initialize(self, bankroll: Decimal) -> None:
        normalized = _normalize_decimal(bankroll)
        self.start_bankroll = normalized
        self.current_bankroll = normalized
        self.profit_percent = Decimal("0")
        self.wagered_total = Decimal("0")
        self.last_bet_amount = Decimal("0")
        self.last_chance = Decimal("0")
        self.last_result_win = None
        self._active_strategy = self._select_strategy()
        self._bet_strategy = self._active_strategy
        self.last_strategy_name = self._active_strategy.name

    def update_bankroll(self, bankroll: Decimal) -> None:
        self.current_bankroll = _normalize_decimal(bankroll)
        if self.start_bankroll > 0:
            self.profit_percent = (self.current_bankroll - self.start_bankroll) / self.start_bankroll
        else:
            self.profit_percent = Decimal("0")

    def _select_strategy(self) -> BaseStrategy:
        switch = self.config.strategy_switch
        if self.profit_percent <= -switch.loss_trigger:
            return self.recovery
        if self.profit_percent >= switch.profit_trigger:
            return self.adaptive_hunt
        if switch.wager_focus:
            return self.wager_grinder
        return self.wager_grinder

    def get_active_strategy(self) -> BaseStrategy:
        selected = self._select_strategy()
        self._active_strategy = selected
        return selected

    def get_bet(self, bankroll: Decimal) -> tuple[Decimal, Decimal]:
        self.update_bankroll(bankroll)
        strategy = self.get_active_strategy()
        raw_amount, chance = strategy.get_bet(self.current_bankroll)
        amount = self.optimizer.optimize_amount(
            strategy_name=strategy.name,
            bankroll=self.current_bankroll,
            raw_amount=raw_amount,
            profit_percent=self.profit_percent,
        )
        self.last_bet_amount = amount
        self.last_chance = chance
        self.last_strategy_name = strategy.name
        self._bet_strategy = strategy
        return amount, chance

    def record_result(self, win: bool, bankroll_after: Decimal) -> None:
        self.wagered_total += self.last_bet_amount
        self.last_result_win = win
        if win:
            self._bet_strategy.on_win()
        else:
            self._bet_strategy.on_loss()
        self.update_bankroll(bankroll_after)
        self._active_strategy = self._select_strategy()

    def should_stop(self) -> bool:
        if self.start_bankroll <= 0:
            return False
        stop_floor = self.start_bankroll * (Decimal("1") - self.config.stop_loss_percent)
        return self.current_bankroll <= stop_floor

    def take_profit_reached(self) -> bool:
        if self.start_bankroll <= 0:
            return False
        return self.current_bankroll >= self.start_bankroll * (Decimal("1") + self.config.take_profit_percent)

    @property
    def active_strategy_name(self) -> str:
        return self._active_strategy.name

    @property
    def active_state(self) -> str:
        return self._active_strategy.state

    @property
    def active_losing_streak(self) -> int:
        return self._active_strategy.losing_streak

    def snapshot(self) -> Dict[str, Any]:
        return {
            "start_bankroll": format(self.start_bankroll, "f"),
            "current_bankroll": format(self.current_bankroll, "f"),
            "profit_percent": float(self.profit_percent),
            "profit_percent_display": float(self.profit_percent * Decimal("100")),
            "wagered_total": format(self.wagered_total, "f"),
            "last_bet_amount": format(self.last_bet_amount, "f"),
            "last_chance": format(self.last_chance, "f"),
            "active_strategy": self.active_strategy_name,
            "active_state": self.active_state,
            "losing_streak": self.active_losing_streak,
            "last_result_win": self.last_result_win,
            "stop_loss_triggered": self.should_stop(),
            "take_profit_reached": self.take_profit_reached(),
            "adaptive_hunt": self.adaptive_hunt.get_state(),
            "wager_grinder": self.wager_grinder.get_state(),
            "recovery": self.recovery.get_state(),
        }


def _normalize_decimal(value: Decimal | str | float | int) -> Decimal:
    normalized = Decimal(str(value))
    return normalized if normalized > 0 else Decimal("0")


def _clamp_amount(amount: Decimal, bankroll: Decimal, max_bet_percent: Decimal) -> Decimal:
    if bankroll <= 0:
        return Decimal("0")
    capped = min(amount, bankroll, bankroll * max_bet_percent)
    floored = max(capped, _MIN_BET_AMOUNT)
    return floored.quantize(_DECIMAL_EIGHT_PLACES, rounding=ROUND_DOWN)
