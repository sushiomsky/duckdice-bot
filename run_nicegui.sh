#!/bin/bash
# Start DuckDice Bot NiceGUI Edition

cd "$(dirname "$0")"

echo "🎲 DuckDice Bot - NiceGUI Edition"
echo "=================================="
echo ""

# Activate venv
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run: python3 -m venv venv && source venv/bin/activate && pip install nicegui"
    exit 1
fi

# Check if NiceGUI is installed
python3 -c "import nicegui" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing NiceGUI..."
    pip install nicegui
fi

echo "🚀 Starting web server..."
echo "📱 Open your browser to: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the app
python3 gui/app.py
