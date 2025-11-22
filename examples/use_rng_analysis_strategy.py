#!/usr/bin/env python3
"""
Example: Using RNG Analysis Results to Configure a Betting Strategy

This example demonstrates how to:
1. Run RNG analysis on bet history
2. Generate strategy configuration from the analysis
3. Use the generated configuration with the auto-bet engine

⚠️ IMPORTANT DISCLAIMER:
- This is for EDUCATIONAL PURPOSES ONLY
- Cryptographic RNG cannot be predicted
- Past patterns do NOT predict future outcomes
- The house edge ensures long-term losses
- Only use faucet mode or amounts you can afford to lose
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_engine.engine import AutoBetEngine, EngineConfig


def step1_generate_strategy_config():
    """
    Step 1: Generate strategy configuration from RNG analysis
    
    This runs the RNG analysis on your bet history and creates:
    - rng_strategy_config.json (JSON format)
    - rng_strategy_params.py (Python format)
    """
    print("="*70)
    print("STEP 1: GENERATING STRATEGY FROM RNG ANALYSIS")
    print("="*70)
    
    try:
        # Import the strategy generator
        sys.path.insert(0, str(Path(__file__).parent.parent / "rng_analysis"))
        from strategy_generator import generate_strategy_from_analysis
        
        # Generate strategy configuration
        # This analyzes bet_history/*.csv files
        insights = generate_strategy_from_analysis(
            data_dir=str(Path(__file__).parent.parent / "bet_history"),
            output_json="rng_strategy_config.json",
            output_python="rng_strategy_params.py"
        )
        
        return insights
        
    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies for RNG analysis")
        print(f"   {e}")
        print(f"\nInstall with:")
        print(f"   cd rng_analysis")
        print(f"   pip install -r requirements_analysis.txt")
        return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def step2_load_and_use_strategy(api_key: str, use_faucet: bool = True, dry_run: bool = True):
    """
    Step 2: Load the generated strategy and use it with the auto-bet engine
    
    Args:
        api_key: Your DuckDice API key
        use_faucet: Whether to use faucet balance (recommended for testing)
        dry_run: Whether to simulate bets without actual API calls
    """
    print("\n" + "="*70)
    print("STEP 2: LOADING AND USING STRATEGY")
    print("="*70)
    
    # Check if config file exists
    config_path = Path("rng_strategy_config.json")
    if not config_path.exists():
        print(f"\n❌ Config file not found: {config_path}")
        print("   Run step1_generate_strategy_config() first")
        return
    
    # Load strategy from config
    try:
        from betbot_strategies.rng_analysis_strategy import load_strategy_from_config
        
        # Load the conservative strategy (index 0)
        print("\nLoading strategy from config...")
        strategy_config = load_strategy_from_config(str(config_path), strategy_index=0)
        
        print(f"✅ Loaded strategy: {strategy_config['strategy_name']}")
        print(f"   Parameters: {strategy_config['params']}")
        
    except Exception as e:
        print(f"❌ Error loading strategy: {e}")
        return
    
    # Create API client
    api = DuckDiceAPI(DuckDiceConfig(api_key=api_key))
    
    # Create engine configuration
    engine_config = EngineConfig(
        symbol="XLM",  # Stellar Lumens
        faucet=use_faucet,
        dry_run=dry_run,
        delay_ms=750,
        jitter_ms=500,
        stop_loss=-0.02,      # Stop after losing 2%
        take_profit=0.01,     # Stop after gaining 1%
        max_bets=50,          # Max 50 bets per session
        max_losses=10,        # Stop after 10 consecutive losses
        max_duration_sec=300, # Stop after 5 minutes
    )
    
    # Create auto-bet engine
    engine = AutoBetEngine(api, engine_config)
    
    # Define output handlers
    def print_bet(msg: str):
        print(f"  {msg}")
    
    def log_json(data: dict):
        # Could save to file or database
        pass
    
    # Run the strategy
    print("\n" + "="*70)
    print("STARTING AUTO-BET SESSION")
    print("="*70)
    print(f"Mode: {'DRY RUN (simulated)' if dry_run else 'LIVE'}")
    print(f"Currency: {engine_config.symbol}")
    print(f"Faucet: {use_faucet}")
    print(f"Stop Loss: {engine_config.stop_loss*100}%")
    print(f"Take Profit: {engine_config.take_profit*100}%")
    print(f"Max Bets: {engine_config.max_bets}")
    print()
    
    try:
        result = engine.run(
            strategy_name=strategy_config['strategy_name'],
            params=strategy_config['params'],
            printer=print_bet,
            json_sink=log_json,
        )
        
        print("\n" + "="*70)
        print("SESSION COMPLETE")
        print("="*70)
        print(f"Result: {result}")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Session interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during session: {e}")
        import traceback
        traceback.print_exc()


def step3_compare_strategies():
    """
    Step 3: Compare different strategies from the analysis
    
    This loads multiple recommended strategies and shows their parameters
    """
    print("\n" + "="*70)
    print("STEP 3: COMPARING RECOMMENDED STRATEGIES")
    print("="*70)
    
    config_path = Path("rng_strategy_config.json")
    if not config_path.exists():
        print(f"\n❌ Config file not found: {config_path}")
        return
    
    import json
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        strategies = config.get('strategy_recommendations', {}).get('recommended_strategies', [])
        
        if not strategies:
            print("No strategies found in config")
            return
        
        print(f"\nFound {len(strategies)} recommended strategies:\n")
        
        for i, strategy in enumerate(strategies):
            print(f"{i+1}. {strategy['name'].upper()}")
            print(f"   Base Strategy: {strategy['base_strategy']}")
            print(f"   Reason: {strategy['reason']}")
            
            if 'warning' in strategy:
                print(f"   ⚠️  Warning: {strategy['warning']}")
            
            print(f"   Parameters:")
            for key, value in strategy['parameters'].items():
                print(f"     {key}: {value}")
            print()
        
        print("="*70)
        print("\nTo use a different strategy:")
        print("  strategy_config = load_strategy_from_config('rng_strategy_config.json', strategy_index=1)")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main example function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Example: Using RNG Analysis Results with Auto-Bet',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Step 1: Generate strategy from analysis
  python use_rng_analysis_strategy.py --generate
  
  # Step 2: Use strategy (dry run)
  python use_rng_analysis_strategy.py --api-key YOUR_KEY --dry-run
  
  # Step 3: Use strategy (live with faucet)
  python use_rng_analysis_strategy.py --api-key YOUR_KEY --faucet
  
  # Compare strategies
  python use_rng_analysis_strategy.py --compare

⚠️ DISCLAIMER: Educational purposes only! Past patterns don't predict future outcomes.
        """
    )
    
    parser.add_argument('--generate', action='store_true',
                       help='Generate strategy configuration from RNG analysis')
    parser.add_argument('--compare', action='store_true',
                       help='Compare recommended strategies')
    parser.add_argument('--api-key', type=str,
                       help='DuckDice API key')
    parser.add_argument('--faucet', action='store_true',
                       help='Use faucet balance')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulate bets without API calls')
    parser.add_argument('--live', action='store_true',
                       help='Run live betting (requires API key)')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("RNG ANALYSIS TO BETTING STRATEGY EXAMPLE".center(70))
    print("="*70)
    print("\n⚠️  DISCLAIMER: This is for EDUCATIONAL PURPOSES ONLY")
    print("   - Cryptographic RNG cannot be predicted")
    print("   - Past patterns don't predict future outcomes")
    print("   - The house edge ensures long-term losses")
    print("   - Use faucet mode or amounts you can afford to lose")
    print()
    
    if args.generate:
        # Generate strategy configuration
        insights = step1_generate_strategy_config()
        
        if insights:
            print("\n✅ Strategy configuration generated successfully!")
            print("\nNext steps:")
            print("  1. Review rng_strategy_config.json")
            print("  2. Run with --compare to see all strategies")
            print("  3. Test with --api-key YOUR_KEY --dry-run")
        
    elif args.compare:
        # Compare strategies
        step3_compare_strategies()
        
    elif args.api_key:
        # Run betting session
        if not args.dry_run and not args.faucet and not args.live:
            print("\n⚠️  WARNING: You must specify --dry-run, --faucet, or --live")
            print("   For safety, use --dry-run first to test")
            return
        
        step2_load_and_use_strategy(
            api_key=args.api_key,
            use_faucet=args.faucet or args.dry_run,
            dry_run=args.dry_run
        )
        
    else:
        # Show help
        parser.print_help()
        print("\n" + "="*70)
        print("Quick Start:")
        print("="*70)
        print("\n1. Generate strategy from your bet history:")
        print("   python use_rng_analysis_strategy.py --generate")
        print("\n2. Compare recommended strategies:")
        print("   python use_rng_analysis_strategy.py --compare")
        print("\n3. Test with dry run (no real bets):")
        print("   python use_rng_analysis_strategy.py --api-key YOUR_KEY --dry-run")
        print("\n4. Test with faucet (small amounts):")
        print("   python use_rng_analysis_strategy.py --api-key YOUR_KEY --faucet")
        print()


if __name__ == "__main__":
    main()
