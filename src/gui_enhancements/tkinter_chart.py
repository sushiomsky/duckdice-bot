#!/usr/bin/env python3
"""
Pure Tkinter Chart - No matplotlib required
Real-time profit/loss visualization using Canvas
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple, Deque
from datetime import datetime
from decimal import Decimal
from collections import deque


class TkinterLiveChart(ttk.Frame):
    """
    Pure Tkinter implementation of live chart.
    Works without matplotlib - always available!
    """
    
    def __init__(self, parent, max_points: int = 100):
        """
        Initialize chart panel.
        
        Args:
            parent: Parent widget
            max_points: Maximum number of data points to display
        """
        super().__init__(parent)
        
        self.max_points = max_points
        
        # Data storage
        self.timestamps: Deque[datetime] = deque(maxlen=max_points)
        self.balances: Deque[float] = deque(maxlen=max_points)
        self.wins: Deque[Tuple[datetime, float]] = deque(maxlen=max_points)
        self.losses: Deque[Tuple[datetime, float]] = deque(maxlen=max_points)
        
        self.min_balance = 0
        self.max_balance = 100
        
        self._create_ui()
    
    def _create_ui(self):
        """Create chart UI."""
        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(
            title_frame,
            text="📊 Live Profit/Loss Chart",
            font=('Segoe UI', 12, 'bold')
        ).pack(side=tk.LEFT)
        
        # Stats
        self.stats_var = tk.StringVar(value="No data yet")
        ttk.Label(
            title_frame,
            textvariable=self.stats_var,
            font=('Segoe UI', 9),
            foreground='#757575'
        ).pack(side=tk.RIGHT)
        
        # Canvas for chart
        canvas_frame = ttk.Frame(self, relief=tk.SUNKEN, borderwidth=2)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            bg='#FFFFFF',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Legend
        legend_frame = ttk.Frame(self)
        legend_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self._create_legend_item(legend_frame, "Balance", "#1976D2")
        self._create_legend_item(legend_frame, "Wins", "#2E7D32")
        self._create_legend_item(legend_frame, "Losses", "#C62828")
        
        # Bind resize
        self.canvas.bind('<Configure>', lambda e: self._redraw())
    
    def _create_legend_item(self, parent, label: str, color: str):
        """Create a legend item."""
        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, padx=10)
        
        # Color box
        canvas = tk.Canvas(frame, width=20, height=12, highlightthickness=0, bg='#FAFAFA')
        canvas.pack(side=tk.LEFT, padx=(0, 5))
        canvas.create_rectangle(2, 2, 18, 10, fill=color, outline=color)
        
        # Label
        ttk.Label(
            frame,
            text=label,
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT)
    
    def add_data_point(self, balance: Decimal, is_win: bool = None):
        """
        Add a new data point to the chart.
        
        Args:
            balance: Current balance
            is_win: True if win, False if loss, None if neutral update
        """
        now = datetime.now()
        balance_float = float(balance)
        
        self.timestamps.append(now)
        self.balances.append(balance_float)
        
        # Track wins/losses
        if is_win is True:
            self.wins.append((now, balance_float))
        elif is_win is False:
            self.losses.append((now, balance_float))
        
        # Update range
        if len(self.balances) > 0:
            self.min_balance = min(self.balances)
            self.max_balance = max(self.balances)
            
            # Add 10% padding
            range_padding = (self.max_balance - self.min_balance) * 0.1
            if range_padding < 0.01:  # Minimum padding
                range_padding = 0.1
            
            self.min_balance -= range_padding
            self.max_balance += range_padding
        
        # Update stats
        if len(self.balances) > 0:
            current = self.balances[-1]
            initial = self.balances[0]
            profit = current - initial
            profit_pct = ((current / initial) - 1) * 100 if initial > 0 else 0
            
            self.stats_var.set(
                f"Current: {current:.8f} | "
                f"Profit: {profit:+.8f} ({profit_pct:+.2f}%) | "
                f"Points: {len(self.balances)}"
            )
        
        self._redraw()
    
    def _redraw(self):
        """Redraw the entire chart."""
        self.canvas.delete('all')
        
        if len(self.timestamps) < 2:
            # Show message when no data
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            
            self.canvas.create_text(
                width // 2,
                height // 2,
                text="Waiting for betting data...",
                font=('Segoe UI', 12),
                fill='#BDBDBD'
            )
            return
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 50 or height < 50:
            return  # Canvas not ready
        
        # Margins
        margin_left = 60
        margin_right = 20
        margin_top = 20
        margin_bottom = 40
        
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom
        
        if chart_width < 10 or chart_height < 10:
            return
        
        # Draw grid
        self._draw_grid(margin_left, margin_top, chart_width, chart_height)
        
        # Draw balance line
        self._draw_balance_line(margin_left, margin_top, chart_width, chart_height)
        
        # Draw markers
        self._draw_markers(margin_left, margin_top, chart_width, chart_height)
        
        # Draw axes
        self._draw_axes(margin_left, margin_top, chart_width, chart_height)
    
    def _draw_grid(self, x_offset, y_offset, width, height):
        """Draw grid lines."""
        # Horizontal grid lines (5 lines)
        for i in range(6):
            y = y_offset + (height * i / 5)
            self.canvas.create_line(
                x_offset, y,
                x_offset + width, y,
                fill='#E0E0E0',
                width=1
            )
        
        # Vertical grid lines (time markers)
        for i in range(11):
            x = x_offset + (width * i / 10)
            self.canvas.create_line(
                x, y_offset,
                x, y_offset + height,
                fill='#E0E0E0',
                width=1
            )
    
    def _draw_balance_line(self, x_offset, y_offset, width, height):
        """Draw the main balance line."""
        if len(self.balances) < 2:
            return
        
        points = []
        
        for i, balance in enumerate(self.balances):
            # X position (time)
            x = x_offset + (width * i / (len(self.balances) - 1))
            
            # Y position (balance)
            if self.max_balance > self.min_balance:
                normalized = (balance - self.min_balance) / (self.max_balance - self.min_balance)
            else:
                normalized = 0.5
            
            y = y_offset + height - (height * normalized)
            
            points.extend([x, y])
        
        # Draw smooth line
        if len(points) >= 4:
            self.canvas.create_line(
                *points,
                fill='#1976D2',
                width=2,
                smooth=True
            )
    
    def _draw_markers(self, x_offset, y_offset, width, height):
        """Draw win/loss markers."""
        # Draw wins (green triangles up)
        for timestamp, balance in self.wins:
            try:
                idx = list(self.timestamps).index(timestamp)
                x = x_offset + (width * idx / (len(self.balances) - 1))
                
                if self.max_balance > self.min_balance:
                    normalized = (balance - self.min_balance) / (self.max_balance - self.min_balance)
                else:
                    normalized = 0.5
                
                y = y_offset + height - (height * normalized)
                
                # Triangle pointing up
                size = 6
                self.canvas.create_polygon(
                    x, y - size,
                    x - size, y + size,
                    x + size, y + size,
                    fill='#2E7D32',
                    outline='#1B5E20'
                )
            except ValueError:
                continue
        
        # Draw losses (red triangles down)
        for timestamp, balance in self.losses:
            try:
                idx = list(self.timestamps).index(timestamp)
                x = x_offset + (width * idx / (len(self.balances) - 1))
                
                if self.max_balance > self.min_balance:
                    normalized = (balance - self.min_balance) / (self.max_balance - self.min_balance)
                else:
                    normalized = 0.5
                
                y = y_offset + height - (height * normalized)
                
                # Triangle pointing down
                size = 6
                self.canvas.create_polygon(
                    x, y + size,
                    x - size, y - size,
                    x + size, y - size,
                    fill='#C62828',
                    outline='#B71C1C'
                )
            except ValueError:
                continue
    
    def _draw_axes(self, x_offset, y_offset, width, height):
        """Draw axes and labels."""
        # Y-axis labels (balance)
        for i in range(6):
            y = y_offset + (height * i / 5)
            
            # Calculate balance value
            if self.max_balance > self.min_balance:
                balance = self.max_balance - ((self.max_balance - self.min_balance) * i / 5)
            else:
                balance = self.min_balance
            
            # Label
            self.canvas.create_text(
                x_offset - 10,
                y,
                text=f"{balance:.4f}",
                anchor=tk.E,
                font=('Segoe UI', 8),
                fill='#757575'
            )
        
        # X-axis labels (time)
        if len(self.timestamps) > 0:
            # Show first, middle, and last timestamps
            positions = [0, len(self.timestamps) // 2, len(self.timestamps) - 1]
            
            for idx in positions:
                if idx < len(self.timestamps):
                    x = x_offset + (width * idx / (len(self.balances) - 1))
                    time_str = self.timestamps[idx].strftime('%H:%M:%S')
                    
                    self.canvas.create_text(
                        x,
                        y_offset + height + 15,
                        text=time_str,
                        font=('Segoe UI', 8),
                        fill='#757575'
                    )
        
        # Axis lines
        self.canvas.create_line(
            x_offset, y_offset,
            x_offset, y_offset + height,
            fill='#212121',
            width=2
        )
        
        self.canvas.create_line(
            x_offset, y_offset + height,
            x_offset + width, y_offset + height,
            fill='#212121',
            width=2
        )
    
    def clear(self):
        """Clear all data."""
        self.timestamps.clear()
        self.balances.clear()
        self.wins.clear()
        self.losses.clear()
        self.min_balance = 0
        self.max_balance = 100
        self.stats_var.set("No data yet")
        self._redraw()


# Backwards compatibility - use TkinterLiveChart as fallback
LiveChartPanel = TkinterLiveChart
