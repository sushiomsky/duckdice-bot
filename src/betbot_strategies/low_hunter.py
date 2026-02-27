from __future__ import annotations
"""
Low Hunter Strategy

Always bets at exactly 0.01% chance on Range Dice, locked to the LOW end
of the domain (slot 0 out of 0–9999).  Payout ~9900×.

Unlike Nano Hunter (which picks a fresh random slot each bet), Low Hunter
always targets slot 0 — the absolute lowest possible outcome.  This is a
pure low-end jackpot hunt: one specific slot, maximum payout.

Core mechanics
--------------
* Every bet targets slot 0 (range 0–0, chance = 0.01%, payout ≈ 9900×).
* Bet size is a configurable fraction of CURRENT balance.
* Optional loss multiplier (Martingale-style) up to a configurable cap.
* Optional profit target — stops cleanly when the goal is hit.
* On a win the multiplier resets to 1× (base bet).

Range Dice domain: 0 – 9999 (10 000 slots)
  slot 0  →  chance = 0.01%  →  payout ≈ 9900×
"""
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata


@register("low-hunter")
class LowHunter:
    """0.01%-chance Range Dice hunter locked to slot 0 (the lowest outcome)."""

    @classmethod
    def name(cls) -> str:
        return "low-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Always bets at exactly 0.01% chance on Range Dice, targeting slot 0 "
            "(the lowest possible outcome). Payout ~9900×. Bet size is a configurable "
            "fraction of your current balance with optional martingale-style loss "
            "escalation and profit target."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Extreme",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Very Long",
            recommended_for="Expert",
            pros=[
                "Massive ~9900× payout on a hit",
                "Always targets slot 0 — deterministic, transparent",
                "Very small bets — long bankroll life",
                "No complex state — pure probability play",
                "Optional martingale to accelerate recovery",
            ],
            cons=[
                "Expected loss per bet ≈ 1% (house edge)",
                "Average wait: ~10 000 bets per win",
                "Martingale can amplify losses quickly",
                "No guaranteed profit — pure gamble",
                "Requires large bankroll for martingale use",
            ],
            best_use_case=(
                "Low-end jackpot hunting with small bets. Ideal for players who want "
                "a fixed, repeatable target rather than a random slot. Works best with "
                "flat sizing (loss_mult=1.0) and a large enough bankroll."
            ),
            tips=[
                "Start with base_bet_pct=0.001 (0.1% of balance)",
                "Keep loss_mult=1.0 unless you understand martingale risk",
                "Set profit_target_pct to lock in gains automatically",
                "~10 000 bets between wins on average — patience required",
                "Each win needs ~9900 losing bets to break even at flat sizing",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_pct": {
                "type": "float",
                "default": 0.005,
                "desc": "Fraction of CURRENT balance bet per spin (0.005 = 0.5%)",
            },
            "loss_mult": {
                "type": "float",
                "default": 1.1,
                "desc": "Multiply bet by this factor after each loss (1.1 = +10%, 1.0 = flat)",
            },
            "max_mult": {
                "type": "float",
                "default": 10.0,
                "desc": "Cap the accumulated multiplier at this value (10 = max 10× base)",
            },
            "min_bet_abs": {
                "type": "str",
                "default": "",
                "desc": "Absolute minimum bet (decimal string e.g. '0.00000001'). Overrides pct floor.",
            },
            "max_bet_pct": {
                "type": "float",
                "default": 0.10,
                "desc": "Hard cap: bet never exceeds this fraction of current balance",
            },
            "profit_target_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Stop when profit ≥ this % of starting balance (0 = disabled)",
            },
        }

    # ------------------------------------------------------------------ init

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        self.base_bet_pct      = float(params.get("base_bet_pct",      0.005))
        self.loss_mult         = max(1.0, float(params.get("loss_mult",  1.1)))
        self.max_mult          = max(1.0, float(params.get("max_mult",   10.0)))
        self.max_bet_pct       = float(params.get("max_bet_pct",        0.10))
        self.profit_target_pct = float(params.get("profit_target_pct",  0.0))

        raw_min = str(params.get("min_bet_abs", "") or "")
        self.min_bet_abs: Optional[Decimal] = None
        if raw_min:
            try:
                self.min_bet_abs = Decimal(raw_min)
            except Exception:
                pass

        self._cur_mult:     float   = 1.0
        self._starting_bal: Decimal = Decimal("0")
        self._target_bal:   Decimal = Decimal("0")
        self._live_bal:     Decimal = Decimal("0")
        self._bets:         int     = 0
        self._wins:         int     = 0
        self._biggest_win:  Decimal = Decimal("0")

    # --------------------------------------------------------- session hooks

    def on_session_start(self) -> None:
        bal = _dec(self.ctx.starting_balance or "0")
        self._starting_bal = bal
        self._live_bal     = bal
        self._cur_mult     = 1.0
        self._bets         = 0
        self._wins         = 0
        self._biggest_win  = Decimal("0")

        if self.profit_target_pct > 0:
            self._target_bal = bal * Decimal(str(1 + self.profit_target_pct / 100))
        else:
            self._target_bal = Decimal("0")

        self.ctx.printer(
            f"[low-hunter] 0.01% Range Dice LOW hunter started | "
            f"balance={bal} | base_bet={self.base_bet_pct*100:.4f}% | "
            f"loss_mult={self.loss_mult}× cap={self.max_mult}× | "
            + (f"target={self._target_bal} (+{self.profit_target_pct:.1f}%)"
               if self._target_bal else "no target")
        )

    def on_session_end(self, reason: str) -> None:
        start = self._starting_bal
        final = self._live_bal
        pnl   = final - start
        pct   = float(pnl / start * 100) if start else 0.0
        sign  = "+" if pnl >= 0 else ""
        self.ctx.printer(
            f"[low-hunter] session ended ({reason}) | "
            f"bets={self._bets} wins={self._wins} | "
            f"PnL={sign}{pnl:.8f} ({sign}{pct:.2f}%) | "
            f"biggest_win={self._biggest_win:.8f}"
        )

    # ------------------------------------------------------------- next bet

    def next_bet(self) -> Optional[BetSpec]:
        if self._target_bal > 0 and self._live_bal >= self._target_bal:
            self.ctx.printer(
                f"[low-hunter] 🎯 profit target reached "
                f"({self._live_bal:.8f} ≥ {self._target_bal:.8f}) — stopping"
            )
            return None

        bal = self._live_bal
        if bal <= 0:
            return None

        base = bal * Decimal(str(self.base_bet_pct))
        amt  = base * Decimal(str(min(self._cur_mult, self.max_mult)))

        if self.min_bet_abs and amt < self.min_bet_abs:
            amt = self.min_bet_abs

        cap = bal * Decimal(str(self.max_bet_pct))
        if amt > cap:
            amt = cap

        amt = amt.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        if amt <= 0:
            return None

        return {
            "game":   "range-dice",
            "amount": format(amt, "f"),
            "range":  (0, 0),   # slot 0 only — lowest possible, 0.01% chance
            "is_in":  True,
            "faucet": self.ctx.faucet,
        }

    # ---------------------------------------------------------- bet result

    def on_bet_result(self, result: BetResult) -> None:
        self.ctx.recent_results.append(result)
        self._bets += 1

        try:
            self._live_bal = Decimal(str(result.get("balance", self._live_bal)))
        except Exception:
            pass

        won = bool(result.get("win"))
        if won:
            self._wins    += 1
            self._cur_mult = 1.0
            try:
                profit = Decimal(str(result.get("profit", "0")))
                if profit > self._biggest_win:
                    self._biggest_win = profit
                self.ctx.printer(
                    f"[low-hunter] 🎰 WIN! profit={profit:.8f} "
                    f"bal={self._live_bal:.8f} after {self._bets} bets"
                )
            except Exception:
                pass
        else:
            if self.loss_mult > 1.0:
                self._cur_mult = min(self._cur_mult * self.loss_mult, self.max_mult)

    # --------------------------------------------------------------- helpers


def _dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")
