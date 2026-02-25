from __future__ import annotations
"""
Cold-Chaos-50 Strategy

50% chance Range Dice that hunts the COLDEST half of the number space.

Core mechanics
--------------
* Builds a slot-frequency map from full bet DB history for this symbol.
* Finds the contiguous 5 000-slot window (of the 5 001 possible) whose
  sum of appearances is LOWEST — the coldest half.
* Picks randomly from the top-N coldest windows, weighted by coldness.
* Bet sizing is CHAOTIC: moves in discrete 25% steps up or down based on
  win/loss streaks, with a configurable random chance of doing something
  unexpected (jumping extra far, reversing direction, or fully random).
* Balance pressure and streak direction are the "logic"; chaos is the noise.

Bet level
---------
  amount = balance × base_bet_pct × (1 + level × 0.25)

  level 0  → 1.00× base   (e.g. 0.50% of balance)
  level 4  → 2.00× base   (e.g. 1.00%)
  level 8  → 3.00× base   (e.g. 1.50%)
  level 16 → 5.00× base   (e.g. 2.50%)

Level is clamped between min_level and max_level every step.

Range Dice domain: 0 – 9999 (10 000 slots)
  window width = 5 000  →  chance = 50.00%  →  payout ≈ 1.98×
"""
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Tuple

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_DOMAIN = 10_000
_WIDTH  = 5_000     # 50% chance


# ── Cold range finder ──────────────────────────────────────────────────────────

class _RangeFreqMap:
    """Builds a slot-frequency array and finds coldest 5 000-slot windows."""

    def __init__(self, history_limit: int) -> None:
        self.history_limit = history_limit
        self.counts: List[int] = [0] * _DOMAIN
        self.total:  int       = 0

    # ---- loading -------------------------------------------------------

    def load(self, symbol: str) -> int:
        try:
            from betbot_engine.bet_database import BetDatabase
            rolls = BetDatabase().get_recent_rolls(symbol=symbol, limit=self.history_limit)
            c = [0] * _DOMAIN
            for r in rolls:
                c[min(int(r), _DOMAIN - 1)] += 1
            self.counts = c
            self.total  = len(rolls)
            return self.total
        except Exception:
            return 0

    def record(self, slot: int) -> None:
        self.counts[min(max(slot, 0), _DOMAIN - 1)] += 1
        self.total += 1

    # ---- sliding window sum -------------------------------------------

    def coldest_windows(self, n: int) -> List[Tuple[int, int]]:
        """Return up to n (sum, start) pairs, coldest first.

        Uses prefix-sum for O(domain) computation.
        Falls back to random windows when history is empty.
        """
        if self.total == 0:
            starts = list(range(0, _DOMAIN - _WIDTH + 1, 10))  # every 10th
            import random
            random.shuffle(starts)
            return [(0, s) for s in starts[:n]]

        # prefix sums
        p = [0] * (_DOMAIN + 1)
        for i, c in enumerate(self.counts):
            p[i + 1] = p[i] + c

        windows = []
        for s in range(_DOMAIN - _WIDTH + 1):
            windows.append((p[s + _WIDTH] - p[s], s))
        windows.sort(key=lambda x: x[0])
        return windows[:n]


# ── Bet level stepper ──────────────────────────────────────────────────────────

