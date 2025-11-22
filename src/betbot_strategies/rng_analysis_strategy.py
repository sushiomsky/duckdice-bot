from __future__ import annotations
"""
RNG Analysis Strategy
Uses insights from RNG analysis to inform betting decisions.

⚠️ EDUCATIONAL PURPOSE ONLY
This strategy demonstrates integration with RNG analysis but:
- Cryptographic RNG is unpredictable by design
- Past patterns don't predict future outcomes
- The house edge ensures long-term losses
- Only use for learning, not real betting
"""
from typing import Any, Dict, Optional
from decimal import Decimal
import json
from pathlib import Path

from . import register
from .base import StrategyContext, BetSpec, BetResult


@register("rng-analysis-strategy")
class RNGAnalysisStrategy:
    """Strategy that uses RNG analysis insights for betting decisions."""

    @classmethod
    def name(cls) -> str:
        return "rng-analysis-strategy"

    @classmethod
    def describe(cls) -> str:
        return "Uses RNG analysis insights (educational only - doesn't beat house edge)"

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_amount": {
                "type": "str", 
                "default": "0.000001", 
                "desc": "Base bet amount (decimal string)"
            },
            "chance": {
                "type": "str", 
                "default": "50", 
                "desc": "Chance percent as string"
            },
            "is_high": {
                "type": "bool", 
                "default": False, 
                "desc": "Bet High if True else Low (can be auto-set from analysis)"
            },
            "win_threshold": {
                "type": "float", 
                "default": 0.5, 
                "desc": "Win rate threshold to trigger bet size increase"
            },
            "loss_multiplier": {
                "type": "float", 
                "default": 1.5, 
                "desc": "Multiplier after loss (1.0 = flat betting)"
            },
            "win_multiplier": {
                "type": "float", 
                "default": 1.0, 
                "desc": "Multiplier after win (1.0 = flat betting)"
            },
            "max_multiplier": {
                "type": "float", 
                "default": 8.0, 
                "desc": "Maximum bet multiplier"
            },
            "use_patterns": {
                "type": "bool", 
                "default": False, 
                "desc": "Use pattern detection from recent results"
            },
            "pattern_window": {
                "type": "int", 
                "default": 10, 
                "desc": "Number of recent bets to analyze for patterns"
            },
            "config_file": {
                "type": "str", 
                "default": "", 
                "desc": "Path to RNG analysis config JSON file (optional)"
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.base_amount = Decimal(str(params.get("base_amount", "0.000001")))
        self.chance = str(params.get("chance", "50"))
        self.is_high = bool(params.get("is_high", False))
        self.win_threshold = float(params.get("win_threshold", 0.5))
        self.loss_multiplier = float(params.get("loss_multiplier", 1.5))
        self.win_multiplier = float(params.get("win_multiplier", 1.0))
        self.max_multiplier = float(params.get("max_multiplier", 8.0))
        self.use_patterns = bool(params.get("use_patterns", False))
        self.pattern_window = int(params.get("pattern_window", 10))
        self.config_file = str(params.get("config_file", ""))

        # State
        self._current_multiplier = 1.0
        self._win_streak = 0
        self._loss_streak = 0
        self._total_bets = 0
        
        # Load analysis config if provided
        self._analysis_config = None
        if self.config_file:
            self._load_analysis_config(self.config_file)

    def _load_analysis_config(self, config_path: str):
        """Load RNG analysis configuration from JSON file"""
        try:
            path = Path(config_path)
            if path.exists():
                with open(path, 'r') as f:
                    self._analysis_config = json.load(f)
                    
                # Auto-configure from analysis if available
                ml_summary = self._analysis_config.get('ml_summary', {})
                pattern_insights = self._analysis_config.get('pattern_insights', {})
                
                # Adjust betting direction based on pattern insights
                if pattern_insights.get('high_number_frequency', 0.5) > 0.52:
                    self.is_high = True
                elif pattern_insights.get('low_number_frequency', 0.5) > 0.52:
                    self.is_high = False
                    
                print(f"📊 Loaded RNG analysis config from {config_path}")
                print(f"   ML improvement: {ml_summary.get('improvement_over_baseline', 0):.2f}%")
                print(f"   Predictive power: {ml_summary.get('predictive_power', 'unknown')}")
                print(f"   Configured betting: {'HIGH' if self.is_high else 'LOW'}")
        except Exception as e:
            print(f"⚠️  Could not load analysis config from {config_path}: {e}")

    def on_session_start(self) -> None:
        """Called when betting session starts"""
        self._current_multiplier = 1.0
        self._win_streak = 0
        self._loss_streak = 0
        self._total_bets = 0
        
        if self._analysis_config:
            warnings = self._analysis_config.get('risk_assessment', {}).get('warnings', [])
            print("\n⚠️  STRATEGY WARNINGS:")
            for warning in warnings[:3]:
                print(f"   - {warning}")
            print()

    def _detect_pattern(self) -> Optional[str]:
        """
        Detect simple patterns in recent results
        Returns pattern type or None
        """
        if not self.use_patterns or len(self.ctx.recent_results) < self.pattern_window:
            return None
        
        recent = list(self.ctx.recent_results)[-self.pattern_window:]
        
        # Check for win/loss streaks
        wins = sum(1 for r in recent if r.get('win', False))
        win_rate = wins / len(recent)
        
        # Check for alternating pattern
        alternating = 0
        for i in range(1, len(recent)):
            if recent[i].get('win', False) != recent[i-1].get('win', False):
                alternating += 1
        alternating_rate = alternating / (len(recent) - 1)
        
        # Detect patterns (note: these are likely spurious)
        if win_rate > 0.7:
            return 'hot_streak'
        elif win_rate < 0.3:
            return 'cold_streak'
        elif alternating_rate > 0.7:
            return 'alternating'
        
        return None

    def _adjust_bet_size(self, pattern: Optional[str]) -> Decimal:
        """
        Adjust bet size based on pattern and current state
        """
        amount = self.base_amount * Decimal(str(self._current_multiplier))
        
        # Apply pattern-based adjustments (if enabled)
        if self.use_patterns and pattern:
            if pattern == 'cold_streak':
                # After many losses, slightly increase (Martingale-like)
                # But this doesn't overcome house edge!
                amount *= Decimal('1.2')
            elif pattern == 'hot_streak':
                # After many wins, reduce to preserve profit
                amount *= Decimal('0.8')
        
        # Ensure we don't exceed maximum
        max_amount = self.base_amount * Decimal(str(self.max_multiplier))
        if amount > max_amount:
            amount = max_amount
        
        # Ensure minimum
        if amount < self.base_amount:
            amount = self.base_amount
        
        return amount

    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet specification"""
        self._total_bets += 1
        
        # Detect patterns if enabled
        pattern = self._detect_pattern()
        
        # Calculate bet amount
        amount = self._adjust_bet_size(pattern)
        
        # Log pattern detection
        if pattern and self._total_bets % 10 == 0:
            print(f"📊 Pattern detected: {pattern} (multiplier: {self._current_multiplier:.2f}x)")
        
        return {
            "game": "dice",
            "amount": format(amount, 'f'),
            "chance": self.chance,
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def on_bet_result(self, result: BetResult) -> None:
        """Handle bet result and update strategy state"""
        self.ctx.recent_results.append(result)
        
        win = result.get('win', False)
        
        if win:
            self._win_streak += 1
            self._loss_streak = 0
            
            # After win, apply win multiplier
            self._current_multiplier *= self.win_multiplier
            
            # Reset if below base
            if self._current_multiplier < 1.0:
                self._current_multiplier = 1.0
                
        else:
            self._loss_streak += 1
            self._win_streak = 0
            
            # After loss, apply loss multiplier
            self._current_multiplier *= self.loss_multiplier
            
            # Cap at maximum
            if self._current_multiplier > self.max_multiplier:
                self._current_multiplier = self.max_multiplier
        
        # Adaptive behavior based on recent performance
        if len(self.ctx.recent_results) >= 20:
            recent = list(self.ctx.recent_results)[-20:]
            recent_win_rate = sum(1 for r in recent if r.get('win', False)) / len(recent)
            
            # If doing very poorly, reset multiplier
            if recent_win_rate < 0.3:
                self._current_multiplier = 1.0

    def on_session_end(self, reason: str) -> None:
        """Called when betting session ends"""
        if self._total_bets > 0:
            wins = sum(1 for r in self.ctx.recent_results if r.get('win', False))
            win_rate = wins / self._total_bets if self._total_bets > 0 else 0
            
            print(f"\n📊 RNG Analysis Strategy Session Summary:")
            print(f"   Total bets: {self._total_bets}")
            print(f"   Win rate: {win_rate:.2%}")
            print(f"   Longest win streak: {self._win_streak}")
            print(f"   Longest loss streak: {self._loss_streak}")
            print(f"   Final multiplier: {self._current_multiplier:.2f}x")
            print(f"   Reason: {reason}")
            
            if self._analysis_config:
                expected_exploitability = self._analysis_config.get('risk_assessment', {}).get('exploitability', 'none')
                print(f"   Analysis predicted exploitability: {expected_exploitability}")
                print(f"\n   ⚠️  Remember: Past analysis doesn't predict future outcomes!")


# Convenience function to load recommended strategy from config
def load_strategy_from_config(config_path: str, strategy_index: int = 0) -> Dict[str, Any]:
    """
    Load a recommended strategy configuration from RNG analysis config
    
    Args:
        config_path: Path to rng_strategy_config.json or rng_strategy_params.py
        strategy_index: Which recommended strategy to load (0 = most conservative)
        
    Returns:
        Dictionary with strategy_name and params suitable for AutoBetEngine
    """
    try:
        # Try JSON first
        if config_path.endswith('.json'):
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            # Try to import Python module
            import importlib.util
            spec = importlib.util.spec_from_file_location("rng_config", config_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                strategies = getattr(module, 'STRATEGIES', [])
                
                if not strategies or strategy_index >= len(strategies):
                    raise ValueError(f"Strategy index {strategy_index} out of range")
                
                strategy = strategies[strategy_index]
                return {
                    'strategy_name': strategy['base_strategy'],
                    'params': strategy['parameters']
                }
        
        # Extract from JSON
        strategies = config.get('strategy_recommendations', {}).get('recommended_strategies', [])
        
        if not strategies or strategy_index >= len(strategies):
            raise ValueError(f"Strategy index {strategy_index} out of range")
        
        strategy = strategies[strategy_index]
        
        # If it's the RNG analysis strategy, add config file path
        params = strategy['parameters'].copy()
        if strategy['base_strategy'] == 'rng-analysis-strategy':
            params['config_file'] = config_path
        
        return {
            'strategy_name': strategy['base_strategy'],
            'params': params
        }
        
    except Exception as e:
        raise ValueError(f"Could not load strategy from {config_path}: {e}")
