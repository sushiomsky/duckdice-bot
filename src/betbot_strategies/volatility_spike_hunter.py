from __future__ import annotations
"""
Volatility Spike Hunter Strategy
=================================
A quant-grade, deterministic dice betting engine engineered to:
  1. Hunt only inside statistically open "volatility windows"
  2. Produce rare but large (+10% to +500%) balance spikes on each successful hit
  3. Never chase losses or escalate beyond hard per-cycle limits
  4. Operate via a 3-phase state machine: PROBE → LOAD → SNIPE

─────────────────────────────────────────────────────────────────────────────
PHILOSOPHY
─────────────────────────────────────────────────────────────────────────────
Every cycle is a bounded, pre-accepted-loss bet placed at a statistically
favorable moment.  Profit comes from timing and sizing, not from frequency.
Losses are the cost of waiting.  Survival > Frequency > Profit magnitude.

Expected equity curve: long flat / slightly-declining stretches with sharp
upward spikes on the rare cycles that hit.

─────────────────────────────────────────────────────────────────────────────
CORE MATH
─────────────────────────────────────────────────────────────────────────────
DuckDice house edge: 1%
  effective payout multiplier = 99.0 / chance_pct

Profit from a winning bet:
  profit = bet_amount × (payout_mult − 1)
         = bet_amount × (99.0/chance_pct − 1)

To hit a desired profit of  P = balance × target_ratio:
  With a given bet fraction  f = bet_amount / balance:
    payout_mult_needed = target_ratio / f + 1
    chance_pct         = 99.0 / payout_mult_needed

  After clamping chance to the phase range, recompute bet to preserve target:
    bet_amount = (balance × target_ratio) / (99.0/chance_pct − 1)
    clamp bet_amount to [bet_min_frac, bet_max_frac] × balance

Bet-size hard limits:
  Minimum : 0.2% of current balance  (never tiny)
  Maximum : 2.0% of current balance  (never ruinous)

─────────────────────────────────────────────────────────────────────────────
VOLATILITY WINDOW DETECTION
─────────────────────────────────────────────────────────────────────────────
Two complementary metrics are computed over a rolling window of recent bets:

1. Poisson Z-score (measures statistical deficit of wins):
     expected_hits = Σ (chance_i / 100)   for each bet in rolling window
     actual_hits   = count of wins in window
     std           = √(expected_hits)      (Poisson std ≈ √λ)
     z             = (actual_hits − expected_hits) / std
     → z < −1.2  means we are statistically underperforming expectation
     → the more negative, the more "overdue" the window is

2. Cold-streak ratio (measures how overdue the current chance level is):
     expected_per_win = 100.0 / chance_pct
     cold_ratio       = bets_since_last_win / expected_per_win
     → cold_ratio > 1.5  means we have gone 1.5× the expected wait without a hit

A volatility window is OPEN when EITHER condition is true.
Outside an open window, the strategy stays PASSIVE (minimal observation bets).

─────────────────────────────────────────────────────────────────────────────
STATE MACHINE
─────────────────────────────────────────────────────────────────────────────
  PASSIVE  →  Window closed: place minimal bets to feed rolling window stats.
              Transitions to PROBE when a volatility window opens.

  PROBE    →  Phase A: medium-low chance (0.8%–3.0%), minimum bet size.
              Target profit: 10%–30% of balance.
              Confirm window is still open.  Advance to LOAD after phase limit.

  LOAD     →  Phase B: lower chance (0.3%–0.8%), ramping bet size.
              Target profit: 25%–100% of balance.
              Continue if window holds.  Advance to SNIPE after phase limit.

  SNIPE    →  Phase C: lowest chance (0.1%–0.5%), maximum bet size.
              Target profit: 100%–500% of balance.
              Abort after snipe attempt limit exhausted.

  COOLDOWN →  After any cycle end (hit OR abort): flat minimal bets for
              200–500 rolls to let the RNG normalize and prevent clustering.
              Returns to PASSIVE when complete.

─────────────────────────────────────────────────────────────────────────────
CYCLE GUARDS
─────────────────────────────────────────────────────────────────────────────
  Max loss per cycle  : 5% of balance at cycle start  (configurable)
  Max bets per cycle  : 300                           (configurable)
  Hard session stop   : 25% drawdown from peak balance (configurable)

On any abort condition the cycle ends immediately → cooldown → back to PASSIVE.
There is NO escalation, NO recovery attempt, NO martingale.
"""

import math
from collections import deque
from decimal import Decimal, ROUND_DOWN
from typing import Any, Deque, Dict, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

# ─────────────────────────────────────────────────── Tunable constants ──────

# DuckDice house edge / effective multiplier base
_HOUSE_EDGE_PCT  = 1.0
_EFFECTIVE_MULT  = 99.0       # 100 − house_edge

# ── Chance bounds per phase (percent) ────────────────────────────────────────
_PROBE_CHANCE_MIN  = 0.80     # Phase A lower bound
_PROBE_CHANCE_MAX  = 3.00     # Phase A upper bound
_LOAD_CHANCE_MIN   = 0.30     # Phase B lower bound
_LOAD_CHANCE_MAX   = 0.80     # Phase B upper bound
_SNIPE_CHANCE_MIN  = 0.10     # Phase C lower bound
_SNIPE_CHANCE_MAX  = 0.50     # Phase C upper bound

