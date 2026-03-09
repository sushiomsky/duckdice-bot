"""
Oracle Engine Strategy — Advanced 19-Mode Adaptive State Machine Betting Engine

Architecture
============
The Oracle Engine is a fully rule-based state machine that eliminates simple
martingale mechanics in favour of 19 specialised betting modes, each with its
own bet-sizing, chance selection, roll-direction logic, and transition criteria.

State Machine Flow
──────────────────
     ┌──────────────────────────────────────────────┐
     │               ORACLE ENGINE                  │
     │                                              │
     │  ┌─────────────┐   ┌────────────────────┐   │
     │  │  State      │──▶│  Transition Engine │   │
     │  │  Tracker    │   │  (priority rules)  │   │
     │  └─────────────┘   └────────┬───────────┘   │
     │                             │                │
     │  ┌──────────────────────────▼─────────────┐  │
     │  │           Mode Handlers (×19)          │  │
     │  │  GRIND · RECOVERY · SNIPER · COOLDOWN  │  │
     │  │  BALANCE_ATTACK · STREAK_RIDER · …     │  │
     │  └──────────────────────────┬─────────────┘  │
     │                             │                │
     │  ┌──────────────────────────▼─────────────┐  │
     │  │           Bet Composer                 │  │
     │  │  • chance offset  ±1 %                 │  │
     │  │  • random direction override           │  │
     │  │  • max-bet safety cap (10 % bankroll)  │  │
     │  └────────────────────────────────────────┘  │
     └──────────────────────────────────────────────┘

Mode Table (summary — full details in each handler)
════════════════════════════════════════════════════
 Mode              Chance       Bet size           Trigger
 ─────────────────────────────────────────────────────────────────────────
 GRIND             6–12 %       0.10–0.30 %        Default / reset
 RECOVERY          12–35 %      0.20–1.40 %        loss_streak ≥ 3
 SNIPER            0.5–1.5 %    0.10–0.30 %        random 1/150
 COOLDOWN          45–49 %      0.05 %             after BALANCE_ATTACK / STREAK_RIDER
 BALANCE_ATTACK    49.5 %       5–10 %             bankroll +10 %
 STREAK_RIDER      35–45 %      0.30–0.80 %        win_streak ≥ 4
 STREAK_BREAKER    25/49.5/10 % 0.20–0.50 %        loss_streak ≥ 7
 VOLATILITY        5 % / 75 %   0.30–0.70 %        every 100 bets
 MICRO_BET         49.5 %       0.01 %             after STREAK_BREAKER
 BANKROLL_DEFENSE  48–49.5 %    0.05 %             bankroll −30 %
 SCALPER           20–35 %      0.10–0.20 %        periodic from GRIND
 TREND             30–40 %      0.20–0.40 %        periodic from GRIND
 ANTI_STREAK       25–40 %      0.15–0.35 %        periodic from GRIND
 PULSE             8 % / 60 %   0.15–0.30 %        periodic from GRIND
 PROBE             5–50 %       0.005 %            periodic from GRIND
 RISK_BURST        40–49.5 %    0.50–4.50 %        manual / random
 RANDOMIZER        2–49.5 %     0.05–0.50 %        random
 PROFIT_LOCK       49.5 %       0.02 %             profit ≥ 20 %
 ENDGAME           35–49.5 %    variable           profit ≥ 85 % of target
 FALLBACK          49.5 %       0.10 %             error / unknown state

Transition Priority (highest first)
═════════════════════════════════════
 1. bankroll ≤ −30 %                   → BANKROLL_DEFENSE
 2. profit ≥ target × 0.85             → ENDGAME
 3. profit ≥ +20 %                     → PROFIT_LOCK
 4. loss_streak ≥ 7                    → STREAK_BREAKER
 5. loss_streak ≥ 3                    → RECOVERY
 6. win_streak ≥ 4                     → STREAK_RIDER
 7. bankroll ≥ +10 % (40 % prob)       → BALANCE_ATTACK
 8. total_bets % 100 == 0              → VOLATILITY
 9. random 1/150 + allow_sniper        → SNIPER
10. mode_bets limit (mode-specific)    → GRIND / COOLDOWN / MICRO_BET
11. mode_bets ≥ 60 in GRIND (random)   → SCALPER / PULSE / PROBE / TREND / ANTI_STREAK
"""

from __future__ import annotations

import math
import random
from collections import deque
from decimal import ROUND_DOWN, Decimal
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata


