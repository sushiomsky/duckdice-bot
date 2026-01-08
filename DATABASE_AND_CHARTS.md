# 📊 Database & Live Charts - Always Working!

## Overview

DuckDice Bot features **persistent SQLite database** for all bet history and **pure Tkinter live charts** that work without any external dependencies!

---

## ✨ Key Features

### 1. **SQLite Database Storage**
- ✅ **Persistent storage** - All bets saved forever
- ✅ **Separate tables** - Live bets vs Simulation bets
- ✅ **Session tracking** - Group bets by session
- ✅ **Full metadata** - Every detail saved
- ✅ **Fast queries** - Indexed for performance
- ✅ **Export support** - CSV export available

### 2. **Pure Tkinter Live Charts**
- ✅ **No dependencies** - Works without matplotlib!
- ✅ **Real-time updates** - Smooth 60 FPS rendering
- ✅ **Win/loss markers** - Visual indicators
- ✅ **Auto-scaling** - Adapts to data range
- ✅ **Statistics display** - Current profit, win rate
- ✅ **Responsive** - Resizes with window

### 3. **Dual Chart System**
- 🎨 **Tkinter Chart** - Always available (default)
- 📊 **Matplotlib Chart** - Optional upgrade (if installed)
- 🔄 **Auto-detection** - Uses best available

---

## 📁 Database Structure

### Location
```
~/.duckdice/bets.db
```

### Tables

#### `live_bets`
Stores real money bets:
```sql
- id (INTEGER PRIMARY KEY)
- timestamp (TEXT)
- session_id (TEXT)
- symbol (TEXT) - Currency (BTC, DOGE, etc.)
- strategy (TEXT) - Strategy name
- bet_amount (REAL)
- chance (REAL) - Win chance %
- payout (REAL) - Payout multiplier
- is_high (INTEGER) - Roll high/low
- is_win (INTEGER) - Win/loss
- profit (REAL) - Profit/loss
- balance (REAL) - Balance after bet
- roll_value (REAL) - Actual roll
- target_value (REAL) - Target number
- multiplier (REAL)
- metadata (TEXT) - JSON additional data
```

#### `simulation_bets`
Identical structure for simulation bets

#### `sessions`
Tracks betting sessions:
```sql
- id (TEXT PRIMARY KEY)
- is_simulation (INTEGER)
- start_time (TEXT)
- end_time (TEXT)
- strategy (TEXT)
- initial_balance (REAL)
- final_balance (REAL)
- total_bets (INTEGER)
- total_wins (INTEGER)
- total_profit (REAL)
- metadata (TEXT)
```

---

## 🔧 API Usage

### BetLogger

```python
from src.gui_enhancements.bet_logger import BetLogger
from decimal import Decimal

# Initialize
logger = BetLogger()  # Uses ~/.duckdice/bets.db

# Start session
session_id = "my-session-1"
logger.start_session(
    session_id=session_id,
    is_simulation=True,  # or False for live
    strategy="classic-martingale",
    initial_balance=100
)

# Log a bet
bet_data = {
    'session_id': session_id,
    'symbol': 'DOGE',
    'strategy': 'classic-martingale',
    'bet_amount': Decimal("1.0"),
    'chance': Decimal("50.0"),
    'payout': Decimal("2.0"),
    'is_high': True,
    'is_win': True,
    'profit': Decimal("1.0"),
    'balance': Decimal("101.0")
}

logger.log_bet(bet_data, is_simulation=True)

# Get statistics
stats = logger.get_statistics(
    is_simulation=True,
    session_id=session_id
)
print(f"Total bets: {stats['total_bets']}")
print(f"Win rate: {stats['win_rate']:.1f}%")
print(f"Total profit: {stats['total_profit']:.4f}")

# Query bets
bets = logger.get_bets(
    is_simulation=True,
    session_id=session_id,
    limit=100
)

# End session
logger.end_session(
    session_id=session_id,
    is_simulation=True,
    final_balance=105
)

# Export to CSV
logger.export_to_csv(
    output_file="my_bets.csv",
    is_simulation=True
)
```

