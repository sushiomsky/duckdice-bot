from __future__ import annotations
"""
Combined High-Roller System
===========================
Three aggressive betting modes with automatic switching based on recent roll
history and strict bankroll protection.

Modes
-----
1. Kelly Hybrid (default)         — scaled bets on win streaks (8 → 12 → 18 %)
2. Streak Harvester               — exponential ladder on confirmed streaks
3. Volatility Breakout            — fixed-tier escalation on high variance windows

Bet type
--------
Range Dice (0-9999) — always "is_in".  The range window is chosen as the
contiguous 5 000-slot block (≈ 50 % chance, payout ≈ ×1.98) whose numbers
have been rolled least often so far.  With no history the mid-window
2500-7499 is used as a neutral starting point.

Protection rules
----------------
• Stop-loss  : bankroll ≤ start × (1 − stop_loss)      (default −35 %)
• Profit goal: bankroll ≥ start × profit_target         (default ×2)
• Max bet cap: bet ≤ bankroll × max_bet_fraction        (hard 20 % limit)
"""

from collections import deque
from decimal import Decimal, getcontext
from typing import Any, Deque, Dict, List, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

getcontext().prec = 28

# Mode identifiers
_KELLY    = "kelly_hybrid"
_HARVEST  = "streak_harvester"
_BREAKOUT = "volatility_breakout"

# Kelly Hybrid win-streak → bet fraction table
_KELLY_LADDER: List[Decimal] = [
    Decimal("0.08"),   # streak 0–1
    Decimal("0.08"),   # streak 1
    Decimal("0.12"),   # streak 2
    Decimal("0.18"),   # streak 3+
]

# Volatility Breakout fixed tiers
_BREAKOUT_LADDER: List[Decimal] = [
    Decimal("0.10"),
    Decimal("0.15"),
    Decimal("0.22"),   # cap at max_bet_fraction enforced by _cap_bet
]


