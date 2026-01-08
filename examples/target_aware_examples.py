#!/usr/bin/env python3
"""
Example: Using Target-Aware Strategy Programmatically

This example demonstrates how to use the target-aware strategy
directly from Python code without the interactive launcher.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_engine.engine import AutoBetEngine, EngineConfig


def example_basic_usage():
    """
    Basic example: Set up and run target-aware strategy.
    """
    # Replace with your API key
    API_KEY = os.environ.get('DUCKDICE_API_KEY', 'YOUR_API_KEY_HERE')
    
    if API_KEY == 'YOUR_API_KEY_HERE':
        print("Error: Set DUCKDICE_API_KEY environment variable")
        sys.exit(1)
    
    # Initialize API
    print("Initializing API...")
    config = DuckDiceConfig(api_key=API_KEY)
    api = DuckDiceAPI(config)
    
    # Configure the betting session
    symbol = "DOGE"  # Change to your currency
    
    # Create engine configuration
    engine_config = EngineConfig(
        symbol=symbol,
        delay_ms=750,       # 750ms between bets
        jitter_ms=500,      # Random jitter up to 500ms
        dry_run=False,      # Set True for testing
        faucet=False,       # Use main balance
        max_bets=100,       # Stop after 100 bets
        max_duration_sec=600,  # Stop after 10 minutes
    )
    
    # Strategy parameters
    strategy_params = {
        "target": "100",              # Target 100 DOGE
        "min_bet": "1",               # Minimum bet 1 DOGE
        # Using defaults for state configuration
    }
    
    # Create engine
    engine = AutoBetEngine(api, engine_config)
    
    # Run the strategy
    print(f"\nStarting target-aware strategy for {symbol}")
    print(f"Target: {strategy_params['target']}")
    print(f"Max bets: {engine_config.max_bets}")
    print("-" * 60)
    
    try:
        summary = engine.run(
            strategy_name="target-aware",
            params=strategy_params,
            printer=lambda msg: print(msg, flush=True),
        )
        
        # Display results
        print("\n" + "="*60)
        print("SESSION SUMMARY")
        print("="*60)
        print(f"Total Bets: {summary.get('total_bets', 0)}")
        print(f"Wins: {summary.get('wins', 0)}")
        print(f"Losses: {summary.get('losses', 0)}")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def example_custom_configuration():
    """
    Advanced example: Custom state configuration.
    """
    API_KEY = os.environ.get('DUCKDICE_API_KEY')
    if not API_KEY:
        print("Set DUCKDICE_API_KEY environment variable")
        return
    
    config = DuckDiceConfig(api_key=API_KEY)
    api = DuckDiceAPI(config)
    
    # More aggressive configuration
    engine_config = EngineConfig(
        symbol="BTC",
        delay_ms=500,
        dry_run=False,
        max_bets=1000,
    )
    
    # Custom parameters for aggressive play
    strategy_params = {
        "target": "0.001",
        "min_bet": "0.00000001",
        # More aggressive SAFE state
        "safe_chance_min": "90",
        "safe_chance_max": "95",
        "safe_bet_pct_min": 0.002,    # 0.2%
        "safe_bet_pct_max": 0.005,    # 0.5%
        # More aggressive BUILD state
        "build_chance_min": "60",
        "build_chance_max": "80",
        "build_bet_pct_min": 0.005,   # 0.5%
        "build_bet_pct_max": 0.01,    # 1%
        # More aggressive STRIKE state
        "strike_chance_min": "10",
        "strike_chance_max": "30",
        "strike_bet_pct_min": 0.015,  # 1.5%
        "strike_bet_pct_max": 0.03,   # 3%
        # Tighter drawdown protection
        "drawdown_downgrade": 0.02,   # 2%
        "drawdown_force_safe": 0.04,  # 4%
        "drawdown_stop": 0.08,        # 8%
    }
    
    engine = AutoBetEngine(api, engine_config)
    
    print("Running with aggressive custom configuration...")
    summary = engine.run(
        strategy_name="target-aware",
        params=strategy_params,
    )
    
    print(f"Results: {summary.get('total_bets')} bets placed")


def example_fetch_and_select():
    """
    Example: Fetch balances and programmatically select currency.
    """
    API_KEY = os.environ.get('DUCKDICE_API_KEY')
    if not API_KEY:
        print("Set DUCKDICE_API_KEY environment variable")
        return
    
    config = DuckDiceConfig(api_key=API_KEY)
    api = DuckDiceAPI(config)
    
    # Fetch user info
    print("Fetching balances...")
    user_info = api.get_user_info()
    balances = user_info.get('balances', [])
    
    # Find currencies with balance > 0
    available = []
    for balance_entry in balances:
        currency = balance_entry.get('currency')
        main = Decimal(str(balance_entry.get('main', '0')))
        if main > 0:
            available.append((currency, main))
            print(f"  {currency}: {main}")
    
    if not available:
        print("No balances available")
        return
    
    # Select first available (or implement your logic)
    symbol, balance = available[0]
    print(f"\nSelected: {symbol} with balance {balance}")
    
    # Get min bet
    stats = api.get_currency_stats(symbol)
    min_bet = Decimal(str(stats.get('minBet', '0.00000001')))
    print(f"Min bet: {min_bet}")
    
    # Set target (e.g., 10% gain)
    target = balance * Decimal('1.1')
    print(f"Target: {target} (+10%)")
    
    # Run strategy
    engine_config = EngineConfig(symbol=symbol, max_bets=500)
    strategy_params = {
        "target": str(target),
        "min_bet": str(min_bet),
    }
    
    engine = AutoBetEngine(api, engine_config)
    summary = engine.run("target-aware", strategy_params)
    
    print(f"\nCompleted: {summary.get('total_bets')} bets")


if __name__ == "__main__":
    print("Target-Aware Strategy Examples")
    print("="*60)
    print("\nRunning basic example...")
    print("(Press Ctrl+C to stop)")
    print("")
    
    # Run the basic example
    # Uncomment others to try different configurations
    example_basic_usage()
    
    # example_custom_configuration()
    # example_fetch_and_select()
