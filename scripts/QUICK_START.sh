#!/bin/bash
# Quick Start Script for DuckDice Bot
# Sets up the project and launches a working interface.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

echo "🎲 DuckDice Bot - Quick Start"
echo "=============================="
echo ""
echo "Choose interface:"
echo "  1) Modern Textual TUI (recommended)"
echo "  2) Classic ncurses TUI"
echo "  3) CLI interactive mode"
echo ""
read -p "Enter choice (1, 2, or 3) [1]: " choice
choice="${choice:-1}"

echo ""
echo "🔍 Checking Python..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: ${PYTHON_VERSION}"

if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

echo ""
echo "📦 Activating virtual environment..."
source venv/bin/activate

echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Textual is optional in pyproject extras; install for TUI paths.
if [ "${choice}" = "1" ] || [ "${choice}" = "2" ]; then
    pip install textual -q
fi
echo "✓ Dependencies installed"

mkdir -p data data/logs bet_history

echo ""
echo "✅ Setup complete!"
echo "=================================="

case "${choice}" in
    1)
        echo "🚀 Launching Textual TUI..."
        echo "Keyboard Shortcuts: Ctrl+S start, Ctrl+X stop, Ctrl+Q quit"
        python3 duckdice_tui.py
        ;;
    2)
        echo "🚀 Launching ncurses TUI..."
        echo "Keyboard Controls: S start/resume, P pause, X stop, Q quit"
        python3 duckdice_tui.py --ncurses
        ;;
    3)
        echo "🚀 Launching CLI interactive mode..."
        python3 duckdice_cli.py interactive
        ;;
    *)
        echo "❌ Invalid choice: ${choice}"
        exit 1
        ;;
esac
