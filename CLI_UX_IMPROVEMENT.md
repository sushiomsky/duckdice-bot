# CLI UX Improvement - Auto-Mode Detection

## Feature: Smart Mode Auto-Detection

### Problem
Users had to answer mode selection prompt (simulation/live-main/live-faucet) every time, even when they had saved API key and clearly wanted live mode.

### Solution
Auto-detect live mode when API key is found in config.

## Changes Made

### Logic Update (`duckdice_cli.py`)
```python
# OLD: Always prompt for mode
mode = prompt_choice("Select betting mode:", ...)

# NEW: Check API key first
api_key = args.api_key or config_mgr.config.get('api_key')
if args.mode:
    mode = args.mode  # CLI arg takes precedence
elif api_key:
    mode = 'live-main'  # Auto-select if API key exists
else:
    mode = prompt_choice(...)  # Prompt only if no API key
```

## Behavior

### Scenario 1: No API Key Saved
```bash
$ python3 duckdice_cli.py run -s streak-hunter

# Prompts for mode (simulation/live-main/live-faucet)
Select betting mode:
  1. simulation (default)
  2. live-main
  3. live-faucet
```

### Scenario 2: API Key Saved
```bash
$ python3 duckdice_cli.py run -s streak-hunter -c btc --max-bets 100

# NO PROMPT - auto-selects live-main mode
# Uses saved API key automatically
# Goes straight to betting
```

### Scenario 3: Force Simulation
```bash
$ python3 duckdice_cli.py run -m simulation -s streak-hunter

# Uses simulation mode even if API key exists
# CLI arg overrides auto-detection
```

## Benefits

✅ **Faster workflow** - Skip unnecessary prompt  
✅ **Smart defaults** - API key presence indicates live intent  
✅ **Still flexible** - Can override with `-m simulation`  
✅ **Better UX** - Less friction for repeat users

## Testing

```bash
# Test 1: No API key → Prompts
rm ~/.duckdice/config.json
python3 duckdice_cli.py run -s classic-martingale
# Result: ✅ Prompts for mode

# Test 2: API key saved → Auto live
echo '{"api_key":"test123"}' > ~/.duckdice/config.json
python3 duckdice_cli.py run -s classic-martingale
# Result: ✅ Auto-selects live mode (no prompt)

# Test 3: Force simulation
python3 duckdice_cli.py run -m simulation -s classic-martingale
# Result: ✅ Uses simulation despite API key
```

## Version
**4.7.0 → 4.7.1**

## Files Modified
- `duckdice_cli.py` - Auto-mode detection logic
- `src/cli_display.py` - Version bump to 4.7.1

## Breaking Changes
**None** - Fully backward compatible!

---

**Status**: ✅ Complete and tested  
**Date**: 2026-01-13
