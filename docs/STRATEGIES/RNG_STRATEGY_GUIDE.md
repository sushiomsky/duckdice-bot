# RNG Analysis Strategy - Complete Guide

## Overview

The RNG Analysis Strategy is an **educational/experimental** strategy that analyzes patterns in previous bets to make betting decisions. 

⚠️ **IMPORTANT**: This strategy is for research and learning purposes only. Cryptographic RNG (Random Number Generator) is unpredictable by design, and past patterns do NOT predict future outcomes.

## How It Works

### Pattern Detection from Previous Bets

The strategy analyzes recent bet history to detect patterns:

1. **Cold Streak Detection** - Many losses in a row (<30% win rate)
2. **Hot Streak Detection** - Many wins in a row (>70% win rate)
3. **Alternating Pattern** - Win/loss alternating frequently (>70%)

### Bet Adjustment Based on Patterns

- **Cold Streak**: Slightly increases bet size (Martingale-like)
- **Hot Streak**: Reduces bet size to preserve profits
- **Alternating**: Standard betting

### Dynamic Multiplier

- Increases after losses (by `loss_multiplier`)
- Can decrease after wins (by `win_multiplier`)
- Capped at `max_multiplier`
- Resets when recent performance is very poor

## Parameters

All parameters are customizable:

```bash
-P base_amount=0.0001          # Base bet amount
-P chance=50                   # Win chance %
-P is_high=false              # Bet High or Low
-P use_patterns=true          # Enable pattern detection
-P pattern_window=10          # Number of bets to analyze
-P loss_multiplier=1.5        # Multiplier after loss
-P win_multiplier=1.0         # Multiplier after win
-P max_multiplier=8.0         # Maximum bet multiplier
```

## Usage Examples

### Basic Usage (Pattern Detection Enabled)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s rng-analysis-strategy \
  -c btc \
  -P use_patterns=true \
  -P pattern_window=10 \
  --max-bets 100
```

### Conservative Settings

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s rng-analysis-strategy \
  -c btc \
  -P base_amount=0.00001 \
  -P use_patterns=true \
  -P pattern_window=20 \
  -P loss_multiplier=1.2 \
  -P max_multiplier=3.0 \
  --stop-loss -0.1 \
  --max-bets 200
```

### Aggressive Settings (⚠️ High Risk)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s rng-analysis-strategy \
  -c btc \
  -P base_amount=0.001 \
  -P use_patterns=true \
  -P pattern_window=5 \
  -P loss_multiplier=1.5 \
  -P max_multiplier=8.0 \
  --stop-loss -0.3 \
  --max-bets 50
```

### Without Pattern Detection (Simple Martingale)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s rng-analysis-strategy \
  -c btc \
  -P use_patterns=false \
  -P loss_multiplier=2.0 \
  --max-bets 100
```

## Testing Pattern Detection

### Verify It's Working

Run a session and look for pattern detection messages:

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s rng-analysis-strategy \
  -c btc \
  -P use_patterns=true \
  -P pattern_window=10 \
  --max-bets 30
```

You should see output like:
```
📊 Pattern detected: cold_streak (multiplier: 3.50x)
📊 Pattern detected: hot_streak (multiplier: 1.20x)
```

### Session Summary

At the end, you'll see:
```
📊 RNG Analysis Strategy Session Summary:
   Total bets: 30
   Win rate: 45.00%
   Longest win streak: 4
   Longest loss streak: 6
   Final multiplier: 2.40x
   Reason: max_bets
```

## How Pattern Detection Works

### 1. Data Collection

The strategy maintains a sliding window of recent bet results:
- Configurable size via `pattern_window` parameter
- Default: 10 most recent bets
- Stored in `ctx.recent_results`

### 2. Pattern Analysis

Every bet, the strategy analyzes the window:

```python
def _detect_pattern(self):
    """Detect patterns in recent results"""
    recent = list(self.ctx.recent_results)[-self.pattern_window:]
    
    # Calculate win rate
    wins = sum(1 for r in recent if r.get('win', False))
    win_rate = wins / len(recent)
    
    # Detect patterns
    if win_rate > 0.70:  # Hot streak
        return 'hot_streak'
    elif win_rate < 0.30:  # Cold streak
        return 'cold_streak'
    elif alternating_rate > 0.70:  # Alternating
        return 'alternating'
    
    return None
```

### 3. Bet Adjustment

Based on detected pattern:

```python
def _adjust_bet_size(self, pattern):
    """Adjust bet based on pattern"""
    amount = self.base_amount * self._current_multiplier
    
    if pattern == 'cold_streak':
        amount *= 1.2  # Increase 20%
    elif pattern == 'hot_streak':
        amount *= 0.8  # Decrease 20%
    
    # Cap at max_multiplier
    max_amount = self.base_amount * self.max_multiplier
    return min(amount, max_amount)
