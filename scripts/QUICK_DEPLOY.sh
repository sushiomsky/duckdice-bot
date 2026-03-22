#!/bin/bash
# Quick Deployment Script for DuckDice Bot
# Version: 4.0.0

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

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
pip install -q textual
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

# Run quick validation
echo "🧪 Running validation tests..."
if pytest tests/test_strategy_integration.py -q >/dev/null 2>&1; then
    echo "   ✅ Validation test passed"
else
    echo "   ⚠️  Validation test had issues (continuing)"
fi
echo ""

# Start TUI
echo "🚀 Starting terminal interface..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎛️  Interface: Textual TUI"
echo "   Ctrl+S start, Ctrl+X stop, Ctrl+Q quit"
echo ""
echo "⌨️  Press Ctrl+C to stop"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Launch application
python3 duckdice_tui.py
