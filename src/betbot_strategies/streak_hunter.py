from __future__ import annotations
"""
Streak Hunter Strategy - Hunt 14% chance with compounding streak progression

Strategy:
- Target: 14% win chance (~7x payout)
- Base bet: max(min_bet, balance/300)
- On first win: Bet 200% of previous bet (2x last bet)
- On second win: Bet 180% of previous bet (1.8x last bet)
- On third win: Bet 160% of previous bet (1.6x last bet)
- Pattern continues: 140%, 120%, 100%, 80%... of previous bet
- Reset to base bet on any loss
- Optional: Lottery bets (0.01-4% chance) when streak = 0 for huge payouts

Example with base bet = 1:
- Bet 1 (streak 0): 1.0 → WIN (streak = 1)
- Bet 2 (streak 1): 2.0 (200% of 1.0) → WIN (streak = 2)
- Bet 3 (streak 2): 3.6 (180% of 2.0) → WIN (streak = 3)
- Bet 4 (streak 3): 5.76 (160% of 3.6) → WIN (streak = 4)
- Bet 5 (streak 4): 8.06 (140% of 5.76) → WIN (streak = 5)
- Bet 6 (streak 5): 9.67 (120% of 8.06) → LOSE (reset)
- Bet 7 (streak 0): 1.0 (back to base)

With lottery enabled (every 10 bets, only when streak = 0):
- Bet 10: 1.0 @ 2.5% chance (lottery) → LOSE
- Bet 11: 1.0 (continue normal betting)
- Bet 20: 1.0 @ 0.5% chance (lottery) → WIN +200x! 💰
Note: Lottery bets ONLY happen when streak = 0 to avoid disrupting progression!
"""
from decimal import Decimal
from typing import Any, Dict, Optional

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("streak-hunter")
class StreakHunter:
    """Hunt winning streaks at 14% chance with decreasing multipliers."""

    @classmethod
    def name(cls) -> str:
        return "streak-hunter"

    @classmethod
    def describe(cls) -> str:
        return "Hunt 14% streaks with compounding bets: 200%→180%→160% of previous bet"

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Medium-High",
            bankroll_required="Medium",
            volatility="High",
            time_to_profit="Variable",
            recommended_for="Intermediate",
            pros=[
                "Capitalizes on lucky winning streaks",
                "Conservative base bet (balance/300)",
                "Decreasing multipliers reduce risk over time",
                "Resets quickly on losses to preserve capital",
                "Exciting gameplay with potential big wins",
                "Works well at 14% chance (7x payout)"
            ],
            cons=[
                "Relies on getting winning streaks",
                "Single loss resets all progress",
                "High variance at 14% win chance",
                "Multipliers decrease so growth slows",
                "Can be frustrating with bad luck",
                "Requires patience during dry spells"
            ],
            best_use_case="Medium sessions where you want to hunt lucky streaks with managed risk. The decreasing multipliers prevent exponential growth while still capitalizing on wins.",
            tips=[
                "Set strict stop-loss (recommend -20% to -30%)",
                "Use take-profit at +50% to +100%",
                "Best with medium bankroll (100-500 units)",
                "Consider max_bets limit to prevent extended sessions",
                "Track your streak lengths - rare to hit 5+",
                "The 14% chance gives ~7x payout, perfect for this strategy",
                "If you hit 3-win streak, consider taking profit"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "chance": {
                "type": "str",
                "default": "14",
                "desc": "Win chance percent (default 14% for ~7x payout)"
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet on High (True) or Low (False)"
            },
            "min_bet": {
                "type": "str",
                "default": "0.00000100",
                "desc": "Minimum bet amount (fallback if balance/300 is lower)"
            },
            "balance_divisor": {
                "type": "int",
                "default": 300,
                "desc": "Divide balance by this for base bet (default 300)"
            },
            "first_multiplier": {
                "type": "float",
                "default": 2.0,
                "desc": "Multiplier on first win (200% = 2.0)"
            },
            "second_multiplier": {
                "type": "float",
                "default": 1.8,
                "desc": "Multiplier on second win (180% = 1.8)"
            },
            "third_multiplier": {
                "type": "float",
                "default": 1.6,
                "desc": "Multiplier on third win (160% = 1.6)"
            },
            "multiplier_decrease": {
                "type": "float",
                "default": 0.2,
                "desc": "Decrease amount for each subsequent win (0.2 = 20%)"
            },
            "min_multiplier": {
                "type": "float",
                "default": 0.5,
                "desc": "Minimum multiplier (stops decreasing at this value)"
            },
            "lottery_enabled": {
                "type": "bool",
                "default": False,
                "desc": "Enable occasional low-chance 'lottery' bets"
            },
            "lottery_frequency": {
                "type": "int",
                "default": 10,
                "desc": "Place lottery bet every N bets (default 10)"
            },
            "lottery_chance_min": {
                "type": "float",
                "default": 0.01,
                "desc": "Minimum lottery win chance % (default 0.01%)"
            },
            "lottery_chance_max": {
                "type": "float",
                "default": 4.0,
                "desc": "Maximum lottery win chance % (default 4%)"
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.chance = str(params.get("chance", "14"))
        self.is_high = bool(params.get("is_high", True))
        self.min_bet = Decimal(str(params.get("min_bet", "0.00000100")))
        self.balance_divisor = int(params.get("balance_divisor", 300))
        self.first_multiplier = float(params.get("first_multiplier", 2.0))
        self.second_multiplier = float(params.get("second_multiplier", 1.8))
        self.third_multiplier = float(params.get("third_multiplier", 1.6))
        self.multiplier_decrease = float(params.get("multiplier_decrease", 0.2))
        self.min_multiplier = float(params.get("min_multiplier", 0.5))
        
        # Lottery settings
        self.lottery_enabled = bool(params.get("lottery_enabled", False))
        self.lottery_frequency = int(params.get("lottery_frequency", 10))
        self.lottery_chance_min = float(params.get("lottery_chance_min", 0.01))
        self.lottery_chance_max = float(params.get("lottery_chance_max", 4.0))

        # State
        self._win_streak = 0
        self._last_profit = Decimal("0")
        self._last_bet_amount = Decimal("0")  # Track previous bet for progression
        self._total_bets = 0
        self._total_wins = 0
        self._max_streak = 0
        self._current_base = self.min_bet
        self._lottery_wins = 0
        self._lottery_attempts = 0

    def on_session_start(self) -> None:
        """Called when betting session starts"""
        self._win_streak = 0
        self._last_profit = Decimal("0")
        self._last_bet_amount = Decimal("0")
        self._total_bets = 0
        self._total_wins = 0
        self._max_streak = 0
        self._current_base = self._calculate_base_bet()
        self._lottery_wins = 0
        self._lottery_attempts = 0
        
        print(f"\n🎯 Streak Hunter Strategy Started")
        print(f"   Target chance: {self.chance}%")
        print(f"   Base bet: {self._current_base:.8f}")
        print(f"   Win multipliers: {self.first_multiplier}x → {self.second_multiplier}x → {self.third_multiplier}x → ...")
        if self.lottery_enabled:
            print(f"   🎰 Lottery: Every {self.lottery_frequency} bets @ {self.lottery_chance_min}-{self.lottery_chance_max}%")
        print(f"   Reset on: Any loss\n")

    def _calculate_base_bet(self) -> Decimal:
        """Calculate base bet: max(min_bet, balance/divisor)"""
        current_balance = Decimal(self.ctx.current_balance_str())
        balance_based = current_balance / Decimal(str(self.balance_divisor))
        return max(self.min_bet, balance_based)

    def _get_multiplier_for_streak(self, streak: int) -> float:
        """Get multiplier based on current win streak"""
        if streak == 0:
            return 1.0
        elif streak == 1:
            return self.first_multiplier
        elif streak == 2:
            return self.second_multiplier
        elif streak == 3:
            return self.third_multiplier
        else:
            # After 3rd win, decrease by multiplier_decrease each time
            # 4th: 1.6 - 0.2 = 1.4
            # 5th: 1.4 - 0.2 = 1.2
            # 6th: 1.2 - 0.2 = 1.0
            # 7th: 1.0 - 0.2 = 0.8
            # etc., but floor at min_multiplier
            additional_wins = streak - 3
            mult = self.third_multiplier - (self.multiplier_decrease * additional_wins)
            return max(mult, self.min_multiplier)

    def _calculate_bet_amount(self) -> Decimal:
        """Calculate bet amount based on streak"""
        if self._win_streak == 0:
            # First bet or after loss - use base bet
            return self._current_base
        else:
            # On a streak - multiply PREVIOUS BET by streak multiplier
            multiplier = self._get_multiplier_for_streak(self._win_streak)
            
            # Use last bet amount if we have one, otherwise base
            previous_bet = self._last_bet_amount if self._last_bet_amount > 0 else self._current_base
            amount = previous_bet * Decimal(str(multiplier))
            
            return amount

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet specification"""
        self._total_bets += 1
        
        # Recalculate base bet periodically (every 10 bets)
        if self._total_bets % 10 == 0:
            self._current_base = self._calculate_base_bet()
        
        # Check if this should be a lottery bet (ONLY when not on a streak!)
        is_lottery = False
        if self.lottery_enabled and self._win_streak == 0 and self._total_bets % self.lottery_frequency == 0:
            is_lottery = True
            self._lottery_attempts += 1
            
            # Random chance between min and max
            lottery_chance = self.ctx.rng.uniform(self.lottery_chance_min, self.lottery_chance_max)
            # Round to 2 decimal places for API compatibility
            lottery_chance = round(lottery_chance, 2)
            amount = self._current_base
            
            # Calculate potential payout
            payout_mult = 99.0 / lottery_chance if lottery_chance > 0 else 0
            print(f"\n🎰 LOTTERY BET #{self._lottery_attempts}! Chance: {lottery_chance:.2f}% (up to {payout_mult:.0f}x payout!)")
            
            # Store this bet amount
            self._last_bet_amount = amount
            
            return {
                "game": "dice",
                "amount": format(amount, 'f'),
                "chance": f"{lottery_chance:.2f}",  # Format to exactly 2 decimal places
                "is_high": self.is_high,
                "faucet": self.ctx.faucet,
            }
        
        # Normal streak bet
        amount = self._calculate_bet_amount()
        
        # Store this bet amount for next progression calculation
        self._last_bet_amount = amount
        
        # Log streak info periodically
        if self._win_streak > 0 and self._total_bets % 5 == 0:
            mult = self._get_multiplier_for_streak(self._win_streak)
            print(f"🔥 On {self._win_streak}-win streak! Next multiplier: {mult:.1f}x")
        
        return {
            "game": "dice",
            "amount": format(amount, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        """Handle bet result and update strategy state"""
        self.ctx.recent_results.append(result)
        
        win = result.get('win', False)
        profit = Decimal(str(result.get('profit', '0')))
        chance_str = str(result.get('chance', '0'))
        
        # Check if this was a lottery bet (very low chance)
        try:
            chance = float(chance_str)
            is_lottery = chance < 5.0  # Anything under 5% is considered lottery
        except:
            is_lottery = False
        
        if win:
            # Check for lottery win
            if is_lottery:
                self._lottery_wins += 1
                payout = float(profit) / float(result.get('amount', '1'))
                print(f"💰 LOTTERY WIN! {chance:.2f}% hit! Profit: {profit:.8f} ({payout:.1f}x payout)")
                # Don't count lottery wins in streak
            else:
                self._win_streak += 1
                self._last_profit = profit
                
                # Track max streak
                if self._win_streak > self._max_streak:
                    self._max_streak = self._win_streak
                
                # Celebrate milestones
                if self._win_streak == 3:
                    print(f"🎉 3-win streak! Profit multiplier now {self._get_multiplier_for_streak(3):.1f}x")
                elif self._win_streak == 5:
                    print(f"🚀 5-win streak! Amazing! Multiplier: {self._get_multiplier_for_streak(5):.1f}x")
                elif self._win_streak >= 7:
                    print(f"💎 {self._win_streak}-win streak! Legendary! Multiplier: {self._get_multiplier_for_streak(self._win_streak):.1f}x")
            
            self._total_wins += 1
        else:
            # Loss
            if is_lottery:
                # Lottery loss doesn't break streak
                pass
            else:
                # Normal bet loss - reset everything
                if self._win_streak > 0:
                    print(f"❌ Streak ended at {self._win_streak} wins. Resetting to base bet.")
                
                self._win_streak = 0
                self._last_profit = Decimal("0")
                self._last_bet_amount = Decimal("0")  # Reset bet tracking

    def on_session_end(self, reason: str) -> None:
        """Called when betting session ends"""
        if self._total_bets > 0:
            win_rate = self._total_wins / self._total_bets if self._total_bets > 0 else 0
            
            print(f"\n🎯 Streak Hunter Session Summary:")
            print(f"   Total bets: {self._total_bets}")
            print(f"   Wins: {self._total_wins}")
            print(f"   Win rate: {win_rate:.2%}")
            print(f"   Max streak achieved: {self._max_streak}")
            print(f"   Final streak: {self._win_streak}")
            
            if self.lottery_enabled:
                lottery_win_rate = self._lottery_wins / self._lottery_attempts if self._lottery_attempts > 0 else 0
                print(f"\n   🎰 Lottery Stats:")
                print(f"   Attempts: {self._lottery_attempts}")
                print(f"   Wins: {self._lottery_wins}")
                if self._lottery_wins > 0:
                    print(f"   🎉 You hit {self._lottery_wins} lottery win(s)!")
                print(f"   Hit rate: {lottery_win_rate:.2%}")
            
            print(f"\n   Stop reason: {reason}")
            
            if self._max_streak >= 5:
                print(f"   🏆 Impressive! You hit a {self._max_streak}-win streak!")
            elif self._max_streak >= 3:
                print(f"   ✨ Nice! You got a {self._max_streak}-win streak!")
            else:
                print(f"   💡 Tip: 14% chance means ~1 in 7 bets win. Keep trying!")
