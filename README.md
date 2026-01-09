# 🎲 DuckDice Bot - Ultimate Edition

**The most advanced automation toolkit for DuckDice.io**

A comprehensive toolkit with both GUI and web interface for the [DuckDice Bot API](https://duckdice.io/bot-api). Automate betting strategies, analyze patterns, and manage your gaming responsibly with beautiful, modern interfaces.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/sushiomsky/duckdice-bot)
[![Release](https://img.shields.io/github/v/release/sushiomsky/duckdice-bot)](https://github.com/sushiomsky/duckdice-bot/releases/latest)

## 🚀 Quick Start

### Option 1: Download Pre-built Packages (Easiest)

Download the latest release for your platform:
- **Windows**: [DuckDiceBot-Windows-x64.zip](https://github.com/sushiomsky/duckdice-bot/releases/latest)
- **macOS**: [DuckDiceBot-macOS-universal.zip](https://github.com/sushiomsky/duckdice-bot/releases/latest)
- **Linux**: [DuckDiceBot-Linux-x64.tar.gz](https://github.com/sushiomsky/duckdice-bot/releases/latest)

Extract and run `DuckDiceBot` (or `DuckDiceBot.exe` on Windows).

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python duckdice_gui_ultimate.py

# Or run the web interface
./run_nicegui.sh  # On Windows: python app/main.py
```

Get your API key from [DuckDice](https://duckdice.io) → Account Settings → Bot API

## ✨ Features

### 🎮 Two Powerful Interfaces

#### Desktop GUI (Tkinter)
- **Native Desktop App**: Full-featured traditional GUI
- **16 Enhanced Strategies**: Martingale, Fibonacci, D'Alembert, and more
- **Real-time Statistics**: Live dashboard with multi-period analytics
- **Offline Simulator**: Test strategies without risking funds
- **Database Logging**: Persistent bet history with JSONL format

#### Web Interface (NiceGUI)
- **Modern Web UI**: Access from any device on your network
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Real-time Updates**: Live betting status and statistics
- **Dark/Light Themes**: Beautiful, customizable interface

### 🎯 Core Features

#### Betting Strategies
- **16 Pre-built Strategies**: From conservative to aggressive
  - Martingale, Anti-Martingale, Fibonacci, Labouchere
  - D'Alembert, Paroli, Oscar's Grind, 1-3-2-6
  - Kelly Criterion, Flat Betting, and more
- **Custom Scripts**: Create your own with built-in editor
- **Strategy Templates**: Professional starting points
- **Turbo Mode**: 15-25x faster betting (0ms delays)

#### Analytics & Verification
- **📊 Statistics Dashboard**: Multi-period analysis (24h, 7d, 30d, 90d, all-time)
- **📈 Win/Loss Tracking**: Visual progress, streak analysis
- **🔐 Provably Fair Verification**: Verify any bet's fairness
- **📤 Export Functions**: CSV export for external analysis
- **🎲 RNG Analysis**: Visual pattern detection tools

#### Smart Features
- **🚰 Faucet Grind**: Auto-claim and grind to cashout
- **💰 Profit Targets**: Auto-stop at win/loss thresholds
- **🔄 Session Management**: Save/load betting sessions
- **⌨️ Keyboard Shortcuts**: Quick access to all features
- **🌍 Multi-Currency**: Support for all DuckDice currencies

### 🛡️ Safety Features

- **Offline Simulator**: Test without real bets
- **Balance Protection**: Configurable limits
- **Emergency Stop**: Instant betting halt (Ctrl+C)
- **Sandboxed Scripts**: Safe execution environment
- **Audit Logging**: Complete bet history

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

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

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
