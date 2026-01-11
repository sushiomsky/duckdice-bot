# -*- coding: utf-8 -*-
"""
Simple tests for GUI components - runs without pytest
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import threading
from datetime import datetime
from gui.state import AppState, BetRecord, app_state


def test_state_initialization():
    """Test AppState initializes correctly"""
    state = AppState()
    assert state.running == False
    assert state.simulation_mode == True
    assert state.balance == 0.0
    print("[PASS] State initialization test passed")


def test_state_update():
    """Test state update method"""
    state = AppState()
    state.update(balance=1.5, total_bets=10)
    assert state.balance == 1.5
    assert state.total_bets == 10
    print("[PASS] State update test passed")


def test_bet_record():
    """Test BetRecord creation"""
    bet = BetRecord(
        timestamp=datetime.now(),
        amount=0.001,
        target=49.5,
        roll=45.0,
        won=True,
        profit=0.001,
        balance=1.001,
        strategy="Martingale"
    )
    assert bet.won == True
    assert bet.profit == 0.001
    assert bet.amount == 0.001
    print("[PASS] BetRecord test passed")


def test_thread_safety():
    """Test concurrent state updates"""
    state = AppState()
    state.update(balance=0.0)
    
    def increment():
        for _ in range(100):
            current = state.get('balance', 0)
            state.update(balance=current + 0.01)
    
    threads = [threading.Thread(target=increment) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should be 5.0 with proper locking
    assert abs(state.balance - 5.0) < 0.1
    print(f"[PASS] Thread safety test passed (balance={state.balance:.2f})")


def test_bot_controller_import():
    """Test bot_controller imports without errors"""
    from gui.bot_controller import bot_controller
    assert bot_controller is not None
    assert not bot_controller.is_running()
    print("[PASS] BotController import test passed")


def test_utils_validation():
    """Test validation functions"""
    from gui.utils import validate_bet_amount, validate_target_chance
    
    is_valid, msg = validate_bet_amount("0.001")
    assert is_valid == True
    
    is_valid, msg = validate_bet_amount("invalid")
    assert is_valid == False
    
    is_valid, msg = validate_target_chance("49.5")
    assert is_valid == True
    
    is_valid, msg = validate_target_chance("150.0")
    assert is_valid == False
    
    print("[PASS] Validation tests passed")


def test_utils_formatting():
    """Test formatting functions"""
    from gui.utils import format_balance, format_profit, format_number
    
    formatted = format_balance(0.12345678)
    assert "0.12345678" in formatted
    
    formatted = format_profit(0.5)
    assert "+0.5" in formatted or "0.5" in formatted
    
    formatted = format_number(1234.56)
    assert "1234" in formatted
    
    print("[PASS] Formatting tests passed")


def run_all_tests():
    """Run all tests"""
    print("\n[TEST] Running GUI Component Tests...\n")
    
    tests = [
        test_state_initialization,
        test_state_update,
        test_bet_record,
        test_thread_safety,
        test_bot_controller_import,
        test_utils_validation,
        test_utils_formatting,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__} error: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}\n")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
