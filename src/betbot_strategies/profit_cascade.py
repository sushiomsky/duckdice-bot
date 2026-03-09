"""
Dynamic Profit Cascade Strategy

12-tier chance cycling that dynamically sizes bets to target a specific
profit percentage of the current balance at each tier. Features:

  • Bet size = target_profit / payout_multiplier
  • Loss recovery: incremental bet increases per tier
  • Balance protection: safe mode when down 20% from session start
  • Moonshot bets every 500 bets (random low-chance, 3% of balance)
  • Cycles through: 50% → 40% → 25% → 20% → 14% → 10% → 5% → 2% → 1%
                   → 0.5% → 0.1% → 0.01% → (repeat)
"""

from __future__ import annotations

import random
from decimal import ROUND_DOWN, Decimal
from typing import Any, Dict, List, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

# ── Constants ────────────────────────────────────────────────────────────────

_HOUSE_EDGE = Decimal("0.99")        # 1% house edge → payout = 99/chance
_MIN_BET = Decimal("0.00000001")
_QUANT = Decimal("0.00000001")

_MOONSHOT_INTERVAL = 500
_MOONSHOT_CHANCES: List[float] = [0.5, 0.1, 0.01]
_MOONSHOT_BET_PCT = Decimal("0.03")  # 3% of balance

_SAFE_DRAWDOWN_THRESHOLD = Decimal("0.20")   # enter safe mode at -20%
_SAFE_MODE_CHANCE = "50"
_SAFE_MODE_BET_PCT = Decimal("0.003")        # 0.3% of balance

# ── Tier table ────────────────────────────────────────────────────────────────
# Each entry: (chance%, target_profit_fraction, max_attempts, loss_increase_fraction)
#   target_profit_fraction: e.g. 0.10 = +10% of balance
#   loss_increase_fraction: added multiplier per loss  (0.12 = +12%)

_TIERS: List[Dict[str, Any]] = [
    {"chance": 50.0,  "target_pct": 0.10,  "max_attempts": 20,   "loss_inc": 0.12},
    {"chance": 40.0,  "target_pct": 0.15,  "max_attempts": 30,   "loss_inc": 0.12},
    {"chance": 25.0,  "target_pct": 0.20,  "max_attempts": 40,   "loss_inc": 0.12},
    {"chance": 20.0,  "target_pct": 0.30,  "max_attempts": 60,   "loss_inc": 0.12},
    {"chance": 14.0,  "target_pct": 0.50,  "max_attempts": 80,   "loss_inc": 0.12},
    {"chance": 10.0,  "target_pct": 1.00,  "max_attempts": 120,  "loss_inc": 0.12},
    {"chance": 5.0,   "target_pct": 2.00,  "max_attempts": 200,  "loss_inc": 0.12},
    {"chance": 2.0,   "target_pct": 3.00,  "max_attempts": 350,  "loss_inc": 0.05},
    {"chance": 1.0,   "target_pct": 5.00,  "max_attempts": 500,  "loss_inc": 0.05},
    {"chance": 0.5,   "target_pct": 7.00,  "max_attempts": 700,  "loss_inc": 0.05},
    {"chance": 0.1,   "target_pct": 9.00,  "max_attempts": 1000, "loss_inc": 0.05},
    {"chance": 0.01,  "target_pct": 10.00, "max_attempts": 2000, "loss_inc": 0.05},
]


def _clamp(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return max(lo, min(value, hi))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANT, rounding=ROUND_DOWN)


# ── Helper classes ────────────────────────────────────────────────────────────

class ChanceManager:
    """Tracks the active chance tier and attempt counter."""

    def __init__(self, start_index: int = 0) -> None:
        self._index: int = max(0, min(start_index, len(_TIERS) - 1))
        self._attempts: int = 0

    def reset(self, start_index: int = 0) -> None:
        self._index = max(0, min(start_index, len(_TIERS) - 1))
        self._attempts = 0

    # ── Tier properties ───────────────────────────────────────────────────

    @property
    def tier(self) -> Dict[str, Any]:
        return _TIERS[self._index]

    @property
    def index(self) -> int:
        return self._index

    @property
    def chance(self) -> float:
        return float(self.tier["chance"])

    @property
    def chance_str(self) -> str:
        c = self.chance
        return str(int(c)) if c == int(c) else str(c)

    @property
    def target_pct(self) -> Decimal:
        return Decimal(str(self.tier["target_pct"]))

    @property
    def max_attempts(self) -> int:
        return int(self.tier["max_attempts"])

    @property
    def loss_inc(self) -> Decimal:
        return Decimal(str(self.tier["loss_inc"]))

    @property
    def payout_multiplier(self) -> Decimal:
        """Net payout = (99 / chance) accounting for 1% house edge."""
        return _HOUSE_EDGE * Decimal("100") / Decimal(str(self.chance))

    # ── Attempt tracking ──────────────────────────────────────────────────

    @property
    def attempts(self) -> int:
        return self._attempts

    def tick(self) -> None:
        """Increment attempt counter."""
        self._attempts += 1

    def exhausted(self) -> bool:
        return self._attempts >= self.max_attempts

    def advance(self) -> None:
        """Move to the next tier (cycles back to 0 after the last)."""
        self._index = (self._index + 1) % len(_TIERS)
        self._attempts = 0