### Live Chart

```python
import tkinter as tk
from src.gui_enhancements.tkinter_chart import TkinterLiveChart
from decimal import Decimal

# Create window
root = tk.Tk()

# Create chart
chart = TkinterLiveChart(root, max_points=100)
chart.pack(fill=tk.BOTH, expand=True)

# Add data points
balance = Decimal("100")
for i in range(50):
    is_win = i % 2 == 0
    profit = Decimal("0.5") if is_win else Decimal("-0.3")
    balance += profit
    
    # Update chart
    chart.add_data_point(balance, is_win)

# Clear chart
chart.clear()

root.mainloop()
```

---

## 🎯 Integration in GUI

The GUI automatically integrates both systems:

### Dashboard Tab
- Shows current balance
- Displays session statistics
- Updates in real-time

### Auto Bet Tab
- Logs every bet to database
- Updates live chart
- Tracks session progress

### History Tab
- Queries database
- Filters by date/outcome
- Exports to CSV/JSON

### Statistics Tab
- Calculates from database
- Shows win rate, profit
- Historical trends

---

## 📊 Chart Features

### Visual Elements
- **Blue Line** - Balance over time
- **Green Triangles** - Wins (pointing up)
- **Red Triangles** - Losses (pointing down)
- **Grid Lines** - Reference points
- **Axes Labels** - Balance & time

### Statistics Display
Shows in real-time:
- Current balance
- Total profit (amount + %)
- Number of data points

### Auto-Scaling
- Automatically adjusts Y-axis to data range
- Adds 10% padding for clarity
- X-axis shows time labels

### Performance
- Smooth 60 FPS updates
- Efficient canvas redrawing
- Handles 100+ data points easily

---

## 🔄 Simulation vs Live

### Simulation Mode
- Stored in `simulation_bets` table
- Safe testing environment
- No real money involved
- Full statistics tracking

### Live Mode
- Stored in `live_bets` table
- Real API calls
- Actual betting
- Complete audit trail

### Both Modes Feature
- Full database logging
- Live chart updates
- Session management
- Statistics calculation
- History export

---

## 💾 Data Persistence

### Automatic Saving
- Every bet logged immediately
- No data loss on crash
- Database transactions
- Commit after each bet

### Data Retention
- Unlimited history storage
- Automatic cleanup available
- `clear_old_data(days=90)` method
- Manual export before cleanup

### Database Backups
Location: `~/.duckdice/bets.db`

Backup manually:
```bash
cp ~/.duckdice/bets.db ~/.duckdice/bets_backup_$(date +%Y%m%d).db
```

---

## 📈 Query Examples

### Get Today's Stats
```python
from datetime import datetime

start_date = datetime.now().date().isoformat()
stats = logger.get_statistics(
    is_simulation=False,
    start_date=start_date
)
```

### Filter by Strategy
```python
stats = logger.get_statistics(
    is_simulation=True,
    strategy="classic-martingale"
)
```

### Get Recent Sessions
```python
sessions = logger.get_sessions(
    is_simulation=True,
    limit=10
)
```

### Export Session Data
```python
bets = logger.get_bets(
    is_simulation=True,
    session_id="my-session",
    limit=1000
)

logger.export_to_csv(
    output_file="session_export.csv",
    is_simulation=True,
    session_id="my-session"
)
```

---

## 🎨 Chart Customization

### Tkinter Chart
Pure Python, always available:
- Customizable colors
- Adjustable max_points
- Responsive layout
- Clean design

### Matplotlib Chart (Optional)
Install for advanced features:
```bash
pip install matplotlib
```

Features:
- Zoom/pan tools
- Save as image
- Professional appearance
- Interactive toolbar

---

## ⚡ Performance

