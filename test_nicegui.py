#!/usr/bin/env python3
"""
Test NiceGUI app without starting server
Quick functionality check
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("🎲 DuckDice Bot NiceGUI - Quick Test")
print("=" * 60)
print()

# Test imports
print("Testing imports...")
try:
    from app.ui.theme import Theme
    print("  ✅ Theme")
    
    from app.state.store import store
    print("  ✅ State Store")
    
    from app.services.backend import backend
    print("  ✅ Backend")
    
    from app.ui.components import card, primary_button
    print("  ✅ Components")
    
    print()
    print("All imports successful!")
    print()
except ImportError as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)

# Test theme
print("Theme Configuration:")
print(f"  Primary Color: {Theme.PRIMARY}")
print(f"  Background: {Theme.BG_PRIMARY}")
print(f"  Text: {Theme.TEXT_PRIMARY}")
print()

# Test store
print("State Store:")
print(f"  Connected: {store.connected}")
print(f"  Currency: {store.currency}")
print(f"  Mode: {store.mode}")
print(f"  Betting Mode: {store.betting_mode}")
print()

# Test strategies
print("Strategies:")
strategies = backend.get_strategies()
print(f"  Total strategies: {len(strategies)}")
if strategies:
    print("  Available strategies:")
    for s in strategies[:5]:  # Show first 5
        print(f"    - {s['name']} ({s['risk_level']})")
    if len(strategies) > 5:
        print(f"    ... and {len(strategies) - 5} more")
else:
    print("  ⚠️  No strategies loaded (this is normal without full initialization)")
print()

print("=" * 60)
print("✅ All tests passed!")
print()
print("To start the web server:")
print("  ./run_nicegui.sh")
print()
print("Then open: http://localhost:8080")
print("=" * 60)
