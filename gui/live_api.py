"""
Live API Integration Module
Connects GUI to real DuckDice API for live betting
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from gui.state import app_state, BetRecord
from src.duckdice_api.api import DuckDiceAPI
from src.duckdice_api.config import DuckDiceConfig

logger = logging.getLogger(__name__)


class LiveAPIManager:
    """
    Manages live API connection and bet execution.
    Wraps DuckDiceAPI with GUI-specific error handling.
    """
    
    def __init__(self):
        self.client: Optional[DuckDiceAPI] = None
        self.connected = False
        self.currency = 'BTC'  # Default currency
    
    def connect(self, api_key: str, currency: str = 'BTC') -> tuple[bool, str]:
        """
        Initialize API client and test connection.
        Returns: (success: bool, message: str)
        """
        try:
            # Create config and client
            config = DuckDiceConfig(api_key=api_key)
            self.client = DuckDiceAPI(config)
            self.currency = currency
            
            # Test connection by fetching balance
            balance = self.client.get_main_balance(currency)
            self.connected = True
            
            # Update app state with real balance
            app_state.update(balance=balance, starting_balance=balance)
            
            logger.info(f"Successfully connected to DuckDice API. Balance: {balance} {currency}")
            return True, f"Connected successfully! Balance: {balance:.8f} {currency}"
            
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            self.connected = False
            return False, f"Connection failed: {str(e)}"
    
    def disconnect(self):
        """Close API connection"""
        self.client = None
        self.connected = False
        logger.info("Disconnected from DuckDice API")
    
    def is_connected(self) -> bool:
        """Check if API is connected"""
        return self.connected and self.client is not None
    
    def place_bet(self, amount: float, target_chance: float, bet_high: bool = True) -> Optional[BetRecord]:
        """
        Place a bet on DuckDice.
        
        Args:
            amount: Bet amount in BTC
            target_chance: Win probability (0.01 - 98.99)
            bet_high: True to bet on roll > target, False for roll < target
        
        Returns:
            BetRecord if successful, None if failed
        """
        if not self.is_connected():
            logger.error("Cannot place bet: not connected to API")
            return None
        
        try:
            # Place bet via API
            result = self.client.play_dice(
                symbol=self.currency,
                amount=amount,
                target=target_chance,
                bet_type='over' if bet_high else 'under'
            )
            
            # Parse API response
            won = result.get('won', False)
            roll = result.get('result', 0.0)
            payout = result.get('payout', 0.0) if won else 0.0
            profit = payout - amount if won else -amount
            
            # Get updated balance
            new_balance = self.client.get_main_balance(self.currency)
            app_state.update(balance=new_balance)
            
            # Create bet record
            bet_record = BetRecord(
                timestamp=datetime.now(),
                amount=amount,
                target=target_chance,
                roll=roll,
                won=won,
                profit=profit,
                balance=new_balance,
                strategy=app_state.strategy_name or 'unknown'
            )
            
            logger.info(f"Bet placed: {amount} {self.currency} @ {target_chance}% -> {'WIN' if won else 'LOSS'}")
            return bet_record
            
        except Exception as e:
            logger.error(f"Failed to place bet: {e}", exc_info=True)
            app_state.update(last_error=str(e))
            return None
    
    def get_balance(self) -> Optional[float]:
        """Fetch current balance from API"""
        if not self.is_connected():
            return None
        
        try:
            balance = self.client.get_main_balance(self.currency)
            app_state.update(balance=balance)
            return balance
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            return None
    
    def get_user_info(self) -> Optional[Dict]:
        """Fetch user information from API"""
        if not self.is_connected():
            return None
        
        try:
            user_info = self.client.get_user_info()
            return user_info
        except Exception as e:
            logger.error(f"Failed to fetch user info: {e}")
            return None


# Global instance
live_api = LiveAPIManager()
