from __future__ import annotations
"""
BlaksRunner 5.0 Strategy - Faithful port from PredictiveRolls (Rust/sushiomsky)

Adaptive chance-based strategy that:
- Tracks a rolling average of the last N winning roll positions to dynamically
  set the win-chance window (higher payout when wins cluster near the edge).
- Auto-tunes the bet size after every outcome to recover accumulated losses
  (spent) while targeting a configurable win multiplier scaled to balance.
- Optionally toggles High/Low direction after an extended loss streak.

Original source: PredictiveRolls-main/src/strategies/blaks_runner.rs
"""
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

# Smallest representable bet (8 decimal places = 1 satoshi)
_SATOSHI = Decimal("0.00000001")


@register("blaks-runner")
class BlaksRunner:
    """
    BlaksRunner 5.0: adaptive win-chance + loss-recovery auto-tuning.

    The rolling average of where recent wins landed sets the next win-chance.
    Bet size is auto-tuned each roll to recover accumulated losses.
    """

    @classmethod
    def name(cls) -> str:
        return "blaks-runner"

    @classmethod
    def describe(cls) -> str:
        return (
            "BlaksRunner 5.0: adaptive win-chance from win-position rolling average "
            "with loss-recovery auto-tuning. Port of PredictiveRolls Rust strategy."
        )

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Large",
            volatility="High",
            time_to_profit="Slow",
            recommended_for="Advanced",
            pros=[
                "Dynamically adjusts win-chance based on where wins actually occur",
                "Auto-tunes bet size to recover losses over time",
                "Win multiplier scales with balance growth",
                "Optional high/low direction toggle prevents bias exploitation",
                "Self-correcting: chance widens when losses exceed statistical expectation",
            ],
            cons=[
                "Complex interaction of many parameters; hard to tune",
                "Requires large bankroll to absorb recovery bets",
                "Low win-chance window means long dry spells are expected",
                "Auto-tune can produce very large bets during deep loss streaks",
                "No hard loss limit built-in; rely on session stop-loss",
            ],
            best_use_case=(
                "Long sessions with a large bankroll where you want an adaptive strategy "
                "that dynamically tracks roll patterns and self-corrects bet sizing."
            ),
            tips=[
                "Start with a tiny base_amount (e.g. 0.00000001)",
                "Set a stop-loss of 20-30% of starting balance",
                "Keep max_bet at 0 (unlimited) unless you know your bankroll limit",
                "house_percent should match the site's actual house edge (DuckDice = 1)",
                "Increase inc_divisor to scale win_mult more conservatively",
                "Enable toggle_high_low only if you suspect directional bias",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {
                "type": "str",
                "default": "0.000001",
                "desc": "Base (minimum) bet amount — set to your coin's minimum bet",
            },
            "base_chance": {
                "type": "float",
                "default": 4.4,
                "desc": "Initial win-chance % after a win (reset value)",
            },
            "chance_inc": {
                "type": "float",
                "default": 0.0001,
                "desc": "Amount to widen win-chance when losses exceed statistical expectation",
            },
            "house_percent": {
                "type": "float",
                "default": 1.0,
                "desc": "House edge % (DuckDice = 1, others may differ)",
            },
            "max_win_mult": {
                "type": "int",
                "default": 512,
                "desc": "Maximum win multiplier cap (0 = unlimited)",
            },
            "inc_divisor": {
                "type": "float",
                "default": 10000000.0,
                "desc": "Divides (balance_in_satoshis) to derive win_mult; larger = slower growth",
            },
            "chance_max": {
                "type": "float",
                "default": 1.5,
                "desc": "Max chance = base_chance * chance_max (caps rolling-average chance)",
            },
            "average_max": {
                "type": "int",
                "default": 8,
                "desc": "Rolling window size for win-position average",
            },
            "toggle_high_low": {
                "type": "bool",
                "default": False,
                "desc": "Toggle bet direction (high/low) when expected losses are exhausted",
            },
            "bet_high": {
                "type": "bool",
                "default": False,
                "desc": "Initial bet direction (True = High, False = Low)",
            },
            "max_bet": {
                "type": "float",
                "default": 0.0,
                "desc": "Absolute maximum bet amount (0 = unlimited)",
            },
            "site_max_profit": {
                "type": "float",
                "default": 0.0,
                "desc": "Site maximum profit per bet (0 = unlimited)",
            },
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx

        # --- configurable parameters ---
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.base_chance: float = float(params.get("base_chance", 4.4))
        self.chance_inc: float = float(params.get("chance_inc", 0.0001))
        self.house_percent: float = float(params.get("house_percent", 1.0))
        self.max_win_mult: int = int(params.get("max_win_mult", 512))
        self.inc_divisor: float = float(params.get("inc_divisor", 10_000_000.0))
        self.chance_max: float = float(params.get("chance_max", 1.5))
        self.average_max: int = int(params.get("average_max", 8))
        self.toggle_high_low: bool = bool(params.get("toggle_high_low", False))
        self.bet_high: bool = bool(params.get("bet_high", False))
        self.max_bet: float = float(params.get("max_bet", 0.0))
        self.site_max_profit: float = float(params.get("site_max_profit", 0.0))

        # --- runtime state ---
        self._reset_state()

    def _reset_state(self) -> None:
        """(Re)initialize all runtime state to defaults."""
        self.chance: float = 1.0                        # current win-chance %
        self.old_base_chance: float = 0.0               # base_chance captured on first bet
        self._next_bet_d: Decimal = self.base_amount
        self._base_bet_d: Decimal = self.base_amount

        self.spent: float = 0.0                         # accumulated losses to recover
        self.loss_count: int = 0
        self.step_count: int = 0
        self.high_low_loss_count: int = 0
        self.roll_count: int = 0

        self.win_mult: float = 1.0
        self.temp_win_mult: float = 1.0

        self.high_low_average: List[float] = [0.0] * self.average_max
        self.average_count: int = 0                     # write index (wraps)

        self.total_profit: float = 0.0
        self.profit: float = 0.0

    def on_session_start(self) -> None:
        self._reset_state()

    def on_session_end(self, reason: str) -> None:
        pass

    # ------------------------------------------------------------------
    # Core logic helpers
    # ------------------------------------------------------------------

    def _calc_chance(self, win: bool, number: int) -> None:
        """Update self.chance from outcome.

        On win  – derive chance from the rolled number position (rolling avg).
        On loss – widen chance slightly if losses exceed statistical expectation.
        """
        if self.old_base_chance == 0.0:
            self.old_base_chance = self.base_chance

        if win:
            rolled_number = number // 100          # map 0-9999 → 0-99
            target = (100 - rolled_number) if rolled_number >= 50 else rolled_number
            # target = distance from edge (0-50); lower = tighter bet window

            self.high_low_average[self.average_count] = float(target)
            self.average_count = (self.average_count + 1) % self.average_max

            temp_average = sum(self.high_low_average) / self.average_max
            self.chance = max(temp_average, 0.01)  # floor: never allow chance=0

            cap = self.old_base_chance * self.chance_max
            if self.chance > cap:
                self.chance = cap
        else:
            # expected payout multiplier at current chance
            expected_wins = (100.0 - (100.0 * (self.house_percent / 100.0))) / max(self.chance, 0.001)
            if self.loss_count > expected_wins:
                self.chance += self.chance_inc

    def _auto_tune(self) -> None:
        """Adjust self.next_bet to recover spent losses and hit win target."""
        chance = max(self.chance, 0.01)  # guard against division by zero

        # Profit if we bet base_bet and win
        win_amount = ((100.0 - self.house_percent) / chance) * float(self._base_bet_d)

        # Expected cost factor per bet cycle (~1 + 2*chance/100)
        temp_calc = 1.0 + (chance / 100.0) * (
            (100.0 - self.house_percent) / ((100.0 - self.house_percent) / 2.0)
        )

        needed = (
            win_amount * self.temp_win_mult
            + float(self._next_bet_d) * temp_calc
            + self.spent
        )

        next_mult = needed / win_amount if win_amount > 0 else 1.0
        if next_mult < 1.0:
            next_mult = 1.0

        next_bet_f = float(self._base_bet_d) * next_mult

        # Apply site max-profit cap
        if self.site_max_profit > 0:
            max_for_site = self.site_max_profit / (win_amount / float(self._base_bet_d))
            if next_bet_f > max_for_site:
                next_bet_f = max_for_site

        # Apply absolute max-bet cap
        if self.max_bet > 0 and next_bet_f > self.max_bet:
            next_bet_f = self.max_bet

        # Floor at base amount
        next_bet_f = max(next_bet_f, float(self.base_amount))

        self._next_bet_d = Decimal(str(next_bet_f)).quantize(_SATOSHI, rounding=ROUND_DOWN)

    # ------------------------------------------------------------------
    # Strategy interface
    # ------------------------------------------------------------------

    def next_bet(self) -> Optional[BetSpec]:
        if self.old_base_chance == 0.0:
            self.old_base_chance = self.base_chance

        self._auto_tune()

        chance = max(self.chance, 0.01)

        return {
            "game": "dice",
            "amount": format(self._next_bet_d, "f"),
            "chance": f"{chance:.4f}",
            "is_high": self.bet_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        win = bool(result.get("win"))
        number = int(result.get("number", 5000))
        profit_d = Decimal(str(result.get("profit", "0")))
        self.roll_count += 1
        self.ctx.recent_results.append(result)

        if win:
            win_amount = float(profit_d)  # positive net profit
            self.total_profit += win_amount
            self.profit += win_amount

            # Reset on win
            self.chance = self.base_chance
            self.loss_count = 0
            self.step_count = 0
            self.high_low_loss_count = 0

            # Recover spent losses
            self.spent = max(0.0, self.spent - win_amount)

            # Scale win_mult to current balance
            balance_str = result.get("balance", self.ctx.starting_balance)
            balance_f = float(Decimal(str(balance_str)))
            # Scale win_mult to current balance as a multiple of base_bet
            # (currency-agnostic: works for BTC, DOGE, ETH, etc.)
            # For BTC: (1 BTC / 1e-8) / 10M = 1e8/1e7 = 10  → same as original
            base_bet_f = float(self._base_bet_d) if float(self._base_bet_d) > 0 else 1e-8
            temp_mult = max(1.0, (balance_f / base_bet_f) / self.inc_divisor)
            if self.max_win_mult > 0:
                temp_mult = min(temp_mult, float(self.max_win_mult))
            self.win_mult = temp_mult
            self.temp_win_mult = self.win_mult

            # Reset bet to base; recalc chance from roll position; auto-tune
            self._next_bet_d = self._base_bet_d
            self._calc_chance(True, number)
            self._auto_tune()

        else:
            loss_amount = abs(float(profit_d))  # positive loss magnitude
            self.loss_count += 1
            self.high_low_loss_count += 1
            self.spent += loss_amount
            self.profit -= loss_amount
            self.profit = max(0.0, self.profit)

            # Toggle direction or reduce win_mult when losses exceed expectation
            expected_wins = (
                (100.0 - (100.0 * (self.house_percent / 100.0)))
                / max(self.chance, 0.01)
            )
            if self.high_low_loss_count >= expected_wins:
                if self.toggle_high_low:
                    self.bet_high = not self.bet_high

                if self.loss_count >= expected_wins * 25 and self.temp_win_mult > 1.0:
                    self.temp_win_mult = 1.0

                self.high_low_loss_count = 0

            self._calc_chance(False, number)
            self._auto_tune()
