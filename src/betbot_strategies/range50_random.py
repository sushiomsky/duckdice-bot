from __future__ import annotations
"""
Range50Random Strategy  (improved)
====================================
Range Dice with exactly 50% chance per bet (5000-slot window over 0–9999).

Improvements over the original:
  • Four adaptive bet-sizing modes: flat, random, streak, oscars
  • Three window-placement modes: random, sequential, split
  • Streak tracking with configurable win/loss streak caps
  • Drawdown guard: hard-stop when balance drops below stop_loss_pct
  • Profit target: auto-stop when take_profit_pct is reached
  • Proper on_session_start / on_session_end with summary stats
  • Periodic mid-session status logging every N bets
  • Conservative default bet sizes (1%–3% instead of 5%–20%)
  • Removed noisy per-bet logger call

Sizing modes
────────────
  flat     — always bet min_frac of balance  (steady, conservative)
  random   — random fraction ∈ [min_frac, max_frac] per bet  (original)
  streak   — fraction ramps from min_frac → max_frac over win streak,
             resets to min_frac on any loss  (capitalise on hot runs)
  oscars   — Oscar's Grind: flat bets, raise by one unit on a win,
             lock when the session is net-positive, reset on loss  (smooth)

Window modes
────────────
  random      — uniform random start in [0, 4999]  (original)
  sequential  — slide window by step_size each bet, wraps at boundary
  split       — alternate between low half (0–4999) and high half (5000–9999)
                with random jitter within each half, useful as a 2-zone test
"""

from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_DOMAIN   = 10_000   # Range Dice slots (0–9999)
_WIDTH    = 5_000    # exactly 50% chance
_LOG_EVERY = 100     # print status every N bets


