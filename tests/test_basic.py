#!/usr/bin/env python3
"""
Basic tests for DuckDice CLI tool
Tests argument parsing and API client functionality
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add parent directory to path to import duckdice module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import duckdice


class TestDuckDiceConfig(unittest.TestCase):
    """Test DuckDiceConfig dataclass"""
    
    def test_config_creation(self):
        """Test creating a config with required parameters"""
        config = duckdice.DuckDiceConfig(api_key="test-key")
        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.base_url, "https://duckdice.io/api")
        self.assertEqual(config.timeout, 30)
    
    def test_config_custom_values(self):
        """Test creating a config with custom values"""
        config = duckdice.DuckDiceConfig(
            api_key="test-key",
            base_url="https://custom.api",
            timeout=60
        )
        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.base_url, "https://custom.api")
        self.assertEqual(config.timeout, 60)


class TestDuckDiceAPI(unittest.TestCase):
    """Test DuckDiceAPI class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = duckdice.DuckDiceConfig(api_key="test-api-key")
        self.api = duckdice.DuckDiceAPI(self.config)
    
    def test_api_initialization(self):
        """Test API client initialization"""
        self.assertEqual(self.api.config.api_key, "test-api-key")
        self.assertIsNotNone(self.api.session)
        self.assertEqual(
            self.api.session.headers['Content-Type'],
            'application/json'
        )
        self.assertEqual(
            self.api.session.headers['User-Agent'],
            'DuckDiceCLI/1.0.0'
        )
    
    @patch('requests.Session.post')
    def test_play_dice_success(self, mock_post):
        """Test successful dice play"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'bet': {'hash': 'test123', 'result': True},
            'user': {'username': 'testuser'}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Call method
        result = self.api.play_dice(
            symbol="BTC",
            amount="0.1",
            chance="50",
            is_high=True
        )
        
        # Assertions
        self.assertIn('bet', result)
        self.assertIn('user', result)
        self.assertEqual(result['bet']['hash'], 'test123')
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn('api_key', call_args[1]['params'])
        self.assertEqual(
            call_args[1]['json']['symbol'],
            'BTC'
        )
    
    @patch('requests.Session.post')
    def test_play_range_dice_success(self, mock_post):
        """Test successful range dice play"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'bet': {'hash': 'range123', 'result': False},
            'user': {'username': 'testuser'}
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Call method
        result = self.api.play_range_dice(
            symbol="XLM",
            amount="0.5",
            range_values=[1000, 5000],
            is_in=True
        )
        
        # Assertions
        self.assertIn('bet', result)
        self.assertEqual(result['bet']['hash'], 'range123')
        
        # Verify range was passed correctly
        call_args = mock_post.call_args
        self.assertEqual(
            call_args[1]['json']['range'],
            [1000, 5000]
        )
    
    @patch('requests.Session.get')
    def test_get_currency_stats_success(self, mock_get):
        """Test successful currency stats retrieval"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'bets': 100,
            'wins': 50,
            'profit': '10.5',
            'volume': '100.0',
            'balances': {'main': '50.0', 'faucet': '0.5'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Call method
        result = self.api.get_currency_stats("BTC")
        
        # Assertions
        self.assertEqual(result['bets'], 100)
        self.assertEqual(result['wins'], 50)
        self.assertIn('balances', result)
        
        # Verify correct endpoint was called
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn('bot/stats/BTC', call_args[0][0])
    
    @patch('requests.Session.get')
    def test_get_user_info_success(self, mock_get):
        """Test successful user info retrieval"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'hash': 'user123',
            'username': 'testuser',
            'level': 5,
            'balances': [],
            'wageringBonuses': [],
            'tle': []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Call method
        result = self.api.get_user_info()
        
        # Assertions
        self.assertEqual(result['username'], 'testuser')
        self.assertEqual(result['level'], 5)
        self.assertIn('balances', result)


