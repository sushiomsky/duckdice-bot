from __future__ import annotations
"""
Base types and protocols for auto-betting strategies.

No third-party dependencies are used so that the core remains lightweight.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, Optional, Protocol, TypedDict, Literal
from collections import deque
import random
import time
from decimal import Decimal

from duckdice_api.api import DuckDiceAPI


class BetSpec(TypedDict, total=False):
    """Normalized bet specification emitted by strategies.
    - For Original Dice specify: game="dice", chance (str), is_high (bool)
    - For Range Dice specify: game="range-dice", range=(min, max), is_in (bool)
    - Always specify: amount (str)
    """
    game: Literal["dice", "range-dice"]
    amount: str
    # Dice
    chance: str
    is_high: bool
    # Range Dice
    range: tuple[int, int]
    is_in: bool
    # Optional passthrough
    faucet: bool


class BetResult(TypedDict, total=False):
    """Canonicalized bet result passed back to strategies and logger."""
    win: bool
    profit: str
    balance: str
    number: int
    payout: str
    chance: str
    is_high: Optional[bool]
    range: Optional[tuple[int, int]]
    is_in: Optional[bool]
    api_raw: Dict[str, Any]
    simulated: bool
    timestamp: float


@dataclass
class SessionLimits:
    symbol: str
    stop_loss: float = -0.02      # -2% of starting balance
    take_profit: float = 0.02     # +2%
    max_bet: Optional[Decimal] = None  # absolute max amount in currency units
    max_bets: Optional[int] = None
    max_losses: Optional[int] = None
    max_duration_sec: Optional[int] = None


@dataclass
class StrategyContext:
    api: DuckDiceAPI
    symbol: str
    faucet: bool
    dry_run: bool
    rng: random.Random
    logger: Callable[[Dict[str, Any]], None]
    limits: SessionLimits
    delay_ms: int = 750
    jitter_ms: int = 500
    recent_results: Deque[BetResult] = field(default_factory=lambda: deque(maxlen=256))
    starting_balance: str = "0"

    def sleep_with_jitter(self):
        base = max(0, self.delay_ms) / 1000.0
        jitter = self.rng.uniform(0, max(0, self.jitter_ms) / 1000.0)
        time.sleep(base + jitter)

    def current_balance_str(self) -> str:
        """Return the latest known balance as a decimal string.
        Uses the most recent result if available, otherwise the starting balance.
        """
        if self.recent_results:
            last = self.recent_results[-1]
            bal = str(last.get("balance", self.starting_balance))
            return bal
        return self.starting_balance


@dataclass
class StrategyMetadata:
    """Rich metadata for strategy display in GUI."""
    risk_level: str  # "Low", "Medium", "High", "Very High"
    bankroll_required: str  # "Small", "Medium", "Large", "Very Large"
    volatility: str  # "Low", "Medium", "High"
    time_to_profit: str  # "Quick", "Moderate", "Slow"
    recommended_for: str  # "Beginners", "Intermediate", "Advanced", "Experts"
    pros: list[str]
    cons: list[str]
    best_use_case: str
    tips: list[str]


class AutoBetStrategy(Protocol):
    """Protocol all strategies must implement."""

    @classmethod
    def name(cls) -> str: ...

    @classmethod
    def describe(cls) -> str: ...

    @classmethod
    def metadata(cls) -> StrategyMetadata: ...

    @classmethod
    def schema(cls) -> Dict[str, Any]: ...

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None: ...

    def on_session_start(self) -> None: ...

    def next_bet(self) -> Optional[BetSpec]: ...

    def on_bet_result(self, result: BetResult) -> None: ...

    def on_session_end(self, reason: str) -> None: ...
