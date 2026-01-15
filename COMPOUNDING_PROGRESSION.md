# Streak Hunter - Compounding Progression Fix

**Date:** 2026-01-12  
**Version:** 4.4.0 → 4.5.0  
**Change:** Compounding bet progression + No lottery during streaks

## Changes Made

### 1. Compounding Bet Progression

**Before (Linear - WRONG):**
```
Base bet = 1.0
Win 1: Bet = 1.0 × 2.0 = 2.0
Win 2: Bet = 1.0 × 1.8 = 1.8  ❌ (smaller than previous!)
Win 3: Bet = 1.0 × 1.6 = 1.6  ❌
Win 4: Bet = 1.0 × 1.4 = 1.4  ❌
```

**After (Compounding - CORRECT):**
```
Base bet = 1.0
Win 1: Bet = 1.0 × 2.0 = 2.0
Win 2: Bet = 2.0 × 1.8 = 3.6  ✅ (compounds!)
Win 3: Bet = 3.6 × 1.6 = 5.76 ✅
Win 4: Bet = 5.76 × 1.4 = 8.06 ✅
```

### 2. No Lottery During Streaks

**Before:**
- Lottery could interrupt an active streak
- Confusing behavior

**After:**
- Lottery ONLY when `streak = 0`
- Never disrupts progression
- Clear separation between strategies

## Implementation

### Code Changes

**File:** `src/betbot_strategies/streak_hunter.py`

**Added state tracking (line 173):**
```python
self._last_bet_amount = Decimal("0")  # Track previous bet for compounding
```

**Fixed bet calculation (lines 230-241):**
```python
def _calculate_bet_amount(self) -> Decimal:
    if self._win_streak == 0:
        return self._current_base
    else:
        # Multiply PREVIOUS BET by multiplier (compounding!)
        multiplier = self._get_multiplier_for_streak(self._win_streak)
        previous_bet = self._last_bet_amount if self._last_bet_amount > 0 else self._current_base
        amount = previous_bet * Decimal(str(multiplier))
        return amount
```

**Store bet amount in next_bet() (line 278):**
```python
# Store this bet amount for next progression calculation
self._last_bet_amount = amount
```

**Lottery only when streak = 0 (line 254):**
```python
# Check if lottery bet (ONLY when not on a streak!)
if self.lottery_enabled and self._win_streak == 0 and self._total_bets % self.lottery_frequency == 0:
```

**Reset on loss (line 348):**
```python
self._last_bet_amount = Decimal("0")  # Reset bet tracking
```

## Progression Comparison

| Streak | Old (Linear) | New (Compounding) | Difference |
|--------|-------------|-------------------|------------|
| 0 | 1.00 | 1.00 | - |
| 1 | 2.00 | 2.00 | - |
| 2 | 1.80 | 3.60 | +100% ✅ |
| 3 | 1.60 | 5.76 | +260% ✅ |
| 4 | 1.40 | 8.06 | +476% ✅ |
| 5 | 1.20 | 9.68 | +706% ✅ |
| 6 | 1.00 | 9.68 | +868% ✅ |

## Example Session

### Old Behavior (Linear)
```
Bet 1: 1.0 @ 14% → WIN (streak = 1)
Bet 2: 2.0 @ 14% → WIN (streak = 2)
Bet 3: 1.8 @ 14% → WIN (streak = 3)  ❌ went DOWN
Bet 4: 1.6 @ 14% → WIN (streak = 4)  ❌ went DOWN again
Bet 10: 1.0 @ 1.5% → 🎰 LOTTERY (during streak!) ❌ confusing
```

### New Behavior (Compounding)
```
Bet 1: 1.0 @ 14% → WIN (streak = 1)
Bet 2: 2.0 @ 14% → WIN (streak = 2)
Bet 3: 3.6 @ 14% → WIN (streak = 3)  ✅ compounds!
Bet 4: 5.76 @ 14% → WIN (streak = 4) ✅ keeps growing!
Bet 5: 8.06 @ 14% → LOSE (reset)
Bet 6: 1.0 @ 14% → Continue
...
Bet 10: 1.0 @ 1.5% → 🎰 LOTTERY (only when streak = 0) ✅
```

