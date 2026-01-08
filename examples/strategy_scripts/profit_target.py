"""
Profit Target Script

Demonstrates a strategy that aims for specific profit targets.
Adjusts bet size to reach profit goal efficiently.

Usage:
  python duckdice.py auto --symbol XLM --strategy custom-script \
    --params script_path=examples/strategy_scripts/profit_target.py,profit_target=0.00001
"""

from decimal import Decimal

# Global state
base_amount = 0.000001
current_amount = base_amount
chance = "49.5"
is_high = True
profit_target = 0.00001
session_profit = 0.0
starting_balance = 0.0


def init(params, context):
    """Initialize with profit target."""
    global base_amount, current_amount, profit_target, starting_balance, chance
    
    base_amount = float(params.get('base_amount', 0.000001))
    current_amount = base_amount
    profit_target = float(params.get('profit_target', 0.00001))
    chance = str(params.get('chance', '49.5'))
    
    # Get starting balance from context
    starting_balance = float(context.starting_balance or '0')
    
    print(f"Profit target strategy: target={profit_target}, base={base_amount}")
    print(f"Starting balance: {starting_balance}")


def next_bet():
    """Calculate bet to reach target efficiently."""
    global current_amount
    
    # If close to target, bet exactly what we need
    remaining = profit_target - session_profit
    
    if 0 < remaining < current_amount:
        # Bet just enough to hit target
        bet_amount = remaining * 2  # Account for 50% win chance
        current_amount = max(base_amount, bet_amount)
    
    return {
        'game': 'dice',
        'amount': str(current_amount),
        'chance': chance,
        'is_high': is_high,
    }


def on_result(result):
    """Track profit and adjust."""
    global current_amount, base_amount, session_profit
    
    win = result.get('win', False)
    profit = float(result.get('profit', '0'))
    balance = float(result.get('balance', '0'))
    
    session_profit += profit
    progress = (session_profit / profit_target * 100) if profit_target > 0 else 0
    
    print(f"Win: {win}, Profit: {profit:.8f}, Session: {session_profit:.8f} ({progress:.1f}%)")
    
    if session_profit >= profit_target:
        print(f"🎯 TARGET REACHED! Profit: {session_profit:.8f}")
        # Could signal to stop here
        return None
    
    # Adjust bet based on how close we are
    if win:
        # On win, keep current bet or reduce slightly
        current_amount = base_amount
    else:
        # On loss, increase to recover
        current_amount = min(current_amount * 2, base_amount * 10)


def on_session_end(reason):
    """Report final results."""
    print(f"\n{'='*50}")
    print(f"Session ended: {reason}")
    print(f"Target profit: {profit_target:.8f}")
    print(f"Actual profit: {session_profit:.8f}")
    
    if session_profit >= profit_target:
        print("✅ Target achieved!")
    else:
        print(f"❌ Short by: {profit_target - session_profit:.8f}")
    print(f"{'='*50}")