@register("combined-high-roller")
class CombinedHighRollerStrategy:
    """
    Combined High-Roller System: three aggressive modes (Kelly Hybrid /
    Streak Harvester / Volatility Breakout) with automatic switching and
    strict 35 % stop-loss / 2× profit-target protection.
    """

    # ------------------------------------------------------------------ #
    #  Class-level metadata                                               #
    # ------------------------------------------------------------------ #

    @classmethod
    def name(cls) -> str:
        return "combined-high-roller"

    @classmethod
    def describe(cls) -> str:
        return (
            "Three-mode aggressive system (Kelly Hybrid / Streak Harvester / "
            "Volatility Breakout) on Range Dice — always targets the coldest "
            "50 % window with 35 % stop-loss."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Large",
            volatility="High",
            time_to_profit="Quick",
            recommended_for="Experts",
            pros=[
                "Aggressive bankroll growth potential (targets ×2 per session)",
                "Adaptive mode switching reacts to live roll patterns",
                "Hard bet cap prevents catastrophic single-roll loss",
                "Three specialised modes cover streak, breakout, and base play",
                "Fully deterministic given roll history — reproducible in simulation",
            ],
            cons=[
                "Very high volatility — large swings are by design",
                "8–20 % per-roll sizing = rapid ruin possible on bad streaks",
                "Stop-loss at −35 % means significant drawdown before exit",
                "Not suitable for small bankrolls or risk-averse players",
                "Streak Harvester doubles bets — a single ladder loss hurts",
            ],
            best_use_case=(
                "Experts who accept large swings and want maximum bankroll growth "
                "speed within a single tightly controlled session."
            ),
            tips=[
                "Run in simulation first to observe mode transitions",
                "Do not increase max_ladder_depth beyond 3 — compounding risk is extreme",
                "Prefer 'normal' speed so you can watch mode transitions",
                "Treat each session as a self-contained unit — honour both stop conditions",
                "volatility_trigger=4 on a 10-roll window fires often; increase to 6 for calmer play",
                "The cold-range selector needs history — first ~20 bets use the neutral mid-window",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "range_size": {
                "type": "int",
                "default": 5000,
                "desc": (
                    "Number of slots in the bet window (0-9999 total). "
                    "5000 = ~50 % chance, payout ≈ ×1.98. Changing this alters win probability."
                ),
            },
            "base_bet_fraction": {
                "type": "float",
                "default": 0.08,
                "desc": "Base bet as fraction of bankroll (default 8 %)",
            },
            "max_bet_fraction": {
                "type": "float",
                "default": 0.20,
                "desc": "Hard safety cap on any single bet as fraction of bankroll (default 20 %)",
            },
            "multiplier": {
                "type": "float",
                "default": 2.0,
                "desc": "Step multiplier inside the Streak Harvester ladder",
            },
            "max_ladder_depth": {
                "type": "int",
                "default": 3,
                "desc": "Maximum Streak Harvester ladder steps before returning to Kelly Hybrid",
            },
            "stop_loss": {
                "type": "float",
                "default": 0.35,
                "desc": "Drawdown fraction that triggers session stop (0.35 = −35 %)",
            },
            "profit_target": {
                "type": "float",
                "default": 2.0,
                "desc": "Bankroll multiplier that triggers session stop (2.0 = ×2 start)",
            },
            "history_window": {
                "type": "int",
                "default": 10,
                "desc": "Number of recent rolls tracked for volatility detection",
            },
            "streak_trigger": {
                "type": "int",
                "default": 2,
                "desc": "Consecutive wins required to activate Streak Harvester",
            },
            "volatility_trigger": {
                "type": "int",
                "default": 4,
                "desc": "Win/loss imbalance in the history window to activate Volatility Breakout",
            },
            "min_bet": {
                "type": "str",
                "default": "0.000001",
                "desc": "Absolute minimum bet amount (floor)",
            },
        }

    # ------------------------------------------------------------------ #
    #  Construction                                                        #
    # ------------------------------------------------------------------ #

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.range_size         = max(1, min(9999, int(params.get("range_size", 5000))))
        self.base_bet_fraction  = float(params.get("base_bet_fraction", 0.08))
        self.max_bet_fraction   = float(params.get("max_bet_fraction", 0.20))
        self.multiplier         = float(params.get("multiplier", 2.0))
        self.max_ladder_depth   = max(1, int(params.get("max_ladder_depth", 3)))
        self.stop_loss          = float(params.get("stop_loss", 0.35))
        self.profit_target      = float(params.get("profit_target", 2.0))
        self.history_window     = max(1, int(params.get("history_window", 10)))
        self.streak_trigger     = max(1, int(params.get("streak_trigger", 2)))
        self.volatility_trigger = max(1, int(params.get("volatility_trigger", 4)))
        self.min_bet            = Decimal(str(params.get("min_bet", "0.000001")))

        # Runtime state — fully reset in on_session_start / initialize()
        self._start_bankroll: Decimal          = Decimal("0")
        self._bankroll:        Decimal          = Decimal("0")
        self._roll_history:    Deque[bool]      = deque(maxlen=self.history_window)
        self._win_streak:      int              = 0
        self._loss_streak:     int              = 0
        self._mode:            str              = _KELLY
        self._ladder_step:     int              = 0
        self._last_bet_amount: Decimal          = Decimal("0")
        self._total_bets:      int              = 0
        self._total_wins:      int              = 0
        self._should_stop:     bool             = False
        # Frequency histogram: number → times rolled (range dice 0-9999)
        self._number_freq:     Dict[int, int]   = {}
        # Cached coldest range; recomputed after each roll
        self._cold_range:      Tuple[int, int]  = self._default_range()

    # ------------------------------------------------------------------ #
    #  Session lifecycle                                                   #
    # ------------------------------------------------------------------ #

    def on_session_start(self) -> None:
        self._start_bankroll = self._resolve_starting_balance()
        self._bankroll       = self._start_bankroll
        self._roll_history   = deque(maxlen=self.history_window)
        self._win_streak     = 0
        self._loss_streak    = 0
        self._mode           = _KELLY
        self._ladder_step    = 0
        self._last_bet_amount = Decimal("0")
        self._total_bets     = 0
        self._total_wins     = 0
        self._should_stop    = False
        self._number_freq    = {}
        self._cold_range     = self._default_range()

        stop_floor  = self._start_bankroll * Decimal(str(1.0 - self.stop_loss))
        profit_ceil = self._start_bankroll * Decimal(str(self.profit_target))
        self.ctx.printer(
            f"[high-roller] session started | "
            f"bankroll={self._start_bankroll:.8f} | "
            f"stop≤{stop_floor:.8f} | target≥{profit_ceil:.8f} | "
            f"range_size={self.range_size} (Range Dice, is_in)"
        )

    def on_session_end(self, reason: str) -> None:
        win_rate = (self._total_wins / self._total_bets * 100) if self._total_bets else 0.0
        pnl      = self._bankroll - self._start_bankroll
        pnl_pct  = float(pnl / self._start_bankroll * 100) if self._start_bankroll else 0.0
        self.ctx.printer(
            f"[high-roller] ended({reason}) | "
            f"bets={self._total_bets} wins={self._total_wins} ({win_rate:.1f}%) | "
            f"start={self._start_bankroll:.8f} end={self._bankroll:.8f} "
            f"PnL={pnl:+.8f} ({pnl_pct:+.2f}%)"
        )

    # ------------------------------------------------------------------ #
    #  Bet-size calculators                                               #
    # ------------------------------------------------------------------ #

    def calculate_kelly_bet(self) -> Decimal:
        """
        Kelly Hybrid ladder — scaled by consecutive win streak:
          streak 0–1 → 8 %   streak 2 → 12 %   streak 3+ → 18 %
        """
        bankroll = self._safe_bankroll()
        idx  = min(self._win_streak, len(_KELLY_LADDER) - 1)
        frac = _KELLY_LADDER[idx]
        return self._cap_bet(bankroll * frac)

    def calculate_streak_harvester_bet(self) -> Decimal:
        """
        Streak Harvester exponential ladder (up to max_ladder_depth steps):
          step 0 = base_bet_fraction
          step n = step 0 × multiplier^n
        All steps are capped at max_bet_fraction.
        """
        bankroll = self._safe_bankroll()
        step     = min(self._ladder_step, self.max_ladder_depth - 1)
        base     = bankroll * Decimal(str(self.base_bet_fraction))
        amount   = base * (Decimal(str(self.multiplier)) ** step)
        return self._cap_bet(amount)

    def calculate_breakout_bet(self) -> Decimal:
        """
        Volatility Breakout fixed-tier ladder:
          step 0 = 10 %   step 1 = 15 %   step 2 = 22 % (capped to max_bet_fraction)
        """
        bankroll = self._safe_bankroll()
        step     = min(self._ladder_step, len(_BREAKOUT_LADDER) - 1)
        return self._cap_bet(bankroll * _BREAKOUT_LADDER[step])

    # ------------------------------------------------------------------ #
    #  Mode evaluation and transitions                                    #
    # ------------------------------------------------------------------ #

    def _check_volatility(self) -> bool:
        """True when the history window is full and win/loss imbalance exceeds threshold."""
        if len(self._roll_history) < self.history_window:
            return False
        wins   = sum(1 for r in self._roll_history if r)
        losses = len(self._roll_history) - wins
        return abs(wins - losses) >= self.volatility_trigger

    def update_mode(self, last_win: bool) -> None:
        """
        Evaluate mode transitions after every roll result.
        Priority order: Streak Harvester > Volatility Breakout > Kelly Hybrid.

        Kelly Hybrid  → Streak Harvester : win_streak >= streak_trigger
        Kelly Hybrid  → Volatility Breakout : volatility condition met
        Streak Harvester → Kelly Hybrid  : loss, or ladder exhausted
        Volatility Breakout → Kelly Hybrid : loss, or ladder exhausted
        """
        if self._mode == _KELLY:
            if self._win_streak >= self.streak_trigger:
                self._mode        = _HARVEST
                self._ladder_step = 0
                self.ctx.printer(
                    f"[high-roller] ▶ STREAK HARVESTER "
                    f"(streak={self._win_streak}, trigger={self.streak_trigger})"
                )
            elif self._check_volatility():
                wins   = sum(1 for r in self._roll_history if r)
                losses = len(self._roll_history) - wins
                self._mode        = _BREAKOUT
                self._ladder_step = 0
                self.ctx.printer(
                    f"[high-roller] ▶ VOLATILITY BREAKOUT "
                    f"(wins={wins} losses={losses} imbalance={abs(wins-losses)}, "
                    f"trigger={self.volatility_trigger})"
                )

        elif self._mode == _HARVEST:
            if last_win:
                next_step = self._ladder_step + 1
                if next_step >= self.max_ladder_depth:
                    self._mode        = _KELLY
                    self._ladder_step = 0
                    self.ctx.printer(
                        f"[high-roller] ✓ harvest ladder complete → KELLY HYBRID"
                    )
                else:
                    self._ladder_step = next_step
                    self.ctx.printer(
                        f"[high-roller] harvest step {self._ladder_step + 1}/{self.max_ladder_depth}"
                    )
            else:
                self._mode        = _KELLY
                self._ladder_step = 0
                self.ctx.printer("[high-roller] ✗ harvest loss → KELLY HYBRID")

        elif self._mode == _BREAKOUT:
            if last_win:
                next_step = self._ladder_step + 1
                if next_step >= len(_BREAKOUT_LADDER):
                    self._mode        = _KELLY
                    self._ladder_step = 0
                    self.ctx.printer(
                        "[high-roller] ✓ breakout ladder complete → KELLY HYBRID"
                    )
                else:
                    self._ladder_step = next_step
                    self.ctx.printer(
                        f"[high-roller] breakout step {self._ladder_step + 1}/{len(_BREAKOUT_LADDER)}"
                    )
            else:
                self._mode        = _KELLY
                self._ladder_step = 0
                self.ctx.printer("[high-roller] ✗ breakout loss → KELLY HYBRID")

    # ------------------------------------------------------------------ #
    #  Bankroll protection                                                #
    # ------------------------------------------------------------------ #

    def apply_bankroll_protection(self) -> bool:
        """
        Check stop-loss and profit-target conditions.
        Returns True when the session must stop.
        """
        if self._start_bankroll <= 0:
            return False

        stop_floor  = self._start_bankroll * Decimal(str(1.0 - self.stop_loss))
        profit_ceil = self._start_bankroll * Decimal(str(self.profit_target))

        if self._bankroll <= stop_floor:
            self.ctx.printer(
                f"[high-roller] ⛔ STOP-LOSS: "
                f"{self._bankroll:.8f} ≤ {stop_floor:.8f} "
                f"(−{self.stop_loss * 100:.0f} % of start)"
            )
            return True

        if self._bankroll >= profit_ceil:
            self.ctx.printer(
                f"[high-roller] 🎯 PROFIT TARGET: "
                f"{self._bankroll:.8f} ≥ {profit_ceil:.8f} "
                f"(×{self.profit_target} of start)"
            )
            return True

        return False

    def should_stop(self) -> bool:
        """Return True when a protection rule has fired."""
        return self._should_stop

    # ------------------------------------------------------------------ #
    #  Core protocol — called by the engine                              #
    # ------------------------------------------------------------------ #

    def next_bet(self) -> Optional[BetSpec]:
        """Calculate and return the next bet, or None to end the session."""
        if self._should_stop:
            return None

        if self._mode == _KELLY:
            amount = self.calculate_kelly_bet()
        elif self._mode == _HARVEST:
            amount = self.calculate_streak_harvester_bet()
        else:
            amount = self.calculate_breakout_bet()

        self._last_bet_amount = amount
        rng_lo, rng_hi        = self._cold_range

        self.ctx.printer(
            f"[high-roller] {self._mode} | "
            f"step={self._ladder_step} streak={self._win_streak} | "
            f"bet={amount:.8f} bankroll={self._bankroll:.8f} | "
            f"range=[{rng_lo},{rng_hi}]"
        )

        return {
            "game":    "range-dice",
            "amount":  format(amount, "f"),
            "range":   (rng_lo, rng_hi),
            "is_in":   True,
            "faucet":  self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        """Update all internal state after a bet result."""
        won = bool(result.get("win", False))
        self._total_bets += 1
        if won:
            self._total_wins += 1

        # Update bankroll from API-reported balance (most authoritative)
        raw_bal = result.get("balance")
        if raw_bal is not None:
            try:
                self._bankroll = Decimal(str(raw_bal))
            except Exception:
                pass

        # Track rolled number for frequency histogram
        num = result.get("number")
        if num is not None:
            try:
                n = int(num)
                if 0 <= n <= 9999:
                    self._number_freq[n] = self._number_freq.get(n, 0) + 1
            except (ValueError, TypeError):
                pass

        # Recompute coldest range after each roll
        self._cold_range = self._find_coldest_range()

        # Update streak counters
        if won:
            self._win_streak  += 1
            self._loss_streak  = 0
        else:
            self._win_streak   = 0
            self._loss_streak += 1

        # Append to rolling window BEFORE mode evaluation so volatility
        # check sees the current roll
        self._roll_history.append(won)

        # Evaluate mode transitions
        self.update_mode(won)

        # Check protection rules — may set _should_stop
        self._should_stop = self.apply_bankroll_protection()

        self.ctx.recent_results.append(result)

    # ------------------------------------------------------------------ #
    #  Convenience API for external / testing callers                    #
    # ------------------------------------------------------------------ #

    def initialize(self, start_bankroll: float) -> None:
        """
        Programmatic initialisation without a StrategyContext session start.
        Useful for unit tests and Monte Carlo callers.
        """
        self._start_bankroll  = Decimal(str(start_bankroll))
        self._bankroll        = self._start_bankroll
        self._roll_history    = deque(maxlen=self.history_window)
        self._win_streak      = 0
        self._loss_streak     = 0
        self._mode            = _KELLY
        self._ladder_step     = 0
        self._last_bet_amount = Decimal("0")
        self._total_bets      = 0
        self._total_wins      = 0
        self._should_stop     = False
        self._number_freq     = {}
        self._cold_range      = self._default_range()

    def on_roll_result(self, win: bool, number: Optional[int] = None) -> None:
        """
        Lightweight wrapper around on_bet_result for callers that don't have
        a full BetResult dict.  Infers balance from the last bet amount.
        Optionally accepts the rolled number (0-9999) for frequency tracking.
        """
        bet = self._last_bet_amount or self.min_bet
        # Approximate payout for range-dice at range_size slots
        if win:
            p = self.range_size / 10000.0
            payout_mult = Decimal(str(0.99 / p if p > 0 else 2.0))
            profit = bet * (payout_mult - Decimal("1"))
        else:
            profit = -bet
        new_balance = self._bankroll + profit
        result: dict = {"win": win, "balance": str(new_balance)}
        if number is not None:
            result["number"] = number
        self.on_bet_result(result)

    def get_next_bet(self) -> float:
        """
        Return the next bet amount as a plain float.
        Returns 0.0 when the session should stop.
        """
        spec = self.next_bet()
        return float(spec["amount"]) if spec else 0.0

    # ------------------------------------------------------------------ #
    #  Private helpers                                                    #
    # ------------------------------------------------------------------ #

    def _resolve_starting_balance(self) -> Decimal:
        """Determine starting balance from context, falling back gracefully."""
        try:
            bal = Decimal(str(self.ctx.starting_balance or "0"))
            if bal > 0:
                return bal
        except Exception:
            pass
        # Try the latest known balance from a resumed session
        try:
            bal = Decimal(self.ctx.current_balance_str())
            if bal > 0:
                return bal
        except Exception:
            pass
        return self.min_bet * Decimal("1000")

    def _safe_bankroll(self) -> Decimal:
        """Return current bankroll, guarding against zero."""
        return self._bankroll if self._bankroll > 0 else (
            self._start_bankroll if self._start_bankroll > 0 else self.min_bet
        )

    def _cap_bet(self, amount: Decimal) -> Decimal:
        """Apply max_bet_fraction cap and min_bet floor."""
        cap = self._safe_bankroll() * Decimal(str(self.max_bet_fraction))
        return max(min(amount, cap), self.min_bet)

    def _default_range(self) -> Tuple[int, int]:
        """Return the neutral mid-window used before any history is available."""
        lo = (10000 - self.range_size) // 2
        return (lo, lo + self.range_size - 1)

    def _find_coldest_range(self) -> Tuple[int, int]:
        """
        Sliding-window O(N) search over 0-9999 for the contiguous block of
        `range_size` slots with the fewest total hits in the session history.

        Returns (lo, hi) inclusive.  Falls back to the neutral mid-window
        when no history has been recorded yet.
        """
        if not self._number_freq:
            return self._default_range()

        N    = 10000
        size = self.range_size

        # Build full frequency array (only hits stored in sparse dict)
        freq = [self._number_freq.get(i, 0) for i in range(N)]

        # Initialise window sum for [0, size-1]
        window_sum = sum(freq[:size])
        min_sum    = window_sum
        min_start  = 0

        for i in range(1, N - size + 1):
            window_sum += freq[i + size - 1] - freq[i - 1]
            if window_sum < min_sum:
                min_sum   = window_sum
                min_start = i

        return (min_start, min_start + size - 1)
