# Live Statistics Display Bug Fix - v4.9.1

## Problem Identified

The live betting statistics were showing **completely incorrect values**:
- ❌ Win rate: Always 0.00% (even when wins occurred)
- ❌ Wins counter: Always 0
- ❌ Profit: Always 0.00000000
- ❌ Balance: Showing 0.00000000 or incorrect values

This led to confusing dual output where:
1. Engine printer showed correct values: `bet#489 win=Y profit=0.36 bal=2.34`
2. CLI display showed wrong values: `Bets: 980  Wins: 0  Losses: 980  Win Rate: 0.0%`

## Root Cause

The `SessionTracker` class was looking for bet result data at the **wrong nesting level**:

### Incorrect Code (Lines 137-143):
```python
def update(self, bet_result: Dict[str, Any]):
    self.total_bets += 1
    if bet_result.get('win'):  # ❌ WRONG: 'win' is nested inside 'result'
        self.wins += 1
    else:
        self.losses += 1
```

### Actual Data Structure from Engine:
```python
{
    "event": "bet",
    "result": {          # ← Win/loss data is HERE
        "win": True,
        "profit": 0.5
    },
    "balance": "10.5",
    "bet": {
        "amount": 1.0,
        "payout_multiplier": 2.0
    }
}
```

Since `bet_result.get('win')` returned `None` (not inside 'result'), the condition was always False:
- Wins were **never** counted
- Win rate was always 0%
- Every bet was counted as a loss

## Fixes Applied

### 1. Fixed SessionTracker.update() (duckdice_cli.py:134-146)
```python
def update(self, bet_result: Dict[str, Any]):
    """Update stats from bet result"""
    self.total_bets += 1
    
    # Extract result data (win/loss/profit are nested in 'result' dict)
    result = bet_result.get('result', {})  # ✅ Get nested dict
    if result.get('win'):                   # ✅ Check inside result
        self.wins += 1
    else:
        self.losses += 1
    
    if 'balance' in bet_result:
        self.current_balance = float(bet_result['balance'])
```

### 2. Fixed json_sink() bet data extraction (duckdice_cli.py:257-300)
```python
def json_sink(bet_data: Dict[str, Any]):
    """Track bet statistics with enhanced display"""
    tracker.update(bet_data)
    
    # Extract nested result data
    result = bet_data.get('result', {})           # ✅ Extract result dict
    balance = float(bet_data.get('balance', 0))
    
    if tracker.starting_balance is None:
        profit = float(result.get('profit', 0))   # ✅ Get profit from result
        tracker.starting_balance = balance - profit
        tracker.current_balance = balance
    
    if tracker.total_bets % 1 == 0:
        win = result.get('win', False)            # ✅ Get win from result
        profit_val = float(result.get('profit', 0))  # ✅ Get profit from result
        bet_spec = bet_data.get('bet', {})        # ✅ Get bet details
        bet_amount = float(bet_spec.get('amount', 0))
        multiplier = float(bet_spec.get('payout_multiplier', 0))
        # ... display code
```

## Testing

Created test script to verify the fix:

```python
# Test data simulating engine output
test_bets = [
    {"event": "bet", "result": {"win": True, "profit": 0.5}, "balance": "10.5"},
    {"event": "bet", "result": {"win": False, "profit": -1.0}, "balance": "9.5"},
    {"event": "bet", "result": {"win": True, "profit": 1.0}, "balance": "10.5"},
]

# Results after fix:
✅ Total Bets: 3 (expected: 3)
✅ Wins: 2 (expected: 2)
✅ Losses: 1 (expected: 1)
✅ Win Rate: 66.67% (expected: 66.67%)
✅ Starting Balance: 10.00 (expected: 10.00)
✅ Current Balance: 10.50 (expected: 10.50)
✅ Profit: 0.50 (expected: 0.50)
✅ Profit %: 5.00% (expected: 5.00%)
```

## Impact

### Before Fix:
```
╭───────────────────── Live Statistics ─────────────────────╮
│ Bets: 1000  Wins: 0  Losses: 1000  Win Rate: 0.0%         │
│ Profit: +0.00000000  Balance: 0.00000000                  │
╰────────────────────────────────────────────────────────────╯
```

### After Fix:
```
╭───────────────────── Live Statistics ─────────────────────╮
│ Bets: 1000  Wins: 467  Losses: 533  Win Rate: 46.7%       │
│ Profit: +2.35000000  Balance: 12.35000000                 │
╰────────────────────────────────────────────────────────────╯
```

## Files Changed

1. **src/cli_display.py** - Version bump to 4.9.1
2. **duckdice_cli.py** - Fixed SessionTracker and json_sink parsing

## Version

- Previous: 4.9.0
- Current: **4.9.1**

## Related Issues

This bug did NOT affect:
- ✅ Engine's internal calculations (always correct)
- ✅ Engine's console output (always correct)
- ✅ Final session summary (uses engine data)
- ✅ Strategy comparison tool (uses engine directly)

Only affected:
- ❌ Live CLI statistics display during betting sessions
- ❌ Rich-formatted bet result output
- ❌ Progress bar updates

---

**Status**: ✅ Fixed and tested
**Date**: 2026-01-15
**Priority**: High (user-facing display bug)
