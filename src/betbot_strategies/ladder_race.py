from __future__ import annotations
"""
Multiplier Ladder Race Strategy

Contest strategy: win each multiplier once in sequential order.
  Stage 1: 5x   (19.8% chance) — first win advances to next stage
  Stage 2: 10x  ( 9.9% chance) — first win advances to next stage
  Stage 3: 50x  ( 1.98% chance) — first win advances to next stage
  Stage 4: 100x ( 0.99% chance) — first win completes the ladder

Stops automatically and prints all 4 winning bet IDs ready to post.
"""

from decimal import ROUND_DOWN, Decimal
from typing import Any, Dict, List, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_MIN_BET = Decimal("0.1")       # Contest minimum
_QUANT   = Decimal("0.00000001")

# (label, chance_str)
_LADDER: List[tuple[str, str]] = [
    ("5x",   "19.8"),
    ("10x",  "9.9"),
    ("50x",  "1.98"),
    ("100x", "0.99"),
]


def _bet_id(api_raw: Dict[str, Any]) -> Optional[str]:
    """Extract the bet ID string from a raw API response."""
    bet = (api_raw or {}).get("bet", {}) or {}
    raw_id = bet.get("id") or bet.get("betId")
    return str(raw_id) if raw_id is not None else None


@register("ladder-race")
class LadderRaceStrategy:
    """
    Contest ladder-race: win 5x → 10x → 50x → 100x in sequential order.

    Every win at the current stage advances to the next. Stops automatically
    once all 4 wins are collected and prints a ready-to-post entry message.
    """

    @classmethod
    def name(cls) -> str:
        return "ladder-race"

    @classmethod
    def describe(cls) -> str:
        return (
            "Contest strategy: wins 5x, 10x, 50x, 100x in sequential order. "
            "Any win at each stage advances the ladder. Stops when complete."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Small",
            volatility="Very High",
            time_to_profit="N/A — contest focused",
            recommended_for="Contest participants",
            pros=[
                "Fully automated ladder hunt",
                "Auto-stops when all 4 targets collected",
                "Prints ready-to-post contest entry on completion",
                "Minimum $0.1 bet per contest rules",
            ],
            cons=[
                "100x stage (0.99%) can require many bets",
                "High variance at 50x and 100x stages",
            ],
            best_use_case="DuckDice Multiplier Ladder Race contest participation.",
            tips=[
                "Ensure balance can sustain the 50x and 100x stages",
                "Bot stops automatically — watch for the '🏁 LADDER COMPLETE' message",
                "All 4 IDs are printed at the end; paste them in ONE message to the contest",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "bet_amount": {
                "type": "float",
                "default": 0.1,
                "desc": "Amount to bet per roll (minimum 0.1 for contest eligibility)",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet direction: True=High, False=Low",
            },
        }

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        raw_amount = Decimal(str(params.get("bet_amount", "0.1")))
        self._bet_amount: Decimal = max(raw_amount, _MIN_BET).quantize(
            _QUANT, rounding=ROUND_DOWN
        )
        self._is_high: bool = bool(params.get("is_high", True))
        self._stage: int = 0
        self._collected: List[str] = []
        self._done: bool = False
        self._bets_this_stage: int = 0
        self._total_bets: int = 0

    def on_session_start(self) -> None:
        self._stage = 0
        self._collected = []
        self._done = False
        self._bets_this_stage = 0
        self._total_bets = 0
        self._print_stage_banner()

    def next_bet(self) -> Optional[BetSpec]:
        if self._done:
            return None

        _, chance_str = _LADDER[self._stage]
        return {
            "game":    "dice",
            "amount":  format(self._bet_amount, "f"),
            "chance":  chance_str,
            "is_high": self._is_high,
            "faucet":  self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        if self._done:
            return

        self._total_bets += 1
        self._bets_this_stage += 1
        self.ctx.recent_results.append(result)

        if not result.get("win"):
            return

        # ── Win — record the bet ID and advance ───────────────────────────
        api_raw = result.get("api_raw") or {}
        simulated = result.get("simulated", False) or api_raw.get("simulated", False)
        bet_id = _bet_id(api_raw) if not simulated else f"SIM-{self._total_bets:06d}"

        label, _ = _LADDER[self._stage]
        display_id = bet_id or "???"
        self._collected.append(display_id)

        self.ctx.printer(
            f"  ✅  Stage {self._stage + 1}/{len(_LADDER)} ({label}) — "
            f"ID {display_id}  (took {self._bets_this_stage} bets)"
        )

        self._stage += 1
        self._bets_this_stage = 0

        if self._stage >= len(_LADDER):
            self._done = True
            self._on_complete()
        else:
            self._print_stage_banner()

    def on_session_end(self, reason: str) -> None:
        if self._collected and not self._done:
            self.ctx.printer("\n⚠️  Session ended before ladder was complete.")
            self.ctx.printer(
                f"   Progress: {len(self._collected)}/{len(_LADDER)} stages done"
            )
            for i, bid in enumerate(self._collected):
                label, _ = _LADDER[i]
                self.ctx.printer(f"   Stage {i + 1} ({label}): {bid}")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _print_stage_banner(self) -> None:
        label, chance_str = _LADDER[self._stage]
        self.ctx.printer(
            f"\n🪜  Stage {self._stage + 1}/{len(_LADDER)}: "
            f"hunting {label} win ({chance_str}% chance)"
        )

    def _on_complete(self) -> None:
        self.ctx.printer("\n" + "=" * 60)
        self.ctx.printer("🏁  LADDER COMPLETE!  All 4 targets collected.")
        self.ctx.printer("=" * 60)
        self.ctx.printer("\nYour winning bet IDs:")
        for i, bid in enumerate(self._collected):
            label, _ = _LADDER[i]
            self.ctx.printer(f"  {i + 1}. {label:>4s}  →  {bid}")
        self.ctx.printer(
            "\n📋  Copy-paste entry (ONE message):\n"
            f"   {self._collected[0]}  {self._collected[1]}  "
            f"{self._collected[2]}  {self._collected[3]}"
        )
        self.ctx.printer(f"\n📊  Total bets placed: {self._total_bets}")
        self.ctx.printer("=" * 60 + "\n")
