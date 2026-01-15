# Bug Fix - Lottery Invalid Chance Error

**Date:** 2026-01-12  
**Version:** 4.5.2 → 4.5.3  
**Issue:** Lottery bets failing with "Invalid chance" error

## Problem

When lottery feature was enabled, the bot would crash on lottery bets with:

```
HTTP Error: 422 Client Error: Unprocessable Entity
Response: {"error":"Invalid chance."}
```

Example:
```
🎰 LOTTERY BET #1! Chance: 3.71% (up to 27x payout!)
HTTP Error: 422 - Invalid chance.
```

### Root Cause

The lottery chance was generated as a floating-point number with many decimal places:
```python
lottery_chance = self.ctx.rng.uniform(0.01, 4.0)
# Result: 3.7123456789012345 (too many decimals!)
```

DuckDice API expects chance values with **exactly 2 decimal places** (e.g., "3.71" not "3.7123456789").

## Solution

Added rounding and proper formatting:

```python
# Generate random chance
lottery_chance = self.ctx.rng.uniform(lottery_chance_min, lottery_chance_max)
# Round to 2 decimal places
lottery_chance = round(lottery_chance, 2)

# Format to exactly 2 decimal places
return {
    "chance": f"{lottery_chance:.2f}",  # "3.71" not "3.7123456789"
}
```

## Files Modified

**src/betbot_strategies/streak_hunter.py** (lines 261-274)
- Added `round(lottery_chance, 2)` 
- Changed chance format from `str(lottery_chance)` to `f"{lottery_chance:.2f}"`
- Added safety check for payout calculation

## Testing

✅ All 5 CLI tests passing  
✅ Lottery chances formatted correctly (2 decimals)  
✅ API accepts formatted chances  
✅ Payout calculation safe (division by zero check)

## Examples

**Before (FAIL):**
```python
chance = 3.7123456789
"chance": str(3.7123456789)  # → "3.7123456789" ❌ API rejects
```

**After (WORKS):**
```python
chance = round(3.7123456789, 2)  # → 3.71
"chance": f"{3.71:.2f}"          # → "3.71" ✅ API accepts
```

## Impact

The lottery feature now works correctly with all chance ranges:
- 0.01% → "0.01" ✅
- 1.5% → "1.50" ✅  
- 3.71% → "3.71" ✅
- 4.0% → "4.00" ✅

## Related Issues

This fix also resolves:
- Random API rejections on lottery bets
- Inconsistent lottery behavior
- "Invalid chance" errors

---

**Version:** 4.5.3  
**Status:** Fixed ✅  
**Feature:** Lottery bets now work reliably
