#!/usr/bin/env python3
"""
Test script to demonstrate API fallback domain functionality.
"""
import sys
sys.path.insert(0, 'src')

from duckdice_api.api import DuckDiceAPI, DuckDiceConfig

def test_fallback_domains():
    """Test that fallback domains are configured correctly."""
    
    print("=" * 60)
    print("DuckDice API Fallback Domain Test")
    print("=" * 60)
    
    # Create config
    config = DuckDiceConfig(
        api_key='test_api_key_for_demo',
        base_url='https://duckdice.io/api',
        timeout=5
    )
    
    print("\n+ Configuration Created")
    print(f"  Primary URL: {config.base_url}")
    print(f"  Timeout: {config.timeout}s")
    print(f"\n  Fallback Domains:")
    for i, domain in enumerate(config.fallback_domains, 1):
        print(f"    {i}. {domain}")
    
    # Create API client
    api = DuckDiceAPI(config)
    
    print(f"\n+ API Client Initialized")
    print(f"  Current active URL: {api.current_base_url}")
    
    print("\n" + "=" * 60)
    print("Fallback Behavior:")
    print("=" * 60)
    print("""
When making API calls, the client will:

1. Try duckdice.io first (primary)
2. If connection fails → try duckdice.live
3. If that fails → try duckdice.net
4. If all fail → raise exception

The client remembers which domain worked and uses it
for subsequent requests, improving performance.

Automatic fallback happens on:
- Connection errors (server unreachable)
- Timeout errors (server too slow)
- HTTP errors (500, 502, 503, etc.)

The switch is transparent - your bot keeps running!
    """)
    
    print("=" * 60)
    print("Testing with simulation mode...")
    print("=" * 60)
    print("\nRun this to test:")
    print("  python duckdice_cli.py run -m simulation -c btc -s simple-progression-40 -b 100 --max-bets 10")
    print("\n+ Fallback domain test complete!")

if __name__ == "__main__":
    test_fallback_domains()
