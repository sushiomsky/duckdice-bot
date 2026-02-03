# 🎲 DuckDice Bot

**Professional automated betting toolkit for DuckDice.io**

[![Version](https://img.shields.io/badge/version-4.11.2-blue.svg)](https://github.com/sushiomsky/duckdice-bot/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/duckdice-betbot)](https://pypi.org/project/duckdice-betbot/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/sushiomsky/duckdice-bot)

Automate betting strategies, analyze results, and manage your gaming with a powerful CLI/TUI toolkit. Features 25 built-in strategies, DiceBot compatibility, and comprehensive risk management.

---

## ✨ Features

### 🎯 **25 Built-in Strategies**
From conservative (D'Alembert, Oscar's Grind) to aggressive (Martingale, Streak Hunter) to experimental (Adaptive Volatility Hunter, Micro Exponential)

### 🖥️ **Three Interfaces**
- **CLI** - Automation, scripting, headless servers
- **TUI** - Interactive terminal with live stats
- **API** - Python library for custom integrations

### 🛡️ **Safety Features**
- Multi-layer bet validation
- Automatic domain fallback (.io → .live → .net)
- Stop conditions (max bets, profit/loss targets, time limits)
- Comprehensive logging and audit trails

### 🔌 **DiceBot Compatible**
Import Lua strategies from original DiceBot - works without modification

### 📊 **Analysis Tools**
- SQLite bet history logging
- CSV export for analysis
- Strategy comparison tool
- Real-time statistics

---

## 🚀 Quick Start

### Option 1: Install from PyPI (Recommended)

```bash
# Install package
pip install duckdice-betbot

# Run CLI
duckdice --help
duckdice list-strategies

# Interactive mode (with TUI)
pip install duckdice-betbot[tui]
duckdice interactive
```

### Option 2: Download Executable

**No Python installation required!**

1. Go to [Releases](https://github.com/sushiomsky/duckdice-bot/releases/latest)
2. Download for your OS:
   - Windows: `duckdice-bot-windows-x64.zip`
   - macOS: `duckdice-bot-macos-universal.tar.gz`
   - Linux: `duckdice-bot-linux-x64.tar.gz`
3. Extract and run:
   ```bash
   # Windows
   duckdice.exe --help
   
   # macOS/Linux
   chmod +x duckdice
   ./duckdice --help
   ```

### Option 3: Install from Source

```bash
# Clone repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# Install dependencies
pip install -r requirements.txt

# Run
python duckdice_cli.py --help
```

---

## 📖 Your First Bet

### 1. Get Your API Key

1. Log in to [DuckDice.io](https://duckdice.io)
2. Go to Settings → API
3. Generate API key
4. Copy key

### 2. Set Environment Variable

```bash
# Linux/macOS
export DUCKDICE_API_KEY="your-api-key-here"

# Windows PowerShell
$env:DUCKDICE_API_KEY="your-api-key-here"

# Or create .env file
echo "DUCKDICE_API_KEY=your-api-key" > .env
```

### 3. Run a Strategy

```bash
# List available strategies
duckdice list-strategies

# Run classic martingale for 50 bets
duckdice run --strategy classic-martingale --bets 50

# Run with profit target
duckdice run --strategy dalembert --profit-target 0.5

# Run interactive mode (TUI)
duckdice interactive
```

---

## 🎯 Strategies Overview

**25 Strategies Organized by Risk Level:**

### 🟢 Conservative (Low Risk)
Perfect for beginners or risk-averse players
- **D'Alembert** - Balanced progression system
- **Oscar's Grind** - Patient profit-seeking  
- **One-Three-Two-Six** - Simple 4-step sequence

### 🟡 Moderate (Medium Risk)
Balanced risk/reward for most players
- **Simple Progression 40** - 40% chance with smart scaling
- **Kelly Capped** - Statistical optimization with safety caps
- **Fibonacci** - Classic mathematical sequence
- **Target Aware** - Goal-oriented state machine

### 🟠 Aggressive (High Risk)
For experienced players seeking bigger wins
- **Paroli** - Double on wins, limit losses
- **Anti-Martingale Streak** - Capitalize on hot streaks
- **Labouchère** - Cancellation system

### 🔴 High-Risk (Very High Risk)
High volatility - can win or lose big quickly
- **Classic Martingale** - Double on loss (requires large bankroll)
- **Streak Hunter** - Hunt 14% chance streaks with compounding
- **Adaptive Volatility Hunter** - Ultra-low chance lottery hunting (0.01%-1%)
- **Micro Exponential** - 300x growth target (EXTREME risk)
- **Progressive Win Scaling** - Aggressive win streak amplification

### 🟣 Specialized
Specific use cases
- **Faucet Grind** - Auto-claim and bet faucet
- **Max Wager Flow** - Maximize volume for VIP/bonuses
- **RNG Analysis** - Pattern detection (educational)
- **Custom Script** - Load your own Lua/Python strategies

**📊 [Complete Strategy Guide](docs/STRATEGIES/README.md)** - Detailed descriptions, parameters, and recommendations

---

## 💡 Common Use Cases

### Faucet Grinding
```bash
# Auto-claim faucet and grind it up
duckdice run --strategy faucet-grind --bets 1000
```

### Target-Based Betting
```bash
# Stop when reaching $5 profit
duckdice run --strategy target-aware --profit-target 5.0 --currency usdt
```

### Time-Limited Session
```bash
# Run for 30 minutes
duckdice run --strategy simple-progression-40 --duration 1800
```

### Custom Strategy
```bash
# Load your own strategy
duckdice run --strategy custom-script --script-path my_strategy.py
```

### Strategy Comparison
```bash
# Compare 3 strategies side-by-side
python scripts/compare_strategies.sh
```

---

## 🎨 Interactive Mode (TUI)

**Beautiful terminal interface with real-time updates:**

```bash
duckdice interactive
```

**Features:**
- 📊 Live bet visualization
- 📈 Real-time profit/loss graphs
- ⌨️ Keyboard shortcuts for quick actions
- 🎯 Strategy switching on-the-fly
- 📋 Detailed statistics panel

**Keyboard Shortcuts:**
- `Space` - Pause/Resume
- `q` - Quit safely
- `s` - Switch strategy
- `↑/↓` - Adjust bet amount
- `h` - Toggle high/low
- `?` - Show help

**📖 [TUI Guide](docs/INTERFACES/TUI_GUIDE.md)**

---

## 🔧 Advanced Configuration

### Custom Parameters

Most strategies accept parameters:

```bash
# Martingale with custom multiplier
duckdice run --strategy classic-martingale --param multiplier=2.5

# Labouchère with custom sequence
duckdice run --strategy labouchere --param sequence="1,2,3,4,5"

# Kelly with max fraction
duckdice run --strategy kelly-capped --param max_kelly_fraction=0.05
```

### Configuration File

Save settings to avoid typing them every time:

```json
{
  "strategy": "simple-progression-40",
  "currency": "btc",
  "max_bets": 100,
  "profit_target": 1.0,
  "stop_loss": -0.5,
  "parameters": {
    "base_bet_percent": 0.01
  }
}
```

```bash
duckdice run --config my-config.json
```

### Multiple Currencies

```bash
# Bitcoin
duckdice run --strategy martingale --currency btc

# Ethereum
duckdice run --strategy fibonacci --currency eth

# USDT (stable)
duckdice run --strategy dalembert --currency usdt
```

---

## 📊 Analyzing Results

### View Bet History

```bash
# Show last 50 bets
duckdice history --limit 50

# Filter by session
duckdice history --session abc123

# Export to CSV
duckdice export --output my_bets.csv
```

### Database Location

Bet history stored in SQLite:
```
data/duckdice_bot.db
```

### Query with SQL

```bash
sqlite3 data/duckdice_bot.db
```

```sql
-- Win rate by strategy
SELECT strategy, 
       COUNT(*) as bets,
       SUM(CASE WHEN win THEN 1 ELSE 0 END) as wins,
       ROUND(AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate
FROM bet_history
GROUP BY strategy;

-- Biggest wins
SELECT timestamp, strategy, bet_amount, profit
FROM bet_history
WHERE profit > 0
ORDER BY profit DESC
LIMIT 10;
```

**📖 [Database Guide](docs/DATABASE_LOGGING.md)**

---

## 🐍 Python API

Use as a library in your own scripts:

```python
from duckdice_api import DuckDiceAPI
from betbot_engine import BettingEngine

# Initialize API
api = DuckDiceAPI(api_key="your-key")

# Manual betting
result = api.place_bet(
    amount=0.01,
    chance=50.0,
    bet_high=True
)
print(f"Win: {result['win']}, Profit: {result['profit']}")

# Or use the engine
engine = BettingEngine(
    api=api,
    strategy="classic-martingale",
    max_bets=100
)

# Subscribe to events
def on_bet(event_data):
    print(f"Bet #{event_data['bet_number']}: {event_data['profit']}")

engine.event_bus.subscribe('bet_placed', on_bet)
engine.run()
```

**📖 [API Documentation](docs/API_REFERENCE.md)**

---

## 🛡️ Safety & Risk Management

### Built-in Safeguards

1. **Bet Validation** - Three-layer validation prevents invalid bets
2. **Balance Checks** - Never bet more than available
3. **Stop Conditions** - Auto-stop on profit/loss targets
4. **Domain Fallback** - Automatic retry across 3 domains
5. **Request Limits** - Respects API rate limits

### Stop Conditions

```bash
# Maximum bets
duckdice run --strategy martingale --bets 100

# Profit target (stop on reaching goal)
duckdice run --strategy fibonacci --profit-target 5.0

# Stop loss (limit losses)
duckdice run --strategy dalembert --stop-loss -2.0

# Time limit (seconds)
duckdice run --strategy paroli --duration 3600

# Multiple conditions (stop on first met)
duckdice run --strategy martingale \
  --bets 500 \
  --profit-target 10.0 \
  --stop-loss -5.0 \
  --duration 7200
```

### Responsible Gaming

⚠️ **Important Reminders:**

- 🎲 **House edge**: All games have ~1% house edge - long-term losses are mathematically guaranteed
- 💰 **Only bet what you can afford to lose** - Never bet money needed for essentials
- 🛑 **Set limits** - Use stop-loss and profit targets religiously
- 📊 **Track your gambling** - Review bet history regularly
- 🆘 **Seek help if needed** - Visit [BeGambleAware.org](https://www.begambleaware.org) or [GamblersAnonymous.org](https://www.gamblersanonymous.org)

---

## 📚 Documentation

### User Guides
- **[Getting Started](GETTING_STARTED.md)** - Complete beginner's guide
- **[CLI Guide](docs/INTERFACES/CLI_GUIDE.md)** - All CLI commands and options
- **[TUI Guide](docs/INTERFACES/TUI_GUIDE.md)** - Interactive mode walkthrough
- **[Quick Reference](QUICK_REFERENCE.md)** - Command cheat sheet

### Strategy Documentation
- **[All Strategies](docs/STRATEGIES/README.md)** - Complete strategy catalog
- **[Strategy Comparison](docs/STRATEGIES/COMPARISON.md)** - Side-by-side analysis
- **[Adaptive Volatility Hunter](docs/STRATEGIES/ADAPTIVE_VOLATILITY_HUNTER_GUIDE.md)**
- **[Streak Hunter](docs/STRATEGIES/STREAK_HUNTER.md)**

### Technical Documentation
- **[Architecture](docs/ARCHITECTURE/README.md)** - System design and components
- **[API Reference](docs/API_REFERENCE.md)** - Python API documentation
- **[Bet Validation](docs/BET_VALIDATION.md)** - How bets are validated
- **[Database](docs/DATABASE_LOGGING.md)** - Bet history and logging

### Developer Guides
- **[Contributing](CONTRIBUTING.md)** - How to contribute
- **[Development Guardrails](.github/DEVELOPMENT_GUARDRAILS.md)** - Repository rules
- **[Build Guide](docs/BUILD.md)** - Building from source

---

## 🛠️ Development

### Requirements

- Python 3.9+
- pip or poetry

### Setup Development Environment

```bash
# Clone repo
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Run tests
pytest tests/ -v

# Run linter
flake8 src/ tests/
```

### Creating Custom Strategies

```python
# my_strategy.py
class MyStrategy:
    def __init__(self, initial_balance):
        self.balance = initial_balance
        self.basebet = initial_balance * 0.01
    
    def get_initial_bet(self):
        return self.basebet
    
    def get_initial_chance(self):
        return 50.0
    
    def dobet(self):
        """Called after each bet"""
        global balance, nextbet, chance, win
        
        if win:
            nextbet = self.basebet  # Reset on win
        else:
            nextbet = nextbet * 2   # Double on loss
        
        # Ensure we don't exceed balance
        if nextbet > balance:
            nextbet = balance
```

```bash
# Run your strategy
duckdice run --strategy custom-script --script-path my_strategy.py
```

**📖 [Strategy Development Guide](docs/ARCHITECTURE/STRATEGY_DEVELOPMENT.md)**

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

### Ways to Contribute

- 🐛 Report bugs via [Issues](https://github.com/sushiomsky/duckdice-bot/issues)
- 💡 Suggest features
- 📝 Improve documentation
- 🎯 Add new strategies
- 🧪 Write tests
- 🔧 Fix bugs

### Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes
4. Run tests (`pytest tests/`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open Pull Request

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

**TL;DR**: Free to use, modify, and distribute. Attribution appreciated but not required.

---

## 🔗 Links

- **GitHub**: [github.com/sushiomsky/duckdice-bot](https://github.com/sushiomsky/duckdice-bot)
- **PyPI**: [pypi.org/project/duckdice-betbot](https://pypi.org/project/duckdice-betbot/)
- **DuckDice.io**: [duckdice.io](https://duckdice.io)
- **Issues**: [github.com/sushiomsky/duckdice-bot/issues](https://github.com/sushiomsky/duckdice-bot/issues)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## ⭐ Star History

If you find this project useful, consider giving it a star on GitHub!

---

## 💬 Support

- **Documentation**: [Full docs](docs/)
- **Issues**: [GitHub Issues](https://github.com/sushiomsky/duckdice-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sushiomsky/duckdice-bot/discussions)

---

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

**Current Version**: 4.11.2

**Recent Updates**:
- ✅ Fixed PyInstaller executable builds
- ✅ PyPI Trusted Publishing setup
- ✅ Adaptive Volatility Hunter emergency brake fix
- ✅ Python 3.9-3.12 compatibility
- ✅ CI/CD automation improvements

---

## ⚖️ Disclaimer

This software is provided "as-is" without warranty of any kind. Gambling involves risk of financial loss. The authors are not responsible for any losses incurred through use of this software. 

**Gamble responsibly. Only bet what you can afford to lose.**

---

**Made with ❤️ by the DuckDice Bot community**

**Version**: 4.11.2 | **Last Updated**: 2026-02-03
