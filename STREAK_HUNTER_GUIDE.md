# Streak Hunter Strategy

## Overview

The **Streak Hunter** strategy is designed to capitalize on winning streaks at low probability (14% chance) by using a **decreasing multiplier system** that manages risk while maximizing profit potential.

## Core Concept

- **Hunt for streaks** at 14% win chance (~7x payout)
- **Conservative base bet**: max(min_bet, balance/300)
- **Increasing bets on wins** with decreasing multipliers
- **Reset to base** on any loss
- **Perfect for**: Players who want excitement with controlled risk

## How It Works

### Betting Pattern

| Win # | Multiplier | Bet Amount |
|-------|------------|------------|
| Base (0) | 1.0x | Base bet |
| Win 1 | 2.0x | Base bet × 2.0 (200%) |
| Win 2 | 1.8x | Base bet × 1.8 (180%) |
| Win 3 | 1.6x | Base bet × 1.6 (160%) |
| Win 4 | 1.4x | Base bet × 1.4 (140%) |
| Win 5 | 1.2x | Base bet × 1.2 (120%) |
| Win 6 | 1.0x | Base bet × 1.0 (100%) |
| Win 7+ | 0.8x → 0.5x | Continues decreasing (floor at 0.5x) |
| **Loss** | **RESET** | **Back to base bet** |

### Example Session

```
Starting balance: 100 BTC
Base bet: 100/300 = 0.333 BTC

Bet 1: 0.333 BTC @ 14% → LOSS → Balance: 99.667
Bet 2: 0.333 BTC @ 14% → WIN +2.0 BTC → Balance: 101.667
Bet 3: 0.667 BTC @ 14% (0.333 × 2.0) → WIN +4.0 BTC → Balance: 105.667
Bet 4: 0.600 BTC @ 14% (0.333 × 1.8) → WIN +3.6 BTC → Balance: 109.267
Bet 5: 0.533 BTC @ 14% (0.333 × 1.6) → LOSS → Balance: 108.734
Bet 6: 0.362 BTC @ 14% → ... (reset to base: 108.734/300)
```

## Parameters

All parameters are customizable:

```bash
-P chance=14                # Win chance % (default 14)
-P is_high=true            # Bet High or Low
-P min_bet=0.00000100      # Minimum bet amount
-P balance_divisor=300     # Base bet = balance/this
-P first_multiplier=2.0    # 1st win multiplier
-P second_multiplier=1.8   # 2nd win multiplier
-P third_multiplier=1.6    # 3rd win multiplier
-P multiplier_decrease=0.2 # Decrease per win after 3rd
-P min_multiplier=0.5      # Floor for decreasing
```

## Usage Examples

### Default (As Designed)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s streak-hunter \
  -c btc \
  --max-bets 100 \
  --stop-loss -0.3 \
  --take-profit 0.5
```

### Conservative (Lower Risk)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s streak-hunter \
  -c btc \
  -P min_bet=0.001 \
  -P balance_divisor=500 \
  -P first_multiplier=1.5 \
  -P second_multiplier=1.3 \
  -P third_multiplier=1.2 \
  --stop-loss -0.2 \
  --max-bets 200
```

### Aggressive (Higher Risk/Reward)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s streak-hunter \
  -c btc \
  -P balance_divisor=200 \
  -P first_multiplier=2.5 \
  -P second_multiplier=2.2 \
  -P third_multiplier=2.0 \
  --stop-loss -0.4 \
  --take-profit 1.0 \
  --max-bets 50
```

### Different Win Chance

```bash
# Try 10% chance (~10x payout)
python3 duckdice_cli.py run \
  -s streak-hunter \
  -m simulation \
  -P chance=10 \
  -P balance_divisor=400
```

## Strategy Features

### ✅ Advantages

1. **Conservative Base Bet**: Only risks 1/300th of balance by default
2. **Decreasing Multipliers**: Prevents runaway exponential growth
3. **Quick Reset**: One loss resets everything (capital preservation)
4. **Streak Tracking**: Shows current streak and multipliers
5. **Flexible Parameters**: Customize every aspect
6. **Works at 14%**: Optimized for ~7x payout sweet spot

### ⚠️ Considerations

1. **Streak Dependency**: Needs winning streaks to profit
2. **High Variance**: 14% win chance means long dry spells
3. **Reset Risk**: Single loss wipes streak progress
4. **Not Martingale**: Doesn't chase losses (safer but needs wins)

## Session Output

When running, you'll see:

```
🎯 Streak Hunter Strategy Started
   Target chance: 14%
   Base bet: 0.33333333
   Win multipliers: 2.0x → 1.8x → 1.6x → ...
   Reset on: Any loss

🔥 On 2-win streak! Next multiplier: 1.8x
🎉 3-win streak! Profit multiplier now 1.6x
🚀 5-win streak! Amazing! Multiplier: 1.2x
💎 7-win streak! Legendary! Multiplier: 0.8x

❌ Streak ended at 3 wins. Resetting to base bet.

🎯 Streak Hunter Session Summary:
   Total bets: 50
   Wins: 7
   Win rate: 14.00%
   Max streak achieved: 3
   ✨ Nice! You got a 3-win streak!
