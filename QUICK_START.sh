#!/bin/bash
# Quick Start Script for DuckDice Bot
# This script sets up and runs the bot in one command

set -e

cd "$(dirname "$0")"

echo "🎲 DuckDice Bot - Quick Start"
echo "=============================="
echo ""
echo "Choose interface:"
echo "  1) Web Interface (NiceGUI) - Recommended"
echo "  2) Desktop GUI (Tkinter)"
echo ""
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "2" ]; then
    # Tkinter GUI
    echo ""
    echo "🖥️  Starting Tkinter Desktop GUI..."
    echo ""
    
    # Check Tkinter
    if ! python3 -c "import tkinter" 2>/dev/null; then
        echo "❌ Tkinter not installed."
        echo ""
        echo "To install:"
        echo "  macOS: brew install python-tk@3.14"
        echo "  Ubuntu: sudo apt-get install python3-tk"
        exit 1
    fi
    
    # Activate venv if exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Run Tkinter GUI
    python3 duckdice_gui_ultimate.py
    exit 0
fi

# Web Interface (default)
echo ""
echo "🌐 Setting up Web Interface..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "✓ Dependencies installed"

# Create data directory if it doesn't exist
mkdir -p data
mkdir -p data/logs

# Check installation
echo ""
echo "🔍 Verifying installation..."
python3 -c "import nicegui; print('✓ NiceGUI installed')"
python3 -c "import matplotlib; print('✓ Matplotlib installed')"
python3 -c "import requests; print('✓ Requests installed')"

echo ""
echo "✅ Setup complete!"
echo ""
echo "=================================="
echo "🚀 Starting DuckDice Bot..."
echo "=================================="
echo ""
echo "📱 Web Interface: http://localhost:8080"
echo ""
echo "Keyboard Shortcuts:"
echo "  Ctrl+S - Start/Stop bot"
echo "  ESC    - Emergency stop"
echo "  Ctrl+P - Pause/Resume"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the app
python3 gui/app.py
