#!/usr/bin/env python3
"""
Session Recovery Dialog for Tkinter GUI
Offers to restore previous betting session if interrupted
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional, Dict, Any, Callable


class SessionRecoveryDialog(tk.Toplevel):
    """
    Dialog for recovering interrupted betting sessions.
    Shows session details and offers restore option.
    """
    
    def __init__(self, parent, session_data: Dict[str, Any], 
                 on_restore: Callable = None, on_discard: Callable = None):
        """
        Initialize session recovery dialog.
        
        Args:
            parent: Parent window
            session_data: Previous session information
            on_restore: Callback when user chooses to restore
            on_discard: Callback when user chooses to discard
        """
        super().__init__(parent)
        
        self.session_data = session_data
        self.on_restore_callback = on_restore
        self.on_discard_callback = on_discard
        self.result = None
        
        self._setup_dialog()
        self._create_ui()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _setup_dialog(self):
        """Configure dialog window."""
        self.title("Session Recovery")
        self.resizable(False, False)
        self.configure(bg='#FAFAFA')
    
    def _create_ui(self):
        """Create dialog UI."""
        # Main container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Icon and title
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Warning icon
        icon_label = tk.Label(
            header_frame,
            text="⚠️",
            font=('Segoe UI', 32),
            bg='#FAFAFA'
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Title and message
        text_frame = ttk.Frame(header_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(
            text_frame,
            text="Previous Session Found",
            font=('Segoe UI', 14, 'bold')
        ).pack(anchor=tk.W)
        
        ttk.Label(
            text_frame,
            text="Would you like to restore your previous betting session?",
            font=('Segoe UI', 10),
            foreground='#757575'
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Session details
        details_frame = ttk.LabelFrame(main_frame, text="Session Details", padding=15)
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self._create_detail_row(details_frame, "Strategy:", 
                                self.session_data.get('strategy_name', 'Unknown'))
        self._create_detail_row(details_frame, "Currency:", 
                                self.session_data.get('currency', 'Unknown'))
        self._create_detail_row(details_frame, "Total Bets:", 
                                str(self.session_data.get('total_bets', 0)))
        
        # Format timestamps
        started = self.session_data.get('started_at')
        if started:
            try:
                if isinstance(started, str):
                    started_dt = datetime.fromisoformat(started)
                else:
                    started_dt = started
                started_str = started_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                started_str = str(started)
        else:
            started_str = 'Unknown'
        
        self._create_detail_row(details_frame, "Started:", started_str)
        
        # Session stats
        stats_frame = ttk.Frame(details_frame)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        wins = self.session_data.get('wins', 0)
        losses = self.session_data.get('losses', 0)
        profit = self.session_data.get('total_profit', 0)
        
        self._create_stat_card(stats_frame, "Wins", wins, "#2E7D32")
        self._create_stat_card(stats_frame, "Losses", losses, "#C62828")
        
        profit_color = "#2E7D32" if profit >= 0 else "#C62828"
        profit_text = f"{profit:+.8f}"
        self._create_stat_card(stats_frame, "Profit", profit_text, profit_color)
        
        # Warning message
        warning_frame = ttk.Frame(main_frame)
        warning_frame.pack(fill=tk.X, pady=(0, 15))
        
        warning_label = ttk.Label(
            warning_frame,
            text="⚡ Note: Restoring will continue from where you left off",
            font=('Segoe UI', 9),
            foreground='#F57C00'
        )
        warning_label.pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Discard button
        discard_btn = ttk.Button(
            button_frame,
            text="Start Fresh",
            command=self._on_discard
        )
        discard_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Restore button (accent)
        restore_btn = ttk.Button(
            button_frame,
            text="Restore Session",
            command=self._on_restore,
            style='Accent.TButton'
        )
        restore_btn.pack(side=tk.RIGHT)
    
    def _create_detail_row(self, parent, label: str, value: str):
        """Create a detail label-value row."""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        
        ttk.Label(
            row,
            text=label,
            font=('Segoe UI', 9, 'bold'),
            width=12
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            row,
            text=value,
            font=('Segoe UI', 9)
        ).pack(side=tk.LEFT)
    
    def _create_stat_card(self, parent, label: str, value, color: str):
        """Create a small stat card."""
        card = ttk.Frame(parent, relief=tk.RAISED, borderwidth=1)
        card.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
        
        ttk.Label(
            card,
            text=label,
            font=('Segoe UI', 8),
            foreground='#757575'
        ).pack(pady=(5, 0))
        
        value_label = tk.Label(
            card,
            text=str(value),
            font=('Segoe UI', 12, 'bold'),
            foreground=color,
            bg='#FFFFFF'
        )
        value_label.pack(pady=(0, 5))
    
    def _on_restore(self):
        """Handle restore action."""
        self.result = 'restore'
        if self.on_restore_callback:
            self.on_restore_callback(self.session_data)
        self.destroy()
    
    def _on_discard(self):
        """Handle discard action."""
        self.result = 'discard'
        if self.on_discard_callback:
            self.on_discard_callback()
        self.destroy()


class ConfirmationDialog(tk.Toplevel):
    """
    General purpose confirmation dialog with customizable appearance.
    """
    
    def __init__(self, parent, title: str, message: str,
                 confirm_text: str = "Confirm", cancel_text: str = "Cancel",
                 dialog_type: str = "warning", on_confirm: Callable = None):
        """
        Initialize confirmation dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Main message
            confirm_text: Text for confirm button
            cancel_text: Text for cancel button
            dialog_type: 'warning', 'error', 'info', or 'question'
            on_confirm: Callback when confirmed
        """
        super().__init__(parent)
        
        self.on_confirm_callback = on_confirm
        self.confirmed = False
        
        self._setup_dialog(title)
        self._create_ui(title, message, confirm_text, cancel_text, dialog_type)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _setup_dialog(self, title: str):
        """Configure dialog window."""
        self.title(title)
        self.resizable(False, False)
        self.configure(bg='#FAFAFA')
    
    def _create_ui(self, title: str, message: str, confirm_text: str, 
                   cancel_text: str, dialog_type: str):
        """Create dialog UI."""
        # Icon mapping
        icons = {
            'warning': ('⚠️', '#F57C00'),
            'error': ('❌', '#C62828'),
            'info': ('ℹ️', '#0288D1'),
            'question': ('❓', '#1976D2')
        }
        
        icon, color = icons.get(dialog_type, ('ℹ️', '#0288D1'))
        
        # Main container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Icon and message
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Icon
        icon_label = tk.Label(
            content_frame,
            text=icon,
            font=('Segoe UI', 32),
            bg='#FAFAFA'
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Message
        message_label = tk.Label(
            content_frame,
            text=message,
            font=('Segoe UI', 11),
            bg='#FAFAFA',
            wraplength=350,
            justify=tk.LEFT
        )
        message_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text=cancel_text,
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Confirm button
        confirm_btn = ttk.Button(
            button_frame,
            text=confirm_text,
            command=self._on_confirm,
            style='Accent.TButton'
        )
        confirm_btn.pack(side=tk.RIGHT)
        
        # Bind Enter and Escape
        self.bind('<Return>', lambda e: self._on_confirm())
        self.bind('<Escape>', lambda e: self._on_cancel())
    
    def _on_confirm(self):
        """Handle confirm action."""
        self.confirmed = True
        if self.on_confirm_callback:
            self.on_confirm_callback()
        self.destroy()
    
    def _on_cancel(self):
        """Handle cancel action."""
        self.confirmed = False
        self.destroy()
    
    @staticmethod
    def ask(parent, title: str, message: str, 
            confirm_text: str = "Confirm", cancel_text: str = "Cancel",
            dialog_type: str = "question") -> bool:
        """
        Show confirmation dialog and wait for result.
        
        Returns:
            True if confirmed, False otherwise
        """
        dialog = ConfirmationDialog(
            parent, title, message, confirm_text, cancel_text, dialog_type
        )
        parent.wait_window(dialog)
        return dialog.confirmed


class TooltipManager:
    """
    Manages tooltips for widgets.
    Shows helpful hints on hover.
    """
    
    def __init__(self):
        self.tooltips = {}
        self.current_tooltip = None
    
    def add(self, widget, text: str, delay: int = 500):
        """
        Add tooltip to widget.
        
        Args:
            widget: Widget to add tooltip to
            text: Tooltip text
            delay: Delay in ms before showing
        """
        self.tooltips[widget] = {
            'text': text,
            'delay': delay,
            'timer': None
        }
        
        widget.bind('<Enter>', lambda e: self._on_enter(widget))
        widget.bind('<Leave>', lambda e: self._on_leave(widget))
    
    def _on_enter(self, widget):
        """Handle mouse enter."""
        tooltip_data = self.tooltips.get(widget)
        if not tooltip_data:
            return
        
        # Schedule tooltip
        def show():
            self._show_tooltip(widget, tooltip_data['text'])
        
        tooltip_data['timer'] = widget.after(tooltip_data['delay'], show)
    
    def _on_leave(self, widget):
        """Handle mouse leave."""
        tooltip_data = self.tooltips.get(widget)
        if not tooltip_data:
            return
        
        # Cancel scheduled tooltip
        if tooltip_data['timer']:
            widget.after_cancel(tooltip_data['timer'])
            tooltip_data['timer'] = None
        
        # Hide current tooltip
        self._hide_tooltip()
    
    def _show_tooltip(self, widget, text: str):
        """Show tooltip near widget."""
        self._hide_tooltip()
        
        # Create tooltip window
        self.current_tooltip = tk.Toplevel(widget)
        self.current_tooltip.wm_overrideredirect(True)
        
        # Tooltip content
        label = tk.Label(
            self.current_tooltip,
            text=text,
            background='#FFFFFF',
            foreground='#212121',
            relief=tk.SOLID,
            borderwidth=1,
            font=('Segoe UI', 9),
            padx=8,
            pady=4
        )
        label.pack()
        
        # Position near widget
        x = widget.winfo_rootx() + widget.winfo_width() // 2
        y = widget.winfo_rooty() + widget.winfo_height() + 5
        self.current_tooltip.wm_geometry(f"+{x}+{y}")
    
    def _hide_tooltip(self):
        """Hide current tooltip."""
        if self.current_tooltip:
            self.current_tooltip.destroy()
            self.current_tooltip = None