class BetManager:
    """Calculates and adjusts bet sizes for each tier."""

    def __init__(self) -> None:
        self._base: Decimal = _MIN_BET
        self._current: Decimal = _MIN_BET

    def recalculate(
        self, balance: Decimal, target_pct: Decimal, payout: Decimal
    ) -> None:
        """Set base bet = (balance × target_pct) / payout, then reset current."""
        target_profit = balance * target_pct
        raw = target_profit / payout
        self._base = _quantize(_clamp(raw, _MIN_BET, balance))
        self._current = self._base

    def on_loss(self, loss_inc: Decimal) -> None:
        """Increase current bet by loss_inc fraction (e.g. 0.12 = +12%)."""
        self._current = _quantize(self._current * (Decimal("1") + loss_inc))
        self._current = max(self._current, _MIN_BET)

    def reset(self) -> None:
        self._current = self._base

    def clamp(self, balance: Decimal) -> Decimal:
        return _clamp(self._current, _MIN_BET, balance)

    @property
    def current(self) -> Decimal:
        return self._current


class RiskManager:
    """Monitors drawdown and governs safe-mode activation."""

    def __init__(self) -> None:
        self._start: Decimal = Decimal("0")
        self._safe: bool = False

    def set_start(self, balance: Decimal) -> None:
        self._start = balance
        self._safe = False

    def update(self, balance: Decimal) -> None:
        """Re-evaluate safe mode based on current balance."""
        if self._start <= Decimal("0"):
            return
        drawdown = (self._start - balance) / self._start
        if drawdown >= _SAFE_DRAWDOWN_THRESHOLD:
            self._safe = True
        elif self._safe and balance >= self._start:
            # Full recovery required to exit safe mode
            self._safe = False

    @property
    def active(self) -> bool:
        return self._safe

    def safe_bet(self, balance: Decimal) -> Decimal:
        raw = balance * _SAFE_MODE_BET_PCT
        return _quantize(_clamp(raw, _MIN_BET, balance))


class ProfitTracker:
    """Accumulates session statistics."""

    def __init__(self) -> None:
        self._bets: int = 0
        self._wins: int = 0
        self._losses: int = 0
        self._profit: Decimal = Decimal("0")
        self._peak: Decimal = Decimal("0")

    def reset(self, start_balance: Decimal) -> None:
        self._bets = 0
        self._wins = 0
        self._losses = 0
        self._profit = Decimal("0")
        self._peak = start_balance

    def record(self, result: BetResult, balance: Decimal) -> None:
        self._bets += 1
        profit = Decimal(str(result.get("profit", "0")))
        self._profit += profit
        if result.get("win"):
            self._wins += 1
        else:
            self._losses += 1
        if balance > self._peak:
            self._peak = balance

    @property
    def total_bets(self) -> int:
        return self._bets

    @property
    def wins(self) -> int:
        return self._wins

    @property
    def losses(self) -> int:
        return self._losses

    @property
    def net_profit(self) -> Decimal:
        return self._profit

    @property
    def peak(self) -> Decimal:
        return self._peak


