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

Lottery Bets (Optional):
- Every N bets a random low-chance "lottery" bet is placed instead
- Win chance: random between lottery_min_chance% (x) and lottery_max_chance% (y) each bet
- Amount: lottery_bet_pct% of current balance (fixed %)
- Win streak state is preserved through lottery bets
"""

import random
import logging
from decimal import Decimal
from typing import Any, Dict, Optional
from .base import BetSpec, BetResult, StrategyContext
from . import register

logger = logging.getLogger(__name__)


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
                "default": 300,
                "desc": "Balance divisor for base bet (balance/divisor). Higher = smaller bets."
            },
            "chance": {
                "type": "float",
                "default": 8.0,
                "desc": "Win chance percentage (1-98). Default 8% balances risk/reward."
            },
            "win_multiplier": {
                "type": "float",
                "default": 2.5,
                "desc": "Bet multiplier on win (150% increase = 2.5x). Default 2.5."
            },
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet high if True, low if False"
            },
            # Lottery bet parameters
            "lottery_enabled": {
                "type": "bool",
                "default": False,
                "desc": "Enable periodic lottery bets (random low-chance bets)."
            },
            "lottery_interval": {
                "type": "int",
                "default": 10,
                "desc": "Place a lottery bet every N bets (z). E.g. 10 = every 10th bet."
            },
            "lottery_min_chance": {
                "type": "float",
                "default": 0.1,
                "desc": "Minimum win chance for lottery bets (x%). Low = bigger payout. E.g. 0.1 = 0.1%."
            },
            "lottery_max_chance": {
                "type": "float",
                "default": 1.0,
                "desc": "Maximum win chance for lottery bets (y%). A random chance in [x, y] is picked each time."
            },
            "lottery_bet_pct": {
                "type": "float",
                "default": 1.0,
                "desc": "Lottery bet size as % of current balance. E.g. 1.0 = 1% of balance."
            },
        }
    
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext):
        self.ctx = ctx
        
        # Parameters
        self.divisor = int(params.get("divisor", 250))
        self.chance = Decimal(str(params.get("chance", 5.0)))
        self.win_multiplier = Decimal(str(params.get("win_multiplier", 3.4)))
        self.is_high = bool(params.get("is_high", True))
        
        # Lottery parameters
        self.lottery_enabled = bool(params.get("lottery_enabled", False))
        self.lottery_interval = int(params.get("lottery_interval", 10))
        self.lottery_min_chance = Decimal(str(params.get("lottery_min_chance", 0.1)))
        self.lottery_max_chance = Decimal(str(params.get("lottery_max_chance", 1.0)))
        self.lottery_bet_pct = Decimal(str(params.get("lottery_bet_pct", 1.0)))
        
        # State
        self.current_balance = Decimal(ctx.starting_balance)
        self.base_bet = self._calculate_base_bet(self.current_balance)
        self.current_bet = self.base_bet
        self.win_streak = 0
        self._is_lottery_bet = False  # Flag for next bet type
        
        # Statistics
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
        self.max_streak = 0
        self.streak_wins = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # Track streak distribution
        self.lottery_bets = 0
        self.lottery_wins = 0
        
    def _calculate_base_bet(self, balance: Decimal) -> Decimal:
        """Calculate base bet as balance / divisor."""
        if balance <= Decimal("0"):
            return Decimal("0.00000001")  # Minimum bet
        
        base = balance / Decimal(str(self.divisor))
        return max(base, Decimal("0.00000001"))
    
    def on_session_start(self) -> None:
        """Called when session starts."""
        logger.info("STREAK MULTIPLIER STRATEGY")
        logger.info("Base Bet: balance / %s", self.divisor)
        logger.info("Win Chance: %s%%", self.chance)
        logger.info(
            "Win Multiplier: %sx (%.0f%% increase)",
            self.win_multiplier,
            (self.win_multiplier - 1) * 100,
        )
        logger.info("Direction: %s", 'HIGH' if self.is_high else 'LOW')
        logger.info("Starting Balance: %s", self.current_balance)
        logger.info("Initial Base Bet: %s", self.base_bet)
        logger.info("Expected Payout: ~%.2fx per win", float(Decimal("99") / self.chance))
        logger.info("Streak Probabilities:")
        prob = float(self.chance / Decimal("100"))
        for i in range(1, 6):
            streak_prob = prob ** i
            logger.info("  %s-win streak: %.4f%% (1 in %s)", i, streak_prob * 100, int(1 / streak_prob))
        if self.lottery_enabled:
            logger.info("Lottery Bets: ENABLED")
            logger.info("  Interval: every %s bets", self.lottery_interval)
            logger.info("  Bet Size: %s%% of balance", self.lottery_bet_pct)
            logger.info(
                "  Win Chance: %s%% - %s%% (random each bet)",
                self.lottery_min_chance,
                self.lottery_max_chance,
            )
            min_payout = float(Decimal("99") / self.lottery_max_chance)
            max_payout = float(Decimal("99") / self.lottery_min_chance)
            logger.info("  Potential Payout: ~%.2fx - %.2fx per win", min_payout, max_payout)
    
    def _calculate_lottery_bet(self) -> tuple:
        """Return (amount, chance) for a lottery bet. Chance is random in [min, max]."""
        amount = self.current_balance * self.lottery_bet_pct / Decimal("100")
        amount = max(amount, Decimal("0.00000001"))

        # Pick a random win chance between min and max
        if self.lottery_max_chance <= self.lottery_min_chance:
            chance = self.lottery_min_chance
        else:
            rand = Decimal(str(random.uniform(0.0, 1.0)))
            chance = self.lottery_min_chance + rand * (self.lottery_max_chance - self.lottery_min_chance)

        return amount, chance

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet."""
        # Determine if this is a lottery bet slot
        next_bet_number = self.total_bets + 1
        if self.lottery_enabled and self.lottery_interval > 0:
            self._is_lottery_bet = (next_bet_number % self.lottery_interval == 0)
        else:
            self._is_lottery_bet = False

        if self._is_lottery_bet:
            lottery_amount, lottery_chance = self._calculate_lottery_bet()
            if lottery_amount > self.current_balance:
                lottery_amount = self.current_balance
            if lottery_amount <= Decimal("0"):
                return None
            self._last_lottery_chance = lottery_chance
            return {
                "game": "dice",
                "amount": format(lottery_amount, 'f'),
                "chance": format(lottery_chance, 'f'),
                "is_high": self.is_high,
                "faucet": self.ctx.faucet,
            }

        # Normal streak bet
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

        if self._is_lottery_bet:
            # Lottery bet result — does not affect win streak
            self.lottery_bets += 1
            chance_used = getattr(self, "_last_lottery_chance", self.lottery_min_chance)
            if result.get("win"):
                self.lottery_wins += 1
                logger.info("[Bet #%s] LOTTERY WIN! chance=%.4f%%", self.total_bets, chance_used)
                logger.info("  Profit: %+.8f | Balance: %.8f", profit, self.current_balance)
            else:
                logger.info("[Bet #%s] lottery miss chance=%.4f%%", self.total_bets, chance_used)
                logger.info("  Profit: %+.8f | Balance: %.8f", profit, self.current_balance)
            return
        
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
            logger.info("[Bet #%s] WIN (Streak: %s)", self.total_bets, self.win_streak)
            logger.info("  Profit: %+.8f | Balance: %.8f", profit, self.current_balance)
            logger.info("  Next bet: %.8f (%sx increase)", self.current_bet, self.win_multiplier)
            
        else:
            # LOSS: Reset to base bet
            self.total_losses += 1
            
            # Log loss and reset
            logger.info("[Bet #%s] LOSS (Streak broken: %s)", self.total_bets, self.win_streak)
            logger.info("  Profit: %+.8f | Balance: %.8f", profit, self.current_balance)
            logger.info("  Reset to base: %.8f", self.base_bet)
            
            # Reset
            self.win_streak = 0
            self.current_bet = self.base_bet
    
    def on_session_end(self, stopped_reason: str = "completed") -> None:
        """Called when session ends."""
        logger.info("STREAK MULTIPLIER STRATEGY - SESSION SUMMARY")
        logger.info("Total Bets: %s", self.total_bets)
        logger.info("Wins: %s", self.total_wins)
        logger.info("Losses: %s", self.total_losses)
        if self.total_bets > 0:
            win_rate = (self.total_wins / self.total_bets) * 100
            logger.info("Win Rate: %.2f%%", win_rate)
        logger.info("Final Balance: %.8f", self.current_balance)
        logger.info("Starting Balance: %s", self.ctx.starting_balance)
        
        profit = self.current_balance - Decimal(self.ctx.starting_balance)
        profit_pct = (profit / Decimal(self.ctx.starting_balance)) * 100
        logger.info("Profit: %+.8f (%+.2f%%)", profit, profit_pct)
        
        logger.info("Max Win Streak: %s", self.max_streak)
        logger.info("Streak Distribution:")
        for streak in sorted(self.streak_wins.keys()):
            count = self.streak_wins[streak]
            if count > 0:
                label = f"{streak}+ wins" if streak == 5 else f"{streak}-win"
                logger.info("  %s: %s times", label, count)

        if self.lottery_enabled and self.lottery_bets > 0:
            logger.info("Lottery Bets: %s placed, %s won", self.lottery_bets, self.lottery_wins)
            lottery_win_rate = (self.lottery_wins / self.lottery_bets) * 100
            avg_chance = float((self.lottery_min_chance + self.lottery_max_chance) / 2)
            logger.info(
                "Lottery Win Rate: %.2f%% (avg expected ~%.2f%%)",
                lottery_win_rate,
                avg_chance,
            )
