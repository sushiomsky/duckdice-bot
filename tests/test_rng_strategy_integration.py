#!/usr/bin/env python3
"""
Tests for RNG Analysis to Strategy Integration

Tests the integration between RNG analysis results and betting strategies.
"""

import sys
import unittest
from pathlib import Path
from collections import deque
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestRNGStrategyIntegration(unittest.TestCase):
    """Test RNG analysis strategy integration"""
    
    def test_strategy_registration(self):
        """Test that RNG analysis strategy is registered"""
        from betbot_strategies import rng_analysis_strategy
        from betbot_strategies import list_strategies, get_strategy
        
        # Check it's in the list
        strategies = list_strategies()
        strategy_names = [s['name'] for s in strategies]
        
        self.assertIn('rng-analysis-strategy', strategy_names)
        
        # Check we can get it
        StrategyClass = get_strategy('rng-analysis-strategy')
        self.assertEqual(StrategyClass.name(), 'rng-analysis-strategy')
    
    def test_strategy_schema(self):
        """Test strategy schema is properly defined"""
        from betbot_strategies import rng_analysis_strategy
        from betbot_strategies import get_strategy
        
        StrategyClass = get_strategy('rng-analysis-strategy')
        schema = StrategyClass.schema()
        
        # Check required fields
        required_fields = [
            'base_amount', 'chance', 'is_high',
            'use_patterns', 'config_file'
        ]
        
        for field in required_fields:
            self.assertIn(field, schema)
        
        # Check field structure
        for field, spec in schema.items():
            self.assertIn('type', spec)
            self.assertIn('desc', spec)
    
    def test_strategy_instantiation(self):
        """Test strategy can be instantiated"""
        from betbot_strategies import rng_analysis_strategy
        from betbot_strategies import get_strategy
        from betbot_strategies.base import StrategyContext, SessionLimits
        from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
        
        StrategyClass = get_strategy('rng-analysis-strategy')
        
        # Create mock context
        api = DuckDiceAPI(DuckDiceConfig(api_key='test'))
        ctx = StrategyContext(
            api=api,
            symbol='XLM',
            faucet=True,
            dry_run=True,
            rng=random.Random(42),
            logger=lambda x: None,
            limits=SessionLimits(symbol='XLM'),
            recent_results=deque(maxlen=256)
        )
        
        # Instantiate with minimal params
        params = {
            'base_amount': '0.000001',
            'chance': '50',
        }
        
        strategy = StrategyClass(params, ctx)
        
        # Check attributes
        self.assertEqual(str(strategy.base_amount), '0.000001')
        self.assertEqual(strategy.chance, '50')
    
    def test_strategy_next_bet(self):
        """Test strategy generates valid bets"""
        from betbot_strategies import rng_analysis_strategy
        from betbot_strategies import get_strategy
        from betbot_strategies.base import StrategyContext, SessionLimits
        from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
        
        StrategyClass = get_strategy('rng-analysis-strategy')
        
        api = DuckDiceAPI(DuckDiceConfig(api_key='test'))
        ctx = StrategyContext(
            api=api,
            symbol='XLM',
            faucet=True,
            dry_run=True,
            rng=random.Random(42),
            logger=lambda x: None,
            limits=SessionLimits(symbol='XLM'),
            recent_results=deque(maxlen=256)
        )
        
        params = {
            'base_amount': '0.000001',
            'chance': '50',
            'is_high': True,
        }
        
        strategy = StrategyClass(params, ctx)
        
        # Generate bet
        bet = strategy.next_bet()
        
        # Validate bet structure
        self.assertIsNotNone(bet)
        self.assertIn('game', bet)
        self.assertIn('amount', bet)
        self.assertIn('chance', bet)
        self.assertIn('is_high', bet)
        
        # Validate values
        self.assertEqual(bet['game'], 'dice')
        self.assertEqual(bet['chance'], '50')
        self.assertTrue(bet['is_high'])
        
        # Amount should be parseable
        from decimal import Decimal
        amount = Decimal(bet['amount'])
        self.assertGreater(amount, 0)
    
    def test_strategy_bet_result_handling(self):
        """Test strategy handles bet results correctly"""
        from betbot_strategies import rng_analysis_strategy
        from betbot_strategies import get_strategy
        from betbot_strategies.base import StrategyContext, SessionLimits, BetResult
        from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
        
        StrategyClass = get_strategy('rng-analysis-strategy')
        
        api = DuckDiceAPI(DuckDiceConfig(api_key='test'))
        ctx = StrategyContext(
            api=api,
            symbol='XLM',
            faucet=True,
            dry_run=True,
            rng=random.Random(42),
            logger=lambda x: None,
            limits=SessionLimits(symbol='XLM'),
            recent_results=deque(maxlen=256)
        )
        
        params = {
            'base_amount': '0.000001',
            'chance': '50',
            'loss_multiplier': 2.0,
        }
        
        strategy = StrategyClass(params, ctx)
        
        # Simulate a loss - using only required and applicable fields
        result: BetResult = {
            'win': False,
            'profit': '-0.000001',
            'balance': '0.001',
            'number': 5000,
            'payout': '2.0',
            'chance': '50',
            'is_high': True,
            'range': None,  # Not applicable for dice game
            'is_in': None,  # Not applicable for dice game
            'api_raw': {},
            'simulated': True,
            'timestamp': 0.0
        }
        
        initial_multiplier = strategy._current_multiplier
        
        # Handle result
        strategy.on_bet_result(result)
        
        # Multiplier should increase after loss
        self.assertGreater(strategy._current_multiplier, initial_multiplier)
        self.assertEqual(strategy._loss_streak, 1)
        self.assertEqual(strategy._win_streak, 0)
    
    def test_strategy_generator_module_exists(self):
        """Test that strategy generator module exists and is importable"""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "rng_analysis"))
            from strategy_generator import StrategyGenerator
            
            # Check class exists
            self.assertTrue(callable(StrategyGenerator))
            
            # Check methods exist
            gen = StrategyGenerator()
            self.assertTrue(hasattr(gen, 'extract_insights'))
            self.assertTrue(hasattr(gen, 'export_to_json'))
            self.assertTrue(hasattr(gen, 'export_to_python_config'))
            
        except ImportError as e:
            self.skipTest(f"Strategy generator dependencies not installed: {e}")
    
    def test_load_strategy_from_config_function(self):
        """Test the helper function to load strategy from config"""
        from betbot_strategies.rng_analysis_strategy import load_strategy_from_config
        
        # Should be callable
        self.assertTrue(callable(load_strategy_from_config))
        
        # Test with non-existent file should raise
        with self.assertRaises(Exception):
            load_strategy_from_config('/tmp/nonexistent_config.json')


