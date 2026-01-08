# Building DuckDice Bot

Instructions for building standalone executables.

## Prerequisites

- Python 3.7+
- PyInstaller: `pip install pyinstaller`

## Build CLI

```bash
pyinstaller --onefile --name duckdice-cli duckdice.py
```

Output: `dist/duckdice-cli` (or `dist/duckdice-cli.exe` on Windows)

## Build GUI

```bash
pyinstaller --onefile --windowed --name duckdice-gui duckdice_gui_ultimate.py
```

Output: `dist/duckdice-gui` (or `dist/duckdice-gui.exe` on Windows)

## Platform-Specific Notes

### Linux
```bash
# Install dependencies
sudo apt-get install python3-tk

# Build
pyinstaller --onefile duckdice.py
```

### macOS
```bash
# Install Tcl/Tk (for GUI)
brew install python-tk

# Build
pyinstaller --onefile --windowed duckdice_gui_ultimate.py
```

### Windows
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Build
pyinstaller --onefile --noconsole duckdice_gui_ultimate.py
```

## Distribution

After building, distribute the executables in `dist/` directory.

**Note:** Users still need their DuckDice API key to use the tools.
