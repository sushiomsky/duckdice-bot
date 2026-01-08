"""
Statistics Dashboard
Comprehensive analytics and performance metrics
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from .bet_logger import BetLogger


class StatisticsDashboard(ttk.Frame):
    """
    Comprehensive statistics dashboard with session comparison,
    strategy analytics, and performance metrics.
    """
    
    def __init__(self, parent, bet_logger: Optional[BetLogger] = None):
        """
        Initialize statistics dashboard.
        
        Args:
            parent: Parent widget
            bet_logger: BetLogger instance
        """
        super().__init__(parent)
        
        self.bet_logger = bet_logger or BetLogger()
        self.current_mode = 'live'
        
        # Initialize label storage
        self.overview_labels = {}
        
        self._create_ui()
        
        # Refresh after UI is created
        self.after(100, self.refresh)
    
    def _create_ui(self):
        """Create the UI components."""
        # Mode selector
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mode_frame, text="Mode:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        self.mode_var = tk.StringVar(value='live')
        ttk.Radiobutton(
            mode_frame,
            text="💰 Live",
            variable=self.mode_var,
            value='live',
            command=self.refresh
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="🧪 Simulation",
            variable=self.mode_var,
            value='simulation',
            command=self.refresh
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            mode_frame,
            text="🔄 Refresh",
            command=self.refresh
        ).pack(side=tk.RIGHT, padx=5)
        
        # Create notebook for different stat views
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Overview
        self.overview_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.overview_tab, text="📊 Overview")
        self._create_overview_tab()
        
        # Tab 2: Strategy Performance
        self.strategy_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.strategy_tab, text="🎯 Strategies")
        self._create_strategy_tab()
        
        # Tab 3: Session History
        self.session_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.session_tab, text="📅 Sessions")
        self._create_session_tab()
        
        # Tab 4: Time Analysis
        self.time_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.time_tab, text="⏱️ Timeline")
        self._create_time_tab()
    
    def _create_overview_tab(self):
        """Create overview statistics tab."""
        # Overall stats
        overall_frame = ttk.LabelFrame(self.overview_tab, text="Overall Statistics", padding=10)
        overall_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create grid layout for stats
        stats_grid = ttk.Frame(overall_frame)
        stats_grid.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid
        for i in range(3):
            stats_grid.columnconfigure(i, weight=1)
        
        row = 0
        
        # Total Bets
        self._create_stat_card(stats_grid, row, 0, "Total Bets", "0", "total_bets")
        self._create_stat_card(stats_grid, row, 1, "Total Wins", "0", "total_wins", fg='#4CAF50')
        self._create_stat_card(stats_grid, row, 2, "Total Losses", "0", "total_losses", fg='#F44336')
        
        row += 1
        
        # Win Rate and Profit
        self._create_stat_card(stats_grid, row, 0, "Win Rate", "0%", "win_rate")
        self._create_stat_card(stats_grid, row, 1, "Total Profit", "0", "total_profit", fg='#2196F3')
        self._create_stat_card(stats_grid, row, 2, "Avg Profit/Bet", "0", "avg_profit", fg='#FF9800')
        
        row += 1
        
        # Max values
        self._create_stat_card(stats_grid, row, 0, "Max Win", "0", "max_win", fg='#4CAF50')
        self._create_stat_card(stats_grid, row, 1, "Max Loss", "0", "max_loss", fg='#F44336')
        self._create_stat_card(stats_grid, row, 2, "Avg Bet Size", "0", "avg_bet")
        
        row += 1
        
        # Balance range
        self._create_stat_card(stats_grid, row, 0, "Min Balance", "0", "min_balance")
        self._create_stat_card(stats_grid, row, 1, "Max Balance", "0", "max_balance")
        self._create_stat_card(stats_grid, row, 2, "Balance Range", "0", "balance_range")
        
        # Risk metrics
        risk_frame = ttk.LabelFrame(self.overview_tab, text="Risk Metrics", padding=10)
        risk_frame.pack(fill=tk.X, pady=5)
        
        risk_grid = ttk.Frame(risk_frame)
        risk_grid.pack(fill=tk.X)
        
        for i in range(3):
            risk_grid.columnconfigure(i, weight=1)
        
        self._create_stat_card(risk_grid, 0, 0, "ROI", "0%", "roi")
        self._create_stat_card(risk_grid, 0, 1, "Profit Factor", "0", "profit_factor")
        self._create_stat_card(risk_grid, 0, 2, "Expectancy", "0", "expectancy")
    
    def _create_stat_card(self, parent, row, col, title, value, key, fg='#212121'):
        """Create a statistics card."""
        frame = ttk.LabelFrame(parent, text=title, padding=5)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
        
        label = ttk.Label(
            frame,
            text=value,
            font=('Arial', 16, 'bold'),
            foreground=fg
        )
        label.pack()
        
        # Store reference (dict already initialized in __init__)
        self.overview_labels[key] = label
    
    def _create_strategy_tab(self):
        """Create strategy performance tab."""
        # TreeView for strategy comparison
        tree_frame = ttk.Frame(self.strategy_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('Strategy', 'Bets', 'Wins', 'Win Rate', 'Profit', 'Avg Profit', 'ROI')
        self.strategy_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            height=12
        )
        
        # Configure columns
        col_widths = {
            'Strategy': 150,
            'Bets': 80,
            'Wins': 80,
            'Win Rate': 100,
            'Profit': 120,
            'Avg Profit': 120,
            'ROI': 80
        }
        
        for col in columns:
            self.strategy_tree.heading(col, text=col)
            self.strategy_tree.column(col, width=col_widths.get(col, 100), anchor='center')
        
        # Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.strategy_tree.yview)
        self.strategy_tree.configure(yscrollcommand=vsb.set)
        
        self.strategy_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tags
        self.strategy_tree.tag_configure('positive', background='#E8F5E9')
        self.strategy_tree.tag_configure('negative', background='#FFEBEE')
    
    def _create_session_tab(self):
        """Create session history tab."""
        # TreeView for sessions
        tree_frame = ttk.Frame(self.session_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('ID', 'Strategy', 'Start', 'Duration', 'Bets', 'Wins', 'Profit', 'ROI')
        self.session_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            height=12
        )
        
        # Configure columns
        col_widths = {
            'ID': 100,
            'Strategy': 120,
            'Start': 160,
            'Duration': 100,
            'Bets': 80,
            'Wins': 80,
            'Profit': 120,
            'ROI': 80
        }
        
        for col in columns:
            self.session_tree.heading(col, text=col)
            self.session_tree.column(col, width=col_widths.get(col, 100), anchor='center')
        
        # Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=vsb.set)
        
        self.session_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tags
        self.session_tree.tag_configure('positive', background='#E8F5E9')
        self.session_tree.tag_configure('negative', background='#FFEBEE')
    
    def _create_time_tab(self):
        """Create time-based analysis tab."""
        # Time period selector
        period_frame = ttk.Frame(self.time_tab)
        period_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(period_frame, text="Period:").pack(side=tk.LEFT, padx=5)
        
        self.period_var = tk.StringVar(value='Today')
        period_combo = ttk.Combobox(
            period_frame,
            textvariable=self.period_var,
            values=['Today', 'Yesterday', 'Last 7 Days', 'Last 30 Days', 'All Time'],
            state='readonly',
            width=15
        )
        period_combo.pack(side=tk.LEFT, padx=5)
        period_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        
        # Time stats
        time_stats_frame = ttk.LabelFrame(self.time_tab, text="Period Statistics", padding=10)
        time_stats_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.time_stats_text = tk.Text(time_stats_frame, height=15, wrap=tk.WORD)
        self.time_stats_text.pack(fill=tk.BOTH, expand=True)
    
    def refresh(self):
        """Refresh all statistics."""
        self.current_mode = self.mode_var.get()
        is_simulation = (self.current_mode == 'simulation')
        
        # Refresh overview
        self._refresh_overview(is_simulation)
        
        # Refresh strategy performance
        self._refresh_strategies(is_simulation)
        
        # Refresh sessions
        self._refresh_sessions(is_simulation)
        
        # Refresh time analysis
        self._refresh_time_analysis(is_simulation)
    
    def _refresh_overview(self, is_simulation: bool):
        """Refresh overview statistics."""
        stats = self.bet_logger.get_statistics(is_simulation=is_simulation)
        
        # Update labels (check if they exist first)
        if not self.overview_labels:
            return
        
        if 'total_bets' in self.overview_labels:
            self.overview_labels['total_bets'].config(text=str(stats.get('total_bets', 0)))
            self.overview_labels['total_wins'].config(text=str(stats.get('total_wins', 0)))
            self.overview_labels['total_losses'].config(text=str(stats.get('total_losses', 0)))
            self.overview_labels['win_rate'].config(text=f"{stats.get('win_rate', 0):.2f}%")
            
            total_profit = stats.get('total_profit', 0)
            profit_color = '#4CAF50' if total_profit >= 0 else '#F44336'
            self.overview_labels['total_profit'].config(
                text=f"{total_profit:+.8f}",
                foreground=profit_color
            )
            
            avg_profit = stats.get('avg_profit', 0)
            avg_color = '#4CAF50' if avg_profit >= 0 else '#F44336'
            self.overview_labels['avg_profit'].config(
                text=f"{avg_profit:+.8f}",
                foreground=avg_color
            )
            
            self.overview_labels['max_win'].config(text=f"{stats.get('max_win', 0):.8f}")
            self.overview_labels['max_loss'].config(text=f"{stats.get('max_loss', 0):.8f}")
            self.overview_labels['avg_bet'].config(text=f"{stats.get('avg_bet', 0):.8f}")
            
            min_bal = stats.get('min_balance', 0)
            max_bal = stats.get('max_balance', 0)
            self.overview_labels['min_balance'].config(text=f"{min_bal:.8f}")
            self.overview_labels['max_balance'].config(text=f"{max_bal:.8f}")
            self.overview_labels['balance_range'].config(text=f"{max_bal - min_bal:.8f}")
            
            # Calculate advanced metrics
            initial_balance = min_bal if min_bal > 0 else 1
            roi = (total_profit / initial_balance * 100) if initial_balance > 0 else 0
            self.overview_labels['roi'].config(text=f"{roi:+.2f}%")
            
            # Profit factor (total wins / total losses)
            total_wins_amount = abs(stats.get('max_win', 0)) * stats.get('total_wins', 0)
            total_losses_amount = abs(stats.get('max_loss', 0)) * stats.get('total_losses', 0)
            profit_factor = (total_wins_amount / total_losses_amount) if total_losses_amount > 0 else 0
            self.overview_labels['profit_factor'].config(text=f"{profit_factor:.2f}")
            
            # Expectancy
            expectancy = avg_profit
            self.overview_labels['expectancy'].config(text=f"{expectancy:+.8f}")
    
    def _refresh_strategies(self, is_simulation: bool):
        """Refresh strategy performance."""
        # Clear tree
        for item in self.strategy_tree.get_children():
            self.strategy_tree.delete(item)
        
        # Get unique strategies
        with self.bet_logger._get_connection() as conn:
            table = "simulation_bets" if is_simulation else "live_bets"
            cursor = conn.cursor()
            cursor.execute(f"SELECT DISTINCT strategy FROM {table} WHERE strategy IS NOT NULL")
            strategies = [row[0] for row in cursor.fetchall()]
        
        # Get stats for each strategy
        for strategy in strategies:
            stats = self.bet_logger.get_statistics(
                is_simulation=is_simulation,
                strategy=strategy
            )
            
            total_bets = stats.get('total_bets', 0)
            total_wins = stats.get('total_wins', 0)
            win_rate = stats.get('win_rate', 0)
            total_profit = stats.get('total_profit', 0)
            avg_profit = stats.get('avg_profit', 0)
            
            # Calculate ROI
            initial = stats.get('min_balance', 1)
            roi = (total_profit / initial * 100) if initial > 0 else 0
            
            values = (
                strategy,
                total_bets,
                total_wins,
                f"{win_rate:.2f}%",
                f"{total_profit:+.8f}",
                f"{avg_profit:+.8f}",
                f"{roi:+.2f}%"
            )
            
            tag = 'positive' if total_profit >= 0 else 'negative'
            self.strategy_tree.insert('', 'end', values=values, tags=(tag,))
    
    def _refresh_sessions(self, is_simulation: bool):
        """Refresh session history."""
        # Clear tree
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        
        # Get sessions
        sessions = self.bet_logger.get_sessions(is_simulation=is_simulation, limit=50)
        
        for session in sessions:
            session_id = session.get('id', '')[:8]
            strategy = session.get('strategy', 'N/A')
            start_time = session.get('start_time', '')[:19]
            
            # Calculate duration
            start = datetime.fromisoformat(session.get('start_time', ''))
            end_str = session.get('end_time')
            if end_str:
                end = datetime.fromisoformat(end_str)
                duration = end - start
                duration_str = str(duration).split('.')[0]  # Remove microseconds
            else:
                duration_str = 'Ongoing'
            
            total_bets = session.get('total_bets', 0)
            total_wins = session.get('total_wins', 0)
            total_profit = session.get('total_profit', 0)
            
            initial = session.get('initial_balance', 0)
            roi = (total_profit / initial * 100) if initial and initial > 0 else 0
            
            values = (
                session_id,
                strategy,
                start_time,
                duration_str,
                total_bets,
                total_wins,
                f"{total_profit:+.8f}",
                f"{roi:+.2f}%"
            )
            
            tag = 'positive' if total_profit >= 0 else 'negative'
            self.session_tree.insert('', 'end', values=values, tags=(tag,))
    
    def _refresh_time_analysis(self, is_simulation: bool):
        """Refresh time-based analysis."""
        period = self.period_var.get()
        
        # Calculate date range
        now = datetime.now()
        filters = {}
        
        if period == 'Today':
            filters['start_date'] = now.replace(hour=0, minute=0, second=0).isoformat()
        elif period == 'Yesterday':
            yesterday = now - timedelta(days=1)
            filters['start_date'] = yesterday.replace(hour=0, minute=0, second=0).isoformat()
            filters['end_date'] = yesterday.replace(hour=23, minute=59, second=59).isoformat()
        elif period == 'Last 7 Days':
            filters['start_date'] = (now - timedelta(days=7)).isoformat()
        elif period == 'Last 30 Days':
            filters['start_date'] = (now - timedelta(days=30)).isoformat()
        
        # Get statistics
        stats = self.bet_logger.get_statistics(is_simulation=is_simulation, **filters)
        
        # Format output
        output = f"Period: {period}\n"
        output += "=" * 50 + "\n\n"
        output += f"Total Bets:     {stats.get('total_bets', 0):,}\n"
        output += f"Total Wins:     {stats.get('total_wins', 0):,}\n"
        output += f"Total Losses:   {stats.get('total_losses', 0):,}\n"
        output += f"Win Rate:       {stats.get('win_rate', 0):.2f}%\n\n"
        output += f"Total Profit:   {stats.get('total_profit', 0):+.8f}\n"
        output += f"Avg Profit:     {stats.get('avg_profit', 0):+.8f}\n"
        output += f"Max Win:        {stats.get('max_win', 0):.8f}\n"
        output += f"Max Loss:       {stats.get('max_loss', 0):.8f}\n\n"
        output += f"Avg Bet:        {stats.get('avg_bet', 0):.8f}\n"
        output += f"Min Balance:    {stats.get('min_balance', 0):.8f}\n"
        output += f"Max Balance:    {stats.get('max_balance', 0):.8f}\n"
        
        # Update text widget
        self.time_stats_text.config(state=tk.NORMAL)
        self.time_stats_text.delete('1.0', tk.END)
        self.time_stats_text.insert('1.0', output)
        self.time_stats_text.config(state=tk.DISABLED)
