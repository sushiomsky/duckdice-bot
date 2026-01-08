"""
Conditional Betting Script

This demonstrates a more complex strategy:
- Analyze recent results
- Switch between high/low based on patterns
- Adjust bet size based on win rate

Usage:
  python duckdice.py auto --symbol XLM --strategy custom-script \
    --params script_path=examples/strategy_scripts/conditional_betting.py,base_amount=0.000001
"""

from collections import deque

# Global state
base_amount = 0.000001
current_amount = base_amount
chance = "49.5"
is_high = True
recent_results = deque(maxlen=10)
wins_in_last_10 = 0


def init(params, context):
    """Initialize strategy."""
    global base_amount, current_amount, chance
    
    base_amount = float(params.get('base_amount', 0.000001))
    current_amount = base_amount
    chance = str(params.get('chance', '49.5'))
    
    print(f"Conditional betting initialized: base={base_amount}")


def next_bet():
    """Determine next bet based on recent patterns."""
    global is_high, current_amount
    
    # If we have enough history, analyze it
    if len(recent_results) >= 5:
        # Count recent high rolls (>50)
        high_count = sum(1 for r in recent_results if r.get('number', 50) > 50)
        
        # Switch to opposite if one side is dominating
        if high_count >= 4:
            is_high = False  # Bet low
        elif high_count <= 1:
            is_high = True   # Bet high
        
        # Adjust bet size based on win rate
        if wins_in_last_10 >= 6:
            # Hot streak, increase bet slightly
            current_amount = base_amount * 1.5
        elif wins_in_last_10 <= 3:
            # Cold streak, reduce bet
            current_amount = base_amount * 0.5
        else:
            current_amount = base_amount
    
    return {
        'game': 'dice',
        'amount': str(current_amount),
        'chance': chance,
        'is_high': is_high,
    }


def on_result(result):
    """Track results and update strategy."""
    global wins_in_last_10
    
    win = result.get('win', False)
    number = result.get('number', 0)
    profit = result.get('profit', '0')
    
    # Add to recent results
    recent_results.append(result)
    
    # Update win counter
    if len(recent_results) > 10:
        # Remove oldest from count
        oldest = recent_results[0]
        if oldest.get('win'):
            wins_in_last_10 -= 1
    
    if win:
        wins_in_last_10 += 1
    
    side = "HIGH" if result.get('is_high') else "LOW"
    print(f"Number: {number}, Side: {side}, Win: {win}, Profit: {profit}")
    print(f"Win rate (last 10): {wins_in_last_10}/10")


def on_session_end(reason):
    """Report final statistics."""
    total = len(recent_results)
    wins = sum(1 for r in recent_results if r.get('win'))
    
    print(f"\nSession ended: {reason}")
    print(f"Recent performance: {wins}/{total} wins")