# ═══════════════════════════════════════════════════════════════════════════════
# MODE ENUM + DISPLAY LABELS
# ═══════════════════════════════════════════════════════════════════════════════

class Mode(Enum):
    GRIND            = "grind"
    RECOVERY         = "recovery"
    SNIPER           = "sniper"
    COOLDOWN         = "cooldown"
    BALANCE_ATTACK   = "balance_attack"
    STREAK_RIDER     = "streak_rider"
    STREAK_BREAKER   = "streak_breaker"
    VOLATILITY       = "volatility"
    MICRO_BET        = "micro_bet"
    BANKROLL_DEFENSE = "bankroll_defense"
    SCALPER          = "scalper"
    TREND            = "trend"
    ANTI_STREAK      = "anti_streak"
    PULSE            = "pulse"
    PROBE            = "probe"
    RISK_BURST       = "risk_burst"
    RANDOMIZER       = "randomizer"
    PROFIT_LOCK      = "profit_lock"
    ENDGAME          = "endgame"
    FALLBACK         = "fallback"


_MODE_LABEL: Dict[Mode, str] = {
    Mode.GRIND:            "⚙  GRIND",
    Mode.RECOVERY:         "🔄 RECOVERY",
    Mode.SNIPER:           "🎯 SNIPER",
    Mode.COOLDOWN:         "❄  COOLDOWN",
    Mode.BALANCE_ATTACK:   "⚔  BALANCE ATTACK",
    Mode.STREAK_RIDER:     "🏄 STREAK RIDER",
    Mode.STREAK_BREAKER:   "💥 STREAK BREAKER",
    Mode.VOLATILITY:       "⚡ VOLATILITY",
    Mode.MICRO_BET:        "🔬 MICRO BET",
    Mode.BANKROLL_DEFENSE: "🛡  BANKROLL DEFENSE",
    Mode.SCALPER:          "✂  SCALPER",
    Mode.TREND:            "📈 TREND",
    Mode.ANTI_STREAK:      "↩  ANTI-STREAK",
    Mode.PULSE:            "〜 PULSE",
    Mode.PROBE:            "🔭 PROBE",
    Mode.RISK_BURST:       "💣 RISK BURST",
    Mode.RANDOMIZER:       "🎲 RANDOMIZER",
    Mode.PROFIT_LOCK:      "🔒 PROFIT LOCK",
    Mode.ENDGAME:          "🏁 ENDGAME",
    Mode.FALLBACK:         "⚠  FALLBACK",
}


def _lbl(m: Mode) -> str:
    return _MODE_LABEL.get(m, m.value.upper())


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

