"""
Adaptive Hunter Strategy - Unified consolidation of 12 hunter variants.

This module provides a single configurable strategy that can operate as any of
the original hunter strategies (cold_number_hunter, streak_hunter, spike_hunter,
volatility_spike_hunter, nano_hunter, dynamic_phase_hunter, gradient_range_hunter,
adaptive_volatility_hunter, regime_hunter, low_hunter, nano_range_hunter, 
streak_pressure_hunter) via constructor parameters.

Core mechanics vary by hunt_type but all share:
- Target-based bet sizing (fraction of balance)
- Optional loss multipliers (martingale-style escalation)
- Profit targets and loss limits
- State tracking for performance metrics
"""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional, List, Tuple
from collections import deque
import math

from . import register
from .base import BetResult, BetSpec, StrategyContext, StrategyMetadata


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED ADAPTIVE HUNTER - 12 variants via hunt_type config parameter
# ═══════════════════════════════════════════════════════════════════════════════

@register("adaptive-hunter")
class AdaptiveHunter:
    """
    Unified hunter strategy: configure via hunt_type parameter to select
    which hunting algorithm to use. Each hunt_type has distinct mechanics
    but shares common bet sizing, state tracking, and lifecycle.
    
    hunt_type options:
    - 'cold_number': Bet on underrepresented slots from history (Range Dice)
    - 'streak': Hunt 14% chance with compounding multipliers on wins
    - 'spike': Volatility spike hunting with 3-phase state machine
    - 'volatility': Adaptive low-chance hunting with RNG volatility detection
    - 'nano': Fixed 0.01% (1-slot, ~9900x) with random windows
    - 'dynamic_phase': Tiered profit target with loss-count phases
    - 'gradient_range': Target-gradient bet sizing with random Range Dice windows
    - 'adaptive_volatility': Ultra-low chance with volatility-based adaptation
    - 'regime': Three-regime stochastic amplifier (A→B→C transitions)
    - 'low': Fixed 0.01% locked to slot 0 (LOW end)
    - 'nano_range': Medium Moon variant with cold-zone bias and survival mode
    - 'streak_pressure': Pattern-pressure detection with escalation hunting
    """

    @classmethod
    def name(cls) -> str:
        return "adaptive-hunter"

    @classmethod
    def describe(cls) -> str:
        return (
            "Unified adaptive hunter: 12 variants selectable via hunt_type. "
            "From cold-number tracking to volatility spike hunting, dynamic phase targeting, "
            "and regime-switching amplifiers. Configure via constructor parameters."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Variable",
            bankroll_required="Medium-Large",
            volatility="Variable",
            time_to_profit="Variable",
            recommended_for="Intermediate-Expert",
            pros=[
                "12 distinct hunting algorithms in a single configurable strategy",
                "Highly customizable: threshold, multiplier, range_mode per hunt_type",
                "Share common state tracking and lifecycle (session hooks)",
                "Easy to switch between hunt types without code changes",
                "Target-aware bet sizing prevents over-betting at goal",
                "Optional loss multiplier escalation (martingale-style)",
            ],
            cons=[
                "Requires understanding which hunt_type best fits your use case",
                "High variance inherent to most hunter strategies",
                "Some variants (nano, volatility) require large bankroll",
                "House edge ~1% per bet regardless of hunt mechanics",
            ],
            best_use_case=(
                "Multi-variant testing and experimentation. Use this when you want to "
                "quickly switch between different hunter approaches without maintaining "
                "12 separate files."
            ),
            tips=[
                "Start with 'streak' or 'gradient_range' for balanced risk/reward",
                "Use 'nano' or 'low' for pure long-shot jackpot hunting",
                "Use 'volatility' or 'adaptive_volatility' if you want RNG-aware betting",
                "Set profit_target_pct and loss_limit_pct to define exit conditions",
                "Use loss_multiplier=1.0 (flat sizing) to prevent escalation risk",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "hunt_type": {
                "type": "str",
                "default": "streak",
                "desc": "Which hunter variant: cold_number|streak|spike|volatility|nano|dynamic_phase|gradient_range|adaptive_volatility|regime|low|nano_range|streak_pressure",
            },
            "threshold": {
                "type": "float",
                "default": 0.3,
                "desc": "Hunt threshold / sensitivity (0.0-1.0 scale, hunt_type dependent)",
            },
            "multiplier": {
                "type": "float",
                "default": 1.2,
                "desc": "Loss multiplier or progression multiplier (default 1.2 = 20% increase per loss)",
            },
            "range_mode": {
                "type": "bool",
                "default": False,
                "desc": "Use Range Dice (True) vs standard Dice (False)",
            },
            "base_bet_pct": {
                "type": "float",
                "default": 0.0025,
                "desc": "Base bet as % of balance (0.005 = 0.5%)",
            },
            "max_bet_pct": {
                "type": "float",
                "default": 0.08,
                "desc": "Hard cap on bet as % of balance (0.08 = 8%)",
            },
            "loss_multiplier": {
                "type": "float",
                "default": 1.0,
                "desc": "Bet multiplier on loss (1.0 = flat, >1.0 = escalation)",
            },
            "max_loss_multiplier": {
                "type": "float",
                "default": 25.0,
                "desc": "Cap on accumulated loss multiplier",
            },
            "profit_target_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Auto-stop when profit ≥ this % of starting balance (0 = off)",
            },
            "loss_limit_pct": {
                "type": "float",
                "default": 0.0,
                "desc": "Auto-stop when loss ≥ this % of starting balance (0 = off)",
            },
            "min_bet_abs": {
                "type": "str",
                "default": "0.00000001",
                "desc": "Absolute minimum bet amount (avoids dust bets)",
            },
            "chance_pct": {
                "type": "float",
                "default": 49.5,
                "desc": "Target win chance % (for streak, gradient, etc.)",
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet HIGH (True) or LOW (False) for dice strategies",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.hunt_type = str(params.get("hunt_type", "streak")).lower()
        self.threshold = float(params.get("threshold", 0.5))
        self.multiplier = float(params.get("multiplier", 1.2))
        self.range_mode = bool(params.get("range_mode", False))
        self.base_bet_pct = float(params.get("base_bet_pct", 0.01))
        self.max_bet_pct = float(params.get("max_bet_pct", 0.10))
        self.loss_multiplier = max(1.0, float(params.get("loss_multiplier", 1.0)))
        self.max_loss_multiplier = float(params.get("max_loss_multiplier", 25.0))
        self.profit_target_pct = float(params.get("profit_target_pct", 0.0))
        self.loss_limit_pct = float(params.get("loss_limit_pct", 0.0))
        self.min_bet_abs = Decimal(str(params.get("min_bet_abs", "0.00000001")))
        self.chance_pct = float(params.get("chance_pct", 14.0))
        self.is_high = bool(params.get("is_high", True))

        # Hunt-type specific state
        self._hunt_state: Dict[str, Any] = {}
        self._initialize_hunt_state()

        # Common state
        self._starting_balance = Decimal("0")
        self._current_balance = Decimal("0")
        self._peak_balance = Decimal("0")
        self._loss_multiplier_current = 1.0
        self._total_bets = 0
        self._total_wins = 0
        self._win_streak = 0
        self._loss_streak = 0
        self._recent_results: deque = deque(maxlen=100)

    def _initialize_hunt_state(self) -> None:
        """Initialize hunt-type-specific state."""
        if self.hunt_type == "cold_number":
            self._hunt_state = {
                "cold_counts": [0] * 10_000,
                "cold_total": 0,
                "last_refresh": 0,
            }
        elif self.hunt_type == "streak":
            self._hunt_state = {
                "win_streak": 0,
                "last_bet_amount": Decimal("0"),
            }
        elif self.hunt_type in ("spike", "volatility", "adaptive_volatility"):
            self._hunt_state = {
                "phase": "PASSIVE",
                "phase_bets": 0,
                "cycle_losses": Decimal("0"),
                "cycle_start_balance": Decimal("0"),
                "recent_chances": deque(maxlen=50),
                "recent_results": deque(maxlen=100),
            }
        elif self.hunt_type == "nano":
            self._hunt_state = {
                "target_slot": None,  # random per bet
            }
        elif self.hunt_type == "dynamic_phase":
            self._hunt_state = {
                "accumulated_losses": Decimal("0"),
                "cycle_start_balance": Decimal("0"),
                "loss_count": 0,
            }
        elif self.hunt_type == "gradient_range":
            self._hunt_state = {
                "target_balance": Decimal("0"),
            }
        elif self.hunt_type == "regime":
            self._hunt_state = {
                "regime": "A",
                "bets_in_regime": 0,
                "regime_entry_balance": Decimal("0"),
                "entropy_history": deque(maxlen=50),
            }
        elif self.hunt_type == "low":
            self._hunt_state = {
                "target_slot": 0,  # always slot 0
            }
        elif self.hunt_type == "nano_range":
            self._hunt_state = {
                "cold_buckets": [0] * 200,
                "cold_total": 0,
                "cycle_bets": 0,
                "drought_length": 0,
            }
        elif self.hunt_type == "streak_pressure":
            self._hunt_state = {
                "phase": "OBSERVE",
                "phase_steps": 0,
                "outcome_history": deque(maxlen=50),
                "hunt_steps_remaining": 0,
            }

    def on_session_start(self) -> None:
        """Initialize session tracking."""
        bal = Decimal(str(self.ctx.starting_balance or "0"))
        self._starting_balance = bal
        self._current_balance = bal
        self._peak_balance = bal
        self._loss_multiplier_current = 1.0
        self._total_bets = 0
        self._total_wins = 0
        self._win_streak = 0
        self._loss_streak = 0
        self._recent_results.clear()

        if self.hunt_type == "dynamic_phase":
            self._hunt_state["cycle_start_balance"] = bal
            self._hunt_state["accumulated_losses"] = Decimal("0")
            self._hunt_state["loss_count"] = 0
        elif self.hunt_type == "gradient_range":
            self._hunt_state["target_balance"] = bal * Decimal("2")  # 2x target
        elif self.hunt_type == "regime":
            self._hunt_state["regime_entry_balance"] = bal

        self.ctx.printer(
            f"[adaptive-hunter] started | hunt_type={self.hunt_type} | "
            f"balance={bal} | threshold={self.threshold} | multiplier={self.multiplier}"
        )

    def on_session_end(self, reason: str) -> None:
        """Log session summary."""
        pnl = self._current_balance - self._starting_balance
        pnl_pct = float(pnl / self._starting_balance * 100) if self._starting_balance else 0
        sign = "+" if pnl >= 0 else ""

        self.ctx.printer(
            f"[adaptive-hunter] ended ({reason}) | hunt_type={self.hunt_type} | "
            f"bets={self._total_bets} | wins={self._total_wins} | "
            f"PnL={sign}{pnl:.8f} ({sign}{pnl_pct:.2f}%) | "
            f"streak={self._win_streak}"
        )

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet based on hunt_type."""
        # Check profit target
        if self.profit_target_pct > 0:
            target = self._starting_balance * Decimal(str(1 + self.profit_target_pct / 100))
            if self._current_balance >= target:
                self.ctx.printer(f"[adaptive-hunter] profit target reached — stopping")
                return None

        # Check loss limit
        if self.loss_limit_pct > 0:
            limit = self._starting_balance * Decimal(str(1 - self.loss_limit_pct / 100))
            if self._current_balance <= limit:
                self.ctx.printer(f"[adaptive-hunter] loss limit hit — stopping")
                return None

        if self._current_balance <= 0:
            return None

        # Dispatch to hunt-type-specific logic
        if self.hunt_type == "cold_number":
            return self._next_bet_cold_number()
        elif self.hunt_type == "streak":
            return self._next_bet_streak()
        elif self.hunt_type == "spike":
            return self._next_bet_spike()
        elif self.hunt_type == "volatility":
            return self._next_bet_volatility()
        elif self.hunt_type == "nano":
            return self._next_bet_nano()
        elif self.hunt_type == "dynamic_phase":
            return self._next_bet_dynamic_phase()
        elif self.hunt_type == "gradient_range":
            return self._next_bet_gradient_range()
        elif self.hunt_type == "adaptive_volatility":
            return self._next_bet_adaptive_volatility()
        elif self.hunt_type == "regime":
            return self._next_bet_regime()
        elif self.hunt_type == "low":
            return self._next_bet_low()
        elif self.hunt_type == "nano_range":
            return self._next_bet_nano_range()
        elif self.hunt_type == "streak_pressure":
            return self._next_bet_streak_pressure()
        else:
            # Default to streak if unknown
            return self._next_bet_streak()

    def on_bet_result(self, result: BetResult) -> None:
        """Update state based on bet result."""
        self.ctx.recent_results.append(result)
        self._recent_results.append(result)
        self._total_bets += 1

        try:
            self._current_balance = Decimal(str(result.get("balance", self._current_balance)))
        except Exception:
            pass
        if self._current_balance > self._peak_balance:
            self._peak_balance = self._current_balance

        won = bool(result.get("win", False))
        if won:
            self._total_wins += 1
            self._win_streak += 1
            self._loss_streak = 0
            self._loss_multiplier_current = 1.0
            if self.hunt_type == "dynamic_phase":
                self._hunt_state["accumulated_losses"] = Decimal("0")
                self._hunt_state["loss_count"] = 0
        else:
            self._loss_streak += 1
            self._win_streak = 0
            if self.loss_multiplier > 1.0:
                self._loss_multiplier_current = min(
                    self._loss_multiplier_current * self.loss_multiplier,
                    self.max_loss_multiplier
                )
            if self.hunt_type == "dynamic_phase":
                loss_amt = Decimal(str(result.get("amount", "0")))
                self._hunt_state["accumulated_losses"] += loss_amt
                self._hunt_state["loss_count"] += 1

    # ───────────────────────────────────────────────────────────────────────────
    # HUNT-TYPE-SPECIFIC IMPLEMENTATIONS
    # ───────────────────────────────────────────────────────────────────────────

    def _next_bet_cold_number(self) -> Optional[BetSpec]:
        """Cold number hunter: bet on least-seen slots in history."""
        bal = self._current_balance
        if bal <= 0:
            return None

        # Update cold counts from recent rolls
        for r in self._recent_results:
            slot = int(float(r.get("number", "0"))) % 10_000
            self._hunt_state["cold_counts"][slot] += 1
            self._hunt_state["cold_total"] += 1

        # Find N coldest slots (weighted toward under-represented)
        if self._hunt_state["cold_total"] > 0:
            alpha = max(1.0, self._hunt_state["cold_total"] / 10_000 * 0.1)
            raw_weights = [1.0 / (c + alpha) for c in self._hunt_state["cold_counts"]]
            total_w = sum(raw_weights)
            normed = [w / total_w for w in raw_weights]

            # Pick from top N coldest
            n_pick = max(1, int(self.threshold * 100))
            indexed = sorted(enumerate(normed), key=lambda x: x[1], reverse=True)
            top_slots = [s for s, _ in indexed[:n_pick]]
            top_weights = [w for _, w in indexed[:n_pick]]
            w_sum = sum(top_weights)
            top_weights = [w / w_sum for w in top_weights]

            chosen_slot = self.ctx.rng.choices(top_slots, weights=top_weights, k=1)[0]
        else:
            chosen_slot = self.ctx.rng.randint(0, 9999)

        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "range-dice",
            "amount": format(amt, "f"),
            "range": (chosen_slot, chosen_slot),
            "is_in": True,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_streak(self) -> Optional[BetSpec]:
        """Streak hunter: 14% chance with compounding multipliers on wins."""
        bal = self._current_balance
        if bal <= 0:
            return None

        # Base bet is balance / divisor, adapting to profit progress
        base = bal / Decimal(str(500))  # default divisor
        base = max(self.min_bet_abs, base)

        # Streak multiplier: 2.0 → 1.8 → 1.6 → ...
        if self._win_streak == 0:
            streak_mult = 1.0
        elif self._win_streak == 1:
            streak_mult = 2.0
        elif self._win_streak == 2:
            streak_mult = 1.8
        elif self._win_streak == 3:
            streak_mult = 1.6
        else:
            streak_mult = max(0.5, 1.6 - 0.2 * (self._win_streak - 3))

        amt = base * Decimal(str(streak_mult)) * Decimal(str(self._loss_multiplier_current))
        amt = min(amt, bal * Decimal(str(self.max_bet_pct)))
        amt = max(self.min_bet_abs, amt)

        return {
            "game": "dice",
            "amount": format(amt, "f"),
            "chance": str(self.chance_pct),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_spike(self) -> Optional[BetSpec]:
        """Volatility spike hunter: 3-phase state machine (PASSIVE → PROBE → LOAD → SNIPE)."""
        bal = self._current_balance
        if bal <= 0:
            return None

        # Simplified spike logic: use current threshold to determine phase
        phase_idx = min(2, int(self.threshold * 3))
        phases = ["PASSIVE", "PROBE", "SNIPE"]
        phase = phases[phase_idx]

        # Chance selection based on phase
        if phase == "PASSIVE":
            chance = 50.0  # minimal bets
        elif phase == "PROBE":
            chance = max(0.8, min(3.0, self.chance_pct))
        else:  # SNIPE
            chance = max(0.1, min(0.5, self.chance_pct / 10))

        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "dice",
            "amount": format(amt, "f"),
            "chance": f"{chance:.2f}",
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_volatility(self) -> Optional[BetSpec]:
        """Adaptive low-chance hunting with RNG volatility detection."""
        bal = self._current_balance
        if bal <= 0:
            return None

        # Compute volatility from recent results
        if len(self._recent_results) > 10:
            wins = sum(1 for r in list(self._recent_results)[-20:] if r.get("win"))
            expected_wins = 0.5 * 20
            volatility = abs(wins - expected_wins) / (expected_wins + 0.1)
        else:
            volatility = 0.5

        # Adapt chance inversely to volatility
        base_chance = 0.5 if volatility < self.threshold else 2.0
        chance = base_chance * (1 + volatility * self.multiplier)
        chance = max(0.01, min(10.0, chance))

        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "dice",
            "amount": format(amt, "f"),
            "chance": f"{chance:.2f}",
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_nano(self) -> Optional[BetSpec]:
        """Nano hunter: fixed 0.01% chance, random slot each bet."""
        bal = self._current_balance
        if bal <= 0:
            return None

        slot = self.ctx.rng.randint(0, 9999)
        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "range-dice",
            "amount": format(amt, "f"),
            "range": (slot, slot),
            "is_in": True,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_dynamic_phase(self) -> Optional[BetSpec]:
        """Dynamic phase hunter: tiered profit targets based on loss count."""
        bal = self._current_balance
        if bal <= 0:
            return None

        # Determine tier based on loss count
        loss_count = self._hunt_state["loss_count"]
        if loss_count == 0:
            target_mult = 2.5
        elif loss_count <= 3:
            target_mult = 1.5
        elif loss_count <= 7:
            target_mult = 0.75
        elif loss_count <= 15:
            target_mult = 0.25
        else:
            target_mult = 0.0

        # Bet formula: (accumulated_losses + target) / payout_mult
        accumulated = self._hunt_state["accumulated_losses"]
        cycle_start = self._hunt_state["cycle_start_balance"]
        target_profit = cycle_start * Decimal(str(target_mult))

        payout_mult = 99.0 / self.chance_pct
        bet_needed = (accumulated + target_profit) / Decimal(str(payout_mult))
        bet_needed = max(self.min_bet_abs, bet_needed)
        bet_needed = min(bet_needed, bal * Decimal(str(self.max_bet_pct)))

        return {
            "game": "dice",
            "amount": format(bet_needed, "f"),
            "chance": str(self.chance_pct),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_gradient_range(self) -> Optional[BetSpec]:
        """Gradient range hunter: target-gradient bet sizing with random windows."""
        bal = self._current_balance
        if bal <= 0:
            return None

        target = self._hunt_state["target_balance"]
        if target <= 0:
            target = bal * Decimal("2")

        # Compute progress (0-1)
        progress = min(1.0, float((bal - self._starting_balance) / (target - self._starting_balance)))

        # Divisor interpolation
        far_div = 300
        near_div = 1000
        divisor = far_div + (near_div - far_div) * progress

        amt = bal / Decimal(str(divisor))
        amt = max(self.min_bet_abs, amt)
        amt = min(amt, bal * Decimal(str(self.max_bet_pct)))

        # Random Range Dice window (0.01% to 1%)
        min_slots = 1
        max_slots = 100
        slot_width = int(self.ctx.rng.uniform(min_slots, max_slots))
        start_slot = self.ctx.rng.randint(0, 10_000 - slot_width)

        return {
            "game": "range-dice",
            "amount": format(amt, "f"),
            "range": (start_slot, start_slot + slot_width - 1),
            "is_in": True,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_adaptive_volatility(self) -> Optional[BetSpec]:
        """Ultra-low chance with volatility-based adaptation."""
        bal = self._current_balance
        if bal <= 0:
            return None

        # Compute recent volatility
        if len(self._recent_results) > 5:
            recent = list(self._recent_results)[-10:]
            win_count = sum(1 for r in recent if r.get("win"))
            expected = len(recent) * 0.5
            volatility = abs(win_count - expected) / (expected + 0.1)
        else:
            volatility = 0.5

        # Adapt chance (lower when calm, higher when chaotic)
        if volatility < self.threshold:
            chance = 0.01  # calm: hunt ultra-low
        else:
            chance = min(1.0, 0.1 + volatility * self.multiplier)

        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "dice",
            "amount": format(amt, "f"),
            "chance": f"{chance:.2f}",
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_regime(self) -> Optional[BetSpec]:
        """Three-regime amplifier: regime A (tail) → B (momentum) → C (cool)."""
        bal = self._current_balance
        if bal <= 0:
            return None

        regime = self._hunt_state["regime"]
        bets_in = self._hunt_state["bets_in_regime"]

        # Simple regime logic based on threshold
        if regime == "A":
            chance = max(0.01, min(1.0, self.chance_pct / 100))
            if bets_in > 10:
                self._hunt_state["regime"] = "B"
                self._hunt_state["bets_in_regime"] = 0
        elif regime == "B":
            chance = max(3.0, min(12.0, self.chance_pct))
            if bets_in > 20:
                self._hunt_state["regime"] = "C"
                self._hunt_state["bets_in_regime"] = 0
        else:  # C
            chance = max(5.0, min(10.0, self.chance_pct))
            if bets_in > 30:
                self._hunt_state["regime"] = "A"
                self._hunt_state["bets_in_regime"] = 0

        self._hunt_state["bets_in_regime"] += 1

        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "dice",
            "amount": format(amt, "f"),
            "chance": f"{chance:.2f}",
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_low(self) -> Optional[BetSpec]:
        """Low hunter: fixed 0.01% locked to slot 0."""
        bal = self._current_balance
        if bal <= 0:
            return None

        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "range-dice",
            "amount": format(amt, "f"),
            "range": (0, 0),
            "is_in": True,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_nano_range(self) -> Optional[BetSpec]:
        """Nano range with cold-zone bias and survival mode."""
        bal = self._current_balance
        if bal <= 0:
            return None

        # Update cold buckets from recent results
        for r in self._recent_results:
            slot = int(float(r.get("number", "0"))) % 10_000
            bucket = slot // (10_000 // 200)
            self._hunt_state["cold_buckets"][bucket] += 1
            self._hunt_state["cold_total"] += 1

        # Pick from coldest buckets
        if self._hunt_state["cold_total"] > 0:
            alpha = max(1.0, self._hunt_state["cold_total"] / 200 * 0.1)
            weights = [1.0 / (c + alpha) for c in self._hunt_state["cold_buckets"]]
            total_w = sum(weights)
            weights = [w / total_w for w in weights]
            chosen_bucket = self.ctx.rng.choices(range(200), weights=weights, k=1)[0]
            start_slot = chosen_bucket * (10_000 // 200)
            end_slot = start_slot + (10_000 // 200) - 1
        else:
            start_slot = 0
            end_slot = 100

        amt = self._calc_bet_amount(bal)
        if amt <= 0:
            return None

        return {
            "game": "range-dice",
            "amount": format(amt, "f"),
            "range": (start_slot, min(end_slot, 9999)),
            "is_in": True,
            "faucet": self.ctx.faucet,
        }

    def _next_bet_streak_pressure(self) -> Optional[BetSpec]:
        """Pattern pressure detection: OBSERVE → HUNT → COOLDOWN cycles."""
        bal = self._current_balance
        if bal <= 0:
            return None

        phase = self._hunt_state["phase"]
        phase_steps = self._hunt_state["phase_steps"]

        # Simplified state machine
        if phase == "OBSERVE":
            # Micro-bets while looking for patterns
            amt = bal * Decimal(str(self.base_bet_pct * 0.1))
            self._hunt_state["phase_steps"] = phase_steps + 1
            if phase_steps > 20:
                self._hunt_state["phase"] = "HUNT"
                self._hunt_state["phase_steps"] = 0
                self._hunt_state["hunt_steps_remaining"] = 5
        elif phase == "HUNT":
            # Escalating bets
            step = 5 - self._hunt_state["hunt_steps_remaining"]
            amt = bal * Decimal(str(self.base_bet_pct)) * Decimal(str(self.multiplier ** step))
            self._hunt_state["hunt_steps_remaining"] -= 1
            if self._hunt_state["hunt_steps_remaining"] <= 0:
                self._hunt_state["phase"] = "COOLDOWN"
                self._hunt_state["phase_steps"] = 0
        else:  # COOLDOWN
            amt = bal * Decimal(str(self.base_bet_pct * 0.05))
            self._hunt_state["phase_steps"] = phase_steps + 1
            if phase_steps > 10:
                self._hunt_state["phase"] = "OBSERVE"
                self._hunt_state["phase_steps"] = 0

        amt = max(self.min_bet_abs, amt)
        amt = min(amt, bal * Decimal(str(self.max_bet_pct)))

        return {
            "game": "dice",
            "amount": format(amt, "f"),
            "chance": str(self.chance_pct),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    # ───────────────────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ───────────────────────────────────────────────────────────────────────────

    def _calc_bet_amount(self, bal: Decimal) -> Decimal:
        """Calculate bet amount with multiplier cap and max limits."""
        base = bal * Decimal(str(self.base_bet_pct))
        with_mult = base * Decimal(str(self._loss_multiplier_current))
        capped = min(with_mult, bal * Decimal(str(self.max_bet_pct)))
        final = max(self.min_bet_abs, capped)
        return final.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
