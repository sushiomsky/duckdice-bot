#!/usr/bin/env python3
"""
Advanced UX Components for Outstanding User Experience
Features: Animations, transitions, notifications, onboarding
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List
import time
from datetime import datetime


class AnimatedProgressBar:
    """Smooth animated progress bar with label."""
    
    def __init__(self, parent, width=300, height=20):
        self.frame = ttk.Frame(parent)
        
        self.canvas = tk.Canvas(
            self.frame, 
            width=width, 
            height=height,
            highlightthickness=0,
            bg='#FAFAFA'
        )
        self.canvas.pack(fill=tk.X, pady=5)
        
        # Background
        self.bg_rect = self.canvas.create_rectangle(
            0, 0, width, height,
            fill='#E0E0E0',
            outline='#BDBDBD'
        )
        
        # Progress bar
        self.progress_rect = self.canvas.create_rectangle(
            0, 0, 0, height,
            fill='#1976D2',
            outline=''
        )
        
        # Label
        self.label_var = tk.StringVar(value="")
        self.label = ttk.Label(
            self.frame,
            textvariable=self.label_var,
            font=('Segoe UI', 9),
            foreground='#757575'
        )
        self.label.pack()
        
        self.width = width
        self.current_value = 0
        self.target_value = 0
        self.animation_id = None
    
    def set_progress(self, percentage: float, label: str = ""):
        """Set progress with smooth animation (0-100)."""
        self.target_value = min(100, max(0, percentage))
        if label:
            self.label_var.set(label)
        
        if self.animation_id:
            self.canvas.after_cancel(self.animation_id)
        
        self._animate_progress()
    
    def _animate_progress(self):
        """Smooth progress animation."""
        if abs(self.current_value - self.target_value) < 0.5:
            self.current_value = self.target_value
        else:
            # Ease-out animation
            diff = self.target_value - self.current_value
            self.current_value += diff * 0.2
        
        # Update canvas
        new_width = (self.current_value / 100) * self.width
        self.canvas.coords(
            self.progress_rect,
            0, 0, new_width, 20
        )
        
        # Continue animation if not done
        if abs(self.current_value - self.target_value) >= 0.5:
            self.animation_id = self.canvas.after(16, self._animate_progress)
    
    def pack(self, **kwargs):
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        self.frame.grid(**kwargs)


class Toast:
    """Modern toast notification system."""
    
    @staticmethod
    def show(parent, message: str, duration: int = 3000, 
             toast_type: str = "info"):
        """
        Show toast notification.
        
        Args:
            parent: Parent window
            message: Message to display
            duration: Duration in milliseconds
            toast_type: 'success', 'error', 'warning', 'info'
        """
        # Color schemes
        colors = {
            'success': ('#2E7D32', '#C8E6C9', '#FFFFFF'),
            'error': ('#C62828', '#FFCDD2', '#FFFFFF'),
            'warning': ('#F57C00', '#FFE0B2', '#000000'),
            'info': ('#0288D1', '#B3E5FC', '#000000')
        }
        
        bg, border, fg = colors.get(toast_type, colors['info'])
        
        # Create toast window
        toast = tk.Toplevel(parent)
        toast.withdraw()  # Hide initially
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        
        # Configure appearance
        frame = tk.Frame(
            toast,
            bg=bg,
            highlightbackground=border,
            highlightthickness=2
        )
        frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Icon
        icons = {
            'success': '✓',
            'error': '✗',
            'warning': '⚠',
            'info': 'ℹ'
        }
        
        icon_label = tk.Label(
            frame,
            text=icons.get(toast_type, 'ℹ'),
            font=('Segoe UI', 16),
            bg=bg,
            fg=fg
        )
        icon_label.pack(side=tk.LEFT, padx=(10, 5), pady=10)
        
        # Message
        msg_label = tk.Label(
            frame,
            text=message,
            font=('Segoe UI', 10),
            bg=bg,
            fg=fg,
            wraplength=300
        )
        msg_label.pack(side=tk.LEFT, padx=(5, 10), pady=10)
        
        # Position toast
        toast.update_idletasks()
        width = toast.winfo_width()
        height = toast.winfo_height()
        
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        
        x = screen_width - width - 20
        y = screen_height - height - 60
        
        toast.geometry(f'+{x}+{y}')
        
        # Fade in animation
        toast.attributes('-alpha', 0.0)
        toast.deiconify()
        
        def fade_in(alpha=0.0):
            alpha = min(1.0, alpha + 0.1)
            toast.attributes('-alpha', alpha)
            if alpha < 1.0:
                toast.after(20, lambda: fade_in(alpha))
            else:
                # Schedule fade out
                toast.after(duration, lambda: fade_out(1.0))
        
        def fade_out(alpha=1.0):
            alpha = max(0.0, alpha - 0.1)
            toast.attributes('-alpha', alpha)
            if alpha > 0.0:
                toast.after(20, lambda: fade_out(alpha))
            else:
                toast.destroy()
        
        fade_in()


class OnboardingWizard:
    """Interactive onboarding wizard for first-time users."""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.current_step = 0
        
        self.steps = [
            self._step_welcome,
            self._step_api_key,
            self._step_features,
            self._step_complete
        ]
    
    def show(self):
        """Show onboarding wizard."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Welcome to DuckDice Bot")
        self.dialog.geometry("600x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 300
        y = (self.dialog.winfo_screenheight() // 2) - 250
        self.dialog.geometry(f"+{x}+{y}")
        
        # Content area
        self.content_frame = ttk.Frame(self.dialog, padding=30)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Navigation
        nav_frame = ttk.Frame(self.dialog, padding=10)
        nav_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.back_btn = ttk.Button(
            nav_frame,
            text="← Back",
            command=self._previous_step
        )
        self.back_btn.pack(side=tk.LEFT)
        
        self.next_btn = ttk.Button(
            nav_frame,
            text="Next →",
            command=self._next_step
        )
        self.next_btn.pack(side=tk.RIGHT)
        
        self.skip_btn = ttk.Button(
            nav_frame,
            text="Skip",
            command=self.dialog.destroy
        )
        self.skip_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Show first step
        self._show_current_step()
    
    def _show_current_step(self):
        """Display current step."""
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Show step
        self.steps[self.current_step]()
        
        # Update navigation
        self.back_btn.config(state=tk.NORMAL if self.current_step > 0 else tk.DISABLED)
        
        if self.current_step == len(self.steps) - 1:
            self.next_btn.config(text="Finish", command=self._finish)
        else:
            self.next_btn.config(text="Next →", command=self._next_step)
    
    def _next_step(self):
        """Go to next step."""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self._show_current_step()
    
    def _previous_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self._show_current_step()
    
    def _finish(self):
        """Complete wizard."""
        self.config_manager.set('show_welcome', False)
        self.dialog.destroy()
    
    def _step_welcome(self):
        """Welcome step."""
        ttk.Label(
            self.content_frame,
            text="🎲 Welcome to DuckDice Bot!",
            font=('Segoe UI', 24, 'bold'),
            foreground='#1976D2'
        ).pack(pady=(50, 20))
        
        ttk.Label(
            self.content_frame,
            text="The most advanced betting automation platform",
            font=('Segoe UI', 12),
            foreground='#757575'
        ).pack(pady=10)
        
        features = [
            "✓ 17 Built-in Betting Strategies",
            "✓ Real-time Performance Analytics",
            "✓ Risk Management Tools",
            "✓ Simulation Mode for Testing",
            "✓ Beautiful Material Design Interface"
        ]
        
        features_frame = ttk.Frame(self.content_frame)
        features_frame.pack(pady=30)
        
        for feature in features:
            ttk.Label(
                features_frame,
                text=feature,
                font=('Segoe UI', 11),
                foreground='#212121'
            ).pack(anchor=tk.W, pady=5)
    
    def _step_api_key(self):
        """API key configuration step."""
        ttk.Label(
            self.content_frame,
            text="🔑 API Configuration",
            font=('Segoe UI', 20, 'bold')
        ).pack(pady=(30, 20))
        
        ttk.Label(
            self.content_frame,
            text="To use DuckDice Bot, you need an API key from DuckDice.io",
            font=('Segoe UI', 11),
            foreground='#757575',
            wraplength=500
        ).pack(pady=10)
        
        # Instructions
        instructions = ttk.LabelFrame(self.content_frame, text="How to get your API key", padding=15)
        instructions.pack(fill=tk.X, pady=20)
        
        steps = [
            "1. Go to https://duckdice.io",
            "2. Login to your account",
            "3. Navigate to Account Settings",
            "4. Click on 'Bot API'",
            "5. Generate and copy your API key"
        ]
        
        for step in steps:
            ttk.Label(
                instructions,
                text=step,
                font=('Segoe UI', 10),
                foreground='#212121'
            ).pack(anchor=tk.W, pady=3)
        
        # API key input
        api_frame = ttk.LabelFrame(self.content_frame, text="Enter API Key", padding=15)
        api_frame.pack(fill=tk.X, pady=10)
        
        self.api_key_var = tk.StringVar()
        api_entry = ttk.Entry(
            api_frame,
            textvariable=self.api_key_var,
            font=('Consolas', 10),
            show='*',
            width=50
        )
        api_entry.pack(fill=tk.X, pady=5)
        
        ttk.Checkbutton(
            api_frame,
            text="Remember API key (stored locally)",
            variable=tk.BooleanVar(value=True)
        ).pack(anchor=tk.W, pady=5)
    
    def _step_features(self):
        """Features overview step."""
        ttk.Label(
            self.content_frame,
            text="🚀 Key Features",
            font=('Segoe UI', 20, 'bold')
        ).pack(pady=(30, 20))
        
        features = [
            ("📊 Dashboard", "Real-time metrics and performance tracking"),
            ("🎲 Quick Bet", "Manual betting with one-click execution"),
            ("🤖 Auto Bet", "Automated strategies with full customization"),
            ("📜 History", "Detailed bet history with filtering"),
            ("📈 Statistics", "Advanced analytics and insights")
        ]
        
        for title, desc in features:
            feature_frame = ttk.Frame(self.content_frame)
            feature_frame.pack(fill=tk.X, pady=10)
            
            ttk.Label(
                feature_frame,
                text=title,
                font=('Segoe UI', 12, 'bold')
            ).pack(anchor=tk.W)
            
            ttk.Label(
                feature_frame,
                text=desc,
                font=('Segoe UI', 10),
                foreground='#757575'
            ).pack(anchor=tk.W, padx=(20, 0))
    
    def _step_complete(self):
        """Completion step."""
        ttk.Label(
            self.content_frame,
            text="✨ All Set!",
            font=('Segoe UI', 24, 'bold'),
            foreground='#2E7D32'
        ).pack(pady=(80, 20))
        
        ttk.Label(
            self.content_frame,
            text="You're ready to start using DuckDice Bot",
            font=('Segoe UI', 12),
            foreground='#757575'
        ).pack(pady=10)
        
        ttk.Label(
            self.content_frame,
            text="💡 Tip: Start with Simulation Mode to test strategies risk-free!",
            font=('Segoe UI', 11, 'italic'),
            foreground='#F57C00'
        ).pack(pady=30)


class LoadingOverlay:
    """Full-screen loading overlay with spinner."""
    
    def __init__(self, parent, message="Loading..."):
        self.overlay = tk.Toplevel(parent)
        self.overlay.withdraw()
        
        # Make it cover parent
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-alpha', 0.9)
        
        # Position over parent
        parent.update_idletasks()
        x = parent.winfo_x()
        y = parent.winfo_y()
        w = parent.winfo_width()
        h = parent.winfo_height()
        self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        
        # Dark semi-transparent background
        frame = tk.Frame(self.overlay, bg='#212121')
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Spinner (animated)
        self.spinner_label = tk.Label(
            frame,
            text="⏳",
            font=('Segoe UI', 48),
            bg='#212121',
            fg='#FFFFFF'
        )
        self.spinner_label.pack(expand=True)
        
        # Message
        self.message_var = tk.StringVar(value=message)
        tk.Label(
            frame,
            textvariable=self.message_var,
            font=('Segoe UI', 14),
            bg='#212121',
            fg='#FFFFFF'
        ).pack()
        
        self.spinning = False
    
    def show(self):
        """Show overlay."""
        self.overlay.deiconify()
        self.overlay.lift()
        self.spinning = True
        self._animate_spinner()
    
    def hide(self):
        """Hide overlay."""
        self.spinning = False
        self.overlay.withdraw()
    
    def update_message(self, message: str):
        """Update loading message."""
        self.message_var.set(message)
    
    def _animate_spinner(self):
        """Animate spinner."""
        if not self.spinning:
            return
        
        spinners = ['⏳', '⌛']
        current = self.spinner_label.cget('text')
        next_spinner = spinners[(spinners.index(current) + 1) % len(spinners)]
        self.spinner_label.config(text=next_spinner)
        
        self.overlay.after(500, self._animate_spinner)


class ConfirmDialog:
    """Beautiful confirmation dialog with custom styling."""
    
    @staticmethod
    def ask(parent, title: str, message: str, 
            danger: bool = False) -> bool:
        """
        Show confirmation dialog.
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Dialog message
            danger: If True, uses warning colors
            
        Returns:
            True if confirmed, False otherwise
        """
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.transient(parent)
        dialog.grab_set()
        
        # Center
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 200
        y = (dialog.winfo_screenheight() // 2) - 100
        dialog.geometry(f"+{x}+{y}")
        
        result = {'confirmed': False}
        
        # Content
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Icon
        icon = "⚠️" if danger else "❓"
        icon_label = tk.Label(
            content,
            text=icon,
            font=('Segoe UI', 32)
        )
        icon_label.pack(pady=(10, 0))
        
        # Message
        msg_label = tk.Label(
            content,
            text=message,
            font=('Segoe UI', 11),
            wraplength=350,
            justify=tk.CENTER
        )
        msg_label.pack(pady=20)
        
        # Buttons
        btn_frame = ttk.Frame(content)
        btn_frame.pack(side=tk.BOTTOM, pady=10)
        
        def on_cancel():
            result['confirmed'] = False
            dialog.destroy()
        
        def on_confirm():
            result['confirmed'] = True
            dialog.destroy()
        
        cancel_btn = ttk.Button(
            btn_frame,
            text="Cancel",
            command=on_cancel,
            width=12
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        confirm_text = "Yes, proceed" if danger else "Confirm"
        confirm_btn = ttk.Button(
            btn_frame,
            text=confirm_text,
            command=on_confirm,
            width=12
        )
        confirm_btn.pack(side=tk.LEFT, padx=5)
        
        # Wait for dialog
        dialog.wait_window()
        
        return result['confirmed']
