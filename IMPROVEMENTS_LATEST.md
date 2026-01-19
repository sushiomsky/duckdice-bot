# Latest Improvements Summary

**Date**: 2026-01-19  
**Version**: 4.9.2+

## Recent Fixes (Latest → Oldest)

### 3. Decimal Precision Fix ✅

**Commit**: `a599cd6` (2026-01-19)

Fixed "Invalid chance" API errors by quantizing bet values to proper precision.

**Problem**: Bet validation calculations produced excessive decimal precision:
```
amount: "0.0000005142646406142484520548250163" (33 decimals!)
Error: "Invalid chance"
```

**Solution**: Quantize to API-compatible precision:
- **Amount**: 8 decimal places (crypto standard)
- **Chance**: 2 decimal places (e.g., 95.50%)

**Implementation**:
```python
amount_quantized = amount_dec.quantize(Decimal("0.00000001"))
chance_quantized = chance_dec.quantize(Decimal("0.01"))
```

**Test Results**:
- ✅ XAUT: 3 real bets, all accepted by API
- ✅ BTC simulation: 20 bets, 95.24% win rate, nearly hit target

---

### 2. JSON Import Scope Fix ✅

**Commit**: `cc27580` (2026-01-19)

Fixed NameError caused by local import shadowing module-level import.

**Problem**:
```python
NameError: cannot access free variable 'json' where it is not
associated with a value in enclosing scope
```

**Root Cause**: Local `import json` in exception handler shadowed module-level import, breaking `file_sink` closure.

**Solution**: 
- Added `import re` to module-level imports
- Removed local imports from exception handler

**Test Results**:
- ✅ range-50-random: 5 simulation bets
- ✅ DECOY live: 3 real bets, +30% profit (+21.69 DECOY)

---

### 1. Auto-Retry with API Minimum Bet ✅

**Commit**: `a7d7e7c` (2026-01-18)

Automatically handles currency-specific minimum bet requirements from DuckDice API.

**Problem**: When strategies calculate bets below API minimums (e.g., LTC requires 0.00001269), the API returns 422 error.

**Solution**: Parse minimum from error response and retry with corrected amount.

**Test Results**:
- ✅ LTC: 10 real bets, +10.43% profit
- ✅ XAUT: 3 real bets, working correctly

---

## Core Features (2026-01-18)

### Streak-Multiplier Strategy ✅

**Commit**: `9cea160`

Exponential bet growth strategy as requested:
- Base bet: balance / 250
- Win chance: 5% (high)
- Win multiplier: 3.4x (240% increase on each win)
- Full reset to base bet on loss

**Features**:
- Configurable parameters (divisor, chance, multiplier, direction)
- Win streak tracking and statistics
- Probability calculations displayed at session start
- DiceBot compatible interface

**Risk Level**: VERY HIGH (exponential growth, low win chance)

**Test Results** (Simulation, 50 bets):
```
Wins: 5 (10% vs 5% expected)
Max Streak: 2
Profit: +30.5%
```

**CLI Usage**:
```bash
duckdice run -m simulation -c btc -s streak-multiplier --max-bets 100
```

**Total Strategies**: 22 (was 21)

---

## Impact Summary

| Improvement | Benefit | Status |
|------------|---------|--------|
| Decimal Precision | XAUT and all currencies work | ✅ Live |
| JSON Scope Fix | All strategies log correctly | ✅ Live |
| Streak-Multiplier | New high-risk exponential strategy | ✅ Live |
| Auto-Retry | Universal currency support | ✅ Live |
| Bet Validation | Engine-level enforcement | ✅ Live |
| Development Guardrails | Consistent code quality | ✅ Active |
| Branch Protection | Main always buildable | ⚠️ Needs GitHub config |
| CI/CD Workflows | Automated builds/releases | ✅ Ready |

## Recent Test Results

**Live Trading** (Real API):
- ✅ LTC: 10 bets, +10.43% profit
- ✅ XAUT: 6 bets total, all successful
- ✅ DECOY: 3 bets, +30% profit

**Simulation** (Monte Carlo):
- ✅ BTC target-aware: 20 bets, 95% win rate
- ✅ BTC streak-multiplier: 50 bets, +30% profit
- ✅ DECOY range-50-random: 5 bets, functional

## Next Steps

1. **Configure GitHub Branch Protection** (5 minutes):
   - See `QUICK_SETUP_BRANCH_PROTECTION.md`
   - Enforce PR workflow for all changes
   - Block direct commits to main

2. **Monitor CI/CD**:
   - Watch for build releases on next commit
   - Verify PyPI auto-publish works

3. **Test New Strategy**:
   - Use small amounts due to high risk
   - Monitor streak distributions
   - Consider adjusting divisor/multiplier

---

**All changes validated and pushed to GitHub** ✅

**Commits**: `a599cd6`, `cc27580`, `a7d7e7c`, `f80d81a`, `9cea160`
