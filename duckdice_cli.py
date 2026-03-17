#!/usr/bin/env python3
"""
DuckDice Bot CLI - Complete Command Line Interface
Supports simulation, live betting (main/faucet), strategy management, and persistence
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List

from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
from betbot_engine.engine import AutoBetEngine, EngineConfig
from betbot_engine.parallel_engine import ParallelBettingEngine
from betbot_strategies import list_strategies, get_strategy

# Enhanced CLI display
try:
    from cli_display import display, CLIDisplay
    USE_RICH = True
except ImportError:
    USE_RICH = False
    display = None

CONFIG_DIR = Path.home() / '.duckdice'
CONFIG_FILE = CONFIG_DIR / 'config.json'
PROFILES_FILE = CONFIG_DIR / 'profiles.json'
DB_FILE = CONFIG_DIR / 'history.db'


class ConfigManager:
    """Manages CLI configuration and strategy profiles"""
    
    def __init__(self):
        CONFIG_DIR.mkdir(exist_ok=True)
        self.config = self._load_config()
        self.profiles = self._load_profiles()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return json.load(f)
        return {
            'api_key': '',
            'default_currency': 'btc',
            'default_mode': 'simulation',
            'default_balance': '100.0',
        }
    
    def _load_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load strategy profiles"""
        if PROFILES_FILE.exists():
            with open(PROFILES_FILE) as f:
                return json.load(f)
        return {}
    
    def save_config(self):
        """Save main configuration"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def save_profiles(self):
        """Save strategy profiles"""
        with open(PROFILES_FILE, 'w') as f:
            json.dump(self.profiles, f, indent=2)
    
    def save_profile(self, name: str, strategy: str, params: Dict[str, Any]):
        """Save a strategy profile"""
        self.profiles[name] = {
            'strategy': strategy,
            'parameters': params,
            'created_at': datetime.now().isoformat()
        }
        self.save_profiles()
    
    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a strategy profile by name"""
        return self.profiles.get(name)
    
    def list_profiles(self) -> List[str]:
        """List all profile names"""
        return list(self.profiles.keys())


class MockDuckDiceAPI:
    """Mock API for simulation mode"""
    
    def get_user_info(self):
        """Return mock user info with common currencies"""
        return {
            'username': 'simulation_user',
            'hash': 'sim123',
            'balances': [
                {'currency': 'BTC', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'ETH', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'DOGE', 'main': '100000.0', 'faucet': '10000.0'},
                {'currency': 'LTC', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'XRP', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'TRX', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'SOL', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'DECOY', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'PEPE', 'main': '100.0', 'faucet': '10.0'},
                {'currency': 'TRUMP', 'main': '100.0', 'faucet': '10.0'},
                # Add more as needed - or use uppercase version
            ]
        }
    
    def play_dice(self, *args, **kwargs):
        """Mock play_dice - should not be called in dry_run"""
        raise NotImplementedError("API calls should not happen in dry_run mode")
    
    def play_range_dice(self, *args, **kwargs):
        """Mock play_range_dice - should not be called in dry_run"""
        raise NotImplementedError("API calls should not happen in dry_run mode")


class SessionTracker:
    """Tracks betting sessions and statistics"""
    
    def __init__(self):
        self.total_bets = 0
        self.wins = 0
        self.losses = 0
        self.starting_balance = None
        self.current_balance = None
    
    def update(self, bet_result: Dict[str, Any]):
        """Update stats from bet result"""
        self.total_bets += 1
        
        # Extract result data (win/loss/profit are nested in 'result' dict)
        result = bet_result.get('result', {})
        if result.get('win'):
            self.wins += 1
        else:
            self.losses += 1
        
        if 'balance' in bet_result:
            self.current_balance = float(bet_result['balance'])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        profit = 0
        profit_pct = 0
        win_rate = 0
        
        if self.starting_balance and self.current_balance:
            profit = self.current_balance - self.starting_balance
            profit_pct = (profit / self.starting_balance * 100) if self.starting_balance > 0 else 0
        
        if self.total_bets > 0:
            win_rate = (self.wins / self.total_bets * 100)
        
        return {
            'total_bets': self.total_bets,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'starting_balance': self.starting_balance or 0,
            'current_balance': self.current_balance or 0,
            'profit': profit,
            'profit_percent': profit_pct
        }


def prompt_with_default(prompt: str, default: Any, cast_type=str) -> Any:
    """Prompt user with a default value"""
    response = input(f"{prompt} [{default}]: ").strip()
    if not response:
        return cast_type(default)
    try:
        return cast_type(response)
    except (ValueError, TypeError):
        print(f"Invalid input, using default: {default}")
        return cast_type(default)


def prompt_choice(prompt: str, choices: List[str], default: str = None) -> str:
    """Prompt user to select from choices"""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")
    
    while True:
        response = input(f"Select [1-{len(choices)}]: ").strip()
        if not response and default:
            return default
        try:
            idx = int(response) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print("Invalid choice, try again.")


def _pick_strategy(preselected: str = None) -> str:
    """Two-step strategy selection: base name → version (if variants exist).
    Shows description after selection. Returns final strategy name (may include @vN).
    """
    from betbot_strategies import list_strategies, get_strategy

    all_raw = list_strategies()
    all_names = [s['name'] for s in all_raw]
    desc_map = {s['name']: s.get('description', '') for s in all_raw}

    # Separate base names from versioned variants
    base_names = sorted(set(n.split('@')[0] for n in all_names))

    if preselected:
        base = preselected.split('@')[0]
        if base not in base_names:
            return preselected
        strategy_base = base
        # If already has version suffix, skip prompts
        if '@' in preselected:
            _show_strategy_desc(preselected, desc_map)
            return preselected
    else:
        strategy_base = prompt_choice("Select strategy:", base_names)

    # Offer version choice if variants exist
    variants = sorted(n for n in all_names if n.startswith(strategy_base + '@'))
    if variants:
        version_opts = [f'{strategy_base} (latest)'] + variants
        choice = prompt_choice(
            f"Multiple versions of '{strategy_base}' available:",
            version_opts,
            default=version_opts[0],
        )
        strategy_name = strategy_base if choice == version_opts[0] else choice
    else:
        strategy_name = strategy_base

    _show_strategy_desc(strategy_name, desc_map)
    return strategy_name


def _show_strategy_desc(strategy_name: str, desc_map: dict) -> None:
    """Print description for the selected strategy."""
    desc = desc_map.get(strategy_name, '')
    if not desc:
        # Try the base name's description for versioned strategies
        base = strategy_name.split('@')[0]
        desc = desc_map.get(base, '')
    if desc:
        if USE_RICH and display:
            display.console.print(f"\n[dim]{desc}[/dim]\n")
        else:
            print(f"\n  {desc}\n")


