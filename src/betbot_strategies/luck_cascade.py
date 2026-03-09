from __future__ import annotations
"""
Luck Cascade — Profit-Funded Tier Descent

Hunts a base low-chance window. As long as session luck% > 100 (actual wins
outpace statistical expectation), accumulated profit is used to hunt
increasingly lower chances in discrete steps.

Luck% = actual_wins / expected_wins x 100
  where expected_wins accumulates as sum(chance_i / 100) over every bet placed.

Tier rule (evaluated before every bet):
  luck% > 100  ->  deepest affordable tier (funded by profit only)
  luck% <= 100 ->  tier 0 (base, funded by balance fraction)

Tiers are fixed discrete steps — no gradual drift:
  Tier 0:  5.00%   ~19x   <- funded by balance fraction
  Tier 1:  1.00%   ~99x   |
  Tier 2:  0.20%  ~499x   |  funded by session profit only
  Tier 3:  0.04% ~2499x   |
  Tier 4:  0.01% ~9999x   |

Base capital is never risked on deeper tiers — only house money.
If profit runs dry the strategy falls back to tier 0 automatically.
"""
import json
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_SATOSHI = Decimal("0.00000001")
_DEFAULT_TIERS: List[float] = [5.0, 1.0, 0.2, 0.04, 0.01]


@register("luck-cascade")
class LuckCascade:
    """Hunt low-chance tiers with profits while luck% > 100%."""

    @classmethod
    def name(cls) -> str:
        return "luck-cascade"

    @classmethod
    def describe(cls) -> str:
        return (
            "Descend into lower-chance tiers while session luck% > 100%. "
            "Deeper tiers spend profit only — base capital stays safe at tier 0."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Medium",
            volatility="Very High",
            time_to_profit="Slow",
            recommended_for="Advanced",
            pros=[
                "Base capital protected: deeper tiers funded by profit only",
                "Automatically rides hot streaks into massive multipliers",
                "Discrete tier jumps — no gradual death-by-drift",
                "Self-correcting: retreats to base the instant luck cools below 100%",
                "Configurable tiers and luck window size",
            ],
            cons=[
                "Long base-tier dry spells before luck > 100% triggers descent",
                "Deep tiers have very low hit rates — patience required",
                "Session luck% spikes on small samples (use luck_window to smooth)",
                "Very high variance at tiers 3-4",
            ],
            best_use_case=(
                "Medium-to-long sessions where you want to capitalise on hot "
                "streaks by hunting large multipliers using house money only."
            ),
            tips=[
                "base_chance 5-10% builds profit quickly at tier 0",
                "profit_bet_pct 5% balances aggression with longevity",
                "luck_window 200-500 gives a reactive but noise-filtered luck signal",
                "luck_window 0 = full-session average (stable, slow to trigger)",
                "Set stop-loss -20% to protect base capital",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {
                "type": "str",
                "default": "0.000001",
                "desc": "Absolute floor — never bet below this",
            },
            "base_bet_pct": {
                "type": "float",
                "default": 0.001,
                "desc": "Tier-0 bet as fraction of current balance (0.002 = 0.2%)",
            },
            "profit_bet_pct": {
                "type": "float",
                "default": 0.02,
                "desc": "Deeper-tier bet as fraction of session profit (0.05 = 5%)",
            },
            "tiers": {
                "type": "str",
                "default": "[5.0, 1.0, 0.2, 0.04, 0.01]",
                "desc": (
                    "JSON list of win-chance % per tier, highest first. "
                    "Tier 0 = base chance. Example: [5.0, 1.0, 0.2, 0.04, 0.01]"
                ),
            },
            "luck_window": {
                "type": "int",
                "default": 0,
                "desc": (
                    "Rolling window size for luck% (0 = full session). "
                    "200-500 = faster-reacting luck signal."
                ),
            },
        }

    # ──────────────────────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.base_bet_pct: float = float(params.get("base_bet_pct", 0.002))
        self.profit_bet_pct: float = float(params.get("profit_bet_pct", 0.05))
        self.luck_window: int = max(0, int(params.get("luck_window", 0)))

        raw = params.get("tiers", _DEFAULT_TIERS)
        if isinstance(raw, str):
            raw = json.loads(raw)
        # Sort highest -> lowest: index 0 = easiest (base), last = hardest (deepest)
        self.tiers: List[float] = sorted([float(t) for t in raw], reverse=True)

        self._reset_state()

    def _reset_state(self) -> None:
        self.session_profit: float = 0.0
        # Each entry: (chance_played: float, won: bool)
        self._history: List[tuple] = []
        self.current_tier: int = 0

    def on_session_start(self) -> None:
        self._reset_state()

    def on_session_end(self, reason: str) -> None:
        pass

    # ── Luck% ─────────────────────────────────────────────────────────────────

    def _luck_pct(self) -> float:
        """Actual wins / expected wins x 100 over the configured window.
        Returns 100.0 (neutral) when there is no history.
        """
        window = (
            self._history[-self.luck_window:]
            if self.luck_window > 0
            else self._history
        )
        if not window:
            return 100.0
        expected = sum(c / 100.0 for c, _ in window)
        if expected <= 0.0:
            return 100.0
        actual = sum(1 for _, w in window if w)
        return (actual / expected) * 100.0

    # ── Tier selection ────────────────────────────────────────────────────────

    def _choose_tier(self) -> int:
        """Return the deepest affordable tier while luck% > 100%, else 0."""
        if self._luck_pct() <= 100.0:
            return 0
        # Walk from deepest to shallowest; pick first we can fund from profit
        for tier_idx in range(len(self.tiers) - 1, 0, -1):
            if self.session_profit >= float(self._calc_bet(tier_idx)):
                return tier_idx
        return 0

    # ── Bet sizing ────────────────────────────────────────────────────────────

    def _calc_bet(self, tier: int) -> Decimal:
        """Bet amount for a given tier index."""
        floor = self.base_amount
        if tier == 0:
            try:
                balance = float(Decimal(self.ctx.current_balance_str()))
            except Exception:
                balance = float(self.base_amount)
            amount_f = max(balance * self.base_bet_pct, float(floor))
        else:
            if self.session_profit <= 0.0:
                return floor
            amount_f = max(self.session_profit * self.profit_bet_pct, float(floor))

        return Decimal(str(amount_f)).quantize(_SATOSHI, rounding=ROUND_DOWN)

    # ── Protocol ──────────────────────────────────────────────────────────────

    def next_bet(self) -> Optional[BetSpec]:
        tier = self._choose_tier()
        self.current_tier = tier
        chance = self.tiers[tier]
        amount = self._calc_bet(tier)

        return {
            "game": "dice",
            "amount": format(amount, "f"),
            "chance": f"{chance:.4f}",
            "is_high": False,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = bool(result.get("win"))
        profit_f = float(Decimal(str(result.get("profit", "0"))))

        self._history.append((self.tiers[self.current_tier], win))

        self.session_profit += profit_f
        if not win:
            # Profit can't go below zero — deeper tiers only ever spend real profit
            self.session_profit = max(self.session_profit, 0.0)

        self.ctx.recent_results.append(result)
