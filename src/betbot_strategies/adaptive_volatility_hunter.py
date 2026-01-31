from __future__ import annotations
"""
Adaptive Volatility Hunter Strategy

Concept:
- Extremely low chance hunting (0.01% to 1.00%)
- Chance adapts with RNG volatility:
    * Calm RNG     -> lower chance (bigger multiplier)
    * Chaotic RNG  -> higher chance (survive droughts)
- Bet size also adapts inversely to volatility
- Cooldown periods after profit locks
- Emergency brake on extreme loss streaks

Volatility combines:
- Win/loss imbalance from recent results
- Current loss streak pressure
Output:
  0.0 = calm / predictable
  1.0 = chaotic / dangerous
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("adaptive-volatility-hunter")
class AdaptiveVolatilityHunter:
    """Hunt ultra-low chances with adaptive volatility-based adjustments."""

    @classmethod
    def name(cls) -> str:
        return "adaptive-volatility-hunter"

    @classmethod
    def describe(cls) -> str:
        return "Ultra-low chance hunting (0.01%-1%) with volatility-adaptive bet sizing and chance selection"

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very High",
            bankroll_required="Large",
            volatility="Extreme",
            time_to_profit="Variable",
            recommended_for="Advanced",
            pros=[
                "Adapts to RNG volatility in real-time",
                "Extremely high payouts (100x to 10000x)",
                "Automatic cooldown after profit locks",
                "Emergency brake prevents catastrophic losses",
                "Conservative bet sizes (0.025% to 1%)",
                "Survives long droughts by increasing chance",
                "Hunt bigger multipliers during calm periods"
            ],
            cons=[
                "Extremely high variance",
                "Can go 1000+ bets without wins",
                "Requires large bankroll for sustainability",
                "Profit is rare but massive",
                "Psychologically challenging",
                "Long losing streaks are expected",
                "Not suitable for impatient players"
            ],
            best_use_case="Advanced players with large bankrolls hunting life-changing multipliers. Best used with strict stop-loss and patience for rare but massive wins.",
            tips=[
                "Set STRICT stop-loss (-10% to -20% max)",
                "Use aggressive take-profit (+50% to +200%)",
                "Requires 500+ unit bankroll minimum",
                "Expect 500-2000 bet sessions for wins",
                "Don't panic during long droughts - it's expected",
                "Consider max_bets limit (1000-5000)",
                "Volatility window of 45 bets is optimal",
                "Profit lock at $0.30 triggers safety cooldown",
                "Emergency brake at volatility >0.9 + 7 loss streak"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "min_chance": {
                "type": "float",
                "default": 0.01,
                "desc": "Absolute minimum chance % (0.01% = 10000x multiplier)"
            },
            "max_chance": {
                "type": "float",
                "default": 1.00,
                "desc": "Absolute maximum chance % (1% = 99x multiplier)"
            },
            "base_chance": {
                "type": "float",
                "default": 0.05,
                "desc": "Neutral midpoint bias for chance selection"
            },
            "min_bet_percent": {
                "type": "float",
                "default": 0.00025,
                "desc": "Minimum bet as % of balance (0.025%)"
            },
            "base_bet_percent": {
                "type": "float",
                "default": 0.0010,
                "desc": "Normal bet as % of balance (0.1%)"
            },
            "max_bet_percent": {
                "type": "float",
                "default": 0.01,
                "desc": "Maximum bet as % of balance (1% - only in calm RNG)"
            },
            "volatility_window": {
                "type": "int",
                "default": 45,
                "desc": "Number of bets analyzed for volatility calculation"
            },
            "loss_streak_weight": {
                "type": "float",
                "default": 2.0,
                "desc": "Extra danger weighting for loss streaks"
            },
            "cooldown_bets": {
                "type": "int",
                "default": 30,
                "desc": "Forced safety period after profit lock"
            },
            "profit_lock_usd": {
                "type": "float",
                "default": 0.30,
                "desc": "Reset aggression after this much profit"
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet on High (True) or Low (False)"
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        
        # Configuration
        self.min_chance = float(params.get("min_chance", 0.01))
        self.max_chance = float(params.get("max_chance", 1.00))
        self.base_chance = float(params.get("base_chance", 0.05))
        self.min_bet_percent = float(params.get("min_bet_percent", 0.00025))
        self.base_bet_percent = float(params.get("base_bet_percent", 0.0010))
        self.max_bet_percent = float(params.get("max_bet_percent", 0.01))
        self.volatility_window = int(params.get("volatility_window", 45))
        self.loss_streak_weight = float(params.get("loss_streak_weight", 2.0))
        self.cooldown_bets = int(params.get("cooldown_bets", 30))
        self.profit_lock_usd = float(params.get("profit_lock_usd", 0.30))
        self.is_high = bool(params.get("is_high", True))
        
        # State
        self._results = []  # 1 = win, 0 = loss
        self._loss_streak = 0
        self._cooldown_counter = 0
        self._last_balance = Decimal("0")
        self._session_profit = Decimal("0")
        self._total_bets = 0
        self._total_wins = 0
        self._max_loss_streak = 0
        self._current_volatility = 0.5

    def on_session_start(self) -> None:
        """Called when betting session starts"""
        self._results = []
        self._loss_streak = 0
        self._cooldown_counter = 0
        self._last_balance = Decimal(self.ctx.starting_balance)
        self._session_profit = Decimal("0")
        self._total_bets = 0
        self._total_wins = 0
        self._max_loss_streak = 0
        self._current_volatility = 0.5
        
        print(f"\n🎯 Adaptive Volatility Hunter Started")
        print(f"   Chance range: {self.min_chance}% ↔ {self.max_chance}%")
        print(f"   Bet range: {self.min_bet_percent*100:.3f}% ↔ {self.max_bet_percent*100:.1f}% of balance")
        print(f"   Volatility window: {self.volatility_window} bets")
        print(f"   Profit lock: ${self.profit_lock_usd:.2f} triggers {self.cooldown_bets}-bet cooldown")
        print(f"   Strategy: Calm RNG → Lower chance (bigger wins)")
        print(f"            Chaos RNG → Higher chance (survive droughts)\n")

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp value between min and max"""
        return max(min_val, min(max_val, value))

    def _push_result(self, win: bool) -> None:
        """Add result to history, maintaining window size"""
        self._results.append(1 if win else 0)
        if len(self._results) > self.volatility_window:
            self._results.pop(0)

    def _calc_volatility(self) -> float:
        """
        Calculate RNG volatility from recent results.
        
        Combines:
        - Win/loss imbalance (deviation from expected 50/50)
        - Current loss streak pressure
        
        Returns:
            0.0 = calm/predictable
            1.0 = chaotic/dangerous
        """
        if len(self._results) < 12:
            return 0.5  # Neutral when insufficient data
        
        # Calculate win ratio
        wins = sum(self._results)
        win_ratio = wins / len(self._results)
        
        # Distance from randomness center (0.5)
        chaos = abs(0.5 - win_ratio) * 2
        
        # Loss streak amplification
        loss_pressure = self._clamp(
            self._loss_streak / (len(self._results) / 2),
            0.0,
            1.0
        )
        
        # Combine chaos and loss pressure
        volatility = self._clamp(
            chaos + (loss_pressure * self.loss_streak_weight),
            0.0,
            1.0
        )
        
        return volatility

    def _calc_adaptive_bet(self, volatility: float) -> Decimal:
        """
        Calculate bet size inversely to volatility.
        
        Calm RNG  -> bet closer to max_bet_percent
        Chaos     -> bet closer to min_bet_percent
        """
        bet_percent = self.max_bet_percent - (
            volatility * (self.max_bet_percent - self.min_bet_percent)
        )
        
        bet_percent = self._clamp(
            bet_percent,
            self.min_bet_percent,
            self.max_bet_percent
        )
        
        current_balance = Decimal(self.ctx.current_balance_str())
        bet = current_balance * Decimal(str(bet_percent))
        
        # Ensure minimum bet
        if bet < Decimal("0.00000001"):
            bet = Decimal("0.00000001")
        
        return bet

    def _calc_adaptive_chance(self, volatility: float) -> float:
        """
        Calculate win chance based on volatility.
        
        Calm RNG  -> hunt deeper (lower chance = bigger multiplier)
        Chaos     -> raise chance to survive
        """
        chance = self.max_chance - (
            volatility * (self.max_chance - self.min_chance)
        )
        
        return self._clamp(chance, self.min_chance, self.max_chance)

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet specification"""
        self._total_bets += 1
        
        # Track session profit
        current_balance = Decimal(self.ctx.current_balance_str())
        self._session_profit = current_balance - self._last_balance
        self._last_balance = current_balance
        
        # Profit lock: force cooldown after good luck
        if float(self._session_profit) >= self.profit_lock_usd:
            self._cooldown_counter = self.cooldown_bets
            self._loss_streak = 0
            self._results = []
            print(f"💰 PROFIT LOCK! +${float(self._session_profit):.2f} → {self.cooldown_bets}-bet cooldown")
        
        # Cooldown mode: ultra safe probing
        if self._cooldown_counter > 0:
            self._cooldown_counter -= 1
            chance = self.max_chance
            current_balance = Decimal(self.ctx.current_balance_str())
            bet_amount = current_balance * Decimal(str(self.min_bet_percent))
            
            if self._cooldown_counter % 10 == 0 and self._cooldown_counter > 0:
                print(f"🛡️  Cooldown: {self._cooldown_counter} bets remaining")
            elif self._cooldown_counter == 0:
                print(f"✅ Cooldown complete - resuming normal operation")
                # Reset loss streak to prevent immediate re-trigger
                self._loss_streak = 0
            
            return BetSpec(
                game="dice",
                amount=str(bet_amount),
                chance=f"{chance:.2f}",
                is_high=self.is_high
            )
        
        # Calculate volatility
        volatility = self._calc_volatility()
        self._current_volatility = volatility
        
        # Apply adaptive logic
        chance = self._calc_adaptive_chance(volatility)
        bet_amount = self._calc_adaptive_bet(volatility)
        
        # Status updates every 50 bets
        if self._total_bets % 50 == 0:
            multiplier = 98.0 / chance
            print(f"📊 Bet #{self._total_bets} | Volatility: {volatility:.2f} | "
                  f"Chance: {chance:.2f}% ({multiplier:.0f}x) | "
                  f"Bet: {float(bet_amount):.8f} ({bet_amount/current_balance*100:.3f}%)")
        
        return BetSpec(
            game="dice",
            amount=str(bet_amount),
            chance=f"{chance:.2f}",
            is_high=self.is_high
        )

    def on_bet_result(self, result: BetResult) -> None:
        """Process bet result and update state"""
        win = result.get("win", False)
        
        # Update results history
        self._push_result(win)
        
        if win:
            self._total_wins += 1
            self._loss_streak = 0
            
            profit = Decimal(result.get("profit", "0"))
            if profit > 0:
                multiplier = 98.0 / float(result.get("chance", "1"))
                print(f"✅ WIN! +{float(profit):.8f} @ {multiplier:.0f}x | "
                      f"Balance: {result.get('balance', '0')}")
        else:
            self._loss_streak += 1
            if self._loss_streak > self._max_loss_streak:
                self._max_loss_streak = self._loss_streak
            
            # Emergency brake (only if not already in cooldown)
            if self._cooldown_counter == 0 and self._current_volatility > 0.9 and self._loss_streak >= 7:
                self._cooldown_counter = self.cooldown_bets
                print(f"🚨 EMERGENCY BRAKE! Volatility {self._current_volatility:.2f} + "
                      f"{self._loss_streak} loss streak → {self.cooldown_bets}-bet cooldown")

    def on_session_end(self, reason: str) -> None:
        """Called when betting session ends"""
        print(f"\n{'='*60}")
        print(f"🏁 Adaptive Volatility Hunter Session Complete")
        print(f"{'='*60}")
        print(f"Reason: {reason}")
        print(f"Total bets: {self._total_bets}")
        print(f"Total wins: {self._total_wins}")
        if self._total_bets > 0:
            win_rate = (self._total_wins / self._total_bets) * 100
            print(f"Win rate: {win_rate:.2f}%")
        print(f"Max loss streak: {self._max_loss_streak}")
        print(f"Final volatility: {self._current_volatility:.2f}")
        print(f"Session profit: {float(self._session_profit):.8f}")
        print(f"{'='*60}\n")
