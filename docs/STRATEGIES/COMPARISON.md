# Strategy Comparison Guide

## Overview

Side-by-side comparison of the **31 strategies** available in DuckDice Bot, organized by category.

Use the comparison tool for live simulation results:

```bash
# Recommended: 10 BTC, 2000 bets for meaningful results
./compare_strategies.sh 10.0 2000

# Or use Python directly
python3 strategy_comparison.py -b 10.0 -n 2000
```

---

## 📊 Master Comparison Table

| Strategy | Category | Risk | Score | Best For |
|----------|----------|------|-------|----------|
| unified-progression | Classic | 🟢 Low | 30.59 | Steady growth (Fib/D'Alembert/Labouchère) |
| oscars-grind | Classic | 🟢 Low | 30.22 | Patient grinding |
| unified-martingale | Classic | 🟠 High | 30.03 | Classic/anti martingale |
| paroli | Classic | 🟠 High | 29.99 | Win-streak doubling |
| one-three-two-six | Classic | 🟢 Low | 29.89 | Simple fixed sequence |
| kelly-capped | Classic | 🟡 Medium | 29.99 | Kelly Criterion with EWMA |
| adaptive-survival | Adaptive | 🟡 Medium | 27.05 | CALM/CHAOS pattern detection |
| target-aware | Adaptive | 🟡 Medium | 30.00 | Goal-oriented state machine |
| oracle-engine | Adaptive | 🟡 Medium | 19.71 | 19-mode adaptive research |
| chance-cycle-multiplier | Adaptive | 🟠 High | 20.26 | 2-phase aggressive/recovery |
| simple-progression-40 | Adaptive | 🟡 Medium | 14.20 | 40% chance decreasing multiplier |
| adaptive-hunter | Adaptive | 🟠 High | 21.08 | 12 hunter variants unified |
| tle-wager-farming | Wager | 🟡 Medium | — | TLE event micro-Paroli |
| wager-loop-stabilizer-v2 | Wager | 🟡 Medium | — | Zone-based wager survival |
| wager-sprint | Wager | 🟡 Medium | — | High-throughput Paroli boost |
| dice-out-002 | Lottery | 🔴 Very High | — | 0.02% range sniper |
| lottery-sniper | Lottery | 🔴 Very High | — | 1% hunt → 0.1% bursts |
| ladder-race | Lottery | 🔴 Very High | — | Contest 5x→10x→50x→100x |
| roll-hunt | Lottery | 🔴 Very High | — | Contest targeting 9990-9999 |
| balance-sweep-sniper | Lottery | 🟡 Medium | — | Multi-coin dust sweeper |
| ai-strat | Research | 🔴 Very High | — | 30+ ML ensemble |
| combined-high-roller | Research | 🔴 Very High | — | Kelly/Streak/Volatility |
| profit-cascade | Research | 🔴 Very High | — | 12-tier dynamic targeting |
| streak-multiplier | Research | 🔴 Very High | — | Exponential win-streak growth |
| master | Meta | 🟣 Variable | — | Cycles 15 sub-strategies ×3 tiers |
| custom-script | Meta | 🟣 Variable | — | User-defined executor |
| multi-strategy-system | Meta | 🟠 Variable | — | Auto-switches grind/recovery/hunt |
| adaptive-hunt | Meta (sub) | 🟠 High | — | Sub-strategy for multi-strategy |
| wager-grinder | Meta (sub) | 🟡 Medium | — | Sub-strategy for multi-strategy |
| recovery | Meta (sub) | 🟢 Low | — | Sub-strategy for multi-strategy |
| unified-faucet | Meta | 🟢 Low | — | Faucet learning tool |

---

## 🏆 Category Breakdown

### Classic Progressions

Best-scoring category overall. These are well-understood mathematical systems.

| Strategy | Approach | Bankroll Safety | Win Streak Needed | Loss Recovery |
|----------|----------|----------------|-------------------|---------------|
| unified-progression | Fib / D'Alembert / Labouchère | ✅ High | No | Gradual |
| oscars-grind | +1 on win only | ✅ High | Mild | Slow but safe |
| unified-martingale | 2x on loss or win | ⚠️ Medium (classic) / ✅ (anti) | Anti mode yes | Fast (classic) |
| paroli | 2x on win, reset on loss | ✅ High | Yes (3+) | Instant reset |
| one-three-two-six | Fixed 1→3→2→6 | ✅ High | Yes (4) | Instant reset |
| kelly-capped | EWMA optimal sizing | ✅ High | No | Statistical |

**Recommendation**: Start with `unified-progression` (mode=dalembert) or `oscars-grind` for the safest experience.

---

### Adaptive / State-Machine

Strategies that change behavior based on detected patterns or progress.

| Strategy | Modes/States | Complexity | Autonomy |
|----------|-------------|------------|----------|
| adaptive-survival | CALM / CHAOS + 4 sub-strategies | ⭐⭐⭐⭐⭐ | Fully automatic |
| target-aware | SAFE / BUILD / STRIKE / FINISH | ⭐⭐⭐⭐ | Goal-driven |
| oracle-engine | 19 adaptive modes | ⭐⭐⭐⭐⭐ | Research |
| chance-cycle-multiplier | Aggressive / Recovery phases | ⭐⭐⭐ | 2-phase cycle |
| simple-progression-40 | Single mode, decreasing multiplier | ⭐⭐ | Simple |
| adaptive-hunter | 12 hunter variants | ⭐⭐⭐⭐ | Multi-variant |

**Recommendation**: `target-aware` for goal-oriented play; `adaptive-survival` for experienced users.

---

### Wager / TLE

Optimized for wager volume rather than profit — ideal for events, bonuses, and VIP requirements.

| Strategy | Mechanism | Speed | Bankroll Drain |
|----------|-----------|-------|---------------|
| tle-wager-farming | Micro-Paroli bursts | ⚡ Fast | Low |
| wager-loop-stabilizer-v2 | Zone-based sizing | ⚡ Fast | Low |
| wager-sprint | High-throughput Paroli | ⚡⚡ Very Fast | Medium |

**Recommendation**: `tle-wager-farming` for events; `wager-sprint` when speed matters most.

---

### Lottery / Contest

High-variance strategies for jackpot hunting and contest leaderboards.

| Strategy | Target | Win Chance | Payout Potential |
|----------|--------|-----------|-----------------|
| dice-out-002 | 0.02% range, 2-slot window | 0.02% | 💎 Massive |
| lottery-sniper | 1% → 10 bursts at 0.1% | 0.1%-1% | 💎 Very High |
| ladder-race | 5x→10x→50x→100x | Varies | 🏆 Contest ranking |
| roll-hunt | Roll 9990-9999 | ~0.1% | 🏆 Contest ranking |
| balance-sweep-sniper | Multi-coin dust | ~50% | 🧹 Consolidation |

**Recommendation**: `lottery-sniper` for balanced lottery play; `ladder-race` or `roll-hunt` for contests.

---

### Aggressive / Research

Experimental strategies with high variance and high potential.

| Strategy | Approach | Models/Tiers | Variance |
|----------|----------|-------------|----------|
| ai-strat | 30+ ML ensemble | Many | 📈 Extreme |
| combined-high-roller | Kelly + Streak + Volatility | 3 systems | 📈 Very High |
| profit-cascade | 12-tier dynamic targeting | 12 tiers | 📈 Very High |
| streak-multiplier | Exponential win-streak growth | Single | 📈 Extreme |

**Recommendation**: Use only with amounts you can afford to lose. `combined-high-roller` is the most structured.

---

### Meta / Infrastructure

Orchestration strategies and building blocks.

| Strategy | Role | Standalone? |
|----------|------|------------|
| master | Cycles 15 sub-strategies across 3 tiers | ✅ Yes |
| custom-script | Runs user Python/Lua scripts | ✅ Yes |
| multi-strategy-system | Auto-switches grind/recovery/hunt | ✅ Yes |
| adaptive-hunt | Low-chance hunting sub-strategy | ❌ Sub-strategy |
| wager-grinder | Volume generation sub-strategy | ❌ Sub-strategy |
| recovery | Bankroll recovery sub-strategy | ❌ Sub-strategy |
| unified-faucet | Faucet learning tool | ✅ Yes |

**Recommendation**: `multi-strategy-system` for hands-off play; `master` for strategy rotation research.

---

## 🔍 Head-to-Head Comparisons

### Conservative vs Aggressive

| Feature | Unified Progression | Unified Martingale (classic) |
|---------|-------------------|----------------------------|
| On loss | +1 step (gradual) | 2× bet (exponential) |
| On win | -1 step / cancel | Reset to base |
| Bust risk | Low | High |
| Recovery speed | Slow | Fast (if it works) |
| Score | 30.59 | 30.03 |

### Wager Strategies Compared

| Feature | TLE Wager Farming | Wager Sprint | Wager Loop Stabilizer v2 |
|---------|------------------|--------------|-------------------------|
| Focus | Event volume | Raw speed | Bankroll preservation |
| Bet sizing | Micro-Paroli | Paroli boost | Zone-based |
| Best for | TLE events | Quick bursts | Long sessions |

### Lottery Strategies Compared

| Feature | Dice Out 002 | Lottery Sniper | Ladder Race |
|---------|-------------|----------------|-------------|
| Win chance | 0.02% | 0.1%-1% | Varies |
| Payout | Massive | Very high | Contest rank |
| Bets needed | Many | Moderate | Few |
| Purpose | Jackpot | Lottery bursts | Contests |

---

## 📈 Running Comparisons

### Quick Start

```bash
# Compare all strategies with default settings
./compare_strategies.sh

# Custom balance and bet count
./compare_strategies.sh 5.0 1000

# Full control
python3 strategy_comparison.py \
    --balance 10.0 \
    --max-bets 2000 \
    --currency btc \
    --seed 42 \
    --output comparison_report.html
```

### Command Line Options

```
-b, --balance BALANCE      Starting balance (default: 1.0)
-n, --max-bets MAX_BETS   Maximum bets per strategy (default: 1000)
-c, --currency CURRENCY    Currency symbol (default: btc)
-s, --seed SEED           Random seed for reproducibility (default: 42)
-o, --output OUTPUT       Output HTML file (default: strategy_comparison.html)
```

### Reproducible Results

```bash
# Same seed = same results every time
python3 strategy_comparison.py -s 42 -n 1000
python3 strategy_comparison.py -s 42 -n 1000  # Identical results
```

---

## 📊 Understanding Results

### Key Metrics

| Metric | What It Means |
|--------|--------------|
| **Profit %** | Ending balance vs starting — positive = profit |
| **Win Rate** | Percentage of bets won |
| **Max Balance** | Peak balance reached (shows upside potential) |
| **Busts** | Times balance dropped to ~zero |
| **Stop Reason** | `max_bets` (normal), `insufficient_balance` (bust), `take_profit` (success) |

### Green Flags ✅
- Positive profit %
- 0 busts
- Consistent win rate
- Stop reason: max_bets or take_profit

### Red Flags 🚩
- Busts > 0
- -100% profit (total loss)
- Very high max bet size
- Stop reason: insufficient_balance

---

## 💡 Tips

1. **Use enough bets** (500-1000+) for meaningful results
2. **Same seed** ensures fair comparison (default: 42)
3. **Try multiple seeds** to see consistency across different RNG sequences
4. **Match bankroll to strategy** — aggressive strategies need larger bankrolls
5. **Read stop reasons** — a strategy that hit take_profit is different from one that busted

---

## Skipped Strategies

Some strategies require special configuration and may be skipped during comparison:
- `custom-script` — needs a script path
- Sub-strategies (`adaptive-hunt`, `wager-grinder`, `recovery`) — not standalone

---

## See Also

- **[Strategy Catalog](./README.md)** — Full strategy descriptions
- **[Streak Hunter Guide](./STREAK_HUNTER.md)** — Detailed streak-hunter walkthrough
- **[Compounding Fix](./COMPOUNDING.md)** — Streak-hunter progression details
- **[CLI Guide](../INTERFACES/CLI_GUIDE.md)** — Running strategies from the command line

---

**⚠️ Disclaimer**: All strategies are subject to house edge (1%). No strategy can guarantee profits. Past simulation results do not predict future performance. Only bet what you can afford to lose.
