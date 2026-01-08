"""
Simple Martingale Script Example

This demonstrates a basic martingale strategy using the scripting engine.
Double bet on loss, reset on win.

Usage:
  python duckdice.py auto --symbol XLM --strategy custom-script \
    --params script_path=examples/strategy_scripts/simple_martingale.py
"""

# Global state
base_amount = 0.000001
current_amount = base_amount
chance = "49.5"
is_high = True


def init(params, context):
    """Initialize strategy with parameters."""
    global base_amount, current_amount, chance, is_high
    
    base_amount = float(params.get('base_amount', 0.000001))
    current_amount = base_amount
    chance = str(params.get('chance', '49.5'))
    is_high = bool(params.get('is_high', True))
    
    print(f"Initialized: base={base_amount}, chance={chance}, high={is_high}")


def next_bet():
    """Return next bet specification."""
    return {
        'game': 'dice',
        'amount': str(current_amount),
        'chance': chance,
        'is_high': is_high,
    }


def on_result(result):
    """Handle bet result and adjust strategy."""
    global current_amount, base_amount
    
    win = result.get('win', False)
    profit = result.get('profit', '0')
    
    if win:
        print(f"WIN! Profit: {profit}, resetting to base")
        current_amount = base_amount
    else:
        print(f"LOSS! Profit: {profit}, doubling bet")
        current_amount *= 2
        
        # Safety: cap at 100x base
        if current_amount > base_amount * 100:
            print("WARNING: Hit 100x cap, resetting!")
            current_amount = base_amount


def on_session_end(reason):
    """Called when session ends."""
    print(f"Session ended: {reason}")
