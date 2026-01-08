#!/usr/bin/env python3
"""
Quick visual test for strategy configuration panel integration
Tests the complete workflow without launching full GUI
"""
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

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
from betbot_strategies import list_strategies, get_strategy
from gui_enhancements import StrategyConfigPanel


class StrategyConfigDemo(tk.Tk):
    """Minimal demo of strategy configuration panel."""
    
    def __init__(self):
        super().__init__()
        self.title("Strategy Configuration Panel - Demo")
        self.geometry("900x700")
        
        # Get strategies
        self.strategies = list_strategies()
        self.strategy_names = [s['name'] for s in self.strategies]
        
        print(f"Found {len(self.strategy_names)} strategies:")
        for name in self.strategy_names:
            print(f"  - {name}")
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create demo UI."""
        # Title
        title = ttk.Label(
            self,
            text="Strategy Configuration Panel Demo",
            font=('Segoe UI', 16, 'bold')
        )
        title.pack(pady=20)
        
        # Strategy selector
        selector_frame = ttk.Frame(self)
        selector_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        ttk.Label(
            selector_frame,
            text="Select Strategy:",
            font=('Segoe UI', 10, 'bold')
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(
            selector_frame,
            textvariable=self.strategy_var,
            values=self.strategy_names,
            state='readonly',
            width=40
        )
        self.strategy_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.strategy_combo.bind('<<ComboboxSelected>>', self._on_strategy_changed)
        
        if self.strategy_names:
            self.strategy_combo.current(0)
            self.strategy_var.set(self.strategy_names[0])
        
        # Test button
        ttk.Button(
            selector_frame,
            text="Get Config",
            command=self._show_config
        ).pack(side=tk.LEFT)
        
        # Config panel
        panel_frame = ttk.LabelFrame(self, text="Configuration", padding=10)
        panel_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.config_panel = StrategyConfigPanel(panel_frame)
        self.config_panel.pack(fill=tk.BOTH, expand=True)
        
        # Load initial strategy
        if self.strategy_names:
            self._on_strategy_changed()
        
        # Status
        self.status = ttk.Label(
            self,
            text="Ready - Select a strategy to see its configuration",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _on_strategy_changed(self, event=None):
        """Handle strategy selection."""
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            return
        
        try:
            # Get strategy class
            strategy_class = get_strategy(strategy_name)
            
            # Load into panel
            self.config_panel.load_strategy(strategy_name, strategy_class)
            
            # Get schema info
            schema = strategy_class.schema()
            param_count = len(schema) if schema else 0
            
            self.status.config(
                text=f"Loaded: {strategy_name} ({param_count} parameters)"
            )
            
        except Exception as e:
            self.status.config(text=f"Error: {e}")
            print(f"Error loading {strategy_name}: {e}")
    
    def _show_config(self):
        """Show current configuration."""
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            return
        
        try:
            config = self.config_panel.get_config()
            
            print(f"\n=== Configuration for {strategy_name} ===")
            for key, value in config.items():
                print(f"  {key}: {value} ({type(value).__name__})")
            
            self.status.config(
                text=f"Configuration retrieved successfully - see console"
            )
            
        except Exception as e:
            self.status.config(text=f"Error: {e}")
            print(f"Error getting config: {e}")


def main():
    """Run demo."""
    app = StrategyConfigDemo()
    app.mainloop()


if __name__ == "__main__":
    main()
