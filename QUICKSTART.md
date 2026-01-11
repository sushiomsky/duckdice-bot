# Quick Start Guide

Get started with DuckDice Bot in minutes!

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
export DUCKDICE_API_KEY="your-api-key-here"
```

## GUI Mode (Recommended)

Launch the graphical interface:

```bash
./run_gui.sh
# Or: python3 duckdice_gui_ultimate.py
```

**Features:**
- 🎲 Dice & Range Dice betting
- 📊 Live statistics & balance tracking
- 🤖 Automated betting strategies
- 🎯 Target-aware betting
- ⚙️ Advanced risk controls

## CLI Mode (Advanced)

### Get User Info
```bash
python3 duckdice.py --api-key "$DUCKDICE_API_KEY" user-info
```

### Play Dice
```bash
# Bet 0.1 BTC on high with 77.77% win chance
python3 duckdice.py --api-key "$DUCKDICE_API_KEY" dice \
  --symbol BTC --amount 0.1 --chance 77.77 --high
```

### Check Stats
```bash
python3 duckdice.py --api-key "$DUCKDICE_API_KEY" stats --symbol BTC
```

## Automated Betting

Run auto-bet strategies:

```bash
# Using GUI - Auto Bet tab
./run_gui.sh

# Using CLI
python3 examples/auto_bet.py --api-key "$DUCKDICE_API_KEY" --strategy martingale
```

**Available Strategies:**
- `flat` - Fixed bet amount
- `martingale` - Double after loss
- `fibonacci` - Fibonacci sequence
- `dalembert` - Gradual progression
- `paroli` - Reverse martingale
- `labouchere` - Cancellation system
- `oscars_grind` - Conservative progression
- `one_three_two_six` - Fixed pattern
- `target_aware` - AI-powered betting

## RNG Analysis

Analyze betting patterns (educational):

```bash
cd rng_analysis
pip install -r requirements_analysis.txt
python3 main_analysis.py
```

## Safety Features

All modes include:
- 🛡️ Stop-loss limits
- 💰 Take-profit targets
- 🎯 Max bet limits
- ⏱️ Time/bet count limits
- 📊 Real-time balance tracking

## Getting Help

- Full documentation: [README.md](README.md)
- API details: [src/duckdice_api/](src/duckdice_api/)
- Strategy guide: [src/betbot_strategies/](src/betbot_strategies/)
- RNG analysis: [rng_analysis/README.md](rng_analysis/README.md)

## ⚠️ Responsible Gambling

- Only bet what you can afford to lose
- Use stop-loss and take-profit limits
- Take regular breaks
- Gambling should be entertainment, not income

---

**Ready to start? Launch the GUI with `./run_gui.sh`**
