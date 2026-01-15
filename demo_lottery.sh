#!/bin/bash
# Demo: Streak Hunter with Lottery Feature

echo "🎰 Demo: Streak Hunter Strategy with Lottery Bets"
echo "="
echo ""
echo "Running 30 bets with:"
echo "  • Main: 14% chance streak hunting"
echo "  • Lottery: Every 5 bets @ 0.5-3% chance"
echo "  • Base bet: ~0.33 BTC"
echo ""
echo "Watch for 🎰 LOTTERY BET messages!"
echo ""

python3 duckdice_cli.py run \
  -m simulation \
  -s streak-hunter \
  -c btc \
  --max-bets 30 \
  --param lottery_enabled=true \
  --param lottery_frequency=5 \
  --param lottery_chance_min=0.5 \
  --param lottery_chance_max=3.0
