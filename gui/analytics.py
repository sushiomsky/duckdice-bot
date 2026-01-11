"""
Analytics module for DuckDice Bot.

Provides statistical analysis and performance metrics for betting sessions.
"""
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from gui.state import BetRecord


@dataclass
class SessionAnalytics:
    """Analytics for a betting session."""
    
    # Basic stats
    total_bets: int
    wins: int
    losses: int
    win_rate: float  # Percentage
    
    # Financial metrics
    total_wagered: float
    gross_profit: float  # Total winnings
    gross_loss: float  # Total losses
    net_profit: float
    roi: float  # Return on Investment (%)
    profit_factor: float  # Gross profit / Gross loss
    
    # Average metrics
    avg_bet_size: float
    avg_win: float
    avg_loss: float
    avg_profit_per_bet: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    largest_win: float
    largest_loss: float
    
    # Streak statistics
    longest_win_streak: int
    longest_loss_streak: int
    current_streak: int
    current_streak_type: str  # "win" or "loss"
    
    # Statistical measures
    std_deviation: float
    variance: float
    
    # Session info
    starting_balance: float
    ending_balance: float
    duration_bets: int  # Number of bets as a measure of duration


class AnalyticsCalculator:
    """Calculate analytics from bet history."""
    
    @staticmethod
    def calculate_session_analytics(bets: List[BetRecord], 
                                    starting_balance: float = 0) -> SessionAnalytics:
        """
        Calculate comprehensive analytics for a betting session.
        
        Args:
            bets: List of BetRecord objects
            starting_balance: Starting balance for the session
        
        Returns:
            SessionAnalytics object with all calculated metrics
        """
        if not bets:
            return AnalyticsCalculator._empty_analytics(starting_balance)
        
        # Basic counts
        total_bets = len(bets)
        wins = sum(1 for bet in bets if bet.won)
        losses = total_bets - wins
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        
        # Financial calculations
        total_wagered = sum(bet.amount for bet in bets)
        profits = [bet.profit for bet in bets]
        wins_amounts = [bet.profit for bet in bets if bet.profit > 0]
        loss_amounts = [abs(bet.profit) for bet in bets if bet.profit < 0]
        
        gross_profit = sum(wins_amounts) if wins_amounts else 0
        gross_loss = sum(loss_amounts) if loss_amounts else 0
        net_profit = sum(profits)
        
        # ROI and profit factor
        roi = (net_profit / total_wagered * 100) if total_wagered > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        # Average calculations
        avg_bet_size = total_wagered / total_bets if total_bets > 0 else 0
        avg_win = (gross_profit / wins) if wins > 0 else 0
        avg_loss = (gross_loss / losses) if losses > 0 else 0
        avg_profit_per_bet = net_profit / total_bets if total_bets > 0 else 0
        
        # Risk metrics
        max_dd, max_dd_pct = AnalyticsCalculator._calculate_drawdown(bets, starting_balance)
        largest_win = max(wins_amounts) if wins_amounts else 0
        largest_loss = max(loss_amounts) if loss_amounts else 0
        
        # Streak statistics
        streaks = AnalyticsCalculator._calculate_streaks(bets)
        
        # Statistical measures
        std_dev = AnalyticsCalculator._calculate_std_deviation(profits)
        variance = std_dev ** 2
        
        # Session info
        ending_balance = bets[-1].balance if bets else starting_balance
        
        return SessionAnalytics(
            total_bets=total_bets,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            total_wagered=total_wagered,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_profit=net_profit,
            roi=roi,
            profit_factor=profit_factor,
            avg_bet_size=avg_bet_size,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_profit_per_bet=avg_profit_per_bet,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            largest_win=largest_win,
            largest_loss=largest_loss,
            longest_win_streak=streaks['longest_win_streak'],
            longest_loss_streak=streaks['longest_loss_streak'],
            current_streak=streaks['current_streak'],
            current_streak_type=streaks['current_streak_type'],
            std_deviation=std_dev,
            variance=variance,
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            duration_bets=total_bets
        )
    
    @staticmethod
    def _empty_analytics(starting_balance: float = 0) -> SessionAnalytics:
        """Return empty analytics for no bets."""
        return SessionAnalytics(
            total_bets=0, wins=0, losses=0, win_rate=0,
            total_wagered=0, gross_profit=0, gross_loss=0, net_profit=0,
            roi=0, profit_factor=0, avg_bet_size=0, avg_win=0, avg_loss=0,
            avg_profit_per_bet=0, max_drawdown=0, max_drawdown_pct=0,
            largest_win=0, largest_loss=0, longest_win_streak=0,
            longest_loss_streak=0, current_streak=0, current_streak_type="",
            std_deviation=0, variance=0, starting_balance=starting_balance,
            ending_balance=starting_balance, duration_bets=0
        )
    
    @staticmethod
    def _calculate_drawdown(bets: List[BetRecord], starting_balance: float) -> tuple:
        """
        Calculate maximum drawdown.
        
        Returns:
            Tuple of (max_drawdown_amount, max_drawdown_percentage)
        """
        if not bets:
            return 0, 0
        
        peak = starting_balance
        max_dd = 0
        max_dd_pct = 0
        
        for bet in bets:
            balance = bet.balance
            
            # Update peak if we've reached a new high
            if balance > peak:
                peak = balance
            
            # Calculate current drawdown
            drawdown = peak - balance
            drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0
            
            # Update max drawdown
            if drawdown > max_dd:
                max_dd = drawdown
                max_dd_pct = drawdown_pct
        
        return max_dd, max_dd_pct
    
    @staticmethod
    def _calculate_streaks(bets: List[BetRecord]) -> Dict[str, Any]:
        """Calculate win/loss streak statistics."""
        if not bets:
            return {
                'longest_win_streak': 0,
                'longest_loss_streak': 0,
                'current_streak': 0,
                'current_streak_type': ''
            }
        
        longest_win = 0
        longest_loss = 0
        current_streak = 0
        current_type = None
        
        for bet in bets:
            if bet.won:
                if current_type == 'win':
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = 'win'
                longest_win = max(longest_win, current_streak)
            else:
                if current_type == 'loss':
                    current_streak += 1
                else:
                    current_streak = 1
                    current_type = 'loss'
                longest_loss = max(longest_loss, current_streak)
        
        return {
            'longest_win_streak': longest_win,
            'longest_loss_streak': longest_loss,
            'current_streak': current_streak,
            'current_streak_type': current_type or ''
        }
    
    @staticmethod
    def _calculate_std_deviation(values: List[float]) -> float:
        """Calculate standard deviation of a list of values."""
        if not values or len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    @staticmethod
    def calculate_sharpe_ratio(profits: List[float], risk_free_rate: float = 0) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return).
        
        Args:
            profits: List of profit/loss values
            risk_free_rate: Risk-free rate of return (default 0)
        
        Returns:
            Sharpe ratio (higher is better)
        """
        if not profits or len(profits) < 2:
            return 0
        
        avg_return = sum(profits) / len(profits)
        std_dev = AnalyticsCalculator._calculate_std_deviation(profits)
        
        if std_dev == 0:
            return 0
        
        return (avg_return - risk_free_rate) / std_dev
    
    @staticmethod
    def calculate_expected_value(bets: List[BetRecord]) -> float:
        """
        Calculate expected value per bet.
        
        Returns:
            Average expected profit per bet
        """
        if not bets:
            return 0
        
        total_profit = sum(bet.profit for bet in bets)
        return total_profit / len(bets)
    
    @staticmethod
    def calculate_win_loss_ratio(bets: List[BetRecord]) -> float:
        """
        Calculate win/loss ratio.
        
        Returns:
            Average win / Average loss
        """
        wins = [bet.profit for bet in bets if bet.profit > 0]
        losses = [abs(bet.profit) for bet in bets if bet.profit < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        return (avg_win / avg_loss) if avg_loss > 0 else 0


class StrategyComparison:
    """Compare performance of different strategies or sessions."""
    
    @staticmethod
    def compare_sessions(sessions: Dict[str, SessionAnalytics]) -> Dict[str, Any]:
        """
        Compare multiple sessions.
        
        Args:
            sessions: Dict mapping session names to SessionAnalytics
        
        Returns:
            Dict with comparison metrics
        """
        if not sessions:
            return {}
        
        # Find best/worst performers
        by_roi = sorted(sessions.items(), key=lambda x: x[1].roi, reverse=True)
        by_win_rate = sorted(sessions.items(), key=lambda x: x[1].win_rate, reverse=True)
        by_profit_factor = sorted(sessions.items(), key=lambda x: x[1].profit_factor, reverse=True)
        
        return {
            'best_roi': by_roi[0] if by_roi else None,
            'worst_roi': by_roi[-1] if by_roi else None,
            'best_win_rate': by_win_rate[0] if by_win_rate else None,
            'worst_win_rate': by_win_rate[-1] if by_win_rate else None,
            'best_profit_factor': by_profit_factor[0] if by_profit_factor else None,
            'most_consistent': StrategyComparison._find_most_consistent(sessions),
            'rankings': {
                'by_roi': [(name, analytics.roi) for name, analytics in by_roi],
                'by_win_rate': [(name, analytics.win_rate) for name, analytics in by_win_rate],
                'by_profit_factor': [(name, analytics.profit_factor) for name, analytics in by_profit_factor]
            }
        }
    
    @staticmethod
    def _find_most_consistent(sessions: Dict[str, SessionAnalytics]) -> Optional[tuple]:
        """Find the most consistent strategy (lowest std deviation)."""
        if not sessions:
            return None
        
        by_consistency = sorted(
            sessions.items(),
            key=lambda x: x[1].std_deviation
        )
        
        return by_consistency[0] if by_consistency else None


# Global calculator instance
_analytics_calculator = AnalyticsCalculator()

def get_analytics_calculator() -> AnalyticsCalculator:
    """Get the global analytics calculator instance."""
    return _analytics_calculator
