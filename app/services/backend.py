"""
Business logic layer - wraps existing DuckDice API
Provides async interface for UI components
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from duckdice_api import DuckDiceAPI, DuckDiceConfig
from betbot_strategies import list_strategies, get_strategy
from faucet_manager import FaucetManager, FaucetConfig, CookieManager
from app.state.store import store, BetResult


class Backend:
    """Async wrapper for DuckDice API operations"""
    
    def __init__(self):
        self.api: Optional[DuckDiceAPI] = None
        self.faucet_manager: Optional[FaucetManager] = None
        self.cookie_manager = CookieManager()
        
    async def connect(self, api_key: str) -> tuple[bool, str]:
        """
        Connect to DuckDice API
        Returns: (success, message)
        """
        try:
            config = DuckDiceConfig(api_key=api_key)
            self.api = DuckDiceAPI(config)
            
            # Test connection
            balances = await asyncio.to_thread(self.api.get_balances)
            user_info = await asyncio.to_thread(self.api.get_user_info) if hasattr(self.api, 'get_user_info') else {}
            
            # Update store
            store.api_key = api_key
            store.connected = True
            store.username = user_info.get('username', 'User')
            
            # Load currencies
            currencies = await asyncio.to_thread(self.api.get_available_currencies)
            store.available_currencies = currencies
            
            # Initialize faucet manager
            faucet_config = FaucetConfig(
                enabled=store.faucet_auto_claim,
                interval=60,
                currency=store.currency
            )
            self.faucet_manager = FaucetManager(self.api, faucet_config)
            
            # Load saved cookie
            saved_cookie = self.cookie_manager.get_cookie()
            if saved_cookie:
                store.faucet_cookie = saved_cookie
            
            return True, f"Connected as {store.username}"
            
        except Exception as e:
            store.connected = False
            return False, f"Connection failed: {str(e)}"
    
    async def disconnect(self):
        """Disconnect from API"""
        if self.faucet_manager:
            self.faucet_manager.stop_auto_claim()
        
        self.api = None
        self.faucet_manager = None
        store.connected = False
        store.username = ""
    
    async def refresh_balances(self) -> bool:
        """Refresh balance values"""
        if not self.api:
            return False
        
        try:
            main = await asyncio.to_thread(
                self.api.get_main_balance, 
                store.currency
            )
            faucet = await asyncio.to_thread(
                self.api.get_faucet_balance,
                store.currency
            )
            
            store.update_balances(float(main), float(faucet))
            return True
            
        except Exception:
            return False
    
    async def place_bet(
        self,
        amount: float,
        chance: float,
        target: float,
        game_type: str = "dice"
    ) -> tuple[bool, str, Optional[BetResult]]:
        """
        Place a single bet
        Returns: (success, message, result)
        """
        if not self.api:
            return False, "Not connected", None
        
        try:
            # Determine if simulation
            is_simulation = store.mode == "simulation"
            use_faucet = store.betting_mode == "faucet"
            
            # Place bet
            if game_type == "dice":
                result = await asyncio.to_thread(
                    self.api.play_dice,
                    currency=store.currency,
                    amount=amount,
                    chance=chance,
                    target=target,
                    simulation=is_simulation,
                    faucet=use_faucet
                )
            else:
                # Range dice not implemented yet
                return False, "Range dice not supported", None
            
            # Create result object
            bet_result = BetResult(
                id=result.get('bet_id', ''),
                timestamp=datetime.now(),
                currency=store.currency,
                amount=amount,
                chance=chance,
                target=target,
                result=result.get('result', 0),
                profit=result.get('profit', 0),
                is_win=result.get('win', False),
                mode=store.betting_mode
            )
            
            # Update store
            store.add_bet_result(bet_result)
            
            # Refresh balances if live
            if not is_simulation:
                await self.refresh_balances()
            
            return True, "Bet placed successfully", bet_result
            
        except Exception as e:
            return False, f"Bet failed: {str(e)}", None
    
    async def claim_faucet(self) -> tuple[bool, str]:
        """Claim faucet manually"""
        if not self.faucet_manager:
            return False, "Faucet not initialized"
        
        try:
            result = await asyncio.to_thread(
                self.faucet_manager.claim_now
            )
            
            if result:
                await self.refresh_balances()
                return True, f"Faucet claimed! Next claim in 60s"
            else:
                return False, "Claim failed - check cookie or cooldown"
                
        except Exception as e:
            return False, f"Claim error: {str(e)}"
    
    def save_faucet_cookie(self, cookie: str):
        """Save faucet cookie"""
        self.cookie_manager.set_cookie(cookie)
        store.faucet_cookie = cookie
    
    def get_strategies(self) -> List[Dict[str, Any]]:
        """Get all available strategies"""
        strategies = list_strategies()
        return [
            {
                'id': s['id'],
                'name': s['name'],
                'description': s.get('description', ''),
                'risk_level': s.get('risk_level', 'medium'),
                'pros': s.get('pros', []),
                'cons': s.get('cons', []),
            }
            for s in strategies
        ]
    
    async def start_auto_bet(
        self,
        strategy_id: str,
        config: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Start automated betting with strategy"""
        # To be implemented - complex async loop
        return False, "Auto-bet not implemented yet"
    
    async def stop_auto_bet(self):
        """Stop automated betting"""
        store.auto_bet_running = False


# Global backend instance
backend = Backend()
