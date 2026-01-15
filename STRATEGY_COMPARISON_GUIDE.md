# Strategy Comparison Tool

## Overview

Compare **all** betting strategies under identical conditions and generate beautiful, interactive HTML reports with comprehensive analysis.

**Fixed and verified with realistic results!**

## Quick Start

```bash
# Recommended: 10 BTC, 2000 bets for meaningful results
./compare_strategies.sh 10.0 2000

# Or use Python directly
python3 strategy_comparison.py -b 10.0 -n 2000
```

## Sample Results

With 10 BTC starting balance and 2000 bets:

- **Stable strategies**: anti-martingale-streak, classic-martingale, paroli (~0%)
- **Slight profit**: labouchere (+0.02%)
- **Moderate risk**: kelly-capped (-0.73%), oscars-grind (-0.03%)
- **High risk**: streak-hunter (-55% high variance!)
- **Busters**: faucet-cashout, max-wager-flow, range-50-random (-99%)

## Features

✨ **Comprehensive Testing**
- Tests all 18 strategies with identical starting conditions
- Same random seed for reproducibility
- Parallel comparison in one run

📊 **Rich HTML Reports**
- Interactive Chart.js charts
- Profit comparison bar charts
- Win rate analysis
- Max balance reached
- Total wagered comparison

📈 **Detailed Metrics**
- Win rate
- Profit/Loss percentage
- Max balance reached
- Min balance (bust detection)
- Average bet size
- Max bet size
- Total wagered
- Execution time
- Stop reason
- Bust count

🎯 **Smart Analysis**
- Ranks strategies by performance
- Identifies profitable vs busted strategies
- Shows best and worst performers
- Individual strategy breakdowns

## Quick Start

### Basic Usage

```bash
# Compare all strategies with default settings (1.0 BTC, 500 bets)
./compare_strategies.sh
```

### Custom Parameters

```bash
# Custom balance and bet count
./compare_strategies.sh 5.0 1000

# With custom output file
./compare_strategies.sh 2.0 750 my_report.html
```

### Using Python Directly

```bash
# Full control over all parameters
python3 strategy_comparison.py \
    --balance 10.0 \
    --max-bets 2000 \
    --currency btc \
    --seed 42 \
    --output detailed_comparison.html
```

## Command Line Options

### strategy_comparison.py

```
-b, --balance BALANCE      Starting balance (default: 1.0)
-n, --max-bets MAX_BETS   Maximum bets per strategy (default: 1000)
-c, --currency CURRENCY    Currency symbol (default: btc)
-s, --seed SEED           Random seed for reproducibility (default: 42)
-o, --output OUTPUT       Output HTML file (default: strategy_comparison.html)
```

## Examples

### Compare with Large Bankroll
```bash
python3 strategy_comparison.py -b 100.0 -n 5000
```

### Quick Test (Fast)
```bash
python3 strategy_comparison.py -b 1.0 -n 100
```

### Comprehensive Test (Thorough)
```bash
python3 strategy_comparison.py -b 10.0 -n 10000
```

### Reproducible Results
```bash
# Same seed = same results every time
python3 strategy_comparison.py -s 42 -n 1000
python3 strategy_comparison.py -s 42 -n 1000  # Identical results
```

## Output Report

The generated HTML report includes:

### Summary Section
- Total strategies tested
- Skipped strategies (require special config)
- Starting balance
- Max bets per strategy
- Profitable count
- Busted count
- Best and worst returns

### Interactive Charts
1. **Profit Comparison** - Bar chart showing profit % for each strategy
2. **Max Balance Reached** - Highest balance achieved per strategy
3. **Win Rate Comparison** - Win rate % for each strategy
4. **Total Wagered** - Total amount bet per strategy

### Detailed Table
Sortable table with:
- Rank (🥇🥈🥉)
- Strategy name
- Bets placed
- Win rate %
- Ending balance
- Profit %
- Max balance
- Bust count
- Avg bet size
- Stop reason

### Individual Strategy Details
For each strategy:
- Bets placed
- Win rate
- Ending balance
- Profit/Loss
- Max balance
- Min balance
- Avg bet size
- Max bet size
- Total wagered
- Duration
- Busts
- Stop reason

## Understanding Results

### Profit % (Key Metric)
- **Positive** (green): Strategy made money
- **Negative** (red): Strategy lost money
- **-100%**: Complete bust (lost everything)

### Win Rate
- Percentage of bets won
- Higher is generally better, but not always
- Some strategies bet less frequently but win big

### Max Balance
- Highest balance reached during session
- Shows potential even if strategy ultimately lost
- Useful for understanding volatility

### Busts
- Number of times balance dropped to ~zero
- **0 busts**: Strategy maintained balance
- **>0 busts**: Strategy went broke (may have recovered)

