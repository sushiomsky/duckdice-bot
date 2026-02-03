# DuckDice Bot Architecture

**Version**: 4.11.2 | **License**: MIT

## 🏗️ System Overview

```
┌─────────────────────────────────────────────────────────┐
│                   User Interfaces                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │   CLI    │  │   TUI    │  │   Python API         │  │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘  │
└───────┼─────────────┼───────────────────┼──────────────┘
        │             │                   │
        └─────────────┴───────────────────┘
                      │
        ┌─────────────▼──────────────┐
        │    BetBot Engine           │
        │  ┌──────────────────────┐  │
        │  │  Strategy Manager    │  │
        │  └──────────────────────┘  │
        │  ┌──────────────────────┐  │
        │  │  Bet Validator       │  │
        │  └──────────────────────┘  │
        │  ┌──────────────────────┐  │
        │  │  Event System        │  │
        │  └──────────────────────┘  │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │    DuckDice API Client     │
        │  ┌──────────────────────┐  │
        │  │  Domain Fallback     │  │
        │  └──────────────────────┘  │
        │  ┌──────────────────────┐  │
        │  │  Rate Limiting       │  │
        │  └──────────────────────┘  │
        │  ┌──────────────────────┐  │
        │  │  Response Parser     │  │
        │  └──────────────────────┘  │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │   DuckDice.io API          │
        │   (.io / .live / .net)     │
        └────────────────────────────┘
```

---

## 📦 Core Components

### 1. **BetBot Engine** (`src/betbot_engine/`)

The core betting engine that orchestrates all operations.

**Key Files**:
- `engine.py` - Main engine loop and state management
- `bet_validator.py` - Validates bets against API limits
- `event_system.py` - Event pub/sub for extensibility
- `database.py` - SQLite bet history logging

**Responsibilities**:
- Strategy execution
- Bet placement and tracking
- Balance management
- Stop condition evaluation
- Event publishing

**Example**:
```python
from betbot_engine import BettingEngine

engine = BettingEngine(
    api=duck_api,
    strategy="classic-martingale",
    max_bets=100
)
engine.run()
```

---

### 2. **Strategy System** (`src/betbot_strategies/`)

Pluggable strategy architecture with DiceBot compatibility.

**Key Concepts**:
- All strategies implement the **`dobet()` pattern**
- Compatible with original DiceBot Lua scripts
- Python strategies use same global variables
- No modifications needed for imported strategies

**Globals Available to Strategies**:
```python
# Read/Write
balance         # Current balance
nextbet         # Next bet amount
chance          # Win chance (0.01 - 98.00)
bethigh         # True = bet high, False = bet low

# Read-Only
win             # True if last bet won
currentprofit   # Profit from current bet
profit          # Session profit/loss
currentstreak   # Current win/loss streak
previousbet     # Amount of previous bet
```

**Strategy Interface**:
```python
class MyStrategy:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        # Initialize strategy state
    
    def dobet(self):
        """Called after each bet"""
        # Strategy logic here
        # Modify: balance, nextbet, chance, bethigh
        pass
    
    def get_initial_bet(self):
        """Return first bet amount"""
        return self.balance * 0.01
    
    def get_initial_chance(self):
        """Return first bet chance"""
        return 50.0
```

**See**: [Strategy Development Guide](./STRATEGY_DEVELOPMENT.md)

---

### 3. **DuckDice API Client** (`src/duckdice_api/`)

Robust API client with automatic fallback and retry logic.

**Key Files**:
- `api.py` - Main API client class
- `config.py` - Configuration and domain management
- `exceptions.py` - Custom exception types

**Features**:
- ✅ **Multi-domain fallback**: `.io` → `.live` → `.net`
- ✅ **Auto-retry**: Exponential backoff on failures
- ✅ **Rate limiting**: Prevents API throttling
- ✅ **Request validation**: Checks limits before sending
- ✅ **Response parsing**: Handles all API error codes

**Domain Fallback Logic**:
```python
DOMAIN_ORDER = [
    "duckdice.io",      # Primary
    "duckdice.live",    # Fallback 1
    "duckdice.net"      # Fallback 2
]

# Automatic retry on failure:
# 1. Try duckdice.io (timeout 10s)
# 2. Try duckdice.live (timeout 15s)
# 3. Try duckdice.net (timeout 20s)
# 4. Raise APIError if all fail
```

**Example**:
```python
from duckdice_api import DuckDiceAPI

api = DuckDiceAPI(api_key="your-key")

# Automatic domain fallback
result = api.place_bet(
    amount=0.01,
    chance=50.0,
    bet_high=True
)

# Manual domain selection
api.config.current_domain = "duckdice.live"
```

**See**: [API Fallback Documentation](../API_FALLBACK.md)

---

## 🔄 Request Flow

### Typical Bet Sequence

