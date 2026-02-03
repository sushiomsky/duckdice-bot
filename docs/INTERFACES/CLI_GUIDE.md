# DuckDice Bot CLI Guide

Complete command-line interface for automated betting on DuckDice.io

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x duckdice_cli.py
```

### Your First Simulation

```bash
# Run classic martingale strategy in simulation mode
python3 duckdice_cli.py run \
  --mode simulation \
  --strategy classic-martingale \
  --currency btc \
  --max-bets 100
```

### Interactive Mode (Recommended for Beginners)

The easiest way to get started is with interactive mode - it will guide you through all the setup steps:

```bash
# Start interactive mode (no arguments needed!)
python3 duckdice_cli.py

# Or explicitly
python3 duckdice_cli.py interactive
```

Interactive mode walks you through:
1. **Betting Mode** - Choose simulation, live-main, or live-faucet
2. **Currency** - Select BTC, DOGE, ETH, LTC, BCH, or TRX
3. **Initial Balance** - Set starting balance (simulation only)
4. **Strategy Selection** - Choose from 18 strategies grouped by risk level
5. **Parameter Configuration** - Customize strategy parameters or use defaults
6. **Risk Management** - Set stop-loss, take-profit, and bet limits
7. **Confirmation** - Review summary and start betting

**Example Interactive Session:**
```
$ python3 duckdice_cli.py

============================================================
🎲 DuckDice Bot - Interactive Mode
============================================================

Step 1: Select Betting Mode
----------------------------------------
  1. simulation      - Safe testing with virtual balance
  2. live-main       - Real betting with your main balance
  3. live-faucet     - Real betting with faucet balance

Select [1-3]: 1
✓ Selected: simulation

Step 2: Select Currency
----------------------------------------
  1. BTC  2. DOGE  3. ETH  4. LTC  5. BCH  6. TRX

Select [1-6]: 1
✓ Selected: BTC

Step 3: Initial Balance (Simulation)
----------------------------------------
Starting balance [100.0]: 50
✓ Balance: 50.0

Step 4: Select Strategy
----------------------------------------
🟢 Conservative (Low Risk):
  • dalembert  • oscars-grind  • one-three-two-six

🔴 Aggressive (High Risk):
  • classic-martingale  • streak-hunter

Select [1-18]: 17
✓ Selected: streak-hunter

Step 5: Configure Strategy
----------------------------------------
Configure strategy parameters? (y/n) [n]: n
✓ Using default parameters

Step 6: Risk Management
----------------------------------------
Stop-loss % (e.g., -0.5 = -50%) [-0.5]: -0.3
Take-profit % (e.g., 1.0 = +100%) [1.0]: 0.5
Maximum bets (0 = unlimited) [0]: 50
Max consecutive losses (0 = unlimited) [0]: 

📋 SESSION SUMMARY
Mode:         simulation
Currency:     BTC
Balance:      50.0
Strategy:     streak-hunter
Stop-loss:    -30.0%
Take-profit:  50.0%
Max bets:     50

Ready to start? (y/n) [y]: y
🚀 Starting session...
```

## Features

✅ **18 Built-in Strategies** - From conservative to aggressive
✅ **Simulation Mode** - Test strategies risk-free with virtual balance
✅ **Live Betting** - Real betting on DuckDice (main or faucet balance)
✅ **Profile Management** - Save and reuse strategy configurations
✅ **Risk Controls** - Stop-loss, take-profit, max bets, max losses
✅ **Session History** - All bets saved to SQLite database
✅ **Interactive & Automated** - Use command-line args or interactive prompts

## Commands

### List Strategies

View all available betting strategies:

```bash
python3 duckdice_cli.py strategies
```

Example output:
```
Available Strategies:
============================================================
  • classic-martingale
    Double bet on loss, reset on win. High risk, requires large bankroll.
  • fibonacci
    Follow Fibonacci sequence: advance on loss, retreat on win. Moderate risk.
  • dalembert
    Increase bet by fixed amount on loss, decrease on win. Balanced approach.
  ...
```

### Run a Strategy

#### Simulation Mode (Recommended for Testing)

```bash
# Basic simulation
python3 duckdice_cli.py run \
  --mode simulation \
  --strategy fibonacci \
  --currency btc

# With limits
python3 duckdice_cli.py run \
  --mode simulation \
  --strategy classic-martingale \
  --currency btc \
  --max-bets 100 \
  --stop-loss -0.2 \
  --take-profit 0.5
```

#### Live Mode - Main Balance

```bash
python3 duckdice_cli.py run \
  --mode live-main \
  --strategy dalembert \
  --currency btc \
  --api-key YOUR_API_KEY \
  --max-bets 50
```

#### Live Mode - Faucet Balance

```bash
python3 duckdice_cli.py run \
  --mode live-faucet \
  --strategy faucet-grind \
  --currency doge \
  --api-key YOUR_API_KEY
