from __future__ import annotations
"""
Range Decoy Ramp Strategy
==========================
0.02% Range Dice sniper with a configurable decoy pre-roll phase and a
progressive bet ramp that grows from ``min_bet`` to ``max_bet`` over
``ramp_rolls`` real (sniper) rolls.

Phases
------
1. **Decoy** (pre-roll):  Place ``decoy_count`` flat bets at ``decoy_chance``%
   to warm up entropy, mask the real strategy, and probe recent RNG state.
   Decoy bets use ``decoy_amount``; wins/losses do not affect the ramp counter.

2. **Sniper** (main loop):  Bet inside a 2-slot, 0.02% Range Dice window.
   Bet size starts at ``min_bet`` and ramps linearly (or exponentially) to
   ``max_bet`` after ``ramp_rolls`` total sniper bets.  If ``reset_on_win``
   is True the ramp counter resets to 0 on every hit.

Bet-size formula
----------------
progress = clamp(sniper_rolls / ramp_rolls, 0.0, 1.0)

linear:       bet = min_bet + (max_bet - min_bet) * progress
exponential:  bet = min_bet * (max_bet / min_bet) ** progress

Key parameters
--------------
min_bet       Absolute minimum bet (decimal string, e.g. "0.00000001")
max_bet       Absolute maximum bet reached at ramp_rolls
ramp_rolls    Sniper bets needed to reach max_bet  (default 5000)
ramp_style    "linear" | "exponential"             (default "linear")
reset_on_win  Reset ramp counter after each hit    (default True)
decoy_count   Number of decoy bets before sniping  (default 50)
decoy_chance  Win-chance % for decoy bets           (default 49.5)
decoy_amount  Flat bet for decoy phase (decimal string, default min_bet)
window_mode   "random" | "sequential" | "fixed"    (default "random")
window_start  Slot for fixed mode  (0–9998)         (default 4999)
step_size     Slots to advance per bet in sequential mode (default 1)
stop_loss_pct Stop when balance drops this % from start  (default 50)
take_profit_pct Stop when profit reaches this % of start (default 0 = off)
"""

import math
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_DOMAIN = 10_000   # Range Dice slot domain 0–9999
_WIDTH  = 2        # 0.02% of 10,000 = 2 slots
_LOG_EVERY = 250   # status log every N sniper bets


