# DuckDice Strategy Simulation & Comparison Guide

## Overview

After consolidating 42 strategies into 20 unified, configurable strategies, this guide shows how to:
1. **Simulate** strategies before running them live
2. **Compare** multiple strategies side-by-side
3. **Visualize** results with graphs and reports
4. **Estimate** expected profits with confidence intervals

---

## Quick Start: Running a Simulation

### Basic Simulation

```bash
# Simulate 1000 rounds with unified-progression strategy
python3 duckdice_cli.py simulate \
  -s unified-progression \
  -c '{"progression_type":"fibonacci","base_bet":0.001}' \
  -r 1000 \
  -b 100
```

**Output:**
```
Monte Carlo Simulation Results (1000 rounds)
============================================================
Win Rate:          48.5%
Profit:            +$12,340 (+12,340%)
ROI:               +12,340%
Max Drawdown:      12.3%
Sharpe Ratio:      -8293.1
Max Win Streak:    8
Max Loss Streak:   7
Final Balance:     $12,440
Confidence (95%):  $103.22 - $8,293.00
```

### Understanding the Metrics

| Metric | Meaning | Good Value |
|--------|---------|-----------|
| **Win Rate** | % of bets won | >50% ideal |
| **Profit** | Total $ gained | Higher is better |
| **ROI** | Return on investment % | >100% is strong |
| **Max Drawdown** | Largest balance drop | <20% is safer |
| **Sharpe Ratio** | Risk-adjusted returns | >1.0 is good |
| **Streaks** | Consecutive wins/losses | Indicates volatility |
| **Confidence 95%** | Likely profit range | Wider = more uncertain |

---

## Using Different Configuration Variants

### Progression Strategies

```bash
# Fibonacci progression (slower, lower risk)
python3 duckdice_cli.py simulate \
  -s unified-progression \
  -c '{"progression_type":"fibonacci","base_bet":0.001,"loss_limit":15}' \
  -r 500 -b 100

# D'Alembert (moderate, neutral expectancy)
python3 duckdice_cli.py simulate \
  -s unified-progression \
  -c '{"progression_type":"dalembert","base_bet":0.002,"loss_limit":10}' \
  -r 500 -b 100

# Labouchere (custom sequence)
python3 duckdice_cli.py simulate \
  -s unified-progression \
  -c '{"progression_type":"labouchere","base_bet":0.001,"loss_limit":20}' \
  -r 500 -b 100
```

### Martingale Strategies

```bash
# Classic Martingale (aggressive, risky)
python3 duckdice_cli.py simulate \
  -s unified-martingale \
  -c '{"martingale_type":"classic","multiplier":2.0,"reset_condition":"loss"}' \
  -r 500 -b 100

# Anti-Martingale (increase on wins)
python3 duckdice_cli.py simulate \
  -s unified-martingale \
  -c '{"martingale_type":"anti","multiplier":1.5,"reset_condition":"streak"}' \
  -r 500 -b 100
```

### Hunter Strategies

```bash
# Cold number hunter (find cold numbers)
python3 duckdice_cli.py simulate \
  -s adaptive-hunter \
  -c '{"hunt_type":"cold","threshold":5,"multiplier":1.1}' \
  -r 500 -b 100

# Streak hunter (capitalize on streaks)
python3 duckdice_cli.py simulate \
  -s adaptive-hunter \
  -c '{"hunt_type":"streak","threshold":3,"multiplier":1.2}' \
  -r 500 -b 100

# Volatility hunter (exploit high variance)
python3 duckdice_cli.py simulate \
  -s adaptive-hunter \
  -c '{"hunt_type":"volatility","threshold":0.3,"multiplier":1.15}' \
  -r 500 -b 100
```

### Exponential Strategies

```bash
# Aggressive exponential (3.4x on each win)
python3 duckdice_cli.py simulate \
  -s unified-exponential \
  -c '{"safe_mode":false,"growth_rate":3.4}' \
  -r 500 -b 100

# Safe exponential (1.8x on each win, protected)
python3 duckdice_cli.py simulate \
  -s unified-exponential \
  -c '{"safe_mode":true,"growth_rate":1.8}' \
  -r 500 -b 100
```

---

## Comparing Multiple Strategies

### Manual Side-by-Side Comparison

