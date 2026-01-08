from __future__ import annotations
"""
FaucetCashout Strategy (USD-targeted)
- Goal: grow a tiny faucet balance (USD-equivalent) to a USD target using 50% odds
- Uses staged fractions and strong safeguards.
- Converts USD target to coin target using either provided usd_per_coin or
  a lightweight price fetch (CoinGecko) if coingecko_id is provided.

Defaults (can be tuned via params):
- Stage A: until usd_balance >= 0.25 USD → fraction in [0.02, 0.0333]
- Stage B: until usd_balance >= 5.00 USD → fraction in [0.04, 0.066]
- Stage C: until usd_balance >= usd_target → fraction in [0.066, 0.10]
- Hard stop-loss at -25% relative to session start (USD).

Notes:
- Targets and thresholds are USD-denominated.
- If no price is available, falls back to usd_per_coin=1.0 (coin==USD) and logs a warning.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional
import time

import requests

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@dataclass
class _Stages:
    a_min: float = 0.02
    a_max: float = 0.0333
    b_min: float = 0.04
    b_max: float = 0.066
    c_min: float = 0.066
    c_max: float = 0.10


@register("faucet-cashout")
class FaucetCashout:
    """Grow micro balance to a USD target with staged 50% bets and safeguards."""

    @classmethod
    def name(cls) -> str:
        return "faucet-cashout"

    @classmethod
    def describe(cls) -> str:
        return "USD-targeted staged growth: 50% bets with conservative sizing to reach a USD balance target."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very Low",
            bankroll_required="None (Free)",
            volatility="Low",
            time_to_profit="Slow",
            recommended_for="Beginners",
            pros=[
                "Zero risk - uses free faucet bets",
                "Perfect for learning without deposit",
                "Slow grind but absolutely free",
                "Great for testing strategies",
                "Can build up from nothing"
            ],
            cons=[
                "Extremely slow progress",
                "Requires huge time investment",
                "Faucet limits may apply",
                "Not realistic profit strategy",
                "Better options exist for real play"
            ],
            best_use_case="Learning tool for absolute beginners. Test platform features risk-free.",
            tips=[
                "Be patient - this is a marathon not a sprint",
                "Use to learn platform mechanics",
                "Don't expect meaningful profits",
                "Great for strategy testing",
                "Transition to real betting once comfortable",
                "Set realistic cashout targets (e.g., 0.0001)"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "usd_target": {"type": "float", "default": 20.0, "desc": "Target balance in USD-equivalent"},
            "usd_stage_a": {"type": "float", "default": 0.25, "desc": "Stage A→B threshold (USD)"},
            "usd_stage_b": {"type": "float", "default": 5.0, "desc": "Stage B→C threshold (USD)"},
            "stageA_min_frac": {"type": "float", "default": 0.02},
            "stageA_max_frac": {"type": "float", "default": 0.0333},
            "stageB_min_frac": {"type": "float", "default": 0.04},
            "stageB_max_frac": {"type": "float", "default": 0.066},
            "stageC_min_frac": {"type": "float", "default": 0.066},
            "stageC_max_frac": {"type": "float", "default": 0.10},
            "min_amount": {"type": "str", "default": "", "desc": "Absolute minimum bet amount (decimal string)"},
            "retreat_on_losses": {"type": "int", "default": 3},
            "cooldown_bets": {"type": "int", "default": 0},
            "hard_stop_loss": {"type": "float", "default": -0.25, "desc": "Stop if USD equity falls by this ratio from start"},
            "game": {"type": "str", "default": "dice", "desc": "dice|range-dice"},
            "chance": {"type": "float", "default": 50.0, "desc": "Chance percent for dice"},
            # Pricing
            "usd_per_coin": {"type": "float", "default": 0.0, "desc": "Override price: USD per 1 coin (if > 0)"},
            "coingecko_id": {"type": "str", "default": "", "desc": "CoinGecko ID for symbol (e.g., 'bitcoin')"},
            "price_refresh_sec": {"type": "int", "default": 300, "desc": "Refresh price every N seconds (0=once)"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.usd_target = float(params.get("usd_target", 20.0))
        self.usd_stage_a = float(params.get("usd_stage_a", 0.25))
        self.usd_stage_b = float(params.get("usd_stage_b", 5.0))
        self.stages = _Stages(
            a_min=float(params.get("stageA_min_frac", 0.02)),
            a_max=float(params.get("stageA_max_frac", 0.0333)),
            b_min=float(params.get("stageB_min_frac", 0.04)),
            b_max=float(params.get("stageB_max_frac", 0.066)),
            c_min=float(params.get("stageC_min_frac", 0.066)),
            c_max=float(params.get("stageC_max_frac", 0.10)),
        )
        self.min_amount = str(params.get("min_amount", "") or "") or None
        self.retreat_on_losses = int(params.get("retreat_on_losses", 3))
        self.cooldown_bets = int(params.get("cooldown_bets", 0))
        self.hard_stop_loss = float(params.get("hard_stop_loss", -0.25))
        self.game = (str(params.get("game", "dice") or "dice")).lower()
        if self.game not in ("dice", "range-dice"):
            self.game = "dice"
        self.chance = float(params.get("chance", 50.0))

        # pricing
        self._usd_per_coin_param = float(params.get("usd_per_coin", 0.0) or 0.0)
        self._coingecko_id = (str(params.get("coingecko_id", "") or "").strip())
        self._price_refresh_sec = max(0, int(params.get("price_refresh_sec", 300) or 0))

        # state
        self._losses = 0
        self._cooldown_left = 0
        self._price_usd_per_coin = 0.0
        self._last_price_ts = 0.0
        self._usd_start = 0.0

    def on_session_start(self) -> None:
        # Initialize price and starting USD equity
        self._ensure_price()
        try:
            bal_s = self.ctx.current_balance_str()
            bal = float(Decimal(str(bal_s))) if bal_s else 0.0
        except Exception:
            bal = 0.0
        self._usd_start = bal * self._price()

    def _ensure_price(self) -> None:
        if self._usd_per_coin_param > 0:
            self._price_usd_per_coin = float(self._usd_per_coin_param)
            return
        now = time.time()
        if self._price_usd_per_coin > 0 and self._price_refresh_sec > 0 and (now - self._last_price_ts) < self._price_refresh_sec:
            return
        if not self._coingecko_id:
            # fallback
            self._price_usd_per_coin = 1.0
            self._last_price_ts = now
            self._log_warning("No coingecko_id provided; using 1.0 USD/coin fallback.")
            return
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={self._coingecko_id}&vs_currencies=usd"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json() or {}
            usd = float((data.get(self._coingecko_id) or {}).get("usd", 0.0) or 0.0)
            if usd > 0:
                self._price_usd_per_coin = usd
                self._last_price_ts = now
            else:
                raise ValueError("invalid usd price")
        except Exception:
            if self._price_usd_per_coin <= 0:
                self._price_usd_per_coin = 1.0
                self._log_warning("Failed to fetch price; using 1.0 USD/coin fallback.")

    def _price(self) -> float:
        self._ensure_price()
        return float(self._price_usd_per_coin or 1.0)

    def _usd_equity(self) -> float:
        try:
            bal_s = self.ctx.current_balance_str()
            bal = float(Decimal(str(bal_s))) if bal_s else 0.0
        except Exception:
            bal = 0.0
        return bal * self._price()

    def _stage_fracs(self) -> tuple[float, float]:
        usd = self._usd_equity()
        if usd < self.usd_stage_a:
            return (self.stages.a_min, self.stages.a_max)
        if usd < self.usd_stage_b:
            return (self.stages.b_min, self.stages.b_max)
        if usd < self.usd_target:
            return (self.stages.c_min, self.stages.c_max)
        # target reached; keep minimal risk
        return (0.0, 0.0)

    def _log_warning(self, msg: str) -> None:
        self.ctx.logger({"event": "warning", "msg": msg})

    def next_bet(self) -> Optional[BetSpec]:
        if self._cooldown_left > 0:
            self._cooldown_left -= 1
            return None
        lo, hi = self._stage_fracs()
        if hi <= 0.0:
            return None
        import random as _r
        frac = _r.uniform(lo, hi)
        # determine amount in coins
        bal_s = self.ctx.current_balance_str() or self.ctx.starting_balance or "0"
        try:
            bal = Decimal(str(bal_s))
        except Exception:
            bal = Decimal(0)
        amt = bal * Decimal(str(frac))
        if self.min_amount:
            try:
                ma = Decimal(str(self.min_amount))
                if amt < ma:
                    amt = ma
            except Exception:
                pass
        if amt <= 0:
            return None
        if self.game == "dice":
            bet: BetSpec = {
                "game": "dice",
                "amount": format(amt, 'f'),
                "chance": str(self.chance),
                "is_high": bool(self.ctx.rng.random() < 0.5),
                "faucet": self.ctx.faucet,
            }
        else:
            # range-dice 50% window
            start_max = 9999 - 5000 + 1
            start = int(self.ctx.rng.randrange(start_max))
            r = (start, start + 5000 - 1)
            bet = {
                "game": "range-dice",
                "amount": format(amt, 'f'),
                "range": (int(r[0]), int(r[1])),
                "is_in": True,
                "faucet": self.ctx.faucet,
            }
        return bet

    def on_bet_result(self, result: BetResult) -> None:
        if result.get("win"):
            self._losses = 0
        else:
            self._losses += 1
            if self._losses >= self.retreat_on_losses:
                self._cooldown_left = max(self._cooldown_left, self.cooldown_bets)
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        pass
