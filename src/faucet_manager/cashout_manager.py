"""
Cashout Manager - Manage faucet to main balance transfers
"""

from typing import Optional, Tuple


class CashoutManager:
    """
    Manage faucet to main balance cashout operations.
    
    DuckDice requires minimum $20 USD equivalent for cashout.
    """
    
    CASHOUT_THRESHOLD_USD = 20.0
    
    def __init__(self, threshold_usd: float = CASHOUT_THRESHOLD_USD):
        """
        Initialize cashout manager.
        
        Args:
            threshold_usd: Minimum USD amount for cashout
        """
        self.threshold_usd = threshold_usd
        self.total_cashed_out = 0.0
        self.cashout_count = 0
        
    def can_cashout(self, balance_usd: float) -> Tuple[bool, str]:
        """
        Check if cashout is allowed.
        
        Args:
            balance_usd: Current faucet balance in USD
            
        Returns:
            (can_cashout, reason_if_not)
        """
        if balance_usd >= self.threshold_usd:
            return True, ""
        
        remaining = self.threshold_usd - balance_usd
        progress = (balance_usd / self.threshold_usd) * 100
        
        return False, f"Need ${remaining:.2f} more ({progress:.1f}% complete)"
    
    def get_progress(self, balance_usd: float) -> float:
        """
        Get progress towards cashout threshold.
        
        Args:
            balance_usd: Current faucet balance in USD
            
        Returns:
            Progress percentage (0-100)
        """
        if balance_usd >= self.threshold_usd:
            return 100.0
        
        return (balance_usd / self.threshold_usd) * 100
    
    def record_cashout(self, amount_usd: float) -> None:
        """
        Record a successful cashout.
        
        Args:
            amount_usd: Amount cashed out in USD
        """
        self.total_cashed_out += amount_usd
        self.cashout_count += 1
    
    def get_statistics(self) -> dict:
        """
        Get cashout statistics.
        
        Returns:
            Dict with statistics
        """
        return {
            'cashout_threshold': self.threshold_usd,
            'total_cashed_out': self.total_cashed_out,
            'cashout_count': self.cashout_count,
            'average_cashout': self.total_cashed_out / self.cashout_count if self.cashout_count > 0 else 0
        }
    
    def calculate_optimal_cashout(self, balance_usd: float) -> Optional[float]:
        """
        Calculate optimal amount to cashout.
        
        Args:
            balance_usd: Current faucet balance in USD
            
        Returns:
            Amount to cashout (None if below threshold)
        """
        if balance_usd < self.threshold_usd:
            return None
        
        # Cashout everything above threshold
        return balance_usd
