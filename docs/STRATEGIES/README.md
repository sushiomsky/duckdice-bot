# DuckDice Bot - All Strategies

**Runtime strategy catalog** | Updated: v4.11.2 | **31 strategies**

## 📊 Quick Comparison

| Category | Strategies | Risk Level | Best For |
|----------|-----------|------------|----------|
| **Classic Progressions** | Unified Progression, Oscar's Grind, Unified Martingale, Paroli, 1-3-2-6, Kelly Capped | 🟢 Low–Medium | Steady growth, beginners |
| **Adaptive / State-Machine** | Adaptive Survival, Target Aware, Oracle Engine, Chance Cycle Multiplier, Simple Progression 40, Adaptive Hunter | 🟡 Medium | Pattern-based, adaptive play |
| **Wager / TLE** | TLE Wager Farming, Wager Loop Stabilizer v2, Wager Sprint | 🟡 Medium | Volume / event grinding |
| **Lottery / Contest** | Dice Out 002, Lottery Sniper, Ladder Race, Roll Hunt, Balance Sweep Sniper | 🔴 Very High | Jackpot hunting, contests |
| **Aggressive / Research** | AI Strat, Combined High Roller, Profit Cascade, Streak Multiplier | 🔴 Very High | Experimental, high reward |
| **Meta / Infrastructure** | Master, Custom Script, Multi-Strategy System, Unified Faucet | 🟣 Varies | Orchestration, learning |

---

## 🎯 Classic Progressions

### **Unified Progression** ⚖️
**Type**: Multi-Mode Progression | **Risk**: 🟢 Low | **Score**: 30.59 (SAFE tier)

Combines three classic systems in one strategy:
- **Fibonacci** — advance on loss, retreat 2 steps on win
- **D'Alembert** — increase by fixed amount on loss, decrease on win
- **Labouchère** — cancellation list progression

```bash
duckdice run --strategy unified-progression --param mode=fibonacci
```

---

### **Oscar's Grind** 🐌
**Type**: Conservative Grind | **Risk**: 🟢 Low | **Score**: 30.22

Patient profit-seeking system:
- Increase bet only after wins
- Target small cumulative profit
- Very conservative

```bash
duckdice run --strategy oscars-grind --param target_profit=0.5
```

---

### **Unified Martingale** 💰
**Type**: Progressive | **Risk**: 🟠 High | **Score**: 30.03

Classic and anti-martingale in one strategy:
- **Classic** — double on loss, reset on win
- **Anti** — multiply on wins, reset on loss

⚠️ Classic mode can deplete bankroll rapidly on long loss streaks

```bash
duckdice run --strategy unified-martingale --param mode=classic
duckdice run --strategy unified-martingale --param mode=anti
```

---

### **Paroli** 🎯
**Type**: Progressive Win | **Risk**: 🟠 High | **Score**: 29.99

Double on wins, reset on loss:
- Target win streak (default: 3)
- Resets after streak or loss
- Limits downside vs pure anti-martingale

```bash
duckdice run --strategy paroli --param target_streak=4
```

---

### **One-Three-Two-Six** 🎲
**Type**: Fixed Sequence | **Risk**: 🟢 Low | **Score**: 29.89

Simple 4-step sequence:
- Sequence: 1 → 3 → 2 → 6 units
- Advance on wins, reset on loss
- Conservative risk profile

```bash
duckdice run --strategy one-three-two-six
```

---

### **Kelly Capped** 📊
**Type**: Statistical | **Risk**: 🟡 Medium | **Score**: 29.99

Kelly Criterion with safety caps:
- Calculates optimal bet from EWMA winrate
- Capped at configurable max (default 10%)

```bash
duckdice run --strategy kelly-capped --param max_kelly_fraction=0.05
```

---

## 🧠 Adaptive / State-Machine

### **Adaptive Survival** 🧠
**Type**: Meta-Strategy | **Risk**: 🟡 Medium | **Score**: 27.05

Pattern-detecting meta-strategy with CALM/CHAOS modes and 4 sub-strategies:
- Dynamic chance adjustment (5%-50%)
- Emergency brake system
- Profit lock mechanisms

```bash
duckdice run --strategy adaptive-survival --bets 200
```

---

### **Target Aware** 🎯
**Type**: Goal-Oriented State Machine | **Risk**: 🟡 Medium | **Score**: 30.00

