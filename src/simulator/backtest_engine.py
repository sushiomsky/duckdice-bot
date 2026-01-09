"""
Backtesting framework for strategy validation.
"""

import json
import csv
from pathlib import Path
from decimal import Decimal
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .models import SimulationConfig, SimulatedBet, SimulationResult
from .simulation_engine import SimulationEngine
from .performance_metrics import MetricsCalculator
from .risk_analyzer import RiskAnalyzer

logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """Load and parse historical bet data."""
    
    @staticmethod
    def load_from_csv(filepath: Path) -> List[Dict[str, Any]]:
        """
        Load historical data from CSV file.
        
        Expected columns: outcome, timestamp (optional)
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of outcome dictionaries
        """
        outcomes = []
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                outcome = {
                    'outcome': float(row.get('outcome', row.get('roll', 0))),
                    'timestamp': row.get('timestamp'),
                }
                outcomes.append(outcome)
        
        logger.info(f"Loaded {len(outcomes)} outcomes from CSV: {filepath}")
        return outcomes
    
    @staticmethod
    def load_from_json(filepath: Path) -> List[Dict[str, Any]]:
        """
        Load historical data from JSON file.
        
        Expected format: Array of objects with 'outcome' field
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            List of outcome dictionaries
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle both array of objects and single object with bets array
        if isinstance(data, list):
            outcomes = data
        elif isinstance(data, dict) and 'bets' in data:
            outcomes = data['bets']
        else:
            raise ValueError("Invalid JSON format")
        
        # Extract outcomes
        result = []
        for item in outcomes:
            outcome = {
                'outcome': float(item.get('outcome', item.get('roll', 0))),
                'timestamp': item.get('timestamp'),
            }
            result.append(outcome)
        
        logger.info(f"Loaded {len(result)} outcomes from JSON: {filepath}")
        return result
    
    @staticmethod
    def load_from_bet_history(bet_history_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Load from bet_history/ directory (latest file).
        
        Args:
            bet_history_dir: Optional custom bet history directory
            
        Returns:
            List of outcome dictionaries
        """
        if bet_history_dir is None:
            bet_history_dir = Path('bet_history')
        
        if not bet_history_dir.exists():
            raise FileNotFoundError(f"Bet history directory not found: {bet_history_dir}")
        
        # Find latest JSON file
        json_files = list(bet_history_dir.glob('*.json'))
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in {bet_history_dir}")
        
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Loading latest bet history: {latest_file}")
        
        return HistoricalDataLoader.load_from_json(latest_file)


class HistoricalOutcomeGenerator:
    """Generate outcomes from historical data."""
    
    def __init__(self, outcomes: List[Dict[str, Any]]):
        """Initialize with historical outcomes."""
        self.outcomes = outcomes
        self._index = 0
        
    def generate(self) -> float:
        """Get next historical outcome."""
        if self._index >= len(self.outcomes):
            # Loop back to start if we run out
            self._index = 0
        
        outcome = self.outcomes[self._index]['outcome']
        self._index += 1
        return outcome
    
    def reset(self):
        """Reset to start of historical data."""
        self._index = 0


