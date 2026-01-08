"""
Dynamic Strategy Configuration Panel
Automatically generates UI forms based on strategy schemas
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Callable
from decimal import Decimal


class StrategyConfigPanel(ttk.Frame):
    """
    Dynamic configuration panel that generates UI based on strategy schema.
    Supports: str, int, float, bool types with validation and tooltips.
    """
    
    def __init__(self, parent, on_change: Optional[Callable] = None, **kwargs):
        """
        Initialize strategy config panel.
        
        Args:
            parent: Parent widget
            on_change: Callback when configuration changes
        """
        super().__init__(parent, **kwargs)
        
        self.on_change_callback = on_change
        self.current_strategy = None
        self.param_widgets = {}
        self.param_vars = {}
        
        self._create_ui()
    
    def _create_ui(self):
        """Create the UI structure."""
        # Title
        self.title_label = ttk.Label(
            self,
            text="Strategy Configuration",
            font=('Segoe UI', 12, 'bold')
        )
        self.title_label.pack(pady=(0, 10))
        
        # Scrollable frame for parameters
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        self.params_container = ttk.Frame(canvas)
        
        canvas.create_window((0, 0), window=self.params_container, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Update scroll region when frame changes size
        self.params_container.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        # Help text
        self.help_label = ttk.Label(
            self,
            text="💡 Hover over field names for descriptions",
            font=('Segoe UI', 9),
            foreground='#757575'
        )
        self.help_label.pack(pady=(10, 0))
    
    def load_strategy(self, strategy_name: str, strategy_class: type):
        """
        Load strategy and generate configuration UI.
        
        Args:
            strategy_name: Name of the strategy
            strategy_class: Strategy class with schema() method
        """
        self.current_strategy = strategy_name
        
        # Clear existing widgets
        for widget in self.params_container.winfo_children():
            widget.destroy()
        
        self.param_widgets.clear()
        self.param_vars.clear()
        
        # Update title
        self.title_label.config(text=f"{strategy_name.title()} Configuration")
        
        # Get schema
        if not hasattr(strategy_class, 'schema'):
            self._show_no_config()
            return
        
        try:
            schema = strategy_class.schema()
        except Exception as e:
            self._show_error(f"Error loading schema: {e}")
            return
        
        if not schema:
            self._show_no_config()
            return
        
        # Generate UI for each parameter
        row = 0
        for param_name, param_spec in schema.items():
            self._create_param_field(row, param_name, param_spec)
            row += 1
        
        # Validation summary
        if row > 0:
            ttk.Separator(self.params_container, orient=tk.HORIZONTAL).grid(
                row=row, column=0, columnspan=3, sticky='ew', pady=10
            )
            
            self.validation_label = ttk.Label(
                self.params_container,
                text="✅ All parameters valid",
                foreground='#2E7D32',
                font=('Segoe UI', 9)
            )
            self.validation_label.grid(row=row+1, column=0, columnspan=3, pady=5)
    
    def _create_param_field(self, row: int, param_name: str, param_spec: Dict[str, Any]):
        """Create input field for a parameter."""
        param_type = param_spec.get('type', 'str')
        default_value = param_spec.get('default', '')
        description = param_spec.get('desc', '')
        
        # Label with tooltip
        label = ttk.Label(
            self.params_container,
            text=param_name.replace('_', ' ').title() + ":",
            font=('Segoe UI', 10)
        )
        label.grid(row=row, column=0, sticky=tk.E, padx=(0, 10), pady=5)
        
        # Add tooltip to label
        if description:
            self._add_tooltip(label, description)
        
        # Create appropriate widget based on type
        if param_type == 'bool':
            var = tk.BooleanVar(value=bool(default_value))
            widget = ttk.Checkbutton(
                self.params_container,
                variable=var,
                command=self._on_param_changed
            )
        
        elif param_type == 'int':
            var = tk.StringVar(value=str(default_value))
            widget = ttk.Spinbox(
                self.params_container,
                textvariable=var,
                from_=0,
                to=999999,
                increment=1,
                width=15,
                command=self._on_param_changed
            )
            var.trace_add('write', lambda *args: self._on_param_changed())
        
        elif param_type == 'float':
            var = tk.StringVar(value=str(default_value))
            widget = ttk.Entry(
                self.params_container,
                textvariable=var,
                width=15
            )
            var.trace_add('write', lambda *args: self._on_param_changed())
        
        else:  # str
            var = tk.StringVar(value=str(default_value))
            widget = ttk.Entry(
                self.params_container,
                textvariable=var,
                width=25
            )
            var.trace_add('write', lambda *args: self._on_param_changed())
        
        widget.grid(row=row, column=1, sticky=tk.W, pady=5)
        
        # Default value hint
        hint_text = f"Default: {default_value}"
        hint_label = ttk.Label(
            self.params_container,
            text=hint_text,
            font=('Segoe UI', 8),
            foreground='#9E9E9E'
        )
        hint_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Store references
        self.param_vars[param_name] = {'var': var, 'type': param_type}
        self.param_widgets[param_name] = widget
    
    def _add_tooltip(self, widget, text: str):
        """Add tooltip to widget."""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(
                tooltip,
                text=text,
                background="#FFFFDD",
                foreground="#000000",
                relief=tk.SOLID,
                borderwidth=1,
                padding=5,
                wraplength=300
            )
            label.pack()
            
            widget._tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, '_tooltip'):
                widget._tooltip.destroy()
                delattr(widget, '_tooltip')
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)
    
    def _show_no_config(self):
        """Show message when strategy has no configuration."""
        label = ttk.Label(
            self.params_container,
            text="This strategy has no configurable parameters.",
            font=('Segoe UI', 10),
            foreground='#757575'
        )
        label.pack(pady=20)
    
    def _show_error(self, message: str):
        """Show error message."""
        label = ttk.Label(
            self.params_container,
            text=f"❌ {message}",
            font=('Segoe UI', 10),
            foreground='#C62828'
        )
        label.pack(pady=20)
    
    def _on_param_changed(self):
        """Handle parameter change."""
        if self._validate_all():
            if hasattr(self, 'validation_label'):
                self.validation_label.config(
                    text="✅ All parameters valid",
                    foreground='#2E7D32'
                )
        else:
            if hasattr(self, 'validation_label'):
                self.validation_label.config(
                    text="⚠️ Please check parameter values",
                    foreground='#F57C00'
                )
        
        if self.on_change_callback:
            self.on_change_callback(self.get_config())
    
    def _validate_all(self) -> bool:
        """Validate all parameters."""
        for param_name, param_data in self.param_vars.items():
            var = param_data['var']
            param_type = param_data['type']
            
            try:
                value = var.get()
                
                if param_type == 'int':
                    int(value)
                elif param_type == 'float':
                    float(value)
                elif param_type == 'str':
                    # For Decimal strings, try to parse
                    if value:
                        Decimal(str(value))
            except (ValueError, TypeError):
                return False
        
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration as dictionary.
        
        Returns:
            Dictionary of parameter names to values
        """
        config = {}
        
        for param_name, param_data in self.param_vars.items():
            var = param_data['var']
            param_type = param_data['type']
            
            try:
                value = var.get()
                
                if param_type == 'bool':
                    config[param_name] = bool(value)
                elif param_type == 'int':
                    config[param_name] = int(value)
                elif param_type == 'float':
                    config[param_name] = float(value)
                else:  # str
                    config[param_name] = str(value)
            
            except (ValueError, TypeError):
                # Use default on error
                config[param_name] = var.get()
        
        return config
    
    def set_config(self, config: Dict[str, Any]):
        """
        Set configuration from dictionary.
        
        Args:
            config: Dictionary of parameter names to values
        """
        for param_name, value in config.items():
            if param_name in self.param_vars:
                self.param_vars[param_name]['var'].set(value)
    
    def reset_to_defaults(self):
        """Reset all parameters to default values."""
        # Would need to store defaults, for now just reload strategy
        if self.current_strategy:
            # Reload strategy to reset to defaults
            pass


