# Quick Start: RNG Analysis to Bot Strategy

## What This Does

Converts your RNG analysis results into ready-to-use betting strategies for the DuckDice auto-bet engine.

## ⚠️ Warning

**Educational purposes only!** Cryptographic RNG cannot be predicted. Past patterns don't predict future outcomes. This demonstrates integration, not a winning system.

## 3-Step Process

### Step 1: Generate Strategy Configuration

```bash
cd rng_analysis
python strategy_generator.py
```

**Output:**
- `rng_strategy_config.json` - Analysis results and recommendations
- `rng_strategy_params.py` - Python configuration file

### Step 2: Review the Recommendations

```bash
cat rng_strategy_config.json
```

Look for:
- `risk_assessment.exploitability` - Usually "none" (good!)
- `ml_summary.improvement_over_baseline` - Usually <5% (expected)
- `strategy_recommendations` - Multiple strategies to try

### Step 3: Use with Auto-Bet Engine

```bash
# Test with dry run (no real bets)
python ../examples/use_rng_analysis_strategy.py --api-key YOUR_KEY --dry-run

# Test with faucet (free balance)
python ../examples/use_rng_analysis_strategy.py --api-key YOUR_KEY --faucet

# Compare all strategies
python ../examples/use_rng_analysis_strategy.py --compare
```

## Available Strategies

The generator creates 3+ strategies:

1. **Conservative** (Recommended)
   - Fibonacci progression on loss streaks
   - Safest approach
   - Best for demonstration

2. **Pattern-Adapted** (If patterns detected)
   - Uses RNG analysis insights
   - Likely won't work due to overfitting
   - Educational value only

3. **Kelly Conservative**
   - Bankroll-based sizing
   - Very conservative cap
   - Good risk management example

## Python API Usage

```python
from betbot_strategies.rng_analysis_strategy import load_strategy_from_config
from betbot_engine.engine import AutoBetEngine, EngineConfig
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig

# Load generated strategy
strategy = load_strategy_from_config('rng_strategy_config.json', strategy_index=0)

# Setup engine
api = DuckDiceAPI(DuckDiceConfig(api_key="YOUR_KEY"))
engine_config = EngineConfig(
    symbol="XLM",
    faucet=True,
    stop_loss=-0.02,
    take_profit=0.01,
    max_bets=50
)

# Run
engine = AutoBetEngine(api, engine_config)
result = engine.run(
    strategy_name=strategy['strategy_name'],
    params=strategy['params']
)
```

## What to Expect

### If RNG is Secure (Expected)
- ML improvement: <5%
- Exploitability: none
- Strategy performance: No better than random

### If You See Patterns (Unlikely)
- ML improvement: >5%
- This is likely **overfitting**
- Won't work in real betting
- Still educational!

## Understanding the Output

```json
{
  "ml_summary": {
    "improvement_over_baseline": 2.3,  // <5% = secure RNG
    "predictive_power": "low"           // Good!
  },
  "risk_assessment": {
    "exploitability": "none",           // RNG is secure
    "recommended_action": "Do not use for real betting"
  }
}
```

## Tips

1. **Always use faucet or dry-run first**
2. **Set strict limits** (stop-loss, max bets)
3. **Don't increase bet sizes** based on "patterns"
4. **Remember the house edge** is real
5. **This is educational** - not a money-making system

## Troubleshooting

**No CSV files found:**
```bash
# Check bet history directory
ls -la ../bet_history/*.csv
```

**Missing dependencies:**
```bash
pip install -r requirements_analysis.txt
```

**Strategy not working:**
- Remember: It's not supposed to beat the house edge!
- This demonstrates integration, not exploitation
- Use for learning, not profit

## More Information

- [Complete Guide](../docs/RNG_ANALYSIS_TO_STRATEGY_GUIDE.md)
- [RNG Analysis README](README.md)
- [Example Script](../examples/use_rng_analysis_strategy.py)

## Remember

**The best strategy is not to gamble, or gamble only for entertainment with money you can afford to lose.**

Cryptographic RNG is designed to be unpredictable. No amount of analysis will change that. This tool teaches you *why* that's true.
