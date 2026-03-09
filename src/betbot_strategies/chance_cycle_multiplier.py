"""
Chance-Cycle Multiplier Strategy
═════════════════════════════════
A two-phase adaptive cycling strategy for provably-fair Dice games.

  ┌─────────────────────────────────────────────────────────────────────┐
  │  Phase 1 — AGGRESSIVE  (Multiplication)                             │
  │  Low chance 15–25 % → payout 4×–6.6×                               │
  │  Bet 1.5–3 % of balance.  Aim: +50–200 % wave on hot streak.       │
  ├─────────────────────────────────────────────────────────────────────┤
  │  Phase 2 — RECOVERY    (Grinding)                                   │
  │  High chance 80–95 % → payout 1.04×–1.24×                          │
  │  Bet 0.5–1 % base, ×1.35 after each loss (capped at 25 % balance). │
  │  Aim: climb back to 95 %+ of recent peak.                          │
  └─────────────────────────────────────────────────────────────────────┘

  Switching rules
  ───────────────
  Aggressive → Recovery :  4+ consecutive losses  OR  balance falls
                            >22 % below session high.
  Recovery   → Aggressive:  balance recovers to ≥ 95 % of session high.

  Hard limits
  ───────────
  Stop-loss  : −40 % of starting balance → session ends.
  Profit lock: +30 % reached → reduce aggressive bet to 1 % and protect.

  ⚠  WARNING  ⚠
  Dice games carry a ~1 % house edge on every bet.  No strategy removes
  this edge.  Variance CAN still bust any bankroll.  Never bet more than
  you can afford to lose.  Gamble responsibly.
"""

from __future__ import annotations

import random
from decimal import ROUND_DOWN, Decimal
from typing import Any, Dict, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata


# ─────────────────────────────────────────────────────────────────────────────

class _Phase:
    AGGRESSIVE = "aggressive"
    RECOVERY   = "recovery"


