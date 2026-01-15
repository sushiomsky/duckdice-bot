# HTML Report Data Consistency Issues - Analysis

## Report: report2.html
**Generated:** 2026-01-15  
**Strategies Tested:** 16  
**Runs per Strategy:** 100  
**Bets per Run:** 10,000  

---

## Issues Found

### 1. ❌ **Summary Card Calculations Incorrect**

**Location:** Lines 201-206

#### Avg Positive Return
```html
<div class="summary-card">
    <h3>Avg Positive Return</h3>
    <div class="value positive">-0.00%</div>  ❌ NEGATIVE value with "positive" class
</div>
```

**Problem:** Shows `-0.00%` but has class "positive"
- Should either be positive value OR have "negative" class
- Logic error in calculating average of positive strategies only

#### Avg Negative Return
```html
<div class="summary-card">
    <h3>Avg Negative Return</h3>
    <div class="value negative">-100.00%</div>  ❌ Extreme outlier
</div>
```

**Problem:** -100.00% is caused by target-aware strategy
- Target-aware places 0 bets, shows -100% profit (calculation error)
- This outlier should be excluded or handled specially

---

### 2. ❌ **target-aware Strategy Data Invalid**

**Table Data:**
| Metric | Value | Issue |
|--------|-------|-------|
| Bets Placed | 0 | ❌ Placed no bets across 100 runs |
| Win Rate | 0.00% | Expected (no bets) |
| Ending Balance | 10.000000 | Same as starting |
| **Profit %** | **-100.00%** | ❌ **WRONG** - should be 0.00% |
| Median % | -100.00% | ❌ Should be 0.00% |
| Best % | -100.00% | ❌ Should be 0.00% |
| Worst % | -100.00% | ❌ Should be 0.00% |
| Bust Rate | 0.0% | Correct |

**Root Cause:**
```python
# In strategy_comparison.py, profit calculation:
profit_percent = (ending_balance - starting_balance) / starting_balance * 100
# When ending_balance = starting_balance = 10.0:
profit_percent = (10.0 - 10.0) / 10.0 * 100 = 0.0%  # ✅ Correct

# BUT, target-aware places 0 bets, so it might be hitting a different code path
# that incorrectly initializes or calculates the profit_percent field
```

**Issue:** The strategy completes immediately (target already reached), placing 0 bets.
The metrics calculation appears to have a bug where 0 bets results in -100% instead of 0%.

---

### 3. ⚠️ **range-50-random Strategy Extreme Variance**

**Table Data:**
| Metric | Value | Analysis |
|--------|-------|----------|
| Avg Profit % | -41.48% | Poor average |
| Median % | -99.06% | Most runs nearly busted |
| **Best %** | **+1083.57%** | ❌ 10x gain! Extreme outlier |
| Worst % | -99.18% | Nearly busted |
| Std Dev | 251.12 | ❌ HUGE variance |
| Bets Placed | 407 | Avg stopped early |

**Issues:**
1. **Best run showing +1083.57%** suggests possible:
   - Calculation error in profit_percent
   - Extreme win streak that's statistically unlikely
   - Bug in the strategy logic causing massive bet sizes

2. **Standard deviation of 251.12** is abnormally high
   - Normal strategies: 0.00 - 0.20
   - This strategy: 251.12 (1000x higher!)
   - Indicates massive swings between runs

3. **Only 407 bets average** (vs 10,000 max)
   - Strategy stopping early due to bust or extreme conditions
   - Most runs hit stop-loss at -99%

**Likely Cause:** This is a high-variance strategy that randomly bets 50% of balance.
One lucky run could genuinely 10x the balance, but most runs bust.

---

### 4. ⚠️ **Duration Field Always 0.00s**

**All Strategies Show:**
```html
<div class="metric-label">Duration</div>
<div class="metric-value">0.00s</div>
```

**From code (strategy_comparison.py line 217):**
```python
'duration_sec': 0.0,  # Not applicable for Monte Carlo
```