def run_strategy(strategy_name: str, params: Dict[str, Any], config: EngineConfig,
                api_key: str = None, dry_run: bool = True, use_parallel: bool = False,
                max_concurrent: int = 5, resume_state: Optional[Dict[str, Any]] = None):
    """Run a betting strategy with enhanced display and runtime controls"""
    
    # Use rich display if available
    if USE_RICH and display:
        display.print_section(f"Starting Strategy: {strategy_name}")
        if dry_run:
            mode_label = 'Simulation'
        elif config.tle_hash:
            mode_label = 'TLE Event'
        elif config.faucet:
            mode_label = 'Faucet'
        else:
            mode_label = 'Main'
        display.print_info(f"Mode: {mode_label}")
        display.print_info(f"Currency: {config.symbol}")
        if config.tle_hash:
            display.print_info(f"🏆 TLE Hash: {config.tle_hash}")
        if use_parallel:
            display.print_info(f"⚡ Parallel Mode: {max_concurrent} concurrent bets")
        print()
    else:
        print(f"\n{'='*60}")
        print(f"Starting strategy: {strategy_name}")
        if dry_run:
            mode_label = 'Simulation'
        elif config.tle_hash:
            mode_label = 'TLE Event'
        elif config.faucet:
            mode_label = 'Faucet'
        else:
            mode_label = 'Main'
        print(f"Mode: {mode_label}")
        print(f"Currency: {config.symbol}")
        if config.tle_hash:
            print(f"🏆 TLE Hash: {config.tle_hash}")
        if use_parallel:
            print(f"⚡ Parallel Mode: {max_concurrent} concurrent bets")
        print(f"{'='*60}\n")
    
    # Runtime controls
    print("⌨️  Runtime Controls:")
    print("  • Press Ctrl+C to stop")
    if use_parallel:
        print(f"  • Parallel: {max_concurrent} concurrent API calls")
    else:
        print(f"  • Speed: Fast ({config.delay_ms}ms + {config.jitter_ms}ms jitter)")
    print()
    
    # Session tracker
    tracker = SessionTracker()
    stop_requested = False
    current_speed = config.delay_ms  # Track current speed
    
    # Progress bar for rich display
    progress = None
    task_id = None
    
    if USE_RICH and display and config.max_bets:
        progress = display.create_progress_bar(config.max_bets, f"Running {strategy_name}")
        progress.__enter__()
        task_id = progress.add_task(f"Placing bets...", total=config.max_bets)
    def should_stop():
        return stop_requested
    
    def printer(msg: str):
        """Print bet results and debug messages"""
        if USE_RICH and display:
            display.console.print(msg)
        else:
            print(msg)
    
    def json_sink(bet_data: Dict[str, Any]):
        """Track bet statistics with enhanced display"""
        tracker.update(bet_data)
        
        # Extract nested result data
        result = bet_data.get('result', {})
        balance = float(bet_data.get('balance', 0))
        
        # Get balance from bet data
        if tracker.starting_balance is None:
            # First bet - extract starting balance
            profit = float(result.get('profit', 0))
            tracker.starting_balance = balance - profit
            tracker.current_balance = balance
        
        # Print formatted bet result
        if tracker.total_bets % 1 == 0:  # Every bet
            win = result.get('win', False)
            profit_val = float(result.get('profit', 0))
            bet_spec = bet_data.get('bet', {})
            bet_amount = float(bet_spec.get('amount', 0))
            multiplier = float(bet_spec.get('payout_multiplier', 0))
            
            if USE_RICH and display:
                # Enhanced display with colors
                display.print_bet_result(
                    tracker.total_bets,
                    win,
                    profit_val,
                    balance,
                    bet_amount,
                    multiplier
                )
                
                # Update progress bar
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)
            else:
                # Fallback plain text
                win_marker = "✓" if win else "✗"
                status = "WIN" if win else "LOSE"
                print(f"Bet #{tracker.total_bets}: {win_marker} {status} | "
                      f"Profit: {profit_val:>12} | "
                      f"Balance: {balance:>12}")
        
        # Print stats periodically
        if tracker.total_bets % 10 == 0:
            stats = tracker.get_stats()
            if USE_RICH and display:
                display.print_live_stats(
                    tracker.total_bets,
                    stats['wins'],
                    stats['losses'],
                    stats['profit'],
                    stats['current_balance'],
                    stats['win_rate']
                )
            else:
                print(f"\n--- Stats after {tracker.total_bets} bets ---")
                print(f"Win rate: {stats['win_rate']:.1f}%")
                print(f"Profit: {stats['profit']:.8f} ({stats['profit_percent']:.2f}%)")
                print(f"Balance: {stats['current_balance']:.8f}\n")
    
    try:
        # Create API
        if not dry_run:
            if not api_key:
                raise ValueError("API key required for live betting")
            api = DuckDiceAPI(DuckDiceConfig(api_key=api_key))
        else:
            # For simulation, use mock API
            api = MockDuckDiceAPI()
        
        # Create engine (parallel or sequential)
        if use_parallel:
            # Parallel engine needs manual strategy setup
            from betbot_strategies.base import StrategyContext, SessionLimits
            import random
            import time as time_mod
            
            # Get starting balance
            try:
                user_info = api.get_user_info()
                from betbot_engine.engine import _parse_user_symbol_balance, _decimal
                starting_balance = _parse_user_symbol_balance(user_info, config.symbol)
            except Exception as e:
                print(f"⚠️  Warning: Failed to fetch balance: {e}")
                starting_balance = _decimal(0)
            
            # Create limits
            limits = SessionLimits(
                symbol=config.symbol,
                stop_loss=config.stop_loss,
                take_profit=config.take_profit,
                max_bet=_decimal(config.max_bet) if config.max_bet else None,
                max_bets=config.max_bets,
                max_losses=config.max_losses,
                max_duration_sec=config.max_duration_sec,
            )
            
            # Create RNG
            rng = random.Random(int(time_mod.time() * 1000) & 0xFFFFFFFF)
            
            # Create context
            ctx = StrategyContext(
                api=api,
                symbol=config.symbol,
                faucet=config.faucet,
                dry_run=config.dry_run,
                rng=rng,
                logger=lambda rec: None,  # Handled by json_sink
                limits=limits,
                delay_ms=config.delay_ms,
                jitter_ms=config.jitter_ms,
                starting_balance=str(starting_balance)
            )
            
            # Create strategy instance
            strategy_class = get_strategy(strategy_name)
            strategy_instance = strategy_class(params, ctx)

            # --- Keypress bet-size adjuster ---
            from betbot_engine.keypress_adjuster import KeypressAdjuster
            _adj_step = float(params.get("min_bet_abs", 0.000001))
            _adjuster = KeypressAdjuster(step=_adj_step, printer=printer)
            _adjuster.start()

            # Create parallel engine
            parallel_engine = ParallelBettingEngine(api, config, max_concurrent=max_concurrent)
            
            # Run parallel betting session
            result = parallel_engine.run(
                strategy=strategy_instance,
                printer=printer,
                json_sink=json_sink,
                stop_checker=should_stop
            )
        else:
            # --- Keypress bet-size adjuster (sequential) ---
            from betbot_engine.keypress_adjuster import KeypressAdjuster
            _adj_step = float(params.get("min_bet_abs", 0.000001))
            _adjuster = KeypressAdjuster(step=_adj_step, printer=printer)
            _adjuster.start()

            # Sequential engine (original)
            engine = AutoBetEngine(api, config)
            
            # Run betting session
            result = engine.run(
                strategy_name=strategy_name,
                params=params,
                printer=printer,  # Enable printer for debug messages
                json_sink=json_sink,
                stop_checker=should_stop,
                resume_state=resume_state,
                bet_offset_fn=_adjuster.get_offset,
            )
        
        # Close progress bar if active
        if progress:
            progress.__exit__(None, None, None)

        # Stop keypress adjuster
        try:
            _adjuster.stop()
        except Exception:
            pass
        
        # Print final summary
        stats = tracker.get_stats()
        
        if USE_RICH and display:
            display.print_section("Session Summary")
            
            summary_stats = {
                'Stop Reason': result.get('stop_reason', 'unknown'),
                'Total Bets': stats['total_bets'],
                'Wins': stats['wins'],
                'Losses': stats['losses'],
                'Win Rate': f"{stats['win_rate']:.2f}%",
                'Starting Balance': f"{stats['starting_balance']:.8f}",
                'Ending Balance': f"{stats['current_balance']:.8f}",
                'Profit': f"{stats['profit']:.8f}",
                'Profit %': f"{stats['profit_percent']:.2f}%"
            }
            
            display.print_statistics_table(summary_stats)
            display.print_success("Session completed")
        else:
            print(f"\n{'='*60}")
            print("SESSION SUMMARY")
            print(f"{'='*60}")
            print(f"Stop reason: {result.get('stop_reason', 'unknown')}")
            print(f"Total bets: {stats['total_bets']}")
            print(f"Wins: {stats['wins']}")
            print(f"Losses: {stats['losses']}")
            print(f"Win rate: {stats['win_rate']:.2f}%")
            print(f"Starting balance: {stats['starting_balance']:.8f}")
            print(f"Ending balance: {stats['current_balance']:.8f}")
            print(f"Profit: {stats['profit']:.8f} ({stats['profit_percent']:.2f}%)")
            print(f"{'='*60}\n")
        return result

    except KeyboardInterrupt:
        if progress:
            progress.__exit__(None, None, None)
        if USE_RICH and display:
            display.print_warning("Interrupted by user")
        else:
            print("\n\n⚠ Interrupted by user")
        stop_requested = True
        return None
    except Exception as e:
        if progress:
            progress.__exit__(None, None, None)
        if USE_RICH and display:
            display.print_error(f"Error: {e}")
        else:
            print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Faucet balance thresholds (min bet per currency, matches engine floor)
# ---------------------------------------------------------------------------
_FAUCET_MIN_BETS: Dict[str, float] = {
    'btc': 0.00000034, 'eth': 0.000001, 'ltc': 0.0001, 'doge': 0.1,
    'bch': 0.00001,    'trx': 1.0,      'sol': 0.000001, 'xrp': 0.000001,
    'pepe': 1.0,       'trump': 1.0,
}


def _faucet_do_claim(api, symbol: str, cookie: Optional[str],
                     last_claim_time: float) -> tuple:
    """Wait for 60s cooldown if needed, then claim faucet.

    Returns (success, new_faucet_balance, claims_remaining, updated_last_claim_time).
    """
    import time
    elapsed = time.time() - last_claim_time
    if elapsed < 60.0:
        wait_sec = int(60.0 - elapsed) + 2   # +2s server-side buffer
        print(f"⏳ Faucet cooldown — waiting {wait_sec}s…")
        for remaining in range(wait_sec, 0, -1):
            print(f"\r⏳ {remaining:3d}s remaining…  ", end="", flush=True)
            time.sleep(1)
        print()

    now = time.time()
    result = api.claim_faucet(symbol, cookie)

    if result.get('success'):
        amount = result.get('amount', 0)
        claims_left = result.get('claims_remaining', 0)
        print(f"🪙  Faucet claimed! +{amount} {symbol.upper()}  |  "
              f"Claims remaining today: {claims_left}")
        try:
            new_bal = api.get_faucet_balance(symbol)
        except Exception:
            new_bal = float(amount)
        return True, new_bal, claims_left, now
    else:
        error = result.get('error', 'unknown error')
        claims_left = result.get('claims_remaining', 0)
        print(f"❌  Faucet claim failed: {error}")
        if claims_left == 0:
            print("⏰  Daily faucet limit reached.")
        return False, 0.0, claims_left, last_claim_time


