"""Roll Hunt Low Contest Strategy — targets numbers 0-4 at 15% LOW.

The DuckDice Roll Hunt (Low) contest rewards players who land on 0-4 while
betting LOW. This strategy uses 15% chance (bet low) with small bet sizes
(1/400 of bankroll) to sustain long sessions while hunting those rare rolls.

Win-streak multiplier:
  After each consecutive win the bet size is multiplied by a configurable
  factor (e.g. ×4, ×2).  Any loss resets to base bet.
  Example with hit_multipliers="4,2":  base 1 → win → 4 → win → 8 → loss → 1

Leader-beat tracker:
  Set leader_score to the current leader's bet amount at their hit.
  The strategy shows the minimum bet size required to beat them and
  flags every contest hit as winning or losing against the leader.

On hitting the target range (0-4):
  • Prints the winning bet hash immediately
  • Shows whether the bet beats the current leader
  • Pauses the session

On session end:
  • Prints all bets that landed 0-4 with hashes, numbers, bet amounts,
    and leader-beat status
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


TARGET_LO = 0
TARGET_HI = 4
BET_FRACTION = 1 / 400


@register("roll-hunt-low")
class RollHuntLowStrategy:
    """15%-LOW dice strategy for Roll Hunt contests targeting numbers 0-4."""

    @classmethod
    def name(cls) -> str:
        return "roll-hunt-low"

    @classmethod
    def describe(cls) -> str:
        return (
            "Roll Hunt Low contest strategy — bets 15% LOW targeting 0-4. "
            "Pauses on contest hit. Tracks minimum bet needed to beat the leader."
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
                "default": "15",
                "desc": "Dice win chance percentage (default: 15)",
            },
            "is_high": {
                "type": "bool",
                "default": False,
                "desc": "Bet high if True, bet low if False (default: False = LOW)",
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
            "min_bet": {
                "type": "float",
                "default": 0.00000001,
                "min": 0.00000001,
                "desc": (
                    "Minimum absolute bet size in base currency. "
                    "Bet is always max(balance × bet_fraction, min_bet)."
                ),
            },
            "leader_score": {
                "type": "float",
                "default": 0.0,
                "min": 0.0,
                "desc": (
                    "Current leader's bet amount at their contest hit. "
                    "Set this to display minimum bet needed to beat them. "
                    "0 = disabled."
                ),
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.bet_fraction = float(params.get("bet_fraction", BET_FRACTION))
        self.win_chance = str(params.get("win_chance", "15"))
        self.is_high = bool(params.get("is_high", False))
        self.max_streak_bet_fraction = float(
            params.get("max_streak_bet_fraction", 0.1)
        )
        self.min_bet = Decimal(str(params.get("min_bet", "0.00000001")))
        self.leader_score = Decimal(str(params.get("leader_score", "0")))

        raw_mult = params.get("hit_multipliers", "4,2")
        self.hit_multipliers = self._parse_multipliers(raw_mult)

        self._total_bets = 0
        self._wins = 0
        self._losses = 0
        self._contest_hits: List[Dict[str, Any]] = []
        self._current_balance = Decimal("0")
        self._starting_balance = Decimal("0")

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

    def _min_to_beat(self) -> Optional[Decimal]:
        """Minimum bet amount required to beat the leader (leader_score + 1 sat)."""
        if self.leader_score <= 0:
            return None
        return self.leader_score + Decimal("0.00000001")

    def on_session_start(self) -> None:
        bal_str = self.ctx.current_balance_str()
        self._current_balance = (
            Decimal(bal_str) if bal_str != "0" else Decimal(self.ctx.starting_balance)
        )
        self._starting_balance = self._current_balance

        mult_str = (
            " → ".join(f"×{m:g}" for m in self.hit_multipliers)
            if self.hit_multipliers
            else "OFF"
        )
        direction = "HIGH" if self.is_high else "LOW"

        lines = [
            f"[roll-hunt-low] 🎯 Contest mode started",
            f"  Balance:    {self._current_balance:.8f} {self.ctx.symbol}",
            f"  Bet size:   {self.bet_fraction:.4%} of balance  (min: {self.min_bet:.8f} {self.ctx.symbol})",
            f"  Dice:       {self.win_chance}% chance — {direction}",
            f"  Target:     {TARGET_LO}-{TARGET_HI}",
            f"  Multiplier: {mult_str}  (cap: {self.max_streak_bet_fraction:.0%} of bankroll)",
        ]

        min_bet = self._min_to_beat()
        if min_bet is not None:
            lines.append(
                f"  Leader:     {self.leader_score:.8f} {self.ctx.symbol}  "
                f"→  min bet to beat: {min_bet:.8f} {self.ctx.symbol}"
            )

        self.ctx.printer("\n".join(lines))

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._current_balance
        if bal <= 0:
            return None

        base = bal * Decimal(str(self.bet_fraction))
        base = max(base, self.min_bet)
        self._base_bet = base

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

        cap = bankroll * Decimal(str(self.max_streak_bet_fraction))
        if amount > cap:
            amount = cap

        return max(amount, self.min_bet)

    def on_bet_result(self, result: BetResult) -> None:
        self._total_bets += 1
        number = result.get("number", -1)
        win = result.get("win", False)

        if win:
            self._wins += 1
            self._win_streak += 1
            if self.hit_multipliers and self._win_streak > 0:
                depth = min(self._win_streak, len(self.hit_multipliers))
                mult_label = "×".join(
                    f"{self.hit_multipliers[i]:g}" for i in range(depth)
                )
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

        api_raw = result.get("api_raw", {})
        bet_data = api_raw.get("bet", {}) if isinstance(api_raw, dict) else {}
        bet_hash = bet_data.get("hash", "N/A")

        # Contest hit: number landed in 0-4
        if number is not None and TARGET_LO <= number <= TARGET_HI:
            min_bet = self._min_to_beat()
            beats_leader = (
                min_bet is not None and self._multiplied_bet >= min_bet
            )

            hit_info = {
                "number": number,
                "hash": bet_hash,
                "bet_num": self._total_bets,
                "balance": str(self._current_balance),
                "win": win,
                "timestamp": time.time(),
                "bet_amount": str(self._multiplied_bet),
                "beats_leader": beats_leader,
            }
            self._contest_hits.append(hit_info)

            leader_note = ""
            if min_bet is not None:
                if beats_leader:
                    leader_note = (
                        f"\n  🥇 BEATS LEADER!  "
                        f"Bet {self._multiplied_bet:.8f} > {self.leader_score:.8f}"
                    )
                else:
                    gap = self.leader_score - self._multiplied_bet + Decimal("0.00000001")
                    leader_note = (
                        f"\n  ⚠️  Does NOT beat leader  "
                        f"(need {gap:.8f} {self.ctx.symbol} more)"
                    )

            self.ctx.printer(
                f"\n{'🎉' * 10}\n"
                f"  🏆 ROLL HUNT HIT!  Number: {number}\n"
                f"  Hash:        {bet_hash}\n"
                f"  Bet #:       {self._total_bets}\n"
                f"  Bet amount:  {self._multiplied_bet:.8f} {self.ctx.symbol}\n"
                f"  Balance:     {self._current_balance:.8f}"
                f"{leader_note}\n"
                f"{'🎉' * 10}"
            )
            input("  ⏸  PAUSED — Press Enter to continue betting...")

        # Periodic progress report
        if self._total_bets % 200 == 0:
            pnl = self._current_balance - self._starting_balance
            sign = "+" if pnl >= 0 else ""
            min_bet = self._min_to_beat()
            leader_part = (
                f"  | min_to_beat={min_bet:.8f}" if min_bet is not None else ""
            )
            self.ctx.printer(
                f"  [roll-hunt-low] bet #{self._total_bets:,}  "
                f"bal={self._current_balance:.8f}  "
                f"PnL={sign}{pnl:.8f}  "
                f"hits={len(self._contest_hits)}"
                f"{leader_part}"
            )

    def on_session_end(self, reason: str) -> None:
        pnl = self._current_balance - self._starting_balance
        sign = "+" if pnl >= 0 else ""
        total = self._wins + self._losses
        wr = (self._wins / total * 100) if total > 0 else 0

        lines = [
            f"\n[roll-hunt-low] Session ended: {reason}",
            f"  Bets:       {self._total_bets:,}",
            f"  W/L:        {self._wins}/{self._losses} ({wr:.1f}%)",
            f"  PnL:        {sign}{pnl:.8f} {self.ctx.symbol}",
            f"  Balance:    {self._current_balance:.8f}",
        ]
        min_bet = self._min_to_beat()
        if min_bet is not None:
            lines.append(
                f"  Leader:     {self.leader_score:.8f} {self.ctx.symbol}  "
                f"(min to beat: {min_bet:.8f})"
            )
        self.ctx.printer("\n".join(lines))

        if self._contest_hits:
            self.ctx.printer(
                f"\n  🏆 Contest Hits (rolls {TARGET_LO}-{TARGET_HI}): "
                f"{len(self._contest_hits)}"
            )
            has_leader = self.leader_score > 0
            col = f"  {'#':<5} {'Num':>5} {'W':>3} {'Bet Amount':>14}"
            if has_leader:
                col += f" {'Leader?':>8}"
            col += f" {'Hash':<42} {'Bet#':>8}"
            self.ctx.printer(f"  {'─' * (len(col) - 2)}")
            self.ctx.printer(col)
            self.ctx.printer(f"  {'─' * (len(col) - 2)}")
            for i, h in enumerate(self._contest_hits, 1):
                w = "✓" if h["win"] else "✗"
                row = (
                    f"  {i:<5} {h['number']:>5} {w:>3} "
                    f"{float(h['bet_amount']):>14.8f}"
                )
                if has_leader:
                    ldr = "🥇" if h.get("beats_leader") else "✗"
                    row += f" {ldr:>8}"
                row += f" {h['hash']:<42} #{h['bet_num']:>7,}"
                self.ctx.printer(row)
            self.ctx.printer(f"  {'─' * (len(col) - 2)}")
        else:
            self.ctx.printer(
                f"\n  No rolls {TARGET_LO}-{TARGET_HI} recorded this session."
            )