class TestStrategyGeneratorModule(unittest.TestCase):
    """Test strategy generator module (if dependencies available)"""
    
    def setUp(self):
        """Skip tests if dependencies not available"""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "rng_analysis"))
            import pandas as pd
            import numpy as np
        except ImportError as e:
            self.skipTest(f"RNG analysis dependencies not installed: {e}")
    
    def test_strategy_generator_instantiation(self):
        """Test StrategyGenerator can be instantiated"""
        from strategy_generator import StrategyGenerator
        
        gen = StrategyGenerator()
        self.assertIsNotNone(gen)
        self.assertIsInstance(gen.analysis_results, dict)
    
    def test_generate_strategy_recommendations(self):
        """Test generating strategy recommendations from mock data"""
        from strategy_generator import StrategyGenerator
        
        gen = StrategyGenerator()
        
        # Mock insights
        insights = {
            'metadata': {'total_bets_analyzed': 1000},
            'ml_summary': {'improvement_over_baseline': 2.5},
            'statistical_summary': {'is_uniform': True},
            'pattern_insights': {'overall_win_rate': 0.5},
            'risk_assessment': {'exploitability': 'none'}
        }
        
        # Generate recommendations
        recommendations = gen._generate_strategy_recommendations(insights)
        
        # Check structure
        self.assertIn('recommended_strategies', recommendations)
        self.assertIn('parameters', recommendations)
        
        # Should have at least one strategy
        strategies = recommendations['recommended_strategies']
        self.assertGreater(len(strategies), 0)
        
        # Each strategy should have required fields
        for strategy in strategies:
            self.assertIn('name', strategy)
            self.assertIn('base_strategy', strategy)
            self.assertIn('parameters', strategy)


if __name__ == '__main__':
    unittest.main()
