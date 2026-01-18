"""
Streak Multiplier Strategy - Exponential growth on win streaks

Strategy Overview:
- Base bet: balance / 250
- Win chance: 5% (high)
- On win: Increase bet by 240% (multiply by 3.4x)
- On loss: Reset to base bet

This is an aggressive exponential growth strategy that capitalizes on
rare win streaks. With 5% chance, hitting consecutive wins is uncommon,
but the 240% increase compounds rapidly when streaks occur.

Example progression (starting with 1.0 balance):
- Bet 1: 0.004 @ 5% → Win  → Profit: ~0.072
- Bet 2: 0.0136 @ 5% → Win → Profit: ~0.245
- Bet 3: 0.0462 @ 5% → Win → Profit: ~0.832
- Bet 4: 0.157 @ 5% → Win  → Profit: ~2.83
- Any loss: Reset to 0.004

Risk Level: VERY HIGH
- Low win chance (5%)
- Exponential bet growth
- Large drawdown on losses
- Designed for lottery-style wins

Probability Analysis:
- 2-win streak: 0.25% (1 in 400)
- 3-win streak: 0.0125% (1 in 8,000)
- 4-win streak: 0.000625% (1 in 160,000)
"""

from decimal import Decimal
from typing import Any, Dict, Optional
from betbot_strategies.base import BetSpec, BetResult, StrategyContext
from betbot_strategies import register