class TestFormatters(unittest.TestCase):
    """Test output formatter functions"""
    
    def test_format_bet_result(self):
        """Test bet result formatting"""
        response = {
            'bet': {
                'hash': 'test123',
                'result': True,
                'number': 6559,
                'choice': '>2222',
                'choiceOption': '0.2222',
                'symbol': 'XLM',
                'betAmount': '0.1',
                'chance': 77.77,
                'payout': 1.273,
                'winAmount': '0.127',
                'profit': '0.027',
                'mined': '0.001',
                'gameMode': 'main',
                'nonce': 100,
                'game': {'name': 'Original Dice'}
            },
            'isJackpot': False,
            'user': {
                'username': 'testuser',
                'level': 5,
                'balance': '10.0',
                'bets': 100,
                'wins': 50,
                'luck': 99.5,
                'profit': '5.0',
                'volume': '100.0',
                'absoluteLevel': {
                    'level': 10,
                    'xp': 5000,
                    'xpNext': 6000
                }
            }
        }
        
        result = duckdice.format_bet_result(response)
        
        # Check that important information is in output
        self.assertIn('WIN', result)
        self.assertIn('test123', result)
        self.assertIn('6559', result)
        self.assertIn('testuser', result)
        self.assertIn('XLM', result)
    
    def test_format_currency_stats(self):
        """Test currency stats formatting"""
        response = {
            'bets': 100,
            'wins': 50,
            'profit': '10.5',
            'volume': '100.0',
            'balances': {
                'main': '50.0',
                'faucet': '0.5'
            }
        }
        
        result = duckdice.format_currency_stats(response, 'BTC')
        
        # Check that important information is in output
        self.assertIn('BTC', result)
        self.assertIn('100', result)  # bets
        self.assertIn('50', result)   # wins
        self.assertIn('10.5', result) # profit
    
    def test_format_user_info(self):
        """Test user info formatting"""
        response = {
            'hash': 'user123',
            'username': 'testuser',
            'level': 5,
            'createdAt': 1234567890,
            'balances': [
                {
                    'currency': 'BTC',
                    'main': '1.0',
                    'faucet': '0.1'
                }
            ],
            'wagered': [
                {
                    'currency': 'BTC',
                    'amount': '10.0'
                }
            ],
            'wageringBonuses': [],
            'tle': []
        }
        
        result = duckdice.format_user_info(response)
        
        # Check that important information is in output
        self.assertIn('testuser', result)
        self.assertIn('user123', result)
        self.assertIn('BTC', result)


class TestArgumentParser(unittest.TestCase):
    """Test command line argument parser"""
    
    def test_parser_dice_command(self):
        """Test parsing dice command"""
        parser = duckdice.create_parser()
        args = parser.parse_args([
            '--api-key', 'test-key',
            'dice',
            '--symbol', 'BTC',
            '--amount', '0.1',
            '--chance', '50',
            '--high'
        ])
        
        self.assertEqual(args.command, 'dice')
        self.assertEqual(args.api_key, 'test-key')
        self.assertEqual(args.symbol, 'BTC')
        self.assertEqual(args.amount, '0.1')
        self.assertEqual(args.chance, '50')
        self.assertTrue(args.high)
        self.assertFalse(args.faucet)
    
    def test_parser_range_dice_command(self):
        """Test parsing range-dice command"""
        parser = duckdice.create_parser()
        args = parser.parse_args([
            '--api-key', 'test-key',
            'range-dice',
            '--symbol', 'XLM',
            '--amount', '0.5',
            '--range', '1000', '5000',
            '--in'
        ])
        
        self.assertEqual(args.command, 'range-dice')
        self.assertEqual(args.symbol, 'XLM')
        self.assertEqual(args.range, [1000, 5000])
        self.assertTrue(args.in_range)
    
    def test_parser_stats_command(self):
        """Test parsing stats command"""
        parser = duckdice.create_parser()
        args = parser.parse_args([
            '--api-key', 'test-key',
            'stats',
            '--symbol', 'BTC'
        ])
        
        self.assertEqual(args.command, 'stats')
        self.assertEqual(args.symbol, 'BTC')
    
    def test_parser_user_info_command(self):
        """Test parsing user-info command"""
        parser = duckdice.create_parser()
        args = parser.parse_args([
            '--api-key', 'test-key',
            'user-info'
        ])
        
        self.assertEqual(args.command, 'user-info')
    
    def test_parser_json_flag(self):
        """Test JSON output flag"""
        parser = duckdice.create_parser()
        args = parser.parse_args([
            '--api-key', 'test-key',
            '--json',
            'user-info'
        ])
        
        self.assertTrue(args.json)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
