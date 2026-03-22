"""Gambler Execution Agent — adaptive strategy selection and risk management.

Responsibilities:
- Select the best strategy from analyst rankings
- Monitor live performance and adapt
- Switch strategies when conditions deteriorate
- Enforce independent risk management (stop-loss, take-profit)
- Log session results for feedback to the analyst
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GamblerAgent:
    """Adaptive execution agent that selects and switches strategies at runtime."""

    def __init__(
        self,
        rankings: Optional[List[Any]] = None,
        session_budget: Optional[float] = None,
        stop_loss_pct: float = -0.35,
        take_profit_pct: float = 2.0,
        max_bets: Optional[int] = None,
        switch_cooldown: int = 50,
        data_dir: str = "data/agents",
    ) -> None:
        self._rankings = rankings or []
        self._session_budget = session_budget
        self._stop_loss_pct = stop_loss_pct
        self._take_profit_pct = take_profit_pct
        self._max_bets = max_bets
        self._switch_cooldown = switch_cooldown
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        # Session state
        self._session_active = False
        self._starting_balance: float = 0.0
        self._current_balance: float = 0.0
        self._peak_balance: float = 0.0
        self._bets_placed: int = 0
        self._wins: int = 0
        self._losses: int = 0
        self._current_win_streak: int = 0
        self._current_loss_streak: int = 0
        self._max_loss_streak: int = 0
        self._max_win_streak: int = 0
        self._total_wagered: float = 0.0
        self._recent_outcomes: Deque[bool] = deque(maxlen=50)
        self._current_strategy: Optional[str] = None
        self._bets_since_switch: int = 0

    # ------------------------------------------------------------------
    # Strategy selection
    # ------------------------------------------------------------------

    def select_strategy(
        self,
        rankings: List[Any],
        mode: str = "balanced",
    ) -> str:
        """Pick the best strategy name from rankings based on *mode*.

        Modes:
          - ``conservative``: highest survival_rate with risk_of_ruin < 0.3
          - ``balanced``: highest composite_score
          - ``aggressive``: highest avg_roi
          - ``wager_farming``: highest avg_total_wagered
        """
        if not rankings:
            raise ValueError("No rankings available to select a strategy")

        if mode == "conservative":
            candidates = [r for r in rankings if r.risk_of_ruin < 0.3]
            if not candidates:
                candidates = rankings
            best = max(candidates, key=lambda r: r.survival_rate)
        elif mode == "aggressive":
            best = max(rankings, key=lambda r: r.avg_roi)
        elif mode == "wager_farming":
            best = max(rankings, key=lambda r: r.avg_total_wagered)
        else:
            best = max(rankings, key=lambda r: r.composite_score)

        logger.info(
            "Selected strategy %s (mode=%s, score=%.4f)",
            best.strategy_name,
            mode,
            best.composite_score,
        )
        return best.strategy_name

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self, starting_balance: float) -> None:
        """Reset all session tracking for a new run."""
        self._session_active = True
        self._starting_balance = starting_balance
        self._current_balance = starting_balance
        self._peak_balance = starting_balance
        self._bets_placed = 0
        self._wins = 0
        self._losses = 0
        self._current_win_streak = 0
        self._current_loss_streak = 0
        self._max_loss_streak = 0
        self._max_win_streak = 0
        self._total_wagered = 0.0
        self._recent_outcomes.clear()
        self._bets_since_switch = 0
        logger.info("Session started with balance %.8f", starting_balance)

    def should_stop(self) -> Tuple[bool, str]:
        """Check session stop conditions.

        Returns:
            ``(should_stop, reason)``
        """
        if not self._session_active:
            return True, "session_not_active"

        if self._starting_balance <= 0:
            return True, "zero_starting_balance"

        pnl_pct = (self._current_balance - self._starting_balance) / self._starting_balance

        if pnl_pct <= self._stop_loss_pct:
            return True, f"stop_loss ({pnl_pct:+.2%} <= {self._stop_loss_pct:+.2%})"

        if pnl_pct >= self._take_profit_pct:
            return True, f"take_profit ({pnl_pct:+.2%} >= {self._take_profit_pct:+.2%})"

        if self._max_bets is not None and self._bets_placed >= self._max_bets:
            return True, f"max_bets ({self._bets_placed})"

        if self._session_budget is not None:
            if self._total_wagered >= self._session_budget:
                return True, f"budget_exhausted ({self._total_wagered:.8f})"

        if self._current_balance <= 0:
            return True, "bankrupt"

        return False, ""

    # ------------------------------------------------------------------
    # Bet result processing
    # ------------------------------------------------------------------

    def on_bet_result(self, result: dict) -> None:
        """Update session tracking from a bet result."""
        win = bool(result.get("win", False))

        try:
            profit = float(result.get("profit", "0"))
        except (ValueError, TypeError):
            profit = 0.0

        try:
            balance = float(result.get("balance", "0"))
        except (ValueError, TypeError):
            balance = self._current_balance + profit

        self._current_balance = balance
        if balance > self._peak_balance:
            self._peak_balance = balance

        self._bets_placed += 1
        self._bets_since_switch += 1
        self._total_wagered += abs(profit) if not win else 0.0
        # Approximate wager from profit when win: profit = amount * (payout - 1)
        # Better: track bet amount directly if available
        if "amount" in result:
            try:
                self._total_wagered += float(result["amount"])
            except (ValueError, TypeError):
                pass

        self._recent_outcomes.append(win)

        if win:
            self._wins += 1
            self._current_win_streak += 1
            self._current_loss_streak = 0
            self._max_win_streak = max(self._max_win_streak, self._current_win_streak)
        else:
            self._losses += 1
            self._current_loss_streak += 1
            self._current_win_streak = 0
            self._max_loss_streak = max(self._max_loss_streak, self._current_loss_streak)

    # ------------------------------------------------------------------
    # Strategy switching
    # ------------------------------------------------------------------

    def should_switch_strategy(self) -> Tuple[bool, str]:
        """Detect whether the current strategy should be switched.

        Returns:
            ``(should_switch, reason)``
        """
        if self._bets_since_switch < self._switch_cooldown:
            return False, ""

        if self._current_loss_streak >= 8:
            return True, "loss_streak"

        if self._peak_balance > 0:
            drawdown = (self._peak_balance - self._current_balance) / self._peak_balance
            if drawdown > 0.25:
                return True, "drawdown"

        if len(self._recent_outcomes) >= 50:
            recent_wins = sum(1 for o in self._recent_outcomes if o)
            win_rate = recent_wins / len(self._recent_outcomes)
            if win_rate < 0.35:
                return True, "poor_win_rate"

        return False, ""

    def pick_fallback_strategy(
        self,
        current_name: str,
        rankings: List[Any],
    ) -> Optional[str]:
        """Pick the next best strategy from rankings, excluding current.

        Prefers higher survival_rate when switching due to losses.
        """
        candidates = [r for r in rankings if r.strategy_name != current_name]
        if not candidates:
            return None

        # Prefer survival when we're switching (defensive)
        best = max(candidates, key=lambda r: (r.survival_rate * 0.6 + r.composite_score * 0.4))
        logger.info(
            "Fallback strategy: %s (survival=%.2f%%, score=%.4f)",
            best.strategy_name,
            best.survival_rate * 100,
            best.composite_score,
        )
        self._bets_since_switch = 0
        self._current_strategy = best.strategy_name
        return best.strategy_name

    # ------------------------------------------------------------------
    # Stats / reporting
    # ------------------------------------------------------------------

    def get_session_stats(self) -> dict:
        """Return current session statistics."""
        total = self._wins + self._losses
        win_rate = (self._wins / total * 100) if total > 0 else 0.0

        drawdown_pct = 0.0
        if self._peak_balance > 0:
            drawdown_pct = (self._peak_balance - self._current_balance) / self._peak_balance * 100

        return {
            "wins": self._wins,
            "losses": self._losses,
            "win_rate": round(win_rate, 2),
            "current_balance": self._current_balance,
            "starting_balance": self._starting_balance,
            "peak_balance": self._peak_balance,
            "drawdown_pct": round(drawdown_pct, 2),
            "total_wagered": self._total_wagered,
            "current_win_streak": self._current_win_streak,
            "current_loss_streak": self._current_loss_streak,
            "max_win_streak": self._max_win_streak,
            "max_loss_streak": self._max_loss_streak,
            "bets_placed": self._bets_placed,
            "current_strategy": self._current_strategy,
            "pnl": self._current_balance - self._starting_balance,
            "pnl_pct": (
                (self._current_balance - self._starting_balance) / self._starting_balance * 100
                if self._starting_balance > 0
                else 0.0
            ),
        }

    # ------------------------------------------------------------------
    # Session logging
    # ------------------------------------------------------------------

    def log_session(self, strategy_name: str, result_summary: dict) -> None:
        """Append session result to persistent log."""
        path = os.path.join(self._data_dir, "session_logs.json")

        entries = self._load_json_list(path)
        entry = dict(result_summary)
        entry["strategy_name"] = strategy_name
        entry["timestamp"] = time.time()
        entries.append(entry)

        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(entries, fh, indent=2)
        except OSError:
            logger.exception("Failed to save session log")

    def get_session_history(self) -> List[dict]:
        """Load all session logs."""
        path = os.path.join(self._data_dir, "session_logs.json")
        return self._load_json_list(path)

    @staticmethod
    def _load_json_list(path: str) -> List[dict]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []
