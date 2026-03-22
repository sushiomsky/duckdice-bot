"""Roll Hunt Contest Strategy — targets the 9990-9999 range for contest wins.

The DuckDice Roll Hunt contest rewards players who land in a specific
high-number range (9990-9999). This strategy uses normal dice at 5% chance
(bet high) with small bet sizes (1/300 of bankroll) to sustain long sessions.

Win-streak multiplier:
  After each consecutive win the bet size is multiplied by a configurable
  factor (e.g. ×4, ×2, ×1.5).  Any loss resets to base bet.
  Example with hit_multipliers="4,2":  base 1 → win → 4 → win → 8 → loss → 1

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
BET_FRACTION = 1 / 400


@register("roll-hunt")
class RollHuntStrategy:
    """Normal-dice strategy for Roll Hunt contests."""

    @classmethod
    def name(cls) -> str:
        return "roll-hunt"

    @classmethod
    def describe(cls) -> str:
        return (
            "Roll Hunt contest strategy — bets normal dice at 5% chance (high) "
            "targeting 9990-9999. Pauses on contest hit. Prints all 9990+ hashes."
        )

    @classmethod
    def metadata(cls) -> dict:
        return {"category": "contest", "risk": "low", "game": "dice"}

    @classmethod
    def schema(cls) -> dict:
        return {
            "bet_fraction": {
                "type": "float",
                "default": BET_FRACTION,
                "min": 0.0001,
                "max": 0.1,
                "desc": "Fraction of bankroll per bet (default: 1/400)",
            },
            "win_chance": {
                "type": "str",
                "default": "5",
                "desc": "Dice win chance percentage (default: 5)",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet high if True, bet low if False",
            },
            "hit_multipliers": {
                "type": "str",
                "default": "4,2",
                "desc": (
                    "Comma-separated multipliers on consecutive wins. "
                    "E.g. '4,2' → base×4 on 1st win, ×2 on 2nd. "
                    "'0' to disable."
                ),
            },
            "max_streak_bet_fraction": {
                "type": "float",
                "default": 0.1,
                "min": 0.001,
                "max": 0.5,
                "desc": (
                    "Hard cap: multiplied bet cannot exceed this fraction "
                    "of bankroll (default: 10%)"
                ),
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.bet_fraction = float(params.get("bet_fraction", BET_FRACTION))
        self.win_chance = str(params.get("win_chance", "5"))
        self.is_high = bool(params.get("is_high", True))
        self.max_streak_bet_fraction = float(
            params.get("max_streak_bet_fraction", 0.1)
        )

        # Parse hit multipliers
        raw_mult = params.get("hit_multipliers", "4,2")
        self.hit_multipliers = self._parse_multipliers(raw_mult)

        self._total_bets = 0
        self._wins = 0
        self._losses = 0
        self._contest_hits: List[Dict[str, Any]] = []  # bets landing 9990+
        self._hit_target = False
        self._current_balance = Decimal("0")
        self._starting_balance = Decimal("0")

        # Win-streak multiplier state
        self._win_streak = 0
        self._base_bet = Decimal("0")
        self._multiplied_bet = Decimal("0")

    @staticmethod
    def _parse_multipliers(raw: Any) -> List[float]:
        """Parse a comma-separated string or list into multiplier floats."""
        if isinstance(raw, (list, tuple)):
            return [float(v) for v in raw if float(v) > 0]
        if isinstance(raw, (int, float)):
            return [float(raw)] if float(raw) > 0 else []
        raw = str(raw).strip()
        if not raw or raw == "0":
            return []
        parts = [s.strip() for s in raw.split(",") if s.strip()]
        result = []
        for p in parts:
            try:
                v = float(p)
                if v > 0:
                    result.append(v)
            except ValueError:
                continue
        return result

    def on_session_start(self) -> None:
        bal_str = self.ctx.current_balance_str()
        self._current_balance = Decimal(bal_str) if bal_str != "0" else Decimal(self.ctx.starting_balance)
        self._starting_balance = self._current_balance

        mult_str = " → ".join(f"×{m:g}" for m in self.hit_multipliers) if self.hit_multipliers else "OFF"
        direction = "HIGH" if self.is_high else "LOW"
        self.ctx.printer(
            f"[roll-hunt] 🎯 Contest mode started\n"
            f"  Balance:    {self._current_balance:.8f} {self.ctx.symbol}\n"
            f"  Bet size:   1/{int(1/self.bet_fraction)} of bankroll\n"
            f"  Dice:       {self.win_chance}% chance — {direction}\n"
            f"  Target:     {TARGET_LO}-{TARGET_HI}\n"
            f"  Multiplier: {mult_str}  (cap: {self.max_streak_bet_fraction:.0%} of bankroll)"
        )

    def next_bet(self) -> Optional[BetSpec]:
        if self._hit_target:
            return None

        bal = self._current_balance
        if bal <= 0:
            return None

        # Base bet from current bankroll
        base = bal * Decimal(str(self.bet_fraction))
        base = max(base, Decimal("0.00000001"))
        self._base_bet = base

        # Apply win-streak multiplier
        amount = self._apply_streak_multiplier(base, bal)
        self._multiplied_bet = amount

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": self.win_chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _apply_streak_multiplier(self, base: Decimal, bankroll: Decimal) -> Decimal:
        """Scale bet up based on consecutive win streak."""
        if not self.hit_multipliers or self._win_streak == 0:
            return base

        amount = base
        depth = min(self._win_streak, len(self.hit_multipliers))
        for i in range(depth):
            amount *= Decimal(str(self.hit_multipliers[i]))

        # Hard cap: never exceed max_streak_bet_fraction of bankroll
        cap = bankroll * Decimal(str(self.max_streak_bet_fraction))
        if amount > cap:
            amount = cap

        return max(amount, Decimal("0.00000001"))

    def on_bet_result(self, result: BetResult) -> None:
        self._total_bets += 1
        number = result.get("number", -1)
        win = result.get("win", False)

        if win:
            self._wins += 1
            self._win_streak += 1
            if self.hit_multipliers and self._win_streak > 0:
                depth = min(self._win_streak, len(self.hit_multipliers))
                mult_label = "×".join(f"{self.hit_multipliers[i]:g}" for i in range(depth))
                self.ctx.printer(
                    f"  🔥 Win streak {self._win_streak}! "
                    f"Multiplier chain: {mult_label}  "
                    f"(next bet ≈ {self._multiplied_bet:.8f})"
                )
        else:
            if self._win_streak > 0 and self.hit_multipliers:
                self.ctx.printer(
                    f"  ↩ Streak broken at {self._win_streak}. Reset to base bet."
                )
            self._losses += 1
            self._win_streak = 0

        try:
            self._current_balance = Decimal(str(result.get("balance", "0")))
        except Exception:
            pass

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

        # Log near-misses (9990+) that weren't contest-winning
        elif number is not None and number >= TARGET_LO:
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
