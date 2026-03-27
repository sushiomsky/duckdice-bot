"""
Master Meta-Strategy

Dynamically selects and switches between 15 sub-strategies organised into
three risk tiers based on live performance metrics:

  Tier 0  SAFE        — 9 strategies, conservative, high survival
  Tier 1  MODERATE    — 4 strategies, balanced risk/reward  (default)
  Tier 2  AGGRESSIVE  — 2 strategies, high-variance, optional

Switching triggers (evaluated after every bet):
  • rotation_interval bets elapsed         → rotate to next strategy in tier
  • loss_streak_rotate consecutive losses  → rotate within tier (skip current)
  • loss_streak_deescalate losses          → drop one tier
  • win_streak_escalate consecutive wins   → raise one tier
  • drawdown ≥ drawdown_deescalate_pct     → drop one tier
  • session drawdown ≥ drawdown_emergency_pct → emergency-reset to tier 0

All sub-strategies are instantiated with their EV-optimised defaults.
Each sub-strategy gets its own private recent_results deque to avoid
double-append conflicts.

Removed strategies (bad/redundant):
  fib-loss-cluster, rng-analysis-strategy, chance-descent, luck-cascade
"""

from __future__ import annotations

import random
from collections import deque
from decimal import Decimal
from typing import Any, Deque, Dict, List, Optional

from . import get_strategy, register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

# ── Tier layout ──────────────────────────────────────────────────────────────
# Ordered by EV score descending within each tier.

_TIERS: Dict[int, List[str]] = {
    0: [  # SAFE — conservative, high survival
        "unified-progression",       # score 30.59
        "oscars-grind",              # score 30.22
        "unified-martingale",        # score 30.03
        "target-aware",              # score 30.00
        "unified-faucet",            # score 30.00
        "kelly-capped",              # score 29.99
        "paroli",                    # score 29.99
        "one-three-two-six",         # score 29.89
        "adaptive-survival",         # score 27.05
    ],
    1: [  # MODERATE — balanced risk/reward
        "adaptive-hunter",           # score 21.08
        "chance-cycle-multiplier",   # score 20.26
        "oracle-engine",             # score 19.71
        "simple-progression-40",     # score 14.20
    ],
    2: [  # AGGRESSIVE — high-variance, optional
        "profit-cascade",            # score -5.52, survival 100 %
        "streak-multiplier",         # score -7.29, survival 73 %
    ],
}

_TIER_NAMES = {0: "SAFE", 1: "MODERATE", 2: "AGGRESSIVE"}
_MIN_TIER = 0
_MAX_TIER = 2


# ── PerformanceMonitor ───────────────────────────────────────────────────────

class PerformanceMonitor:
    """Tracks session-wide and per-strategy metrics for switch decisions."""

    def __init__(self, starting_balance: Decimal) -> None:
        self._session_start = starting_balance
        self._strat_start   = starting_balance
        self._balance       = starting_balance
        self._peak          = starting_balance
        self._win_streak    = 0
        self._loss_streak   = 0
        self._strat_bets    = 0

    # ── Called each bet ───────────────────────────────────────────────────

    def record(self, result: BetResult, balance: Decimal) -> None:
        self._balance = balance
        if balance > self._peak:
            self._peak = balance
        win = bool(result.get("win"))
        self._strat_bets += 1
        if win:
            self._win_streak  += 1
            self._loss_streak  = 0
        else:
            self._loss_streak += 1
            self._win_streak   = 0

    def on_switch(self) -> None:
        """Reset per-strategy counters when a switch occurs."""
        self._strat_bets  = 0
        self._win_streak  = 0
        self._loss_streak = 0
        self._strat_start = self._balance

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def balance(self) -> Decimal:
        return self._balance

    @property
    def peak_drawdown(self) -> float:
        """Current peak-to-trough drawdown (0-1)."""
        if self._peak <= 0:
            return 0.0
        return max(0.0, float((self._peak - self._balance) / self._peak))

    @property
    def session_drawdown(self) -> float:
        """Drawdown from session start (0-1)."""
        if self._session_start <= 0 or self._balance >= self._session_start:
            return 0.0
        return float((self._session_start - self._balance) / self._session_start)

    @property
    def win_streak(self) -> int:
        return self._win_streak

    @property
    def loss_streak(self) -> int:
        return self._loss_streak

    @property
    def strat_bets(self) -> int:
        return self._strat_bets


# ── StrategyPool ─────────────────────────────────────────────────────────────