```

## Strategy Logic Flow

```
Start Bet
    ↓
Check if enough history? (>= pattern_window)
    ↓
  YES → Analyze patterns
    ↓
Pattern detected? (cold/hot/alternating)
    ↓
  YES → Adjust bet size accordingly
    ↓
Calculate bet amount (base_amount × multiplier)
    ↓
Place bet
    ↓
Update multiplier based on result:
  - Win: × win_multiplier
  - Loss: × loss_multiplier
    ↓
Add result to history window
    ↓
Check if recent performance very poor?
    ↓
  YES → Reset multiplier to 1.0
    ↓
Next Bet
```

## Educational Value

This strategy demonstrates:

✅ **Pattern Recognition** - How to detect sequences in data
✅ **Sliding Window Analysis** - Analyzing recent history
✅ **Adaptive Betting** - Adjusting based on observations
✅ **State Management** - Tracking streaks and multipliers
✅ **Risk Management** - Multiplier caps and resets

❌ **Does NOT Overcome**:
- House edge (still applies to every bet)
- Cryptographic randomness
- Mathematical expectation (negative EV)

## Comparison with Other Strategies

| Feature | RNG Analysis | Classic Martingale | Fibonacci |
|---------|-------------|-------------------|-----------|
| Pattern detection | ✅ Yes | ❌ No | ❌ No |
| Adaptive sizing | ✅ Yes | ❌ Fixed 2x | ❌ Fixed sequence |
| Historical analysis | ✅ Yes | ❌ No | ❌ No |
| Risk level | High | Very High | Medium |
| Complexity | High | Low | Low |

## Configuration File Support

The strategy can load pre-analyzed patterns from a config file:

```bash
-P config_file=/path/to/rng_analysis_results.json
```

This allows using external RNG analysis tools to generate configuration.

## Practical Testing Workflow

### 1. Start Conservative

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s rng-analysis-strategy \
  -P base_amount=0.00001 \
  -P use_patterns=true \
  -P loss_multiplier=1.1 \
  -P max_multiplier=2.0 \
  --max-bets 50
```

### 2. Observe Patterns

Watch for pattern detection messages and note:
- How often patterns are detected
- Which patterns occur most
- How bet size changes

### 3. Adjust Parameters

Based on observations:
- Increase `pattern_window` for more stable detection
- Decrease `pattern_window` for quicker adaptation
- Adjust `loss_multiplier` based on risk tolerance
- Set `max_multiplier` conservatively

### 4. Compare Results

Run multiple sessions with different settings:

```bash
# Session 1: No patterns
python3 duckdice_cli.py run ... -P use_patterns=false

# Session 2: Small window
python3 duckdice_cli.py run ... -P pattern_window=5

# Session 3: Large window
python3 duckdice_cli.py run ... -P pattern_window=20
```

## Warnings & Limitations

⚠️ **Critical Understanding**:

1. **Gambler's Fallacy**: Past outcomes don't influence future rolls
2. **Pattern Illusion**: Detected patterns are statistical noise
3. **House Edge**: Every bet has negative expected value
4. **No Guarantee**: Strategy cannot predict cryptographic RNG
5. **Learning Tool**: Use for education, not profit expectation

## Advanced Features

### Pattern Thresholds

The strategy uses configurable thresholds:

```python
PATTERN_HOT_STREAK_THRESHOLD = 0.7   # >70% wins
PATTERN_COLD_STREAK_THRESHOLD = 0.3  # <30% wins
PATTERN_ALTERNATING_THRESHOLD = 0.7  # >70% alternations
```

These can be customized by modifying the strategy code.

### Adaptive Reset

If recent 20-bet win rate drops below 30%, the multiplier resets:

```python
if recent_win_rate < 0.3:
    self._current_multiplier = 1.0
```

This prevents runaway losses during extended bad luck.

## Show Strategy Details

```bash
python3 duckdice_cli.py show rng-analysis-strategy
```

This displays:
- Full parameter list
- Risk assessment
- Pros and cons
- Usage tips
- Example commands

## Summary

✅ **Pattern detection from previous bets**: WORKING  
✅ **Adaptive bet sizing**: WORKING  
✅ **Configurable parameters**: WORKING  
✅ **Educational value**: HIGH  
⚠️ **Profit potential**: NONE (house edge applies)  
⚠️ **Risk level**: HIGH  

**Best Use**: Research, learning, experimentation in simulation mode.  
**Not Recommended For**: Real money betting with profit expectations.

---

**See Also**:
- PARAMETERS_GUIDE.md
- CLI_GUIDE.md
- FEATURES_COMPLETE.md
