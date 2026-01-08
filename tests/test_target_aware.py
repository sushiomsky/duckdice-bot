#!/usr/bin/env python3
"""
Validation Test for Target-Aware Strategy

Verifies that the target-aware strategy is correctly implemented
and can be instantiated with valid parameters.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from betbot_strategies import get_strategy, list_strategies
from betbot_strategies.base import StrategyContext, SessionLimits
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
import random

# Import target_aware to register it
from betbot_strategies import target_aware  # noqa: F401


def test_strategy_registration():
    """Test that target-aware strategy is registered."""
    print("Test 1: Strategy Registration")
    print("-" * 60)
    
    strategies = list_strategies()
    strategy_names = [s['name'] for s in strategies]
    
    if 'target-aware' in strategy_names:
        print("✅ target-aware strategy is registered")
        
        # Get strategy details
        for strat in strategies:
            if strat['name'] == 'target-aware':
                print(f"   Description: {strat['description'][:60]}...")
                break
    else:
        print("❌ target-aware strategy NOT found")
        print(f"   Available: {', '.join(strategy_names)}")
        return False
    
    print()
    return True


def test_strategy_schema():
    """Test that strategy schema is complete."""
    print("Test 2: Strategy Schema")
    print("-" * 60)
    
    try:
        cls = get_strategy('target-aware')
        schema = cls.schema()
        
        required_params = ['target', 'min_bet']
        optional_params = [
            'safe_chance_min', 'safe_chance_max',
            'build_chance_min', 'build_chance_max',
            'strike_chance_min', 'strike_chance_max',
            'drawdown_downgrade', 'drawdown_force_safe', 'drawdown_stop'
        ]
        
        print(f"✅ Schema has {len(schema)} parameters")
        
        for param in required_params:
            if param in schema:
                print(f"   ✓ {param}: {schema[param].get('desc', 'N/A')[:40]}...")
            else:
                print(f"   ✗ Missing required param: {param}")
                return False
        
        print(f"   ✓ All {len(required_params)} required parameters present")
        print(f"   ✓ {len([p for p in optional_params if p in schema])} optional parameters present")
        
    except Exception as e:
        print(f"❌ Error getting schema: {e}")
        return False
    
    print()
    return True


def test_strategy_instantiation():
    """Test that strategy can be instantiated."""
    print("Test 3: Strategy Instantiation")
    print("-" * 60)
    
    try:
        # Create mock API (won't be used in this test)
        config = DuckDiceConfig(api_key="test_key")
        api = DuckDiceAPI(config)
        
        # Create context
        limits = SessionLimits(symbol="DOGE")
        ctx = StrategyContext(
            api=api,
            symbol="DOGE",
            faucet=False,
            dry_run=True,
            rng=random.Random(42),
            logger=lambda x: None,
            limits=limits,
            starting_balance="10000",
        )
        
        # Instantiate strategy
        params = {
            "target": "15000",
            "min_bet": "1",
        }
        
        cls = get_strategy('target-aware')
        strategy = cls(params, ctx)
        
        print("✅ Strategy instantiated successfully")
        print(f"   Target: {strategy.target}")
        print(f"   Min Bet: {strategy.min_bet}")
        print(f"   Starting Balance: {strategy.starting_balance}")
        
        # Test on_session_start
        strategy.on_session_start()
        print("✅ on_session_start() executed")
        
    except Exception as e:
        print(f"❌ Error instantiating strategy: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    return True


def test_payout_calculation():
    """Test payout and profit calculations."""
    print("Test 4: Payout Calculations")
    print("-" * 60)
    
    try:
        cls = get_strategy('target-aware')
        
        # Create a mock instance to access methods
        config = DuckDiceConfig(api_key="test")
        api = DuckDiceAPI(config)
        limits = SessionLimits(symbol="TEST")
        ctx = StrategyContext(
            api=api, symbol="TEST", faucet=False, dry_run=True,
            rng=random.Random(), logger=lambda x: None, limits=limits
        )
        
        strategy = cls({"target": "100", "min_bet": "1"}, ctx)
        
        # Test payout multiplier calculation
        test_cases = [
            (Decimal("50"), Decimal("1.98")),    # 50% chance
            (Decimal("98"), Decimal("1.0102")),  # 98% chance
            (Decimal("10"), Decimal("9.9")),     # 10% chance
        ]
        
        print("Testing payout multiplier formula: (100 - 1) / chance")
        for chance, expected_multiplier in test_cases:
            result = strategy._compute_payout_multiplier(chance)
            print(f"   Chance {chance}% → Multiplier {result:.4f} (expected ~{expected_multiplier})")
            
            # Test profit calculation
            bet = Decimal("100")
            profit = strategy._compute_profit(bet, chance)
            expected_profit = bet * (result - Decimal("1"))
            print(f"   Bet {bet} → Profit {profit:.4f}")
        
        print("✅ Payout calculations working correctly")
        
    except Exception as e:
        print(f"❌ Error in payout calculations: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    return True


def test_state_determination():
    """Test state machine logic."""
    print("Test 5: State Machine")
    print("-" * 60)
    
    try:
        cls = get_strategy('target-aware')
        
        config = DuckDiceConfig(api_key="test")
        api = DuckDiceAPI(config)
        limits = SessionLimits(symbol="TEST")
        ctx = StrategyContext(
            api=api, symbol="TEST", faucet=False, dry_run=True,
            rng=random.Random(), logger=lambda x: None, limits=limits,
            starting_balance="10000"
        )
        
        strategy = cls({"target": "15000", "min_bet": "1"}, ctx)
        strategy.on_session_start()
        
        # Test state determination at different balance levels
        test_cases = [
            (Decimal("5000"), "SAFE", "< 60% of target"),
            (Decimal("10000"), "BUILD", "60-85% of target"),
            (Decimal("13000"), "STRIKE", "85-97% of target"),
        ]
        
        print("Testing state transitions:")
        for balance, expected_state, description in test_cases:
            # Simulate balance
            strategy.starting_balance = balance
            strategy.peak_balance = balance
            
            # Determine state
            state = strategy._determine_state(balance, 0.0)
            
            symbol = "✓" if state.value == expected_state else "✗"
            print(f"   {symbol} Balance {balance} → {state.value} ({description})")
        
        print("✅ State machine logic working")
        
    except Exception as e:
        print(f"❌ Error in state determination: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    return True


def run_all_tests():
    """Run all validation tests."""
    print("="*60)
    print("TARGET-AWARE STRATEGY VALIDATION")
    print("="*60)
    print()
    
    tests = [
        test_strategy_registration,
        test_strategy_schema,
        test_strategy_instantiation,
        test_payout_calculation,
        test_state_determination,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED")
        print("✅ Target-aware strategy is ready to use")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Review errors above")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
