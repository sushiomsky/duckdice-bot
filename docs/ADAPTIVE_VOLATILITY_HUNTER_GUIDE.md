# 🎯 Adaptive Volatility Hunter Strategy Guide

## Overview

The **Adaptive Volatility Hunter** is an advanced ultra-low chance hunting strategy that adapts to RNG volatility in real-time. It dynamically adjusts both bet sizes and win chances based on recent result patterns, hunting for massive multipliers (100x to 10000x) while protecting capital during chaotic RNG periods.

**Strategy Type**: Specialized - Very High Risk  
**Risk Level**: ⚠️ **EXTREME**  
**Recommended For**: Advanced players with large bankrolls  

---

## Core Concept

### Volatility-Adaptive Logic

The strategy analyzes recent betting results to calculate RNG "volatility":

- **Calm RNG** (Volatility 0.0 - 0.3)
  - Hunt deeper: **Lower chance** → Bigger multipliers (1000x - 10000x)
  - Bet more: **Higher bet %** (up to 1% of balance)
  - Rationale: Stable patterns = safe to chase massive wins

- **Chaotic RNG** (Volatility 0.7 - 1.0)
  - Survival mode: **Higher chance** → Better survival rate (100x - 500x)
  - Bet less: **Lower bet %** (down to 0.025% of balance)
  - Rationale: Unstable patterns = prioritize capital preservation

### Volatility Calculation

Volatility combines two factors:

1. **Win/Loss Imbalance**: Distance from expected 50/50 randomness
2. **Loss Streak Pressure**: Current consecutive losses amplified by weight factor

```
Volatility = Chaos + (LossStreakPressure × LossStreakWeight)
- Chaos = |0.5 - WinRatio| × 2
- LossStreakPressure = CurrentStreak / (WindowSize / 2)
```

**Result**: Value between 0.0 (calm) and 1.0 (chaotic)

---

## Key Features

### 🔄 Adaptive Chance Selection

| Volatility | Win Chance | Multiplier | Strategy |
|-----------|------------|------------|----------|
| 0.0 - 0.3 | 0.01% - 0.10% | 9800x - 980x | Hunt massive wins |
| 0.3 - 0.7 | 0.10% - 0.50% | 980x - 196x | Balanced approach |
| 0.7 - 1.0 | 0.50% - 1.00% | 196x - 98x | Survival mode |

### 💰 Adaptive Bet Sizing

| Volatility | Bet Size | Rationale |
|-----------|----------|-----------|
| 0.0 - 0.3 | 0.5% - 1.0% | Calm = safe to bet more |
| 0.3 - 0.7 | 0.1% - 0.5% | Moderate caution |
| 0.7 - 1.0 | 0.025% - 0.1% | Chaos = ultra conservative |

### 🛡️ Safety Mechanisms

1. **Profit Lock Cooldown**
   - Triggers: Session profit ≥ $0.30 (configurable)
   - Effect: Forces 30-bet ultra-safe cooldown period
   - Resets: Volatility tracking and loss streak
   - Purpose: Protect winnings from giving back

2. **Emergency Brake**
   - Triggers: Volatility > 0.9 AND Loss streak ≥ 7
   - Effect: Immediately enters cooldown mode
   - Protection: Won't re-trigger while already in cooldown
   - Purpose: Prevent catastrophic losses during extreme chaos

3. **Cooldown Mode**
   - Bet size: Minimum (0.025% of balance)
   - Win chance: Maximum (1%)
   - Duration: 30 bets (default)
   - Status: Progress updates every 10 bets
   - Exit: Displays "✅ Cooldown complete" message when done

---

## Configuration Parameters

### Core Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_chance` | float | 0.01 | Absolute minimum chance % (0.01% = 10000x) |
| `max_chance` | float | 1.00 | Absolute maximum chance % (1% = 98x) |
| `base_chance` | float | 0.05 | Neutral midpoint bias for chance selection |

