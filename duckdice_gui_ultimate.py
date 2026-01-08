#!/usr/bin/env python3
"""
DuckDice Ultimate GUI - Outstanding UX Edition
The most intuitive and beautiful dice betting interface

Design Principles:
- Dashboard-first: Key metrics always visible
- Guided workflow: Clear path from setup to betting
- Visual feedback: Immediate response to all actions
- Smart assistance: Contextual help and validation
- Professional polish: Modern, cohesive design
"""

import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from decimal import Decimal
from typing import Optional, Dict, Any, List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from duckdice_api import DuckDiceAPI, DuckDiceConfig
from betbot_engine import run_auto_bet, EngineConfig
from betbot_strategies import list_strategies, get_strategy
# Import all strategy modules to trigger registration
from betbot_strategies import (
    classic_martingale,
    anti_martingale_streak,
    labouchere,
    dalembert,
    fibonacci,
    paroli,
    oscars_grind,
    one_three_two_six,
    rng_analysis_strategy,
    target_aware,
    faucet_cashout,
    kelly_capped,
    max_wager_flow,
    range50_random,
    fib_loss_cluster,
    custom_script
)
from gui_enhancements import (
    BetLogger,
    EnhancedBetHistoryViewer,
    StatisticsDashboard,
    EmergencyStopManager,
    SoundManager,
    LiveChartPanel,
    StrategyConfigPanel,
    AnimatedProgressBar,
    Toast,
    OnboardingWizard,
    LoadingOverlay,
    ConfirmDialog
)
from gui_enhancements.keyboard_shortcuts import KeyboardShortcutManager, ShortcutsDialog
from gui_enhancements.modern_ui import (
    ModernColorScheme,
    ModeIndicatorBanner,
    ModernButton,
    ConnectionStatusBar
)
from script_editor import ScriptEditor, DiceBotAPI
from faucet_manager import FaucetManager, FaucetConfig, CookieManager
from updater import AutoUpdater



class ModernTheme:
    """
    Professional color palette and design system.
    Inspired by Material Design 3 and modern banking apps.
    """
    
    # Primary colors
    PRIMARY = "#1976D2"          # Vibrant blue
    PRIMARY_DARK = "#1565C0"     # Darker blue
    PRIMARY_LIGHT = "#BBDEFB"    # Light blue
    
    # Semantic colors
    SUCCESS = "#2E7D32"          # Green
    SUCCESS_LIGHT = "#C8E6C9"
    ERROR = "#C62828"            # Red
    ERROR_LIGHT = "#FFCDD2"
    WARNING = "#F57C00"          # Orange
    WARNING_LIGHT = "#FFE0B2"
    INFO = "#0288D1"             # Cyan
    INFO_LIGHT = "#B3E5FC"
    
    # Neutrals
    BACKGROUND = "#FAFAFA"
    SURFACE = "#FFFFFF"
    BORDER = "#E0E0E0"
    TEXT_PRIMARY = "#212121"
    TEXT_SECONDARY = "#757575"
    TEXT_DISABLED = "#BDBDBD"
    
    # Dark mode
    DARK_BG = "#121212"
    DARK_SURFACE = "#1E1E1E"
    DARK_BORDER = "#2C2C2C"
    DARK_TEXT = "#FFFFFF"
    DARK_TEXT_SECONDARY = "#B0B0B0"
    
    # Gradients (for future use)
    GRADIENT_START = "#1976D2"
    GRADIENT_END = "#42A5F5"
    
    @classmethod
    def get_palette(cls, is_dark: bool = False):
        """Get complete color palette for theme."""
        if is_dark:
            return {
                'bg': cls.DARK_BG,
                'surface': cls.DARK_SURFACE,
                'border': cls.DARK_BORDER,
                'text': cls.DARK_TEXT,
                'text_secondary': cls.DARK_TEXT_SECONDARY,
                'primary': cls.PRIMARY,
                'success': cls.SUCCESS,
                'error': cls.ERROR,
                'warning': cls.WARNING,
                'info': cls.INFO
            }
        else:
            return {
                'bg': cls.BACKGROUND,
                'surface': cls.SURFACE,
                'border': cls.BORDER,
                'text': cls.TEXT_PRIMARY,
                'text_secondary': cls.TEXT_SECONDARY,
                'primary': cls.PRIMARY,
                'success': cls.SUCCESS,
                'error': cls.ERROR,
                'warning': cls.WARNING,
                'info': cls.INFO
            }


class ConfigManager:
    """Enhanced configuration manager with validation."""
    
    def __init__(self, config_file: str = "duckdice_ultimate_config.json"):
        self.config_file = Path.home() / ".duckdice" / config_file
        self.config_file.parent.mkdir(exist_ok=True)
        self.config = self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Validate and merge with defaults
                    defaults = self.default_config()
                    defaults.update(config)
                    return defaults
            except Exception as e:
                print(f"Error loading config: {e}")
        return self.default_config()
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def default_config(self) -> Dict[str, Any]:
        """Return default configuration with smart defaults."""
        return {
            # API Configuration
            "api_key": "",
            "base_url": "https://duckdice.io/api",
            "timeout": 30,
            "remember_api_key": False,
            
            # UI Preferences
            "theme": "light",
            "window_geometry": "1400x900",
            "window_position": None,
            "show_welcome": True,
            "show_tooltips": True,
            
            # Betting Preferences
            "last_symbol": "DOGE",
            "default_strategy": "target-aware",
            "confirm_bets": True,
            "confirm_stop": True,
            
            # Features
            "auto_refresh_balance": True,
            "refresh_interval": 30,
            "sound_enabled": True,
            "emergency_stop_enabled": True,
            "save_sessions": True,
            
            # Advanced
            "max_bet_history": 10000,
            "log_level": "INFO",
            "enable_analytics": True,
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save."""
        self.config[key] = value
        self.save()
    
    def set_many(self, updates: Dict[str, Any]) -> None:
        """Update multiple config values at once."""
        self.config.update(updates)
        self.save()


class StatusIndicator(ttk.Frame):
    """
    Animated status indicator with color coding and pulse effect.
    Shows connection status, betting status, etc.
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.status_var = tk.StringVar(value="Disconnected")
        self.color = ModernTheme.TEXT_DISABLED
        self.is_pulsing = False
        
        # Indicator dot
        self.canvas = tk.Canvas(self, width=12, height=12, 
                               highlightthickness=0, bg=ModernTheme.SURFACE)
        self.canvas.pack(side=tk.LEFT, padx=(0, 5))
        
        self.dot = self.canvas.create_oval(2, 2, 10, 10, 
                                          fill=self.color, outline="")
        
        # Status text
        self.label = ttk.Label(self, textvariable=self.status_var,
                              font=('Segoe UI', 9))
        self.label.pack(side=tk.LEFT)
    
    def set_status(self, status: str, state: str = "normal", pulse: bool = False):
        """
        Set status with color coding and optional pulse animation.
        
        Args:
            status: Status text
            state: 'connected', 'betting', 'error', 'warning', 'normal', 'success'
            pulse: Enable pulse animation
        """
        self.status_var.set(status)
        
        color_map = {
            'connected': ModernTheme.SUCCESS,
            'betting': ModernTheme.PRIMARY,
            'success': ModernTheme.SUCCESS,
            'error': ModernTheme.ERROR,
            'warning': ModernTheme.WARNING,
            'normal': ModernTheme.TEXT_DISABLED
        }
        
        self.color = color_map.get(state, ModernTheme.TEXT_DISABLED)
        self.canvas.itemconfig(self.dot, fill=self.color)
        
        # Start pulse animation if requested
        if pulse and not self.is_pulsing:
            self.is_pulsing = True
            self._pulse_animation()
        elif not pulse:
            self.is_pulsing = False
    
    def _pulse_animation(self, scale=1.0, direction=1):
        """Animate pulsing dot."""
        if not self.is_pulsing:
            # Reset to normal size
            self.canvas.coords(self.dot, 2, 2, 10, 10)
            return
        
        # Update scale
        scale += direction * 0.1
        
        # Reverse direction at limits
        if scale >= 1.3:
            direction = -1
            scale = 1.3
        elif scale <= 0.8:
            direction = 1
            scale = 0.8
        
        # Calculate new coordinates
        center = 6
        size = 4 * scale
        x1, y1 = center - size, center - size
        x2, y2 = center + size, center + size
        
        self.canvas.coords(self.dot, x1, y1, x2, y2)
        
        # Continue animation
        self.canvas.after(50, lambda: self._pulse_animation(scale, direction))


class DashboardCard(ttk.LabelFrame):
    """
    Modern card component for dashboard metrics.
    Features large value display with label, trend indicator, and animations.
    """
    
    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, text=title, padding=15, **kwargs)
        
        self.value_var = tk.StringVar(value="--")
        self.subtitle_var = tk.StringVar(value="")
        self.current_value = 0
        self.target_value = 0
        
        # Icon (optional)
        self.icon_label = ttk.Label(
            self,
            text="",
            font=('Segoe UI', 20)
        )
        self.icon_label.pack(pady=(0, 5))
        
        # Main value
        self.value_label = ttk.Label(
            self,
            textvariable=self.value_var,
            font=('Segoe UI', 24, 'bold'),
            foreground=ModernTheme.PRIMARY
        )
        self.value_label.pack(pady=(5, 0))
        
        # Subtitle
        self.subtitle_label = ttk.Label(
            self,
            textvariable=self.subtitle_var,
            font=('Segoe UI', 9),
            foreground=ModernTheme.TEXT_SECONDARY
        )
        self.subtitle_label.pack()
        
        # Trend indicator (up/down arrow)
        self.trend_var = tk.StringVar(value="")
        self.trend_label = ttk.Label(
            self,
            textvariable=self.trend_var,
            font=('Segoe UI', 12)
        )
        self.trend_label.pack(pady=(5, 0))
    
    def set_value(self, value: str, subtitle: str = "", color: str = None, 
                  trend: str = None, icon: str = None):
        """
        Update card value with optional animations.
        
        Args:
            value: Display value
            subtitle: Subtitle text
            color: Text color
            trend: Trend indicator ('up', 'down', None)
            icon: Emoji icon
        """
        self.value_var.set(value)
        self.subtitle_var.set(subtitle)
        
        if color:
            self.value_label.config(foreground=color)
        
        if icon:
            self.icon_label.config(text=icon)
        
        if trend == 'up':
            self.trend_var.set("↑ Trending Up")
            self.trend_label.config(foreground=ModernTheme.SUCCESS)
        elif trend == 'down':
            self.trend_var.set("↓ Trending Down")
            self.trend_label.config(foreground=ModernTheme.ERROR)
        else:
            self.trend_var.set("")
    
    def flash(self):
        """Flash the card to draw attention."""
        original_bg = self.cget('background')
        
        def restore_bg():
            try:
                self.config(background=original_bg)
            except:
                pass
        
        self.config(background=ModernTheme.PRIMARY_LIGHT)
        self.after(200, restore_bg)