## Mathematical Impact

### Risk Analysis

With compounding, streaks become much more profitable but also riskier:

**4-Win Streak:**
- Old: Total wagered = 1.0 + 2.0 + 1.8 + 1.6 = 6.4
- New: Total wagered = 1.0 + 2.0 + 3.6 + 5.76 = 12.36
- **+93% more wagered**

**Profit Potential:**
At 14% chance (~7x payout):
- Old 4-win: ~45 profit (7x × 6.4)
- New 4-win: ~86.5 profit (7x × 12.36)
- **+92% more profit!**

### Risk Management

The compounding makes streaks more powerful but also riskier:

**Recommendation:**
- Lower your base bet (e.g., balance/500 instead of /300)
- Set stricter stop-loss (-15% instead of -30%)
- Take profit earlier (+30% instead of +50%)
- Be more conservative with multipliers

**Example Conservative Setup:**
```bash
python3 duckdice_cli.py run \
  -m live-main -s streak-hunter -c decoy \
  --param balance_divisor=500 \
  --param first_multiplier=1.5 \
  --param second_multiplier=1.3 \
  --param third_multiplier=1.2 \
  --stop-loss -0.15 \
  --take-profit 0.3
```

## Lottery Behavior

### Before
Lottery could happen anytime based on bet count, even during a streak.

### After
Lottery ONLY happens when `streak = 0`:
- After a loss (streak reset)
- At session start
- After a lottery bet itself

This prevents lottery from disrupting your streak progression.

## Benefits

### Compounding
✅ **Accelerated Growth** - Profits multiply much faster  
✅ **Intuitive** - Each bet builds on the last  
✅ **Exciting** - Watching bets grow is thrilling  
⚠️ **Higher Risk** - Losses hurt more after long streaks

### No Lottery During Streaks
✅ **Clarity** - Two distinct strategies don't mix  
✅ **Protection** - Streak progression uninterrupted  
✅ **Predictability** - Know exactly when lottery happens

## Testing

✅ All 5 CLI tests passing  
✅ Compounding verified (1.0 → 2.0 → 3.6 → 5.76...)  
✅ Lottery only at streak = 0  
✅ Bet tracking working correctly

## Files Modified

1. **src/betbot_strategies/streak_hunter.py**
   - Lines 1-28: Updated documentation
   - Line 38: Updated description
   - Line 173: Added `_last_bet_amount` tracking
   - Lines 185-187: Reset bet amount on session start
   - Lines 230-241: Compounding calculation
   - Line 254: Lottery only when streak = 0
   - Line 278: Store bet amount
   - Line 348: Reset on loss

## Recommendations

### For Existing Users
If you were using the old linear progression:
1. **Lower your base bet** by 40-50%
2. **Reduce multipliers** to 1.5x/1.3x/1.2x
3. **Set tighter stop-loss** at -15% to -20%
4. **Test in simulation first!**

### For New Users
The new compounding progression is more aggressive:
- Start with balance/500 (instead of /300)
- Use default multipliers (2.0x/1.8x/1.6x)
- Set stop-loss at -20%
- Set take-profit at +30% to +50%

### Example Conservative Config
```bash
--param balance_divisor=500
--param first_multiplier=1.4
--param second_multiplier=1.25
--param third_multiplier=1.15
--param multiplier_decrease=0.1
```

This gives: 1.0 → 1.4 → 1.75 → 2.01 → 2.21 (much safer)

## Summary

The streak-hunter strategy now uses **true compounding** where each bet is a percentage increase from the previous bet, creating exponential growth on winning streaks. Lottery bets are now isolated to non-streak moments, preventing confusion.

**Impact:**
- 📈 **Higher reward potential** (+100% to +800% on streaks)
- ⚠️ **Higher risk** (more capital at stake)
- 🎯 **Clearer strategy** (lottery separate from streaks)
- ✅ **Production ready**

---

**Version:** 4.5.0  
**Status:** Production Ready ✅  
**Feature:** Compounding Progression + Lottery Isolation
