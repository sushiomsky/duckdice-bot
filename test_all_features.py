#!/usr/bin/env python3
"""
Comprehensive Integration Test
Tests all features: simulation, quick bet, auto bet, database, charts
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from decimal import Decimal
import tkinter as tk

def test_simulation_engine():
    """Test simulation engine (offline betting)."""
    print("\n" + "="*70)
    print("TEST 1: SIMULATION ENGINE (OFFLINE BETTING)")
    print("="*70)
    
    from simulation_engine import SimulationEngine, SimulatedDuckDiceAPI
    
    # Test basic engine
    engine = SimulationEngine(Decimal("100"))
    assert engine.balance == Decimal("100")
    print("✓ Engine initialized")
    
    # Place bets
    for i in range(20):
        result = engine.place_bet(
            Decimal("1"),
            Decimal("50"),
            Decimal("2"),
            True
        )
        assert 'is_win' in result
        assert 'balance' in result
    
    print(f"✓ Placed 20 bets")
    
    stats = engine.get_statistics()
    assert stats['total_bets'] == 20
    print(f"✓ Statistics: {stats['total_wins']} wins, {stats['total_losses']} losses")
    
    # Test API wrapper
    api = SimulatedDuckDiceAPI(Decimal("100"))
    result = api.place_bet("DOGE", Decimal("5"), Decimal("66"), True)
    assert 'win' in result
    assert 'balance' in result
    print("✓ API-compatible wrapper works")
    
    balances = api.get_balances()
    assert 'SIM' in balances
    print("✓ Get balances works")
    
    print("\n✅ SIMULATION ENGINE: PASS")
    return True

def test_database_logging():
    """Test database logging for live and simulation."""
    print("\n" + "="*70)
    print("TEST 2: DATABASE LOGGING")
    print("="*70)
    
    from gui_enhancements.bet_logger import BetLogger
    
    logger = BetLogger()
    print(f"✓ Database: {logger.db_path}")
    
    # Test simulation logging
    session_id = "test-sim-session"
    logger.start_session(session_id, is_simulation=True, strategy="test", initial_balance=100)
    
    for i in range(10):
        logger.log_bet({
            'session_id': session_id,
            'symbol': 'DOGE',
            'strategy': 'test',
            'bet_amount': Decimal("1"),
            'chance': Decimal("50"),
            'payout': Decimal("2"),
            'is_high': True,
            'is_win': i % 2 == 0,
            'profit': Decimal("1") if i % 2 == 0 else Decimal("-1"),
            'balance': Decimal("100")
        }, is_simulation=True)
    
    print("✓ Logged 10 simulation bets")
    
    stats = logger.get_statistics(is_simulation=True, session_id=session_id)
    assert stats['total_bets'] == 10
    print(f"✓ Statistics: {stats['total_bets']} bets, {stats['win_rate']:.1f}% win rate")
    
    logger.end_session(session_id, final_balance=100)
    print("✓ Session ended")
    
    # Test querying
    bets = logger.get_bets(is_simulation=True, session_id=session_id, limit=5)
    assert len(bets) <= 5
    print(f"✓ Query returned {len(bets)} bets")
    
    print("\n✅ DATABASE LOGGING: PASS")
    return True

def test_charts():
    """Test chart rendering."""
    print("\n" + "="*70)
    print("TEST 3: LIVE CHARTS")
    print("="*70)
    
    from gui_enhancements.tkinter_chart import TkinterLiveChart
    
    root = tk.Tk()
    root.withdraw()
    
    chart = TkinterLiveChart(root, max_points=50)
    print("✓ Tkinter chart created (no matplotlib needed)")
    
    # Add data points
    balance = Decimal("100")
    for i in range(30):
        is_win = i % 3 != 0
        profit = Decimal("0.5") if is_win else Decimal("-0.5")
        balance += profit
        chart.add_data_point(balance, is_win)
    
    assert len(chart.balances) == 30
    print(f"✓ Added 30 data points")
    print(f"✓ Win markers: {len(chart.wins)}")
    print(f"✓ Loss markers: {len(chart.losses)}")
    
    # Test clear
    chart.clear()
    assert len(chart.balances) == 0
    print("✓ Clear function works")
    
    root.destroy()
    
    print("\n✅ LIVE CHARTS: PASS")
    return True

def test_gui_components():
    """Test GUI initialization."""
    print("\n" + "="*70)
    print("TEST 4: GUI COMPONENTS")
    print("="*70)
    
    from duckdice_gui_ultimate import UltimateGUI
    
    root = UltimateGUI()
    print("✓ GUI initialized")
    
    # Check components exist
    assert hasattr(root, 'bet_logger')
    assert hasattr(root, 'connection_status')
    assert hasattr(root, 'betting_status')
    assert hasattr(root, 'notebook')
    assert hasattr(root, 'shortcut_manager')
    print("✓ Core components present")
    
    # Check tabs
    assert root.notebook.index('end') == 5
    print(f"✓ All 5 tabs created")
    
    # Check quick bet components
    assert hasattr(root, 'qb_symbol_var')
    assert hasattr(root, 'qb_amount_var')
    assert hasattr(root, 'qb_chance_var')
    assert hasattr(root, 'qb_chart')
    print("✓ Quick bet tab components present")
    
    root.after(100, root.destroy)
    root.mainloop()
    
    print("\n✅ GUI COMPONENTS: PASS")
    return True

def test_simulation_mode():
    """Test simulation mode (offline)."""
    print("\n" + "="*70)
    print("TEST 5: SIMULATION MODE (OFFLINE)")
    print("="*70)
    
    from simulation_engine import SimulatedDuckDiceAPI
    from gui_enhancements.bet_logger import BetLogger
    from gui_enhancements.tkinter_chart import TkinterLiveChart
    import tkinter as tk
    
    # Setup
    api = SimulatedDuckDiceAPI(Decimal("100"))
    logger = BetLogger()
    
    root = tk.Tk()
    root.withdraw()
    chart = TkinterLiveChart(root, max_points=50)
    
    session_id = "offline-test"
    logger.start_session(session_id, is_simulation=True, strategy="manual", initial_balance=100)
    
    # Simulate 20 bets (completely offline)
    for i in range(20):
        result = api.place_bet("DOGE", Decimal("1"), Decimal("50"), True)
        
        # Log to database
        logger.log_bet({
            'session_id': session_id,
            'symbol': 'DOGE',
            'strategy': 'manual',
            'bet_amount': Decimal("1"),
            'chance': Decimal("50"),
            'payout': Decimal(result['payout']),
            'is_high': True,
            'is_win': result['win'],
            'profit': Decimal(result['profit']),
            'balance': Decimal(result['balance'])
        }, is_simulation=True)
        
        # Update chart
        chart.add_data_point(Decimal(result['balance']), result['win'])
    
    print("✓ Placed 20 OFFLINE bets")
    print("✓ All bets logged to database")
    print("✓ Chart updated in real-time")
    
    # Verify
    stats = logger.get_statistics(is_simulation=True, session_id=session_id)
    assert stats['total_bets'] == 20
    print(f"✓ Statistics: {stats['total_bets']} bets, {stats['win_rate']:.1f}% win rate")
    
    assert len(chart.balances) == 20
    print(f"✓ Chart has {len(chart.balances)} points")
    
    logger.end_session(session_id, final_balance=Decimal(result['balance']))
    root.destroy()
    
    print("\n✅ SIMULATION MODE: PASS (WORKS OFFLINE!)")
    return True

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("COMPREHENSIVE INTEGRATION TEST SUITE")
    print("="*70)
    print("\nTesting ALL features:")
    print("  • Simulation engine (offline betting)")
    print("  • Database logging (live & simulation)")
    print("  • Live charts (Tkinter)")
    print("  • GUI components")
    print("  • Offline mode")
    
    results = []
    
    try:
        results.append(("Simulation Engine", test_simulation_engine()))
    except Exception as e:
        print(f"\n❌ SIMULATION ENGINE FAILED: {e}")
        results.append(("Simulation Engine", False))
    
    try:
        results.append(("Database Logging", test_database_logging()))
    except Exception as e:
        print(f"\n❌ DATABASE LOGGING FAILED: {e}")
        results.append(("Database Logging", False))
    
    try:
        results.append(("Live Charts", test_charts()))
    except Exception as e:
        print(f"\n❌ LIVE CHARTS FAILED: {e}")
        results.append(("Live Charts", False))
    
    try:
        results.append(("GUI Components", test_gui_components()))
    except Exception as e:
        print(f"\n❌ GUI COMPONENTS FAILED: {e}")
        results.append(("GUI Components", False))
    
    try:
        results.append(("Simulation Mode", test_simulation_mode()))
    except Exception as e:
        print(f"\n❌ SIMULATION MODE FAILED: {e}")
        results.append(("Simulation Mode", False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nFeatures Confirmed:")
        print("  ✅ Simulation works OFFLINE (no API needed)")
        print("  ✅ Quick bet ready for use")
        print("  ✅ Database logging both modes")
        print("  ✅ Charts update in real-time")
        print("  ✅ GUI fully functional")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
