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
# Import all strategies to register them
from betbot_strategies import (
    classic_martingale,
    anti_martingale_streak,
    labouchere,
    dalembert,
    fibonacci,
    paroli,
    oscars_grind,
    one_three_two_six,
    rng_analysis_strategy,
    target_aware,
    faucet_cashout,
    kelly_capped,
    max_wager_flow,
    range50_random,
    fib_loss_cluster,
    custom_script
)
from faucet_manager import FaucetManager, FaucetConfig, CookieManager
from app.state.store import store, BetResult


class Backend:
    """Async wrapper for DuckDice API operations"""
    
    def __init__(self):
        self.api: Optional[DuckDiceAPI] = None
        self.faucet_manager: Optional[FaucetManager] = None
        self.cookie_manager = CookieManager()
        self._refresh_task: Optional[asyncio.Task] = None
        
    def start_auto_refresh(self, interval: int = 30):
        """Start automatic balance refresh"""
        if self._refresh_task and not self._refresh_task.done():
            return
        
        async def refresh_loop():
            while self.api and store.connected:
                await asyncio.sleep(interval)
                await self.refresh_balances()
        
        self._refresh_task = asyncio.create_task(refresh_loop())
    
    def stop_auto_refresh(self):
        """Stop automatic balance refresh"""
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
        
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
            
            # Start auto-refresh
            self.start_auto_refresh(30)
            
            return True, f"Connected as {store.username}"
            
        except Exception as e:
            store.connected = False
            return False, f"Connection failed: {str(e)}"
    
    async def disconnect(self):
        """Disconnect from API"""
        if self.faucet_manager:
            self.faucet_manager.stop_auto_claim()
        
        self.stop_auto_refresh()
        
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
        
        # Transform to expected format
        result = []
        for s in strategies:
            strategy_id = s.get('name', '')
            
            # Try to get the class to extract metadata
            try:
                cls = get_strategy(strategy_id)
                metadata = {}
                
                # Try to get metadata if available
                if hasattr(cls, 'get_metadata') and callable(getattr(cls, 'get_metadata')):
                    try:
                        metadata = cls.get_metadata()
                    except:
                        pass
                
                result.append({
                    'id': strategy_id,
                    'name': metadata.get('name', strategy_id.replace('_', ' ').title()),
                    'description': s.get('description', metadata.get('description', '')),
                    'risk_level': metadata.get('risk_level', 'medium'),
                    'pros': metadata.get('pros', []),
                    'cons': metadata.get('cons', []),
                })
            except:
                # Fallback if strategy class not found
                result.append({
                    'id': strategy_id,
                    'name': strategy_id.replace('_', ' ').title(),
                    'description': s.get('description', ''),
                    'risk_level': 'medium',
                    'pros': [],
                    'cons': [],
                })
        
        return result
    
    async def start_auto_bet(
        self,
        strategy_id: str,
        base_bet: float,
        max_bets: int = 0,
        stop_loss: float = 0.0,
        take_profit: float = 0.0
    ) -> tuple[bool, str]:
        """Start automated betting with strategy"""
        if not self.api:
            return False, "Not connected to API"
        
        if store.auto_bet_running:
            return False, "Auto-bet already running"
        
        # Get strategy
        strategy = get_strategy(strategy_id)
        if not strategy:
            return False, f"Strategy not found: {strategy_id}"
        
        # Mark as running
        store.auto_bet_running = True
        store.auto_bet_count = 0
        
        # Start betting loop in background
        asyncio.create_task(self._auto_bet_loop(
            strategy=strategy,
            base_bet=base_bet,
            max_bets=max_bets,
            stop_loss=stop_loss,
            take_profit=take_profit
        ))
        
        return True, f"Auto-bet started with {strategy['name']}"
    
    async def _auto_bet_loop(
        self,
        strategy: Dict[str, Any],
        base_bet: float,
        max_bets: int,
        stop_loss: float,
        take_profit: float
    ):
        """Background auto-bet execution loop"""
        starting_balance = store.get_current_balance()
        
        try:
            while store.auto_bet_running:
                # Check stop conditions
                current_balance = store.get_current_balance()
                profit = current_balance - starting_balance
                
                # Stop loss check
                if stop_loss > 0 and profit <= -stop_loss:
                    await self.stop_auto_bet()
                    break
                
                # Take profit check
                if take_profit > 0 and profit >= take_profit:
                    await self.stop_auto_bet()
                    break
                
                # Max bets check
                if max_bets > 0 and store.auto_bet_count >= max_bets:
                    await self.stop_auto_bet()
                    break
                
                # Place bet using strategy
                # For now, simple implementation - just use base bet at 50% chance
                # Real implementation would call strategy.get_next_bet()
                success, message, result = await self.place_bet(
                    amount=base_bet,
                    chance=50.0,
                    target=50.0
                )
                
                if success:
                    store.auto_bet_count += 1
                    # Small delay between bets
                    await asyncio.sleep(1)
                else:
                    # Error occurred, stop
                    await self.stop_auto_bet()
                    break
                    
        except Exception as e:
            print(f"Auto-bet error: {e}")
            await self.stop_auto_bet()
    
    async def stop_auto_bet(self):
        """Stop automated betting"""
        store.auto_bet_running = False


# Global backend instance
backend = Backend()