# ── Target profit bounds per phase (fraction of balance) ─────────────────────
_PROBE_TARGET_MIN  = 0.10     # Phase A floor   (10%)
_PROBE_TARGET_MAX  = 0.30     # Phase A ceiling (30%) — overridden by param
_LOAD_TARGET_MIN   = 0.25     # Phase B floor   (25%)
_LOAD_TARGET_MAX   = 1.00     # Phase B ceiling (100%) — overridden by param
_SNIPE_TARGET_MIN  = 1.00     # Phase C floor   (100%)
_SNIPE_TARGET_MAX  = 5.00     # Phase C ceiling (500%) — overridden by param

# ── Bet size hard limits (fraction of balance) ────────────────────────────────
_BET_MIN_FRAC  = 0.002        # 0.2% absolute floor
_BET_MAX_FRAC  = 0.020        # 2.0% absolute ceiling

# ── Cycle / phase progression limits ─────────────────────────────────────────
_PROBE_MAX_BETS    = 80       # Phase A max bets before advancing to Load
_LOAD_MAX_BETS     = 120      # Phase B max bets before advancing to Snipe
_SNIPE_MAX_BETS    = 100      # Phase C max attempts before aborting cycle

# ── Session / cycle hard guards ───────────────────────────────────────────────
_CYCLE_MAX_LOSS_FRAC  = 0.05  # Default max loss per cycle (5% of cycle-start balance)
_CYCLE_MAX_BETS       = 300   # Default max bets per hunt cycle
_SESSION_DRAWDOWN     = 0.25  # Default hard-stop at 25% drawdown from peak

# ── Cooldown lengths (in bets) ────────────────────────────────────────────────
_COOLDOWN_MIN = 200
_COOLDOWN_MAX = 500

# ── Volatility window thresholds ─────────────────────────────────────────────
_ZSCORE_THRESHOLD      = -1.2   # z below this → window open
_COLD_RATIO_THRESHOLD  =  1.5   # cold_ratio above this → window open
_ROLLING_WINDOW_MIN    =  300   # minimum allowed rolling window
_ROLLING_WINDOW_MAX    = 2000   # maximum allowed rolling window
_MIN_WINDOW_DATA       =   50   # minimum entries before window detection activates

# ── Cooldown chance (flat, safe, not 50%) ────────────────────────────────────
_COOLDOWN_CHANCE = 2.0          # 2% during cooldown → 48.5× payout


