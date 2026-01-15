#!/bin/bash
# Quick setup and validation script

set -e

echo "🚀 DuckDice Bot - Setup & Validation"
echo "===================================="
echo ""

# Check Python
echo "1️⃣  Checking Python..."
python3 --version
echo ""

# Check/create venv
if [ ! -d "venv" ]; then
    echo "2️⃣  Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

echo "3️⃣  Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "4️⃣  Installing dependencies..."
pip install --upgrade pip
pip install -e .
pip install pytest pytest-cov
echo ""

# Run quick validation
echo "5️⃣  Running validation tests..."
pytest tests/test_strategy_integration.py -v --tb=short
echo ""

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Run tests: ./scripts/run_tests.sh"
echo "  3. Run bot: duckdice --help"
echo ""