class MoonshotManager:
    """Fires a high-stakes low-chance bet every _MOONSHOT_INTERVAL bets."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._last_trigger: int = 0
        self._pending: bool = False

    def reset(self) -> None:
        self._last_trigger = 0
        self._pending = False

    def check(self, total_bets: int) -> None:
        """Call after each recorded bet; sets pending flag when threshold hit."""
        if (
            total_bets > 0
            and total_bets % _MOONSHOT_INTERVAL == 0
            and total_bets != self._last_trigger
        ):
            self._last_trigger = total_bets
            self._pending = True

    @property
    def pending(self) -> bool:
        return self._pending

    def consume(self, balance: Decimal, is_high: bool) -> BetSpec:
        """Return the moonshot BetSpec and clear the pending flag."""
        self._pending = False
        chance = self._rng.choice(_MOONSHOT_CHANCES)
        chance_str = str(chance) if chance != int(chance) else str(int(chance))
        bet = _quantize(_clamp(balance * _MOONSHOT_BET_PCT, _MIN_BET, balance))
        return {
            "game": "dice",
            "amount": format(bet, "f"),
            "chance": chance_str,
            "is_high": is_high,
        }


# ── Main strategy class ───────────────────────────────────────────────────────

@register("profit-cascade")
class ProfitCascade:
    """
    Dynamic Profit Cascade: 12-tier chance cycling with balance-relative
    profit targeting, loss recovery, safe mode, and moonshot bets.
    """

    @classmethod
    def name(cls) -> str:
        return "profit-cascade"

    @classmethod
    def describe(cls) -> str:
        return (
            "12-tier chance cycling (50%→0.01%) with dynamic bet sizing that "
            "targets +10% to +1000% of balance per tier. Includes loss recovery, "
            "20%-drawdown safe mode, and moonshot bets every 500 bets."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Large",
            volatility="High",
            time_to_profit="Slow",
            recommended_for="Experts",
            pros=[
                "Dynamically sizes bets relative to current balance",
                "Targets large profit multipliers at low-chance tiers",
                "Automatic safe mode prevents catastrophic loss",
                "Moonshot bets provide occasional high-payout opportunities",
                "Cycles through 12 tiers for varied play",
            ],
            cons=[
                "High variance — extended losing streaks possible at low tiers",
                "Requires a large bankroll to sustain low-chance tier sequences",
                "Long sessions may be needed before a full cycle completes",
            ],
            best_use_case=(
                "Large bankroll seeking high-upside variance play with built-in "
                "drawdown protection."
            ),
            tips=[
                "Start with start_tier=0 (50%) to build balance before descending",
                "Monitor safe mode frequency — frequent activation signals too small a bankroll",
                "Moonshots at 0.01% have ~9900× payout; 3% of balance is the stake",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "start_tier": {
                "type": "int",
                "default": 0,
                "desc": "Starting tier index (0=50%, 11=0.01%)",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet direction: True=High, False=Low",
            },
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self._is_high: bool = bool(params.get("is_high", True))
        start_tier: int = int(params.get("start_tier", 0))

        self._chance_mgr = ChanceManager(start_index=start_tier)
        self._bet_mgr = BetManager()
        self._risk_mgr = RiskManager()
        self._profit_tracker = ProfitTracker()
        self._moonshot_mgr = MoonshotManager(rng=ctx.rng)

        self._balance: Decimal = Decimal(str(ctx.starting_balance))
        self._start_tier: int = start_tier

    def on_session_start(self) -> None:
        self._balance = Decimal(str(self.ctx.starting_balance))
        self._chance_mgr.reset(self._start_tier)
        self._risk_mgr.set_start(self._balance)
        self._profit_tracker.reset(self._balance)
        self._moonshot_mgr.reset()
        self._recalc_base_bet()

    def next_bet(self) -> Optional[BetSpec]:
        self._sync_balance()

        if self._balance <= _MIN_BET:
            return None

        # ── Safe mode overrides everything except moonshots ───────────────
        if self._risk_mgr.active:
            safe_amount = self._risk_mgr.safe_bet(self._balance)
            return {
                "game": "dice",
                "amount": format(safe_amount, "f"),
                "chance": _SAFE_MODE_CHANCE,
                "is_high": self._is_high,
                "faucet": self.ctx.faucet,
            }

        # ── Pending moonshot ──────────────────────────────────────────────
        if self._moonshot_mgr.pending:
            spec = self._moonshot_mgr.consume(self._balance, self._is_high)
            spec["faucet"] = self.ctx.faucet
            return spec

        # ── Normal tier bet ───────────────────────────────────────────────
        amount = self._bet_mgr.clamp(self._balance)
        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self._chance_mgr.chance_str,
            "is_high": self._is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        bal_str = result.get("balance")
        if bal_str is not None:
            self._balance = Decimal(str(bal_str))

        self._profit_tracker.record(result, self._balance)
        self.ctx.recent_results.append(result)

        # Update safe-mode status
        self._risk_mgr.update(self._balance)

        # Queue moonshot if threshold reached
        self._moonshot_mgr.check(self._profit_tracker.total_bets)

        # Skip tier logic while in safe mode or after a moonshot bet
        if self._risk_mgr.active:
            return

        win = bool(result.get("win"))

        if win:
            # Advance to next tier, recalculate bet for new balance
            self._chance_mgr.advance()
            self._recalc_base_bet()
        else:
            self._chance_mgr.tick()
            self._bet_mgr.on_loss(self._chance_mgr.loss_inc)

            # Tier exhausted without a win — move on anyway
            if self._chance_mgr.exhausted():
                self._chance_mgr.advance()
                self._recalc_base_bet()

    def on_session_end(self, reason: str) -> None:
        pass

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _sync_balance(self) -> None:
        """Pull the most recent balance from result history."""
        if self.ctx.recent_results:
            bal_str = self.ctx.recent_results[-1].get("balance")
            if bal_str is not None:
                self._balance = Decimal(str(bal_str))

    def _recalc_base_bet(self) -> None:
        """Recalculate base bet for the current tier and current balance."""
        self._bet_mgr.recalculate(
            self._balance,
            self._chance_mgr.target_pct,
            self._chance_mgr.payout_multiplier,
        )