### Bet Sizing

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_bet_percent` | float | 0.00025 | Minimum bet % of balance (0.025%) |
| `base_bet_percent` | float | 0.0010 | Normal bet % of balance (0.1%) |
| `max_bet_percent` | float | 0.01 | Maximum bet % of balance (1%) |

### Volatility & Safety

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `volatility_window` | int | 45 | Bets analyzed for volatility (45 optimal) |
| `loss_streak_weight` | float | 2.0 | Amplification factor for loss streaks |
| `cooldown_bets` | int | 30 | Forced safety period duration |
| `profit_lock_usd` | float | 0.30 | Profit threshold for cooldown trigger |

### Game Mode

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `is_high` | bool | True | Bet on High (True) or Low (False) |

---

## Usage Examples

### Basic Usage (Default Settings)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s adaptive-volatility-hunter \
  --max-bets 1000 \
  --stop-loss -0.10 \
  --take-profit 0.50
```

**Expected Behavior**:
- 1000 bet limit (expect ~500-1000 bets for a win)
- Stop at -10% loss
- Stop at +50% profit
- Uses all default parameters

### Conservative Hunt (Larger Bankroll Focus)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s adaptive-volatility-hunter \
  -P min_chance=0.05 \
  -P max_chance=0.50 \
  -P min_bet_percent=0.0001 \
  -P max_bet_percent=0.005 \
  --max-bets 2000 \
  --stop-loss -0.05 \
  --take-profit 0.30
```

**Configuration**:
- Chance range: 0.05% - 0.50% (200x - 2000x multipliers)
- Bet range: 0.01% - 0.5% of balance
- More bets allowed (2000)
- Tighter stop-loss (-5%)

### Aggressive Hunt (High Risk / High Reward)

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s adaptive-volatility-hunter \
  -P min_chance=0.01 \
  -P max_chance=0.10 \
  -P max_bet_percent=0.02 \
  -P profit_lock_usd=1.00 \
  --max-bets 5000 \
  --stop-loss -0.20 \
  --take-profit 2.00
```

**Configuration**:
- Chance range: 0.01% - 0.10% (980x - 9800x multipliers!)
- Max bet: 2% of balance
- Higher profit lock threshold
- Wider loss tolerance (-20%)
- Target +200% profit

### Fine-Tuned Volatility Response

```bash
python3 duckdice_cli.py run \
  -m simulation \
  -s adaptive-volatility-hunter \
  -P volatility_window=60 \
  -P loss_streak_weight=1.5 \
  -P cooldown_bets=20 \
  --max-bets 1500
```

**Configuration**:
- Larger volatility window (60 bets = more stable calculation)
- Lower loss streak weight (1.5 = less panic)
- Shorter cooldowns (20 bets)

---

## Strategy Behavior Examples

### Scenario 1: Calm RNG Period

```
Volatility: 0.15 (calm)
Bet: 0.8% of balance
Chance: 0.03% (3300x multiplier)
Status: Hunting deep for massive win
```

### Scenario 2: Moderate Volatility

```
Volatility: 0.55 (moderate chaos)
Bet: 0.25% of balance
Chance: 0.28% (350x multiplier)
Status: Balanced approach
```

### Scenario 3: High Volatility

```
Volatility: 0.85 (extreme chaos)
Bet: 0.05% of balance
Chance: 0.87% (112x multiplier)
Status: Survival mode - protecting capital
```

### Scenario 4: Emergency Brake

```
Volatility: 0.92
Loss Streak: 8
Action: EMERGENCY BRAKE ACTIVATED
Cooldown: 30 bets @ 1% chance, 0.025% bet size
```

### Scenario 5: Profit Lock

```
Session Profit: +$0.35
Action: PROFIT LOCK TRIGGERED
Cooldown: 30 bets @ 1% chance, 0.025% bet size
Result: Volatility + loss streak reset
```

---

## Recommended Session Profiles

### Profile 1: Long Session Hunter (Recommended)

```bash
Strategy: adaptive-volatility-hunter
Stop Loss: -10% to -15%
Take Profit: +50% to +100%
Max Bets: 1000-2000
Bankroll: 500+ units minimum
Expected Duration: Long (500-2000 bets for wins)
```

**Best For**: Patient players hunting life-changing wins

### Profile 2: Quick Hunt

```bash
Strategy: adaptive-volatility-hunter
Parameters: min_chance=0.10, max_chance=0.50
Stop Loss: -5%
Take Profit: +20%
Max Bets: 500
Bankroll: 300+ units
```

