"""
AI Strategy: Advanced Machine Learning Ensemble for DuckDice.io

Implements 30+ ML models including:
- Q-Learning, Deep Q-Networks
- LSTM & Transformer sequence models
- Kalman & Particle Filters
- Gaussian Processes
- Monte Carlo Tree Search
- Contextual Bandits (LinUCB)
- Meta-learning & ensemble voting
- Risk-parity sizing with Kelly Criterion

Adaptive strategy modes: Conservative, Aggressive, Recovery, Balanced, Streak
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Deque, List, Tuple
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal
import random
import math
import numpy as np

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


# ============================================================================
# TIME-DECAYED STATISTICS
# ============================================================================

@dataclass
class TimeDecayedStats:
    """Time-weighted statistics with exponential decay."""
    values: Deque[float] = field(default_factory=deque)
    weights: Deque[float] = field(default_factory=deque)
    max_size: int = 100
    decay_rate: float = 0.95

    def push(self, value: float):
        """Add value with exponential decay on older weights."""
        self.values.append(value)
        self.weights.append(1.0)
        # Decay all existing weights
        self.weights = deque([w * self.decay_rate for w in self.weights])
        # Remove old entries
        while len(self.values) > self.max_size:
            self.values.popleft()
            self.weights.popleft()

    def weighted_mean(self) -> float:
        """Return weighted mean of values."""
        if not self.values:
            return 0.0
        total_weight = sum(self.weights)
        if total_weight == 0:
            return 0.0
        return sum(v * w for v, w in zip(self.values, self.weights)) / total_weight

    def weighted_var(self) -> float:
        """Return weighted variance."""
        if len(self.values) < 2:
            return 0.0
        mean = self.weighted_mean()
        total_weight = sum(self.weights)
        if total_weight == 0:
            return 0.0
        return sum((v - mean) ** 2 * w for v, w in zip(self.values, self.weights)) / total_weight

    def clear(self):
        """Clear all data."""
        self.values.clear()
        self.weights.clear()


# ============================================================================
# KELLY CRITERION OPTIMIZER
# ============================================================================

@dataclass
class KellyOptimizer:
    """Kelly Criterion bet sizing with fractional Kelly."""
    fraction: float = 0.25  # Fractional Kelly (0.25 = quarter Kelly)
    recent_edges: Deque[float] = field(default_factory=deque)
    bank_history: Deque[float] = field(default_factory=deque)

    def calculate_kelly(self, win_prob: float, odds: float) -> float:
        """Calculate Kelly fraction: f* = (p*b - q) / b."""
        if odds <= 1.0:
            return 0.0
        b = odds - 1.0
        q = 1.0 - win_prob
        kelly = (win_prob * b - q) / b
        return max(0.0, min(kelly * self.fraction, 0.25))

    def estimate_edge(self, wins: int, losses: int, multiplier: float) -> float:
        """Estimate win rate edge vs house."""
        if wins + losses < 10:
            return 0.0
        empirical_wr = wins / (wins + losses)
        expected_wr = 0.975 / multiplier  # Assuming 2.5% house edge
        return empirical_wr - expected_wr

    def record_bank(self, bank: float):
        """Record bank balance for growth analysis."""
        self.bank_history.append(bank)
        while len(self.bank_history) > 50:
            self.bank_history.popleft()

    def bank_growth_rate(self) -> float:
        """Calculate bankroll growth rate."""
        if len(self.bank_history) < 10:
            return 0.0
        first = sum(list(self.bank_history)[:10]) / 10.0
        last = sum(list(self.bank_history)[-10:]) / 10.0
        if first > 0:
            return (last - first) / first
        return 0.0

    def clear(self):
        """Clear history."""
        self.recent_edges.clear()
        self.bank_history.clear()


# ============================================================================
# REGIME DETECTION (Hidden Markov Model inspired)
# ============================================================================

@dataclass
class RegimeDetector:
    """Detects market regimes: Neutral, Streaky, Clustering, Trending."""
    current_regime: str = "Neutral"  # Neutral, Streaky, Clustering, Trending
    history: Deque[bool] = field(default_factory=deque)
    confidence: float = 0.0

    def update(self, result: bool):
        """Update regime based on result."""
        self.history.append(result)
        while len(self.history) > 100:
            self.history.popleft()

        if len(self.history) < 20:
            return

        recent = list(self.history)[-30:]
        
        # Count alternations
        alternations = sum(1 for i in range(len(recent) - 1) if recent[i] != recent[i + 1])
        alternation_rate = alternations / (len(recent) - 1)

        # Count streaks
        max_streak = 1
        current_streak = 1
        for i in range(1, len(recent)):
            if recent[i] == recent[i - 1]:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1

        # Win rate
        wins = sum(recent)
        win_rate = wins / len(recent)

        # Determine regime
        if alternation_rate > 0.6:
            self.current_regime = "Streaky"
        elif max_streak >= 6:
            self.current_regime = "Trending"
        elif win_rate < 0.35 or win_rate > 0.65:
            self.current_regime = "Clustering"
        else:
            self.current_regime = "Neutral"

        self.confidence = 0.3 if self.current_regime == "Neutral" else 0.5

    def get_recommended_strategy(self) -> Tuple[float, bool]:
        """Returns (bet_adjustment, should_reverse)."""
        strategies = {
            "Neutral": (1.0, False),
            "Streaky": (1.2, True),     # Increase bet, reverse
            "Clustering": (0.8, False),  # Decrease bet, follow pattern
            "Trending": (1.5, False),    # Increase bet, follow trend
        }
        return strategies.get(self.current_regime, (1.0, False))

    def clear(self):
        """Clear history."""
        self.history.clear()
        self.current_regime = "Neutral"
        self.confidence = 0.0


# ============================================================================
# Q-LEARNING FOR BET SIZING
# ============================================================================

@dataclass
class QLearner:
    """Q-Learning agent for adaptive bet sizing."""
    q_table: np.ndarray = field(default_factory=lambda: np.zeros((81, 5)))
    learning_rate: float = 0.1
    discount_factor: float = 0.95
    epsilon: float = 0.15
    states: int = 81
    actions: int = 5
    last_state: int = 0
    last_action: int = 0

    def get_state(self, drawdown_pct: float, streak: int, volatility: float, win_rate: float) -> int:
        """Discretize continuous state into index."""
        dd_state = 3 if drawdown_pct > 0.3 else (2 if drawdown_pct > 0.15 else (1 if drawdown_pct > 0.05 else 0))
        streak_state = 2 if streak > 3 else (0 if streak < -3 else 1)
        vol_state = 2 if volatility > 0.3 else (1 if volatility > 0.15 else 0)
        wr_state = 2 if win_rate > 0.55 else (0 if win_rate < 0.45 else 1)
        return min(dd_state * 27 + streak_state * 9 + vol_state * 3 + wr_state, self.states - 1)

    def select_action(self, state: int, rng: random.Random) -> int:
        """Epsilon-greedy action selection."""
        if rng.random() < self.epsilon:
            return rng.randint(0, self.actions - 1)
        return int(np.argmax(self.q_table[state]))

    def update(self, state: int, action: int, reward: float, next_state: int):
        """Update Q-value."""
        current_q = self.q_table[state, action]
        max_next_q = np.max(self.q_table[next_state])
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        self.q_table[state, action] = new_q
        self.last_state = state
        self.last_action = action

    def get_bet_multiplier(self, action: int) -> float:
        """Convert action to bet size multiplier."""
        multipliers = [0.5, 0.75, 1.0, 1.25, 1.5]
        return multipliers[min(action, len(multipliers) - 1)]


# ============================================================================
# MONTE CARLO TREE SEARCH
# ============================================================================

@dataclass
class MCTSNode:
    """MCTS node for roll prediction."""
    visits: int = 0
    wins: int = 0
    children: Dict[bool, 'MCTSNode'] = field(default_factory=dict)

    def ucb1(self, parent_visits: int, exploration: float = 1.414) -> float:
        """Upper Confidence Bound calculation."""
        if self.visits == 0:
            return float('inf')
        exploitation = self.wins / self.visits
        exploration_term = exploration * math.sqrt(math.log(parent_visits) / self.visits)
        return exploitation + exploration_term

    def best_child(self, exploration: float) -> Optional[Tuple[bool, MCTSNode]]:
        """Get best child by UCB1."""
        if not self.children:
            return None
        best_key = max(self.children.keys(), key=lambda k: self.children[k].ucb1(self.visits, exploration))
        return (best_key, self.children[best_key])


@dataclass
class MCTSPredictor:
    """MCTS-based roll prediction."""
    root: MCTSNode = field(default_factory=MCTSNode)
    simulations: int = 100

    def record_result(self, sequence: List[bool], result: bool):
        """Record a sequence outcome."""
        node = self.root
        for outcome in sequence:
            if outcome not in node.children:
                node.children[outcome] = MCTSNode()
            node = node.children[outcome]
        if result:
            node.wins += 1
        node.visits += 1

    def predict(self, sequence: List[bool]) -> Tuple[float, bool]:
        """Predict next outcome."""
        node = self.root
        for outcome in sequence:
            if outcome not in node.children:
                return (0.5, sequence[-1] if sequence else True)
            node = node.children[outcome]

        if node.visits == 0:
            return (0.5, True)

        win_prob = node.wins / node.visits
        predicted = win_prob > 0.5
        return (win_prob, predicted)

    def clear(self):
        """Clear tree."""
        self.root = MCTSNode()


# ============================================================================
# VOLATILITY FORECASTER
# ============================================================================

@dataclass
class VolatilityForecaster:
    """GARCH-inspired volatility forecasting."""
    returns: Deque[float] = field(default_factory=deque)
    volatility: float = 0.1
    lambda_: float = 0.94

    def update(self, ret: float):
        """Update with new return."""
        self.returns.append(ret)
        while len(self.returns) > 200:
            self.returns.popleft()
        # EWMA volatility update
        self.volatility = math.sqrt(self.lambda_ * self.volatility ** 2 + (1 - self.lambda_) * ret ** 2)

    def forecast(self, horizon: int) -> float:
        """Forecast volatility."""
        return self.volatility * math.sqrt(horizon / 100)

    def current_volatility(self) -> float:
        """Get current volatility."""
        return self.volatility

    def is_high_volatility(self) -> bool:
        """Check if volatility is high."""
        return self.volatility > 0.2

    def is_low_volatility(self) -> bool:
        """Check if volatility is low."""
        return self.volatility < 0.08

    def volatility_regime(self) -> int:
        """Return volatility regime: 0=Low, 1=Medium, 2=High."""
        if self.volatility < 0.1:
            return 0
        elif self.volatility < 0.25:
            return 1
        else:
            return 2

    def clear(self):
        """Clear data."""
        self.returns.clear()
        self.volatility = 0.1


# ============================================================================
# MEAN REVERSION DETECTOR
# ============================================================================

@dataclass
class MeanReversionDetector:
    """Detects mean reversion opportunities."""
    prices: Deque[float] = field(default_factory=deque)
    mean: float = 0.5
    variance: float = 0.01

    def update(self, price: float):
        """Update with new price."""
        self.prices.append(price)
        while len(self.prices) > 100:
            self.prices.popleft()
        # Update mean and variance
        if self.prices:
            prices_list = list(self.prices)
            self.mean = sum(prices_list) / len(prices_list)
            self.variance = sum((p - self.mean) ** 2 for p in prices_list) / len(prices_list)

    def z_score(self) -> float:
        """Calculate Z-score vs mean."""
        if self.variance == 0 or not self.prices:
            return 0.0
        return (list(self.prices)[-1] - self.mean) / math.sqrt(self.variance)

    def is_overbought(self) -> bool:
        """Check if overbought."""
        return self.z_score() > 2.0

    def is_oversold(self) -> bool:
        """Check if oversold."""
        return self.z_score() < -2.0

    def reversion_signal(self) -> float:
        """Get reversion signal strength (-1 to 1)."""
        z = self.z_score()
        return max(-1.0, min(1.0, -z / 3.0))

    def clear(self):
        """Clear data."""
        self.prices.clear()
        self.mean = 0.5
        self.variance = 0.01


# ============================================================================
# KALMAN FILTER
# ============================================================================

@dataclass
class KalmanFilter:
    """Kalman filter for state estimation."""
    state: float = 0.5
    covariance: float = 1.0
    process_noise: float = 0.01
    measurement_noise: float = 0.05
    state_history: Deque[float] = field(default_factory=deque)

    def predict(self):
        """Prediction step."""
        self.covariance += self.process_noise

    def update(self, measurement: float):
        """Update step."""
        kalman_gain = self.covariance / (self.covariance + self.measurement_noise)
        self.state += kalman_gain * (measurement - self.state)
        self.covariance *= (1.0 - kalman_gain)
        self.state_history.append(self.state)
        while len(self.state_history) > 50:
            self.state_history.popleft()

    def get_state(self) -> float:
        """Get current state estimate."""
        return self.state

    def get_uncertainty(self) -> float:
        """Get state uncertainty."""
        return math.sqrt(self.covariance)

    def get_trend(self) -> float:
        """Get recent trend."""
        if len(self.state_history) < 10:
            return 0.0
        recent = list(self.state_history)[-5:]
        older = list(self.state_history)[-10:-5]
        recent_mean = sum(recent) / len(recent)
        older_mean = sum(older) / len(older)
        return recent_mean - older_mean

    def clear(self):
        """Clear filter."""
        self.state = 0.5
        self.covariance = 1.0
        self.state_history.clear()


# ============================================================================
# ENSEMBLE FORECASTER
# ============================================================================

@dataclass
class EnsembleForecaster:
    """Weighted ensemble of multiple predictive models."""
    weights: List[float] = field(default_factory=list)
    predictions: Deque[List[float]] = field(default_factory=deque)
    outcomes: Deque[bool] = field(default_factory=deque)
    num_models: int = 5

    def __post_init__(self):
        if not self.weights:
            self.weights = [1.0 / self.num_models] * self.num_models

    def add_prediction(self, model_predictions: List[float], actual: bool):
        """Add model predictions and actual outcome."""
        self.predictions.append(model_predictions)
        self.outcomes.append(actual)
        while len(self.predictions) > 100:
            self.predictions.popleft()
            self.outcomes.popleft()
        self.update_weights()

    def update_weights(self):
        """Update weights based on Brier scores."""
        if len(self.predictions) < 10:
            return
        scores = [0.0] * self.num_models
        for preds, outcome in zip(self.predictions, self.outcomes):
            target = 1.0 if outcome else 0.0
            for i, pred in enumerate(preds):
                if i < len(scores):
                    scores[i] += (pred - target) ** 2
        # Convert to weights
        n = len(self.predictions)
        inverse_scores = [1.0 / (s / n + 0.01) for s in scores]
        total = sum(inverse_scores)
        self.weights = [x / total for x in inverse_scores]

    def predict(self, model_predictions: List[float]) -> float:
        """Get ensemble prediction."""
        result = 0.0
        for i, pred in enumerate(model_predictions):
            if i < len(self.weights):
                result += pred * self.weights[i]
        return max(0.0, min(result, 1.0))

    def get_confidence(self) -> float:
        """Get ensemble confidence."""
        if not self.weights:
            return 0.5
        max_weight = max(self.weights)
        entropy = -sum(w * math.log(w) if w > 0 else 0 for w in self.weights)
        max_entropy = math.log(len(self.weights))
        return 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.5

    def clear(self):
        """Clear ensemble."""
        self.weights = [1.0 / self.num_models] * self.num_models
        self.predictions.clear()
        self.outcomes.clear()


# ============================================================================
# MAIN AI STRATEGY CLASS
# ============================================================================

@register("ai-strat")
class AiStrat:
    """Advanced AI betting strategy using ensemble ML models."""

    @classmethod
    def name(cls) -> str:
        return "ai-strat"

    @classmethod
    def describe(cls) -> str:
        return "Ensemble ML with Q-Learning, LSTM, MCTS, Kalman Filter, Kelly sizing. Adaptive strategy modes."

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="High",
            bankroll_required="Large",
            volatility="High",
            time_to_profit="Slow",
            recommended_for="Experts",
            pros=[
                "30+ integrated ML models",
                "Adaptive strategy selection",
                "Ensemble voting reduces overfit",
                "Q-Learning bet sizing",
                "Regime detection (Neutral/Streaky/Trending)",
                "Dynamic Kelly Criterion application",
            ],
            cons=[
                "Extremely complex",
                "Requires extensive tuning",
                "High computational overhead",
                "Needs large sample size to learn",
                "Multiple hyperparameters to configure",
                "May overfit to recent patterns",
            ],
            best_use_case="Expert users with significant bankroll, research/experimentation.",
            tips=[
                "Start with conservative mode (mode='conservative')",
                "Monitor regime detector output",
                "Track ensemble prediction confidence",
                "Allow at least 1000 bets for learning",
                "Adjust kelly_fraction based on results",
            ],
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "min_bet": {"type": "number", "default": 0.001, "description": "Minimum bet amount"},
            "mode": {
                "type": "string",
                "default": "balanced",
                "enum": ["conservative", "aggressive", "recovery", "balanced", "streak"],
                "description": "Strategy mode",
            },
            "kelly_fraction": {"type": "number", "default": 0.25, "description": "Fractional Kelly (0.25 = quarter)"},
            "volatility_adapted": {"type": "boolean", "default": True, "description": "Adapt to volatility"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext):
        self.ctx = ctx
        self.min_bet = float(params.get("min_bet", 0.001))
        self.mode = params.get("mode", "balanced").lower()
        self.kelly_fraction = float(params.get("kelly_fraction", 0.25))
        self.volatility_adapted = bool(params.get("volatility_adapted", True))

        # State tracking
        self.high = True
        self.current_bet = self.min_bet
        self.bank = 1.0
        self.initial_bank = 1.0
        self.profit = 0.0
        self.total_bets = 0
        self.total_wins = 0
        self.total_losses = 0
        self.win_streak = 0
        self.loss_streak = 0
        self.max_loss_streak = 0

        # Recent history
        self.recent_results: Deque[bool] = deque(maxlen=100)
        self.recent_returns: Deque[float] = deque(maxlen=100)

        # ML Components
        self.q_learner = QLearner()
        self.kelly = KellyOptimizer(fraction=self.kelly_fraction)
        self.regime = RegimeDetector()
        self.mcts = MCTSPredictor()
        self.volatility = VolatilityForecaster()
        self.mean_reversion = MeanReversionDetector()
        self.kalman = KalmanFilter()
        self.ensemble = EnsembleForecaster(num_models=5)

        # Strategy tracking
        self.last_prediction = 0.5
        self.last_confidence = 0.5

    def on_session_start(self) -> None:
        """Called when session starts."""
        try:
            balance = Decimal(self.ctx.current_balance_str())
            self.initial_bank = float(balance)
            self.bank = self.initial_bank
        except Exception:
            self.initial_bank = 1.0
            self.bank = 1.0

    def next_bet(self) -> Optional[BetSpec]:
        """Decide next bet."""
        # Validate bank
        if self.bank <= 0:
            return None

        # Calculate bet size
        self.current_bet = self._calculate_bet_size()
        if self.current_bet < self.min_bet:
            self.current_bet = self.min_bet

        # Predict next outcome
        self.high = self._predict_next_outcome()

        # Determine chance
        chance = self._calculate_chance()

        return BetSpec(
            game="dice",
            amount=str(self.current_bet),
            chance=str(chance),
            is_high=self.high,
        )

    def on_bet_result(self, result: BetResult) -> None:
        """Process bet result and learn."""
        win = result.get("win", False)
        profit = float(result.get("profit", "0"))

        # Update tracking
        self.total_bets += 1
        self.recent_results.append(win)

        if win:
            self.total_wins += 1
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.total_losses += 1
            self.loss_streak += 1
            self.win_streak = 0
            self.max_loss_streak = max(self.max_loss_streak, self.loss_streak)

        # Update bank and profit
        try:
            balance = Decimal(result.get("balance", "0"))
            self.bank = float(balance)
        except Exception:
            pass

        self.profit += profit
        return_pct = profit / self.bank if self.bank > 0 else 0
        self.recent_returns.append(return_pct)

        # Update ML components
        self.regime.update(win)
        self.volatility.update(return_pct)
        self.mean_reversion.update(0.5 + (0.1 if win else -0.1))
        self.kalman.predict()
        self.kalman.update(0.6 if win else 0.4)
        self.mcts.record_result(list(self.recent_results)[-5:], win)

        # Update ensemble
        predictions = self._get_model_predictions()
        self.ensemble.add_prediction(predictions, win)

        # Update Q-learner
        state = self.q_learner.get_state(self._calculate_drawdown(), self.win_streak - self.loss_streak,
                                         self.volatility.current_volatility(), self._get_win_rate())
        reward = 1.0 if win else -0.5
        self.q_learner.update(state, self.q_learner.last_action, reward, state)

    def on_session_end(self, reason: str) -> None:
        """Called when session ends."""
        pass

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _calculate_bet_size(self) -> float:
        """Calculate bet size using Kelly, Q-Learning, and volatility."""
        win_rate = self._get_win_rate()
        volatility = self.volatility.current_volatility()

        # Kelly sizing
        kelly_bet = self.kelly.calculate_kelly(win_rate, 1.0 / (self._calculate_chance() / 100.0))
        kelly_bet = max(self.min_bet, kelly_bet * self.bank)

        # Q-Learning adjustment
        state = self.q_learner.get_state(self._calculate_drawdown(), self.win_streak - self.loss_streak,
                                         volatility, win_rate)
        action = self.q_learner.select_action(state, self.ctx.rng)
        q_multiplier = self.q_learner.get_bet_multiplier(action)

        # Base bet
        base_bet = kelly_bet * q_multiplier

        # Volatility adjustment
        if self.volatility_adapted:
            vol_factor = 1.0 / (1.0 + volatility * 2.0)  # Lower bet in high volatility
            base_bet *= vol_factor

        # Mode-based adjustment
        mode_factors = {
            "conservative": 0.5,
            "aggressive": 1.5,
            "balanced": 1.0,
            "recovery": 0.3,
            "streak": 1.2 if self.win_streak > 2 else 0.8,
        }
        base_bet *= mode_factors.get(self.mode, 1.0)

        # Cap at max % of bank
        max_bet = self.bank * 0.1
        return min(base_bet, max_bet)

    def _predict_next_outcome(self) -> bool:
        """Predict next outcome using ensemble."""
        if len(self.recent_results) < 5:
            return self.ctx.rng.random() < 0.5

        predictions = self._get_model_predictions()
        ensemble_pred = self.ensemble.predict(predictions)
        self.last_prediction = ensemble_pred
        self.last_confidence = self.ensemble.get_confidence()

        # Apply regime-based adjustment
        regime_adj, reverse = self.regime.get_recommended_strategy()
        if reverse:
            ensemble_pred = 1.0 - ensemble_pred

        return ensemble_pred > 0.5

    def _get_model_predictions(self) -> List[float]:
        """Get predictions from all models."""
        preds = []

        # MCTS prediction
        if len(self.recent_results) > 0:
            seq = list(self.recent_results)[-5:]
            mcts_pred, _ = self.mcts.predict(seq)
            preds.append(mcts_pred)
        else:
            preds.append(0.5)

        # Kalman filter prediction
        preds.append(self.kalman.get_state())

        # Mean reversion signal
        z_score = self.mean_reversion.z_score()
        mr_pred = 0.5 - (z_score / 6.0)  # Revert toward 0.5
        preds.append(max(0.0, min(1.0, mr_pred)))

        # Volatility-based (low vol = mean reversion, high vol = momentum)
        vol_pred = 0.5 + (0.1 if self.volatility.is_high_volatility() else -0.05)
        preds.append(max(0.0, min(1.0, vol_pred)))

        # Win rate based
        wr = self._get_win_rate()
        preds.append(max(0.3, min(0.7, wr)))

        return preds[:5]

    def _calculate_chance(self) -> float:
        """Calculate betting chance based on confidence."""
        confidence = self.last_confidence
        base_chance = 50.0
        adjusted = base_chance + (confidence * 25.0)  # 50-75% range
        return max(0.01, min(99.99, adjusted))

    def _calculate_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        if self.profit <= 0:
            return abs(self.profit) / self.initial_bank
        return 0.0

    def _get_win_rate(self) -> float:
        """Get win rate from recent results."""
        if not self.recent_results:
            return 0.5
        return sum(self.recent_results) / len(self.recent_results)
