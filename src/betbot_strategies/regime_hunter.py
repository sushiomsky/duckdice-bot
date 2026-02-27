from __future__ import annotations
"""
Regime Hunter — Stochastic Amplifier Strategy

Models the betting process as a non-stationary Markov chain with three
volatility regimes and regime-switching governed by eight state variables.

  Regime A – Extreme Tail Hunting   (0.01% – 1.00%)
  Regime B – Momentum Extraction    (3.00% – 12.00%)
  Regime C – Variance Cooling       (5.00% – 10.00%)

Eight state variables updated continuously:
  B_t  – current balance
  b_t  – last bet size
  p_t  – current win probability (%)
  L_t  – consecutive loss count
  D_t  – bets since last Regime-A extreme hit
  H_t  – total session bets (seed history depth)
  E_t  – entropy / dispersion metric of recent rolls ∈ [0, 1]
  R_t  – realized drawdown from global equity high ∈ [0, 1]

Regime transitions:
  A → B : win occurs in Regime A (tail event captured)
  B → C : drawdown from B-high > b_dd_tolerance  OR  B ≥ b_target_mult × B_entry
  C → A : E_t < c_entropy_thresh  AND  R_t < c_drawdown_thresh
          (enforces minimum c_min_bets before transition)

Bet-size functions:
  Regime A:  b_t = B_t · α · g(L_t, D_t, E_t),  capped at β · B_t
             g(·) = 1 + w_L·ln(1+L̃) + w_D·ln(1+D̃) + w_E·E_t   (sub-exponential)

  Regime B:  b_t = B_t · k · h(W_t, R_Bt),  capped at β · B_t
             h(·) = (1 + κ_W · W_t) · exp(−κ_R · R_Bt)           (convex-concave)

  Regime C:  b_t = B_t · γ · exp(−λ · τ),  floor at c_gamma_floor · B_t
             τ = bets since entering Regime C                       (decay)
"""

import math
from decimal import Decimal
from typing import Any, Dict, List, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_MIN_BET = Decimal("0.00000001")


