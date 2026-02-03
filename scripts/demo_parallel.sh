#!/bin/bash
# Demo: Sequential vs Parallel Betting Performance

echo "=========================================="
echo "DuckDice Bot - Parallel Betting Demo"
echo "=========================================="
echo ""

echo "Test 1: Sequential Mode (default)"
echo "----------------------------------"
echo "Running 20 bets with classic-martingale..."
time python3 duckdice_cli.py run -m simulation -s classic-martingale -c btc \
    --max-bets 20 -P base_amount=0.001 2>&1 | grep -E "(Bet #|Stop reason)"
echo ""

echo "Test 2: Parallel Mode (3 concurrent)"
echo "-------------------------------------"
echo "Running 20 bets with classic-martingale..."
time python3 duckdice_cli.py run -m simulation -s classic-martingale -c btc \
    --max-bets 20 --parallel --max-concurrent 3 -P base_amount=0.001 2>&1 | grep -E "(Bet #|Stop reason|Parallel)"
echo ""

echo "Test 3: Parallel Mode (5 concurrent)"
echo "-------------------------------------"
echo "Running 20 bets with classic-martingale..."
time python3 duckdice_cli.py run -m simulation -s classic-martingale -c btc \
    --max-bets 20 --parallel --max-concurrent 5 -P base_amount=0.001 2>&1 | grep -E "(Bet #|Stop reason|Parallel)"
echo ""

echo "=========================================="
echo "Demo Complete!"
echo "=========================================="
