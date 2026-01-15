#!/usr/bin/env python3
"""
Settings Panel for Tkinter GUI
Comprehensive settings management with live preview
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable


class SettingsPanel(tk.Toplevel):
    """
    Complete settings management dialog.
    Organized in categories with live preview.
    """
    
    def __init__(self, parent, config_manager, on_save: Callable = None):
        """
        Initialize settings panel.
        
        Args:
            parent: Parent window
            config_manager: ConfigManager instance
            on_save: Callback when settings are saved
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.on_save_callback = on_save
        self.changes = {}
        
        self._setup_dialog()
        self._create_ui()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (600 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")
    
    def _setup_dialog(self):
        """Configure dialog window."""
        self.title("Settings")
        self.geometry("600x500")
        self.configure(bg='#FAFAFA')
    
    def _create_ui(self):
        """Create settings UI."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Frame(main_frame, padding=15)
        header.pack(fill=tk.X)
        
        ttk.Label(
            header,
            text="⚙️ Settings",
            font=('Segoe UI', 16, 'bold')
        ).pack(side=tk.LEFT)
        
        # Category navigation + content
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Left sidebar - categories
        sidebar = ttk.Frame(content_frame, width=150)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        sidebar.pack_propagate(False)
        
        # Right panel - settings
        self.settings_container = ttk.Frame(content_frame)
        self.settings_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Categories
        categories = [
            ("🎨", "Appearance"),
            ("🤖", "Betting"),
            ("🔔", "Notifications"),
            ("🔒", "Security"),
            ("⚡", "Advanced")
        ]
        
        self.category_buttons = {}
        for icon, name in categories:
            btn = ttk.Button(
                sidebar,
                text=f"{icon} {name}",
                command=lambda n=name: self._show_category(n)
            )
            btn.pack(fill=tk.X, pady=2)
            self.category_buttons[name] = btn
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame, padding=15)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="Reset to Defaults",
            command=self._reset_defaults
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self._save_settings,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT)
        
        # Show first category
        self._show_category("Appearance")
    
    def _show_category(self, category: str):
        """Show settings for a category."""
        # Clear current
        for widget in self.settings_container.winfo_children():
            widget.destroy()
        
        # Highlight selected category
        for name, btn in self.category_buttons.items():
            if name == category:
                btn.state(['pressed'])
            else:
                btn.state(['!pressed'])
        
        # Create scrollable frame
        canvas = tk.Canvas(self.settings_container, bg='#FAFAFA', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.settings_container, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Show category content
        if category == "Appearance":
            self._create_appearance_settings(scrollable_frame)
        elif category == "Betting":
            self._create_betting_settings(scrollable_frame)
        elif category == "Notifications":
            self._create_notification_settings(scrollable_frame)
        elif category == "Security":
            self._create_security_settings(scrollable_frame)
        elif category == "Advanced":
            self._create_advanced_settings(scrollable_frame)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_appearance_settings(self, parent):
        """Create appearance settings."""
        self._create_section(parent, "Theme")
        
        theme_var = tk.StringVar(value=self.config_manager.get('theme', 'light'))
        self._create_radio_group(
            parent, theme_var, 'theme',
            [('Light', 'light'), ('Dark', 'dark')]
        )
        
        self._create_section(parent, "Window")
        
        show_tooltips_var = tk.BooleanVar(
            value=self.config_manager.get('show_tooltips', True)
        )
        self._create_checkbox(
            parent, "Show tooltips", show_tooltips_var, 'show_tooltips'
        )
        
        self._create_section(parent, "Dashboard")
        
        show_welcome_var = tk.BooleanVar(
            value=self.config_manager.get('show_welcome', True)
        )
        self._create_checkbox(
            parent, "Show welcome wizard on startup", show_welcome_var, 'show_welcome'
        )
    
    def _create_betting_settings(self, parent):
        """Create betting settings."""
        self._create_section(parent, "Defaults")
        
        default_symbol_var = tk.StringVar(
            value=self.config_manager.get('last_symbol', 'DOGE')
        )
        self._create_entry(
            parent, "Default currency:", default_symbol_var, 'last_symbol'
        )
        
        default_strategy_var = tk.StringVar(
            value=self.config_manager.get('default_strategy', 'target-aware')
        )
        self._create_entry(
            parent, "Default strategy:", default_strategy_var, 'default_strategy'
        )
        
        self._create_section(parent, "Safety")
        
        confirm_bets_var = tk.BooleanVar(
            value=self.config_manager.get('confirm_bets', True)
        )
        self._create_checkbox(
            parent, "Confirm before starting bets", confirm_bets_var, 'confirm_bets'
        )
        
        confirm_stop_var = tk.BooleanVar(
            value=self.config_manager.get('confirm_stop', True)
        )
        self._create_checkbox(
            parent, "Confirm before stopping", confirm_stop_var, 'confirm_stop'
        )
        
        emergency_stop_var = tk.BooleanVar(
            value=self.config_manager.get('emergency_stop_enabled', True)
        )
        self._create_checkbox(
            parent, "Enable emergency stop (F12)", emergency_stop_var, 'emergency_stop_enabled'
        )
    
    def _create_notification_settings(self, parent):
        """Create notification settings."""
        self._create_section(parent, "Sound")
        
        sound_enabled_var = tk.BooleanVar(
            value=self.config_manager.get('sound_enabled', True)
        )
        self._create_checkbox(
            parent, "Enable sound notifications", sound_enabled_var, 'sound_enabled'
        )
        
        self._create_section(parent, "Auto-refresh")
        
        auto_refresh_var = tk.BooleanVar(
            value=self.config_manager.get('auto_refresh_balance', True)
        )
        self._create_checkbox(
            parent, "Auto-refresh balance", auto_refresh_var, 'auto_refresh_balance'
        )
        
        refresh_interval_var = tk.IntVar(
            value=self.config_manager.get('refresh_interval', 30)
        )
        self._create_spinbox(
            parent, "Refresh interval (seconds):", refresh_interval_var, 
            'refresh_interval', from_=5, to=300
        )
    
    def _create_security_settings(self, parent):
        """Create security settings."""
        self._create_section(parent, "API Key")
        
        remember_api_var = tk.BooleanVar(
            value=self.config_manager.get('remember_api_key', False)
        )
        self._create_checkbox(
            parent, "Remember API key (stored locally)", remember_api_var, 'remember_api_key'
        )
        
        self._create_section(parent, "Session")
        
        save_sessions_var = tk.BooleanVar(
            value=self.config_manager.get('save_sessions', True)
        )
        self._create_checkbox(
            parent, "Save betting sessions", save_sessions_var, 'save_sessions'
        )
    
    def _create_advanced_settings(self, parent):
        """Create advanced settings."""
        self._create_section(parent, "Performance")
        
        max_history_var = tk.IntVar(
            value=self.config_manager.get('max_bet_history', 10000)
        )
        self._create_spinbox(
            parent, "Max bet history:", max_history_var,
            'max_bet_history', from_=100, to=100000
        )
        
        self._create_section(parent, "Updates")
        
        check_updates_var = tk.BooleanVar(
            value=self.config_manager.get('check_updates_on_startup', True)
        )
        self._create_checkbox(
            parent, "Check for updates on startup", check_updates_var, 
            'check_updates_on_startup'
        )
        
        self._create_section(parent, "Logging")
        
        log_level_var = tk.StringVar(
            value=self.config_manager.get('log_level', 'INFO')
        )
        self._create_radio_group(
            parent, log_level_var, 'log_level',
            [('Debug', 'DEBUG'), ('Info', 'INFO'), ('Warning', 'WARNING'), ('Error', 'ERROR')]
        )
        
        enable_analytics_var = tk.BooleanVar(
            value=self.config_manager.get('enable_analytics', True)
        )
        self._create_checkbox(
            parent, "Enable analytics tracking", enable_analytics_var, 'enable_analytics'
        )
    
    def _create_section(self, parent, title: str):
        """Create a section header."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(15, 5))
        
        ttk.Label(
            frame,
            text=title,
            font=('Segoe UI', 11, 'bold')
        ).pack(anchor=tk.W)
        
        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))
    
    def _create_checkbox(self, parent, text: str, variable: tk.BooleanVar, config_key: str):
        """Create a checkbox setting."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        cb = ttk.Checkbutton(
            frame,
            text=text,
            variable=variable,
            command=lambda: self._on_setting_changed(config_key, variable.get())
        )
        cb.pack(anchor=tk.W, padx=10)
    
    def _create_radio_group(self, parent, variable: tk.StringVar, config_key: str, options: list):
        """Create radio button group."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5, padx=10)
        
        for text, value in options:
            rb = ttk.Radiobutton(
                frame,
                text=text,
                variable=variable,
                value=value,
                command=lambda: self._on_setting_changed(config_key, variable.get())
            )
            rb.pack(anchor=tk.W, pady=2)
    
    def _create_entry(self, parent, label: str, variable: tk.StringVar, config_key: str):
        """Create entry field."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        
        entry = ttk.Entry(frame, textvariable=variable, width=30)
        entry.pack(side=tk.LEFT, padx=(5, 0))
        entry.bind(
            '<FocusOut>',
            lambda e: self._on_setting_changed(config_key, variable.get())
        )
    
    def _create_spinbox(self, parent, label: str, variable: tk.IntVar, 
                       config_key: str, from_: int, to: int):
        """Create spinbox field."""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
        
        spinbox = ttk.Spinbox(
            frame, from_=from_, to=to, textvariable=variable, width=15,
            command=lambda: self._on_setting_changed(config_key, variable.get())
        )
        spinbox.pack(side=tk.LEFT, padx=(5, 0))
    
    def _on_setting_changed(self, key: str, value: Any):
        """Track setting changes."""
        self.changes[key] = value
    
    def _save_settings(self):
        """Save all changes."""
        if self.changes:
            self.config_manager.set_many(self.changes)
        
        if self.on_save_callback:
            self.on_save_callback(self.changes)
        
        self.destroy()
    
    def _reset_defaults(self):
        """Reset all settings to defaults."""
        from src.gui_enhancements.session_recovery_dialog import ConfirmationDialog
        
        confirmed = ConfirmationDialog.ask(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\nThis cannot be undone.",
            "Reset",
            "Cancel",
            "warning"
        )
        
        if confirmed:
            defaults = self.config_manager.default_config()
            self.config_manager.config = defaults
            self.config_manager.save()
            self.changes.clear()
            
            # Reload current category
            for name, btn in self.category_buttons.items():
                if 'pressed' in btn.state():
                    self._show_category(name)
                    break
