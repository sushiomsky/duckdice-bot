#!/bin/bash
# Launcher script for DuckDice GUI
# 
# Usage: ./run_gui.sh
#
# This script ensures the GUI is run with the correct Python environment.

set -e

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.8 or later."
    exit 1
fi

# Check if tkinter is available
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Error: tkinter is not available in your Python installation."
    echo ""
    echo "To install tkinter:"
    echo "  - macOS: brew install python-tk@3.14 (or your Python version)"
    echo "  - Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  - Fedora: sudo dnf install python3-tkinter"
    exit 1
fi

echo "Starting DuckDice GUI..."
python3 duckdice_gui.py "$@"