@register("regime-hunter")
class RegimeHunter:
    """
    Stochastic amplifier: tail-hunt in Regime A, extract momentum in Regime B,
    cool variance in Regime C. All decisions are functions of eight live state
    variables. No fixed progression, no 50% bets, no linear martingale.
    """

    # ── Class-level API ────────────────────────────────────────────────────

    @classmethod
    def name(cls) -> str:
        return "regime-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Three-regime stochastic amplifier: tail-hunt (A) → momentum extraction (B) "
            "→ variance cooling (C). All sizing driven by 8 live state variables. "
            "Targets +25% to +1000%+ balance jumps via fat-tailed equity distribution."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Extreme",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Rare but Explosive",
            recommended_for="Expert",
            pros=[
                "Non-stationary Markov model — adapts to all eight live state variables",
                "Sub-exponential (not linear) martingale prevents rapid blow-up",
                "Momentum Extraction regime compounds single tail wins into streak gains",
                "Variance Cooling regime resets state before next hunting cycle",
                "Hard bet cap β · B_t prevents single-bet ruin",
                "Multi-regime design produces fat-tailed, right-skewed equity distribution",
                "All regime parameters independently configurable",
                "Full state-variable logging every N bets",
            ],
            cons=[
                "Very high variance — extended sessions without hits are expected",
                "Regime B can lose streak gains quickly if drawdown tolerance is low",
                "Cooling regime may feel slow — minimum bet period required",
                "Requires large bankroll for all three regimes to function",
                "Not EV-positive; optimised for distribution shape, not expected value",
                "Psychologically demanding across all three phases",
            ],
            best_use_case=(
                "Expert players with large bankrolls seeking explosive right-tail equity events. "
                "Set stop-loss at -15% to -25%. Use max_bets to bound session length. "
                "Tune α and β in Regime A to control maximum tail exposure."
            ),
            tips=[
                "Regime A: lower a_alpha = safer probing; higher a_beta = bigger single hit",
                "Regime B: b_kappa_w controls convexity — raise for more explosive streaks",
                "Regime B: b_dd_tolerance 0.10–0.20 balances momentum vs survival",
                "Regime C: c_lambda 0.03–0.08 controls cooling speed",
                "Use stop-loss -20% + take-profit +300% for typical sessions",
                "H_t signal gains strength after 200+ bets — early sessions are noisier",
                "Print interval 100 gives clean logs without flooding output",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            # ── Regime A
            "a_chance_min":       {"type": "float", "default": 0.01,  "desc": "A: min win chance % (0.01% = ~9900x)"},
            "a_chance_max":       {"type": "float", "default": 1.00,  "desc": "A: max win chance % (1% = ~99x)"},
            "a_alpha":            {"type": "float", "default": 0.0005,"desc": "A: base risk fraction (b_t = B_t·α·g)"},
            "a_beta":             {"type": "float", "default": 0.02,  "desc": "A: hard bet cap as fraction of B_t"},
            "a_g_streak_weight":  {"type": "float", "default": 0.40,  "desc": "A: g(·) weight on L_t (streak pressure)"},
            "a_g_distance_weight":{"type": "float", "default": 0.30,  "desc": "A: g(·) weight on D_t (hit distance)"},
            "a_g_entropy_weight": {"type": "float", "default": 0.30,  "desc": "A: g(·) weight on E_t (entropy)"},
            # ── Regime B
            "b_chance_min":       {"type": "float", "default": 3.00,  "desc": "B: min win chance %"},
            "b_chance_max":       {"type": "float", "default": 12.00, "desc": "B: max win chance %"},
            "b_k":                {"type": "float", "default": 0.010, "desc": "B: base bet fraction (b_t = B_t·k·h)"},
            "b_kappa_w":          {"type": "float", "default": 0.20,  "desc": "B: h(·) win-streak amplification κ_W"},
            "b_kappa_r":          {"type": "float", "default": 4.00,  "desc": "B: h(·) drawdown dampening κ_R"},
            "b_target_mult":      {"type": "float", "default": 1.50,  "desc": "B: exit when B ≥ entry × this multiple"},
            "b_dd_tolerance":     {"type": "float", "default": 0.15,  "desc": "B: exit when drawdown from B-high > this"},
            "b_max_bets":         {"type": "int",   "default": 150,   "desc": "B: forced exit after this many bets"},
            # ── Regime C
            "c_chance_min":       {"type": "float", "default": 5.00,  "desc": "C: min win chance %"},
            "c_chance_max":       {"type": "float", "default": 10.00, "desc": "C: max win chance %"},
            "c_gamma":            {"type": "float", "default": 0.003, "desc": "C: initial bet fraction (b_t = B_t·γ·exp(-λτ))"},
            "c_gamma_floor":      {"type": "float", "default": 0.0002,"desc": "C: minimum bet fraction during decay"},
            "c_lambda":           {"type": "float", "default": 0.05,  "desc": "C: exponential decay rate λ"},
            "c_min_bets":         {"type": "int",   "default": 40,    "desc": "C: minimum bets before transition to A"},
            "c_entropy_thresh":   {"type": "float", "default": 0.40,  "desc": "C: transition to A when E_t < this"},
            "c_drawdown_thresh":  {"type": "float", "default": 0.08,  "desc": "C: transition to A when R_t < this"},
            # ── Global
            "history_window":     {"type": "int",   "default": 256,   "desc": "Rolling history size for E_t computation"},
            "print_interval":     {"type": "int",   "default": 100,   "desc": "Log state variables every N bets (0=off)"},
            "is_high":            {"type": "bool",  "default": True,   "desc": "Bet High (True) or Low (False)"},
        }

    # ── Init ───────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        def _f(k, d): return float(params.get(k, d))
        def _i(k, d): return int(params.get(k, d))

        # Regime A
        self._a_chance_min        = _f("a_chance_min",        0.01)
        self._a_chance_max        = _f("a_chance_max",        1.00)
        self._a_alpha             = _f("a_alpha",             0.0005)
        self._a_beta              = _f("a_beta",              0.02)
        self._a_g_streak_weight   = _f("a_g_streak_weight",   0.40)
        self._a_g_distance_weight = _f("a_g_distance_weight", 0.30)
        self._a_g_entropy_weight  = _f("a_g_entropy_weight",  0.30)

        # Regime B
        self._b_chance_min        = _f("b_chance_min",        3.00)
        self._b_chance_max        = _f("b_chance_max",        12.00)
        self._b_k                 = _f("b_k",                 0.010)
        self._b_kappa_w           = _f("b_kappa_w",           0.20)
        self._b_kappa_r           = _f("b_kappa_r",           4.00)
        self._b_target_mult       = _f("b_target_mult",       1.50)
        self._b_dd_tolerance      = _f("b_dd_tolerance",      0.15)
        self._b_max_bets          = _i("b_max_bets",          150)

        # Regime C
        self._c_chance_min        = _f("c_chance_min",        5.00)
        self._c_chance_max        = _f("c_chance_max",        10.00)
        self._c_gamma             = _f("c_gamma",             0.003)
        self._c_gamma_floor       = _f("c_gamma_floor",       0.0002)
        self._c_lambda            = _f("c_lambda",            0.05)
        self._c_min_bets          = _i("c_min_bets",          40)
        self._c_entropy_thresh    = _f("c_entropy_thresh",    0.40)
        self._c_drawdown_thresh   = _f("c_drawdown_thresh",   0.08)

        # Global
        self._history_window      = _i("history_window",      256)
        self._print_interval      = _i("print_interval",      100)
        self._is_high             = bool(params.get("is_high", True))

        self._reset_session()

    def _reset_session(self) -> None:
        """Initialise / clear all state variables."""
        # ── Eight state variables ───────────────────────────────────────────
        self._B_t: Decimal   = Decimal("0")    # current balance
        self._b_t: Decimal   = Decimal("0")    # last bet
        self._p_t: float     = self._a_chance_max  # current win-chance %
        self._L_t: int       = 0               # consecutive losses
        self._D_t: int       = 0               # bets since last A-hit
        self._H_t: int       = 0               # total session bets
        self._E_t: float     = 0.5             # entropy metric
        self._R_t: float     = 0.0             # global drawdown

        # ── Regime state ────────────────────────────────────────────────────
        self._regime: str       = "A"

        # Regime A
        self._a_entry_balance: Decimal = Decimal("0")

        # Regime B
        self._B_entry_balance: Decimal = Decimal("0")
        self._B_equity_high:   Decimal = Decimal("0")
        self._W_t: int         = 0     # wins since entering B
        self._R_Bt: float      = 0.0   # drawdown from B equity high
        self._b_bets: int      = 0     # bets taken in B

        # Regime C
        self._tau_c: int       = 0     # bets since entering C

        # ── Global tracking ─────────────────────────────────────────────────
        self._equity_high:  Decimal    = Decimal("0")
        self._history:      List[int]  = []   # 1=win, 0=loss; rolling

        # ── Session stats ────────────────────────────────────────────────────
        self._total_bets:        int   = 0
        self._total_wins:        int   = 0
        self._a_hits:            int   = 0    # wins captured in Regime A
        self._b_cycles:          int   = 0    # times entered Regime B
        self._c_cycles:          int   = 0    # times entered Regime C
        self._session_start_bal: Decimal = Decimal("0")
        self._peak_balance:      Decimal = Decimal("0")

    # ── Session hooks ──────────────────────────────────────────────────────

    def on_session_start(self) -> None:
        self._reset_session()
        bal = Decimal(self.ctx.starting_balance or "0")
        self._B_t              = bal
        self._equity_high      = bal
        self._session_start_bal = bal
        self._peak_balance     = bal
        self._a_entry_balance  = bal

        p = self.ctx.printer
        p(f"\n{'═'*62}")
        p(f"  ⚡  REGIME HUNTER — STOCHASTIC AMPLIFIER")
        p(f"{'═'*62}")
        p(f"  Regime A  : {self._a_chance_min:.2f}% – {self._a_chance_max:.2f}%  "
          f"(α={self._a_alpha:.5f}, β={self._a_beta:.3f})")
        p(f"  Regime B  : {self._b_chance_min:.1f}% – {self._b_chance_max:.1f}%  "
          f"(k={self._b_k:.3f}, κW={self._b_kappa_w}, κR={self._b_kappa_r})")
        p(f"  Regime C  : {self._c_chance_min:.1f}% – {self._c_chance_max:.1f}%  "
          f"(γ={self._c_gamma:.4f}, λ={self._c_lambda:.3f})")
        p(f"  Transitions:  A→B on hit  |  B→C on DD>{self._b_dd_tolerance:.0%} or ×{self._b_target_mult}  "
          f"|  C→A on E<{self._c_entropy_thresh} & R<{self._c_drawdown_thresh:.0%}")
        p(f"  Hard cap  : β={self._a_beta:.1%} per bet")
        p(f"{'═'*62}\n")

    # ── State variable calculations ────────────────────────────────────────

    def _current_balance(self) -> Decimal:
        raw = self.ctx.current_balance_str() or self.ctx.starting_balance or "0"
        return Decimal(str(raw))

    def _update_equity_state(self, balance: Decimal) -> None:
        """Update R_t, B-regime high, and global equity high."""
        self._B_t = balance
        if balance > self._equity_high:
            self._equity_high = balance
        if self._equity_high > Decimal("0"):
            self._R_t = float((self._equity_high - balance) / self._equity_high)
        else:
            self._R_t = 0.0
        if balance > self._peak_balance:
            self._peak_balance = balance
        # Regime B equity high
        if self._regime == "B":
            if balance > self._B_equity_high:
                self._B_equity_high = balance
            if self._B_equity_high > Decimal("0"):
                self._R_Bt = float(
                    (self._B_equity_high - balance) / self._B_equity_high
                )

    def _push_result(self, win: bool) -> None:
        self._history.append(1 if win else 0)
        if len(self._history) > self._history_window:
            self._history = self._history[-self._history_window:]

    def _calc_entropy(self) -> float:
        """
        E_t ∈ [0, 1]: composite dispersion / coldness metric.

        Three components weighted equally:
          1. Local win-rate deficit vs p_t  (cold = high E)
          2. Streak pressure vs expected    (long cold = high E)
          3. Variance deviation from Bernoulli(p_t) expectation
        """
        p_frac = self._p_t / 100.0
        if p_frac <= 0:
            return 0.5

        # Confidence weight: metrics stabilise after enough history
        confidence = min(1.0, self._H_t / max(50.0, 2.0 / p_frac))

        # ── Component 1: win-rate deficit ────────────────────────────────
        n_window = min(len(self._history), max(50, min(self._history_window, int(4.0 / p_frac))))
        if n_window >= 5:
            window = self._history[-n_window:]
            obs_rate = sum(window) / len(window)
            rate_deficit = max(0.0, (p_frac - obs_rate) / p_frac)
            c1 = min(1.0, rate_deficit)
        else:
            c1 = 0.5

        # ── Component 2: streak pressure ────────────────────────────────
        # Expected geometric mean run length = 1/p_frac
        expected_streak = 1.0 / p_frac
        c2 = min(1.0, self._L_t / max(expected_streak * 0.5, 1.0))

        # ── Component 3: variance deviation ─────────────────────────────
        if n_window >= 10:
            window = self._history[-n_window:]
            obs_rate = sum(window) / len(window)
            obs_var  = obs_rate * (1.0 - obs_rate)
            exp_var  = p_frac  * (1.0 - p_frac)
            if exp_var > 1e-12:
                c3 = min(1.0, abs(obs_var - exp_var) / exp_var)
            else:
                c3 = 0.0
        else:
            c3 = 0.5

        raw = (c1 + c2 + c3) / 3.0
        # Regress toward neutral (0.5) when session is young
        return 0.5 + (raw - 0.5) * confidence

    # ── Bet-size functions ─────────────────────────────────────────────────

    def _g_function(self) -> float:
        """
        g(L_t, D_t, E_t): sub-exponential scaling for Regime A.
        Logarithmically bounded — cannot produce runaway exponential growth.
        """
        p_frac = self._p_t / 100.0
        expected = 1.0 / max(p_frac, 1e-6)

        # Normalised inputs; log-compressed to prevent blow-up
        L_norm = self._L_t     / max(expected * 0.5, 1.0)
        D_norm = self._D_t     / max(expected * 1.0, 1.0)
        E_norm = self._E_t                                 # already ∈ [0, 1]

        g = (
            1.0
            + self._a_g_streak_weight   * math.log(1.0 + L_norm)
            + self._a_g_distance_weight * math.log(1.0 + D_norm)
            + self._a_g_entropy_weight  * E_norm
        )
        return g

    def _h_function(self) -> float:
        """
        h(W_t, R_Bt): convex-on-wins, concave-on-drawdown for Regime B.
        High W_t amplifies exposure; high R_Bt suppresses it.
        """
        win_amp   = 1.0 + self._b_kappa_w * self._W_t
        dd_damp   = math.exp(-self._b_kappa_r * self._R_Bt)
        return win_amp * dd_damp

    def _bet_amount(self, frac: float) -> Decimal:
        """Convert a balance fraction to a clamped, valid Decimal bet."""
        balance = self._B_t
        bet = balance * Decimal(str(max(frac, 0.0)))
        # Hard global cap: β · B_t
        hard_cap = balance * Decimal(str(self._a_beta))
        bet = min(bet, hard_cap)
        return max(_MIN_BET, bet)

    # ── Adaptive chance selectors ──────────────────────────────────────────

    def _chance_a(self) -> float:
        """
        Regime A adaptive chance: dive deeper (lower p = bigger M) when
        streak and entropy pressure are high.
        """
        p_frac     = self._p_t / 100.0
        expected   = 1.0 / max(p_frac, 1e-6)
        streak_sig = min(1.0, self._L_t     / max(expected * 1.0, 1.0))
        dist_sig   = min(1.0, self._D_t     / max(expected * 2.0, 1.0))
        pressure   = 0.5 * streak_sig + 0.3 * dist_sig + 0.2 * self._E_t

        # Interpolate: max chance when pressure=0, min chance when pressure=1
        chance = self._a_chance_max - pressure * (self._a_chance_max - self._a_chance_min)
        return max(self._a_chance_min, min(self._a_chance_max, chance))

    def _chance_b(self) -> float:
        """
        Regime B adaptive chance: start at max (frequent wins to build W_t),
        drift toward min as drawdown grows (preserve gains).
        """
        base  = self._b_chance_max
        drift = self._R_Bt * (self._b_chance_max - self._b_chance_min)
        # Also decay slightly with W_t to lock profit once momentum is built
        w_decay = math.exp(-0.04 * self._W_t) * (self._b_chance_max - self._b_chance_min)
        chance = base - drift - w_decay * 0.3
        return max(self._b_chance_min, min(self._b_chance_max, chance))

    def _chance_c(self) -> float:
        """
        Regime C adaptive chance: moderate mid-range, drifting upward
        (toward more wins) as τ grows to normalise win-rate statistics.
        """
        mid   = (self._c_chance_min + self._c_chance_max) / 2.0
        drift = (self._c_chance_max - mid) * (1.0 - math.exp(-0.03 * self._tau_c))
        return max(self._c_chance_min, min(self._c_chance_max, mid + drift))

    # ── Regime transitions ─────────────────────────────────────────────────

    def _enter_regime_b(self, win_profit: Decimal) -> None:
        self._regime          = "B"
        self._b_bets          = 0
        self._W_t             = 0
        self._R_Bt            = 0.0
        self._B_entry_balance = self._B_t
        self._B_equity_high   = self._B_t
        self._b_cycles       += 1

        mult_approx = (100.0 - 1.0) / max(self._p_t, 0.001)
        gain_pct = float(win_profit) / max(float(self._B_t - win_profit), 1e-12) * 100
        p = self.ctx.printer
        p(f"\n{'★'*62}")
        p(f"  💥  A → B  |  Tail event captured!  Regime B activated")
        p(f"  A-hit profit  : +{float(win_profit):.8f}  (~+{gain_pct:.1f}%)")
        p(f"  Payout approx : ~{mult_approx:.0f}×")
        p(f"  Balance now   : {float(self._B_t):.8f}")
        p(f"  A-hits total  : {self._a_hits}  |  B-cycles : {self._b_cycles}")
        p(f"{'★'*62}\n")

    def _enter_regime_c(self, reason: str) -> None:
        self._regime  = "C"
        self._tau_c   = 0
        self._c_cycles += 1

        p = self.ctx.printer
        p(f"\n  ❄  B → C  |  {reason}")
        p(f"     Balance: {float(self._B_t):.8f}  "
          f"R_Bt={self._R_Bt:.2%}  W_t={self._W_t}  bets_in_B={self._b_bets}")
        p(f"     Cooling for ≥{self._c_min_bets} bets (γ={self._c_gamma:.4f}, λ={self._c_lambda:.3f})\n")

    def _enter_regime_a(self, reason: str) -> None:
        self._regime         = "A"
        self._a_entry_balance = self._B_t

        p = self.ctx.printer
        p(f"\n  🎯  C → A  |  {reason}")
        p(f"     E_t={self._E_t:.3f}  R_t={self._R_t:.2%}  "
          f"Balance={float(self._B_t):.8f}  D_t={self._D_t}\n")

    # ── Check regime exit conditions ───────────────────────────────────────

    def _check_b_exit(self) -> Optional[str]:
        """Return reason string if Regime B should exit, else None."""
        if self._R_Bt > self._b_dd_tolerance:
            return f"drawdown {self._R_Bt:.1%} > tolerance {self._b_dd_tolerance:.0%}"
        if (self._B_entry_balance > Decimal("0")
                and self._B_t >= self._B_entry_balance * Decimal(str(self._b_target_mult))):
            return f"target {self._b_target_mult}× entry balance reached"
        if self._b_bets >= self._b_max_bets:
            return f"max bets ({self._b_max_bets}) reached in Regime B"
        return None

    def _check_c_exit(self) -> bool:
        """Return True if Regime C should transition to A."""
        if self._tau_c < self._c_min_bets:
            return False
        return self._E_t < self._c_entropy_thresh and self._R_t < self._c_drawdown_thresh

    # ── Core loop ──────────────────────────────────────────────────────────

    def next_bet(self) -> Optional[BetSpec]:
        self._H_t += 1
        self._total_bets += 1

        # Refresh balance
        self._B_t = self._current_balance()

        # ── Regime A: Extreme Tail Hunting ─────────────────────────────────
        if self._regime == "A":
            self._E_t = self._calc_entropy()
            chance    = self._chance_a()
            self._p_t = chance

            g    = self._g_function()
            frac = self._a_alpha * g
            bet  = self._bet_amount(frac)

        # ── Regime B: Momentum Extraction ──────────────────────────────────
        elif self._regime == "B":
            self._b_bets += 1
            self._E_t    = self._calc_entropy()
            chance       = self._chance_b()
            self._p_t    = chance

            # Check exit before placing bet
            exit_reason = self._check_b_exit()
            if exit_reason:
                self._enter_regime_c(exit_reason)
                # Place first cooling bet immediately
                return self._next_c_bet()

            h    = self._h_function()
            frac = self._b_k * h
            bet  = self._bet_amount(frac)

        # ── Regime C: Variance Cooling ─────────────────────────────────────
        else:  # "C"
            return self._next_c_bet()

        self._b_t = bet

        # State log
        if self._print_interval > 0 and self._H_t % self._print_interval == 0:
            self._log_state()

        return BetSpec(
            game="dice",
            amount=str(bet),
            chance=f"{chance:.4f}",
            is_high=self._is_high,
        )

    def _next_c_bet(self) -> BetSpec:
        """Helper: build one Regime C bet and handle C→A transition."""
        self._tau_c   += 1
        self._E_t      = self._calc_entropy()
        chance         = self._chance_c()
        self._p_t      = chance

        # Exponential decay; floor at c_gamma_floor
        decay_frac = self._c_gamma * math.exp(-self._c_lambda * self._tau_c)
        frac       = max(decay_frac, self._c_gamma_floor)
        bet        = self._bet_amount(frac)
        self._b_t  = bet

        if self._print_interval > 0 and self._H_t % self._print_interval == 0:
            self._log_state()

        # Check transition back to A
        if self._check_c_exit():
            self._enter_regime_a(
                f"E_t={self._E_t:.3f} < {self._c_entropy_thresh}  &  "
                f"R_t={self._R_t:.2%} < {self._c_drawdown_thresh:.0%}"
            )

        return BetSpec(
            game="dice",
            amount=str(bet),
            chance=f"{chance:.4f}",
            is_high=self._is_high,
        )

    # ── Result processing ──────────────────────────────────────────────────

    def on_bet_result(self, result: BetResult) -> None:
        win     = bool(result.get("win", False))
        profit  = Decimal(str(result.get("profit", "0")))
        balance = Decimal(str(result.get("balance", "0") or "0"))

        # Update balance state and equity metrics
        self._update_equity_state(balance)
        self._push_result(win)
        self.ctx.recent_results.append(result)

        if win:
            self._total_wins += 1
            self._L_t = 0
        else:
            self._L_t += 1
            self._D_t += 1

        # ── Regime-specific handling ────────────────────────────────────────
        if self._regime == "A":
            if win:
                self._a_hits += 1
                self._D_t = 0      # reset extreme-hit distance
                self._enter_regime_b(profit)

        elif self._regime == "B":
            if win:
                self._W_t += 1
            # Re-check exit conditions after result (covers mid-bet drawdown)
            exit_reason = self._check_b_exit()
            if exit_reason:
                self._enter_regime_c(exit_reason)

        # Regime C — no special handling; transition checked in next_bet

    # ── Logging ────────────────────────────────────────────────────────────

    def _log_state(self) -> None:
        """Emit full state-variable snapshot."""
        regime_icon = {"A": "🎯", "B": "💥", "C": "❄️ "}
        p = self.ctx.printer
        p(
            f"{regime_icon.get(self._regime,'?')} Bet#{self._H_t:>6}  "
            f"[{self._regime}]  "
            f"B={float(self._B_t):.6f}  "
            f"p_t={self._p_t:.3f}%  "
            f"L={self._L_t}  D={self._D_t}  "
            f"E={self._E_t:.3f}  R={self._R_t:.2%}  "
            f"{'W='+str(self._W_t)+' ' if self._regime=='B' else ''}"
            f"{'τ='+str(self._tau_c)+' ' if self._regime=='C' else ''}"
            f"hits={self._a_hits}/{self._total_bets}"
        )

    # ── Session end ────────────────────────────────────────────────────────

    def on_session_end(self, reason: str) -> None:
        final = self._current_balance()
        pnl   = final - self._session_start_bal
        pnl_pct = float(pnl) / max(float(self._session_start_bal), 1e-12) * 100.0
        peak_pct = (
            float(self._peak_balance - self._session_start_bal)
            / max(float(self._session_start_bal), 1e-12) * 100.0
        )

        p = self.ctx.printer
        p(f"\n{'═'*62}")
        p(f"  🏁  REGIME HUNTER — SESSION END")
        p(f"{'═'*62}")
        p(f"  Reason          : {reason}")
        p(f"  Total bets      : {self._H_t}")
        p(f"  Total wins      : {self._total_wins}")
        p(f"  Regime A hits   : {self._a_hits}")
        p(f"  Regime B cycles : {self._b_cycles}")
        p(f"  Regime C cycles : {self._c_cycles}")
        p(f"  Final regime    : {self._regime}")
        p(f"  Max L_t streak  : (session peak)")
        p(f"  Max D_t         : (session peak)")
        p(f"  Final E_t       : {self._E_t:.4f}")
        p(f"  Final R_t       : {self._R_t:.2%}")
        p(f"  Peak balance    : {float(self._peak_balance):.8f}  (+{peak_pct:.1f}%)")
        p(f"  Session PnL     : {float(pnl):+.8f}  ({pnl_pct:+.2f}%)")
        p(f"  Final balance   : {float(final):.8f}")
        p(f"{'═'*62}\n")
