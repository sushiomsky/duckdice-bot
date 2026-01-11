#!/usr/bin/env python3
"""
Test script to verify strategy configuration panel integration
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from betbot_strategies import list_strategies, get_strategy

def test_strategy_integration():
    """Test that all strategies can be loaded and have schemas."""
    strategies = list_strategies()
    print(f"Found {len(strategies)} strategies:\n")
    
    for strategy_name in strategies:
        print(f"Testing: {strategy_name}")
        try:
            strategy_class = get_strategy(strategy_name)
            
            # Check if schema exists
            if not hasattr(strategy_class, 'schema'):
                print(f"  ❌ No schema() method")
                continue
            
            # Get schema
            schema = strategy_class.schema()
            
            if not schema:
                print(f"  ⚠️  Empty schema")
                continue
            
            print(f"  ✓ Schema found with {len(schema)} parameters:")
            for param_name, param_info in schema.items():
                param_type = param_info.get('type', 'unknown')
                param_default = param_info.get('default', 'N/A')
                param_desc = param_info.get('desc', 'No description')
                print(f"    • {param_name}: {param_type} = {param_default}")
                print(f"      {param_desc}")
            print()
            
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
    
    print(f"\nSummary: Successfully tested {len(strategies)} strategies")

if __name__ == "__main__":
    test_strategy_integration()
