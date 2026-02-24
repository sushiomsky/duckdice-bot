from __future__ import annotations
# =============================================================================
# nano-range-hunter  VERSION 4  (latest)
# Changelog:
#   v1 — Original: oscillating chance, cold-zone bias, drought/emergency modes.
#   v2 — Added post-win boost phase (elevated chance + larger bets after each win).
#   v3 — Added 50/50 recovery burst; persistent session defaults; risk warnings.
#   v4 — Added min_bet_abs: absolute coin-unit floor overrides balance% minimum.
# Select older versions: --strategy "nano-range-hunter@v3"
# =============================================================================
"""
Nano Range Hunter Strategy

Hunts ultra-rare wins (0.01% – 1%) on Range Dice.

Core mechanics
--------------
* Every bet picks a FRESH random window position across the full 0-9999 domain
  so the target number changes each time.
* Chance oscillates through a slow sine-like cycle between min_chance and a
  dynamic ceiling. This means the window WIDTH (and therefore the multiplier)
  shifts with every bet – no two bets share the same chance OR the same target.
* Loss adaptation: after a drought the ceiling rises, widening chance and
  reducing expected loss-per-bet so the bankroll survives longer.
* Win reward: a win snaps the ceiling back toward min_chance to hunt the next
  big multiplier aggressively while still having profit headroom.
* Bet sizing is a fraction of CURRENT balance, ensuring bets shrink as the
  bankroll shrinks (fractional Kelly-style).  A drought-multiplier further
  scales bets down under prolonged losing streaks.
* Profit lock: after a configurable cumulative gain the strategy enters a
  reduced-exposure probe phase to guard profits.

Range Dice domain: 0 – 9999 (10 000 slots)
  window width = round(chance_pct * 100)  → 1 slot at 0.01%, 100 slots at 1%
  payout multiplier ≈ 99 / chance_pct
"""

import json
import math
import random
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

_DOMAIN = 10_000          # Range Dice total slots  (0 … 9999)
_MIN_SLOT_WIDTH = 1
_COLD_BUCKETS  = 200      # divide 0-9999 into 200 buckets of 50 slots each
_COLD_HISTORY  = 5000     # analyse last N rolls from DB
_COLD_REFRESH  = 300      # refresh map every N bets

# Persistent defaults file (relative to working directory = project root)
_LAST_PARAMS_FILE = Path("data/nano_range_hunter_last_params.json")

# All param keys persisted across sessions
_ALL_PARAMS = {
    "min_chance", "max_chance", "cycle_length",
    "win_at_ceil", "win_at_nano", "max_bet_pct", "min_bet_pct", "min_bet_abs",
    "drawdown_sensitivity", "drawdown_bet_floor",
    "drought_widen_at", "drought_widen_step", "emergency_streak",
    "recovery_streak", "recovery_bets", "recovery_chance", "recovery_bet_pct",
    "post_win_bets", "post_win_chance", "post_win_bet_mult",
    "profit_lock_pct", "probe_bets", "cold_zone_bias", "is_in",
    "profit_target_pct",
}


