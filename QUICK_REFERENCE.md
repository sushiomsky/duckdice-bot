# DuckDice CLI - Quick Reference

## Installation
```bash
pip install -r requirements.txt
```

## Basic Commands

| Command | Description |
|---------|-------------|
| `python3 duckdice_cli.py` | **Interactive mode** (recommended) |
| `python3 duckdice_cli.py interactive` | Start interactive guided setup |
| `python3 duckdice_cli.py strategies` | List all strategies |
| `python3 duckdice_cli.py run` | Start betting with arguments |
| `python3 duckdice_cli.py profiles` | List saved profiles |
| `python3 duckdice_cli.py config` | Show configuration |
| `python3 duckdice_cli.py --help` | Show help |

## Quick Start Examples

### Interactive Mode (Easiest!)
```bash
# Just run without arguments - will guide you through everything
python3 duckdice_cli.py

# Steps:
# 1. Choose mode (simulation/live-main/live-faucet)
# 2. Select currency (btc/doge/eth/ltc/bch/trx)
# 3. Set balance (simulation only)
# 4. Pick strategy (18 available, grouped by risk)
# 5. Configure parameters (or use defaults)
# 6. Set risk limits
# 7. Start betting!
```

### Simulation (Safe Testing)
```bash
# Interactive mode
python3 duckdice_cli.py

# Automated mode
python3 duckdice_cli.py run \
  -m simulation \
  -s classic-martingale \
  -c btc \
  --max-bets 100
```

### Live Betting
```bash
# Main balance
python3 duckdice_cli.py run \
  -m live-main \
  -s fibonacci \
  -c btc \
  -k YOUR_API_KEY

# Faucet balance
python3 duckdice_cli.py run \
  -m live-faucet \
  -s dalembert \
  -c doge \
  -k YOUR_API_KEY
```

## Strategies Cheat Sheet

| Strategy | Risk | Best For |
|----------|------|----------|
| dalembert | Low | Beginners, steady play |
| oscars-grind | Low | Small consistent profits |
| fibonacci | Medium | Balanced approach |
| paroli | Medium | Positive progression |
| classic-martingale | **HIGH** | ⚠️ Large bankroll only |
| faucet-grind | Medium | Faucet balance grinding |

## Risk Controls

```bash
--stop-loss -0.2      # Stop at -20%
--take-profit 0.5     # Stop at +50%
--max-bets 100        # Max 100 bets
--max-losses 5        # Stop after 5 losses
--max-duration 3600   # 1 hour time limit
```

## Profile Management

```bash
# Save profile
python3 duckdice_cli.py save-profile my-strategy -s fibonacci

# Use profile  
python3 duckdice_cli.py run -p my-strategy -m simulation
```

## Configuration

```bash
# Set API key
python3 duckdice_cli.py config --set api_key=YOUR_KEY

# Set defaults
python3 duckdice_cli.py config --set default_currency=doge
python3 duckdice_cli.py config --set default_mode=simulation
```

## Database Queries

```bash
# Open database
sqlite3 ~/.duckdice/history.db

# Recent sessions
SELECT * FROM sessions ORDER BY started_at DESC LIMIT 10;

# Win rate
SELECT strategy, 
       CAST(SUM(won) AS FLOAT) / COUNT(*) * 100 as win_rate
FROM bet_history 
GROUP BY strategy;
```

## Safety Checklist

- ✅ Test in simulation first
- ✅ Use faucet before main balance
- ✅ Set stop-loss limits
- ✅ Start with small amounts
- ✅ Monitor actively
- ⚠️ Never use martingale without limits

## Getting Help

```bash
# Command help
python3 duckdice_cli.py run --help

# Documentation
cat CLI_GUIDE.md
cat README.md
```

## File Locations

- Config: `~/.duckdice/config.json`
- Profiles: `~/.duckdice/profiles.json`
- History: `~/.duckdice/history.db`
- Logs: `bet_history/auto/*.jsonl`

## Tips

💡 Omit arguments for interactive prompts  
💡 Use profiles to save time  
💡 Query database for analytics  
💡 Set conservative limits  
💡 Monitor output carefully  
💡 Test strategies in simulation  

---

**Full Documentation**: CLI_GUIDE.md  
**Get API Key**: https://duckdice.io → Bot API

## New Strategy: Streak Hunter

Hunt winning streaks at 14% chance with decreasing multipliers:

```bash
# Default settings
python3 duckdice_cli.py run -s streak-hunter -m simulation

# Conservative
python3 duckdice_cli.py run -s streak-hunter -m simulation \
  -P min_bet=0.001 \
  -P balance_divisor=500 \
  --stop-loss -0.2 \
  --max-bets 100

# Custom multipliers
python3 duckdice_cli.py run -s streak-hunter -m simulation \
  -P first_multiplier=1.5 \
  -P second_multiplier=1.3 \
  -P third_multiplier=1.2
```

**How it works:**
- Hunts 14% win chance (~7x payout)
- Base bet: max(min_bet, balance/300)
- Win 1: Bet profit × 2.0 (200%)
- Win 2: Bet profit × 1.8 (180%)
- Win 3: Bet profit × 1.6 (160%)
- Win 4+: Decreases by 0.2 each time
- **Reset to base on any loss**
