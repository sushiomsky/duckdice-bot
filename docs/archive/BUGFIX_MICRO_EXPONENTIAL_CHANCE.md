# Micro Exponential Strategy - Invalid Chance Fix

## Issue #2: Invalid Chance Error

After fixing the minimum bet issue, a second error occurred:

```
HTTP Error: 422 Client Error: Unprocessable Entity
Response: {"error":"Invalid chance."}
```

## Root Cause

The strategy was returning a bet specification in the wrong format:

### Incorrect Format
```python
return {
    'amount': str(betsize),
    'chance': str(chance),  # Could have many decimal places
    'prediction': 'over' if random.random() > 0.5 else 'under'  # Wrong key
}
```

### Issues
1. **Missing `game` key**: Required to specify dice game type
2. **Wrong prediction format**: Used `'prediction': 'over'/'under'` instead of `'is_high': bool`
3. **Unformatted chance**: Decimal values like "60.0" or "0.12836184490003433" not formatted
4. **Missing `is_high` key**: Required boolean for over/under bet

## Fix Applied

### Correct Format
```python
# Format chance to 2 decimal places for API compatibility
chance_formatted = f"{float(chance):.2f}"

return {
    'game': 'dice',                    # Required: game type
    'amount': str(betsize),             # Amount as string
    'chance': chance_formatted,         # Formatted to 2 decimals (e.g., "60.00")
    'is_high': random.random() > 0.5    # Boolean for over/under
}
```

### Changes
1. ✅ Added `'game': 'dice'` - Required by API
2. ✅ Changed `'prediction'` to `'is_high'` - Correct key name
3. ✅ Format boolean instead of string - API expects `True`/`False` not `'over'`/`'under'`
4. ✅ Format chance to 2 decimals - "60.00" instead of "60.0" or "60.123456"

## Test Results

### Before Fix
```python
{
    'amount': '0.00100390560',
    'chance': '60.0',
    'prediction': 'under'
}
```
Result: ❌ `{"error":"Invalid chance."}`

### After Fix
```python
{
    'game': 'dice',
    'amount': '0.00100390560',
    'chance': '60.00',
    'is_high': False
}
```
Result: ✅ Accepted by API

## Comparison with Other Strategies

### Classic Martingale (Reference)
```python
def next_bet(self) -> Optional[BetSpec]:
    return {
        "game": "dice",
        "amount": format(self._current_amount, 'f'),
        "chance": self.chance,
        "is_high": self.is_high,
    }
```

### Micro Exponential (Now Fixed)
```python
def next_bet(self) -> BetSpec:
    # ... calculate chance and betsize ...
    chance_formatted = f"{float(chance):.2f}"
    
    return {
        'game': 'dice',
        'amount': str(betsize),
        'chance': chance_formatted,
        'is_high': random.random() > 0.5
    }
```

## API Requirements

DuckDice API expects bet specifications with:

| Field    | Type   | Required | Format                    |
|----------|--------|----------|---------------------------|
| game     | string | Yes      | "dice"                    |
| amount   | string | Yes      | Decimal string            |
| chance   | string | Yes      | Number as string (0.01-98)|
| is_high  | bool   | Yes      | true/false                |

## All Modes Now Working

All 5 betting modes now return valid bet specifications:

1. **PROBE** - `chance: "60.00"` ✅
2. **PRESSURE** - `chance: "18.00"` ✅
3. **HUNT** - `chance: "0.12"` to `"0.20"` ✅
4. **CHAOS** - `chance: "5.00"` to `"70.00"` ✅
5. **KILL** - `chance: "0.08"` to `"0.25"` ✅

## Files Modified

- `src/betbot_strategies/micro_exponential.py` - Fixed `next_bet()` return format

## Combined Fixes Summary

### Fix #1: Minimum Bet
- Changed default `min_bet` from 0.00000001 to 0.001
- Added dynamic `base_bet_percent` adjustment for balances <$1

### Fix #2: Invalid Chance
- Added `'game': 'dice'` key
- Changed `'prediction'` to `'is_high'` with boolean value
- Format chance to 2 decimal places

## Status

✅ **FULLY FIXED** - Strategy now works correctly with live API:
- ✅ Respects minimum bet requirements
- ✅ Returns valid bet specifications
- ✅ All 5 modes operational
- ✅ Ready for live trading

---

**Fix Date**: January 15, 2025  
**Issues Fixed**: 2 (minimum bet, invalid chance)  
**Status**: Ready for Production
