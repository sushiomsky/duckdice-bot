# 🏗️ DuckDice Bot Architecture

**Version**: 4.9.2  
**Last Updated**: January 16, 2026

---

## 📐 System Overview

DuckDice Bot is a modular, CLI/TUI-first betting automation toolkit built with Python. The architecture emphasizes separation of concerns, testability, and extensibility.

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   CLI    │  │ TUI-Textual  │  │ TUI-NCurses  │          │
│  │ (Primary)│  │   (Modern)   │  │  (Classic)   │          │
│  └────┬─────┘  └──────┬───────┘  └──────┬───────┘          │
└───────┼────────────────┼──────────────────┼─────────────────┘
        │                │                  │
        └────────────────┴──────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │      Betting Engine Core         │
        │  ┌────────────────────────────┐  │
        │  │  Session Management        │  │
        │  │  Strategy Execution        │  │
        │  │  Risk Controls             │  │
        │  │  Analytics Engine          │  │
        │  └────────────────────────────┘  │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │    Strategy System (22)          │
        │  ┌────────────────────────────┐  │
        │  │  Conservative (3)          │  │
        │  │  Moderate (4)              │  │
        │  │  Aggressive (3)            │  │
        │  │  Specialized (10)          │  │
        │  │  Custom Scripts (2)        │  │
        │  └────────────────────────────┘  │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │      DuckDice API Client         │
        │  ┌────────────────────────────┐  │
        │  │  Connection Pool           │  │
        │  │  Request/Response Models   │  │
        │  │  Error Handling            │  │
        │  │  Rate Limiting             │  │
        │  └────────────────────────────┘  │
        └────────────────┬────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │     Persistence Layer            │
        │  ┌────────────────────────────┐  │
        │  │  SQLite Database           │  │
        │  │  - Bet History             │  │
        │  │  - Session Data            │  │
        │  │  - User Profiles           │  │
        │  │  - Analytics Cache         │  │
        │  └────────────────────────────┘  │
        └──────────────────────────────────┘
```

---

## 🎯 Core Components

### 1. User Interfaces

#### CLI Interface (`duckdice_cli.py`)
**Purpose**: Primary command-line interface for automation and scripting

**Key Features**:
- Interactive mode with guided configuration
- Argument-based batch execution
- Rich terminal output with colors and formatting
- Profile management
- Real-time statistics display

**Entry Points**:
```python
def main():
    """Main entry point with argument parsing"""
    
def interactive_mode():
    """Guided configuration workflow"""
    
def run_betting_session(config):
    """Execute betting with selected strategy"""
```

#### TUI Interfaces (`src/interfaces/tui/`)
**Purpose**: Visual terminal interfaces for monitoring and control

**Textual Interface** (`textual_interface.py`):
- Modern, rich terminal UI using Textual library
- Real-time dashboard with live updates
- Interactive bet history table
- Mouse and keyboard support
- Progress indicators and charts

**NCurses Interface** (`ncurses_interface.py`):
- Classic terminal UI using Python's curses module
- Lightweight with no external dependencies
- Keyboard-only navigation
- Minimal resource usage
- Works over SSH

---

### 2. Betting Engine (`src/betbot_engine/`)

#### Engine Core (`engine.py`)
**Purpose**: Main betting logic and execution control

**Responsibilities**:
- Execute betting strategies
- Apply risk controls (stop-loss, take-profit)
- Manage bet execution flow
- Handle errors and retries
- Coordinate with API client

**Key Methods**:
```python
class BettingEngine:
    def execute_bet(self, amount, chance, direction):
        """Execute a single bet"""
        
    def run_session(self, strategy, config):
        """Run a complete betting session"""
        
    def apply_risk_controls(self, session_state):
        """Check and apply risk limits"""
```

#### Session Management (`session.py`)
**Purpose**: Track and manage betting sessions

**Responsibilities**:
- Session state tracking
- Bet history recording
- Statistics calculation
- Session persistence
- Recovery from interruptions

#### Analytics Engine (`analytics.py`)
**Purpose**: Performance metrics and reporting

**Metrics Calculated**:
- Win rate, profit/loss, ROI
- Max win/loss streaks
- Average bet size
- Profit factor
- Expected value
- Risk metrics (drawdown, variance)

---

### 3. Strategy System (`src/betbot_strategies/`)

#### Base Strategy (`base.py`)
**Purpose**: Abstract base class for all strategies

```python
class BaseStrategy(ABC):
    @abstractmethod
    def calculate_next_bet(self, last_bet, won, balance):
        """Calculate next bet amount based on outcome"""
        
    def on_win(self, bet_amount, profit):
        """Handle win event"""
        
    def on_loss(self, bet_amount):
        """Handle loss event"""
        
    def reset(self):
        """Reset strategy state"""
```

#### Strategy Categories

**Conservative (3 strategies)**:
- D'Alembert: Gradual progression
- Oscar's Grind: Small consistent profits
- 1-3-2-6: Fixed sequence

**Moderate (4 strategies)**:
- Fibonacci: Fibonacci sequence progression
- Labouchere: Cancellation system
- Paroli: Reverse martingale with limits
- Fib Loss Cluster: Fibonacci on loss streaks

**Aggressive (3 strategies)**:
- Classic Martingale: Double on loss
- Anti-Martingale Streak: Multiply on wins
- Streak Hunter: Win streak amplifier

**Specialized (10 strategies)**:
- Faucet Grind: Optimized for faucet betting
- Faucet Cashout: USD-targeted staged growth
- Kelly Capped: Kelly criterion with safety caps
- Target Aware: State machine with profit targets
- RNG Analysis: Pattern detection (educational)
- Range50 Random: Range dice at 50% chance
- Max Wager Flow: Maximize wagering throughput
- Micro Exponential: Exponential growth with micro bets
- Micro Exponential Safe: Safe variant with caps
- Custom Script: User-defined Python strategies

---

### 4. API Client (`src/duckdice_api/`)

#### API Client (`api.py`)
**Purpose**: Interface with DuckDice Bot API

**Features**:
- Connection pooling for performance
- Automatic retry with exponential backoff
- Rate limiting compliance
- Request/response validation
- Error handling and logging

**Key Methods**:
```python
class DuckDiceAPI:
    def bet(self, amount, chance, direction, currency):
        """Place a bet"""
        
    def get_balance(self, currency):
        """Get current balance"""
        
    def claim_faucet(self):
        """Claim faucet reward"""
        
    def get_user_info(self):
        """Get user account information"""
