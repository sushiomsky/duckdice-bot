"""
Enhanced Bet History Viewer
Advanced viewer with SQLite backend, live/simulation toggle, and statistics
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from .bet_logger import BetLogger


class EnhancedBetHistoryViewer(ttk.Frame):
    """
    Advanced bet history viewer with SQLite backend.
    Supports live/simulation mode toggle, advanced filtering, and statistics.
    """
    
    def __init__(self, parent, bet_logger: Optional[BetLogger] = None):
        """
        Initialize enhanced bet history viewer.
        
        Args:
            parent: Parent widget
            bet_logger: BetLogger instance (creates new if None)
        """
        super().__init__(parent)
        
        self.bet_logger = bet_logger or BetLogger()
        self.current_mode = 'live'  # 'live' or 'simulation'
        self.current_page = 0
        self.page_size = 100
        
        self._create_ui()
        self.refresh()
    
    def _create_ui(self):
        """Create the UI components."""
        # Top control bar
        control_bar = ttk.Frame(self)
        control_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Mode toggle
        mode_frame = ttk.LabelFrame(control_bar, text="Mode", padding=5)
        mode_frame.pack(side=tk.LEFT, padx=5)
        
        self.mode_var = tk.StringVar(value='live')
        ttk.Radiobutton(
            mode_frame,
            text="💰 Live Bets",
            variable=self.mode_var,
            value='live',
            command=self._on_mode_changed
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="🧪 Simulation",
            variable=self.mode_var,
            value='simulation',
            command=self._on_mode_changed
        ).pack(side=tk.LEFT, padx=5)
        
        # Filter controls
        filter_frame = ttk.Frame(control_bar)
        filter_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=2)
        
        self.filter_var = tk.StringVar(value='All')
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=['All', 'Wins', 'Losses', 'Today', 'Yesterday', 'Last 7 Days', 'Last 30 Days'],
            width=15,
            state='readonly'
        )
        filter_combo.pack(side=tk.LEFT, padx=2)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        
        ttk.Label(filter_frame, text="Strategy:").pack(side=tk.LEFT, padx=2)
        
        self.strategy_var = tk.StringVar(value='All')
        self.strategy_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.strategy_var,
            values=['All'],
            width=15,
            state='readonly'
        )
        self.strategy_combo.pack(side=tk.LEFT, padx=2)
        self.strategy_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        
        # Action buttons
        action_frame = ttk.Frame(control_bar)
        action_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="🔄 Refresh",
            command=self.refresh,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            action_frame,
            text="💾 Export CSV",
            command=self.export_csv,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            action_frame,
            text="📊 Export JSON",
            command=self.export_json,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            action_frame,
            text="🗑️ Clear",
            command=self.clear_history,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Statistics panel
        stats_frame = ttk.LabelFrame(self, text="Statistics", padding=5)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Left stats
        left_stats = ttk.Frame(stats_frame)
        left_stats.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.total_label = ttk.Label(left_stats, text="Total: 0")
        self.total_label.pack(side=tk.LEFT, padx=10)
        
        self.wins_label = ttk.Label(left_stats, text="Wins: 0", foreground='#4CAF50')
        self.wins_label.pack(side=tk.LEFT, padx=10)
        
        self.losses_label = ttk.Label(left_stats, text="Losses: 0", foreground='#F44336')
        self.losses_label.pack(side=tk.LEFT, padx=10)
        
        self.winrate_label = ttk.Label(left_stats, text="Win Rate: 0%")
        self.winrate_label.pack(side=tk.LEFT, padx=10)
        
        # Right stats
        right_stats = ttk.Frame(stats_frame)
        right_stats.pack(side=tk.RIGHT)
        
        self.profit_label = ttk.Label(right_stats, text="Profit: 0")
        self.profit_label.pack(side=tk.LEFT, padx=10)
        
        self.avgprofit_label = ttk.Label(right_stats, text="Avg: 0")
        self.avgprofit_label.pack(side=tk.LEFT, padx=10)
        
        # TreeView frame
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        
        # Create TreeView
        columns = ('Time', 'Session', 'Symbol', 'Strategy', 'Bet', 'Chance', 'Payout', 'Result', 'Profit', 'Balance')
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            height=15
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Column configuration
        col_widths = {
            'Time': 160,
            'Session': 100,
            'Symbol': 70,
            'Strategy': 120,
            'Bet': 100,
            'Chance': 70,
            'Payout': 70,
            'Result': 80,
            'Profit': 100,
            'Balance': 120
        }
        
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))
            self.tree.column(col, width=col_widths.get(col, 100), anchor='center')
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Tags for coloring
        self.tree.tag_configure('win', background='#E8F5E9')
        self.tree.tag_configure('loss', background='#FFEBEE')
        
        # Pagination controls
        pagination_frame = ttk.Frame(self)
        pagination_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.page_label = ttk.Label(pagination_frame, text="Page 1")
        self.page_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            pagination_frame,
            text="⬅ Previous",
            command=self.previous_page,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            pagination_frame,
            text="Next ➡",
            command=self.next_page,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(pagination_frame, text="Per page:").pack(side=tk.LEFT, padx=5)
        
        self.pagesize_var = tk.StringVar(value='100')
        pagesize_combo = ttk.Combobox(
            pagination_frame,
            textvariable=self.pagesize_var,
            values=['50', '100', '200', '500'],
            width=8,
            state='readonly'
        )
        pagesize_combo.pack(side=tk.LEFT, padx=2)
        pagesize_combo.bind('<<ComboboxSelected>>', lambda e: self._on_pagesize_changed())
    
    def _on_mode_changed(self):
        """Handle mode toggle."""
        self.current_mode = self.mode_var.get()
        self.current_page = 0
        self.refresh()
    
    def _on_pagesize_changed(self):
        """Handle page size change."""
        try:
            self.page_size = int(self.pagesize_var.get())
            self.current_page = 0
            self.refresh()
        except:
            pass
    
    def refresh(self):
        """Refresh bet history from database."""
        is_simulation = (self.current_mode == 'simulation')
        
        # Build filters
        filters = {}
        
        # Strategy filter
        if self.strategy_var.get() != 'All':
            filters['strategy'] = self.strategy_var.get()
        
        # Date filter
        filter_type = self.filter_var.get()
        now = datetime.now()
        
        if filter_type == 'Today':
            filters['start_date'] = now.replace(hour=0, minute=0, second=0).isoformat()
        elif filter_type == 'Yesterday':
            yesterday = now - timedelta(days=1)
            filters['start_date'] = yesterday.replace(hour=0, minute=0, second=0).isoformat()
            filters['end_date'] = yesterday.replace(hour=23, minute=59, second=59).isoformat()
        elif filter_type == 'Last 7 Days':
            filters['start_date'] = (now - timedelta(days=7)).isoformat()
        elif filter_type == 'Last 30 Days':
            filters['start_date'] = (now - timedelta(days=30)).isoformat()
        
        # Get bets
        bets = self.bet_logger.get_bets(
            is_simulation=is_simulation,
            limit=self.page_size,
            offset=self.current_page * self.page_size,
            **filters
        )
        
        # Get statistics
        stats = self.bet_logger.get_statistics(
            is_simulation=is_simulation,
            **filters
        )
        
        # Update UI
        self._populate_tree(bets)
        self._update_statistics(stats)
        self._update_strategy_list(is_simulation)
        
        # Update pagination
        self.page_label.config(text=f"Page {self.current_page + 1}")
    
    def _populate_tree(self, bets: List[Dict[str, Any]]):
        """Populate TreeView with bets."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add bets
        for bet in bets:
            # Format values
            timestamp = bet.get('timestamp', '')[:19]  # Trim microseconds
            session_id = bet.get('session_id', '')[:8]  # Truncate
            symbol = bet.get('symbol', '')
            strategy = bet.get('strategy', '')
            bet_amount = f"{bet.get('bet_amount', 0):.8f}"
            chance = f"{bet.get('chance', 0):.2f}%"
            payout = f"{bet.get('payout', 0):.4f}x"
            result = '✅ Win' if bet.get('is_win') else '❌ Loss'
            profit = f"{bet.get('profit', 0):+.8f}"
            balance = f"{bet.get('balance', 0):.8f}"
            
            values = (timestamp, session_id, symbol, strategy, bet_amount, 
                     chance, payout, result, profit, balance)
            
            tag = 'win' if bet.get('is_win') else 'loss'
            self.tree.insert('', 'end', values=values, tags=(tag,))
    
    def _update_statistics(self, stats: Dict[str, Any]):
        """Update statistics labels."""
        total = stats.get('total_bets', 0)
        wins = stats.get('total_wins', 0)
        losses = stats.get('total_losses', 0)
        win_rate = stats.get('win_rate', 0)
        total_profit = stats.get('total_profit', 0)
        avg_profit = stats.get('avg_profit', 0)
        
        self.total_label.config(text=f"Total: {total}")
        self.wins_label.config(text=f"Wins: {wins}")
        self.losses_label.config(text=f"Losses: {losses}")
        self.winrate_label.config(text=f"Win Rate: {win_rate:.2f}%")
        
        # Color profit labels
        profit_color = '#4CAF50' if total_profit >= 0 else '#F44336'
        self.profit_label.config(
            text=f"Profit: {total_profit:+.8f}",
            foreground=profit_color
        )
        
        avg_color = '#4CAF50' if avg_profit >= 0 else '#F44336'
        self.avgprofit_label.config(
            text=f"Avg: {avg_profit:+.8f}",
            foreground=avg_color
        )
    
    def _update_strategy_list(self, is_simulation: bool):
        """Update strategy combobox with available strategies."""
        # Get unique strategies from database
        with self.bet_logger._get_connection() as conn:
            table = "simulation_bets" if is_simulation else "live_bets"
            cursor = conn.cursor()
            cursor.execute(f"SELECT DISTINCT strategy FROM {table} WHERE strategy IS NOT NULL")
            strategies = [row[0] for row in cursor.fetchall()]
        
        strategies.insert(0, 'All')
        self.strategy_combo['values'] = strategies
    
    def _sort_by_column(self, column: str):
        """Sort tree by column (placeholder)."""
        # Would implement sorting logic here
        pass
    
    def previous_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh()
    
    def next_page(self):
        """Go to next page."""
        self.current_page += 1
        self.refresh()
    
    def export_csv(self):
        """Export current view to CSV."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{self.current_mode}_bets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename:
            return
        
        try:
            is_simulation = (self.current_mode == 'simulation')
            self.bet_logger.export_to_csv(Path(filename), is_simulation=is_simulation)
            messagebox.showinfo("Export", f"Exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def export_json(self):
        """Export current view to JSON."""
        import json
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"{self.current_mode}_bets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if not filename:
            return
        
        try:
            is_simulation = (self.current_mode == 'simulation')
            bets = self.bet_logger.get_bets(is_simulation=is_simulation, limit=100000)
            
            with open(filename, 'w') as f:
                json.dump(bets, f, indent=2, default=str)
            
            messagebox.showinfo("Export", f"Exported {len(bets)} bets to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def clear_history(self):
        """Clear bet history (with confirmation)."""
        mode_name = "simulation" if self.current_mode == 'simulation' else "live"
        
        result = messagebox.askyesno(
            "Clear History",
            f"Are you sure you want to clear ALL {mode_name} bet history?\n\n"
            f"This action cannot be undone!",
            icon='warning'
        )
        
        if not result:
            return
        
        try:
            is_simulation = (self.current_mode == 'simulation')
            table = "simulation_bets" if is_simulation else "live_bets"
            
            with self.bet_logger._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {table}")
                deleted = cursor.rowcount
                conn.commit()
            
            messagebox.showinfo("Clear History", f"Deleted {deleted} {mode_name} bets")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear history: {e}")
