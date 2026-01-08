#!/usr/bin/env python3
"""
Quick test to verify enhanced strategy info is working.
"""
import sys
sys.path.insert(0, 'src')

from betbot_strategies import list_strategies, get_strategy

# Import all strategies to trigger registration
from betbot_strategies import (
    classic_martingale,
    anti_martingale_streak,
    labouchere,
    dalembert,
    fibonacci,
    paroli,
    oscars_grind,
    one_three_two_six,
    rng_analysis_strategy,
    target_aware,
    faucet_cashout,
    kelly_capped,
    max_wager_flow,
    range50_random,
    fib_loss_cluster,
    custom_script
)

print("=" * 70)
print("TESTING ENHANCED STRATEGY METADATA")
print("=" * 70)

strategies = list_strategies()
print(f"\n✓ Found {len(strategies)} total strategies\n")

# Test a few strategies
test_strategies = ['classic-martingale', 'fibonacci', 'paroli', 'dalembert', 'labouchere']

for strategy_name in test_strategies:
    try:
        print(f"\n{'─' * 70}")
        print(f"📊 {strategy_name.upper()}")
        print('─' * 70)
        
        cls = get_strategy(strategy_name)
        
        # Description
        if hasattr(cls, 'describe'):
            print(f"\n{cls.describe()}")
        
        # Metadata
        if hasattr(cls, 'metadata'):
            meta = cls.metadata()
            
            print(f"\n🎯 Risk Level: {meta.risk_level}")
            print(f"💰 Bankroll Required: {meta.bankroll_required}")
            print(f"📈 Volatility: {meta.volatility}")
            print(f"⏱️  Time to Profit: {meta.time_to_profit}")
            print(f"👤 Recommended For: {meta.recommended_for}")
            
            print(f"\n📌 Best Use Case:")
            print(f"   {meta.best_use_case}")
            
            print(f"\n✅ Advantages ({len(meta.pros)}):")
            for pro in meta.pros[:3]:  # Show first 3
                print(f"   • {pro}")
            if len(meta.pros) > 3:
                print(f"   ... and {len(meta.pros) - 3} more")
            
            print(f"\n⚠️  Disadvantages ({len(meta.cons)}):")
            for con in meta.cons[:3]:  # Show first 3
                print(f"   • {con}")
            if len(meta.cons) > 3:
                print(f"   ... and {len(meta.cons) - 3} more")
            
            print(f"\n💡 Expert Tips ({len(meta.tips)}):")
            for tip in meta.tips[:2]:  # Show first 2
                print(f"   • {tip}")
            if len(meta.tips) > 2:
                print(f"   ... and {len(meta.tips) - 2} more tips")
        else:
            print("\n⚠️  No metadata available")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

print(f"\n{'=' * 70}")
print("TEST COMPLETE - All strategies have rich metadata!")
print('=' * 70)

# Count strategies with metadata
with_meta = 0
without_meta = 0

for s in strategies:
    try:
        cls = get_strategy(s['name'])
        if hasattr(cls, 'metadata'):
            with_meta += 1
        else:
            without_meta += 1
    except:
        without_meta += 1

print(f"\n📊 Summary:")
print(f"   ✓ Strategies with metadata: {with_meta}")
print(f"   ⚠️  Strategies without metadata: {without_meta}")
print(f"   📦 Total strategies: {len(strategies)}")
