"""
Claim Tracker - Track faucet claims and enforce daily limits
"""

from typing import List, Tuple
from dataclasses import dataclass
from datetime import datetime
import time


@dataclass
class ClaimRecord:
    """Single faucet claim record"""
    timestamp: float
    currency: str
    amount: float  # In crypto
    amount_usd: float  # In USD
    cooldown: int  # Cooldown applied (seconds)


class ClaimTracker:
    """
    Track faucet claims and enforce 24-hour limits.
    
    DuckDice faucet allows 35-60 claims per 24 hours with
    variable cooldown (0-60 seconds) between claims.
    """
    
    def __init__(self, min_claims: int = 35, max_claims: int = 60):
        """
        Initialize claim tracker.
        
        Args:
            min_claims: Minimum claims guaranteed per 24h
            max_claims: Maximum claims possible per 24h
        """
        self.min_claims = min_claims
        self.max_claims = max_claims
        
        self.claims_today: List[ClaimRecord] = []
        self.total_claimed_usd: float = 0.0
        self.last_claim_time: float = 0.0
        self.next_reset_time: float = time.time() + 86400  # 24h from now
        
    def can_claim(self) -> Tuple[bool, str]:
        """
        Check if claim is allowed.
        
        Returns:
            (can_claim, reason_if_not)
        """
        # Check if 24h period has reset
        if time.time() >= self.next_reset_time:
            self.reset_daily()
        
        # Check daily claim limit
        if len(self.claims_today) >= self.max_claims:
            remaining = self.next_reset_time - time.time()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return False, f"Daily limit reached. Resets in {hours}h {minutes}m"
        
        # Check cooldown
        if self.last_claim_time > 0:
            # Minimum 1 second between claims (to be safe)
            elapsed = time.time() - self.last_claim_time
            if elapsed < 1:
                return False, "Cooldown active (minimum 1s between claims)"
        
        return True, ""
    
    def record_claim(
        self, 
        currency: str,
        amount: float, 
        amount_usd: float,
        cooldown: int
    ) -> None:
        """
        Record a successful claim.
        
        Args:
            currency: Currency symbol
            amount: Amount claimed in crypto
            amount_usd: Amount in USD
            cooldown: Cooldown period applied (seconds)
        """
        claim = ClaimRecord(
            timestamp=time.time(),
            currency=currency,
            amount=amount,
            amount_usd=amount_usd,
            cooldown=cooldown
        )
        
        self.claims_today.append(claim)
        self.total_claimed_usd += amount_usd
        self.last_claim_time = time.time()
    
    def get_next_claim_time(self) -> float:
        """
        Get timestamp when next claim can happen.
        
        Returns:
            Timestamp (0 if can claim now)
        """
        can_claim, _ = self.can_claim()
        if can_claim:
            return 0.0
        
        # At limit - return reset time
        if len(self.claims_today) >= self.max_claims:
            return self.next_reset_time
        
        # Still in cooldown - return when cooldown expires
        if self.last_claim_time > 0:
            return self.last_claim_time + 1  # Minimum 1s cooldown
        
        return 0.0
    
    def reset_daily(self) -> None:
        """Reset the 24-hour claim counter"""
        self.claims_today.clear()
        self.total_claimed_usd = 0.0
        self.next_reset_time = time.time() + 86400
    
    def get_claims_remaining(self) -> int:
        """Get number of claims remaining today"""
        if time.time() >= self.next_reset_time:
            return self.max_claims
        return max(0, self.max_claims - len(self.claims_today))
    
    def get_statistics(self) -> dict:
        """
        Get claim statistics.
        
        Returns:
            Dict with statistics
        """
        total_claims = len(self.claims_today)
        
        return {
            'claims_today': total_claims,
            'claims_remaining': self.get_claims_remaining(),
            'total_usd_today': self.total_claimed_usd,
            'average_claim_usd': self.total_claimed_usd / total_claims if total_claims > 0 else 0,
            'time_until_reset': max(0, self.next_reset_time - time.time()),
            'last_claim_time': self.last_claim_time,
            'can_claim_now': self.can_claim()[0]
        }
