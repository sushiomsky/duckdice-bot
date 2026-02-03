#!/bin/bash
# Demo script showing database logging in action

echo "=== Database Logging Demo ==="
echo ""
echo "1. Running a 20-bet simulation with classic-martingale..."
echo ""

python duckdice_cli.py run -m simulation -c btc -s classic-martingale \
    -b 100 -P base_amount=0.0001 -P chance=50 --max-bets 20 --db-log

echo ""
echo "2. Querying the database for the session..."
echo ""

SESSION_ID=$(sqlite3 data/duckdice_bot.db "SELECT session_id FROM sessions ORDER BY started_at DESC LIMIT 1;")

echo "Session ID: $SESSION_ID"
echo ""

sqlite3 data/duckdice_bot.db "SELECT 
    session_id,
    strategy_name,
    total_bets,
    wins,
    losses,
    ROUND(profit, 8) as profit,
    stop_reason
FROM sessions 
WHERE session_id = '$SESSION_ID';"

echo ""
echo "3. Last 5 bets from this session:"
echo ""

sqlite3 -header -column data/duckdice_bot.db "
SELECT 
    bet_number as '#',
    ROUND(amount, 8) as Amount,
    chance as 'Chance%',
    CASE WHEN won=1 THEN 'WIN' ELSE 'LOSS' END as Result,
    ROUND(profit, 8) as Profit,
    ROUND(balance, 8) as Balance,
    loss_streak as Streak
FROM bet_history 
WHERE session_id = '$SESSION_ID'
ORDER BY bet_number DESC
LIMIT 5;"

echo ""
echo "4. Session statistics:"
echo ""

sqlite3 data/duckdice_bot.db "
SELECT 
    'Total Bets: ' || COUNT(*) as stat FROM bet_history WHERE session_id = '$SESSION_ID'
UNION ALL
SELECT 'Total Wins: ' || SUM(won) FROM bet_history WHERE session_id = '$SESSION_ID'
UNION ALL
SELECT 'Win Rate: ' || ROUND(CAST(SUM(won) AS FLOAT) / COUNT(*) * 100, 2) || '%' FROM bet_history WHERE session_id = '$SESSION_ID'
UNION ALL
SELECT 'Total Profit: ' || ROUND(SUM(profit), 8) FROM bet_history WHERE session_id = '$SESSION_ID'
UNION ALL
SELECT 'Max Loss Streak: ' || MAX(loss_streak) FROM bet_history WHERE session_id = '$SESSION_ID';
"

echo ""
echo "=== Demo Complete ==="
echo "Database: data/duckdice_bot.db"
echo "See docs/DATABASE_LOGGING.md for more information"
