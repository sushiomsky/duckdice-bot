"""
DiceBot API Compatibility Layer

DiceBot uses a Lua-based scripting system with a specific API.
This module provides compatibility for DiceBot scripts to run in our system.

Common DiceBot API:
- nextbet: The next bet amount
- chance: Win chance (0-100)
- bethigh: true/false for over/under
- win: true/false if last bet won
- currentprofit: Current session profit
- previousbet: Last bet amount
- currentstreak: Current streak count
"""

import sys
from decimal import Decimal
from typing import Dict, Any, Optional


class DiceBotAPI:
    """
    DiceBot-compatible API for running Lua-like scripts.
    
    This provides the same variables and functions that DiceBot scripts expect.
    Scripts can read/write these variables to control betting behavior.
    """
    
    def __init__(self):
        # Betting parameters (writable by script)
        self.nextbet = Decimal("0.00000001")  # Next bet amount
        self.chance = Decimal("49.5")          # Win chance %
        self.bethigh = True                    # Bet high/low
        
        # State variables (read-only, updated by engine)
        self.win = False                       # Did last bet win?
        self.currentprofit = Decimal("0")      # Session profit/loss
        self.previousbet = Decimal("0")        # Last bet amount
        self.currentstreak = 0                 # Current win/loss streak
        self.bets = 0                          # Total bets placed
        
        # Balance info
        self.balance = Decimal("0")            # Current balance
        self.startbalance = Decimal("0")       # Starting balance
        
        # User script code
        self.script_code = ""
        
        # Simulation state
        self.is_simulation = True
        
        # Stop flag
        self.should_stop = False
    
    def reset(self, starting_balance: Decimal):
        """Reset state for new betting session."""
        self.balance = starting_balance
        self.startbalance = starting_balance
        self.currentprofit = Decimal("0")
        self.previousbet = Decimal("0")
        self.currentstreak = 0
        self.bets = 0
        self.win = False
        self.should_stop = False
    
    def update_from_bet_result(self, won: bool, bet_amount: Decimal, payout: Decimal):
        """Update state after a bet result."""
        self.win = won
        self.previousbet = bet_amount
        self.bets += 1
        
        # Update balance
        if won:
            self.balance += payout - bet_amount
            profit = payout - bet_amount
        else:
            self.balance -= bet_amount
            profit = -bet_amount
        
        # Update profit
        self.currentprofit = self.balance - self.startbalance
        
        # Update streak
        if won:
            if self.currentstreak > 0:
                self.currentstreak += 1
            else:
                self.currentstreak = 1
        else:
            if self.currentstreak < 0:
                self.currentstreak -= 1
            else:
                self.currentstreak = -1
    
    def execute_script(self):
        """
        Execute the user's DiceBot script.
        
        The script should modify nextbet, chance, and bethigh variables.
        For now, we'll use Python eval() but in production should use
        a proper Lua interpreter or safe sandbox.
        """
        if not self.script_code:
            return
        
        try:
            # Create a safe execution context with DiceBot variables
            context = {
                'nextbet': float(self.nextbet),
                'chance': float(self.chance),
                'bethigh': self.bethigh,
                'win': self.win,
                'currentprofit': float(self.currentprofit),
                'previousbet': float(self.previousbet),
                'currentstreak': self.currentstreak,
                'bets': self.bets,
                'balance': float(self.balance),
                'startbalance': float(self.startbalance),
                # DiceBot functions
                'stop': self._stop,
                'Decimal': Decimal,
            }
            
            # Execute script (simplified - would need proper Lua interpreter)
            exec(self.script_code, context)
            
            # Update variables from context
            self.nextbet = Decimal(str(context.get('nextbet', self.nextbet)))
            self.chance = Decimal(str(context.get('chance', self.chance)))
            self.bethigh = context.get('bethigh', self.bethigh)
            
        except Exception as e:
            print(f"Script execution error: {e}", file=sys.stderr)
            raise
    
    def _stop(self):
        """DiceBot stop() function - stops the betting."""
        self.should_stop = True
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state as dictionary."""
        return {
            'nextbet': float(self.nextbet),
            'chance': float(self.chance),
            'bethigh': self.bethigh,
            'win': self.win,
            'currentprofit': float(self.currentprofit),
            'previousbet': float(self.previousbet),
            'currentstreak': self.currentstreak,
            'bets': self.bets,
            'balance': float(self.balance),
            'should_stop': self.should_stop,
        }


# Example DiceBot scripts that users might write
EXAMPLE_SCRIPTS = {
    "Simple Martingale": """# Simple Martingale Strategy
basebet = 0.00000001
multiplier = 2.0

if win:
    nextbet = basebet
else:
    nextbet = previousbet * multiplier
""",
    
    "Target Profit": """# Stop at target profit
basebet = 0.00000001
target = 0.001

nextbet = basebet

if currentprofit >= target:
    stop()
""",
    
    "Anti-Martingale": """# Increase on wins, reset on loss
basebet = 0.00000001
multiplier = 2.0

if win:
    nextbet = previousbet * multiplier
else:
    nextbet = basebet
""",
    
    "Streak Counter": """# Adjust based on streak
basebet = 0.00000001

if currentstreak >= 3:
    nextbet = basebet * 2
elif currentstreak <= -3:
    nextbet = basebet * 2
else:
    nextbet = basebet
""",
}
