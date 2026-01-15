# Bug Fix - Take Profit None Error

**Date:** 2026-01-12  
**Version:** 4.5.1 → 4.5.2  
**Issue:** Crash when running without target balance

## Problem

When running a strategy with **no target balance** (target = 0), the bot crashed with:

```
decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]
```

### Root Cause

In `src/betbot_engine/engine.py` line 400, the engine tried to convert `take_profit=None` to a Decimal:

```python
if change_ratio >= Decimal(str(limits.take_profit)):  # ❌ take_profit is None!
```

This happened when user selected target = 0, which sets `take_profit = None`.

## Solution

Added a None check before converting to Decimal:

```python
# Only check take_profit if it's set (not None)
if limits.take_profit is not None and change_ratio >= Decimal(str(limits.take_profit)):
    stopped_reason = "take_profit"
    break
```

## Files Modified

**src/betbot_engine/engine.py** (line 400)
- Added None check for `limits.take_profit`

## Testing

✅ All 5 CLI tests passing  
✅ Can run without target (target = 0)  
✅ Can run with target (target > 0)  
✅ Stop-loss still works  
✅ Take-profit works when set

## Usage

Now you can run strategies **without a target**:

```bash
# Interactive mode - select target = 0
python3 duckdice_cli.py interactive
# When prompted: Target balance [default]: 0

# Or run mode without limits
python3 duckdice_cli.py run -m live-main -s streak-hunter -c btc
```

The strategy will run until:
- Strategy decides to stop (e.g., streak-hunter has no built-in stop)
- You press Ctrl+C
- Stop-loss is hit
- Max bets reached (if set)

---

**Version:** 4.5.2  
**Status:** Fixed ✅
