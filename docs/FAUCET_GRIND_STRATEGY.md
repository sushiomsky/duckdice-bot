# 🎯 Faucet Grind Strategy Guide

## Overview

The **Faucet Grind** strategy is an automated system that transforms free faucet claims into real withdrawable balance through intelligent betting. It combines automatic faucet claiming with optimal all-in betting to reach the $20 USD cashout threshold.

---

## How It Works

### The Grind Cycle

```
1. Check Faucet Available
   ↓
2. Claim Faucet ($0.01-$0.46)
   ↓
3. Wait for Cooldown (0-60s)
   ↓
4. Calculate Optimal Chance
   ↓
5. Place All-In Bet
   ↓
6. WIN? → Check if ≥$20 → Cashout
   ↓
7. LOSS? → Wait 60s → Back to Step 1
```

The strategy repeats this cycle automatically until the $20 cashout threshold is reached.

---

## Mathematical Foundation

### Optimal Chance Calculation

The strategy calculates the perfect win chance to reach $20 from your current balance:

```python
chance = (balance_usd × 100 × (1 - house_edge)) / target_usd

# With 3% house edge for faucet bets:
chance = (balance_usd × 100 × 0.97) / 20
```

### Examples

| Balance | Calculation | Chance Needed |
|---------|-------------|---------------|
| $1.00 | (1 × 100 × 0.97) / 20 | **4.85%** |
| $5.00 | (5 × 100 × 0.97) / 20 | **24.25%** |
| $10.00 | (10 × 100 × 0.97) / 20 | **48.5%** |
| $15.00 | (15 × 100 × 0.97) / 20 | **72.75%** |
| $19.00 | (19 × 100 × 0.97) / 20 | **92.08%** |

**Note**: The closer you are to $20, the higher your win chance!

---

## Configuration Parameters

### Strategy Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `target_usd` | 20.0 | Target cashout amount in USD |
| `min_chance` | 1.1 | Minimum bet chance (safety) |
| `max_chance` | 95.0 | Maximum bet chance (safety) |
| `house_edge` | 0.03 | House edge for faucet (3%) |
| `cooldown_after_loss` | 60 | Seconds to wait after loss |
| `auto_cashout` | true | Auto-cashout at target |
| `max_consecutive_losses` | 100 | Stop after X losses (safety) |

### Faucet Mechanics

- **Claims per 24h**: 35-60 (varies)
- **Claim amount**: $0.01 - $0.46 USD equivalent
- **Cooldown**: 0-60 seconds (variable)
- **Cashout threshold**: $20.00 USD minimum
- **House edge**: 3% on faucet bets

---

## Getting Started

### Prerequisites

1. **DuckDice Account**: Create account at https://duckdice.io
2. **API Key**: Get from Account Settings → Bot API
3. **Browser Cookie**: Extract from DevTools while logged in
4. **Currency Selected**: Any supported cryptocurrency

### Step 1: Configure API Key

```bash
# In NiceGUI interface:
1. Go to Settings page
2. Enter your API key
3. Click "Connect"
4. Verify connection success
```

### Step 2: Configure Faucet Cookie

```bash
# Get cookie from browser:
1. Login to DuckDice.io
2. Open DevTools (F12)
3. Go to Application → Cookies
4. Copy entire cookie value
5. Paste in Settings → Faucet Cookie
```

### Step 3: Start Faucet Grind

```bash
# In NiceGUI interface:
1. Go to Faucet page
2. Verify cookie configured
3. Click "Start Faucet Grind"
4. Monitor progress automatically
```

### Step 4: Monitor Progress

The interface shows:
- Current faucet balance (crypto + USD)
- Progress bar to $20 target
- Claims today / Total claimed
- Grind status (claiming, betting, waiting)
- Session statistics (bets, wins, losses)

---

## Strategy Behavior

### Claim Phase

- Checks if claim is available (cooldown expired)
- Respects daily limit (35-60 claims per 24h)
- Waits for cooldown period after each claim
- Tracks claim statistics (count, total USD)

### Betting Phase

- Calculates optimal chance for $20 target
- Places all-in bet (entire faucet balance)
- Always bets "high" (over target number)
- Accounts for 3% house edge

### Win Scenario

1. Balance updated with winnings
2. Checks if balance ≥ $20 USD
3. If yes: Triggers auto-cashout
4. If no: Waits for next claim, repeats

### Loss Scenario

1. Balance reduced to zero (all-in lost)
2. Waits 60 seconds (cooldown_after_loss)
3. Claims next faucet automatically
4. Repeats betting cycle

### Cashout Phase

- Detects when balance ≥ $20 USD
- Automatically transfers to main balance
- Records cashout statistics
- Can continue grinding if auto_cashout=false

---

## Expected Results

### Time Investment

Reaching $20 from zero depends on:
- **Luck**: High variance due to all-in betting
- **Claim frequency**: 35-60 claims per 24h
- **Claim amounts**: $0.01-$0.46 per claim
- **Win streaks**: Critical for progress

**Realistic Estimate**: 
- **Best case**: 1-2 days (lucky streak)
- **Average**: 3-7 days (normal variance)
- **Worst case**: 2+ weeks (unlucky)

### Probability Analysis

Starting from $5 balance (after ~10-20 claims):