### Stop Reason
- `max_bets`: Reached bet limit (normal)
- `insufficient_balance`: Went broke
- `strategy_stopped`: Strategy decided to stop
- `take_profit`: Reached profit target

## Interpreting Ranks

**🥇 Rank 1-3**: Top performing strategies
- Best profit %
- Good candidates for live betting
- Check max balance and busts too!

**Middle Ranks**: Moderate performance
- May be suitable depending on risk tolerance
- Compare win rates and volatility

**Bottom Ranks**: Poor performers
- Lost significant amount
- High risk of bust
- Avoid or adjust parameters

## Tips

### For Meaningful Comparisons
1. **Use enough bets**: 500-1000+ recommended
2. **Same seed**: Ensures fairness (default: 42)
3. **Adequate balance**: Start with 1.0+ to avoid early busts
4. **Multiple runs**: Try different seeds to see consistency

### Choosing a Strategy
1. Look at **profit %** first
2. Check **bust count** (lower is safer)
3. Consider **max balance** (upside potential)
4. Review **avg bet size** (risk level)
5. Read stop reason (how it ended)

### Red Flags 🚩
- Busts > 0 (went broke at least once)
- -100% profit (total loss)
- Very high max bet size (risky)
- Stop reason: insufficient_balance

### Green Flags ✅
- Positive profit %
- 0 busts
- Consistent win rate
- Stop reason: max_bets or take_profit

## Skipped Strategies

Some strategies require special configuration:
- `custom-script`: Needs script path
- `faucet-grind`: Requires specific setup

These will be marked as "Skipped" in the report.

## Performance

Execution time varies by settings:

| Bets | Strategies | Time (approx) |
|------|-----------|---------------|
| 100  | 16        | ~10 seconds   |
| 500  | 16        | ~30 seconds   |
| 1000 | 16        | ~60 seconds   |
| 5000 | 16        | ~5 minutes    |

*Simulation runs at maximum speed (no delays)*

## Technical Details

### Simulation
- Uses `dry_run=True` mode
- MockDuckDiceAPI for fast simulation
- No network calls (100% local)
- Reproducible with fixed seed

### Fair Comparison
- Same starting balance for all
- Same max bets limit for all
- Same random seed for all
- Same stop loss/take profit for all
- Identical conditions = fair test

### Data Collection
- Tracks every bet
- Records balance history (every 10 bets)
- Calculates comprehensive metrics
- Detects busts (balance ≤ 0.0001)

## Troubleshooting

### Report Doesn't Open
- Use full file path: `file:///path/to/strategy_comparison.html`
- Or open directly in browser: drag & drop HTML file

### All Strategies Bust
- Increase starting balance: `-b 10.0`
- Reduce max bets: `-n 100`
- Strategies may be too aggressive for small bankroll

### Different Results Each Run
- Not using same seed
- Fix with: `-s 42` (or any number)
- Same seed = identical results

### Takes Too Long
- Reduce max bets: `-n 100`
- Each bet processes quickly, but 16 strategies × 1000 bets = 16,000 total bets

## Advanced Usage

### Compare Different Conditions

```bash
# Conservative test (small risk)
python3 strategy_comparison.py -b 100.0 -n 100 -o conservative.html

# Moderate test (balanced)
python3 strategy_comparison.py -b 10.0 -n 500 -o moderate.html

# Aggressive test (high risk)
python3 strategy_comparison.py -b 1.0 -n 2000 -o aggressive.html
```

### Batch Comparisons

```bash
# Test multiple seeds for consistency
for seed in 42 100 200 300 400; do
    python3 strategy_comparison.py -s $seed -o "report_seed_$seed.html"
done
```

### Find Best Strategy

```bash
# Run comprehensive test
python3 strategy_comparison.py -b 10.0 -n 5000 -o best_strategy.html

# Open report and look at:
# 1. Highest profit % (rank 1)
# 2. Zero busts
# 3. Reasonable win rate
# 4. Max balance > starting balance
```

## Files Generated

- `strategy_comparison.html` - Main report (default)
- Custom output file (if specified with `-o`)
- Self-contained (includes Chart.js inline)
- Can be shared/archived

## Integration

### Add to CI/CD
```bash
# Run comparison as part of testing
python3 strategy_comparison.py -n 100 -o ci_report.html
# Parse results to fail build if all strategies bust
```

### Automated Testing
```bash
# Nightly comparison
0 2 * * * cd /path/to/duckdice-bot && ./compare_strategies.sh 10.0 1000 daily_$(date +\%Y\%m\%d).html
```

## Version

Compatible with DuckDice Bot v4.7.1+

## See Also

- `USER_GUIDE.md` - General bot usage
- `STREAK_HUNTER_GUIDE.md` - Specific strategy guide
- `PARAMETERS_GUIDE.md` - Strategy parameters

---

**Pro Tip**: Run multiple comparisons with different starting balances to see how strategies perform under different bankroll conditions!
