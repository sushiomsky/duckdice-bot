# Installation Fix for PyPI Package

## Issue

The `duckdice_cli.py`, `strategy_comparison.py`, `duckdice_tui.py`, and `duckdice.py` modules are in the root directory, but setuptools' editable install only includes the `src/` directory by default.

## Solution for Users

If you get `ModuleNotFoundError: No module named 'duckdice_cli'`:

### Option 1: Standard Install (Recommended for users)
```bash
pip install duckdice-betbot
# This works because non-editable install copies all files
```

### Option 2: Fix Editable Install (For developers)
```bash
cd /path/to/duckdice-bot
pip install -e .

# Then manually add root directory to the .pth file:
echo "$(pwd)" >> venv/lib/python*/site-packages/__editable__.duckdice_betbot-*.pth
```

### Option 3: Run from Source
```bash
cd /path/to/duckdice-bot
python duckdice_cli.py [args]
python duckdice_tui.py [args]
```

## Long-term Fix

Move all root `.py` files into `src/` directory structure:
```
src/
  duckdice_cli/
    __init__.py
    __main__.py  (contains main() function)
```

This is the recommended Python package structure and will fix the issue permanently.

## For Package Maintainers

Update `pyproject.toml` to properly handle both locations or restructure the package.
