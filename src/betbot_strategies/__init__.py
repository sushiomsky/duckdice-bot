"""
Strategy plugin registry for auto-betting.

Usage:
  from betbot_strategies import register, get_strategy, list_strategies

A strategy module should import `register` and decorate a concrete class
implementing the `AutoBetStrategy` protocol in `base.py`.
"""
from __future__ import annotations
from typing import Callable, Dict, List, Type

_registry: Dict[str, Type] = {}


def register(name: str) -> Callable[[Type], Type]:
    """Class decorator to register a strategy under a name.

    Example:
        @register("anti-martingale-streak")
        class AntiMartingaleStreak(AutoBetStrategy):
            ...
    """
    def deco(cls: Type) -> Type:
        key = name.strip().lower()
        if key in _registry:
            # Allow re-registration of the same class in hot-reload scenarios
            if _registry[key] is not cls:
                raise ValueError(f"Strategy name already registered: {name}")
        _registry[key] = cls
        setattr(cls, "_strategy_name", key)
        return cls

    return deco


def get_strategy(name: str) -> Type:
    key = (name or "").strip().lower()
    if key not in _registry:
        raise KeyError(f"Unknown strategy: {name}. Available: {', '.join(sorted(_registry))}")
    return _registry[key]


def list_strategies() -> List[Dict[str, str]]:
    """Return list of strategies with names and optional descriptions.
    Each class may provide `describe()` classmethod.
    """
    items: List[Dict[str, str]] = []
    for name, cls in sorted(_registry.items()):
        desc = ""
        if hasattr(cls, "describe") and callable(getattr(cls, "describe")):
            try:
                desc = cls.describe()  # type: ignore[attr-defined]
            except Exception:
                desc = ""
        items.append({"name": name, "description": desc or getattr(cls, "__doc__", "").strip()})
    return items

# Import all strategy modules to trigger registration
from . import (
    # Unified consolidated strategies
    adaptive_hunter,             # CONSOLIDATED: 12 hunter variants
    unified_progression,         # CONSOLIDATED: fibonacci, dalembert, labouchere
    unified_martingale,          # CONSOLIDATED: classic_martingale, anti_martingale_streak
    unified_faucet,              # CONSOLIDATED: faucet_cashout, faucet_grind

    # Classic progression strategies
    paroli,                      # Paroli: reverse martingale (double on wins)
    oscars_grind,                # Oscar's Grind: conservative +1 unit on win
    one_three_two_six,           # 1-3-2-6: fixed sequence positive progression
    kelly_capped,                # Kelly Criterion: EWMA-based fractional Kelly sizing

    # Adaptive / state-machine strategies
    adaptive_survival,           # Meta-strategy with adaptive pattern detection
    target_aware,                # State machine: SAFE/BUILD/STRIKE/FINISH
    oracle_engine,               # Oracle Engine: 19-mode adaptive state machine
    chance_cycle_multiplier,     # 2-phase aggressive/recovery cycling
    simple_progression_40,       # 40% chance win progression with decreasing multiplier

    # Wager / TLE strategies
    tle_wager_farming,           # TLE Wager Farming: micro-Paroli for event rewards
    wager_loop_stabilizer_v2,    # WLS V2: zone-based survival wager stabilizer
    wager_sprint,                # Wager Sprint: high-throughput Paroli boost

    # Lottery / contest strategies
    dice_out_002,                # 0.02% range sniper: 2-slot window, ~4950× payout
    lottery_sniper,              # Lottery Sniper: 1% hunt → 10 lottery bursts at 0.1%
    ladder_race,                 # Ladder Race: contest hunter 5x→10x→50x→100x
    roll_hunt,                   # Roll Hunt: contest strategy targeting 9990-9999
    roll_hunt_low,               # Roll Hunt Low: 15% LOW contest targeting 0-4
    balance_sweep_sniper,        # Balance Sweep Sniper: multi-coin dust sweeper

    # Aggressive / high-roller strategies
    ai_strat,                    # AI Strategy: 30+ ML models ensemble
    combined_high_roller,        # Combined High-Roller: Kelly / Streak / Volatility modes
    profit_cascade,              # Profit Cascade: 12-tier dynamic profit targeting
    streak_multiplier,           # Exponential growth on win streaks

    # Meta-strategies
    master,                      # Master: meta-strategy cycling sub-strategies across 3 tiers
    custom_script,               # Custom Script: user-defined strategy executor
    adaptive_hunt,               # Multi-strategy subsystem: low-chance hunt phase
    wager_grinder,               # Multi-strategy subsystem: wager-focused phase
    recovery,                    # Multi-strategy subsystem: high-chance recovery phase
    multi_strategy_system,       # Wrapper that auto-switches between the phases
)

# DEPRECATED (consolidated into unified_* above):
# - classic_martingale → unified_martingale
# - anti_martingale_streak → unified_martingale
# - fibonacci, dalembert, labouchere → unified_progression
# - faucet_cashout, faucet_grind → unified_faucet
# - 12 hunter variants → adaptive_hunter
#
# REMOVED (bad/redundant strategies):
# - blaks_runner (dangerous Martingale variant)
# - max_wager_flow (mathematically unsound)
# - progressive_win_scaling (96% loss on first bet)
# - range_decoy_ramp (poor lottery variant)
# - cold_chaos_50 (chaos entertainment, no edge)
# - unified_exponential (impossible 100-300× targets)
# - nano_range_hunter + versions (extreme lottery)
# - range50_random (redundant 50% approach)
# - fib_loss_cluster (redundant with unified_progression Fibonacci)
# - chance_descent (mathematically incoherent)
# - rng_analysis_strategy (educational only)
# - luck_cascade (luck% not predictive)

# Load all versioned strategy snapshots (registers as "strategy-name@vN")
from . import versions
