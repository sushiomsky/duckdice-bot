# Tkinter GUI Development - Quick Start Guide

## For Developers

This guide helps you continue developing the DuckDice Bot tkinter GUI with the new enhancements.

## Project Structure

```
duckdice-bot/
├── duckdice_gui_ultimate.py          # Main tkinter GUI
├── src/
│   ├── gui_enhancements/             # Modular GUI components
│   │   ├── session_recovery_dialog.py  # Session recovery & confirmations
│   │   ├── settings_panel.py           # Settings management
│   │   ├── export_dialog.py            # Data export
│   │   ├── keyboard_shortcuts.py       # Keyboard navigation
│   │   ├── tkinter_chart.py            # Pure tkinter charts
│   │   ├── modern_ui.py                # Modern UI components
│   │   └── ...
│   ├── betbot_strategies/            # 17 betting strategies
│   ├── duckdice_api/                 # API client
│   └── ...
└── test_tkinter_enhancements.py     # Test new components
```

## Quick Setup

### 1. Install Dependencies

```bash
cd duckdice-bot
pip install -r requirements.txt
```

### 2. Run the GUI

```bash
python3 duckdice_gui_ultimate.py
```

### 3. Test New Components

```bash
python3 test_tkinter_enhancements.py
```

## Using New Components

### Session Recovery

Detect and restore interrupted sessions:

```python
# In your GUI __init__ or startup
def _check_for_interrupted_session(self):
    """Check for interrupted session on startup."""
    session_file = Path.home() / ".duckdice" / "last_session.json"
    
    if session_file.exists():
        with open(session_file) as f:
            session_data = json.load(f)
        
        SessionRecoveryDialog(
            self,
            session_data,
            on_restore=self._restore_session,
            on_discard=self._clear_session
        )

def _restore_session(self, data):
    """Restore previous session."""
    # Load strategy
    strategy_name = data['strategy_name']
    # Restore state
    # ...

def _clear_session(self):
    """Clear session and start fresh."""
    session_file = Path.home() / ".duckdice" / "last_session.json"
    session_file.unlink(missing_ok=True)
```

### Confirmation Dialogs

Replace standard messagebox with professional dialogs:

```python
# Before (old way)
result = messagebox.askyesno("Stop Betting", "Are you sure?")

# After (new way)
result = ConfirmationDialog.ask(
    self,
    title="Stop Betting",
    message="Are you sure you want to stop the current betting session?",
    confirm_text="Stop",
    cancel_text="Continue",
    dialog_type="warning"  # or 'error', 'info', 'question'
)
```

### Settings Panel

Show comprehensive settings:

```python
def _show_settings(self):
    """Open settings panel."""
    def on_save(changes):
        """Handle settings changes."""
        # Apply theme if changed
        if 'theme' in changes:
            self._apply_theme()
        
        # Update features if changed
        if 'sound_enabled' in changes:
            self.sound_manager.enabled = changes['sound_enabled']
        
        # Show confirmation
        Toast.show(self, "Settings saved!", toast_type="success")
    
    SettingsPanel(self, self.config_manager, on_save=on_save)
```

### Data Export

Export bet data:

```python
def _export_data(self):
    """Export bet history and statistics."""
    if not self.bet_logger.bets:
        Toast.show(self, "No data to export", toast_type="warning")
        return
    
    # Prepare session stats
    session_stats = {
        'total_bets': len(self.bet_logger.bets),
        'wins': sum(1 for b in self.bet_logger.bets if b.get('profit', 0) > 0),
        'losses': sum(1 for b in self.bet_logger.bets if b.get('profit', 0) < 0),
        'total_profit': sum(b.get('profit', 0) for b in self.bet_logger.bets)
    }
    
    ExportDialog(self, self.bet_logger.bets, session_stats)
```

### Tooltips

Add helpful tooltips:

```python
# In __init__
self.tooltip_manager = TooltipManager()

# Add tooltips to widgets
self.tooltip_manager.add(
    self.start_button,
    "Click to start automated betting",
    delay=500  # milliseconds
)

self.tooltip_manager.add(
    self.stop_button,
    "Stop betting immediately (or press F12)"
)
```

### Keyboard Shortcuts

Setup default shortcuts:

