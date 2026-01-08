# DuckDice Bot - CLI & GUI

A comprehensive command-line interface and GUI for the [DuckDice Bot API](https://duckdice.io/bot-api). Play games, analyze patterns, and automate betting strategies responsibly.

## 🚀 Quick Start

**New users:** See [QUICKSTART.md](QUICKSTART.md) to get running in 2 minutes.

## Features

### 🖥️ DuckDice GUI (Recommended)
- ✅ User-friendly tabbed interface
- ✅ Visual betting controls (Dice, Range Dice)
- ✅ Automated betting with 9+ strategies
- ✅ Real-time stats and balance tracking
- ✅ Advanced risk controls (stop-loss, take-profit)
- ✅ Target-aware AI betting

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
16+ built-in strategies with **enhanced information system**:
- **Classic:** Martingale, Fibonacci, D'Alembert, Paroli
- **Advanced:** Labouchere, Oscar's Grind, 1-3-2-6, Kelly Criterion
- **AI-Powered:** Target-Aware, RNG Analysis (experimental)
- **Custom:** Script your own strategies

**NEW**: Each strategy now includes:
- 🎯 Risk level indicators (🟢 Low → 🔴 Very High)
- 💡 Expert tips and best practices
- ✅ Comprehensive pros/cons analysis
- 📊 Bankroll and volatility requirements
- 📚 Detailed usage guidelines

Click "ℹ️ Info" in the GUI to see beautiful strategy guides!

[→ Strategy Documentation](src/betbot_strategies/) | [→ Enhanced Info Guide](docs/ENHANCED_STRATEGY_INFO.md)

## Installation

### Option 1: Run from Source (All Platforms)

```bash
# 1. Clone repository
git clone <repository-url>
cd duckdice-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API key
export DUCKDICE_API_KEY="your-api-key-here"

# 4. Run
python3 duckdice_gui_ultimate.py
```

Get your API key from [DuckDice](https://duckdice.io) → Account Settings → Bot API

### Option 2: Build Standalone Executable

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

See [WINDOWS_BUILD.md](WINDOWS_BUILD.md) for detailed Windows build instructions.

**Note:** Pre-built Windows packages are not yet available. You must build on Windows or run from source.

## Usage

### GUI Mode (Recommended)

```bash
./run_gui.sh
# Or: python3 duckdice_gui_ultimate.py
```

### CLI Mode

```bash
# Check balance
python3 duckdice.py --api-key "$DUCKDICE_API_KEY" user-info

# Place bet
python3 duckdice.py --api-key "$DUCKDICE_API_KEY" dice \
  --symbol BTC --amount 0.1 --chance 50 --high

# Get statistics
python3 duckdice.py --api-key "$DUCKDICE_API_KEY" stats --symbol BTC
```

### Automated Betting

```bash
# GUI: Launch and go to Auto Bet tab
./run_gui.sh

# CLI: Use auto-bet script
python3 examples/auto_bet.py --api-key "$DUCKDICE_API_KEY" --strategy martingale
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed examples.**

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

## Project Structure

```
duckdice-bot/
├── duckdice.py                    # CLI tool
├── duckdice_gui_ultimate.py       # GUI application
├── run_gui.sh                     # GUI launcher
├── requirements.txt               # Dependencies
├── QUICKSTART.md                  # Quick start guide
├── README.md                      # This file
│
├── src/
│   ├── betbot_engine/            # Auto-bet engine
│   ├── betbot_strategies/        # Betting strategies
│   ├── duckdice_api/             # API client
│   └── gui_enhancements/         # GUI components
│
├── examples/                      # Example scripts
│   ├── auto_bet.py               # Auto-betting
│   ├── balance_tracker.py        # Balance monitoring
│   └── strategy_scripts/         # Custom strategies
│
├── rng_analysis/                  # RNG analysis toolkit
│   ├── main_analysis.py          # Main analyzer
│   ├── ml_predictor.py           # ML models
│   ├── deep_learning_predictor.py # DL models
│   └── strategy_generator.py    # Strategy from analysis
│
└── tests/                         # Test suite
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

## License

Provided as-is for DuckDice API interaction. Use responsibly per DuckDice Terms of Service.

See [LICENSE](LICENSE) for details.

---

**Get Started:** [QUICKSTART.md](QUICKSTART.md) | **API Docs:** [duckdice.io/bot-api](https://duckdice.io/bot-api)
