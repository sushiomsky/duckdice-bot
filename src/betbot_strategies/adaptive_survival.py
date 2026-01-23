from __future__ import annotations
"""
Adaptive Survival Strategy - Cautious Opportunistic Meta-Strategy

A sophisticated decision-making system that behaves like a cautious but
opportunistic player focused on long-term survival over fast wins.

Core Philosophy:
- Observe before acting
- Detect calm vs chaos phases
- Multiple competing approaches
- Smooth adaptive transitions
- Survival-first principles

Components:
- Pattern Detector: Identifies market conditions (calm/chaos)
- Sub-Strategies: Multiple independent approaches with different risk profiles
- Performance Tracker: Monitors success of each approach
- Adaptive Selector: Chooses best-performing approach
- Survival Safeguards: Automatic conservative fallback

The strategy continuously analyzes recent outcomes, adjusts risk exposure based
on detected patterns, and gracefully transitions between conservative and
opportunistic modes while maintaining strict survival constraints.
"""
from typing import Any, Dict, Optional
from decimal import Decimal, getcontext
from enum import Enum
from collections import deque
import statistics

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

getcontext().prec = 28


class PhaseType(Enum):
    """Market phase classification."""
    CALM = "CALM"          # Low variance, predictable patterns
    CHAOS = "CHAOS"        # High variance, random behavior
    TRANSITION = "TRANSITION"  # Moving between states
    UNKNOWN = "UNKNOWN"    # Insufficient data


class ApproachType(Enum):
    """Sub-strategy approaches."""
    CONSERVATIVE = "CONSERVATIVE"    # Safe fallback, always active
    MODERATE = "MODERATE"            # Balanced, calm phases
    OPPORTUNISTIC = "OPPORTUNISTIC"  # Aggressive, strong calm
    RECOVERY = "RECOVERY"            # Post-drawdown mode


class PatternDetector:
    """Detects calm vs chaos phases in recent outcomes."""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self.results = deque(maxlen=window_size)
    
    def add_result(self, result: BetResult):
        """Add a bet result to the analysis window."""
        self.results.append(result)
    
    def detect_phase(self) -> tuple[PhaseType, float]:
        """
        Detect current market phase.
        
        Returns:
            (phase_type, confidence_score)
        """
        if len(self.results) < 10:
            return (PhaseType.UNKNOWN, 0.0)
        
        # Calculate metrics
        wins = sum(1 for r in self.results if r.get('win', False))
        win_rate = wins / len(self.results)
        
        # Profit variance
        profits = [float(r.get('profit', 0)) for r in self.results]
        if len(profits) > 1:
            variance = statistics.variance(profits)
            std_dev = statistics.stdev(profits)
        else:
            variance = 0
            std_dev = 0
        
        # Clustering (consecutive same outcomes)
        max_streak = 0
        current_streak = 1
        last_win = self.results[0].get('win', False)
        for r in list(self.results)[1:]:
            if r.get('win', False) == last_win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
            last_win = r.get('win', False)
        
        clustering_score = max_streak / len(self.results)
        
        # Calm indicators:
        # - Win rate near expected (45-55%)
        # - Low profit variance
        # - Some clustering
        calm_score = 0.0
        if 0.40 <= win_rate <= 0.60:
            calm_score += 0.4
        if clustering_score > 0.3:
            calm_score += 0.3
        if variance < 0.0001:  # Low variance
            calm_score += 0.3
        
        # Chaos indicators:
        # - Extreme win rate (<35% or >65%)
        # - High profit variance
        # - No clustering
        chaos_score = 0.0
        if win_rate < 0.35 or win_rate > 0.65:
            chaos_score += 0.4
        if variance > 0.001:  # High variance
            chaos_score += 0.3
        if clustering_score < 0.2:
            chaos_score += 0.3
        
        # Determine phase
        if calm_score > chaos_score and calm_score > 0.6:
            return (PhaseType.CALM, calm_score)
        elif chaos_score > calm_score and chaos_score > 0.6:
            return (PhaseType.CHAOS, chaos_score)
        elif abs(calm_score - chaos_score) < 0.2:
            return (PhaseType.TRANSITION, max(calm_score, chaos_score))
        else:
            return (PhaseType.UNKNOWN, 0.5)
    
    def get_variance_score(self) -> float:
        """Get normalized variance score (0-1, higher = more chaotic)."""
        if len(self.results) < 2:
            return 0.5
        
        profits = [float(r.get('profit', 0)) for r in self.results]
        try:
            variance = statistics.variance(profits)
            # Normalize to 0-1 range (empirical threshold)
            return min(1.0, variance / 0.001)
        except:
            return 0.5


