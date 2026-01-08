#!/usr/bin/env python3
"""
Offline Simulation Engine
Simulates betting without API connection using local RNG
"""

import random
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime


class SimulationEngine:
    """
    Offline betting simulation engine.
    Provides realistic betting simulation without API connection.
    """
    
    def __init__(self, initial_balance: Decimal = Decimal("100.0")):
        """
        Initialize simulation engine.
        
        Args:
            initial_balance: Starting balance for simulation
        """
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
        self.session_active = False
        
        # Use cryptographically secure random if available
        try:
            self.random = random.SystemRandom()
        except:
            self.random = random.Random()
    
    def place_bet(
        self,
        bet_amount: Decimal,
        chance: Decimal,
        payout: Decimal,
        is_high: bool = True
    ) -> Dict[str, Any]:
        """
        Simulate a bet placement.
        
        Args:
            bet_amount: Amount to bet
            chance: Win chance percentage (0-100)
            payout: Payout multiplier
            is_high: Bet on high (True) or low (False)
            
        Returns:
            Dictionary with bet result
        """
        # Validate inputs
        if bet_amount <= 0:
            raise ValueError("Bet amount must be positive")
        
        if bet_amount > self.balance:
            raise ValueError(f"Insufficient balance: {self.balance} < {bet_amount}")
        
        if not (0 < chance < 100):
            raise ValueError("Chance must be between 0 and 100")
        
        # Generate random roll (0-99.99)
        roll = Decimal(str(self.random.random() * 100))
        
        # Determine target based on chance
        if is_high:
            target = Decimal("100") - chance
            is_win = roll >= target
        else:
            target = chance
            is_win = roll < target
        
        # Calculate profit/loss
        if is_win:
            profit = bet_amount * (payout - Decimal("1"))
            self.total_wins += 1
        else:
            profit = -bet_amount
            self.total_losses += 1
        
        # Update balance
        self.balance += profit
        self.total_bets += 1
        
        # Return result
        return {
            'bet_id': f"sim_{self.total_bets}_{datetime.now().timestamp()}",
            'timestamp': datetime.now().isoformat(),
            'bet_amount': bet_amount,
            'chance': chance,
            'payout': payout,
            'is_high': is_high,
            'is_win': is_win,
            'profit': profit,
            'balance': self.balance,
            'roll_value': roll,
            'target_value': target,
            'multiplier': payout if is_win else Decimal("0"),
            'simulated': True
        }
    
    def get_balance(self) -> Decimal:
        """Get current balance."""
        return self.balance
    
    def set_balance(self, balance: Decimal):
        """Set balance (for testing)."""
        self.balance = balance
    
    def reset(self, initial_balance: Optional[Decimal] = None):
        """
        Reset simulation to initial state.
        
        Args:
            initial_balance: New starting balance (or use original)
        """
        if initial_balance is not None:
            self.initial_balance = initial_balance
        
        self.balance = self.initial_balance
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        profit = self.balance - self.initial_balance
        profit_pct = ((self.balance / self.initial_balance) - 1) * 100 if self.initial_balance > 0 else 0
        win_rate = (self.total_wins / self.total_bets * 100) if self.total_bets > 0 else 0
        
        return {
            'total_bets': self.total_bets,
            'total_wins': self.total_wins,
            'total_losses': self.total_losses,
            'win_rate': win_rate,
            'initial_balance': self.initial_balance,
            'current_balance': self.balance,
            'total_profit': profit,
            'profit_percentage': profit_pct
        }
    
    def can_bet(self, bet_amount: Decimal) -> bool:
        """Check if balance is sufficient for bet."""
        return self.balance >= bet_amount


class SimulatedDuckDiceAPI:
    """
    API-compatible simulation wrapper.
    Drop-in replacement for DuckDiceAPI in simulation mode.
    """
    
    def __init__(self, initial_balance: Decimal = Decimal("100.0")):
        """Initialize simulated API."""
        self.engine = SimulationEngine(initial_balance)
        self.default_symbol = "SIM"
        self.balances = {
            self.default_symbol: {
                'available': str(initial_balance),
                'btc_value': str(initial_balance * Decimal("0.00001"))
            }
        }
    
    def place_bet(
        self,
        symbol: str,
        amount: Decimal,
        chance: Decimal,
        is_high: bool,
        client_seed: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate bet placement (API-compatible).
        
        Args:
            symbol: Currency symbol (ignored in simulation)
            amount: Bet amount
            chance: Win chance
            is_high: Bet on high
            client_seed: Client seed (ignored)
            
        Returns:
            Bet result dictionary
        """
        # Calculate payout from chance
        payout = Decimal("100") / chance
        
        # Place simulated bet
        result = self.engine.place_bet(amount, chance, payout, is_high)
        
        # Update balances
        self.balances[self.default_symbol]['available'] = str(self.engine.balance)
        self.balances[self.default_symbol]['btc_value'] = str(self.engine.balance * Decimal("0.00001"))
        
        # Format as API response
        return {
            'id': result['bet_id'],
            'symbol': symbol,
            'amount': str(amount),
            'chance': str(chance),
            'high': is_high,
            'payout': str(result['payout']),
            'profit': str(result['profit']),
            'roll': str(result['roll_value']),
            'target': str(result['target_value']),
            'balance': str(result['balance']),
            'win': result['is_win'],
            'created_at': result['timestamp']
        }
    
    def get_balances(self) -> Dict[str, Any]:
        """Get balances (API-compatible)."""
        # Update with current balance
        self.balances[self.default_symbol]['available'] = str(self.engine.balance)
        self.balances[self.default_symbol]['btc_value'] = str(self.engine.balance * Decimal("0.00001"))
        return self.balances
    
    def get_balance(self, symbol: str) -> Decimal:
        """Get balance for specific symbol."""
        return self.engine.balance
    
    def reset(self, balance: Decimal):
        """Reset simulation."""
        self.engine.reset(balance)
        self.balances[self.default_symbol]['available'] = str(balance)
        self.balances[self.default_symbol]['btc_value'] = str(balance * Decimal("0.00001"))
