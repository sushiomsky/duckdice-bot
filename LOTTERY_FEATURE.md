# Streak Hunter - Lottery Feature

**Date:** 2026-01-12  
**Version:** 4.4.0  
**Feature:** Optional lottery bets for huge payout potential

## Overview

The streak-hunter strategy now supports **optional lottery bets** - occasional low-probability, high-reward bets that add excitement and jackpot potential without disrupting your main streak-hunting strategy.

## How It Works

### Key Features

1. **Occasional Bets**: Place lottery bets every N normal bets (default: every 10 bets)
2. **Low Chance**: Random win probability between 0.01% and 4% (configurable)
3. **Base Bet Amount**: Uses your base bet (same as normal bets)
4. **Huge Payouts**: 25x to 9900x multiplier potential!
5. **Streak Preservation**: Lottery losses don't break your winning streak!

### Lottery vs Normal Bets

| Aspect | Normal Bet | Lottery Bet |
|--------|-----------|-------------|
| Frequency | Every bet | Every Nth bet |
| Win Chance | 14% (default) | 0.01-4% |
| Payout | ~7x | 25-9900x |
| On Loss | Breaks streak | **Preserves streak** ✅ |
| On Win | Continues streak | Doesn't count toward streak |

### Example Session

```
Bet 1: 0.33 @ 14% → WIN (streak = 1)
Bet 2: 0.67 @ 14% → WIN (streak = 2)
Bet 3: 0.60 @ 14% → WIN (streak = 3)
Bet 4: 0.53 @ 14% → WIN (streak = 4)
Bet 5: 0.47 @ 14% → LOSE (streak = 0)
Bet 6: 0.33 @ 14% → WIN (streak = 1)
Bet 7: 0.67 @ 14% → WIN (streak = 2)
Bet 8: 0.60 @ 14% → WIN (streak = 3)
Bet 9: 0.53 @ 14% → WIN (streak = 4)
Bet 10: 0.33 @ 1.5% → 🎰 LOTTERY! LOSE (streak = 4, preserved!)
Bet 11: 0.47 @ 14% → WIN (streak = 5)
...
Bet 20: 0.33 @ 0.8% → 🎰 LOTTERY! WIN +41 BTC! 💰 (125x payout!)
Bet 21: 0.33 @ 14% → Continue normal betting (streak = 0)
```

## Configuration

### Parameters

```bash
# Enable lottery feature
--param lottery_enabled=true

# Place lottery bet every 10 normal bets
--param lottery_frequency=10

# Minimum win chance (0.01% = 1 in 10,000)
--param lottery_chance_min=0.01

# Maximum win chance (4% = 1 in 25)
--param lottery_chance_max=4.0
```

### Payout Calculation

Win chance → Payout multiplier:
- **4.0%** → ~25x payout
- **2.0%** → ~50x payout
- **1.0%** → ~99x payout
- **0.5%** → ~198x payout
- **0.1%** → ~990x payout
- **0.01%** → ~9900x payout!

Formula: `payout = 99 / win_chance`

## Usage Examples

### Conservative Lottery (Higher Chances)

```bash
python3 duckdice_cli.py run \
  -m live-main \
  -s streak-hunter \
  -c decoy \
  --param lottery_enabled=true \
  --param lottery_frequency=10 \
  --param lottery_chance_min=2.0 \
  --param lottery_chance_max=4.0 \
  --stop-loss -0.2 \
  --take-profit 1.0
```

**Result**: Lottery bets every 10 bets with 2-4% chance (25-50x payout)

### Aggressive Lottery (Jackpot Hunting)

```bash
python3 duckdice_cli.py run \
  -m live-main \
  -s streak-hunter \
  -c decoy \
  --param lottery_enabled=true \
  --param lottery_frequency=15 \
  --param lottery_chance_min=0.01 \
  --param lottery_chance_max=0.5 \
  --stop-loss -0.3 \
  --take-profit 5.0
```

**Result**: Lottery bets every 15 bets with 0.01-0.5% chance (198-9900x payout!)

### Frequent Small Lottery