class BacktestEngine:
    """Backtesting engine for strategy validation."""
    
    def __init__(self):
        """Initialize backtest engine."""
        self.historical_outcomes: List[Dict[str, Any]] = []
        
    def load_history_csv(self, filepath: Path):
        """Load historical outcomes from CSV."""
        self.historical_outcomes = HistoricalDataLoader.load_from_csv(filepath)
        
    def load_history_json(self, filepath: Path):
        """Load historical outcomes from JSON."""
        self.historical_outcomes = HistoricalDataLoader.load_from_json(filepath)
        
    def load_history_dir(self, bet_history_dir: Optional[Path] = None):
        """Load from bet_history/ directory."""
        self.historical_outcomes = HistoricalDataLoader.load_from_bet_history(
            bet_history_dir
        )
    
    def run_backtest(
        self,
        strategy_func: callable,
        starting_balance: float,
        currency: str = 'USD',
        max_bets: Optional[int] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> SimulationResult:
        """
        Run backtest with historical data.
        
        Args:
            strategy_func: Strategy function (state) -> (amount, chance, roll_over)
            starting_balance: Starting balance
            currency: Currency code
            max_bets: Maximum number of bets (None = use all history)
            strategy_params: Optional strategy parameters
            
        Returns:
            SimulationResult with complete analysis
        """
        if not self.historical_outcomes:
            raise ValueError("No historical data loaded")
        
        logger.info(f"Starting backtest with {len(self.historical_outcomes)} outcomes")
        
        # Create simulation config
        config = SimulationConfig(
            starting_balance=Decimal(str(starting_balance)),
            currency=currency,
            house_edge=3.0,  # DuckDice standard
            max_bets=max_bets,
        )
        
        # Create virtual balance
        from .simulation_engine import VirtualBalance
        balance = VirtualBalance(config.starting_balance, config.currency)
        
        # Create historical outcome generator
        outcome_gen = HistoricalOutcomeGenerator(self.historical_outcomes)
        
        # Initialize strategy state
        strategy_state = {
            'balance': balance.balance,
            'starting_balance': balance.starting_balance,
            'bet_count': 0,
            'wins': 0,
            'losses': 0,
            'params': strategy_params or {},
        }
        
        # Run backtest
        bets: List[SimulatedBet] = []
        start_time = datetime.now()
        
        num_bets = min(max_bets or len(self.historical_outcomes), len(self.historical_outcomes))
        
        for i in range(num_bets):
            # Get strategy decision
            try:
                amount, chance, roll_over = strategy_func(strategy_state)
            except Exception as e:
                logger.error(f"Strategy error at bet {i+1}: {e}")
                break
            
            # Check if can afford
            bet_amount = Decimal(str(amount))
            if not balance.can_afford(bet_amount):
                logger.warning(f"Insufficient balance at bet {i+1}")
                break
            
            # Get historical outcome
            outcome = outcome_gen.generate()
            
            # Determine win/loss
            if roll_over:
                won = outcome > (100 - chance)
            else:
                won = outcome < chance
            
            # Calculate profit
            if won:
                multiplier = 100 / chance
                payout = bet_amount * Decimal(str(multiplier))
                house_edge_mult = Decimal(str(1 - config.house_edge / 100))
                payout = payout * house_edge_mult
                profit = payout - bet_amount
            else:
                profit = -bet_amount
            
            # Update balance
            new_balance = balance.update(profit)
            
            # Record bet
            bet = SimulatedBet(
                bet_number=i + 1,
                timestamp=datetime.now(),
                amount=bet_amount,
                chance=chance,
                roll_over=roll_over,
                outcome=outcome,
                won=won,
                profit=profit,
                balance_after=new_balance,
            )
            bets.append(bet)
            
            # Update strategy state
            strategy_state['balance'] = new_balance
            strategy_state['bet_count'] = i + 1
            if won:
                strategy_state['wins'] += 1
            else:
                strategy_state['losses'] += 1
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Calculate metrics and risk
        metrics = MetricsCalculator.calculate(bets, config.starting_balance)
        risk = RiskAnalyzer.analyze(bets, config.starting_balance)
        
        result = SimulationResult(
            config=config,
            bets=bets,
            metrics=metrics,
            risk_analysis=risk,
            final_balance=bets[-1].balance_after if bets else config.starting_balance,
            total_time=total_time,
        )
        
        logger.info(
            f"Backtest complete: {len(bets)} bets, "
            f"final balance: {result.final_balance}, "
            f"P/L: {metrics.profit_loss}"
        )
        
        return result
    
    def compare_strategies(
        self,
        strategies: Dict[str, tuple[callable, Optional[Dict[str, Any]]]],
        starting_balance: float,
        currency: str = 'USD',
        max_bets: Optional[int] = None,
    ) -> Dict[str, SimulationResult]:
        """
        Compare multiple strategies with same historical data.
        
        Args:
            strategies: Dict of {name: (strategy_func, params)}
            starting_balance: Starting balance
            currency: Currency code
            max_bets: Maximum bets per strategy
            
        Returns:
            Dict of {name: SimulationResult}
        """
        results = {}
        
        for name, (strategy_func, params) in strategies.items():
            logger.info(f"Running backtest for strategy: {name}")
            result = self.run_backtest(
                strategy_func,
                starting_balance,
                currency,
                max_bets,
                params,
            )
            results[name] = result
        
        return results
