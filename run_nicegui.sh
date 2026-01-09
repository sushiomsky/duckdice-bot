#!/bin/bash
# Start DuckDice Bot NiceGUI Web Interface

cd "$(dirname "$0")"

echo "🎲 DuckDice Bot - NiceGUI Web Interface v3.10.0"
echo "================================================"
echo ""

# Activate venv
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if NiceGUI is installed
python3 -c "import nicegui" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

echo "🚀 Starting web server..."
echo "📱 Open your browser to: http://localhost:8080"
echo ""
echo "Features:"
echo "  • Dashboard - Real-time bot control"
echo "  • Strategies - Configure 5 betting strategies"
echo "  • Simulator - Offline testing with analytics"
echo "  • History - Bet history and CSV export"
echo "  • Settings - Stop conditions and preferences"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the new GUI
python3 gui/app.py
