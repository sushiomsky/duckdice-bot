"""Roll Hunt Contest Strategy — targets the 9990-9999 range for contest wins.

The DuckDice Roll Hunt contest rewards players who land in a specific
high-number range (9990-9999). This strategy uses range-dice at ~5% chance
with small bet sizes (1/300 of bankroll) to sustain long sessions.

On hitting the target range:
  • Prints the winning bet hash immediately
  • Pauses the session

On session end:
  • Prints all bets that landed 9990+ with their hashes and numbers
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .base import BetResult, BetSpec, StrategyContext

_REG: Dict[str, Any] = {}
try:
    from . import register
except ImportError:
    from betbot_strategies import register


TARGET_LO = 9990
TARGET_HI = 9999
BET_FRACTION = 1 / 300
RANGE_WIDTH = 500          # 500 slots out of 10000 → 5% chance


@register("roll-hunt")
class RollHuntStrategy:
    """Adaptive range-dice strategy for Roll Hunt contests."""

    @classmethod
    def name(cls) -> str:
        return "roll-hunt"

    @classmethod
    def describe(cls) -> str:
        return (
            "Roll Hunt contest strategy — bets range-dice at ~5% chance "
            "targeting 9990-9999. Pauses on contest hit. Prints all 9990+ hashes."
        )

    @classmethod
    def metadata(cls) -> dict:
        return {"category": "contest", "risk": "low", "game": "range-dice"}

    @classmethod
    def schema(cls) -> list:
        return [
            {
                "key": "bet_fraction",
                "type": "float",
                "default": BET_FRACTION,
                "min": 0.0001,
                "max": 0.1,
                "description": "Fraction of bankroll per bet (default: 1/300)",
            },
            {
                "key": "range_lo",
                "type": "int",
                "default": 9500,
                "min": 0,
                "max": 9999,
                "description": "Lower bound of the betting range (default: 9500)",
            },
            {
                "key": "range_hi",
                "type": "int",
                "default": 9999,
                "min": 0,
                "max": 9999,
                "description": "Upper bound of the betting range (default: 9999)",
            },
            {
                "key": "adaptive",
                "type": "bool",
                "default": True,
                "description": "Shift range toward recent hot zones",
            },
        ]

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.bet_fraction = float(params.get("bet_fraction", BET_FRACTION))
        self.range_lo = int(params.get("range_lo", 9500))
        self.range_hi = int(params.get("range_hi", 9999))
        self.adaptive = bool(params.get("adaptive", True))

        self._total_bets = 0
        self._wins = 0
        self._losses = 0
        self._contest_hits: List[Dict[str, Any]] = []  # bets landing 9990+
        self._hit_target = False
        self._current_balance = Decimal("0")
        self._starting_balance = Decimal("0")

        # Adaptive state: track recent roll distribution
        self._recent_rolls: List[int] = []
        self._adaptation_window = 100

    def on_session_start(self) -> None:
        bal_str = self.ctx.current_balance_str()
        self._current_balance = Decimal(bal_str) if bal_str != "0" else Decimal(self.ctx.starting_balance)
        self._starting_balance = self._current_balance

        chance_pct = (self.range_hi - self.range_lo + 1) / 100
        self.ctx.printer(
            f"[roll-hunt] 🎯 Contest mode started\n"
            f"  Balance:    {self._current_balance:.8f} {self.ctx.symbol}\n"
            f"  Bet size:   1/{int(1/self.bet_fraction)} of bankroll\n"
            f"  Range:      {self.range_lo}-{self.range_hi} ({chance_pct:.1f}% chance)\n"
            f"  Target:     {TARGET_LO}-{TARGET_HI}\n"
            f"  Adaptive:   {'ON' if self.adaptive else 'OFF'}"
        )

    def next_bet(self) -> Optional[BetSpec]:
        if self._hit_target:
            return None

        bal = self._current_balance
        if bal <= 0:
            return None

        amount = bal * Decimal(str(self.bet_fraction))
        amount = max(amount, Decimal("0.00000001"))

        lo, hi = self._get_range()

        return {
            "game": "range-dice",
            "amount": format(amount, "f"),
            "range": (lo, hi),
            "is_in": True,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        self._total_bets += 1
        number = result.get("number", -1)
        win = result.get("win", False)

        if win:
            self._wins += 1
        else:
            self._losses += 1

        try:
            self._current_balance = Decimal(str(result.get("balance", "0")))
        except Exception:
            pass

        # Track roll for adaptive shifting
        if number is not None and number >= 0:
            self._recent_rolls.append(number)
            if len(self._recent_rolls) > self._adaptation_window:
                self._recent_rolls = self._recent_rolls[-self._adaptation_window:]

        # Extract bet hash from API response
        api_raw = result.get("api_raw", {})
        bet_data = api_raw.get("bet", {}) if isinstance(api_raw, dict) else {}
        bet_hash = bet_data.get("hash", "N/A")

        # Check for contest hit (9990-9999)
        if number is not None and TARGET_LO <= number <= TARGET_HI:
            hit_info = {
                "number": number,
                "hash": bet_hash,
                "bet_num": self._total_bets,
                "balance": str(self._current_balance),
                "win": win,
                "timestamp": time.time(),
            }
            self._contest_hits.append(hit_info)

            self.ctx.printer(
                f"\n{'🎉' * 10}\n"
                f"  🏆 ROLL HUNT HIT! Number: {number}\n"
                f"  Hash: {bet_hash}\n"
                f"  Bet #{self._total_bets} | Balance: {self._current_balance:.8f}\n"
                f"{'🎉' * 10}\n"
            )
            self._hit_target = True

        # Log near-misses (9990+) that weren't the bet's winning range
        elif number is not None and number >= TARGET_LO and not win:
            hit_info = {
                "number": number,
                "hash": bet_hash,
                "bet_num": self._total_bets,
                "balance": str(self._current_balance),
                "win": win,
                "timestamp": time.time(),
            }
            self._contest_hits.append(hit_info)
            self.ctx.printer(
                f"  📌 Near roll: {number} (hash: {bet_hash}) — bet #{self._total_bets}"
            )

        # Periodic progress
        if self._total_bets % 200 == 0:
            pnl = self._current_balance - self._starting_balance
            sign = "+" if pnl >= 0 else ""
            self.ctx.printer(
                f"  [roll-hunt] bet #{self._total_bets:,}  "
                f"bal={self._current_balance:.8f}  "
                f"PnL={sign}{pnl:.8f}  "
                f"hits={len(self._contest_hits)}"
            )

    def on_session_end(self, reason: str) -> None:
        pnl = self._current_balance - self._starting_balance
        sign = "+" if pnl >= 0 else ""
        total = self._wins + self._losses
        wr = (self._wins / total * 100) if total > 0 else 0

        self.ctx.printer(
            f"\n[roll-hunt] Session ended: {reason}\n"
            f"  Bets:       {self._total_bets:,}\n"
            f"  W/L:        {self._wins}/{self._losses} ({wr:.1f}%)\n"
            f"  PnL:        {sign}{pnl:.8f} {self.ctx.symbol}\n"
            f"  Balance:    {self._current_balance:.8f}"
        )

        if self._contest_hits:
            self.ctx.printer(
                f"\n  🏆 Contest Hits (rolls ≥ {TARGET_LO}): {len(self._contest_hits)}"
            )
            self.ctx.printer(f"  {'─' * 60}")
            self.ctx.printer(f"  {'#':<6} {'Number':>6} {'Win':>4} {'Hash':<40} {'Bet#':>8}")
            self.ctx.printer(f"  {'─' * 60}")
            for i, h in enumerate(self._contest_hits, 1):
                w = "✓" if h["win"] else "✗"
                self.ctx.printer(
                    f"  {i:<6} {h['number']:>6} {w:>4} {h['hash']:<40} #{h['bet_num']:>7,}"
                )
            self.ctx.printer(f"  {'─' * 60}")
        else:
            self.ctx.printer(f"\n  No rolls ≥ {TARGET_LO} recorded this session.")

    # ------------------------------------------------------------------
    # Adaptive range selection
    # ------------------------------------------------------------------

    def _get_range(self) -> tuple:
        """Return (lo, hi) range for the next bet.

        In adaptive mode, shifts the range window toward areas where
        recent rolls have clustered, while always covering 9990-9999.
        """
        if not self.adaptive or len(self._recent_rolls) < 20:
            return (self.range_lo, self.range_hi)

        # Count how many recent rolls landed in the upper half (5000+)
        upper_count = sum(1 for r in self._recent_rolls[-50:] if r >= 5000)
        total = min(len(self._recent_rolls), 50)

        if total == 0:
            return (self.range_lo, self.range_hi)

        upper_ratio = upper_count / total

        # If rolls are clustering high (> 55% in upper half), tighten toward top
        width = self.range_hi - self.range_lo + 1
        if upper_ratio > 0.55:
            # Shift range up — keep hi at 9999, raise lo
            new_lo = max(self.range_lo, 9999 - width + 1)
            return (new_lo, 9999)
        elif upper_ratio < 0.45:
            # Rolls clustering low — widen range a bit to cover more ground
            new_lo = max(0, self.range_lo - 100)
            new_hi = min(9999, new_lo + width - 1 + 100)
            return (new_lo, new_hi)
        else:
            return (self.range_lo, self.range_hi)
