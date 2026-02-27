from __future__ import annotations
"""
Streak Pressure Hunter Strategy

A high-volatility 50/50 strategy that hunts "pressure zones" in recent outcome
history and deploys a controlled, capped escalation phase to capture large
single-bet profits before immediately de-risking.

═══════════════════════════════════════════════════════════════════════
THREE-PHASE LIFECYCLE
═══════════════════════════════════════════════════════════════════════

  OBSERVE ──► HUNT ──► COOLDOWN ──► OBSERVE ──► ...

  OBSERVE  : Micro-bets (observe_bet_pct% of balance) while monitoring
             outcome history for pattern pressure zones.

  HUNT     : Pattern detected → deploy up to max_hunt_steps escalating bets.
             Bet sizes: base × multiplier^step (step 0 … max_hunt_steps-1).
             Any win immediately ends the hunt → COOLDOWN.
             All steps exhausted without a win → back to OBSERVE with backoff.

  COOLDOWN : After any successful hit, revert to micro-bets for cooldown_steps
             bets to protect profits and reset pattern state.

═══════════════════════════════════════════════════════════════════════
PATTERN TRIGGERS (Pressure Zones)
═══════════════════════════════════════════════════════════════════════

  RUN      : N+ consecutive identical outcomes (e.g. WWWWW or LLLLL).
             Signals streak exhaustion — the run may break soon.

  ALT      : N+ consecutive alternating outcomes (WLWLWL…).
             Signals compression — the sequence may cluster soon.

  Both trigger the same hunt escalation; the trigger label is logged only.

═══════════════════════════════════════════════════════════════════════
SAFETY MECHANISMS
═══════════════════════════════════════════════════════════════════════

  • Hunts are strictly time-limited (max_hunt_steps bets max).
  • Escalation is purely multiplicative from base; no runaway chains.
  • Failed hunt back-off prevents immediately re-hunting an exhausted pattern.
  • Consecutive failed hunts trigger an extended cooldown.
  • Hunt buffer is cleared after each hunt cycle for a fresh pattern slate.
  • Session stop-loss / take-profit enforced by the engine's SessionLimits.

═══════════════════════════════════════════════════════════════════════
RISK PROFILE (default params, % of balance at time of hunt)
═══════════════════════════════════════════════════════════════════════

  Steps  1.5% → 3.75% → 9.4% → 23.4% → 58.6%
  Max total cost if ALL steps miss: ~96.7% of balance.
  → ONLY deploy at the suggested 5-step depth if bankroll ≥ 300 units.
  → For safety set max_hunt_steps = 3 or 4 and/or lower hunt_multiplier.
"""
from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import Any, Deque, Dict, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata


@register("streak-pressure-hunter")
class StreakPressureHunter:
    """50/50 streak-pattern hunter: observe → escalate → protect capital."""

    # ─────────────────────────────────────── class-level identity ──

    @classmethod
    def name(cls) -> str:
        return "streak-pressure-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "50/50 streak hunter: waits for run/alt pressure zones, deploys "
            "a capped escalating bet sequence, locks profit on any hit"
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Rare but Explosive",
            recommended_for="Advanced",
            pros=[
                "Uses only 50/50 bets — maximum per-bet win probability",
                "Pattern-gated entry reduces random constant hunting",
                "Strictly capped escalation prevents infinite martingale",
                "Immediate cooldown locks in profit after every successful hit",
                "Configurable risk: tune steps and multiplier to taste",
                "Extended cooldown auto-triggers after failed hunt clusters",
                "Session profit-target exits keep big gains intact",
            ],
            cons=[
                "Extreme variance; large swings expected per session",
                "Failed hunts at deep steps can consume 80–100% of bankroll",
                "Streak patterns offer correlation hints but no guarantees",
                "Requires large bankroll to survive multiple failed hunt cycles",
                "Deep escalation (step 4–5) is psychologically demanding",
                "Inherently negative EV like all escalation strategies",
            ],
            best_use_case=(
                "Advanced players seeking rare, explosive balance-growth events "
                "via 50/50 betting. Set a strict take-profit target (+200%–+500%) "
                "and hard stop-loss. Most sessions end flat or slightly negative; "
                "explosive sessions occur infrequently but dramatically."
            ),
            tips=[
                "Set strict stop-loss: -20% to -30% recommended",
                "Use take-profit: +200% to +500% for explosive-growth sessions",
                "Minimum bankroll: 300 units at default 5-step settings",
                "Lower risk: reduce max_hunt_steps to 3 or 4",
                "Lower hunt_multiplier (e.g. 2.0) for slower, safer escalation",
                "run_threshold 5, alt_threshold 7 are empirically tuned defaults",
                "cooldown_steps 40–60 gives good pattern-state reset time",
                "observe_window 20–30 is optimal for pattern sensitivity",
                "Never disable extended cooldown — it guards against tilt cycles",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "min_bet": {
                "type": "str",
                "default": "0.00000100",
                "desc": "Absolute minimum bet amount (floor for all bets)",
            },
            "observe_bet_pct": {
                "type": "float",
                "default": 0.001,
                "desc": "Observation bet as fraction of balance (0.001 = 0.1%)",
            },
            "observe_window": {
                "type": "int",
                "default": 25,
                "desc": "Outcome history depth for pattern detection (bets)",
            },
            "run_threshold": {
                "type": "int",
                "default": 5,
                "desc": "Consecutive identical outcomes needed to trigger a run-hunt",
            },
            "alt_threshold": {
                "type": "int",
                "default": 7,
                "desc": "Consecutive alternating outcomes needed to trigger an alt-hunt",
            },
            "hunt_base_pct": {
                "type": "float",
                "default": 0.015,
                "desc": "Hunt step-1 bet as fraction of balance (0.015 = 1.5%)",
            },
            "hunt_multiplier": {
                "type": "float",
                "default": 2.5,
                "desc": "Bet multiplier per hunt step (2.5 × each step)",
            },
            "max_hunt_steps": {
                "type": "int",
                "default": 5,
                "desc": "Maximum bets in a single hunt before aborting (hard cap)",
            },
            "cooldown_steps": {
                "type": "int",
                "default": 40,
                "desc": "Micro-bets after a successful hit (profit protection phase)",
            },
            "backoff_steps": {
                "type": "int",
                "default": 15,
                "desc": "Extra observe-bets after a failed hunt before re-scanning",
            },
            "max_failed_hunts": {
                "type": "int",
                "default": 3,
                "desc": "Consecutive failed hunts that trigger extended cooldown",
            },
            "extended_cooldown_steps": {
                "type": "int",
                "default": 80,
                "desc": "Micro-bets for extended cooldown after hunt failure cluster",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet High (True) or Low (False)",
            },
        }

    # ─────────────────────────────────────────────────── init ──

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        p = params

        self.min_bet = Decimal(str(p.get("min_bet", "0.00000100")))
        self.observe_bet_pct = float(p.get("observe_bet_pct", 0.001))
        self.observe_window = int(p.get("observe_window", 25))
        self.run_threshold = int(p.get("run_threshold", 5))
        self.alt_threshold = int(p.get("alt_threshold", 7))
        self.hunt_base_pct = float(p.get("hunt_base_pct", 0.015))
        self.hunt_multiplier = float(p.get("hunt_multiplier", 2.5))
        self.max_hunt_steps = int(p.get("max_hunt_steps", 5))
        self.cooldown_steps = int(p.get("cooldown_steps", 40))
        self.backoff_steps = int(p.get("backoff_steps", 15))
        self.max_failed_hunts = int(p.get("max_failed_hunts", 3))
        self.extended_cooldown_steps = int(p.get("extended_cooldown_steps", 80))
        self.is_high = bool(p.get("is_high", True))

        # Mutable state — fully reset in on_session_start
        self._buf: Deque[bool] = deque(maxlen=self.observe_window)
        self._phase: str = "observe"         # "observe" | "hunt" | "cooldown"
        self._hunt_step: int = 0             # current step index (0-based)
        self._hunt_trigger: str = ""         # description of pattern that fired
        self._cooldown_remaining: int = 0
        self._backoff_remaining: int = 0
        self._consecutive_failed: int = 0
        self._starting_balance: Decimal = Decimal("0")

        # Session stats
        self._total_bets: int = 0
        self._total_wins: int = 0
        self._total_hunts: int = 0
        self._successful_hunts: int = 0
        self._failed_hunts: int = 0
        self._deepest_step_hit: int = 0      # highest step index on a win

    # ──────────────────────────────────────────── lifecycle ──

    def on_session_start(self) -> None:
        self._buf.clear()
        self._phase = "observe"
        self._hunt_step = 0
        self._hunt_trigger = ""
        self._cooldown_remaining = 0
        self._backoff_remaining = 0
        self._consecutive_failed = 0
        self._starting_balance = Decimal(self.ctx.starting_balance)
        self._total_bets = 0
        self._total_wins = 0
        self._total_hunts = 0
        self._successful_hunts = 0
        self._failed_hunts = 0
        self._deepest_step_hit = 0

        # Display full hunt escalation schedule for transparency
        step_pcts = [
            self.hunt_base_pct * (self.hunt_multiplier ** s)
            for s in range(self.max_hunt_steps)
        ]
        total_risk_pct = sum(step_pcts) * 100
        step_labels = " → ".join(f"{p*100:.1f}%" for p in step_pcts)

        print(f"\n🎯 Streak Pressure Hunter | 50/50 Pattern Mode")
        print(f"   Observe: {self.observe_bet_pct*100:.2f}% bets | "
              f"Window: {self.observe_window} | "
              f"Run ≥ {self.run_threshold} | Alt ≥ {self.alt_threshold}")
        print(f"   Hunt escalation (% of balance): {step_labels}")
        print(f"   Max hunt cost if ALL {self.max_hunt_steps} steps fail: "
              f"~{total_risk_pct:.1f}% of balance")
        print(f"   Post-hit cooldown: {self.cooldown_steps} micro-bets | "
              f"Extended cooldown: {self.extended_cooldown_steps} micro-bets "
              f"(after {self.max_failed_hunts} consecutive failures)\n")

    def on_session_end(self, reason: str) -> None:
        current_bal = Decimal(self.ctx.current_balance_str())
        if self._starting_balance > 0:
            delta_pct = float(
                (current_bal - self._starting_balance) / self._starting_balance * 100
            )
        else:
            delta_pct = 0.0

        win_rate = self._total_wins / max(1, self._total_bets) * 100
        hunt_rate = (
            self._successful_hunts / max(1, self._total_hunts) * 100
            if self._total_hunts
            else 0.0
        )

        print(f"\n{'═'*60}")
        print(f"🏁 Streak Pressure Hunter | Session Complete")
        print(f"{'═'*60}")
        print(f"  Stop reason    : {reason}")
        print(f"  Total bets     : {self._total_bets}  (win rate {win_rate:.1f}%)")
        print(f"  Hunts launched : {self._total_hunts}")
        print(f"  Hunts won      : {self._successful_hunts}  ({hunt_rate:.0f}% hit rate)")
        print(f"  Hunts failed   : {self._failed_hunts}")
        print(f"  Deepest step   : {self._deepest_step_hit + 1} "
              f"/ {self.max_hunt_steps}")
        print(f"  Balance Δ      : {delta_pct:+.2f}%")
        print(f"{'═'*60}\n")

    # ──────────────────────────────────────── pattern detection ──

    def _run_streak(self) -> int:
        """Count consecutive identical outcomes at the tail of the buffer."""
        if len(self._buf) < 2:
            return 0
        buf = list(self._buf)
        last = buf[-1]
        count = 1
        for i in range(len(buf) - 2, -1, -1):
            if buf[i] == last:
                count += 1
            else:
                break
        return count

    def _alt_streak(self) -> int:
        """Count consecutive alternating outcomes at the tail of the buffer."""
        if len(self._buf) < 2:
            return 0
        buf = list(self._buf)
        count = 1
        for i in range(len(buf) - 1, 0, -1):
            if buf[i] != buf[i - 1]:
                count += 1
            else:
                break
        return count

    def _check_pattern(self) -> Tuple[bool, str]:
        """Return (should_hunt, trigger_description) based on current buffer.

        Requires at least half the observe_window before scanning to avoid
        triggering on insufficient data at session start.
        """
        min_data = max(self.run_threshold, self.alt_threshold)
        if len(self._buf) < min_data:
            return False, ""

        run = self._run_streak()
        if run >= self.run_threshold:
            return True, f"run×{run}"

        alt = self._alt_streak()
        if alt >= self.alt_threshold:
            return True, f"alt×{alt}"

        return False, ""

    # ─────────────────────────────────────────── bet sizing ──

    def _observe_bet_amount(self) -> Decimal:
        bal = Decimal(self.ctx.current_balance_str())
        return max(bal * Decimal(str(self.observe_bet_pct)), self.min_bet)

    def _hunt_bet_amount(self, step: int) -> Decimal:
        pct = self.hunt_base_pct * (self.hunt_multiplier ** step)
        bal = Decimal(self.ctx.current_balance_str())
        return max(bal * Decimal(str(pct)), self.min_bet)

    def _make_observe_spec(self) -> BetSpec:
        return BetSpec(
            game="dice",
            amount=str(self._observe_bet_amount()),
            chance="49.5",
            is_high=self.is_high,
        )

    # ─────────────────────────────────────────────── next_bet ──

    def next_bet(self) -> Optional[BetSpec]:
        self._total_bets += 1

        # ── COOLDOWN phase ────────────────────────────────────────────
        if self._phase == "cooldown":
            self._cooldown_remaining -= 1
            if self._cooldown_remaining <= 0:
                self._phase = "observe"
                print("✅ Cooldown complete — resuming observation")
            return self._make_observe_spec()

        # ── OBSERVE phase ─────────────────────────────────────────────
        if self._phase == "observe":
            if self._backoff_remaining > 0:
                self._backoff_remaining -= 1
                return self._make_observe_spec()

            fire, trigger = self._check_pattern()
            if not fire:
                return self._make_observe_spec()

            # Pattern detected — transition to HUNT immediately
            self._phase = "hunt"
            self._hunt_step = 0
            self._hunt_trigger = trigger
            self._total_hunts += 1
            bal = self.ctx.current_balance_str()
            print(
                f"\n🚨 HUNT #{self._total_hunts} | Pattern: {trigger} | "
                f"Balance: {bal}"
            )
            # Fall through to HUNT block below

        # ── HUNT phase ────────────────────────────────────────────────
        if self._phase == "hunt":
            step = self._hunt_step
            amount = self._hunt_bet_amount(step)
            step_pct = self.hunt_base_pct * (self.hunt_multiplier ** step) * 100
            print(
                f"   🏹 Step {step + 1}/{self.max_hunt_steps} | "
                f"Bet: {float(amount):.8f} ({step_pct:.1f}% of bal)"
            )
            return BetSpec(
                game="dice",
                amount=str(amount),
                chance="49.5",
                is_high=self.is_high,
            )

        # Fallback safety
        return self._make_observe_spec()

    # ────────────────────────────────────────── on_bet_result ──

    def on_bet_result(self, result: BetResult) -> None:
        win: bool = result.get("win", False)
        profit = Decimal(str(result.get("profit", "0")))
        balance_str = result.get("balance", self.ctx.starting_balance)

        if win:
            self._total_wins += 1

        # ── Observe / Cooldown: feed outcome into pattern buffer ───────
        if self._phase in ("observe", "cooldown"):
            self._buf.append(win)
            return

        # ── Hunt phase result ─────────────────────────────────────────
        if self._phase != "hunt":
            return

        step = self._hunt_step

        if win:
            # ✅ HIT — collect profit, enter cooldown
            self._successful_hunts += 1
            self._consecutive_failed = 0
            if step > self._deepest_step_hit:
                self._deepest_step_hit = step
            step_pct = self.hunt_base_pct * (self.hunt_multiplier ** step) * 100
            print(
                f"\n💥 HIT at step {step + 1}/{self.max_hunt_steps}! "
                f"+{float(profit):.8f} (bet was {step_pct:.1f}% of balance) "
                f"| Balance: {balance_str}"
            )
            self._phase = "cooldown"
            self._cooldown_remaining = self.cooldown_steps
            self._hunt_step = 0
            self._buf.clear()  # Fresh slate — don't re-detect same pressure zone

        else:
            # ❌ Miss — advance to next step or abort
            self._hunt_step += 1

            if self._hunt_step >= self.max_hunt_steps:
                # All hunt steps exhausted — hunt failed
                self._failed_hunts += 1
                self._consecutive_failed += 1
                print(
                    f"\n⚠️  Hunt #{self._total_hunts} FAILED "
                    f"(all {self.max_hunt_steps} steps missed) | "
                    f"Consecutive failures: {self._consecutive_failed}"
                )
                self._hunt_step = 0
                self._buf.clear()

                if self._consecutive_failed >= self.max_failed_hunts:
                    # Failure cluster → extended cooldown
                    self._phase = "cooldown"
                    self._cooldown_remaining = self.extended_cooldown_steps
                    print(
                        f"🚫 {self.max_failed_hunts} consecutive failures → "
                        f"{self.extended_cooldown_steps}-bet extended cooldown"
                    )
                else:
                    # Standard back-off
                    self._phase = "observe"
                    self._backoff_remaining = self.backoff_steps
                    print(
                        f"   ↩  Back-off: {self.backoff_steps} observe-bets "
                        f"before re-scanning"
                    )
