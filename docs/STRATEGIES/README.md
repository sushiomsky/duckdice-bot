# DuckDice Bot - All Strategies

**Total Strategies: 25** | Updated: v4.11.2

## 📊 Quick Comparison

| Category | Strategies | Risk Level | Best For |
|----------|-----------|------------|----------|
| **Conservative** | D'Alembert, Oscar's Grind, 1-3-2-6 | 🟢 Low | Steady growth, beginners |
| **Balanced** | Kelly Capped, Simple Progression, Target Aware | 🟡 Medium | Risk-adjusted returns |
| **Aggressive** | Martingale, Anti-Martingale, Paroli | 🟠 High | Quick profits, experienced users |
| **High-Risk** | Adaptive Volatility Hunter, Micro Exponential | 🔴 Very High | Thrill-seekers, small stakes |
| **Specialized** | Faucet Grind, Max Wager Flow, RNG Analysis | 🟣 Varies | Specific use cases |

---

## 🎯 All Strategies (Alphabetical)

### 1. **Adaptive Survival** 🧠
**Type**: Meta-Strategy | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐⭐⭐⭐

Advanced pattern-detecting meta-strategy that combines multiple approaches:
- RNG analysis for trend detection
- Dynamic chance adjustment (5%-50%)
- Emergency brake system
- Profit lock mechanisms

**Best for**: Experienced users who understand risk management

```bash
duckdice run --strategy adaptive-survival --bets 200
```

---

### 2. **Adaptive Volatility Hunter** 🎰
**Type**: Ultra-Low Chance | **Risk**: 🔴 Very High | **Complexity**: ⭐⭐⭐⭐

Hunts massive multipliers (100x-10000x) with adaptive risk:
- Win chance: 0.01% - 1.00%
- Volatility-based adjustments
- Emergency brake at 7+ losses
- Profit lock cooldown

**Best for**: Lottery-style hunting with small stakes

```bash
duckdice run --strategy adaptive-volatility-hunter --bets 100
```

📖 [Detailed Guide](./ADAPTIVE_VOLATILITY_HUNTER_GUIDE.md)

---

### 3. **Anti-Martingale Streak** 📈
**Type**: Progressive Win | **Risk**: 🟠 High | **Complexity**: ⭐⭐

Reverse martingale - multiplies on wins, resets on loss:
- Default multiplier: 2x per win
- Max streak cap prevents runaway risk
- Quick profit potential on win streaks

**Best for**: Capitalizing on hot streaks

```bash
duckdice run --strategy anti-martingale-streak --param multiplier=2.5
```

---

### 4. **Classic Martingale** 💰
**Type**: Progressive Loss | **Risk**: 🔴 Very High | **Complexity**: ⭐⭐

The classic "double on loss" strategy:
- 2x bet after each loss
- Reset to base bet on win
- Requires large bankroll

⚠️ **Warning**: Can deplete bankroll rapidly on long loss streaks

```bash
duckdice run --strategy classic-martingale --bets 50
```

---

### 5. **Custom Script** 📝
**Type**: Programmable | **Risk**: Varies | **Complexity**: ⭐⭐⭐⭐⭐

Load custom Python or Lua (DiceBot-compatible) strategies:

```bash
duckdice run --strategy custom-script --script-path my_strategy.py
```

---

### 6. **D'Alembert** ⚖️
**Type**: Balanced | **Risk**: 🟢 Low | **Complexity**: ⭐⭐

Gradual progression system:
- Increase bet by fixed amount on loss
- Decrease by same amount on win
- More conservative than Martingale

**Best for**: Risk-averse players seeking steady growth

```bash
duckdice run --strategy dalembert --param increment=0.001
```

---

### 7. **Faucet Cashout** 💧
**Type**: USD-Targeted | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐⭐

Staged growth system with profit milestones:
- 50% chance (conservative)
- Targets: $0.10 → $0.50 → $1.00+
- Auto-cashout at goals

**Best for**: Grinding faucet claims to real profits

```bash
duckdice run --strategy faucet-cashout
```

---

### 8. **Faucet Grind** 🔄
**Type**: Auto-Claim Loop | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐

Automated faucet grinding:
1. Auto-claim faucet
2. Calculate optimal bet chance
3. All-in bet
4. Repeat

```bash
duckdice run --strategy faucet-grind --bets 1000
```

---

### 9. **Fibonacci Loss Cluster** 📐
**Type**: Progressive Loss | **Risk**: 🟠 High | **Complexity**: ⭐⭐⭐

