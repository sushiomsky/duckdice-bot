"""
Modern UI Components for DuckDice Bot
Provides professional, eye-catching UI elements with clear mode indicators
"""

import tkinter as tk
from tkinter import ttk
from typing import Literal, Callable, Optional


class ModernColorScheme:
    """
    Professional color scheme with dark mode support.
    Designed for clarity and visual appeal.
    """
    
    # Light Theme
    LIGHT = {
        'bg': '#F5F7FA',
        'surface': '#FFFFFF',
        'surface_raised': '#FFFFFF',
        'border': '#E1E4E8',
        'text_primary': '#24292E',
        'text_secondary': '#586069',
        'text_disabled': '#959DA5',
        
        # Accents
        'primary': '#0366D6',
        'primary_hover': '#0256C2',
        'success': '#28A745',
        'success_hover': '#22863A',
        'error': '#D73A49',
        'error_hover': '#CB2431',
        'warning': '#F59E0B',
        'warning_hover': '#D97706',
        
        # Mode indicators
        'simulation': '#10B981',
        'simulation_bg': '#D1FAE5',
        'live': '#EF4444',
        'live_bg': '#FEE2E2',
        'disconnected': '#6B7280',
        'disconnected_bg': '#F3F4F6',
    }
    
    # Dark Theme
    DARK = {
        'bg': '#0D1117',
        'surface': '#161B22',
        'surface_raised': '#21262D',
        'border': '#30363D',
        'text_primary': '#C9D1D9',
        'text_secondary': '#8B949E',
        'text_disabled': '#484F58',
        
        # Accents
        'primary': '#58A6FF',
        'primary_hover': '#79C0FF',
        'success': '#3FB950',
        'success_hover': '#56D364',
        'error': '#F85149',
        'error_hover': '#FF7B72',
        'warning': '#D29922',
        'warning_hover': '#E3B341',
        
        # Mode indicators
        'simulation': '#3FB950',
        'simulation_bg': '#1A2F23',
        'live': '#F85149',
        'live_bg': '#2B1A1C',
        'disconnected': '#8B949E',
        'disconnected_bg': '#21262D',
    }


class ModeIndicatorBanner(tk.Frame):
    """
    Large, prominent banner showing current mode.
    Impossible to miss - prevents accidental real money betting.
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.current_mode = "disconnected"
        self.theme = "light"
        self._create_ui()
    
    def _create_ui(self):
        """Create the banner UI."""
        self.configure(relief=tk.SOLID, borderwidth=3)
        
        # Icon and text container
        content = tk.Frame(self, bg=self['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Icon
        self.icon_label = tk.Label(
            content,
            text="●",
            font=('Segoe UI', 32),
            bg=self['bg']
        )
        self.icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Text content
        text_frame = tk.Frame(content, bg=self['bg'])
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.mode_label = tk.Label(
            text_frame,
            text="DISCONNECTED",
            font=('Segoe UI', 20, 'bold'),
            bg=self['bg']
        )
        self.mode_label.pack(anchor=tk.W)
        
        self.description_label = tk.Label(
            text_frame,
            text="Not connected to DuckDice API",
            font=('Segoe UI', 11),
            bg=self['bg']
        )
        self.description_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Set initial mode
        self.set_mode("disconnected")
    
    def set_mode(self, mode: Literal["simulation", "live", "disconnected"]):
        """
        Set the current mode and update visuals.
        
        Args:
            mode: 'simulation', 'live', or 'disconnected'
        """
        self.current_mode = mode
        colors = ModernColorScheme.LIGHT if self.theme == "light" else ModernColorScheme.DARK
        
        if mode == "simulation":
            bg_color = colors['simulation_bg']
            fg_color = colors['simulation']
            icon = "🟢"
            title = "SIMULATION MODE"
            desc = "Safe testing - No real money at risk"
        elif mode == "live":
            bg_color = colors['live_bg']
            fg_color = colors['live']
            icon = "🔴"
            title = "LIVE MODE"
            desc = "⚠️ REAL MONEY BETTING - Be careful!"
        else:  # disconnected
            bg_color = colors['disconnected_bg']
            fg_color = colors['disconnected']
            icon = "⚫"
            title = "DISCONNECTED"
            desc = "Not connected to DuckDice API"
        
        # Update colors
        self.configure(bg=bg_color, highlightbackground=fg_color, highlightthickness=3)
        for widget in self.winfo_children():
            widget.configure(bg=bg_color)
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    child.configure(bg=bg_color)
        
        # Update text
        self.icon_label.configure(text=icon, fg=fg_color)
        self.mode_label.configure(text=title, fg=fg_color)
        self.description_label.configure(text=desc, fg=fg_color)
    
    def set_theme(self, theme: Literal["light", "dark"]):
        """Switch between light and dark theme."""
        self.theme = theme
        self.set_mode(self.current_mode)


class ModernButton(tk.Canvas):
    """
    Beautiful modern button with hover effects and loading state.
    """
    
    def __init__(
        self,
        parent,
        text: str = "",
        command: Optional[Callable] = None,
        style: Literal["primary", "success", "error", "secondary"] = "primary",
        size: Literal["small", "medium", "large"] = "medium",
        **kwargs
    ):
        # Size configurations
        sizes = {
            'small': {'height': 32, 'font_size': 10, 'padding': 12},
            'medium': {'height': 40, 'font_size': 11, 'padding': 20},
            'large': {'height': 48, 'font_size': 12, 'padding': 24},
        }
        
        size_config = sizes[size]
        
        super().__init__(
            parent,
            height=size_config['height'],
            highlightthickness=0,
            **kwargs
        )
        
        self.text = text
        self.command = command
        self.style = style
        self.size_config = size_config
        self.is_hovered = False
        self.is_loading = False
        self.theme = "light"
        
        self._create_button()
        self._bind_events()
    
    def _create_button(self):
        """Create button graphics."""
        colors = ModernColorScheme.LIGHT
        
        # Style colors
        style_colors = {
            'primary': (colors['primary'], colors['primary_hover']),
            'success': (colors['success'], colors['success_hover']),
            'error': (colors['error'], colors['error_hover']),
            'secondary': (colors['border'], colors['text_secondary']),
        }
        
        self.normal_color, self.hover_color = style_colors[self.style]
        text_color = '#FFFFFF' if self.style != 'secondary' else colors['text_primary']
        
        # Background rounded rectangle
        width = self.winfo_reqwidth() or 200
        height = self.size_config['height']
        radius = height // 2
        
        self.bg_rect = self.create_rounded_rectangle(
            2, 2, width - 2, height - 2,
            radius=radius,
            fill=self.normal_color,
            outline=''
        )
        
        # Text
        self.text_id = self.create_text(
            width // 2, height // 2,
            text=self.text,
            fill=text_color,
            font=('Segoe UI', self.size_config['font_size'], 'bold')
        )
        
        # Loading spinner (hidden by default)
        self.spinner_id = self.create_text(
            30, height // 2,
            text="⏳",
            fill=text_color,
            font=('Segoe UI', self.size_config['font_size']),
            state='hidden'
        )
    
    def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
        """Create a rounded rectangle."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _bind_events(self):
        """Bind mouse events."""
        self.tag_bind(self.bg_rect, '<Enter>', self._on_enter)
        self.tag_bind(self.bg_rect, '<Leave>', self._on_leave)
        self.tag_bind(self.bg_rect, '<Button-1>', self._on_click)
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
    
    def _on_enter(self, event=None):
        """Mouse enter - show hover state."""
        if not self.is_loading:
            self.is_hovered = True
            self.itemconfig(self.bg_rect, fill=self.hover_color)
            self.config(cursor='hand2')
    
    def _on_leave(self, event=None):
        """Mouse leave - remove hover state."""
        self.is_hovered = False
        self.itemconfig(self.bg_rect, fill=self.normal_color)
        self.config(cursor='')
    
    def _on_click(self, event=None):
        """Button clicked."""
        if not self.is_loading and self.command:
            self.command()
    
    def set_loading(self, loading: bool):
        """Show/hide loading state."""
        self.is_loading = loading
        if loading:
            self.itemconfig(self.spinner_id, state='normal')
            self.itemconfig(self.text_id, state='hidden')
            self.config(cursor='wait')
        else:
            self.itemconfig(self.spinner_id, state='hidden')
            self.itemconfig(self.text_id, state='normal')
            self.config(cursor='hand2' if self.is_hovered else '')


