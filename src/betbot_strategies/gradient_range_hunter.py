from __future__ import annotations
"""
Gradient Range Hunter Strategy

Range Dice (bet in) with a target-driven bet sizing gradient and a randomly
selected chance window per bet.

Window width is picked log-uniformly between ``min_chance_pct`` (0.01%, 1 slot)
and ``max_chance_pct`` (1.00%, 100 slots) on the 0–9999 domain so the RNG has
no fixed window to exploit.  Window position is uniformly random each bet.

Bet sizing gradient
-------------------
Two divisors define how aggressive bets are relative to current balance:

  far_divisor   (default 300)
    Far from target → bet = balance / 300  ≈ 0.33 %
    Larger swings early to accumulate progress quickly.

  near_divisor  (default 1000)
    Close to target → bet = balance / 1000 ≈ 0.10 %
    Smaller, precise bets to preserve gains and avoid overshooting.

The effective divisor interpolates linearly:

    progress  = (balance - start) / (target - start)   # clipped to [0, 1]
    divisor   = far_divisor + (near_divisor - far_divisor) * progress
    bet       = balance / divisor

An optional ±jitter randomises each bet slightly to avoid pattern detection.

Domain: 0–9999 (10 000 slots)
  width = 1   → chance = 0.01 %  → multiplier ≈ 9 900 ×
  width = 100 → chance = 1.00 %  → multiplier ≈    99 ×
"""
import math
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_DOMAIN = 10_000   # Range Dice slots  0–9999


