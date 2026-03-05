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
        # Fallback for nano-range-hunter (default to @v1)
        if key == "nano-range-hunter" and "nano-range-hunter@v1" in _registry:
            key = "nano-range-hunter@v1"
        else:
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
    # Unified consolidated strategies (replace 12 originals)
    adaptive_hunter,             # CONSOLIDATED: 12 hunter variants
    unified_progression,         # CONSOLIDATED: fibonacci, dalembert, labouchere
    unified_martingale,          # CONSOLIDATED: classic_martingale, anti_martingale_streak
    unified_exponential,         # CONSOLIDATED: micro_exponential, micro_exponential_safe
    unified_faucet,              # CONSOLIDATED: faucet_cashout, faucet_grind
    
    # Other strategies (non-consolidated)
    paroli,
    oscars_grind,
    one_three_two_six,
    rng_analysis_strategy,
    target_aware,
    kelly_capped,
    max_wager_flow,
    range50_random,
    fib_loss_cluster,
    custom_script,
    progressive_win_scaling,
    streak_multiplier,  # Exponential growth on win streaks
    adaptive_survival,  # Meta-strategy with adaptive pattern detection
    simple_progression_40,  # Simple 40% chance win progression
    dice_out_002,                # 0.02% range sniper: 2-slot window, ~4950× payout
    blaks_runner,                # BlaksRunner 5.0: adaptive chance + loss-recovery auto-tuning
    luck_cascade,                # Luck Cascade: descend lower-chance tiers while luck% > 100%
    chance_descent,              # Chance Descent: win-driven chance compression, reset on loss
    nano_range_hunter,           # Range dice multi-variant strategy (versions v1, v3)
    ai_strat,                    # AI Strategy: 30+ ML models ensemble
)

# DEPRECATED (consolidated into unified_* above):
# - classic_martingale → unified_martingale
# - anti_martingale_streak → unified_martingale
# - fibonacci, dalembert, labouchere → unified_progression
# - micro_exponential, micro_exponential_safe → unified_exponential
# - faucet_cashout, faucet_grind → unified_faucet
# - cold_number_hunter, streak_hunter, spike_hunter, volatility_spike_hunter,
#   nano_hunter, dynamic_phase_hunter, gradient_range_hunter,
#   adaptive_volatility_hunter, regime_hunter, low_hunter, nano_range_hunter,
#   streak_pressure_hunter → adaptive_hunter
# These files are archived in ./deprecated/ for reference

# Load all versioned strategy snapshots (registers as "strategy-name@vN")
from . import versions