```

#### Data Models (`models.py`)
**Purpose**: Type-safe data structures

```python
@dataclass
class BetResult:
    bet_id: str
    amount: Decimal
    chance: Decimal
    roll: Decimal
    won: bool
    profit: Decimal
    balance: Decimal
    currency: str
    timestamp: datetime
```

---

### 5. Persistence Layer

#### Database Schema (SQLite)

**Tables**:

```sql
-- Bet history
CREATE TABLE bet_history (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    bet_id TEXT,
    timestamp DATETIME,
    amount REAL,
    chance REAL,
    roll REAL,
    won BOOLEAN,
    profit REAL,
    balance REAL,
    currency TEXT,
    strategy TEXT
);

-- Sessions
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    started_at DATETIME,
    ended_at DATETIME,
    strategy TEXT,
    currency TEXT,
    initial_balance REAL,
    final_balance REAL,
    total_bets INTEGER,
    total_wins INTEGER,
    total_losses INTEGER,
    profit REAL
);

-- User profiles
CREATE TABLE profiles (
    profile_name TEXT PRIMARY KEY,
    strategy TEXT,
    currency TEXT,
    config JSON,
    created_at DATETIME,
    updated_at DATETIME
);
```

---

## 🔄 Data Flow

### Betting Flow

```
1. User Input (CLI/TUI)
   ↓
2. Configuration Validation
   ↓
3. Strategy Initialization
   ↓
4. Session Start
   ↓
5. Loop:
   a. Strategy calculates next bet
   b. Risk controls check
   c. API executes bet
   d. Result processing
   e. Statistics update
   f. Database logging
   g. UI update
   ↓
6. Session End (limit reached or user stop)
   ↓
7. Final statistics and report
```

### Configuration Flow

```
1. Load defaults from config.json
   ↓
2. Override with CLI arguments
   ↓
3. Override with interactive input
   ↓
4. Validate configuration
   ↓
5. Save to profile (optional)
   ↓
6. Execute betting session
```

---

## 🔌 Extension Points

### Adding a New Strategy

1. Create new file in `src/betbot_strategies/`
2. Inherit from `BaseStrategy`
3. Implement required methods
4. Register in `__init__.py`
5. Add tests in `tests/`

Example:
```python
from .base import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, **params):
        super().__init__()
        self.param = params.get('param', default_value)
        
    def calculate_next_bet(self, last_bet, won, balance):
        # Your logic here
        return next_bet_amount
```

### Adding a New Interface

1. Create new directory in `src/interfaces/`
2. Implement interface using core engine
3. Add entry point in main launcher
4. Update documentation

---

## 🛡️ Security Considerations

### API Key Management
- Never hardcode API keys
- Use environment variables or config files
- Config files in `.gitignore`
- Secure file permissions (0600)

### Custom Script Execution
- Sandboxed execution environment
- Restricted imports (no os, sys, subprocess)
- Timeout protection
- Exception isolation

### Database Security
- Local SQLite database
- No remote access
- Regular backups recommended
- Sensitive data encryption (future)

---

## ⚡ Performance Optimizations

### API Client
- Connection pooling (reuse connections)
- Request batching where possible
- Exponential backoff for retries
- Caching for static data

### Database
- Indexed columns for fast queries
- Batch inserts for bet history
- Periodic VACUUM for optimization
- In-memory caching for sessions

### TUI Rendering
- Debounced updates (max 10 Hz)
- Partial screen updates
- Async rendering
- Efficient data structures

---

## 🧪 Testing Strategy

### Unit Tests
- Strategy logic validation
- API client mocking
- Database operations
- Configuration parsing

### Integration Tests
- End-to-end betting flow
- Database persistence
- Error handling
- Recovery scenarios

### Performance Tests
- Bet execution speed
- Database query performance
- Memory usage
- TUI rendering speed

---

## 📦 Deployment

### Local Installation
```bash
pip install duckdice-betbot
```

### From Source
```bash
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot
pip install -e .
```

### Docker (Future)
```bash
docker run -it duckdice-bot
```

---

## 🔮 Future Architecture Considerations

### Microservices (v6.0+)
- Separate API gateway
- Strategy execution service
- Analytics service
- Web dashboard service

### Message Queue (v6.0+)
- Async bet execution
- Event-driven architecture
- Distributed processing

### Cloud Deployment (v6.0+)
- Serverless functions
- Managed databases
- Auto-scaling

---

## 📚 Related Documentation

- [Project Structure](PROJECT_STRUCTURE.md) - File organization
- [Roadmap](ROADMAP.md) - Future plans
- [Contributing](../CONTRIBUTING.md) - Development guidelines
- [API Reference](API_REFERENCE.md) - API documentation

---

**Last Updated**: January 16, 2026  
**Version**: 4.9.2  
**Maintainer**: DuckDice Bot Team
