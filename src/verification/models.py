"""
Verification Data Models.

Data structures for bet verification results.
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class VerificationResult:
    """Result of a single bet verification."""
    
    is_valid: bool
    calculated_roll: float
    actual_roll: float
    server_seed: str
    client_seed: str
    nonce: int
    hash_value: str
    error: Optional[str] = None
    
    def __post_init__(self):
        """Validate roll precision."""
        # Ensure rolls are within valid range
        if not (0.0 <= self.calculated_roll <= 100.0):
            self.error = f"Invalid calculated roll: {self.calculated_roll}"
            self.is_valid = False
        
        if not (0.0 <= self.actual_roll <= 100.0):
            self.error = f"Invalid actual roll: {self.actual_roll}"
            self.is_valid = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'is_valid': self.is_valid,
            'calculated_roll': self.calculated_roll,
            'actual_roll': self.actual_roll,
            'server_seed': self.server_seed,
            'client_seed': self.client_seed,
            'nonce': self.nonce,
            'hash_value': self.hash_value,
            'error': self.error,
            'match': abs(self.calculated_roll - self.actual_roll) < 0.001
        }
    
    def get_status_icon(self) -> str:
        """Get status icon for UI."""
        if self.error:
            return '⚠️'
        elif self.is_valid:
            return '✅'
        else:
            return '❌'
    
    def get_status_text(self) -> str:
        """Get human-readable status."""
        if self.error:
            return f'Error: {self.error}'
        elif self.is_valid:
            return 'Verified - Provably Fair'
        else:
            return f'FAILED - Mismatch detected (Δ={abs(self.calculated_roll - self.actual_roll):.3f})'


@dataclass
class VerificationReport:
    """Report for batch bet verification."""
    
    total_bets: int
    verified_bets: int
    failed_bets: int
    results: List[VerificationResult]
    timestamp: datetime
    
    def __post_init__(self):
        """Calculate statistics."""
        if not self.results:
            self.total_bets = 0
            self.verified_bets = 0
            self.failed_bets = 0
        else:
            self.total_bets = len(self.results)
            self.verified_bets = sum(1 for r in self.results if r.is_valid)
            self.failed_bets = sum(1 for r in self.results if not r.is_valid)
    
    def get_pass_rate(self) -> float:
        """Get percentage of verified bets."""
        if self.total_bets == 0:
            return 0.0
        return (self.verified_bets / self.total_bets) * 100.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'total_bets': self.total_bets,
            'verified_bets': self.verified_bets,
            'failed_bets': self.failed_bets,
            'pass_rate': self.get_pass_rate(),
            'timestamp': self.timestamp.isoformat(),
            'results': [r.to_dict() for r in self.results]
        }
    
    def to_csv(self) -> str:
        """Convert to CSV format."""
        lines = [
            'Bet Verification Report',
            f'Generated: {self.timestamp.isoformat()}',
            f'Total Bets: {self.total_bets}',
            f'Verified: {self.verified_bets}',
            f'Failed: {self.failed_bets}',
            f'Pass Rate: {self.get_pass_rate():.2f}%',
            '',
            'Nonce,Server Seed,Client Seed,Hash,Calculated Roll,Actual Roll,Status,Error'
        ]
        
        for result in self.results:
            status = 'PASS' if result.is_valid else 'FAIL'
            error = result.error or ''
            lines.append(
                f'{result.nonce},{result.server_seed},{result.client_seed},'
                f'{result.hash_value},{result.calculated_roll:.3f},'
                f'{result.actual_roll:.3f},{status},{error}'
            )
        
        return '\n'.join(lines)
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        rate = self.get_pass_rate()
        icon = '✅' if rate == 100.0 else '⚠️' if rate >= 95.0 else '❌'
        
        return (
            f'{icon} Verification Complete\n'
            f'Total: {self.total_bets} bets\n'
            f'Verified: {self.verified_bets}\n'
            f'Failed: {self.failed_bets}\n'
            f'Pass Rate: {rate:.2f}%'
        )
