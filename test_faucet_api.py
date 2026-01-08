#!/usr/bin/env python3
"""
Test script for faucet mode and API integration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from duckdice_api import DuckDiceAPI, DuckDiceConfig
from faucet_manager import FaucetManager, FaucetConfig

# API key
API_KEY = "8f9a51ce-af2d-11f0-a08a-524acb1a7d8c"

def test_api_connection():
    """Test basic API connection."""
    print("=" * 50)
    print("Testing API Connection...")
    print("=" * 50)
    
    try:
        config = DuckDiceConfig(api_key=API_KEY)
        api = DuckDiceAPI(config)
        
        # Get user info
        user_info = api.get_user_info()
        print(f"✅ Connected! User: {user_info.get('username', 'Unknown')}")
        
        return api
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def test_balances(api):
    """Test balance retrieval."""
    print("\n" + "=" * 50)
    print("Testing Balance Retrieval...")
    print("=" * 50)
    
    try:
        # Get balances
        balances = api.get_balances()
        print(f"\n💰 Total currencies: {len(balances)}")
        
        # Test DOGE balances specifically
        print("\n📊 DOGE Balances:")
        main_doge = api.get_main_balance("DOGE")
        faucet_doge = api.get_faucet_balance("DOGE")
        print(f"  Main:   {main_doge:.8f} DOGE")
        print(f"  Faucet: {faucet_doge:.8f} DOGE")
        
        # Show all available currencies
        print("\n🪙 Available Currencies:")
        currencies = api.get_available_currencies()
        print(f"  {', '.join(currencies[:10])}")
        if len(currencies) > 10:
            print(f"  ...and {len(currencies) - 10} more")
        
        return True
    except Exception as e:
        print(f"❌ Balance check failed: {e}")
        return False

def test_faucet_manager(api):
    """Test faucet manager."""
    print("\n" + "=" * 50)
    print("Testing Faucet Manager...")
    print("=" * 50)
    
    try:
        config = FaucetConfig(
            enabled=False,  # Don't auto-claim during test
            interval=60,
            currency="DOGE"
        )
        faucet_mgr = FaucetManager(api, config)
        
        print("✅ Faucet Manager initialized")
        
        # Check if can claim
        can_claim = faucet_mgr.can_claim()
        print(f"📌 Can claim now: {can_claim}")
        
        if not can_claim:
            next_claim = faucet_mgr.get_next_claim_time()
            print(f"⏱️  Next claim in: {int(next_claim)}s")
        
        # Note: Not actually claiming without cookie
        print("\nℹ️  Note: Actual claiming requires browser cookie")
        print("   Configure cookie in GUI Settings → Faucet tab")
        
        return True
    except Exception as e:
        print(f"❌ Faucet manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n🚀 DuckDice Bot - API & Faucet Tests\n")
    
    # Test 1: API Connection
    api = test_api_connection()
    if not api:
        print("\n❌ Cannot proceed without API connection")
        return
    
    # Test 2: Balances
    if not test_balances(api):
        print("\n⚠️  Balance check failed, but continuing...")
    
    # Test 3: Faucet Manager
    test_faucet_manager(api)
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS COMPLETE!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Launch GUI: python3 duckdice_gui_ultimate.py")
    print("2. Go to Settings → Faucet tab")
    print("3. Paste your browser cookie")
    print("4. Enable auto-claim")
    print("5. Test faucet claiming!")

if __name__ == "__main__":
    main()