class _LevelStepper:
    """Manages discrete bet level with chaotic stepping logic.

    Levels map linearly: amount_multiplier = 1.0 + level × 0.25
    Steps are always multiples of 1 (= 25% of base).
    """

    def __init__(self, min_lvl: int, max_lvl: int,
                 chaos_pct: float, streak_threshold: int) -> None:
        self.min_lvl         = min_lvl
        self.max_lvl         = max_lvl
        self.chaos_pct       = chaos_pct
        self.streak_threshold = streak_threshold
        self.level = 0
        self.win_streak  = 0
        self.loss_streak = 0

    def multiplier(self) -> float:
        return 1.0 + self.level * 0.25

    def step(self, won: bool, rng: Any) -> str:
        """Update level after a bet result.  Returns a short description."""
        # ----- determine base delta based on outcome -----
        if won:
            self.win_streak  += 1
            self.loss_streak  = 0
            base_delta = rng.choice([1, 2, 3])            # go UP after win
            streak_bonus = 1 if self.win_streak >= self.streak_threshold else 0
            base_delta += streak_bonus
        else:
            self.loss_streak += 1
            self.win_streak   = 0
            base_delta = -rng.choice([1, 2, 3])           # go DOWN after loss
            streak_extra = -1 if self.loss_streak >= self.streak_threshold else 0
            base_delta += streak_extra

        action = "win↑" if base_delta > 0 else "loss↓"

        # ----- chaos roll -----
        chaos = rng.random() < self.chaos_pct
        if chaos:
            r = rng.random()
            if r < 0.40:
                # reverse direction: bold move against the trend
                base_delta = -base_delta
                action = "🎲 reverse"
            elif r < 0.70:
                # amplify: jump twice as far (extra volatile)
                base_delta = base_delta * 2
                action = "🎲 amplify"
            else:
                # fully random: pick any level (maximum chaos)
                self.level = rng.randint(self.min_lvl, self.max_lvl)
                return "🎲 random-jump"

        old = self.level
        self.level = max(self.min_lvl, min(self.max_lvl, self.level + base_delta))
        return f"{action} {old}→{self.level} (Δ{base_delta:+d})"


# ── Strategy ───────────────────────────────────────────────────────────────────