```
User
  │
  ├─► CLI/TUI: Parse args, load config
  │
  ├─► Engine: Initialize strategy
  │
  ├─► Strategy: get_initial_bet() → 0.01 BTC
  ├─► Strategy: get_initial_chance() → 50.0%
  │
  ├─► Validator: Check bet against API limits
  │   ├─ Min bet: 0.00000001 BTC
  │   ├─ Max bet: (varies by balance)
  │   ├─ Chance: 0.01% - 98.00%
  │   └─ ✓ Valid
  │
  ├─► API Client: place_bet(0.01, 50.0, True)
  │   ├─► Try duckdice.io
  │   ├─ ✓ Success
  │   └─ Return result
  │
  ├─► Engine: Update balance, profit
  ├─► Strategy: dobet() - calculate next bet
  ├─► Event System: Publish 'bet_placed' event
  ├─► Database: Log bet to SQLite
  │
  └─► Repeat or stop (max bets, profit target, etc.)
```

---

## 🛡️ Bet Validation

**Three-layer validation** ensures safe operation:

### Layer 1: Strategy Validation
- Strategies self-validate before returning bet
- Example: Martingale checks bankroll vs next bet

### Layer 2: Engine Validation
- Checks bet amount vs balance
- Verifies chance is in valid range (0.01 - 98.00)
- Ensures bet meets minimum (0.00000001)

### Layer 3: API Validation
- Server-side validation by DuckDice API
- Returns error codes if invalid:
  - `422`: Unprocessable Entity (invalid params)
  - `400`: Bad Request (malformed)
  - `401`: Unauthorized (bad API key)

**Bet Adjustment Logic**:
```python
# If bet < minimum
if bet < 0.00000001:
    bet = 0.00000001
    logger.warning("Bet too small, using minimum")

# If bet > balance
if bet > balance:
    bet = balance
    logger.warning("Bet exceeds balance, using max")
```

**See**: [Bet Validation Details](../BET_VALIDATION.md)

---

## 📡 Event System

Extensible pub/sub system for monitoring and plugins.

**Available Events**:
- `bet_placed` - After successful bet
- `bet_failed` - After failed bet attempt
- `balance_updated` - When balance changes
- `strategy_changed` - Strategy switch (TUI)
- `stop_condition_met` - Engine stopping
- `session_start` - Engine starts
- `session_end` - Engine stops

**Subscribe to Events**:
```python
from betbot_engine import BettingEngine

def on_bet(event_data):
    print(f"Bet placed: {event_data['amount']} @ {event_data['chance']}%")
    print(f"Result: {'WIN' if event_data['win'] else 'LOSS'}")

engine = BettingEngine(...)
engine.event_bus.subscribe('bet_placed', on_bet)
engine.run()
```

**Custom Event Handlers**:
```python
class TelegramNotifier:
    def __init__(self, bot_token):
        self.bot = telegram.Bot(token=bot_token)
    
    def on_big_win(self, event_data):
        if event_data['profit'] > 1.0:
            self.bot.send_message(
                chat_id=CHAT_ID,
                text=f"🎉 Big win! +{event_data['profit']} BTC"
            )

notifier = TelegramNotifier(TOKEN)
engine.event_bus.subscribe('bet_placed', notifier.on_big_win)
```

---

## 💾 Database Logging

All bets logged to SQLite for analysis and replay.

**Schema**:
```sql
CREATE TABLE bet_history (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    strategy TEXT,
    bet_amount REAL,
    chance REAL,
    bet_high BOOLEAN,
    win BOOLEAN,
    profit REAL,
    balance REAL,
    roll REAL,
    session_id TEXT
);
```

**Querying History**:
```python
from betbot_engine import BetDatabase

db = BetDatabase("data/duckdice_bot.db")

# Get recent bets
recent = db.get_recent_bets(limit=100)

# Get session stats
stats = db.get_session_stats(session_id="abc123")

# Export to CSV
db.export_to_csv("my_bets.csv", session_id="abc123")
```

**See**: [Database Documentation](../DATABASE_LOGGING.md)

---

## 🔌 Plugin Architecture

Extend functionality through plugins:

### Example: Custom Stop Condition
```python
from betbot_engine import BettingEngine

class TimeBasedStopper:
    def __init__(self, duration_seconds):
        self.start_time = time.time()
        self.duration = duration_seconds
    
    def should_stop(self, engine_state):
        elapsed = time.time() - self.start_time
        return elapsed >= self.duration

engine = BettingEngine(...)
engine.add_stop_condition(TimeBasedStopper(3600))  # 1 hour
engine.run()
```

