from __future__ import annotations
"""
Spike Hunter — Rare Massive Multiplier Strategy

Philosophy: A predator waiting for statistical pressure, then striking once
for a single, massive balance multiplication event. Not a grinder.

Three personality modes:
  sane       – 0.50% chance (~198x),  targets +100%  per hit
  high-risk  – 0.10% chance (~990x),  targets +200%  per hit
  insane     – 0.01% chance (~9900x), targets +500%+ per hit

Behavioral phases:
  OBSERVATION → tiny probe bets, accumulate three RNG signals
  ATTACK      → meaningful bets, bounded escalation, hard abort cap
  COOLDOWN    → post-win or post-abort quiet period

Readiness score (0.0–1.0) combines:
  1. Miss streak pressure  (50%) – streak vs expected miss count
  2. Cold density anomaly  (30%) – observed wins vs expected in window
  3. RNG pattern imbalance (20%) – recent win/loss ratio vs expected

Anti-overfitting: no single trigger fires the attack; all three signals
must together push the readiness score above the configured threshold.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

# ── Phase labels ──────────────────────────────────────────────────────────────
_OBS  = "observation"
_ATK  = "attack"
_COOL = "cooldown"

# ── Per-mode preset defaults ──────────────────────────────────────────────────
# chance:              Win-chance % used in both phases
# obs_bet_pct:         Observation bet as fraction of current balance
# atk_bet_pct:         Attack BASE bet as fraction of balance at attack start
#                      Sized so a single win ≈ target gain on that balance.
# max_attack_bets:     Hard abort cap (total bets inside one attack cycle)
# atk_escalation:      Multiply bet by this factor on each successive attack miss
# max_escal_steps:     Cap escalation at this many steps; stays flat thereafter
# streak_trigger_mult: Enter attack readiness check at N × expected_miss_streak
# density_window:      Rolling window size for cold-density signal
# attack_threshold:    Combined readiness score required to start attack phase
# cooldown_bets:       Bets to sit out after win or abort before next observation
# profit_lock_pct:     Fraction of cycle profit to conceptually "lock" (logged)
_PRESETS: Dict[str, Dict[str, Any]] = {
    "sane": {
        "chance":               0.50,
        "obs_bet_pct":          0.0001,   # 0.01% balance per probe
        "atk_bet_pct":          0.0051,   # 0.51% → 198 × 0.0051 ≈ +100% gain
        "max_attack_bets":      40,
        "atk_escalation":       1.25,
        "max_escal_steps":      6,
        "streak_trigger_mult":  3.0,
        "density_window":       500,
        "attack_threshold":     0.72,
        "cooldown_bets":        25,
        "profit_lock_pct":      0.50,
    },
    "high-risk": {
        "chance":               0.10,
        "obs_bet_pct":          0.00005,  # 0.005% balance per probe
        "atk_bet_pct":          0.0021,   # 0.21% → 990 × 0.0021 ≈ +208% gain
        "max_attack_bets":      25,
        "atk_escalation":       1.50,
        "max_escal_steps":      5,
        "streak_trigger_mult":  2.5,
        "density_window":       1200,
        "attack_threshold":     0.70,
        "cooldown_bets":        40,
        "profit_lock_pct":      0.60,
    },
    "insane": {
        "chance":               0.01,
        "obs_bet_pct":          0.00002,  # 0.002% balance per probe
        "atk_bet_pct":          0.00051,  # 0.051% → 9900 × 0.00051 ≈ +505% gain
        "max_attack_bets":      15,
        "atk_escalation":       2.00,
        "max_escal_steps":      4,
        "streak_trigger_mult":  1.5,
        "density_window":       8000,
        "attack_threshold":     0.65,
        "cooldown_bets":        60,
        "profit_lock_pct":      0.70,
    },
}

_MIN_BET = Decimal("0.00000001")


@register("spike-hunter")
class SpikeHunter:
    """
    Spike Hunter: observation-attack-reset predator.

    Waits patiently in observation mode, building a multi-signal readiness
    score.  When RNG pressure is sufficient it enters attack mode with
    meaningful (not tiny) bets sized to produce a large balance jump on a
    single win.  Losses inside an attack are bounded by a hard abort cap.
    """

    # ── Class-level API ────────────────────────────────────────────────────

    @classmethod
    def name(cls) -> str:
        return "spike-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Rare-spike predator: tiny observation bets build multi-signal readiness; "
            "attack phase bets large for +100%–+500%+ balance multiplication on a "
            "single hit. Three modes: sane / high-risk / insane."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Extreme",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Rare but Massive",
            recommended_for="Expert",
            pros=[
                "Targets +100% to +500%+ balance gain per single win",
                "Attack bets are sized to produce visible balance jumps",
                "Multi-signal readiness prevents impulsive attacks",
                "Hard abort cap limits maximum loss per hunt cycle",
                "Three modes for different risk appetites",
                "Observation phase costs very little",
                "Auto profit-lock after each hit",
                "Post-win and post-abort cooldown prevents chasing",
            ],
            cons=[
                "Extremely high variance — most sessions show no hits",
                "Long observation phases required before each attack",
                "Attack cycles can fail repeatedly before a win",
                "Not suitable for small bankrolls",
                "Psychologically demanding — must tolerate long cold periods",
                "Total session loss is possible and expected frequently",
            ],
            best_use_case=(
                "Players with large bankrolls seeking rare life-changing multiplier "
                "events. Set a hard stop-loss at -20% and take-profit at +200%. "
                "Run insane mode only with 10 000+ expected-hit-count bankrolls."
            ),
            tips=[
                "sane mode:     stop-loss -15%, take-profit +100%",
                "high-risk mode: stop-loss -20%, take-profit +200%",
                "insane mode:   stop-loss -25%, take-profit +500%",
                "Use max_bets 5000–50000 depending on mode",
                "Do NOT increase atk_bet_pct above 2% — risk of ruin spikes",
                "Cooldown period is your friend; never disable it",
                "Post-win: reduce aggression with a fresh session rather than continuing",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "mode": {
                "type": "str",
                "default": "high-risk",
                "desc": "Personality mode: 'sane' | 'high-risk' | 'insane'",
            },
            "chance": {
                "type": "float",
                "default": 0.0,
                "desc": "Override win-chance % (0 = use mode preset). E.g. 0.10 = 0.10%",
            },
            "obs_bet_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Override observation bet as fraction of balance (0 = mode preset)",
            },
            "atk_bet_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Override attack BASE bet as fraction of balance at attack start (0 = mode preset)",
            },
            "max_attack_bets": {
                "type": "int",
                "default": 0,
                "desc": "Override hard abort cap per attack cycle (0 = mode preset)",
            },
            "atk_escalation": {
                "type": "float",
                "default": 0.0,
                "desc": "Override per-miss bet escalation multiplier (0 = mode preset)",
            },
            "max_escal_steps": {
                "type": "int",
                "default": 0,
                "desc": "Override max escalation steps before flat cap (0 = mode preset)",
            },
            "streak_trigger_mult": {
                "type": "float",
                "default": 0.0,
                "desc": "Override streak trigger as N × expected_miss_streak (0 = mode preset)",
            },
            "density_window": {
                "type": "int",
                "default": 0,
                "desc": "Override rolling window for cold-density signal (0 = mode preset)",
            },
            "attack_threshold": {
                "type": "float",
                "default": 0.0,
                "desc": "Override combined readiness score to enter attack (0 = mode preset)",
            },
            "cooldown_bets": {
                "type": "int",
                "default": 0,
                "desc": "Override post-win/abort quiet period length (0 = mode preset)",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet High (True) or Low (False)",
            },
        }

    # ── Initialization ─────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        mode_key = str(params.get("mode", "high-risk")).lower()
        if mode_key not in _PRESETS:
            mode_key = "high-risk"
        preset = _PRESETS[mode_key]
        self._mode = mode_key

        # Merge preset with any explicit overrides (0 / 0.0 means "use preset")
        def _p(key: str, cast):
            raw = params.get(key, 0)
            return cast(raw) if raw else cast(preset[key])

        self._chance          = _p("chance",               float)
        self._obs_bet_pct     = _p("obs_bet_pct",          float)
        self._atk_bet_pct     = _p("atk_bet_pct",          float)
        self._max_attack_bets = _p("max_attack_bets",       int)
        self._atk_escalation  = _p("atk_escalation",        float)
        self._max_escal_steps = _p("max_escal_steps",       int)
        self._streak_trigger_mult = _p("streak_trigger_mult", float)
        self._density_window  = _p("density_window",        int)
        self._attack_threshold = _p("attack_threshold",     float)
        self._cooldown_bets   = _p("cooldown_bets",         int)
        self._profit_lock_pct = float(preset["profit_lock_pct"])
        self._is_high         = bool(params.get("is_high", True))

        # Derived constants
        self._expected_miss_streak = (100.0 / self._chance)
        self._trigger_streak = self._expected_miss_streak * self._streak_trigger_mult
        approx_multiplier = (100.0 - 1.0) / self._chance  # ~99% RTP
        self._expected_gain_pct = self._atk_bet_pct * approx_multiplier * 100.0

        self._reset_state()

    def _reset_state(self) -> None:
        """Full state reset — call once at session start and after each cycle."""
        self._phase: str                 = _OBS
        self._obs_history: List[int]     = []   # 1=win, 0=miss; rolling observation log
        self._obs_miss_streak: int       = 0    # consecutive misses since last win
        self._cooldown_counter: int      = 0
        self._atk_bet_count: int         = 0    # bets taken in current attack
        self._atk_base_bet: Decimal      = Decimal("0")
        self._atk_escal_step: int        = 0
        self._total_bets: int            = 0
        self._total_wins: int            = 0
        self._attack_cycles: int         = 0
        self._attack_wins: int           = 0
        self._attack_aborts: int         = 0
        self._session_start_balance: Decimal = Decimal("0")
        self._locked_profit: Decimal     = Decimal("0")
        self._last_readiness: float      = 0.0

    # ── Session hooks ──────────────────────────────────────────────────────

    def on_session_start(self) -> None:
        self._reset_state()
        self._session_start_balance = Decimal(self.ctx.starting_balance or "0")

        approx_mult = int((100.0 - 1.0) / self._chance)
        p = self.ctx.printer
        p(f"\n{'═'*60}")
        p(f"  🎯  SPIKE HUNTER  [{self._mode.upper()}]")
        p(f"{'═'*60}")
        p(f"  Chance        : {self._chance:.2f}%  (~{approx_mult}× multiplier)")
        p(f"  Attack bet    : {self._atk_bet_pct*100:.3f}% of balance at attack start")
        p(f"  Expected gain : ~+{self._expected_gain_pct:.0f}% per hit")
        p(f"  Trigger streak: {self._trigger_streak:.0f} misses  "
          f"({self._streak_trigger_mult:.1f}× expected)")
        p(f"  Attack cap    : {self._max_attack_bets} bets  "
          f"(escalation ×{self._atk_escalation:.2f}, max {self._max_escal_steps} steps)")
        p(f"  Cooldown      : {self._cooldown_bets} bets after each cycle")
        p(f"  Readiness gate: {self._attack_threshold:.2f}")
        p(f"{'═'*60}\n")

    # ── Readiness signals ──────────────────────────────────────────────────

    def _signal_streak(self) -> float:
        """Normalized miss-streak pressure (0→1). Reaches 1.0 at trigger_streak."""
        return min(1.0, self._obs_miss_streak / max(1.0, self._trigger_streak))

    def _signal_cold_density(self) -> float:
        """
        Cold-density anomaly: how far below expected win count is the window?
        Score 1.0 = zero wins seen; 0.0 = exactly expected win count.
        """
        if len(self._obs_history) < 20:
            return 0.0
        window = self._obs_history[-min(len(self._obs_history), self._density_window):]
        observed_wins = sum(window)
        expected_wins = len(window) * (self._chance / 100.0)
        if expected_wins < 1e-9:
            return 0.0
        return max(0.0, min(1.0, 1.0 - observed_wins / max(1.0, expected_wins)))

    def _signal_pattern_imbalance(self) -> float:
        """
        Win/miss ratio in most recent 50 observations vs expected.
        High score = RNG is running colder than chance in recent history.
        """
        window_size = min(50, len(self._obs_history))
        if window_size < 10:
            return 0.0
        window = self._obs_history[-window_size:]
        observed_ratio = sum(window) / window_size
        expected_ratio = self._chance / 100.0
        if observed_ratio < expected_ratio:
            return min(1.0, (expected_ratio - observed_ratio) / max(expected_ratio, 1e-9))
        return 0.0  # warmer than expected — not a good time to attack

    def _calc_readiness(self) -> float:
        """
        Combined readiness score 0.0–1.0.
        Weights: streak 50% | cold_density 30% | pattern_imbalance 20%.
        """
        s1 = self._signal_streak()
        s2 = self._signal_cold_density()
        s3 = self._signal_pattern_imbalance()
        return min(1.0, 0.50 * s1 + 0.30 * s2 + 0.20 * s3)

    # ── Bet sizing ─────────────────────────────────────────────────────────

    def _current_balance(self) -> Decimal:
        raw = self.ctx.current_balance_str() or self.ctx.starting_balance or "0"
        return Decimal(str(raw))

    def _obs_bet(self) -> Decimal:
        """Tiny observation probe bet — minimal cost, maximal information."""
        bet = self._current_balance() * Decimal(str(self._obs_bet_pct))
        return max(_MIN_BET, bet)

    def _attack_bet(self) -> Decimal:
        """
        Escalating attack bet.
        Step 0..max_escal_steps: base × escalation^step
        Beyond max_escal_steps: flat at base × escalation^max_escal_steps
        """
        step = min(self._atk_escal_step, self._max_escal_steps)
        multiplier = Decimal(str(self._atk_escalation ** step))
        bet = self._atk_base_bet * multiplier
        return max(_MIN_BET, bet)

    # ── Phase transitions ──────────────────────────────────────────────────

    def _enter_attack(self) -> None:
        balance = self._current_balance()
        self._atk_base_bet   = balance * Decimal(str(self._atk_bet_pct))
        self._atk_bet_count  = 0
        self._atk_escal_step = 0
        self._attack_cycles += 1
        self._phase = _ATK

        approx_mult = (100.0 - 1.0) / self._chance
        projected_gain = float(self._atk_base_bet) * approx_mult
        p = self.ctx.printer
        p(f"\n🏹 ATTACK #{self._attack_cycles}  |  "
          f"readiness={self._last_readiness:.2f}  |  "
          f"streak={self._obs_miss_streak}  |  "
          f"balance={float(balance):.8f}")
        p(f"   Base bet: {float(self._atk_base_bet):.8f}  "
          f"({self._atk_bet_pct*100:.3f}% of balance)")
        p(f"   Win target: +{projected_gain:.8f}  "
          f"(~+{self._expected_gain_pct:.0f}% of current balance)\n")

    def _abort_attack(self) -> None:
        self._attack_aborts += 1
        self._phase = _COOL
        self._cooldown_counter = self._cooldown_bets
        # Reset observation accumulator so next attack starts fresh
        self._obs_miss_streak = 0
        self._obs_history.clear()

        self.ctx.printer(
            f"💀 ATTACK #{self._attack_cycles} ABORTED  |  "
            f"{self._atk_bet_count}/{self._max_attack_bets} bets used  |  "
            f"cooldown={self._cooldown_bets}"
        )

    def _win_attack(self, profit: Decimal, balance: Decimal) -> None:
        self._attack_wins += 1
        self._total_wins += 1
        self._locked_profit += profit * Decimal(str(self._profit_lock_pct))
        self._phase = _COOL
        self._cooldown_counter = self._cooldown_bets
        # Reset observation for next hunt cycle
        self._obs_miss_streak = 0
        self._obs_history.clear()

        gain_pct = float(profit) / max(float(balance - profit), 1e-12) * 100
        p = self.ctx.printer
        p(f"\n{'★'*60}")
        p(f"  💰  HIT! Attack #{self._attack_cycles} WIN")
        p(f"  Profit    : +{float(profit):.8f}  (~+{gain_pct:.1f}%)")
        p(f"  Balance   : {float(balance):.8f}")
        p(f"  Locked    : {float(self._locked_profit):.8f}  "
          f"({self._profit_lock_pct*100:.0f}% of this win)")
        p(f"  Cooldown  : {self._cooldown_bets} bets")
        p(f"{'★'*60}\n")

    # ── Core strategy loop ─────────────────────────────────────────────────

    def next_bet(self) -> Optional[BetSpec]:
        self._total_bets += 1

        # ── COOLDOWN ──────────────────────────────────────────────────────
        if self._phase == _COOL:
            self._cooldown_counter -= 1
            if self._cooldown_counter <= 0:
                self._phase = _OBS
                if self._cooldown_counter == 0:
                    self.ctx.printer("✅ Cooldown complete — entering observation")
            # Use a safe tiny probe during cooldown
            return BetSpec(
                game="dice",
                amount=str(self._obs_bet()),
                chance=f"{self._chance:.4f}",
                is_high=self._is_high,
            )

        # ── OBSERVATION ───────────────────────────────────────────────────
        if self._phase == _OBS:
            readiness = self._calc_readiness()
            self._last_readiness = readiness

            # Status report every 200 bets
            if self._total_bets % 200 == 0:
                self.ctx.printer(
                    f"👁  OBS bet #{self._total_bets}  |  "
                    f"streak={self._obs_miss_streak}/{self._trigger_streak:.0f}  |  "
                    f"readiness={readiness:.2f}/{self._attack_threshold:.2f}  |  "
                    f"balance={float(self._current_balance()):.8f}"
                )

            if readiness >= self._attack_threshold:
                self._enter_attack()
                # Fall through to ATTACK logic immediately this bet
            else:
                return BetSpec(
                    game="dice",
                    amount=str(self._obs_bet()),
                    chance=f"{self._chance:.4f}",
                    is_high=self._is_high,
                )

        # ── ATTACK ────────────────────────────────────────────────────────
        if self._phase == _ATK:
            if self._atk_bet_count >= self._max_attack_bets:
                self._abort_attack()
                # Return a safe cooldown probe for this bet
                return BetSpec(
                    game="dice",
                    amount=str(self._obs_bet()),
                    chance=f"{self._chance:.4f}",
                    is_high=self._is_high,
                )

            self._atk_bet_count += 1
            bet_amount = self._attack_bet()

            # Verbose every 5 attack bets
            if self._atk_bet_count % 5 == 1 or self._atk_bet_count == 1:
                self.ctx.printer(
                    f"⚔  ATK {self._atk_bet_count}/{self._max_attack_bets}  |  "
                    f"bet={float(bet_amount):.8f}  "
                    f"(escal step {self._atk_escal_step}/{self._max_escal_steps})"
                )

            return BetSpec(
                game="dice",
                amount=str(bet_amount),
                chance=f"{self._chance:.4f}",
                is_high=self._is_high,
            )

        # Fallback — should never reach here
        return BetSpec(
            game="dice",
            amount=str(self._obs_bet()),
            chance=f"{self._chance:.4f}",
            is_high=self._is_high,
        )

    # ── Result processing ──────────────────────────────────────────────────

    def on_bet_result(self, result: BetResult) -> None:
        win     = bool(result.get("win", False))
        profit  = Decimal(str(result.get("profit", "0")))
        balance = Decimal(str(result.get("balance", "0")))

        # Observation history (always track, even in cooldown/attack)
        self._obs_history.append(1 if win else 0)
        # Keep history bounded to 2× density_window to save memory
        max_hist = max(self._density_window * 2, 200)
        if len(self._obs_history) > max_hist:
            self._obs_history = self._obs_history[-max_hist:]

        if win:
            self._obs_miss_streak = 0
        else:
            self._obs_miss_streak += 1

        # Phase-specific processing
        if self._phase == _ATK:
            if win:
                self._win_attack(profit, balance)
            else:
                # Advance escalation (capped at max_escal_steps)
                if self._atk_escal_step < self._max_escal_steps:
                    self._atk_escal_step += 1

        self.ctx.recent_results.append(result)

    # ── Session end ────────────────────────────────────────────────────────

    def on_session_end(self, reason: str) -> None:
        final_balance = self._current_balance()
        session_pnl   = final_balance - self._session_start_balance
        pnl_pct       = (float(session_pnl) / max(float(self._session_start_balance), 1e-12)) * 100.0
        hit_rate      = (
            f"{self._attack_wins}/{self._attack_cycles}"
            if self._attack_cycles > 0 else "0/0"
        )

        p = self.ctx.printer
        p(f"\n{'═'*60}")
        p(f"  🏁  SPIKE HUNTER [{self._mode.upper()}] — SESSION END")
        p(f"{'═'*60}")
        p(f"  Reason         : {reason}")
        p(f"  Total bets     : {self._total_bets}")
        p(f"  Attack cycles  : {self._attack_cycles}  (wins/total: {hit_rate})")
        p(f"  Aborts         : {self._attack_aborts}")
        p(f"  Total wins     : {self._total_wins}")
        p(f"  Max miss streak: {self._obs_miss_streak}")
        p(f"  Locked profit  : {float(self._locked_profit):.8f}")
        p(f"  Session PnL    : {float(session_pnl):+.8f}  ({pnl_pct:+.2f}%)")
        p(f"  Final balance  : {float(final_balance):.8f}")
        p(f"{'═'*60}\n")