def _run_faucet_auto_loop(strategy_name: str, params: Dict[str, Any],
                           config: "EngineConfig", api_key: str,
                           cookie: Optional[str], take_profit_target: float) -> None:
    """Run a strategy on faucet balance with automatic reclaim on bust.

    Flow per iteration:
    1. Verify faucet balance can cover min bet; if not, claim (respecting 60s cooldown).
    2. Run one strategy session.
    3. If take-profit reached (overall or per-session) → stop.
    4. If busted (stop_loss / insufficient_balance): double-check faucet balance,
       then claim and restart.
    5. Stop when no claims remain for the day or Ctrl-C.
    """
    import time
    from duckdice_api.api import DuckDiceAPI, DuckDiceConfig

    api = DuckDiceAPI(DuckDiceConfig(api_key=api_key))
    sym = config.symbol.lower()
    min_bet = _FAUCET_MIN_BETS.get(sym, 0.00000001)

    last_claim_time: float = 0.0
    session_num: int = 0
    overall_start_balance: Optional[float] = None

    print(f"\n🔄  Faucet auto-loop started | strategy={strategy_name} "
          f"| currency={sym.upper()} | overall target=+{take_profit_target*100:.0f}%")
    print(f"    Auto-reclaim after bust  |  60s cooldown respected  |  "
          f"stops when daily limit exhausted\n")

    while True:
        # ── 1. Ensure there is enough faucet balance to bet ────────────────
        try:
            faucet_bal = api.get_faucet_balance(sym)
        except Exception as e:
            print(f"⚠️  Could not read faucet balance: {e}")
            faucet_bal = 0.0

        if faucet_bal < min_bet:
            print(f"\n💸  Faucet balance {faucet_bal:.8f} < min bet {min_bet}. Claiming…")
            ok, faucet_bal, claims_left, last_claim_time = _faucet_do_claim(
                api, sym, cookie, last_claim_time)
            if not ok or claims_left == 0 or faucet_bal < min_bet:
                print("⛔  Cannot continue: faucet unavailable or daily limit reached.")
                break

        if overall_start_balance is None:
            overall_start_balance = faucet_bal

        session_num += 1
        if session_num > 1:
            print(f"\n{'─'*60}")
            print(f"🔄  Faucet session #{session_num}  |  balance: {faucet_bal:.8f} {sym.upper()}")
            print(f"{'─'*60}\n")

        # ── 2. Run one session ──────────────────────────────────────────────
        result = run_strategy(strategy_name, params, config, api_key, dry_run=False)

        if result is None:
            # Ctrl-C or unhandled error — stop loop
            break

        stop_reason = result.get('stop_reason', 'unknown')
        final_balance = float(result.get('final_balance', result.get('ending_balance', 0)))

        # ── 3. Overall take-profit check ───────────────────────────────────
        if overall_start_balance and overall_start_balance > 0:
            total_gain = (final_balance - overall_start_balance) / overall_start_balance
            if total_gain >= take_profit_target:
                print(f"\n🎯  Overall faucet target reached! "
                      f"+{total_gain*100:.1f}% on {sym.upper()}")
                break

        if stop_reason == 'take_profit':
            print(f"\n🎯  Take-profit reached in session #{session_num}!")
            break

        # ── 4. Non-bust stops — just exit ─────────────────────────────────
        if stop_reason in ('cancelled', 'max_bets', 'max_duration'):
            print(f"\nℹ️   Session ended: {stop_reason}. Exiting faucet loop.")
            break

        # ── 5. Bust — verify balance really below min bet ─────────────────
        try:
            current_faucet = api.get_faucet_balance(sym)
        except Exception:
            current_faucet = 0.0

        if current_faucet >= min_bet:
            print(f"\nℹ️   Still {current_faucet:.8f} {sym.upper()} in faucet — continuing.")
            continue

        # Truly busted — reclaim
        print(f"\n💸  Bust ({stop_reason}) | faucet balance: {current_faucet:.8f} < {min_bet}. Reclaiming…")
        ok, new_bal, claims_left, last_claim_time = _faucet_do_claim(
            api, sym, cookie, last_claim_time)
        if not ok:
            print("⛔  Claim failed. Exiting faucet loop.")
            break
        if claims_left == 0:
            print("⏰  No faucet claims remaining today. Exiting.")
            break
        if new_bal < min_bet:
            print(f"⚠️   Claimed but balance {new_bal:.8f} still below min bet. Exiting.")
            break

    print(f"\n{'='*60}")
    print(f"🏁  Faucet auto-loop finished after {session_num} session(s).")
    print(f"{'='*60}\n")


