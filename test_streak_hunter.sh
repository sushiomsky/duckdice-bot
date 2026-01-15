#!/bin/bash
echo "=== Testing Streak Hunter Strategy ==="
echo ""

echo "Test 1: Show strategy details"
python3 duckdice_cli.py show streak-hunter | grep -E "(Description|Risk Level|Parameters|chance|multiplier)"
echo ""

echo "Test 2: Default parameters (should show 14% chance, balance/300)"
timeout 30 python3 duckdice_cli.py run -s streak-hunter -m simulation -c btc --max-bets 10 2>&1 | grep -E "(Target chance|Base bet|Win multipliers|Streak|SUMMARY)" | head -20
echo ""

echo "Test 3: Custom parameters"
timeout 30 python3 duckdice_cli.py run -s streak-hunter -m simulation -c btc --max-bets 10 \
  -P chance=14 \
  -P min_bet=0.01 \
  -P first_multiplier=1.5 \
  -P second_multiplier=1.3 \
  2>&1 | grep -E "(Applying|chance|multiplier|Base bet|Win multipliers)"
echo ""

echo "=== All Streak Hunter Tests Complete ==="