@register("gradient-range-hunter")
class GradientRangeHunter:
    """Range Dice bet-in: random 0.01%–1% window, target-gradient bet sizing."""

    @classmethod
    def name(cls) -> str:
        return "gradient-range-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Random 0.01%–1% Range Dice (bet in) with gradient bet sizing: "
            "bet ≈ balance/300 when far from target, balance/1000 when close. "
            "Window position and width are re-randomised every bet."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Target-aware: automatically de-risks as you approach goal",
                "Random window prevents RNG pattern exploitation",
                "Wide payout range (99× – 9 900×) from varied chance widths",
                "Smooth bet gradient — no sudden sizing jumps",
                "Configurable divisors to match your risk preference",
            ],
            cons=[
                "House edge ~1 % per bet regardless of window choice",
                "High-variance due to low-chance windows",
                "No loss-recovery mechanic — flat divisor-based sizing",
                "Target overshoot still possible on single large win",
            ],
            best_use_case=(
                "Goal-oriented sessions where you want to grow balance by a "
                "fixed percentage and lock in gains automatically."
            ),
            tips=[
                "Set profit_target_pct to 5–20 % for realistic session goals",
                "Lower far_divisor (e.g. 150) for more aggressive early bets",
                "Raise near_divisor (e.g. 2000) for extra caution near target",
                "Use min_chance_pct=0.05 to limit the most extreme windows",
                "jitter=0.0 disables randomisation for deterministic sizing",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "profit_target_pct": {
                "type": "float",
                "default": 10.0,
                "desc": (
                    "Session profit target as % of starting balance. "
                    "Strategy stops when this is reached. (0 = run indefinitely)"
                ),
            },
            "far_divisor": {
                "type": "float",
                "default": 300.0,
                "desc": (
                    "Bet = balance / far_divisor when far from target "
                    "(≈ 0.33 % of balance at default 300)."
                ),
            },
            "near_divisor": {
                "type": "float",
                "default": 1000.0,
                "desc": (
                    "Bet = balance / near_divisor when near target "
                    "(≈ 0.10 % of balance at default 1000)."
                ),
            },
            "min_chance_pct": {
                "type": "float",
                "default": 0.01,
                "desc": (
                    "Minimum window chance in % (narrowest = 0.01 %, 1 slot, "
                    "~9 900 × payout)."
                ),
            },
            "max_chance_pct": {
                "type": "float",
                "default": 1.0,
                "desc": (
                    "Maximum window chance in % (widest = 1 %, 100 slots, "
                    "~99 × payout)."
                ),
            },
            "jitter": {
                "type": "float",
                "default": 0.15,
                "desc": "Random ± jitter fraction applied to each bet (0.15 = ±15 %).",
            },
        }

    # ──────────────────────────────────────────────────────────────── init

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.profit_target_pct = float(params.get("profit_target_pct", 10.0))
        self.far_divisor       = max(1.0, float(params.get("far_divisor",  300.0)))
        self.near_divisor      = max(1.0, float(params.get("near_divisor", 1000.0)))
        self.min_chance_pct    = max(0.01,  float(params.get("min_chance_pct", 0.01)))
        self.max_chance_pct    = min(49.0,  float(params.get("max_chance_pct", 1.0)))
        self.jitter            = max(0.0,   float(params.get("jitter", 0.15)))

        # Clamp: near_divisor must be ≥ far_divisor (bets shrink near target)
        if self.near_divisor < self.far_divisor:
            self.near_divisor = self.far_divisor

        # Convert chance % → slot widths
        self._min_width = max(1, round(self.min_chance_pct / 100 * _DOMAIN))
        self._max_width = max(self._min_width, round(self.max_chance_pct / 100 * _DOMAIN))

        self._starting_bal: Decimal = Decimal("0")
        self._target_bal:   Decimal = Decimal("0")
        self._live_bal:     Decimal = Decimal("0")
        self._bets:   int = 0
        self._wins:   int = 0

    # ──────────────────────────────────────────────────────── session hooks

    def on_session_start(self) -> None:
        bal = _dec(self.ctx.starting_balance or "0")
        self._starting_bal = bal
        self._live_bal     = bal
        self._bets         = 0
        self._wins         = 0

        if self.profit_target_pct > 0 and bal > 0:
            self._target_bal = bal * Decimal(str(1 + self.profit_target_pct / 100))
        else:
            self._target_bal = Decimal("0")

        self.ctx.printer(
            f"[gradient-range-hunter] started | balance={bal} | "
            f"target={self._target_bal} (+{self.profit_target_pct:.1f}%) | "
            f"divisor: {self.far_divisor:.0f} → {self.near_divisor:.0f} | "
            f"window: {self.min_chance_pct:.4f}%–{self.max_chance_pct:.2f}% "
            f"({self._min_width}–{self._max_width} slots)"
        )

    def on_session_end(self, reason: str) -> None:
        start = self._starting_bal
        final = self._live_bal
        pnl   = final - start
        pct   = float(pnl / start * 100) if start else 0.0
        sign  = "+" if pnl >= 0 else ""
        self.ctx.printer(
            f"[gradient-range-hunter] session ended ({reason}) | "
            f"bets={self._bets} wins={self._wins} | "
            f"PnL={sign}{pnl:.8f} ({sign}{pct:.2f}%)"
        )

    # ───────────────────────────────────────────────────────────── next bet

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._live_bal
        if bal <= 0:
            return None

        # Profit target check
        if self._target_bal > 0 and bal >= self._target_bal:
            self.ctx.printer(
                f"[gradient-range-hunter] 🎯 target reached "
                f"({bal:.8f} ≥ {self._target_bal:.8f}) — stopping"
            )
            return None

        amt = self._calc_bet(bal)
        if amt <= 0:
            return None

        lo, hi = self._random_window()

        return {
            "game":   "range-dice",
            "amount": format(amt, "f"),
            "range":  (lo, hi),
            "is_in":  True,
            "faucet": self.ctx.faucet,
        }

    # ─────────────────────────────────────────────────────────── bet result

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)
        self._bets += 1

        try:
            self._live_bal = _dec(result.get("balance", self._live_bal))
        except Exception:
            pass

        if bool(result.get("win")):
            self._wins += 1
            try:
                profit   = _dec(result.get("profit", "0"))
                progress = self._progress()
                self.ctx.printer(
                    f"[gradient-range-hunter] ✓ WIN profit={profit:.8f} "
                    f"bal={self._live_bal:.8f} "
                    f"progress={progress*100:.1f}%"
                )
            except Exception:
                pass

    # ──────────────────────────────────────────────────────────── helpers

    def _progress(self) -> float:
        """0.0 = at start, 1.0 = at target (clipped)."""
        if self._target_bal <= self._starting_bal:
            return 0.0
        raw = float(
            (self._live_bal - self._starting_bal)
            / (self._target_bal - self._starting_bal)
        )
        return max(0.0, min(1.0, raw))

    def _calc_bet(self, bal: Decimal) -> Decimal:
        progress = self._progress()
        divisor  = self.far_divisor + (self.near_divisor - self.far_divisor) * progress
        amt      = bal / Decimal(str(divisor))

        if self.jitter > 0:
            j   = 1.0 + self.ctx.rng.uniform(-self.jitter, self.jitter)
            amt = amt * Decimal(str(max(0.01, j)))

        return amt.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

    def _random_window(self) -> tuple[int, int]:
        """Pick a random window log-uniformly in [min_width, max_width]."""
        if self._min_width >= self._max_width:
            width = self._min_width
        else:
            log_lo  = math.log(self._min_width)
            log_hi  = math.log(self._max_width)
            width   = max(1, round(math.exp(self.ctx.rng.uniform(log_lo, log_hi))))

        max_start = _DOMAIN - width
        lo = self.ctx.rng.randint(0, max_start)
        return lo, lo + width - 1


# ── helpers ─────────────────────────────────────────────────────────────────────

def _dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")