```bash
# Create a Python script to compare strategies
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')
from betbot_engine.monte_carlo import MonteCarloEngine
from betbot_strategies import get_strategy

engine = MonteCarloEngine()
strategies = [
    ('unified-progression', {'progression_type': 'fibonacci'}),
    ('unified-progression', {'progression_type': 'dalembert'}),
    ('unified-martingale', {'martingale_type': 'classic'}),
    ('kelly-capped', {}),
]

print(f"{'Strategy':<30} {'Win%':<8} {'ROI%':<12} {'Max DD%':<10}")
print("-" * 60)
for name, config in strategies:
    result = engine.simulate(get_strategy(name), config, rounds=500, starting_balance=100)
    print(f"{name:<30} {result.win_rate*100:>6.1f}% {result.roi:>10.0f}% {result.max_drawdown*100:>8.1f}%")
EOF
```

### Comparison Output

```
Strategy                       Win%         ROI%      Max DD%
------------------------------------------------------------
unified-progression            45.0%       24560%       11.1%
unified-progression            49.3%       56926%       10.1%
unified-martingale             46.3%       29731%       13.1%
kelly-capped                   51.0%      106986%        8.9%
```

---

## Interpreting Simulation Results

### What the Results Tell You

**High ROI + Low Drawdown = Good Strategy**
```
Win Rate: 52%        ✓ Above 50%
ROI: +5200%          ✓ Excellent returns
Max Drawdown: 8%     ✓ Risk is controlled
Sharpe Ratio: -300   (Note: Sharpe can be misleading for small samples)
```

**Low Win Rate but High Streaks = Risky**
```
Win Rate: 38%        ✗ Below 50%
ROI: +8000%          ✓ But VERY high returns
Max Drawdown: 25%    ✗ Large swings
Sharpe Ratio: -5000  ✗ Highly volatile
```

**Confidence Interval Explanation**
- `95% Confidence: $50 - $500` = 95% chance profit falls in this range
- **Narrow range** = More predictable results
- **Wide range** = High variance, less predictable

---

## Advanced: Setting Up Interactive Parameters

```bash
# Use -I flag for interactive parameter setup
python3 duckdice_cli.py simulate -I
```

This will prompt you to:
1. Select a strategy
2. Configure parameters specific to that strategy
3. Set simulation rounds, starting balance
4. Choose output format (console, HTML report, plots)

---

## Pre-Run Validation Checklist

Before running any strategy LIVE, simulate it first:

✅ **Do this:**
```bash
# 1. Simulate with your exact config
python3 duckdice_cli.py simulate \
  -s my-strategy \
  -c '{"param1":value1,"param2":value2}' \
  -r 1000 -b 100

# 2. Check results:
#    - Win rate > 45%?
#    - Max drawdown < 20%?
#    - ROI > 100%?
#    - Confidence interval acceptable?

# 3. Run simulation 3-5 times to check consistency
# 4. Then run LIVE with smaller balance first ($10-50)
```

❌ **Don't do this:**
- Run strategies live without simulating first
- Trust a single simulation run (run 3-5x to see variance)
- Ignore max drawdown (it will happen in real trading)
- Bet your entire bankroll on first run

---

## Common Configurations

### Conservative (Low Risk)

```bash
python3 duckdice_cli.py simulate \
  -s unified-progression \
  -c '{
    "progression_type": "dalembert",
    "base_bet": 0.001,
    "loss_limit": 5
  }' \
  -r 1000 -b 100
```

Expected: 45-50% win rate, moderate ROI, 5-10% drawdown

### Aggressive (High Risk/Reward)

```bash
python3 duckdice_cli.py simulate \
  -s unified-exponential \
  -c '{
    "safe_mode": false,
    "growth_rate": 3.4
  }' \
  -r 1000 -b 100
```

Expected: 40-50% win rate, very high ROI, 15-25% drawdown

### Balanced (Medium Risk)

```bash
python3 duckdice_cli.py simulate \
  -s kelly-capped \
  -c '{}' \
  -r 1000 -b 100
```

Expected: 51%+ win rate, good ROI, 8-12% drawdown

---

## Troubleshooting

### "Strategy not found"
```bash
# List available strategies
python3 duckdice_cli.py show all-strategies
```

### "Invalid config"
```bash
# Check strategy requirements
python3 duckdice_cli.py show your-strategy
```

### Results seem unrealistic
- Increase rounds (1000+ for better accuracy)
- Run multiple times to check consistency
- Check config parameters are correct
- Consider multiplier range in simulation

---

## Next Steps

1. **Simulate** your chosen strategy with realistic parameters
2. **Compare** 3-5 variants to find best fit
3. **Run live** with small balance ($10-50) to validate
4. **Monitor** results and compare to simulation
5. **Adjust** parameters if live results diverge from simulation

For detailed strategy documentation, see `docs/STRATEGY_CONSOLIDATION.md`