```

#### Interactive Mode

If you omit arguments, the CLI will prompt you interactively:

```bash
python3 duckdice_cli.py run
```

Prompts:
```
Select betting mode:
  1. simulation (default)
  2. live-main
  3. live-faucet
Select [1-3]: 

Currency [btc]: 

Select strategy:
  1. anti-martingale-streak
  2. classic-martingale
  ...
```

### Save Strategy Profile

Save your favorite strategy configurations for reuse:

```bash
# Interactive
python3 duckdice_cli.py save-profile

# With arguments
python3 duckdice_cli.py save-profile my-martingale \
  --strategy classic-martingale
```

This will prompt you for each parameter:
```
Configure parameters (press Enter for default):
base_amount (Base bet amount) [0.000001]: 0.00001
chance (Win chance percent) [49.5]: 49.5
is_high (Bet on High (True) or Low (False)) [True]: True
multiplier (Multiplier on loss (typically 2.0)) [2.0]: 2.0
max_streak (Max loss streak before reset) [10]: 8
reset_on_win (Reset to base on win) [True]: True
```

### Use Saved Profile

```bash
python3 duckdice_cli.py run \
  --profile my-martingale \
  --mode simulation
```

### List Profiles

```bash
python3 duckdice_cli.py profiles
```

### Configure Defaults

```bash
# View current configuration
python3 duckdice_cli.py config

# Set default values
python3 duckdice_cli.py config --set default_currency=doge
python3 duckdice_cli.py config --set default_mode=simulation
```

## Command Reference

### `run` - Run a Strategy

| Argument | Description | Default |
|----------|-------------|---------|
| `-m, --mode` | Betting mode: `simulation`, `live-main`, `live-faucet` | Interactive prompt |
| `-c, --currency` | Currency: `btc`, `doge`, `eth`, etc. | `btc` |
| `-s, --strategy` | Strategy name | Interactive prompt |
| `-p, --profile` | Load saved profile | None |
| `-b, --balance` | Initial balance (simulation only) | `100.0` |
| `-k, --api-key` | DuckDice API key (live mode) | From config or prompt |
| `--stop-loss` | Stop loss as decimal (e.g., `-0.5` = -50%) | `-0.5` |
| `--take-profit` | Take profit as decimal (e.g., `1.0` = +100%) | `1.0` |
| `--max-bets` | Maximum number of bets | Unlimited |
| `--max-losses` | Maximum consecutive losses | Unlimited |
| `--max-duration` | Maximum duration in seconds | Unlimited |

### `strategies` - List Available Strategies

No arguments. Shows all built-in strategies with descriptions.

### `save-profile` - Save Strategy Configuration

| Argument | Description |
|----------|-------------|
| `name` | Profile name (positional or prompted) |
| `-s, --strategy` | Strategy name | Interactive prompt |

### `profiles` - List Saved Profiles

No arguments. Shows all saved profiles.

### `config` - Manage Configuration

| Argument | Description |
|----------|-------------|
| `--set` | Set config value: `key=value` |

## Strategies

### Conservative (Low Risk)

- **dalembert** - Increase bet by fixed amount on loss, decrease on win
- **oscars-grind** - Increase bet after wins, target small consistent profits
- **one-three-two-six** - Fixed sequence, controlled risk

### Moderate Risk

- **fibonacci** - Follow Fibonacci sequence on losses
- **labouchere** - Cancellation system
- **paroli** - Double on wins up to target streak

### Aggressive (High Risk)

- **classic-martingale** - Double on loss (requires large bankroll!)
- **anti-martingale-streak** - Multiply on wins
- **fib-loss-cluster** - Fibonacci on loss streaks

### Specialized

- **faucet-grind** - Optimized for faucet betting
- **faucet-cashout** - USD-targeted staged growth
- **kelly-capped** - Kelly criterion with caps
- **target-aware** - State machine with profit targets
- **range50-random** - Range dice at 50% chance
- **max-wager-flow** - Maximize wagering throughput

### Advanced

- **rng-analysis-strategy** - Uses RNG analysis (educational)
- **custom-script** - Load your own Python strategy

## Risk Management

### Stop Loss

Automatically stops when balance drops by specified percentage:

```bash
--stop-loss -0.2  # Stop at -20%
--stop-loss -0.5  # Stop at -50%
```

### Take Profit

Automatically stops when balance increases by specified percentage:

```bash
--take-profit 0.5   # Stop at +50%
--take-profit 1.0   # Stop at +100%
--take-profit 2.0   # Stop at +200%
```

### Max Bets

Limit total number of bets:

```bash
--max-bets 100   # Stop after 100 bets
--max-bets 1000  # Stop after 1000 bets
```

### Max Losses

Stop after N consecutive losses:

```bash
--max-losses 5   # Stop after 5 losses in a row
--max-losses 10  # Stop after 10 losses in a row
```

### Max Duration

Stop after specified time:

```bash
--max-duration 300    # Stop after 5 minutes
--max-duration 3600   # Stop after 1 hour
```

## Session History

All bets are automatically saved to `~/.duckdice/history.db` (SQLite database).

### Database Schema

**sessions** table:
- session_id, strategy, currency, mode
- starting_balance, ending_balance
- total_bets, wins, losses, profit
- started_at, ended_at, stop_reason

**bet_history** table:
- session_id, timestamp
- amount, chance, target, roll
- won, profit, balance
- strategy, currency, mode

### Query Examples

```bash
# Install sqlite3 if needed
sqlite3 ~/.duckdice/history.db