SAFE/BUILD/STRIKE/FINISH state machine optimized to reach profit target:
- Conservative near target, aggressive when far away
- Adjusts strategy based on distance to goal

```bash
duckdice run --strategy target-aware --profit-target 5.0
```

---

### **Oracle Engine** 🔮
**Type**: Multi-Mode Adaptive | **Risk**: 🟡 Medium | **Score**: 19.71

19-mode adaptive state machine:
- Complex pattern recognition
- Automatic mode switching
- Research/experimental

```bash
duckdice run --strategy oracle-engine --bets 500
```

---

### **Chance Cycle Multiplier** 🔄
**Type**: 2-Phase Cycling | **Risk**: 🟠 High | **Score**: 20.26

Aggressive/recovery 2-phase system:
- Phase 1: Aggressive low-chance betting
- Phase 2: Conservative recovery after drawdown

```bash
duckdice run --strategy chance-cycle-multiplier --bets 200
```

---

### **Simple Progression 40** 📈
**Type**: Win Progression | **Risk**: 🟡 Medium | **Score**: 14.20

40% chance with decreasing win multiplier:
- Win #1: +50%, Win #2: +40%, Win #3: +30%, Win #4: +20%
- Always 1% of current balance

```bash
duckdice run --strategy simple-progression-40 --bets 100
```

---

### **Adaptive Hunter** 🏹
**Type**: Unified Hunter | **Risk**: 🟠 High | **Score**: 21.08

12 hunter variants unified into one configurable strategy:
- Streak hunting, volatility tracking, pattern detection
- Multiple hunting modes

```bash
duckdice run --strategy adaptive-hunter --bets 200
```

---

## 💸 Wager / TLE

### **TLE Wager Farming** 🌾
**Type**: Event Farming | **Risk**: 🟡 Medium

Micro-Paroli optimized for TLE (Time-Limited Event) volume:
- Maximizes wagered amount within event windows
- Fast bet cycling

```bash
duckdice run --strategy tle-wager-farming --bets 1000
```

---

### **Wager Loop Stabilizer v2** 🔁
**Type**: Zone-Based Survival | **Risk**: 🟡 Medium

Zone-based wager survival system:
- Maintains bankroll while generating wager volume
- Adaptive bet sizing by zone

```bash
duckdice run --strategy wager-loop-stabilizer-v2 --bets 1000
```

---

### **Wager Sprint** 🏃
**Type**: High-Throughput | **Risk**: 🟡 Medium

High-throughput Paroli boost for rapid wager generation:
- Speed-optimized betting cycles
- Short burst sessions

```bash
duckdice run --strategy wager-sprint --bets 500
```

---

## 🎰 Lottery / Contest

### **Dice Out 002** 🎯
**Type**: Range Sniper | **Risk**: 🔴 Very High

0.02% range sniper with 2-slot window:
- Targets extremely narrow range for massive payout
- Lottery-style odds

```bash
duckdice run --strategy dice-out-002 --bets 100
```

---

### **Lottery Sniper** 🔫
**Type**: Hunt → Burst | **Risk**: 🔴 Very High

Two-phase lottery hunting:
- Phase 1: 1% chance hunting
- Phase 2: 10 lottery bursts at 0.1%

```bash
duckdice run --strategy lottery-sniper --bets 200
```

---

### **Ladder Race** 🪜
**Type**: Contest Ladder | **Risk**: 🔴 Very High

Progressive contest multiplier ladder:
- Sequence: 5x → 10x → 50x → 100x
- Designed for contest leaderboard climbing

```bash
duckdice run --strategy ladder-race --bets 50
```

---

### **Roll Hunt** 🎲
**Type**: Contest Targeting | **Risk**: 🔴 Very High

Contest strategy targeting high roll numbers:
- Targets range 9990-9999
- Optimized for roll-number contests

```bash
duckdice run --strategy roll-hunt --bets 100
```

---

### **Balance Sweep Sniper** 🧹
**Type**: Multi-Coin Dust Sweeper | **Risk**: 🟡 Medium

Sweeps small balances across multiple coins:
- Consolidates dust into playable amounts
- Multi-currency support

```bash
duckdice run --strategy balance-sweep-sniper
```

---

## 🚀 Aggressive / Research

### **AI Strat** 🤖
**Type**: ML Ensemble | **Risk**: 🔴 Very High

30+ ML model ensemble strategy:
- Multiple machine learning approaches
- Experimental/research

```bash
duckdice run --strategy ai-strat --bets 200
```

