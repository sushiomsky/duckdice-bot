"""
Chart generation module for DuckDice Bot GUI.

Creates matplotlib charts for bet history visualization.
Charts are rendered as base64 images for embedding in NiceGUI.
"""
import io
import base64
from typing import List, Optional, Tuple
from datetime import datetime
import logging

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for server-side rendering
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    Figure = None

from gui.state import BetRecord, app_state

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generates charts from bet history data."""
    
    def __init__(self):
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available, charts disabled")
        
        # Chart styling
        self.figsize = (10, 6)
        self.dpi = 100
        self.style = 'seaborn-v0_8-darkgrid'
    
    def _fig_to_base64(self, fig: Figure) -> str:
        """Convert matplotlib figure to base64 string for embedding."""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close(fig)
        return f"data:image/png;base64,{img_base64}"
    
    def balance_over_time(self, bets: List[BetRecord]) -> Optional[str]:
        """
        Create balance over time chart.
        
        Args:
            bets: List of BetRecord objects
        
        Returns:
            Base64 encoded PNG image or None if no data
        """
        if not MATPLOTLIB_AVAILABLE or not bets:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=self.figsize)
            
            # Extract data
            timestamps = [bet.timestamp for bet in bets]
            balances = [bet.balance for bet in bets]
            
            # Plot
            ax.plot(timestamps, balances, linewidth=2, color='#2563eb', label='Balance')
            
            # Add starting balance line
            if app_state.starting_balance:
                ax.axhline(y=app_state.starting_balance, color='#64748b', 
                          linestyle='--', linewidth=1, label='Starting Balance')
            
            # Formatting
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel(f'Balance ({app_state.currency.upper() if app_state.currency else "BTC"})', 
                         fontsize=12)
            ax.set_title('Balance Over Time', fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            fig.autofmt_xdate()
            
            # Color the area
            if balances:
                ax.fill_between(timestamps, balances, alpha=0.2, color='#2563eb')
            
            return self._fig_to_base64(fig)
        
        except Exception as e:
            logger.error(f"Error creating balance chart: {e}")
            return None
    
    def profit_loss_chart(self, bets: List[BetRecord]) -> Optional[str]:
        """
        Create cumulative profit/loss chart.
        
        Args:
            bets: List of BetRecord objects
        
        Returns:
            Base64 encoded PNG image or None if no data
        """
        if not MATPLOTLIB_AVAILABLE or not bets:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=self.figsize)
            
            # Calculate cumulative profit
            timestamps = [bet.timestamp for bet in bets]
            cumulative_profit = []
            running_total = 0
            
            for bet in bets:
                running_total += bet.profit
                cumulative_profit.append(running_total)
            
            # Plot
            colors = ['#22c55e' if p >= 0 else '#ef4444' for p in cumulative_profit]
            ax.plot(timestamps, cumulative_profit, linewidth=2, color='#6366f1', 
                   label='Cumulative Profit/Loss')
            
            # Zero line
            ax.axhline(y=0, color='#64748b', linestyle='-', linewidth=1, alpha=0.5)
            
            # Fill area
            ax.fill_between(timestamps, cumulative_profit, 0, 
                           where=[p >= 0 for p in cumulative_profit],
                           alpha=0.3, color='#22c55e', label='Profit')
            ax.fill_between(timestamps, cumulative_profit, 0,
                           where=[p < 0 for p in cumulative_profit],
                           alpha=0.3, color='#ef4444', label='Loss')
            
            # Formatting
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel(f'Profit/Loss ({app_state.currency.upper() if app_state.currency else "BTC"})', 
                         fontsize=12)
            ax.set_title('Cumulative Profit/Loss', fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            fig.autofmt_xdate()
            
            return self._fig_to_base64(fig)
        
        except Exception as e:
            logger.error(f"Error creating profit/loss chart: {e}")
            return None
    
    def win_loss_distribution(self, bets: List[BetRecord]) -> Optional[str]:
        """
        Create win/loss distribution pie chart.
        
        Args:
            bets: List of BetRecord objects
        
        Returns:
            Base64 encoded PNG image or None if no data
        """
        if not MATPLOTLIB_AVAILABLE or not bets:
            return None
        
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            
            # Count wins and losses
            wins = sum(1 for bet in bets if bet.won)
            losses = len(bets) - wins
            
            # Win/Loss pie chart
            if wins > 0 or losses > 0:
                labels = ['Wins', 'Losses']
                sizes = [wins, losses]
                colors = ['#22c55e', '#ef4444']
                explode = (0.05, 0)
                
                ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                       autopct='%1.1f%%', shadow=True, startangle=90)
                ax1.set_title('Win/Loss Distribution', fontsize=14, fontweight='bold')
            
            # Profit distribution histogram
            profits = [bet.profit for bet in bets]
            if profits:
                ax2.hist(profits, bins=30, color='#6366f1', alpha=0.7, edgecolor='black')
                ax2.axvline(x=0, color='#64748b', linestyle='--', linewidth=2)
                ax2.set_xlabel(f'Profit ({app_state.currency.upper() if app_state.currency else "BTC"})', 
                              fontsize=12)
                ax2.set_ylabel('Frequency', fontsize=12)
                ax2.set_title('Profit Distribution', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
        
        except Exception as e:
            logger.error(f"Error creating win/loss chart: {e}")
            return None
    
    def streak_analysis(self, bets: List[BetRecord]) -> Optional[str]:
        """
        Create streak analysis chart showing win/loss streaks over time.
        
        Args:
            bets: List of BetRecord objects
        
        Returns:
            Base64 encoded PNG image or None if no data
        """
        if not MATPLOTLIB_AVAILABLE or not bets:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=self.figsize)
            
            # Calculate streaks
            timestamps = []
            streaks = []
            current_streak = 0
            
            for i, bet in enumerate(bets):
                timestamps.append(bet.timestamp)
                
                if bet.won:
                    current_streak = current_streak + 1 if current_streak > 0 else 1
                else:
                    current_streak = current_streak - 1 if current_streak < 0 else -1
                
                streaks.append(current_streak)
            
            # Plot
            colors = ['#22c55e' if s > 0 else '#ef4444' for s in streaks]
            ax.bar(range(len(streaks)), streaks, color=colors, alpha=0.7)
            
            # Zero line
            ax.axhline(y=0, color='#64748b', linestyle='-', linewidth=1)
            
            # Formatting
            ax.set_xlabel('Bet Number', fontsize=12)
            ax.set_ylabel('Streak (+ wins, - losses)', fontsize=12)
            ax.set_title('Win/Loss Streaks', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add max streak annotations
            if streaks:
                max_win = max(streaks)
                max_loss = min(streaks)
                if max_win > 0:
                    ax.annotate(f'Max: {max_win}', xy=(streaks.index(max_win), max_win),
                               xytext=(10, 10), textcoords='offset points',
                               bbox=dict(boxstyle='round', fc='#22c55e', alpha=0.7),
                               fontsize=10, color='white')
                if max_loss < 0:
                    ax.annotate(f'Max: {max_loss}', xy=(streaks.index(max_loss), max_loss),
                               xytext=(10, -20), textcoords='offset points',
                               bbox=dict(boxstyle='round', fc='#ef4444', alpha=0.7),
                               fontsize=10, color='white')
            
            return self._fig_to_base64(fig)
        
        except Exception as e:
            logger.error(f"Error creating streak chart: {e}")
            return None
    
    def save_chart_to_file(self, chart_base64: str, filename: str):
        """
        Save base64 chart to PNG file.
        
        Args:
            chart_base64: Base64 encoded image data
            filename: Output filename
        """
        try:
            # Remove data URL prefix if present
            if chart_base64.startswith('data:image/png;base64,'):
                chart_base64 = chart_base64.replace('data:image/png;base64,', '')
            
            # Decode and save
            img_data = base64.b64decode(chart_base64)
            with open(filename, 'wb') as f:
                f.write(img_data)
            
            logger.info(f"Chart saved to {filename}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving chart: {e}")
            return False


# Global singleton instance
_chart_generator = None

def get_chart_generator() -> ChartGenerator:
    """Get the global chart generator instance."""
    global _chart_generator
    if _chart_generator is None:
        _chart_generator = ChartGenerator()
    return _chart_generator