@register("volatility-spike-hunter")
class VolatilitySpikeHunter:
    """
    Quant-grade dice strategy: hunts volatility windows for rare +10%–500% spikes.

    No martingale.  No loss chasing.  All risk bounded per cycle.
    Losses are the cost of waiting for high-probability-of-misalignment moments.
    """

    # ──────────────────────────────────────────────── class-level API ─────────

    @classmethod
    def name(cls) -> str:
        return "volatility-spike-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Hunts statistically open volatility windows for rare +10%–500% balance "
            "spikes. 3-phase state machine (Probe→Load→Snipe). No martingale. "
            "Bounded cycle losses (5% default). Hard 25% drawdown session stop."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Rare but Large",
            recommended_for="Expert",
            pros=[
                "No martingale or loss-chasing — losses bounded per cycle",
                "Profit spikes of +10% to +500% per successful hit",
                "Dual volatility detection: Poisson z-score + cold-streak ratio",
                "3-phase machine (Probe→Load→Snipe) controls risk progression",
                "Hard 25% drawdown session stop prevents catastrophic loss",
                "Bet sizing always 0.2%–2% of balance — no single bet can ruin you",
                "Post-hit cooldown (200–500 bets) prevents streak-chasing",
                "Fully deterministic and auditable math — no magic",
            ],
            cons=[
                "Most cycles end in controlled losses (that is the design)",
                "Long flat or declining periods between profit spikes",
                "Extreme patience required — psychologically demanding",
                "Large bankroll needed to absorb multi-cycle drawdown",
                "Negative expected value per bet — house edge is unavoidable",
                "No guaranteed recovery — this is not a recovery system",
            ],
            best_use_case=(
                "Expert players with large bankrolls seeking occasional large balance "
                "multiplications. Treats gambling as a bounded-loss probability exercise, "
                "not a recovery game. One successful snipe covers many losing cycles."
            ),
            tips=[
                "Bankroll should be 500× minimum bet for session survival",
                "Expect 80–95% of cycles to end without a hit (that is normal)",
                "Each snipe hit at +100–500% covers dozens of probe cycles",
                "Never manually override cooldown — it prevents tilt and streak-chasing",
                "rolling_window: smaller=faster/noisier, larger=smoother/slower",
                "snipe_target_max=2.0 is more achievable than 5.0 — tune to taste",
                "Set engine stop_loss to −30% to −50% to survive multi-cycle variance",
                "Use is_high=True (default) or False — direction does not affect math",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "rolling_window": {
                "type": "int",
                "default": 500,
                "desc": "Rolling window size for z-score (300–2000). Larger = smoother response.",
            },
            "zscore_threshold": {
                "type": "float",
                "default": -1.2,
                "desc": "Z-score below this value opens a volatility window. Range: −0.5 (loose) to −2.5 (strict).",
            },
            "cold_ratio_threshold": {
                "type": "float",
                "default": 1.5,
                "desc": "Cold-streak multiplier that opens window. 1.5 = 50% overdue. Range: 1.0–3.0.",
            },
            "probe_target_max": {
                "type": "float",
                "default": 0.30,
                "desc": "Phase A max target profit as fraction of balance (0.30 = 30%). Range: 0.10–0.50.",
            },
            "load_target_max": {
                "type": "float",
                "default": 1.00,
                "desc": "Phase B max target profit as fraction of balance (1.00 = 100%). Range: 0.25–2.00.",
            },
            "snipe_target_max": {
                "type": "float",
                "default": 3.00,
                "desc": "Phase C max target profit as fraction of balance (3.00 = 300%). Max 5.00.",
            },
            "cycle_max_loss_pct": {
                "type": "float",
                "default": 5.0,
                "desc": "Maximum loss per hunt cycle as % of cycle-start balance. Default 5%.",
            },
            "cycle_max_bets": {
                "type": "int",
                "default": 300,
                "desc": "Maximum bets allowed per hunt cycle before forced abort.",
            },
            "session_drawdown_pct": {
                "type": "float",
                "default": 25.0,
                "desc": "Hard session stop when drawdown from peak reaches this %. Default 25%.",
            },
            "cooldown_min": {
                "type": "int",
                "default": 200,
                "desc": "Minimum flat bets in cooldown after any cycle end.",
            },
            "cooldown_max": {
                "type": "int",
                "default": 500,
                "desc": "Maximum flat bets in cooldown (randomized each time).",
            },
            "min_bet_pct": {
                "type": "float",
                "default": 0.2,
                "desc": "Hard floor for bet size as % of balance. Default 0.2%.",
            },
            "max_bet_pct": {
                "type": "float",
                "default": 2.0,
                "desc": "Hard ceiling for bet size as % of balance. Default 2.0%.",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet direction: True = High, False = Low. Does not affect math.",
            },
        }

    # ─────────────────────────────────────────────────── __init__ ─────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        # ── User-configurable parameters ──────────────────────────────────────
        self.rolling_window      = int(  params.get("rolling_window",       500))
        self.zscore_threshold    = float(params.get("zscore_threshold",    -1.2))
        self.cold_ratio_thresh   = float(params.get("cold_ratio_threshold", 1.5))
        self.probe_target_max    = float(params.get("probe_target_max",    0.30))
        self.load_target_max     = float(params.get("load_target_max",     1.00))
        self.snipe_target_max    = min(5.0, float(params.get("snipe_target_max", 3.00)))
        self.cycle_max_loss_frac = float(params.get("cycle_max_loss_pct",   5.0)) / 100.0
        self.cycle_max_bets      = int(  params.get("cycle_max_bets",       300))
        self.session_drawdown    = float(params.get("session_drawdown_pct", 25.0)) / 100.0
        self.cooldown_min        = int(  params.get("cooldown_min",         200))
        self.cooldown_max        = int(  params.get("cooldown_max",         500))
        self.bet_min_frac        = float(params.get("min_bet_pct",          0.2)) / 100.0
        self.bet_max_frac        = float(params.get("max_bet_pct",          2.0)) / 100.0
        self.is_high             = bool( params.get("is_high",              True))

        # Clamp rolling window to valid range
        self.rolling_window = max(_ROLLING_WINDOW_MIN, min(_ROLLING_WINDOW_MAX, self.rolling_window))
        # Clamp bet limits to hard-coded safety bounds
        self.bet_min_frac = max(_BET_MIN_FRAC, self.bet_min_frac)
        self.bet_max_frac = min(_BET_MAX_FRAC, self.bet_max_frac)

        # ── Rolling window: each entry is (chance_pct: float, won: bool) ───────
        # This feeds both the Poisson z-score and cold-streak computations.
        self._window: Deque[Tuple[float, bool]] = deque(maxlen=self.rolling_window)

        # ── Session-level state ───────────────────────────────────────────────
        self._phase:         str     = "PASSIVE"
        self._total_bets:    int     = 0
        self._total_wins:    int     = 0
        self._total_cycles:  int     = 0
        self._cycle_hits:    int     = 0
        self._starting_bal:  Decimal = Decimal("0")
        self._peak_bal:      Decimal = Decimal("0")
        self._live_bal:      Decimal = Decimal("0")

        # ── Cycle state ───────────────────────────────────────────────────────
        # Reset at each new hunt cycle via _start_cycle().
        self._cycle_bets:         int     = 0
        self._cycle_start_bal:    Decimal = Decimal("0")
        self._cycle_max_loss_abs: Decimal = Decimal("0")
        self._cycle_loss:         Decimal = Decimal("0")
        self._phase_bets:         int     = 0   # bets completed in current phase

        # Current bet parameters (set by each phase's bet factory)
        self._current_chance:       float = _PROBE_CHANCE_MAX
        self._current_target_ratio: float = _PROBE_TARGET_MIN

        # ── Cooldown state ────────────────────────────────────────────────────
        self._cooldown_remaining: int = 0

        # ── Cold-streak tracking ──────────────────────────────────────────────
        # Number of bets placed (any phase) since the last win (any chance).
        # Used for cold_ratio = bets_since_last_win / expected_per_win.
        self._bets_since_last_win: int = 0

    # ──────────────────────────────────────────────── session lifecycle ────────

    def on_session_start(self) -> None:
        bal = _dec(self.ctx.starting_balance or "0")
        self._starting_bal  = bal
        self._peak_bal      = bal
        self._live_bal      = bal
        self._phase         = "PASSIVE"
        self._total_bets    = 0
        self._total_wins    = 0
        self._total_cycles  = 0
        self._cycle_hits    = 0
        self._cooldown_remaining  = 0
        self._bets_since_last_win = 0
        self._window.clear()
        self._reset_cycle_counters()

        self.ctx.printer(
            f"\n{'═' * 64}\n"
            f"  🎯 VOLATILITY SPIKE HUNTER  |  session started\n"
            f"  Balance       : {bal:.8f}\n"
            f"  Bet range     : {self.bet_min_frac*100:.1f}% – {self.bet_max_frac*100:.1f}% of balance\n"
            f"  Cycle limits  : max_loss={self.cycle_max_loss_frac*100:.1f}%  max_bets={self.cycle_max_bets}\n"
            f"  Session stop  : {self.session_drawdown*100:.0f}% drawdown from peak\n"
            f"  Window params : z<{self.zscore_threshold}  OR  cold_ratio>{self.cold_ratio_thresh}×\n"
            f"  Rolling window: {self.rolling_window} bets\n"
            f"  Target range  : Probe +{self.probe_target_max*100:.0f}%  "
            f"Load +{self.load_target_max*100:.0f}%  "
            f"Snipe +{self.snipe_target_max*100:.0f}%\n"
            f"{'═' * 64}\n"
        )

    def on_session_end(self, reason: str) -> None:
        start = self._starting_bal
        final = self._live_bal
        pnl   = final - start
        pct   = float(pnl / start * 100) if start else 0.0
        sign  = "+" if pnl >= 0 else ""
        dd    = _drawdown(self._peak_bal, final)
        self.ctx.printer(
            f"\n{'═' * 64}\n"
            f"  🏁 VOLATILITY SPIKE HUNTER  |  {reason}\n"
            f"  Total bets    : {self._total_bets}\n"
            f"  Total wins    : {self._total_wins}\n"
            f"  Cycles run    : {self._total_cycles}\n"
            f"  Cycle hits    : {self._cycle_hits}\n"
            f"  PnL           : {sign}{pnl:.8f}  ({sign}{pct:.2f}%)\n"
            f"  Max drawdown  : {dd*100:.1f}%\n"
            f"{'═' * 64}\n"
        )

    # ──────────────────────────────────────────────────── next_bet ────────────

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._live_bal
        if bal <= 0:
            return None

        # ── Hard session stop: 25% drawdown from peak ─────────────────────────
        dd = _drawdown(self._peak_bal, bal)
        if dd >= self.session_drawdown:
            self.ctx.printer(
                f"[VSH] ⛔ HARD STOP — drawdown {dd*100:.1f}% ≥ "
                f"{self.session_drawdown*100:.0f}% — session ended"
            )
            return None

        self._total_bets += 1

        # ── Route to active phase ─────────────────────────────────────────────
        if self._phase == "PASSIVE":
            return self._bet_passive(bal)
        elif self._phase == "PROBE":
            return self._bet_probe(bal)
        elif self._phase == "LOAD":
            return self._bet_load(bal)
        elif self._phase == "SNIPE":
            return self._bet_snipe(bal)
        elif self._phase == "COOLDOWN":
            return self._bet_cooldown(bal)
        else:
            # Defensive fallback — should never reach here
            self._phase = "PASSIVE"
            return self._bet_passive(bal)

    # ──────────────────────────────────────────────── on_bet_result ───────────

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)

        # ── Update live balance and peak ──────────────────────────────────────
        try:
            self._live_bal = Decimal(str(result.get("balance", self._live_bal)))
        except Exception:
            pass
        if self._live_bal > self._peak_bal:
            self._peak_bal = self._live_bal

        won = bool(result.get("win"))

        # ── Record this bet into the rolling window ───────────────────────────
        # We use the chance we intended (self._current_chance) since the API
        # may round internally; this ensures our stats reflect our own sizing logic.
        self._window.append((self._current_chance, won))

        # ── Update cold-streak counter ────────────────────────────────────────
        if won:
            self._bets_since_last_win = 0
            self._total_wins += 1
        else:
            self._bets_since_last_win += 1

        # ── Cycle-level accounting (active hunt phases only) ──────────────────
        if self._phase in ("PROBE", "LOAD", "SNIPE"):
            self._cycle_bets  += 1
            self._phase_bets  += 1

            if won:
                # ─── Successful hit: log, enter cooldown, reset cycle ─────────
                self._on_cycle_hit(result)
            else:
                # ─── Miss: accumulate cycle loss for next abort check ─────────
                try:
                    profit = Decimal(str(result.get("profit", "0")))
                    if profit < 0:
                        self._cycle_loss += abs(profit)
                except Exception:
                    pass

    # ──────────────────────────────────────────────── phase handlers ──────────

    def _bet_passive(self, bal: Decimal) -> BetSpec:
        """
        PASSIVE — idle observation to build rolling-window statistics.

        Place minimal bets at the probe floor chance (cheapest, safest).
        Once the rolling window has enough data and a volatility window opens,
        transition to PROBE and begin a hunt cycle.
        """
        chance   = _PROBE_CHANCE_MAX       # 3.0% — cheapest probe, ~32× payout
        bet_amt  = _clamp_bet(bal, self.bet_min_frac, self.bet_min_frac, self.bet_max_frac)
        self._current_chance       = chance
        self._current_target_ratio = _PROBE_TARGET_MIN

        # Check for an open volatility window only once we have sufficient data
        if len(self._window) >= _MIN_WINDOW_DATA:
            z, cold_ratio = self._volatility_metrics(chance)
            if self._window_open(z, cold_ratio):
                # ── TRANSITION: PASSIVE → PROBE ──────────────────────────────
                self._start_cycle(bal)
                self._phase      = "PROBE"
                self._phase_bets = 0
                self.ctx.printer(
                    f"[VSH] 🔔 volatility window OPEN  "
                    f"z={z:.2f}  cold_ratio={cold_ratio:.2f}×  "
                    f"→ starting cycle #{self._total_cycles}  bal={bal:.8f}"
                )
                return self._make_probe_bet(bal)

        if self._total_bets % 100 == 1:
            # Periodic status log (every 100 bets)
            z, cold = self._volatility_metrics(chance)
            self.ctx.printer(
                f"[VSH] PASSIVE  bets={self._total_bets}  "
                f"window_data={len(self._window)}  "
                f"z={z:.2f}  cold={cold:.2f}×  "
                f"window={'OPEN' if self._window_open(z, cold) else 'closed'}  "
                f"bal={bal:.8f}"
            )

        return BetSpec(
            game="dice",
            amount=format(bet_amt, "f"),
            chance=f"{chance:.4f}",
            is_high=self.is_high,
        )

    def _bet_probe(self, bal: Decimal) -> BetSpec:
        """
        PROBE — Phase A: medium-low chance (0.8%–3%), minimum bet, target +10%–30%.

        Primary purpose is to confirm the volatility window is still open and
        collect phase-local statistics before committing more capital.

        Advancement: after _PROBE_MAX_BETS → advance to LOAD.
        Abort: cycle loss limit, cycle bet limit, or window closure.
        """
        # Check hard cycle abort first (checked at start of every phase bet)
        if self._cycle_exhausted():
            return self._abort_cycle(bal, "cycle limit reached in PROBE")

        # Soft abort: window closed after we've had enough phase data to confirm
        if self._phase_bets >= 20:
            z, cold = self._volatility_metrics(self._current_chance)
            if not self._window_open(z, cold):
                return self._abort_cycle(bal, "volatility window closed in PROBE")

        # Phase advancement: move to LOAD after probe phase is complete
        if self._phase_bets >= _PROBE_MAX_BETS:
            z, cold = self._volatility_metrics(self._current_chance)
            self.ctx.printer(
                f"[VSH] ⬆  PROBE→LOAD  phase_bets={self._phase_bets}  "
                f"z={z:.2f}  cold={cold:.2f}×  bal={bal:.8f}"
            )
            self._phase      = "LOAD"
            self._phase_bets = 0
            return self._make_load_bet(bal)

        return self._make_probe_bet(bal)

    def _bet_load(self, bal: Decimal) -> BetSpec:
        """
        LOAD — Phase B: lower chance (0.3%–0.8%), ramping bet, target +25%–100%.

        Risk escalation is moderate and linear — no geometric growth.
        Both bet size and profit target ramp linearly across the phase.

        Window closure is NOT checked here: we already paid the probe cost to
        enter this phase.  Only hard limits (cycle loss/bet count) abort LOAD.
        Advancement: after _LOAD_MAX_BETS → advance to SNIPE.
        Abort: cycle loss limit or cycle bet limit only.
        """
        if self._cycle_exhausted():
            return self._abort_cycle(bal, "cycle limit reached in LOAD")

        if self._phase_bets >= _LOAD_MAX_BETS:
            z, cold = self._volatility_metrics(self._current_chance)
            self.ctx.printer(
                f"[VSH] ⬆  LOAD→SNIPE  phase_bets={self._phase_bets}  "
                f"z={z:.2f}  cold={cold:.2f}×  bal={bal:.8f}"
            )
            self._phase      = "SNIPE"
            self._phase_bets = 0
            return self._make_snipe_bet(bal)

        return self._make_load_bet(bal)

    def _bet_snipe(self, bal: Decimal) -> BetSpec:
        """
        SNIPE — Phase C: lowest chance (0.1%–0.5%), max bet, target +100%–500%.

        This is the committed execution phase.  We have already invested cycles
        in probing and loading; now we execute with maximum permitted bet size.
        Soft window closure is NOT checked here — we finish the snipe or exhaust
        the attempt limit (to avoid incomplete cycles wasting probe+load cost).

        Abort: cycle loss limit, cycle bet limit, snipe attempt limit.
        """
        if self._cycle_exhausted():
            return self._abort_cycle(bal, "cycle limit reached in SNIPE")

        if self._phase_bets >= _SNIPE_MAX_BETS:
            return self._abort_cycle(bal, "snipe attempt limit exhausted")

        return self._make_snipe_bet(bal)

    def _bet_cooldown(self, bal: Decimal) -> BetSpec:
        """
        COOLDOWN — flat minimal bets to let RNG normalize.

        Transition back to PASSIVE when countdown reaches zero.
        Cooldown bets use a moderate chance (2%) — not extremes, not 50%.
        """
        self._cooldown_remaining -= 1

        if self._cooldown_remaining <= 0:
            self._phase = "PASSIVE"
            self.ctx.printer(
                f"[VSH] ✅ cooldown complete → PASSIVE  "
                f"bets={self._total_bets}  bal={bal:.8f}"
            )

        if self._cooldown_remaining % 100 == 0 and self._cooldown_remaining > 0:
            self.ctx.printer(
                f"[VSH] 🛡  cooldown {self._cooldown_remaining} bets remaining  "
                f"bal={bal:.8f}"
            )

        chance  = _COOLDOWN_CHANCE   # 2.0% — safe, not 50%
        bet_amt = _clamp_bet(bal, self.bet_min_frac, self.bet_min_frac, self.bet_max_frac)
        self._current_chance       = chance
        self._current_target_ratio = 0.0

        return BetSpec(
            game="dice",
            amount=format(bet_amt, "f"),
            chance=f"{chance:.4f}",
            is_high=self.is_high,
        )

    # ──────────────────────────────────────────────── bet factories ───────────

    def _make_probe_bet(self, bal: Decimal) -> BetSpec:
        """
        Phase A bet construction.

        Target profit ramps linearly from PROBE_TARGET_MIN to probe_target_max
        as phase progresses.  Bet size stays at minimum.

        chance is derived from target + bet_frac and clamped to probe range.
        """
        # Linear ramp of target profit across probe phase
        t = self._phase_bets / max(_PROBE_MAX_BETS, 1)
        target_ratio = _lerp(_PROBE_TARGET_MIN,
                              min(self.probe_target_max, _PROBE_TARGET_MAX), t)

        chance, bet_amt = _derive_bet(
            bal, target_ratio,
            self.bet_min_frac,          # probe uses minimum bet
            _PROBE_CHANCE_MIN, _PROBE_CHANCE_MAX,
            self.bet_min_frac, self.bet_max_frac,
        )
        self._current_chance       = chance
        self._current_target_ratio = target_ratio

        if self._phase_bets % 20 == 0:
            payout_x = _EFFECTIVE_MULT / max(chance, 0.0001)
            self.ctx.printer(
                f"[VSH] PROBE  bet#{self._phase_bets}/{_PROBE_MAX_BETS}  "
                f"chance={chance:.3f}%  payout={payout_x:.0f}×  "
                f"bet={float(bet_amt):.8f} ({float(bet_amt/bal)*100:.2f}%)  "
                f"target=+{target_ratio*100:.0f}%  "
                f"cycle_loss={float(self._cycle_loss):.8f}"
            )

        return BetSpec(
            game="dice",
            amount=format(bet_amt, "f"),
            chance=f"{chance:.4f}",
            is_high=self.is_high,
        )

    def _make_load_bet(self, bal: Decimal) -> BetSpec:
        """
        Phase B bet construction.

        Both target profit and bet size ramp linearly across the load phase:
          - target: LOAD_TARGET_MIN → load_target_max
          - bet:    bet_min_frac×2  → bet_max_frac×0.8
        chance is derived and clamped to load range.
        """
        t = self._phase_bets / max(_LOAD_MAX_BETS, 1)
        target_ratio = _lerp(_LOAD_TARGET_MIN,
                              min(self.load_target_max, _LOAD_TARGET_MAX), t)
        # Bet size ramps from 0.4% to 1.6% (within 0.2%–2% bounds)
        bet_frac = _lerp(self.bet_min_frac * 2.0, self.bet_max_frac * 0.8, t)

        chance, bet_amt = _derive_bet(
            bal, target_ratio, bet_frac,
            _LOAD_CHANCE_MIN, _LOAD_CHANCE_MAX,
            self.bet_min_frac, self.bet_max_frac,
        )
        self._current_chance       = chance
        self._current_target_ratio = target_ratio

        if self._phase_bets % 20 == 0:
            payout_x = _EFFECTIVE_MULT / max(chance, 0.0001)
            self.ctx.printer(
                f"[VSH] LOAD   bet#{self._phase_bets}/{_LOAD_MAX_BETS}  "
                f"chance={chance:.3f}%  payout={payout_x:.0f}×  "
                f"bet={float(bet_amt):.8f} ({float(bet_amt/bal)*100:.2f}%)  "
                f"target=+{target_ratio*100:.0f}%  "
                f"cycle_loss={float(self._cycle_loss):.8f}"
            )

        return BetSpec(
            game="dice",
            amount=format(bet_amt, "f"),
            chance=f"{chance:.4f}",
            is_high=self.is_high,
        )

    def _make_snipe_bet(self, bal: Decimal) -> BetSpec:
        """
        Phase C bet construction.

        Target profit ramps from SNIPE_TARGET_MIN to snipe_target_max across phase.
        Bet size ramps from 75% to 100% of bet_max_frac (pushing to ceiling).
        chance is derived and clamped to snipe range.
        """
        t = self._phase_bets / max(_SNIPE_MAX_BETS, 1)
        target_ratio = _lerp(_SNIPE_TARGET_MIN,
                              min(self.snipe_target_max, _SNIPE_TARGET_MAX), t)
        # Ramp bet from 75% of max (1.5%) up to 100% of max (2%)
        bet_frac = _lerp(self.bet_max_frac * 0.75, self.bet_max_frac, t)

        chance, bet_amt = _derive_bet(
            bal, target_ratio, bet_frac,
            _SNIPE_CHANCE_MIN, _SNIPE_CHANCE_MAX,
            self.bet_min_frac, self.bet_max_frac,
        )
        self._current_chance       = chance
        self._current_target_ratio = target_ratio

        if self._phase_bets % 10 == 0:
            payout_x = _EFFECTIVE_MULT / max(chance, 0.0001)
            z, cold  = self._volatility_metrics(chance)
            self.ctx.printer(
                f"[VSH] SNIPE  bet#{self._phase_bets}/{_SNIPE_MAX_BETS}  "
                f"chance={chance:.3f}%  payout={payout_x:.0f}×  "
                f"bet={float(bet_amt):.8f} ({float(bet_amt/bal)*100:.2f}%)  "
                f"target=+{target_ratio*100:.0f}%  "
                f"z={z:.2f}  cold={cold:.2f}×  "
                f"cycle_loss={float(self._cycle_loss):.8f}"
            )

        return BetSpec(
            game="dice",
            amount=format(bet_amt, "f"),
            chance=f"{chance:.4f}",
            is_high=self.is_high,
        )

    # ──────────────────────────────────────── volatility computation ──────────

    def _volatility_metrics(self, ref_chance: float) -> Tuple[float, float]:
        """
        Compute the two volatility metrics over the current rolling window.

        ── Metric 1: Poisson Z-score ─────────────────────────────────────────
        For a sequence of bets with varying (low) win probabilities, the number
        of wins follows a Poisson distribution when probabilities are small.

          expected_hits = Σ (chance_i / 100)    sum over all bets in window
          actual_hits   = count of wins in window
          std           = √(expected_hits)       Poisson std = √λ
          z             = (actual_hits − expected_hits) / std

        z < 0  → fewer wins than expected (favorable for hunting)
        z < −1.2 → statistically significant deficit (window open)

        ── Metric 2: Cold-streak ratio ────────────────────────────────────────
        At a given chance p%, a win is expected every 100/p bets on average.
        The cold_ratio measures how overdue we currently are:

          expected_per_win = 100.0 / ref_chance
          cold_ratio       = bets_since_last_win / expected_per_win

        cold_ratio > 1.5 means we are 1.5× the expected wait without a win.

        Returns:
            (z_score, cold_ratio)
        """
        entries = list(self._window)
        n = len(entries)

        if n == 0:
            return (0.0, 0.0)

        # Poisson z-score
        expected_hits = sum(c / 100.0 for c, _ in entries)
        actual_hits   = sum(1 for _, w in entries if w)

        if expected_hits < 1e-9:
            z = 0.0
        else:
            std = math.sqrt(expected_hits)
            z   = (actual_hits - expected_hits) / std

        # Cold-streak ratio
        expected_per_win = 100.0 / max(ref_chance, 0.0001)
        cold_ratio = self._bets_since_last_win / max(expected_per_win, 1.0)

        return (z, cold_ratio)

    def _window_open(self, z: float, cold_ratio: float) -> bool:
        """
        Determine whether a volatility window is currently open.

        Either condition is sufficient:
          1. Poisson z-score below threshold (statistical deficit of wins)
          2. Cold-streak ratio above threshold (unusually long drought)

        This is NOT a predictor of imminent wins — it identifies moments where
        recent history shows an abnormal lack of wins relative to expectation.
        Whether that deficit will self-correct soon is unknowable; we simply
        hunt more aggressively during these windows and accept bounded losses
        when they fail to produce a hit.
        """
        return z < self.zscore_threshold or cold_ratio > self.cold_ratio_thresh

    # ──────────────────────────────────────── cycle management ────────────────

    def _start_cycle(self, bal: Decimal) -> None:
        """Initialize counters for a new hunt cycle."""
        self._total_cycles       += 1
        self._cycle_bets          = 0
        self._phase_bets          = 0
        self._cycle_start_bal     = bal
        self._cycle_max_loss_abs  = bal * Decimal(str(self.cycle_max_loss_frac))
        self._cycle_loss          = Decimal("0")

    def _reset_cycle_counters(self) -> None:
        """Zero all cycle counters (called from on_session_start)."""
        self._cycle_bets         = 0
        self._phase_bets         = 0
        self._cycle_start_bal    = Decimal("0")
        self._cycle_max_loss_abs = Decimal("0")
        self._cycle_loss         = Decimal("0")

    def _cycle_exhausted(self) -> bool:
        """Return True if the cycle should be aborted due to hard limits."""
        # Max bets per cycle
        if self._cycle_bets >= self.cycle_max_bets:
            return True
        # Max loss per cycle (5% of cycle-start balance by default)
        if self._cycle_loss >= self._cycle_max_loss_abs:
            return True
        return False

    def _abort_cycle(self, bal: Decimal, reason: str) -> BetSpec:
        """Abort current cycle, log reason, and transition to COOLDOWN."""
        pct_lost = (
            float(self._cycle_loss / self._cycle_start_bal * 100)
            if self._cycle_start_bal > 0 else 0.0
        )
        self.ctx.printer(
            f"[VSH] 🔴 CYCLE ABORT  ({reason})  "
            f"cycle_bets={self._cycle_bets}  "
            f"loss={float(self._cycle_loss):.8f} (−{pct_lost:.2f}%)  "
            f"bal={bal:.8f}"
        )
        cooldown_len = self.ctx.rng.randint(self.cooldown_min, self.cooldown_max)
        self._phase              = "COOLDOWN"
        self._cooldown_remaining = cooldown_len
        self._current_chance     = _COOLDOWN_CHANCE
        self._reset_cycle_counters()

        bet_amt = _clamp_bet(bal, self.bet_min_frac, self.bet_min_frac, self.bet_max_frac)
        return BetSpec(
            game="dice",
            amount=format(bet_amt, "f"),
            chance=f"{_COOLDOWN_CHANCE:.4f}",
            is_high=self.is_high,
        )

    def _on_cycle_hit(self, result: BetResult) -> None:
        """
        Handle a successful hit within a hunt cycle.

        Log the win, compute actual profit vs target, then enter cooldown.
        Post-snipe hits get the longest cooldown (to prevent euphoria-driven
        re-entry into another aggressive cycle immediately).
        """
        self._cycle_hits += 1

        try:
            profit   = Decimal(str(result.get("profit", "0")))
            bal      = Decimal(str(result.get("balance", self._live_bal)))
            pct_gain = float(profit / self._cycle_start_bal * 100) if self._cycle_start_bal else 0.0
            payout_x = _EFFECTIVE_MULT / max(self._current_chance, 0.0001)
            self.ctx.printer(
                f"\n[VSH] 🎰 *** HIT ***  phase={self._phase}  "
                f"profit=+{profit:.8f}  (+{pct_gain:.1f}%)  "
                f"payout={payout_x:.0f}×  "
                f"chance={self._current_chance:.3f}%  "
                f"target=+{self._current_target_ratio*100:.0f}%  "
                f"cycle_bets={self._cycle_bets}  "
                f"bal={bal:.8f}\n"
            )
        except Exception:
            pass

        # Longer cooldown for more aggressive phases — prevents immediate re-entry
        if self._phase == "SNIPE":
            base = self.cooldown_max       # maximum rest after snipe hit
        elif self._phase == "LOAD":
            base = (self.cooldown_min + self.cooldown_max) // 2
        else:
            base = self.cooldown_min

        cooldown_len = self.ctx.rng.randint(base, self.cooldown_max)
        self._phase              = "COOLDOWN"
        self._cooldown_remaining = cooldown_len
        self._reset_cycle_counters()