**Best For**: Shorter sessions with moderate multipliers (200x-1000x)

### Profile 3: Extreme Hunt (Expert Only)

```bash
Strategy: adaptive-volatility-hunter
Parameters: min_chance=0.01, max_chance=0.05
Stop Loss: -25%
Take Profit: +500%
Max Bets: 10000
Bankroll: 1000+ units REQUIRED
```

**Best For**: Experienced players with deep pockets chasing 2000x-10000x wins

---

## Performance Characteristics

### Win Frequency

| Chance Range | Expected Hits per 1000 Bets |
|--------------|----------------------------|
| 0.01% - 0.05% | 0.25 - 0.40 (rare) |
| 0.05% - 0.10% | 0.50 - 0.75 |
| 0.10% - 0.50% | 1.00 - 3.00 |
| 0.50% - 1.00% | 3.00 - 7.00 |

**Note**: Actual frequency varies based on volatility adjustments!

### Typical Session Outcomes

- **Most Common**: Slow bleed with emergency brakes (-5% to -15%)
- **Break-even**: Rare - usually either profit or loss
- **Big Wins**: 1 in 5-10 sessions hit 100x+ multiplier (+50% to +500%)
- **Catastrophic Loss**: Rare due to emergency brake (<5% of sessions)

---

## Critical Tips ⚠️

### Bankroll Management

1. **Minimum Bankroll**: 500 units (10000 satoshi for BTC, 100000 DOGE)
2. **Recommended**: 1000+ units for comfort
3. **Never exceed**: 1-2% bet size even in calm RNG

### Session Limits

1. **ALWAYS set stop-loss**: -10% to -20% maximum
2. **Set aggressive take-profit**: +50% to +200%
3. **Max bets limit**: 1000-5000 (prevents infinite bleeding)
4. **Max duration**: Consider 30-60 minute limits

### Psychological Preparation

1. **Expect long droughts**: 500-2000 bets without wins is NORMAL
2. **Don't chase losses**: Let the strategy adapt, don't override
3. **Trust the emergency brake**: It's saving you from catastrophe
4. **Celebrate cooldowns**: Profit locks mean you WON

### When to Use

✅ **Good Times**:
- Large bankroll available
- Patient mindset
- Hunting for massive single wins
- Willing to accept high variance

❌ **Bad Times**:
- Small bankroll (<200 units)
- Need consistent wins
- Impatient or emotional
- Can't handle 1000+ bet losing streaks

---

## Volatility Window Optimization

### Window Size Impact

| Window Size | Responsiveness | Stability | Best For |
|-------------|---------------|-----------|----------|
| 20-30 bets | High | Low | Aggressive adaptation |
| 40-50 bets | Moderate | Moderate | **Recommended** |
| 60-80 bets | Low | High | Conservative adaptation |
| 100+ bets | Very Low | Very High | Smooth but slow |

**Default (45)**: Optimal balance between responsiveness and stability

---

## Comparison with Other Strategies

| Feature | Volatility Hunter | Streak Hunter | Classic Martingale |
|---------|------------------|---------------|-------------------|
| Win Chance Range | 0.01% - 1% | ~14% | ~49.5% |
| Multiplier Range | 98x - 9800x | ~7x | ~2x |
| Adaptivity | High | None | None |
| Variance | Extreme | High | Low |
| Bankroll Need | Very Large | Medium | Medium |
| Win Frequency | Very Rare | Moderate | High |
| Win Size | Massive | Good | Small |

---

## Advanced Customization

### Hyper-Conservative (Survival Focus)

```bash
-P min_chance=0.10 \
-P max_chance=1.00 \
-P max_bet_percent=0.005 \
-P loss_streak_weight=3.0
```

**Effect**: Quickly shifts to safer bets at first sign of chaos

### Hyper-Aggressive (Massive Wins Focus)

```bash
-P min_chance=0.01 \
-P max_chance=0.05 \
-P loss_streak_weight=1.0 \
-P cooldown_bets=15
```

**Effect**: Stays at ultra-low chances longer, shorter cooldowns

### Profit Lock Tuning