Fibonacci sequence triggered by loss streaks:
- Activates after N consecutive losses
- Sequence: 1, 1, 2, 3, 5, 8, 13...
- Flattens bet progression vs Martingale

```bash
duckdice run --strategy fib-loss-cluster --param threshold=3
```

---

### 10. **Fibonacci** 📏
**Type**: Progressive Loss | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐

Classic Fibonacci progression:
- Advance on loss
- Retreat 2 steps on win
- Sequence: 1, 1, 2, 3, 5, 8...

```bash
duckdice run --strategy fibonacci
```

---

### 11. **Kelly Capped** 📊
**Type**: Statistical | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐⭐⭐

Kelly Criterion with safety caps:
- Calculates optimal bet from EWMA winrate
- Capped at configurable max (default 10%)
- Experimental/educational

```bash
duckdice run --strategy kelly-capped --param max_kelly_fraction=0.05
```

---

### 12. **Labouchère** 📋
**Type**: Cancellation System | **Risk**: 🟠 High | **Complexity**: ⭐⭐⭐⭐

Cancellation list progression:
- Bet sum of first + last numbers
- Cancel numbers on win, add on loss
- Customizable sequence

```bash
duckdice run --strategy labouchere --param sequence="1,2,3,4"
```

---

### 13. **Max Wager Flow** 💸
**Type**: Volume Maximizer | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐⭐

Maximize total wagered amount:
- Uses ~50% chance for balance
- Fraction-of-balance bet sizing
- Optimizes for wagering requirements

**Best for**: Bonus wagering, VIP volume

```bash
duckdice run --strategy max-wager-flow --param fraction=0.05
```

---

### 14. **Micro Exponential** 🚀
**Type**: Extreme Growth | **Risk**: 🔴 EXTREME | **Complexity**: ⭐⭐⭐⭐

300x growth target from micro balance:
- 5% win chance (19x multiplier)
- Extreme compounding
- High bust probability

⚠️ **Use ONLY with small amounts you can afford to lose**

```bash
duckdice run --strategy micro-exponential --bets 100
```

---

### 15. **Micro Exponential Safe** 🛡️
**Type**: Exponential Growth | **Risk**: 🔴 Very High | **Complexity**: ⭐⭐⭐⭐

Safer variant targeting 100x:
- 10% win chance (9x multiplier)
- Safety limits on progression
- Still very risky

```bash
duckdice run --strategy micro-exponential-safe --bets 100
```

---

### 16. **One-Three-Two-Six** 🎲
**Type**: Fixed Sequence | **Risk**: 🟢 Low | **Complexity**: ⭐

Simple 4-step sequence:
- Sequence: 1 → 3 → 2 → 6 units
- Advance on wins, reset on loss
- Conservative risk profile

```bash
duckdice run --strategy one-three-two-six
```

---

### 17. **Oscar's Grind** 🐌
**Type**: Conservative Grind | **Risk**: 🟢 Low | **Complexity**: ⭐⭐

Patient profit-seeking system:
- Increase bet only after wins
- Target small cumulative profit
- Very conservative

**Best for**: Patient players, long sessions

```bash
duckdice run --strategy oscars-grind --param target_profit=0.5
```

---

### 18. **Paroli** 🎯
**Type**: Progressive Win | **Risk**: 🟠 High | **Complexity**: ⭐⭐

Double on wins, reset on loss:
- Target win streak (default: 3)
- Resets after streak or loss
- Limits downside vs anti-martingale

```bash
duckdice run --strategy paroli --param target_streak=4
```

---

### 19. **Progressive Win Scaling** 🌊
**Type**: Aggressive Win Progression | **Risk**: 🔴 Very High | **Complexity**: ⭐⭐⭐

Dynamic chance adjustment on win streaks:
- Starts at 24% chance
- Drops to 4% chance after wins
- Compounds bet size aggressively

```bash
duckdice run --strategy progressive-win-scaling
```

📖 [Detailed Guide](../PROGRESSIVE_WIN_SCALING_GUIDE.md)

---

### 20. **Range 50 Random** 🎰
**Type**: Range Dice | **Risk**: 🟡 Medium | **Complexity**: ⭐

50% chance range betting:
- Random 5000-wide window each bet
- Even odds gameplay
- Simple variance

```bash
duckdice run --strategy range-50-random --bets 100
```

---

### 21. **RNG Analysis Strategy** 🔬
**Type**: Educational | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐⭐

