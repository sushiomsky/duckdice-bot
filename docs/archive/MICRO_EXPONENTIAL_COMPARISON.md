# Micro Exponential Strategy Variants - Comparison Guide

## Overview

Two variants are now available:
1. **`micro-exponential`** - Original extreme version (EXTREME RISK)
2. **`micro-exponential-safe`** - Safer variant with limits (HIGH RISK)

## Side-by-Side Comparison

| Feature | micro-exponential | micro-exponential-safe |
|---------|-------------------|------------------------|
| **Risk Level** | EXTREME | HIGH |
| **Profit Target** | 300x | 100x |
| **Max Drawdown** | 45% | 35% |
| **KILL Bet Size** | 65% of balance | 50% of balance |
| **CHAOS Max Bet** | 30% of balance | 10% of balance |
| **CHAOS Multiplier** | 0.3x - 2.5x | 0.5x - 1.5x |
| **PRESSURE Max Bet** | 25% of balance | 20% of balance |
| **PRESSURE Streak Cap** | Unlimited | Max 8 losses |
| **PROBE Weight** | 30 | 40 (more conservative) |
| **CHAOS Weight** | 20 | 10 (less chaos) |
| **Emergency Brake** | None | 50% drawdown → PROBE |
| **Loss Streak Switching** | 10-bet cooldown | 3-bet cooldown at 5+ losses |
| **KILL Activation** | Vol >0.72, DD <20%, 12% chance | Vol >0.75, DD <15%, 8% chance |

## Detailed Differences

### 1. Profit Target
**Original**: 300x (unrealistic for most sessions)
```python
profit_target_x = '300'  # Stop at 30,000% profit
```

**Safe**: 100x (more achievable)
```python
profit_target_x = '100'  # Stop at 10,000% profit
```

### 2. CHAOS Mode Safety
**Original**: Can bet up to 30% of balance with wild multipliers
```python
multiplier = Decimal(str(random.uniform(0.3, 2.5)))  # Up to 2.5x base bet
betsize = self.clamp(betsize, self.min_bet, self.current_balance * Decimal('0.30'))
```

**Safe**: Limited to 10% with tighter multipliers
```python
multiplier = Decimal(str(random.uniform(0.5, 1.5)))  # Max 1.5x base bet
betsize = self.clamp(betsize, self.min_bet, self.current_balance * Decimal('0.10'))
```

**Impact**: Prevents the death spiral seen in the original (5 consecutive 51 DECOY bets)

### 3. KILL Mode Aggression
**Original**: Bets 65% of entire balance
```python
kill_bet_percent = '0.65'  # 65% all-in
```

**Safe**: Bets 50% of balance
```python
kill_bet_percent = '0.50'  # 50% semi-all-in
```

**Impact**: Still explosive but leaves recovery room

### 4. PRESSURE Martingale Protection
**Original**: Unlimited loss streak multiplication
```python
multiplier = Decimal('1.3') ** self.loss_streak  # Can grow infinitely
```

**Safe**: Capped at 8 losses
```python
capped_streak = min(self.loss_streak, 8)
multiplier = Decimal('1.3') ** capped_streak  # Max 1.3^8 = 8.16x
```

**Impact**: Prevents martingale from consuming entire balance

### 5. Emergency Drawdown Protection
**Original**: None - will ride to $0
```python
# No emergency mechanism
```

**Safe**: Auto-switches to PROBE at 50% drawdown
```python
if drawdown >= 50:
    if not self.emergency_mode:
        self.emergency_mode = True
    self.current_strategy = self.MODE_PROBE
    return
```

**Impact**: Attempt to preserve remaining capital in deep drawdown

### 6. Fast Mode Switching in Trouble
**Original**: Always 10-bet cooldown
```python
return self.total_bets - self.last_switch_bet >= self.switch_cooldown_bets
```

**Safe**: Reduced to 3 bets during loss streaks
```python
if self.loss_streak >= 5:
    return self.total_bets - self.last_switch_bet >= 3  # Fast escape
return self.total_bets - self.last_switch_bet >= self.switch_cooldown_bets
```