class StrategyPool:
    """Lazy-instantiates sub-strategies and caches them for the session."""

    def __init__(self, master_ctx: StrategyContext) -> None:
        self._master_ctx = master_ctx
        self._cache: Dict[str, Any] = {}

    def get(self, name: str, current_balance: Decimal) -> Optional[Any]:
        """Return a ready-to-use strategy instance (initialises on first call)."""
        if name in self._cache:
            return self._cache[name]
        try:
            cls    = get_strategy(name)
            params = {k: v.get("default") for k, v in cls.schema().items()}
            # Each sub-strategy gets its own private deque to avoid
            # double-append conflicts with the master's deque.
            sub_ctx = StrategyContext(
                api             = self._master_ctx.api,
                symbol          = self._master_ctx.symbol,
                faucet          = self._master_ctx.faucet,
                dry_run         = self._master_ctx.dry_run,
                rng             = self._master_ctx.rng,
                logger          = self._master_ctx.logger,
                limits          = self._master_ctx.limits,
                delay_ms        = self._master_ctx.delay_ms,
                jitter_ms       = self._master_ctx.jitter_ms,
                recent_results  = deque(maxlen=256),
                starting_balance= str(current_balance),
                printer         = self._master_ctx.printer,
            )
            strat = cls(params, sub_ctx)
            strat.on_session_start()
            self._cache[name] = strat
            return strat
        except Exception:
            return None

    def end_all(self, reason: str) -> None:
        for strat in self._cache.values():
            try:
                strat.on_session_end(reason)
            except Exception:
                pass


# ── SwitchEngine ─────────────────────────────────────────────────────────────

class SwitchEngine:
    """Encapsulates all switching and tier-management logic."""

    def __init__(
        self,
        rotation_interval:    int,
        loss_streak_rotate:   int,
        loss_streak_deesc:    int,
        win_streak_esc:       int,
        drawdown_deesc:       float,
        drawdown_emergency:   float,
        starting_tier:        int,
        allow_aggressive:     bool,
        rng:                  random.Random,
    ) -> None:
        self._rotation_interval  = rotation_interval
        self._loss_rotate        = loss_streak_rotate
        self._loss_deesc         = loss_streak_deesc
        self._win_esc            = win_streak_esc
        self._dd_deesc           = drawdown_deesc
        self._dd_emergency       = drawdown_emergency
        self._max_tier           = _MAX_TIER if allow_aggressive else 1
        self._rng                = rng

        self._tier: int          = max(_MIN_TIER, min(starting_tier, self._max_tier))
        self._rr: Dict[int, int] = {t: 0 for t in _TIERS}  # round-robin index per tier
        self._current: str       = _TIERS[self._tier][0]
        self._reason: str        = "init"

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def current(self) -> str:
        return self._current

    @property
    def tier(self) -> int:
        return self._tier

    @property
    def reason(self) -> str:
        return self._reason

    def evaluate(self, perf: PerformanceMonitor) -> Optional[str]:
        """
        Check performance metrics and return the name of the next strategy
        if a switch is warranted, or None to keep the current one.
        Switches are prioritised: emergency > de-escalate > rotate > escalate.
        """
        dd_session = perf.session_drawdown
        dd_peak    = perf.peak_drawdown
        losses     = perf.loss_streak
        wins       = perf.win_streak
        bets       = perf.strat_bets

        # ── Emergency: session drawdown ───────────────────────────────────
        if dd_session >= self._dd_emergency and self._tier != _MIN_TIER:
            self._tier   = _MIN_TIER
            self._reason = f"emergency dd={dd_session:.1%}"
            return self._advance(skip_current=True)

        # ── De-escalate: peak drawdown ────────────────────────────────────
        if dd_peak >= self._dd_deesc and self._tier > _MIN_TIER:
            self._tier   = max(_MIN_TIER, self._tier - 1)
            self._reason = f"deescalate dd={dd_peak:.1%}"
            return self._advance(skip_current=True)

        # ── De-escalate: heavy loss streak ────────────────────────────────
        if losses >= self._loss_deesc and self._tier > _MIN_TIER:
            self._tier   = max(_MIN_TIER, self._tier - 1)
            self._reason = f"deescalate losses={losses}"
            return self._advance(skip_current=True)

        # ── Rotate within tier: moderate loss streak ──────────────────────
        if losses >= self._loss_rotate:
            self._reason = f"rotate losses={losses}"
            return self._advance(skip_current=True)

        # ── Rotate within tier: interval ──────────────────────────────────
        if bets >= self._rotation_interval:
            self._reason = f"interval {bets}bets"
            return self._advance(skip_current=False)

        # ── Escalate: win streak ──────────────────────────────────────────
        if wins >= self._win_esc and self._tier < self._max_tier:
            self._tier   = min(self._max_tier, self._tier + 1)
            self._reason = f"escalate wins={wins}"
            return self._advance(skip_current=False)

        return None  # keep current strategy

    def force_advance(self) -> str:
        """Force a rotation (used when sub-strategy returns None)."""
        self._reason = "sub-strategy stopped"
        return self._advance(skip_current=True)

    # ── Internal ──────────────────────────────────────────────────────────

    def _advance(self, skip_current: bool = False) -> str:
        pool = _TIERS.get(self._tier, _TIERS[_MIN_TIER])
        candidates = [s for s in pool if not skip_current or s != self._current]
        if not candidates:
            candidates = pool

        idx     = self._rr.get(self._tier, 0) % len(candidates)
        chosen  = candidates[idx]
        self._rr[self._tier] = (idx + 1) % len(candidates)
        self._current = chosen
        return chosen