@register("range-decoy-ramp")
class RangeDecoyRamp:
    """
    0.02% Range Dice sniper: decoy preroll phase + progressive bet ramp.

    Phase 1 — Decoy: flat bets at a configurable chance (default 49.5%) to
    seed entropy and mask the real strategy.
    Phase 2 — Sniper: 2-slot 0.02% window bets growing from min_bet to
    max_bet over ramp_rolls bets (configurable).
    """

    @classmethod
    def name(cls) -> str:
        return "range-decoy-ramp"

    @classmethod
    def describe(cls) -> str:
        return (
            "0.02% Range Dice sniper with a decoy preroll phase and a "
            "progressive bet ramp from min_bet to max_bet over ramp_rolls bets. "
            "Configurable ramp style (linear/exponential), window mode, and stop conditions."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Medium-Large",
            volatility="Extreme",
            time_to_profit="Rare / Burst",
            recommended_for="Advanced",
            pros=[
                "Decoy phase warms up entropy and masks the strategy pattern",
                "Progressive ramp concentrates larger bets later in a dry run",
                "Configurable ramp: linear or exponential growth curve",
                "reset_on_win resets the ramp after a hit, preventing over-betting",
                "Window mode flexibility: random, sequential, or fixed slot",
                "~4,950× payout on hit amplifies a ramped bet significantly",
            ],
            cons=[
                "Still 0.02% per sniper bet — long losing streaks are normal",
                "Decoy bets consume balance before sniping begins",
                "House edge applies to every bet in both phases",
                "High max_bet reached near ramp_rolls can risk significant balance",
            ],
            best_use_case=(
                "Long-session jackpot hunting where you want bets to naturally "
                "grow as the dry-run extends, without a hard martingale reset. "
                "Decoy phase adds a layer of pattern obfuscation."
            ),
            tips=[
                "Set reset_on_win=True so a hit resets the ramp, protecting profits",
                "Use ramp_style=exponential for slower early growth, rapid late growth",
                "Keep decoy_count=30-100 for entropy seeding without wasting too much balance",
                "Set stop_loss_pct=40 to exit before a full wipeout",
                "window_mode=sequential scans the full domain systematically",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "min_bet": {
                "type": "str",
                "default": "0.00000001",
                "desc": "Absolute minimum bet (starting ramp value, decimal string).",
            },
            "max_bet": {
                "type": "str",
                "default": "0.00010000",
                "desc": "Absolute maximum bet reached after ramp_rolls sniper bets.",
            },
            "ramp_rolls": {
                "type": "int",
                "default": 5000,
                "desc": "Number of sniper bets to reach max_bet (default 5000).",
            },
            "ramp_style": {
                "type": "str",
                "default": "linear",
                "desc": "Bet growth curve: 'linear' or 'exponential'.",
            },
            "reset_on_win": {
                "type": "bool",
                "default": True,
                "desc": "Reset ramp counter to 0 after each sniper hit.",
            },
            "decoy_count": {
                "type": "int",
                "default": 50,
                "desc": "Number of decoy bets before sniping starts (0 to skip).",
            },
            "decoy_chance": {
                "type": "float",
                "default": 49.5,
                "desc": "Win-chance % for decoy bets (default 49.5 = near-coinflip).",
            },
            "decoy_amount": {
                "type": "str",
                "default": "",
                "desc": "Flat bet for decoy phase (decimal string). Defaults to min_bet.",
            },
            "window_mode": {
                "type": "str",
                "default": "random",
                "desc": (
                    "Sniper window placement: "
                    "'random' = uniform random slot; "
                    "'sequential' = advance step_size per bet (wraps); "
                    "'fixed' = always window_start."
                ),
            },
            "window_start": {
                "type": "int",
                "default": 4999,
                "desc": "Fixed window start slot (0–9998), used when window_mode='fixed'.",
            },
            "step_size": {
                "type": "int",
                "default": 1,
                "desc": "Slots to advance per bet in sequential mode (1–9998).",
            },
            "stop_loss_pct": {
                "type": "float",
                "default": 50.0,
                "desc": "Stop when balance drops this % from session start. 0 = disabled.",
            },
            "take_profit_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Stop when profit reaches this % of start balance. 0 = disabled.",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.min_bet      = _safe_dec(params.get("min_bet", "0.00000001")) or Decimal("0.00000001")
        self.max_bet      = _safe_dec(params.get("max_bet", "0.00010000")) or self.min_bet
        self.ramp_rolls   = max(1, int(params.get("ramp_rolls", 5000)))
        self.ramp_style   = str(params.get("ramp_style", "linear")).lower()
        self.reset_on_win = bool(params.get("reset_on_win", True))

        self.decoy_count  = max(0, int(params.get("decoy_count", 50)))
        self.decoy_chance = max(0.01, min(98.0, float(params.get("decoy_chance", 49.5))))
        raw_decoy_amt     = str(params.get("decoy_amount", "") or "")
        self.decoy_amount = _safe_dec(raw_decoy_amt) if raw_decoy_amt else self.min_bet

        self.window_mode  = str(params.get("window_mode", "random")).lower()
        self.window_start = max(0, min(_DOMAIN - _WIDTH, int(params.get("window_start", 4999))))
        self.step_size    = max(1, min(_DOMAIN - _WIDTH, int(params.get("step_size", 1))))

        self.stop_loss_pct   = float(params.get("stop_loss_pct", 50.0))
        self.take_profit_pct = float(params.get("take_profit_pct", 0.0))

        if self.ramp_style not in ("linear", "exponential"):
            self.ramp_style = "linear"
        if self.window_mode not in ("random", "sequential", "fixed"):
            self.window_mode = "random"
        if self.max_bet < self.min_bet:
            self.max_bet = self.min_bet

        # Session state
        self._starting_bal:    Decimal = Decimal("0")
        self._live_bal:        Decimal = Decimal("0")
        self._stop_bal:        Decimal = Decimal("0")
        self._target_bal:      Decimal = Decimal("0")

        self._decoy_done:      int = 0   # decoy bets completed
        self._sniper_rolls:    int = 0   # sniper bets since last hit (or session start)
        self._total_sniper:    int = 0   # total sniper bets this session
        self._total_wins:      int = 0
        self._seq_pos:         int = 0
        self._in_decoy:        bool = self.decoy_count > 0

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def on_session_start(self) -> None:
        bal = _safe_dec(self.ctx.starting_balance or "0")
        self._starting_bal = bal
        self._live_bal     = bal
        self._decoy_done   = 0
        self._sniper_rolls = 0
        self._total_sniper = 0
        self._total_wins   = 0
        self._seq_pos      = 0
        self._in_decoy     = self.decoy_count > 0

        self._stop_bal = (
            bal * Decimal(str(1 - self.stop_loss_pct / 100))
            if self.stop_loss_pct > 0 else Decimal("0")
        )
        self._target_bal = (
            bal * Decimal(str(1 + self.take_profit_pct / 100))
            if self.take_profit_pct > 0 else Decimal("0")
        )

        self.ctx.printer(
            f"[range-decoy-ramp] started  bal={bal:.8f}  "
            f"decoy={self.decoy_count}×{float(self.decoy_amount):.8f}@{self.decoy_chance:.1f}%  "
            f"ramp={self.ramp_style}  min={float(self.min_bet):.8f}  "
            f"max={float(self.max_bet):.8f}  over={self.ramp_rolls} rolls  "
            f"reset_on_win={self.reset_on_win}"
        )

    def on_session_end(self, reason: str) -> None:
        start = self._starting_bal
        final = self._live_bal
        pnl   = final - start
        pct   = float(pnl / start * 100) if start else 0.0
        sign  = "+" if pnl >= 0 else ""
        wr    = (self._total_wins / self._total_sniper * 100) if self._total_sniper else 0.0
        self.ctx.printer(
            f"[range-decoy-ramp] ended ({reason})  "
            f"decoy_bets={self._decoy_done}  sniper_bets={self._total_sniper}  "
            f"hits={self._total_wins}  hit_rate={wr:.4f}%  "
            f"PnL={sign}{pnl:.8f} ({sign}{pct:.2f}%)"
        )

    # ── bet generation ────────────────────────────────────────────────────────

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._live_bal
        if bal <= 0:
            return None

        if self._stop_bal > 0 and bal <= self._stop_bal:
            self.ctx.printer(
                f"[range-decoy-ramp] ⛔ stop-loss  bal={bal:.8f} ≤ {self._stop_bal:.8f}"
            )
            return None

        if self._target_bal > 0 and bal >= self._target_bal:
            self.ctx.printer(
                f"[range-decoy-ramp] 🎯 profit target  bal={bal:.8f} ≥ {self._target_bal:.8f}"
            )
            return None

        # ── Phase 1: decoy ───────────────────────────────────────────────────
        if self._in_decoy:
            return self._decoy_bet()

        # ── Phase 2: sniper ──────────────────────────────────────────────────
        return self._sniper_bet(bal)

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)

        try:
            self._live_bal = Decimal(str(result.get("balance", self._live_bal)))
        except Exception:
            pass

        if self._in_decoy:
            self._decoy_done += 1
            if self._decoy_done >= self.decoy_count:
                self._in_decoy = False
                self.ctx.printer(
                    f"[range-decoy-ramp] ✅ decoy phase complete "
                    f"({self._decoy_done} bets)  entering sniper mode"
                )
            return

        # Sniper result
        won = bool(result.get("win"))
        self._total_sniper += 1

        if won:
            self._total_wins += 1
            payout = float(result.get("profit", 0))
            self.ctx.printer(
                f"[range-decoy-ramp] 💥 HIT!  sniper_roll={self._sniper_rolls}  "
                f"profit={payout:+.8f}  total_hits={self._total_wins}"
            )
            if self.reset_on_win:
                self._sniper_rolls = 0
                self.ctx.printer("[range-decoy-ramp] 🔄 ramp reset after hit")
            else:
                self._sniper_rolls += 1
        else:
            self._sniper_rolls += 1

    # ── helpers ───────────────────────────────────────────────────────────────

    def _decoy_bet(self) -> BetSpec:
        amt = self.decoy_amount.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        amt = max(amt, Decimal("0.00000001"))
        return {
            "game":    "dice",
            "amount":  format(amt, "f"),
            "chance":  f"{self.decoy_chance:.2f}",
            "is_high": False,
            "faucet":  self.ctx.faucet,
        }

    def _sniper_bet(self, bal: Decimal) -> BetSpec:
        amt   = self._ramp_bet()
        start, end = self._pick_window()

        self._total_sniper  # already incremented in on_bet_result; track before result
        roll_num = self._sniper_rolls + 1  # next roll number (1-based for display)

        if roll_num % _LOG_EVERY == 0 or roll_num == 1:
            progress_pct = min(self._sniper_rolls / self.ramp_rolls * 100, 100.0)
            self.ctx.printer(
                f"[range-decoy-ramp] sniper#{roll_num}  "
                f"bal={bal:.8f}  bet={float(amt):.8f}  "
                f"ramp={progress_pct:.1f}%  window=[{start},{end}]  "
                f"hits={self._total_wins}"
            )

        return {
            "game":   "range-dice",
            "amount": format(amt, "f"),
            "range":  (start, end),
            "is_in":  True,
            "faucet": self.ctx.faucet,
        }

    def _ramp_bet(self) -> Decimal:
        """Compute the current ramped bet size based on sniper_rolls progress."""
        progress = min(self._sniper_rolls / self.ramp_rolls, 1.0)

        if self.ramp_style == "exponential" and self.max_bet > self.min_bet:
            ratio = float(self.max_bet / self.min_bet)
            raw   = self.min_bet * Decimal(str(ratio ** progress))
        else:
            raw = self.min_bet + (self.max_bet - self.min_bet) * Decimal(str(progress))

        raw = raw.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        return max(raw, self.min_bet)

    def _pick_window(self) -> Tuple[int, int]:
        max_start = _DOMAIN - _WIDTH  # 9998

        if self.window_mode == "fixed":
            start = self.window_start
        elif self.window_mode == "sequential":
            start = self._seq_pos
            self._seq_pos = (self._seq_pos + self.step_size) % (max_start + 1)
        else:
            start = self.ctx.rng.randint(0, max_start)

        return (start, start + _WIDTH - 1)


def _safe_dec(v: Any) -> Optional[Decimal]:
    try:
        return Decimal(str(v))
    except Exception:
        return None