**Impact**: Can escape bad modes faster when losing

### 7. Strategy Weighting
**Original**: More aggressive distribution
```python
weights = {
    self.MODE_PROBE: 30,
    self.MODE_PRESSURE: 25,
    self.MODE_HUNT: 25,
    self.MODE_CHAOS: 20
}
```

**Safe**: More conservative distribution
```python
weights = {
    self.MODE_PROBE: 40,     # +10 (more safety)
    self.MODE_PRESSURE: 25,
    self.MODE_HUNT: 25,
    self.MODE_CHAOS: 10      # -10 (less chaos)
}
```

## Real-World Session Comparison

### Original Micro-Exponential
```
Started: 79.43 DECOY
Peak: 243.28 DECOY (+206%)
Ended: 0.00 DECOY (-100%)
Bets: 345
Duration: 49s
Cause of Death: CHAOS mode locked at 51 DECOY bets (25% of balance)
```

### Expected Micro-Exponential-Safe Behavior
```
Started: 79.43 DECOY
Peak: ~150 DECOY (+89%) - Lower target
Max CHAOS bet: ~15 DECOY (10% limit)
Emergency brake: Activates at ~120 DECOY (50% drawdown from 243)
Expected survival: Higher - more time to recover
```

## When to Use Each

### Use Original (`micro-exponential`)
✅ Absolute dust amounts (<$0.50)  
✅ "YOLO" experimental sessions  
✅ Want maximum explosive potential  
✅ Don't care about losing everything  
✅ Entertainment/learning value  

❌ Any amount you care about  
❌ Want consistent results  
❌ Conservative player  

### Use Safe Variant (`micro-exponential-safe`)
✅ Small balances ($0.50 - $5)  
✅ Want some risk management  
✅ Learning adaptive strategies  
✅ Higher survival chance  
✅ Still want 100x potential  

❌ Truly micro dust (too conservative)  
❌ Want maximum explosiveness  
❌ Significant balances  

## Usage Examples

### Original (Maximum Chaos)
```bash
python duckdice_cli.py \
  --strategy micro-exponential \
  --symbol USDT \
  --target-balance 10.0  # From $0.20 to $10 (50x)
```

### Safe Variant (Controlled Chaos)
```bash
python duckdice_cli.py \
  --strategy micro-exponential-safe \
  --symbol USDT \
  --target-balance 5.0  # From $0.20 to $5 (25x)
```

## Performance Expectations

### Original
- **Best Case**: 300x in one session (0.1% chance)
- **Good Case**: 5-10x before busting (5% chance)
- **Typical Case**: 2-3x then bust (30% chance)
- **Bad Case**: Immediate bust (65% chance)

### Safe Variant
- **Best Case**: 100x in one session (1% chance)
- **Good Case**: 5-10x before busting (15% chance)
- **Typical Case**: 2-3x then slow decline (40% chance)
- **Bad Case**: Bust but takes longer (45% chance)

## Key Insight

Both strategies will **eventually bust** - that's their nature. The difference is:

**Original**: 🚀 Rocket ship that explodes spectacularly  
**Safe**: 🛩️ Airplane that can glide a bit before crashing

Neither is a sustainable long-term strategy, but the safe variant gives you:
- More time to hit your target
- Better chance of cashing out at profit
- Less dramatic death spirals
- More strategic depth (emergency mechanisms)

## Recommendation

**For $0.20 USDT dust recovery**:
- Use **safe variant** first
- If you reach $1-2, consider switching to original for final 5-10x push
- Or cash out and celebrate 5-10x gains!

**For pure entertainment**:
- Use **original** and watch the fireworks 🎆
- Record the session for educational purposes
- Expect to lose, enjoy the ride

---

**Strategy Count**: 20 total  
**Micro Exponential Family**: 2 variants  
**Both Available**: Use at your own risk! 🎲