def cmd_run(args):
    """Run a betting strategy"""
    config_mgr = ConfigManager()

    # ------------------------------------------------------------------
    # --continue: load last cancelled session and pre-fill defaults
    # ------------------------------------------------------------------
    _resume_state: Optional[Dict[str, Any]] = None
    if getattr(args, 'resume', False):
        db_path = getattr(args, 'db_path', None) or 'data/duckdice_bot.db'
        try:
            from betbot_engine.bet_database import BetDatabase
            from pathlib import Path
            _db = BetDatabase(Path(db_path))
            _last = _db.get_last_cancelled_session()
            if not _last:
                print("⚠️  No cancelled session found in DB. Starting fresh.")
            else:
                import json as _json
                _tail = _db.get_session_tail_state(_last['session_id'])
                # Pre-fill args (only if not already explicitly set)
                if not args.strategy:
                    args.strategy = _last['strategy_name']
                if not args.currency:
                    args.currency = _last['symbol']
                if not args.mode and _last.get('simulation_mode') is not None:
                    args.mode = 'simulation' if _last['simulation_mode'] else 'live-main'
                # Load saved strategy params (CLI --param overrides apply later)
                if not args.profile and not args.params:
                    _saved_params = _last.get('strategy_params')
                    if _saved_params:
                        try:
                            _parsed = _json.loads(_saved_params) if isinstance(_saved_params, str) else _saved_params
                            args._resume_params = _parsed
                        except Exception:
                            args._resume_params = None
                # Restore limits (only if not explicitly provided)
                if args.stop_loss is None and _last.get('stop_loss') is not None:
                    args.stop_loss = _last['stop_loss']
                if args.take_profit is None and _last.get('take_profit') is not None:
                    args.take_profit = _last['take_profit']
                if args.max_bets is None and _last.get('max_bets') is not None:
                    args.max_bets = _last['max_bets']
                if args.max_losses is None and _last.get('max_losses') is not None:
                    args.max_losses = _last['max_losses']
                if args.max_duration is None and _last.get('max_duration_sec') is not None:
                    args.max_duration = _last['max_duration_sec']
                _resume_state = {
                    'resumed_from': _last['session_id'],
                    **_tail,
                }
                _ended_bal = _last.get('ending_balance') or _tail.get('last_balance', 0)
                print(f"\n♻️  Continuing cancelled session: {_last['session_id']}")
                print(f"   Strategy : {_last['strategy_name']}")
                print(f"   Currency : {_last['symbol']}")
                print(f"   Bal when stopped : {_ended_bal:.8f}")
                print(f"   Loss streak      : {_tail.get('loss_streak', '?')} (will restore)")
                print(f"   Bets done        : {_last.get('total_bets', '?')}")
                print()
        except Exception as _e:
            print(f"⚠️  Could not load last session ({_e}). Starting fresh.")

    # Check for API key first (auto-detect live mode)
    api_key = args.api_key or config_mgr.config.get('api_key')

    # Pre-fetch TLEs when we have an API key so we can show event names in the
    # mode menu AND reuse the data for TLE selection without a second round-trip.
    _prefetched_tles: list = []
    if api_key and not args.mode:
        try:
            _api_tmp = DuckDiceAPI(DuckDiceConfig(api_key=api_key))
            _prefetched_tles = _api_tmp.get_user_info().get('tle', []) or []
        except Exception:
            pass

    # Build mode choices — annotate live-tle with event names when available
    if _prefetched_tles:
        _tle_names = ', '.join(t.get('name', '?') for t in _prefetched_tles)
        _tle_label = f"live-tle  [{_tle_names}]"
    else:
        _tle_label = "live-tle"
    _mode_choices = ['simulation', 'live-main', 'live-faucet', _tle_label]

    # Resolve mode: explicit CLI flag > saved default with prompt > prompt
    if args.mode:
        mode = args.mode
    else:
        _saved_default = config_mgr.config.get('default_mode', 'live-main' if api_key else 'simulation')
        # Highlight live-tle as default when TLEs are active
        _default = _tle_label if _prefetched_tles else _saved_default
        mode = prompt_choice("Select betting mode:", _mode_choices, _default)
        # Normalise the annotated label back to the bare token
        if mode.startswith('live-tle'):
            mode = 'live-tle'

    # Parse mode flags
    is_simulation = (mode == 'simulation')
    use_faucet    = (mode == 'live-faucet')
    use_tle       = (mode == 'live-tle')

    # TLE mode: resolve hash (CLI flag > interactive selection from prefetched list)
    tle_hash = getattr(args, 'tle_hash', None)
    if use_tle and not is_simulation:
        if not tle_hash:
            # Use prefetched TLEs (or re-fetch if we skipped above via --mode flag)
            _tles = _prefetched_tles
            if not _tles:
                try:
                    _api_tmp = DuckDiceAPI(DuckDiceConfig(api_key=api_key))
                    _tles = _api_tmp.get_user_info().get('tle', []) or []
                except Exception:
                    _tles = []
            if _tles:
                if len(_tles) == 1:
                    # Only one event — auto-select, no menu needed
                    tle_hash = _tles[0].get('hash', '')
                    print(f"🏆 TLE auto-selected: {_tles[0].get('name', '')} (hash: {tle_hash})")
                else:
                    _tle_choices = [
                        f"{t.get('name', 'Unknown')} [{t.get('status', '')}]  (hash: {t.get('hash', '')})"
                        for t in _tles
                    ]
                    _choice = prompt_choice("Select TLE to bet in:", _tle_choices)
                    tle_hash = _tles[_tle_choices.index(_choice)].get('hash', '')
            else:
                print("⚠️  No active TLEs found on your account.")
                tle_hash = prompt_with_default("Enter TLE hash manually (or leave blank to cancel)", "")
                if not tle_hash:
                    print("Cancelled: no TLE hash provided.")
                    return
        else:
            print(f"🏆 TLE Mode — using hash: {tle_hash}")
    elif not use_tle and not is_simulation and _prefetched_tles:
        # Already showed TLE names in the mode menu; no extra output needed
        pass
    
    # Get currency
    currency = args.currency or prompt_with_default(
        "Currency",
        config_mgr.config.get('default_currency', 'btc')
    )
    
    # Get available strategies
    available_strategies_raw = list_strategies()
    available_strategies = [s['name'] if isinstance(s, dict) else s for s in available_strategies_raw]

    if not available_strategies:
        print("Error: No strategies available")
        return

    # Get strategy (with version selection and description if interactive)
    if args.strategy:
        strategy_name = _pick_strategy(preselected=args.strategy)
    else:
        strategy_name = _pick_strategy()

    if strategy_name not in available_strategies:
        print(f"Error: Unknown strategy '{strategy_name}'")
        print(f"Available strategies: {', '.join(available_strategies)}")
        return
    
    # Load profile or use defaults
    params = {}
    if args.profile:
        profile = config_mgr.get_profile(args.profile)
        if profile:
            params = profile['parameters']
            print(f"Loaded profile: {args.profile}")
        else:
            print(f"Warning: Profile '{args.profile}' not found, using defaults")
    elif hasattr(args, '_resume_params') and args._resume_params:
        # Restored from cancelled session DB record
        params = dict(args._resume_params)
        print(f"Restored strategy parameters from previous session")
    
    # Get strategy class for schema
    try:
        strategy_class = get_strategy(strategy_name)
        if hasattr(strategy_class, 'schema'):
            schema = strategy_class.schema()
            print(f"\nStrategy: {strategy_name}")
            if hasattr(strategy_class, 'describe'):
                print(f"Description: {strategy_class.describe()}")
            
            # Use defaults from schema if no profile
            if not params:
                for param_name, param_info in schema.items():
                    params[param_name] = param_info.get('default')
                
                # Override with command-line parameters if provided
                if args.params:
                    print(f"Applying custom parameters...")
                    for param_str in args.params:
                        if '=' in param_str:
                            key, value = param_str.split('=', 1)
                            # Type conversion based on schema
                            if key in schema:
                                param_type = schema[key].get('type', 'str')
                                try:
                                    if param_type == 'int':
                                        params[key] = int(value)
                                    elif param_type == 'float':
                                        params[key] = float(value)
                                    elif param_type == 'bool':
                                        params[key] = value.lower() in ('true', '1', 'yes', 'on')
                                    else:
                                        params[key] = value
                                    print(f"  {key} = {params[key]}")
                                except ValueError as e:
                                    print(f"  Warning: Invalid value for {key}: {e}")
                            else:
                                print(f"  Warning: Unknown parameter '{key}' for strategy '{strategy_name}'")
                else:
                    print(f"Using default parameters")
                
                # Interactive parameter configuration if requested
                if args.interactive_params:
                    print("\nConfigure parameters (press Enter for current value):")
                    for param_name, param_info in schema.items():
                        current = params.get(param_name, param_info.get('default'))
                        desc = param_info.get('desc', '')
                        new_value = prompt_with_default(f"{param_name} ({desc})", current)
                        
                        # Type conversion
                        param_type = param_info.get('type', 'str')
                        try:
                            if param_type == 'int':
                                params[param_name] = int(new_value)
                            elif param_type == 'float':
                                params[param_name] = float(new_value)
                            elif param_type == 'bool':
                                if isinstance(new_value, bool):
                                    params[param_name] = new_value
                                else:
                                    params[param_name] = str(new_value).lower() in ('true', '1', 'yes', 'on')
                            else:
                                params[param_name] = str(new_value)
                        except ValueError:
                            print(f"    Warning: Invalid value, using default")
                            params[param_name] = param_info.get('default')
    except Exception as e:
        print(f"Warning: Could not load strategy schema: {e}")
    
    # Get API key for live mode (already fetched above, but prompt if missing)
    if not is_simulation and not api_key:
        api_key = input("Enter API key: ").strip()
        if input("Save API key? (y/n): ").lower() == 'y':
            config_mgr.config['api_key'] = api_key
            config_mgr.save_config()
    
    # Get speed preset
    speed = getattr(args, 'speed', 'fast')
    delay_ms, jitter_ms = EngineConfig.get_speed_preset(speed)
    
    # Get parallel settings
    use_parallel = getattr(args, 'parallel', False)
    max_concurrent = getattr(args, 'max_concurrent', 5)
    
    # Create engine config
    config = EngineConfig(
        symbol=currency,
        dry_run=is_simulation,
        faucet=use_faucet,
        stop_loss=args.stop_loss if args.stop_loss is not None else -0.25,  # -25% recommended
        take_profit=args.take_profit if args.take_profit is not None else 1.0,  # +100%
        max_bets=args.max_bets,
        max_losses=args.max_losses,
        max_duration_sec=args.max_duration,
        delay_ms=delay_ms,
        jitter_ms=jitter_ms,
        db_log=getattr(args, 'db_log', True),
        db_path=getattr(args, 'db_path', None),
        tle_hash=tle_hash or None,
    )
    
    # Run strategy (faucet mode uses the auto-reclaim loop)
    if use_faucet and not is_simulation:
        # Resolve cookie: CLI arg → saved file → None
        faucet_cookie = getattr(args, 'faucet_cookie', None)
        if not faucet_cookie:
            try:
                from faucet_manager.cookie_manager import CookieManager as _CM
                faucet_cookie = _CM().get_cookie()
            except Exception:
                faucet_cookie = None
        if not faucet_cookie:
            print("⚠️  No faucet cookie found. Auto-reclaim disabled.")
            print("   Use --faucet-cookie or run interactive mode to save one.")
        _run_faucet_auto_loop(
            strategy_name, params, config, api_key,
            cookie=faucet_cookie,
            take_profit_target=args.take_profit if args.take_profit is not None else 1.0,
        )
    else:
        run_strategy(strategy_name, params, config, api_key, is_simulation,
                     use_parallel=use_parallel, max_concurrent=max_concurrent,
                     resume_state=_resume_state)


def cmd_list_strategies(args):
    """List all available strategies with enhanced display"""
    strategies = list_strategies()
    strategy_names = [s.get('name') if isinstance(s, dict) else s for s in strategies]
    
    if USE_RICH and display:
        display.print_section("Available Strategies")
        display.print_strategy_list(strategy_names)
        
        if args.verbose:
            display.print_info("Showing detailed parameter information...")
            for name in strategy_names:
                try:
                    strategy_class = get_strategy(name)
                    if hasattr(strategy_class, 'schema'):
                        print(f"\n[bold cyan]{name}[/bold cyan]")
                        schema = strategy_class.schema()
                        for param_name, param_info in schema.items():
                            default = param_info.get('default')
                            desc_param = param_info.get('desc', '')
                            param_type = param_info.get('type', 'str')
                            display.print_parameter_prompt(param_name, desc_param, default, param_type)
                except Exception:
                    pass
    else:
        print("\nAvailable Strategies:")
        print("=" * 60)
        for strategy_info in strategies:
            if isinstance(strategy_info, dict):
                name = strategy_info.get('name', 'unknown')
                desc = strategy_info.get('description', '')
                print(f"  • {name}")
                if desc:
                    print(f"    {desc}")
                
                # Show parameters if --verbose
                if args.verbose:
                    try:
                        strategy_class = get_strategy(name)
                        if hasattr(strategy_class, 'schema'):
                            schema = strategy_class.schema()
                            print(f"    Parameters:")
                            for param_name, param_info in schema.items():
                                default = param_info.get('default')
                                desc_param = param_info.get('desc', '')
                                print(f"      - {param_name}: {desc_param} (default: {default})")
                    except Exception:
                        pass
            else:
                print(f"  • {strategy_info}")
        print()