### Database
- **Indexed queries** - Fast lookups
- **Batch inserts** - Efficient logging
- **Connection pooling** - Reuses connections
- **Optimized schema** - Minimal storage

### Charts
- **Deque storage** - O(1) operations
- **Canvas optimization** - Efficient redraws
- **Lazy updates** - Only redraw when needed
- **Memory efficient** - Circular buffer

---

## 🐛 Troubleshooting

### "Database locked"
→ Close other instances of the app
→ Check file permissions on ~/.duckdice/

### "Chart not updating"
→ Ensure `add_data_point()` is called
→ Check if window is visible
→ Verify data is valid (Decimal type)

### "Missing statistics"
→ Ensure bets are logged with is_simulation flag
→ Check session_id matches
→ Verify database has data

### "Slow queries"
→ Database auto-indexes common queries
→ Limit result sets with `limit` parameter
→ Use date filters to narrow results

---

## 📚 Best Practices

### Logging Bets
```python
# Always use Decimal for money
bet_amount = Decimal("1.0")  # ✓
bet_amount = 1.0  # ✗ (float imprecision)

# Include session_id
bet_data['session_id'] = current_session  # ✓

# Set is_simulation correctly
logger.log_bet(data, is_simulation=True)  # ✓
```

### Managing Sessions
```python
# Start session before betting
logger.start_session(...)

# Log bets during session
for bet in bets:
    logger.log_bet(...)

# End session after betting
logger.end_session(...)
```

### Updating Charts
```python
# Update chart after each bet
balance = new_balance()
is_win = bet_won()
chart.add_data_point(balance, is_win)  # ✓

# Clear chart when starting new session
chart.clear()  # ✓
```

---

## 🎯 Example: Complete Session

```python
from src.gui_enhancements.bet_logger import BetLogger
from src.gui_enhancements.tkinter_chart import TkinterLiveChart
import tkinter as tk
from decimal import Decimal

# Setup
logger = BetLogger()
root = tk.Tk()
chart = TkinterLiveChart(root, max_points=100)
chart.pack(fill=tk.BOTH, expand=True)

# Start session
session_id = "demo-session"
logger.start_session(
    session_id, 
    is_simulation=True,
    strategy="classic-martingale",
    initial_balance=100
)

# Simulate betting
balance = Decimal("100")
for i in range(50):
    is_win = i % 3 != 0
    profit = Decimal("1") if is_win else Decimal("-1")
    balance += profit
    
    # Log to database
    logger.log_bet({
        'session_id': session_id,
        'symbol': 'DOGE',
        'strategy': 'classic-martingale',
        'bet_amount': Decimal("1"),
        'chance': Decimal("66"),
        'payout': Decimal("1.5"),
        'is_high': True,
        'is_win': is_win,
        'profit': profit,
        'balance': balance
    }, is_simulation=True)
    
    # Update chart
    chart.add_data_point(balance, is_win)

# End session
logger.end_session(session_id, is_simulation=True, final_balance=balance)

# Show stats
stats = logger.get_statistics(is_simulation=True, session_id=session_id)
print(f"Final stats: {stats}")

root.mainloop()
```

---

## ✅ Summary

### Database Features
✓ Persistent SQLite storage
✓ Separate live/simulation tables
✓ Session management
✓ Full statistics
✓ Query filtering
✓ CSV export
✓ Automatic indexing

### Chart Features
✓ Works without matplotlib
✓ Real-time updates
✓ Win/loss markers
✓ Auto-scaling
✓ Statistics display
✓ Responsive design
✓ 60 FPS smooth

### Integration
✓ Auto-logging in GUI
✓ Real-time chart updates
✓ Session tracking
✓ Export capabilities
✓ Historical analysis

---

**Both systems work perfectly without any external dependencies!** 🎉

Database: SQLite (built into Python)
Charts: Tkinter Canvas (built into Python)
No matplotlib required (but supported if installed)!
