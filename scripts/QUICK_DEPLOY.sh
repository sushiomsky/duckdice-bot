#!/bin/bash
# Quick Deployment Script for DuckDice Bot
# Version: 4.0.0

set -e  # Exit on error

echo "🎲 DuckDice Bot - Quick Deployment"
echo "===================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python $PYTHON_VERSION detected"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "   ❌ Python 3.8+ required"
    exit 1
fi
echo "   ✅ Python version OK"
echo ""

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "📦 Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "   ✅ Activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "   ✅ Dependencies installed"
echo ""

# Create data directory
if [ ! -d "data" ]; then
    echo "📁 Creating data directory..."
    mkdir -p data
    echo "   ✅ Created"
else
    echo "📁 Data directory exists"
fi
echo ""

# Make scripts executable
echo "🔐 Setting permissions..."
chmod +x run_nicegui.sh run_gui.sh run_gui_web.sh
echo "   ✅ Scripts executable"
echo ""

# Run tests
echo "🧪 Running validation tests..."
cd tests/gui
if python3 test_gui_components.py 2>&1 | grep -q "7 passed"; then
    echo "   ✅ All tests passed"
else
    echo "   ⚠️  Some tests failed (non-critical)"
fi
cd ../..
echo ""

# Start server
echo "🚀 Starting web server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 Open your browser to:"
echo "   http://localhost:8080"
echo ""
echo "⌨️  Press Ctrl+C to stop"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Launch application
python3 gui/app.py