@register("oracle-engine")
class OracleEngine:
    """
    Oracle Engine — 19-mode adaptive state machine betting strategy.

    Every bet the engine evaluates a priority-ordered set of transition rules
    across bankroll state, streaks, volatility signals, and random triggers,
    then dispatches to the appropriate mode handler.  No simple martingale.

    Parameters
    ----------
    base_bet_pct : float (default 0.002)
        Base bet as a fraction of current bankroll (0.002 = 0.2 %).
    stop_loss_pct : float (default 0.30)
        Halt session when bankroll falls this far below start (0.30 = −30 %).
    profit_target_pct : float (default 0.50)
        Trigger ENDGAME / halt when profit reaches this fraction (0.50 = +50 %).
    starting_mode : str (default "grind")
        Which mode to enter at session start.
    allow_sniper : bool (default True)
        Allow random SNIPER mode triggers (1/150 chance per bet).
    aggression : float (default 1.0)
        Global bet-size multiplier applied on top of each mode's sizing.
        Values > 1 increase all bets proportionally.
    seed : int (default None)
        RNG seed for reproducible sessions.
    """

    # Hard safety cap: never risk more than this fraction in a single bet.
    _MAX_BET_FRACTION = Decimal("0.10")
    _MIN_BET           = Decimal("0.00000001")

    # ── Class-level protocol methods ───────────────────────────────────────────

    @classmethod
    def name(cls) -> str:
        return "oracle-engine"

    @classmethod
    def describe(cls) -> str:
        return (
            "Oracle Engine: 19-mode adaptive state machine.  Dynamically switches "
            "between GRIND, RECOVERY, SNIPER, BALANCE ATTACK, STREAK_RIDER, "
            "PROFIT_LOCK, ENDGAME and 12 more specialised modes using bankroll "
            "state, streaks, volatility signals and random triggers.  No martingale."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Variable (Low to High)",
            bankroll_required="Medium",
            volatility="Adaptive",
            time_to_profit="Variable",
            recommended_for="Intermediate–Expert",
            pros=[
                "19 specialised modes cover every bankroll condition",
                "No simple martingale — Kelly-inspired adaptive sizing",
                "Automatic loss-protection and profit-lock phases",
                "Randomised chance offsets and direction defeat pattern detection",
                "Hard 10 % per-bet cap and stop-loss protect bankroll",
            ],
            cons=[
                "High complexity — many parameters to tune",
                "Greater variance than pure conservative strategies",
                "Mode transitions add short-term unpredictability",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_pct": {
                "type": "float", "default": 0.002,
                "min": 0.0001, "max": 0.05,
                "help": "Base bet fraction of balance (0.002 = 0.2 %)",
            },
            "stop_loss_pct": {
                "type": "float", "default": 0.30,
                "min": 0.05, "max": 0.95,
                "help": "Stop session on this fractional bankroll drop",
            },
            "profit_target_pct": {
                "type": "float", "default": 0.50,
                "min": 0.05, "max": 10.0,
                "help": "Engage ENDGAME / stop at this profit fraction",
            },
            "starting_mode": {
                "type": "str", "default": "grind",
                "choices": [m.value for m in Mode],
                "help": "Initial operating mode",
            },
            "allow_sniper": {
                "type": "bool", "default": True,
                "help": "Enable random SNIPER mode triggers (1/150 probability)",
            },
            "aggression": {
                "type": "float", "default": 1.0,
                "min": 0.1, "max": 3.0,
                "help": "Global bet-size multiplier (1.0 = neutral)",
            },
            "seed": {
                "type": "int", "default": None,
                "help": "RNG seed for reproducibility (None = random)",
            },
        }

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self._base_bet_pct      = Decimal(str(params.get("base_bet_pct",      0.002)))
        self._stop_loss_pct     = Decimal(str(params.get("stop_loss_pct",     0.30)))
        self._profit_target_pct = Decimal(str(params.get("profit_target_pct", 0.50)))
        self._allow_sniper      = bool(params.get("allow_sniper", True))
        self._aggression        = Decimal(str(params.get("aggression",        1.0)))

        seed = params.get("seed")
        self._rng = random.Random(seed) if seed is not None else random.Random()

        mode_str = params.get("starting_mode", "grind")
        try:
            self._mode = Mode(mode_str)
        except ValueError:
            self._mode = Mode.GRIND
        self._prev_mode = self._mode

        # Bankroll state
        self._start_bal:   Decimal = Decimal("0")
        self._current_bal: Decimal = Decimal("0")
        self._peak_bal:    Decimal = Decimal("0")

        # Streak counters
        self._win_streak:  int = 0
        self._loss_streak: int = 0

        # Bet counters
        self._total_bets: int = 0
        self._mode_bets:  int = 0   # bets spent in current mode

        # Roll / result history (last 100)
        self._roll_hist:   Deque[int]  = deque(maxlen=100)
        self._result_hist: Deque[bool] = deque(maxlen=100)

        # Mode-switch audit log (last 30 transitions)
        self._mode_log: List[str] = []

        # Per-mode transient state
        self._pulse_high:      bool = True
        self._vol_high:        bool = True
        self._recovery_step:   int  = 0
        self._risk_burst_left: int  = 0
        self._probe_left:      int  = 0
        self._trend_bias:      float = 0.0   # −1 (low) … +1 (high)

    def on_session_start(self) -> None:
        self._start_bal   = Decimal(self.ctx.starting_balance)
        self._current_bal = Decimal(self.ctx.starting_balance)
        self._peak_bal    = Decimal(self.ctx.starting_balance)

        self._win_streak  = self._loss_streak  = 0
        self._total_bets  = self._mode_bets    = 0
        self._recovery_step = self._risk_burst_left = self._probe_left = 0
        self._trend_bias  = 0.0
        self._pulse_high  = self._vol_high = True
        self._roll_hist.clear()
        self._result_hist.clear()
        self._mode_log.clear()

        self.ctx.printer(f"[Oracle Engine] Session started — {_lbl(self._mode)}")

    # ── Main Loop ──────────────────────────────────────────────────────────────

    def next_bet(self) -> Optional[BetSpec]:
        self._current_bal = self._read_balance()

        if self._should_stop():
            return None

        self._evaluate_transitions()

        spec = self._dispatch()

        # Global safety cap: max 10 % of bankroll per bet
        max_bet = self._current_bal * self._MAX_BET_FRACTION
        amt = min(Decimal(spec["amount"]), max(max_bet, self._MIN_BET))
        amt = max(amt, self._MIN_BET)
        spec["amount"] = str(amt.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN))

        self._total_bets += 1
        self._mode_bets  += 1
        return spec

    def on_bet_result(self, result: BetResult) -> None:
        won  = result.get("win", False)
        bal  = result.get("balance", str(self._current_bal))
        num  = result.get("number", 5000)

        self._current_bal = Decimal(str(bal))
        self._peak_bal    = max(self._peak_bal, self._current_bal)

        # Streaks
        if won:
            self._win_streak  += 1
            self._loss_streak  = 0
        else:
            self._loss_streak += 1
            self._win_streak   = 0

        self._result_hist.append(won)
        self._roll_hist.append(num)

        # Mode-specific counters
        if self._mode == Mode.RECOVERY:
            self._recovery_step = max(0, self._recovery_step + (0 if won else 1) - (1 if won else 0))
        elif self._mode == Mode.RISK_BURST:
            self._risk_burst_left = max(0, self._risk_burst_left - 1)
        elif self._mode == Mode.PROBE:
            self._probe_left = max(0, self._probe_left - 1)

        # Rolling trend bias: (mean_roll − 5000) / 5000
        if len(self._roll_hist) >= 10:
            mean_r = sum(self._roll_hist) / len(self._roll_hist)
            self._trend_bias = (mean_r - 5000.0) / 5000.0

    def on_session_end(self, reason: str) -> None:
        if self._start_bal > 0:
            pnl  = self._current_bal - self._start_bal
            sign = "+" if pnl >= 0 else ""
            recent_modes = " → ".join(self._mode_log[-6:]) or self._mode.value
            self.ctx.printer(
                f"[Oracle Engine] End: {reason} | "
                f"P&L: {sign}{float(pnl):.8f} | "
                f"Bets: {self._total_bets} | "
                f"Modes: {recent_modes}"
            )

    # ══════════════════════════════════════════════════════════════════════════
    # TRANSITION ENGINE
    # ══════════════════════════════════════════════════════════════════════════

    def _evaluate_transitions(self) -> None:  # noqa: C901 (complexity OK for a state machine)
        """
        Priority-ordered transition rules.  Higher blocks can only be reached
        if lower-priority blocks did not already set new_mode.

        Priority order
        ──────────────
        1  Bankroll defence (hard floor)
        2  Endgame (near profit target)
        3  Profit lock (≥ 20 % profit)
        4  Streak breaker (≥ 7 losses)
        5  Recovery (≥ 3 losses)
        6  Streak rider (≥ 4 wins)
        7  Balance attack (+10 % bankroll, probabilistic)
        8  Periodic volatility burst (every 100 bets)
        9  Random sniper (1/150 per bet)
        10 Mode duration limits
        11 Variety injection from long GRIND sessions
        """
        if self._start_bal == 0:
            return

        bal     = self._current_bal
        pct     = float((bal - self._start_bal) / self._start_bal)
        mode    = self._mode
        losses  = self._loss_streak
        wins    = self._win_streak
        mbets   = self._mode_bets
        target  = float(self._profit_target_pct)

        new_mode: Optional[Mode] = None

        # ── 1. Bankroll defence ────────────────────────────────────────────────
        if pct <= -0.30 and mode != Mode.BANKROLL_DEFENSE:
            new_mode = Mode.BANKROLL_DEFENSE

        # ── 2. Endgame ─────────────────────────────────────────────────────────
        elif target > 0 and pct >= target * 0.85 and mode not in (Mode.ENDGAME, Mode.PROFIT_LOCK):
            new_mode = Mode.ENDGAME

        # ── 3. Profit lock ─────────────────────────────────────────────────────
        elif pct >= 0.20 and mode not in (Mode.PROFIT_LOCK, Mode.ENDGAME, Mode.COOLDOWN):
            new_mode = Mode.PROFIT_LOCK

        # ── 4. Streak breaker ──────────────────────────────────────────────────
        elif losses >= 7 and mode not in (
            Mode.BANKROLL_DEFENSE, Mode.STREAK_BREAKER, Mode.MICRO_BET,
            Mode.PROFIT_LOCK, Mode.ENDGAME,
        ):
            new_mode = Mode.STREAK_BREAKER

        # ── 5. Recovery ────────────────────────────────────────────────────────
        # PROFIT_LOCK / ENDGAME already use dust bets — no need to escalate for minor losses
        elif losses >= 3 and mode not in (
            Mode.RECOVERY, Mode.BANKROLL_DEFENSE, Mode.STREAK_BREAKER,
            Mode.PROFIT_LOCK, Mode.ENDGAME,
        ):
            new_mode = Mode.RECOVERY

        # ── 6. Streak rider ────────────────────────────────────────────────────
        elif wins >= 4 and mode not in (Mode.STREAK_RIDER, Mode.PROFIT_LOCK, Mode.ENDGAME, Mode.COOLDOWN):
            new_mode = Mode.STREAK_RIDER

        # ── 7. Balance attack ──────────────────────────────────────────────────
        elif (
            pct >= 0.10
            and mode not in (Mode.BALANCE_ATTACK, Mode.PROFIT_LOCK, Mode.ENDGAME, Mode.COOLDOWN, Mode.BANKROLL_DEFENSE)
            and self._rng.random() < 0.40
        ):
            new_mode = Mode.BALANCE_ATTACK

        # ── 8. Periodic volatility burst ──────────────────────────────────────
        elif self._total_bets > 0 and self._total_bets % 100 == 0 and mode != Mode.BANKROLL_DEFENSE:
            new_mode = Mode.VOLATILITY

        # ── 9. Random sniper ───────────────────────────────────────────────────
        elif (
            self._allow_sniper
            and self._rng.random() < (1 / 150)
            and mode not in (Mode.SNIPER, Mode.BANKROLL_DEFENSE, Mode.ENDGAME, Mode.PROFIT_LOCK)
        ):
            new_mode = Mode.SNIPER

        # ── 10. Mode duration limits ───────────────────────────────────────────
        elif mbets >= 25 and mode in (Mode.SNIPER, Mode.VOLATILITY, Mode.RANDOMIZER):
            new_mode = Mode.GRIND
        elif mbets >= 20 and mode == Mode.RISK_BURST:
            new_mode = Mode.GRIND
        elif mbets >= 50 and mode in (Mode.BALANCE_ATTACK, Mode.STREAK_RIDER):
            new_mode = Mode.COOLDOWN
        elif mbets >= 20 and mode == Mode.COOLDOWN:
            new_mode = Mode.GRIND
        elif mbets >= 40 and mode == Mode.RECOVERY and losses == 0:
            new_mode = Mode.GRIND
        elif mbets >= 15 and mode == Mode.STREAK_BREAKER:
            new_mode = Mode.MICRO_BET
        elif mbets >= 20 and mode == Mode.MICRO_BET:
            new_mode = Mode.GRIND
        elif mbets >= 60 and mode == Mode.PROFIT_LOCK and losses == 0:
            new_mode = Mode.GRIND   # Quiet period over — resume normal grinding
        elif mbets >= 30 and mode == Mode.BANKROLL_DEFENSE and pct > -0.15:
            new_mode = Mode.GRIND

        # ── 11. Variety injection from long GRIND sessions ────────────────────
        elif mbets >= 60 and mode == Mode.GRIND:
            roll = self._rng.random()
            if roll < 0.15:
                new_mode = Mode.SCALPER
            elif roll < 0.28:
                new_mode = Mode.PULSE
            elif roll < 0.40:
                new_mode = Mode.PROBE
            elif roll < 0.52:
                new_mode = Mode.TREND
            elif roll < 0.62:
                new_mode = Mode.ANTI_STREAK
            elif roll < 0.70:
                new_mode = Mode.RISK_BURST
            elif roll < 0.76:
                new_mode = Mode.RANDOMIZER

        if new_mode is not None and new_mode != mode:
            self._switch_mode(new_mode)

    def _switch_mode(self, new_mode: Mode) -> None:
        prev = self._mode
        self._prev_mode = prev
        self._mode      = new_mode
        self._mode_bets = 0

        # Initialise mode-specific transient state
        if new_mode == Mode.RECOVERY:
            self._recovery_step = min(self._loss_streak, 6)
        elif new_mode == Mode.RISK_BURST:
            self._risk_burst_left = 10 + self._rng.randint(0, 10)
        elif new_mode == Mode.PROBE:
            self._probe_left = 5 + self._rng.randint(0, 10)
        elif new_mode == Mode.PULSE:
            self._pulse_high = bool(self._rng.randint(0, 1))
        elif new_mode == Mode.VOLATILITY:
            self._vol_high = bool(self._rng.randint(0, 1))

        self._mode_log.append(new_mode.value)
        if len(self._mode_log) > 30:
            self._mode_log.pop(0)

        self.ctx.printer(f"[Oracle Engine] {_lbl(prev)} → {_lbl(new_mode)}  (bet #{self._total_bets})")

    # ══════════════════════════════════════════════════════════════════════════
    # MODE DISPATCH
    # ══════════════════════════════════════════════════════════════════════════

    def _dispatch(self) -> BetSpec:
        _handlers = {
            Mode.GRIND:            self._mode_grind,
            Mode.RECOVERY:         self._mode_recovery,
            Mode.SNIPER:           self._mode_sniper,
            Mode.COOLDOWN:         self._mode_cooldown,
            Mode.BALANCE_ATTACK:   self._mode_balance_attack,
            Mode.STREAK_RIDER:     self._mode_streak_rider,
            Mode.STREAK_BREAKER:   self._mode_streak_breaker,
            Mode.VOLATILITY:       self._mode_volatility,
            Mode.MICRO_BET:        self._mode_micro_bet,
            Mode.BANKROLL_DEFENSE: self._mode_bankroll_defense,
            Mode.SCALPER:          self._mode_scalper,
            Mode.TREND:            self._mode_trend,
            Mode.ANTI_STREAK:      self._mode_anti_streak,
            Mode.PULSE:            self._mode_pulse,
            Mode.PROBE:            self._mode_probe,
            Mode.RISK_BURST:       self._mode_risk_burst,
            Mode.RANDOMIZER:       self._mode_randomizer,
            Mode.PROFIT_LOCK:      self._mode_profit_lock,
            Mode.ENDGAME:          self._mode_endgame,
            Mode.FALLBACK:         self._mode_fallback,
        }
        handler = _handlers.get(self._mode, self._mode_fallback)
        try:
            return handler()
        except Exception:
            return self._mode_fallback()

    # ══════════════════════════════════════════════════════════════════════════
    # MODE HANDLERS
    # ══════════════════════════════════════════════════════════════════════════

    def _mode_grind(self) -> BetSpec:
        """
        Low-risk steady grinding.
        Chance 6–12 %.  Bet 0.10–0.30 % of bankroll.
        Designed for sustained, low-variance accumulation.
        """
        chance  = 6.0 + self._rng.uniform(0.0, 6.0)
        bet_pct = Decimal(str(round(0.001 + self._rng.uniform(0.0, 0.002), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_recovery(self) -> BetSpec:
        """
        Triggered after 3+ consecutive losses.
        Gradually escalates chance (12 → 33 %) and bet size (0.2 → 1.4 %) as
        the step counter increases with each loss, reducing on each win.
        Avoids doubling-down; uses a softer ramp.
        """
        step    = min(self._recovery_step, 6)
        chance  = 12.0 + step * 3.5                              # 12–33.5 %
        bet_pct = Decimal(str(round(0.002 + step * 0.002, 6)))   # 0.20–1.40 %
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_sniper(self) -> BetSpec:
        """
        Rare high-multiplier opportunistic shot.
        Chance 0.5–1.5 % (payout ~67× – 200×).  Tiny bet: 0.10–0.30 % bankroll.
        Triggered randomly at ~1/150 probability per bet.
        """
        chance  = 0.5  + self._rng.uniform(0.0, 1.0)
        bet_pct = Decimal(str(round(0.001 + self._rng.uniform(0.0, 0.002), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_cooldown(self) -> BetSpec:
        """
        Profit-protection phase.  Ultra-conservative near-even bets.
        Entered after BALANCE_ATTACK or STREAK_RIDER to consolidate gains.
        Chance 45–49 %.  Bet 0.05 % bankroll.
        """
        chance  = 45.0 + self._rng.uniform(0.0, 4.0)
        bet_pct = Decimal("0.0005")
        amount  = self._current_bal * bet_pct
        return self._make_spec(amount, chance)

    def _mode_balance_attack(self) -> BetSpec:
        """
        Aggressive push when ahead ≥ 10 %.
        Near-even 49.5 % chance for ~1× payout.  Bet 5–10 % of bankroll.
        High frequency wins accelerate bankroll growth from a position of safety.
        """
        chance  = 49.5
        frac    = Decimal(str(round(self._rng.uniform(0.05, 0.10), 4)))
        amount  = self._current_bal * frac * self._aggression
        return self._make_spec(amount, chance)

    def _mode_streak_rider(self) -> BetSpec:
        """
        Activated after 4+ consecutive wins.  Escalates bet size with streak
        length (capped at 3× base) to capitalise on runs.
        Chance 35–45 %.  Bet 0.30–0.80 % + streak bonus.
        """
        bonus   = min(self._win_streak * 0.10, 0.30)    # +0–30 % of base
        chance  = 35.0 + self._rng.uniform(0.0, 10.0)
        bet_pct = Decimal(str(round((0.003 + self._rng.uniform(0.0, 0.005)) * (1.0 + bonus), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_streak_breaker(self) -> BetSpec:
        """
        Activated after 7+ consecutive losses.
        Cycles through three radically different patterns every 3 bets to
        disrupt perceived streaks: 25 % → 49.5 % → 10 %.
        Direction is fully randomised to prevent bias entrenchment.
        """
        phase   = self._mode_bets % 3
        chance  = (25.0, 49.5, 10.0)[phase]
        bet_pct = Decimal(str(round(0.002 + self._rng.uniform(0.0, 0.003), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance, is_high=self._rng.random() > 0.5)

    def _mode_volatility(self) -> BetSpec:
        """
        Short high-risk bursts triggered every 100 bets.
        Alternates sharply between 75 % (easy win, low payout) and 5 %
        (hard win, high payout) on successive bets.
        Bet 0.30–0.70 % bankroll.
        """
        self._vol_high = not self._vol_high
        chance  = 75.0 if self._vol_high else 5.0
        bet_pct = Decimal(str(round(0.003 + self._rng.uniform(0.0, 0.004), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_micro_bet(self) -> BetSpec:
        """
        Risk-reset phase after STREAK_BREAKER.
        Near-certain 49.5 % chance.  Bet is 0.01 % bankroll — dust level.
        Goal: rebuild psychological and statistical baseline before resuming.
        """
        amount = self._current_bal * Decimal("0.0001")
        return self._make_spec(amount, 49.5)

    def _mode_bankroll_defense(self) -> BetSpec:
        """
        Emergency capital protection when bankroll is ≤ 70 % of start.
        Near-even 48–49.5 % chance.  Bet 0.05 % only.
        Stays active until bankroll recovers to −15 % of start.
        """
        chance  = 48.0 + self._rng.uniform(0.0, 1.5)
        amount  = self._current_bal * Decimal("0.0005")
        return self._make_spec(amount, chance)

    def _mode_scalper(self) -> BetSpec:
        """
        Many small quick bets at moderate win probability.
        Chance 20–35 %.  Bet 0.10–0.20 % bankroll.
        Suitable for steady nibbling at the house edge.
        """
        chance  = 20.0 + self._rng.uniform(0.0, 15.0)
        bet_pct = Decimal(str(round(0.001 + self._rng.uniform(0.0, 0.001), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_trend(self) -> BetSpec:
        """
        Roll-distribution-aware betting.
        Analyses the rolling mean of the last ≤100 dice rolls (0–9999).
        If the mean is above 5000 (high bias), bets LOW to go against the
        trend; if below 5000, bets HIGH.  Chance adjusts with bias strength.
        """
        bias      = self._trend_bias           # −1 … +1
        chance    = 30.0 + abs(bias) * 10.0    # 30–40 %
        is_high   = bias < 0.0                 # bet against the trend
        bet_pct   = Decimal(str(round(0.002 + self._rng.uniform(0.0, 0.002), 6)))
        amount    = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance, is_high=is_high)

    def _mode_anti_streak(self) -> BetSpec:
        """
        Contrarian pattern inversion.
        Examines last 10 outcomes; if more wins than losses, bets low
        (expecting regression); if more losses, bets high.
        Chance 25–40 %.  Bet 0.15–0.35 % bankroll.
        """
        recent_wins = sum(1 for r in list(self._result_hist)[-10:] if r)
        is_high     = recent_wins < 5
        chance      = 25.0 + self._rng.uniform(0.0, 15.0)
        bet_pct     = Decimal(str(round(0.0015 + self._rng.uniform(0.0, 0.002), 6)))
        amount      = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance, is_high=is_high)

    def _mode_pulse(self) -> BetSpec:
        """
        Alternating high/low chance every single bet.
        60 % (high chance, ~1.6× payout) → 8 % (low chance, ~12× payout) → repeat.
        Bet 0.15–0.30 % bankroll.
        Creates a natural win/loss oscillation that can stack gains.
        """
        self._pulse_high = not self._pulse_high
        chance  = 60.0 if self._pulse_high else 8.0
        bet_pct = Decimal(str(round(0.0015 + self._rng.uniform(0.0, 0.0015), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_probe(self) -> BetSpec:
        """
        Tiny fully-random exploratory bets that gather roll distribution data
        while resetting the engine's behavioural baseline.
        Chance: fully random 5–50 %.  Bet: 0.005 % (dust amount).
        """
        chance  = self._rng.uniform(5.0, 50.0)
        amount  = self._current_bal * Decimal("0.00005")
        return self._make_spec(amount, chance)

    def _mode_risk_burst(self) -> BetSpec:
        """
        Short aggressive burst phase (10–20 bets).
        Near-even 40–49.5 % chance with significantly elevated bet size.
        Bet 0.50–4.50 % bankroll.  High expected value per unit time.
        """
        chance  = 40.0 + self._rng.uniform(0.0, 9.5)
        bet_pct = Decimal(str(round(0.005 + self._rng.uniform(0.0, 0.040), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_randomizer(self) -> BetSpec:
        """
        Fully chaotic betting to break any pattern that a sequence-analysing
        RNG might detect.
        Chance: random 2–49.5 %.  Bet: random 0.05–0.50 % bankroll.
        Direction and everything else is random.
        """
        chance  = self._rng.uniform(2.0, 49.5)
        bet_pct = Decimal(str(round(self._rng.uniform(0.0005, 0.005), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance, is_high=self._rng.random() > 0.5)

    def _mode_profit_lock(self) -> BetSpec:
        """
        Entered when profit ≥ 20 %.  Drastically reduces exposure.
        Near-even 49.5 % chance.  Bet only 0.02 % bankroll.
        Protects accumulated gains while still turning the engine.
        """
        amount = self._current_bal * Decimal("0.0002")
        return self._make_spec(amount, 49.5)

    def _mode_endgame(self) -> BetSpec:
        """
        Activated when within 15 % of profit target.
        If gap to target is ≤ 1 % of bankroll, places a single near-exact bet.
        Otherwise bets moderately (35–45 %) with slightly elevated sizing.
        Exits session when target is reached (via _should_stop).
        """
        remaining = self._profit_remaining()
        if remaining <= self._current_bal * Decimal("0.01"):
            # Final push — bet just enough to close the gap
            amount = remaining * Decimal("1.02") + self._MIN_BET
            return self._make_spec(amount, 49.5)
        chance  = 35.0 + self._rng.uniform(0.0, 10.0)
        bet_pct = Decimal(str(round(0.003 + self._rng.uniform(0.0, 0.005), 6)))
        amount  = self._current_bal * bet_pct * self._aggression
        return self._make_spec(amount, chance)

    def _mode_fallback(self) -> BetSpec:
        """
        Safe fallback for any unhandled / error states.
        Near-even 49.5 % chance.  Bet 0.10 % bankroll.
        """
        amount = self._current_bal * Decimal("0.001")
        return self._make_spec(amount, 49.5)

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _make_spec(
        self,
        amount:  Decimal,
        chance:  float,
        *,
        is_high: Optional[bool] = None,
    ) -> BetSpec:
        """
        Compose a final BetSpec, applying:
          • Random chance offset ±1 %
          • Random roll direction (is_high) unless explicitly provided
          • Amount floor at MIN_BET
        """
        # Chance offset ±1 % (avoids deterministic patterns)
        chance += self._rng.uniform(-1.0, 1.0)
        chance  = max(0.01, min(97.0, chance))

        # Direction: random unless the mode explicitly overrides
        if is_high is None:
            is_high = self._rng.random() > 0.5

        amount = max(amount, self._MIN_BET)

        return {
            "game":    "dice",
            "amount":  str(amount.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)),
            "chance":  f"{chance:.2f}",
            "is_high": is_high,
        }

    def _read_balance(self) -> Decimal:
        """Read latest balance from result history; fall back to cached value."""
        if self.ctx.recent_results:
            last = self.ctx.recent_results[-1]
            raw  = last.get("balance")
            if raw:
                return Decimal(str(raw))
        return self._current_bal if self._current_bal > 0 else self._start_bal

    def _profit_remaining(self) -> Decimal:
        """Distance between current balance and profit target balance."""
        target = self._start_bal * (1 + self._profit_target_pct)
        return max(Decimal("0"), target - self._current_bal)

    def _should_stop(self) -> bool:
        """Return True if stop-loss or profit-target is breached."""
        if self._start_bal == 0:
            return False
        pct = float((self._current_bal - self._start_bal) / self._start_bal)
        if pct <= -float(self._stop_loss_pct):
            self.ctx.printer(f"[Oracle Engine] ⛔ Stop-loss triggered ({pct:.1%})")
            return True
        if pct >= float(self._profit_target_pct):
            self.ctx.printer(f"[Oracle Engine] 🎉 Profit target reached ({pct:.1%})")
            return True
        return False
