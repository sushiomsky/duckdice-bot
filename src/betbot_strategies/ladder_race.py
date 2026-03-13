from __future__ import annotations
"""
Multiplier Ladder Race Strategy

4 consecutive winning bets with no misses allowed between them:
  Bet 1: win 5x   (19.8% chance)
  Bet 2: win 10x  ( 9.9% chance)  — must follow immediately after bet 1
  Bet 3: win 50x  ( 1.98% chance) — must follow immediately after bet 2
  Bet 4: win 100x ( 0.99% chance) — must follow immediately after bet 3

Any loss resets the sequence back to stage 1.
Stops automatically and prints all 4 winning bet IDs ready to post.
"""

from decimal import ROUND_DOWN, Decimal
from typing import Any, Dict, List, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata

_MIN_BET = Decimal("0.1")
_QUANT   = Decimal("0.00000001")

# (label, chance_str)
_LADDER: List[tuple[str, str]] = [
    ("5x",   "19.8"),
    ("10x",  "9.9"),
    ("50x",  "1.98"),
    ("100x", "0.99"),
]


def _bet_id(api_raw: Dict[str, Any]) -> Optional[str]:
    bet = (api_raw or {}).get("bet", {}) or {}
    raw_id = bet.get("id") or bet.get("betId")
    return str(raw_id) if raw_id is not None else None


@register("ladder-race")
class LadderRaceStrategy:
    """
    Contest ladder-race: 4 consecutive wins — 5x → 10x → 50x → 100x.
    Any loss resets back to stage 1. Stops when all 4 land back-to-back.
    """

    @classmethod
    def name(cls) -> str:
        return "ladder-race"

    @classmethod
    def describe(cls) -> str:
        return (
            "Contest strategy: 4 back-to-back wins (5x→10x→50x→100x). "
            "Any loss resets to stage 1. Stops when all 4 land consecutively."
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
                "Fully automated consecutive-win hunt",
                "Auto-stops when all 4 consecutive targets collected",
                "Prints ready-to-post contest entry on completion",
                "Minimum $0.1 bet per contest rules",
            ],
            cons=[
                "Any loss resets the entire sequence",
                "Combined probability ~0.004% per 4-bet attempt",
                "Can take a very large number of attempts",
            ],
            best_use_case="DuckDice Multiplier Ladder Race contest participation.",
            tips=[
                "Ensure sufficient balance — the 50x/100x resets are costly",
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
        self._current_run: List[str] = []   # IDs collected in the current attempt
        self._done: bool = False
        self._total_bets: int = 0
        self._attempts: int = 0             # number of times stage 1 was reached

    def on_session_start(self) -> None:
        self._stage = 0
        self._current_run = []
        self._done = False
        self._total_bets = 0
        self._attempts = 0
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
        self.ctx.recent_results.append(result)

        api_raw   = result.get("api_raw") or {}
        simulated = result.get("simulated", False) or api_raw.get("simulated", False)
        bet_id    = _bet_id(api_raw) if not simulated else f"SIM-{self._total_bets:06d}"
        label, _  = _LADDER[self._stage]

        if result.get("win"):
            display_id = bet_id or "???"
            self._current_run.append(display_id)
            self.ctx.printer(
                f"  ✅  Step {self._stage + 1}/4 ({label}) — ID {display_id}"
            )
            self._stage += 1

            if self._stage >= len(_LADDER):
                self._done = True
                self._on_complete()
            else:
                self._print_stage_banner()
        else:
            # Any loss resets the whole sequence
            if self._stage > 0:
                self.ctx.printer(
                    f"  ❌  Step {self._stage + 1}/4 ({label}) lost — "
                    "resetting to step 1"
                )
            self._stage = 0
            self._current_run = []
            self._attempts += 1

    def on_session_end(self, reason: str) -> None:
        if self._current_run and not self._done:
            self.ctx.printer("\n⚠️  Session ended mid-sequence.")
            self.ctx.printer(
                f"   Reached step {len(self._current_run) + 1}/4 before stopping."
            )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _print_stage_banner(self) -> None:
        label, chance_str = _LADDER[self._stage]
        self.ctx.printer(
            f"\n🪜  Step {self._stage + 1}/4: need {label} win ({chance_str}% chance)"
        )

    def _on_complete(self) -> None:
        self.ctx.printer("\n" + "=" * 60)
        self.ctx.printer("🏁  LADDER COMPLETE!  4 consecutive wins!")
        self.ctx.printer("=" * 60)
        self.ctx.printer("\nYour winning bet IDs:")
        for i, bid in enumerate(self._current_run):
            label, _ = _LADDER[i]
            self.ctx.printer(f"  {i + 1}. {label:>4s}  →  {bid}")
        self.ctx.printer(
            "\n📋  Copy-paste entry (ONE message):\n"
            f"   {self._current_run[0]}  {self._current_run[1]}  "
            f"{self._current_run[2]}  {self._current_run[3]}"
        )
        self.ctx.printer(
            f"\n📊  Total bets: {self._total_bets}  |  "
            f"Attempts: {self._attempts + 1}"
        )
        self.ctx.printer("=" * 60 + "\n")
