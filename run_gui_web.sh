#!/bin/bash
# Quick start script for NiceGUI web interface

echo "Starting DuckDice Bot Web Interface..."
echo "URL: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the GUI
python gui/app.py
