"""
Bet Verifier.

Implements provably fair verification for DuckDice bets using SHA-256.
"""

import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import VerificationResult, VerificationReport


def calculate_roll(server_seed: str, client_seed: str, nonce: int) -> float:
    """
    Calculate the provably fair roll result.
    
    DuckDice Algorithm:
    1. Concatenate: server_seed + client_seed + nonce
    2. SHA-256 hash the combination
    3. Take first 5 hex characters
    4. Convert to decimal
    5. Roll = (decimal % 100000) / 1000.0
    
    Args:
        server_seed: Server's secret seed (revealed after use)
        client_seed: Client's seed
        nonce: Bet number/counter
        
    Returns:
        Roll result (0.000 - 99.999)
        
    Example:
        >>> calculate_roll("server123", "client456", 0)
        45.678
    """
    # Combine seeds and nonce
    message = f"{server_seed}{client_seed}{nonce}"
    
    # SHA-256 hash
    hash_object = hashlib.sha256(message.encode('utf-8'))
    hash_hex = hash_object.hexdigest()
    
    # Take first 5 hex characters
    first_5_hex = hash_hex[:5]
    
    # Convert to decimal
    decimal_value = int(first_5_hex, 16)
    
    # Calculate roll (0.000 - 99.999)
    roll = (decimal_value % 100000) / 1000.0
    
    return roll


def get_full_hash(server_seed: str, client_seed: str, nonce: int) -> str:
    """
    Get the full SHA-256 hash for verification display.
    
    Args:
        server_seed: Server's secret seed
        client_seed: Client's seed
        nonce: Bet number
        
    Returns:
        Full SHA-256 hash (hex string)
    """
    message = f"{server_seed}{client_seed}{nonce}"
    hash_object = hashlib.sha256(message.encode('utf-8'))
    return hash_object.hexdigest()


class BetVerifier:
    """
    Provably fair bet verifier for DuckDice.
    
    Verifies that bet results match the cryptographic calculation,
    proving the server didn't manipulate the outcome.
    """
    
    # Tolerance for floating point comparison (0.001 = 1 decimal place)
    ROLL_TOLERANCE = 0.001
    
    def verify_bet(
        self,
        server_seed: str,
        client_seed: str,
        nonce: int,
        actual_roll: float
    ) -> VerificationResult:
        """
        Verify a single bet.
        
        Args:
            server_seed: Server's revealed seed
            client_seed: Client's seed used for bet
            nonce: Bet nonce/counter
            actual_roll: Actual roll result from bet
            
        Returns:
            VerificationResult with verification details
        """
        try:
            # Calculate expected roll
            calculated_roll = calculate_roll(server_seed, client_seed, nonce)
            
            # Get full hash for display
            hash_value = get_full_hash(server_seed, client_seed, nonce)
            
            # Compare results (with tolerance for float precision)
            is_valid = abs(calculated_roll - actual_roll) < self.ROLL_TOLERANCE
            
            return VerificationResult(
                is_valid=is_valid,
                calculated_roll=calculated_roll,
                actual_roll=actual_roll,
                server_seed=server_seed,
                client_seed=client_seed,
                nonce=nonce,
                hash_value=hash_value
            )
            
        except Exception as e:
            # Handle any verification errors
            return VerificationResult(
                is_valid=False,
                calculated_roll=0.0,
                actual_roll=actual_roll,
                server_seed=server_seed,
                client_seed=client_seed,
                nonce=nonce,
                hash_value='',
                error=str(e)
            )
    
    def verify_batch(
        self,
        bets: List[Dict[str, Any]]
    ) -> VerificationReport:
        """
        Verify multiple bets in batch.
        
        Args:
            bets: List of bet dictionaries with keys:
                - server_seed: Server's revealed seed
                - client_seed: Client seed
                - nonce: Bet nonce
                - roll: Actual roll result
                
        Returns:
            VerificationReport with all results
        """
        results = []
        
        for bet in bets:
            result = self.verify_bet(
                server_seed=bet.get('server_seed', ''),
                client_seed=bet.get('client_seed', ''),
                nonce=bet.get('nonce', 0),
                actual_roll=bet.get('roll', 0.0)
            )
            results.append(result)
        
        return VerificationReport(
            total_bets=len(results),
            verified_bets=0,  # Will be calculated in __post_init__
            failed_bets=0,     # Will be calculated in __post_init__
            results=results,
            timestamp=datetime.now()
        )
    
    def verify_win_calculation(
        self,
        roll: float,
        target: str,
        prediction: float
    ) -> bool:
        """
        Verify if a bet result is a win.
        
        Args:
            roll: Actual roll result
            target: 'over' or 'under'
            prediction: Prediction value (chance)
            
        Returns:
            True if win, False if loss
        """
        if target.lower() == 'over':
            return roll > prediction
        elif target.lower() == 'under':
            return roll < prediction
        else:
            raise ValueError(f"Invalid target: {target}")
    
    def get_calculation_steps(
        self,
        server_seed: str,
        client_seed: str,
        nonce: int
    ) -> Dict[str, Any]:
        """
        Get detailed calculation steps for educational/debugging purposes.
        
        Args:
            server_seed: Server seed
            client_seed: Client seed
            nonce: Nonce
            
        Returns:
            Dictionary with step-by-step breakdown
        """
        # Step 1: Concatenate
        message = f"{server_seed}{client_seed}{nonce}"
        
        # Step 2: Hash
        hash_object = hashlib.sha256(message.encode('utf-8'))
        hash_hex = hash_object.hexdigest()
        
        # Step 3: Extract first 5 hex chars
        first_5_hex = hash_hex[:5]
        
        # Step 4: Convert to decimal
        decimal_value = int(first_5_hex, 16)
        
        # Step 5: Calculate roll
        modulo_result = decimal_value % 100000
        roll = modulo_result / 1000.0
        
        return {
            'step1_message': message,
            'step2_hash': hash_hex,
            'step3_first_5_hex': first_5_hex,
            'step4_decimal': decimal_value,
            'step5_modulo': modulo_result,
            'step6_roll': roll,
            'formula': f'({decimal_value} % 100000) / 1000 = {roll:.3f}'
        }


# Convenience function for quick verification
def verify_single_bet(
    server_seed: str,
    client_seed: str,
    nonce: int,
    actual_roll: float
) -> VerificationResult:
    """
    Quick verification of a single bet.
    
    Args:
        server_seed: Server seed
        client_seed: Client seed
        nonce: Nonce
        actual_roll: Actual roll
        
    Returns:
        VerificationResult
    """
    verifier = BetVerifier()
    return verifier.verify_bet(server_seed, client_seed, nonce, actual_roll)
