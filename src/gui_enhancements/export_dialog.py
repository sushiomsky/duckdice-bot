#!/usr/bin/env python3
"""
Export Dialog for Tkinter GUI
Export bet history and analytics to various formats
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class ExportDialog(tk.Toplevel):
    """
    Dialog for exporting bet data and analytics.
    Supports CSV, JSON, and formatted text.
    """
    
    def __init__(self, parent, bet_data: List[Dict[str, Any]], session_stats: Dict[str, Any] = None):
        """
        Initialize export dialog.
        
        Args:
            parent: Parent window
            bet_data: List of bet records to export
            session_stats: Optional session statistics
        """
        super().__init__(parent)
        
        self.bet_data = bet_data
        self.session_stats = session_stats or {}
        
        self._setup_dialog()
        self._create_ui()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (500 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (450 // 2)
        self.geometry(f"+{x}+{y}")
    
    def _setup_dialog(self):
        """Configure dialog window."""
        self.title("Export Data")
        self.geometry("500x450")
        self.configure(bg='#FAFAFA')
    
    def _create_ui(self):
        """Create export UI."""
        # Main container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            header_frame,
            text="📤 Export Data",
            font=('Segoe UI', 14, 'bold')
        ).pack(side=tk.LEFT)
        
        # Data summary
        summary_frame = ttk.LabelFrame(main_frame, text="Data Summary", padding=15)
        summary_frame.pack(fill=tk.X, pady=(0, 15))
        
        summary_text = f"Total Bets: {len(self.bet_data)}"
        if self.session_stats:
            wins = self.session_stats.get('wins', 0)
            losses = self.session_stats.get('losses', 0)
            profit = self.session_stats.get('total_profit', 0)
            summary_text += f"\nWins: {wins} | Losses: {losses} | Profit: {profit:.8f}"
        
        ttk.Label(
            summary_frame,
            text=summary_text,
            font=('Segoe UI', 10)
        ).pack(anchor=tk.W)
        
        # Format selection
        format_frame = ttk.LabelFrame(main_frame, text="Export Format", padding=15)
        format_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.format_var = tk.StringVar(value='csv')
        
        formats = [
            ('CSV (Comma-Separated)', 'csv', '📊'),
            ('JSON (JavaScript Object)', 'json', '📋'),
            ('TXT (Formatted Text)', 'txt', '📄')
        ]
        
        for label, value, icon in formats:
            rb = ttk.Radiobutton(
                format_frame,
                text=f"{icon} {label}",
                variable=self.format_var,
                value=value
            )
            rb.pack(anchor=tk.W, pady=3)
        
        # Options
        options_frame = ttk.LabelFrame(main_frame, text="Export Options", padding=15)
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.include_stats_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Include session statistics",
            variable=self.include_stats_var
        ).pack(anchor=tk.W, pady=2)
        
        self.include_timestamp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Include export timestamp",
            variable=self.include_timestamp_var
        ).pack(anchor=tk.W, pady=2)
        
        self.open_after_export_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Open file after export",
            variable=self.open_after_export_var
        ).pack(anchor=tk.W, pady=2)
        
        # File name preview
        preview_frame = ttk.LabelFrame(main_frame, text="File Name Preview", padding=10)
        preview_frame.pack(fill=tk.X, pady=(0, 15))
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.filename_var = tk.StringVar(
            value=f"duckdice_export_{timestamp}.{self.format_var.get()}"
        )
        
        ttk.Label(
            preview_frame,
            textvariable=self.filename_var,
            font=('Segoe UI', 9),
            foreground='#1976D2'
        ).pack(anchor=tk.W)
        
        # Update filename when format changes
        self.format_var.trace('w', lambda *args: self._update_filename())
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            button_frame,
            text="Export",
            command=self._do_export,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT)
    
    def _update_filename(self):
        """Update filename preview when format changes."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = self.format_var.get()
        self.filename_var.set(f"duckdice_export_{timestamp}.{ext}")
    
    def _do_export(self):
        """Execute the export."""
        if not self.bet_data:
            messagebox.showwarning("No Data", "No bet data to export.")
            return
        
        # Get file path
        file_types = {
            'csv': [("CSV files", "*.csv"), ("All files", "*.*")],
            'json': [("JSON files", "*.json"), ("All files", "*.*")],
            'txt': [("Text files", "*.txt"), ("All files", "*.*")]
        }
        
        format_type = self.format_var.get()
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Data",
            defaultextension=f".{format_type}",
            initialfile=self.filename_var.get(),
            filetypes=file_types.get(format_type, [("All files", "*.*")])
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Export based on format
            if format_type == 'csv':
                self._export_csv(file_path)
            elif format_type == 'json':
                self._export_json(file_path)
            elif format_type == 'txt':
                self._export_txt(file_path)
            
            # Success message
            messagebox.showinfo(
                "Export Successful",
                f"Data exported successfully to:\n{file_path}"
            )
            
            # Open file if requested
            if self.open_after_export_var.get():
                import os
                import platform
                
                if platform.system() == 'Darwin':  # macOS
                    os.system(f'open "{file_path}"')
                elif platform.system() == 'Windows':
                    os.startfile(file_path)
                else:  # Linux
                    os.system(f'xdg-open "{file_path}"')
            
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export data:\n{e}")
    
    def _export_csv(self, file_path: str):
        """Export to CSV format."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            # Add timestamp header if requested
            if self.include_timestamp_var.get():
                f.write(f"# Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Add stats header if requested
            if self.include_stats_var.get() and self.session_stats:
                f.write("# Session Statistics\n")
                for key, value in self.session_stats.items():
                    f.write(f"# {key}: {value}\n")
                f.write("\n")
            
            # Determine columns from first bet
            if self.bet_data:
                fieldnames = list(self.bet_data[0].keys())
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.bet_data)
    
    def _export_json(self, file_path: str):
        """Export to JSON format."""
        export_data = {
            'bets': self.bet_data,
        }
        
        if self.include_timestamp_var.get():
            export_data['exported_at'] = datetime.now().isoformat()
        
        if self.include_stats_var.get() and self.session_stats:
            export_data['session_stats'] = self.session_stats
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    def _export_txt(self, file_path: str):
        """Export to formatted text."""
        with open(file_path, 'w', encoding='utf-8') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write("DuckDice Bet History Export\n")
            if self.include_timestamp_var.get():
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Session stats
            if self.include_stats_var.get() and self.session_stats:
                f.write("SESSION STATISTICS\n")
                f.write("-" * 80 + "\n")
                for key, value in self.session_stats.items():
                    f.write(f"{key:.<40} {value}\n")
                f.write("\n")
            
            # Bet details
            f.write("BET HISTORY\n")
            f.write("-" * 80 + "\n\n")
            
            for i, bet in enumerate(self.bet_data, 1):
                f.write(f"Bet #{i}\n")
                for key, value in bet.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
            
            # Footer
            f.write("=" * 80 + "\n")
            f.write(f"Total bets: {len(self.bet_data)}\n")


class QuickExportMenu:
    """
    Context menu for quick export actions.
    Can be attached to tables and charts.
    """
    
    def __init__(self, parent, data_provider_callback):
        """
        Initialize quick export menu.
        
        Args:
            parent: Parent widget
            data_provider_callback: Function that returns data to export
        """
        self.parent = parent
        self.data_provider = data_provider_callback
        
        self.menu = tk.Menu(parent, tearoff=0)
        self.menu.add_command(label="📤 Export to CSV", command=lambda: self._quick_export('csv'))
        self.menu.add_command(label="📋 Export to JSON", command=lambda: self._quick_export('json'))
        self.menu.add_separator()
        self.menu.add_command(label="⚙️ Export Options...", command=self._show_export_dialog)
    
    def show(self, event):
        """Show context menu at cursor position."""
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
    
    def _quick_export(self, format_type: str):
        """Quick export without dialog."""
        data = self.data_provider()
        if not data:
            messagebox.showwarning("No Data", "No data to export.")
            return
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"duckdice_quick_export_{timestamp}.{format_type}"
        
        # Get save location
        file_path = filedialog.asksaveasfilename(
            parent=self.parent,
            title="Quick Export",
            defaultextension=f".{format_type}",
            initialfile=filename,
            filetypes=[(f"{format_type.upper()} files", f"*.{format_type}"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Use ExportDialog's export methods
            dialog = ExportDialog(self.parent, data)
            
            if format_type == 'csv':
                dialog._export_csv(file_path)
            elif format_type == 'json':
                dialog._export_json(file_path)
            
            messagebox.showinfo("Success", f"Exported to:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export:\n{e}")
    
    def _show_export_dialog(self):
        """Show full export dialog."""
        data = self.data_provider()
        if not data:
            messagebox.showwarning("No Data", "No data to export.")
            return
        
        ExportDialog(self.parent, data)
