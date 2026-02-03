#!/bin/bash
# Quick script to compare all strategies with Monte Carlo simulation

echo "🎲 DuckDice Strategy Comparison Tool - Monte Carlo"
echo "===================================================="
echo ""

# Default values
BALANCE="${1:-10.0}"
BETS="${2:-10000}"
RUNS="${3:-100}"
OUTPUT="${4:-strategy_comparison_$(date +%Y%m%d_%H%M%S).html}"

echo "Configuration:"
echo "  Starting Balance: $BALANCE BTC"
echo "  Bets Per Run: $BETS"
echo "  Runs Per Strategy: $RUNS"
echo "  Total Bets Per Strategy: $((BETS * RUNS))"
echo "  Output: $OUTPUT"
echo ""
echo "⏳ Running Monte Carlo simulation (this will take a while)..."
echo ""

python3 strategy_comparison.py -b "$BALANCE" -n "$BETS" -r "$RUNS" -o "$OUTPUT"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Comparison complete!"
    echo ""
    echo "📊 Open the report:"
    echo "   file://$(pwd)/$OUTPUT"
    echo ""
    echo "💡 Tip: Open in your web browser to view interactive charts"
else
    echo ""
    echo "❌ Comparison failed!"
    exit 1
fi
