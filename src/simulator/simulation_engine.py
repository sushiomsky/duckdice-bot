"""
Simulation engine for virtual dice betting.
"""

import random
from decimal import Decimal
from datetime import datetime
from typing import Optional, Callable, List
import logging

from .models import SimulationConfig, SimulatedBet

logger = logging.getLogger(__name__)


class VirtualBalance:
    """Manages virtual balance for simulation."""
    
    def __init__(self, starting_balance: Decimal, currency: str):
        """Initialize virtual balance."""
        self.starting_balance = starting_balance
        self.currency = currency
        self._balance = starting_balance
        self._peak_balance = starting_balance
        
    @property
    def balance(self) -> Decimal:
        """Get current balance."""
        return self._balance
    
    @property
    def peak_balance(self) -> Decimal:
        """Get peak balance reached."""
        return self._peak_balance
    
    @property
    def profit_loss(self) -> Decimal:
        """Get total profit/loss."""
        return self._balance - self.starting_balance
    
    def update(self, amount: Decimal) -> Decimal:
        """Update balance by amount (positive or negative)."""
        self._balance += amount
        if self._balance > self._peak_balance:
            self._peak_balance = self._balance
        return self._balance
    
    def can_afford(self, amount: Decimal) -> bool:
        """Check if can afford bet."""
        return self._balance >= amount
    
    def reset(self):
        """Reset to starting balance."""
        self._balance = self.starting_balance
        self._peak_balance = self.starting_balance


class OutcomeGenerator:
    """Generates bet outcomes."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize outcome generator."""
        self._random = random.Random(seed)
        
    def generate(self) -> float:
        """Generate random outcome between 0 and 100."""
        return self._random.uniform(0, 100)
    
    def reset_seed(self, seed: Optional[int] = None):
        """Reset random seed."""
        self._random.seed(seed)


class SimulationEngine:
    """Core simulation engine for dice betting."""
    
    def __init__(
        self,
        starting_balance: float,
        currency: str = 'USD',
        house_edge: float = 3.0,
        seed: Optional[int] = None,
    ):
        """
        Initialize simulation engine.
        
        Args:
            starting_balance: Starting balance amount
            currency: Currency code (USD, BTC, etc.)
            house_edge: House edge percentage (0-100)
            seed: Random seed for reproducibility
        """
        self.config = SimulationConfig(
            starting_balance=Decimal(str(starting_balance)),
            currency=currency,
            house_edge=house_edge,
            seed=seed,
        )
        
        self.balance = VirtualBalance(
            self.config.starting_balance,
            self.config.currency,
        )
        self.outcome_generator = OutcomeGenerator(seed)
        self.bet_history: List[SimulatedBet] = []
        self._bet_count = 0
        
    def reset(self):
        """Reset simulation to initial state."""
        self.balance.reset()
        self.outcome_generator.reset_seed(self.config.seed)
        self.bet_history.clear()
        self._bet_count = 0
        logger.info("Simulation reset")
        
    def execute_bet(
        self,
        amount: float,
        chance: float,
        roll_over: bool = True,
    ) -> SimulatedBet:
        """
        Execute a simulated bet.
        
        Args:
            amount: Bet amount
            chance: Win chance (0-100)
            roll_over: True = roll over, False = roll under
            
        Returns:
            SimulatedBet result
        """
        bet_amount = Decimal(str(amount))
        
        # Check if can afford
        if not self.balance.can_afford(bet_amount):
            raise ValueError(
                f"Insufficient balance: {self.balance.balance} < {bet_amount}"
            )
        
        # Generate outcome
        outcome = self.outcome_generator.generate()
        
        # Determine win/loss
        if roll_over:
            won = outcome > (100 - chance)
        else:
            won = outcome < chance
        
        # Calculate profit/loss
        if won:
            # Calculate payout with house edge
            # payout = bet * multiplier * (1 - house_edge/100)
            multiplier = 100 / chance
            payout = bet_amount * Decimal(str(multiplier))
            # Apply house edge
            house_edge_mult = Decimal(str(1 - self.config.house_edge / 100))
            payout = payout * house_edge_mult
            profit = payout - bet_amount
        else:
            profit = -bet_amount
        
        # Update balance
        new_balance = self.balance.update(profit)
        
        # Record bet
        self._bet_count += 1
        bet = SimulatedBet(
            bet_number=self._bet_count,
            timestamp=datetime.now(),
            amount=bet_amount,
            chance=chance,
            roll_over=roll_over,
            outcome=outcome,
            won=won,
            profit=profit,
            balance_after=new_balance,
        )
        self.bet_history.append(bet)
        
        logger.debug(
            f"Bet #{self._bet_count}: {bet_amount} @ {chance}% "
            f"= {outcome:.3f} ({'WIN' if won else 'LOSS'}) "
            f"profit={profit:.8f} balance={new_balance:.8f}"
        )
        
        return bet
    
    def get_balance(self) -> Decimal:
        """Get current balance."""
        return self.balance.balance
    
    def get_profit_loss(self) -> Decimal:
        """Get total profit/loss."""
        return self.balance.profit_loss
    
    def get_bet_count(self) -> int:
        """Get number of bets executed."""
        return self._bet_count
    
    def get_history(self) -> List[SimulatedBet]:
        """Get bet history."""
        return self.bet_history.copy()