@register("cold-chaos-50")
class ColdChaos50:
    """Chaotic 50%-chance Range Dice on the coldest half of slot history."""

    @classmethod
    def name(cls) -> str:
        return "cold-chaos-50"

    @classmethod
    def describe(cls) -> str:
        return (
            "50% chance Range Dice always targeting the coldest 5 000-slot window "
            "in your bet history. Bet size moves in 25% steps, driven by win/loss "
            "streaks — but with a random chaos factor that can reverse direction, "
            "amplify jumps, or teleport to a random level."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Medium",
            volatility="Very High",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "50% win rate — frequent feedback to react to",
                "Cold-window selection targets underrepresented ranges",
                "Non-smooth 25%-step sizing creates genuine swings",
                "Win streaks rapidly escalate exposure",
                "Chaos element prevents mechanical exploitation",
            ],
            cons=[
                "House edge applies regardless of cold-window selection",
                "Chaos can amplify losses unpredictably",
                "Requires history for meaningful cold map",
                "Max-level bets during loss streaks drain bankroll fast",
                "Fully random level jump can be badly timed",
            ],
            best_use_case=(
                "High-action 50/50 sessions where you want swinging bet sizes "
                "without strict Martingale math — pure controlled chaos."
            ),
            tips=[
                "Set max_level low (8-12) for safer sessions",
                "chaos_pct=0.10 is moderate; 0.25+ is wild",
                "streak_threshold=3 reacts faster than 5",
                "More DB history = better cold window targeting",
                "Watch the level log — amps and reverses are the fun part",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_pct": {
                "type": "float", "default": 0.02,
                "desc": "Bet fraction of balance at level 0 (0.02 = 2%)",
            },
            "min_level": {
                "type": "int", "default": 0,
                "desc": "Minimum bet level (level 0 = 1.00× base)",
            },
            "max_level": {
                "type": "int", "default": 12,
                "desc": "Maximum bet level (level 12 = 4.00× base)",
            },
            "start_level": {
                "type": "int", "default": 4,
                "desc": "Starting bet level",
            },
            "chaos_pct": {
                "type": "float", "default": 0.15,
                "desc": "Probability of chaotic level step (0.15 = 15% of bets)",
            },
            "streak_threshold": {
                "type": "int", "default": 4,
                "desc": "Win/loss streak length triggering an extra ±1 level step",
            },
            "cold_windows_n": {
                "type": "int", "default": 15,
                "desc": "Pick randomly from the top-N coldest windows (1 = always coldest)",
            },
            "history_limit": {
                "type": "int", "default": 150_000,
                "desc": "Max historical rolls loaded from DB for cold-map computation",
            },
            "refresh_every": {
                "type": "int", "default": 100,
                "desc": "Re-compute cold map from DB every N bets",
            },
            "profit_target_pct": {
                "type": "float", "default": 0.0,
                "desc": "Auto-stop when profit ≥ this % of starting balance (0 = off)",
            },
            "stop_loss_pct": {
                "type": "float", "default": 0.0,
                "desc": "Auto-stop when loss ≥ this % of starting balance (0 = off)",
            },
        }

    # ──────────────────────────────────────────────────────────────── init

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.base_bet_pct   = float(params.get("base_bet_pct",   0.02))
        min_lvl             = int(params.get("min_level",         0))
        max_lvl             = int(params.get("max_level",         12))
        start_lvl           = int(params.get("start_level",       4))
        chaos_pct           = float(params.get("chaos_pct",       0.15))
        streak_thr          = int(params.get("streak_threshold",  4))
        self.cold_windows_n = max(1, int(params.get("cold_windows_n", 15)))
        self.history_limit  = int(params.get("history_limit",    150_000))
        self.refresh_every  = max(1, int(params.get("refresh_every",   100)))
        self.profit_target  = float(params.get("profit_target_pct", 0.0))
        self.stop_loss      = float(params.get("stop_loss_pct",      0.0))

        self._stepper = _LevelStepper(min_lvl, max_lvl, chaos_pct, streak_thr)
        self._stepper.level = max(min_lvl, min(max_lvl, start_lvl))

        self._freq          = _RangeFreqMap(self.history_limit)
        self._starting_bal: Decimal = Decimal("0")
        self._live_bal:     Decimal = Decimal("0")
        self._target_bal:   Decimal = Decimal("0")
        self._floor_bal:    Decimal = Decimal("0")
        self._bets:         int     = 0
        self._wins:         int     = 0
        self._losses:       int     = 0
        self._biggest_win:  Decimal = Decimal("0")

    # ──────────────────────────────────────────────────────── session hooks

    def on_session_start(self) -> None:
        bal = _dec(self.ctx.starting_balance or "0")
        self._starting_bal = bal
        self._live_bal     = bal

        if self.profit_target > 0:
            self._target_bal = bal * Decimal(str(1 + self.profit_target / 100))
        else:
            self._target_bal = Decimal("0")

        if self.stop_loss > 0:
            self._floor_bal = bal * Decimal(str(1 - self.stop_loss / 100))
        else:
            self._floor_bal = Decimal("0")

        loaded = self._freq.load(self.ctx.symbol)
        lvl    = self._stepper.level
        mult   = self._stepper.multiplier()
        self.ctx.printer(
            f"[cold-chaos-50] started | balance={bal} | "
            f"history={loaded:,} bets | cold_windows={self.cold_windows_n} | "
            f"level={lvl} ({mult:.2f}× base={self.base_bet_pct*100:.2f}%) | "
            f"chaos={self._stepper.chaos_pct*100:.0f}%"
            + (f" | target=+{self.profit_target:.0f}%" if self._target_bal else "")
            + (f" | stop_loss=-{self.stop_loss:.0f}%" if self._floor_bal else "")
        )

    def on_session_end(self, reason: str) -> None:
        start = self._starting_bal
        final = self._live_bal
        pnl   = final - start
        pct   = float(pnl / start * 100) if start else 0.0
        sign  = "+" if pnl >= 0 else ""
        wr    = self._wins / max(1, self._bets) * 100
        self.ctx.printer(
            f"[cold-chaos-50] session ended ({reason}) | "
            f"bets={self._bets} W={self._wins} L={self._losses} "
            f"WR={wr:.1f}% | PnL={sign}{pnl:.8f} ({sign}{pct:.2f}%) | "
            f"biggest_win={self._biggest_win:.8f} | "
            f"final_level={self._stepper.level}"
        )

    # ─────────────────────────────────────────────────────────── next bet

    def next_bet(self) -> Optional[BetSpec]:
        bal = self._live_bal

        # Profit target / stop-loss
        if self._target_bal > 0 and bal >= self._target_bal:
            self.ctx.printer(f"[cold-chaos-50] 🎯 profit target reached → stopping")
            return None
        if self._floor_bal > 0 and bal <= self._floor_bal:
            self.ctx.printer(f"[cold-chaos-50] 🛑 stop-loss hit → stopping")
            return None
        if bal <= 0:
            return None

        # Periodic refresh
        if self._bets > 0 and self._bets % self.refresh_every == 0:
            n = self._freq.load(self.ctx.symbol)
            self.ctx.printer(
                f"[cold-chaos-50] ↻ cold map refreshed ({n:,} bets) | "
                f"level={self._stepper.level} ({self._stepper.multiplier():.2f}×) | "
                f"W{self._stepper.win_streak}/L{self._stepper.loss_streak}"
            )

        # Pick coldest window
        windows = self._freq.coldest_windows(self.cold_windows_n)
        start   = self._pick_window(windows)

        # Calculate bet amount
        amt = self._calc_amt(bal)
        if amt <= 0:
            return None

        return {
            "game":   "range-dice",
            "amount": format(amt, "f"),
            "range":  (start, start + _WIDTH - 1),
            "is_in":  True,
            "faucet": self.ctx.faucet,
        }

    # ──────────────────────────────────────────────────────────── result

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)
        self._bets += 1

        try:
            self._live_bal = Decimal(str(result.get("balance", self._live_bal)))
        except Exception:
            pass

        # Record roll in live freq map
        roll_raw = result.get("number")
        if roll_raw is not None:
            try:
                self._freq.record(int(float(roll_raw)))
            except Exception:
                pass

        won = bool(result.get("win"))
        if won:
            self._wins += 1
            try:
                profit = Decimal(str(result.get("profit", "0")))
                if profit > self._biggest_win:
                    self._biggest_win = profit
            except Exception:
                pass
        else:
            self._losses += 1

        # Step the bet level (chaotic)
        desc = self._stepper.step(won, self.ctx.rng)
        self.ctx.printer(
            f"[cold-chaos-50] {'✅ WIN ' if won else '❌ loss'} "
            f"| step: {desc} | "
            f"level={self._stepper.level} ({self._stepper.multiplier():.2f}×) | "
            f"W{self._stepper.win_streak}/L{self._stepper.loss_streak}"
        )

    # ──────────────────────────────────────────────────────────── helpers

    def _pick_window(self, windows: List[Tuple[int, int]]) -> int:
        """Pick a window from the coldest candidates, weighted by coldness."""
        if not windows:
            return self.ctx.rng.randint(0, _DOMAIN - _WIDTH)

        if len(windows) == 1:
            return windows[0][1]

        # Inverse-frequency weighting (lower sum → higher weight)
        # Use max_sum - sum so colder windows get bigger weight
        sums = [w[0] for w in windows]
        max_s = max(sums) + 1
        weights = [max_s - s for s in sums]
        total = sum(weights)
        weights = [w / total for w in weights]

        chosen = self.ctx.rng.choices(windows, weights=weights, k=1)[0]
        return chosen[1]

    def _calc_amt(self, bal: Decimal) -> Decimal:
        mult = Decimal(str(self._stepper.multiplier()))
        amt  = bal * Decimal(str(self.base_bet_pct)) * mult
        return amt.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


# ── helpers ────────────────────────────────────────────────────────────────────

def _dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")
