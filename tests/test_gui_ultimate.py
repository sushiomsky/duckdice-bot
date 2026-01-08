#!/usr/bin/env python3
"""Quick test of the Ultimate GUI"""
import sys
print("Testing Ultimate GUI launch...")
try:
    import tkinter as tk
    print("✅ tkinter imported")
    
    sys.path.insert(0, 'src')
    from gui_enhancements import BetLogger, EnhancedBetHistoryViewer, StatisticsDashboard
    print("✅ GUI enhancements imported")
    
    # Test BetLogger
    logger = BetLogger()
    print("✅ BetLogger initialized")
    
    # Test GUI components
    root = tk.Tk()
    root.withdraw()
    
    stats = StatisticsDashboard(root, bet_logger=logger)
    print("✅ StatisticsDashboard initialized")
    
    print("\n🎉 All components working! GUI should launch successfully.")
    print("\nTo run the full GUI:")
    print("  python3 duckdice_gui_ultimate.py")
    
    root.destroy()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