### Example: Live Statistics Dashboard
```python
class LiveDashboard:
    def __init__(self):
        self.bets = 0
        self.wins = 0
    
    def on_bet(self, event_data):
        self.bets += 1
        if event_data['win']:
            self.wins += 1
        
        win_rate = (self.wins / self.bets) * 100
        print(f"Win Rate: {win_rate:.2f}% ({self.wins}/{self.bets})")

dashboard = LiveDashboard()
engine.event_bus.subscribe('bet_placed', dashboard.on_bet)
```

---

## 🏛️ Design Principles

### 1. **CLI-First Architecture**
Every feature MUST work via non-interactive CLI:
```bash
# All features accessible without prompts
duckdice run --strategy X --bets 100 --profit-target 1.0
```

### 2. **100% Decoupled Layers**
- Core engine has ZERO UI dependencies
- Strategies have ZERO UI dependencies  
- UI layers are thin wrappers around core

**Correct**:
```python
# Core engine
class BettingEngine:
    def run(self):
        result = self.place_bet()  # No UI calls
        return result

# UI layer
def interactive_mode():
    engine = BettingEngine()
    user_input = input("Bet amount? ")  # UI in UI layer only
    engine.run()
```

**Incorrect**:
```python
# ❌ WRONG - UI in core
class BettingEngine:
    def run(self):
        if interactive:
            amount = input("Bet amount? ")  # ❌ UI in core
```

### 3. **DiceBot Compatibility**
All strategies maintain 100% compatibility with original DiceBot:
- Same global variables
- Same `dobet()` pattern
- Imported Lua strategies work WITHOUT modification

### 4. **Clean Repository**
- NO legacy files (git history preserves them)
- NO `.bak` or `.old` files
- NO commented-out code blocks
- Documentation always current (no "TODO" docs)

---

## 📁 Directory Structure

```
duckdice-bot/
├── src/
│   ├── betbot_engine/           # Core engine
│   │   ├── engine.py
│   │   ├── bet_validator.py
│   │   ├── event_system.py
│   │   └── database.py
│   ├── betbot_strategies/       # 25 strategies
│   │   ├── __init__.py
│   │   ├── classic_martingale.py
│   │   ├── adaptive_survival.py
│   │   └── ...
│   └── duckdice_api/            # API client
│       ├── api.py
│       ├── config.py
│       └── exceptions.py
├── duckdice_cli.py             # CLI interface
├── duckdice_tui.py             # TUI interface
├── duckdice.py                 # Legacy wrapper
├── tests/                      # Test suite
├── scripts/                    # Demo/utility scripts
├── docs/                       # Documentation
│   ├── INTERFACES/
│   ├── STRATEGIES/
│   └── ARCHITECTURE/
├── .github/
│   └── workflows/              # CI/CD
│       └── build-and-release.yml
├── pyproject.toml             # Python package config
├── requirements.txt           # Dependencies
└── README.md                  # Project overview
```

---

## 🧪 Testing

**Test Coverage**:
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Strategy tests: `tests/strategies/`

**Run Tests**:
```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_engine.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Philosophy**:
- Tests MUST pass before merging to main
- CI runs tests on Python 3.9-3.12 × 3 OS
- Broken tests block releases (per DEVELOPMENT_GUARDRAILS.md)

---

## 🚀 CI/CD Pipeline

**Trigger**: Commit to `main` or tag `v*`

**Steps**:
1. **Test** (Python 3.9, 3.10, 3.11, 3.12 × Windows/macOS/Linux)
2. **Build Python Package** (wheel + sdist)
3. **Build Executables** (PyInstaller for each OS)
4. **Publish to PyPI** (Trusted Publishing, no secrets)
5. **Create GitHub Release** (with all artifacts)

**Workflow File**: `.github/workflows/build-and-release.yml`

**See**: [Release Workflow](../RELEASE_WORKFLOW.md)

---

## 🔐 Security

### API Key Management
```bash
# Environment variable (recommended)
export DUCKDICE_API_KEY="your-key-here"
duckdice run --strategy martingale

# .env file (local dev)
echo "DUCKDICE_API_KEY=your-key" > .env
duckdice run --strategy martingale

# Command line (least secure)
duckdice run --strategy martingale --api-key "your-key"
```

### Secrets in CI/CD
- Uses GitHub Secrets for sensitive data
- PyPI publishing via Trusted Publishing (OIDC, no tokens)
- No secrets committed to repository

---

## 📚 Further Reading

- **[Bet Validation](../BET_VALIDATION.md)** - How bets are validated
- **[API Fallback](../API_FALLBACK.md)** - Domain fallback logic
- **[Database Logging](../DATABASE_LOGGING.md)** - Bet history storage
- **[Strategy Development](./STRATEGY_DEVELOPMENT.md)** - Create custom strategies
- **[Development Guardrails](../../.github/DEVELOPMENT_GUARDRAILS.md)** - Repository rules

---

**Last Updated**: v4.11.2 (2026-02-03)
