"""
Bet History Viewer
Searchable GUI for browsing past bets with filters and export
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal
import json
import csv


class BetHistoryViewer(ttk.Frame):
    """
    Interactive bet history browser with search and export.
    """
    
    def __init__(self, parent):
        """Initialize bet history viewer."""
        super().__init__(parent)
        
        self.bets: List[Dict[str, Any]] = []
        self.filtered_bets: List[Dict[str, Any]] = []
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the UI components."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="Filter:").pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add('write', lambda *args: self.apply_filter())
        filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var, width=15)
        filter_combo['values'] = ['All', 'Wins', 'Losses', 'Today', 'Last Hour']
        filter_combo.set('All')
        filter_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *args: self.apply_filter())
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="💾 Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📊 Export JSON", command=self.export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑️ Clear", command=self.clear).pack(side=tk.LEFT, padx=5)
        
        # Stats panel
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="Total: 0 | Wins: 0 | Losses: 0 | Win Rate: 0%")
        self.stats_label.pack(side=tk.LEFT)
        
        # TreeView for bets
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        
        # Create TreeView
        columns = ('Time', 'Symbol', 'Bet', 'Chance', 'Payout', 'Result', 'Profit', 'Balance')
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )
        
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        # Column headings
        col_widths = {
            'Time': 150,
            'Symbol': 80,
            'Bet': 100,
            'Chance': 80,
            'Payout': 80,
            'Result': 80,
            'Profit': 100,
            'Balance': 120
        }
        
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=col_widths.get(col, 100))
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Tags for coloring
        self.tree.tag_configure('win', background='#E8F5E9')
        self.tree.tag_configure('loss', background='#FFEBEE')
    
    def add_bet(self, bet_data: Dict[str, Any]):
        """
        Add a bet to the history.
        
        Args:
            bet_data: Dict with keys: timestamp, symbol, bet_amount, chance,
                     payout, is_win, profit, balance
        """
        self.bets.append(bet_data)
        
        # Keep only last 10,000 bets in memory
        if len(self.bets) > 10000:
            self.bets.pop(0)
        
        self.apply_filter()
    
    def apply_filter(self):
        """Apply current filter and search to bet list."""
        filter_type = self.filter_var.get()
        search_term = self.search_var.get().lower()
        
        # Filter bets
        filtered = self.bets.copy()
        
        if filter_type == 'Wins':
            filtered = [b for b in filtered if b.get('is_win', False)]
        elif filter_type == 'Losses':
            filtered = [b for b in filtered if not b.get('is_win', False)]
        elif filter_type == 'Today':
            today = datetime.now().date()
            filtered = [
                b for b in filtered
                if datetime.fromisoformat(b.get('timestamp', '')).date() == today
            ]
        elif filter_type == 'Last Hour':
            one_hour_ago = datetime.now().timestamp() - 3600
            filtered = [
                b for b in filtered
                if datetime.fromisoformat(b.get('timestamp', '')).timestamp() > one_hour_ago
            ]
        
        # Search filter
        if search_term:
            filtered = [
                b for b in filtered
                if search_term in str(b.get('symbol', '')).lower()
                or search_term in str(b.get('bet_amount', '')).lower()
            ]
        
        self.filtered_bets = filtered
        self.refresh_tree()
        self.update_stats()
    
    def refresh_tree(self):
        """Refresh the TreeView with filtered bets."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add filtered bets (most recent first)
        for bet in reversed(self.filtered_bets[-1000:]):  # Show last 1000
            values = (
                bet.get('timestamp', '')[:19],  # Trim microseconds
                bet.get('symbol', ''),
                f"{bet.get('bet_amount', 0):.8f}",
                f"{bet.get('chance', 0):.2f}%",
                f"{bet.get('payout', 0):.4f}x",
                '✅ Win' if bet.get('is_win') else '❌ Loss',
                f"{bet.get('profit', 0):+.8f}",
                f"{bet.get('balance', 0):.8f}"
            )
            
            tag = 'win' if bet.get('is_win') else 'loss'
            self.tree.insert('', 0, values=values, tags=(tag,))
    
    def update_stats(self):
        """Update statistics display."""
        total = len(self.filtered_bets)
        wins = sum(1 for b in self.filtered_bets if b.get('is_win', False))
        losses = total - wins
        win_rate = (wins / total * 100) if total > 0 else 0
        
        total_profit = sum(Decimal(str(b.get('profit', 0))) for b in self.filtered_bets)
        
        self.stats_label.config(
            text=f"Total: {total} | Wins: {wins} | Losses: {losses} | "
                 f"Win Rate: {win_rate:.1f}% | Profit: {total_profit:+.8f}"
        )
    
    def sort_by_column(self, column: str):
        """Sort tree by column."""
        # This is a placeholder - full implementation would sort filtered_bets
        # and refresh the tree
        pass
    
    def refresh(self):
        """Refresh the display."""
        self.apply_filter()
    
    def clear(self):
        """Clear all bet history."""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all bet history?"):
            self.bets.clear()
            self.filtered_bets.clear()
            self.refresh_tree()
            self.update_stats()
    
    def export_csv(self):
        """Export filtered bets to CSV."""
        if not self.filtered_bets:
            messagebox.showinfo("Export", "No bets to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.filtered_bets[0].keys())
                writer.writeheader()
                writer.writerows(self.filtered_bets)
            
            messagebox.showinfo("Export", f"Exported {len(self.filtered_bets)} bets to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def export_json(self):
        """Export filtered bets to JSON."""
        if not self.filtered_bets:
            messagebox.showinfo("Export", "No bets to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.filtered_bets, f, indent=2, default=str)
            
            messagebox.showinfo("Export", f"Exported {len(self.filtered_bets)} bets to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def load_from_file(self, filename: str):
        """Load bet history from JSON file."""
        try:
            with open(filename, 'r') as f:
                self.bets = json.load(f)
            self.apply_filter()
            messagebox.showinfo("Load", f"Loaded {len(self.bets)} bets from {filename}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load: {e}")
