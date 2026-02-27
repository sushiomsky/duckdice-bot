import sys
import os
from decimal import Decimal, ROUND_DOWN

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from betbot_strategies.nano_range_hunter import NanoRangeHunter
from betbot_strategies.base import StrategyContext, SessionLimits
from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
import random

def verify_profit_bounds():
    config = DuckDiceConfig(api_key="test")
    api = DuckDiceAPI(config)
    limits = SessionLimits(symbol="BTC")
    ctx = StrategyContext(
        api=api, symbol="BTC", faucet=False, dry_run=True,
        rng=random.Random(42), logger=lambda x: None, limits=limits,
        starting_balance="1.0"
    )
    
    # We need to remove recovery params from the call since they are gone
    params = {
        "win_at_ceil": 0.25,
        "win_at_nano": 10.0,
        "min_chance": 0.01,
        "max_chance": 1.0,
    }
    
    strat = NanoRangeHunter(params, ctx)
    strat.on_session_start()
    
    balance = Decimal("1.0")
    strat._live_bal = balance
    
    # Test a range of chances
    chances = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]
    
    print(f"{'Chance (%)':>10} | {'Multiplier':>10} | {'Bet Amount':>12} | {'Win Profit %':>12} | {'Valid'}")
    print("-" * 65)
    
    all_valid = True
    for chance in chances:
        bet = strat._calc_bet(chance)
        multiplier = Decimal(str(99.0 / chance - 1.0))
        profit = bet * multiplier
        profit_pct = (profit / balance) * 100
        
        # Valid range is 25% to 1000%
        is_valid = Decimal("24.99") <= profit_pct <= Decimal("1000.01")
        if not is_valid:
            all_valid = False
            
        print(f"{chance:>10.2f} | {99.0/chance:>10.2f} | {float(bet):>12.8f} | {float(profit_pct):>12.2f}% | {'✅' if is_valid else '❌'}")

    if all_valid:
        print("\n✅ All profit percentages are within the 25%-1000% range.")
    else:
        print("\n❌ Some profit percentages are outside the 25%-1000% range.")
        sys.exit(1)

if __name__ == "__main__":
    verify_profit_bounds()