---

### **Combined High Roller** 🎰
**Type**: Multi-System Aggressive | **Risk**: 🔴 Very High

Combines Kelly, Streak, and Volatility Range Dice:
- Three aggressive systems in one
- High variance, high potential

```bash
duckdice run --strategy combined-high-roller --bets 100
```

---

### **Profit Cascade** 💎
**Type**: Dynamic Targeting | **Risk**: 🔴 Very High

12-tier dynamic profit targeting system:
- Cascading profit targets
- Aggressive bet scaling per tier

```bash
duckdice run --strategy profit-cascade --bets 200
```

---

### **Streak Multiplier** ⚡
**Type**: Exponential Win Streak | **Risk**: 🔴 Very High

5% chance with exponential bet growth:
- Multiplies bet on each consecutive win
- Very high variance

```bash
duckdice run --strategy streak-multiplier --bets 100
```

---

## 🔀 Meta / Infrastructure

### **Master** 👑
**Type**: Meta-Strategy Orchestrator | **Risk**: 🟣 Variable

Cycles 15 sub-strategies across 3 performance tiers:
- Automatic strategy rotation
- Promotes/demotes based on results

```bash
duckdice run --strategy master --bets 1000
```

---

### **Custom Script** 📝
**Type**: Programmable | **Risk**: Varies

Load custom Python or Lua (DiceBot-compatible) strategies:

```bash
duckdice run --strategy custom-script --script-path my_strategy.py
```

---

### **Multi-Strategy System** 🔀
**Type**: Auto-Switching Meta Strategy | **Risk**: 🟠 Variable

Manager-driven orchestration switching between three internal modes:
- **Wager Grinder** — 20%-40% chance volume generation
- **Recovery** — 65%-80% chance bankroll recovery after drawdown
- **Adaptive Hunt** — 1% → 0.01% low-chance hunting after profit expansion

```bash
duckdice run --strategy multi-strategy-system \
  --param base_bet_percent=0.001 \
  --param max_bet_percent=0.03 \
  --param loss_trigger=0.05 \
  --param profit_trigger=0.10 \
  --param wager_focus=true
```

> **Sub-strategies** (not used standalone):
> `adaptive-hunt`, `wager-grinder`, `recovery`

---

### **Unified Faucet** 💧
**Type**: Faucet Learning Tool | **Risk**: 🟢 Low

Consolidated faucet strategy for learning and micro-balance play:
- Auto-claim and bet cycling
- Beginner-friendly

```bash
duckdice run --strategy unified-faucet --bets 500
```

---

## 📖 Strategy Selection Guide

### By Use Case

**First Time User**
→ `unified-progression`, `one-three-two-six`, `oscars-grind`

**Steady Growth**
→ `simple-progression-40`, `target-aware`, `kelly-capped`

**Quick Profits**
→ `paroli`, `unified-martingale --param mode=anti`, `streak-multiplier`

**Wager Grinding**
→ `tle-wager-farming`, `wager-loop-stabilizer-v2`, `wager-sprint`

**Lottery / Contests**
→ `dice-out-002`, `lottery-sniper`, `ladder-race`, `roll-hunt`

**Advanced / Custom**
→ `adaptive-survival`, `master`, `custom-script`, `ai-strat`

---

### By Risk Tolerance

🟢 **Conservative** (Can't afford to lose)
- Unified Progression (Fibonacci/D'Alembert/Labouchère)
- Oscar's Grind
- One-Three-Two-Six
- Unified Faucet

🟡 **Moderate** (Can handle some variance)
- Simple Progression 40
- Kelly Capped
- Target Aware
- Wager strategies (TLE, Loop Stabilizer, Sprint)

🟠 **Aggressive** (Seeking bigger wins)
- Paroli
- Unified Martingale
- Chance Cycle Multiplier
- Adaptive Hunter

🔴 **High-Risk** (Prepared to lose it all)
- Streak Multiplier
- Combined High Roller
- Profit Cascade
- AI Strat
- Lottery / Contest strategies

---

## 🔧 Customization

Most strategies support parameters:

```bash
# Set custom parameters
duckdice run --strategy unified-progression \
  --param mode=labouchere \
  --param sequence="1,2,3,4,5"

# List strategy parameters
duckdice describe-strategy unified-progression
```

---

## 📊 Backtesting

Compare strategies before risking real funds:

```bash
# Compare all strategies
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