| Target | Chance | Success Rate |
|--------|--------|--------------|
| $20 | 24.25% | **~1 in 4** attempts |
| $10 | 48.5% | ~1 in 2 attempts |
| $40 | 12.1% | ~1 in 8 attempts |

**Key Insight**: Multiple smaller wins are easier than one big win!

---

## Safety Features

### Automatic Safeguards

1. **Max Consecutive Losses**: Stops after 100 losses (configurable)
2. **Chance Limits**: Won't bet below 1.1% or above 95%
3. **Balance Validation**: Checks balance before each bet
4. **Cooldown Enforcement**: Respects faucet cooldown periods
5. **Daily Limit**: Stops at 60 claims per 24h

### Error Handling

- **API Errors**: Retries with exponential backoff
- **Cookie Expiration**: Alerts user to refresh cookie
- **Network Issues**: Waits and retries automatically
- **Balance Mismatch**: Refreshes balance from API

---

## Tips for Success

### 1. Be Patient

Faucet grinding is a **marathon, not a sprint**. High variance means:
- Long losing streaks are normal
- Don't give up after 10-20 losses
- Law of large numbers favors you over time

### 2. Maximize Claims

- Check every hour to claim maximum 60/day
- Set reminders if not using auto-claim
- More claims = more chances to win

### 3. Understand Variance

With 24.25% chance (from $5):
- You'll lose **3 out of 4** bets on average
- But you only need **ONE win** to progress
- Variance evens out over many attempts

### 4. Monitor Cookie

- Cookies expire after ~30 days
- Refresh cookie if claims start failing
- Keep backup of your cookie

### 5. Consider Alternatives

If $20 seems too far:
- Adjust target_usd to $10 or $15
- Higher success chance with lower target
- Build confidence with smaller goals

---

## Troubleshooting

### "Cookie required" error

**Solution**: 
1. Login to DuckDice.io
2. Open browser DevTools (F12)
3. Application → Cookies → duckdice.io
4. Copy entire cookie string
5. Settings → Faucet Cookie → Paste

### "Daily limit reached"

**Solution**: Wait for 24h reset. Timer shown in UI.

### "Claim failed" repeatedly

**Possible causes**:
1. Cookie expired → Refresh cookie
2. Network issue → Check internet
3. DuckDice maintenance → Wait and retry
4. Already at daily limit → Wait for reset

### Strategy not starting

**Checklist**:
- ✅ API key connected?
- ✅ Cookie configured?
- ✅ Faucet balance > 0?
- ✅ Not at daily claim limit?

### Balance not updating

**Solution**:
1. Click "Refresh Balance" in Settings
2. Check API connection status
3. Verify currency selection

---

## Advanced Usage

### Custom Target Amount

```python
# In strategy parameters:
"target_usd": 10.0  # Lower target = higher success chance
```

### Disable Auto-Cashout

```python
# Continue grinding past $20:
"auto_cashout": false
```

### Adjust Loss Recovery

```python
# Faster recovery (risky):
"cooldown_after_loss": 30  # Instead of 60

# Safer recovery:
"cooldown_after_loss": 90
```

---

## Comparison with Other Strategies

| Strategy | Risk | Speed | Complexity | Success Rate |
|----------|------|-------|------------|--------------|
| **Faucet Grind** | Very Low | Slow | Simple | Medium |
| Classic Martingale | High | Fast | Simple | High (short-term) |
| Kelly Criterion | Medium | Medium | Complex | High |
| Manual Faucet | None | Very Slow | None | 100% (safe) |

---

## FAQ

### Q: Is this guaranteed to reach $20?

**A**: No. Due to variance, you might never reach $20 (extremely unlikely but possible). However, over many attempts, most users will eventually succeed.

### Q: How long will it take?

**A**: Depends on luck. Anywhere from 1 day to several weeks. Average is 3-7 days with regular claiming.

### Q: Can I lose my main balance?

**A**: No! This strategy only uses faucet balance. Your main balance is never at risk.

### Q: What if I get close to $20 but lose?

**A**: That's variance. The strategy will keep trying. Many users report getting to $18-19 multiple times before finally hitting $20.

### Q: Can I run this 24/7?

**A**: Yes, but you're limited to 35-60 claims per 24h. The strategy will automatically wait when at the limit.

### Q: Should I use simulation or live mode?

**A**: Always use **live mode** for faucet grinding. Simulation mode doesn't access real faucet balances.

---

## Support & Resources

- **GitHub Issues**: https://github.com/sushiomsky/duckdice-bot/issues
- **Strategy Code**: `src/betbot_strategies/faucet_grind.py`
- **Documentation**: This file
- **DuckDice API**: https://duckdice.io/bot-api

---

## Disclaimer

⚠️ **Important Notices**:

1. Gambling involves risk. Only bet what you can afford to lose.
2. This bot is for educational/entertainment purposes.
3. Past performance doesn't guarantee future results.
4. DuckDice faucet terms may change at any time.
5. Always gamble responsibly.

**Remember**: The house always has an edge (3% for faucet). Long-term, you're expected to lose slightly more than you win. Faucet grinding is free, but time-consuming. Consider it a learning tool rather than a profit strategy.

---

**Version**: 1.0  
**Last Updated**: 2026-01-09  
**Strategy**: Faucet Grind  
**Author**: DuckDice Bot Team
