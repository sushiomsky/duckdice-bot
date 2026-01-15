# DuckDice Bot - Interface Guide

## Quick Reference

### Tkinter GUI (Desktop)
```bash
./run_gui.sh
# or
python3 duckdice_gui_ultimate.py
```

**Requirements**: Python 3.8+ with tkinter

### NiceGUI (Web Interface)
```bash
./run_nicegui.sh
# or
python3 gui/app.py
```

**Requirements**: Python 3.8+ with nicegui (`pip install nicegui`)

## What's Different?

### Tkinter GUI
- ✅ Traditional desktop application
- ✅ No browser required
- ✅ Works offline
- ❌ Does NOT include v4.0.1 improvements

### NiceGUI Web Interface
- ✅ Modern web-based interface
- ✅ Keyboard shortcuts (Ctrl+S, ESC, Ctrl+P)
- ✅ Session recovery system
- ✅ Profile auto-refresh
- ✅ Confirmation dialogs
- ✅ All v4.0.1 improvements
- ⚠️ Requires browser

## Improvements Only in Web Interface (v4.0.1)

1. **Profile Auto-Refresh** - List updates immediately after save/delete
2. **Confirmation Dialogs** - Prevents accidental deletions
3. **Keyboard Shortcuts** - Ctrl+S (start/stop), ESC (emergency), Ctrl+P (pause)
4. **Session Recovery** - Auto-save every 10 bets, crash recovery
5. **Better UX** - Enhanced notifications and error messages

## Running Now

Since you want Tkinter:
```bash
./run_gui.sh
```

This will now launch `duckdice_gui_ultimate.py` (the Tkinter desktop GUI).

---

**Note**: All code refactoring and improvements were made to the web interface (`gui/` folder). The Tkinter GUI (`duckdice_gui_ultimate.py`) is the original version and does not include these enhancements.