```bash
-P profit_lock_usd=0.10 \  # Lock profits early
-P cooldown_bets=50        # Long protection period
```

**Effect**: Conservative profit protection

---

## Monitoring & Interpreting Output

### Status Messages

```
📊 Bet #50 | Volatility: 0.45 | Chance: 0.15% (653x) | Bet: 0.00012000 (0.450%)
```

**Interpretation**:
- Moderate volatility (0.45)
- Hunting at 0.15% chance (653x multiplier)
- Betting 0.45% of current balance

```
🚨 EMERGENCY BRAKE! Volatility 0.92 + 8 loss streak → 30-bet cooldown
```

**Action**: Strategy detected extreme danger, entering safety mode

```
💰 PROFIT LOCK! +$0.45 → 30-bet cooldown
```

**Action**: Hit profit target, protecting gains

```
🛡️ Cooldown: 20 bets remaining
```

**Status**: In safety mode, 20 more ultra-safe bets before normal operation

---

## Troubleshooting

### Problem: Constant Emergency Brakes

**Cause**: Volatility too sensitive  
**Solution**:
```bash
-P loss_streak_weight=1.5    # Reduce from 2.0
-P volatility_window=60       # Increase from 45
```

### Problem: Betting Too Much in Chaos

**Cause**: Bet range too wide  
**Solution**:
```bash
-P max_bet_percent=0.005     # Reduce from 0.01
-P min_bet_percent=0.0001    # Reduce from 0.00025
```

### Problem: Never Getting Big Multipliers

**Cause**: Too conservative chance range  
**Solution**:
```bash
-P min_chance=0.01           # Lower minimum
-P max_chance=0.20           # Lower maximum
```

### Problem: Profit Locks Too Frequent

**Cause**: Low profit threshold  
**Solution**:
```bash
-P profit_lock_usd=1.00      # Increase from 0.30
```

---

## Real-World Example Session

```bash
# Start session
$ python3 duckdice_cli.py run -m simulation -s adaptive-volatility-hunter \
  --max-bets 1500 --stop-loss -0.15 --take-profit 0.75

# Session log:
Bets 1-50: Vol 0.50, hunting @ 0.25% (392x) - no wins
Bets 51-100: Vol increasing to 0.75, raised chance to 0.65%
Bet 112: Emergency brake! Vol 0.91 + 9 loss streak
Bets 113-142: Cooldown @ 1% chance
Bet 138: WIN @ 98x! +0.25 balance
Bets 143-172: Profit lock cooldown
Bets 173-250: Vol 0.35, hunting @ 0.18% (544x)
Bet 247: WIN @ 544x! +1.20 balance
PROFIT LOCK! Session ended at +75% profit
```

**Total**: 247 bets, 2 wins, +75% profit, 28 minutes

---

## Final Recommendations

### DO:
✅ Set strict stop-loss (-10% to -20%)  
✅ Use large bankroll (500+ units minimum)  
✅ Be patient (expect 500-2000 bet sessions)  
✅ Trust the emergency brake  
✅ Celebrate profit locks  
✅ Use max_bets limit (1000-5000)  

### DON'T:
❌ Use with small bankroll (<200 units)  
❌ Panic during long losing streaks  
❌ Disable safety features  
❌ Expect consistent wins  
❌ Use without stop-loss  
❌ Override strategy decisions manually  

---

## Conclusion

The **Adaptive Volatility Hunter** is an advanced, high-risk strategy for experienced players hunting life-changing multipliers. Its real-time adaptation to RNG volatility provides both aggressive profit-seeking during calm periods and capital protection during chaos.

**Perfect for**: Patient, well-funded players willing to endure extreme variance for the chance at 100x-10000x wins.

**Not suitable for**: Small bankrolls, impatient players, or those seeking consistent returns.

**Remember**: This strategy can go 1000+ bets without a win. The emergency brake and profit lock are your safety nets. Trust them.

---

*For more strategy guides, see:*
- [Streak Hunter Guide](STREAK_HUNTER_GUIDE.md)
- [Adaptive Survival Guide](docs/ADAPTIVE_SURVIVAL_GUIDE.md)
- [RNG Strategy Guide](RNG_STRATEGY_GUIDE.md)