```python
from gui_enhancements.keyboard_shortcuts import (
    KeyboardShortcutManager,
    setup_default_shortcuts
)

# In __init__
self.shortcut_manager = KeyboardShortcutManager(self)

# Setup all default shortcuts
setup_default_shortcuts(self, self.shortcut_manager)

# Add custom shortcuts
self.shortcut_manager.register(
    '<Control-r>',
    self._refresh_data,
    'Refresh all data'
)
```

## Adding New Features

### 1. Create New Component

```python
# src/gui_enhancements/my_component.py
import tkinter as tk
from tkinter import ttk

class MyComponent(tk.Toplevel):
    """Description of component."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        
        self._setup_dialog()
        self._create_ui()
    
    def _setup_dialog(self):
        """Configure dialog window."""
        self.title("My Component")
        self.geometry("400x300")
        self.transient(self.master)
        self.grab_set()
    
    def _create_ui(self):
        """Create UI."""
        # Your UI code here
        pass
```

### 2. Export Component

```python
# src/gui_enhancements/__init__.py
from .my_component import MyComponent

__all__ = [
    # ... existing exports
    'MyComponent'
]
```

### 3. Use in Main GUI

```python
# duckdice_gui_ultimate.py
from gui_enhancements import MyComponent

class UltimateGUI(tk.Tk):
    def show_my_component(self):
        MyComponent(self)
```

## Best Practices

### 1. Follow Existing Patterns

✅ Use `ttk` widgets for consistent styling  
✅ Add docstrings to all methods  
✅ Use type hints where possible  
✅ Handle errors gracefully  

### 2. UI Design

✅ Modal dialogs for important actions  
✅ Clear button labels (not OK/Cancel)  
✅ Visual feedback (icons, colors)  
✅ Keyboard shortcuts  

### 3. Configuration

✅ Use ConfigManager for persistence  
✅ Provide sensible defaults  
✅ Validate user input  
✅ Save on change  

### 4. Error Handling

```python
try:
    # Risky operation
    result = self.api.do_something()
except APIError as e:
    # Show user-friendly error
    Toast.show(self, f"Operation failed: {e}", toast_type="error")
except Exception as e:
    # Log unexpected errors
    logging.error(f"Unexpected error: {e}")
    messagebox.showerror("Error", f"Unexpected error: {e}")
```

## Testing

### Test Individual Components

```python
# Create test file: test_my_feature.py
import tkinter as tk
from gui_enhancements import MyComponent

def test_component():
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    MyComponent(root)
    
    root.mainloop()

if __name__ == "__main__":
    test_component()
```

### Test Integration

```bash
# Run full GUI
python3 duckdice_gui_ultimate.py

# Test new components
python3 test_tkinter_enhancements.py
```

## Common Tasks

### Add Menu Item

```python
# In _create_menu()
file_menu.add_command(
    label="My Action",
    command=self._my_action,
    accelerator="Ctrl+M"
)
```

### Add Toolbar Button

```python
# In toolbar section
my_btn = ttk.Button(
    toolbar,
    text="My Action",
    command=self._my_action
)
my_btn.pack(side=tk.LEFT, padx=2)

# Add tooltip
self.tooltip_manager.add(my_btn, "Description of action")
```

### Add Settings Option

```python
# In SettingsPanel._create_*_settings()
my_var = tk.BooleanVar(value=self.config_manager.get('my_setting', True))
self._create_checkbox(
    parent,
    "Enable my feature",
    my_var,
    'my_setting'
)
```

## Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Use Python Debugger

```python
import pdb

def my_method(self):
    pdb.set_trace()  # Breakpoint
    # Your code
```

### Check State

```python
print(f"Current state: {vars(self)}")
print(f"Config: {self.config_manager.config}")
```

## Resources

- **Main GUI**: `duckdice_gui_ultimate.py`
- **Documentation**: `TKINTER_ENHANCEMENTS.md`
- **Examples**: `test_tkinter_enhancements.py`
- **User Guide**: `USER_GUIDE.md`

## Getting Help

1. Check existing components for examples
2. Read the documentation files
3. Run the test suite
4. Review the session summary

## Next Steps

1. ✅ Read this guide
2. ✅ Run test suite
3. ✅ Review existing components
4. ✅ Start building!

---

Happy coding! 🚀