def cmd_show_strategy(args):
    """Show detailed information about a strategy"""
    strategy_name = args.strategy
    
    try:
        strategy_class = get_strategy(strategy_name)
        
        print(f"\n{'='*60}")
        print(f"Strategy: {strategy_name}")
        print(f"{'='*60}")
        
        if hasattr(strategy_class, 'describe'):
            print(f"\nDescription:")
            print(f"  {strategy_class.describe()}")
        
        if hasattr(strategy_class, 'metadata'):
            meta = strategy_class.metadata()
            print(f"\nMetadata:")
            print(f"  Risk Level: {meta.risk_level}")
            print(f"  Bankroll Required: {meta.bankroll_required}")
            print(f"  Volatility: {meta.volatility}")
            print(f"  Time to Profit: {meta.time_to_profit}")
            print(f"  Recommended For: {meta.recommended_for}")
            
            if meta.pros:
                print(f"\n  Pros:")
                for pro in meta.pros:
                    print(f"    + {pro}")
            
            if meta.cons:
                print(f"\n  Cons:")
                for con in meta.cons:
                    print(f"    - {con}")
            
            if hasattr(meta, 'best_use_case') and meta.best_use_case:
                print(f"\n  Best Use Case:")
                print(f"    {meta.best_use_case}")
            
            if hasattr(meta, 'tips') and meta.tips:
                print(f"\n  Tips:")
                for tip in meta.tips:
                    print(f"    💡 {tip}")
        
        if hasattr(strategy_class, 'schema'):
            schema = strategy_class.schema()
            print(f"\nParameters:")
            print(f"{'  Name':<20} {'Type':<10} {'Default':<15} Description")
            print(f"  {'-'*70}")
            for param_name, param_info in schema.items():
                param_type = param_info.get('type', 'str')
                default = str(param_info.get('default', ''))
                desc = param_info.get('desc', '')
                print(f"  {param_name:<20} {param_type:<10} {default:<15} {desc}")
        
        print(f"\nUsage Example:")
        print(f"  python3 duckdice_cli.py run -m simulation -s {strategy_name} \\")
        print(f"    -P base_amount=0.00001 -P chance=49.5 --max-bets 100")
        print()
        
    except Exception as e:
        print(f"Error: Strategy '{strategy_name}' not found or could not be loaded")
        print(f"Details: {e}")


def cmd_save_profile(args):
    """Save a strategy profile"""
    config_mgr = ConfigManager()
    strategies_raw = list_strategies()
    strategies = [s['name'] if isinstance(s, dict) else s for s in strategies_raw]
    
    name = args.name or input("Profile name: ").strip()
    strategy = args.strategy or prompt_choice("Strategy:", sorted(strategies))
    
    # Get strategy schema and collect parameters
    params = {}
    try:
        strategy_class = get_strategy(strategy)
        if hasattr(strategy_class, 'schema'):
            schema = strategy_class.schema()
            print("\nConfigure parameters (press Enter for default):")
            for param_name, param_info in schema.items():
                default = param_info.get('default')
                desc = param_info.get('desc', '')
                value = prompt_with_default(f"{param_name} ({desc})", default)
                params[param_name] = value
    except Exception as e:
        print(f"Warning: Could not load strategy schema: {e}")
    
    config_mgr.save_profile(name, strategy, params)
    print(f"✓ Profile '{name}' saved")


def cmd_list_profiles(args):
    """List saved profiles"""
    config_mgr = ConfigManager()
    profiles = config_mgr.list_profiles()
    
    if not profiles:
        print("No saved profiles")
        return
    
    print("\nSaved Profiles:")
    print("=" * 60)
    for name in sorted(profiles):
        profile = config_mgr.get_profile(name)
        print(f"  • {name}")
        print(f"    Strategy: {profile['strategy']}")
        print(f"    Created: {profile.get('created_at', 'unknown')}")
        if profile.get('parameters'):
            print(f"    Parameters: {len(profile['parameters'])} configured")
    print()


def cmd_config(args):
    """Configure default settings"""
    config_mgr = ConfigManager()
    
    print("\nCurrent Configuration:")
    print("=" * 60)
    for key, value in config_mgr.config.items():
        if key != 'api_key':
            print(f"  {key}: {value}")
        else:
            masked = value[:8] + '...' if value and len(value) > 8 else '(not set)'
            print(f"  {key}: {masked}")
    print()
    
    if args.set:
        key, value = args.set.split('=', 1)
        config_mgr.config[key] = value
        config_mgr.save_config()
        print(f"✓ Set {key} = {value}")


def cmd_probe_min_bets(args):
    """Probe the API to discover the minimum bet for every coin (except BTC).

    Places a 0.00000001 bet on each currency and reads the API error response to
    extract the actual minimum.  Results are written to data/min_bets.json so
    future sessions skip the initial too-small-bet retry.
    """
    from pathlib import Path
    from betbot_engine.min_bet_cache import probe_coin, load as _load_cache

    config_mgr = ConfigManager()
    api_key = getattr(args, "api_key", None) or config_mgr.config.get("api_key", "")
    if not api_key:
        api_key = input("Enter API key: ").strip()
        if not api_key:
            print("❌  API key required.")
            return

    from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
    api = DuckDiceAPI(DuckDiceConfig(api_key=api_key))

    try:
        currencies = api.get_available_currencies()
    except Exception as e:
        print(f"❌  Could not fetch currencies: {e}")
        return

    skip = {s.upper() for s in (getattr(args, "skip", None) or ["BTC"])}
    cache_path = Path(getattr(args, "output", None) or "data/min_bets.json")

    print(f"\nProbing minimum bets for {len(currencies)} currencies (skip: {', '.join(sorted(skip))})\n")
    width = max(len(c) for c in currencies)

    for symbol in sorted(currencies):
        if symbol.upper() in skip:
            cached = _load_cache(cache_path).get(symbol.upper(), "—")
            print(f"  {symbol.upper():<{width}}  skipped  (cached: {cached})")
            continue

        result = probe_coin(api, symbol, path=cache_path)
        if result is not None:
            print(f"  {symbol.upper():<{width}}  min = {result}")
        else:
            print(f"  {symbol.upper():<{width}}  ⚠  could not determine min bet")

    print(f"\n✅  Cache written to {cache_path}")
    print("\nDiscovered minimum bets:")
    print("-" * (width + 22))
    for sym, val in sorted(_load_cache(cache_path).items()):
        print(f"  {sym:<{width}}  {val}")