```bash
python3 duckdice_cli.py run \
  -m live-main \
  -s streak-hunter \
  -c decoy \
  --param lottery_enabled=true \
  --param lottery_frequency=5 \
  --param lottery_chance_min=1.0 \
  --param lottery_chance_max=3.0 \
  --stop-loss -0.25 \
  --take-profit 0.5
```

**Result**: Lottery bets every 5 bets with 1-3% chance (33-99x payout)

## Strategy Benefits

### Why Add Lottery Bets?

1. **Jackpot Potential**: One lucky 0.01% win can turn 0.33 BTC into 3,267 BTC!
2. **Streak Preservation**: Lottery losses don't reset your winning streak
3. **Entertainment**: Adds excitement to regular betting
4. **Same Risk**: Uses base bet amount, not inflated bet sizes
5. **Configurable**: Tune frequency and chances to your risk tolerance

### Risk Management

The lottery feature is **safer than it sounds**:
- Uses only base bet (smallest bet size)
- Losses don't break your streak
- Can be disabled anytime (default: off)
- Frequency is controllable
- Win chance range is configurable

### Mathematical Expectation

Average lottery cost over 100 bets (assuming base bet = 1):
- **Frequency 10**: 10 lottery bets = -9.9 expected loss (99% house edge)
- **Frequency 20**: 5 lottery bets = -4.95 expected loss
- **Frequency 5**: 20 lottery bets = -19.8 expected loss

But one lucky win can more than cover all losses!

## Session Statistics

With lottery enabled, you'll see additional stats:

```
🎯 Streak Hunter Session Summary:
   Total bets: 100
   Wins: 23
   Win rate: 23.00%
   Max streak achieved: 4
   Final streak: 0

   🎰 Lottery Stats:
   Attempts: 10
   Wins: 1
   🎉 You hit 1 lottery win(s)!
   Hit rate: 10.00%

   Stop reason: take_profit
```

## Tips & Tricks

### Best Practices

1. **Start Conservative**: Try 2-4% range first
2. **Monitor Results**: Track your lottery hit rate
3. **Adjust Frequency**: More frequent = more costs, less frequent = fewer chances
4. **Set Take-Profit**: If you hit big, cash out!
5. **Budget Wisely**: Lottery costs add up over many bets

### Recommended Settings by Goal

**Goal: Steady Growth with Occasional Wins**
```
lottery_frequency=15
lottery_chance_min=1.5
lottery_chance_max=3.0
```

**Goal: Jackpot Hunting**
```
lottery_frequency=20
lottery_chance_min=0.01
lottery_chance_max=0.1
```

**Goal: Balanced Fun**
```
lottery_frequency=10
lottery_chance_min=0.5
lottery_chance_max=2.0
```

## Disable Lottery

To run without lottery (default):
```bash
python3 duckdice_cli.py run \
  -m live-main \
  -s streak-hunter \
  -c decoy
```

Or explicitly:
```bash
--param lottery_enabled=false
```

## Example Output

```
🎯 Streak Hunter Strategy Started
   Target chance: 14%
   Base bet: 0.33333333
   Win multipliers: 2.0x → 1.8x → 1.6x → ...
   🎰 Lottery: Every 10 bets @ 0.01-4.0%
   Reset on: Any loss

Bet #1: ✓ WIN | Balance: 102.0
Bet #2: ✓ WIN | Balance: 106.5
...
🎰 LOTTERY BET #1! Chance: 1.25% (up to 79x payout!)
Bet #10: ✗ LOSE | Balance: 105.2
🔥 On 2-win streak! Next multiplier: 1.8x
Bet #11: ✓ WIN | Balance: 108.7
...
🎰 LOTTERY BET #2! Chance: 0.35% (up to 283x payout!)
💰 LOTTERY WIN! 0.35% hit! Profit: 93.66666667 (283.0x payout)
Bet #20: ✓ WIN | Balance: 202.4
```

## Summary

The lottery feature transforms streak-hunter into a dual-strategy approach:
- **Main game**: Hunt 14% streaks with controlled progression
- **Side game**: Occasional jackpot attempts for massive wins

Perfect for players who want both **steady growth** and **big win potential**!

---

**Version:** 4.4.0  
**Feature Status:** Production Ready ✅  
**Default:** Disabled (opt-in)