```

## Mathematical Analysis

### Expected Streaks at 14% Chance

| Streak Length | Probability | Expected Every N Bets |
|---------------|-------------|----------------------|
| 1 win | 14.0% | 7 bets |
| 2 wins | 2.0% | 50 bets |
| 3 wins | 0.27% | 370 bets |
| 4 wins | 0.038% | 2,640 bets |
| 5 wins | 0.0053% | 18,900 bets |

### Why Decreasing Multipliers?

1. **Risk Management**: Prevents bet size from growing too fast
2. **Sustainability**: Can survive longer dry spells
3. **Psychological**: Less devastating when streak breaks
4. **Mathematical**: Still profitable without excessive risk

### Base Bet Formula

```
base_bet = max(min_bet, current_balance / balance_divisor)
```

- Adapts to current balance
- Never goes below min_bet
- Automatically scales up/down with balance changes

## Risk Management

### Recommended Settings

**Conservative (Low Risk)**
```bash
-P balance_divisor=500
-P first_multiplier=1.3
--stop-loss -0.15
--max-bets 200
```

**Moderate (Medium Risk)**
```bash
-P balance_divisor=300
-P first_multiplier=2.0
--stop-loss -0.25
--max-bets 100
```

**Aggressive (High Risk)**
```bash
-P balance_divisor=200
-P first_multiplier=2.5
--stop-loss -0.40
--max-bets 50
```

### Always Use Limits!

- `--stop-loss`: Prevent catastrophic losses
- `--take-profit`: Lock in wins when lucky
- `--max-bets`: Prevent endless sessions
- `--max-losses`: Stop after bad runs

## Comparison with Other Strategies

| Feature | Streak Hunter | Martingale | Fibonacci |
|---------|--------------|------------|-----------|
| Chase losses | ❌ No | ✅ Yes | ✅ Yes |
| Reset on loss | ✅ Yes | ❌ No | ❌ No |
| Win probability | 14% (low) | 49%+ (high) | 49%+ (high) |
| Multiplier pattern | Decreasing | Fixed 2x | Sequence |
| Risk level | Medium-High | Very High | Medium |
| Capital preservation | ✅ Good | ❌ Poor | ⚠️ Fair |

## Tips & Best Practices

### 🎯 Strategy Tips

1. **Set Take-Profit**: If you hit 3+ win streak, strongly consider cashing out
2. **Track Streaks**: The strategy shows max streak - aim for 2-3 wins
3. **Adjust Divisor**: Higher divisor = safer, lower = more aggressive
4. **Use Stop-Loss**: 14% means variance - protect your bankroll
5. **Session Limits**: Don't let it run indefinitely

### 💡 Parameter Tuning

**Want less variance?**
- Increase `balance_divisor` (400-500)
- Decrease multipliers (1.5, 1.3, 1.2)
- Lower `chance` to 10-12%

**Want more action?**
- Decrease `balance_divisor` (200-250)
- Increase multipliers (2.5, 2.2, 2.0)
- Raise `chance` to 20-25%

### ⚠️ Common Mistakes

1. **Chasing streaks too long** - Take profit at 3-4 wins
2. **No stop-loss** - Always set limits!
3. **Too aggressive divisor** - Start conservative
4. **Ignoring variance** - 14% means long dry spells are normal

## Show Strategy Details

```bash
python3 duckdice_cli.py show streak-hunter
```

Displays:
- Full parameter list with defaults
- Risk assessment
- Pros and cons
- Usage tips
- Example commands

## Advanced: Custom Progression

You can create custom multiplier progressions:

### Flat Multiplier
```bash
-P first_multiplier=1.5 \
-P second_multiplier=1.5 \
-P third_multiplier=1.5 \
-P multiplier_decrease=0
```

### Aggressive Start, Safe Later
```bash
-P first_multiplier=3.0 \
-P second_multiplier=2.0 \
-P third_multiplier=1.5 \
-P multiplier_decrease=0.3
```

### Conservative Throughout
```bash
-P first_multiplier=1.2 \
-P second_multiplier=1.1 \
-P third_multiplier=1.05 \
-P multiplier_decrease=0.05
```

## Testing Workflow

### 1. Test in Simulation
```bash
python3 duckdice_cli.py run -s streak-hunter -m simulation --max-bets 100
```

### 2. Observe Patterns
- Note max streak achieved
- Check win rate (should be ~14%)
- Watch balance volatility

### 3. Adjust Parameters
Based on results, tune:
- `balance_divisor` for risk
- Multipliers for aggression
- Limits for safety

### 4. Live Testing (Faucet)
```bash
python3 duckdice_cli.py run -s streak-hunter -m live-faucet -k API_KEY
```

## Summary

✅ **Hunt streaks** at 14% chance  
✅ **Decreasing multipliers** (2.0x → 1.8x → 1.6x → ...)  
✅ **Conservative base** (balance/300)  
✅ **Reset on loss** (capital preservation)  
✅ **Flexible parameters** (fully customizable)  
✅ **Risk managed** (decreasing prevents exponential growth)  

**Best for**: Players who want excitement of hunting streaks with smart risk management.

**Not for**: Players expecting consistent steady profits (high variance strategy).

---

**See Also**:
- PARAMETERS_GUIDE.md
- CLI_GUIDE.md
- QUICK_REFERENCE.md