def cmd_interactive(args=None):
    """Full interactive mode - guided betting setup with balance checking"""
    
    if USE_RICH and display:
        display.print_banner()
        display.print_section("Interactive Setup")
        print("Welcome! Let's set up your betting session.\n")
    else:
        print("\n" + "="*60)
        print("🎲 DuckDice Bot - Interactive Mode")
        print("="*60)
        print("\nWelcome! Let's set up your betting session.\n")
    
    config_mgr = ConfigManager()

    is_simulation = False
    faucet_cookie: Optional[str] = None

    # ── Ask: main balance or faucet balance? ────────────────────────────
    print("\n⚙️  Choose balance type:")
    balance_type_choice = prompt_choice("", ["main", "faucet"], "main")
    use_faucet = (balance_type_choice == "faucet")

    if USE_RICH and display:
        display.print_info(f"Mode: Live ({'Faucet' if use_faucet else 'Main'} Balance)")
    else:
        print(f"ℹ️  Mode: Live ({'Faucet' if use_faucet else 'Main'} Balance)\n")

    # ── If faucet: load or prompt for browser cookie (needed for claiming) ─
    if use_faucet:
        try:
            from faucet_manager.cookie_manager import CookieManager as _CM
            _cm = _CM()
            faucet_cookie = _cm.get_cookie()
        except Exception:
            faucet_cookie = None

        if faucet_cookie:
            print(f"🍪  Faucet cookie loaded from saved config.\n")
        else:
            print("\n🍪  Auto-claiming requires your DuckDice browser session cookie.")
            print("    Log in at duckdice.io, then copy the full Cookie header value.")
            faucet_cookie = input("    Paste cookie (or press Enter to skip auto-claim): ").strip() or None
            if faucet_cookie:
                try:
                    from faucet_manager.cookie_manager import CookieManager as _CM2
                    _cm2 = _CM2()
                    save_cookie = input("    Save cookie for future sessions? (y/n) [y]: ").strip().lower()
                    if save_cookie != 'n':
                        _cm2.set_cookie(faucet_cookie)
                        _cm2.save()
                        print("    ✓ Cookie saved\n")
                except Exception:
                    pass
            else:
                print("    ⚠️  No cookie — faucet will NOT be auto-reclaimed on bust.\n")
    
    # Step 1: API Key (auto-detect, don't prompt if found)
    api_key = config_mgr.config.get('api_key')
    api = None
    
    if api_key:
        # API key found - use it silently
        if USE_RICH and display:
            display.print_success(f"API key detected: {api_key[:12]}...")
        else:
            print(f"✓ API key detected: {api_key[:12]}...\n")
    else:
        # No API key - must prompt
        if USE_RICH and display:
            display.print_step(1, "API Key Required", 5)
        else:
            print("Step 1: API Key Required")
            print("-" * 40)
        
        api_key = input("Enter your DuckDice API key: ").strip()
        if not api_key:
            if USE_RICH and display:
                display.print_error("API key required for live mode")
            else:
                print("✗ API key required for live mode")
            return
        
        # Save for future use
        save_key = input("Save this key? (y/n) [y]: ").strip().lower()
        if save_key != 'n':
            config_mgr.config['api_key'] = api_key
            config_mgr.save_config()
            if USE_RICH and display:
                display.print_success("API key saved")
            else:
                print("✓ API key saved")
    
    # Connect to API
    try:
        from duckdice_api.api import DuckDiceAPI, DuckDiceConfig
        api = DuckDiceAPI(DuckDiceConfig(api_key=api_key))
        if USE_RICH and display:
            display.print_success("Connected to DuckDice")
        else:
            print("✓ Connected to DuckDice\n")
    except Exception as e:
        if USE_RICH and display:
            display.print_error(f"Failed to connect: {e}")
        else:
            print(f"✗ Failed to connect: {e}")
        return
    
    # Step 2: Get balances and filter currencies
    available_currencies = []
    balances_dict = {}
    
    # Live mode - fetch balances and filter
    if USE_RICH and display:
        display.print_step(2, "Select Currency", 5)
        display.print_info("Fetching your balances...")
    else:
        print("\nStep 2: Select Currency")
        print("-" * 40)
        print("Fetching your balances...")
    
    try:
        user_info = api.get_user_info()
        balances = user_info.get('balances', [])
        
        # Minimum bet amounts (approximate)
        min_bets = {
            'btc': 0.00000001,
            'eth': 0.000001,
            'ltc': 0.0001,
            'doge': 0.1,
            'bch': 0.00001,
            'trx': 1.0
        }
        
        # Filter currencies with sufficient balance
        balance_type = 'faucet' if use_faucet else 'main'
        for bal in balances:
            curr = bal['currency'].lower()
            amount = float(bal.get(balance_type, 0))
            min_bet = min_bets.get(curr, 0)
            
            if amount > min_bet:
                available_currencies.append(curr)
                balances_dict[curr] = amount
        
        if not available_currencies:
            if USE_RICH and display:
                display.print_error(f"No currencies with sufficient {balance_type} balance")
            else:
                print(f"✗ No currencies with sufficient {balance_type} balance")
            return
        
        print(f"\nAvailable currencies ({balance_type} balance):")
        for i, curr in enumerate(available_currencies, 1):
            balance = balances_dict[curr]
            print(f"  {i}. {curr.upper():<6} - Balance: {balance:.8f}")
        
        currency = prompt_choice("", available_currencies, available_currencies[0])
        initial_balance = balances_dict[currency]
        
        if USE_RICH and display:
            display.print_success(f"Selected: {currency.upper()} (Balance: {initial_balance:.8f})")
        else:
            print(f"✓ Selected: {currency.upper()} (Balance: {initial_balance:.8f})\n")
        
    except Exception as e:
        if USE_RICH and display:
            display.print_error(f"Failed to fetch balances: {e}")
        else:
            print(f"✗ Failed to fetch balances: {e}")
        return
    
    
    # Step 3: Choose strategy
    if USE_RICH and display:
        display.print_step(3, "Select Strategy", 5)
    else:
        print(f"\nStep 3: Select Strategy")
        print("-" * 40)

    available_strategies_raw = list_strategies()
    all_names = [s['name'] for s in available_strategies_raw]
    # Show only base names (no @vN variants) in the grouped/numbered list
    base_strategy_names = sorted(set(n.split('@')[0] for n in all_names))

    if USE_RICH and display:
        display.print_strategy_list(base_strategy_names)
    else:
        # Group strategies by risk level
        print("\n🟢 Conservative (Low Risk):")
        conservative = ['dalembert', 'oscars-grind', 'one-three-two-six']
        for s in [s for s in base_strategy_names if s in conservative]:
            print(f"  • {s}")

        print("\n🟡 Moderate (Medium Risk):")
        moderate = ['fibonacci', 'labouchere', 'paroli', 'fib-loss-cluster']
        for s in [s for s in base_strategy_names if s in moderate]:
            print(f"  • {s}")

        print("\n🔴 Aggressive (High Risk):")
        aggressive = ['classic-martingale', 'anti-martingale-streak', 'streak-hunter']
        for s in [s for s in base_strategy_names if s in aggressive]:
            print(f"  • {s}")

        print("\n🔵 Specialized:")
        specialized = ['faucet-grind', 'faucet-cashout', 'kelly-capped', 'target-aware',
                       'rng-analysis-strategy', 'range-50-random', 'max-wager-flow', 'custom-script']
        for s in [s for s in base_strategy_names if s in specialized]:
            print(f"  • {s}")

    print("\nFull list:")
    for i, s in enumerate(base_strategy_names, 1):
        if i % 3 == 1:
            print(f"  {i:2}. {s:<25}", end="")
        elif i % 3 == 2:
            print(f"{i:2}. {s:<25}", end="")
        else:
            print(f"{i:2}. {s}")
    if len(base_strategy_names) % 3 != 0:
        print()

    strategy_name = _pick_strategy()
    if USE_RICH and display:
        display.print_success(f"Selected: {strategy_name}")
    else:
        print(f"✓ Selected: {strategy_name}\n")
    
    # Step 4: Set target balance
    if USE_RICH and display:
        display.print_step(4, "Set Target", 5)
    else:
        print(f"\nStep 4: Set Target")
        print("-" * 40)
    
    print(f"Current balance: {initial_balance:.8f} {currency.upper()}")
    print("Set your target balance to reach (or 0 to bet until strategy exits)\n")
    
    target_balance = prompt_with_default(
        "Target balance",
        str(initial_balance * 2),  # Default: double your balance
        float
    )
    
    if target_balance > 0:
        profit_needed = target_balance - initial_balance
        profit_percent = (profit_needed / initial_balance) * 100
        if USE_RICH and display:
            display.print_success(
                f"Target: {target_balance:.8f} {currency.upper()} "
                f"(+{profit_percent:.1f}%)"
            )
        else:
            print(f"✓ Target: {target_balance:.8f} {currency.upper()} (+{profit_percent:.1f}%)\n")
    else:
        if USE_RICH and display:
            display.print_info("No target set - will run until strategy exits")
        else:
            print("✓ No target set - will run until strategy exits\n")
    
    # Step 5: Configure strategy parameters
    if USE_RICH and display:
        display.print_step(5, "Configure Strategy", 5)
    else:
        print(f"\nStep 5: Configure Strategy")
        print("-" * 40)
    
    params = {}
    profiles = config_mgr.list_profiles()
    
    if profiles:
        print("Available profiles:")
        for i, profile in enumerate(profiles, 1):
            p = config_mgr.get_profile(profile)
            print(f"  {i}. {profile} ({p['strategy']})")
        
        use_profile = input("\nUse a saved profile? (y/n) [n]: ").strip().lower()
        if use_profile == 'y':
            profile_name = prompt_choice("Select profile:", profiles)
            profile = config_mgr.get_profile(profile_name)
            params = profile['parameters']
            if USE_RICH and display:
                display.print_success(f"Loaded profile: {profile_name}")
            else:
                print(f"✓ Loaded profile: {profile_name}\n")
    
    # Configure parameters if not from profile
    if not params:
        try:
            strategy_class = get_strategy(strategy_name)
            if hasattr(strategy_class, 'schema'):
                schema = strategy_class.schema()
                
                # Ask if user wants to configure parameters
                configure = input("\nConfigure strategy parameters? (y/n) [n]: ").strip().lower()
                
                if configure == 'y':
                    print(f"Configure {strategy_name} parameters:")
                    print("(Press Enter to use default values)\n")
                    
                    for param_name, param_info in schema.items():
                        default = param_info.get('default')
                        desc = param_info.get('desc', '')
                        param_type = param_info.get('type', 'str')
                        
                        # Get type conversion function
                        type_func = str
                        if param_type == 'int':
                            type_func = int
                        elif param_type == 'float':
                            type_func = float
                        elif param_type == 'bool':
                            type_func = bool
                        
                        value = prompt_with_default(f"  {param_name} ({desc})", default, type_func)
                        
                        # Special handling for bool
                        if param_type == 'bool' and not isinstance(value, bool):
                            params[param_name] = str(value).lower() in ('true', '1', 'yes', 'on')
                        else:
                            params[param_name] = value
                    
                    print()
                    
                    # Ask if user wants to save as profile
                    save_profile = input("Save these settings as a profile? (y/n) [n]: ").strip().lower()
                    if save_profile == 'y':
                        profile_name = input("Profile name: ").strip()
                        if profile_name:
                            config_mgr.save_profile(profile_name, strategy_name, params)
                            if USE_RICH and display:
                                display.print_success(f"Saved profile: {profile_name}")
                            else:
                                print(f"✓ Saved profile: {profile_name}\n")
                else:
                    # Use all defaults
                    params = {}
                    if USE_RICH and display:
                        display.print_info("Using default parameters")
                    else:
                        print("✓ Using default parameters\n")
            else:
                # Use defaults
                params = {}
        except Exception as e:
            print(f"Warning: Could not load strategy schema: {e}")
            params = {}
    
    # Summary
    if USE_RICH and display:
        print()
        summary_data = {
            'Mode': 'Simulation' if is_simulation else f"Live ({'Faucet' if use_faucet else 'Main'})",
            'Currency': currency.upper(),
            'Current Balance': f"{initial_balance:.8f}",
            'Strategy': strategy_name,
        }
        
        if target_balance > 0:
            summary_data['Target Balance'] = f"{target_balance:.8f}"
            summary_data['Profit Needed'] = f"+{profit_needed:.8f} (+{profit_percent:.1f}%)"
        else:
            summary_data['Target'] = 'Run until strategy exits'
        
        if params:
            summary_data['Parameters'] = f"{len(params)} configured"
        
        display.print_session_summary(summary_data)
    else:
        print("\n" + "="*60)
        print("📋 SESSION SUMMARY")
        print("="*60)
        # Nested f-strings not supported in Python 3.9
        mode_str = 'Simulation' if is_simulation else ('Live (Faucet)' if use_faucet else 'Live (Main)')
        print(f"Mode:             {mode_str}")
        print(f"Currency:         {currency.upper()}")
        print(f"Current Balance:  {initial_balance:.8f}")
        print(f"Strategy:         {strategy_name}")
        if target_balance > 0:
            print(f"Target Balance:   {target_balance:.8f}")
            print(f"Profit Needed:    +{profit_needed:.8f} (+{profit_percent:.1f}%)")
        else:
            print(f"Target:           Run until strategy exits")
        if params:
            print(f"Parameters:       {len(params)} configured")
        print("="*60)
    
    # Display equivalent CLI command
    print("\n💡 Equivalent CLI command:")
    print("-" * 60)
    
    # Build the command
    mode = 'live-main' if not is_simulation else ('live-faucet' if use_faucet else 'simulation')
    cmd_parts = [
        "duckdice run",
        f"-m {mode}",
        f"-c {currency}",
        f"-s {strategy_name}"
    ]
    
    # Add take profit if set
    if target_balance > 0:
        take_profit_pct = ((target_balance - initial_balance) / initial_balance)
        cmd_parts.append(f"--take-profit {take_profit_pct:.4f}")
    
    # Add parameters if configured
    if params:
        for key, value in params.items():
            cmd_parts.append(f"-P {key}={value}")
    
    cli_command = " \\\n  ".join(cmd_parts)
    print(f"\n  {cli_command}\n")
    print("-" * 60)
    
    # Confirmation
    confirm = input("\nReady to start? (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        if USE_RICH and display:
            display.print_warning("Cancelled")
        else:
            print("❌ Cancelled")
        return
    
    # Calculate take_profit from target
    if target_balance > 0:
        take_profit = (target_balance - initial_balance) / initial_balance
    else:
        take_profit = None  # No profit target
    
    # Start live session
    if USE_RICH and display:
        display.print_success("Starting LIVE session...")
    else:
        print("\n🚀 Starting LIVE session...\n")
    
    # Create engine config for actual run
    config = EngineConfig(
        symbol=currency,
        dry_run=is_simulation,
        faucet=use_faucet if not is_simulation else False,
        stop_loss=-0.99,  # Allow 99% loss before stopping (essentially no stop loss)
        take_profit=take_profit,
        max_bets=None,  # Run until target or strategy exits
        max_losses=None,
        delay_ms=50,    # Ultra-fast betting: 50ms delay
        jitter_ms=25    # Minimal jitter: 25ms
    )
    
    # Run strategy (faucet mode uses the auto-reclaim loop)
    if use_faucet and not is_simulation:
        _run_faucet_auto_loop(
            strategy_name, params, config, api_key,
            cookie=faucet_cookie,
            take_profit_target=take_profit if take_profit else 1.0,
        )
    else:
        run_strategy(strategy_name, params, config, api_key, is_simulation)


def cmd_simulate(args):
    """Monte Carlo simulation of a strategy without real funds."""
    import json
    from src.betbot_engine.monte_carlo import MonteCarloEngine
    from betbot_engine.visualization import (
        generate_html_report, plot_equity_curve, plot_comparison_bars,
        plot_drawdown_analysis, plot_risk_return_scatter
    )
    from betbot_strategies import get_strategy
    
    # Get strategy name
    strategy_name = args.strategy
    if not strategy_name:
        strategies = [s['name'] for s in list_strategies()]
        strategy_name = prompt_choice('Select strategy', strategies)
    
    # Parse config
    config = {}
    if args.config:
        try:
            config = json.loads(args.config)
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON config: {args.config}")
            return
    elif args.interactive_params:
        print("\n📝 Configure strategy parameters:")
        try:
            strat_cls = get_strategy(strategy_name)
            schema = strat_cls.schema() if hasattr(strat_cls, 'schema') else {}
            for key, info in schema.items():
                default = info.get('default', '')
                val_type = info.get('type', 'str')
                prompt_str = f"  {key} ({val_type}) [{default}]: "
                user_val = input(prompt_str).strip()
                if user_val:
                    if val_type == 'int':
                        config[key] = int(user_val)
                    elif val_type == 'float':
                        config[key] = float(user_val)
                    elif val_type == 'bool':
                        config[key] = user_val.lower() in ('true', 'yes', '1')
                    else:
                        config[key] = user_val
                elif default:
                    config[key] = default
        except Exception as e:
            print(f"⚠️ Error configuring parameters: {e}")
    
    # Simulation parameters
    rounds = args.rounds or 1000
    balance = float(args.balance or 100.0)
    
    print(f"\n🎲 Starting Monte Carlo simulation...")
    print(f"   Strategy: {strategy_name}")
    print(f"   Rounds: {rounds:,}")
    print(f"   Starting Balance: ${balance:.2f}")
    print(f"   Config: {config}")
    print()
    
    # Run simulation
    try:
        engine = MonteCarloEngine()
        result = engine.simulate(
            strategy_class=get_strategy(strategy_name),
            config=config,
            rounds=rounds,
            starting_balance=balance,
            fast_mode=True,
        )
        
        # Display results
        print(result.summary())
        print()
        
        # Generate report if requested
        if args.report:
            try:
                generate_html_report(
                    [result],
                    [strategy_name],
                    save_path=args.report,
                )
                print(f"✅ Report saved to: {args.report}")
            except ImportError:
                print("⚠️ matplotlib/seaborn required for reports. Install: pip install matplotlib seaborn")
        
        # Generate plots if requested
        if args.plots:
            try:
                plot_equity_curve([result], [strategy_name], 
                                save_path=f"{args.plots}_equity.png")
                plot_drawdown_analysis(result, 
                                      save_path=f"{args.plots}_drawdown.png")
                print(f"✅ Plots saved to: {args.plots}_*.png")
            except ImportError:
                print("⚠️ matplotlib required for plots. Install: pip install matplotlib seaborn")
        
    except Exception as e:
        print(f"❌ Simulation error: {e}")
        import traceback
        traceback.print_exc()


def cmd_simulate_all(args):
    """Monte Carlo simulation of all strategies → comprehensive HTML report."""
    import sys
    from betbot_engine.strategy_simulator import simulate_strategy, default_params
    from betbot_engine.html_report import build_report
    from betbot_strategies import list_strategies, get_strategy

    rounds   = args.rounds
    n_runs   = args.runs
    balance  = args.balance
    output   = args.output
    seed     = args.seed
    exclude  = {e.lower() for e in (args.exclude or [])}

    all_names = [s["name"] for s in list_strategies()]
    if args.strategies:
        names = [n for n in args.strategies if n in all_names]
        missing = [n for n in args.strategies if n not in all_names]
        if missing:
            print(f"⚠️  Unknown strategies (skipped): {', '.join(missing)}")
    else:
        names = [n for n in all_names if n.lower() not in exclude]

    if not names:
        print("❌ No strategies to simulate.")
        return

    print(f"\n🦆  DuckDice Monte Carlo — All Strategy Report")
    print(f"   Strategies  : {len(names)}")
    print(f"   Runs/strategy: {n_runs}")
    print(f"   Bets/run     : {rounds}")
    print(f"   Start balance: ${balance:.2f}")
    print(f"   Seed         : {seed}")
    print(f"   Output       : {output}\n")

    results = []
    for idx, name in enumerate(names):
        try:
            cls = get_strategy(name)
            params = default_params(cls)
        except Exception as e:
            print(f"  [{idx+1:2d}/{len(names)}] {name:<35s} ⚠️  load error: {e}")
            continue

        # Progress bar
        bar_width = 20

        def progress(run_i: int, total: int):
            filled = int(bar_width * run_i / max(total, 1))
            bar = "█" * filled + "░" * (bar_width - filled)
            pct = int(run_i / max(total, 1) * 100)
            print(f"\r  [{idx+1:2d}/{len(names)}] {name:<35s} [{bar}] {pct:3d}%",
                  end="", flush=True)

        progress(0, n_runs)
        try:
            result = simulate_strategy(
                cls,
                params,
                n_bets=rounds,
                n_runs=n_runs,
                starting_balance=balance,
                base_seed=seed,
                progress_cb=progress,
            )
            results.append(result)
            roi_str = f"{result.roi_mean:+.2f}%"
            dd_str  = f"dd={result.max_drawdown_mean:.1%}"
            print(f"\r  [{idx+1:2d}/{len(names)}] {name:<35s} ✅  roi={roi_str:<10} {dd_str}")
        except Exception as e:
            print(f"\r  [{idx+1:2d}/{len(names)}] {name:<35s} ❌  {e}")

    if not results:
        print("\n❌ All simulations failed — no report generated.")
        return

    print(f"\n📝 Building HTML report ({len(results)} strategies)…")
    try:
        path = build_report(results, output_path=output)
        print(f"✅  Report saved → {path}")
        print(f"   Open in browser: file://{os.path.abspath(path)}")
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="DuckDice Bot CLI - Automated betting toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments for interactive mode."
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Interactive mode
    interactive_parser = subparsers.add_parser('interactive', 
                                               help='Full interactive setup (guided)')
    interactive_parser.set_defaults(func=cmd_interactive)
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a betting strategy')
    run_parser.add_argument('-m', '--mode', choices=['simulation', 'live-main', 'live-faucet', 'live-tle'],
                           help='Betting mode (live-tle requires --tle <hash> or interactive TLE selection)')
    run_parser.add_argument('-c', '--currency', help='Currency (btc, doge, etc.)')
    run_parser.add_argument('-s', '--strategy', help='Strategy name')
    run_parser.add_argument('-p', '--profile', help='Load strategy profile')
    run_parser.add_argument('-b', '--balance', help='Initial balance (simulation only)')
    run_parser.add_argument('-k', '--api-key', help='API key (live mode)')
    run_parser.add_argument('--stop-loss', type=float, help='Stop loss percentage (e.g., -0.25 for -25%%, default: -0.25)')
    run_parser.add_argument('--take-profit', type=float, help='Take profit percentage (e.g., 1.0 for +100%%, default: +100%%)')
    run_parser.add_argument('--max-bets', type=int, help='Maximum number of bets')
    run_parser.add_argument('--max-losses', type=int, help='Maximum consecutive losses')
    run_parser.add_argument('--max-duration', type=int, help='Maximum duration in seconds')
    run_parser.add_argument('--speed', type=str, choices=['ultra', 'turbo', 'fast', 'normal', 'slow'],
                           default='fast', help='Betting speed preset (default: fast ~16 bets/sec). '
                           'ultra=~80/s, turbo=~30/s, fast=~16/s, normal=~5/s, slow=~1.5/s')
    run_parser.add_argument('--parallel', action='store_true',
                           help='Enable parallel betting mode (multiple concurrent API requests)')
    run_parser.add_argument('--max-concurrent', type=int, default=5,
                           help='Maximum concurrent bets in parallel mode (default: 5)')
    run_parser.add_argument('--param', '-P', dest='params', action='append',
                           help='Strategy parameter (key=value). Can be used multiple times. '
                                'Example: -P base_amount=0.00001 -P chance=49.5 -P multiplier=2')
    run_parser.add_argument('--interactive-params', '-I', action='store_true',
                           help='Interactively configure strategy parameters')
    run_parser.add_argument('--db-log', action='store_true', default=True,
                           help='Enable database logging (default: enabled)')
    run_parser.add_argument('--no-db-log', action='store_false', dest='db_log',
                           help='Disable database logging')
    run_parser.add_argument('--db-path', type=str,
                           help='Custom database path (default: data/duckdice_bot.db)')
    run_parser.add_argument('--continue', '-C', action='store_true', dest='resume',
                           help='Continue the last cancelled session (restores strategy, params, limits, and state)')
    run_parser.add_argument('--faucet-cookie', type=str, dest='faucet_cookie',
                           help='Browser session cookie for faucet auto-claim (live-faucet mode). '
                                'If omitted, uses cookie saved in ~/.duckdice/faucet_cookies.json')
    run_parser.add_argument('--tle', type=str, dest='tle_hash', default=None,
                           help='Time Limited Event hash to participate in (live mode only). '
                                'Use the hash shown when listing active TLEs on startup.')
    run_parser.set_defaults(func=cmd_run)
    
    # List strategies
    list_parser = subparsers.add_parser('strategies', help='List available strategies')
    list_parser.add_argument('-v', '--verbose', action='store_true',
                            help='Show detailed parameter information')
    list_parser.set_defaults(func=cmd_list_strategies)
    
    # Show strategy details
    show_parser = subparsers.add_parser('show', help='Show detailed strategy information')
    show_parser.add_argument('strategy', help='Strategy name')
    show_parser.set_defaults(func=cmd_show_strategy)
    
    # Save profile
    save_parser = subparsers.add_parser('save-profile', help='Save a strategy profile')
    save_parser.add_argument('name', nargs='?', help='Profile name')
    save_parser.add_argument('-s', '--strategy', help='Strategy name')
    save_parser.set_defaults(func=cmd_save_profile)
    
    # List profiles
    profiles_parser = subparsers.add_parser('profiles', help='List saved profiles')
    profiles_parser.set_defaults(func=cmd_list_profiles)
    
    # Config
    config_parser = subparsers.add_parser('config', help='Configure settings')
    config_parser.add_argument('--set', help='Set config value (key=value)')
    config_parser.set_defaults(func=cmd_config)
    
    # Monte Carlo simulation
    sim_parser = subparsers.add_parser('simulate', help='Monte Carlo simulation of a strategy')
    sim_parser.add_argument('-s', '--strategy', help='Strategy name')
    sim_parser.add_argument('-c', '--config', help='Strategy config as JSON')
    sim_parser.add_argument('-r', '--rounds', type=int, help='Number of simulation rounds (default: 1000)')
    sim_parser.add_argument('-b', '--balance', help='Starting balance (default: 100.0)')
    sim_parser.add_argument('-I', '--interactive-params', action='store_true',
                           help='Interactively configure parameters')
    sim_parser.add_argument('--report', help='Save HTML report to path')
    sim_parser.add_argument('--plots', help='Save plots to path prefix')
    sim_parser.set_defaults(func=cmd_simulate)

    # Monte Carlo all-strategies report
    sim_all_parser = subparsers.add_parser(
        'simulate-all',
        help='Monte Carlo simulation of ALL strategies — produces HTML report',
    )
    sim_all_parser.add_argument(
        '--rounds', type=int, default=500,
        help='Bets per simulation run (default: 500)',
    )
    sim_all_parser.add_argument(
        '--runs', type=int, default=30,
        help='Monte Carlo runs per strategy (default: 30)',
    )
    sim_all_parser.add_argument(
        '--balance', type=float, default=100.0,
        help='Starting balance (default: 100.0)',
    )
    sim_all_parser.add_argument(
        '--output', default='simulation_report.html',
        help='Output HTML file path (default: simulation_report.html)',
    )
    sim_all_parser.add_argument(
        '--strategies', nargs='+', metavar='NAME',
        help='Only simulate these strategies (default: all)',
    )
    sim_all_parser.add_argument(
        '--exclude', nargs='+', metavar='NAME', default=[],
        help='Strategies to skip',
    )
    sim_all_parser.add_argument(
        '--seed', type=int, default=42,
        help='Base random seed for reproducibility (default: 42)',
    )
    sim_all_parser.set_defaults(func=cmd_simulate_all)

    # Probe minimum bets
    probe_parser = subparsers.add_parser(
        'probe-min-bets',
        help='Probe API to discover minimum bet per coin and cache results',
    )
    probe_parser.add_argument('-k', '--api-key', dest='api_key', help='API key')
    probe_parser.add_argument(
        '--skip', nargs='+', default=['BTC'],
        metavar='COIN',
        help='Coins to skip (default: BTC)',
    )
    probe_parser.add_argument(
        '--output', default='data/min_bets.json',
        metavar='FILE',
        help='Output cache file (default: data/min_bets.json)',
    )
    probe_parser.set_defaults(func=cmd_probe_min_bets)
    
    args = parser.parse_args()
    
    # If no command provided, run interactive mode
    if not args.command:
        cmd_interactive()
        return
    
    args.func(args)


if __name__ == '__main__':
    # Print banner if rich is available
    if USE_RICH and display:
        display.print_banner()
    main()
