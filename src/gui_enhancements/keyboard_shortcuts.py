#!/usr/bin/env python3
"""
Keyboard Shortcuts Manager
Provides comprehensive keyboard navigation and shortcuts
"""

import tkinter as tk
from typing import Callable, Dict


class KeyboardShortcutManager:
    """Manages keyboard shortcuts for the application."""
    
    def __init__(self, root):
        self.root = root
        self.shortcuts: Dict[str, Callable] = {}
        self.enabled = True
        
    def register(self, key_combo: str, callback: Callable, description: str = ""):
        """
        Register a keyboard shortcut.
        
        Args:
            key_combo: Key combination (e.g., '<Control-s>', '<F5>')
            callback: Function to call
            description: Human-readable description
        """
        self.shortcuts[key_combo] = {
            'callback': callback,
            'description': description
        }
        self.root.bind(key_combo, lambda e: self._handle_shortcut(key_combo))
    
    def _handle_shortcut(self, key_combo: str):
        """Handle shortcut execution."""
        if not self.enabled:
            return
        
        if key_combo in self.shortcuts:
            try:
                self.shortcuts[key_combo]['callback']()
            except Exception as e:
                print(f"Shortcut error ({key_combo}): {e}")
    
    def disable(self):
        """Temporarily disable all shortcuts."""
        self.enabled = False
    
    def enable(self):
        """Re-enable shortcuts."""
        self.enabled = True
    
    def get_shortcuts_list(self) -> list:
        """Get list of all registered shortcuts."""
        return [
            {
                'key': key.replace('<', '').replace('>', '').replace('Control', 'Ctrl'),
                'description': info['description']
            }
            for key, info in self.shortcuts.items()
        ]


class ShortcutsDialog:
    """Dialog showing all available keyboard shortcuts."""
    
    def __init__(self, parent, shortcut_manager: KeyboardShortcutManager):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Keyboard Shortcuts")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 300
        self.dialog.geometry(f"+{x}+{y}")
        
        # Title
        title_frame = tk.Frame(self.dialog, bg='#1976D2', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="⌨️ Keyboard Shortcuts",
            font=('Segoe UI', 16, 'bold'),
            bg='#1976D2',
            fg='#FFFFFF'
        ).pack(expand=True)
        
        # Shortcuts list
        content = tk.Frame(self.dialog, bg='#FAFAFA')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Scrollable frame
        canvas = tk.Canvas(content, bg='#FAFAFA', highlightthickness=0)
        scrollbar = tk.Scrollbar(content, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#FAFAFA')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add shortcuts
        shortcuts = shortcut_manager.get_shortcuts_list()
        
        for i, shortcut in enumerate(shortcuts):
            row_frame = tk.Frame(scrollable_frame, bg='#FFFFFF', relief=tk.FLAT, bd=1)
            row_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # Key combination (left)
            key_frame = tk.Frame(row_frame, bg='#E3F2FD', relief=tk.RAISED, bd=1)
            key_frame.pack(side=tk.LEFT, padx=10, pady=10)
            
            tk.Label(
                key_frame,
                text=shortcut['key'],
                font=('Consolas', 10, 'bold'),
                bg='#E3F2FD',
                fg='#1976D2',
                padx=10,
                pady=5
            ).pack()
            
            # Description (right)
            tk.Label(
                row_frame,
                text=shortcut['description'],
                font=('Segoe UI', 10),
                bg='#FFFFFF',
                fg='#212121',
                anchor='w'
            ).pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Close button
        btn_frame = tk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        close_btn = tk.Button(
            btn_frame,
            text="Close",
            command=self.dialog.destroy,
            bg='#1976D2',
            fg='#FFFFFF',
            font=('Segoe UI', 10, 'bold'),
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor='hand2'
        )
        close_btn.pack(side=tk.RIGHT)
        
        # Bind Escape key to close
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
    
    def show(self):
        """Show the dialog."""
        self.dialog.wait_window()
