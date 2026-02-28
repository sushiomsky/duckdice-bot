from __future__ import annotations
"""
DiceOut002 Strategy
====================
Range Dice sniper targeting an ultra-narrow 0.02% window (2 slots out of 0–9999).

Win probability per bet: ~0.02% (2/10,000)
Expected payout on hit:  ~4,950× bet (at 99% RTP)

Flat bet sizing only: each bet is bet_frac × current balance, so the absolute
bet amount scales down naturally as the balance falls and up as it grows.

Window placement per bet:
  random     — uniform random position in [0, 9998]  (default)
  sequential — advance by step_size each bet, wraps at 9999
  fixed      — always use the same start slot (window_start param)

Defaults are tuned for extended survival:
  bet_frac=0.0002 (0.02% of current balance per bet)
  stop_loss_pct=50.0
  take_profit_pct=0.0 (disabled)
"""

from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_DOMAIN = 10_000   # Range Dice slot domain 0–9999
_WIDTH  = 2        # 0.02% of 10,000 = 2 slots
_LOG_EVERY = 500   # status print every N bets


@register("dice-out-002")
class DiceOut002:
    """0.02% range sniper: 2-slot window, ultra-rare hit, ~4950× payout."""

    @classmethod
    def name(cls) -> str:
        return "dice-out-002"

    @classmethod
    def describe(cls) -> str:
        return (
            "0.02% Range Dice sniper: bet inside a 2-slot window (out of 0–9999). "
            "~4,950× payout on hit. Flat bet_frac of current balance per bet."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Medium",
            volatility="Extreme",
            time_to_profit="Rare / Burst",
            recommended_for="Advanced",
            pros=[
                "Massive payout on hit (~4,950× bet)",
                "Bet scales with balance — smaller bets as bankroll shrinks",
                "Very low per-bet cost keeps sessions long",
                "Predictable, controlled drawdown curve",
                "Simple mechanics, easy to reason about",
            ],
            cons=[
                "0.02% win rate — expect ~5,000 bets between wins on average",
                "Long losing streaks are the norm, not the exception",
                "Negative expected value due to house edge",
                "A single session can end with zero hits",
            ],
            best_use_case=(
                "High-risk lottery play. Lower bet_frac for maximum longevity; "
                "raise it to chase faster hits at the cost of a deeper drawdown."
            ),
            tips=[
                "Set bet_frac=0.0001 (0.01% of balance) for longer sessions",
                "Set stop_loss_pct=30 to exit before full wipeout",
                "Use window_mode=random for unbiased coverage",
                "window_mode=sequential scans every slot systematically",
                "Track hits per session; even one hit is a big win",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "bet_frac": {
                "type": "float",
                "default": 0.0002,
                "desc": "Bet as fraction of current balance per bet (0.0002 = 0.02%).",
            },
            "window_mode": {
                "type": "str",
                "default": "random",
                "desc": (
                    "Window placement: 'random' = uniform random; "
                    "'sequential' = advance step_size per bet; "
                    "'fixed' = always window_start."
                ),
            },
            "window_start": {
                "type": "int",
                "default": 4999,
                "desc": "Fixed window start slot (0–9998) used when window_mode='fixed'.",
            },
            "step_size": {
                "type": "int",
                "default": 1,
                "desc": "Slots to advance per bet in sequential mode (1–9998).",
            },
            "stop_loss_pct": {
                "type": "float",
                "default": 50.0,
                "desc": "Stop when balance drops by this % from session start. 0 = disabled.",
            },
            "take_profit_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Stop when profit reaches this % of start balance. 0 = disabled.",
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

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.bet_frac     = float(params.get("bet_frac", 0.0002))
        self.window_mode  = str(params.get("window_mode", "random")).lower()
        self.window_start = max(0, min(_DOMAIN - _WIDTH, int(params.get("window_start", 4999))))
        self.step_size    = max(1, min(_DOMAIN - _WIDTH, int(params.get("step_size", 1))))
        self.stop_loss_pct   = float(params.get("stop_loss_pct", 50.0))
        self.take_profit_pct = float(params.get("take_profit_pct", 0.0))

        raw_min = str(params.get("min_amount", "") or "")
        raw_max = str(params.get("max_amount", "") or "")
        self._abs_min: Optional[Decimal] = _safe_dec(raw_min) if raw_min else None
        self._abs_max: Optional[Decimal] = _safe_dec(raw_max) if raw_max else None

        if self.window_mode not in ("random", "sequential", "fixed"):
            self.window_mode = "random"

        # Session state
        self._starting_bal: Decimal = Decimal("0")
        self._live_bal:     Decimal = Decimal("0")
        self._stop_bal:     Decimal = Decimal("0")
        self._target_bal:   Decimal = Decimal("0")

        self._total_bets:     int = 0
        self._total_wins:     int = 0
        self._loss_streak:    int = 0
        self._max_loss_streak: int = 0
        self._seq_pos:        int = 0

    def on_session_start(self) -> None:
        bal = _safe_dec(self.ctx.starting_balance or "0")
        self._starting_bal = bal
        self._live_bal     = bal
        self._total_bets   = 0
        self._total_wins   = 0
        self._loss_streak  = 0
        self._max_loss_streak = 0
        self._seq_pos      = 0

        self._stop_bal = (
            bal * Decimal(str(1 - self.stop_loss_pct / 100))
            if self.stop_loss_pct > 0 else Decimal("0")
        )
        self._target_bal = (
            bal * Decimal(str(1 + self.take_profit_pct / 100))
            if self.take_profit_pct > 0 else Decimal("0")
        )

        self.ctx.printer(
            f"[dice-out-002] started  bal={bal:.8f}  "
            f"window={self.window_mode}  bet={self.bet_frac*100:.4f}% of balance"
            + (f"  stop={self.stop_loss_pct:.1f}%" if self.stop_loss_pct else "")
            + (f"  target=+{self.take_profit_pct:.1f}%" if self.take_profit_pct else "")
        )

    def on_session_end(self, reason: str) -> None:
        start = self._starting_bal
        final = self._live_bal
        pnl   = final - start
        pct   = float(pnl / start * 100) if start else 0.0
        sign  = "+" if pnl >= 0 else ""
        wr    = (self._total_wins / self._total_bets * 100) if self._total_bets else 0.0
        self.ctx.printer(
            f"[dice-out-002] ended ({reason})  "
            f"bets={self._total_bets}  hits={self._total_wins}  hit_rate={wr:.4f}%  "
            f"PnL={sign}{pnl:.8f} ({sign}{pct:.2f}%)  "
            f"max_loss_streak={self._max_loss_streak}"
        )

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._live_bal
        if bal <= 0:
            return None

        if self._stop_bal > 0 and bal <= self._stop_bal:
            self.ctx.printer(
                f"[dice-out-002] ⛔ stop-loss  bal={bal:.8f} ≤ {self._stop_bal:.8f}"
            )
            return None

        if self._target_bal > 0 and bal >= self._target_bal:
            self.ctx.printer(
                f"[dice-out-002] 🎯 profit target  bal={bal:.8f} ≥ {self._target_bal:.8f}"
            )
            return None

        self._total_bets += 1

        amt = self._size_bet(bal)
        if amt <= 0:
            return None

        start, end = self._pick_window()

        if self._total_bets % _LOG_EVERY == 0:
            pnl = float(bal - self._starting_bal)
            self.ctx.printer(
                f"[dice-out-002] bet#{self._total_bets}  "
                f"bal={bal:.8f}  PnL={pnl:+.8f}  "
                f"hits={self._total_wins}  loss_streak={self._loss_streak}  "
                f"window=[{start},{end}]  bet={float(amt):.8f}"
            )

        return {
            "game":   "range-dice",
            "amount": format(amt, "f"),
            "range":  (start, end),
            "is_in":  True,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)

        try:
            self._live_bal = Decimal(str(result.get("balance", self._live_bal)))
        except Exception:
            pass

        won = bool(result.get("win"))
        if won:
            self._total_wins  += 1
            self._loss_streak  = 0
        else:
            self._loss_streak += 1
            if self._loss_streak > self._max_loss_streak:
                self._max_loss_streak = self._loss_streak

    # ── helpers ───────────────────────────────────────────────────────────

    def _size_bet(self, bal: Decimal) -> Decimal:
        raw = bal * Decimal(str(self.bet_frac))
        return self._clamp(raw, bal)

    def _clamp(self, amt: Decimal, bal: Decimal) -> Decimal:
        a = amt
        if self._abs_min is not None:
            a = max(a, self._abs_min)
        if self._abs_max is not None:
            a = min(a, self._abs_max)
        a = a.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        return max(a, Decimal("0.00000001"))

    def _pick_window(self) -> Tuple[int, int]:
        max_start = _DOMAIN - _WIDTH  # 9998

        if self.window_mode == "fixed":
            start = self.window_start

        elif self.window_mode == "sequential":
            start = self._seq_pos
            self._seq_pos = (self._seq_pos + self.step_size) % (max_start + 1)

        else:  # random
            start = self.ctx.rng.randint(0, max_start)

        return (start, start + _WIDTH - 1)


def _safe_dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")
