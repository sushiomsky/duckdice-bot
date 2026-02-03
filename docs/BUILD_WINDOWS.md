# Building Windows Package for DuckDice Bot

## Current Status

❌ **No pre-built Windows package available yet**

The build system is fully configured but needs to be run **on an actual Windows machine**. You cannot cross-compile Windows .exe files from macOS/Linux.

## Option 1: Build It Yourself (Recommended)

### Requirements
- Windows 10/11
- Python 3.7 or newer ([Download](https://www.python.org/downloads/))
- Git (optional)

### Quick Build Steps

1. **Get the code:**
   ```cmd
   git clone <repository-url>
   cd duckdice-bot
   ```

2. **Run the build script:**
   ```cmd
   build_windows.bat
   ```

   That's it! The script will:
   - ✅ Install all dependencies
   - ✅ Install PyInstaller
   - ✅ Build standalone .exe
   - ✅ Output to `dist\DuckDiceBot.exe`

3. **Find your executable:**
   ```
   dist\DuckDiceBot.exe  (ready to run!)
   ```

### Build Time
- First build: ~3-5 minutes
- Subsequent builds: ~1-2 minutes

### File Size
Expected: ~50-80 MB (includes Python + all dependencies)

## Option 2: Manual Build

If the batch script doesn't work:

```cmd
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build
pyinstaller --clean duckdice_gui_ultimate.spec

# Output
dist\DuckDiceBot.exe
```

## Option 3: Run Without Building

Don't need an .exe? Just run directly:

```cmd
# Install dependencies once
pip install -r requirements.txt

# Run anytime
python duckdice_gui_ultimate.py
```

## Build Configuration

The build uses `duckdice_gui_ultimate.spec` which includes:

✅ All 16 betting strategies
✅ Simulation engine (offline mode)
✅ Database logging (SQLite)
✅ Charts (pure Tkinter, no matplotlib needed)
✅ UX enhancements (toasts, shortcuts, etc.)
✅ Enhanced strategy info system

## Troubleshooting

### "Python not found"
Install Python from https://www.python.org/downloads/
**Important:** Check "Add Python to PATH" during installation!

### "pip not found"
Python installer should include pip. Try:
```cmd
python -m pip install --upgrade pip
```

### Build fails with import errors
Install missing packages:
```cmd
pip install -r requirements.txt
```

### "Missing module" errors
Add to hidden imports in `duckdice_gui_ultimate.spec`

### Antivirus flags .exe
This is normal for PyInstaller executables. Add exception or:
- Use `--onedir` instead of `--onefile` in spec
- Submit to VirusTotal for whitelisting
- Sign the executable with code signing certificate

## Creating Installer (Optional)

For a professional installer (.msi or setup.exe):

### Using NSIS (Free)

1. **Install NSIS:**
   https://nsis.sourceforge.io/Download

2. **Build .exe first:**
   ```cmd
   build_windows.bat
   ```

3. **Create installer:**
   ```cmd
   makensis scripts\build_ultimate.sh
   ```
   (Script contains NSIS config, extract the section)

### Using Inno Setup (Free)

1. **Install Inno Setup:**
   https://jrsoftware.org/isdl.php

2. **Create installer script:** See online guides

## Distribution

Once built, you can:

1. **Share the .exe:**
   - Just send `DuckDiceBot.exe`
   - No Python installation needed
   - Runs on any Windows 10/11

2. **Create ZIP:**
   ```cmd
   # Include documentation
   copy dist\DuckDiceBot.exe release\
   copy QUICK_START_GUIDE.md release\
   copy COMPLETE_FEATURES.md release\
   
   # Zip it
   tar -a -c -f DuckDiceBot-Windows.zip release\*
   ```

3. **Create installer:**
   Use NSIS or Inno Setup (see above)

## Pre-Built Package Request

To get a pre-built Windows package:

1. **Contact repo maintainer**
2. **Wait for GitHub Actions CI/CD** (if configured)
3. **Check Releases page** for official builds

Currently: ⏳ Pending first Windows build

## Why Can't We Build for Windows on macOS?

PyInstaller bundles:
- Python interpreter
- All dependencies  
- Platform-specific binaries

Each platform must build its own. You cannot:
- ❌ Build .exe on macOS/Linux
- ❌ Build .app on Windows/Linux
- ❌ Build Linux binary on macOS/Windows

## GitHub Actions (Future)

For automated builds on all platforms:

```yaml
# .github/workflows/build.yml
name: Build
on: [push]
jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pip install pyinstaller
      - run: pyinstaller --clean duckdice_gui_ultimate.spec
      - uses: actions/upload-artifact@v2
        with:
          name: DuckDiceBot-Windows
          path: dist/DuckDiceBot.exe
```

## Current Recommendation

**For Windows users:**

1. Clone the repo
2. Run `build_windows.bat`
3. Wait 3-5 minutes
4. Get your `dist\DuckDiceBot.exe`
5. Run and enjoy!

**OR**

Just run directly with Python (no build needed):
```cmd
pip install -r requirements.txt
python duckdice_gui_ultimate.py
```

---

**Questions?** Check:
- BUILD.md - General build instructions
- QUICK_START_GUIDE.md - Running without building
- COMPLETE_FEATURES.md - What's included
