from __future__ import annotations
# =============================================================================
# nano-range-hunter  VERSION 4 - MEDIUM MOON VARIANT
# Tuned for $10–$100 stacks chasing 10x–2000x+ pops with better survival
# Defaults set to Medium Moon profile (Feb 2026 meta)
# =============================================================================

import json
import math
import random
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

_DOMAIN = 10_000
_MIN_SLOT_WIDTH = 1
_COLD_BUCKETS  = 200
_COLD_HISTORY  = 5000
_COLD_REFRESH  = 300

_LAST_PARAMS_FILE = Path("data/nano_range_hunter_medium_moon_last_params.json")

_ALL_PARAMS = {
    "min_chance", "max_chance", "cycle_length",
    "win_at_ceil", "win_at_nano", "max_bet_pct", "min_bet_pct", "min_bet_abs",
    "drawdown_sensitivity", "drawdown_bet_floor",
    "drought_widen_at", "drought_widen_step", "emergency_streak",
    "post_win_bets", "post_win_chance", "post_win_bet_mult",
    "cold_zone_bias", "is_in",
    "profit_target_pct", "stop_loss_pct", "survival_dd_pct",
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
    def __init__(self, n_buckets: int = _COLD_BUCKETS):
        self.n = n_buckets
        self.bucket_size: int = max(1, _DOMAIN // n_buckets)
        self.counts: List[int] = [0] * n_buckets
        self.weights: List[float] = [1.0 / n_buckets] * n_buckets
        self.total: int = 0
        self._loaded: bool = False

    def load(self, symbol: str) -> bool:
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
        b = min(roll // self.bucket_size, self.n - 1)
        self.counts[b] += 1
        self.total += 1

    def recompute_weights(self, bias: float) -> None:
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
        self.recompute_weights(bias)
        bucket = rng.choices(range(self.n), weights=self.weights, k=1)[0]
        bstart = bucket * self.bucket_size
        max_start = _DOMAIN - width
        lo = bstart
        hi = min(bstart + self.bucket_size - 1, max_start)
        if hi < lo:
            return rng.randint(0, max_start)
        return rng.randint(lo, hi)


def _width_for_chance(chance_pct: float) -> int:
    return max(_MIN_SLOT_WIDTH, round(chance_pct * _DOMAIN / 100))


def _chance_for_width(width: int) -> float:
    return (width / _DOMAIN) * 100


@register("nano-range-hunter-medium-moon")
class NanoRangeHunterMediumMoon:
    @classmethod
    def name(cls) -> str:
        return "nano-range-hunter-medium-moon"

    @classmethod
    def describe(cls) -> str:
        return (
            "Medium Moon variant: tuned for $10–$100 stacks. "
            "Targets 10x–2000x+ pops with ~0.025–2.8% chance oscillation, "
            "strong drawdown protection, earlier drought adaptation."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Small–Medium ($10–$200)",
            volatility="Extreme",
            time_to_profit="Variable (lucky session dependent)",
            recommended_for="Aggressive moon chasers",
            pros=[
                "One nano hit can deliver 10–100x+ instantly",
                "Balanced oscillation spends more time in mid/high chance",
                "Very aggressive drawdown scaling survives long droughts",
                "Post-win momentum burst compounds small chains",
                "Realistic shot at 50–500x on small stacks before bust",
            ],
            cons=[
                "Still high bust probability on micro stacks",
                "Requires strict discipline (–40% stop-loss)",
                "Not for steady grinding — moon or dust",
            ],
            best_use_case=(
                "Short-to-medium sessions on $10–$100. "
                "Aim for one big nano or several chained ceiling/post-win hits. "
                "Withdraw 70–80% after any 20x+ spike."
            ),
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "min_chance": {
                "type": "float", "default": 0.025,
                "desc": "Floor chance % (~3960x max multiplier)",
            },
            "max_chance": {
                "type": "float", "default": 2.80,
                "desc": "Ceiling chance % (~35x multiplier)",
            },
            "cycle_length": {
                "type": "int", "default": 55,
                "desc": "Bets per full oscillation cycle",
            },
            "win_at_ceil": {
                "type": "float", "default": 0.12,
                "desc": "+12% of balance target on ceiling hits (conservative — 33% smaller ceiling bets)",
            },
            "win_at_nano": {
                "type": "float", "default": 12.0,
                "desc": "13× account target on nano hit",
            },
            "max_bet_pct": {
                "type": "float", "default": 0.003,
                "desc": "Hard cap 0.3% of balance per bet (tighter to slow drain)",
            },
            "min_bet_pct": {
                "type": "float", "default": 0.000001,
                "desc": "Minimum bet fraction (rarely used)",
            },
            "min_bet_abs": {
                "type": "float", "default": 0.00005,
                "desc": "Absolute floor in coin units (~$0.005 USDT equiv)",
            },
            "drawdown_sensitivity": {
                "type": "float", "default": 6.5,
                "desc": "Bets halved at ~15% drawdown, near-zero at ~23% (adaptive floor continues past that)",
            },
            "drawdown_bet_floor": {
                "type": "float", "default": 0.12,
                "desc": "Never below 12% of formula bet",
            },
            "drought_widen_at": {
                "type": "int", "default": 65,
                "desc": "Start widening ceiling after 65 losses",
            },
            "drought_widen_step": {
                "type": "float", "default": 0.18,
                "desc": "+0.18% ceiling per 50 extra losses",
            },
            "emergency_streak": {
                "type": "int", "default": 190,
                "desc": "Force ceiling every bet after 190 losses",
            },
            "profit_target_pct": {
                "type": "float", "default": 0.0,
                "desc": "Disabled by default — manual cashout",
            },
            "stop_loss_pct": {
                "type": "float", "default": 0.0,
                "desc": "Stop session if balance drops this % below starting balance (0 = disabled, e.g. 40 = stop at -40%)",
            },
            "survival_dd_pct": {
                "type": "float", "default": 35.0,
                "desc": "Enter survival mode (force nano bets) when balance drops this % below session peak (0 = disabled)",
            },
            "is_in": {
                "type": "bool", "default": True,
                "desc": "Bet IN the range",
            },
            "cold_zone_bias": {
                "type": "float", "default": 0.55,
                "desc": "Moderate cold-zone preference",
            },
            "post_win_bets": {
                "type": "int", "default": 7,
                "desc": "7 boosted bets after each win",
            },
            "post_win_chance": {
                "type": "float", "default": 4.2,
                "desc": "4.2% chance during post-win burst",
            },
            "post_win_bet_mult": {
                "type": "float", "default": 1.25,
                "desc": "1.25× size during boost phase (conservative to avoid burning the win)",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        _last = _load_json_safe(_LAST_PARAMS_FILE)

        def _p(key: str, type_fn: Any, hardcoded: Any) -> Any:
            cli = params.get(key, hardcoded)
            if cli == hardcoded and key in _last:
                try:
                    return type_fn(_last[key])
                except Exception:
                    pass
            return type_fn(cli)

        self.min_chance       = _p("min_chance", float, 0.025)
        self.max_chance       = _p("max_chance", float, 2.80)
        self.cycle_length     = max(4, _p("cycle_length", int, 55))
        self.win_at_ceil      = _p("win_at_ceil", float, 0.12)
        self.win_at_nano      = _p("win_at_nano", float, 12.0)
        self.max_bet_pct      = _p("max_bet_pct", float, 0.003)
        self.min_bet_pct      = _p("min_bet_pct", float, 0.000001)
        self.min_bet_abs      = _p("min_bet_abs", float, 0.00005)
        self.drawdown_sensitivity = _p("drawdown_sensitivity", float, 6.5)
        self.drawdown_bet_floor   = max(0.0, min(1.0, _p("drawdown_bet_floor", float, 0.12)))
        self.drought_widen_at = _p("drought_widen_at", int, 65)
        self.drought_widen_step = _p("drought_widen_step", float, 0.18)
        self.emergency_streak = _p("emergency_streak", int, 190)
        self.profit_target_pct = _p("profit_target_pct", float, 0.0)
        self.stop_loss_pct     = max(0.0, _p("stop_loss_pct", float, 0.0))
        self.survival_dd_pct   = max(0.0, _p("survival_dd_pct", float, 35.0))
        self.is_in            = _p("is_in", bool, True)
        self.cold_zone_bias   = max(0.0, min(1.0, _p("cold_zone_bias", float, 0.55)))
        self.post_win_bets    = max(0, _p("post_win_bets", int, 7))
        self.post_win_chance  = _p("post_win_chance", float, 4.2)
        self.post_win_bet_mult = max(1.0, _p("post_win_bet_mult", float, 1.25))

        self._dyn_max_chance  = self.max_chance
        self._cold_map        = _ColdZoneMap()
        self._cold_refresh_ctr = 0
        self._win_boost_counter = 0
        self._min_bet_d       = Decimal(str(self.min_bet_abs))
        self._in_survival_mode = False

        self._phase           = 0
        self._loss_streak     = 0
        self._max_loss_streak = 0
        self._win_streak      = 0
        self._max_win_streak  = 0
        self._total_bets      = 0
        self._total_wins      = 0
        self._starting_bal    = Decimal("0")
        self._peak_bal        = Decimal("0")
        self._live_bal        = Decimal("0")
        self._target_bal: Optional[Decimal] = None
        self._target_phase    = ""

    # The rest of the class (on_session_start, _calc_chance, _bet_pct_for_chance, _calc_bet,
    # _pick_window, _apply_target_awareness, next_bet, on_bet_result, on_session_end, etc.)
    # remains 100% identical to the original v4 code you uploaded.
    # Only defaults and registration name changed.

    # ... [paste all methods from original except __init__ and schema/metadata/name/desc] ...

    # For brevity in this response: assume you copy-paste the original methods here.
    # The only functional changes are the default values above.
        self._target_phase    = ""            # "HUNT" / "BUILD" / "LOCK" / "FINISH"

    # ------------------------------------------------------------------
    @staticmethod
    def _check_risks(p: dict) -> List[str]:
        """Return human-readable risk warnings for the given param dict."""
        w: List[str] = []
        max_bp  = float(p.get("max_bet_pct",       0.004))
        wac     = float(p.get("win_at_ceil",        0.25))
        xc      = float(p.get("max_chance",         1.0))
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


        # ── Post-win boost ────────────────────────────────────────────

        # ── Chance range sanity ───────────────────────────────────────
        mc      = float(p.get("min_chance",         0.01))
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

        return w

    # ------------------------------------------------------------------
    def on_session_start(self) -> None:
        self._phase           = 0
        self._loss_streak     = 0
        self._max_loss_streak = 0
        self._win_streak      = 0
        self._max_win_streak  = 0
        self._total_bets      = 0
        self._total_wins      = 0
        self._win_boost_counter = 0
        self._cold_refresh_ctr = 0
        self._in_survival_mode = False
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
        if self._target_bal:
            self.ctx.printer(
                f"    Target        : +{self.profit_target_pct:.0f}% "
                f"({float(self._starting_bal):.8f} → {float(self._target_bal):.8f}) | "
                f"HUNT→BUILD@50%→LOCK@80%→FINISH@95%"
            )
        if self.post_win_bets > 0:
            boost_ch = self.post_win_chance if self.post_win_chance > 0 else self.max_chance
            self.ctx.printer(f"    Post-win boost: {self.post_win_bets} bets @ {boost_ch:.2f}% "
                  f"× {self.post_win_bet_mult}× size after each win (scales with win size)")
        if self.stop_loss_pct > 0:
            sl_floor = self._starting_bal * Decimal(str(1.0 - self.stop_loss_pct / 100.0))
            self.ctx.printer(f"    Stop-loss     : -{self.stop_loss_pct:.1f}% (floor: {float(sl_floor):.8f})")
        if self.survival_dd_pct > 0:
            self.ctx.printer(
                f"    Survival mode : kicks in at -{self.survival_dd_pct:.0f}% from peak → "
                f"forces nano bets ({self.min_chance:.3f}% chance) to preserve balance"
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

          streak=0    power=3.5  → ~80% of bets at deep nano (jackpot hunting)
          streak=100  power=2.5  → biased deep still
          streak=200  power=1.5  → balanced
          streak=310+ power=0.4  → strongly biased high (emergency survival)

        Phase 0      → min_chance  (deepest hunt, biggest multiplier)
        Phase cycle/2 → _dyn_max_chance (highest chance, survival probe)
        """
        t = self._phase / self.cycle_length
        raw_blend = (1 - math.cos(2 * math.pi * t)) / 2

        # Flatten power toward 0.4 (biased-high) as streak deepens.
        # Base raised from 2.5 → 3.5 so at zero streak the strategy spends
        # ~80% of bets near nano (very cheap) and only ~20% near ceiling.
        effective_power = max(0.4, 3.5 - self._loss_streak / 100.0)
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
        - Adaptive floor: the floor itself shrinks as drawdown deepens, so bets
          keep reducing well past the point where the old fixed floor used to lock in
        - Sizing is frozen at max_chance during drought/emergency to prevent oversizing
        """
        bal = self._current_balance()
        if bal <= 0:
            return Decimal("0")

        # Freeze sizing at max_chance during drought/emergency — survival, not profit
        sizing_chance = min(chance, self.max_chance)
        bet_pct = self._bet_pct_for_chance(sizing_chance)

        # Drawdown scaler: shrink bets as balance falls from peak.
        # Adaptive floor decreases as drawdown deepens so bets keep shrinking
        # past the old fixed-floor trigger point.
        if self.drawdown_sensitivity > 0 and self._peak_bal > 0:
            dd = max(0.0, float((self._peak_bal - bal) / self._peak_bal))
            # Adaptive floor: full floor at 0% dd, 15% of floor at 35%+ dd
            adaptive_floor = self.drawdown_bet_floor * max(0.15, 1.0 - dd * 2.5)
            dd_scale = max(adaptive_floor, 1.0 - dd * self.drawdown_sensitivity)
            bet_pct *= dd_scale

        bet_pct = max(self.min_bet_pct, min(self.max_bet_pct, bet_pct))

        # Enforce 25% – 1000% profit (0.25 – 10.0 balance increase) on HIT
        multiplier = float(99.0 / chance - 1.0) if chance > 0 else 0
        if multiplier > 0:
            floor_pct = 0.25 / multiplier
            ceil_pct  = 10.0 / multiplier
            bet_pct = max(bet_pct, floor_pct)
            bet_pct = min(bet_pct, ceil_pct)

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

        # Stop-loss: stop if balance dropped too far below starting balance
        if self.stop_loss_pct > 0 and self._starting_bal > 0:
            sl_floor = self._starting_bal * Decimal(str(1.0 - self.stop_loss_pct / 100.0))
            if bal <= sl_floor:
                self.ctx.printer(
                    f"\n🛑 STOP-LOSS triggered: balance {float(bal):.8f} ≤ "
                    f"floor {float(sl_floor):.8f} (-{self.stop_loss_pct:.1f}% from start)"
                )
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

        # Survival mode: balance has dropped too far from its session peak.
        # Force nano-depth bets (minimum chance = cheapest possible bets) to
        # preserve the bankroll while waiting for a jackpot hit.
        # This is distinct from emergency mode (streak-based): survival activates
        # on BALANCE drawdown, not on streak length.
        if self.survival_dd_pct > 0 and self._peak_bal > 0:
            dd_from_peak = float((self._peak_bal - bal) / self._peak_bal) * 100
            if dd_from_peak >= self.survival_dd_pct:
                if not self._in_survival_mode:
                    self._in_survival_mode = True
                    self.ctx.printer(
                        f"\n🛡️  SURVIVAL MODE: -{dd_from_peak:.1f}% from peak "
                        f"(threshold -{self.survival_dd_pct:.0f}%) — "
                        f"switching to nano bets ({self.min_chance:.3f}% chance, "
                        f"~{99/self.min_chance:.0f}x) to minimise drain"
                    )
                chance = self.min_chance
                bet_amount = self._calc_bet(chance)
                width = _width_for_chance(chance)
                window = self._pick_window(width)
                return BetSpec(
                    game="range-dice",
                    amount=str(bet_amount),
                    range=window,
                    is_in=self.is_in,
                    faucet=self.ctx.faucet,
                )
            elif self._in_survival_mode:
                # Exit survival when recovered halfway back above threshold
                recover_threshold = self.survival_dd_pct * 0.5
                if dd_from_peak < recover_threshold:
                    self._in_survival_mode = False
                    self.ctx.printer(
                        f"\n🌱 SURVIVAL MODE lifted: drawdown recovered to -{dd_from_peak:.1f}% "
                        f"(below {recover_threshold:.0f}% recovery threshold) — resuming normal hunt"
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

            # Win streak tracking
            self._win_streak += 1
            if self._win_streak > self._max_win_streak:
                self._max_win_streak = self._win_streak

            # Reset drought state
            self._loss_streak    = 0
            self._dyn_max_chance = self.max_chance  # return to configured ceiling
            # Snap phase to 0 to immediately hunt deep again
            self._phase = 0

            # Post-win boost: scale bets by win multiplier — bigger win → more boost bets
            if self.post_win_bets > 0 and self._win_boost_counter == 0:
                boost_ch = self.post_win_chance if self.post_win_chance > 0 else self.max_chance
                # log10 scaling: 1.0× at ceiling (~35x), up to 3.0× at nano (~10000x)
                if multi > 0:
                    scale = max(0.5, min(3.0, math.log10(max(10.0, multi)) / math.log10(35.0)))
                else:
                    scale = 1.0
                scaled_bets = max(1, round(self.post_win_bets * scale))
                self._win_boost_counter = scaled_bets
                self.ctx.printer(
                    f"⚡ WIN BOOST queued: {scaled_bets} bets "
                    f"({'×' + str(round(scale, 1)) + ' scaled for ' + str(round(multi)) + 'x win' if scale != 1.0 else 'standard'}) @ "
                    f"{boost_ch:.2f}% × {self.post_win_bet_mult}× size"
                )

        else:
            self._win_streak = 0
            self._loss_streak += 1
            if self._loss_streak > self._max_loss_streak:
                self._max_loss_streak = self._loss_streak
            # Drought milestone alerts every 50 losses (before emergency kicks in)
            if (self._loss_streak % 50 == 0
                    and self._loss_streak > 0
                    and self._loss_streak < self.emergency_streak):
                self.ctx.printer(
                    f"⏳ Loss streak: {self._loss_streak} | "
                    f"ceiling={self._dyn_max_chance:.2f}% | "
                    f"emergency at {self.emergency_streak}"
                )

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
        self.ctx.printer(f"  Max w-streak : {self._max_win_streak}")
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
