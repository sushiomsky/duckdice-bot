# Quick Reference: Strategy Consolidation & Monte Carlo

## New Features

### 1. Run Monte Carlo Simulations

```bash
# Simple simulation
duckdice simulate -s adaptive-hunter -r 5000

# With custom config
duckdice simulate -s unified-progression \
  -c '{"progression_type":"fibonacci","base_bet":"0.00001"}'

# Interactive configuration
duckdice simulate -s unified-martingale -I

# With reports and plots
duckdice simulate -s unified-exponential \
  -r 10000 -b 500 \
  --report report.html \
  --plots plots/exp
```

### 2. Consolidated Strategies

#### Adaptive Hunter (12 in 1)
```bash
# Cold number hunting
duckdice run -s adaptive-hunter -P hunt_type=cold_number

# Streak hunting
duckdice run -s adaptive-hunter -P hunt_type=streak

# Dynamic phase hunting
duckdice run -s adaptive-hunter -P hunt_type=dynamic_phase
```

#### Unified Progression (3 in 1)
```bash
# Fibonacci
duckdice run -s unified-progression -P progression_type=fibonacci

# D'Alembert
duckdice run -s unified-progression -P progression_type=dalembert

# Labouchere
duckdice run -s unified-progression -P progression_type=labouchere
```

#### Unified Martingale (2 in 1)
```bash
# Classic martingale
duckdice run -s unified-martingale -P martingale_type=classic

# Anti-martingale
duckdice run -s unified-martingale -P martingale_type=anti
```

#### Unified Exponential (2 in 1)
```bash
# Aggressive (300x target)
duckdice run -s unified-exponential -P safe_mode=False

# Safe (100x target)
duckdice run -s unified-exponential -P safe_mode=True
```

#### Unified Faucet (2 in 1)
```bash
# Conservative grinding
duckdice run -s unified-faucet -P faucet_mode=cashout

# Aggressive all-in
duckdice run -s unified-faucet -P faucet_mode=grind
```

## Configuration Examples

### Monte Carlo - Fibonacci Progression
```bash
duckdice simulate -s unified-progression \
  -c '{
    "progression_type": "fibonacci",
    "base_bet": "0.000001",
    "chance": "49.5",
    "max_level": 15
  }' \
  -r 10000 \
  --report fibonacci_report.html
```

### Monte Carlo - Cold Number Hunter
```bash
duckdice simulate -s adaptive-hunter \
  -c '{
    "hunt_type": "cold_number",
    "threshold": 0.5,
    "base_bet_pct": 0.01,
    "loss_multiplier": 1.06
  }' \
  -r 5000 -b 100
```

### Monte Carlo - Anti Martingale
```bash
duckdice simulate -s unified-martingale \
  -c '{
    "martingale_type": "anti",
    "base_bet": "0.00001",
    "multiplier": 2.0,
    "max_multiplier": 32.0
  }' \
  -r 2000 \
  --plots anti_mart
```

## Understanding Simulation Results

### Key Metrics
- **Win Rate**: % of winning bets
- **ROI**: Return on Investment as percentage
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return (higher = better)
- **Confidence Interval**: 95% bounds on final balance

### Interpretation
- ROI > 0% = Profitable strategy
- Max Drawdown < 20% = Good risk management
- Sharpe Ratio > 0.5 = Favorable risk/return
- Win Rate > house edge (~1%) = Positive expectancy

## Troubleshooting

### Missing matplotlib
```bash
pip install matplotlib seaborn
```

### Strategy not found
```bash
# List all strategies
duckdice strategies

# Show details of a strategy
duckdice show adaptive-hunter
```

### Invalid JSON config
```bash
# Use single quotes, escape internal quotes
duckdice simulate -s unified-progression \
  -c '{"progression_type":"fibonacci"}'
```

## File Structure

```
src/betbot_strategies/
├── adaptive_hunter.py          # 12 hunters consolidated
├── unified_progression.py      # 3 progressions consolidated
├── unified_martingale.py       # 2 martingales consolidated
├── unified_exponential.py      # 2 exponentials consolidated
├── unified_faucet.py           # 2 faucets consolidated
└── deprecated/                 # Historical reference
    ├── cold_number_hunter.py
    ├── fibonacci.py
    └── ... (18 more legacy files)

src/betbot_engine/
├── monte_carlo.py              # New: Simulation engine
├── visualization.py            # New: Plotting & reports
└── ...
```

## API Usage (Python)

```python
from src.betbot_engine.monte_carlo import MonteCarloEngine
from src.betbot_engine.visualization import (
    plot_equity_curve, generate_html_report
)
from src.betbot_strategies import get_strategy

# Create engine
engine = MonteCarloEngine()

# Run simulation
result = engine.simulate(
    strategy_class=get_strategy('unified-progression'),
    config={'progression_type': 'fibonacci', 'base_bet': '0.000001'},
    rounds=10000,
    starting_balance=100.0,
    win_probability=0.495
)

# Display summary
print(result.summary())

# Generate report
generate_html_report([result], ['Fibonacci'], 'report.html')

# Plot equity curve
plot_equity_curve([result], ['Fibonacci'], 'equity.png')
```

## Best Practices

1. **Always simulate before deploying**
   ```bash
   duckdice simulate -s your-strategy -I --report report.html
   ```

2. **Test multiple configurations**
   ```bash
   duckdice simulate -s adaptive-hunter -P hunt_type=cold_number
   duckdice simulate -s adaptive-hunter -P hunt_type=streak
   duckdice simulate -s adaptive-hunter -P hunt_type=volatility
   ```

3. **Use adequate sample size**
   - 1000 rounds: Quick test
   - 5000 rounds: Reasonable estimate
   - 10000+ rounds: High confidence

4. **Review all metrics**
   - Check ROI, win_rate, max_drawdown
   - Look at confidence intervals
   - Consider Sharpe ratio

5. **Interactive parameters for tuning**
   ```bash
   duckdice simulate -s your-strategy -I
   ```

## Migration Guide (for existing users)

All original strategies still work:
- `cold-number-hunter` → Use `adaptive-hunter` with `hunt_type=cold_number`
- `fibonacci` → Use `unified-progression` with `progression_type=fibonacci`
- `classic-martingale` → Use `unified-martingale` with `martingale_type=classic`
- `micro-exponential` → Use `unified-exponential` with `safe_mode=False`
- `faucet-cashout` → Use `unified-faucet` with `faucet_mode=cashout`

No changes needed to existing profiles - they will continue to work!