class ModernButton(ttk.Button):
    """
    Enhanced button with icon support and loading state.
    """
    
    def __init__(self, parent, text: str, icon: str = "", **kwargs):
        # Combine icon and text
        display_text = f"{icon} {text}" if icon else text
        super().__init__(parent, text=display_text, **kwargs)
        
        self._original_text = display_text
        self._loading = False
    
    def set_loading(self, loading: bool = True):
        """Show loading state."""
        if loading and not self._loading:
            self._loading = True
            self.config(text="⏳ Loading...", state='disabled')
        elif not loading and self._loading:
            self._loading = False
            self.config(text=self._original_text, state='normal')


class TooltipManager:
    """
    Contextual tooltip system for enhanced UX.
    Shows helpful hints on hover.
    """
    
    def __init__(self):
        self.tooltip_window = None
        self.tooltips = {}
    
    def add_tooltip(self, widget, text: str):
        """Add tooltip to a widget."""
        self.tooltips[widget] = text
        widget.bind('<Enter>', lambda e: self._show_tooltip(e, text))
        widget.bind('<Leave>', lambda e: self._hide_tooltip())
    
    def _show_tooltip(self, event, text: str):
        """Show tooltip near cursor."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
        
        x = event.widget.winfo_rootx() + 20
        y = event.widget.winfo_rooty() + event.widget.winfo_height() + 5
        
        self.tooltip_window = tk.Toplevel()
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(
            self.tooltip_window,
            text=text,
            background="#FFFFDD",
            foreground="#000000",
            relief=tk.SOLID,
            borderwidth=1,
            padding=5,
            font=('Segoe UI', 9)
        )
        label.pack()
    
    def _hide_tooltip(self):
        """Hide tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class QuickStartWizard(tk.Toplevel):
    """
    First-time setup wizard for new users.
    Guides through API setup and initial configuration.
    """
    
    def __init__(self, parent, config_manager: ConfigManager):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.result = None
        
        self.title("Quick Start Setup")
        self.geometry("600x500")
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"+{x}+{y}")
        
        self._create_ui()
    
    def _create_ui(self):
        """Create wizard UI."""
        # Header
        header = ttk.Frame(self, padding=20)
        header.pack(fill=tk.X)
        
        ttk.Label(
            header,
            text="🎉 Welcome to DuckDice Bot!",
            font=('Segoe UI', 20, 'bold')
        ).pack()
        
        ttk.Label(
            header,
            text="Let's get you set up in just a few steps",
            font=('Segoe UI', 11),
            foreground=ModernTheme.TEXT_SECONDARY
        ).pack(pady=(5, 0))
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20)
        
        # Content
        content = ttk.Frame(self, padding=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Step 1: API Key
        step1 = ttk.LabelFrame(content, text="Step 1: API Connection", padding=15)
        step1.pack(fill=tk.X, pady=10)
        
        ttk.Label(
            step1,
            text="Enter your DuckDice API key to get started:",
            font=('Segoe UI', 10)
        ).pack(anchor=tk.W, pady=(0, 10))
        
        self.api_key_var = tk.StringVar()
        api_entry = ttk.Entry(step1, textvariable=self.api_key_var, 
                             show="*", width=50, font=('Consolas', 10))
        api_entry.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            step1,
            text="💡 Get your API key from DuckDice.io → Account → API",
            font=('Segoe UI', 9),
            foreground=ModernTheme.TEXT_SECONDARY
        ).pack(anchor=tk.W)
        
        self.remember_key_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            step1,
            text="Remember my API key (saved securely)",
            variable=self.remember_key_var
        ).pack(anchor=tk.W, pady=(10, 0))
        
        # Step 2: Preferences
        step2 = ttk.LabelFrame(content, text="Step 2: Preferences (Optional)", padding=15)
        step2.pack(fill=tk.X, pady=10)
        
        prefs_grid = ttk.Frame(step2)
        prefs_grid.pack(fill=tk.X)
        
        self.sound_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            prefs_grid,
            text="🔊 Enable sound notifications",
            variable=self.sound_var
        ).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.emergency_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            prefs_grid,
            text="🚨 Enable emergency stop (Ctrl+Shift+S)",
            variable=self.emergency_var
        ).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.tooltips_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            prefs_grid,
            text="💬 Show helpful tooltips",
            variable=self.tooltips_var
        ).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # Footer buttons
        footer = ttk.Frame(self, padding=20)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(
            footer,
            text="Skip Setup",
            command=self._skip
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            footer,
            text="Complete Setup →",
            command=self._complete,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT)
    
    def _complete(self):
        """Complete setup and save settings."""
        api_key = self.api_key_var.get().strip()
        
        if not api_key:
            messagebox.showwarning(
                "API Key Required",
                "Please enter your API key to continue.\n\n"
                "You can get one from DuckDice.io → Account → API"
            )
            return
        
        # Save configuration
        self.config_manager.set_many({
            'api_key': api_key if self.remember_key_var.get() else "",
            'remember_api_key': self.remember_key_var.get(),
            'sound_enabled': self.sound_var.get(),
            'emergency_stop_enabled': self.emergency_var.get(),
            'show_tooltips': self.tooltips_var.get(),
            'show_welcome': False
        })
        
        self.result = {
            'api_key': api_key,
            'completed': True
        }
        
        self.destroy()
    
    def _skip(self):
        """Skip setup wizard."""
        if messagebox.askyesno(
            "Skip Setup",
            "Are you sure you want to skip setup?\n\n"
            "You'll need to configure API settings manually."
        ):
            self.config_manager.set('show_welcome', False)
            self.result = {'completed': False}
            self.destroy()


# To be continued in next part...
# This is the foundation - I'll continue with the main GUI class