@register("chance-cycle-multiplier")
class ChanceCycleMultiplier:
    """
    Chance-Cycle Multiplier: two-phase cycling strategy.

    Alternates between a low-chance multiplication phase (hunt big payouts on
    streaks) and a high-chance grinding recovery phase (mild progression to
    claw back losses).  The key mechanic is deliberately changing the win-
    chance %: low chance = high payout potential; high chance = capital safety.

    Parameters
    ----------
    base_bet_pct : float (default 0.02)
        Starting bet in Phase 1 as a fraction of balance (0.02 = 2 %).
    aggressive_chance : float (default 20.0)
        Win-chance % to use in the Aggressive phase (15–25 recommended).
    recovery_chance : float (default 88.0)
        Win-chance % to use in the Recovery phase (80–95 recommended).
    recovery_loss_mult : float (default 1.35)
        Multiplier applied to the Recovery bet after each loss (1.30–1.50).
    recovery_bet_cap : float (default 0.25)
        Maximum single bet as fraction of balance in Recovery phase (0.25 = 25 %).
    loss_streak_trigger : int (default 4)
        Consecutive losses in Aggressive phase that force a switch to Recovery.
    drawdown_trigger : float (default 0.22)
        Fractional drop from session high that forces a switch to Recovery (0.22 = 22 %).
    recovery_target : float (default 0.95)
        Recovery phase exits when balance ≥ session_high × this value.
    stop_loss_pct : float (default 0.40)
        Session ends when balance drops this far below starting value (0.40 = 40 %).
    profit_lock_pct : float (default 0.30)
        When profit reaches this level, halve aggressive bet as protection (0.30 = 30 %).
    seed : int (optional)
        RNG seed for reproducible sessions.
    """

    _MIN_BET = Decimal("0.00000001")

    # ── Protocol methods ──────────────────────────────────────────────────────

    @classmethod
    def name(cls) -> str:
        return "chance-cycle-multiplier"

    @classmethod
    def describe(cls) -> str:
        return (
            "Chance-Cycle Multiplier: alternates between a low-chance "
            "multiplication phase (15–25%, 4×–6.6× payout) and a high-chance "
            "grinding recovery phase (80–95%, 1.04×–1.24× payout) with mild "
            "loss progression.  Key mechanic: deliberately changing chance %."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium–High",
            bankroll_required="Medium (200–500× base bet recommended)",
            volatility="High in Aggressive phase, Low in Recovery",
            time_to_profit="Variable — session target +30–100 %",
            recommended_for="Intermediate players who understand variance",
            pros=[
                "Aggressive phase captures big wins on hot streaks",
                "Recovery phase uses mild (not full Martingale) progression",
                "Hard stop-loss and profit-lock protect the bankroll",
                "Chance % cycling is transparent and easy to follow manually",
                "Works equally well for manual play or auto-bet scripts",
            ],
            cons=[
                "~1 % house edge still applies on every single bet",
                "Aggressive phase variance can lose several bets in a row",
                "Recovery progression can still hit the 25 % cap in deep runs",
                "NOT a long-term profitable system — house edge grinds all edges",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_pct": {
                "type": "float", "default": 0.010,
                "min": 0.001, "max": 0.10,
                "help": "Aggressive phase base bet as fraction of balance (0.01 = 1 %)",
            },
            "aggressive_chance": {
                "type": "float", "default": 25.0,
                "min": 10.0, "max": 30.0,
                "help": "Win chance % in Aggressive phase (15–25 recommended)",
            },
            "recovery_chance": {
                "type": "float", "default": 88.0,
                "min": 70.0, "max": 97.0,
                "help": "Win chance % in Recovery phase (80–95 recommended)",
            },
            "recovery_loss_mult": {
                "type": "float", "default": 1.35,
                "min": 1.10, "max": 1.60,
                "help": "Bet multiplier after each Recovery loss (never full double)",
            },
            "recovery_bet_cap": {
                "type": "float", "default": 0.25,
                "min": 0.05, "max": 0.50,
                "help": "Max single bet as fraction of balance in Recovery (25 % cap)",
            },
            "loss_streak_trigger": {
                "type": "int", "default": 4,
                "min": 2, "max": 10,
                "help": "Consecutive losses in Aggressive phase that trigger Recovery",
            },
            "drawdown_trigger": {
                "type": "float", "default": 0.22,
                "min": 0.10, "max": 0.40,
                "help": "Drop from session high that triggers Recovery (0.22 = 22 %)",
            },
            "recovery_target": {
                "type": "float", "default": 0.95,
                "min": 0.80, "max": 1.00,
                "help": "Recovery exits when balance >= session_high × this value",
            },
            "stop_loss_pct": {
                "type": "float", "default": 0.40,
                "min": 0.10, "max": 0.90,
                "help": "Hard stop: session ends at this fractional loss from start",
            },
            "profit_lock_pct": {
                "type": "float", "default": 0.30,
                "min": 0.10, "max": 2.0,
                "help": "Profit fraction at which aggressive bet is halved",
            },
            "seed": {
                "type": "int", "default": None,
                "help": "RNG seed for reproducible sessions",
            },
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self._base_bet_pct       = Decimal(str(params.get("base_bet_pct",       0.020)))
        self._agg_chance         = float(params.get("aggressive_chance",        20.0))
        self._rec_chance         = float(params.get("recovery_chance",          88.0))
        self._rec_loss_mult      = Decimal(str(params.get("recovery_loss_mult", 1.35)))
        self._rec_cap            = Decimal(str(params.get("recovery_bet_cap",   0.25)))
        self._loss_streak_trigger = int(params.get("loss_streak_trigger",       4))
        self._drawdown_trigger   = Decimal(str(params.get("drawdown_trigger",   0.22)))
        self._recovery_target    = Decimal(str(params.get("recovery_target",    0.95)))
        self._stop_loss_pct      = Decimal(str(params.get("stop_loss_pct",      0.40)))
        self._profit_lock_pct    = Decimal(str(params.get("profit_lock_pct",    0.30)))

        seed = params.get("seed")
        self._rng = random.Random(seed) if seed is not None else random.Random()

        # Runtime state (populated in on_session_start)
        self._start_bal:   Decimal = Decimal("0")
        self._current_bal: Decimal = Decimal("0")
        self._session_high: Decimal = Decimal("0")  # peak balance this session

        self._phase          = _Phase.AGGRESSIVE
        self._loss_streak    = 0                    # consecutive losses in current phase
        self._total_bets     = 0
        self._phase_bets     = 0                    # bets spent in current phase
        self._cycles_done    = 0                    # full A→R→A cycles completed

        # Recovery phase: current base bet (resets on phase entry or win)
        self._rec_current_bet: Decimal = Decimal("0")

        self._profit_locked  = False    # True once profit_lock_pct hit

    def on_session_start(self) -> None:
        self._start_bal    = Decimal(self.ctx.starting_balance)
        self._current_bal  = Decimal(self.ctx.starting_balance)
        self._session_high = Decimal(self.ctx.starting_balance)

        self._phase        = _Phase.AGGRESSIVE
        self._loss_streak  = 0
        self._total_bets   = self._phase_bets = self._cycles_done = 0
        self._profit_locked = False
        self._reset_recovery_bet()

        self.ctx.printer(
            f"[Chance-Cycle Multiplier] Session started | "
            f"Balance: {float(self._start_bal):.8f} | "
            f"Phase: AGGRESSIVE ({self._agg_chance:.1f}% chance)"
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    def next_bet(self) -> Optional[BetSpec]:
        self._current_bal = self._read_balance()

        if self._check_hard_limits():
            return None

        self._evaluate_phase_switch()

        if self._phase == _Phase.AGGRESSIVE:
            return self._build_aggressive_bet()
        else:
            return self._build_recovery_bet()

    def on_bet_result(self, result: BetResult) -> None:
        won = result.get("win", False)
        bal = result.get("balance", str(self._current_bal))

        self._current_bal  = Decimal(str(bal))
        self._session_high = max(self._session_high, self._current_bal)
        self._total_bets  += 1
        self._phase_bets  += 1

        if won:
            self._loss_streak = 0
            if self._phase == _Phase.RECOVERY:
                # Win in Recovery: reset progression bet back to phase entry level
                self._reset_recovery_bet()
        else:
            self._loss_streak += 1
            if self._phase == _Phase.RECOVERY:
                # Escalate the recovery bet by multiplier (mild progression)
                self._rec_current_bet = min(
                    self._rec_current_bet * self._rec_loss_mult,
                    self._current_bal * self._rec_cap,
                )
                self._rec_current_bet = max(self._rec_current_bet, self._MIN_BET)

    def on_session_end(self, reason: str) -> None:
        pnl  = self._current_bal - self._start_bal
        sign = "+" if pnl >= 0 else ""
        self.ctx.printer(
            f"[Chance-Cycle Multiplier] Session ended: {reason} | "
            f"P&L: {sign}{float(pnl):.8f} | "
            f"Bets: {self._total_bets} | Cycles: {self._cycles_done} | "
            f"Peak: {float(self._session_high):.8f}"
        )

    # ── Phase switching ───────────────────────────────────────────────────────

    def _evaluate_phase_switch(self) -> None:
        bal   = self._current_bal
        high  = self._session_high
        phase = self._phase

        if phase == _Phase.AGGRESSIVE:
            # → Recovery on: 4+ consecutive losses OR >22% drawdown from peak
            drawdown = (high - bal) / high if high > 0 else Decimal("0")
            if self._loss_streak >= self._loss_streak_trigger or drawdown >= self._drawdown_trigger:
                self._switch_phase(_Phase.RECOVERY)

        else:  # RECOVERY
            # → Aggressive on: balance ≥ 95% of session peak
            if high > 0 and bal >= high * self._recovery_target:
                self._switch_phase(_Phase.AGGRESSIVE)
                self._cycles_done += 1

    def _switch_phase(self, new_phase: str) -> None:
        old_label = "AGGRESSIVE" if self._phase == _Phase.AGGRESSIVE else "RECOVERY"
        new_label = "AGGRESSIVE" if new_phase == _Phase.AGGRESSIVE else "RECOVERY"

        self._phase       = new_phase
        self._phase_bets  = 0
        self._loss_streak = 0

        if new_phase == _Phase.RECOVERY:
            self._reset_recovery_bet()
            self.ctx.printer(
                f"[Chance-Cycle] {old_label} → {new_label}  "
                f"(bet #{self._total_bets}) | "
                f"Bal: {float(self._current_bal):.8f} | "
                f"Peak: {float(self._session_high):.8f} | "
                f"Recovery chance: {self._rec_chance:.1f}%"
            )
        else:
            self.ctx.printer(
                f"[Chance-Cycle] {old_label} → {new_label}  "
                f"(bet #{self._total_bets}, cycle #{self._cycles_done + 1}) | "
                f"Bal: {float(self._current_bal):.8f} | "
                f"Aggressive chance: {self._agg_chance:.1f}%"
            )

    # ── Bet builders ──────────────────────────────────────────────────────────

    def _build_aggressive_bet(self) -> BetSpec:
        """
        Phase 1 — Aggressive / Multiplication.
        Chance: 15–25 %.  Bet: 1.5–3 % of current balance (compounding).
        After profit_lock_pct is hit, bet size is halved as protection.
        """
        # Slight random jitter on both chance and bet size for variety
        chance  = self._agg_chance + self._rng.uniform(-2.0, 2.0)
        chance  = max(10.0, min(30.0, chance))

        bet_pct = self._base_bet_pct
        if self._profit_locked:
            bet_pct = bet_pct * Decimal("0.5")  # halve size after profit lock

        # Compound: bet off current balance
        amount = self._current_bal * bet_pct
        amount = max(amount, self._MIN_BET)

        return {
            "game":    "dice",
            "amount":  str(amount.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)),
            "chance":  f"{chance:.2f}",
            "is_high": self._rng.random() > 0.5,
        }

    def _build_recovery_bet(self) -> BetSpec:
        """
        Phase 2 — Recovery / Grinding.
        Chance: 80–95 %.  Bet: starts at 0.5–1 % of balance, escalates ×1.35
        after each loss (mild progression), hard-capped at 25 % of balance.
        Resets to base on every win.
        """
        chance = self._rec_chance + self._rng.uniform(-1.5, 1.5)
        chance = max(70.0, min(97.0, chance))

        # Cap the current progressive bet at 25% of balance
        amount = min(self._rec_current_bet, self._current_bal * self._rec_cap)
        amount = max(amount, self._MIN_BET)

        return {
            "game":    "dice",
            "amount":  str(amount.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)),
            "chance":  f"{chance:.2f}",
            "is_high": self._rng.random() > 0.5,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _reset_recovery_bet(self) -> None:
        """Set recovery base bet to 0.5–1 % of current balance."""
        base = self._current_bal if self._current_bal > 0 else self._start_bal
        # Start at roughly half the aggressive base (conservative entry)
        self._rec_current_bet = base * (self._base_bet_pct * Decimal("0.40"))
        self._rec_current_bet = max(self._rec_current_bet, self._MIN_BET)

    def _read_balance(self) -> Decimal:
        if self.ctx.recent_results:
            last = self.ctx.recent_results[-1]
            raw  = last.get("balance")
            if raw:
                return Decimal(str(raw))
        return self._current_bal if self._current_bal > 0 else self._start_bal

    def _check_hard_limits(self) -> bool:
        """Return True (and stop) if stop-loss or profit-lock threshold hit."""
        if self._start_bal == 0:
            return False

        pct = (self._current_bal - self._start_bal) / self._start_bal

        # Hard stop-loss: −40 %
        if pct <= -self._stop_loss_pct:
            self.ctx.printer(
                f"[Chance-Cycle] ⛔ HARD STOP-LOSS hit "
                f"({float(pct):.1%} from start).  Ending session."
            )
            return True

        # Profit lock: reduce aggression once +30 % reached
        if not self._profit_locked and pct >= self._profit_lock_pct:
            self._profit_locked = True
            self.ctx.printer(
                f"[Chance-Cycle] 🔒 PROFIT LOCK engaged at "
                f"+{float(pct):.1%}.  Aggressive bet halved.  "
                f"Consider withdrawing half your profits!"
            )

        return False
