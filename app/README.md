# ⚠️ DEPRECATED - Old Web Interface Prototype

**This directory contains an incomplete prototype and is no longer maintained.**

## ✅ Use the New Web Interface Instead

The complete, production-ready NiceGUI web interface is now available in the `gui/` directory!

### Quick Start
```bash
# Run the new web interface
python3 gui/app.py

# Or use the convenience script
./run_gui_web.sh
# or
./run_nicegui.sh
```

Opens at: **http://localhost:8080**

## New Web Interface Features (v3.10.0)

✅ **5 Complete Screens**:
- **Dashboard** - Real-time bot control with live stats
- **Strategies** - Configure 5 betting strategies
- **Simulator** - Offline testing with analytics
- **History** - Bet history and CSV export
- **Settings** - Stop conditions and preferences

✅ **Safety Features**:
- Simulation mode by default
- No auto-start
- Emergency stop always accessible
- Thread-safe operations
- Input validation

✅ **Performance**:
- Real-time updates every 250ms
- <1 second page load
- Low memory usage (~50MB)

## Documentation

- **[GUI_README.md](../GUI_README.md)** - Complete user guide
- **[START_HERE.md](../START_HERE.md)** - Quick reference
- **[NICEGUI_IMPLEMENTATION.md](../NICEGUI_IMPLEMENTATION.md)** - Technical docs

## Migration Note

This `app/` directory will be removed in a future release. Please use `gui/` instead.

---

**Status**: Deprecated  
**Replacement**: `gui/` directory  
**Version**: v3.10.0+
