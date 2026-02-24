from __future__ import annotations
# =============================================================================
# nano-range-hunter  VERSION 1
# Snapshot: commit 1974988 (pre-session baseline)
# Changelog:
#   v1 — Original: oscillating chance, cold-zone bias, drought/emergency modes,
#         fractional Kelly sizing, profit-lock probe phase.
# To use: --strategy "nano-range-hunter@v1"
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

import math
import random
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple

from .. import register
from ..base import StrategyContext, BetSpec, BetResult, StrategyMetadata

_DOMAIN = 10_000          # Range Dice total slots  (0 … 9999)
_MIN_SLOT_WIDTH = 1
_COLD_BUCKETS  = 200      # divide 0-9999 into 200 buckets of 50 slots each
_COLD_HISTORY  = 5000     # analyse last N rolls from DB
_COLD_REFRESH  = 300      # refresh map every N bets


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


@register("nano-range-hunter@v1")
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
                "type": "float", "default": 0.12,
                "desc": "Profit target as fraction of balance when hitting at max_chance (0.12 = +12% per ceiling hit). Lower = smaller ceiling bets = much less drain between jackpots.",
            },
            "win_at_nano": {
                "type": "float", "default": 3.0,
                "desc": "Profit target as multiple of balance when hitting at min_chance (3.0 = profit triples balance; new balance = 4×). Geometrically interpolated — bet_pct is monotone, peak drain only at ceiling.",
            },
            "max_bet_pct": {
                "type": "float", "default": 0.004,
                "desc": "Hard cap: max bet as fraction of balance (0.4% safety ceiling)",
            },
            "min_bet_pct": {
                "type": "float", "default": 0.000001,
                "desc": "Theoretical floor (effectively 0 — the API minimum is always the real floor)",
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
            "is_in": {
                "type": "bool", "default": True,
                "desc": "Bet IN the range (True) or OUT of it (False)",
            },
            "cold_zone_bias": {
                "type": "float", "default": 0.65,
                "desc": "How strongly to prefer historically cold number zones (0.0=uniform, 1.0=max cold-bias). Loads last 5 000 rolls from history. Note: PRNG has no memory — this is a preference, not a mathematical edge.",
            },
        }

    # ------------------------------------------------------------------
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.min_chance       = float(params.get("min_chance", 0.01))
        self.max_chance       = float(params.get("max_chance", 1.00))
        self.cycle_length     = max(4, int(params.get("cycle_length", 100)))
        # Win targets — legacy compat: if old target_win_pct is in params, derive from it.
        _legacy = float(params["target_win_pct"]) if "target_win_pct" in params else None
        self.win_at_ceil      = float(params.get("win_at_ceil",  _legacy if _legacy else 0.12))
        self.win_at_nano      = float(params.get("win_at_nano",  _legacy * 10 if _legacy else 3.0))
        self.max_bet_pct      = float(params.get("max_bet_pct", 0.004))
        self.min_bet_pct      = float(params.get("min_bet_pct", 0.000001))
        self.drawdown_sensitivity = float(params.get("drawdown_sensitivity", 4.0))
        self.drawdown_bet_floor   = max(0.0, min(1.0, float(params.get("drawdown_bet_floor", 0.2))))
        self.drought_widen_at = int(params.get("drought_widen_at", 100))
        self.drought_widen_step = float(params.get("drought_widen_step", 0.10))
        self.emergency_streak = int(params.get("emergency_streak", 250))
        self.profit_lock_pct  = float(params.get("profit_lock_pct", 0.75))
        self.probe_bets       = int(params.get("probe_bets", 20))
        self.is_in            = bool(params.get("is_in", True))
        self.cold_zone_bias   = max(0.0, min(1.0, float(params.get("cold_zone_bias", 0.65))))

        # Derived: adaptive ceiling (raised during droughts, reset on wins)
        self._dyn_max_chance  = self.max_chance

        # Cold-zone frequency map
        self._cold_map        = _ColdZoneMap()
        self._cold_refresh_ctr = 0

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

    # ------------------------------------------------------------------
    def on_session_start(self) -> None:
        self._phase           = 0
        self._loss_streak     = 0
        self._max_loss_streak = 0
        self._total_bets      = 0
        self._total_wins      = 0
        self._probe_counter   = 0
        self._cold_refresh_ctr = 0
        self._dyn_max_chance  = self.max_chance
        self._starting_bal    = Decimal(self.ctx.starting_balance)
        self._peak_bal        = self._starting_bal
        self._live_bal        = self._starting_bal

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
        print(f"\n🎯  Nano Range Hunter started")
        print(f"    Chance range  : {self.min_chance}% ↔ {self.max_chance}%")
        print(f"    Multipliers   : ~{99/self.max_chance:.0f}x – ~{99/self.min_chance:.0f}x")
        print(f"    Win at ceiling: +{self.win_at_ceil*100:.0f}% of balance  "
              f"(bet {bp_ceil*100:.3f}% per try)")
        print(f"    Win at nano   : +{self.win_at_nano*100:.0f}% of balance  "
              f"(bet {bp_nano*100:.5f}% per try) → {1+self.win_at_nano:.1f}× account")
        print(f"    Max drain/50  : {bp_ceil*50*100:.1f}% (ceiling phase, no wins)")
        print(f"    Drawdown scale: sensitivity={self.drawdown_sensitivity}  "
              f"floor={self.drawdown_bet_floor:.0%}  (bets shrink as balance falls from peak)")
        print(f"    Bet cap       : {self.max_bet_pct*100:.2f}% of balance per bet")
        print(f"    Drought widen : after {self.drought_widen_at} consecutive losses")
        print(f"    Cold zones    : {cold_status}")
        print(f"    Profit lock   : +{self.profit_lock_pct*100:.0f}% gain triggers {self.probe_bets}-bet reduced-stake cooldown\n")

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
        print(
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
        if bet < Decimal("0.00000034"):
            bet = Decimal("0.00000034")
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
    def next_bet(self) -> Optional[BetSpec]:
        self._total_bets += 1

        bal = self._current_balance()
        if bal <= 0:
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
            probe_bet = max(probe_bet, Decimal("0.00000034"))
            width = _width_for_chance(probe_chance)
            window = self._pick_window(width)
            if self._probe_counter % 10 == 0 and self._probe_counter > 0:
                print(f"🛡️  Probe mode: {self._probe_counter} bets remaining")
            return BetSpec(
                game="range-dice",
                amount=str(probe_bet),
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

        # Emergency mode: streak too deep — bypass oscillation, force ceiling chance
        # every bet until a win. At 1.5-5% chance P(≥1 win in 200 bets) > 95%.
        if self._loss_streak >= self.emergency_streak:
            chance = self._dyn_max_chance
            bet_amount = self._calc_bet(chance)
            width = _width_for_chance(chance)
            window = self._pick_window(width)
            if self._loss_streak == self.emergency_streak:
                print(
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

        width = _width_for_chance(chance)
        window = self._pick_window(width)

        # Advance oscillation phase
        self._phase = (self._phase + 1) % self.cycle_length

        multiplier = 99.0 / chance if chance > 0 else 0

        if self._total_bets % 100 == 0:
            bal = self._current_balance()
            bet_pct_actual = float(bet_amount) / float(bal) if bal > 0 else 0
            expected_win_pct = bet_pct_actual * (99.0 / chance - 1) * 100 if chance > 0 else 0
            # Drawdown info
            dd_pct = float((self._peak_bal - bal) / self._peak_bal * 100) if self._peak_bal > 0 else 0
            print(
                f"📊 Bet #{self._total_bets:>5} | "
                f"Chance: {chance:.4f}% (~{multiplier:.0f}x) | "
                f"Window: {window[0]}-{window[1]} | "
                f"Bet: {bet_pct_actual*100:.4f}% | "
                f"WinIf: +{expected_win_pct:.0f}% | "
                f"DD: {dd_pct:.1f}% | "
                f"Streak: {self._loss_streak}"
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
            print(
                f"🚀 WIN #{self._total_wins}! "
                f"+{float(profit):.8f} (+{profit_pct:.1f}%) @ ~{multi:.0f}x | "
                f"Balance: {float(prev_bal):.8f} → {float(bal):.8f} "
                f"({bal_mult:.2f}×)"
            )

            # Reset drought state
            self._loss_streak    = 0
            self._dyn_max_chance = self.max_chance  # return to configured ceiling
            # Snap phase to 0 to immediately hunt deep again
            self._phase = 0

            # Profit lock: check cumulative gain vs starting balance
            if self._starting_bal > 0:
                gain_pct = float((bal - self._starting_bal) / self._starting_bal)
                if gain_pct >= self.profit_lock_pct and self._probe_counter == 0:
                    self._probe_counter = self.probe_bets
                    print(
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
        print(f"\n{'='*62}")
        print(f"🏁  Nano Range Hunter — Session End")
        print(f"{'='*62}")
        print(f"  Reason       : {reason}")
        print(f"  Total bets   : {self._total_bets}")
        print(f"  Total wins   : {self._total_wins}")
        if self._total_bets > 0:
            print(f"  Win rate     : {self._total_wins/self._total_bets*100:.3f}%")
        print(f"  Max l-streak : {self._max_loss_streak}")
        print(f"  Net P/L      : {net:+.8f}")
        print(f"{'='*62}\n")
