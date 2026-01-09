"""
Performance metrics calculator.
"""

from decimal import Decimal
from typing import List
import logging

from .models import SimulatedBet, PerformanceMetrics

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate performance metrics from bet history."""
    
    @staticmethod
    def calculate(bets: List[SimulatedBet], starting_balance: Decimal) -> PerformanceMetrics:
        """
        Calculate performance metrics from bet history.
        
        Args:
            bets: List of simulated bets
            starting_balance: Starting balance amount
            
        Returns:
            PerformanceMetrics object
        """
        if not bets:
            return MetricsCalculator._empty_metrics()
        
        total_bets = len(bets)
        wins = sum(1 for bet in bets if bet.won)
        losses = total_bets - wins
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0.0
        
        total_wagered = sum(bet.amount for bet in bets)
        profit_loss = bets[-1].balance_after - starting_balance
        roi = float((profit_loss / starting_balance * 100)) if starting_balance > 0 else 0.0
        
        # Calculate streaks
        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for bet in bets:
            if bet.won:
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        # Calculate averages
        avg_bet_size = total_wagered / total_bets if total_bets > 0 else Decimal('0')
        
        win_bets = [bet for bet in bets if bet.won]
        loss_bets = [bet for bet in bets if not bet.won]
        
        avg_win_amount = (
            sum(bet.profit for bet in win_bets) / len(win_bets)
            if win_bets else Decimal('0')
        )
        avg_loss_amount = (
            sum(abs(bet.profit) for bet in loss_bets) / len(loss_bets)
            if loss_bets else Decimal('0')
        )
        
        # Calculate profit factor (gross profit / gross loss)
        gross_profit = sum(bet.profit for bet in win_bets)
        gross_loss = sum(abs(bet.profit) for bet in loss_bets)
        profit_factor = (
            float(gross_profit / gross_loss)
            if gross_loss > 0 else (float(gross_profit) if gross_profit > 0 else 0.0)
        )
        
        # Calculate expected value
        # EV = (win_rate * avg_win) - (loss_rate * avg_loss)
        expected_value = (
            (win_rate / 100 * float(avg_win_amount)) -
            ((100 - win_rate) / 100 * float(avg_loss_amount))
        )
        
        return PerformanceMetrics(
            total_bets=total_bets,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            total_wagered=total_wagered,
            profit_loss=profit_loss,
            roi=roi,
            max_win_streak=max_win_streak,
            max_loss_streak=max_loss_streak,
            avg_bet_size=avg_bet_size,
            avg_win_amount=avg_win_amount,
            avg_loss_amount=avg_loss_amount,
            profit_factor=profit_factor,
            expected_value=expected_value,
        )
    
    @staticmethod
    def _empty_metrics() -> PerformanceMetrics:
        """Return empty metrics."""
        return PerformanceMetrics(
            total_bets=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            total_wagered=Decimal('0'),
            profit_loss=Decimal('0'),
            roi=0.0,
            max_win_streak=0,
            max_loss_streak=0,
            avg_bet_size=Decimal('0'),
            avg_win_amount=Decimal('0'),
            avg_loss_amount=Decimal('0'),
            profit_factor=0.0,
            expected_value=0.0,
        )
