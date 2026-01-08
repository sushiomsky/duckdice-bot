"""
Range Dice Script Example

Demonstrates using Range Dice game mode.
Bet on numbers falling in a specific range.

Usage:
  python duckdice.py auto --symbol XLM --strategy custom-script \
    --params script_path=examples/strategy_scripts/range_dice_example.py
"""

# Global state
base_amount = 0.000001
current_amount = base_amount
range_min = 40
range_max = 60
bet_in = True  # Bet on number being IN the range


def init(params, context):
    """Initialize strategy."""
    global base_amount, current_amount, range_min, range_max, bet_in
    
    base_amount = float(params.get('base_amount', 0.000001))
    current_amount = base_amount
    range_min = int(params.get('range_min', 40))
    range_max = int(params.get('range_max', 60))
    bet_in = bool(params.get('bet_in', True))
    
    print(f"Range Dice: {range_min}-{range_max}, betting {'IN' if bet_in else 'OUT'}")


def next_bet():
    """Return range dice bet."""
    return {
        'game': 'range-dice',
        'amount': str(current_amount),
        'range': (range_min, range_max),
        'is_in': bet_in,
    }


def on_result(result):
    """Handle result."""
    global current_amount, base_amount
    
    win = result.get('win', False)
    number = result.get('number', 0)
    profit = result.get('profit', '0')
    
    in_range = range_min <= number <= range_max
    
    print(f"Number: {number} ({'IN' if in_range else 'OUT'} range), Win: {win}, Profit: {profit}")
    
    # Simple martingale
    if win:
        current_amount = base_amount
    else:
        current_amount *= 2


def on_session_end(reason):
    """Session end."""
    print(f"Range dice session ended: {reason}")
