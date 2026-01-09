"""
Bot controller - Bridge between GUI and bot logic.
Handles threading, exceptions, and state updates.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import threading
import time
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from decimal import Decimal

from gui.state import app_state, BetRecord

# Optional imports - not needed for simulation mode
try:
    from src.duckdice_api.client import EnhancedAPIClient
except ImportError:
    EnhancedAPIClient = None

try:
    from src.betbot_strategies.base import StrategyContext, SessionLimits, BetResult
except ImportError:
    StrategyContext = SessionLimits = BetResult = None

try:
    from src.simulation_engine import SimulationEngine
except ImportError:
    SimulationEngine = None


logger = logging.getLogger(__name__)


class BotController:
    """
    Controls bot execution in background thread.
    Provides start/stop/pause/resume interface.
    """
    
    def __init__(self):
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.api_client: Optional[DuckDiceClient] = None
        self.strategy_runner: Optional[Callable] = None
        self.update_callback: Optional[Callable] = None
        
    def set_update_callback(self, callback: Callable):
        """Set callback for UI updates"""
        self.update_callback = callback
        
    def is_running(self) -> bool:
        """Check if bot is currently running"""
        return app_state.get('running', False) and self.thread and self.thread.is_alive()
    
    def is_paused(self) -> bool:
        """Check if bot is paused"""
        return app_state.get('paused', False)
    
    def start(self, strategy_name: str, strategy_params: Dict[str, Any]):
        """Start bot with given strategy"""
        if self.is_running():
            raise RuntimeError("Bot is already running")
        
        # Validate inputs
        if not app_state.api_key and not app_state.simulation_mode:
            raise ValueError("API key required for live mode")
        
        # Reset state
        app_state.update(
            running=True,
            paused=False,
            current_strategy=strategy_name,
            strategy_params=strategy_params,
            last_error=""
        )
        
        # Start bot thread
        self.stop_event.clear()
        self.pause_event.clear()
        
        self.thread = threading.Thread(
            target=self._run_bot,
            args=(strategy_name, strategy_params),
            daemon=True
        )
        self.thread.start()
        logger.info(f"Bot started with strategy: {strategy_name}")
    
    def stop(self):
        """Stop bot immediately"""
        if not self.is_running():
            return
        
        logger.info("Stopping bot...")
        self.stop_event.set()
        app_state.update(running=False, paused=False)
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("Bot stopped")
    
    def pause(self):
        """Pause bot (between bets)"""
        if not self.is_running() or self.is_paused():
            return
        
        logger.info("Pausing bot...")
        self.pause_event.set()
        app_state.update(paused=True)
    
    def resume(self):
        """Resume paused bot"""
        if not self.is_running() or not self.is_paused():
            return
        
        logger.info("Resuming bot...")
        self.pause_event.clear()
        app_state.update(paused=False)
    
    def _run_bot(self, strategy_name: str, strategy_params: Dict[str, Any]):
        """Main bot loop (runs in background thread)"""
        try:
            if app_state.simulation_mode:
                self._run_simulation(strategy_name, strategy_params)
            else:
                self._run_live(strategy_name, strategy_params)
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
            app_state.update(
                running=False,
                paused=False,
                last_error=str(e)
            )
            if self.update_callback:
                self.update_callback()
    
    def _run_simulation(self, strategy_name: str, strategy_params: Dict[str, Any]):
        """Run in simulation mode"""
        logger.info("Running in SIMULATION mode")
        
        # Get current balance or use default
        balance = app_state.balance if app_state.balance > 0 else 1.0
        app_state.update(starting_balance=balance, balance=balance)
        
        bet_count = 0
        max_bets = strategy_params.get('max_bets', 100)
        
        while not self.stop_event.is_set() and bet_count < max_bets:
            # Check pause
            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.1)
            
            if self.stop_event.is_set():
                break
            
            # Simulate a bet
            self._simulate_bet(strategy_name, strategy_params)
            bet_count += 1
            
            # Check stop conditions
            if self._should_stop():
                logger.info("Stop condition met")
                break
            
            # Small delay
            time.sleep(0.1)
        
        app_state.update(running=False, paused=False)
        logger.info(f"Simulation complete: {bet_count} bets")
    
    def _simulate_bet(self, strategy_name: str, params: Dict[str, Any]):
        """Simulate a single bet"""
        import random
        
        # Get bet amount (simple logic for simulation)
        amount = params.get('base_bet', 0.001)
        target = params.get('target_chance', 50.0)
        
        # Simulate roll
        roll = random.uniform(0, 100)
        won = roll >= (100 - target)  # Simplified win logic
        
        # Calculate profit
        if won:
            multiplier = 99 / target
            profit = amount * (multiplier - 1)
        else:
            profit = -amount
        
        # Update balance
        new_balance = app_state.balance + profit
        app_state.update(balance=new_balance)
        
        # Update stats
        app_state.update(
            total_bets=app_state.total_bets + 1,
            wins=app_state.wins + (1 if won else 0),
            losses=app_state.losses + (0 if won else 1),
            profit=app_state.profit + profit,
            profit_percent=((new_balance - app_state.starting_balance) / app_state.starting_balance * 100)
        )
        
        # Update streak
        if won:
            if app_state.streak_type == "win":
                app_state.update(current_streak=app_state.current_streak + 1)
            else:
                app_state.update(current_streak=1, streak_type="win")
        else:
            if app_state.streak_type == "loss":
                app_state.update(current_streak=app_state.current_streak + 1)
            else:
                app_state.update(current_streak=1, streak_type="loss")
        
        # Add to history
        bet_record = BetRecord(
            timestamp=datetime.now(),
            amount=amount,
            target=target,
            roll=roll,
            won=won,
            profit=profit,
            balance=new_balance,
            strategy=strategy_name
        )
        app_state.add_bet(bet_record)
        
        # Trigger UI update
        if self.update_callback:
            self.update_callback()
    
    def _run_live(self, strategy_name: str, strategy_params: Dict[str, Any]):
        """Run with real API (not implemented for safety)"""
        raise NotImplementedError("Live mode requires full strategy integration")
    
    def _should_stop(self) -> bool:
        """Check if stop conditions are met"""
        # Check profit target
        if app_state.stop_profit and app_state.profit_percent >= (app_state.stop_profit * 100):
            return True
        
        # Check loss limit
        if app_state.stop_loss and app_state.profit_percent <= (app_state.stop_loss * 100):
            return True
        
        # Check max bets
        if app_state.max_bets and app_state.total_bets >= app_state.max_bets:
            return True
        
        return False


# Global controller instance
bot_controller = BotController()