Uses RNG analysis insights (doesn't beat house edge):
- Pattern detection
- Trend following
- **Educational only**

```bash
duckdice run --strategy rng-analysis-strategy
```

📖 [RNG Analysis Guide](./RNG_STRATEGY_GUIDE.md)

---

### 22. **Simple Progression 40** 📈
**Type**: Win Progression | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐

40% chance with decreasing win progression:
- Win #1: +50%
- Win #2: +40%
- Win #3: +30%
- Win #4: +20%
- Always 1% of current balance

**Best for**: Balanced risk/reward

```bash
duckdice run --strategy simple-progression-40 --bets 100
```

---

### 23. **Streak Hunter** 🏹
**Type**: Streak Betting | **Risk**: 🔴 Very High | **Complexity**: ⭐⭐⭐

Hunts 14% chance streaks with compounding:
- Progression: 200% → 180% → 160% of profit
- High volatility
- Quick profit or bust

```bash
duckdice run --strategy streak-hunter --bets 50
```

📖 [Detailed Guide](./STREAK_HUNTER.md)

---

### 24. **Streak Multiplier** ⚡
**Type**: Exponential Win Streak | **Risk**: 🔴 Very High | **Complexity**: ⭐⭐⭐

5% chance with exponential bet growth:
- Multiplies bet on each win
- Very high variance
- Can generate massive wins or losses

```bash
duckdice run --strategy streak-multiplier
```

---

### 25. **Target Aware** 🎯
**Type**: Goal-Oriented State Machine | **Risk**: 🟡 Medium | **Complexity**: ⭐⭐⭐⭐

State-machine optimized to reach profit target:
- Adjusts strategy based on distance to goal
- Conservative near target
- Aggressive when far away

```bash
duckdice run --strategy target-aware --profit-target 5.0
```

---

## 📖 Strategy Selection Guide

### By Use Case

**First Time User**
→ `dalembert`, `one-three-two-six`, `oscars-grind`

**Steady Growth**
→ `simple-progression-40`, `target-aware`, `kelly-capped`

**Quick Profits**
→ `paroli`, `anti-martingale-streak`, `streak-hunter`

**Faucet Grinding**
→ `faucet-grind`, `faucet-cashout`, `max-wager-flow`

**Thrill/Lottery**
→ `adaptive-volatility-hunter`, `micro-exponential`, `progressive-win-scaling`

**Advanced/Custom**
→ `adaptive-survival`, `custom-script`, `rng-analysis-strategy`

---

### By Risk Tolerance

🟢 **Conservative** (Can't afford to lose)
- D'Alembert
- Oscar's Grind  
- One-Three-Two-Six

🟡 **Moderate** (Can handle some variance)
- Simple Progression 40
- Kelly Capped
- Fibonacci
- Target Aware

🟠 **Aggressive** (Seeking bigger wins)
- Paroli
- Anti-Martingale Streak
- Labouchère

🔴 **High-Risk** (Prepared to lose it all)
- Classic Martingale
- Streak Hunter
- Adaptive Volatility Hunter
- Micro Exponential
- Progressive Win Scaling

---

### By Bankroll Size

**Micro ($0.01 - $1)**
- Micro Exponential (Safe)
- Faucet Grind
- Simple Progression 40

**Small ($1 - $10)**
- Any strategy except Martingale variants
- Recommended: Paroli, D'Alembert, Kelly Capped

**Medium ($10 - $100)**
- Most strategies work well
- Can afford Martingale with limits

**Large ($100+)**
- All strategies viable
- Can handle high-variance strategies

---

## 🔧 Customization

Most strategies support parameters:

```bash
# Set custom parameters
duckdice run --strategy labouchere \
  --param sequence="1,2,3,4,5" \
  --param reset_on_profit=true

# List strategy parameters
duckdice describe-strategy labouchere
```

---

## 📊 Backtesting

Compare strategies before risking real funds:

```bash
# Compare 3 strategies
python scripts/compare_strategies.sh

# Simulate specific strategy
duckdice run --strategy adaptive-survival --bets 1000 --simulate
```

---

## 🎓 Learning Resources

- **[Comparison Guide](./COMPARISON.md)** - Side-by-side analysis
- **[Configuration](../CONFIGURATION.md)** - Strategy parameters
- **[Architecture](../ARCHITECTURE/README.md)** - How strategies work

---

**⚠️ Important Disclaimer**

All strategies are subject to house edge (1%). No strategy can guarantee profits. Gambling involves risk of loss. Only bet what you can afford to lose.

**See Also**:
- [CLI Guide](../INTERFACES/CLI_GUIDE.md)
- [TUI Guide](../INTERFACES/TUI_GUIDE.md)
- [Build Your Own Strategy](../ARCHITECTURE/STRATEGY_DEVELOPMENT.md)
