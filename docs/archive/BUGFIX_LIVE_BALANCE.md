# Live Mode Balance Bug Fix

**Date:** 2026-01-12  
**Status:** ✅ FIXED  
**Version:** 4.3.1

## Problem

When running the bot in live mode, the starting balance was always showing as 0 instead of the actual account balance. This caused strategies to immediately fail with "Balance (0) < minBet" errors.

### Example

```
✓ Selected: DECOY (Balance: 79.73333120)  # Shows correct balance in UI
...
Starting Balance: 0                        # But strategy sees 0!
⛔ STOP: Balance (0) < minBet (0.01)
```

## Root Cause

The `_parse_user_symbol_balance()` function in `src/betbot_engine/engine.py` was performing **case-sensitive** string comparison:

```python
if (b or {}).get("currency") == symbol:  # Case-sensitive!
```

The DuckDice API returns currency codes in **UPPERCASE** (e.g., `"DECOY"`, `"BTC"`), but the CLI was passing **lowercase** symbols (e.g., `"decoy"`, `"btc"`), causing no match and returning 0.

## Solution

Changed the comparison to be **case-insensitive**:

```python
symbol_upper = symbol.upper()
for b in balances:
    currency = (b or {}).get("currency")
    if currency and currency.upper() == symbol_upper:
        # ... rest of code
```

## Files Changed

1. **src/betbot_engine/engine.py** (lines 130-141)
   - Made `_parse_user_symbol_balance()` case-insensitive
   - Improved error handling

2. **duckdice_cli.py** (lines 91-112)
   - Updated `MockDuckDiceAPI` to use uppercase currency codes
   - Added more currencies (DECOY, PEPE, TRUMP, etc.)
   - Enabled printer in run_strategy() for debugging

## Testing

✅ All 5 CLI tests passing  
✅ Live mode now correctly reads DECOY balance (79.73)  
✅ Simulation mode still works (balance=100)  
✅ Case-insensitive comparison verified

## Before vs After

| Scenario | Before | After |
|----------|--------|-------|
| Live DECOY | 0 ❌ | 79.73 ✅ |
| Live BTC | 0 ❌ | 0.001 ✅ |
| Simulation | 100 ✅ | 100 ✅ |

## Impact

- **Live betting now works correctly** - strategies can actually place bets
- **No impact on simulation mode** - still works as before
- **Backward compatible** - accepts both uppercase and lowercase symbols

## Related Issues

This also fixed the pre-live simulation preview feature, which was showing balance=0 when testing with DECOY (MockDuckDiceAPI didn't have DECOY currency defined).

---

**Next Steps:** User should test live betting with small amounts to verify end-to-end functionality.