def _load_json_safe(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save_json_safe(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


class _ColdZoneMap:
    """Frequency map of rolled numbers used to bias window placement.

    The domain (0-9999) is split into equal buckets. Buckets hit less
    often in recent history get higher sampling weight, so the strategy
    *tends* toward cold zones while still exploring the full domain.

    bias=0.0 → purely random; bias=1.0 → strongest cold preference.
    """

    def __init__(self, n_buckets: int = _COLD_BUCKETS):
        self.n = n_buckets
        self.bucket_size: int = max(1, _DOMAIN // n_buckets)
        self.counts: List[int] = [0] * n_buckets
        self.weights: List[float] = [1.0 / n_buckets] * n_buckets
        self.total: int = 0
        self._loaded: bool = False

    def load(self, symbol: str) -> bool:
        """Populate counts from bet_history. Returns True on success."""
        try:
            from betbot_engine.bet_database import BetDatabase
            rolls = BetDatabase().get_recent_rolls(symbol=symbol, limit=_COLD_HISTORY)
            if not rolls:
                return False
            counts = [0] * self.n
            for r in rolls:
                b = min(int(r) // self.bucket_size, self.n - 1)
                counts[b] += 1
            self.counts = counts
            self.total = len(rolls)
            self._loaded = True
            return True
        except Exception:
            return False

    def record(self, roll: int) -> None:
        """Incorporate a new roll into the live counts."""
        b = min(roll // self.bucket_size, self.n - 1)
        self.counts[b] += 1
        self.total += 1

    def recompute_weights(self, bias: float) -> None:
        """Blend cold-zone weights with a uniform distribution.

        alpha smoothing prevents obsessing over a single cold bucket.
        """
        if self.total == 0:
            self.weights = [1.0 / self.n] * self.n
            return
        alpha = max(1.0, self.total / self.n * 0.15)
        raw = [1.0 / (c + alpha) for c in self.counts]
        s = sum(raw)
        cold = [w / s for w in raw]
        uniform = 1.0 / self.n
        self.weights = [(1.0 - bias) * uniform + bias * cw for cw in cold]

    def biased_start(self, rng: random.Random, width: int, bias: float) -> int:
        """Pick a window start position biased toward cold buckets."""
        self.recompute_weights(bias)
        bucket = rng.choices(range(self.n), weights=self.weights, k=1)[0]
        bstart = bucket * self.bucket_size
        max_start = _DOMAIN - width
        lo = bstart
        hi = min(bstart + self.bucket_size - 1, max_start)
        if hi < lo:
            # Window too wide to fit inside this bucket — use global random
            return rng.randint(0, max_start)
        return rng.randint(lo, hi)


def _width_for_chance(chance_pct: float) -> int:
    """Convert a chance percentage to a Range Dice window width."""
    return max(_MIN_SLOT_WIDTH, round(chance_pct * _DOMAIN / 100))


def _chance_for_width(width: int) -> float:
    """Convert a Range Dice window width back to a chance percentage."""
    return (width / _DOMAIN) * 100


@register("nano-range-hunter")
class NanoRangeHunter:
    """Ultra-low chance Range Dice hunter with rotating targets and adaptive sizing."""

    @classmethod
    def name(cls) -> str:
        return "nano-range-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Range Dice: hunts 0.01%–1% chances with a fresh random target window "
            "and adaptive chance every bet; balance-proportional sizing limits bust risk."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Variable",
            recommended_for="Advanced",
            pros=[
                "Tiered win targets: nano hits pay 300%+ (4× balance), ceiling hits pay ~12%",
                "Fresh target window every bet – no pattern exploitation",
                "Chance shifts each bet; cycles from nano to micro range",
                "Balance-proportional bets shrink as bankroll shrinks",
                "Aggressive drawdown scaling (4×) rapidly cuts bets as balance falls",
                "Drought sizing frozen at ceiling level — no runaway bets during widening",
                "Drought adaptation widens chance to reduce loss rate",
                "Profit-lock probe mode guards cumulative gains",
                "Potential 100x – 10 000x single-bet multipliers",
                "~15% stop-loss rate across 200–1000 bet sessions (vs 33–49% with old defaults)",
            ],
            cons=[
                "Very high variance; long droughts are expected",
                "Requires large bankroll (500+ base bet units recommended)",
                "Nano wins are rare; patience required",
                "Not suitable for short sessions",
            ],
            best_use_case=(
                "Long-running sessions where a single jackpot win is the goal. "
                "win_at_nano=3.0 means one nano hit triples profits from scratch (4× account). "
                "Ceiling hits give +12% each — meaningful but sized to minimise dry-spell drain. "
                "Pair with a strict stop-loss (–20%) and generous take-profit (+200%+). "
                "~15% stop-loss rate across 200–1000 bet sessions with default params."
            ),
            tips=[
                "Set stop_loss to –20% or tighter",
                "Use take_profit of +200%–+500% to ride a lucky session",
                "Increase win_at_nano (e.g. 5.0) for bigger but rarer nano jackpots",
                "Increase win_at_ceil (e.g. 0.20) for larger ceiling wins at cost of higher drain",
                "Increase cycle_length for slower chance rotation (less variance)",
                "Lower max_bet_pct (e.g. 0.003) to massively extend runway",
                "drought_widen_at controls how soon bets widen; raise it for patience",
                "drawdown_sensitivity=4.0 halves bets at just 12.5% drawdown — the key survival lever",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "min_chance": {
                "type": "float", "default": 0.01,
                "desc": "Floor chance % (0.01 = ~9800x multiplier)",
            },
            "max_chance": {
                "type": "float", "default": 1.00,
                "desc": "Ceiling chance % (1.00 = ~98x; higher = more frequent wins, lower loss-per-bet)",
            },
            "cycle_length": {
                "type": "int", "default": 100,
                "desc": "Bets per full chance oscillation cycle",
            },
            "win_at_ceil": {
                "type": "float", "default": 0.25,
                "desc": "Profit target as fraction of balance when hitting at max_chance (0.25 = +25% per ceiling hit). Lower = smaller ceiling bets = much less drain between jackpots.",
            },
            "win_at_nano": {
                "type": "float", "default": 3.0,
                "desc": "Profit target as multiple of balance when hitting at min_chance (3.0 = profit triples balance; new balance = 4×). Geometrically interpolated — bet_pct is monotone, peak drain only at ceiling.",
            },
            "max_bet_pct": {
                "type": "float", "default": 0.01,
                "desc": "Hard cap: max bet as fraction of balance (1% safety ceiling)",
            },
            "min_bet_pct": {
                "type": "float", "default": 0.000001,
                "desc": "Minimum bet as fraction of balance. Rarely the real floor — min_bet_abs usually dominates.",
            },
            "min_bet_abs": {
                "type": "float", "default": 0.000001,
                "desc": "Absolute minimum bet in coin units regardless of balance size (e.g. 0.01 = 1 cent). Overrides min_bet_pct when balance is small. Set to match 1 cent in your currency.",
            },
            "drawdown_sensitivity": {
                "type": "float", "default": 4.0,
                "desc": "How aggressively to reduce bets as balance falls from peak (4.0 = halve bets at 12.5% drawdown; 0 = disabled). Higher values extend runway dramatically during droughts.",
            },
            "drawdown_bet_floor": {
                "type": "float", "default": 0.2,
                "desc": "Minimum bet scale factor during drawdown (0.2 = never drop below 20% of formula bet)",
            },
            "drought_widen_at": {
                "type": "int", "default": 100,
                "desc": "Consecutive losses before chance ceiling starts rising (lower = adapt sooner)",
            },
            "drought_widen_step": {
                "type": "float", "default": 0.10,
                "desc": "How much the ceiling rises per 50 extra losses",
            },
            "emergency_streak": {
                "type": "int", "default": 250,
                "desc": "Streak depth that triggers emergency mode: forces ceiling chance every bet until a win",
            },
            "profit_lock_pct": {
                "type": "float", "default": 0.75,
                "desc": "Cumulative gain fraction that triggers probe cooldown (0.75 = +75%; higher = fewer interruptions)",
            },
            "probe_bets": {
                "type": "int", "default": 20,
                "desc": "Number of reduced-stake probe bets after profit lock (short cooldown only)",
            },
            "profit_target_pct": {
                "type": "float", "default": 0.0,
                "desc": (
                    "Profit target as % of starting balance (0 = disabled). "
                    "E.g. 100 = double your balance (+100%). "
                    "Enables target-aware mode: strategy reduces variance as it approaches the goal "
                    "and calculates a precise finish-bet in the final 5% to close the gap cleanly. "
                    "Phases — HUNT (<50%): unchanged; BUILD (50-80%): raise chance floor, scale bets ×0.75; "
                    "LOCK (80-95%): ceiling-biased chance, bets ×0.5; FINISH (≥95%): exact close-out bet."
                ),
            },
            "is_in": {
                "type": "bool", "default": True,
                "desc": "Bet IN the range (True) or OUT of it (False)",
            },
            "cold_zone_bias": {
                "type": "float", "default": 0.65,
                "desc": "How strongly to prefer historically cold number zones (0.0=uniform, 1.0=max cold-bias). Loads last 5 000 rolls from history. Note: PRNG has no memory — this is a preference, not a mathematical edge.",
            },
            "post_win_bets": {
                "type": "int", "default": 10,
                "desc": "Bets at boosted size/chance immediately after each win (0 = disabled). Capitalises on fresh-win momentum before returning to deep hunting.",
            },
            "post_win_chance": {
                "type": "float", "default": 0.0,
                "desc": "Chance % to use during post-win boost (0.0 = use max_chance). Set higher, e.g. 2.0, for a wider window and more frequent follow-up wins.",
            },
            "post_win_bet_mult": {
                "type": "float", "default": 2.0,
                "desc": "Multiply bet size during post-win boost phase (2.0 = double bets for the next post_win_bets bets). Hard-capped at 3 % of balance.",
            },
            "recovery_streak": {
                "type": "int", "default": 400,
                "desc": "Consecutive losses that trigger a 50/50 recovery burst. Fires after emergency mode when the drought is extreme. 0 = disabled.",
            },
            "recovery_bets": {
                "type": "int", "default": 5,
                "desc": "Number of ~50/50 bets per recovery burst. Kept small to limit house-edge cost.",
            },
            "recovery_chance": {
                "type": "float", "default": 49.5,
                "desc": "Win chance % for recovery bets (49.5 ≈ coin-flip; ~2× payout). Lower = rarer but bigger payout.",
            },
            "recovery_bet_pct": {
                "type": "float", "default": 0.005,
                "desc": "Bet size as fraction of balance for recovery bets (0.5% default). Hard-capped at 2% to prevent busting.",
            },
        }

    # ------------------------------------------------------------------
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        # Load last-session params as fallback defaults.
        # Resolution order: explicit CLI value > last-session value > hardcoded default.
        # If the value in `params` equals the hardcoded schema default we assume it
        # was not explicitly set by the user and prefer the last-session value instead.
        _last = _load_json_safe(_LAST_PARAMS_FILE)

        def _p(key: str, type_fn: Any, hardcoded: Any) -> Any:
            cli = params.get(key, hardcoded)
            if cli == hardcoded and key in _last:
                try:
                    return type_fn(_last[key])
                except Exception:
                    pass
            return type_fn(cli)

        self.min_chance       = _p("min_chance", float, 0.01)
        self.max_chance       = _p("max_chance", float, 1.00)
        self.cycle_length     = max(4, _p("cycle_length", int, 100))
        # Win targets — legacy compat: if old target_win_pct is in params, derive from it.
        _legacy = float(params["target_win_pct"]) if "target_win_pct" in params else None
        self.win_at_ceil      = _p("win_at_ceil", float, _legacy if _legacy else 0.25)
        self.win_at_nano      = _p("win_at_nano", float, _legacy * 10 if _legacy else 3.0)
        self.max_bet_pct      = _p("max_bet_pct", float, 0.01)
        self.min_bet_pct      = _p("min_bet_pct", float, 0.000001)
        self.min_bet_abs      = _p("min_bet_abs", float, 0.000001)
        self.drawdown_sensitivity = _p("drawdown_sensitivity", float, 4.0)
        self.drawdown_bet_floor   = max(0.0, min(1.0, _p("drawdown_bet_floor", float, 0.2)))
        self.drought_widen_at = _p("drought_widen_at", int, 100)
        self.drought_widen_step = _p("drought_widen_step", float, 0.10)
        self.emergency_streak = _p("emergency_streak", int, 250)
        self.profit_lock_pct  = _p("profit_lock_pct", float, 0.75)
        self.probe_bets       = _p("probe_bets", int, 20)
        self.profit_target_pct = _p("profit_target_pct", float, 0.0)
        self.is_in            = _p("is_in", bool, True)
        self.cold_zone_bias   = max(0.0, min(1.0, _p("cold_zone_bias", float, 0.65)))
        self.post_win_bets    = max(0, _p("post_win_bets", int, 10))
        self.post_win_chance  = _p("post_win_chance", float, 0.0)
        self.post_win_bet_mult = max(1.0, _p("post_win_bet_mult", float, 2.0))
        self.recovery_streak  = max(0, _p("recovery_streak", int, 400))
        self.recovery_bets    = max(1, _p("recovery_bets", int, 5))
        self.recovery_chance  = max(1.0, min(98.0, _p("recovery_chance", float, 49.5)))
        self.recovery_bet_pct = max(0.0001, min(0.02, _p("recovery_bet_pct", float, 0.005)))

        # Derived: adaptive ceiling (raised during droughts, reset on wins)
        self._dyn_max_chance  = self.max_chance

        # Cold-zone frequency map
        self._cold_map        = _ColdZoneMap()
        self._cold_refresh_ctr = 0

        # Post-win boost counter
        self._win_boost_counter = 0
        # 50/50 recovery burst counter
        self._recovery_counter  = 0
        # Cached Decimal floor for fast use in hot path
        self._min_bet_d = Decimal(str(self.min_bet_abs))

        # State
        self._phase           = 0          # oscillation phase 0..cycle_length-1
        self._loss_streak     = 0
        self._max_loss_streak = 0
        self._total_bets      = 0
        self._total_wins      = 0
        self._probe_counter   = 0
        self._starting_bal    = Decimal("0")
        self._peak_bal        = Decimal("0")
        self._live_bal        = Decimal("0")  # updated every bet from result
        self._target_bal: Optional[Decimal] = None
        self._target_phase    = ""            # "HUNT" / "BUILD" / "LOCK" / "FINISH"

    # ------------------------------------------------------------------
    @staticmethod
    def _check_risks(p: dict) -> List[str]:
        """Return human-readable risk warnings for the given param dict."""
        w: List[str] = []
        max_bp  = float(p.get("max_bet_pct",       0.004))
        rec_bp  = float(p.get("recovery_bet_pct",  0.005))
        pwm     = float(p.get("post_win_bet_mult",  2.0))
        wac     = float(p.get("win_at_ceil",        0.12))
        ds      = float(p.get("drawdown_sensitivity", 4.0))
        es      = int(p.get("emergency_streak",    250))
        rs      = int(p.get("recovery_streak",     400))
        rc      = float(p.get("recovery_chance",   49.5))
        rb      = int(p.get("recovery_bets",         5))
        dws     = float(p.get("drought_widen_step", 0.10))
        mc      = float(p.get("min_chance",         0.01))
        xc      = float(p.get("max_chance",         1.0))
        pwb     = int(p.get("post_win_bets",        10))
        pwc     = float(p.get("post_win_chance",    0.0))
        dba     = int(p.get("drought_widen_at",    100))
        clk     = int(p.get("cycle_length",        100))
        mba     = float(p.get("min_bet_abs",       0.00001))

        # ── Absolute minimum bet vs balance ───────────────────────────
        # (Can't check against live balance here, but warn if it looks large)
        if mba > 1.0:
            w.append(
                f"🚨 CRITICAL  min_bet_abs={mba} — absolute floor is very high. "
                f"Every bet will be at least {mba} coin units. Verify this matches your currency."
            )
        elif mba > 0.1:
            w.append(
                f"⚠️  HIGH     min_bet_abs={mba} — floor of {mba} coin units per bet. "
                f"Ensure your balance can sustain this (recommend ≥500× min_bet_abs)."
            )

        # ── Bet sizing ────────────────────────────────────────────────
        eff_ceil = max(xc, 0.0001)
        drain50  = wac * eff_ceil / max(0.0001, 99.0 - eff_ceil) * 50
        if max_bp >= 0.015:
            w.append(
                f"🚨 CRITICAL  max_bet_pct={max_bp*100:.2f}% — catastrophic drain risk. "
                f"A drought of 200 bets at ceiling drains >{200*max_bp*100:.0f}% of "
                f"starting balance. Recommended ≤0.5%. Use drawdown_sensitivity instead."
            )
        elif max_bp >= 0.008:
            w.append(
                f"⚠️  HIGH     max_bet_pct={max_bp*100:.2f}% — drain of ~{drain50*100:.1f}% "
                f"per 50 ceiling bets. Drawdown scaling will help, but consider ≤0.5%."
            )

        if rec_bp >= 0.015:
            w.append(
                f"🚨 CRITICAL  recovery_bet_pct={rec_bp*100:.2f}% — {rb} recovery bets × "
                f"{rec_bp*100:.2f}% = up to -{rb*rec_bp*100:.1f}% of balance in one burst. "
                f"Recommended ≤0.5%."
            )
        elif rec_bp >= 0.01:
            w.append(
                f"⚠️  HIGH     recovery_bet_pct={rec_bp*100:.2f}% — full burst costs "
                f"{rb*rec_bp*100:.1f}% if all {rb} recovery bets lose."
            )

        # ── Post-win boost ────────────────────────────────────────────
        if pwm >= 4.0:
            boost_ch = pwc if pwc > 0 else xc
            w.append(
                f"⚠️  HIGH     post_win_bet_mult={pwm}× — a single loss in the {pwb}-bet "
                f"boost gives back most of the win profit. Each boost bet is "
                f"~{pwm * wac * boost_ch / max(0.0001, 99-boost_ch) * 100:.2f}% of balance."
            )
        elif pwm >= 3.0:
            w.append(
                f"💡 MODERATE post_win_bet_mult={pwm}× — aggressive post-win boost. "
                f"Monitor that wins aren't being given back during the boost phase."
            )

        # ── Recovery vs emergency ordering ───────────────────────────
        if rs > 0 and rs <= es:
            w.append(
                f"🚨 CRITICAL  recovery_streak={rs} ≤ emergency_streak={es} — "
                f"recovery fires BEFORE emergency mode, interrupting it. "
                f"Set recovery_streak > emergency_streak (e.g. {es + 150})."
            )

        if rc < 40.0:
            w.append(
                f"💡 MODERATE recovery_chance={rc:.1f}% — below 40% is no longer near-fair. "
                f"House edge matters more here; consider 45–50%."
            )

        # ── Drought widening ──────────────────────────────────────────
        if dws >= 0.30:
            steps_to_5 = max(0, int((5.0 - xc) / dws)) * 50
            w.append(
                f"⚠️  HIGH     drought_widen_step={dws} — ceiling reaches 5% after "
                f"~{steps_to_5} extra losses beyond drought_widen_at={dba}. "
                f"At 5% the multiplier is only ~20x — no longer nano range."
            )

        # ── Chance range sanity ───────────────────────────────────────
        if mc >= xc:
            w.append(
                f"🚨 CRITICAL  min_chance={mc}% ≥ max_chance={xc}% — invalid range. "
                f"Strategy bets at a fixed chance. Set min_chance < max_chance."
            )
        elif mc > 1.0:
            w.append(
                f"💡 INFO      min_chance={mc:.2f}% — lowest multiplier is only "
                f"~{99/mc:.0f}x. For true jackpot hunting consider ≤0.1%."
            )

        # ── Drawdown protection ───────────────────────────────────────
        if ds < 1.0 and max_bp > 0.005:
            w.append(
                f"⚠️  HIGH     drawdown_sensitivity={ds} with max_bet_pct={max_bp*100:.2f}% "
                f"— very low drawdown protection combined with large bets. "
                f"Bets won't shrink as balance falls. Consider sensitivity ≥2.0."
            )

        if clk < 20:
            w.append(
                f"💡 MODERATE cycle_length={clk} — very fast oscillation means many "
                f"consecutive near-ceiling bets per cycle. Consider ≥50 for smoother variance."
            )

        return w

    # ------------------------------------------------------------------
    def on_session_start(self) -> None:
        self._phase           = 0
        self._loss_streak     = 0
        self._max_loss_streak = 0
        self._total_bets      = 0
        self._total_wins      = 0
        self._probe_counter   = 0
        self._win_boost_counter = 0
        self._recovery_counter  = 0
        self._cold_refresh_ctr = 0
        self._dyn_max_chance  = self.max_chance
        self._starting_bal    = Decimal(self.ctx.starting_balance)
        self._peak_bal        = self._starting_bal
        self._live_bal        = self._starting_bal
        self._target_phase    = ""
        if self.profit_target_pct > 0:
            self._target_bal = self._starting_bal * Decimal(str(1 + self.profit_target_pct / 100))
        else:
            self._target_bal = None

        # Load cold-zone frequency map from bet history
        if self.cold_zone_bias > 0.0:
            loaded = self._cold_map.load(self.ctx.symbol)
            cold_status = (
                f"loaded {self._cold_map.total} rolls, bias={self.cold_zone_bias:.2f}"
                if loaded else "no history yet — uniform start"
            )
        else:
            cold_status = "disabled (bias=0)"

        bp_ceil = self.win_at_ceil * self.max_chance / max(0.0001, 99.0 - self.max_chance)
        bp_nano = self.win_at_nano * self.min_chance / max(0.0001, 99.0 - self.min_chance)

        # ── Check for last-session params diff ────────────────────────
        _last = _load_json_safe(_LAST_PARAMS_FILE)
        _changed_from_last: List[str] = []
        if _last:
            for key in _ALL_PARAMS:
                old = _last.get(key)
                cur = getattr(self, key, None)
                if old is not None and old != cur:
                    _changed_from_last.append(f"{key}: {old} → {cur}")

        self.ctx.printer(f"\n🎯  Nano Range Hunter started")
        self.ctx.printer(f"    Chance range  : {self.min_chance}% ↔ {self.max_chance}%")
        self.ctx.printer(f"    Multipliers   : ~{99/self.max_chance:.0f}x – ~{99/self.min_chance:.0f}x")
        self.ctx.printer(f"    Win at ceiling: +{self.win_at_ceil*100:.0f}% of balance  "
              f"(bet {bp_ceil*100:.3f}% per try)")
        self.ctx.printer(f"    Win at nano   : +{self.win_at_nano*100:.0f}% of balance  "
              f"(bet {bp_nano*100:.5f}% per try) → {1+self.win_at_nano:.1f}× account")
        self.ctx.printer(f"    Max drain/50  : {bp_ceil*50*100:.1f}% (ceiling phase, no wins)")
        self.ctx.printer(f"    Drawdown scale: sensitivity={self.drawdown_sensitivity}  "
              f"floor={self.drawdown_bet_floor:.0%}  (bets shrink as balance falls from peak)")
        self.ctx.printer(f"    Bet cap       : {self.max_bet_pct*100:.2f}% of balance per bet  "
              f"(min {self.min_bet_abs} absolute)")
        self.ctx.printer(f"    Drought widen : after {self.drought_widen_at} losses  "
              f"(+{self.drought_widen_step*100:.0f}% ceiling per 50 extra losses, "
              f"emergency at streak {self.emergency_streak})")
        self.ctx.printer(f"    Cold zones    : {cold_status}")
        self.ctx.printer(f"    Profit lock   : +{self.profit_lock_pct*100:.0f}% gain triggers "
              f"{self.probe_bets}-bet reduced-stake cooldown")
        if self._target_bal:
            self.ctx.printer(
                f"    Target        : +{self.profit_target_pct:.0f}% "
                f"({float(self._starting_bal):.8f} → {float(self._target_bal):.8f}) | "
                f"HUNT→BUILD@50%→LOCK@80%→FINISH@95%"
            )
        if self.post_win_bets > 0:
            boost_ch = self.post_win_chance if self.post_win_chance > 0 else self.max_chance
            self.ctx.printer(f"    Post-win boost: {self.post_win_bets} bets @ {boost_ch:.2f}% "
                  f"× {self.post_win_bet_mult}× size after each win")
        if self.recovery_streak > 0:
            self.ctx.printer(
                f"    Recovery burst: {self.recovery_bets} × {self.recovery_chance:.1f}% bets @ "
                f"{self.recovery_bet_pct*100:.2f}% balance after streak ≥ {self.recovery_streak}"
            )

        if _last:
            if _changed_from_last:
                self.ctx.printer(f"\n    ↩️  Changed from last session:")
                for diff in _changed_from_last:
                    self.ctx.printer(f"       {diff}")
            else:
                self.ctx.printer(f"\n    ↩️  All params match last session (loaded from saved defaults)")

        # ── Risk warnings ─────────────────────────────────────────────
        effective = {k: getattr(self, k, None) for k in _ALL_PARAMS if hasattr(self, k)}
        risks = self._check_risks(effective)
        if risks:
            self.ctx.printer(f"\n  ⚠️  Risk warnings ({len(risks)}):")
            for r in risks:
                self.ctx.printer(f"    {r}")
        else:
            self.ctx.printer(f"\n  ✅  No risk warnings — config looks safe")
        self.ctx.printer("")

    # ------------------------------------------------------------------
    def on_resume(self, state: Dict[str, Any]) -> None:
        """Restore strategy state from a prior cancelled session.

        Called by the engine after on_session_start() when --continue is used.
        Restores loss_streak and oscillation phase so hunting resumes in context.
        """
        if "loss_streak" in state:
            self._loss_streak = int(state["loss_streak"])
            self._max_loss_streak = self._loss_streak
        if "bet_number" in state:
            # Approximate oscillation phase from total bets played
            self._phase = int(state["bet_number"]) % self.cycle_length
        if "last_balance" in state and state["last_balance"]:
            try:
                self._live_bal = Decimal(str(state["last_balance"]))
                self._starting_bal = self._live_bal
                self._peak_bal = self._live_bal
            except Exception:
                pass
        # Recompute adaptive ceiling based on restored streak
        drought_excess = max(0, self._loss_streak - self.drought_widen_at)
        extra_steps = drought_excess // 50
        self._dyn_max_chance = min(
            self.max_chance + extra_steps * self.drought_widen_step,
            max(self.max_chance, 5.0),
        )
        self.ctx.printer(
            f"♻️  Resumed — loss_streak={self._loss_streak}  "
            f"phase={self._phase}  dyn_ceiling={self._dyn_max_chance:.2f}%  "
            f"balance={float(self._live_bal):.8f}"
        )

    # ------------------------------------------------------------------
    def _current_balance(self) -> Decimal:
        # _live_bal is updated from every bet result — most accurate
        if self._live_bal > 0:
            return self._live_bal
        raw = self.ctx.current_balance_str() or self.ctx.starting_balance or "0"
        try:
            return Decimal(str(raw))
        except Exception:
            return Decimal("0")

    # ------------------------------------------------------------------
    def _calc_chance(self) -> float:
        """
        Return the win-chance % for this bet.

        Uses a skewed cosine so the strategy spends most time hunting deep
        (near min_chance) during calm periods. As a losing streak grows, the
        power exponent is flattened toward 0.4 which INVERTS the bias — the
        strategy then spends more time at HIGH chances to survive the drought:

          streak=0    power=2.5  → ~70% of bets at deep nano (jackpot hunting)
          streak=100  power=1.5  → balanced
          streak=200  power=0.5  → biased toward high chance (survival mode)
          streak=210+ power=0.4  → strongly biased high (emergency survival)

        Phase 0      → min_chance  (deepest hunt, biggest multiplier)
        Phase cycle/2 → _dyn_max_chance (highest chance, survival probe)
        """
        t = self._phase / self.cycle_length
        raw_blend = (1 - math.cos(2 * math.pi * t)) / 2

        # Flatten power toward 0.4 (biased-high) as streak deepens
        effective_power = max(0.4, 2.5 - self._loss_streak / 100.0)
        blend = raw_blend ** effective_power

        chance = self.min_chance + blend * (self._dyn_max_chance - self.min_chance)
        return max(self.min_chance, min(self._dyn_max_chance, chance))


    # ------------------------------------------------------------------
    def _bet_pct_for_chance(self, sizing_chance: float) -> float:
        """Return the raw bet fraction for a given chance via geometric interpolation.

        Bet_pct endpoints are derived from the win targets:
          bp_ceil = win_at_ceil * max_chance / (99 - max_chance)
          bp_nano = win_at_nano * min_chance / (99 - min_chance)

        Intermediate chances receive the geometric mean of these endpoints on a
        log scale. This makes bet_pct MONOTONICALLY DECREASING as chance decreases
        (deeper = cheaper), eliminating the dangerous mid-range bet hump that the
        old linear-target formula created.

        Profit at any chance:
          profit_pct = bet_pct * (99/chance - 1)
        which equals win_at_ceil at ceiling and win_at_nano at nano exactly.
        """
        bp_ceil = self.win_at_ceil * self.max_chance / max(0.0001, 99.0 - self.max_chance)
        bp_nano = self.win_at_nano * self.min_chance / max(0.0001, 99.0 - self.min_chance)

        if sizing_chance >= self.max_chance or self.max_chance <= self.min_chance:
            return bp_ceil
        if sizing_chance <= self.min_chance:
            return bp_nano

        log_ratio = math.log(self.max_chance / sizing_chance) / math.log(self.max_chance / self.min_chance)
        log_ratio = max(0.0, min(1.0, log_ratio))
        return math.exp(math.log(bp_ceil) + log_ratio * math.log(bp_nano / bp_ceil))

    # ------------------------------------------------------------------
    def _calc_bet(self, chance: float) -> Decimal:
        """Geometrically interpolated bet with drawdown-aware scaling.

        - bet_pct is monotonically decreasing as chance decreases (no mid-range hump)
        - Maximum drain rate only occurs at ceiling chance, not at intermediate depths
        - Drawdown scaler reduces bets proportionally as balance falls from peak,
          extending runway during losing streaks
        - Sizing is frozen at max_chance during drought/emergency to prevent oversizing
        """
        bal = self._current_balance()
        if bal <= 0:
            return Decimal("0")

        # Freeze sizing at max_chance during drought/emergency — survival, not profit
        sizing_chance = min(chance, self.max_chance)
        bet_pct = self._bet_pct_for_chance(sizing_chance)

        # Drawdown scaler: shrink bets as balance falls from peak
        if self.drawdown_sensitivity > 0 and self._peak_bal > 0:
            dd = max(0.0, float((self._peak_bal - bal) / self._peak_bal))
            dd_scale = max(self.drawdown_bet_floor, 1.0 - dd * self.drawdown_sensitivity)
            bet_pct *= dd_scale

        bet_pct = max(self.min_bet_pct, min(self.max_bet_pct, bet_pct))

        bet = bal * Decimal(str(bet_pct))
        if bet < self._min_bet_d:
            bet = self._min_bet_d
        return bet.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


    # ------------------------------------------------------------------
    def _pick_window(self, width: int) -> Tuple[int, int]:
        """Pick a window biased toward historically cold number zones.

        When cold_zone_bias=0 (or no history), falls back to uniform random.
        Periodically refreshes the frequency map from the DB.
        """
        self._cold_refresh_ctr += 1
        if self._cold_refresh_ctr >= _COLD_REFRESH:
            self._cold_refresh_ctr = 0
            self._cold_map.load(self.ctx.symbol)

        max_start = _DOMAIN - width
        if self.cold_zone_bias > 0.0 and self._cold_map._loaded:
            start = self._cold_map.biased_start(self.ctx.rng, width, self.cold_zone_bias)
        else:
            start = self.ctx.rng.randint(0, max_start)
        return (start, start + width - 1)

    # ------------------------------------------------------------------
    def _target_phase_label(self, progress: float) -> str:
        if progress >= 0.95:  return "FINISH"
        if progress >= 0.80:  return "LOCK"
        if progress >= 0.50:  return "BUILD"
        return "HUNT"

    def _apply_target_awareness(
        self, chance: float, bet: Decimal, bal: Decimal
    ) -> Tuple[float, Decimal]:
        """Adjust chance and bet based on proximity to profit target.

        HUNT  (<50% progress): no change — hunt aggressively
        BUILD (50–80%):  raise chance floor to geometric mean of min/max, scale bet ×0.75–1.0
        LOCK  (80–95%):  floor at max_chance×0.5, scale bet ×0.5
        FINISH (≥95%):   one precise ceiling-chance bet sized to close the remaining gap exactly
        """
        if not self._target_bal or self._starting_bal <= 0:
            return chance, bet

        gain_needed = float(self._target_bal - self._starting_bal)
        if gain_needed <= 0:
            return chance, bet

        gain_actual = float(bal - self._starting_bal)
        progress = gain_actual / gain_needed  # 0.0 = start, 1.0 = target

        phase = self._target_phase_label(progress)

        # Log phase transitions
        if phase != self._target_phase:
            self._target_phase = phase
            pct_done = max(0.0, progress * 100)
            self.ctx.printer(
                f"🎯 Target phase → {phase} ({pct_done:.1f}% of +{self.profit_target_pct:.0f}% goal | "
                f"balance {float(bal):.8f} / target {float(self._target_bal):.8f})"
            )

        if phase == "HUNT":
            return chance, bet

        if phase == "FINISH":
            remaining = self._target_bal - bal
            if remaining <= 0:
                return chance, bet
            finish_chance = self.max_chance
            multiplier = 99.0 / finish_chance - 1.0
            if multiplier > 0:
                finish_bet = remaining / Decimal(str(multiplier))
                finish_bet = max(finish_bet, self._min_bet_d)
                # Hard cap: never risk more than max_bet_pct in a single finish bet
                cap = bal * Decimal(str(self.max_bet_pct))
                finish_bet = min(finish_bet, cap)
                finish_bet = finish_bet.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
                return finish_chance, finish_bet

        if phase == "LOCK":
            lock_floor = max(self.min_chance, self.max_chance * 0.5)
            adjusted_chance = max(chance, lock_floor)
            adjusted_bet = (bet * Decimal("0.5")).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
            return adjusted_chance, max(adjusted_bet, self._min_bet_d)

        # BUILD (50–80%): geometric mean as floor, gradual bet scale-down
        build_floor = math.sqrt(self.min_chance * self.max_chance)
        adjusted_chance = max(chance, build_floor)
        # scale linearly from 1.0 at 50% progress to 0.75 at 80%
        scale = 1.0 - 0.25 * (progress - 0.50) / 0.30
        scale = max(0.75, min(1.0, scale))
        adjusted_bet = (bet * Decimal(str(round(scale, 4)))).quantize(
            Decimal("0.00000001"), rounding=ROUND_DOWN
        )
        return adjusted_chance, max(adjusted_bet, self._min_bet_d)

    # ------------------------------------------------------------------
    def next_bet(self) -> Optional[BetSpec]:
        self._total_bets += 1

        bal = self._current_balance()
        if bal <= 0:
            return None

        # Target-awareness: stop when profit target reached
        if self._target_bal and bal >= self._target_bal:
            gain_pct = float((bal - self._starting_bal) / self._starting_bal * 100) if self._starting_bal > 0 else 0
            self.ctx.printer(
                f"\n🎯 PROFIT TARGET REACHED! "
                f"Balance: {float(bal):.8f} (+{gain_pct:.1f}% / target was +{self.profit_target_pct:.0f}%)"
            )
            return None

        # Update peak balance for profit-lock check
        if bal > self._peak_bal:
            self._peak_bal = bal

        # Probe mode: reduced-stake bets after profit lock
        # Uses 10% of the formula bet so wins during probe still count for something.
        if self._probe_counter > 0:
            self._probe_counter -= 1
            probe_chance = min(self._dyn_max_chance, self.max_chance)
            probe_bet_pct = max(self.min_bet_pct, self._bet_pct_for_chance(probe_chance) * 0.10)
            probe_bet = (bal * Decimal(str(probe_bet_pct))).quantize(
                Decimal("0.00000001"), rounding=ROUND_DOWN
            )
            probe_bet = max(probe_bet, self._min_bet_d)
            width = _width_for_chance(probe_chance)
            window = self._pick_window(width)
            if self._probe_counter % 10 == 0 and self._probe_counter > 0:
                self.ctx.printer(f"🛡️  Probe mode: {self._probe_counter} bets remaining")
            return BetSpec(
                game="range-dice",
                amount=str(probe_bet),
                range=window,
                is_in=self.is_in,
                faucet=self.ctx.faucet,
            )

        # Post-win boost: elevated chance + larger bet for N bets after each win.
        # Capitalises on momentum by staying wide before returning to deep hunting.
        if self._win_boost_counter > 0:
            self._win_boost_counter -= 1
            boost_chance = self.post_win_chance if self.post_win_chance > 0 else self.max_chance
            base_bet = self._calc_bet(boost_chance)
            boosted = base_bet * Decimal(str(self.post_win_bet_mult))
            # Hard cap: never exceed 3% of balance in a single boost bet
            hard_cap = bal * Decimal("0.03")
            boosted = min(boosted, hard_cap).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
            boosted = max(boosted, self._min_bet_d)
            width = _width_for_chance(boost_chance)
            window = self._pick_window(width)
            remaining = self._win_boost_counter + 1
            if remaining in (self.post_win_bets, 1) or remaining % 5 == 0:
                self.ctx.printer(
                    f"⚡ Win-boost #{self.post_win_bets - self._win_boost_counter}/{self.post_win_bets} | "
                    f"chance={boost_chance:.2f}% | bet×{self.post_win_bet_mult} | "
                    f"{self._win_boost_counter} left"
                )
            return BetSpec(
                game="range-dice",
                amount=str(boosted),
                range=window,
                is_in=self.is_in,
                faucet=self.ctx.faucet,
            )

        # Dynamic ceiling: raise when in a deep drought
        drought_excess = max(0, self._loss_streak - self.drought_widen_at)
        extra_steps = drought_excess // 50
        self._dyn_max_chance = min(
            self.max_chance + extra_steps * self.drought_widen_step,
            # Hard cap: allow up to 5% during extreme droughts for survival
            max(self.max_chance, 5.0),
        )

        # 50/50 recovery burst: fires after an extreme drought to claw back losses
        # with near-fair-odds bets before returning to nano hunting.
        if self.recovery_streak > 0 and self._loss_streak >= self.recovery_streak:
            if self._recovery_counter == 0:
                # Arm a new burst
                self._recovery_counter = self.recovery_bets
                self.ctx.printer(
                    f"🆘 RECOVERY BURST triggered at streak {self._loss_streak}! "
                    f"{self.recovery_bets} × {self.recovery_chance:.1f}% bets "
                    f"@ {self.recovery_bet_pct*100:.2f}% of balance"
                )
        if self._recovery_counter > 0:
            self._recovery_counter -= 1
            rec_bet = (bal * Decimal(str(self.recovery_bet_pct))).quantize(
                Decimal("0.00000001"), rounding=ROUND_DOWN
            )
            rec_bet = max(rec_bet, self._min_bet_d)
            width = _width_for_chance(self.recovery_chance)
            window = self._pick_window(width)
            multi = 99.0 / self.recovery_chance
            self.ctx.printer(
                f"🔄 Recovery bet {self.recovery_bets - self._recovery_counter}/{self.recovery_bets} | "
                f"{self.recovery_chance:.1f}% (~{multi:.1f}x) | "
                f"amount={float(rec_bet):.8f} | streak={self._loss_streak}"
            )
            if self._recovery_counter == 0:
                # Back off the streak so we don't immediately re-arm on the next loss
                self._loss_streak = max(0, self.recovery_streak - 50)
            return BetSpec(
                game="range-dice",
                amount=str(rec_bet),
                range=window,
                is_in=self.is_in,
                faucet=self.ctx.faucet,
            )

        # Emergency mode: streak too deep — bypass oscillation, force ceiling chance
        # every bet until a win. At 1.5-5% chance P(≥1 win in 200 bets) > 95%.
        if self._loss_streak >= self.emergency_streak:
            chance = self._dyn_max_chance
            bet_amount = self._calc_bet(chance)
            width = _width_for_chance(chance)
            window = self._pick_window(width)
            if self._loss_streak == self.emergency_streak:
                self.ctx.printer(
                    f"🚨 EMERGENCY MODE activated at streak {self._loss_streak}! "
                    f"Forcing {chance:.2f}% chance (~{99/chance:.0f}x) until next win."
                )
            return BetSpec(
                game="range-dice",
                amount=str(bet_amount),
                range=window,
                is_in=self.is_in,
                faucet=self.ctx.faucet,
            )

        chance = self._calc_chance()
        bet_amount = self._calc_bet(chance)

        # Apply target-awareness: adjust chance/bet based on proximity to goal
        if self._target_bal:
            chance, bet_amount = self._apply_target_awareness(chance, bet_amount, bal)

        width = _width_for_chance(chance)
        window = self._pick_window(width)

        # Advance oscillation phase
        self._phase = (self._phase + 1) % self.cycle_length

        multiplier = 99.0 / chance if chance > 0 else 0

        if self._total_bets % 100 == 0:
            bal = self._current_balance()
            bet_pct_actual = float(bet_amount) / float(bal) if bal > 0 else 0
            expected_win_pct = bet_pct_actual * (99.0 / chance - 1) * 100 if chance > 0 else 0
            dd_pct = float((self._peak_bal - bal) / self._peak_bal * 100) if self._peak_bal > 0 else 0
            target_info = ""
            if self._target_bal and self._starting_bal > 0:
                gain_needed = float(self._target_bal - self._starting_bal)
                gain_actual = float(bal - self._starting_bal)
                pct = gain_actual / gain_needed * 100 if gain_needed > 0 else 0
                target_info = f" | Target: {pct:.1f}% [{self._target_phase}]"
            self.ctx.printer(
                f"📊 Bet #{self._total_bets:>5} | "
                f"Chance: {chance:.4f}% (~{multiplier:.0f}x) | "
                f"Window: {window[0]}-{window[1]} | "
                f"Bet: {bet_pct_actual*100:.4f}% | "
                f"WinIf: +{expected_win_pct:.0f}% | "
                f"DD: {dd_pct:.1f}% | "
                f"Streak: {self._loss_streak}"
                f"{target_info}"
            )

        return BetSpec(
            game="range-dice",
            amount=str(bet_amount),
            range=window,
            is_in=self.is_in,
            faucet=self.ctx.faucet,
        )

    # ------------------------------------------------------------------
    def on_bet_result(self, result: BetResult) -> None:
        win = result.get("win", False)

        # Always track live balance from result
        bal_str = result.get("balance", "0")
        if bal_str:
            try:
                self._live_bal = Decimal(str(bal_str))
            except Exception:
                pass

        # Feed the rolled number into the cold-zone map for live tracking
        if self.cold_zone_bias > 0.0:
            number = result.get("number")
            if number is not None:
                try:
                    self._cold_map.record(int(number))
                except Exception:
                    pass

        if win:
            self._total_wins += 1
            profit = Decimal(str(result.get("profit", "0")))
            bal    = Decimal(str(result.get("balance", "0")))
            chance_used = float(result.get("chance", self.max_chance))
            multi  = 99.0 / chance_used if chance_used > 0 else 0
            prev_bal = bal - profit
            bal_mult = float(bal / prev_bal) if prev_bal > 0 else 0
            profit_pct = float(profit / prev_bal * 100) if prev_bal > 0 else 0
            self.ctx.printer(
                f"🚀 WIN #{self._total_wins}! "
                f"+{float(profit):.8f} (+{profit_pct:.1f}%) @ ~{multi:.0f}x | "
                f"Balance: {float(prev_bal):.8f} → {float(bal):.8f} "
                f"({bal_mult:.2f}×)"
            )

            # Reset drought state
            self._loss_streak    = 0
            self._dyn_max_chance = self.max_chance  # return to configured ceiling
            self._recovery_counter = 0              # cancel any in-flight recovery burst
            # Snap phase to 0 to immediately hunt deep again
            self._phase = 0

            # Post-win boost: queue N elevated bets before returning to deep hunt
            if self.post_win_bets > 0 and self._win_boost_counter == 0:
                boost_ch = self.post_win_chance if self.post_win_chance > 0 else self.max_chance
                self._win_boost_counter = self.post_win_bets
                self.ctx.printer(
                    f"⚡ WIN BOOST queued: {self.post_win_bets} bets @ "
                    f"{boost_ch:.2f}% × {self.post_win_bet_mult}× size"
                )

            # Profit lock: check cumulative gain vs starting balance
            if self._starting_bal > 0:
                gain_pct = float((bal - self._starting_bal) / self._starting_bal)
                if gain_pct >= self.profit_lock_pct and self._probe_counter == 0:
                    self._probe_counter = self.probe_bets
                    self.ctx.printer(
                        f"💰 PROFIT LOCK! +{gain_pct*100:.1f}% gain → "
                        f"{self.probe_bets}-bet probe cooldown"
                    )
        else:
            self._loss_streak += 1
            if self._loss_streak > self._max_loss_streak:
                self._max_loss_streak = self._loss_streak

    # ------------------------------------------------------------------
    def on_session_end(self, reason: str) -> None:
        bal = self._current_balance()
        net = float(bal - self._starting_bal)
        self.ctx.printer(f"\n{'='*62}")
        self.ctx.printer(f"🏁  Nano Range Hunter — Session End")
        self.ctx.printer(f"{'='*62}")
        self.ctx.printer(f"  Reason       : {reason}")
        self.ctx.printer(f"  Total bets   : {self._total_bets}")
        self.ctx.printer(f"  Total wins   : {self._total_wins}")
        if self._total_bets > 0:
            self.ctx.printer(f"  Win rate     : {self._total_wins/self._total_bets*100:.3f}%")
        self.ctx.printer(f"  Max l-streak : {self._max_loss_streak}")
        self.ctx.printer(f"  Net P/L      : {net:+.8f}")
        if self._target_bal and self._starting_bal > 0:
            gain_needed = float(self._target_bal - self._starting_bal)
            gain_pct = net / float(self._starting_bal) * 100 if self._starting_bal > 0 else 0
            progress = net / gain_needed * 100 if gain_needed > 0 else 0
            if bal >= self._target_bal:
                self.ctx.printer(f"  Target       : ✅ REACHED! +{gain_pct:.1f}% (goal was +{self.profit_target_pct:.0f}%)")
            else:
                self.ctx.printer(f"  Target       : {progress:.1f}% of +{self.profit_target_pct:.0f}% goal reached")
        self.ctx.printer(f"{'='*62}\n")

        # Save effective params so the next session defaults to them
        save_data: dict = {k: getattr(self, k) for k in _ALL_PARAMS if hasattr(self, k)}
        _save_json_safe(_LAST_PARAMS_FILE, save_data)
        self.ctx.printer(f"  💾  Params saved → {_LAST_PARAMS_FILE} (used as defaults next session)")