class UltimateGUI(tk.Tk):
    """
    The ultimate DuckDice betting interface.
    Features dashboard-first design, guided workflows, and outstanding UX.
    """
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config_manager = ConfigManager()
        
        # Initialize components
        self.api = None
        self.bet_logger = BetLogger()
        self.tooltip_manager = TooltipManager()
        self.emergency_stop = None
        self.sound_manager = None
        self.shortcut_manager = KeyboardShortcutManager(self)
        self.faucet_manager = None  # Initialized when API connected
        self.auto_updater = AutoUpdater(callback=self._update_log)
        
        # State
        self.current_session_id = None
        self.is_betting = False
        self.is_simulation = False
        self.betting_mode = "main"  # "main" or "faucet"
        # Load cached currencies or use defaults
        cached = self.config_manager.get('cached_currencies', None)
        self.available_currencies = cached if cached else ["BTC", "ETH", "DOGE", "LTC", "TRX", "XRP"]
        
        # Setup UI
        self._setup_window()
        self._apply_theme()
        self._create_menu()
        self._create_ui()
        
        # Post-init
        self._setup_emergency_stop()
        self._setup_sound()
        self._setup_keyboard_shortcuts()
        self._load_saved_state()
        
        # Show enhanced welcome wizard for first-time users
        if self.config_manager.get('show_welcome', True):
            self.after(500, self._show_welcome_wizard)
        
        # Check for updates on startup (async)
        if self.config_manager.get('check_updates_on_startup', True):
            self.after(2000, lambda: self.auto_updater.check_updates_async(self))
    
    def _setup_window(self):
        """Configure main window."""
        self.title("DuckDice Bot - Ultimate Edition")
        
        # Geometry
        geometry = self.config_manager.get('window_geometry', '1400x900')
        self.geometry(geometry)
        
        # Center window if no saved position
        if not self.config_manager.get('window_position'):
            self.update_idletasks()
            x = (self.winfo_screenwidth() // 2) - (1400 // 2)
            y = (self.winfo_screenheight() // 2) - (900 // 2)
            self.geometry(f"+{x}+{y}")
        
        # Icon (if available)
        try:
            # self.iconbitmap('icon.ico')
            pass
        except:
            pass
        
        # Window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _apply_theme(self):
        """Apply modern theme."""
        style = ttk.Style()
        
        # Use modern theme
        available_themes = style.theme_names()
        if 'vista' in available_themes:
            style.theme_use('vista')
        elif 'clam' in available_themes:
            style.theme_use('clam')
        
        # Custom styles
        is_dark = self.config_manager.get('theme') == 'dark'
        palette = ModernTheme.get_palette(is_dark)
        
        # Configure ttk styles
        style.configure('TFrame', background=palette['bg'])
        style.configure('TLabel', background=palette['bg'], 
                       foreground=palette['text'])
        style.configure('TButton', padding=8)
        
        # Accent button
        style.configure('Accent.TButton',
                       foreground=ModernTheme.SURFACE,
                       background=ModernTheme.PRIMARY,
                       borderwidth=0,
                       focuscolor='none',
                       padding=10)
        
        # Success button
        style.configure('Success.TButton',
                       foreground=ModernTheme.SURFACE,
                       background=ModernTheme.SUCCESS)
        
        # Danger button
        style.configure('Danger.TButton',
                       foreground=ModernTheme.SURFACE,
                       background=ModernTheme.ERROR)
        
        self.configure(bg=palette['bg'])
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Session", command=self._new_session,
                             accelerator="Ctrl+N")
        file_menu.add_command(label="Export Session...", command=self._export_session,
                             accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self._show_settings,
                             accelerator="Ctrl+,")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing,
                             accelerator="Ctrl+Q")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Balances", command=self._refresh_balances,
                             accelerator="F5")
        view_menu.add_command(label="Refresh Currencies", command=self._refresh_currencies,
                             accelerator="F6")
        view_menu.add_command(label="Toggle Theme", command=self._toggle_theme)
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Tooltips",
                                  variable=tk.BooleanVar(
                                      value=self.config_manager.get('show_tooltips', True)
                                  ),
                                  command=self._toggle_tooltips)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Test API Connection", command=self._test_connection)
        tools_menu.add_command(label="Clear Bet History...", command=self._clear_history)
        tools_menu.add_separator()
        tools_menu.add_command(label="Emergency Stop Test", command=self._test_emergency_stop)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Check for Updates...", command=self._check_for_updates)
        help_menu.add_separator()
        help_menu.add_command(label="Quick Start Guide", command=self._show_quick_start)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        
        # Bind keyboard shortcuts
        self.bind_all('<Control-n>', lambda e: self._new_session())
        self.bind_all('<Control-e>', lambda e: self._export_session())
        self.bind_all('<Control-comma>', lambda e: self._show_settings())
        self.bind_all('<Control-q>', lambda e: self._on_closing())
        self.bind_all('<F5>', lambda e: self._refresh_balances())
        self.bind_all('<F6>', lambda e: self._refresh_currencies())
    
    def _create_ui(self):
        """Create main UI layout."""
        # Main container
        main_container = ttk.Frame(self, padding=0)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # ===== MODE INDICATOR BANNER (TOP) =====
        self.mode_banner = ModeIndicatorBanner(main_container)
        self.mode_banner.pack(fill=tk.X, padx=10, pady=10)
        
        # Top bar (status and quick actions)
        self._create_top_bar(main_container)
        
        # Main content area with sidebar
        content_area = ttk.Frame(main_container)
        content_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Left sidebar (navigation and quick stats)
        self._create_sidebar(content_area)
        
        # Right main panel (dashboard and tabs)
        self._create_main_panel(content_area)
        
        # ===== CONNECTION STATUS BAR (BOTTOM) =====
        self.status_bar = ConnectionStatusBar(main_container)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Old status bar (keeping for backwards compatibility temporarily)
        # self._create_status_bar(main_container)
    
    def _create_top_bar(self, parent):
        """Create top bar with connection status and quick actions."""
        top_bar = ttk.Frame(parent, padding=10)
        top_bar.pack(fill=tk.X)
        
        # Left: Connection status
        left_frame = ttk.Frame(top_bar)
        left_frame.pack(side=tk.LEFT)
        
        self.connection_status = StatusIndicator(left_frame)
        self.connection_status.pack(side=tk.LEFT, padx=(0, 20))
        self.connection_status.set_status("Not connected", "normal")
        
        self.betting_status = StatusIndicator(left_frame)
        self.betting_status.pack(side=tk.LEFT)
        self.betting_status.set_status("Idle", "normal")
        
        # Right: Quick actions
        right_frame = ttk.Frame(top_bar)
        right_frame.pack(side=tk.RIGHT)
        
        self.quick_connect_btn = ModernButton(
            right_frame,
            text="Connect",
            icon="🔌",
            command=self._quick_connect,
            style='Accent.TButton'
        )
        self.quick_connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.quick_refresh_btn = ModernButton(
            right_frame,
            text="Refresh",
            icon="🔄",
            command=self._refresh_balances
        )
        self.quick_refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)
    
    def _create_sidebar(self, parent):
        """Create left sidebar with navigation and stats."""
        sidebar = ttk.Frame(parent, width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)
        
        # Title
        ttk.Label(
            sidebar,
            text="DuckDice Bot",
            font=('Segoe UI', 16, 'bold'),
            foreground=ModernTheme.PRIMARY
        ).pack(pady=(10, 20))
        
        # Quick stats cards
        stats_frame = ttk.LabelFrame(sidebar, text="Quick Stats", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stat_balance = self._create_stat_row(stats_frame, "💰", "Balance", "--")
        self.stat_profit = self._create_stat_row(stats_frame, "📈", "Session Profit", "--")
        self.stat_winrate = self._create_stat_row(stats_frame, "🎯", "Win Rate", "--")
        
        # Navigation
        nav_frame = ttk.LabelFrame(sidebar, text="Navigation", padding=10)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.nav_dashboard_btn = ttk.Button(
            nav_frame,
            text="📊 Dashboard",
            command=lambda: self._switch_view('dashboard'),
            width=20
        )
        self.nav_dashboard_btn.pack(fill=tk.X, pady=2)
        
        self.nav_betting_btn = ttk.Button(
            nav_frame,
            text="🎲 Quick Bet",
            command=lambda: self._switch_view('betting'),
            width=20
        )
        self.nav_betting_btn.pack(fill=tk.X, pady=2)
        
        self.nav_auto_btn = ttk.Button(
            nav_frame,
            text="🤖 Auto Bet",
            command=lambda: self._switch_view('auto'),
            width=20
        )
        self.nav_auto_btn.pack(fill=tk.X, pady=2)
        
        self.nav_history_btn = ttk.Button(
            nav_frame,
            text="📜 History",
            command=lambda: self._switch_view('history'),
            width=20
        )
        self.nav_history_btn.pack(fill=tk.X, pady=2)
        
        self.nav_stats_btn = ttk.Button(
            nav_frame,
            text="📈 Statistics",
            command=lambda: self._switch_view('statistics'),
            width=20
        )
        self.nav_stats_btn.pack(fill=tk.X, pady=2)
        
        # Mode toggle
        mode_frame = ttk.LabelFrame(sidebar, text="Mode", padding=10)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mode_var = tk.StringVar(value='live')
        ttk.Radiobutton(
            mode_frame,
            text="💰 Live Betting",
            variable=self.mode_var,
            value='live',
            command=self._on_mode_changed
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            mode_frame,
            text="🧪 Simulation",
            variable=self.mode_var,
            value='simulation',
            command=self._on_mode_changed
        ).pack(anchor=tk.W, pady=2)
    
    def _create_stat_row(self, parent, icon, label, value):
        """Create a stat row in sidebar."""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=5)
        
        ttk.Label(row, text=icon, font=('Segoe UI', 12)).pack(side=tk.LEFT)
        ttk.Label(row, text=label, font=('Segoe UI', 9),
                 foreground=ModernTheme.TEXT_SECONDARY).pack(side=tk.LEFT, padx=5)
        
        value_var = tk.StringVar(value=value)
        ttk.Label(row, textvariable=value_var, font=('Segoe UI', 10, 'bold')).pack(side=tk.RIGHT)
        
        return value_var
    
    def _create_main_panel(self, parent):
        """Create main content panel."""
        main_panel = ttk.Frame(parent)
        main_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create notebook for different views
        self.notebook = ttk.Notebook(main_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Dashboard tab
        self.dashboard_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.dashboard_tab, text="📊 Dashboard")
        self._create_dashboard(self.dashboard_tab)
        
        # Quick bet tab
        self.betting_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.betting_tab, text="🎲 Quick Bet")
        self._create_quick_bet_tab(self.betting_tab)
        
        # Auto bet tab
        self.auto_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.auto_tab, text="🤖 Auto Bet")
        self._create_auto_bet_tab(self.auto_tab)
        
        # History tab
        self.history_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.history_tab, text="📜 History")
        self._create_history_tab(self.history_tab)
        
        # Statistics tab
        self.stats_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.stats_tab, text="📈 Statistics")
        self._create_statistics_tab(self.stats_tab)
        
        # Script Editor tab
        self.script_tab = ttk.Frame(self.notebook, padding=0)
        self.notebook.add(self.script_tab, text="📝 Script Editor")
        self._create_script_editor_tab(self.script_tab)
    
    def _create_dashboard(self, parent):
        """Create main dashboard view."""
        # Title
        ttk.Label(
            parent,
            text="Dashboard",
            font=('Segoe UI', 20, 'bold')
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Metric cards grid
        cards_frame = ttk.Frame(parent)
        cards_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Configure grid - now 5 columns for main + faucet balances
        for i in range(5):
            cards_frame.columnconfigure(i, weight=1, uniform='card')
        
        # Create cards
        self.card_main_balance = DashboardCard(cards_frame, "💰 Main Balance")
        self.card_main_balance.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        self.card_faucet_balance = DashboardCard(cards_frame, "🚰 Faucet Balance")
        self.card_faucet_balance.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.card_profit = DashboardCard(cards_frame, "Session Profit")
        self.card_profit.grid(row=0, column=2, padx=5, pady=5, sticky='ew')
        
        self.card_bets = DashboardCard(cards_frame, "Total Bets")
        self.card_bets.grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        
        self.card_winrate = DashboardCard(cards_frame, "Win Rate")
        self.card_winrate.grid(row=0, column=4, padx=5, pady=5, sticky='ew')
        
        # Keep old card for compatibility
        self.card_balance = self.card_main_balance
        
        # Chart area
        chart_frame = ttk.LabelFrame(parent, text="Profit/Loss Chart", padding=10)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.main_chart = LiveChartPanel(chart_frame, max_points=500)
        self.main_chart.pack(fill=tk.BOTH, expand=True)
    
    def _create_quick_bet_tab(self, parent):
        """Create quick bet tab for manual betting."""
        # Main container
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Left: Bet controls
        left_frame = ttk.Frame(container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Title
        ttk.Label(
            left_frame,
            text="Quick Bet",
            font=('Segoe UI', 20, 'bold')
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Bet Configuration
        config_frame = ttk.LabelFrame(left_frame, text="Bet Configuration", padding=15)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Mode selection (Main / Faucet)
        ttk.Label(config_frame, text="Mode:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.qb_mode_var = tk.StringVar(value=self.betting_mode)
        mode_combo = ttk.Combobox(
            config_frame,
            textvariable=self.qb_mode_var,
            values=["main", "faucet"],
            state='readonly',
            width=15
        )
        mode_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        mode_combo.bind('<<ComboboxSelected>>', self._on_qb_mode_changed)
        
        # Currency selection
        ttk.Label(config_frame, text="Currency:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.qb_symbol_var = tk.StringVar(value="DOGE")
        symbol_combo = ttk.Combobox(
            config_frame,
            textvariable=self.qb_symbol_var,
            values=self.available_currencies,
            state='readonly',
            width=15
        )
        symbol_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        self.qb_symbol_combo = symbol_combo  # Store reference for updating
        
        # Faucet claim button (only visible in faucet mode)
        self.qb_claim_btn = ttk.Button(
            config_frame,
            text="🚰 Claim Faucet",
            command=self._claim_faucet_now,
            width=20
        )
        self.qb_claim_label = ttk.Label(config_frame, text="", foreground="gray")
        
        # Bet amount
        ttk.Label(config_frame, text="Bet Amount:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.qb_amount_var = tk.StringVar(value="1.0")
        amount_entry = ttk.Entry(config_frame, textvariable=self.qb_amount_var, width=18)
        amount_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Win chance
        ttk.Label(config_frame, text="Win Chance %:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.qb_chance_var = tk.StringVar(value="50.0")
        chance_entry = ttk.Entry(config_frame, textvariable=self.qb_chance_var, width=18)
        chance_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Chance presets
        preset_frame = ttk.Frame(config_frame)
        preset_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        for chance in [10, 25, 50, 75, 90]:
            ttk.Button(
                preset_frame,
                text=f"{chance}%",
                command=lambda c=chance: self.qb_chance_var.set(str(c)),
                width=6
            ).pack(side=tk.LEFT, padx=2)
        
        # High/Low selection
        ttk.Label(config_frame, text="Bet Type:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.qb_is_high_var = tk.BooleanVar(value=True)
        
        bet_type_frame = ttk.Frame(config_frame)
        bet_type_frame.grid(row=5, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(
            bet_type_frame,
            text="Roll High",
            variable=self.qb_is_high_var,
            value=True
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Radiobutton(
            bet_type_frame,
            text="Roll Low",
            variable=self.qb_is_high_var,
            value=False
        ).pack(side=tk.LEFT)
        
        # Calculated payout
        calc_frame = ttk.LabelFrame(left_frame, text="Bet Info", padding=15)
        calc_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.qb_payout_var = tk.StringVar(value="2.00x")
        ttk.Label(calc_frame, text="Payout Multiplier:").pack(side=tk.LEFT)
        ttk.Label(
            calc_frame,
            textvariable=self.qb_payout_var,
            font=('Segoe UI', 12, 'bold'),
            foreground=ModernTheme.PRIMARY
        ).pack(side=tk.RIGHT)
        
        # Auto-update payout when chance changes
        self.qb_chance_var.trace_add('write', lambda *args: self._update_quick_bet_payout())
        self._update_quick_bet_payout()
        
        # Bet button
        self.qb_bet_btn = ModernButton(
            left_frame,
            text="Place Bet",
            icon="🎲",
            command=self._place_quick_bet
        )
        self.qb_bet_btn.pack(fill=tk.X, pady=10)
        
        # Right: Result display and chart
        right_frame = ttk.Frame(container)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Balance display
        balance_frame = ttk.LabelFrame(right_frame, text="Balance", padding=15)
        balance_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.qb_balance_var = tk.StringVar(value="--")
        ttk.Label(
            balance_frame,
            textvariable=self.qb_balance_var,
            font=('Segoe UI', 18, 'bold'),
            foreground=ModernTheme.PRIMARY
        ).pack()
        
        # Last bet result
        result_frame = ttk.LabelFrame(right_frame, text="Last Bet Result", padding=15)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.qb_result_text = tk.Text(
            result_frame,
            height=10,
            wrap=tk.WORD,
            font=('Consolas', 10),
            state=tk.DISABLED
        )
        self.qb_result_text.pack(fill=tk.BOTH, expand=True)
        
        # Mini chart
        from gui_enhancements.tkinter_chart import TkinterLiveChart
        chart_frame = ttk.LabelFrame(right_frame, text="Balance History", padding=5)
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.qb_chart = TkinterLiveChart(chart_frame, max_points=50)
        self.qb_chart.pack(fill=tk.BOTH, expand=True)
    
    def _update_quick_bet_payout(self):
        """Update payout multiplier based on chance."""
        try:
            chance = Decimal(self.qb_chance_var.get())
            if 0 < chance < 100:
                payout = Decimal("100") / chance
                self.qb_payout_var.set(f"{payout:.2f}x")
            else:
                self.qb_payout_var.set("Invalid")
        except:
            self.qb_payout_var.set("--")
    
    def _place_quick_bet(self):
        """Place a quick bet."""
        try:
            # Get bet parameters
            symbol = self.qb_symbol_var.get()
            amount = Decimal(self.qb_amount_var.get())
            chance = Decimal(self.qb_chance_var.get())
            is_high = self.qb_is_high_var.get()
            
            # Validate
            if amount <= 0:
                Toast.show(self, "Bet amount must be positive", toast_type="error")
                return
            
            if not (0 < chance < 100):
                Toast.show(self, "Chance must be between 0 and 100", toast_type="error")
                return
            
            # Determine if simulation mode
            is_simulation = self.sim_mode_var.get() if hasattr(self, 'sim_mode_var') else True
            
            # Place bet
            if is_simulation or not self.api:
                result = self._place_simulated_quick_bet(symbol, amount, chance, is_high)
            else:
                result = self._place_live_quick_bet(symbol, amount, chance, is_high)
            
            # Update UI
            self._update_quick_bet_result(result)
            
        except ValueError as e:
            Toast.show(self, f"Invalid input: {e}", toast_type="error")
        except Exception as e:
            Toast.show(self, f"Bet failed: {e}", toast_type="error")
    
    def _place_simulated_quick_bet(self, symbol: str, amount: Decimal, chance: Decimal, is_high: bool):
        """Place a simulated bet."""
        from simulation_engine import SimulationEngine
        
        # Initialize simulation engine if needed
        if not hasattr(self, 'qb_sim_engine'):
            self.qb_sim_engine = SimulationEngine(Decimal("100.0"))
        
        # Calculate payout
        payout = Decimal("100") / chance
        
        # Place bet
        result = self.qb_sim_engine.place_bet(amount, chance, payout, is_high)
        
        # Log to database
        bet_data = {
            'session_id': self.current_session_id or 'quick-bet',
            'symbol': symbol,
            'strategy': 'manual',
            'bet_amount': amount,
            'chance': chance,
            'payout': payout,
            'is_high': is_high,
            'is_win': result['is_win'],
            'profit': result['profit'],
            'balance': result['balance']
        }
        
        self.bet_logger.log_bet(bet_data, is_simulation=True)
        
        # Update chart
        self.qb_chart.add_data_point(result['balance'], result['is_win'])
        
        # Update balance display
        self.qb_balance_var.set(f"{result['balance']:.8f} {symbol}")
        
        return result
    
    def _place_live_quick_bet(self, symbol: str, amount: Decimal, chance: Decimal, is_high: bool):
        """Place a live bet via API."""
        try:
            # Place bet through API
            result = self.api.place_bet(symbol, amount, chance, is_high)
            
            # Get current balance
            balance = Decimal(result['balance'])
            
            # Log to database
            bet_data = {
                'session_id': self.current_session_id or 'quick-bet',
                'symbol': symbol,
                'strategy': 'manual',
                'bet_amount': amount,
                'chance': chance,
                'payout': Decimal(result['payout']),
                'is_high': is_high,
                'is_win': result['win'],
                'profit': Decimal(result['profit']),
                'balance': balance,
                'roll_value': Decimal(result['roll']),
                'target_value': Decimal(result['target'])
            }
            
            self.bet_logger.log_bet(bet_data, is_simulation=False)
            
            # Update chart
            self.qb_chart.add_data_point(balance, result['win'])
            
            # Update balance display
            self.qb_balance_var.set(f"{balance:.8f} {symbol}")
            
            # Format result for display
            return {
                'is_win': result['win'],
                'profit': Decimal(result['profit']),
                'balance': balance,
                'roll_value': Decimal(result['roll']),
                'target_value': Decimal(result['target']),
                'bet_amount': amount,
                'chance': chance
            }
            
        except Exception as e:
            raise Exception(f"API error: {e}")
    
    def _update_quick_bet_result(self, result: dict):
        """Update result display."""
        outcome = "WIN" if result['is_win'] else "LOSS"
        outcome_color = "green" if result['is_win'] else "red"
        
        text = f"""
╔════════════════════════════════════════╗
║           BET RESULT: {outcome:4s}          ║
╚════════════════════════════════════════╝

Roll:      {result.get('roll_value', 0):.2f}
Target:    {result.get('target_value', 0):.2f}
Profit:    {result['profit']:+.8f}
Balance:   {result['balance']:.8f}

Bet:       {result.get('bet_amount', 0):.8f}
Chance:    {result.get('chance', 0):.2f}%
"""
        
        self.qb_result_text.config(state=tk.NORMAL)
        self.qb_result_text.delete(1.0, tk.END)
        self.qb_result_text.insert(1.0, text)
        self.qb_result_text.config(state=tk.DISABLED)
        
        # Show toast
        if result['is_win']:
            Toast.show(self, f"WIN! +{result['profit']:.4f}", toast_type="success")
        else:
            Toast.show(self, f"Loss: {result['profit']:.4f}", toast_type="error")
    
    def _create_auto_bet_tab(self, parent):
        """Create auto bet tab with strategy configuration."""
        # Title
        ttk.Label(
            parent,
            text="Automated Betting",
            font=('Segoe UI', 20, 'bold')
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Main container with two columns
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Left column: Strategy selection and config
        left_frame = ttk.Frame(content)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Strategy selection frame
        strategy_select_frame = ttk.LabelFrame(left_frame, text="Select Strategy", padding=15)
        strategy_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Strategy dropdown
        ttk.Label(strategy_select_frame, text="Strategy:", 
                 font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        strategy_frame = ttk.Frame(strategy_select_frame)
        strategy_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(
            strategy_frame,
            textvariable=self.strategy_var,
            state='readonly',
            font=('Segoe UI', 10),
            width=40
        )
        self.strategy_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Populate strategies with risk indicators
        self.available_strategies = list_strategies()
        self.strategy_names = []
        self.strategy_display_names = []
        
        # Risk level emoji indicators
        risk_emoji = {
            'Very Low': '🟢',
            'Low': '🟢',
            'Medium': '🟡',
            'High': '🟠',
            'Very High': '🔴',
            'Variable': '⚪'
        }
        
        for s in self.available_strategies:
            name = s['name']
            self.strategy_names.append(name)
            
            # Try to get metadata for risk indicator
            try:
                from src.betbot_strategies import get_strategy
                strategy_class = get_strategy(name)
                if hasattr(strategy_class, 'metadata'):
                    metadata = strategy_class.metadata()
                    emoji = risk_emoji.get(metadata.risk_level, '⚪')
                    display_name = f"{emoji} {name}"
                else:
                    display_name = f"⚪ {name}"
            except:
                display_name = f"⚪ {name}"
            
            self.strategy_display_names.append(display_name)
        
        self.strategy_combo['values'] = self.strategy_display_names
        if self.strategy_display_names:
            self.strategy_combo.current(0)
            self.strategy_var.set(self.strategy_display_names[0])
        
        # Refresh button
        ttk.Button(
            strategy_frame,
            text="ℹ️ Info",
            command=self._show_strategy_info,
            width=10
        ).pack(side=tk.LEFT)
        
        # Bind strategy selection change
        self.strategy_combo.bind('<<ComboboxSelected>>', self._on_strategy_selected)
        
        # Strategy configuration panel
        config_frame = ttk.LabelFrame(left_frame, text="Strategy Configuration", padding=15)
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        self.strategy_config_panel = StrategyConfigPanel(config_frame)
        self.strategy_config_panel.pack(fill=tk.BOTH, expand=True)
        
        # Load initial strategy
        if self.strategy_names:
            self._on_strategy_selected()
        
        # Right column: Controls and status
        right_frame = ttk.Frame(content, width=350)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        right_frame.pack_propagate(False)
        
        # Bet settings
        bet_settings_frame = ttk.LabelFrame(right_frame, text="Bet Settings", padding=15)
        bet_settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Mode selection (Main / Faucet)
        ttk.Label(bet_settings_frame, text="Betting Mode:",
                 font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.ab_mode_var = tk.StringVar(value=self.betting_mode)
        mode_combo = ttk.Combobox(
            bet_settings_frame,
            textvariable=self.ab_mode_var,
            values=["main", "faucet"],
            state='readonly',
            width=13
        )
        mode_combo.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        mode_combo.bind('<<ComboboxSelected>>', self._on_ab_mode_changed)
        
        # House edge display
        self.ab_house_edge_label = ttk.Label(
            bet_settings_frame,
            text="House Edge: 1%",
            font=('Segoe UI', 8),
            foreground="gray"
        )
        self.ab_house_edge_label.grid(row=0, column=2, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Max bets
        ttk.Label(bet_settings_frame, text="Max Bets (0 = unlimited):",
                 font=('Segoe UI', 9)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_bets_var = tk.StringVar(value="0")
        ttk.Entry(bet_settings_frame, textvariable=self.max_bets_var,
                 width=15).grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Stop on profit
        ttk.Label(bet_settings_frame, text="Stop on Profit:",
                 font=('Segoe UI', 9)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.stop_profit_var = tk.StringVar(value="")
        ttk.Entry(bet_settings_frame, textvariable=self.stop_profit_var,
                 width=15).grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Stop on loss
        ttk.Label(bet_settings_frame, text="Stop on Loss:",
                 font=('Segoe UI', 9)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.stop_loss_var = tk.StringVar(value="")
        ttk.Entry(bet_settings_frame, textvariable=self.stop_loss_var,
                 width=15).grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Simulation mode checkbox
        self.sim_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            bet_settings_frame,
            text="Simulation Mode (Test Only)",
            variable=self.sim_mode_var,
            command=self._on_sim_mode_changed
        ).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        
        # Control buttons
        control_frame = ttk.LabelFrame(right_frame, text="Controls", padding=15)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_auto_btn = ModernButton(
            control_frame,
            text="Start Auto Bet",
            icon="▶️",
            command=self._start_auto_betting,
            style='Accent.TButton'
        )
        self.start_auto_btn.pack(fill=tk.X, pady=5)
        
        self.stop_auto_btn = ModernButton(
            control_frame,
            text="Stop Betting",
            icon="⏹️",
            command=self._stop_auto_betting,
            state=tk.DISABLED
        )
        self.stop_auto_btn.pack(fill=tk.X, pady=5)
        
        self.pause_auto_btn = ModernButton(
            control_frame,
            text="Pause",
            icon="⏸️",
            command=self._pause_auto_betting,
            state=tk.DISABLED
        )
        self.pause_auto_btn.pack(fill=tk.X, pady=5)
        
        # Status display
        status_frame = ttk.LabelFrame(right_frame, text="Status", padding=15)
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.auto_status_text = tk.Text(
            status_frame,
            height=10,
            wrap=tk.WORD,
            font=('Consolas', 9),
            state=tk.DISABLED,
            bg=ModernTheme.BACKGROUND
        )
        self.auto_status_text.pack(fill=tk.BOTH, expand=True)
        
        # Add initial status message
        self._update_auto_status("Ready to start automated betting.\nSelect a strategy and configure parameters.")
    
    def _on_strategy_selected(self, event=None):
        """Handle strategy selection change."""
        display_name = self.strategy_var.get()
        if display_name:
            # Extract actual strategy name (remove emoji prefix)
            strategy_name = display_name.split(' ', 1)[1] if ' ' in display_name else display_name
            
            try:
                # Get strategy class
                strategy_class = get_strategy(strategy_name)
                # Load strategy configuration into panel
                self.strategy_config_panel.load_strategy(strategy_name, strategy_class)
                
                # Show risk info in status
                if hasattr(strategy_class, 'metadata'):
                    metadata = strategy_class.metadata()
                    risk_msg = f"Risk: {metadata.risk_level} | Bankroll: {metadata.bankroll_required}"
                    self._update_auto_status(f"Loaded: {strategy_name}\n{risk_msg}\nConfigure parameters and click Start.")
                else:
                    self._update_auto_status(f"Loaded strategy: {strategy_name}\nConfigure parameters and click Start.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load strategy: {e}")
                self._update_auto_status(f"Error loading strategy: {e}")
    
    def _show_strategy_info(self):
        """Show comprehensive information about selected strategy."""
        display_name = self.strategy_var.get()
        if not display_name:
            return
        
        # Extract actual strategy name (remove emoji prefix)
        strategy_name = display_name.split(' ', 1)[1] if ' ' in display_name else display_name
        
        try:
            strategy_class = get_strategy(strategy_name)
            
            # Create custom dialog window
            info_window = tk.Toplevel(self)
            info_window.title(f"Strategy Guide: {strategy_name.title()}")
            info_window.geometry("700x800")
            info_window.configure(bg='#FFFFFF')
            
            # Make modal
            info_window.transient(self)
            info_window.grab_set()
            
            # Main scrollable container
            canvas = tk.Canvas(info_window, bg='#FFFFFF', highlightthickness=0)
            scrollbar = ttk.Scrollbar(info_window, orient=tk.VERTICAL, command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW)
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Content container
            content = ttk.Frame(scrollable_frame, padding=20)
            content.pack(fill=tk.BOTH, expand=True)
            
            # Header
            header_frame = tk.Frame(content, bg='#1976D2', padx=20, pady=15)
            header_frame.pack(fill=tk.X, pady=(0, 20))
            
            title_label = tk.Label(
                header_frame,
                text=strategy_name.replace('-', ' ').title(),
                font=('Segoe UI', 20, 'bold'),
                fg='#FFFFFF',
                bg='#1976D2'
            )
            title_label.pack()
            
            desc = strategy_class.describe() if hasattr(strategy_class, 'describe') else ""
            subtitle = tk.Label(
                header_frame,
                text=desc,
                font=('Segoe UI', 11),
                fg='#E3F2FD',
                bg='#1976D2',
                wraplength=600
            )
            subtitle.pack(pady=(5, 0))
            
            # Get metadata if available
            if hasattr(strategy_class, 'metadata'):
                metadata = strategy_class.metadata()
                
                # Risk Indicators Row
                indicators_frame = tk.Frame(content, bg='#FFFFFF')
                indicators_frame.pack(fill=tk.X, pady=(0, 20))
                
                def create_indicator(parent, label, value, color):
                    frame = tk.Frame(parent, bg='#F5F5F5', padx=15, pady=10)
                    frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
                    
                    tk.Label(
                        frame,
                        text=label,
                        font=('Segoe UI', 9),
                        fg='#757575',
                        bg='#F5F5F5'
                    ).pack()
                    
                    tk.Label(
                        frame,
                        text=value,
                        font=('Segoe UI', 11, 'bold'),
                        fg=color,
                        bg='#F5F5F5'
                    ).pack(pady=(3, 0))
                
                # Risk level color coding
                risk_colors = {
                    'Very Low': '#4CAF50',
                    'Low': '#8BC34A',
                    'Medium': '#FFC107',
                    'High': '#FF9800',
                    'Very High': '#F44336',
                    'Variable': '#9E9E9E'
                }
                
                create_indicator(indicators_frame, "Risk Level", 
                               metadata.risk_level, 
                               risk_colors.get(metadata.risk_level, '#9E9E9E'))
                create_indicator(indicators_frame, "Bankroll", 
                               metadata.bankroll_required, '#1976D2')
                create_indicator(indicators_frame, "Volatility", 
                               metadata.volatility, '#7B1FA2')
                
                # Secondary indicators
                indicators_frame2 = tk.Frame(content, bg='#FFFFFF')
                indicators_frame2.pack(fill=tk.X, pady=(0, 20))
                
                create_indicator(indicators_frame2, "Time to Profit", 
                               metadata.time_to_profit, '#00796B')
                create_indicator(indicators_frame2, "Recommended For", 
                               metadata.recommended_for, '#0288D1')
                
                # Best Use Case
                self._create_info_section(content, "📌 Best Use Case", 
                                        metadata.best_use_case, '#E3F2FD')
                
                # Pros
                pros_frame = self._create_info_section_frame(content, "✅ Advantages", '#E8F5E9')
                for pro in metadata.pros:
                    self._create_bullet_point(pros_frame, pro, '•', '#4CAF50')
                
                # Cons
                cons_frame = self._create_info_section_frame(content, "⚠️ Disadvantages", '#FFEBEE')
                for con in metadata.cons:
                    self._create_bullet_point(cons_frame, con, '•', '#F44336')
                
                # Tips
                tips_frame = self._create_info_section_frame(content, "💡 Expert Tips", '#FFF3E0')
                for i, tip in enumerate(metadata.tips, 1):
                    self._create_bullet_point(tips_frame, tip, f'{i}.', '#FF9800')
            
            # Parameters section
            schema = strategy_class.schema()
            params_frame = self._create_info_section_frame(content, "⚙️ Parameters", '#F5F5F5')
            
            for param_name, param_info in schema.items():
                param_container = tk.Frame(params_frame, bg='#FFFFFF', padx=10, pady=8)
                param_container.pack(fill=tk.X, pady=2)
                
                tk.Label(
                    param_container,
                    text=f"• {param_name}",
                    font=('Segoe UI', 10, 'bold'),
                    fg='#212121',
                    bg='#FFFFFF',
                    anchor=tk.W
                ).pack(fill=tk.X)
                
                tk.Label(
                    param_container,
                    text=f"  {param_info.get('desc', 'No description')}",
                    font=('Segoe UI', 9),
                    fg='#616161',
                    bg='#FFFFFF',
                    anchor=tk.W,
                    wraplength=600
                ).pack(fill=tk.X, padx=(15, 0))
                
                tk.Label(
                    param_container,
                    text=f"  Type: {param_info.get('type', 'unknown')} | Default: {param_info.get('default', 'N/A')}",
                    font=('Segoe UI', 8),
                    fg='#9E9E9E',
                    bg='#FFFFFF',
                    anchor=tk.W
                ).pack(fill=tk.X, padx=(15, 0))
            
            # Close button
            close_btn = ModernButton(
                content,
                text="Close",
                command=info_window.destroy,
                bg='#1976D2',
                fg='#FFFFFF',
                hover_bg='#1565C0',
                font=('Segoe UI', 11, 'bold')
            )
            close_btn.pack(pady=(20, 10))
            
            # Pack scrollbar and canvas
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Center window
            info_window.update_idletasks()
            x = (info_window.winfo_screenwidth() // 2) - (700 // 2)
            y = (info_window.winfo_screenheight() // 2) - (800 // 2)
            info_window.geometry(f"700x800+{x}+{y}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get strategy info: {e}")
    
    def _create_info_section(self, parent, title, text, bg_color):
        """Create an info section with colored background."""
        frame = tk.Frame(parent, bg=bg_color, padx=15, pady=12)
        frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(
            frame,
            text=title,
            font=('Segoe UI', 11, 'bold'),
            fg='#212121',
            bg=bg_color,
            anchor=tk.W
        ).pack(fill=tk.X)
        
        tk.Label(
            frame,
            text=text,
            font=('Segoe UI', 10),
            fg='#424242',
            bg=bg_color,
            anchor=tk.W,
            wraplength=600,
            justify=tk.LEFT
        ).pack(fill=tk.X, pady=(5, 0))
        
        return frame
    
    def _create_info_section_frame(self, parent, title, bg_color):
        """Create a titled frame for list content."""
        container = tk.Frame(parent, bg='#FFFFFF')
        container.pack(fill=tk.X, pady=(0, 15))
        
        header = tk.Frame(container, bg=bg_color, padx=15, pady=10)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text=title,
            font=('Segoe UI', 11, 'bold'),
            fg='#212121',
            bg=bg_color
        ).pack(anchor=tk.W)
        
        content_frame = tk.Frame(container, bg='#FFFFFF', padx=15, pady=5)
        content_frame.pack(fill=tk.X)
        
        return content_frame
    
    def _create_bullet_point(self, parent, text, bullet, color):
        """Create a bullet point item."""
        item_frame = tk.Frame(parent, bg='#FFFFFF', pady=3)
        item_frame.pack(fill=tk.X)
        
        bullet_label = tk.Label(
            item_frame,
            text=bullet,
            font=('Segoe UI', 10, 'bold'),
            fg=color,
            bg='#FFFFFF',
            width=3,
            anchor=tk.W
        )
        bullet_label.pack(side=tk.LEFT)
        
        text_label = tk.Label(
            item_frame,
            text=text,
            font=('Segoe UI', 9),
            fg='#424242',
            bg='#FFFFFF',
            anchor=tk.W,
            wraplength=600,
            justify=tk.LEFT
        )
        text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _on_sim_mode_changed(self):
        """Handle simulation mode toggle."""
        is_simulation = self.sim_mode_var.get()
        self.is_simulation = is_simulation
        
        # Update mode banner
        if hasattr(self, 'mode_banner'):
            mode = "simulation" if is_simulation else "live"
            self.mode_banner.set_mode(mode)
        
        # Update status bar
        if hasattr(self, 'status_bar'):
            mode_text = "Simulation" if is_simulation else "Live Betting"
            self.status_bar.set_mode(mode_text)
        
        # Update status message
        if is_simulation:
            self._update_auto_status("⚠️ Simulation mode enabled - no real bets will be placed.")
        else:
            self._update_auto_status("✓ Live mode enabled - real bets will be placed.")

    
    def _update_auto_status(self, message: str):
        """Update auto bet status display."""
        if not hasattr(self, 'auto_status_text'):
            return
        self.auto_status_text.config(state=tk.NORMAL)
        self.auto_status_text.delete(1.0, tk.END)
        self.auto_status_text.insert(1.0, message)
        self.auto_status_text.config(state=tk.DISABLED)
    
    def _start_auto_betting(self):
        """Start automated betting."""
        # Validate connection
        if not self.api:
            messagebox.showwarning("Not Connected", "Please connect to DuckDice first.")
            return
        
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            messagebox.showwarning("No Strategy", "Please select a strategy.")
            return
        
        try:
            # Get strategy configuration
            strategy_config = self.strategy_config_panel.get_config()
            
            # Get bet settings
            max_bets = int(self.max_bets_var.get() or 0)
            stop_profit = Decimal(self.stop_profit_var.get()) if self.stop_profit_var.get() else None
            stop_loss = Decimal(self.stop_loss_var.get()) if self.stop_loss_var.get() else None
            
            # Update UI state
            self.start_auto_btn.config(state=tk.DISABLED)
            self.stop_auto_btn.config(state=tk.NORMAL)
            self.pause_auto_btn.config(state=tk.NORMAL)
            self.betting_status.set_status("Betting", "betting", pulse=True)
            
            self._update_auto_status(
                f"Starting automated betting...\n"
                f"Strategy: {strategy_name}\n"
                f"Mode: {'Simulation' if self.sim_mode_var.get() else 'Live'}\n"
                f"Max bets: {max_bets if max_bets > 0 else 'Unlimited'}"
            )
            
            # TODO: Start betting thread with strategy
            # This will be implemented when integrating with betbot_engine
            
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid bet settings: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start auto betting: {e}")
            self._reset_auto_controls()
    
    def _stop_auto_betting(self):
        """Stop automated betting."""
        self._reset_auto_controls()
        self.betting_status.set_status("Idle", "normal", pulse=False)
        self._update_auto_status("Betting stopped by user.")
        Toast.show(self, "Betting stopped", toast_type="info")
    
    def _pause_auto_betting(self):
        """Pause automated betting."""
        # Toggle pause state
        if self.pause_auto_btn.cget('text').startswith("⏸️"):
            self.pause_auto_btn.config(text="▶️ Resume")
            self.betting_status.set_status("Paused", "warning", pulse=False)
            self._update_auto_status("Betting paused. Click Resume to continue.")
            Toast.show(self, "Betting paused", toast_type="warning")
        else:
            self.pause_auto_btn.config(text="⏸️ Pause")
            self.betting_status.set_status("Betting", "betting", pulse=True)
            self._update_auto_status("Betting resumed.")
            Toast.show(self, "Betting resumed", toast_type="success")
    
    def _reset_auto_controls(self):
        """Reset auto bet control button states."""
        self.start_auto_btn.config(state=tk.NORMAL)
        self.stop_auto_btn.config(state=tk.DISABLED)
        self.pause_auto_btn.config(state=tk.DISABLED)
        self.pause_auto_btn.config(text="⏸️ Pause")
    
    def _create_history_tab(self, parent):
        """Create history tab."""
        self.history_viewer = EnhancedBetHistoryViewer(parent, bet_logger=self.bet_logger)
        self.history_viewer.pack(fill=tk.BOTH, expand=True)
    
    def _create_statistics_tab(self, parent):
        """Create statistics tab."""
        self.stats_dashboard = StatisticsDashboard(parent, bet_logger=self.bet_logger)
        self.stats_dashboard.pack(fill=tk.BOTH, expand=True)
    
    def _create_script_editor_tab(self, parent):
        """Create script editor tab."""
        # Title and description
        header = tk.Frame(parent, bg="white", height=60)
        header.pack(fill=tk.X, padx=0, pady=0)
        
        ttk.Label(
            header,
            text="DiceBot-Compatible Script Editor",
            font=('Segoe UI', 16, 'bold')
        ).pack(anchor=tk.W, padx=20, pady=(10, 0))
        
        ttk.Label(
            header,
            text="Write custom betting strategies using Python. Compatible with DiceBot script syntax.",
            font=('Segoe UI', 9),
            foreground="#666"
        ).pack(anchor=tk.W, padx=20, pady=(0, 10))
        
        # Script editor widget
        self.script_editor = ScriptEditor(parent)
        self.script_editor.pack(fill=tk.BOTH, expand=True)
    
    def _create_status_bar(self, parent):
        """Create bottom status bar."""
        status_bar = ttk.Frame(parent, padding=5)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, side=tk.BOTTOM)
        
        # Left: Status message
        self.status_message = tk.StringVar(value="Ready")
        ttk.Label(status_bar, textvariable=self.status_message,
                 font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        # Right: App info
        ttk.Label(status_bar, text="DuckDice Bot Ultimate v3.0",
                 font=('Segoe UI', 9),
                 foreground=ModernTheme.TEXT_SECONDARY).pack(side=tk.RIGHT)
    
    # Essential methods implementation
    def _setup_emergency_stop(self):
        """Setup emergency stop manager."""
        try:
            # Create callback for emergency stop
            def emergency_stop_callback():
                if self.is_betting:
                    self._stop_auto_betting()
                    messagebox.showwarning(
                        "Emergency Stop",
                        "Betting stopped via emergency hotkey!"
                    )
            
            self.emergency_stop = EmergencyStopManager(emergency_stop_callback)
            self.emergency_stop.start()
        except Exception as e:
            print(f"Emergency stop setup failed: {e}")
    
    def _setup_sound(self):
        """Setup sound manager."""
        try:
            if self.config_manager.get('sound_enabled'):
                self.sound_manager = SoundManager()
        except Exception as e:
            print(f"Sound manager setup failed: {e}")
    
    def _load_saved_state(self):
        """Load saved API key and preferences."""
        if self.config_manager.get('remember_api_key'):
            api_key = self.config_manager.get('api_key', '')
            if api_key and hasattr(self, 'api_key_entry'):
                self.api_key_entry.insert(0, api_key)
    
    def _show_welcome_wizard(self):
        """Show enhanced welcome wizard for first-time users."""
        wizard = OnboardingWizard(self, self.config_manager)
        wizard.show()
    
    def _on_closing(self):
        """Handle window close event."""
        # Stop faucet manager if running
        if self.faucet_manager:
            self.faucet_manager.stop_auto_claim()
        
        if self.is_betting:
            if ConfirmDialog.ask(
                self,
                "Quit Application",
                "Betting is currently active. Are you sure you want to stop and quit?",
                danger=True
            ):
                self._stop_auto_betting()
                self.quit()
        else:
            self.quit()
    
    def _on_qb_mode_changed(self, event=None):
        """Handle Quick Bet mode change (main/faucet)."""
        mode = self.qb_mode_var.get()
        self.betting_mode = mode
        self.config_manager.set('betting_mode', mode)
        
        # Show/hide faucet claim button
        if mode == "faucet":
            self.qb_claim_btn.grid(row=1, column=2, padx=5, pady=5)
            self.qb_claim_label.grid(row=1, column=3, padx=5, pady=5)
            self._update_faucet_claim_status()
        else:
            self.qb_claim_btn.grid_forget()
            self.qb_claim_label.grid_forget()
        
        Toast.show(self, f"Switched to {mode.title()} mode", toast_type="info")
    
    def _on_ab_mode_changed(self, event=None):
        """Handle Auto Bet mode change (main/faucet)."""
        mode = self.ab_mode_var.get()
        self.betting_mode = mode
        self.config_manager.set('betting_mode', mode)
        
        # Update house edge display
        house_edge = "3%" if mode == "faucet" else "1%"
        self.ab_house_edge_label.config(text=f"House Edge: {house_edge}")
        
        Toast.show(self, f"Auto Bet mode: {mode.title()} ({house_edge} house edge)", toast_type="info")
    
    def _claim_faucet_now(self):
        """Manually claim faucet."""
        if not self.faucet_manager:
            Toast.show(self, "Please connect to API first", toast_type="warning")
            return
        
        currency = self.qb_symbol_var.get()
        success = self.faucet_manager.claim_now(currency)
        
        if success:
            self._update_faucet_claim_status()
    
    def _update_faucet_claim_status(self):
        """Update faucet claim button and countdown label."""
        if not self.faucet_manager or not hasattr(self, 'qb_claim_label'):
            return
        
        remaining = self.faucet_manager.get_next_claim_time()
        
        if remaining > 0:
            self.qb_claim_btn.config(state='disabled')
            self.qb_claim_label.config(text=f"Next claim in {int(remaining)}s")
            # Schedule next update
            self.after(1000, self._update_faucet_claim_status)
        else:
            self.qb_claim_btn.config(state='normal')
            self.qb_claim_label.config(text="Ready to claim!")
    
    def _new_session(self):
        """Start a new betting session."""
        if self.bet_logger.bets and not ConfirmDialog.ask(
            self,
            "New Session",
            "Start a new session? Current bet history will be archived.",
            danger=False
        ):
            return
        
        self.current_session_id = str(uuid.uuid4())
        self.bet_logger.clear()
        Toast.show(self, "New betting session started!", toast_type="success")
    
    def _export_session(self):
        """Export current session data."""
        if not self.bet_logger.bets:
            Toast.show(self, "No bets to export", toast_type="warning")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.bet_logger.export_json(filename)
                Toast.show(self, "Session exported successfully!", toast_type="success")
            except Exception as e:
                Toast.show(self, f"Export failed: {e}", toast_type="error")
    
    def _show_settings(self):
        """Show enhanced settings dialog with tabs."""
        dialog = tk.Toplevel(self)
        dialog.title("Settings")
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === API SETTINGS TAB ===
        api_tab = ttk.Frame(notebook, padding=15)
        notebook.add(api_tab, text="API Settings")
        
        ttk.Label(api_tab, text="API Key:", font=('', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        api_key_var = tk.StringVar(value=self.config_manager.get('api_key', ''))
        api_key_entry = ttk.Entry(api_tab, textvariable=api_key_var, width=50, show="*")
        api_key_entry.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.EW)
        
        remember_var = tk.BooleanVar(value=self.config_manager.get('remember_api_key', False))
        ttk.Checkbutton(
            api_tab,
            text="Remember API key",
            variable=remember_var
        ).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        ttk.Label(api_tab, text="\nGet your API key from DuckDice.io → Account Settings → Bot API",
                 foreground="gray").grid(row=3, column=0, columnspan=2, sticky=tk.W)
        
        # === FAUCET SETTINGS TAB ===
        faucet_tab = ttk.Frame(notebook, padding=15)
        notebook.add(faucet_tab, text="Faucet Settings")
        
        # Auto-claim toggle
        faucet_enabled_var = tk.BooleanVar(value=self.config_manager.get('faucet_auto_claim', False))
        ttk.Checkbutton(
            faucet_tab,
            text="Enable Auto-Claim",
            variable=faucet_enabled_var,
            command=lambda: self._toggle_faucet_fields(faucet_enabled_var.get(), cookie_text, interval_spin)
        ).grid(row=0, column=0, sticky=tk.W, pady=10)
        
        # Claim interval
        ttk.Label(faucet_tab, text="Claim Interval (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5)
        interval_var = tk.IntVar(value=self.config_manager.get('faucet_interval', 60))
        interval_spin = ttk.Spinbox(faucet_tab, from_=60, to=300, textvariable=interval_var, width=10)
        interval_spin.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Cookie input
        ttk.Label(faucet_tab, text="Browser Cookie (required for auto-claim):", 
                 font=('', 10, 'bold')).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        
        cookie_frame = ttk.Frame(faucet_tab)
        cookie_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        cookie_scrollbar = ttk.Scrollbar(cookie_frame)
        cookie_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        cookie_text = tk.Text(cookie_frame, height=8, width=60, yscrollcommand=cookie_scrollbar.set, wrap=tk.WORD)
        cookie_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cookie_scrollbar.config(command=cookie_text.yview)
        
        # Load existing cookie
        cookie_mgr = CookieManager()
        existing_cookie = cookie_mgr.get_cookie()
        if existing_cookie:
            cookie_text.insert('1.0', existing_cookie)
        
        # Instructions
        instructions = tk.Text(faucet_tab, height=6, width=60, wrap=tk.WORD, bg="#f9f9f9", relief=tk.FLAT)
        instructions.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 0))
        instructions.insert('1.0', 
            "How to get your cookie:\n"
            "1. Open DuckDice.io in your browser and log in\n"
            "2. Open Developer Tools (F12)\n"
            "3. Go to Network tab → Reload page\n"
            "4. Click any request → Headers → Copy entire 'Cookie' value\n"
            "5. Paste it above and Save"
        )
        instructions.config(state='disabled')
        
        # Configure grid weights
        faucet_tab.rowconfigure(3, weight=1)
        faucet_tab.columnconfigure(0, weight=1)
        
        # Initially disable fields if auto-claim is off
        if not faucet_enabled_var.get():
            cookie_text.config(state='disabled')
            interval_spin.config(state='disabled')
        
        # === SOUND SETTINGS TAB ===
        sound_tab = ttk.Frame(notebook, padding=15)
        notebook.add(sound_tab, text="Sound")
        
        sound_var = tk.BooleanVar(value=self.config_manager.get('sound_enabled', True))
        ttk.Checkbutton(
            sound_tab,
            text="Enable sound effects",
            variable=sound_var
        ).pack(anchor=tk.W, pady=10)
        
        # === BUTTONS ===
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_settings():
            # Save API settings
            self.config_manager.set_many({
                'api_key': api_key_var.get(),
                'remember_api_key': remember_var.get(),
                'sound_enabled': sound_var.get(),
                'faucet_auto_claim': faucet_enabled_var.get(),
                'faucet_interval': interval_var.get()
            })
            self.config_manager.save()
            
            # Save faucet cookie
            cookie_str = cookie_text.get('1.0', 'end-1c').strip()
            if cookie_str:
                cookie_mgr.set_cookie(cookie_str)
            
            # Update faucet manager if exists
            if self.faucet_manager:
                self.faucet_manager.config.enabled = faucet_enabled_var.get()
                self.faucet_manager.config.interval = interval_var.get()
                if faucet_enabled_var.get():
                    self.faucet_manager.start_auto_claim()
                else:
                    self.faucet_manager.stop_auto_claim()
            
            messagebox.showinfo("Settings", "Settings saved successfully!")
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Save", command=save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def _toggle_faucet_fields(self, enabled, cookie_text, interval_spin):
        """Enable/disable faucet settings fields."""
        state = 'normal' if enabled else 'disabled'
        cookie_text.config(state=state)
        interval_spin.config(state=state)
    
    def _refresh_balances(self):
        """Refresh account balances."""
        if not self.api:
            Toast.show(self, "Please connect to the API first", toast_type="warning")
            return
        
        # Show loading overlay
        loading = LoadingOverlay(self, "Refreshing balances...")
        loading.show()
        
        def refresh_task():
            try:
                # Get selected currency for detailed balance
                currency = self.qb_symbol_var.get() if hasattr(self, 'qb_symbol_var') else "DOGE"
                
                # Get both main and faucet balances
                main_balance = self.api.get_main_balance(currency)
                faucet_balance = self.api.get_faucet_balance(currency)
                
                # Get total BTC value from all balances
                balances = self.api.get_balances()
                total_btc = sum(float(b.get('btc_value', 0)) for b in balances.values())
                
                # Update dashboard cards
                def update_ui():
                    if hasattr(self, 'card_main_balance'):
                        self.card_main_balance.set_value(f"{main_balance:.8f} {currency}")
                    if hasattr(self, 'card_faucet_balance'):
                        self.card_faucet_balance.set_value(f"{faucet_balance:.8f} {currency}")
                    if hasattr(self, 'card_balance'):
                        self.card_balance.set_value(f"{total_btc:.8f} BTC")
                    
                    loading.hide()
                    Toast.show(self, "Balances refreshed!", toast_type="success")
                
                self.after(0, update_ui)
            except Exception as e:
                self.after(0, lambda: loading.hide())
                self.after(100, lambda: Toast.show(self, f"Failed to refresh: {e}", toast_type="error"))
        
        threading.Thread(target=refresh_task, daemon=True).start()
    
    def _refresh_currencies(self):
        """Refresh available currencies from API."""
        if not self.api:
            Toast.show(self, "Please connect to the API first", toast_type="warning")
            return
        
        # Show brief feedback
        Toast.show(self, "Refreshing currencies...", toast_type="info")
        
        def fetch_currencies():
            try:
                currencies = self.api.get_available_currencies()
                
                def update_ui():
                    self.available_currencies = currencies
                    # Cache for offline use
                    self.config_manager.set('cached_currencies', currencies)
                    
                    # Update Quick Bet currency dropdown
                    if hasattr(self, 'qb_symbol_combo'):
                        current_value = self.qb_symbol_var.get()
                        self.qb_symbol_combo['values'] = currencies
                        # Restore selection if still valid
                        if current_value not in currencies and currencies:
                            self.qb_symbol_var.set(currencies[0])
                    
                    Toast.show(self, f"Currencies updated ({len(currencies)} available)", toast_type="success")
                
                self.after(0, update_ui)
            except Exception as e:
                def show_error():
                    Toast.show(self, f"Failed to refresh currencies: {e}", toast_type="error")
                self.after(0, show_error)
        
        threading.Thread(target=fetch_currencies, daemon=True).start()
    
    def _toggle_theme(self):
        """Toggle between light and dark theme."""
        current = self.config_manager.get('theme', 'light')
        new_theme = 'dark' if current == 'light' else 'light'
        self.config_manager.set('theme', new_theme)
        Toast.show(self, f"Theme changed to {new_theme}. Restart to apply.", toast_type="info")
    
    def _toggle_tooltips(self):
        """Toggle tooltips on/off."""
        enabled = self.config_manager.get('show_tooltips', True)
        self.config_manager.set('show_tooltips', not enabled)
        status = "disabled" if enabled else "enabled"
        Toast.show(self, f"Tooltips {status}", toast_type="info")
    
    def _test_connection(self):
        """Test API connection."""
        api_key = self.config_manager.get('api_key', '')
        if not api_key:
            Toast.show(self, "Please set your API key in Settings first", toast_type="warning")
            self.after(1000, self._show_settings)
            return
        
        # Show loading
        loading = LoadingOverlay(self, "Testing connection...")
        loading.show()
        
        def test_task():
            try:
                config = DuckDiceConfig(api_key=api_key)
                test_api = DuckDiceAPI(config)
                balances = test_api.get_balances()
                
                self.after(0, lambda: loading.hide())
                self.after(100, lambda: Toast.show(
                    self,
                    f"✓ Connected! Found {len(balances)} currencies",
                    toast_type="success"
                ))
            except Exception as e:
                self.after(0, lambda: loading.hide())
                self.after(100, lambda: Toast.show(
                    self,
                    f"Connection failed: {e}",
                    toast_type="error"
                ))
        
        threading.Thread(target=test_task, daemon=True).start()
    
    def _clear_history(self):
        """Clear bet history."""
        if ConfirmDialog.ask(self, "Clear History", "Clear all bet history?", danger=True):
            self.bet_logger.clear()
            Toast.show(self, "Bet history cleared", toast_type="success")
    
    def _test_emergency_stop(self):
        """Test emergency stop functionality."""
        messagebox.showinfo(
            "Emergency Stop",
            "Emergency stop is configured to monitor for hotkey.\n"
            "Install pynput to enable this feature:\n"
            "pip install pynput"
        )
    
    def _show_quick_start(self):
        """Show quick start guide."""
        messagebox.showinfo(
            "Quick Start Guide",
            "1. Set your API key in Settings (menu bar)\n"
            "2. Click 'Connect' to establish connection\n"
            "3. Choose Auto Bet tab\n"
            "4. Select a strategy\n"
            "5. Configure parameters\n"
            "6. Click Start to begin betting\n\n"
            "Tip: Enable simulation mode for testing!"
        )
    
    def _show_shortcuts(self):
        """Show keyboard shortcuts."""
        dialog = ShortcutsDialog(self, self.shortcut_manager)
        dialog.show()
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Connection
        self.shortcut_manager.register(
            '<Control-k>',
            self._quick_connect,
            'Quick Connect/Disconnect'
        )
        
        # Refresh
        self.shortcut_manager.register(
            '<F5>',
            self._refresh_balances,
            'Refresh Balances'
        )
        
        # Settings
        self.shortcut_manager.register(
            '<Control-comma>',
            self._show_settings,
            'Open Settings'
        )
        
        # New Session
        self.shortcut_manager.register(
            '<Control-n>',
            self._new_session,
            'New Session'
        )
        
        # Export
        self.shortcut_manager.register(
            '<Control-e>',
            self._export_session,
            'Export Session'
        )
        
        # Tab Navigation
        self.shortcut_manager.register(
            '<Control-1>',
            lambda: self._switch_view('dashboard'),
            'Go to Dashboard'
        )
        
        self.shortcut_manager.register(
            '<Control-2>',
            lambda: self._switch_view('betting'),
            'Go to Quick Bet'
        )
        
        self.shortcut_manager.register(
            '<Control-3>',
            lambda: self._switch_view('auto'),
            'Go to Auto Bet'
        )
        
        self.shortcut_manager.register(
            '<Control-4>',
            lambda: self._switch_view('history'),
            'Go to History'
        )
        
        self.shortcut_manager.register(
            '<Control-5>',
            lambda: self._switch_view('statistics'),
            'Go to Statistics'
        )
        
        # Help
        self.shortcut_manager.register(
            '<F1>',
            self._show_quick_start,
            'Show Quick Start Guide'
        )
        
        self.shortcut_manager.register(
            '<Control-slash>',
            self._show_shortcuts,
            'Show Keyboard Shortcuts'
        )
        
        # Quick actions
        self.shortcut_manager.register(
            '<Control-q>',
            self._on_closing,
            'Quit Application'
        )
    
    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About DuckDice Bot",
            "DuckDice Bot Ultimate Edition v3.2.0\n\n"
            "Advanced betting automation for DuckDice.io\n"
            "17 built-in strategies • Faucet Mode • Auto-Update\n\n"
            "MIT License © 2025\n"
            "https://github.com/sushiomsky/duckdice-bot"
        )
    
    def _check_for_updates(self):
        """Check for updates manually."""
        self.auto_updater.check_and_prompt_update(self)
    
    def _update_log(self, message: str):
        """Callback for auto-updater to log messages."""
        Toast.show(self, message, toast_type="info")
    
    def _quick_connect(self):
        """Quick connect to API."""
        api_key = self.config_manager.get('api_key', '')
        
        if not api_key:
            Toast.show(self, "Please configure your API key first", toast_type="warning")
            self.after(1000, self._show_settings)
            return
        
        # Show loading
        loading = LoadingOverlay(self, "Connecting to DuckDice...")
        loading.show()
        
        def connect_task():
            try:
                # Create API connection
                config = DuckDiceConfig(api_key=api_key)
                self.api = DuckDiceAPI(config)
                
                # Test connection
                balances = self.api.get_balances()
                user_info = self.api.get_user_info() if hasattr(self.api, 'get_user_info') else {}
                
                # Update UI on main thread
                def update_ui():
                    loading.hide()
                    self.connection_status.set_status("Connected", "connected")
                    self.quick_connect_btn.config(text="🔌 Disconnect")
                    
                    # Initialize faucet manager
                    faucet_config = FaucetConfig(
                        enabled=self.config_manager.get('faucet_auto_claim', False),
                        interval=self.config_manager.get('faucet_interval', 60),
                        currency=self.config_manager.get('faucet_currency', 'DOGE')
                    )
                    self.faucet_manager = FaucetManager(self.api, faucet_config)
                    
                    # Setup faucet callbacks
                    self.faucet_manager.on_claim_success = lambda curr, bal: Toast.show(
                        self, f"Faucet claimed! {curr} balance: {bal:.8f}", toast_type="success"
                    )
                    self.faucet_manager.on_claim_failure = lambda curr, err: Toast.show(
                        self, f"Faucet claim failed: {err}", toast_type="error"
                    )
                    
                    # Start auto-claim if enabled
                    if faucet_config.enabled:
                        self.faucet_manager.start_auto_claim()
                    
                    # Update new mode banner and status bar
                    if hasattr(self, 'mode_banner'):
                        mode = "simulation" if self.is_simulation else "live"
                        self.mode_banner.set_mode(mode)
                    
                    if hasattr(self, 'status_bar'):
                        self.status_bar.set_connection(True)
                        mode_text = "Simulation" if self.is_simulation else "Live Betting"
                        self.status_bar.set_mode(mode_text)
                        
                        # Update balance in status bar
                        if balances:
                            first_currency = list(balances.keys())[0]
                            amount = balances[first_currency].get('amount', '0')
                            self.status_bar.set_balance(amount, first_currency)
                    
                    # Update dashboard
                    if hasattr(self, 'card_balance'):
                        total_btc = sum(float(b.get('btc_value', 0)) for b in balances.values())
                        self.card_balance.set_value(f"{total_btc:.8f} BTC")
                    
                    # Refresh available currencies
                    self._refresh_currencies()
                    
                    Toast.show(self, "Successfully connected to DuckDice!", toast_type="success")
                
                self.after(0, update_ui)
                
            except Exception as e:
                def show_error():
                    loading.hide()
                    self.connection_status.set_status("Error", "error")
                    
                    # Update mode banner to disconnected
                    if hasattr(self, 'mode_banner'):
                        self.mode_banner.set_mode("disconnected")
                    if hasattr(self, 'status_bar'):
                        self.status_bar.set_connection(False)
                    
                    Toast.show(self, f"Connection failed: {e}", toast_type="error")
                
                self.after(0, show_error)
        
        threading.Thread(target=connect_task, daemon=True).start()
    
    def _switch_view(self, view):
        """Switch between different views."""
        view_map = {
            'dashboard': 0,
            'betting': 1,
            'auto': 2,
            'history': 3,
            'statistics': 4
        }
        if view in view_map and hasattr(self, 'notebook'):
            self.notebook.select(view_map[view])
    
    def _on_mode_changed(self):
        """Handle betting mode change."""
        if hasattr(self, 'sim_mode_var'):
            sim_mode = self.sim_mode_var.get()
            self.is_simulation = sim_mode
            mode_text = "Simulation" if sim_mode else "Live"
            if hasattr(self, 'betting_status'):
                self.betting_status.set_status(f"{mode_text} Mode", "warning" if sim_mode else "normal")


def main():
    """Application entry point."""
    app = UltimateGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
