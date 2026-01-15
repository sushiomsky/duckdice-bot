#!/usr/bin/env python3
"""
Test script for the new event-driven architecture.

This script demonstrates how to use the engine with the new RichInterface.
"""

import os
import sys
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from betbot_engine.engine import AutoBetEngine, EngineConfig
from betbot_engine.observers import EventEmitter
from interfaces.cli.rich_interface import RichInterface
from duckdice_api.api import DuckDiceAPI


def test_event_system_with_simulation():
    """Test the event system using simulation mode"""
    
    # Create interface
    interface = RichInterface()
    
    # Create event emitter and attach interface as observer
    emitter = EventEmitter()
    emitter.add_observer(interface)
    
    # Create engine configuration (simulation mode)
    config = EngineConfig(
        symbol="TRX",
        dry_run=True,  # Simulation mode
        faucet=False,
        log_dir="bet_history",
        max_bets=10,  # Just 10 bets for testing
        stop_loss=-0.5,
        take_profit=None,
        max_losses=None,
        max_duration_sec=None,
        delay_ms=100,  # Fast for testing
        jitter_ms=50,
        seed=42
    )
    
    # Create API (won't be used in dry_run mode, but required)
    from duckdice_api.api import DuckDiceConfig
    api_config = DuckDiceConfig(api_key="test_key")
    api = DuckDiceAPI(api_config)
    
    # Create engine
    engine = AutoBetEngine(api, config)
    
    # Strategy parameters
    strategy_params = {
        "base_bet": "0.00000100",
        "target_value": "50.00",
        "use_faucet": False
    }
    
    print("\n" + "="*70)
    print("Testing Event-Driven Architecture with RichInterface")
    print("="*70 + "\n")
    
    # Run session with event emitter
    try:
        summary = engine.run(
            strategy_name="classic-martingale",  # Use correct strategy name
            params=strategy_params,
            emitter=emitter
        )
        
        print("\n" + "="*70)
        print("Test completed successfully!")
        print("="*70)
        print(f"\nSession summary: {summary}")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_backward_compatibility():
    """Test that the old callback system still works"""
    
    print("\n" + "="*70)
    print("Testing Backward Compatibility (Legacy Callbacks)")
    print("="*70 + "\n")
    
    # Create engine configuration (simulation mode)
    config = EngineConfig(
        symbol="TRX",
        dry_run=True,
        faucet=False,
        log_dir="bet_history",
        max_bets=5,
        stop_loss=-0.5,
        take_profit=None,
        max_losses=None,
        max_duration_sec=None,
        delay_ms=100,
        jitter_ms=50,
        seed=42
    )
    
    # Create API
    from duckdice_api.api import DuckDiceConfig
    api_config = DuckDiceConfig(api_key="test_key")
    api = DuckDiceAPI(api_config)
    
    # Create engine
    engine = AutoBetEngine(api, config)
    
    # Legacy callback
    def printer(msg: str):
        print(f"[LEGACY] {msg}")
    
    # Strategy parameters
    strategy_params = {
        "base_bet": "0.00000100",
        "target_value": "50.00",
        "use_faucet": False
    }
    
    try:
        summary = engine.run(
            strategy_name="classic-martingale",  # Use correct strategy name
            params=strategy_params,
            printer=printer
        )
        
        print("\n✅ Legacy callback system still works!")
        return True
        
    except Exception as e:
        print(f"\n❌ Legacy callback test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Testing Event-Driven Engine Refactoring")
    print("=" * 70)
    
    # Test 1: New event system
    test1_passed = test_event_system_with_simulation()
    
    # Test 2: Backward compatibility
    test2_passed = test_backward_compatibility()
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"Event System Test:         {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Backward Compatibility:    {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("="*70)
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Event system is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        sys.exit(1)
