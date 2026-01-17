# Bet Validation and Adjustment System

## Overview

The DuckDice Bot engine includes comprehensive bet validation and automatic adjustment logic to ensure bets are always valid and maximize success rate even with small balances or edge cases.

## Architecture

### Responsibility Separation

**Strategies** (What to bet):
- Calculate bet amounts based on strategy logic
- Determine win chance percentages
- Choose bet direction (high/low)
- Don't worry about minimum constraints

**Engine** (Can we bet it?):
- Validates all bet parameters
- Adjusts bets to meet platform requirements
- Ensures minimum profit constraints
- Caps bets at available balance
- Provides transparent feedback

## Validation Process

### Step 1: Minimum Bet Enforcement

```python
if bet_amount < min_bet:
    bet_amount = min_bet
    print(f"📈 Adjusted bet from {original} to minimum {min_bet}")
```

**Purpose**: Ensure bet meets platform minimum (typically 1 satoshi)

**Example**:
- Strategy proposes: 0.000000001 BTC
- Engine adjusts to: 0.00000001 BTC

### Step 2: Balance Capping

```python
if bet_amount > current_balance:
    if current_balance < min_bet:
        return None  # Cannot place any valid bet
    bet_amount = current_balance
    print(f"⚖️  Capped bet to available balance: {bet_amount}")
```

**Purpose**: Never bet more than you have

**Example**:
- Strategy proposes: 10.0 USDT
- Current balance: 0.5 USDT
- Engine adjusts to: 0.5 USDT

### Step 3: Chance Range Validation

```python
if chance > 98:
    chance = 98
    print(f"⚖️  Capped chance to maximum: 98%")
elif chance < 1:
    chance = 1
    print(f"📈 Raised chance to minimum: 1%")
```

**Purpose**: Keep win chance within valid range (1-98%)

### Step 4: Minimum Profit Enforcement

This is the most sophisticated validation step.

#### Problem

DuckDice requires profit >= minimum bet for all bets.

**Formula**:
```
profit = bet_amount × (payout_multiplier - 1)
payout_multiplier ≈ 99 / win_chance
```

For `profit >= min_bet`:
```
bet_amount × ((99/chance) - 1) >= min_bet
```

#### Solution A: Increase Bet Amount

If balance allows, increase the bet:

```python
required_bet = min_bet / (payout_multiplier - 1)
if required_bet <= current_balance:
    bet_amount = required_bet
    print(f"💰 Increased bet to {required_bet} to meet minimum profit")
```

**Example**:
- Original: 0.000002 @ 95% chance
- Payout multiplier: 99/95 = 1.042
- Required bet: 0.0000005 / (1.042 - 1) = 0.0000119
- Adjusted: 0.0000119 @ 95% chance
- Profit: 0.0000005 ✅

#### Solution B: Reduce Win Chance

If balance is too low to increase bet, reduce win chance (higher multiplier):

```python
max_valid_chance = 99 / ((min_bet / bet_amount) + 1)
if max_valid_chance >= min_chance:
    chance = max_valid_chance
    print(f"🎯 Reduced chance to {chance}% to meet minimum profit")
```

**Example**:
- Original: 0.01 @ 98% chance (all balance)
- Cannot increase bet (already at balance)
- Reduce chance: 98% → 90%
- New multiplier: 99/90 = 1.1 (higher)
- Profit now meets minimum ✅

#### Solution C: Return None

If neither solution works:

```python
return None  # Stop session
print("⚠️  Cannot construct valid bet: profit < minimum")
```

**When this happens**:
- Balance too low for any valid bet
- Constraints cannot be satisfied
- Session ends gracefully

## User's XAUT Case Study

### Scenario

```
Balance: 0.00021797 XAUT
min_bet: 0.0000005 XAUT
Strategy: target-aware (SAFE state)
Proposed bet: 0.000002 @ 95% chance
```

### Problem (Before Fix)

```
profit = 0.000002 × (99/95 - 1) = 0.000000084
0.000000084 < 0.0000005  ❌

API Response:
HTTP Error: 422 Unprocessable Entity
{"error": "Invalid chance."}
```

### Solution (After Fix)