class ConnectionStatusBar(tk.Frame):
    """
    Status bar showing connection, mode, and balance.
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, relief=tk.FLAT, borderwidth=0, **kwargs)
        self.theme = "light"
        self._create_ui()
    
    def _create_ui(self):
        """Create status bar UI."""
        colors = ModernColorScheme.LIGHT
        self.configure(bg=colors['surface'], height=40)
        
        # Left: Connection status
        left_frame = tk.Frame(self, bg=colors['surface'])
        left_frame.pack(side=tk.LEFT, padx=15, pady=8)
        
        self.conn_indicator = tk.Label(
            left_frame,
            text="● Disconnected",
            font=('Segoe UI', 9),
            fg=colors['disconnected'],
            bg=colors['surface']
        )
        self.conn_indicator.pack(side=tk.LEFT)
        
        # Center: Mode
        center_frame = tk.Frame(self, bg=colors['surface'])
        center_frame.pack(side=tk.LEFT, expand=True, padx=15, pady=8)
        
        self.mode_label = tk.Label(
            center_frame,
            text="Mode: Not Connected",
            font=('Segoe UI', 9, 'bold'),
            fg=colors['text_secondary'],
            bg=colors['surface']
        )
        self.mode_label.pack()
        
        # Right: Balance
        right_frame = tk.Frame(self, bg=colors['surface'])
        right_frame.pack(side=tk.RIGHT, padx=15, pady=8)
        
        self.balance_label = tk.Label(
            right_frame,
            text="Balance: --",
            font=('Segoe UI', 9),
            fg=colors['text_secondary'],
            bg=colors['surface']
        )
        self.balance_label.pack(side=tk.RIGHT)
    
    def set_connection(self, connected: bool):
        """Update connection status."""
        colors = ModernColorScheme.LIGHT if self.theme == "light" else ModernColorScheme.DARK
        
        if connected:
            self.conn_indicator.configure(
                text="● Connected",
                fg=colors['success']
            )
        else:
            self.conn_indicator.configure(
                text="● Disconnected",
                fg=colors['disconnected']
            )
    
    def set_mode(self, mode: str):
        """Update mode display."""
        self.mode_label.configure(text=f"Mode: {mode}")
    
    def set_balance(self, balance: str, currency: str = ""):
        """Update balance display."""
        self.balance_label.configure(text=f"Balance: {balance} {currency}")
