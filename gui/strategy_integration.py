"""
Strategy integration helper for bot_controller.

Converts between GUI state and strategy classes.
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, Deque
from decimal import Decimal
from collections import deque
import random
import time
import logging

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from duckdice_api.api import DuckDiceAPI
from betbot_strategies import get_strategy
from betbot_strategies.base import (
    StrategyContext, SessionLimits, BetSpec, BetResult, AutoBetStrategy
)

from gui.state import app_state, BetRecord
from datetime import datetime

logger = logging.getLogger(__name__)


class StrategyRunner:
    """Runs a strategy instance and manages its lifecycle."""
    
    def __init__(self, strategy_name: str, strategy_params: Dict[str, Any], api: DuckDiceAPI):
        """
        Initialize strategy runner.
        
        Args:
            strategy_name: Name of strategy (e.g. 'classic-martingale')
            strategy_params: Parameters from GUI
            api: DuckDiceAPI instance
        """
        self.strategy_name = strategy_name
        self.strategy_params = strategy_params
        self.api = api
        
        # Create strategy context
        self.ctx = self._create_context()
        
        # Get strategy class and instantiate
        strategy_class = get_strategy(strategy_name)
        self.strategy: AutoBetStrategy = strategy_class(strategy_params, self.ctx)
        
        logger.info(f"Initialized strategy: {strategy_name}")
    
    def _create_context(self) -> StrategyContext:
        """Create StrategyContext from app_state."""
        # Create session limits from stop conditions
        limits = SessionLimits(
            symbol=app_state.currency or "btc",
            stop_loss=-(app_state.stop_loss or 0.02),  # Negative for loss
            take_profit=app_state.stop_profit or 0.02,
            max_bet=Decimal(str(app_state.max_bet)) if app_state.max_bet else None,
            max_bets=app_state.max_bets,
            max_losses=None,
            max_duration_sec=None
        )
        
        # Create context
        ctx = StrategyContext(
            api=self.api,
            symbol=app_state.currency or "btc",
            faucet=app_state.use_faucet or False,
            dry_run=app_state.simulation_mode,
            rng=random.Random(),
            logger=self._log_bet,
            limits=limits,
            delay_ms=int((app_state.bet_delay or 1.0) * 1000),
            jitter_ms=100,
            recent_results=deque(maxlen=256),
            starting_balance=str(app_state.starting_balance or "0")
        )
        
        return ctx
    
    def _log_bet(self, data: Dict[str, Any]):
        """Logger callback for strategy."""
        logger.debug(f"Bet: {data}")
    
    def start_session(self):
        """Call strategy.on_session_start()."""
        self.strategy.on_session_start()
        logger.info("Strategy session started")
    
    def get_next_bet(self) -> Optional[BetSpec]:
        """Get next bet from strategy."""
        try:
            return self.strategy.next_bet()
        except Exception as e:
            logger.error(f"Error getting next bet: {e}")
            return None
    
    def process_result(self, result: BetResult):
        """Pass result to strategy."""
        try:
            self.strategy.on_bet_result(result)
            self.ctx.recent_results.append(result)
        except Exception as e:
            logger.error(f"Error processing result: {e}")
    
    def end_session(self, reason: str):
        """Call strategy.on_session_end()."""
        try:
            self.strategy.on_session_end(reason)
            logger.info(f"Strategy session ended: {reason}")
        except Exception as e:
            logger.error(f"Error ending session: {e}")


def bet_spec_to_api_params(spec: BetSpec) -> Dict[str, Any]:
    """
    Convert BetSpec to DuckDiceAPI.play_dice() parameters.
    
    Args:
        spec: BetSpec from strategy.next_bet()
    
    Returns:
        Dict with keys: amount, chance, bet_high
    """
    game = spec.get("game", "dice")
    
    if game == "dice":
        # Original dice game
        return {
            "amount": float(spec["amount"]),
            "chance": float(spec["chance"]),
            "bet_high": spec.get("is_high", True)
        }
    elif game == "range-dice":
        # Range dice - convert range to chance
        # For now, we'll convert to regular dice
        # This is a simplification - full range support needs more API work
        min_val, max_val = spec.get("range", (0, 50))
        chance = max_val - min_val
        is_in = spec.get("is_in", True)
        
        # If is_in, we want the roll to be in the range
        # Convert to high/low for regular dice
        return {
            "amount": float(spec["amount"]),
            "chance": float(chance),
            "bet_high": is_in  # Simplified mapping
        }
    else:
        raise ValueError(f"Unsupported game type: {game}")


def api_response_to_bet_result(api_response: Dict[str, Any], bet_spec: BetSpec) -> BetResult:
    """
    Convert API response to BetResult.
    
    Args:
        api_response: Response from DuckDiceAPI.play_dice()
            Expected keys: won (bool), result (float), payout (float)
        bet_spec: The BetSpec that was used for the bet
    
    Returns:
        BetResult for strategy processing
    """
    won = api_response.get("won", False)
    amount = Decimal(str(bet_spec["amount"]))
    
    # Calculate profit
    if won:
        payout = Decimal(str(api_response.get("payout", 0)))
        profit = payout - amount
    else:
        profit = -amount
    
    # Get updated balance (we'll fetch this separately if needed)
    balance = api_response.get("balance", "0")
    
    result: BetResult = {
        "win": won,
        "profit": str(profit),
        "balance": str(balance),
        "number": int(api_response.get("result", 0)),
        "payout": str(api_response.get("payout", 0)),
        "chance": bet_spec.get("chance", "0"),
        "is_high": bet_spec.get("is_high"),
        "range": bet_spec.get("range"),
        "is_in": bet_spec.get("is_in"),
        "api_raw": api_response,
        "simulated": False,
        "timestamp": time.time()
    }
    
    return result


def bet_result_to_bet_record(result: BetResult, strategy_name: str) -> BetRecord:
    """
    Convert BetResult to BetRecord for app_state.
    
    Args:
        result: BetResult from strategy processing
        strategy_name: Name of strategy
    
    Returns:
        BetRecord for GUI display
    """
    # Calculate amount from profit
    profit = float(result["profit"])
    won = result["win"]
    
    if won:
        payout = float(result.get("payout", 0))
        amount = payout - profit
    else:
        amount = -profit
    
    return BetRecord(
        timestamp=datetime.fromtimestamp(result.get("timestamp", time.time())),
        amount=amount,
        target=float(result.get("chance", 0)),
        roll=float(result.get("number", 0)),
        won=won,
        profit=profit,
        balance=float(result["balance"]),
        strategy=strategy_name
    )
