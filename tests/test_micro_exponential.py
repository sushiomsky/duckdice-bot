#!/usr/bin/env python3
"""
Test the Micro Exponential Growth strategy in simulation mode.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from betbot_engine.engine import AutoBetEngine, EngineConfig
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig


def test_micro_exponential():
    """Test the micro exponential strategy"""
    
    print("=" * 70)
    print("Testing Micro Exponential Growth Engine")
    print("=" * 70)
    print()
    
    # Create API (won't be used in dry_run mode)
    api_config = DuckDiceConfig(api_key="test_key")
    api = DuckDiceAPI(api_config)
    
    # Create engine configuration (simulation mode)
    config = EngineConfig(
        symbol="TRX",
        dry_run=True,  # Simulation mode
        faucet=False,
        log_dir="bet_history",
        max_bets=50,  # Test with 50 bets
        stop_loss=None,  # Strategy manages its own risk
        take_profit=None,  # Strategy has internal target
        max_losses=None,
        max_duration_sec=None,
        delay_ms=50,  # Fast for testing
        jitter_ms=25,
        seed=12345  # Fixed seed for reproducibility
    )
    
    # Create engine
    engine = AutoBetEngine(api, config)
    
    # Strategy parameters
    strategy_params = {
        'base_bet_percent': '0.002',     # 0.2% of balance
        'min_bet': '0.00000001',
        'profit_target_x': '300',        # Stop at 300x
        'max_drawdown_percent': '45',    # Accept 45% drawdown
        'kill_chance_min': '0.08',       # 0.08% min for kill mode
        'kill_chance_max': '0.25',       # 0.25% max for kill mode
        'kill_bet_percent': '0.65',      # 65% of balance in kill mode
        'kill_cooldown': '20',           # Reduced for testing
        'vol_window': '20'               # Reduced window for testing
    }
    
    # Printer callback
    def printer(msg: str):
        print(msg)
    
    print("Strategy: Micro Exponential Growth Engine")
    print("Mode: SIMULATION (dry_run=True)")
    print("Bets: 50 test bets")
    print()
    
    try:
        summary = engine.run(
            strategy_name="micro-exponential",
            params=strategy_params,
            printer=printer
        )
        
        print()
        print("=" * 70)
        print("Test Results")
        print("=" * 70)
        print(f"Total Bets:        {summary.get('bets', 0)}")
        print(f"Duration:          {summary.get('duration_sec', 0):.2f}s")
        print(f"Starting Balance:  {summary.get('starting_balance', '0')}")
        print(f"Ending Balance:    {summary.get('ending_balance', '0')}")
        print(f"Profit/Loss:       {summary.get('profit', '0')}")
        print(f"Stop Reason:       {summary.get('stop_reason', 'unknown')}")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Micro Exponential Growth Engine Test")
    print()
    
    success = test_micro_exponential()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("\nNOTE: This strategy is designed for micro balances and high risk tolerance.")
        print("      Use with caution and only with funds you can afford to lose.")
        sys.exit(0)
    else:
        print("\n❌ Test failed. Please review the output above.")
        sys.exit(1)
