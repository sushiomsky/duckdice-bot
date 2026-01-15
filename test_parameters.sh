#!/bin/bash
# Test parameter passing functionality

echo "=== Testing Strategy Parameter Support ==="
echo ""

echo "Test 1: Show strategy with parameters"
python3 duckdice_cli.py show classic-martingale | grep -A 10 "Parameters:"
echo ""

echo "Test 2: Run with custom parameters"
timeout 15 python3 duckdice_cli.py run \
  -m simulation \
  -s classic-martingale \
  -c btc \
  --max-bets 5 \
  -P base_amount=0.00001 \
  -P multiplier=1.5 \
  -P max_streak=3 | grep -E "(Applying|base_amount|multiplier|max_streak|Starting strategy)"
echo ""

echo "Test 3: RNG strategy with parameters"
timeout 15 python3 duckdice_cli.py run \
  -m simulation \
  -s rng-analysis-strategy \
  -c btc \
  --max-bets 5 \
  -P use_patterns=true \
  -P pattern_window=3 | grep -E "(Applying|use_patterns|pattern_window|Starting strategy)"
echo ""

echo "Test 4: List strategies verbose"
python3 duckdice_cli.py strategies -v | head -30
echo ""

echo "=== All Parameter Tests Complete ==="