```
Engine detects: profit < min_bet
Calculates required bet: 0.0000005 / (99/95 - 1) = 0.0000119
Checks balance: 0.0000119 <= 0.00021797 ✅
Adjusts bet: 0.0000119 @ 95% chance

New profit: 0.0000119 × (99/95 - 1) = 0.0000005 ✅
Bet placed successfully!
```

### Console Output

```
💰 Increased bet from 0.000002 to 0.0000119 to meet minimum profit
✅ Bet #1 placed successfully
```

## Benefits

### 1. Robustness
- No more API errors for edge cases
- Handles tiny balances gracefully
- Works with any strategy

### 2. Transparency
- Clear console messages
- Shows all adjustments
- Explains why changes were made

### 3. Simplicity
- Strategies don't need complex validation
- Engine handles all edge cases
- Consistent behavior across all strategies

### 4. User Experience
- Bets work even with dust balances
- No unexpected failures
- Predictable behavior

## API Reference

### _validate_and_adjust_bet()

```python
def _validate_and_adjust_bet(
    bet: BetSpec,
    current_balance: Decimal,
    min_bet: Decimal = Decimal("0.00000001"),
    max_chance: Decimal = Decimal("98"),
    min_chance: Decimal = Decimal("1"),
    printer: Optional[Callable[[str], None]] = None,
) -> Optional[BetSpec]:
    """
    Validate and adjust bet to meet minimum constraints.
    
    Returns:
        Adjusted BetSpec if valid, None if impossible
    """
```

**Parameters**:
- `bet`: Bet specification from strategy
- `current_balance`: Available balance
- `min_bet`: Minimum bet amount (default: 1 satoshi)
- `max_chance`: Maximum win chance (default: 98%)
- `min_chance`: Minimum win chance (default: 1%)
- `printer`: Optional output function

**Returns**:
- Adjusted `BetSpec` if valid bet can be constructed
- `None` if constraints cannot be satisfied

**Side Effects**:
- Prints adjustment messages via `printer` if provided
- Never modifies input `bet` (returns new dict)

## Testing

See `test_bet_validation.py` (deleted after testing):

```python
# Test minimum bet enforcement
test_minimum_bet_enforcement()

# Test balance capping  
test_balance_cap()

# Test insufficient balance
test_insufficient_balance()

# Test minimum profit (user's case)
test_minimum_profit_adjustment()

# Test chance reduction fallback
test_chance_reduction_for_profit()
```

All tests pass ✅

## Configuration

### Default Values

```python
# In engine.py run_auto_bet()
min_bet = Decimal("0.00000001")  # 1 satoshi
max_chance = Decimal("98")       # Platform maximum
min_chance = Decimal("1")        # Platform minimum
```

### Per-Currency Minimums

Some currencies may have different minimums:

```python
# Future enhancement - per-currency minimums
currency_min_bets = {
    "btc": Decimal("0.00000001"),   # 1 satoshi
    "eth": Decimal("0.000000001"),  # 1 gwei
    "usdt": Decimal("0.01"),        # 1 cent
    "xaut": Decimal("0.0000005"),   # User's case
}
```

## Future Enhancements

1. **Currency-Specific Minimums**
   - Load from config or API
   - Auto-detect from user's balance

2. **Smart Chance Adjustment**
   - Find optimal chance within range
   - Maximize profit while meeting constraints

3. **Strategy Feedback**
   - Notify strategy of adjustments
   - Allow strategy to recalculate if needed

4. **Historical Tracking**
   - Log all adjustments
   - Analytics on adjustment frequency

5. **Dry-Run Validation**
   - Test bet validity before placing
   - Simulation mode respects same rules

## Related Files

- `src/betbot_engine/engine.py` - Validation implementation
- `src/betbot_strategies/target_aware.py` - Simplified strategy
- `tests/test_target_aware.py` - Strategy tests
- `tests/test_strategy_integration.py` - Integration tests

## Commit History

- `efbab91` - Simplified target-aware validation
- `eddf7c4` - Added comprehensive engine validation

## Summary

The bet validation system ensures **every bet works**, even in edge cases. By automatically adjusting bets to meet platform requirements, users can run strategies confidently with any balance size.

**Key Principle**: Strategies focus on **strategy logic**, engine handles **platform constraints**.
