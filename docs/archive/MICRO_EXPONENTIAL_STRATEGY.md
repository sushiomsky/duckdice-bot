# Micro Exponential Growth Strategy - Implementation Complete

## Overview

Successfully implemented the **Micro Balance Exponential Growth Engine** - an extremely aggressive betting strategy designed to turn dust balances into 100x+ gains through asymmetric volatility exploitation.

## Strategy Details

### Purpose
Turn micro balances (<$1) into 300x gains using adaptive multi-mode betting and volatility learning.

### Risk Profile
- **Risk Level**: EXTREME
- **Bankroll Required**: Micro (<$1)
- **Volatility**: Extreme
- **Max Drawdown**: 45%
- **Target**: 300x profit

### Betting Modes

The strategy dynamically switches between 5 different modes:

1. **PROBE** (60% chance)
   - Low-risk data collection
   - 0.5x base bet size
   - Used for safe pattern learning

2. **PRESSURE** (18% chance)
   - Loss clustering exploitation
   - Martingale scaling (1.3x per loss)
   - Capped at 25% of balance

3. **HUNT** (0.08-0.20% chance)
   - Asymmetric long-shot engine
   - Random ultra-low chances
   - Base bet sizing

4. **CHAOS** (5-70% chance)
   - Entropy forcing with randomness
   - Random chance and bet size
   - Up to 30% of balance

5. **KILL** (0.08-0.25% chance)
   - Explosion mode
   - 65% of balance on single bet
   - Only activates under specific conditions

### Adaptive Features

**Volatility Learning**
- Tracks last 40 results (configurable)
- Calculates volatility score (0-1)
- Higher score = more predictable patterns
- Influences strategy selection

**Dynamic Base Bet Adjustment**
- Starts at 0.2% of balance
- Reduces to 0.1% at 20x profit
- Reduces to 0.05% at 50x profit
- Automatic de-risking as balance grows

**Strategy Switching Logic**
- Cooldown: 10 bets between switches
- Weighted probabilities based on conditions:
  - Loss streak ≥6: +40 weight to PRESSURE
  - Win streak ≥3: +30 weight to HUNT
  - Volatility >0.6: +40 weight to CHAOS
  - Drawdown >25%: +60 weight to PROBE

**KILL Mode Activation**
Requires ALL conditions:
- Volatility score >0.72
- Drawdown <20%
- Cooldown elapsed (120 bets)
- 12% random chance

## Parameters

```python
{
    'base_bet_percent': '0.01',        # 1% for balances <$1, 0.2% for larger
    'min_bet': '0.001',                # 0.001 (suitable for USDT/BTC/ETH)
    'max_bet_percent': '0.90',         # Can bet up to 90%
    'profit_target_x': '300',          # Stop at 300x
    'max_drawdown_percent': '45',      # Accept 45% drawdown
    'kill_chance_min': '0.08',         # 0.08% min for KILL
    'kill_chance_max': '0.25',         # 0.25% max for KILL
    'kill_bet_percent': '0.65',        # 65% of balance in KILL
    'kill_cooldown': '120',            # 120 bets between KILL attempts
    'vol_window': '40',                # Window for volatility calc
    'switch_cooldown_bets': '10'       # Bets before strategy switch
}
```

**Note**: The strategy automatically adjusts `base_bet_percent` to 1% for balances under $1 to ensure bets meet minimum bet requirements.

## Usage

### Command Line
```bash
python duckdice_cli.py \
  --strategy micro-exponential \
  --symbol TRX \
  --base-bet-percent 0.002 \
  --profit-target-x 300
```

### Python API
```python
from betbot_engine.engine import AutoBetEngine, EngineConfig
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig

# Configure
api_config = DuckDiceConfig(api_key="YOUR_API_KEY")
api = DuckDiceAPI(api_config)

engine_config = EngineConfig(
    symbol="TRX",
    dry_run=False,  # Set to True for simulation
    max_bets=None,
    stop_loss=None,  # Strategy manages risk internally
    take_profit=None
)

engine = AutoBetEngine(api, engine_config)

# Run
summary = engine.run(
    strategy_name="micro-exponential",
    params={
        'base_bet_percent': '0.002',
        'profit_target_x': '300'
    }
)
```

## Warnings

⚠️ **EXTREME RISK STRATEGY**

This strategy is:
- **NOT** for conservative players
- **NOT** for significant balances
- **NOT** guaranteed to work
- Designed for DUST RECOVERY ONLY

Characteristics:
- Accepts deep drawdowns (up to 45%)
- Uses very aggressive betting in KILL mode
- High variance - can bust quickly
- Requires favorable volatility patterns
- Best for amounts you can afford to lose completely

## Test Results

Strategy successfully:
- ✅ Loads and registers correctly
- ✅ Initializes with all parameters
- ✅ Executes in simulation mode
- ✅ Implements all 5 betting modes
- ✅ Tracks volatility and adapts
- ✅ Switches strategies based on conditions
- ✅ Calculates bet sizes correctly
- ✅ Integrates with existing engine

## Files

- **Implementation**: `src/betbot_strategies/micro_exponential.py` (280 lines)
- **Test Script**: `test_micro_exponential.py`
- **Documentation**: This file

## Strategy Count

Total strategies now: **19**
- Previously: 18
- Added: `micro-exponential`

## Recommendations

### Best Use Cases
1. Dust balance recovery (<$0.10)
2. Experimental sessions with small amounts
3. High-risk tolerance users
4. Learning about adaptive strategies

### Not Recommended For
1. Main bankroll management
2. Conservative players
3. Balances over $1
4. Emotional attachment to funds

### Tips for Use
1. Start with absolute dust amounts
2. Set strict loss limits
3. Don't expect consistent results
4. Treat as experimental/entertainment
5. Never bet more than you can lose

## Technical Implementation

### Code Structure
- Clean Python implementation
- Follows existing strategy pattern
- No external dependencies
- Well-documented modes
- Type hints throughout

### Integration
- Registered with strategy registry
- Compatible with all interfaces (CLI, GUI, Web)
- Works in simulation mode
- Supports all standard parameters
- Event-driven architecture ready

## Conclusion

The Micro Exponential Growth Engine is now fully implemented and ready for use. It represents an extreme approach to micro-balance recovery, trading safety for the potential of asymmetric gains.

**Use responsibly and only with funds you can afford to lose completely.**

---

**Implementation Date**: January 15, 2025  
**Status**: ✅ Complete and Tested  
**Strategy ID**: `micro-exponential`