# Example usage and test
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '../..')
    
    from betbot_strategies import get_strategy, list_strategies
    
    # Import strategies to register them
    from betbot_strategies import (
        classic_martingale,
        fibonacci,
        target_aware
    )
    
    root = tk.Tk()
    root.title("Strategy Config Panel Test")
    root.geometry("600x500")
    
    # Create panel
    panel = StrategyConfigPanel(root, padding=10)
    panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Strategy selector
    selector_frame = ttk.Frame(root, padding=10)
    selector_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    ttk.Label(selector_frame, text="Select Strategy:").pack(side=tk.LEFT, padx=5)
    
    strategy_var = tk.StringVar()
    strategies = list_strategies()
    strategy_names = [s['name'] for s in strategies]
    
    def on_strategy_selected(event=None):
        strategy_name = strategy_var.get()
        if strategy_name:
            strategy_cls = get_strategy(strategy_name)
            panel.load_strategy(strategy_name, strategy_cls)
    
    combo = ttk.Combobox(
        selector_frame,
        textvariable=strategy_var,
        values=strategy_names,
        state='readonly',
        width=30
    )
    combo.pack(side=tk.LEFT, padx=5)
    combo.bind('<<ComboboxSelected>>', on_strategy_selected)
    
    # Set default
    if strategy_names:
        strategy_var.set(strategy_names[0])
        on_strategy_selected()
    
    # Show config button
    def show_config():
        config = panel.get_config()
        print("Current configuration:")
        for key, value in config.items():
            print(f"  {key}: {value} ({type(value).__name__})")
    
    ttk.Button(
        selector_frame,
        text="Show Config",
        command=show_config
    ).pack(side=tk.LEFT, padx=5)
    
    root.mainloop()
