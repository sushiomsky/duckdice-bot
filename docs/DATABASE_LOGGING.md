# Database Logging Implementation

## Overview
Complete betting stream logging to SQLite database for debugging and strategy improvement analysis has been implemented and integrated into the core betting engine.

## Features

### Complete Bet Stream Capture
Every bet is logged with comprehensive data:
- **Bet Specification**: amount, chance, target, is_high/is_in, range, game type
- **Results**: win/loss, profit, roll number, payout multiplier
- **Balance Progression**: current balance after each bet
- **Strategy State**: internal strategy state snapshots (if available)
- **Session Context**: loss streaks, bet counts, timestamps

### Database Schema

#### `bet_history` Table
Stores every individual bet with complete details:
```sql
- id (PRIMARY KEY)
- session_id (indexed)
- timestamp (indexed)
- bet_number
- symbol, strategy (indexed)
- amount, chance, target, is_high
- range_low, range_high, is_in, game_type
- roll, won, profit, payout
- balance, loss_streak
- simulation_mode (indexed)
- api_raw (JSON), strategy_state (JSON)
- created_at
```

#### `sessions` Table
Tracks betting sessions with aggregated statistics:
```sql
- id (PRIMARY KEY)
- session_id (UNIQUE, indexed)
- strategy_name, symbol
- simulation_mode
- strategy_params (JSON)
- starting_balance, ending_balance
- started_at, ended_at (indexed)
- stop_reason
- stop_loss, take_profit, max_bet, max_bets, max_losses, max_duration_sec
- total_bets, wins, losses
- profit, profit_percent, duration_seconds
- metadata (JSON)
```

#### `strategy_profiles` Table
Saved strategy configurations for reuse:
```sql
- id (PRIMARY KEY)
- name (UNIQUE)
- strategy_name
- parameters (JSON)
- description
- created_at, updated_at
```

## Usage

### CLI Flags
```bash
# Enable database logging (default: enabled)
python duckdice_cli.py run --db-log ...

# Disable database logging
python duckdice_cli.py run --no-db-log ...

# Custom database path
python duckdice_cli.py run --db-path /path/to/custom.db ...
```

### Database Location
- **Default**: `data/duckdice_bot.db`
- **Custom**: Specify with `--db-path` flag

### Example Usage
```bash
# Run strategy with database logging (automatic)
python duckdice_cli.py run -m simulation -c btc -s classic-martingale \
    -b 100 -P base_amount=0.0001 -P chance=50 --max-bets 100

# Run without database logging
python duckdice_cli.py run -m simulation -c btc -s fibonacci \
    -b 100 --no-db-log ...
```

## Querying the Database

### Using Python
```python
from src.betbot_engine.bet_database import BetDatabase

db = BetDatabase()

# Get recent sessions
sessions = db.get_sessions(limit=10)

# Get session details
bets = db.get_session_bets(session_id='20260123_134416')

# Get statistics
stats = db.get_statistics(strategy_name='classic-martingale', since='2026-01-01')

# Export to CSV
from pathlib import Path
db.export_to_csv(
    output_path=Path('session_export.csv'),
    session_id='20260123_134416'
)
```

### Using SQL Directly
```bash
# List all sessions
sqlite3 data/duckdice_bot.db "SELECT session_id, strategy_name, total_bets, wins, losses, profit FROM sessions ORDER BY started_at DESC LIMIT 10;"

# Get bet details for a session
sqlite3 data/duckdice_bot.db "SELECT bet_number, amount, chance, won, profit, balance FROM bet_history WHERE session_id='20260123_134416' ORDER BY bet_number;"

# Strategy statistics
sqlite3 data/duckdice_bot.db "
SELECT 
    strategy,
    COUNT(*) as total_bets,
    SUM(won) as wins,
    SUM(CASE WHEN won=0 THEN 1 ELSE 0 END) as losses,
    AVG(profit) as avg_profit
FROM bet_history 
WHERE simulation_mode=1 
GROUP BY strategy;
"
```

## Benefits for Debugging

### 1. Bet-by-Bet Analysis
- Examine exact sequence of bets
- Identify patterns in wins/losses
- Analyze loss streaks
- Verify strategy logic execution

### 2. Balance Tracking
- Monitor balance progression over time
- Identify drawdown periods
- Detect balance anomalies

### 3. Strategy State Snapshots
- Inspect internal strategy state at each bet
- Debug strategy decision-making
- Verify parameter updates

### 4. Performance Analysis
- Compare strategies across sessions
- Identify optimal parameters
- Measure win rates and profitability

## Benefits for Strategy Improvement

### 1. Historical Analysis
- Query bets by date range, strategy, or session
- Calculate aggregate statistics
- Identify successful patterns

### 2. A/B Testing
- Compare different parameter sets
- Measure strategy performance
- Optimize configurations

### 3. Risk Analysis
- Analyze loss streak distributions
- Calculate maximum drawdown
- Measure volatility

### 4. Export and Analysis
- Export data to CSV for external analysis
- Use with Excel, Python pandas, R
- Create visualizations and reports

## Implementation Details

### Integration Points
- **Engine**: `src/betbot_engine/engine.py`
- **Database**: `src/betbot_engine/bet_database.py`
- **CLI**: `duckdice_cli.py`

### Database Initialization
- Automatic schema creation on first use
- Tables created with proper indexes
- Backward compatible with existing data

### Error Handling
- Database errors don't stop betting
- Graceful degradation if logging fails
- Errors logged but betting continues

### Performance
- Efficient indexes for common queries
- Minimal overhead on betting loop
- Asynchronous writes (SQLite handles this)

## File Locations

### Database
- Default: `data/duckdice_bot.db`
- Automatically created if missing

### JSONL Logs (Still Active)
- Location: `bet_history/auto/`
- Format: `{session_id}_{symbol}_{strategy}.jsonl`
- Complementary to database logging

## Migration

### Existing Data
- New schema is backward compatible
- Old sessions remain queryable
- New columns nullable for compatibility

### Upgrading
- No migration needed
- Database auto-creates new schema
- Existing data preserved

## Future Enhancements

### Potential Additions
1. Visualization dashboards
2. Real-time statistics tracking
3. Strategy comparison tools
4. Automated report generation
5. Machine learning integration for pattern detection

## Technical Notes

### Thread Safety
- SQLite connection per operation
- Context managers ensure proper cleanup
- Safe for parallel betting mode

### Storage
- SQLite file-based storage
- Efficient compression
- Typical size: ~1KB per bet

### Backup
```bash
# Backup database
cp data/duckdice_bot.db data/duckdice_bot_backup_$(date +%Y%m%d).db

# Vacuum database to reclaim space
sqlite3 data/duckdice_bot.db "VACUUM;"
```

## See Also
- `src/betbot_engine/bet_database.py` - Database implementation
- `src/betbot_engine/engine.py` - Engine integration
- `USER_GUIDE.md` - General usage guide
- `CLI_GUIDE.md` - CLI reference