**Issue:** Field is hardcoded to 0.0 because Monte Carlo simulations don't track time.

**Fix Options:**
1. Remove duration field from Monte Carlo reports
2. Change label to "Duration (N/A for simulation)"
3. Track actual simulation wall-clock time

---

### 5. ✅ **Other Data Appears Consistent**

**Verified Correct:**
- Top performing strategies showing realistic -0.00% to +0.00% (house edge)
- Win rates clustered around 49.5-50.0% (expected for 50% chance bets)
- Bust rates near 0% for conservative strategies
- Bets placed = 10,000 for most strategies (completed full runs)
- Standard deviations reasonable (0.00-0.20) for most strategies

---

## Required Fixes

### Priority 1: Critical Data Errors

#### Fix 1: target-aware -100% profit bug
**File:** `strategy_comparison.py`
**Location:** Profit percent calculation in run_strategy()

**Current Logic:**
```python
if run_metrics['bets_placed'] > 0:
    run_metrics['profit_percent'] = (run_metrics['profit'] / self.starting_balance) * 100
# If bets_placed = 0, profit_percent field not set → defaults to ???
```

**Fix:**
```python
if run_metrics['bets_placed'] > 0:
    run_metrics['win_rate'] = (run_metrics['wins'] / run_metrics['bets_placed']) * 100
    run_metrics['profit'] = run_metrics['ending_balance'] - self.starting_balance
    run_metrics['profit_percent'] = (run_metrics['profit'] / self.starting_balance) * 100
else:
    # No bets placed - set sensible defaults
    run_metrics['win_rate'] = 0.0
    run_metrics['profit'] = 0.0
    run_metrics['profit_percent'] = 0.0
```

#### Fix 2: Summary card calculations
**File:** `strategy_comparison.py`
**Location:** generate_html_report() summary stats

**Current (implied):**
```python
avg_positive = average of all strategies where avg_profit_percent > 0
avg_negative = average of all strategies where avg_profit_percent < 0
```

**Issues:**
1. If NO strategies are positive, avg_positive shows negative number
2. Outliers like target-aware (-100%) skew avg_negative

**Fix:**
```python
# Calculate averages excluding invalid/outlier results
positive_profits = [r['avg_profit_percent'] for r in valid_results 
                   if r['avg_profit_percent'] > 0 and r['bets_placed'] > 0]
negative_profits = [r['avg_profit_percent'] for r in valid_results 
                   if r['avg_profit_percent'] < 0 and r['bets_placed'] > 0]

avg_positive = sum(positive_profits) / len(positive_profits) if positive_profits else 0.0
avg_negative = sum(negative_profits) / len(negative_profits) if negative_profits else 0.0

# Fix CSS class logic
positive_class = "positive" if avg_positive > 0 else "neutral"
negative_class = "negative" if avg_negative < 0 else "neutral"
```

### Priority 2: Display Improvements

#### Fix 3: Handle extreme outliers in display
- Add warning badge for strategies with std dev > 100
- Flag "best%" values > 500% as potential anomalies
- Add tooltip explaining variance for range-50-random

#### Fix 4: Duration field
- Either remove or change to "Simulation Time (N/A)"
- Or track actual wall-clock time per strategy

---

## Summary

| Issue | Severity | Impact | Status |
|-------|----------|--------|--------|
| target-aware shows -100% profit | 🔴 Critical | Incorrect data | Needs Fix |
| Avg Positive Return negative | 🔴 Critical | Misleading summary | Needs Fix |
| range-50-random extreme variance | 🟡 Warning | Accurate but confusing | Document |
| Duration always 0.00s | 🟢 Minor | Cosmetic | Optional Fix |
| Avg Negative Return skewed | 🟡 Warning | Misleading due to outlier | Needs Fix |

---

## Recommendations

1. **Fix profit_percent calculation for 0-bet scenarios**
2. **Exclude 0-bet strategies from summary averages**
3. **Add data validation warnings in HTML**
4. **Document high-variance strategies clearly**
5. **Consider filtering out strategies that can't complete 100 runs**

