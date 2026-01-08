"""
Live Chart Panel
Real-time profit/loss visualization
Supports both matplotlib (if available) and pure Tkinter fallback
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple
from datetime import datetime
from decimal import Decimal
from collections import deque

# Try matplotlib first, fall back to Tkinter implementation
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Always import Tkinter fallback
from .tkinter_chart import TkinterLiveChart


class LiveChartPanel(ttk.Frame):
    """
    Live profit/loss chart with real-time updates.
    Automatically uses matplotlib if available, otherwise uses Tkinter canvas.
    """
    
    def __init__(self, parent, max_points: int = 500, force_tkinter: bool = False):
        """
        Initialize chart panel.
        
        Args:
            parent: Parent widget
            max_points: Maximum number of data points to display
            force_tkinter: Force use of Tkinter chart even if matplotlib available
        """
        super().__init__(parent)
        
        # Decide which implementation to use
        use_matplotlib = MATPLOTLIB_AVAILABLE and not force_tkinter
        
        if use_matplotlib:
            print("✓ Using matplotlib for live charts")
            self.chart = MatplotlibChart(self, max_points)
        else:
            if not MATPLOTLIB_AVAILABLE:
                print("ℹ Using Tkinter canvas for live charts (matplotlib not available)")
            else:
                print("ℹ Using Tkinter canvas for live charts")
            self.chart = TkinterLiveChart(self, max_points)
        
        self.chart.pack(fill=tk.BOTH, expand=True)
    
    def add_data_point(self, balance: Decimal, is_win: bool = None):
        """Add data point to chart."""
        self.chart.add_data_point(balance, is_win)
    
    def clear(self):
        """Clear chart data."""
        self.chart.clear()


class MatplotlibChart(ttk.Frame):
    """Matplotlib-based chart implementation."""
    
    def __init__(self, parent, max_points: int = 500):
        super().__init__(parent)
    
    def __init__(self, parent, max_points: int = 500):
        super().__init__(parent)
        
        self.max_points = max_points
        
        # Data storage
        self.timestamps: deque = deque(maxlen=max_points)
        self.balances: deque = deque(maxlen=max_points)
        self.wins: List[Tuple[datetime, float]] = []
        self.losses: List[Tuple[datetime, float]] = []
        
        self._create_chart()
    
    def _create_chart(self):
        """Create matplotlib chart."""
        # Create figure
        self.fig = Figure(figsize=(10, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Style
        self.fig.patch.set_facecolor('#FFFFFF')
        self.ax.set_facecolor('#F5F5F5')
        self.ax.grid(True, alpha=0.3)
        
        # Labels
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Balance')
        self.ax.set_title('Profit/Loss Over Time')
        
        # Date formatting
        self.ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        
        # Initialize lines
        self.balance_line, = self.ax.plot([], [], 'b-', linewidth=2, label='Balance')
        self.win_markers, = self.ax.plot([], [], 'g^', markersize=8, label='Wins')
        self.loss_markers, = self.ax.plot([], [], 'rv', markersize=8, label='Losses')
        
        self.ax.legend(loc='upper left')
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
    
    def add_data_point(self, balance: Decimal, is_win: bool = None):
        """Add a new data point to the chart."""
        now = datetime.now()
        balance_float = float(balance)
        
        self.timestamps.append(now)
        self.balances.append(balance_float)
        
        # Track wins/losses
        if is_win is True:
            self.wins.append((now, balance_float))
            if len(self.wins) > self.max_points:
                self.wins.pop(0)
        elif is_win is False:
            self.losses.append((now, balance_float))
            if len(self.losses) > self.max_points:
                self.losses.pop(0)
        
        self._update_chart()
    
    def _update_chart(self):
        """Redraw chart with latest data."""
        if len(self.timestamps) == 0:
            return
        
        # Update balance line
        self.balance_line.set_data(list(self.timestamps), list(self.balances))
        
        # Update win markers
        if self.wins:
            win_times, win_balances = zip(*self.wins)
            self.win_markers.set_data(win_times, win_balances)
        
        # Update loss markers
        if self.losses:
            loss_times, loss_balances = zip(*self.losses)
            self.loss_markers.set_data(loss_times, loss_balances)
        
        # Auto-scale
        self.ax.relim()
        self.ax.autoscale_view()
        
        # Redraw
        try:
            self.canvas.draw()
        except:
            pass  # Ignore draw errors
    
    def clear(self):
        """Clear all data."""
        self.timestamps.clear()
        self.balances.clear()
        self.wins.clear()
        self.losses.clear()
        self._update_chart()

        
        # Auto-scale axes
        self.ax.relim()
        self.ax.autoscale_view()
        
        # Rotate x-axis labels for readability
        self.fig.autofmt_xdate()
        
        # Redraw
        self.canvas.draw()
    
    def clear(self):
        """Clear all data from chart."""
        if not self.enabled:
            return
        
        self.timestamps.clear()
        self.balances.clear()
        self.wins.clear()
        self.losses.clear()
        
        self.balance_line.set_data([], [])
        self.win_markers.set_data([], [])
        self.loss_markers.set_data([], [])
        
        self.canvas.draw()
    
    def export_data(self) -> List[dict]:
        """Export chart data for analysis."""
        return [
            {
                'timestamp': ts.isoformat(),
                'balance': bal,
            }
            for ts, bal in zip(self.timestamps, self.balances)
        ]
