# 🎲 DuckDice Bot - Command Line Edition

**Professional automated betting toolkit for DuckDice.io**

A comprehensive command-line toolkit for the [DuckDice Bot API](https://duckdice.io/bot-api). Automate betting strategies, test in simulation mode, and manage your gaming responsibly with a powerful CLI interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/sushiomsky/duckdice-bot)

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# Install dependencies
pip install -r requirements.txt

# Make CLI executable (Unix/macOS)
chmod +x duckdice_cli.py
```

### Your First Run - Simulation Mode

```bash
# Test a strategy risk-free in simulation mode
python3 duckdice_cli.py run \
  --mode simulation \
  --strategy classic-martingale \
  --currency btc \
  --max-bets 100
```

### Live Betting (Get API Key from DuckDice)

```bash
# Bet with main balance
python3 duckdice_cli.py run \
  --mode live-main \
  --strategy fibonacci \
  --currency btc \
  --api-key YOUR_API_KEY \
  --max-bets 50

# Bet with faucet balance
python3 duckdice_cli.py run \
  --mode live-faucet \
  --strategy faucet-grind \
  --currency doge \
  --api-key YOUR_API_KEY
```

Get your API key from [DuckDice](https://duckdice.io) → Account Settings → Bot API

## ✨ Features

### 🎯 Core Capabilities

- **22 Built-in Strategies** - From conservative to aggressive
- **Beautiful Terminal UI** - CLI with colors, TUI with Textual/NCurses ⭐
- **Simulation Mode** - Test risk-free with virtual balance
- **Live Betting** - Real betting with main or faucet balance
- **Interactive Mode** - Guided setup, zero configuration needed
- **Profile Management** - Save and reuse configurations
- **Risk Controls** - Stop-loss, take-profit, max bets/losses
- **Session History** - SQLite database tracks all bets
- **Real-time Stats** - Live progress tracking and statistics
- **Analytics Dashboard** - Comprehensive performance metrics

### 🎮 Three User Interfaces

1. **CLI** - Command-line interface for automation and scripting
2. **TUI (Textual)** - Modern terminal UI with rich visuals
3. **TUI (NCurses)** - Classic terminal UI, lightweight

### 🎲 Three Betting Modes

1. **Simulation** - Test strategies with virtual balance (default)
2. **Live Main** - Bet with your main balance
3. **Live Faucet** - Bet with faucet balance (perfect for testing)

### 🎲 Available Strategies (22 Total)

#### Conservative (Low Risk)
- **dalembert** - Increase/decrease bets gradually
- **oscars-grind** - Target small consistent profits
- **one-three-two-six** - Fixed sequence, controlled risk

#### Moderate Risk
- **fibonacci** - Follow Fibonacci sequence
- **labouchere** - Cancellation system
- **paroli** - Reverse martingale with limits
- **fib-loss-cluster** - Fibonacci on loss streaks

#### Aggressive (High Risk)
- **classic-martingale** - Double on loss (⚠️ requires large bankroll)
- **anti-martingale-streak** - Multiply on wins
- **streak-hunter** - Win streak amplifier

#### Specialized
- **faucet-grind** - Optimized for faucet betting
- **faucet-cashout** - USD-targeted staged growth
- **kelly-capped** - Kelly criterion with safety caps
- **target-aware** - State machine with profit targets
- **range50-random** - Range dice at 50% chance
- **max-wager-flow** - Maximize wagering throughput
- **micro-exponential** - Exponential growth with micro bets ⭐ NEW
- **micro-exponential-safe** - Safe variant with caps ⭐ NEW
- **rng-analysis-strategy** - RNG pattern analysis (educational)
- **custom-script** - Load your own Python strategy

## 📖 Documentation

- **[CLI Guide](CLI_GUIDE.md)** - Complete command reference and examples
- **[TUI Guide](TUI_GUIDE.md)** - Terminal UI interfaces (Textual/NCurses)
- **[User Guide](USER_GUIDE.md)** - Strategy details and best practices
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment tips
- **[Architecture](docs/ARCHITECTURE.md)** - Technical architecture overview
- **[Roadmap](docs/ROADMAP.md)** - Future development plans

## 🎯 Command Overview

### List Available Strategies

```bash
python3 duckdice_cli.py strategies
```

### Run a Strategy

```bash
# Interactive mode (prompts for all options)
python3 duckdice_cli.py run

# With arguments
python3 duckdice_cli.py run \
  --mode simulation \
  --strategy dalembert \
  --currency btc \
  --max-bets 100 \
  --stop-loss -0.2 \
  --take-profit 0.5
```

### Save Strategy Profile

```bash
# Interactive configuration
python3 duckdice_cli.py save-profile my-strategy --strategy fibonacci

# Use saved profile
python3 duckdice_cli.py run --profile my-strategy --mode simulation
```

### List Saved Profiles

```bash
python3 duckdice_cli.py profiles
```

### Configure Defaults

```bash
# View configuration
python3 duckdice_cli.py config

# Set default values
python3 duckdice_cli.py config --set default_currency=doge
python3 duckdice_cli.py config --set api_key=YOUR_KEY
```

## 🛡️ Risk Management

### Built-in Safety Controls

```bash
# Stop at -20% loss
--stop-loss -0.2

# Stop at +50% profit
--take-profit 0.5

# Limit total bets
--max-bets 100

# Stop after N losses in a row
--max-losses 5

# Time limit (seconds)
--max-duration 3600
```

### Example: Conservative Betting

```bash
python3 duckdice_cli.py run \
  --mode simulation \
  --strategy dalembert \
  --currency btc \
  --max-bets 500 \
  --stop-loss -0.1 \
  --take-profit 0.2 \
  --max-losses 3
```

## 📊 Session History

All bets are saved to `~/.duckdice/history.db` (SQLite database)

### Query Your Data

```bash
sqlite3 ~/.duckdice/history.db

# Recent sessions
SELECT session_id, strategy, profit 
FROM sessions 
ORDER BY started_at DESC 
LIMIT 10;

# Win rate by strategy
SELECT strategy, 
       CAST(SUM(won) AS FLOAT) / COUNT(*) * 100 as win_rate
FROM bet_history 
GROUP BY strategy;
```

## 🔧 Advanced Usage

### Batch Testing

```bash
# Test multiple strategies
for strategy in dalembert fibonacci oscars-grind; do
  python3 duckdice_cli.py run \
    -m simulation \
    -s $strategy \
    --max-bets 100
done
```

### Custom Strategy

Create your own strategy script and use it:

```bash
python3 duckdice_cli.py run \
  --strategy custom-script \
  --mode simulation
```

## ⚠️ Safety Tips

**IMPORTANT**: Always test in simulation mode first!

1. ✅ Start with simulation mode
2. ✅ Use faucet balance before main balance
3. ✅ Set stop-loss and take-profit limits
4. ✅ Start with tiny bet amounts
5. ✅ Monitor sessions carefully
6. ⚠️ Martingale strategies are extremely risky
7. ⚠️ No strategy guarantees profit
8. ⚠️ Only bet what you can afford to lose

## 🛠️ Development

### Project Structure

```
duckdice-bot/
├── duckdice_cli.py          # Main CLI entry point
├── src/
│   ├── betbot_strategies/   # 17 betting strategies
│   ├── betbot_engine/       # Core betting engine
│   ├── duckdice_api/        # API client
│   └── simulation_engine.py # Offline simulator
├── tests/                   # Test suite
└── docs/                    # Documentation
```

### Run Tests

```bash
python3 -m pytest tests/
```

## 📝 Configuration Files

All stored in `~/.duckdice/`:

- `config.json` - Default settings (API key, currency, mode)
- `profiles.json` - Saved strategy profiles  
- `history.db` - SQLite database with all bets

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## ⚡ Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history

## 🙏 Acknowledgments

- DuckDice.io for providing the Bot API
- Community contributors and testers

---

**Disclaimer**: Gambling involves risk. This tool is for educational and entertainment purposes. Always gamble responsibly and within your means. The developers are not responsible for any losses incurred while using this software.

## 📚 Documentation

- [Quick Start Guide](QUICK_START_GUIDE.md) - Get up and running in 5 minutes
- [Complete Features](COMPLETE_FEATURES.md) - Full feature documentation
- [Windows Build Guide](WINDOWS_BUILD.md) - Building on Windows
- [Install Guide](INSTALL.md) - Detailed installation instructions
- [Release Checklist](RELEASE_CHECKLIST.md) - For developers
- [Changelog](CHANGELOG.md) - Version history

### Strategy Guides
- [Enhanced Strategy Documentation](docs/ENHANCED_STRATEGY_INFO.md)
- [Custom Script Guide](docs/CUSTOM_SCRIPTS.md)
- [API Reference](docs/API_REFERENCE.md)

## 🔧 Advanced Usage

### Custom Strategies

Create your own betting strategies with the built-in editor:

```python
# Example custom strategy
def calculate_next_bet(last_bet, won, balance):
    if won:
        return last_bet * 0.5  # Reduce on win
    else:
        return last_bet * 2.0  # Double on loss
```

Features:
- Monaco editor with syntax highlighting
- Real-time validation
- Template library
- Version history (auto-save last 10 versions)
- One-click formatting

### API Integration

```python
from duckdice import DuckDiceAPI

api = DuckDiceAPI("your-api-key")
result = api.bet(amount=0.00001, target=50.5, currency="btc")
print(f"Result: {result.profit} {result.currency}")
```

## 🏗️ Building from Source

### Requirements
- Python 3.9 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Build Executable

```bash
# Install build dependencies
pip install -r requirements-build.txt

# Build for your platform
./build_release.sh  # Linux/macOS
build_windows.bat   # Windows

# Output in dist/ directory
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_strategies.py
```

## 📚 Documentation

### User Documentation
- **[Getting Started](GETTING_STARTED.md)** - Quick start guide for all interfaces
- **[User Guide](USER_GUIDE.md)** - Complete user guide
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment instructions

### Developer Documentation
- **[Tkinter GUI Enhancements](docs/tkinter/)** - Desktop GUI new features
- **[NiceGUI Documentation](docs/GUI_README.md)** - Web interface documentation
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Codebase organization
- **[Roadmap](docs/ROADMAP.md)** - Future plans and features

### Build & Release
- **[Windows Build](WINDOWS_BUILD.md)** - Building for Windows
- **[Release Checklist](RELEASE_CHECKLIST.md)** - Release process

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for detailed guidelines.

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/duckdice-bot.git
cd duckdice-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Run tests
python -m pytest
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for educational and entertainment purposes only. Gambling involves risk, and you should never bet more than you can afford to lose. The authors are not responsible for any financial losses incurred through the use of this software.

**Please gamble responsibly.**

## 🔗 Links

- **DuckDice**: https://duckdice.io
- **Bot API Documentation**: https://duckdice.io/bot-api
- **GitHub Repository**: https://github.com/sushiomsky/duckdice-bot
- **Latest Release**: https://github.com/sushiomsky/duckdice-bot/releases/latest
- **Issue Tracker**: https://github.com/sushiomsky/duckdice-bot/issues

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

## 💬 Support

- **Issues**: Report bugs via [GitHub Issues](https://github.com/sushiomsky/duckdice-bot/issues)
- **Discussions**: Join the conversation in [Discussions](https://github.com/sushiomsky/duckdice-bot/discussions)

---

Made with ❤️ by the DuckDice Bot community
