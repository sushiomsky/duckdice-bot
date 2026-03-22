from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from betbot_engine.strategy_manager import BaseStrategy, MultiStrategyConfig


class AdaptiveHuntStrategy(BaseStrategy):
    FARM = "FARM"
    PRE_HUNT = "PRE_HUNT"
    HUNT = "HUNT"
    SNIPE = "SNIPE"

    _STATE_CHANCES = {
        FARM: Decimal("1.0"),
        PRE_HUNT: Decimal("0.5"),
        HUNT: Decimal("0.1"),
        SNIPE: Decimal("0.01"),
    }

    def __init__(self, config: MultiStrategyConfig) -> None:
        self._config = config
        self._losing_streak = 0
        self.current_state = self.FARM
        self.snipe_counter = 0

    @property
    def name(self) -> str:
        return "adaptive-hunt"

    @property
    def state(self) -> str:
        return self.current_state

    @property
    def losing_streak(self) -> int:
        return self._losing_streak

    def _refresh_state(self) -> None:
        if self.current_state == self.SNIPE and self.snipe_counter >= 5:
            self._losing_streak = 0
            self.snipe_counter = 0
            self.current_state = self.FARM
            return
        if self._losing_streak >= 250:
            self.current_state = self.SNIPE
        elif self._losing_streak >= 120:
            self.current_state = self.HUNT
        elif self._losing_streak >= 50:
            self.current_state = self.PRE_HUNT
        else:
            self.current_state = self.FARM

    def get_bet(self, bankroll: Decimal) -> tuple[Decimal, Decimal]:
        self._refresh_state()
        base_bet = bankroll * self._config.base_bet_percent
        amount = base_bet * (Decimal("1") + Decimal(str(self._losing_streak)) * Decimal("0.015"))
        chance = self._STATE_CHANCES[self.current_state]
        if self.current_state == self.SNIPE:
            self.snipe_counter += 1
        return amount, chance

    def on_win(self) -> None:
        self._losing_streak = 0
        self.current_state = self.FARM
        self.snipe_counter = 0

    def on_loss(self) -> None:
        self._losing_streak += 1
        self._refresh_state()

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.current_state,
            "losing_streak": self._losing_streak,
            "snipe_counter": self.snipe_counter,
            "chance": format(self._STATE_CHANCES[self.current_state], "f"),
        }
