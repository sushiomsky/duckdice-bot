#!/bin/bash
# Demonstration of DuckDice Bot Interactive Mode
# This script shows a complete interactive workflow

echo "============================================================"
echo "🎲 DuckDice Bot - Interactive Mode Demo"
echo "============================================================"
echo ""
echo "This demo shows the complete interactive workflow."
echo "We'll configure a simulation session with streak-hunter strategy."
echo ""
echo "Press Enter to continue..."
read

echo ""
echo "Starting interactive mode..."
echo "We'll use these inputs:"
echo "  1. Mode: Simulation"
echo "  2. Currency: BTC"  
echo "  3. Balance: 50.0"
echo "  4. Strategy: streak-hunter (17)"
echo "  5. Configure: No (use defaults)"
echo "  6. Stop-loss: -30% (-0.3)"
echo "  7. Take-profit: +50% (0.5)"
echo "  8. Max bets: 20"
echo "  9. Max losses: 0 (unlimited)"
echo " 10. Start: No (just show summary)"
echo ""
echo "Press Enter to run..."
read

# Run interactive mode with inputs
python3 duckdice_cli.py interactive << 'INPUTS'
1
1
50
17
n
-0.3
0.5
20
0
n
INPUTS

echo ""
echo "============================================================"
echo "Demo Complete!"
echo "============================================================"
echo ""
echo "As you can see, interactive mode makes it easy to:"
echo "  ✅ Configure all options step-by-step"
echo "  ✅ See clear descriptions and defaults"
echo "  ✅ Review summary before starting"
echo "  ✅ Use profiles for repeated configurations"
echo ""
echo "Try it yourself: python3 duckdice_cli.py"
echo ""