# Recent sessions
SELECT session_id, strategy, profit, profit_percent 
FROM sessions 
ORDER BY started_at DESC 
LIMIT 10;

# Best sessions
SELECT session_id, strategy, profit 
FROM sessions 
ORDER BY profit DESC 
LIMIT 10;

# Win rate by strategy
SELECT strategy, 
       COUNT(*) as total,
       SUM(won) as wins,
       CAST(SUM(won) AS FLOAT) / COUNT(*) * 100 as win_rate
FROM bet_history 
GROUP BY strategy;
```

## Configuration Files

All configuration stored in `~/.duckdice/`:

- `config.json` - Default settings (currency, mode, API key)
- `profiles.json` - Saved strategy profiles
- `history.db` - SQLite database with all bet history

### Example config.json

```json
{
  "api_key": "your_api_key_here",
  "default_currency": "btc",
  "default_mode": "simulation",
  "default_balance": "100.0"
}
```

### Example profiles.json

```json
{
  "safe-martingale": {
    "strategy": "classic-martingale",
    "parameters": {
      "base_amount": "0.00000100",
      "chance": "49.5",
      "is_high": true,
      "multiplier": 2.0,
      "max_streak": 6,
      "reset_on_win": true
    },
    "created_at": "2026-01-12T10:30:00"
  }
}
```

## Examples

### Conservative Simulation

Test a safe strategy with strict limits:

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s dalembert \
  -c btc \
  -b 100 \
  --max-bets 500 \
  --stop-loss -0.1 \
  --take-profit 0.2
```

### Aggressive Faucet Grinding

Try to build faucet balance aggressively:

```bash
python3 duckdice_cli.py run \
  -m live-faucet \
  -s faucet-grind \
  -c doge \
  -k YOUR_API_KEY \
  --max-losses 3
```

### Profile-Based Betting

Save your configuration and reuse it:

```bash
# Create profile
python3 duckdice_cli.py save-profile my-strategy -s fibonacci

# Use profile in simulation
python3 duckdice_cli.py run -p my-strategy -m simulation

# Use profile live
python3 duckdice_cli.py run -p my-strategy -m live-main -k YOUR_API_KEY
```

## Troubleshooting

### API Key Not Working

- Ensure your API key is valid
- Check it has necessary permissions
- Try saving it to config: `python3 duckdice_cli.py config --set api_key=YOUR_KEY`

### Strategy Not Found

- List available strategies: `python3 duckdice_cli.py strategies`
- Use exact name from the list (e.g., `classic-martingale`, not `martingale`)

### Simulation Shows No Profit/Loss

- Some strategies have very small base amounts
- Increase max bets or check strategy parameters
- Review strategy description for expected behavior

### Permission Denied

```bash
chmod +x duckdice_cli.py
```

## Safety Tips

⚠️ **IMPORTANT**: Always test in simulation mode first!

1. **Start Small** - Use tiny bet amounts
2. **Set Limits** - Always use stop-loss and max-bets
3. **Test First** - Simulate before going live
4. **Monitor Sessions** - Watch the output
5. **Review History** - Check database for patterns
6. **Use Faucet** - Test with faucet balance before main
7. **Martingale Warning** - Classic martingale is extremely risky!

## Advanced Usage

### Custom Strategy Scripts

Create your own strategy and use it:

```bash
# Create your strategy file: my_strategy.py
# Then use custom-script strategy
python3 duckdice_cli.py run -s custom-script -m simulation
```

### Batch Testing Multiple Strategies

```bash
for strategy in dalembert fibonacci oscars-grind; do
  echo "Testing $strategy..."
  python3 duckdice_cli.py run \
    -m simulation \
    -s $strategy \
    --max-bets 100 \
    --currency btc
done
```

### Export Session Data

```bash
# Export to CSV
sqlite3 -header -csv ~/.duckdice/history.db \
  "SELECT * FROM bet_history WHERE session_id='...';" \
  > session_export.csv
```

## Support

For issues, questions, or contributions:
- GitHub Issues: [Your repo URL]
- Documentation: CLI_GUIDE.md, USER_GUIDE.md
- Strategy Details: Check each strategy's docstrings

## License

[Your license here]