class SubStrategy:
    """Individual betting approach with specific risk profile."""
    
    def __init__(
        self,
        approach_type: ApproachType,
        base_chance: Decimal,
        bet_pct: Decimal,
        max_bet_pct: Decimal
    ):
        self.approach_type = approach_type
        self.base_chance = base_chance
        self.bet_pct = bet_pct
        self.max_bet_pct = max_bet_pct
        self.recent_results = deque(maxlen=20)
        self.total_profit = Decimal(0)
        self.bet_count = 0
    
    def add_result(self, result: BetResult):
        """Record a bet result for this approach."""
        self.recent_results.append(result)
        self.total_profit += Decimal(str(result.get('profit', 0)))
        self.bet_count += 1
    
    def get_performance_score(self) -> float:
        """Calculate performance score (0-1, higher = better)."""
        if not self.recent_results:
            return 0.5  # Neutral
        
        # Win rate component (40%)
        wins = sum(1 for r in self.recent_results if r.get('win', False))
        win_rate = wins / len(self.recent_results)
        win_score = min(1.0, win_rate / 0.6)  # Normalize to 60% = perfect
        
        # Profit trend component (30%)
        recent_5 = list(self.recent_results)[-5:] if len(self.recent_results) >= 5 else list(self.recent_results)
        profit_sum = sum(float(r.get('profit', 0)) for r in recent_5)
        profit_score = 0.5 + min(0.5, max(-0.5, profit_sum * 1000))  # Normalize
        
        # Stability component (30%) - lower variance is better
        if len(self.recent_results) > 1:
            profits = [float(r.get('profit', 0)) for r in self.recent_results]
            try:
                variance = statistics.variance(profits)
                stability_score = max(0.0, 1.0 - (variance / 0.001))
            except:
                stability_score = 0.5
        else:
            stability_score = 0.5
        
        # Weighted combination
        total_score = (
            win_score * 0.4 +
            profit_score * 0.3 +
            stability_score * 0.3
        )
        
        return max(0.0, min(1.0, total_score))
    
    def calculate_bet(self, balance: Decimal, phase: PhaseType) -> tuple[Decimal, Decimal]:
        """
        Calculate bet amount and chance for current conditions.
        
        Returns:
            (bet_amount, chance)
        """
        # Adjust bet size based on phase
        if phase == PhaseType.CHAOS:
            # Reduce exposure in chaos
            bet_amount = balance * self.bet_pct * Decimal("0.5")
        elif phase == PhaseType.CALM:
            # Increase exposure in calm (but stay within max)
            bet_amount = balance * min(self.bet_pct * Decimal("1.5"), self.max_bet_pct)
        else:
            # Normal bet size
            bet_amount = balance * self.bet_pct
        
        # Adjust chance based on phase
        if phase == PhaseType.CHAOS:
            # Higher chance (safer) in chaos
            chance = min(Decimal("98"), self.base_chance + Decimal("10"))
        else:
            chance = self.base_chance
        
        return (bet_amount, chance)