@register("streak-multiplier")
class StreakMultiplierStrategy:
    """
    Exponential bet growth on win streaks with 5% chance.
    
    Configuration:
    - Base bet: balance / divisor (default 250)
    - Win chance: Fixed 5%
    - Win multiplier: 3.4x (240% increase)
    - Direction: High (bet on high numbers)
    """
    
    @staticmethod
    def schema() -> Dict[str, Any]:
        return {
            "divisor": {
                "type": "int",
                "default": 250,
                "desc": "Balance divisor for base bet (balance/divisor). Higher = smaller bets."
            },
            "chance": {
                "type": "float",
                "default": 5.0,
                "desc": "Win chance percentage (1-98). Default 5% for high risk/reward."
            },
            "win_multiplier": {
                "type": "float",
                "default": 3.4,
                "desc": "Bet multiplier on win (240% increase = 3.4x). Default 3.4."
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet high if True, low if False"
            },
        }
    
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext):
        self.ctx = ctx
        
        # Parameters
        self.divisor = int(params.get("divisor", 250))
        self.chance = Decimal(str(params.get("chance", 5.0)))
        self.win_multiplier = Decimal(str(params.get("win_multiplier", 3.4)))
        self.is_high = bool(params.get("is_high", True))
        
        # State
        self.current_balance = Decimal(ctx.starting_balance)
        self.base_bet = self._calculate_base_bet(self.current_balance)
        self.current_bet = self.base_bet
        self.win_streak = 0
        
        # Statistics
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
        self.max_streak = 0
        self.streak_wins = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # Track streak distribution
        
    def _calculate_base_bet(self, balance: Decimal) -> Decimal:
        """Calculate base bet as balance / divisor."""
        if balance <= Decimal("0"):
            return Decimal("0.00000001")  # Minimum bet
        
        base = balance / Decimal(str(self.divisor))
        return max(base, Decimal("0.00000001"))
    
    def on_session_start(self) -> None:
        """Called when session starts."""
        print("\n" + "="*60)
        print("STREAK MULTIPLIER STRATEGY")
        print("="*60)
        print(f"Base Bet: balance / {self.divisor}")
        print(f"Win Chance: {self.chance}%")
        print(f"Win Multiplier: {self.win_multiplier}x ({(self.win_multiplier - 1) * 100:.0f}% increase)")
        print(f"Direction: {'HIGH' if self.is_high else 'LOW'}")
        print(f"Starting Balance: {self.current_balance}")
        print(f"Initial Base Bet: {self.base_bet}")
        print("\nExpected Payout: ~{:.2f}x per win".format(float(Decimal("99") / self.chance)))
        print("\nStreak Probabilities:")
        prob = float(self.chance / Decimal("100"))
        for i in range(1, 6):
            streak_prob = prob ** i
            print(f"  {i}-win streak: {streak_prob*100:.4f}% (1 in {int(1/streak_prob):,})")
        print("="*60 + "\n")
    
    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet."""
        # Update base bet based on current balance
        self.base_bet = self._calculate_base_bet(self.current_balance)
        
        # Check if we can afford the current bet
        if self.current_bet > self.current_balance:
            # Balance too low for current streak bet, reset
            self.current_bet = self.base_bet
            self.win_streak = 0
        
        # Ensure bet is at least base bet
        if self.current_bet < self.base_bet:
            self.current_bet = self.base_bet
        
        # Cap at balance
        if self.current_bet > self.current_balance:
            if self.current_balance >= self.base_bet:
                self.current_bet = self.current_balance
            else:
                # Balance too low even for base bet
                return None
        
        return {
            "game": "dice",
            "amount": format(self.current_bet, 'f'),
            "chance": format(self.chance, 'f'),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }
    
    def on_bet_result(self, result: BetResult) -> None:
        """Process bet result and update strategy state."""
        self.total_bets += 1
        
        # Update balance
        profit = Decimal(str(result.get("profit", "0")))
        self.current_balance += profit
        
        if result.get("win"):
            # WIN: Increase streak and multiply bet
            self.total_wins += 1
            self.win_streak += 1
            self.max_streak = max(self.max_streak, self.win_streak)
            
            # Track streak distribution (cap at 5)
            streak_key = min(self.win_streak, 5)
            if streak_key in self.streak_wins:
                self.streak_wins[streak_key] += 1
            
            # Calculate next bet: current bet * win_multiplier
            self.current_bet = self.current_bet * self.win_multiplier
            
            # Log win
            payout = Decimal(str(result.get("payout", "0")))
            print(f"[Bet #{self.total_bets}] ✅ WIN (Streak: {self.win_streak})")
            print(f"  Profit: {profit:+.8f} | Balance: {self.current_balance:.8f}")
            print(f"  Next bet: {self.current_bet:.8f} ({self.win_multiplier}x increase)")
            
        else:
            # LOSS: Reset to base bet
            self.total_losses += 1
            
            # Log loss and reset
            print(f"[Bet #{self.total_bets}] ❌ LOSS (Streak broken: {self.win_streak})")
            print(f"  Profit: {profit:+.8f} | Balance: {self.current_balance:.8f}")
            print(f"  Reset to base: {self.base_bet:.8f}")
            
            # Reset
            self.win_streak = 0
            self.current_bet = self.base_bet
    
    def on_session_end(self, stopped_reason: str = "completed") -> None:
        """Called when session ends."""
        print("\n" + "="*60)
        print("STREAK MULTIPLIER STRATEGY - SESSION SUMMARY")
        print("="*60)
        print(f"Total Bets: {self.total_bets}")
        print(f"Wins: {self.total_wins}")
        print(f"Losses: {self.total_losses}")
        if self.total_bets > 0:
            win_rate = (self.total_wins / self.total_bets) * 100
            print(f"Win Rate: {win_rate:.2f}%")
        print(f"\nFinal Balance: {self.current_balance:.8f}")
        print(f"Starting Balance: {self.ctx.starting_balance}")
        
        profit = self.current_balance - Decimal(self.ctx.starting_balance)
        profit_pct = (profit / Decimal(self.ctx.starting_balance)) * 100
        print(f"Profit: {profit:+.8f} ({profit_pct:+.2f}%)")
        
        print(f"\nMax Win Streak: {self.max_streak}")
        print("\nStreak Distribution:")
        for streak in sorted(self.streak_wins.keys()):
            count = self.streak_wins[streak]
            if count > 0:
                label = f"{streak}+ wins" if streak == 5 else f"{streak}-win"
                print(f"  {label}: {count} times")
        print("="*60 + "\n")
