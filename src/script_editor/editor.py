"""
Script Editor Widget

Modern script editor with:
- Syntax highlighting
- Line numbers
- Auto-save
- Version management
- Test simulation
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, Dict, Any, List


class ScriptEditor(tk.Frame):
    """
    Modern script editor with syntax highlighting and version control.
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # State
        self.current_file = None
        self.current_script_name = "Untitled"
        self.is_modified = False
        self.versions = []
        
        # Create UI
        self._create_ui()
        
        # Auto-save timer
        self.auto_save_interval = 30000  # 30 seconds
        self._schedule_auto_save()
    
    def _create_ui(self):
        """Create editor UI."""
        # Toolbar
        toolbar = tk.Frame(self, bg="#F5F5F5", height=40)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        # File operations
        tk.Button(
            toolbar, text="📄 New", command=self._new_script,
            bg="white", relief=tk.FLAT, padx=10, pady=5
        ).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(
            toolbar, text="📁 Open", command=self._open_script,
            bg="white", relief=tk.FLAT, padx=10, pady=5
        ).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(
            toolbar, text="💾 Save", command=self._save_script,
            bg="white", relief=tk.FLAT, padx=10, pady=5
        ).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(
            toolbar, text="💾 Save As", command=self._save_as_script,
            bg="white", relief=tk.FLAT, padx=10, pady=5
        ).pack(side=tk.LEFT, padx=2, pady=5)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Examples
        tk.Label(toolbar, text="Examples:", bg="#F5F5F5").pack(side=tk.LEFT, padx=5)
        
        self.example_var = tk.StringVar(value="Choose example...")
        example_combo = ttk.Combobox(
            toolbar,
            textvariable=self.example_var,
            values=["Simple Martingale", "Target Profit", "Anti-Martingale", "Streak Counter"],
            state='readonly',
            width=20
        )
        example_combo.pack(side=tk.LEFT, padx=2)
        example_combo.bind('<<ComboboxSelected>>', self._load_example)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Test button
        tk.Button(
            toolbar, text="▶️ Test", command=self._test_script,
            bg="#4CAF50", fg="white", relief=tk.FLAT, padx=15, pady=5
        ).pack(side=tk.LEFT, padx=2, pady=5)
        
        # Main editor area
        editor_frame = tk.Frame(self)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Line numbers
        self.line_numbers = tk.Text(
            editor_frame,
            width=4,
            padx=5,
            takefocus=0,
            border=0,
            background='#F0F0F0',
            foreground='#999',
            state='disabled',
            font=('Consolas', 11)
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Text editor with scrollbar
        text_frame = tk.Frame(editor_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(
            text_frame,
            wrap=tk.NONE,
            yscrollcommand=scrollbar.set,
            font=('Consolas', 11),
            bg="white",
            fg="#212121",
            insertbackground="#2196F3",
            selectbackground="#BBDEFB",
            tabs=('1c', '2c', '3c', '4c')  # 4-space tabs
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_widget.yview)
        
        # Status bar
        status_bar = tk.Frame(self, bg="#E0E0E0", height=25)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = tk.Label(
            status_bar, text="Ready", bg="#E0E0E0", anchor=tk.W, padx=10
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.position_label = tk.Label(
            status_bar, text="Line 1, Col 1", bg="#E0E0E0", anchor=tk.E, padx=10
        )
        self.position_label.pack(side=tk.RIGHT)
        
        # Bind events
        self.text_widget.bind('<KeyRelease>', self._on_text_change)
        self.text_widget.bind('<Button-1>', self._update_position)
        self.text_widget.bind('<KeyRelease>', self._update_position, add='+')
        
        # Syntax highlighting (basic)
        self._configure_tags()
    
    def _configure_tags(self):
        """Configure syntax highlighting tags."""
        # Keywords
        self.text_widget.tag_config('keyword', foreground='#0000FF', font=('Consolas', 11, 'bold'))
        # Comments
        self.text_widget.tag_config('comment', foreground='#008000', font=('Consolas', 11, 'italic'))
        # Numbers
        self.text_widget.tag_config('number', foreground='#FF6600')
        # Strings
        self.text_widget.tag_config('string', foreground='#A31515')
    
    def _update_line_numbers(self):
        """Update line numbers display."""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)
        
        # Get number of lines
        line_count = int(self.text_widget.index('end-1c').split('.')[0])
        
        # Generate line numbers
        line_numbers_text = '\n'.join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert('1.0', line_numbers_text)
        
        self.line_numbers.config(state='disabled')
    
    def _on_text_change(self, event=None):
        """Handle text changes."""
        self.is_modified = True
        self._update_line_numbers()
        self._update_status()
        self._highlight_syntax()
    
    def _update_position(self, event=None):
        """Update cursor position display."""
        position = self.text_widget.index(tk.INSERT)
        line, col = position.split('.')
        self.position_label.config(text=f"Line {line}, Col {int(col) + 1}")
    
    def _update_status(self):
        """Update status bar."""
        status = f"{self.current_script_name}"
        if self.is_modified:
            status += " (modified)"
        self.status_label.config(text=status)
    
    def _highlight_syntax(self):
        """Basic syntax highlighting."""
        # Remove all tags
        for tag in ['keyword', 'comment', 'number', 'string']:
            self.text_widget.tag_remove(tag, '1.0', tk.END)
        
        # Get all text
        text = self.text_widget.get('1.0', tk.END)
        
        # Highlight keywords
        keywords = ['if', 'else', 'for', 'while', 'def', 'return', 'import', 'from', 'class']
        for keyword in keywords:
            start = '1.0'
            while True:
                start = self.text_widget.search(r'\m' + keyword + r'\M', start, tk.END, regexp=True)
                if not start:
                    break
                end = f"{start}+{len(keyword)}c"
                self.text_widget.tag_add('keyword', start, end)
                start = end
        
        # Highlight comments
        lines = text.split('\n')
        for i, line in enumerate(lines, 1):
            if '#' in line:
                comment_start = line.index('#')
                self.text_widget.tag_add('comment', f"{i}.{comment_start}", f"{i}.end")
    
    def _new_script(self):
        """Create new script."""
        if self.is_modified:
            response = messagebox.askyesnocancel("Save Changes", "Save current script?")
            if response is True:
                self._save_script()
            elif response is None:
                return
        
        self.text_widget.delete('1.0', tk.END)
        self.current_file = None
        self.current_script_name = "Untitled"
        self.is_modified = False
        self._update_status()
    
    def _open_script(self):
        """Open existing script."""
        filepath = filedialog.askopenfilename(
            title="Open Script",
            filetypes=[("Python Scripts", "*.py"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if filepath:
            with open(filepath, 'r') as f:
                content = f.read()
            
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', content)
            self.current_file = filepath
            self.current_script_name = Path(filepath).name
            self.is_modified = False
            self._update_status()
            self._highlight_syntax()
    
    def _save_script(self):
        """Save script."""
        if not self.current_file:
            self._save_as_script()
        else:
            content = self.text_widget.get('1.0', 'end-1c')
            with open(self.current_file, 'w') as f:
                f.write(content)
            self.is_modified = False
            self._update_status()
            self._save_version()
    
    def _save_as_script(self):
        """Save script as new file."""
        filepath = filedialog.asksaveasfilename(
            title="Save Script As",
            defaultextension=".py",
            filetypes=[("Python Scripts", "*.py"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if filepath:
            content = self.text_widget.get('1.0', 'end-1c')
            with open(filepath, 'w') as f:
                f.write(content)
            self.current_file = filepath
            self.current_script_name = Path(filepath).name
            self.is_modified = False
            self._update_status()
            self._save_version()
    
    def _save_version(self):
        """Save current version to history."""
        version = {
            'timestamp': datetime.now().isoformat(),
            'content': self.text_widget.get('1.0', 'end-1c'),
            'name': self.current_script_name
        }
        self.versions.append(version)
        
        # Keep only last 10 versions
        if len(self.versions) > 10:
            self.versions = self.versions[-10:]
    
    def _load_example(self, event=None):
        """Load example script."""
        from .dicebot_compat import EXAMPLE_SCRIPTS
        
        example_name = self.example_var.get()
        if example_name in EXAMPLE_SCRIPTS:
            self.text_widget.delete('1.0', tk.END)
            self.text_widget.insert('1.0', EXAMPLE_SCRIPTS[example_name])
            self.current_script_name = example_name
            self.is_modified = True
            self._update_status()
            self._highlight_syntax()
    
    def _test_script(self):
        """Test script in simulation."""
        content = self.text_widget.get('1.0', 'end-1c')
        
        # Would integrate with simulation engine here
        messagebox.showinfo(
            "Test Script",
            "Script testing will be integrated with the simulation engine.\n\n"
            f"Script length: {len(content)} characters"
        )
    
    def _schedule_auto_save(self):
        """Schedule auto-save."""
        if self.is_modified and self.current_file:
            self._save_script()
        
        self.after(self.auto_save_interval, self._schedule_auto_save)
    
    def get_content(self) -> str:
        """Get current script content."""
        return self.text_widget.get('1.0', 'end-1c')
    
    def set_content(self, content: str):
        """Set script content."""
        self.text_widget.delete('1.0', tk.END)
        self.text_widget.insert('1.0', content)
        self._highlight_syntax()
