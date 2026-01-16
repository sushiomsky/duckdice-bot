# Progressive Win-Only Scaling Strategy

## Overview
Aggressive win-only scaling strategy with 4-24% chance progression that resets completely on any loss.

## Strategy Details

### Core Mechanics
- **Base Bet**: 1/100 of current balance (configurable divisor)
- **Starting Chance**: 4% (very low, very high payout multiplier)
- **Progression**: Only scales up on wins
- **Reset**: Full reset to base bet and base chance on ANY loss

### Win Progression Tables

**Bet Multipliers (applied to previous bet):**
- Win 1: 4.0x (+300%)
- Win 2: 3.4x (+240%)
- Win 3: 2.8x (+180%)
- Win 4: 2.2x (+120%)
- Win 5: 1.6x (+60%)

**Chance Progression:**
- Win 1: 8%
- Win 2: 12%
- Win 3: 16%
- Win 4: 20%
- Win 5: 24% (capped)

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| base_divisor | int | 100 | Divide balance by this for base bet |
| base_chance | float | 4.0 | Starting win chance percentage |
| max_chance | float | 24.0 | Maximum win chance cap |
| is_high | bool | true | Bet on High or Low |

## Risk Profile

- **Risk Level**: Very High ⚠️
- **Bankroll Required**: Medium
- **Volatility**: Extreme
- **Time to Profit**: Very Quick or Very Slow
- **Recommended For**: Experienced risk-takers only

## Pros ✅

1. Massive profit potential during winning streaks
2. Low starting chance (4%) = high multipliers (24x at 4%)
3. Scales aggressively on consecutive wins
4. Full reset limits catastrophic losses
5. Can turn small balance into large profit quickly

## Cons ❌

1. Single loss destroys ALL progress
2. 4% starting chance = 96% chance to lose first bet
3. Requires extremely lucky streaks to profit
4. Emotionally challenging to lose big bets
5. Not sustainable long-term
6. Can drain bankroll quickly

## Best Use Case

High-risk gambling for thrill-seekers. Best for "all-or-nothing" sessions with **expendable bankroll only**.

## Expert Tips 💡

1. **Set strict profit targets and STOP when hit**
2. Expect to lose most sessions - this is statistically normal
3. **Never use more than 5-10% of total bankroll**
4. One 5-win streak can yield 50-100x profit
5. Consider stopping after 3-4 wins (before high chance resets)
6. This is a "lottery ticket" strategy, NOT an investment

## Example Winning Streak

Starting balance: 100 BTC  
Base bet: 1 BTC (100/100)

| Bet | Chance | Amount | Win? | Payout Multiplier | Profit | Balance |
|-----|--------|--------|------|-------------------|--------|---------|
| 1 | 4% | 1.0000 | ✓ | 24.00x | +23.00 | 123.00 |
| 2 | 8% | 4.0000 | ✓ | 11.88x | +43.52 | 166.52 |
| 3 | 12% | 13.6000 | ✓ | 7.92x | +94.11 | 260.63 |
| 4 | 16% | 38.0800 | ✓ | 5.94x | +188.27 | 448.90 |
| 5 | 20% | 83.7760 | ✓ | 4.75x | +314.84 | 763.74 |
| **STOP** | - | - | - | - | **+663.74** | **763.74** |

**Result**: 5-win streak = 663% profit!

But remember: Getting 5 wins in a row starting at 4% chance is:
- Probability: 0.04 × 0.08 × 0.12 × 0.16 × 0.20 = **0.00001536** (0.001536%)
- Odds: **1 in 65,104** chance!

## Usage Examples

### CLI
```bash
# Simulation mode (recommended for testing)
duckdice run \
  -m simulation \
  -c btc \
  -s progressive-win-scaling \
  --max-bets 100 \
  --take-profit 1.0

# Live mode (VERY RISKY!)
duckdice run \
  -m live-main \
  -c btc \
  -s progressive-win-scaling \
  -P base_divisor=200 \
  --take-profit 0.5 \
  --stop-loss -0.1
```

### Interactive Mode
```bash
duckdice interactive
# Select: progressive-win-scaling
# Set target: 2x balance
# Configure: Use defaults or adjust base_divisor for risk
```

## Performance Expectations

### Typical Session (100 bets)
- **Most likely outcome**: -10% to -30% loss
- **Lucky outcome** (1-2 small streaks): +20% to +100%
- **Jackpot outcome** (4-5 win streak): +200% to +1000%

### Long-term Expectation
- **House edge**: ~1-2% (applies to all bets)
- **Expected value**: Negative (this strategy cannot beat house edge)
- **Variance**: Extremely high

## Safety Warnings ⚠️

1. **DO NOT** use this with money you can't afford to lose
2. **DO NOT** chase losses by increasing base_divisor
3. **DO NOT** expect consistent profits - variance is extreme
4. **DO** set strict stop-loss limits
5. **DO** cash out immediately when profit target is hit
6. **DO** understand this is pure gambling, not investing

## Strategy Code Location

`src/betbot_strategies/progressive_win_scaling.py`

## See Also

- [Paroli Strategy](paroli.py) - Similar win-only progression (safer)
- [Streak Hunter](streak_hunter.py) - Another aggressive streak strategy
- [Anti-Martingale](anti_martingale_streak.py) - Positive progression alternative
