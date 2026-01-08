#!/usr/bin/env python3
"""
Interactive Target-Aware Betting Strategy Launcher

This script provides a fully interactive startup for the target-aware strategy:
1. Detects all available balances
2. Prompts user to select currency
3. Prompts user to define target
4. Validates all inputs
5. Launches the target-aware strategy with optimal parameters

Usage:
    python run_target_aware.py <API_KEY>
    
Or set API_KEY environment variable:
    export DUCKDICE_API_KEY=your_key_here
    python run_target_aware.py
"""

import sys
import os
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Tuple

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_engine.engine import AutoBetEngine, EngineConfig


def get_api_key() -> str:
    """Get API key from arguments or environment."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    api_key = os.environ.get('DUCKDICE_API_KEY')
    if not api_key:
        print("Error: API key required", file=sys.stderr)
        print("Usage: python run_target_aware.py <API_KEY>", file=sys.stderr)
        print("   or: export DUCKDICE_API_KEY=your_key", file=sys.stderr)
        sys.exit(1)
    
    return api_key


def fetch_user_balances(api: DuckDiceAPI) -> List[Dict[str, Any]]:
    """
    Fetch all user balances from the API.
    
    Returns list of balance entries with 'currency', 'main', etc.
    """
    try:
        user_info = api.get_user_info()
        balances = user_info.get('balances', [])
        return balances
    except Exception as e:
        print(f"Error fetching user info: {e}", file=sys.stderr)
        sys.exit(1)


def get_currency_min_bet(api: DuckDiceAPI, symbol: str) -> Decimal:
    """
    Get minimum bet for a currency from currency stats.
    
    Returns minBet as Decimal.
    """
    try:
        stats = api.get_currency_stats(symbol)
        min_bet_str = stats.get('minBet', '0.00000001')
        return Decimal(str(min_bet_str))
    except Exception as e:
        print(f"Warning: Could not fetch min bet for {symbol}: {e}", file=sys.stderr)
        # Return conservative default
        return Decimal('0.00000001')


def display_available_balances(
    balances: List[Dict[str, Any]]
) -> List[Tuple[str, Decimal]]:
    """
    Display available balances to user.
    
    Returns list of (currency, balance) tuples for currencies with balance > 0.
    """
    available = []
    
    print("\n" + "="*60)
    print("AVAILABLE BALANCES")
    print("="*60)
    
    for balance_entry in balances:
        currency = balance_entry.get('currency', 'UNKNOWN')
        main_balance_str = balance_entry.get('main', '0')
        
        try:
            main_balance = Decimal(str(main_balance_str))
        except (InvalidOperation, ValueError):
            main_balance = Decimal('0')
        
        if main_balance > 0:
            available.append((currency, main_balance))
    
    if not available:
        print("No currencies with balance > 0 found.")
        print("="*60)
        return []
    
    # Display with index
    for idx, (currency, balance) in enumerate(available, start=1):
        print(f"{idx}) {currency:<10} - {balance}")
    
    print("="*60)
    return available


def select_currency(
    available: List[Tuple[str, Decimal]],
    api: DuckDiceAPI
) -> Tuple[str, Decimal, Decimal]:
    """
    Prompt user to select a currency.
    
    Returns (symbol, balance, minBet) tuple.
    Validates that balance >= minBet.
    """
    while True:
        try:
            selection = input("\nSelect the currency to bet with (number): ").strip()
            idx = int(selection)
            
            if idx < 1 or idx > len(available):
                print(f"Invalid selection. Please choose 1-{len(available)}")
                continue
            
            symbol, balance = available[idx - 1]
            
            # Fetch minBet
            print(f"\nFetching minimum bet for {symbol}...")
            min_bet = get_currency_min_bet(api, symbol)
            
            # Validate balance >= minBet
            if balance < min_bet:
                print(f"\n❌ Error: Balance ({balance}) < minBet ({min_bet})")
                print("Please select a different currency.\n")
                continue
            
            print(f"✅ Selected: {symbol}")
            print(f"   Balance: {balance}")
            print(f"   Min Bet: {min_bet}")
            
            return symbol, balance, min_bet
            
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)


def select_target(balance: Decimal) -> Decimal:
    """
    Prompt user to define target balance.
    
    Validates that target > current balance.
    """
    while True:
        try:
            target_str = input(f"\nTarget balance (current: {balance}): ").strip()
            target = Decimal(target_str)
            
            if target <= balance:
                print(f"❌ Error: Target ({target}) must be > current balance ({balance})")
                continue
            
            gain = target - balance
            gain_pct = float(gain / balance * 100)
            
            print(f"\n✅ Target set: {target}")
            print(f"   Required gain: {gain} (+{gain_pct:.2f}%)")
            
            # Confirm with user
            confirm = input("\nProceed with this target? (y/n): ").strip().lower()
            if confirm in ['y', 'yes']:
                return target
            else:
                print("Target cancelled. Please enter a new target.")
                
        except (InvalidOperation, ValueError):
            print("Invalid input. Please enter a valid number.")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)


def configure_strategy_params(
    symbol: str,
    balance: Decimal,
    target: Decimal,
    min_bet: Decimal
) -> Dict[str, Any]:
    """
    Configure strategy parameters.
    
    Returns parameter dictionary for target-aware strategy.
    """
    print("\n" + "="*60)
    print("STRATEGY CONFIGURATION")
    print("="*60)
    
    # Ask user if they want to customize or use defaults
    print("\nUse default strategy parameters? (recommended)")
    print("  - SAFE state: 95-98% win chance, 0.1-0.2% bet size")
    print("  - BUILD state: 70-85% win chance, 0.3-0.6% bet size")
    print("  - STRIKE state: 15-35% win chance, 0.8-2% bet size")
    print("  - Drawdown protection: 3% downgrade, 6% force safe, 10% stop")
    
    use_defaults = input("\nUse defaults? (y/n): ").strip().lower()
    
    params = {
        "target": str(target),
        "min_bet": str(min_bet),
    }
    
    if use_defaults not in ['y', 'yes']:
        print("\nCustom configuration not yet implemented. Using defaults.")
    
    print("="*60)
    return params


def configure_session_limits() -> Tuple[int, int]:
    """
    Configure session limits.
    
    Returns (max_bets, max_duration_sec) tuple.
    """
    print("\n" + "="*60)
    print("SESSION LIMITS")
    print("="*60)
    
    # Max bets
    while True:
        try:
            max_bets_str = input("\nMaximum number of bets (0 for unlimited): ").strip()
            max_bets = int(max_bets_str)
            if max_bets < 0:
                print("Please enter a non-negative number.")
                continue
            if max_bets == 0:
                max_bets = None
            break
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    # Max duration
    while True:
        try:
            max_duration_str = input("\nMaximum duration in minutes (0 for unlimited): ").strip()
            max_duration_min = int(max_duration_str)
            if max_duration_min < 0:
                print("Please enter a non-negative number.")
                continue
            if max_duration_min == 0:
                max_duration_sec = None
            else:
                max_duration_sec = max_duration_min * 60
            break
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    print("="*60)
    return max_bets, max_duration_sec


def display_session_summary(
    symbol: str,
    balance: Decimal,
    target: Decimal,
    min_bet: Decimal,
    max_bets: int,
    max_duration_sec: int
):
    """Display final session summary before starting."""
    print("\n" + "="*60)
    print("SESSION SUMMARY")
    print("="*60)
    print(f"Currency: {symbol}")
    print(f"Starting Balance: {balance}")
    print(f"Target Balance: {target}")
    print(f"Minimum Bet: {min_bet}")
    print(f"Required Gain: {target - balance} (+{float((target - balance) / balance * 100):.2f}%)")
    print(f"Max Bets: {max_bets if max_bets else 'Unlimited'}")
    if max_duration_sec:
        print(f"Max Duration: {max_duration_sec // 60} minutes")
    else:
        print(f"Max Duration: Unlimited")
    print("="*60)


def run_interactive_session(api_key: str):
    """
    Run the full interactive session.
    
    1. Detect balances
    2. Select currency
    3. Define target
    4. Configure strategy
    5. Launch betting session
    """
    print("\n" + "="*60)
    print("TARGET-AWARE BETTING STRATEGY")
    print("Interactive Startup")
    print("="*60)
    
    # Initialize API
    config = DuckDiceConfig(api_key=api_key)
    api = DuckDiceAPI(config)
    
    # Step 1: Fetch balances
    print("\n[1/5] Fetching account balances...")
    balances = fetch_user_balances(api)
    
    # Step 2: Display and select currency
    print("\n[2/5] Currency Selection")
    available = display_available_balances(balances)
    
    if not available:
        print("\n❌ No balances available for betting.")
        sys.exit(1)
    
    symbol, balance, min_bet = select_currency(available, api)
    
    # Step 3: Define target
    print("\n[3/5] Target Definition")
    target = select_target(balance)
    
    # Step 4: Configure strategy
    print("\n[4/5] Strategy Configuration")
    strategy_params = configure_strategy_params(symbol, balance, target, min_bet)
    
    # Step 5: Configure session limits
    print("\n[5/5] Session Limits")
    max_bets, max_duration_sec = configure_session_limits()
    
    # Display summary
    display_session_summary(
        symbol, balance, target, min_bet, max_bets, max_duration_sec
    )
    
    # Final confirmation
    print("\n⚠️  WARNING: This will place real bets with real money!")
    confirm = input("\nStart betting session? (type 'YES' to confirm): ").strip()
    
    if confirm != 'YES':
        print("\n❌ Session cancelled.")
        sys.exit(0)
    
    # Initialize engine
    engine_config = EngineConfig(
        symbol=symbol,
        delay_ms=750,
        jitter_ms=500,
        dry_run=False,
        faucet=False,
        stop_loss=-1.0,  # Disable percentage-based stop loss (using drawdown instead)
        take_profit=10.0,  # Large value to effectively disable
        max_bets=max_bets,
        max_duration_sec=max_duration_sec,
    )
    
    engine = AutoBetEngine(api, engine_config)
    
    # Run strategy
    print("\n" + "="*60)
    print("STARTING BETTING SESSION")
    print("="*60)
    print("Press Ctrl+C to stop gracefully\n")
    
    try:
        summary = engine.run(
            strategy_name="target-aware",
            params=strategy_params,
            printer=lambda msg: print(msg, flush=True),
        )
        
        # Display final summary
        print("\n" + "="*60)
        print("SESSION COMPLETED")
        print("="*60)
        print(f"Total Bets: {summary.get('total_bets', 0)}")
        print(f"Wins: {summary.get('wins', 0)}")
        print(f"Losses: {summary.get('losses', 0)}")
        if summary.get('total_bets', 0) > 0:
            win_rate = summary.get('wins', 0) / summary.get('total_bets', 1) * 100
            print(f"Win Rate: {win_rate:.2f}%")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⛔ Session stopped by user.")
        print("="*60)
    except Exception as e:
        print(f"\n\n❌ Error during session: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    try:
        api_key = get_api_key()
        run_interactive_session(api_key)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
