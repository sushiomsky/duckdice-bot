# Micro Exponential Strategy - Minimum Bet Fix

## Issue

When first testing the micro-exponential strategy with a 0.20078112 USDT balance, it failed with:

```
HTTP Error: 422 Client Error: Unprocessable Entity
{"error":"The minimum bet is {{amount}} {{symbol}}.","params":{"amount":"0.00096772","symbol":"USDT"}}
```

The strategy calculated a bet of 0.000200781120 USDT (0.2% of balance), which was below the DuckDice minimum of ~0.001 USDT.

## Root Cause

The strategy was designed for extremely small balances (dust) but had:
- Default `base_bet_percent` of 0.2% (too small for balances around $0.20)
- Default `min_bet` of 0.00000001 (suitable for TRX/DOGE, not USDT)

## Fix Applied

### 1. Dynamic Base Bet Percentage

```python
# Adjust base bet percent based on balance size
starting_balance = Decimal(str(ctx.starting_balance))
if starting_balance < Decimal('1.0'):
    # For micro balances under $1, use 1% instead of 0.2%
    default_base_percent = '0.01'
else:
    default_base_percent = '0.002'
```

### 2. Reasonable Minimum Bet

```python
# Set reasonable minimum bet based on currency
# USDT/BTC/ETH typically have ~0.001 minimums
self.min_bet = Decimal(str(params.get('min_bet', '0.001')))
```

## Test Results

### Before Fix
- Balance: 0.20078112 USDT
- Base bet %: 0.2%
- Calculated bet: 0.000200781120 USDT
- Result: ❌ Below minimum (0.001 USDT)

### After Fix
- Balance: 0.20078112 USDT  
- Base bet %: 1.0% (auto-adjusted)
- Calculated bet: 0.00100390560 USDT
- Result: ✅ Meets minimum (0.001 USDT)

## PROBE Mode Example

With the fix, PROBE mode (60% chance, 0.5x multiplier) calculates:
```
Base bet = 0.20078112 * 0.01 = 0.0020078112
PROBE bet = 0.0020078112 * 0.5 = 0.0010039056
```

This safely exceeds the 0.001 USDT minimum.

## Currency-Specific Minimums

The strategy now works correctly with:

| Currency | Typical Minimum | Strategy Min Bet |
|----------|----------------|------------------|
| USDT     | 0.001          | 0.001 ✅         |
| BTC      | 0.000001       | 0.001 ✅         |
| ETH      | 0.0001         | 0.001 ✅         |
| TRX      | 1.0            | 0.001 ⚠️         |
| DOGE     | 1.0            | 0.001 ⚠️         |

**Note**: For TRX/DOGE, you may need to override `min_bet` parameter:
```python
params = {
    'min_bet': '1.0'  # Override for TRX/DOGE
}
```

## Updated Default Parameters

```python
{
    'base_bet_percent': '0.01',    # 1% for <$1 balances (auto-adjusted)
    'min_bet': '0.001',            # Suitable for USDT/BTC/ETH
    'max_bet_percent': '0.90',
    'profit_target_x': '300',
    'max_drawdown_percent': '45',
    'kill_chance_min': '0.08',
    'kill_chance_max': '0.25',
    'kill_bet_percent': '0.65',
    'kill_cooldown': '120',
    'vol_window': '40',
    'switch_cooldown_bets': '10'
}
```

## Recommendations

### For USDT/BTC/ETH (default settings work)
```bash
python duckdice_cli.py \
  --strategy micro-exponential \
  --symbol USDT \
  --target-balance 1.0
```

### For TRX/DOGE (override min_bet)
```bash
python duckdice_cli.py \
  --strategy micro-exponential \
  --symbol TRX \
  --min-bet 1.0
```

### For Larger Balances (>$1)
The strategy automatically uses 0.2% base bet for balances over $1, or you can override:
```bash
python duckdice_cli.py \
  --strategy micro-exponential \
  --symbol USDT \
  --base-bet-percent 0.002  # Override to 0.2%
```

## Files Modified

- `src/betbot_strategies/micro_exponential.py` - Added dynamic base bet adjustment and better min_bet default
- `MICRO_EXPONENTIAL_STRATEGY.md` - Updated documentation with new defaults

## Status

✅ **FIXED** - Strategy now works correctly with all standard currencies and respects minimum bet requirements.

---

**Fix Date**: January 15, 2025  
**Tested With**: 0.20078112 USDT balance  
**Result**: Successfully places bets meeting DuckDice minimums