# ── MasterStrategy ───────────────────────────────────────────────────────────

@register("master")
class MasterStrategy:
    """
    Meta-strategy that orchestrates 19 sub-strategies across 3 risk tiers.
    Monitors win/loss streaks and drawdown after every bet, rotating or
    re-tiering as conditions change. All sub-strategies use their
    EV-optimised default parameters from the previous simulation pass.
    """

    @classmethod
    def name(cls) -> str:
        return "master"

    @classmethod
    def describe(cls) -> str:
        return (
            "Meta-strategy cycling 19 sub-strategies across 3 tiers "
            "(Safe / Moderate / Aggressive). Auto-escalates on win streaks, "
            "de-escalates on drawdown or loss streaks, rotates on interval. "
            "All sub-strategies use EV-optimised defaults."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium",
            bankroll_required="Medium",
            volatility="Medium",
            time_to_profit="Moderate",
            recommended_for="Advanced",
            pros=[
                "Adapts automatically to winning and losing conditions",
                "19 strategy styles reduce single-strategy variance",
                "EV-optimised defaults on all sub-strategies",
                "Emergency drawdown protection forces tier 0",
                "Transparent tier/switch logging for review",
            ],
            cons=[
                "Complex internal state — harder to audit than single strategies",
                "Frequent switching can interrupt strategies mid-progression",
                "Aggressive tier (tier 2) adds significant variance",
            ],
            best_use_case=(
                "General-purpose automated sessions where you want adaptive "
                "risk management without manually monitoring strategy performance."
            ),
            tips=[
                "Use starting_tier=0 for conservative capital-preservation sessions",
                "Use starting_tier=1 (default) for balanced growth-and-protection",
                "Set allow_aggressive=False to keep max tier at MODERATE",
                "Increase rotation_interval for strategies that need more bets to cycle",
                "Decrease drawdown_deescalate_pct (e.g. 0.05) for tighter risk control",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "starting_tier": {
                "type": "int",
                "default": 1,
                "desc": "Starting risk tier: 0=Safe, 1=Moderate (default), 2=Aggressive",
            },
            "rotation_interval": {
                "type": "int",
                "default": 75,
                "desc": "Max bets on one strategy before forced rotation within tier",
            },
            "loss_streak_rotate": {
                "type": "int",
                "default": 8,
                "desc": "Consecutive losses before rotating to a different strategy in same tier",
            },
            "loss_streak_deescalate": {
                "type": "int",
                "default": 15,
                "desc": "Consecutive losses before dropping one tier",
            },
            "win_streak_escalate": {
                "type": "int",
                "default": 12,
                "desc": "Consecutive wins before escalating one tier",
            },
            "drawdown_deescalate_pct": {
                "type": "float",
                "default": 0.08,
                "desc": "Peak-to-trough drawdown fraction that triggers de-escalation (0.08 = 8%)",
            },
            "drawdown_emergency_pct": {
                "type": "float",
                "default": 0.20,
                "desc": "Session drawdown fraction that forces emergency reset to tier 0 (0.20 = 20%)",
            },
            "allow_aggressive": {
                "type": "bool",
                "default": True,
                "desc": "Allow escalation to tier 2 (Aggressive). False caps at MODERATE.",
            },
        }

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self._p = {
            "starting_tier":          int(params.get("starting_tier", 1)),
            "rotation_interval":      int(params.get("rotation_interval", 75)),
            "loss_streak_rotate":     int(params.get("loss_streak_rotate", 8)),
            "loss_streak_deescalate": int(params.get("loss_streak_deescalate", 15)),
            "win_streak_escalate":    int(params.get("win_streak_escalate", 12)),
            "drawdown_deescalate_pct":float(params.get("drawdown_deescalate_pct", 0.08)),
            "drawdown_emergency_pct": float(params.get("drawdown_emergency_pct", 0.20)),
            "allow_aggressive":       bool(params.get("allow_aggressive", True)),
        }
        self._balance: Decimal = Decimal(str(ctx.starting_balance))
        # initialised in on_session_start
        self._perf:   Optional[PerformanceMonitor] = None
        self._pool:   Optional[StrategyPool]       = None
        self._engine: Optional[SwitchEngine]       = None
        self._active: Optional[Any]                = None
        self._active_name: str                     = ""
        self._pending_switch: Optional[str]        = None

    def on_session_start(self) -> None:
        self._balance = Decimal(str(self.ctx.starting_balance))
        self._perf    = PerformanceMonitor(self._balance)
        self._pool    = StrategyPool(self.ctx)
        self._engine  = SwitchEngine(
            rotation_interval  = self._p["rotation_interval"],
            loss_streak_rotate = self._p["loss_streak_rotate"],
            loss_streak_deesc  = self._p["loss_streak_deescalate"],
            win_streak_esc     = self._p["win_streak_escalate"],
            drawdown_deesc     = self._p["drawdown_deescalate_pct"],
            drawdown_emergency = self._p["drawdown_emergency_pct"],
            starting_tier      = self._p["starting_tier"],
            allow_aggressive   = self._p["allow_aggressive"],
            rng                = self.ctx.rng,
        )
        self._pending_switch = None
        first = self._engine.current
        self._activate(first)
        self._log(
            f"[MASTER] session start  tier={_TIER_NAMES[self._engine.tier]}  "
            f"strategy={first}"
        )

    def next_bet(self) -> Optional[BetSpec]:
        self._sync_balance()

        # Apply any queued switch before asking for the next bet
        if self._pending_switch is not None:
            self._do_switch(self._pending_switch)
            self._pending_switch = None

        if self._active is None or self._balance <= Decimal("0"):
            return None

        # Ask the active sub-strategy for a bet
        try:
            spec = self._active.next_bet()
        except Exception:
            spec = None

        if spec is None:
            # Sub-strategy signalled it wants to stop — force a rotation
            next_name = self._engine.force_advance()
            self._do_switch(next_name)
            try:
                spec = self._active.next_bet()
            except Exception:
                return None

        return spec

    def on_bet_result(self, result: BetResult) -> None:
        bal_str = result.get("balance")
        if bal_str is not None:
            self._balance = Decimal(str(bal_str))

        # Forward to sub-strategy (it appends to its own private deque)
        if self._active is not None:
            try:
                self._active.on_bet_result(result)
            except Exception:
                pass

        # Master maintains its own deque for ctx.recent_results
        self.ctx.recent_results.append(result)

        # Update performance metrics
        if self._perf is not None:
            self._perf.record(result, self._balance)

        # Evaluate switch conditions — queue for next next_bet() call
        if self._engine is not None and self._perf is not None:
            next_name = self._engine.evaluate(self._perf)
            if next_name is not None and next_name != self._active_name:
                self._pending_switch = next_name

    def on_session_end(self, reason: str) -> None:
        if self._pool is not None:
            self._pool.end_all(reason)
        self._log(f"[MASTER] session end  reason={reason}")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _sync_balance(self) -> None:
        if self.ctx.recent_results:
            bal_str = self.ctx.recent_results[-1].get("balance")
            if bal_str is not None:
                self._balance = Decimal(str(bal_str))

    def _activate(self, name: str) -> None:
        """Instantiate (or retrieve cached) sub-strategy and set as active."""
        strat = self._pool.get(name, self._balance) if self._pool else None
        self._active      = strat
        self._active_name = name

    def _do_switch(self, next_name: str) -> None:
        """Perform the actual strategy switch and log it."""
        prev = self._active_name
        if self._perf is not None:
            self._perf.on_switch()
        tier = _TIER_NAMES.get(self._engine.tier, "?") if self._engine else "?"
        self._log(
            f"[MASTER] {prev} → {next_name}  "
            f"tier={tier}  reason={self._engine.reason if self._engine else '?'}"
        )
        self._activate(next_name)

    def _log(self, msg: str) -> None:
        try:
            self.ctx.printer(msg)
        except Exception:
            pass