# ─────────────────────────────────────────── Module-level math helpers ────────

def _dec(v: Any) -> Decimal:
    """Safe conversion to Decimal. Returns 0 on any error."""
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _drawdown(peak: Decimal, current: Decimal) -> float:
    """Peak-to-current drawdown as a fraction in [0.0, 1.0]."""
    if peak <= 0:
        return 0.0
    drop = peak - current
    if drop <= 0:
        return 0.0
    return float(drop / peak)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation from a to b. t is clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def _clamp_bet(bal: Decimal, frac: float, min_frac: float, max_frac: float) -> Decimal:
    """
    Calculate bet amount = bal × frac, clamped to [min_frac, max_frac] × bal.
    Result is quantized to 8 decimal places (floor) with a minimum of 1 satoshi.
    """
    clamped = max(min_frac, min(max_frac, frac))
    amt = bal * Decimal(str(clamped))
    amt = amt.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
    return max(amt, Decimal("0.00000001"))


def _derive_bet(
    bal:           Decimal,
    target_ratio:  float,   # desired profit as fraction of balance  (e.g. 0.5 = 50%)
    bet_frac:      float,   # desired bet fraction before clamping   (e.g. 0.01 = 1%)
    chance_min:    float,   # minimum allowed chance (%)
    chance_max:    float,   # maximum allowed chance (%)
    bet_min_frac:  float,   # hard floor for bet fraction
    bet_max_frac:  float,   # hard ceiling for bet fraction
) -> Tuple[float, Decimal]:
    """
    Derive (chance_pct, bet_amount) such that a win at chance_pct produces
    approximately target_ratio × balance as profit.

    Math derivation:
      payout_mult  = 99.0 / chance_pct          (DuckDice effective payout)
      profit       = bet_amount × (payout_mult − 1)

      Setting profit = bal × target_ratio:
        bet_amount = (bal × target_ratio) / (payout_mult − 1)

      Starting from a desired bet fraction bet_frac:
        payout_needed = target_ratio / bet_frac + 1
        chance_raw    = 99.0 / payout_needed

    If chance_raw falls outside [chance_min, chance_max], we clamp chance
    and recompute bet_amount to preserve the profit target as closely as
    possible.  Final bet_amount is clamped to [bet_min_frac, bet_max_frac]×bal.

    Returns:
        (chance_pct, bet_amount)
    """
    # Step 1: compute ideal chance from desired bet fraction and profit target
    safe_frac       = max(bet_min_frac, min(bet_max_frac, bet_frac))
    payout_needed   = target_ratio / max(safe_frac, 1e-9) + 1.0
    chance_raw      = _EFFECTIVE_MULT / max(payout_needed, 1.001)

    # Step 2: clamp chance to phase-appropriate range
    chance = max(chance_min, min(chance_max, chance_raw))

    # Step 3: with clamped chance, recompute bet_amount to match target profit
    payout_actual      = _EFFECTIVE_MULT / max(chance, 0.0001)
    profit_per_bet_unit = payout_actual - 1.0        # profit earned per 1 unit staked

    if profit_per_bet_unit < 1e-9:
        # Degenerate case: chance so high payout ≤ 1 — fallback to min bet
        bet_amt = _clamp_bet(bal, bet_min_frac, bet_min_frac, bet_max_frac)
    else:
        # bet = target_profit / (payout − 1)
        target_profit_abs = bal * Decimal(str(target_ratio))
        raw_bet  = target_profit_abs / Decimal(str(profit_per_bet_unit))
        raw_frac = float(raw_bet / bal) if bal > 0 else bet_min_frac
        bet_amt  = _clamp_bet(bal, raw_frac, bet_min_frac, bet_max_frac)

    return (chance, bet_amt)