@register("adaptive-survival")
class AdaptiveSurvivalStrategy:
    """
    Adaptive Survival - Cautious Opportunistic Meta-Strategy
    
    A sophisticated meta-strategy that maintains multiple betting approaches,
    detects market conditions, and adaptively selects the best-performing
    approach while prioritizing long-term capital survival.
    
    Key Features:
    - Pattern detection (calm vs chaos)
    - Multiple competing sub-strategies
    - Adaptive approach selection
    - Automatic conservative fallback
    - Smooth risk transitions
    - Survival-first principles
    """
    
    @classmethod
    def name(cls) -> str:
        return "adaptive-survival"
    
    @classmethod
    def describe(cls) -> str:
        return (
            "Meta-strategy with pattern detection, multiple competing approaches, "
            "and adaptive selection focused on long-term survival"
        )
    
    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Low",
            time_to_profit="Slow",
            recommended_for="Intermediate",
            pros=[
                "Adapts to changing market conditions",
                "Multiple independent approaches reduce risk",
                "Automatic pattern detection",
                "Conservative fallback always available",
                "Smooth risk transitions",
                "Long-term survival focus"
            ],
            cons=[
                "Complex decision-making process",
                "Slower profit accumulation",
                "Requires sufficient bet history",
                "May be overly conservative",
                "Not optimized for quick wins"
            ],
            best_use_case="Long-term play with capital preservation. Good for patient players.",
            tips=[
                "Give strategy time to observe patterns (20+ bets)",
                "Works best with stable bankroll",
                "Not for aggressive profit targets",
                "Trust the conservative fallback",
                "Monitor phase detection in logs",
                "Adjust base parameters for risk tolerance"
            ]
        )
    
    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "base_bet_pct": {
                "type": "float",
                "default": 0.01,
                "desc": "Base bet as % of balance (1%)",
            },
            "max_bet_pct": {
                "type": "float",
                "default": 0.02,
                "desc": "Maximum bet as % of balance (2%)",
            },
            "conservative_chance": {
                "type": "str",
                "default": "75",
                "desc": "Win chance for conservative approach",
            },
            "moderate_chance": {
                "type": "str",
                "default": "50",
                "desc": "Win chance for moderate approach",
            },
            "opportunistic_chance": {
                "type": "str",
                "default": "40",
                "desc": "Win chance for opportunistic approach",
            },
            "recovery_chance": {
                "type": "str",
                "default": "85",
                "desc": "Win chance for recovery mode",
            },
            "drawdown_threshold": {
                "type": "float",
                "default": -0.05,
                "desc": "Drawdown % to trigger recovery mode (-5%)",
            },
            "loss_streak_limit": {
                "type": "int",
                "default": 5,
                "desc": "Consecutive losses before going conservative",
            },
            "pattern_window": {
                "type": "int",
                "default": 20,
                "desc": "Number of bets to analyze for patterns",
            },
            "performance_threshold": {
                "type": "float",
                "default": 0.3,
                "desc": "Minimum performance score to use approach (0-1)",
            },
        }
    
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext):
        self.params = params
        self.ctx = ctx
        
        # Parse parameters
        self.base_bet_pct = Decimal(str(params.get('base_bet_pct', 0.01)))
        self.max_bet_pct = Decimal(str(params.get('max_bet_pct', 0.02)))
        self.drawdown_threshold = params.get('drawdown_threshold', -0.05)
        self.loss_streak_limit = params.get('loss_streak_limit', 5)
        self.performance_threshold = params.get('performance_threshold', 0.3)
        
        # Initialize pattern detector
        window_size = params.get('pattern_window', 20)
        self.pattern_detector = PatternDetector(window_size)
        
        # Initialize sub-strategies
        self.approaches: Dict[ApproachType, SubStrategy] = {
            ApproachType.CONSERVATIVE: SubStrategy(
                ApproachType.CONSERVATIVE,
                Decimal(str(params.get('conservative_chance', '75'))),
                self.base_bet_pct * Decimal("0.5"),  # 50% of base
                self.base_bet_pct
            ),
            ApproachType.MODERATE: SubStrategy(
                ApproachType.MODERATE,
                Decimal(str(params.get('moderate_chance', '50'))),
                self.base_bet_pct,
                self.max_bet_pct
            ),
            ApproachType.OPPORTUNISTIC: SubStrategy(
                ApproachType.OPPORTUNISTIC,
                Decimal(str(params.get('opportunistic_chance', '40'))),
                self.base_bet_pct * Decimal("1.5"),  # 150% of base
                self.max_bet_pct
            ),
            ApproachType.RECOVERY: SubStrategy(
                ApproachType.RECOVERY,
                Decimal(str(params.get('recovery_chance', '85'))),
                self.base_bet_pct * Decimal("0.3"),  # 30% of base
                self.base_bet_pct * Decimal("0.5")
            ),
        }
        
        # State tracking
        self.current_approach = ApproachType.CONSERVATIVE
        self.loss_streak = 0
        self.starting_balance = Decimal(str(ctx.starting_balance))
        self.in_recovery = False
    
    def on_session_start(self):
        """Called when session starts."""
        pass
    
    def on_bet_result(self, result: BetResult):
        """Called after each bet result."""
        # Update pattern detector
        self.pattern_detector.add_result(result)
        
        # Update current approach's results
        self.approaches[self.current_approach].add_result(result)
        
        # Track loss streak
        if result.get('win', False):
            self.loss_streak = 0
        else:
            self.loss_streak += 1
        
        # Check for recovery mode trigger
        current_balance = Decimal(str(result.get('balance', self.starting_balance)))
        if self.starting_balance > 0:
            drawdown = (current_balance - self.starting_balance) / self.starting_balance
            if float(drawdown) <= self.drawdown_threshold:
                self.in_recovery = True
    
    def next_bet(self) -> Optional[BetSpec]:
        """Generate next bet based on adaptive selection."""
        # Get current balance
        balance = Decimal(str(self.ctx.current_balance_str()))
        
        # Check minimum balance
        if balance < Decimal("0.00000001"):
            return None
        
        # Detect current phase
        phase, confidence = self.pattern_detector.detect_phase()
        
        # Select approach
        selected_approach = self._select_approach(phase, confidence)
        
        # Calculate bet
        bet_amount, chance = self.approaches[selected_approach].calculate_bet(balance, phase)
        
        # Safety caps
        bet_amount = min(bet_amount, balance * self.max_bet_pct)
        bet_amount = max(bet_amount, Decimal("0.00000001"))  # Minimum
        
        # Quantize to 8 decimal places
        bet_amount = bet_amount.quantize(Decimal("0.00000001"))
        
        return {
            "game": "dice",
            "amount": str(bet_amount),
            "chance": str(chance),
            "is_high": True,
        }
    
    def _select_approach(self, phase: PhaseType, confidence: float) -> ApproachType:
        """
        Select best approach based on phase, performance, and safety rules.
        """
        # Force recovery mode if triggered
        if self.in_recovery:
            return ApproachType.RECOVERY
        
        # Force conservative if loss streak too high
        if self.loss_streak >= self.loss_streak_limit:
            return ApproachType.CONSERVATIVE
        
        # In chaos, prefer conservative
        if phase == PhaseType.CHAOS and confidence > 0.6:
            return ApproachType.CONSERVATIVE
        
        # In unknown/transition, use conservative
        if phase in (PhaseType.UNKNOWN, PhaseType.TRANSITION):
            return ApproachType.CONSERVATIVE
        
        # In calm, select based on performance
        if phase == PhaseType.CALM:
            # Calculate scores for each approach
            scores = {
                approach_type: approach.get_performance_score()
                for approach_type, approach in self.approaches.items()
                if approach_type != ApproachType.RECOVERY  # Don't select recovery normally
            }
            
            # Find best performing
            best_approach = max(scores.keys(), key=lambda k: scores[k])
            best_score = scores[best_approach]
            
            # Use best if above threshold, otherwise conservative
            if best_score >= self.performance_threshold:
                return best_approach
        
        # Default to conservative
        return ApproachType.CONSERVATIVE
    
    def on_session_end(self, reason: str):
        """Called when session ends."""
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """Get current strategy state for logging/debugging."""
        phase, confidence = self.pattern_detector.detect_phase()
        
        return {
            "current_approach": self.current_approach.value,
            "phase": phase.value,
            "phase_confidence": confidence,
            "loss_streak": self.loss_streak,
            "in_recovery": self.in_recovery,
            "approach_scores": {
                approach_type.value: approach.get_performance_score()
                for approach_type, approach in self.approaches.items()
            }
        }
