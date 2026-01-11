"""
Unit tests for GUI state management.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import pytest
import threading
import time
from gui.state import AppState, BetRecord, app_state
from datetime import datetime


class TestAppState:
    """Test AppState dataclass"""
    
    def test_initial_state(self):
        """Test default state values"""
        state = AppState()
        assert state.running is False
        assert state.paused is False
        assert state.simulation_mode is True
        assert state.balance == 0.0
        assert state.total_bets == 0
        assert state.wins == 0
        assert state.losses == 0
        assert len(state.bet_history) == 0
    
    def test_update_method(self):
        """Test thread-safe update"""
        state = AppState()
        state.update(balance=1.0, total_bets=10, wins=6, losses=4)
        
        assert state.balance == 1.0
        assert state.total_bets == 10
        assert state.wins == 6
        assert state.losses == 4
    
    def test_get_method(self):
        """Test thread-safe get"""
        state = AppState()
        state.update(balance=1.5)
        
        value = state.get('balance')
        assert value == 1.5
        
        default_value = state.get('nonexistent', 'default')
        assert default_value == 'default'
    
    def test_thread_safety(self):
        """Test concurrent updates don't cause race conditions"""
        state = AppState()
        
        def increment_balance():
            for _ in range(100):
                current = state.get('balance', 0)
                state.update(balance=current + 0.01)
        
        threads = [threading.Thread(target=increment_balance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # With proper locking, final balance should be 10.0
        # (10 threads × 100 increments × 0.01)
        assert state.balance == pytest.approx(10.0, rel=0.01)


class TestBetRecord:
    """Test BetRecord dataclass"""
    
    def test_bet_record_creation(self):
        """Test creating a bet record"""
        now = datetime.now()
        bet = BetRecord(
            bet_number=1,
            timestamp=now,
            bet_amount=0.001,
            target_chance=49.5,
            roll=45.5,
            won=True,
            payout=0.002,
            profit=0.001,
            balance=1.001
        )
        
        assert bet.bet_number == 1
        assert bet.timestamp == now
        assert bet.bet_amount == 0.001
        assert bet.won is True
        assert bet.profit == 0.001
    
    def test_bet_record_loss(self):
        """Test bet record for a loss"""
        bet = BetRecord(
            bet_number=2,
            timestamp=datetime.now(),
            bet_amount=0.001,
            target_chance=49.5,
            roll=95.5,
            won=False,
            payout=0.0,
            profit=-0.001,
            balance=0.999
        )
        
        assert bet.won is False
        assert bet.profit == -0.001
        assert bet.payout == 0.0


class TestGlobalAppState:
    """Test global app_state singleton"""
    
    def test_singleton_instance(self):
        """Test that app_state is a singleton"""
        from gui.state import app_state as state1
        from gui.state import app_state as state2
        
        assert state1 is state2
    
    def test_state_persistence(self):
        """Test state persists across imports"""
        app_state.update(balance=5.0)
        
        from gui.state import app_state as reimported_state
        assert reimported_state.balance == 5.0
        
        # Clean up
        app_state.update(balance=0.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
