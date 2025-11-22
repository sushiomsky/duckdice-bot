# DuckDice API Command Line Tool

A comprehensive command-line interface for the [DuckDice Bot API](https://duckdice.io/bot-api). This tool implements all features of the DuckDice API, allowing you to play games, check stats, and manage your account directly from the terminal.

## Features

### DuckDice CLI Tool
✅ **Original Dice Game** - Play the classic dice game with high/low betting
✅ **Range Dice Game** - Bet on numbers being in or out of a range
✅ **Currency Statistics** - View detailed stats for any currency
✅ **User Information** - Get comprehensive user account details
✅ **Faucet Mode** - Play using faucet balance
✅ **Wagering Bonuses** - Use wagering bonus hashes
✅ **Time Limited Events (TLE)** - Participate in TLE events
✅ **Multiple Output Formats** - Human-readable or JSON output
✅ **Error Handling** - Comprehensive error messages and handling

### RNG Analysis Tool 🔬
✅ **Statistical Analysis** - Distribution tests, autocorrelation, runs test
✅ **Machine Learning** - Random Forest, XGBoost, Neural Networks
✅ **Deep Learning** - LSTM, GRU, CNN-LSTM, Attention models
✅ **Visualizations** - Comprehensive charts and plots
✅ **Pattern Detection** - Attempt to find exploitable patterns (spoiler: you won't)
✅ **Educational** - Learn why cryptographic RNG is secure

[→ See RNG Analysis Documentation](rng_analysis/README.md)

### RNG Analysis to Bot Strategy (NEW! 🤖)
✅ **Strategy Generator** - Convert analysis results to betting strategies
✅ **Multiple Recommendations** - Conservative, pattern-adapted, Kelly strategies
✅ **Risk Assessment** - Evaluates exploitability (usually none)
✅ **Ready to Use** - JSON and Python configuration formats
✅ **Auto-Integration** - Works with auto-bet engine
✅ **Educational Focus** - Demonstrates why patterns don't work

[→ See Strategy Integration Guide](docs/RNG_ANALYSIS_TO_STRATEGY_GUIDE.md) | [Quick Start](rng_analysis/STRATEGY_QUICKSTART.md)

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository:
```bash
git clone <repository-url>
cd duckdice-cli
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable (Unix/Linux/Mac):
```bash
chmod +x duckdice.py
```

## Usage

### Basic Command Structure

```bash
python duckdice.py --api-key YOUR_API_KEY [command] [options]
```

Or if executable:
```bash
./duckdice.py --api-key YOUR_API_KEY [command] [options]
```

### Global Options

- `--api-key KEY` (required) - Your DuckDice API key
- `--base-url URL` - Custom API base URL (default: https://duckdice.io/api)
- `--timeout SECONDS` - Request timeout in seconds (default: 30)
- `--json` - Output raw JSON response instead of formatted text

## Commands

### 1. Original Dice Game (`dice`)

Play the classic dice game by betting on high or low numbers.

#### Syntax

```bash
python duckdice.py --api-key KEY dice --symbol CURRENCY --amount AMOUNT --chance PERCENTAGE (--high|--low) [options]
```

#### Required Arguments

- `--symbol` - Currency symbol (e.g., BTC, XLM, XRP, ETH)
- `--amount` - Bet amount (decimal string)
- `--chance` - Win chance percentage (e.g., 77.77, 50, 88.88)
- `--high` OR `--low` - Bet direction (mutually exclusive)

#### Optional Arguments

- `--faucet` - Use faucet mode
- `--wagering-bonus-hash HASH` - Apply wagering bonus
- `--tle-hash HASH` - Use for Time Limited Event

#### Examples

```bash
# Bet 0.1 BTC on high with 77.77% chance
python duckdice.py --api-key YOUR_KEY dice --symbol BTC --amount 0.1 --chance 77.77 --high

# Bet 0.05 XLM on low with 50% chance using faucet
python duckdice.py --api-key YOUR_KEY dice --symbol XLM --amount 0.05 --chance 50 --low --faucet

# Bet with wagering bonus
python duckdice.py --api-key YOUR_KEY dice --symbol XRP --amount 1 --chance 88.88 --high --wagering-bonus-hash abc123
```

### 2. Range Dice Game (`range-dice`)

Bet on whether the result will be inside or outside a specified range.

#### Syntax

```bash
python duckdice.py --api-key KEY range-dice --symbol CURRENCY --amount AMOUNT --range MIN MAX (--in|--out) [options]
```

#### Required Arguments

- `--symbol` - Currency symbol
- `--amount` - Bet amount
- `--range MIN MAX` - Range boundaries (two integers, 0-9999)
- `--in` OR `--out` - Bet on in-range or out-of-range (mutually exclusive)

#### Optional Arguments

- `--faucet` - Use faucet mode
- `--wagering-bonus-hash HASH` - Apply wagering bonus
- `--tle-hash HASH` - Use for Time Limited Event

#### Examples

```bash
# Bet on number 7777 (in range 7777-7777)
python duckdice.py --api-key YOUR_KEY range-dice --symbol XLM --amount 0.1 --range 7777 7777 --in

# Bet on out of range 0-9998 (only 9999 wins)
python duckdice.py --api-key YOUR_KEY range-dice --symbol BTC --amount 0.01 --range 0 9998 --out

# Bet on in range 1000-5000 using faucet
python duckdice.py --api-key YOUR_KEY range-dice --symbol XRP --amount 0.5 --range 1000 5000 --in --faucet
```

### 3. Currency Statistics (`stats`)

Get statistics for a specific currency including bets, wins, profit, and balances.

#### Syntax

```bash
python duckdice.py --api-key KEY stats --symbol CURRENCY
```

#### Required Arguments

- `--symbol` - Currency symbol (e.g., BTC, XLM, XRP)

#### Examples

```bash
# Get BTC statistics
python duckdice.py --api-key YOUR_KEY stats --symbol BTC

# Get XLM statistics in JSON format
python duckdice.py --api-key YOUR_KEY --json stats --symbol XLM
```

#### Output Includes

- Total bets count
- Total wins count
- Profit in currency
- Volume in currency
- Main balance
- Faucet balance

### 4. User Information (`user-info`)

Get comprehensive information about your user account.

#### Syntax

```bash
python duckdice.py --api-key KEY user-info
```

#### Examples

```bash
# Get user information
python duckdice.py --api-key YOUR_KEY user-info

# Get user information as JSON
python duckdice.py --api-key YOUR_KEY --json user-info
```

#### Output Includes

- Username and user hash
- Level (paws) and absolute level
- Account creation timestamp
- Campaign and affiliate information
- Last deposit details
- Wagered amounts by currency
- All balances (main, faucet, affiliate) for all currencies
- Active wagering bonuses
- Active/finished Time Limited Events (TLEs)

## Output Formats

### Human-Readable Format (Default)

The default output is formatted for easy reading with sections, emojis, and clear labels.

Example:
```
============================================================
BET RESULT
============================================================

🎲 Game: Original Dice
Hash: bb7bd4178d9
Result: ✅ WIN
Number: 6559
Choice: >2222 (0.2222)

💰 Financial Details:
Currency: XLM
Bet Amount: 0.004
Chance: 77.77%
Payout: 1.273x
Win Amount: 0.005092
Profit: 0.001092
...
```

### JSON Format

Use the `--json` flag to get raw JSON output, useful for scripting and automation.

```bash
python duckdice.py --api-key YOUR_KEY --json dice --symbol BTC --amount 0.1 --chance 50 --high
```

Output:
```json
{
  "bet": {
    "hash": "bb7bd4178d9",
    "symbol": "BTC",
    "result": true,
    "choice": ">4999",
    ...
  },
  "user": {
    "username": "YourUsername",
    ...
  }
}
```

## API Key

You need a DuckDice API key to use this tool. Get your API key from:
1. Log in to [DuckDice](https://duckdice.io)
2. Navigate to your account settings
3. Generate or copy your Bot API key

### Securing Your API Key

**Never commit your API key to version control!**

Options for managing your API key:

1. **Environment Variable** (Recommended):
```bash
export DUCKDICE_API_KEY="your-api-key-here"
python duckdice.py --api-key "$DUCKDICE_API_KEY" user-info
```

2. **Configuration File**:
Create a `.env` file or config file (add to `.gitignore`):
```bash
# .env
DUCKDICE_API_KEY=your-api-key-here
```

3. **Shell Alias**:
```bash
alias duckdice='python /path/to/duckdice.py --api-key YOUR_API_KEY'
duckdice user-info
```

## Error Handling

The tool provides clear error messages for common issues:

- **HTTP Errors**: Shows HTTP status code and response
- **Network Errors**: Connection timeouts and failures
- **JSON Errors**: Invalid response parsing
- **Validation Errors**: Invalid arguments or missing parameters

Example error:
```
HTTP Error: 401 Client Error: Unauthorized
Response: {"error": "Invalid API key"}
```

## Advanced Usage

### Scripting and Automation

#### Bash Script Example

```bash
#!/bin/bash
API_KEY="your-api-key"

# Play 10 bets
for i in {1..10}; do
    echo "Bet $i:"
    python duckdice.py --api-key "$API_KEY" dice \
        --symbol XLM --amount 0.1 --chance 50 --high
    sleep 2
done

# Get final stats
python duckdice.py --api-key "$API_KEY" stats --symbol XLM
```

#### Python Script Example

```python
import subprocess
import json

API_KEY = "your-api-key"

# Get user info as JSON
result = subprocess.run([
    'python', 'duckdice.py',
    '--api-key', API_KEY,
    '--json', 'user-info'
], capture_output=True, text=True)

user_info = json.loads(result.stdout)
print(f"Username: {user_info['username']}")
print(f"Level: {user_info['level']}")
```

### Combining with jq

For advanced JSON processing, combine with `jq`:

```bash
# Get only the balance for BTC
python duckdice.py --api-key "$API_KEY" --json stats --symbol BTC | jq '.balances.main'

# Get all currency balances
python duckdice.py --api-key "$API_KEY" --json user-info | jq '.balances[] | {currency, main}'

# Check if last bet won
python duckdice.py --api-key "$API_KEY" --json dice --symbol XLM --amount 0.1 --chance 50 --high | jq '.bet.result'
```

## API Reference

This tool implements the complete [DuckDice Bot API](https://duckdice.io/bot-api):

### Endpoints Implemented

| Endpoint | Command | Description |
|----------|---------|-------------|
| `POST /api/dice/play` | `dice` | Play Original Dice game |
| `POST /api/range-dice/play` | `range-dice` | Play Range Dice game |
| `GET /api/bot/stats/<SYMBOL>` | `stats` | Get currency statistics |
| `GET /api/bot/user-info` | `user-info` | Get user information |

### Response Models

All responses follow the DuckDice API specification:

- **Bet Model**: Complete bet information including hash, result, amounts, and game details
- **User Model**: User profile with levels, stats, and balances
- **Currency Stats**: Bets, wins, profit, volume, and balances per currency
- **User Info**: Comprehensive account data including bonuses and TLEs

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'requests'`
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Issue**: `Permission denied` when running script
```bash
# Solution: Make script executable
chmod +x duckdice.py
```

**Issue**: Invalid API key error
```bash
# Solution: Verify your API key is correct and active
python duckdice.py --api-key YOUR_KEY user-info
```

**Issue**: Connection timeout
```bash
# Solution: Increase timeout or check network connection
python duckdice.py --api-key YOUR_KEY --timeout 60 user-info
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided as-is for interacting with the DuckDice API. Please use responsibly and in accordance with DuckDice's Terms of Service.

## Disclaimer

**Important**: 
- This tool is for educational and convenience purposes
- Gambling involves risk - only bet what you can afford to lose
- Always gamble responsibly
- Check your local laws regarding online gambling
- The authors are not responsible for any losses incurred

## Support

For issues related to:
- **This tool**: Open an issue in this repository
- **DuckDice API**: Visit [DuckDice Support](https://duckdice.io)
- **API Documentation**: [DuckDice Bot API Docs](https://duckdice.io/bot-api)

## RNG Analysis Tool

### What Is This?

The `rng_analysis/` directory contains a comprehensive toolkit that attempts to **"attack" the DuckDice RNG** using advanced machine learning and statistical methods.

### Features

🔬 **Statistical Analysis**
- Chi-square and Kolmogorov-Smirnov tests
- Autocorrelation analysis
- Runs test for randomness
- Fourier analysis for periodic patterns
- Seed and nonce correlation analysis

🤖 **Machine Learning**
- Random Forest, Gradient Boosting
- XGBoost, LightGBM
- Neural Networks (MLP)
- Time series cross-validation
- Win/Loss classification

🧠 **Deep Learning**
- LSTM (Long Short-Term Memory)
- GRU (Gated Recurrent Unit)
- CNN-LSTM hybrid models
- Attention mechanisms
- Sequence prediction

📊 **Visualizations**
- Distribution analysis
- Time series plots
- Autocorrelation functions
- Pattern heatmaps
- Feature importance

### Quick Start

```bash
cd rng_analysis
pip install -r requirements_analysis.txt
python main_analysis.py
```

**See [RNG Analysis README](rng_analysis/README.md) for complete documentation.**

### 🆕 Convert Analysis to Bot Strategy

You can now use RNG analysis results to create ready-to-use betting strategies!

```bash
# 1. Generate strategy from analysis
cd rng_analysis
python strategy_generator.py

# 2. Use the generated strategy
python ../examples/use_rng_analysis_strategy.py --api-key YOUR_KEY --dry-run
```

**See [RNG Analysis to Strategy Guide](docs/RNG_ANALYSIS_TO_STRATEGY_GUIDE.md) for details.**

**Features:**
- 🎯 Converts analysis insights into strategy configurations
- 📊 Multiple recommendation levels (conservative to experimental)
- ⚙️ JSON and Python export formats
- 🤖 Ready-to-use with the auto-bet engine
- ⚠️ Educational only - includes comprehensive warnings

### ⚠️ Important Disclaimer

**This tool is for EDUCATIONAL PURPOSES ONLY.**

Even with advanced ML/DL:
- ❌ You cannot predict cryptographic RNG
- ❌ Patterns in historical data don't predict future outcomes
- ❌ The house edge ensures long-term casino profit
- ❌ Any "improvements" are likely overfitting

**Cryptographic RNG (SHA-256) is designed to resist:**
- Pattern analysis
- Machine learning
- Statistical attacks
- Even quantum computers (for now)

**Use responsibly. Gamble responsibly. This is NOT a way to make money.**

### What You'll Learn

✅ How provably fair RNG works
✅ Why cryptographic hash functions are secure
✅ How to analyze random data statistically
✅ Machine learning for sequence prediction
✅ Why the house always wins
✅ The mathematics of gambling

**Educational value: HIGH 📚**
**Practical exploitation value: ZERO 🚫**

---

## Project Structure

```
duckdice-cli/
├── duckdice.py              # Main CLI tool
├── requirements.txt         # CLI dependencies
├── README.md               # This file
├── examples/               # Example scripts
│   ├── auto_bet.py
│   ├── balance_tracker.py
│   └── stats_monitor.sh
│
├── rng_analysis/           # RNG Analysis toolkit
│   ├── README.md           # Analysis documentation
│   ├── main_analysis.py    # Main analysis runner
│   ├── data_loader.py      # Data loading/preprocessing
│   ├── pattern_analyzer.py # Statistical analysis
│   ├── ml_predictor.py     # Machine learning models
│   ├── deep_learning_predictor.py  # Deep learning
│   ├── visualizer.py       # Visualization tools
│   └── requirements_analysis.txt   # Analysis dependencies
│
└── bet_history/            # Your bet history CSVs
    ├── bets_1.csv
    ├── bets_2.csv
    └── ...
```

---

## Changelog

### Version 1.1.0
- ✨ **NEW: RNG Analysis Toolkit** - Comprehensive ML/DL analysis
- Added statistical pattern detection
- Added machine learning prediction models
- Added deep learning (LSTM, GRU) models
- Added comprehensive visualizations
- Added educational documentation about RNG security

### Version 1.0.0
- Initial release
- Complete implementation of all DuckDice API endpoints
- Support for Original Dice and Range Dice games
- Currency statistics and user information commands
- Human-readable and JSON output formats
- Comprehensive error handling
- Full documentation

---

**Happy Dicing! 🎲 (Responsibly!)**
