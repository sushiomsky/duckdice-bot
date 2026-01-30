#!/bin/bash
# Demo: Adaptive Volatility Hunter Strategy
# Shows the strategy in action with simulation mode

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      Adaptive Volatility Hunter - Demo Session          ║"
echo "║                                                          ║"
echo "║  Ultra-low chance hunting with volatility adaptation    ║"
echo "║  Watch as the strategy adapts to RNG patterns!          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Run with default settings - 100 bets to see the adaptation in action
python3 duckdice_cli.py run \
  --mode simulation \
  --strategy adaptive-volatility-hunter \
  --max-bets 100 \
  --stop-loss -0.10 \
  --take-profit 0.50 \
  <<EOF
doge
EOF

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    Demo Complete                         ║"
echo "║                                                          ║"
echo "║  Key observations:                                       ║"
echo "║  • Volatility calculation adapts in real-time           ║"
echo "║  • Chance and bet size adjust automatically             ║"
echo "║  • Emergency brake activates during chaos               ║"
echo "║  • Profit lock protects winnings                        ║"
echo "║                                                          ║"
echo "║  For detailed guide, see:                               ║"
echo "║  docs/ADAPTIVE_VOLATILITY_HUNTER_GUIDE.md               ║"
echo "╚══════════════════════════════════════════════════════════╝"
