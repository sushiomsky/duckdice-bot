"""
Verification Package.

Provably fair bet verification for DuckDice.
"""

from .bet_verifier import BetVerifier, calculate_roll
from .models import VerificationResult, VerificationReport

__all__ = [
    'BetVerifier',
    'calculate_roll',
    'VerificationResult',
    'VerificationReport',
]