@register("range-50-random")
class Range50Random:
    """
    50% Range Dice with adaptive sizing, streak awareness,
    drawdown guard, and multiple window-placement strategies.
    """

    # ─────────────────────────────────────────────── class-level API ────

    @classmethod
    def name(cls) -> str:
        return "range-50-random"

    @classmethod
    def describe(cls) -> str:
        return (
            "Range-dice at 50% chance: random 5000-wide window per bet. "
            "Four adaptive sizing modes (flat/random/streak/oscars), "
            "three window modes (random/sequential/split), "
            "streak tracking, drawdown guard, profit target."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Small",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Four sizing modes: flat, random, streak, oscars",
                "Three window modes: random, sequential, split",
                "Streak-based sizing capitalises on win runs",
                "Oscar's Grind keeps equity curve smooth",
                "Drawdown guard prevents session wipeout",
                "Profit target locks in gains automatically",
                "Conservative default bet sizes (1%–3%)",
                "Clean session summary with win-rate and PnL",
            ],
            cons=[
                "50% chance × 1% house edge = negative expected value",
                "Streak sizing increases risk during win streaks",
                "No mathematical edge — all modes lose long-term",
                "Sequential/split window modes are cosmetic, not advantageous",
            ],
            best_use_case=(
                "Low-volatility grind with controlled risk. Best with "
                "sizing_mode=oscars for the smoothest equity curve, or "
                "sizing_mode=streak to capitalise on variance runs."
            ),
            tips=[
                "Use sizing_mode=flat for lowest variance (1% flat bet)",
                "Use sizing_mode=oscars for smoothest equity progression",
                "Use sizing_mode=streak only with a take_profit_pct set",
                "Set stop_loss_pct=10 to cut losses early",
                "Set take_profit_pct=5 for quick, repeatable wins",
                "window_mode=split helps visualise zone bias over time",
                "Keep max_win_streak ≤ 5 to avoid over-commitment",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "sizing_mode": {
                "type": "str",
                "default": "streak",
                "desc": (
                    "Bet sizing algorithm: "
                    "'flat' = constant min_frac; "
                    "'random' = uniform in [min_frac, max_frac]; "
                    "'streak' = ramps min→max on win streak, resets on loss; "
                    "'oscars' = Oscar's Grind (raise 1 unit on win, lock when positive)"
                ),
            },
            "window_mode": {
                "type": "str",
                "default": "random",
                "desc": (
                    "'random' = uniform random position; "
                    "'sequential' = slide by step_size each bet; "
                    "'split' = alternate low/high half with random jitter"
                ),
            },
            "min_frac": {
                "type": "float",
                "default": 0.01,
                "desc": "Minimum bet as fraction of balance (0.01 = 1%).",
            },
            "max_frac": {
                "type": "float",
                "default": 0.03,
                "desc": "Maximum bet as fraction of balance (0.03 = 3%). Used by random/streak modes.",
            },
            "max_win_streak": {
                "type": "int",
                "default": 6,
                "desc": "Win streak at which streak mode reaches max_frac (caps streak scaling).",
            },
            "step_size": {
                "type": "int",
                "default": 500,
                "desc": "Window advance per bet in sequential mode (1–5000).",
            },
            "stop_loss_pct": {
                "type": "float",
                "default": 15.0,
                "desc": "Stop session when balance drops by this % from start. 0 = disabled.",
            },
            "take_profit_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Stop session when profit reaches this % of start balance. 0 = disabled.",
            },
            "use_out": {
                "type": "bool",
                "default": False,
                "desc": "Bet Out-of-range instead of In.",
            },
            "min_amount": {
                "type": "str",
                "default": "",
                "desc": "Absolute minimum bet (decimal string). Overrides frac floor.",
            },
            "max_amount": {
                "type": "str",
                "default": "",
                "desc": "Absolute maximum bet (decimal string).",
            },
        }

    # ─────────────────────────────────────────────────── __init__ ────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.sizing_mode   = str(params.get("sizing_mode",    "streak")).lower()
        self.window_mode   = str(params.get("window_mode",    "random")).lower()
        self.min_frac      = float(params.get("min_frac",      0.01))
        self.max_frac      = float(params.get("max_frac",      0.03))
        self.max_win_streak = max(1, int(params.get("max_win_streak", 6)))
        self.step_size     = max(1, min(5000, int(params.get("step_size", 500))))
        self.stop_loss_pct = float(params.get("stop_loss_pct", 15.0))
        self.take_profit_pct = float(params.get("take_profit_pct", 0.0))
        self.use_out       = bool(params.get("use_out",        False))

        raw_min = str(params.get("min_amount", "") or "")
        raw_max = str(params.get("max_amount", "") or "")
        self._abs_min: Optional[Decimal] = _safe_dec(raw_min) if raw_min else None
        self._abs_max: Optional[Decimal] = _safe_dec(raw_max) if raw_max else None

        # Normalise fracs
        if self.max_frac < self.min_frac:
            self.min_frac, self.max_frac = self.max_frac, self.min_frac

        # Validate modes
        if self.sizing_mode not in ("flat", "random", "streak", "oscars"):
            self.sizing_mode = "streak"
        if self.window_mode not in ("random", "sequential", "split"):
            self.window_mode = "random"

        # ── Session state ─────────────────────────────────────────────────
        self._starting_bal:  Decimal = Decimal("0")
        self._live_bal:      Decimal = Decimal("0")
        self._stop_bal:      Decimal = Decimal("0")   # stop-loss threshold
        self._target_bal:    Decimal = Decimal("0")   # profit target threshold

        self._total_bets:    int     = 0
        self._total_wins:    int     = 0
        self._win_streak:    int     = 0   # consecutive wins
        self._loss_streak:   int     = 0   # consecutive losses
        self._max_win_streak_seen: int = 0
        self._max_loss_streak_seen: int = 0

        # Oscar's Grind state
        self._oscars_unit:   Decimal = Decimal("0")   # 1 base unit = min_frac × balance
        self._oscars_bet:    Decimal = Decimal("0")   # current oscars bet size
        self._oscars_cycle_pnl: Decimal = Decimal("0")  # P&L in current cycle

        # Sequential window state
        self._seq_start:     int     = 0   # current window start position

        # Split window state
        self._split_zone:    int     = 0   # 0 = low half, 1 = high half

    # ─────────────────────────────────────────────── session lifecycle ────

    def on_session_start(self) -> None:
        bal = _safe_dec(self.ctx.starting_balance or "0")
        self._starting_bal = bal
        self._live_bal     = bal
        self._total_bets   = 0
        self._total_wins   = 0
        self._win_streak   = 0
        self._loss_streak  = 0
        self._max_win_streak_seen  = 0
        self._max_loss_streak_seen = 0
        self._seq_start    = 0
        self._split_zone   = 0

        # Thresholds
        self._stop_bal = (
            bal * Decimal(str(1 - self.stop_loss_pct / 100))
            if self.stop_loss_pct > 0 else Decimal("0")
        )
        self._target_bal = (
            bal * Decimal(str(1 + self.take_profit_pct / 100))
            if self.take_profit_pct > 0 else Decimal("0")
        )

        # Oscar's Grind initialise
        self._oscars_unit    = bal * Decimal(str(self.min_frac))
        self._oscars_bet     = self._oscars_unit
        self._oscars_cycle_pnl = Decimal("0")

        self.ctx.printer(
            f"[range-50] started  bal={bal:.8f}  "
            f"sizing={self.sizing_mode}  window={self.window_mode}  "
            f"bet={self.min_frac*100:.1f}%–{self.max_frac*100:.1f}%  "
            + (f"stop={self.stop_loss_pct:.1f}%  " if self.stop_loss_pct else "")
            + (f"target=+{self.take_profit_pct:.1f}%" if self.take_profit_pct else "")
        )

    def on_session_end(self, reason: str) -> None:
        start = self._starting_bal
        final = self._live_bal
        pnl   = final - start
        pct   = float(pnl / start * 100) if start else 0.0
        sign  = "+" if pnl >= 0 else ""
        wr    = (self._total_wins / self._total_bets * 100) if self._total_bets else 0.0
        self.ctx.printer(
            f"[range-50] ended ({reason})  "
            f"bets={self._total_bets}  wins={self._total_wins}  wr={wr:.1f}%  "
            f"PnL={sign}{pnl:.8f} ({sign}{pct:.2f}%)  "
            f"max_win_streak={self._max_win_streak_seen}  "
            f"max_loss_streak={self._max_loss_streak_seen}"
        )

    # ──────────────────────────────────────────────────── next_bet ────────

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._live_bal
        if bal <= 0:
            return None

        # ── Stop-loss guard ───────────────────────────────────────────────
        if self._stop_bal > 0 and bal <= self._stop_bal:
            self.ctx.printer(
                f"[range-50] ⛔ stop-loss triggered  "
                f"bal={bal:.8f} ≤ {self._stop_bal:.8f}"
            )
            return None

        # ── Profit target guard ───────────────────────────────────────────
        if self._target_bal > 0 and bal >= self._target_bal:
            self.ctx.printer(
                f"[range-50] 🎯 profit target reached  "
                f"bal={bal:.8f} ≥ {self._target_bal:.8f}"
            )
            return None

        self._total_bets += 1

        # ── Compute bet amount ────────────────────────────────────────────
        amt = self._size_bet(bal)
        if amt <= 0:
            return None

        # ── Compute window position ───────────────────────────────────────
        start, end = self._pick_window()

        # Periodic status log
        if self._total_bets % _LOG_EVERY == 0:
            wr = (self._total_wins / self._total_bets * 100) if self._total_bets else 0.0
            pnl = float(bal - self._starting_bal)
            self.ctx.printer(
                f"[range-50] bet#{self._total_bets}  "
                f"bal={bal:.8f}  PnL={pnl:+.8f}  wr={wr:.1f}%  "
                f"win_streak={self._win_streak}  loss_streak={self._loss_streak}  "
                f"window=[{start},{end}]  bet={float(amt):.8f}"
            )

        return {
            "game":   "range-dice",
            "amount": format(amt, "f"),
            "range":  (start, end),
            "is_in":  not self.use_out,
            "faucet": self.ctx.faucet,
        }

    # ────────────────────────────────────────────────── on_bet_result ────

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)

        # Update live balance
        try:
            self._live_bal = Decimal(str(result.get("balance", self._live_bal)))
        except Exception:
            pass

        won = bool(result.get("win"))

        # ── Update streak counters ────────────────────────────────────────
        if won:
            self._total_wins += 1
            self._win_streak  += 1
            self._loss_streak  = 0
            if self._win_streak > self._max_win_streak_seen:
                self._max_win_streak_seen = self._win_streak
        else:
            self._loss_streak += 1
            self._win_streak   = 0
            if self._loss_streak > self._max_loss_streak_seen:
                self._max_loss_streak_seen = self._loss_streak

        # ── Oscar's Grind cycle P&L update ───────────────────────────────
        try:
            profit = Decimal(str(result.get("profit", "0")))
            self._oscars_cycle_pnl += profit
        except Exception:
            pass

        # ── Oscar's Grind bet adjustment ─────────────────────────────────
        if self.sizing_mode == "oscars":
            self._update_oscars(won)

    # ───────────────────────────────────────────── sizing helpers ─────────

    def _size_bet(self, bal: Decimal) -> Decimal:
        """Compute bet amount for the current bet according to sizing_mode."""
        if self.sizing_mode == "flat":
            frac = self.min_frac

        elif self.sizing_mode == "random":
            frac = self.ctx.rng.uniform(self.min_frac, self.max_frac)

        elif self.sizing_mode == "streak":
            # Linear ramp: min_frac at 0 wins → max_frac at max_win_streak wins.
            # Resets to min_frac immediately on any loss.
            t    = min(self._win_streak, self.max_win_streak) / self.max_win_streak
            frac = self.min_frac + (self.max_frac - self.min_frac) * t

        elif self.sizing_mode == "oscars":
            # Amount is managed by _update_oscars; just return current bet
            amt = self._oscars_bet
            return self._clamp(amt, bal)

        else:
            frac = self.min_frac

        raw = bal * Decimal(str(frac))
        return self._clamp(raw, bal)

    def _clamp(self, amt: Decimal, bal: Decimal) -> Decimal:
        """Apply absolute min/max overrides and quantise to 8 dp."""
        a = amt
        if self._abs_min is not None:
            a = max(a, self._abs_min)
        if self._abs_max is not None:
            a = min(a, self._abs_max)
        # Hard cap: never exceed max_frac of current balance
        cap = bal * Decimal(str(self.max_frac))
        if a > cap:
            a = cap
        a = a.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        return max(a, Decimal("0.00000001"))

    def _update_oscars(self, won: bool) -> None:
        """
        Oscar's Grind logic:
        - Bet = current_bet (starts at 1 unit = min_frac × starting_balance)
        - On a WIN: increase bet by 1 unit IF doing so won't overshoot break-even
        - On a LOSS: keep bet the same (no chasing)
        - When cycle_pnl ≥ 0 (session is net-positive): reset to 1 unit, new cycle
        """
        unit = self._oscars_unit
        if won:
            # Check if we're now net-positive → start fresh cycle
            if self._oscars_cycle_pnl >= 0:
                self._oscars_bet     = unit
                self._oscars_cycle_pnl = Decimal("0")
            else:
                # Raise by 1 unit unless it would overshoot net-even
                # (don't bet more than needed to get back to zero)
                needed     = abs(self._oscars_cycle_pnl)
                next_bet   = self._oscars_bet + unit
                # Payout on range-50 win: 2× bet - 1% house edge ≈ 1× profit
                # Profit if we win = bet amount (at ~50% with 99× house mult ≈ 0.98 profit/bet)
                # Use simple 1:1 approximation for grind sizing
                max_needed = needed   # at 1:1 we need exactly `needed` more profit
                if next_bet <= max_needed + unit:
                    self._oscars_bet = next_bet
                # else keep current bet (enough to recover without overshooting)
        # On loss: no change to bet (the grind doesn't chase)

    # ────────────────────────────────────── window placement helpers ──────

    def _pick_window(self) -> Tuple[int, int]:
        """Return (start, end) for the 5000-slot Range Dice window."""
        max_start = _DOMAIN - _WIDTH   # = 4999

        if self.window_mode == "random":
            start = self.ctx.rng.randint(0, max_start)

        elif self.window_mode == "sequential":
            # Advance start by step_size each bet, wrap at boundary
            start = self._seq_start
            self._seq_start = (self._seq_start + self.step_size) % (max_start + 1)

        elif self.window_mode == "split":
            # Alternate between two zones with jitter:
            #   zone 0 → window starts in [0,    2499]: covers slots 0–4999 to ~2499+4999
            #   zone 1 → window starts in [2500, 4999]: covers slots 2500–9999
            # This creates non-overlapping / shifted coverage patterns
            if self._split_zone == 0:
                start = self.ctx.rng.randint(0, max_start // 2)
            else:
                start = self.ctx.rng.randint(max_start // 2 + 1, max_start)
            self._split_zone ^= 1   # toggle 0 ↔ 1

        else:
            start = self.ctx.rng.randint(0, max_start)

        end = start + _WIDTH - 1
        return (start, end)


# ──────────────────────────────────────────── module helpers ────────────

def _safe_dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")
