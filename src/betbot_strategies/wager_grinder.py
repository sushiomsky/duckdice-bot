from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict
import random

from betbot_engine.strategy_manager import BaseStrategy, MultiStrategyConfig


class WagerGrinderStrategy(BaseStrategy):
    def __init__(self, config: MultiStrategyConfig, rng: random.Random) -> None:
        self._config = config
        self._rng = rng
        self._losing_streak = 0
        self._last_chance = Decimal("30")

    @property
    def name(self) -> str:
        return "wager-grinder"

    @property
    def state(self) -> str:
        return "GRIND"

    @property
    def losing_streak(self) -> int:
        return self._losing_streak

    def get_bet(self, bankroll: Decimal) -> tuple[Decimal, Decimal]:
        self._last_chance = Decimal(str(round(self._rng.uniform(20.0, 40.0), 4)))
        base_bet = bankroll * self._config.base_bet_percent
        amount = base_bet * Decimal("1.5")
        if self._losing_streak > 0:
            amount *= Decimal("1.1") ** self._losing_streak
        return amount, self._last_chance

    def on_win(self) -> None:
        self._losing_streak = 0

    def on_loss(self) -> None:
        self._losing_streak += 1

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "losing_streak": self._losing_streak,
            "chance": format(self._last_chance, "f"),
        }
