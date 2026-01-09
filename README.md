# 🎲 DuckDice Bot - Ultimate Edition

**The most advanced, user-friendly automation toolkit for DuckDice.io**

A comprehensive command-line interface and GUI for the [DuckDice Bot API](https://duckdice.io/bot-api). Play games, analyze patterns, and automate betting strategies responsibly with a **beautiful, modern interface**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/sushiomsky/duckdice-bot)

## ✨ What's New in v3.9

🎉 **Major Performance & Analytics Update!**

### New in v3.9.0 - Statistics & Turbo Mode
- 📊 **Comprehensive Statistics Dashboard**: Multi-period analytics (24h, 7d, 30d, 90d, all-time)
- 📈 **Win/Loss Analysis**: Visual progress bars, currency breakdown, streak tracking
- 💾 **Persistent Bet History**: Auto-saved to disk with JSONL format
- 🔍 **Advanced Filtering**: Date ranges, currency, amount, win/loss filtering
- 📄 **CSV Export Ready**: Export statistics for external analysis
- ⚡ **Turbo Mode**: Maximum betting speed (15-25x faster, 0ms delays)
- 🚀 **Connection Pooling**: HTTP keep-alive for reduced latency
- 🌍 **All Currencies**: Automatic support for all DuckDice currencies
- ⌨️ **Keyboard Shortcut**: Ctrl+7 for instant statistics access

### Previous in v3.5.0 - Bet Verification System
- 🔐 **Provably Fair Verification**: Verify any bet's fairness with SHA-256 cryptographic proof
- 📊 **Step-by-Step Breakdown**: See exactly how each roll is calculated (educational!)
- ✅ **Instant Verification**: Click "Verify" on any bet in history to check fairness
- 📤 **Export Reports**: Download verification reports for audit trails
- 🎯 **100% Accurate**: Exact DuckDice algorithm implementation

### New in v3.4.0 - Unified Script System
- 📝 **Custom Strategy Editor**: Create your own betting strategies with VSCode-quality Monaco editor
- 🎨 **Real-time Validation**: Instant error detection as you type
- 🔒 **100% Safe**: RestrictedPython sandbox blocks all dangerous operations
- 📚 **Professional Templates**: 4 ready-to-use strategy templates (Martingale, Anti-Martingale, Fixed %, Target Profit)
- 🔄 **Version History**: Auto-save with rollback to any of last 10 versions
- 🧪 **Test Mode**: Test scripts with sample data before deploying
- 🎯 **One-Click Format**: Black code formatter integration

### New in v3.3.0 - Faucet Grind
- 🚰 **Faucet Grind Strategy**: Auto-claim faucet and grind to $20 cashout
- 💰 **Smart Betting**: Optimal chance calculation for maximum efficiency
- 📈 **Progress Tracking**: Live progress bar to $20 target
- 🔄 **Auto Recovery**: Loss recovery with next claim cycle

Previous Updates (v3.2):
- 🔄 Auto-Update System with GitHub integration
- 🎨 Modern UI/UX with clear mode indicators
- 💱 Dynamic Currency Fetching
- 🚰 Enhanced Faucet Mode

## 🚀 Quick Start

**New users:** See [QUICKSTART.md](QUICKSTART.md) to get running in 2 minutes.

**Download:** Pre-built executables available on [Releases](../../releases) page (Windows `.exe`, macOS `.app`, Linux binary)

### Web Interface (NiceGUI) - NEW! 🌟

Run the modern web interface for remote access and mobile support:

```bash
./run_nicegui.sh
# Opens at http://localhost:8080
```

**Features:**
- 🌐 Access from any device on your network
- 📱 Mobile-responsive design
- 🎨 Modern dark-mode interface
- ⚡ Real-time updates and animations
- ⌨️ Keyboard shortcuts (Ctrl+B, Ctrl+A, Ctrl+F, etc.)

See [NICEGUI_README.md](NICEGUI_README.md) for full documentation.

## 🌟 Key Features

### 🌐 NiceGUI Web Interface (v1.0+)

**Modern Web Application:**
- 🌐 **Remote Access**: Use from any device on your network
- 📱 **Mobile Responsive**: Full functionality on phones/tablets
- 🎨 **Premium UX**: Smooth animations, dark mode, modern design
- ⚡ **Real-time Updates**: Live balance refresh every 30 seconds
- ⌨️ **Keyboard Shortcuts**: Fast navigation (Ctrl+B, Ctrl+A, etc.)

**10+ Complete Pages:**
- 📊 Dashboard - Live statistics and performance overview
- 🎲 Betting - Manual and automated betting (consolidated)
- 🚰 Faucet - Auto-claim with progress tracking
- 📚 Library - Strategies and custom scripts (consolidated)
- 🛠️ Tools - Simulator, RNG Analysis, Verification (consolidated)
- 📜 History - Complete bet history with filtering
- 📊 Statistics - Comprehensive analytics dashboard (NEW in v3.9!)
- ⚙️ Settings - API connection and preferences
- 🤖 Auto Bet - Strategy automation with 17 strategies
- 🚰 Faucet - Auto-claim with Faucet Grind strategy
- 📚 Strategies - Browse and learn about all strategies
- 💻 **Scripts** - Create/edit custom strategies with Monaco editor (NEW!)
- 📈 History - Bet history with CSV export and verification (NEW!)
- ⚙️ Settings - API configuration and preferences
- ❓ Help/About - Keyboard shortcuts and documentation

### 🔐 Provably Fair Verification (NEW in v3.5!)

**Transparency & Trust:**
- ✅ **Verify Any Bet**: Click verify on any bet to check fairness
- 🔍 **Step-by-Step**: See exactly how SHA-256 produces each roll
- 📊 **Educational**: Learn how provably fair gambling works
- 📤 **Export Reports**: Download verification for your records
- 🎯 **100% Accurate**: Matches DuckDice's algorithm exactly
- ⚡ **Instant**: <1ms verification speed

### 📝 Custom Strategy Editor (NEW in v3.4!)

**Professional Code Editor:**
- 🎨 **Monaco Editor**: VSCode-quality editing experience
- ⚡ **Real-time Validation**: Instant error detection and warnings
- 🔒 **100% Safe**: RestrictedPython blocks dangerous operations
- 🎯 **One-Click Format**: Black code formatter integration
- 📚 **4 Templates**: Professional starter strategies included
- 🔄 **Version History**: Rollback to any of last 10 versions
- 🧪 **Test Mode**: Test scripts safely before deploying
- 💡 **Help System**: Built-in documentation and examples

**Features:**
- Search and filter all scripts
- Duplicate templates to customize
- Export/import scripts as .py files
- Syntax highlighting for Python
- Error messages with line numbers

### 🖥️ DuckDice GUI Ultimate (Tkinter)

**Professional Interface:**
- ✨ **Modern UI** with dark/light theme support
- 🟢 **Clear Mode Indicators**: Impossible to confuse Simulation vs Live betting
- 🔄 **Auto-Update**: Checks for new versions and installs with one click
- 📊 **Live Dashboard**: Real-time balance, profit, win rate, and streak tracking
- 💱 **Dynamic Currencies**: Auto-loads your available currencies from DuckDice API
- 🚰 **Faucet Mode**: Auto-claim with 60s cooldown, separate balance tracking
- 🔔 **Smart Notifications**: Toast popups for all important events

**Betting & Automation:**
- 🎲 Visual betting controls (Dice, Range Dice)
- 🤖 Automated betting with **16 enhanced strategies**
- 🎯 Advanced risk controls (stop-loss, take-profit, max bets)
- 📈 Real-time statistics and performance tracking
- 🧪 **Simulation Mode**: Test strategies safely before risking real funds

**Script Editor (NEW!):**
- 📝 **DiceBot-compatible** script editor with syntax highlighting
- 💾 Auto-save, version history, file management
- 📚 Pre-loaded example strategies (Martingale, Target Profit, etc.)
- ⚡ Write custom strategies in Python with full DiceBot API compatibility

### ⌨️ DuckDice CLI (Advanced)
- ✅ Original Dice & Range Dice games
- ✅ Currency statistics and user info
- ✅ Faucet mode & wagering bonuses
- ✅ Time Limited Events (TLE)
- ✅ JSON output for scripting
- ✅ Comprehensive error handling

### 🔬 RNG Analysis (Educational)
- ✅ Statistical analysis (Chi-square, KS test, runs test)
- ✅ Machine Learning (Random Forest, XGBoost, Neural Networks)
- ✅ Deep Learning (LSTM, GRU, CNN-LSTM, Attention)
- ✅ Pattern detection & visualization
- ✅ Strategy generation from analysis
- ✅ **Learn why cryptographic RNG is unbreakable**

[→ RNG Analysis Documentation](rng_analysis/README.md)

### 🤖 Automated Betting Strategies

**16 Professional Strategies** with enhanced information system:

**Classic Strategies:**
- 🔴 Martingale - Double on loss (high risk, high reward)
- 🟢 Anti-Martingale - Double on win (low risk)
- 🟡 Fibonacci - Mathematically elegant progression
- 🟡 D'Alembert - Gentle increase/decrease
- 🟠 Paroli - Positive progression system

**Advanced Strategies:**
- 🟠 Labouchere - Cancellation system
- 🟡 Oscar's Grind - Grind out small profits
- 🟡 1-3-2-6 - Fixed sequence system
- 🔴 Kelly Criterion (Capped) - Optimal bankroll sizing

**Intelligent Strategies:**
- 🟢 Target-Aware - AI-driven target chasing
- 🟢 Faucet Cashout - Optimize faucet earnings
- 🔴 Max Wager Flow - High-roller strategy
- 🟡 Range50 Random - Randomized approach

**Pattern-Based:**
- 🟠 RNG Analysis - Experimental pattern detection
- 🟠 Fibonacci Loss Cluster - Cluster-aware progression

**Custom:**
- ⚪ Script Editor - Write your own with DiceBot API!

**Each Strategy Includes:**
- 🎯 Risk level indicators (🟢 Low → 🔴 Very High)
- 💡 Expert tips and best practices
- ✅ Comprehensive pros/cons analysis
- 📊 Bankroll requirements and volatility ratings
- 📚 Detailed usage guidelines and warnings
- ⏱️ Time-to-profit estimates

**Click "ℹ️ Info" in the GUI to see beautiful strategy guides!**

[→ Strategy Documentation](src/betbot_strategies/) | [→ Enhanced Info Guide](docs/ENHANCED_STRATEGY_INFO.md)

## 📦 Installation

### Quick Install (Recommended)

**Option 1: Download Pre-Built Executable**

Visit the [Releases](../../releases) page and download the latest version for your platform:
- **Windows**: `DuckDiceBot-Windows.zip` → Extract and run `DuckDiceBot.exe`
- **macOS**: `DuckDiceBot-macOS.zip` → Extract and run `DuckDiceBot.app`
- **Linux**: `DuckDiceBot-Linux.zip` → Extract and run `./DuckDiceBot`

No Python installation required!

**Option 2: Run from Source** (All Platforms)

```bash
# 1. Clone repository
git clone https://github.com/sushiomsky/duckdice-bot.git
cd duckdice-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3A. Run NiceGUI Web Interface (NEW!)
./run_nicegui.sh
# Opens at http://localhost:8080

# 3B. Run Tkinter GUI
python3 duckdice_gui_ultimate.py
```

Get your API key from [DuckDice](https://duckdice.io) → Account Settings → Bot API

### Advanced: Build Your Own Executable

**Windows:**
```cmd
build_windows.bat
# Output: dist\DuckDiceBot.exe
```

**macOS/Linux:**
```bash
bash scripts/build_ultimate.sh
# Output: dist/DuckDiceBot (or .app on macOS)
```

See [WINDOWS_BUILD.md](WINDOWS_BUILD.md) for detailed build instructions.

## 📸 Screenshots

### Modern Dashboard with Mode Indicator
![Dashboard showing live balance tracking and clear mode indicators]

*Real-time balance, profit tracking, and unmissable Simulation/Live mode banner*

### Script Editor with Syntax Highlighting
![DiceBot-compatible script editor with syntax highlighting]

*Write custom strategies with professional code editor features*

### 16 Enhanced Strategies with Detailed Info
![Strategy selection with risk indicators and comprehensive information dialogs]

*Each strategy includes risk levels, expert tips, pros/cons, and usage guidelines*

### Dynamic Currency Selection
![Currency dropdown auto-populated from your DuckDice account]

*No more hardcoded lists - see your actual available currencies*

---

## 🎮 Usage Guide

### Getting Started

1. **Launch the Application**
   ```bash
   python3 duckdice_gui_ultimate.py
   # Or run the pre-built executable
   ```

2. **Configure API Key**
   - Click **Settings** (or press `Ctrl+,`)
   - Enter your DuckDice API key
   - Test connection

3. **Choose Your Mode**
   - 🟢 **Simulation Mode**: Practice with fake balance (safe!)
   - 🔴 **Live Mode**: Real betting with your DuckDice account

4. **Start Betting**
   - **Quick Bet Tab**: Manual single bets
   - **Auto Bet Tab**: Automated strategy betting
   - **Script Editor Tab**: Create custom strategies

### Keyboard Shortcuts

**NiceGUI Web Interface:**
- `Ctrl+D` - Dashboard
- `Ctrl+B` - Quick Bet
- `Ctrl+A` - Auto Bet
- `Ctrl+F` - Faucet
- `Ctrl+H` - History
- `Ctrl+S` - Settings

**Tkinter GUI:**
- `Ctrl+K` - Quick Connect/Disconnect
- `F5` - Refresh Balances
- `F6` - Refresh Currencies
- `Ctrl+N` - New Session
- `Ctrl+E` - Export Session
- `Ctrl+,` - Settings
- `Ctrl+1/2/3/4/5/6` - Switch tabs

### GUI Mode Features

**📊 Dashboard Tab**
- Live balance tracking
- Session profit/loss
- Win rate statistics
- Current streak display

**🎲 Quick Bet Tab**
- Single manual bets
- Choose currency (auto-loaded from your account!)
- Set bet amount and win chance
- Over/Under selection

**🤖 Auto Bet Tab**
- Select from 16 strategies
- Configure risk parameters
- Set stop-loss and take-profit
- View real-time progress

**📝 Script Editor Tab** (NEW!)
- Write custom betting scripts
- DiceBot API compatible
- Syntax highlighting
- Load example scripts
- Auto-save and version history

## CLI Commands Reference

### Dice Game
```bash
python3 duckdice.py --api-key KEY dice \
  --symbol CURRENCY --amount AMOUNT --chance PERCENTAGE (--high|--low) [--faucet]
```

### Range Dice
```bash
python3 duckdice.py --api-key KEY range-dice \
  --symbol CURRENCY --amount AMOUNT --range MIN MAX (--in|--out) [--faucet]
```

### Statistics & Info
```bash
python3 duckdice.py --api-key KEY stats --symbol CURRENCY
python3 duckdice.py --api-key KEY user-info
```

**For full command reference, see: `python3 duckdice.py --help`**

## 📂 Project Structure

```
duckdice-bot/
├── duckdice.py                      # CLI tool
├── duckdice_gui_ultimate.py         # Main GUI application
├── run_gui.sh                       # GUI launcher script
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── QUICKSTART.md                    # Quick start guide
│
├── src/
│   ├── betbot_engine/              # Auto-betting engine core
│   ├── betbot_strategies/          # 16 betting strategies
│   ├── duckdice_api/               # DuckDice API client
│   ├── gui_enhancements/           # Modern UI components
│   │   ├── modern_ui.py           # Mode indicator, status bar
│   │   ├── dashboard.py           # Dashboard widgets
│   │   └── keyboard_shortcuts.py  # Hotkey manager
│   └── script_editor/              # NEW: Script editor module
│       ├── editor.py              # Code editor widget
│       └── dicebot_compat.py      # DiceBot API layer
│
├── examples/                        # Example scripts
│   ├── auto_bet.py                 # Auto-betting demo
│   ├── balance_tracker.py          # Balance monitoring
│   └── strategy_scripts/           # Custom strategy examples
│
├── rng_analysis/                    # RNG analysis toolkit
│   ├── main_analysis.py            # Statistical analyzer
│   ├── ml_predictor.py             # ML models
│   ├── deep_learning_predictor.py  # Deep learning models
│   └── strategy_generator.py      # Strategy generation
│
├── scripts/                         # Build and utility scripts
│   └── build_ultimate.sh           # macOS/Linux build script
│
├── .github/workflows/               # CI/CD automation
│   └── build-release.yml           # Multi-platform builds
│
└── tests/                           # Test suite
```

## RNG Analysis Tool (Educational)

The `rng_analysis/` toolkit attempts to "attack" DuckDice's cryptographic RNG using advanced statistical and ML methods.

### Features
- 🔬 Statistical tests (Chi-square, KS, runs test)
- 🤖 Machine Learning (Random Forest, XGBoost)
- 🧠 Deep Learning (LSTM, GRU, CNN-LSTM)
- 📊 Pattern visualization
- 🎯 Strategy generation from analysis

### Quick Start
```bash
cd rng_analysis
pip install -r requirements_analysis.txt
python3 main_analysis.py
```

**[→ Full RNG Analysis Documentation](rng_analysis/README.md)**

### ⚠️ Important Disclaimer
**This is EDUCATIONAL ONLY.** Even with advanced ML/DL:
- ❌ You cannot predict cryptographic RNG (SHA-256)
- ❌ Historical patterns don't predict future outcomes
- ❌ The house edge ensures long-term casino profit
- ❌ Any "improvements" are overfitting

**Cryptographic RNG resists:** Pattern analysis, ML, statistical attacks, quantum computing (for now)

**Educational value: HIGH 📚 | Exploitation value: ZERO 🚫**

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Disclaimer

⚠️ **Important**: 
- For educational and convenience purposes only
- Gambling involves risk - only bet what you can afford to lose
- Use stop-loss and take-profit limits
- Check local gambling laws
- Authors not responsible for losses

**Gamble responsibly. This is NOT financial advice.**

## 🔧 Technical Highlights

### Modern Architecture
- **Modular Design**: Clean separation of API, engine, strategies, and UI
- **Type Safety**: Full type hints throughout codebase
- **Error Handling**: Comprehensive exception handling and user feedback
- **Thread Safety**: Background tasks for API calls without blocking UI

### Build & Deployment
- **CI/CD Pipeline**: GitHub Actions for automated multi-platform builds
- **Cross-Platform**: Windows, macOS, and Linux support
- **PyInstaller Integration**: Single-file executables for easy distribution
- **Automated Testing**: Test matrix across Python 3.9, 3.10, 3.11

### Code Quality
- **Clean Code**: PEP 8 compliant, well-documented
- **Extensible**: Easy to add new strategies and features
- **Configuration Management**: JSON-based config with validation
- **Logging**: Comprehensive bet history and session tracking

### Performance
- **Efficient API Calls**: Smart caching and batch operations
- **Responsive UI**: Async operations prevent freezing
- **Memory Management**: Efficient data structures and cleanup
- **Fast Startup**: Optimized imports and lazy loading

## 🤝 Contributing

Contributions welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Add tests** for new features
4. **Commit** changes (`git commit -m 'Add amazing feature'`)
5. **Push** to branch (`git push origin feature/amazing-feature`)
6. **Open** a Pull Request

**Areas for Contribution:**
- 🎨 UI/UX improvements
- 🤖 New betting strategies
- 📝 Documentation enhancements
- 🐛 Bug fixes
- 🧪 Test coverage
- 🌍 Internationalization

## 📜 Changelog

### v3.2.0 (2026-01-08) - Ultimate Edition
- ✨ Modern UI with clear Simulation/Live mode indicators
- ✨ Dynamic currency fetching from DuckDice API
- ✨ Professional script editor with DiceBot compatibility
- ✨ Enhanced strategy information system (16 strategies)
- ✨ Smart caching and manual refresh options
- 🔧 Improved API integration
- 🔧 CI/CD pipeline with automated builds
- 📝 Comprehensive documentation updates

### v3.1.0 (Previous)
- Strategy metadata and info dialogs
- Risk level indicators
- Enhanced GUI features

[See full changelog](CHANGELOG.md)

## 📊 Project Stats

- **Lines of Code**: ~15,000+
- **Strategies**: 16 built-in
- **Supported Games**: Dice, Range Dice
- **API Endpoints**: 10+ covered
- **Platforms**: Windows, macOS, Linux
- **License**: MIT

## License

Provided as-is for DuckDice API interaction. Use responsibly per DuckDice Terms of Service.

See [LICENSE](LICENSE) for details.

---

**Get Started:** [QUICKSTART.md](QUICKSTART.md) | **API Docs:** [duckdice.io/bot-api](https://duckdice.io/bot-api) | **Issues:** [GitHub Issues](../../issues) | **Releases:** [Download](../../releases)
