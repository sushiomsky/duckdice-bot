"""
Risk analysis tools.
"""

from decimal import Decimal
from typing import List
import math
import logging

from .models import SimulatedBet, RiskAnalysis

logger = logging.getLogger(__name__)


class DrawdownTracker:
    """Track drawdown statistics."""
    
    def __init__(self, starting_balance: Decimal):
        """Initialize drawdown tracker."""
        self.starting_balance = starting_balance
        self.peak_balance = starting_balance
        self.max_drawdown = Decimal('0')
        self.max_drawdown_pct = 0.0
        
    def update(self, current_balance: Decimal):
        """Update with new balance."""
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        drawdown = self.peak_balance - current_balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
            self.max_drawdown_pct = (
                float(drawdown / self.peak_balance * 100)
                if self.peak_balance > 0 else 0.0
            )
    
    def get_current_drawdown(self, current_balance: Decimal) -> tuple[Decimal, float]:
        """Get current drawdown amount and percentage."""
        drawdown = self.peak_balance - current_balance
        drawdown_pct = (
            float(drawdown / self.peak_balance * 100)
            if self.peak_balance > 0 else 0.0
        )
        return drawdown, drawdown_pct


class RiskAnalyzer:
    """Analyze risk metrics from bet history."""
    
    @staticmethod
    def analyze(bets: List[SimulatedBet], starting_balance: Decimal) -> RiskAnalysis:
        """
        Analyze risk from bet history.
        
        Args:
            bets: List of simulated bets
            starting_balance: Starting balance amount
            
        Returns:
            RiskAnalysis object
        """
        if not bets:
            return RiskAnalyzer._empty_analysis(starting_balance)
        
        # Track drawdown
        tracker = DrawdownTracker(starting_balance)
        for bet in bets:
            tracker.update(bet.balance_after)
        
        current_balance = bets[-1].balance_after
        current_dd, current_dd_pct = tracker.get_current_drawdown(current_balance)
        
        # Calculate variance and standard deviation
        profits = [float(bet.profit) for bet in bets]
        mean_profit = sum(profits) / len(profits)
        variance = sum((p - mean_profit) ** 2 for p in profits) / len(profits)
        std_dev = math.sqrt(variance)
        
        # Estimate suggested bankroll (10x max drawdown)
        suggested_bankroll = tracker.max_drawdown * Decimal('10')
        if suggested_bankroll < starting_balance:
            suggested_bankroll = starting_balance
        
        # Calculate risk of ruin (simplified)
        # Based on win rate and average bet size
        wins = sum(1 for bet in bets if bet.won)
        win_rate = wins / len(bets) if bets else 0.5
        
        avg_bet = sum(bet.amount for bet in bets) / len(bets)
        bankroll_units = float(current_balance / avg_bet) if avg_bet > 0 else 100
        
        # Simplified risk of ruin formula
        # ROR = ((1 - win_rate) / win_rate) ^ bankroll_units
        if win_rate > 0 and win_rate < 1:
            ror_base = (1 - win_rate) / win_rate
            risk_of_ruin = min(ror_base ** (bankroll_units / 10), 1.0)
        else:
            risk_of_ruin = 0.0 if win_rate >= 0.5 else 1.0
        
        return RiskAnalysis(
            max_drawdown=tracker.max_drawdown,
            max_drawdown_pct=tracker.max_drawdown_pct,
            current_drawdown=current_dd,
            current_drawdown_pct=current_dd_pct,
            peak_balance=tracker.peak_balance,
            variance=variance,
            std_deviation=std_dev,
            suggested_bankroll=suggested_bankroll,
            risk_of_ruin=risk_of_ruin,
        )
    
    @staticmethod
    def _empty_analysis(starting_balance: Decimal) -> RiskAnalysis:
        """Return empty risk analysis."""
        return RiskAnalysis(
            max_drawdown=Decimal('0'),
            max_drawdown_pct=0.0,
            current_drawdown=Decimal('0'),
            current_drawdown_pct=0.0,
            peak_balance=starting_balance,
            variance=0.0,
            std_deviation=0.0,
            suggested_bankroll=starting_balance,
            risk_of_ruin=0.0,
        )
