use crate::sites::BetResult;
use crate::strategies::Strategy;
use rand::Rng;
use rayon::prelude::*;
use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex};

// ============================================================================
// MASTER PROTECTION TOGGLE
// Set to false to disable ALL protections and let the AI run unconstrained
// ============================================================================
const PROTECTIONS_ENABLED: bool = false;

// ============================================================================
// TIME-DECAYED STATISTICS
// ============================================================================

#[derive(Debug, Clone)]
struct TimeDecayedStats {
    values: VecDeque<f32>,
    weights: VecDeque<f32>,
    max_size: usize,
    decay_rate: f32,
}

impl TimeDecayedStats {
    fn new(max_size: usize, decay_rate: f32) -> Self {
        Self {
            values: VecDeque::with_capacity(max_size),
            weights: VecDeque::with_capacity(max_size),
            max_size,
            decay_rate,
        }
    }

    fn push(&mut self, value: f32) {
        self.values.push_back(value);
        self.weights.push_back(1.0);
        for w in self.weights.iter_mut() {
            *w *= self.decay_rate;
        }
        if self.values.len() > self.max_size {
            self.values.pop_front();
            self.weights.pop_front();
        }
    }

    fn weighted_mean(&self) -> f32 {
        if self.values.is_empty() {
            return 0.0;
        }
        let sum: f32 = self
            .values
            .iter()
            .zip(self.weights.iter())
            .map(|(v, w)| v * w)
            .sum();
        let wsum: f32 = self.weights.iter().sum();
        if wsum == 0.0 {
            0.0
        } else {
            sum / wsum
        }
    }

    fn weighted_var(&self) -> f32 {
        if self.values.len() < 2 {
            return 0.0;
        }
        let mean = self.weighted_mean();
        let sum: f32 = self
            .values
            .iter()
            .zip(self.weights.iter())
            .map(|(v, w)| (v - mean).powi(2) * w)
            .sum();
        let wsum: f32 = self.weights.iter().sum();
        if wsum == 0.0 {
            0.0
        } else {
            sum / wsum
        }
    }

    fn clear(&mut self) {
        self.values.clear();
        self.weights.clear();
    }
}

// ============================================================================
// KELLY CRITERION CALCULATOR
// ============================================================================

#[derive(Debug, Clone)]
struct KellyOptimizer {
    fraction: f32, // Fractional Kelly (0.25 = quarter Kelly)
    recent_edges: VecDeque<f32>,
    bank_history: VecDeque<f32>,
}

impl KellyOptimizer {
    fn new(fraction: f32) -> Self {
        Self {
            fraction,
            recent_edges: VecDeque::with_capacity(100),
            bank_history: VecDeque::with_capacity(50),
        }
    }

    fn calculate_kelly(&self, win_prob: f32, odds: f32) -> f32 {
        // Kelly formula: f* = (p*b - q) / b where b = odds-1
        let b = odds - 1.0;
        let q = 1.0 - win_prob;
        let kelly = (win_prob * b - q) / b;
        // Apply fractional Kelly and clamp
        (kelly * self.fraction).clamp(0.0, 0.25)
    }

    fn estimate_edge(&self, wins: u32, losses: u32, multiplier: f32) -> f32 {
        if wins + losses < 10 {
            return 0.0;
        }
        let empirical_win_rate = wins as f32 / (wins + losses) as f32;
        let expected_win_rate = 0.975 / multiplier; // Assuming 2.5% house edge
        empirical_win_rate - expected_win_rate
    }

    fn record_bank(&mut self, bank: f32) {
        self.bank_history.push_back(bank);
        if self.bank_history.len() > 50 {
            self.bank_history.pop_front();
        }
    }

    fn bank_growth_rate(&self) -> f32 {
        if self.bank_history.len() < 10 {
            return 0.0;
        }
        let first: f32 = self.bank_history.iter().take(10).sum::<f32>() / 10.0;
        let last: f32 = self.bank_history.iter().rev().take(10).sum::<f32>() / 10.0;
        if first > 0.0 {
            (last - first) / first
        } else {
            0.0
        }
    }

    fn clear(&mut self) {
        self.recent_edges.clear();
        self.bank_history.clear();
    }
}

// ============================================================================
// REGIME DETECTOR (Hidden Markov Model inspired)
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq)]
enum MarketRegime {
    Neutral,
    Streaky,    // Alternating win/loss pattern
    Clustering, // Wins or losses cluster together
    Trending,   // Extended win or loss streaks
}

#[derive(Debug, Clone)]
struct RegimeDetector {
    transition_matrix: [[f32; 4]; 4],
    current_regime: MarketRegime,
    history: VecDeque<bool>,
    emission_probs: [[f32; 2]; 4], // [regime][win/loss]
    confidence: f32,
}

impl RegimeDetector {
    fn new() -> Self {
        Self {
            transition_matrix: [
                [0.7, 0.1, 0.1, 0.1], // From Neutral
                [0.1, 0.7, 0.1, 0.1], // From Streaky
                [0.1, 0.1, 0.7, 0.1], // From Clustering
                [0.1, 0.1, 0.1, 0.7], // From Trending
            ],
            current_regime: MarketRegime::Neutral,
            history: VecDeque::with_capacity(100),
            emission_probs: [
                [0.48, 0.52], // Neutral: roughly 50/50
                [0.45, 0.55], // Streaky: slight alternation
                [0.40, 0.60], // Clustering: outcomes cluster
                [0.35, 0.65], // Trending: extended patterns
            ],
            confidence: 0.0,
        }
    }

    fn update(&mut self, result: bool) {
        self.history.push_back(result);
        if self.history.len() > 100 {
            self.history.pop_front();
        }

        if self.history.len() < 20 {
            return;
        }

        // Analyze recent patterns
        let recent: Vec<bool> = self.history.iter().rev().take(30).copied().collect();

        // Count alternations (streakiness)
        let mut alternations = 0;
        for i in 0..recent.len() - 1 {
            if recent[i] != recent[i + 1] {
                alternations += 1;
            }
        }
        let alternation_rate = alternations as f32 / (recent.len() - 1) as f32;

        // Count streaks
        let mut max_streak = 1u32;
        let mut current_streak = 1u32;
        for i in 1..recent.len() {
            if recent[i] == recent[i - 1] {
                current_streak += 1;
                max_streak = max_streak.max(current_streak);
            } else {
                current_streak = 1;
            }
        }

        // Win rate
        let wins = recent.par_iter().filter(|&&w| w).count() as f32;
        let win_rate = wins / recent.len() as f32;

        // Determine regime
        self.current_regime = if alternation_rate > 0.6 {
            MarketRegime::Streaky
        } else if max_streak >= 6 {
            MarketRegime::Trending
        } else if win_rate < 0.35 || win_rate > 0.65 {
            MarketRegime::Clustering
        } else {
            MarketRegime::Neutral
        };

        self.confidence = if self.current_regime == MarketRegime::Neutral {
            0.3
        } else {
            0.5 + (alternation_rate.abs() - 0.5).abs()
        };
    }

    fn get_recommended_strategy(&self) -> (f32, bool) {
        // Returns (bet_adjustment, should_reverse)
        match self.current_regime {
            MarketRegime::Neutral => (1.0, false),
            MarketRegime::Streaky => (1.2, true), // Increase bet, reverse prediction
            MarketRegime::Clustering => (0.8, false), // Decrease bet, follow pattern
            MarketRegime::Trending => (1.5, false), // Increase bet, follow trend
        }
    }

    fn clear(&mut self) {
        self.history.clear();
        self.current_regime = MarketRegime::Neutral;
        self.confidence = 0.0;
    }
}

// ============================================================================
// Q-LEARNING FOR BET SIZING
// ============================================================================

#[derive(Debug, Clone)]
struct QLearner {
    q_table: Vec<Vec<f32>>, // [state][action]
    learning_rate: f32,
    discount_factor: f32,
    epsilon: f32,
    states: usize,
    actions: usize,
    last_state: usize,
    last_action: usize,
}

impl QLearner {
    fn new(states: usize, actions: usize) -> Self {
        Self {
            q_table: vec![vec![0.0; actions]; states],
            learning_rate: 0.1,
            discount_factor: 0.95,
            epsilon: 0.15,
            states,
            actions,
            last_state: 0,
            last_action: 0,
        }
    }

    fn get_state(&self, drawdown_pct: f32, streak: i32, volatility: f32, win_rate: f32) -> usize {
        // Discretize state space
        let dd_state = if drawdown_pct > 0.3 {
            3
        } else if drawdown_pct > 0.15 {
            2
        } else if drawdown_pct > 0.05 {
            1
        } else {
            0
        };
        let streak_state = if streak > 3 {
            2
        } else if streak < -3 {
            0
        } else {
            1
        };
        let vol_state = if volatility > 0.3 {
            2
        } else if volatility > 0.15 {
            1
        } else {
            0
        };
        let wr_state = if win_rate > 0.55 {
            2
        } else if win_rate < 0.45 {
            0
        } else {
            1
        };

        // Combine into single state index
        (dd_state * 27 + streak_state * 9 + vol_state * 3 + wr_state).min(self.states - 1)
    }

    fn select_action(&mut self, state: usize) -> usize {
        // Epsilon-greedy with decay
        if rand::rng().random::<f32>() < self.epsilon {
            (rand::rng().random::<f32>() * self.actions as f32) as usize
        } else {
            self.q_table[state]
                .iter()
                .enumerate()
                .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
                .map(|(i, _)| i)
                .unwrap_or(0)
        }
    }

    fn update(&mut self, state: usize, action: usize, reward: f32, next_state: usize) {
        let current_q = self.q_table[state][action];
        let max_next_q = self.q_table[next_state]
            .iter()
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        let new_q = current_q
            + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q);
        self.q_table[state][action] = new_q;
        self.last_state = state;
        self.last_action = action;
    }

    fn get_bet_multiplier(&self, action: usize) -> f32 {
        // Actions represent bet size multipliers
        match action {
            0 => 0.5,  // Very conservative
            1 => 0.75, // Conservative
            2 => 1.0,  // Normal
            3 => 1.25, // Slightly aggressive
            4 => 1.5,  // Aggressive
            _ => 1.0,
        }
    }
}

// ============================================================================
// MONTE CARLO TREE SEARCH FOR ROLL PREDICTION
// ============================================================================

#[derive(Debug, Clone)]
struct MCTSNode {
    visits: u32,
    wins: u32,
    children: HashMap<bool, MCTSNode>, // true = high, false = low
}

impl MCTSNode {
    fn new() -> Self {
        Self {
            visits: 0,
            wins: 0,
            children: HashMap::new(),
        }
    }

    fn ucb1(&self, parent_visits: u32, exploration: f32) -> f32 {
        if self.visits == 0 {
            return f32::MAX;
        }
        let win_rate = self.wins as f32 / self.visits as f32;
        let exploration_term =
            exploration * (parent_visits as f32).ln().sqrt() / self.visits as f32;
        win_rate + exploration_term
    }

    fn best_child(&self, exploration: f32) -> Option<(bool, &MCTSNode)> {
        self.children
            .iter()
            .max_by(|(_, a), (_, b)| {
                let a_ucb = a.ucb1(self.visits, exploration);
                let b_ucb = b.ucb1(self.visits, exploration);
                a_ucb
                    .partial_cmp(&b_ucb)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .map(|(k, v)| (*k, v))
    }
}

#[derive(Debug, Clone)]
struct MCTSPredictor {
    root: MCTSNode,
    history: VecDeque<bool>,
    exploration: f32,
    simulations: u32,
}

impl MCTSPredictor {
    fn new() -> Self {
        Self {
            root: MCTSNode::new(),
            history: VecDeque::with_capacity(100), // Reduced from 1000
            exploration: 1.414,
            simulations: 50, // Reduced from 500 - fewer simulations per move
        }
    }

    fn record_result(&mut self, sequence: &[bool], result: bool) {
        let mut node = &mut self.root;
        node.visits += 1;
        if result {
            node.wins += 1;
        }

        for &outcome in sequence.iter().rev().take(10) {
            let child = node.children.entry(outcome).or_insert_with(MCTSNode::new);
            child.visits += 1;
            if result {
                child.wins += 1;
            }
            node = child;
        }
    }

    fn predict(&self, sequence: &[bool]) -> (f32, bool) {
        // Run simulations to find best path
        let mut node = &self.root;
        let mut depth = 0;

        // Traverse down the tree following the sequence
        for &outcome in sequence.iter().rev().take(10) {
            if let Some(child) = node.children.get(&outcome) {
                node = child;
                depth += 1;
            } else {
                break;
            }
        }

        // If we have enough data, use UCB1 to select
        if node.visits > 10 {
            if let Some((choice, child)) = node.best_child(self.exploration) {
                let confidence = if child.visits > 0 {
                    1.0 - 1.0 / (child.visits as f32).sqrt()
                } else {
                    0.0
                };
                return (confidence, choice);
            }
        }

        // Fallback: use frequency from history
        let recent_wins = self.history.iter().rev().take(20).filter(|&&x| x).count() as f32;
        let recent_count = self.history.len().min(20) as f32;
        let win_rate = if recent_count > 0.0 {
            recent_wins / recent_count
        } else {
            0.5
        };
        (0.1, win_rate > 0.5)
    }

    fn clear(&mut self) {
        self.root = MCTSNode::new();
        self.history.clear();
    }
}

// ============================================================================
// VOLATILITY FORECASTER (GARCH-inspired)
// ============================================================================

#[derive(Debug, Clone)]
struct VolatilityForecaster {
    returns: VecDeque<f32>,
    alpha: f32, // Weight on recent squared returns
    beta: f32,  // Weight on previous variance
    omega: f32, // Long-run variance weight
    long_run_var: f32,
    current_var: f32,
    forecast_horizon: usize,
}

impl VolatilityForecaster {
    fn new() -> Self {
        Self {
            returns: VecDeque::with_capacity(50), // Reduced from 500
            alpha: 0.1,
            beta: 0.85,
            omega: 0.05,
            long_run_var: 0.01,
            current_var: 0.01,
            forecast_horizon: 10, // Reduced from 20
        }
    }

    fn update(&mut self, ret: f32) {
        self.returns.push_back(ret);
        if self.returns.len() > 100 {
            self.returns.pop_front();
        }

        // GARCH(1,1) update
        let squared_ret = ret * ret;
        self.current_var = self.omega * self.long_run_var
            + self.alpha * squared_ret
            + self.beta * self.current_var;
    }

    fn forecast(&self, horizon: usize) -> f32 {
        // Forecast variance over horizon
        let mut var = self.current_var;
        for _ in 0..horizon {
            var = self.omega * self.long_run_var + (self.alpha + self.beta) * var;
        }
        var.sqrt()
    }

    fn current_volatility(&self) -> f32 {
        self.current_var.sqrt()
    }

    fn is_high_volatility(&self) -> bool {
        self.current_volatility() > self.long_run_var.sqrt() * 1.5
    }

    fn is_low_volatility(&self) -> bool {
        self.current_volatility() < self.long_run_var.sqrt() * 0.5
    }

    fn volatility_regime(&self) -> u8 {
        if self.is_high_volatility() {
            2 // High volatility
        } else if self.is_low_volatility() {
            0 // Low volatility
        } else {
            1 // Normal
        }
    }

    fn clear(&mut self) {
        self.returns.clear();
        self.current_var = self.long_run_var;
    }
}

// ============================================================================
// MEAN REVERSION DETECTOR
// ============================================================================

#[derive(Debug, Clone)]
struct MeanReversionDetector {
    prices: VecDeque<f32>,
    lookback: usize,
    z_score_threshold: f32,
    half_life: f32,
}

impl MeanReversionDetector {
    fn new() -> Self {
        Self {
            prices: VecDeque::with_capacity(500), // Was 100
            lookback: 60,                         // Was 30
            z_score_threshold: 2.0,
            half_life: 0.0,
        }
    }

    fn update(&mut self, price: f32) {
        self.prices.push_back(price);
        if self.prices.len() > 100 {
            self.prices.pop_front();
        }
        self.estimate_half_life();
    }

    fn estimate_half_life(&mut self) {
        if self.prices.len() < 20 {
            return;
        }
        // Estimate half-life of mean reversion using ADF-inspired method
        let returns: Vec<f32> = self
            .prices
            .iter()
            .skip(1)
            .zip(self.prices.iter())
            .map(|(curr, prev)| curr - prev)
            .collect();

        let mean_ret: f32 = returns.par_iter().sum::<f32>() / returns.len() as f32;
        let variance: f32 = returns
            .par_iter()
            .map(|r| (r - mean_ret).powi(2))
            .sum::<f32>()
            / returns.len() as f32;

        if variance > 0.0 {
            // Autocorrelation lag-1
            let autocorr: f32 = returns
                .iter()
                .skip(1)
                .zip(returns.iter())
                .map(|(r1, r0)| (r1 - mean_ret) * (r0 - mean_ret))
                .sum::<f32>()
                / (variance * returns.len() as f32);

            // Half-life in periods
            if autocorr > 0.0 && autocorr < 1.0 {
                self.half_life = -(2.0_f32).ln() / autocorr.ln();
            }
        }
    }

    fn z_score(&self) -> f32 {
        if self.prices.len() < self.lookback {
            return 0.0;
        }
        let recent: Vec<f32> = self
            .prices
            .iter()
            .rev()
            .take(self.lookback)
            .copied()
            .collect();
        let mean: f32 = recent.par_iter().sum::<f32>() / recent.len() as f32;
        let variance: f32 =
            recent.par_iter().map(|p| (p - mean).powi(2)).sum::<f32>() / recent.len() as f32;
        let std = variance.sqrt();

        if std > 0.0 {
            let current = self.prices.back().copied().unwrap_or(mean);
            (current - mean) / std
        } else {
            0.0
        }
    }

    fn is_overbought(&self) -> bool {
        self.z_score() > self.z_score_threshold
    }

    fn is_oversold(&self) -> bool {
        self.z_score() < -self.z_score_threshold
    }

    fn reversion_signal(&self) -> f32 {
        let z = self.z_score();
        // Returns signal between -1 and 1
        // Positive means price should revert down (sell/low)
        // Negative means price should revert up (buy/high)
        z.tanh()
    }

    fn clear(&mut self) {
        self.prices.clear();
        self.half_life = 0.0;
    }
}

// ============================================================================
// TREND STRENGTH INDICATOR (ADX-inspired)
// ============================================================================

#[derive(Debug, Clone)]
struct TrendStrength {
    high_low_sequence: VecDeque<(bool, f32)>, // (is_high, multiplier)
    lookback: usize,
    adx: f32,
    plus_di: f32,
    minus_di: f32,
}

impl TrendStrength {
    fn new() -> Self {
        Self {
            high_low_sequence: VecDeque::with_capacity(500), // Was 100
            lookback: 28,                                    // Was 14
            adx: 0.0,
            plus_di: 0.0,
            minus_di: 0.0,
        }
    }

    fn update(&mut self, is_high: bool, multiplier: f32) {
        self.high_low_sequence.push_back((is_high, multiplier));
        if self.high_low_sequence.len() > 100 {
            self.high_low_sequence.pop_front();
        }
        self.calculate_adx();
    }

    fn calculate_adx(&mut self) {
        if self.high_low_sequence.len() < self.lookback {
            return;
        }

        let recent: Vec<(bool, f32)> = self
            .high_low_sequence
            .iter()
            .rev()
            .take(self.lookback)
            .copied()
            .collect();

        // Count consecutive highs and lows
        let high_count = recent.par_iter().filter(|(h, _)| *h).count() as f32;
        let low_count = (self.lookback - high_count as usize) as f32;

        // Directional movement
        let total = self.lookback as f32;
        self.plus_di = (high_count / total * 100.0).min(100.0);
        self.minus_di = (low_count / total * 100.0).min(100.0);

        // ADX measures the strength of the trend regardless of direction
        let di_diff = (self.plus_di - self.minus_di).abs();
        let di_sum = self.plus_di + self.minus_di;

        self.adx = if di_sum > 0.0 {
            (di_diff / di_sum * 100.0).min(100.0)
        } else {
            0.0
        };
    }

    fn trend_strength(&self) -> f32 {
        self.adx / 100.0 // Normalized 0-1
    }

    fn is_trending(&self) -> bool {
        self.adx > 25.0
    }

    fn is_strong_trend(&self) -> bool {
        self.adx > 50.0
    }

    fn trend_direction(&self) -> i8 {
        if self.plus_di > self.minus_di {
            1 // Uptrend (more highs)
        } else if self.minus_di > self.plus_di {
            -1 // Downtrend (more lows)
        } else {
            0 // Sideways
        }
    }

    fn clear(&mut self) {
        self.high_low_sequence.clear();
        self.adx = 0.0;
        self.plus_di = 0.0;
        self.minus_di = 0.0;
    }
}

// ============================================================================
// RISK PARITY POSITION SIZER
// ============================================================================

#[derive(Debug, Clone)]
struct RiskParitySizer {
    target_volatility: f32,
    current_exposure: f32,
    max_exposure: f32,
    min_exposure: f32,
    risk_budget: Vec<f32>,
    corr_matrix: Vec<Vec<f32>>,
}

impl RiskParitySizer {
    fn new() -> Self {
        Self {
            target_volatility: 0.02, // 2% target daily vol
            current_exposure: 1.0,
            max_exposure: 2.0,
            min_exposure: 0.1,
            risk_budget: vec![0.5, 0.3, 0.2], // 50% conservative, 30% moderate, 20% aggressive
            corr_matrix: vec![vec![1.0]],
        }
    }

    fn calculate_position_size(&self, volatility: f32, drawdown: f32, win_rate: f32) -> f32 {
        // Risk parity: adjust position to target constant volatility
        let vol_ratio = if volatility > 0.0 {
            self.target_volatility / volatility
        } else {
            1.0
        };

        // Scale down for drawdown
        let dd_factor = (1.0 - drawdown * 2.0).max(self.min_exposure);

        // Scale based on win rate confidence
        let wr_factor = if win_rate > 0.55 {
            1.1
        } else if win_rate < 0.45 {
            0.9
        } else {
            1.0
        };

        let position = vol_ratio * dd_factor * wr_factor;
        position.clamp(self.min_exposure, self.max_exposure)
    }

    fn update_exposure(&mut self, result: bool, profit_ratio: f32) {
        // Adjust exposure based on recent performance
        let adjustment = if result {
            (1.0 + profit_ratio.abs() * 0.1).min(1.2)
        } else {
            (1.0 - profit_ratio.abs() * 0.1).max(0.5)
        };
        self.current_exposure = (self.current_exposure * 0.9 + adjustment * 0.1)
            .clamp(self.min_exposure, self.max_exposure);
    }

    fn get_risk_budget(&self, idx: usize) -> f32 {
        self.risk_budget.get(idx).copied().unwrap_or(0.33)
    }

    fn clear(&mut self) {
        self.current_exposure = 1.0;
    }
}

// ============================================================================
// ADAPTIVE LEARNING RATE OPTIMIZER
// ============================================================================

#[derive(Debug, Clone)]
struct AdaptiveLearningRate {
    base_lr: f32,
    current_lr: f32,
    gradient_history: VecDeque<f32>,
    momentum: f32,
    velocity: f32,
    beta1: f32,
    beta2: f32,
    epsilon: f32,
}

impl AdaptiveLearningRate {
    fn new() -> Self {
        Self {
            gradient_history: VecDeque::with_capacity(50), // Reduced from 500
            base_lr: 0.01,
            current_lr: 0.01,
            momentum: 0.0,
            velocity: 0.0,
            beta1: 0.9,
            beta2: 0.999,
            epsilon: 1e-8,
        }
    }

    fn compute(&mut self, gradient: f32, step: u32) -> f32 {
        // Adam-like adaptive learning rate
        self.momentum = self.beta1 * self.momentum + (1.0 - self.beta1) * gradient;
        self.velocity = self.beta2 * self.velocity + (1.0 - self.beta2) * gradient * gradient;

        let momentum_corrected = self.momentum / (1.0 - self.beta1.powi(step as i32 + 1));
        let velocity_corrected = self.velocity / (1.0 - self.beta2.powi(step as i32 + 1));

        self.current_lr =
            self.base_lr * momentum_corrected / (velocity_corrected.sqrt() + self.epsilon);

        self.gradient_history.push_back(gradient);
        if self.gradient_history.len() > 100 {
            self.gradient_history.pop_front();
        }

        self.current_lr
    }

    fn get_lr(&self) -> f32 {
        self.current_lr
    }

    fn decay(&mut self, factor: f32) {
        self.base_lr *= factor;
        self.current_lr *= factor;
    }

    fn reset(&mut self) {
        self.current_lr = self.base_lr;
        self.gradient_history.clear();
        self.momentum = 0.0;
        self.velocity = 0.0;
    }
}

// ============================================================================
// SEQUENCE PREDICTOR USING MARKOV CHAINS
// ============================================================================

#[derive(Debug, Clone)]
struct MarkovChain {
    transition_counts: HashMap<[bool; 3], [u32; 2]>, // [low, high] counts
    order: usize,
    smoothing: f32,
}

impl MarkovChain {
    fn new(order: usize) -> Self {
        Self {
            transition_counts: HashMap::new(),
            order,
            smoothing: 0.1,
        }
    }

    fn observe(&mut self, sequence: &[bool], outcome: bool) {
        if sequence.len() >= self.order {
            let key: Vec<bool> = sequence.iter().rev().take(self.order).copied().collect();
            let key_array: [bool; 3] = [
                *key.get(0).unwrap_or(&false),
                *key.get(1).unwrap_or(&false),
                *key.get(2).unwrap_or(&false),
            ];
            let entry = self.transition_counts.entry(key_array).or_insert([0, 0]);
            if outcome {
                entry[1] += 1;
            } else {
                entry[0] += 1;
            }
        }
    }

    fn predict(&self, sequence: &[bool]) -> f32 {
        if sequence.len() < self.order {
            return 0.5;
        }

        let key: Vec<bool> = sequence.iter().rev().take(self.order).copied().collect();
        let key_array: [bool; 3] = [
            *key.get(0).unwrap_or(&false),
            *key.get(1).unwrap_or(&false),
            *key.get(2).unwrap_or(&false),
        ];

        let counts = self.transition_counts.get(&key_array).unwrap_or(&[1, 1]);
        let total = counts[0] + counts[1] + 2; // +2 for smoothing

        // Probability of high (true)
        (counts[1] as f32 + self.smoothing) / (total as f32 + self.smoothing * 2.0)
    }

    fn entropy(&self, sequence: &[bool]) -> f32 {
        let prob = self.predict(sequence);
        if prob <= 0.0 || prob >= 1.0 {
            return 0.0;
        }
        -(prob * prob.log2() + (1.0 - prob) * (1.0 - prob).log2())
    }

    fn clear(&mut self) {
        self.transition_counts.clear();
    }
}

// ============================================================================
// ENSEMBLE FORECASTER (Multiple prediction models)
// ============================================================================

#[derive(Debug, Clone)]
struct EnsembleForecaster {
    // Model weights (learned over time)
    weights: Vec<f32>,
    // Recent predictions from each model
    predictions: VecDeque<Vec<f32>>,
    // Recent actual outcomes
    outcomes: VecDeque<bool>,
    // Number of models
    num_models: usize,
}

impl EnsembleForecaster {
    fn new(num_models: usize) -> Self {
        Self {
            weights: vec![1.0 / num_models as f32; num_models],
            predictions: VecDeque::with_capacity(100),
            outcomes: VecDeque::with_capacity(100),
            num_models,
        }
    }

    fn add_prediction(&mut self, model_predictions: Vec<f32>, actual: bool) {
        self.predictions.push_back(model_predictions);
        self.outcomes.push_back(actual);

        if self.predictions.len() > 100 {
            self.predictions.pop_front();
            self.outcomes.pop_front();
        }

        self.update_weights();
    }

    fn update_weights(&mut self) {
        if self.predictions.len() < 10 {
            return;
        }

        // Calculate Brier score for each model
        let mut scores = vec![0.0f32; self.num_models];
        let n = self.predictions.len() as f32;

        for (preds, &outcome) in self.predictions.iter().zip(self.outcomes.iter()) {
            let target = if outcome { 1.0 } else { 0.0 };
            for (i, &pred) in preds.iter().enumerate() {
                scores[i] += (pred - target).powi(2);
            }
        }

        // Convert scores to weights (lower score = higher weight)
        let total_inverse: f32 = scores.par_iter().map(|&s| 1.0 / (s / n + 0.01)).sum();
        for (i, w) in self.weights.iter_mut().enumerate() {
            *w = (1.0 / (scores[i] / n + 0.01)) / total_inverse;
        }
    }

    fn predict(&self, model_predictions: &[f32]) -> f32 {
        let mut ensemble_pred = 0.0;
        for (i, &pred) in model_predictions.iter().enumerate() {
            if i < self.weights.len() {
                ensemble_pred += pred * self.weights[i];
            }
        }
        ensemble_pred.clamp(0.0, 1.0)
    }

    fn get_confidence(&self) -> f32 {
        // High confidence when weights are skewed (one model dominates)
        let max_weight = self.weights.iter().cloned().fold(0.0f32, f32::max);
        let entropy: f32 = -self
            .weights
            .iter()
            .map(|&w| if w > 0.0 { w * w.ln() } else { 0.0 })
            .sum::<f32>();
        let max_entropy = (self.num_models as f32).ln();
        if max_entropy > 0.0 {
            1.0 - (entropy / max_entropy).abs()
        } else {
            0.5
        }
    }

    fn clear(&mut self) {
        self.weights = vec![1.0 / self.num_models as f32; self.num_models];
        self.predictions.clear();
        self.outcomes.clear();
    }
}

// ============================================================================
// KALMAN FILTER FOR STATE ESTIMATION
// ============================================================================

#[derive(Debug, Clone)]
struct KalmanFilter {
    // State estimate
    state: f32,
    // State covariance
    covariance: f32,
    // Process noise
    process_noise: f32,
    // Measurement noise
    measurement_noise: f32,
    // State history for smoothing
    state_history: VecDeque<f32>,
}

impl KalmanFilter {
    fn new(initial_state: f32, process_noise: f32, measurement_noise: f32) -> Self {
        Self {
            state: initial_state,
            covariance: 1.0,
            process_noise,
            measurement_noise,
            state_history: VecDeque::with_capacity(200), // Increased from 50
        }
    }

    fn predict(&mut self) {
        // Predict step (state transition is identity for simplicity)
        self.covariance += self.process_noise;
    }

    fn update(&mut self, measurement: f32) {
        // Update step
        let kalman_gain = self.covariance / (self.covariance + self.measurement_noise);
        self.state += kalman_gain * (measurement - self.state);
        self.covariance *= (1.0 - kalman_gain);

        self.state_history.push_back(self.state);
        if self.state_history.len() > 50 {
            self.state_history.pop_front();
        }
    }

    fn get_state(&self) -> f32 {
        self.state
    }

    fn get_uncertainty(&self) -> f32 {
        self.covariance.sqrt()
    }

    fn get_trend(&self) -> f32 {
        if self.state_history.len() < 5 {
            return 0.0;
        }
        let recent: Vec<f32> = self.state_history.iter().rev().take(5).copied().collect();
        let older: Vec<f32> = self
            .state_history
            .iter()
            .rev()
            .skip(5)
            .take(5)
            .copied()
            .collect();
        if older.is_empty() {
            return 0.0;
        }
        let recent_mean: f32 = recent.par_iter().sum::<f32>() / recent.len() as f32;
        let older_mean: f32 = older.par_iter().sum::<f32>() / older.len() as f32;
        recent_mean - older_mean
    }

    fn clear(&mut self) {
        self.state = 0.5;
        self.covariance = 1.0;
        self.state_history.clear();
    }
}

// ============================================================================
// PARTICLE FILTER FOR NON-LINEAR ESTIMATION
// ============================================================================

#[derive(Debug, Clone)]
struct Particle {
    state: f32,
    weight: f32,
}

#[derive(Debug, Clone)]
struct ParticleFilter {
    particles: Vec<Particle>,
    num_particles: usize,
    resample_threshold: f32,
}

impl ParticleFilter {
    fn new(num_particles: usize) -> Self {
        let particles = (0..num_particles)
            .map(|_| Particle {
                state: rand::rng().random::<f32>(),
                weight: 1.0 / num_particles as f32,
            })
            .collect();

        Self {
            particles,
            num_particles,
            resample_threshold: 0.5,
        }
    }

    fn predict(&mut self, transition_noise: f32) {
        for particle in &mut self.particles {
            // Random walk with noise
            let noise = (rand::rng().random::<f32>() - 0.5) * 2.0 * transition_noise;
            particle.state = (particle.state + noise).clamp(0.0, 1.0);
        }
    }

    fn update(&mut self, observation: bool) {
        let obs_value = if observation { 1.0 } else { 0.0 };

        for particle in &mut self.particles {
            // Update weight based on likelihood
            let likelihood = 1.0 - (particle.state - obs_value).abs();
            particle.weight *= likelihood;
        }

        // Normalize weights
        let total_weight: f32 = self.particles.par_iter().map(|p| p.weight).sum();
        if total_weight > 0.0 {
            for particle in &mut self.particles {
                particle.weight /= total_weight;
            }
        }

        // Resample if necessary
        let effective_particles: f32 = 1.0
            / self
                .particles
                .par_iter()
                .map(|p| p.weight.powi(2))
                .sum::<f32>();
        if effective_particles < self.num_particles as f32 * self.resample_threshold {
            self.resample();
        }
    }

    fn resample(&mut self) {
        let states: Vec<f32> = self.particles.par_iter().map(|p| p.state).collect();
        let weights: Vec<f32> = self.particles.par_iter().map(|p| p.weight).collect();

        let cumulative: Vec<f32> = weights
            .iter()
            .scan(0.0, |acc, &w| {
                *acc += w;
                Some(*acc)
            })
            .collect();

        self.particles = (0..self.num_particles)
            .map(|_| {
                let r = rand::rng().random::<f32>();
                let idx = cumulative
                    .iter()
                    .position(|&c| c >= r)
                    .unwrap_or(self.num_particles - 1);
                Particle {
                    state: states[idx],
                    weight: 1.0 / self.num_particles as f32,
                }
            })
            .collect();
    }

    fn estimate(&self) -> f32 {
        let total: f32 = self.particles.par_iter().map(|p| p.state * p.weight).sum();
        total.clamp(0.0, 1.0)
    }

    fn variance(&self) -> f32 {
        let mean = self.estimate();
        self.particles
            .iter()
            .map(|p| p.weight * (p.state - mean).powi(2))
            .sum()
    }

    fn clear(&mut self) {
        for particle in &mut self.particles {
            particle.state = rand::rng().random::<f32>();
            particle.weight = 1.0 / self.num_particles as f32;
        }
    }
}

// ============================================================================
// REINFORCEMENT LEARNING AGENT (Deep Q-Network inspired)
// ============================================================================

#[derive(Debug, Clone)]
struct ReplayBuffer {
    states: VecDeque<Vec<f32>>,
    actions: VecDeque<usize>,
    rewards: VecDeque<f32>,
    next_states: VecDeque<Vec<f32>>,
    capacities: usize,
}

impl ReplayBuffer {
    fn new(capacity: usize) -> Self {
        Self {
            states: VecDeque::with_capacity(capacity),
            actions: VecDeque::with_capacity(capacity),
            rewards: VecDeque::with_capacity(capacity),
            next_states: VecDeque::with_capacity(capacity),
            capacities: capacity,
        }
    }

    fn push(&mut self, state: Vec<f32>, action: usize, reward: f32, next_state: Vec<f32>) {
        if self.states.len() >= self.capacities {
            self.states.pop_front();
            self.actions.pop_front();
            self.rewards.pop_front();
            self.next_states.pop_front();
        }
        self.states.push_back(state);
        self.actions.push_back(action);
        self.rewards.push_back(reward);
        self.next_states.push_back(next_state);
    }

    fn sample(
        &self,
        batch_size: usize,
    ) -> Option<(Vec<&Vec<f32>>, Vec<usize>, Vec<f32>, Vec<&Vec<f32>>)> {
        if self.states.len() < batch_size {
            return None;
        }

        let indices: Vec<usize> = (0..self.states.len())
            .filter(|_| rand::rng().random::<f32>() < batch_size as f32 / self.states.len() as f32)
            .take(batch_size)
            .collect();

        if indices.is_empty() {
            return None;
        }

        let states: Vec<&Vec<f32>> = indices.iter().map(|&i| &self.states[i]).collect();
        let actions: Vec<usize> = indices.iter().map(|&i| self.actions[i]).collect();
        let rewards: Vec<f32> = indices.iter().map(|&i| self.rewards[i]).collect();
        let next_states: Vec<&Vec<f32>> = indices.iter().map(|&i| &self.next_states[i]).collect();

        Some((states, actions, rewards, next_states))
    }

    fn clear(&mut self) {
        self.states.clear();
        self.actions.clear();
        self.rewards.clear();
        self.next_states.clear();
    }

    fn len(&self) -> usize {
        self.states.len()
    }
}

#[derive(Debug, Clone)]
struct DQNAgent {
    // Simplified neural network weights (linear model)
    weights: Vec<Vec<f32>>, // [state_dim x num_actions]
    biases: Vec<f32>,
    learning_rate: f32,
    discount_factor: f32,
    epsilon: f32,
    replay_buffer: ReplayBuffer,
    state_dim: usize,
    num_actions: usize,
    target_weights: Vec<Vec<f32>>,
    target_biases: Vec<f32>,
    update_counter: usize,
}

impl DQNAgent {
    fn new(state_dim: usize, num_actions: usize) -> Self {
        // Initialize weights with Xavier initialization
        let scale = (2.0 / (state_dim + num_actions) as f32).sqrt();
        let weights: Vec<Vec<f32>> = (0..state_dim)
            .map(|_| {
                (0..num_actions)
                    .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                    .collect()
            })
            .collect();
        let biases = vec![0.0; num_actions];

        Self {
            weights: weights.clone(),
            biases: biases.clone(),
            learning_rate: 0.001,
            discount_factor: 0.99,
            epsilon: 0.1,
            replay_buffer: ReplayBuffer::new(1000), // Reduced from 100000
            state_dim,
            num_actions,
            target_weights: weights,
            target_biases: biases,
            update_counter: 0,
        }
    }

    fn forward(&self, state: &[f32]) -> Vec<f32> {
        // Linear layer: output = state @ weights + biases
        (0..self.num_actions)
            .map(|j| {
                let sum: f32 = state
                    .iter()
                    .zip(self.weights.iter())
                    .map(|(&s, w)| s * w[j])
                    .sum();
                sum + self.biases[j]
            })
            .collect()
    }

    fn select_action(&mut self, state: &[f32]) -> usize {
        if rand::rng().random::<f32>() < self.epsilon {
            (rand::rng().random::<f32>() * self.num_actions as f32) as usize
        } else {
            let q_values = self.forward(state);
            q_values
                .iter()
                .enumerate()
                .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
                .map(|(i, _)| i)
                .unwrap_or(0)
        }
    }

    fn train(&mut self, batch_size: usize) {
        if let Some((states, actions, rewards, next_states)) = self.replay_buffer.sample(batch_size)
        {
            for i in 0..states.len() {
                let state = states[i];
                let action = actions[i];
                let reward = rewards[i];
                let next_state = next_states[i];

                let q_values = self.forward(state);
                let next_q_values = self.forward(next_state);
                let max_next_q = next_q_values
                    .iter()
                    .cloned()
                    .fold(f32::NEG_INFINITY, f32::max);
                let target = reward + self.discount_factor * max_next_q;

                // Gradient descent on the selected action
                let error = target - q_values[action];
                for (j, &s) in state.iter().enumerate() {
                    self.weights[j][action] += self.learning_rate * error * s;
                }
                self.biases[action] += self.learning_rate * error;
            }
        }

        self.update_counter += 1;
        if self.update_counter % 100 == 0 {
            // Update target network
            self.target_weights = self.weights.clone();
            self.target_biases = self.biases.clone();
        }
    }

    fn push_experience(
        &mut self,
        state: Vec<f32>,
        action: usize,
        reward: f32,
        next_state: Vec<f32>,
    ) {
        self.replay_buffer.push(state, action, reward, next_state);
    }

    fn decay_epsilon(&mut self, decay: f32) {
        self.epsilon *= decay;
        self.epsilon = self.epsilon.max(0.01);
    }

    fn clear(&mut self) {
        self.replay_buffer.clear();
        self.epsilon = 0.1;
        self.update_counter = 0;
    }
}

// ============================================================================
// MULTI-ARMED BANDIT WITH CONTEXT (LinUCB)
// ============================================================================

#[derive(Debug, Clone)]
struct LinUCBArm {
    // d-dimensional feature vector
    d: usize,
    // A_a = D_a^T * D_a + I_d (d x d matrix flattened)
    a_matrix: Vec<f32>,
    // b_a = D_a^T * c_a (d-dimensional vector)
    b_vector: Vec<f32>,
    // Number of times pulled
    pulls: u32,
    // Average reward
    avg_reward: f32,
}

impl LinUCBArm {
    fn new(d: usize) -> Self {
        // Initialize A_a as identity matrix
        let mut a_matrix = vec![0.0; d * d];
        for i in 0..d {
            a_matrix[i * d + i] = 1.0;
        }
        Self {
            d,
            a_matrix,
            b_vector: vec![0.0; d],
            pulls: 0,
            avg_reward: 0.0,
        }
    }

    fn update(&mut self, context: &[f32], reward: f32) {
        // Use min of dimension and context length
        let n = self.d.min(context.len());
        // Update A_a += x * x^T
        for i in 0..n {
            for j in 0..n {
                self.a_matrix[i * self.d + j] += context[i] * context[j];
            }
        }
        // Update b_a += x * r
        for i in 0..n {
            self.b_vector[i] += context[i] * reward;
        }
        self.pulls += 1;
        let alpha = 0.1;
        self.avg_reward = alpha * reward + (1.0 - alpha) * self.avg_reward;
    }

    fn get_ucb(&self, context: &[f32], alpha: f32) -> f32 {
        // Use min of dimension and context length
        let n = self.d.min(context.len());

        // Simplified UCB calculation (approximate inverse)
        // theta_a = A_a^-1 * b_a (we approximate this)
        let mut theta = vec![0.0; self.d];

        // Simple iterative approximation of A^-1 * b
        for _ in 0..10 {
            let mut new_theta = vec![0.0; self.d];
            for i in 0..n {
                for j in 0..n {
                    new_theta[i] += self.a_matrix[i * self.d + j] * theta[j];
                }
                new_theta[i] = 2.0 * self.b_vector[i] - new_theta[i];
            }
            theta = new_theta;
        }

        // Calculate x^T * theta
        let mut linear_term = 0.0;
        for i in 0..n {
            linear_term += context[i] * theta[i];
        }

        // Calculate x^T * A^-1 * x (approximate)
        let mut variance_term = 0.0;
        for i in 0..n {
            variance_term += context[i] * context[i] / (self.a_matrix[i * self.d + i] + 0.01);
        }

        linear_term + alpha * variance_term.sqrt()
    }
}

#[derive(Debug, Clone)]
struct LinUCBDisjoint {
    arms: Vec<LinUCBArm>,
    context_dim: usize,
    alpha: f32,
}

impl LinUCBDisjoint {
    fn new(num_arms: usize, context_dim: usize, alpha: f32) -> Self {
        Self {
            arms: (0..num_arms)
                .map(|_| LinUCBArm::new(context_dim * 4))
                .collect(), // 4x context
            context_dim,
            alpha,
        }
    }

    fn select_arm(&self, context: &[f32]) -> usize {
        self.arms
            .iter()
            .enumerate()
            .map(|(i, arm)| (i, arm.get_ucb(context, self.alpha)))
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(0)
    }

    fn update(&mut self, arm_idx: usize, context: &[f32], reward: f32) {
        if arm_idx < self.arms.len() {
            self.arms[arm_idx].update(context, reward);
        }
    }

    fn clear(&mut self) {
        for arm in &mut self.arms {
            *arm = LinUCBArm::new(self.context_dim * 4);
        }
    }
}

// ============================================================================
// LSTM-STYLE SEQUENCE MODEL
// ============================================================================

#[derive(Debug, Clone)]
struct LSTMCell {
    // Input, forget, output, candidate gates
    w_i: Vec<f32>, // Input weights
    w_f: Vec<f32>, // Forget weights
    w_o: Vec<f32>, // Output weights
    w_c: Vec<f32>, // Candidate weights
    b_i: f32,
    b_f: f32,
    b_o: f32,
    b_c: f32,
    hidden_size: usize,
}

impl LSTMCell {
    fn new(input_size: usize, hidden_size: usize) -> Self {
        let scale = (2.0 / (input_size + hidden_size) as f32).sqrt();
        Self {
            w_i: (0..input_size + hidden_size)
                .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                .collect(),
            w_f: (0..input_size + hidden_size)
                .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                .collect(),
            w_o: (0..input_size + hidden_size)
                .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                .collect(),
            w_c: (0..input_size + hidden_size)
                .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                .collect(),
            b_i: 0.0,
            b_f: 1.0, // Forget bias initialized to 1 for gradient flow
            b_o: 0.0,
            b_c: 0.0,
            hidden_size,
        }
    }

    fn forward(&self, input: &[f32], h_prev: &[f32], c_prev: &[f32]) -> (Vec<f32>, Vec<f32>) {
        // Concatenate input and hidden
        let xh: Vec<f32> = input.iter().chain(h_prev.iter()).copied().collect();

        let mut h_new = vec![0.0; self.hidden_size];
        let mut c_new = vec![0.0; self.hidden_size];

        // Simplified: process each hidden unit
        for i in 0..self.hidden_size {
            let i_gate = Self::sigmoid(&xh, &self.w_i, self.b_i);
            let f_gate = Self::sigmoid(&xh, &self.w_f, self.b_f);
            let o_gate = Self::sigmoid(&xh, &self.w_o, self.b_o);
            let c_candidate = Self::tanh_activation(&xh, &self.w_c, self.b_c);

            c_new[i] = f_gate * c_prev[i] + i_gate * c_candidate;
            h_new[i] = o_gate * Self::tanh(c_new[i]);
        }

        (h_new, c_new)
    }

    fn sigmoid(x: &[f32], w: &[f32], b: f32) -> f32 {
        let sum: f32 = x.iter().zip(w.iter()).map(|(xi, wi)| xi * wi).sum();
        1.0 / (1.0 + (-(sum + b)).exp())
    }

    fn tanh_activation(x: &[f32], w: &[f32], b: f32) -> f32 {
        let sum: f32 = x.iter().zip(w.iter()).map(|(xi, wi)| xi * wi).sum();
        Self::tanh(sum + b)
    }

    fn tanh(x: f32) -> f32 {
        x.tanh()
    }
}

#[derive(Debug, Clone)]
struct LSTMSequenceModel {
    cell: LSTMCell,
    hidden: Vec<f32>,
    cell_state: Vec<f32>,
    sequence_length: usize,
}

impl LSTMSequenceModel {
    fn new(input_size: usize, hidden_size: usize) -> Self {
        Self {
            cell: LSTMCell::new(input_size, hidden_size),
            hidden: vec![0.0; hidden_size],
            cell_state: vec![0.0; hidden_size],
            sequence_length: 50, // Increased from 20
        }
    }

    fn process_sequence(&mut self, sequence: &[f32]) -> Vec<f32> {
        // Reset hidden state
        self.hidden.fill(0.0);
        self.cell_state.fill(0.0);

        // Process sequence in chunks of input_size
        let input_size = 10;
        for chunk in sequence.chunks(input_size).take(self.sequence_length) {
            let padded: Vec<f32> = chunk
                .iter()
                .chain(std::iter::repeat(&0.0))
                .take(input_size)
                .copied()
                .collect();
            let (h_new, c_new) = self.cell.forward(&padded, &self.hidden, &self.cell_state);
            self.hidden = h_new;
            self.cell_state = c_new;
        }

        self.hidden.clone()
    }

    fn predict(&mut self, sequence: &[f32]) -> f32 {
        let hidden = self.process_sequence(sequence);
        // Simple linear output
        let sum: f32 = hidden.par_iter().sum();
        Self::sigmoid_output(sum / hidden.len() as f32)
    }

    fn sigmoid_output(x: f32) -> f32 {
        1.0 / (1.0 + (-x).exp())
    }

    fn clear(&mut self) {
        self.hidden.fill(0.0);
        self.cell_state.fill(0.0);
    }
}

// ============================================================================
// TRANSFORMER-STYLE SELF-ATTENTION
// ============================================================================

#[derive(Debug, Clone)]
struct SelfAttention {
    d_k: usize,
    d_v: usize,
    w_q: Vec<Vec<f32>>, // [seq_len x d_k]
    w_k: Vec<Vec<f32>>,
    w_v: Vec<Vec<f32>>,
    w_o: Vec<Vec<f32>>,
    seq_len: usize,
}

impl SelfAttention {
    fn new(d_model: usize, seq_len: usize) -> Self {
        let scale = (2.0 / d_model as f32).sqrt();
        Self {
            d_k: d_model,
            d_v: d_model,
            w_q: (0..seq_len)
                .map(|_| {
                    (0..d_model)
                        .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                        .collect()
                })
                .collect(),
            w_k: (0..seq_len)
                .map(|_| {
                    (0..d_model)
                        .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                        .collect()
                })
                .collect(),
            w_v: (0..seq_len)
                .map(|_| {
                    (0..d_model)
                        .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                        .collect()
                })
                .collect(),
            w_o: (0..d_model)
                .map(|_| {
                    (0..d_model)
                        .map(|_| (rand::rng().random::<f32>() - 0.5) * 2.0 * scale)
                        .collect()
                })
                .collect(),
            seq_len,
        }
    }

    fn attention(
        &self,
        queries: &[Vec<f32>],
        keys: &[Vec<f32>],
        values: &[Vec<f32>],
    ) -> Vec<Vec<f32>> {
        let n = queries.len();
        let mut output = vec![vec![0.0; self.d_v]; n];

        for i in 0..n {
            // Compute attention scores
            let mut scores: Vec<f32> = (0..n)
                .map(|j| {
                    let dot: f32 = queries[i]
                        .iter()
                        .zip(keys[j].iter())
                        .map(|(q, k)| q * k)
                        .sum();
                    dot / (self.d_k as f32).sqrt()
                })
                .collect();

            // Softmax
            let max_score = scores.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
            let exp_sum: f32 = scores.par_iter().map(|s| (s - max_score).exp()).sum();
            for s in &mut scores {
                *s = (*s - max_score).exp() / exp_sum;
            }

            // Weighted sum of values
            for j in 0..n {
                for k in 0..self.d_v {
                    output[i][k] += scores[j] * values[j][k];
                }
            }
        }

        output
    }

    fn forward(&self, x: &[Vec<f32>]) -> Vec<Vec<f32>> {
        // Project to Q, K, V (simplified - single head)
        let seq_len = x.len().min(self.seq_len);
        let mut q = vec![vec![0.0; self.d_k]; seq_len];
        let mut k = vec![vec![0.0; self.d_k]; seq_len];
        let mut v = vec![vec![0.0; self.d_v]; seq_len];

        for i in 0..seq_len {
            for j in 0..self.d_k.min(x[i].len()) {
                let x_val = x[i].get(j).copied().unwrap_or(0.0);
                q[i][j] = x_val * self.w_q[i % self.seq_len].get(j).copied().unwrap_or(1.0);
                k[i][j] = x_val * self.w_k[i % self.seq_len].get(j).copied().unwrap_or(1.0);
                v[i][j] = x_val * self.w_v[i % self.seq_len].get(j).copied().unwrap_or(1.0);
            }
        }

        self.attention(&q, &k, &v)
    }

    fn predict(&self, sequence: &[f32]) -> f32 {
        // Convert sequence to 2D
        let d_model = 8;
        let x: Vec<Vec<f32>> = sequence
            .chunks(d_model)
            .map(|chunk| chunk.to_vec())
            .collect();

        if x.is_empty() {
            return 0.5;
        }

        let attended = self.forward(&x);

        // Pool and predict
        if let Some(last) = attended.last() {
            let sum: f32 = last.par_iter().sum();
            let mean = sum / last.len().max(1) as f32;
            1.0 / (1.0 + (-mean).exp())
        } else {
            0.5
        }
    }
}

// ============================================================================
// GAUSSIAN PROCESS FOR UNCERTAINTY ESTIMATION
// ============================================================================

#[derive(Debug, Clone)]
struct GaussianProcess {
    // Training data
    x_train: Vec<Vec<f32>>,
    y_train: Vec<f32>,
    // Kernel hyperparameters
    length_scale: f32,
    signal_variance: f32,
    noise_variance: f32,
    // Precomputed values
    k_inv: Vec<Vec<f32>>,
    alpha: Vec<f32>,
    max_samples: usize,
}

impl GaussianProcess {
    fn new(length_scale: f32, signal_variance: f32, noise_variance: f32) -> Self {
        Self {
            x_train: Vec::with_capacity(100), // Reduced from 2000 - GP is O(n^3)
            y_train: Vec::with_capacity(100), // Reduced from 2000
            length_scale,
            signal_variance,
            noise_variance,
            k_inv: Vec::new(),
            alpha: Vec::new(),
            max_samples: 100, // Reduced from 2000
        }
    }

    fn rbf_kernel(&self, x1: &[f32], x2: &[f32]) -> f32 {
        let sq_dist: f32 = x1.iter().zip(x2.iter()).map(|(a, b)| (a - b).powi(2)).sum();
        self.signal_variance * (-0.5 * sq_dist / self.length_scale.powi(2)).exp()
    }

    fn add_sample(&mut self, x: Vec<f32>, y: f32) {
        if self.x_train.len() >= self.max_samples {
            self.x_train.remove(0);
            self.y_train.remove(0);
        }
        self.x_train.push(x);
        self.y_train.push(y);
        self.update_cache();
    }

    fn update_cache(&mut self) {
        let n = self.x_train.len();
        if n == 0 {
            return;
        }

        // Compute K matrix
        let mut k = vec![vec![0.0; n]; n];
        for i in 0..n {
            for j in 0..n {
                k[i][j] = self.rbf_kernel(&self.x_train[i], &self.x_train[j]);
                if i == j {
                    k[i][j] += self.noise_variance;
                }
            }
        }

        // Simple matrix inversion using Gauss-Jordan elimination
        self.k_inv = self.invert_matrix(&k);

        // Compute alpha = K^-1 * y
        self.alpha = vec![0.0; n];
        for i in 0..n {
            for j in 0..n {
                self.alpha[i] += self
                    .k_inv
                    .get(i)
                    .and_then(|row| row.get(j))
                    .copied()
                    .unwrap_or(0.0)
                    * self.y_train.get(j).copied().unwrap_or(0.0);
            }
        }
    }

    fn invert_matrix(&self, matrix: &[Vec<f32>]) -> Vec<Vec<f32>> {
        let n = matrix.len();
        if n == 0 {
            return vec![];
        }

        // Augment matrix with identity
        let mut aug = vec![vec![0.0; 2 * n]; n];
        for i in 0..n {
            for j in 0..n {
                aug[i][j] = matrix[i][j];
            }
            aug[i][n + i] = 1.0;
        }

        // Forward elimination with partial pivoting
        for i in 0..n {
            // Find pivot
            let mut max_row = i;
            for k in (i + 1)..n {
                if aug[k][i].abs() > aug[max_row][i].abs() {
                    max_row = k;
                }
            }
            // Swap rows
            aug.swap(i, max_row);

            if aug[i][i].abs() < 1e-10 {
                continue;
            }

            // Scale pivot row
            let pivot = aug[i][i];
            for j in 0..(2 * n) {
                aug[i][j] /= pivot;
            }

            // Eliminate column
            for k in 0..n {
                if k != i {
                    let factor = aug[k][i];
                    for j in 0..(2 * n) {
                        aug[k][j] -= factor * aug[i][j];
                    }
                }
            }
        }

        // Extract inverse
        (0..n).map(|i| aug[i][n..].to_vec()).collect()
    }

    fn predict(&self, x: &[f32]) -> (f32, f32) {
        if self.x_train.is_empty() {
            return (0.5, 1.0);
        }

        let n = self.x_train.len();

        // Compute k* (kernel between test point and training points)
        let k_star: Vec<f32> = self
            .x_train
            .iter()
            .map(|xi| self.rbf_kernel(x, xi))
            .collect();

        // Mean prediction: k*^T * alpha
        let mean: f32 = k_star
            .iter()
            .zip(self.alpha.iter())
            .map(|(k, a)| k * a)
            .sum();

        // Variance prediction (simplified)
        let k_xx = self.signal_variance;
        let variance = k_star
            .iter()
            .zip(self.k_inv.iter())
            .map(|(ks, k_inv_row)| {
                ks * k_inv_row
                    .iter()
                    .zip(k_star.iter())
                    .map(|(inv, ks2)| inv * ks2)
                    .sum::<f32>()
            })
            .sum::<f32>();
        let variance = (k_xx - variance).max(0.01);

        (Self::sigmoid(mean), variance.sqrt())
    }

    fn sigmoid(x: f32) -> f32 {
        1.0 / (1.0 + (-x).exp())
    }

    fn clear(&mut self) {
        self.x_train.clear();
        self.y_train.clear();
        self.k_inv.clear();
        self.alpha.clear();
    }
}

// ============================================================================
// POLICY GRADIENT AGENT (REINFORCE with Baseline)
// ============================================================================

#[derive(Debug, Clone)]
struct PolicyGradientAgent {
    // Policy parameters (logits for each action)
    policy_logits: Vec<f32>,
    // Value function parameters (for baseline)
    value_weights: Vec<f32>,
    // Action history
    action_history: VecDeque<(Vec<f32>, usize, f32)>, // (state, action, reward)
    // Learning rates
    policy_lr: f32,
    value_lr: f32,
    // Discount factor
    gamma: f32,
    // Number of actions
    num_actions: usize,
}

impl PolicyGradientAgent {
    fn new(num_actions: usize, state_dim: usize) -> Self {
        Self {
            policy_logits: vec![0.0; num_actions],
            value_weights: vec![0.0; state_dim],
            action_history: VecDeque::with_capacity(200), // Reduced from 5000
            policy_lr: 0.01,
            value_lr: 0.01,
            gamma: 0.99,
            num_actions,
        }
    }

    fn softmax(logits: &[f32]) -> Vec<f32> {
        let max_logit = logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let exp_sum: f32 = logits.par_iter().map(|&l| (l - max_logit).exp()).sum();
        logits
            .iter()
            .map(|&l| (l - max_logit).exp() / exp_sum)
            .collect()
    }

    fn select_action(&self, _state: &[f32]) -> usize {
        let probs = Self::softmax(&self.policy_logits);
        let r = rand::rng().random::<f32>();
        let mut cumsum = 0.0;
        for (i, &p) in probs.iter().enumerate() {
            cumsum += p;
            if r < cumsum {
                return i;
            }
        }
        self.num_actions - 1
    }

    fn value_estimate(&self, state: &[f32]) -> f32 {
        state
            .iter()
            .zip(self.value_weights.iter())
            .map(|(s, w)| s * w)
            .sum()
    }

    fn store_transition(&mut self, state: Vec<f32>, action: usize, reward: f32) {
        self.action_history.push_back((state, action, reward));
    }

    fn update(&mut self) {
        if self.action_history.is_empty() {
            return;
        }

        // Calculate returns with discount
        let mut returns = vec![0.0; self.action_history.len()];
        let mut running_return = 0.0;
        for (i, (_, _, r)) in self.action_history.iter().enumerate().rev() {
            running_return = r + self.gamma * running_return;
            returns[i] = running_return;
        }

        // Normalize returns
        let mean_return = returns.par_iter().sum::<f32>() / returns.len() as f32;
        let std_return = (returns
            .iter()
            .map(|r| (r - mean_return).powi(2))
            .sum::<f32>()
            / returns.len() as f32)
            .sqrt();
        let normalized_returns: Vec<f32> = returns
            .iter()
            .map(|r| (r - mean_return) / (std_return + 1e-8))
            .collect();

        // Update policy and value
        for ((state, action, _), &advantage) in
            self.action_history.iter().zip(normalized_returns.iter())
        {
            // Policy gradient
            let probs = Self::softmax(&self.policy_logits);
            for i in 0..self.num_actions {
                let grad = if i == *action {
                    1.0 - probs[i]
                } else {
                    -probs[i]
                };
                self.policy_logits[i] += self.policy_lr * advantage * grad;
            }

            // Value function update
            let value = self.value_estimate(state);
            let td_error = advantage - value;
            for (i, &s) in state.iter().enumerate() {
                if i < self.value_weights.len() {
                    self.value_weights[i] += self.value_lr * td_error * s;
                }
            }
        }

        self.action_history.clear();
    }

    fn clear(&mut self) {
        self.action_history.clear();
        self.policy_logits.fill(0.0);
        self.value_weights.fill(0.0);
    }
}

// ============================================================================
// EVOLUTION STRATEGIES (OpenAI-ES style)
// ============================================================================

#[derive(Debug, Clone)]
struct EvolutionStrategies {
    // Parameters to optimize
    params: Vec<f32>,
    // Learning rate
    learning_rate: f32,
    // Noise standard deviation
    sigma: f32,
    // Population size for estimation
    population_size: usize,
    // History of rewards
    reward_history: VecDeque<f32>,
    // Best params seen
    best_params: Vec<f32>,
    best_reward: f32,
}

impl EvolutionStrategies {
    fn new(param_dim: usize) -> Self {
        Self {
            params: vec![0.0; param_dim],
            learning_rate: 0.01,
            sigma: 0.1,
            population_size: 20,                         // Reduced from 50
            reward_history: VecDeque::with_capacity(50), // Reduced from 500
            best_params: vec![0.0; param_dim],
            best_reward: f32::NEG_INFINITY,
        }
    }

    fn sample_noise(&self) -> Vec<f32> {
        (0..self.params.len())
            .map(|_| rand::rng().random::<f32>() * 2.0 - 1.0)
            .collect()
    }

    fn perturb_params(&self, noise: &[f32], direction: i32) -> Vec<f32> {
        self.params
            .iter()
            .zip(noise.iter())
            .map(|(&p, &n)| p + direction as f32 * self.sigma * n)
            .collect()
    }

    fn estimate_gradient(&mut self, evaluate: impl Fn(&[f32]) -> f32) {
        let mut gradient = vec![0.0; self.params.len()];

        for _ in 0..self.population_size {
            let noise = self.sample_noise();

            // Evaluate positive perturbation
            let pos_params = self.perturb_params(&noise, 1);
            let pos_reward = evaluate(&pos_params);

            // Evaluate negative perturbation
            let neg_params = self.perturb_params(&noise, -1);
            let neg_reward = evaluate(&neg_params);

            // Accumulate gradient estimate
            for (g, &n) in gradient.iter_mut().zip(noise.iter()) {
                *g += (pos_reward - neg_reward) * n;
            }
        }

        // Normalize gradient
        let n = self.population_size as f32;
        for g in &mut gradient {
            *g /= 2.0 * n * self.sigma;
        }

        // Update parameters
        for (p, &g) in self.params.iter_mut().zip(gradient.iter()) {
            *p += self.learning_rate * g;
        }
    }

    fn get_params(&self) -> &[f32] {
        &self.params
    }

    fn set_params(&mut self, params: Vec<f32>) {
        self.params = params;
    }

    fn update_best(&mut self, reward: f32) {
        self.reward_history.push_back(reward);
        if reward > self.best_reward {
            self.best_reward = reward;
            self.best_params = self.params.clone();
        }
    }

    fn get_best_reward(&self) -> f32 {
        self.best_reward
    }

    fn clear(&mut self) {
        self.params.fill(0.0);
        self.reward_history.clear();
        self.best_params.fill(0.0);
        self.best_reward = f32::NEG_INFINITY;
    }
}

// ============================================================================
// BANDIT CONTEXT BUILDER
// ============================================================================

#[derive(Debug, Clone)]
struct ContextBuilder {
    // Normalization parameters
    means: Vec<f32>,
    stds: Vec<f32>,
    // Feature count
    num_features: usize,
}

impl ContextBuilder {
    fn new(num_features: usize) -> Self {
        Self {
            means: vec![0.5; num_features],
            stds: vec![0.5; num_features],
            num_features,
        }
    }

    fn build_context(
        &self,
        balance: f32,
        initial_balance: f32,
        win_streak: u32,
        loss_streak: u32,
        multiplier: f32,
        drawdown: f32,
        volatility: f32,
        win_rate: f32,
        recent_profit: f32,
        trend: f32,
        regime: u8,
        confidence: f32,
    ) -> Vec<f32> {
        let mut context = vec![0.0; self.num_features];

        context[0] = balance / initial_balance.max(1e-8); // Normalized balance
        context[1] = (win_streak as f32).tanh(); // Win streak
        context[2] = (loss_streak as f32).tanh(); // Loss streak
        context[3] = (multiplier / 50.0).min(1.0); // Normalized multiplier
        context[4] = drawdown; // Drawdown
        context[5] = volatility; // Volatility
        context[6] = win_rate * 2.0 - 1.0; // Win rate centered
        context[7] = recent_profit.tanh(); // Recent profit
        context[8] = trend; // Trend direction
        context[9] = match regime {
            0 => 0.0,
            1 => 0.5,
            2 => -0.5,
            _ => 0.0,
        }; // Regime encoding
        context[10] = confidence * 2.0 - 1.0; // Confidence

        // Normalize
        for i in 0..self.num_features.min(context.len()) {
            context[i] = (context[i] - self.means[i]) / self.stds[i].max(1e-8);
            context[i] = context[i].clamp(-3.0, 3.0);
        }

        context
    }

    fn update_stats(&mut self, contexts: &[Vec<f32>]) {
        if contexts.is_empty() {
            return;
        }

        for i in 0..self.num_features {
            let sum: f32 = contexts
                .iter()
                .map(|c| c.get(i).copied().unwrap_or(0.0))
                .sum();
            self.means[i] = sum / contexts.len() as f32;

            let sq_sum: f32 = contexts
                .iter()
                .map(|c| (c.get(i).copied().unwrap_or(0.0) - self.means[i]).powi(2))
                .sum();
            self.stds[i] = (sq_sum / contexts.len() as f32).sqrt().max(0.01);
        }
    }
}

// ============================================================================
// HYPERDIMENSIONAL COMPUTING (Vector Symbolic Architectures)
// ============================================================================

#[derive(Debug, Clone)]
struct HDVector {
    data: Vec<i8>, // Bipolar vector: -1 or +1
    dimension: usize,
}

impl HDVector {
    fn new(dimension: usize) -> Self {
        Self {
            data: (0..dimension)
                .map(|_| {
                    if rand::rng().random::<f32>() > 0.5 {
                        1
                    } else {
                        -1
                    }
                })
                .collect(),
            dimension,
        }
    }

    fn from_binary(bits: &[bool], dimension: usize) -> Self {
        let mut data = vec![-1; dimension];
        for (i, &bit) in bits.iter().take(dimension).enumerate() {
            data[i] = if bit { 1 } else { -1 };
        }
        Self { data, dimension }
    }

    fn zero(dimension: usize) -> Self {
        Self {
            data: vec![0; dimension],
            dimension,
        }
    }

    fn bind(&self, other: &HDVector) -> HDVector {
        HDVector {
            data: self
                .data
                .iter()
                .zip(other.data.iter())
                .map(|(a, b)| a * b)
                .collect(),
            dimension: self.dimension,
        }
    }

    fn bundle(&self, other: &HDVector) -> HDVector {
        HDVector {
            data: self
                .data
                .iter()
                .zip(other.data.iter())
                .map(|(a, b)| a + b)
                .collect(),
            dimension: self.dimension,
        }
    }

    fn normalize(&self) -> HDVector {
        HDVector {
            data: self
                .data
                .iter()
                .map(|&x| {
                    if x > 0 {
                        1
                    } else if x < 0 {
                        -1
                    } else {
                        0
                    }
                })
                .collect(),
            dimension: self.dimension,
        }
    }

    fn cosine_similarity(&self, other: &HDVector) -> f32 {
        let dot: i32 = self
            .data
            .iter()
            .zip(other.data.iter())
            .map(|(a, b)| (*a as i32) * (*b as i32))
            .sum();
        let mag1: f32 = (self.data.par_iter().map(|x| (x * x) as i32).sum::<i32>() as f32).sqrt();
        let mag2: f32 = (other.data.par_iter().map(|x| (x * x) as i32).sum::<i32>() as f32).sqrt();
        if mag1 > 0.0 && mag2 > 0.0 {
            dot as f32 / (mag1 * mag2)
        } else {
            0.0
        }
    }

    fn hamming_distance(&self, other: &HDVector) -> usize {
        self.data
            .iter()
            .zip(other.data.iter())
            .filter(|(a, b)| a != b)
            .count()
    }
}

#[derive(Debug, Clone)]
struct HyperdimensionalMemory {
    dimension: usize,
    item_memory: HashMap<String, HDVector>,
    sequence_memory: Vec<HDVector>,
    context_vectors: Vec<HDVector>,
}

impl HyperdimensionalMemory {
    fn new(dimension: usize) -> Self {
        Self {
            dimension,
            item_memory: HashMap::new(),
            sequence_memory: Vec::with_capacity(200), // Reduced from 5000
            context_vectors: Vec::new(),
        }
    }

    fn encode_item(&mut self, key: &str) -> HDVector {
        if let Some(vec) = self.item_memory.get(key) {
            vec.clone()
        } else {
            let vec = HDVector::new(self.dimension);
            self.item_memory.insert(key.to_string(), vec.clone());
            vec
        }
    }

    fn encode_sequence(&mut self, items: &[&str]) -> HDVector {
        let mut result = HDVector::zero(self.dimension);
        let mut position = HDVector::new(self.dimension);

        for item in items.iter().rev() {
            let item_vec = self.encode_item(item);
            // Bind item with position, then bundle into result
            let encoded = item_vec.bind(&position);
            result = result.bundle(&encoded);
            // Rotate position for next item
            position.data.rotate_right(1);
        }

        self.sequence_memory.push(result.clone());
        result.normalize()
    }

    fn query_similar(&self, query: &HDVector, k: usize) -> Vec<(usize, f32)> {
        let mut similarities: Vec<(usize, f32)> = self
            .sequence_memory
            .iter()
            .enumerate()
            .map(|(i, seq)| (i, query.cosine_similarity(seq)))
            .collect();

        similarities.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        similarities.into_iter().take(k).collect()
    }

    fn clear(&mut self) {
        self.item_memory.clear();
        self.sequence_memory.clear();
        self.context_vectors.clear();
    }
}

// ============================================================================
// RESERVOIR COMPUTING (Echo State Network)
// ============================================================================

#[derive(Debug, Clone)]
struct Reservoir {
    // Reservoir weights (fixed random)
    w_reservoir: Vec<Vec<f32>>,
    // Output weights (trained)
    w_output: Vec<Vec<f32>>,
    // Reservoir state
    state: Vec<f32>,
    // Input weights
    w_input: Vec<Vec<f32>>,
    // Parameters
    spectral_radius: f32,
    leak_rate: f32,
    input_size: usize,
    reservoir_size: usize,
    output_size: usize,
}

impl Reservoir {
    fn new(
        input_size: usize,
        reservoir_size: usize,
        output_size: usize,
        spectral_radius: f32,
        leak_rate: f32,
    ) -> Self {
        // Initialize reservoir weights with spectral radius scaling
        let mut w_reservoir = vec![vec![0.0; reservoir_size]; reservoir_size];
        for i in 0..reservoir_size {
            for j in 0..reservoir_size {
                let rand_val = rand::rng().random::<f32>() * 2.0 - 1.0;
                w_reservoir[i][j] = rand_val / reservoir_size as f32;
            }
        }
        // Scale to desired spectral radius
        // (simplified - actual implementation would compute eigenvalues)
        for row in &mut w_reservoir {
            for val in row.iter_mut() {
                *val *= spectral_radius;
            }
        }

        let w_input = (0..reservoir_size)
            .map(|_| {
                (0..input_size)
                    .map(|_| rand::rng().random::<f32>() * 2.0 - 1.0)
                    .collect()
            })
            .collect();

        Self {
            w_reservoir,
            w_output: vec![vec![0.0; output_size]; reservoir_size],
            state: vec![0.0; reservoir_size],
            w_input,
            spectral_radius,
            leak_rate,
            input_size,
            reservoir_size,
            output_size,
        }
    }

    fn tanh(x: f32) -> f32 {
        x.tanh()
    }

    fn update(&mut self, input: &[f32]) {
        let mut new_state = vec![0.0; self.reservoir_size];

        // x(t) = (1 - α) * x(t-1) + α * tanh(W_r * x(t-1) + W_in * u(t))
        for i in 0..self.reservoir_size {
            // Reservoir contribution
            let mut sum = 0.0;
            for j in 0..self.reservoir_size {
                sum += self.w_reservoir[i][j] * self.state[j];
            }

            // Input contribution
            for (j, &inp) in input.iter().enumerate() {
                if j < self.input_size {
                    sum += self.w_input[i][j] * inp;
                }
            }

            // Leaky integration
            new_state[i] =
                (1.0 - self.leak_rate) * self.state[i] + self.leak_rate * Self::tanh(sum);
        }

        self.state = new_state;
    }

    fn output(&self) -> Vec<f32> {
        // y = W_out * x
        (0..self.output_size)
            .map(|i| {
                self.state
                    .iter()
                    .zip(self.w_output.iter())
                    .map(|(x, row)| x * row.get(i).copied().unwrap_or(0.0))
                    .sum()
            })
            .collect()
    }

    fn train(&mut self, inputs: &[Vec<f32>], targets: &[Vec<f32>], regularization: f32) {
        // Collect states
        let mut states: Vec<Vec<f32>> = Vec::new();
        let mut state = vec![0.0; self.reservoir_size];

        for input in inputs {
            // Update state
            for i in 0..self.reservoir_size {
                let mut sum = 0.0;
                for j in 0..self.reservoir_size {
                    sum += self.w_reservoir[i][j] * state[j];
                }
                for (j, &inp) in input.iter().enumerate() {
                    if j < self.input_size {
                        sum += self.w_input[i][j] * inp;
                    }
                }
                state[i] = (1.0 - self.leak_rate) * state[i] + self.leak_rate * sum.tanh();
            }
            states.push(state.clone());
        }

        // Ridge regression: W_out = (S^T S + λI)^{-1} S^T Y
        // Simplified: use pseudo-inverse approximation
        let n = states.len();
        if n == 0 {
            return;
        }

        for i in 0..self.output_size {
            for j in 0..self.reservoir_size {
                let mut numerator = 0.0;
                let mut denominator = 0.0;

                for (k, state) in states.iter().enumerate() {
                    if let Some(target) = targets.get(k) {
                        if let Some(&t) = target.get(i) {
                            numerator += state.get(j).copied().unwrap_or(0.0) * t;
                            denominator += state.get(j).copied().unwrap_or(0.0).powi(2);
                        }
                    }
                }

                denominator += regularization;
                if denominator > 0.0 {
                    self.w_output[j][i] = numerator / denominator;
                }
            }
        }
    }

    fn clear(&mut self) {
        self.state.fill(0.0);
    }
}

// ============================================================================
// SPIKING NEURAL NETWORK (Leaky Integrate-and-Fire)
// ============================================================================

#[derive(Debug, Clone)]
struct SpikingNeuron {
    // Membrane potential
    v: f32,
    // Resting potential
    v_rest: f32,
    // Threshold
    v_threshold: f32,
    // Reset potential
    v_reset: f32,
    // Membrane resistance
    r_membrane: f32,
    // Membrane capacitance
    c_membrane: f32,
    // Time constant
    tau: f32,
    // Refractory period
    refractory: usize,
    // Time since last spike
    since_spike: usize,
    // Synaptic weights
    weights: Vec<f32>,
    // Eligibility trace (for STDP)
    eligibility: Vec<f32>,
}

impl SpikingNeuron {
    fn new(num_inputs: usize) -> Self {
        Self {
            v: -70.0,
            v_rest: -70.0,
            v_threshold: -55.0,
            v_reset: -75.0,
            r_membrane: 1.0,
            c_membrane: 10.0,
            tau: 20.0,
            refractory: 2,
            since_spike: 100,
            weights: (0..num_inputs)
                .map(|_| rand::rng().random::<f32>() * 0.5)
                .collect(),
            eligibility: vec![0.0; num_inputs],
        }
    }

    fn integrate(&mut self, inputs: &[f32], dt: f32) -> bool {
        if self.since_spike < self.refractory {
            self.since_spike += 1;
            return false;
        }

        // Sum synaptic inputs
        let i_syn: f32 = inputs
            .iter()
            .zip(self.weights.iter())
            .map(|(inp, w)| inp * w)
            .sum();

        // Leaky integrate: dV/dt = (-V + V_rest + R*I) / τ
        let dv = (-self.v + self.v_rest + self.r_membrane * i_syn * 100.0) / self.tau;
        self.v += dv * dt;

        // Check for spike
        if self.v >= self.v_threshold {
            self.v = self.v_reset;
            self.since_spike = 0;
            return true;
        }

        self.since_spike += 1;
        false
    }

    fn stdp(&mut self, pre_spikes: &[bool], post_spike: bool, lr: f32) {
        // Spike-timing-dependent plasticity
        for (i, &pre) in pre_spikes.iter().enumerate() {
            if i >= self.weights.len() {
                break;
            }

            if pre && post_spike {
                // Post after pre: LTP
                self.weights[i] += lr * (1.0 - self.weights[i]);
                self.eligibility[i] = 1.0;
            } else if pre {
                // Pre without post: LTD
                self.eligibility[i] *= 0.95;
                self.weights[i] -= lr * self.eligibility[i] * 0.1;
            }

            // Clamp weights
            self.weights[i] = self.weights[i].clamp(0.0, 1.0);
        }
    }
}

#[derive(Debug, Clone)]
struct SpikingNetwork {
    layers: Vec<Vec<SpikingNeuron>>,
    output_weights: Vec<Vec<f32>>,
}

impl SpikingNetwork {
    fn new(layer_sizes: &[usize]) -> Self {
        let layers: Vec<Vec<SpikingNeuron>> = layer_sizes
            .windows(2)
            .map(|sizes| {
                (0..sizes[1])
                    .map(|_| SpikingNeuron::new(sizes[0]))
                    .collect()
            })
            .collect();

        let output_size = *layer_sizes.last().unwrap_or(&1);
        let last_hidden_size = layer_sizes.get(layer_sizes.len() - 2).copied().unwrap_or(1);

        Self {
            layers,
            output_weights: (0..last_hidden_size)
                .map(|_| {
                    (0..output_size)
                        .map(|_| rand::rng().random::<f32>() * 0.5)
                        .collect()
                })
                .collect(),
        }
    }

    fn forward(&mut self, input: &[bool], dt: f32) -> Vec<bool> {
        let mut layer_input: Vec<f32> = input.iter().map(|&s| if s { 1.0 } else { 0.0 }).collect();
        let mut spikes = Vec::new();

        for layer in &mut self.layers {
            let mut layer_spikes = Vec::new();
            for neuron in layer.iter_mut() {
                let spike = neuron.integrate(&layer_input, dt);
                layer_spikes.push(spike);
            }
            spikes.push(layer_spikes.clone());

            // Convert spikes to float for next layer
            layer_input = layer_spikes
                .iter()
                .map(|&s| if s { 1.0 } else { 0.0 })
                .collect();
        }

        // Get output layer spikes
        spikes.last().cloned().unwrap_or_default()
    }

    fn readout(&self, spike_history: &[Vec<bool>]) -> Vec<f32> {
        // Rate-based readout
        if spike_history.is_empty() {
            return vec![0.0; self.output_weights.get(0).map(|o| o.len()).unwrap_or(1)];
        }

        let last_layer = spike_history.last().unwrap();
        let rates: Vec<f32> = last_layer
            .iter()
            .map(|&s| if s { 1.0 } else { 0.0 })
            .collect();

        (0..self.output_weights.get(0).map(|o| o.len()).unwrap_or(1))
            .map(|i| {
                rates
                    .iter()
                    .zip(self.output_weights.iter())
                    .map(|(r, row)| r * row.get(i).copied().unwrap_or(0.0))
                    .sum()
            })
            .collect()
    }

    fn clear(&mut self) {
        for layer in &mut self.layers {
            for neuron in layer.iter_mut() {
                neuron.v = neuron.v_rest;
                neuron.since_spike = 100;
            }
        }
    }
}

// ============================================================================
// NEUROEVOLUTION (NEAT-inspired)
// ============================================================================

#[derive(Debug, Clone, PartialEq)]
struct Gene {
    from: usize,
    to: usize,
    weight: f32,
    enabled: bool,
    innovation: usize,
}

#[derive(Debug, Clone)]
struct Genome {
    genes: Vec<Gene>,
    nodes: usize,
    fitness: f32,
}

impl Genome {
    fn new(inputs: usize, outputs: usize) -> Self {
        let mut genes = Vec::new();
        let mut innovation = 0;

        // Connect all inputs to all outputs
        for i in 0..inputs {
            for o in 0..outputs {
                genes.push(Gene {
                    from: i,
                    to: inputs + o,
                    weight: rand::rng().random::<f32>() * 2.0 - 1.0,
                    enabled: true,
                    innovation,
                });
                innovation += 1;
            }
        }

        Self {
            genes,
            nodes: inputs + outputs,
            fitness: 0.0,
        }
    }

    fn mutate_add_connection(&mut self, innovation: &mut usize) {
        // Try to add a random connection
        let from = (rand::rng().random::<f32>() * self.nodes as f32) as usize;
        let to = (rand::rng().random::<f32>() * self.nodes as f32) as usize;

        // Check if connection already exists
        if self.genes.iter().any(|g| g.from == from && g.to == to) {
            return;
        }

        self.genes.push(Gene {
            from,
            to,
            weight: rand::rng().random::<f32>() * 2.0 - 1.0,
            enabled: true,
            innovation: *innovation,
        });
        *innovation += 1;
    }

    fn mutate_add_node(&mut self, innovation: &mut usize) {
        if self.genes.is_empty() {
            return;
        }

        // Pick a random enabled connection
        let enabled_indices: Vec<usize> = self
            .genes
            .iter()
            .enumerate()
            .filter(|(_, g)| g.enabled)
            .map(|(i, _)| i)
            .collect();

        if enabled_indices.is_empty() {
            return;
        }

        let idx =
            enabled_indices[(rand::rng().random::<f32>() * enabled_indices.len() as f32) as usize];

        // Get values we need before mutating
        let (from, to, weight) = {
            let gene = &self.genes[idx];
            (gene.from, gene.to, gene.weight)
        };

        // Disable old gene
        self.genes[idx].enabled = false;

        // Add new node and connections
        let new_node = self.nodes;
        self.nodes += 1;

        // Connection from old input to new node
        self.genes.push(Gene {
            from,
            to: new_node,
            weight: 1.0,
            enabled: true,
            innovation: *innovation,
        });
        *innovation += 1;

        // Connection from new node to old output
        self.genes.push(Gene {
            from: new_node,
            to,
            weight,
            enabled: true,
            innovation: *innovation,
        });
        *innovation += 1;
    }

    fn mutate_weights(&mut self, rate: f32) {
        for gene in &mut self.genes {
            if rand::rng().random::<f32>() < rate {
                gene.weight += rand::rng().random::<f32>() * 0.4 - 0.2;
                gene.weight = gene.weight.clamp(-1.0, 1.0);
            }
        }
    }

    fn crossover(a: &Genome, b: &Genome) -> Genome {
        let mut child = Genome {
            genes: Vec::new(),
            nodes: a.nodes.max(b.nodes),
            fitness: 0.0,
        };

        // Matching genes from more fit parent
        for ga in &a.genes {
            if let Some(gb) = b.genes.iter().find(|g| g.innovation == ga.innovation) {
                let gene = if rand::rng().random::<f32>() > 0.5 {
                    ga.clone()
                } else {
                    gb.clone()
                };
                child.genes.push(gene);
            } else {
                child.genes.push(ga.clone());
            }
        }

        child
    }

    fn forward(&self, input: &[f32]) -> Vec<f32> {
        let mut values = vec![0.0; self.nodes];

        // Set inputs
        for (i, &v) in input.iter().enumerate() {
            if i < values.len() {
                values[i] = v;
            }
        }

        // Forward pass (simplified - assumes feedforward)
        for _ in 0..5 {
            // Multiple iterations for recurrence
            let mut new_values = values.clone();
            for gene in &self.genes {
                if gene.enabled && gene.from < values.len() && gene.to < values.len() {
                    new_values[gene.to] += values[gene.from] * gene.weight;
                }
            }
            // Apply activation
            for v in &mut new_values {
                *v = v.tanh();
            }
            values = new_values;
        }

        values
    }
}

#[derive(Debug, Clone)]
struct Population {
    genomes: Vec<Genome>,
    species: Vec<Vec<usize>>,
    innovation: usize,
    inputs: usize,
    outputs: usize,
}

impl Population {
    fn new(size: usize, inputs: usize, outputs: usize) -> Self {
        Self {
            genomes: (0..size).map(|_| Genome::new(inputs, outputs)).collect(),
            species: Vec::new(),
            innovation: inputs * outputs,
            inputs,
            outputs,
        }
    }

    fn evolve(&mut self) {
        // Sort by fitness
        self.genomes.sort_by(|a, b| {
            b.fitness
                .partial_cmp(&a.fitness)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        // Keep top 20%
        let keep = self.genomes.len() / 5;
        self.genomes.truncate(keep);

        // Reproduce
        while self.genomes.len() < keep * 5 {
            let parent1_idx = (rand::rng().random::<f32>() * keep as f32) as usize;
            let parent2_idx = (rand::rng().random::<f32>() * keep as f32) as usize;

            if parent1_idx != parent2_idx {
                let child = if self.genomes[parent1_idx].fitness > self.genomes[parent2_idx].fitness
                {
                    Genome::crossover(&self.genomes[parent1_idx], &self.genomes[parent2_idx])
                } else {
                    Genome::crossover(&self.genomes[parent2_idx], &self.genomes[parent1_idx])
                };
                self.genomes.push(child);
            }
        }

        // Mutate
        for genome in &mut self.genomes {
            if rand::rng().random::<f32>() < 0.1 {
                genome.mutate_add_connection(&mut self.innovation);
            }
            if rand::rng().random::<f32>() < 0.05 {
                genome.mutate_add_node(&mut self.innovation);
            }
            genome.mutate_weights(0.8);
        }
    }
}

// ============================================================================
// WORLD MODELS (Dreamer-style imagination)
// ============================================================================

#[derive(Debug, Clone)]
struct WorldModelEncoder {
    weights: Vec<Vec<f32>>,
    latent_dim: usize,
}

impl WorldModelEncoder {
    fn new(input_dim: usize, latent_dim: usize) -> Self {
        Self {
            weights: (0..latent_dim)
                .map(|_| {
                    (0..input_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1)
                        .collect()
                })
                .collect(),
            latent_dim,
        }
    }

    fn encode(&self, input: &[f32]) -> Vec<f32> {
        self.weights
            .iter()
            .map(|w| {
                let sum: f32 = w.iter().zip(input.iter()).map(|(wi, xi)| wi * xi).sum();
                sum.tanh()
            })
            .collect()
    }
}

#[derive(Debug, Clone)]
struct WorldModelDecoder {
    weights: Vec<Vec<f32>>,
    output_dim: usize,
}

impl WorldModelDecoder {
    fn new(latent_dim: usize, output_dim: usize) -> Self {
        Self {
            weights: (0..output_dim)
                .map(|_| {
                    (0..latent_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1)
                        .collect()
                })
                .collect(),
            output_dim,
        }
    }

    fn decode(&self, latent: &[f32]) -> Vec<f32> {
        self.weights
            .iter()
            .map(|w| {
                let sum: f32 = w.iter().zip(latent.iter()).map(|(wi, li)| wi * li).sum();
                sum.tanh()
            })
            .collect()
    }
}

#[derive(Debug, Clone)]
struct RSSM {
    // Recurrent State Space Model (core of Dreamer)
    deterministic_size: usize,
    stochastic_size: usize,
    gru_weights: Vec<Vec<f32>>,
    prior_weights: Vec<Vec<f32>>,
    posterior_weights: Vec<Vec<f32>>,
}

impl RSSM {
    fn new(deterministic_size: usize, stochastic_size: usize) -> Self {
        Self {
            deterministic_size,
            stochastic_size,
            gru_weights: vec![vec![0.1; deterministic_size]; deterministic_size + stochastic_size],
            prior_weights: vec![vec![0.1; stochastic_size * 2]; deterministic_size],
            posterior_weights: vec![
                vec![0.1; stochastic_size * 2];
                deterministic_size + stochastic_size
            ],
        }
    }

    fn gru_step(&self, h: &[f32], z: &[f32]) -> Vec<f32> {
        // Simplified GRU
        let input: Vec<f32> = h.iter().chain(z.iter()).copied().collect();

        let mut new_h = vec![0.0; self.deterministic_size];
        for (i, nh) in new_h.iter_mut().enumerate() {
            for (j, &inp) in input.iter().enumerate() {
                if j < self.gru_weights[i].len() {
                    *nh += inp * self.gru_weights[i][j];
                }
            }
            *nh = nh.tanh();
        }
        new_h
    }

    fn prior(&self, h: &[f32]) -> (Vec<f32>, Vec<f32>) {
        // Prior distribution p(z|h)
        let mut mean = vec![0.0; self.stochastic_size];
        let mut std = vec![1.0; self.stochastic_size];

        for (i, m) in mean.iter_mut().enumerate() {
            for (j, &hj) in h.iter().enumerate() {
                if j < self.prior_weights[i].len() {
                    *m += hj * self.prior_weights[i][j];
                }
            }
        }

        for (i, s) in std.iter_mut().enumerate() {
            for (j, &hj) in h.iter().enumerate() {
                if j + self.stochastic_size < self.prior_weights[i].len() {
                    *s += hj * self.prior_weights[i][j + self.stochastic_size];
                }
            }
            *s = s.exp().max(0.01);
        }

        (mean, std)
    }

    fn posterior(&self, h: &[f32], z: &[f32]) -> (Vec<f32>, Vec<f32>) {
        // Posterior distribution q(z|h, z_embed)
        let input: Vec<f32> = h.iter().chain(z.iter()).copied().collect();

        let mut mean = vec![0.0; self.stochastic_size];
        let mut std = vec![1.0; self.stochastic_size];

        for (i, m) in mean.iter_mut().enumerate() {
            for (j, &inp) in input.iter().enumerate() {
                if j < self.posterior_weights[i].len() {
                    *m += inp * self.posterior_weights[i][j];
                }
            }
        }

        for (i, s) in std.iter_mut().enumerate() {
            for (j, &inp) in input.iter().enumerate() {
                if j + self.stochastic_size < self.posterior_weights[i].len() {
                    *s += inp * self.posterior_weights[i][j + self.stochastic_size];
                }
            }
            *s = s.exp().max(0.01);
        }

        (mean, std)
    }

    fn sample(&self, mean: &[f32], std: &[f32]) -> Vec<f32> {
        mean.iter()
            .zip(std.iter())
            .map(|(&m, &s)| m + s * (rand::rng().random::<f32>() * 2.0 - 1.0))
            .collect()
    }
}

#[derive(Debug, Clone)]
struct DreamerWorldModel {
    encoder: WorldModelEncoder,
    decoder: WorldModelDecoder,
    rssm: RSSM,
    reward_predictor: Vec<f32>,
    imagination_horizon: usize,
}

impl DreamerWorldModel {
    fn new(obs_dim: usize, latent_dim: usize, action_dim: usize) -> Self {
        Self {
            encoder: WorldModelEncoder::new(obs_dim + action_dim, latent_dim),
            decoder: WorldModelDecoder::new(latent_dim, obs_dim),
            rssm: RSSM::new(500, 100), // Increased from 200/30
            reward_predictor: vec![0.01; latent_dim],
            imagination_horizon: 15,
        }
    }

    fn imagine(
        &self,
        initial_state: &[f32],
        policy: &dyn Fn(&[f32]) -> Vec<f32>,
        steps: usize,
    ) -> Vec<(Vec<f32>, f32)> {
        let mut trajectory = Vec::new();
        let mut h = vec![0.0; self.rssm.deterministic_size];
        let mut z = initial_state.to_vec();

        for _ in 0..steps.min(self.imagination_horizon) {
            // Get action from policy
            let action = policy(&z);

            // Encode state-action
            let sa: Vec<f32> = z.iter().chain(action.iter()).copied().collect();
            let embed = self.encoder.encode(&sa);

            // RSSM step
            h = self.rssm.gru_step(&h, &embed);
            let (mean, std) = self.rssm.prior(&h);
            z = self.rssm.sample(&mean, &std);

            // Predict reward
            let reward: f32 = z
                .iter()
                .zip(self.reward_predictor.iter())
                .map(|(zi, r)| zi * r)
                .sum();

            trajectory.push((z.clone(), reward));
        }

        trajectory
    }

    fn train_step(&mut self, states: &[Vec<f32>], actions: &[Vec<f32>], rewards: &[f32]) {
        // Simplified training - update reward predictor
        for (i, &r) in rewards.iter().enumerate() {
            if i < states.len() {
                for (j, &s) in states[i].iter().enumerate() {
                    if j < self.reward_predictor.len() {
                        self.reward_predictor[j] += 0.01 * (r - s * self.reward_predictor[j]) * s;
                    }
                }
            }
        }
    }

    /// Observe a state-reward pair and train online
    fn observe(&mut self, state: Vec<f32>, reward: f32) {
        // Update reward predictor based on state and reward
        for (i, &s) in state.iter().enumerate() {
            if i < self.reward_predictor.len() {
                // Gradient descent on prediction error
                let prediction: f32 = state
                    .iter()
                    .zip(self.reward_predictor.iter())
                    .take(self.reward_predictor.len())
                    .map(|(si, ri)| si * ri)
                    .sum();
                let error = reward - prediction;
                self.reward_predictor[i] += 0.01 * error * s;
            }
        }
    }

    /// Predict reward for a given state
    fn predict_reward(&self, state: &[f32]) -> f32 {
        state
            .iter()
            .zip(self.reward_predictor.iter())
            .map(|(s, r)| s * r)
            .sum()
    }

    fn clear(&mut self) {
        self.reward_predictor.fill(0.01);
    }
}

// ============================================================================
// CONTRASTIVE LEARNING (SimCLR-style)
// ============================================================================

#[derive(Debug, Clone)]
struct ContrastiveLearner {
    encoder: Vec<Vec<f32>>,
    projector: Vec<Vec<f32>>,
    temperature: f32,
    embedding_dim: usize,
    hidden_dim: usize,
    // Memory buffers for contrastive learning
    memory_win: VecDeque<Vec<f32>>,
    memory_loss: VecDeque<Vec<f32>>,
}

impl ContrastiveLearner {
    fn new(input_dim: usize, embedding_dim: usize, hidden_dim: usize) -> Self {
        Self {
            encoder: (0..hidden_dim)
                .map(|_| {
                    (0..input_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1)
                        .collect()
                })
                .collect(),
            projector: (0..embedding_dim)
                .map(|_| {
                    (0..hidden_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1)
                        .collect()
                })
                .collect(),
            temperature: 0.1,
            embedding_dim,
            hidden_dim,
            memory_win: VecDeque::with_capacity(50), // Reduced from 500
            memory_loss: VecDeque::with_capacity(50), // Reduced from 500
        }
    }

    fn encode(&self, input: &[f32]) -> Vec<f32> {
        // Hidden layer
        let hidden: Vec<f32> = self
            .encoder
            .iter()
            .map(|w| {
                let sum: f32 = w.iter().zip(input.iter()).map(|(wi, xi)| wi * xi).sum();
                sum.max(0.0) // ReLU
            })
            .collect();

        // Projection
        self.projector
            .iter()
            .map(|w| {
                let sum: f32 = w.iter().zip(hidden.iter()).map(|(wi, hi)| wi * hi).sum();
                sum.tanh()
            })
            .collect()
    }

    fn contrastive_loss(&self, anchor: &[f32], positive: &[f32], negatives: &[Vec<f32>]) -> f32 {
        let z_anchor = self.encode(anchor);
        let z_positive = self.encode(positive);

        // Normalize
        let norm_anchor: f32 = z_anchor.par_iter().map(|x| x * x).sum::<f32>().sqrt();
        let norm_positive: f32 = z_positive.par_iter().map(|x| x * x).sum::<f32>().sqrt();

        // Similarity
        let sim_positive: f32 = z_anchor
            .iter()
            .zip(z_positive.iter())
            .map(|(a, p)| a * p / (norm_anchor * norm_positive + 1e-8))
            .sum::<f32>()
            / (self.temperature * self.embedding_dim as f32);

        // Negative similarities
        let mut sim_negatives = Vec::new();
        for neg in negatives {
            let z_neg = self.encode(neg);
            let norm_neg: f32 = z_neg.par_iter().map(|x| x * x).sum::<f32>().sqrt();
            let sim: f32 = z_anchor
                .iter()
                .zip(z_neg.iter())
                .map(|(a, n)| a * n / (norm_anchor * norm_neg + 1e-8))
                .sum::<f32>()
                / (self.temperature * self.embedding_dim as f32);
            sim_negatives.push(sim);
        }

        // InfoNCE loss
        let exp_pos = sim_positive.exp();
        let exp_neg_sum: f32 = sim_negatives.par_iter().map(|s| s.exp()).sum();

        -(exp_pos / (exp_pos + exp_neg_sum + 1e-8)).ln()
    }

    fn train(&mut self, pairs: &[(&[f32], &[f32])], lr: f32) {
        // Simplified contrastive training
        for (anchor, positive) in pairs {
            let z_a = self.encode(anchor);
            let z_p = self.encode(positive);

            // Gradient approximation: push anchor and positive closer
            for (i, w_row) in self.projector.iter_mut().enumerate() {
                for (j, w) in w_row.iter_mut().enumerate() {
                    let grad = (z_a.get(i).copied().unwrap_or(0.0)
                        - z_p.get(i).copied().unwrap_or(0.0))
                        * (z_a.get(j).copied().unwrap_or(0.0) + z_p.get(j).copied().unwrap_or(0.0));
                    *w -= lr * grad * 0.01;
                }
            }
        }
    }

    /// Store a sample for contrastive learning with its outcome label
    fn push_sample(&mut self, input: &[f32], is_win: bool) {
        let embedding = self.encode(input);
        // Store in memory buffer (we use a simple approach: keep recent samples)
        if self.memory_win.len() >= 50 {
            self.memory_win.pop_front();
        }
        if self.memory_loss.len() >= 50 {
            self.memory_loss.pop_front();
        }
        if is_win {
            self.memory_win.push_back(embedding);
        } else {
            self.memory_loss.push_back(embedding);
        }

        // Periodically train with contrastive pairs
        if self.memory_win.len() >= 10 && self.memory_loss.len() >= 10 {
            self.train_contrastive();
        }
    }

    fn train_contrastive(&mut self) {
        // Create positive pairs from same class, negatives from opposite
        let lr = 0.001;

        // Train encoder to push wins together and losses together, push wins/losses apart
        if let (Some(win_emb), Some(loss_emb)) = (self.memory_win.back(), self.memory_loss.back()) {
            // Contrastive update on projector weights
            for (i, w_row) in self.projector.iter_mut().enumerate() {
                let win_val = win_emb.get(i).copied().unwrap_or(0.0);
                let loss_val = loss_emb.get(i).copied().unwrap_or(0.0);

                // Gradient: maximize distance between win and loss embeddings
                for (j, w) in w_row.iter_mut().enumerate() {
                    let grad = (win_val - loss_val) * 0.01;
                    *w += lr * grad;
                }
            }
        }
    }

    /// Get similarity between two states (for prediction)
    fn similarity(&self, state1: &[f32], state2: &[f32]) -> f32 {
        let z1 = self.encode(state1);
        let z2 = self.encode(state2);

        let norm1: f32 = z1.par_iter().map(|x| x * x).sum::<f32>().sqrt();
        let norm2: f32 = z2.par_iter().map(|x| x * x).sum::<f32>().sqrt();

        if norm1 < 1e-8 || norm2 < 1e-8 {
            return 0.0;
        }

        z1.iter().zip(z2.iter()).map(|(a, b)| a * b).sum::<f32>() / (norm1 * norm2)
    }

    /// Predict win probability based on similarity to known win/loss states
    fn predict_outcome(&self, state: &[f32]) -> f32 {
        let state_emb = self.encode(state);

        let win_sim: f32 = self
            .memory_win
            .iter()
            .map(|w| {
                let norm1: f32 = state_emb.par_iter().map(|x| x * x).sum::<f32>().sqrt();
                let norm2: f32 = w.par_iter().map(|x| x * x).sum::<f32>().sqrt();
                if norm1 < 1e-8 || norm2 < 1e-8 {
                    0.0
                } else {
                    state_emb
                        .iter()
                        .zip(w.iter())
                        .map(|(a, b)| a * b)
                        .sum::<f32>()
                        / (norm1 * norm2)
                }
            })
            .sum();

        let loss_sim: f32 = self
            .memory_loss
            .iter()
            .map(|l| {
                let norm1: f32 = state_emb.par_iter().map(|x| x * x).sum::<f32>().sqrt();
                let norm2: f32 = l.par_iter().map(|x| x * x).sum::<f32>().sqrt();
                if norm1 < 1e-8 || norm2 < 1e-8 {
                    0.0
                } else {
                    state_emb
                        .iter()
                        .zip(l.iter())
                        .map(|(a, b)| a * b)
                        .sum::<f32>()
                        / (norm1 * norm2)
                }
            })
            .sum();

        let win_count = self.memory_win.len().max(1) as f32;
        let loss_count = self.memory_loss.len().max(1) as f32;

        let avg_win_sim = win_sim / win_count;
        let avg_loss_sim = loss_sim / loss_count;

        // Softmax-like probability
        let exp_win = (avg_win_sim * 5.0).exp();
        let exp_loss = (avg_loss_sim * 5.0).exp();

        exp_win / (exp_win + exp_loss + 1e-8)
    }

    fn clear(&mut self) {
        self.memory_win.clear();
        self.memory_loss.clear();
    }
}

// ============================================================================
// TRANSFORMER PREDICTOR (Self-attention for time series)
// ============================================================================

#[derive(Debug, Clone)]
struct TransformerPredictor {
    d_model: usize,
    n_heads: usize,
    n_layers: usize,
    // Multi-head attention weights
    w_q: Vec<Vec<f32>>, // Query projection
    w_k: Vec<Vec<f32>>, // Key projection
    w_v: Vec<Vec<f32>>, // Value projection
    w_o: Vec<Vec<f32>>, // Output projection
    // Feed-forward weights
    ff_w1: Vec<Vec<f32>>,
    ff_w2: Vec<Vec<f32>>,
    // Layer norms
    ln1_gamma: Vec<f32>,
    ln1_beta: Vec<f32>,
    ln2_gamma: Vec<f32>,
    ln2_beta: Vec<f32>,
    // Positional encoding
    pos_encoding: Vec<Vec<f32>>,
    seq_len: usize,
}

impl TransformerPredictor {
    fn new(d_model: usize, n_heads: usize, n_layers: usize, seq_len: usize) -> Self {
        let init_weight = || {
            (0..d_model)
                .map(|_| {
                    (0..d_model)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect()
        };

        let pos_encoding = (0..seq_len)
            .map(|pos| {
                (0..d_model)
                    .map(|i| {
                        let div = 10000_f32.powf(i as f32 / d_model as f32);
                        if i % 2 == 0 {
                            (pos as f32 / div).sin()
                        } else {
                            (pos as f32 / div).cos()
                        }
                    })
                    .collect()
            })
            .collect();

        Self {
            d_model,
            n_heads,
            n_layers,
            w_q: init_weight(),
            w_k: init_weight(),
            w_v: init_weight(),
            w_o: init_weight(),
            ff_w1: (0..d_model * 4)
                .map(|_| {
                    (0..d_model)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            ff_w2: (0..d_model)
                .map(|_| {
                    (0..d_model * 4)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            ln1_gamma: vec![1.0; d_model],
            ln1_beta: vec![0.0; d_model],
            ln2_gamma: vec![1.0; d_model],
            ln2_beta: vec![0.0; d_model],
            pos_encoding,
            seq_len,
        }
    }

    fn layer_norm(&self, x: &[f32], gamma: &[f32], beta: &[f32]) -> Vec<f32> {
        let mean: f32 = x.par_iter().sum::<f32>() / x.len() as f32;
        let var: f32 = x.par_iter().map(|xi| (xi - mean).powi(2)).sum::<f32>() / x.len() as f32;
        let std = (var + 1e-6).sqrt();
        x.iter()
            .zip(gamma.iter())
            .zip(beta.iter())
            .map(|((xi, g), b)| g * (xi - mean) / std + b)
            .collect()
    }

    fn multi_head_attention(&self, x: &[Vec<f32>]) -> Vec<Vec<f32>> {
        let seq_len = x.len();
        let d_k = self.d_model / self.n_heads;

        // Compute Q, K, V for all positions
        let q: Vec<Vec<f32>> = x
            .iter()
            .map(|xi| {
                self.w_q
                    .iter()
                    .map(|wq| xi.iter().zip(wq.iter()).map(|(a, b)| a * b).sum())
                    .collect()
            })
            .collect();
        let k: Vec<Vec<f32>> = x
            .iter()
            .map(|xi| {
                self.w_k
                    .iter()
                    .map(|wk| xi.iter().zip(wk.iter()).map(|(a, b)| a * b).sum())
                    .collect()
            })
            .collect();
        let v: Vec<Vec<f32>> = x
            .iter()
            .map(|xi| {
                self.w_v
                    .iter()
                    .map(|wv| xi.iter().zip(wv.iter()).map(|(a, b)| a * b).sum())
                    .collect()
            })
            .collect();

        // Multi-head attention with scaled dot-product
        let mut output = vec![vec![0.0; self.d_model]; seq_len];

        for h in 0..self.n_heads {
            let head_offset = h * d_k;

            for i in 0..seq_len {
                // Compute attention scores
                let mut scores: Vec<f32> = (0..seq_len)
                    .map(|j| {
                        let dot: f32 = q[i][head_offset..head_offset + d_k]
                            .iter()
                            .zip(k[j][head_offset..head_offset + d_k].iter())
                            .map(|(a, b)| a * b)
                            .sum();
                        dot / (d_k as f32).sqrt()
                    })
                    .collect();

                // Softmax
                let max_score = scores.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
                let exp_sum: f32 = scores.par_iter().map(|s| (s - max_score).exp()).sum();
                for s in &mut scores {
                    *s = (*s - max_score).exp() / (exp_sum + 1e-8);
                }

                // Apply attention to values
                for j in 0..seq_len {
                    for d in 0..d_k {
                        output[i][head_offset + d] += scores[j] * v[j][head_offset + d];
                    }
                }
            }
        }

        // Output projection
        output
            .iter()
            .map(|oi| {
                self.w_o
                    .iter()
                    .map(|wo| oi.iter().zip(wo.iter()).map(|(a, b)| a * b).sum())
                    .collect()
            })
            .collect()
    }

    fn feed_forward(&self, x: &[f32]) -> Vec<f32> {
        // First linear + ReLU
        let hidden: Vec<f32> = self
            .ff_w1
            .iter()
            .map(|w1| {
                x.iter()
                    .zip(w1.iter())
                    .map(|(a, b)| a * b)
                    .sum::<f32>()
                    .max(0.0)
            })
            .collect();

        // Second linear
        self.ff_w2
            .iter()
            .map(|w2| hidden.iter().zip(w2.iter()).map(|(a, b)| a * b).sum())
            .collect()
    }

    fn forward(&self, x: &[Vec<f32>]) -> Vec<f32> {
        let seq_len = x.len().min(self.seq_len);

        // Add positional encoding
        let mut embed: Vec<Vec<f32>> = x
            .iter()
            .take(seq_len)
            .enumerate()
            .map(|(i, xi)| {
                xi.iter()
                    .zip(self.pos_encoding[i].iter())
                    .map(|(a, b)| a + b)
                    .collect()
            })
            .collect();

        // Pad if necessary
        while embed.len() < self.seq_len {
            embed.push(vec![0.0; self.d_model]);
        }

        // Transformer layers
        for _ in 0..self.n_layers {
            // Multi-head attention + residual + layer norm
            let attn_out = self.multi_head_attention(&embed);
            embed = embed
                .iter()
                .zip(attn_out.iter())
                .map(|(e, a)| {
                    self.layer_norm(
                        &e.iter()
                            .zip(a.iter())
                            .map(|(ei, ai)| ei + ai)
                            .collect::<Vec<_>>(),
                        &self.ln1_gamma,
                        &self.ln1_beta,
                    )
                })
                .collect();

            // Feed-forward + residual + layer norm
            embed = embed
                .iter()
                .map(|e| {
                    let ff_out = self.feed_forward(e);
                    self.layer_norm(
                        &e.iter()
                            .zip(ff_out.iter())
                            .map(|(ei, fi)| ei + fi)
                            .collect::<Vec<_>>(),
                        &self.ln2_gamma,
                        &self.ln2_beta,
                    )
                })
                .collect();
        }

        // Return last position prediction
        embed.last().cloned().unwrap_or_default()
    }

    fn predict(&mut self, sequence: &[Vec<f32>]) -> f32 {
        let output = self.forward(sequence);
        output.first().copied().unwrap_or(0.5)
    }
}

// ============================================================================
// VARIATIONAL AUTOENCODER (VAE) for state representation
// ============================================================================

#[derive(Debug, Clone)]
struct VariationalAutoencoder {
    // Encoder layers
    encoder_w1: Vec<Vec<f32>>,
    encoder_b1: Vec<f32>,
    encoder_mu: Vec<Vec<f32>>,
    encoder_logvar: Vec<Vec<f32>>,
    // Decoder layers
    decoder_w1: Vec<Vec<f32>>,
    decoder_b1: Vec<f32>,
    decoder_out: Vec<Vec<f32>>,
    latent_dim: usize,
    input_dim: usize,
}

impl VariationalAutoencoder {
    fn new(input_dim: usize, latent_dim: usize, hidden_dim: usize) -> Self {
        Self {
            encoder_w1: (0..hidden_dim)
                .map(|_| {
                    (0..input_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            encoder_b1: vec![0.0; hidden_dim],
            encoder_mu: (0..latent_dim)
                .map(|_| {
                    (0..hidden_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            encoder_logvar: (0..latent_dim)
                .map(|_| {
                    (0..hidden_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            decoder_w1: (0..hidden_dim)
                .map(|_| {
                    (0..latent_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            decoder_b1: vec![0.0; hidden_dim],
            decoder_out: (0..input_dim)
                .map(|_| {
                    (0..hidden_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            latent_dim,
            input_dim,
        }
    }

    fn encode(&self, x: &[f32]) -> (Vec<f32>, Vec<f32>) {
        // Hidden layer
        let hidden: Vec<f32> = self
            .encoder_w1
            .iter()
            .zip(self.encoder_b1.iter())
            .map(|(w, b)| {
                let sum: f32 = w.iter().zip(x.iter()).map(|(wi, xi)| wi * xi).sum();
                (sum + b).tanh()
            })
            .collect();

        // Mean
        let mu: Vec<f32> = self
            .encoder_mu
            .iter()
            .map(|w| hidden.iter().zip(w.iter()).map(|(h, wi)| h * wi).sum())
            .collect();

        // Log variance
        let logvar: Vec<f32> = self
            .encoder_logvar
            .iter()
            .map(|w| hidden.iter().zip(w.iter()).map(|(h, wi)| h * wi).sum())
            .collect();

        (mu, logvar)
    }

    fn reparameterize(&self, mu: &[f32], logvar: &[f32]) -> Vec<f32> {
        mu.iter()
            .zip(logvar.iter())
            .map(|(m, l)| {
                let rand_val: f32 = rand::rng().random();
                m + (l / 2.0).exp() * rand_val.sqrt() * (2.0_f32 * std::f32::consts::PI).cos()
            })
            .collect()
    }

    fn decode(&self, z: &[f32]) -> Vec<f32> {
        // Hidden layer
        let hidden: Vec<f32> = self
            .decoder_w1
            .iter()
            .zip(self.decoder_b1.iter())
            .map(|(w, b)| {
                let sum: f32 = w.iter().zip(z.iter()).map(|(wi, zi)| wi * zi).sum();
                (sum + b).tanh()
            })
            .collect();

        // Output - sigmoid activation
        self.decoder_out
            .iter()
            .map(|w| {
                let sum: f32 = hidden.iter().zip(w.iter()).map(|(h, wi)| h * wi).sum();
                1.0 / (1.0 + (-sum).exp()) // sigmoid
            })
            .collect()
    }

    fn forward(&self, x: &[f32]) -> (Vec<f32>, Vec<f32>, Vec<f32>) {
        let (mu, logvar) = self.encode(x);
        let z = self.reparameterize(&mu, &logvar);
        let recon = self.decode(&z);
        (recon, mu, logvar)
    }

    fn loss(&self, x: &[f32], recon: &[f32], mu: &[f32], logvar: &[f32]) -> f32 {
        // Reconstruction loss (BCE)
        let recon_loss: f32 = x
            .iter()
            .zip(recon.iter())
            .map(|(xi, ri)| {
                -xi * ri.clamp(1e-8, 1.0 - 1e-8).ln()
                    - (1.0 - xi) * (1.0 - ri.clamp(1e-8, 1.0 - 1e-8)).ln()
            })
            .sum();

        // KL divergence
        let kl_loss: f32 = -0.5
            * logvar
                .iter()
                .zip(mu.iter())
                .map(|(l, m)| 1.0 + l - m.powi(2) - l.exp())
                .sum::<f32>();

        recon_loss + kl_loss
    }

    fn get_latent(&mut self, x: &[f32]) -> Vec<f32> {
        let (mu, _) = self.encode(x);
        mu
    }
}

// ============================================================================
// NEURAL TURING MACHINE (Differentiable memory)
// ============================================================================

#[derive(Debug, Clone)]
struct NeuralTuringMachine {
    controller_weights: Vec<Vec<f32>>,
    memory: Vec<Vec<f32>>,
    read_weights: Vec<f32>,
    write_weights: Vec<f32>,
    memory_size: usize,
    memory_dim: usize,
    shift_range: usize,
}

impl NeuralTuringMachine {
    fn new(input_dim: usize, memory_size: usize, memory_dim: usize) -> Self {
        // Controller output needs: key(memory_dim) + beta(1) + shift(1) + erase(memory_dim) + add(memory_dim) = 3*memory_dim + 2
        let controller_output_dim = memory_dim * 3 + 2;
        Self {
            controller_weights: (0..controller_output_dim)
                .map(|_| {
                    (0..input_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            memory: vec![vec![0.01; memory_dim]; memory_size],
            read_weights: vec![1.0 / memory_size as f32; memory_size],
            write_weights: vec![1.0 / memory_size as f32; memory_size],
            memory_size,
            memory_dim,
            shift_range: 3,
        }
    }

    fn content_addressing(&self, key: &[f32], beta: f32) -> Vec<f32> {
        let similarities: Vec<f32> = self
            .memory
            .iter()
            .map(|m| {
                let dot: f32 = key.iter().zip(m.iter()).map(|(k, mi)| k * mi).sum();
                let key_norm: f32 = key.par_iter().map(|k| k * k).sum::<f32>().sqrt();
                let m_norm: f32 = m.par_iter().map(|mi| mi * mi).sum::<f32>().sqrt();
                if key_norm > 0.0 && m_norm > 0.0 {
                    dot / (key_norm * m_norm)
                } else {
                    0.0
                }
            })
            .collect();

        // Softmax with sharpness beta
        let max_sim = similarities
            .iter()
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        let exp_sum: f32 = similarities
            .iter()
            .map(|s| (beta * (s - max_sim)).exp())
            .sum();
        similarities
            .iter()
            .map(|s| (beta * (s - max_sim)).exp() / (exp_sum + 1e-8))
            .collect()
    }

    fn shift_weights(&self, weights: &[f32], shift: f32) -> Vec<f32> {
        let shift_idx = (shift * self.shift_range as f32) as usize;
        let mut shifted = vec![0.0; self.memory_size];
        for (i, &w) in weights.iter().enumerate() {
            let new_idx = (i + shift_idx) % self.memory_size;
            shifted[new_idx] += w;
        }
        shifted
    }

    fn read(&mut self) -> Vec<f32> {
        let mut result = vec![0.0; self.memory_dim];
        for (m, w) in self.memory.iter().zip(self.read_weights.iter()) {
            for (r, mi) in result.iter_mut().zip(m.iter()) {
                *r += mi * w;
            }
        }
        for r in result.iter_mut() {
            *r /= self.memory_size as f32;
        }
        result
    }

    fn write(&mut self, erase: &[f32], add: &[f32]) {
        for (i, (m, w)) in self
            .memory
            .iter_mut()
            .zip(self.write_weights.iter())
            .enumerate()
        {
            for (j, mi) in m.iter_mut().enumerate() {
                *mi = *mi * (1.0 - w * erase[j % self.memory_dim]) + w * add[j % self.memory_dim];
            }
        }
    }

    fn forward(&mut self, input: &[f32]) -> Vec<f32> {
        // Controller produces key, beta, shift, erase, add vectors
        let controller_out: Vec<f32> = self
            .controller_weights
            .iter()
            .map(|w| {
                input
                    .iter()
                    .zip(w.iter())
                    .map(|(inp, wi)| inp * wi)
                    .sum::<f32>()
                    .tanh()
            })
            .collect();

        // Split controller output
        let key = &controller_out[0..self.memory_dim];
        let beta = controller_out[self.memory_dim].exp();
        let _shift = 1.0 / (1.0 + (-controller_out[self.memory_dim + 1]).exp()); // sigmoid
        let erase = controller_out[self.memory_dim + 2..self.memory_dim + 2 + self.memory_dim]
            .iter()
            .map(|e| 1.0 / (1.0 + (-e).exp())) // sigmoid
            .collect::<Vec<_>>();
        let add = controller_out[self.memory_dim + 2 + self.memory_dim..]
            .iter()
            .map(|a| a.tanh())
            .collect::<Vec<_>>();

        // Update addressing
        let content_weights = self.content_addressing(key, beta);
        self.read_weights = content_weights.clone();
        self.write_weights = content_weights;

        // Write and read
        self.write(&erase, &add);
        self.read()
    }
}

// ============================================================================
// HAWKES PROCESS (Self-exciting point process for event prediction)
// ============================================================================

#[derive(Debug, Clone)]
struct HawkesProcess {
    // Intensity: λ(t) = μ + Σ α * exp(-β * (t - t_i))
    mu: f32,               // Baseline intensity
    alpha: f32,            // Excitation strength
    beta: f32,             // Decay rate
    events: VecDeque<f32>, // Event times
    last_time: f32,
}

impl HawkesProcess {
    fn new(mu: f32, alpha: f32, beta: f32) -> Self {
        Self {
            mu,
            alpha,
            beta,
            events: VecDeque::with_capacity(1000),
            last_time: 0.0,
        }
    }

    fn intensity(&self, t: f32) -> f32 {
        let excitation: f32 = self
            .events
            .iter()
            .map(|&ti| {
                let dt = t - ti;
                if dt > 0.0 {
                    self.alpha * (-self.beta * dt).exp()
                } else {
                    0.0
                }
            })
            .sum();
        self.mu + excitation
    }

    fn observe_event(&mut self, t: f32) {
        self.events.push_back(t);
        self.last_time = t;
        if self.events.len() > 1000 {
            self.events.pop_front();
        }
    }

    fn predict_next_time(&self, current_time: f32) -> f32 {
        // Approximate next event time
        let intensity = self.intensity(current_time);
        if intensity > 0.0 {
            current_time + 1.0 / intensity
        } else {
            current_time + 1.0 / self.mu.max(0.01)
        }
    }

    fn probability_event(&self, current_time: f32, dt: f32) -> f32 {
        // P(event in [t, t+dt]) ≈ 1 - exp(-∫λ(s)ds)
        // Approximate as λ(t) * dt for small dt
        1.0 - (-self.intensity(current_time) * dt).exp()
    }

    fn update_parameters(&mut self, events: &[f32], lr: f32) {
        // Maximum likelihood update (simplified)
        let n = events.len() as f32;
        if n < 2.0 {
            return;
        }

        // Gradient estimates
        let mut dl_dm = 0.0;
        let mut dl_da = 0.0;
        let mut dl_db = 0.0;

        for i in 1..events.len() {
            let t = events[i];
            let lambda_t = self.intensity(t);
            if lambda_t > 0.0 {
                dl_dm += 1.0 / lambda_t - t;
                for &ti in &self.events {
                    if ti < t {
                        let dt = t - ti;
                        let exp_decay = (-self.beta * dt).exp();
                        dl_da += exp_decay / lambda_t - dt * exp_decay / self.beta;
                        dl_db += -self.alpha * dt * exp_decay / lambda_t
                            + self.alpha * dt * dt * exp_decay / 2.0;
                    }
                }
            }
        }

        self.mu = (self.mu + lr * dl_dm / n).max(0.01);
        self.alpha = (self.alpha + lr * dl_da / n).max(0.0);
        self.beta = (self.beta + lr * dl_db / n).max(0.1);
    }
}

// ============================================================================
// FRACTIONAL BROWNIAN MOTION & HURST EXPONENT
// ============================================================================

#[derive(Debug, Clone)]
struct HurstEstimator {
    returns: VecDeque<f32>,
    window_size: usize,
}

impl HurstEstimator {
    fn new(window_size: usize) -> Self {
        Self {
            returns: VecDeque::with_capacity(window_size),
            window_size,
        }
    }

    fn add_return(&mut self, r: f32) {
        self.returns.push_back(r);
        if self.returns.len() > self.window_size {
            self.returns.pop_front();
        }
    }

    /// Estimate Hurst exponent using R/S analysis
    /// H > 0.5: trending, H < 0.5: mean-reverting, H = 0.5: random walk
    fn estimate_hurst(&self) -> f32 {
        if self.returns.len() < 20 {
            return 0.5;
        }

        let rs_values: Vec<f32> = (5..self.returns.len().min(50))
            .map(|n| {
                let chunks: Vec<Vec<f32>> = self
                    .returns
                    .iter()
                    .cloned()
                    .collect::<Vec<_>>()
                    .chunks(n)
                    .map(|c| c.to_vec())
                    .collect();

                let rs_chunk: Vec<f32> = chunks
                    .iter()
                    .filter(|c| c.len() >= n)
                    .map(|chunk| {
                        let mean: f32 = chunk.par_iter().sum::<f32>() / chunk.len() as f32;
                        let cumulative: Vec<f32> = chunk
                            .iter()
                            .scan(0.0, |acc, &x| {
                                *acc += x - mean;
                                Some(*acc)
                            })
                            .collect();
                        let max_dev = cumulative.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
                        let min_dev = cumulative.iter().cloned().fold(f32::INFINITY, f32::min);
                        let range = max_dev - min_dev;
                        let std: f32 = (chunk.par_iter().map(|x| (x - mean).powi(2)).sum::<f32>()
                            / chunk.len() as f32)
                            .sqrt();
                        if std > 0.0 {
                            range / std
                        } else {
                            1.0
                        }
                    })
                    .collect();

                rs_chunk.par_iter().sum::<f32>() / rs_chunk.len().max(1) as f32
            })
            .collect();

        // Linear regression of log(R/S) vs log(n)
        let log_n: Vec<f32> = (5..self.returns.len().min(50) as usize)
            .map(|n| (n as f32).ln())
            .collect();
        let log_rs: Vec<f32> = rs_values.par_iter().map(|rs| rs.max(0.01).ln()).collect();
        let n = log_rs.len();
        if n < 2 {
            return 0.5;
        }
        let sum_x: f32 = log_n.par_iter().sum();
        let sum_y: f32 = log_rs.par_iter().sum();
        let sum_xy: f32 = log_n
            .par_iter()
            .zip(log_rs.par_iter())
            .map(|(x, y)| x * y)
            .sum();
        let sum_xx: f32 = log_n.par_iter().map(|x| x * x).sum();

        let slope =
            (n as f32 * sum_xy - sum_x * sum_y) / (n as f32 * sum_xx - sum_x * sum_x + 1e-8);
        slope.clamp(0.0, 1.0)
    }

    /// Detrended Fluctuation Analysis (alternative Hurst estimate)
    fn dfa(&self) -> f32 {
        if self.returns.len() < 30 {
            return 0.5;
        }

        let series: Vec<f32> = self.returns.iter().cloned().collect();

        // Integrate
        let mut integrated = vec![0.0];
        for &r in &series {
            integrated.push(integrated.last().copied().unwrap_or(0.0) + r);
        }

        // Calculate F(n) for different window sizes
        let f_values: Vec<f32> = [4, 8, 16, 32, 64]
            .iter()
            .filter(|&&n| n < integrated.len())
            .map(|&n| {
                let chunks: Vec<&[f32]> = integrated.chunks(n).collect();
                let fluctuations: Vec<f32> = chunks
                    .iter()
                    .map(|chunk| {
                        // Linear detrending
                        let len = chunk.len();
                        let sum_x: f32 = (0..len).map(|i| i as f32).sum();
                        let sum_y: f32 = chunk.par_iter().sum();
                        let sum_xy: f32 =
                            chunk.iter().enumerate().map(|(i, &y)| i as f32 * y).sum();
                        let sum_xx: f32 = (0..len).map(|i| (i * i) as f32).sum();

                        let denom = len as f32 * sum_xx - sum_x * sum_x;
                        let (slope, intercept) = if denom.abs() > 1e-8 {
                            let b = (len as f32 * sum_xy - sum_x * sum_y) / denom;
                            let a = (sum_y - b * sum_x) / len as f32;
                            (b, a)
                        } else {
                            (0.0, sum_y / len as f32)
                        };

                        // RMS of detrended
                        let rms: f32 = chunk
                            .iter()
                            .enumerate()
                            .map(|(i, &y)| {
                                let trend = intercept + slope * i as f32;
                                (y - trend).powi(2)
                            })
                            .sum::<f32>()
                            / len as f32;
                        rms.sqrt()
                    })
                    .collect();
                fluctuations.par_iter().sum::<f32>() / fluctuations.len().max(1) as f32
            })
            .collect();

        // Linear regression of log(F) vs log(n)
        let log_n: Vec<f32> = [4, 8, 16, 32, 64]
            .iter()
            .filter(|&&n| n < integrated.len())
            .map(|n| (*n as f32).ln())
            .collect();
        let log_f: Vec<f32> = f_values.par_iter().map(|f| f.max(0.01).ln()).collect();
        let n = log_f.len();
        if n < 2 {
            return 0.5;
        }
        let sum_x: f32 = log_n.par_iter().sum();
        let sum_y: f32 = log_f.par_iter().sum();
        let sum_xy: f32 = log_n
            .par_iter()
            .zip(log_f.par_iter())
            .map(|(x, y)| x * y)
            .sum();
        let sum_xx: f32 = log_n.par_iter().map(|x| x * x).sum();

        let alpha =
            (n as f32 * sum_xy - sum_x * sum_y) / (n as f32 * sum_xx - sum_x * sum_x + 1e-8);
        // Hurst = alpha for fractional Brownian motion
        alpha.clamp(0.0, 1.0)
    }
}

// ============================================================================
// INFORMATION THEORETIC MEASURES (Entropy, Mutual Info, Transfer Entropy)
// ============================================================================

#[derive(Debug, Clone)]
struct InformationTheoretic {
    // For estimating probabilities
    win_history: VecDeque<bool>,
    symbol_counts: HashMap<u8, usize>,
    pair_counts: HashMap<(u8, u8), usize>,
    triple_counts: HashMap<(u8, u8, u8), usize>,
    history_size: usize,
}

impl InformationTheoretic {
    fn new(history_size: usize) -> Self {
        Self {
            win_history: VecDeque::with_capacity(history_size),
            symbol_counts: HashMap::new(),
            pair_counts: HashMap::new(),
            triple_counts: HashMap::new(),
            history_size,
        }
    }

    fn observe(&mut self, win: bool) {
        self.win_history.push_back(win);
        if self.win_history.len() > self.history_size {
            self.win_history.pop_front();
        }
        self.update_counts();
    }

    fn update_counts(&mut self) {
        self.symbol_counts.clear();
        self.pair_counts.clear();
        self.triple_counts.clear();

        let symbols: Vec<u8> = self
            .win_history
            .iter()
            .map(|&w| if w { 1 } else { 0 })
            .collect();

        // Single symbol counts
        for &s in &symbols {
            *self.symbol_counts.entry(s).or_insert(0) += 1;
        }

        // Pair counts
        for i in 0..symbols.len().saturating_sub(1) {
            *self
                .pair_counts
                .entry((symbols[i], symbols[i + 1]))
                .or_insert(0) += 1;
        }

        // Triple counts
        for i in 0..symbols.len().saturating_sub(2) {
            *self
                .triple_counts
                .entry((symbols[i], symbols[i + 1], symbols[i + 2]))
                .or_insert(0) += 1;
        }
    }

    /// Shannon entropy H(X)
    fn entropy(&self) -> f32 {
        let total = self.symbol_counts.values().sum::<usize>() as f32;
        if total == 0.0 {
            return 1.0; // Maximum uncertainty
        }

        -self
            .symbol_counts
            .values()
            .map(|&c| {
                let p = c as f32 / total;
                if p > 0.0 {
                    p * p.log2()
                } else {
                    0.0
                }
            })
            .sum::<f32>()
    }

    /// Joint entropy H(X, Y)
    fn joint_entropy(&self) -> f32 {
        let total = self.pair_counts.values().sum::<usize>() as f32;
        if total == 0.0 {
            return 2.0;
        }

        -self
            .pair_counts
            .values()
            .map(|&c| {
                let p = c as f32 / total;
                if p > 0.0 {
                    p * p.log2()
                } else {
                    0.0
                }
            })
            .sum::<f32>()
    }

    /// Conditional entropy H(X|Y) = H(X,Y) - H(Y)
    fn conditional_entropy(&self) -> f32 {
        self.joint_entropy() - self.entropy()
    }

    /// Mutual information I(X;Y) = H(X) + H(Y) - H(X,Y)
    fn mutual_information(&self) -> f32 {
        2.0 * self.entropy() - self.joint_entropy()
    }

    /// Transfer entropy T_{X->Y} = H(Y_{t+1}|Y_t) - H(Y_{t+1}|Y_t, X_t)
    fn transfer_entropy(&self) -> f32 {
        let h_y = self.entropy();
        let h_yy = self.conditional_entropy();

        // Simplified: H(Y_{t+1}|Y_t) - H(Y_{t+1}|Y_t, X_t)
        // More complex calculation would need 4-grams
        h_y - h_yy
    }

    /// Permutation entropy (ordinal patterns)
    fn permutation_entropy(&self, order: usize) -> f32 {
        if self.win_history.len() < order + 1 {
            return 1.0;
        }

        let symbols: Vec<f32> = self
            .win_history
            .iter()
            .map(|&w| if w { 1.0 } else { 0.0 })
            .collect();

        // Count ordinal patterns
        let mut pattern_counts: HashMap<Vec<usize>, usize> = HashMap::new();

        for i in 0..symbols.len() - order + 1 {
            let window: Vec<f32> = symbols[i..i + order].to_vec();
            // Get permutation pattern
            let mut indexed: Vec<(usize, f32)> = window.iter().cloned().enumerate().collect();
            indexed.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
            let pattern: Vec<usize> = indexed.iter().map(|(i, _)| *i).collect();
            *pattern_counts.entry(pattern).or_insert(0) += 1;
        }

        let total = pattern_counts.values().sum::<usize>() as f32;
        if total == 0.0 {
            return 1.0;
        }

        -pattern_counts
            .values()
            .map(|&c| {
                let p = c as f32 / total;
                if p > 0.0 {
                    p * p.log2()
                } else {
                    0.0
                }
            })
            .sum::<f32>()
            / 2.0_f32.powf(order as f32 * (order as f32).ln() / 2.0_f32.ln())
    }

    /// Approximate entropy
    fn approximate_entropy(&self, m: usize, r: f32) -> f32 {
        if self.win_history.len() < m + 2 {
            return 0.0;
        }

        let u: Vec<f32> = self
            .win_history
            .iter()
            .map(|&w| if w { 1.0 } else { 0.0 })
            .collect();

        let phi = |dim: usize| -> f32 {
            let mut count_sum = 0.0;
            for i in 0..u.len() - dim + 1 {
                let template: Vec<f32> = u[i..i + dim].to_vec();
                let mut matches = 0;
                for j in 0..u.len() - dim + 1 {
                    let dist: f32 = template
                        .iter()
                        .zip(u[j..j + dim].iter())
                        .map(|(a, b)| (a - b).abs())
                        .fold(0.0_f32, |max, d| max.max(d));
                    if dist <= r {
                        matches += 1;
                    }
                }
                count_sum += (matches as f32 / (u.len() - dim + 1) as f32).ln();
            }
            count_sum / (u.len() - dim + 1) as f32
        };

        phi(m) - phi(m + 1)
    }

    /// Sample entropy
    fn sample_entropy(&self, m: usize, r: f32) -> f32 {
        if self.win_history.len() < m + 2 {
            return 0.0;
        }

        let u: Vec<f32> = self
            .win_history
            .iter()
            .map(|&w| if w { 1.0 } else { 0.0 })
            .collect();

        let count_matches = |dim: usize| -> usize {
            let mut matches = 0;
            for i in 0..u.len() - dim {
                for j in (i + 1)..u.len() - dim + 1 {
                    let dist: f32 = u[i..i + dim]
                        .iter()
                        .zip(u[j..j + dim].iter())
                        .map(|(a, b)| (a - b).abs())
                        .fold(0.0_f32, |max, d| max.max(d));
                    if dist <= r {
                        matches += 1;
                    }
                }
            }
            matches
        };

        let a = count_matches(m + 1);
        let b = count_matches(m);

        if b == 0 {
            return 0.0;
        }
        -(a as f32 / b as f32).ln()
    }
}

// ============================================================================
// GAUSSIAN PROCESS THOMPSON SAMPLING
// ============================================================================

#[derive(Debug, Clone)]
struct GPThompsonSampling {
    gp_x: Vec<Vec<f32>>,
    gp_y: Vec<f32>,
    length_scale: f32,
    signal_var: f32,
    noise_var: f32,
    max_samples: usize,
}

impl GPThompsonSampling {
    fn new(length_scale: f32, signal_var: f32, noise_var: f32, max_samples: usize) -> Self {
        Self {
            gp_x: Vec::with_capacity(max_samples),
            gp_y: Vec::with_capacity(max_samples),
            length_scale,
            signal_var,
            noise_var,
            max_samples,
        }
    }

    fn rbf_kernel(&self, x1: &[f32], x2: &[f32]) -> f32 {
        let dist: f32 = x1.iter().zip(x2.iter()).map(|(a, b)| (a - b).powi(2)).sum();
        self.signal_var * (-dist / (2.0 * self.length_scale.powi(2))).exp()
    }

    fn add_observation(&mut self, x: Vec<f32>, y: f32) {
        self.gp_x.push(x);
        self.gp_y.push(y);
        if self.gp_x.len() > self.max_samples {
            self.gp_x.remove(0);
            self.gp_y.remove(0);
        }
    }

    fn predict(&self, x: &[f32]) -> (f32, f32) {
        if self.gp_x.is_empty() {
            return (0.0, self.signal_var);
        }

        let n = self.gp_x.len();

        // K(X, X) + noise
        let mut k_xx = vec![vec![0.0; n]; n];
        for i in 0..n {
            for j in 0..n {
                k_xx[i][j] = self.rbf_kernel(&self.gp_x[i], &self.gp_x[j]);
                if i == j {
                    k_xx[i][j] += self.noise_var;
                }
            }
        }

        // K(x, X)
        let k_x: Vec<f32> = self
            .gp_x
            .par_iter()
            .map(|xi| self.rbf_kernel(x, xi))
            .collect();

        // K(x, x)
        let k_xx_diag = self.signal_var;

        // Solve K^-1 * y (simplified using gradient descent)
        let mut alpha = vec![0.0; n];
        for _ in 0..100 {
            for i in 0..n {
                let mut sum = 0.0;
                for j in 0..n {
                    sum += k_xx[i][j] * alpha[j];
                }
                alpha[i] += 0.01 * (self.gp_y[i] - sum);
            }
        }

        // Mean
        let mean: f32 = k_x.iter().zip(alpha.iter()).map(|(k, a)| k * a).sum();

        // Variance (simplified)
        let mut k_inv_k = vec![0.0; n];
        for i in 0..n {
            for j in 0..n {
                k_inv_k[i] += alpha[j] * k_xx[i][j]; // Approximate
            }
        }
        let variance = k_xx_diag
            - k_x
                .iter()
                .zip(k_inv_k.iter())
                .map(|(k, ki)| k * ki)
                .sum::<f32>();

        (mean, variance.max(0.0))
    }

    fn sample(&self, x: &[f32]) -> f32 {
        let (mean, variance) = self.predict(x);
        // Gaussian sample
        let u1 = rand::rng().random::<f32>();
        let u2 = rand::rng().random::<f32>();
        let z = (-2.0 * u1.max(1e-8).ln()).sqrt() * (2.0 * 3.14159 * u2).cos();
        mean + variance.sqrt() * z
    }
}

// ============================================================================
// DISTRIBUTIONAL RL (C51 style categorical distribution)
// ============================================================================

#[derive(Debug, Clone)]
struct CategoricalDQN {
    num_atoms: usize,
    vmin: f32,
    vmax: f32,
    support: Vec<f32>,
    state_dim: usize,
    num_actions: usize,
    weights: Vec<Vec<Vec<f32>>>, // [layer][output][input]
    biases: Vec<Vec<f32>>,
}

impl CategoricalDQN {
    fn new(state_dim: usize, num_actions: usize, num_atoms: usize, vmin: f32, vmax: f32) -> Self {
        let support: Vec<f32> = (0..num_atoms)
            .map(|i| vmin + (vmax - vmin) * i as f32 / (num_atoms - 1) as f32)
            .collect();

        let hidden_dim = 128;

        Self {
            num_atoms,
            vmin,
            vmax,
            support,
            state_dim,
            num_actions,
            weights: vec![
                // Input -> Hidden
                (0..hidden_dim)
                    .map(|_| {
                        (0..state_dim)
                            .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                            .collect()
                    })
                    .collect(),
                // Hidden -> Output (actions * atoms)
                (0..num_actions * num_atoms)
                    .map(|_| {
                        (0..hidden_dim)
                            .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                            .collect()
                    })
                    .collect(),
            ],
            biases: vec![vec![0.0; hidden_dim], vec![0.0; num_actions * num_atoms]],
        }
    }

    fn forward(&self, state: &[f32]) -> Vec<Vec<f32>> {
        // Layer 1
        let mut hidden: Vec<f32> = self.weights[0]
            .iter()
            .zip(self.biases[0].iter())
            .map(|(w, b)| {
                let sum: f32 = w.iter().zip(state.iter()).map(|(wi, si)| wi * si).sum();
                (sum + b).max(0.0) // ReLU
            })
            .collect();

        // Layer 2
        let output: Vec<f32> = self.weights[1]
            .iter()
            .zip(self.biases[1].iter())
            .map(|(w, b)| {
                let sum: f32 = w.iter().zip(hidden.iter()).map(|(wi, hi)| wi * hi).sum();
                sum + b
            })
            .collect();

        // Reshape to [num_actions, num_atoms] and softmax
        (0..self.num_actions)
            .map(|a| {
                let atoms: Vec<f32> = output[a * self.num_atoms..(a + 1) * self.num_atoms].to_vec();
                // Softmax
                let max_atom = atoms.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
                let exp_sum: f32 = atoms.par_iter().map(|x| (x - max_atom).exp()).sum();
                atoms
                    .iter()
                    .map(|x| (x - max_atom).exp() / exp_sum)
                    .collect()
            })
            .collect()
    }

    fn get_q_values(&self, state: &[f32]) -> Vec<f32> {
        let dists = self.forward(state);
        dists
            .iter()
            .map(|dist| {
                dist.iter()
                    .zip(self.support.iter())
                    .map(|(p, z)| p * z)
                    .sum()
            })
            .collect()
    }

    fn update(
        &mut self,
        state: &[f32],
        action: usize,
        reward: f32,
        next_state: &[f32],
        done: bool,
        gamma: f32,
        lr: f32,
    ) {
        let dist = self.forward(state);
        let next_dist = self.forward(next_state);

        // Find best next action
        let next_q: Vec<f32> = next_dist
            .iter()
            .map(|d| d.iter().zip(self.support.iter()).map(|(p, z)| p * z).sum())
            .collect();
        let best_next_action = next_q
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(0);

        // Compute target distribution
        let mut target_dist = vec![0.0; self.num_atoms];
        for (j, &z) in self.support.iter().enumerate() {
            let tz = if done {
                reward.clamp(self.vmin, self.vmax)
            } else {
                (reward + gamma * z).clamp(self.vmin, self.vmax)
            };

            // Distribute to nearest atoms
            let bj = (tz - self.vmin) / (self.vmax - self.vmin) * (self.num_atoms - 1) as f32;
            let l = bj.floor() as usize;
            let u = bj.ceil() as usize;

            if l >= self.num_atoms || u >= self.num_atoms {
                continue;
            }

            let dl = tz - self.support[l];
            let du = self.support[u.min(self.num_atoms - 1)] - tz;
            let total_dist = dl + du;

            if total_dist > 0.0 && u < self.num_atoms {
                // Projection
                let next_p = next_dist[best_next_action][j];
                let l_clamped = l.min(self.num_atoms - 1);
                let u_clamped = u.min(self.num_atoms - 1);
                target_dist[l_clamped] += next_p * du / total_dist;
                target_dist[u_clamped] += next_p * dl / total_dist;
            }
        }

        // Cross-entropy loss gradient update (simplified)
        for i in 0..self.weights[1]
            .len()
            .min(action * self.num_atoms + self.num_atoms)
        {
            let atom_idx = i % self.num_atoms;
            let log_prob = (dist[action][atom_idx].max(1e-8)).ln();
            let target_log_prob = (target_dist[atom_idx].max(1e-8)).ln();
            let grad = (log_prob - target_log_prob) * lr;

            for w in self.weights[1][i].iter_mut() {
                *w -= grad * 0.01;
            }
        }
    }
}

// ============================================================================
// QUANTUM-INSPIRED ANNEALING OPTIMIZER
// ============================================================================

#[derive(Debug, Clone)]
struct QuantumAnnealingOptimizer {
    spins: Vec<f32>,          // Continuous spin values [-1, 1]
    fields: Vec<f32>,         // External fields
    couplings: Vec<Vec<f32>>, // Spin-spin couplings
    temperature: f32,
    tunneling_strength: f32,
    num_spins: usize,
}

impl QuantumAnnealingOptimizer {
    fn new(num_spins: usize) -> Self {
        Self {
            spins: vec![0.0; num_spins],
            fields: (0..num_spins)
                .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                .collect(),
            couplings: (0..num_spins)
                .map(|i| {
                    (0..num_spins)
                        .map(|j| {
                            if i == j {
                                0.0
                            } else {
                                rand::rng().random::<f32>() * 0.1 - 0.05
                            }
                        })
                        .collect()
                })
                .collect(),
            temperature: 1.0,
            tunneling_strength: 0.5,
            num_spins,
        }
    }

    fn energy(&self) -> f32 {
        let mut e = 0.0;
        // External field contribution
        for (i, (&spin, &field)) in self.spins.iter().zip(self.fields.iter()).enumerate() {
            e -= field * spin;
        }
        // Coupling contribution
        for i in 0..self.num_spins {
            for j in (i + 1)..self.num_spins {
                e -= self.couplings[i][j] * self.spins[i] * self.spins[j];
            }
        }
        e
    }

    fn local_field(&self, i: usize) -> f32 {
        let mut h = self.fields[i];
        for j in 0..self.num_spins {
            if i != j {
                h += self.couplings[i][j] * self.spins[j];
            }
        }
        h
    }

    fn anneal_step(&mut self) {
        for i in 0..self.num_spins {
            let h = self.local_field(i);

            // Classical thermal flip probability
            let delta_e = 2.0 * h * self.spins[i];
            let thermal_prob = (-delta_e / self.temperature).exp();

            // Quantum tunneling probability
            let tunnel_prob =
                self.tunneling_strength * (-self.tunneling_strength * self.spins[i].abs()).exp();

            // Combined update
            let flip_prob = thermal_prob + tunnel_prob;

            if rand::rng().random::<f32>() < flip_prob {
                self.spins[i] *= -1.0;
            } else {
                // Continuous spin update
                let grad = -h + 0.1 * self.spins[i].copysign(1.0); // Regularization
                self.spins[i] = (self.spins[i] - 0.01 * grad).clamp(-1.0, 1.0);
            }
        }

        // Decrease temperature (annealing schedule)
        self.temperature *= 0.999;
        self.tunneling_strength *= 0.999;
    }

    fn get_spin_configuration(&self) -> Vec<i32> {
        self.spins
            .iter()
            .map(|&s| if s > 0.0 { 1 } else { -1 })
            .collect()
    }

    fn to_probability(&self, spin_idx: usize) -> f32 {
        (self.spins[spin_idx] + 1.0) / 2.0
    }
}

// ============================================================================
// META-RL LEARNER (learns to learn)
// ============================================================================

#[derive(Debug, Clone)]
struct MetaRLLearner {
    // Fast weights (task-specific, updated quickly)
    fast_weights: Vec<Vec<f32>>,
    // Slow weights (meta-learned, updated slowly)
    slow_weights: Vec<Vec<f32>>,
    // Update history for meta-gradient
    update_history: VecDeque<Vec<Vec<f32>>>,
    meta_lr: f32,
    inner_lr: f32,
    hidden_dim: usize,
}

impl MetaRLLearner {
    fn new(input_dim: usize, hidden_dim: usize, output_dim: usize) -> Self {
        let init = || {
            (0..hidden_dim)
                .map(|_| {
                    (0..input_dim + 1)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect()
        };

        Self {
            fast_weights: init(),
            slow_weights: init(),
            update_history: VecDeque::with_capacity(100),
            meta_lr: 0.001,
            inner_lr: 0.01,
            hidden_dim,
        }
    }

    fn forward(&self, input: &[f32], use_fast: bool) -> Vec<f32> {
        let weights = if use_fast {
            &self.fast_weights
        } else {
            &self.slow_weights
        };

        weights
            .iter()
            .map(|w| {
                let sum: f32 = input.iter().zip(w.iter()).map(|(inp, wi)| inp * wi).sum();
                (sum + w.last().copied().unwrap_or(0.0)).tanh()
            })
            .collect()
    }

    fn inner_update(&mut self, input: &[f32], target: f32) -> f32 {
        let output = self.forward(input, true);
        let pred = output.first().copied().unwrap_or(0.0);
        let loss = (pred - target).powi(2);

        // Compute gradients and update fast weights
        let grad = 2.0 * (pred - target);
        for w in self.fast_weights.iter_mut() {
            for wi in w.iter_mut() {
                *wi -= self.inner_lr * grad * 0.1;
            }
        }

        loss
    }

    fn meta_update(&mut self) {
        if self.update_history.is_empty() {
            return;
        }

        // Compute meta-gradient from update history
        let meta_grad: Vec<Vec<f32>> = self
            .update_history
            .iter()
            .rev()
            .take(10)
            .flat_map(|updates| updates.iter().cloned())
            .collect();

        // Update slow weights towards direction of successful updates
        for (sw, mg) in self.slow_weights.iter_mut().zip(meta_grad.iter()) {
            for (w, g) in sw.iter_mut().zip(mg.iter()) {
                *w -= self.meta_lr * g;
            }
        }
    }

    fn reset_fast_weights(&mut self) {
        // Reset fast weights to slow weights (new task)
        self.fast_weights = self.slow_weights.clone();
    }

    fn store_update(&mut self) {
        let update: Vec<Vec<f32>> = self
            .fast_weights
            .iter()
            .zip(self.slow_weights.iter())
            .map(|(f, s)| f.iter().zip(s.iter()).map(|(fi, si)| fi - si).collect())
            .collect();
        self.update_history.push_back(update);
        if self.update_history.len() > 100 {
            self.update_history.pop_front();
        }
    }
}

// ============================================================================
// POPULATION-BASED TRAINING (PBT)
// ============================================================================

#[derive(Debug, Clone)]
struct PBTPopulation {
    population: Vec<PBTAgent>,
    generation: usize,
    population_size: usize,
}

#[derive(Debug, Clone)]
struct PBTAgent {
    weights: Vec<f32>,
    hyperparams: Vec<f32>, // [learning_rate, exploration, etc.]
    fitness: f32,
    id: usize,
}

impl PBTPopulation {
    fn new(population_size: usize, weight_dim: usize) -> Self {
        Self {
            population: (0..population_size)
                .map(|id| PBTAgent {
                    weights: (0..weight_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.2 - 0.1)
                        .collect(),
                    hyperparams: vec![0.01, 0.1, 0.9], // lr, exploration, momentum
                    fitness: 0.0,
                    id,
                })
                .collect(),
            generation: 0,
            population_size,
        }
    }

    fn evaluate(&mut self, fitness_fn: impl Fn(&[f32]) -> f32) {
        for agent in &mut self.population {
            agent.fitness = fitness_fn(&agent.weights);
        }
    }

    fn exploit_explore(&mut self) {
        // Sort by fitness
        self.population.sort_by(|a, b| {
            b.fitness
                .partial_cmp(&a.fitness)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        let n = self.population.len();
        let top_n = n / 4;
        let bottom_n = n / 4;

        // Replace bottom performers with copies of top performers
        for i in 0..bottom_n {
            let top_agent = &self.population[i];
            self.population[n - 1 - i] = top_agent.clone();

            // Mutate hyperparameters
            for hp in &mut self.population[n - 1 - i].hyperparams {
                *hp *= 1.0 + (rand::rng().random::<f32>() - 0.5) * 0.2; // ±10% mutation
                *hp = hp.max(1e-6);
            }
        }
    }

    fn step(&mut self, fitness_fn: impl Fn(&[f32]) -> f32) {
        // Train each agent
        for agent in &mut self.population {
            let lr = agent.hyperparams[0];
            let exploration = agent.hyperparams[1];

            // Gradient-free update with exploration noise
            for w in &mut agent.weights {
                *w += lr * (rand::rng().random::<f32>() - 0.5) * exploration;
            }
        }

        // Evaluate
        self.evaluate(fitness_fn);

        // Exploit and explore
        self.exploit_explore();

        self.generation += 1;
    }

    fn best_agent(&self) -> &PBTAgent {
        self.population
            .iter()
            .max_by(|a, b| {
                a.fitness
                    .partial_cmp(&b.fitness)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap_or(&self.population[0])
    }
}

// ============================================================================
// SAFE RL WITH CONSTRAINTS (CMDP)
// ============================================================================

#[derive(Debug, Clone)]
struct SafeRLAgent {
    // Actor network
    actor_weights: Vec<Vec<f32>>,
    // Critic network for value
    critic_weights: Vec<Vec<f32>>,
    // Cost critic for constraint violation
    cost_critic_weights: Vec<Vec<f32>>,
    // Lagrange multiplier for constraint
    lagrange_lambda: f32,
    cost_limit: f32,
    alpha: f32, // Lagrange multiplier learning rate
    gamma: f32,
    lr: f32,
}

impl SafeRLAgent {
    fn new(state_dim: usize, action_dim: usize, hidden_dim: usize) -> Self {
        Self {
            actor_weights: (0..action_dim)
                .map(|_| {
                    (0..hidden_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            critic_weights: (0..hidden_dim)
                .map(|_| {
                    (0..state_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            cost_critic_weights: (0..hidden_dim)
                .map(|_| {
                    (0..state_dim)
                        .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                        .collect()
                })
                .collect(),
            lagrange_lambda: 1.0,
            cost_limit: 0.1,
            alpha: 0.01,
            gamma: 0.99,
            lr: 0.001,
        }
    }

    fn forward_actor(&self, state: &[f32], hidden: &[f32]) -> Vec<f32> {
        self.actor_weights
            .iter()
            .map(|w| {
                let sum: f32 = hidden.iter().zip(w.iter()).map(|(h, wi)| h * wi).sum();
                sum.tanh()
            })
            .collect()
    }

    fn forward_critic(&self, state: &[f32]) -> f32 {
        let hidden: Vec<f32> = self
            .critic_weights
            .iter()
            .map(|w| {
                let sum: f32 = state.iter().zip(w.iter()).map(|(s, wi)| s * wi).sum();
                sum.max(0.0)
            })
            .collect();
        hidden.par_iter().sum()
    }

    fn forward_cost_critic(&self, state: &[f32]) -> f32 {
        let hidden: Vec<f32> = self
            .cost_critic_weights
            .iter()
            .map(|w| {
                let sum: f32 = state.iter().zip(w.iter()).map(|(s, wi)| s * wi).sum();
                sum.max(0.0)
            })
            .collect();
        hidden.par_iter().sum()
    }

    fn update(
        &mut self,
        state: &[f32],
        action_idx: usize,
        reward: f32,
        cost: f32,
        next_state: &[f32],
        done: bool,
    ) {
        // TD targets
        let next_value = if done {
            0.0
        } else {
            self.forward_critic(next_state)
        };
        let next_cost = if done {
            0.0
        } else {
            self.forward_cost_critic(next_state)
        };

        let td_target = reward + self.gamma * next_value;
        let cost_td_target = cost + self.gamma * next_cost;

        // Update critics
        let current_value = self.forward_critic(state);
        let value_error = td_target - current_value;

        let current_cost = self.forward_cost_critic(state);
        let cost_error = cost_td_target - current_cost;

        for w in self.critic_weights.iter_mut() {
            for wi in w.iter_mut() {
                *wi += self.lr * value_error * 0.01;
            }
        }

        for w in self.cost_critic_weights.iter_mut() {
            for wi in w.iter_mut() {
                *wi += self.lr * cost_error * 0.01;
            }
        }

        // Update Lagrange multiplier
        self.lagrange_lambda += self.alpha * (current_cost - self.cost_limit);
        self.lagrange_lambda = self.lagrange_lambda.max(0.0);

        // Update actor with Lagrangian objective
        let safe_reward = reward - self.lagrange_lambda * cost;
        for (i, w) in self.actor_weights.iter_mut().enumerate() {
            if i == action_idx {
                for wi in w.iter_mut() {
                    *wi += self.lr * safe_reward * 0.01;
                }
            }
        }
    }
}

// ============================================================================
// ORNSTEIN-UHLENBECK PROCESS (Mean-reverting stochastic)
// ============================================================================

#[derive(Debug, Clone)]
struct OrnsteinUhlenbeckProcess {
    theta: f32, // Mean reversion speed
    mu: f32,    // Long-term mean
    sigma: f32, // Volatility
    current_value: f32,
}

impl OrnsteinUhlenbeckProcess {
    fn new(theta: f32, mu: f32, sigma: f32, initial: f32) -> Self {
        Self {
            theta,
            mu,
            sigma,
            current_value: initial,
        }
    }

    fn step(&mut self, dt: f32) -> f32 {
        // OU SDE: dX = θ(μ - X)dt + σdW
        let dW = rand::rng().random::<f32>() * dt.sqrt() * (2.0_f32 * std::f32::consts::PI).sin(); // Approximate Brownian
        let dx = self.theta * (self.mu - self.current_value) * dt + self.sigma * dW;
        self.current_value += dx;
        self.current_value
    }

    fn predict(&self, steps: usize, dt: f32) -> Vec<f32> {
        let mut predictions = Vec::with_capacity(steps);
        let mut x = self.current_value;

        for _ in 0..steps {
            let expected = x + self.theta * (self.mu - x) * dt;
            predictions.push(expected);
            x = expected;
        }

        predictions
    }

    fn reset(&mut self, value: f32) {
        self.current_value = value;
    }
}

// ============================================================================
// GUMBEL ALPHAZERO STYLE MCTS
// ============================================================================

#[derive(Debug, Clone)]
struct GumbelMCTS {
    visits: Vec<usize>,
    q_values: Vec<f32>,
    gumbel_values: Vec<f32>,
    num_actions: usize,
    c_visit: f32,
    c_scale: f32,
}

impl GumbelMCTS {
    fn new(num_actions: usize) -> Self {
        Self {
            visits: vec![0; num_actions],
            q_values: vec![0.0; num_actions],
            gumbel_values: (0..num_actions)
                .map(|_| {
                    let u = rand::rng().random::<f32>().max(1e-8);
                    -(-u.ln()).ln()
                })
                .collect(),
            num_actions,
            c_visit: 50.0,
            c_scale: 10.0,
        }
    }

    fn gumbel_score(&self, action: usize, policy_prior: f32) -> f32 {
        let visit_term = self.c_visit + (self.visits[action] as f32).max(1.0).ln();
        let sigma_q = self.sigma_q();
        self.gumbel_values[action]
            + policy_prior.ln()
            + (self.q_values[action] * sigma_q * self.c_scale / visit_term).ln()
    }

    fn sigma_q(&self) -> f32 {
        let max_q = self
            .q_values
            .iter()
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        let min_q = self.q_values.iter().cloned().fold(f32::INFINITY, f32::min);
        if (max_q - min_q).abs() > 1e-8 {
            1.0 / (max_q - min_q)
        } else {
            1.0
        }
    }

    fn select(&self, policy_prior: &[f32]) -> usize {
        let scores: Vec<f32> = (0..self.num_actions)
            .map(|a| self.gumbel_score(a, policy_prior[a]))
            .collect();

        scores
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(0)
    }

    fn update(&mut self, action: usize, value: f32) {
        let n = self.visits[action] as f32;
        self.q_values[action] = (self.q_values[action] * n + value) / (n + 1.0);
        self.visits[action] += 1;
    }

    fn get_improved_policy(&self) -> Vec<f32> {
        let total_visits: usize = self.visits.par_iter().sum();
        if total_visits == 0 {
            return vec![1.0 / self.num_actions as f32; self.num_actions];
        }

        self.visits
            .iter()
            .map(|&v| v as f32 / total_visits as f32)
            .collect()
    }
}

// ============================================================================
// ADVERSARIAL BANDIT (EXP3)
// ============================================================================

#[derive(Debug, Clone)]
struct EXP3Bandit {
    weights: Vec<f32>,
    gamma: f32, // Exploration parameter
    num_arms: usize,
}

impl EXP3Bandit {
    fn new(num_arms: usize, gamma: f32) -> Self {
        Self {
            weights: vec![1.0; num_arms],
            gamma,
            num_arms,
        }
    }

    fn get_distribution(&self) -> Vec<f32> {
        let total_weight: f32 = self.weights.par_iter().sum();
        self.weights
            .iter()
            .map(|&w| (1.0 - self.gamma) * w / total_weight + self.gamma / self.num_arms as f32)
            .collect()
    }

    fn select(&mut self) -> usize {
        let dist = self.get_distribution();
        let r = rand::rng().random::<f32>();
        let mut cumsum = 0.0;
        for (i, &p) in dist.iter().enumerate() {
            cumsum += p;
            if r < cumsum {
                return i;
            }
        }
        self.num_arms - 1
    }

    fn update(&mut self, arm: usize, reward: f32) {
        let dist = self.get_distribution();
        let estimated_reward = reward / dist[arm].max(1e-8);
        self.weights[arm] *= (self.gamma * estimated_reward / self.num_arms as f32).exp();
    }
}

// ============================================================================
// TEMPORAL CONVOLUTIONAL NETWORK (TCN)
// ============================================================================

#[derive(Debug, Clone)]
struct TCN {
    layers: Vec<TCNLayer>,
    output_weights: Vec<f32>,
}

#[derive(Debug, Clone)]
struct TCNLayer {
    conv_weights: Vec<Vec<Vec<f32>>>, // [output_channels][kernel_size][input_channels]
    kernel_size: usize,
    dilation: usize,
    residual_weights: Option<Vec<f32>>,
}

impl TCN {
    fn new(
        input_channels: usize,
        num_layers: usize,
        hidden_channels: usize,
        kernel_size: usize,
    ) -> Self {
        let mut layers = Vec::new();
        let mut in_channels = input_channels;

        for i in 0..num_layers {
            let dilation = 2_usize.pow(i as u32);
            layers.push(TCNLayer {
                conv_weights: (0..hidden_channels)
                    .map(|_| {
                        (0..kernel_size)
                            .map(|_| {
                                (0..in_channels)
                                    .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                                    .collect::<Vec<_>>()
                            })
                            .collect::<Vec<_>>()
                    })
                    .collect::<Vec<_>>(),
                kernel_size,
                dilation,
                residual_weights: if in_channels == hidden_channels {
                    Some(
                        (0..hidden_channels)
                            .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                            .collect(),
                    )
                } else {
                    None
                },
            });
            in_channels = hidden_channels;
        }

        Self {
            layers,
            output_weights: (0..hidden_channels)
                .map(|_| rand::rng().random::<f32>() * 0.1 - 0.05)
                .collect(),
        }
    }

    fn forward(&self, sequence: &[Vec<f32>]) -> Vec<f32> {
        let mut x = sequence.to_vec();

        for layer in &self.layers {
            x = layer.forward(&x);
        }

        // Take last output
        if let Some(last) = x.last() {
            let sum: f32 = self
                .output_weights
                .iter()
                .zip(last.iter())
                .map(|(w, &v)| w * v)
                .sum();
            vec![sum.tanh()]
        } else {
            vec![0.5]
        }
    }
}

impl TCNLayer {
    fn forward(&self, input: &[Vec<f32>]) -> Vec<Vec<f32>> {
        let input_len = input.len();
        let output_channels = self.conv_weights.len();
        let mut output = vec![vec![0.0_f32; output_channels]; input_len];

        for t in 0..input_len {
            for (out_ch, kernel) in self.conv_weights.iter().enumerate() {
                for (k_idx, kernel_row) in kernel.iter().enumerate() {
                    let t_input = t as isize - (k_idx as isize * self.dilation as isize);
                    if t_input >= 0 && (t_input as usize) < input_len {
                        for (in_ch, &w) in kernel_row.iter().enumerate() {
                            if in_ch < input[t_input as usize].len() {
                                output[t][out_ch] += w * input[t_input as usize][in_ch];
                            }
                        }
                    }
                }
                output[t][out_ch] = output[t][out_ch].max(0.0_f32); // ReLU
            }
        }

        // Residual connection
        if let Some(ref res_w) = self.residual_weights {
            for t in 0..input_len {
                for (ch, &w) in res_w.iter().enumerate() {
                    if ch < output[t].len() && t < input.len() && ch < input[t].len() {
                        output[t][ch] += w * input[t][ch];
                    }
                }
            }
        }

        output
    }
}

// ============================================================================
// BAYESIAN ARM (THOMPSON SAMPLING)
// ============================================================================

#[derive(Debug, Clone)]
struct BayesianArm {
    multiplier: f32,
    alpha: f32,
    beta: f32,
    total_profit: f32,
    recent_profits: TimeDecayedStats,
    win_streak: u32,
    loss_streak: u32,
    pull_count: u32,
}

impl BayesianArm {
    fn new(multiplier: f32) -> Self {
        Self {
            multiplier,
            alpha: 1.0,
            beta: 1.0,
            total_profit: 0.0,
            recent_profits: TimeDecayedStats::new(200, 0.98), // Increased from 50
            win_streak: 0,
            loss_streak: 0,
            pull_count: 0,
        }
    }

    fn update(&mut self, won: bool, profit: f32) {
        if won {
            self.alpha += 1.0;
            self.win_streak += 1;
            self.loss_streak = 0;
        } else {
            self.beta += 1.0;
            self.loss_streak += 1;
            self.win_streak = 0;
        }
        self.total_profit += profit;
        self.recent_profits.push(profit);
        self.pull_count += 1;
    }

    fn win_rate(&self) -> f32 {
        self.alpha / (self.alpha + self.beta)
    }

    fn sample(&self, rng_val: f32) -> f32 {
        // Beta distribution approximation using pert
        let a = self.alpha.max(1.0);
        let b = self.beta.max(1.0);
        let mean = a / (a + b);
        let std = (a * b / ((a + b).powi(2) * (a + b + 1.0))).sqrt();
        // Clamp to valid probability
        (mean + std * (rng_val - 0.5) * 2.0).clamp(0.001, 0.999)
    }

    fn entropy(&self) -> f32 {
        let p = self.win_rate();
        let q = 1.0 - p;
        if p > 0.0 && q > 0.0 {
            -(p * p.log2() + q * q.log2())
        } else {
            0.0
        }
    }

    fn confidence(&self) -> f32 {
        1.0 - (self.alpha + self.beta).recip().min(1.0)
    }
}

// ============================================================================
// META-STRATEGY ENSEMBLE
// ============================================================================

#[derive(Debug, Clone, Copy, PartialEq)]
enum MetaStrategy {
    Conservative,
    Aggressive,
    Adaptive,
    Recovery,
    Accumulation,
}

#[derive(Debug, Clone)]
struct Ensemble {
    weights: [f32; 5],
    performances: [f32; 5],
    last: MetaStrategy,
}

impl Ensemble {
    fn new() -> Self {
        Self {
            weights: [1.0; 5],
            performances: [0.0; 5],
            last: MetaStrategy::Adaptive,
        }
    }

    fn update(&mut self, strategy: MetaStrategy, profit: f32) {
        let idx = strategy as usize;
        self.performances[idx] = self.performances[idx] * 0.9 + profit * 0.1;
        let max_p = self
            .performances
            .iter()
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        let exp_sum: f32 = self
            .performances
            .par_iter()
            .map(|p| (p - max_p).exp())
            .sum();
        for (i, w) in self.weights.iter_mut().enumerate() {
            *w = (self.performances[i] - max_p).exp() / exp_sum;
        }
        self.last = strategy;
    }

    fn select(
        &mut self,
        drawdown: f32,
        win_streak: u32,
        volatility: f32,
        profit_ratio: f32,
        rng: f32,
    ) -> MetaStrategy {
        let strategy = if drawdown > 0.25 {
            MetaStrategy::Recovery
        } else if win_streak >= 5 {
            MetaStrategy::Accumulation
        } else if volatility > 0.5 {
            MetaStrategy::Conservative
        } else if profit_ratio > 0.2 {
            MetaStrategy::Aggressive
        } else {
            let strategies = [
                MetaStrategy::Conservative,
                MetaStrategy::Aggressive,
                MetaStrategy::Adaptive,
                MetaStrategy::Recovery,
                MetaStrategy::Accumulation,
            ];
            let mut cumsum = 0.0;
            for (i, &s) in strategies.iter().enumerate() {
                cumsum += self.weights[i];
                if rng < cumsum {
                    return s;
                }
            }
            MetaStrategy::Adaptive
        };
        self.last = strategy;
        strategy
    }
}

// ============================================================================
// ADVANCED PATTERN MEMORY
// ============================================================================

#[derive(Debug, Clone)]
struct PatternMemory {
    sequences: VecDeque<(Vec<bool>, bool, f32)>,
    detected_regime: u8,
}

impl PatternMemory {
    fn new() -> Self {
        Self {
            sequences: VecDeque::with_capacity(500), // Reduced from 10000
            detected_regime: 0,
        }
    }

    fn record(&mut self, seq: &[bool], outcome: bool, mult: f32) {
        let s: Vec<bool> = seq.iter().rev().take(8).copied().collect();
        self.sequences.push_back((s, outcome, mult));
        if self.sequences.len() > 500 {
            // Reduced from 10000
            self.sequences.pop_front();
        }
    }

    fn find_similar(&self, current: &[bool], lookback: usize) -> (u32, u32, f32) {
        let cur: Vec<bool> = current.iter().rev().take(lookback).copied().collect();
        let mut wins = 0u32;
        let mut losses = 0u32;
        let mut profit = 0.0f32;
        for (s, o, m) in &self.sequences {
            if s.len() >= lookback {
                let s_rev: Vec<bool> = s.iter().take(lookback).copied().collect();
                if s_rev == cur {
                    if *o {
                        wins += 1;
                    } else {
                        losses += 1;
                    }
                    profit += if *o { *m - 1.0 } else { -1.0 };
                }
            }
        }
        (wins, losses, profit)
    }

    fn detect_regime(&mut self) -> u8 {
        if self.sequences.len() < 20 {
            return 0;
        }
        let recent: Vec<_> = self.sequences.iter().rev().take(30).collect();
        let wins = recent.par_iter().filter(|(_, o, _)| *o).count();
        let win_rate = wins as f32 / recent.len() as f32;
        self.detected_regime = if win_rate > 0.65 {
            1
        } else if win_rate < 0.35 {
            2
        } else {
            0
        };
        self.detected_regime
    }

    fn clear(&mut self) {
        self.sequences.clear();
        self.detected_regime = 0;
    }
}

// ============================================================================
// CHANGE POINT DETECTOR (CUSUM)
// ============================================================================

#[derive(Debug, Clone)]
struct ChangeDetector {
    cusum_pos: f32,
    cusum_neg: f32,
    threshold: f32,
    ref_mean: f32,
    obs: VecDeque<f32>,
    changed: bool,
}

impl ChangeDetector {
    fn new(threshold: f32) -> Self {
        Self {
            cusum_pos: 0.0,
            cusum_neg: 0.0,
            threshold,
            ref_mean: 0.5,
            obs: VecDeque::with_capacity(100),
            changed: false,
        }
    }

    fn update(&mut self, val: f32) -> bool {
        self.obs.push_back(val);
        if self.obs.len() >= 10 && self.obs.len() % 10 == 0 {
            self.ref_mean = self.obs.par_iter().sum::<f32>() / self.obs.len() as f32;
        }
        let dev = val - self.ref_mean;
        self.cusum_pos = (self.cusum_pos + dev).max(0.0);
        self.cusum_neg = (self.cusum_neg - dev).max(0.0);
        if self.cusum_pos > self.threshold || self.cusum_neg > self.threshold {
            self.cusum_pos = 0.0;
            self.cusum_neg = 0.0;
            self.ref_mean = val;
            self.changed = true;
            return true;
        }
        self.changed = false;
        false
    }

    fn reset(&mut self) {
        self.cusum_pos = 0.0;
        self.cusum_neg = 0.0;
        self.obs.clear();
        self.changed = false;
    }
}

// ============================================================================
// ADVANCED RISK MANAGEMENT
// ============================================================================

#[derive(Debug, Clone)]
struct RiskState {
    peak: f32,
    drawdown: f32,
    max_dd: f32,
    returns: TimeDecayedStats,
    volatility: f32,
    risk_score: f32,
}

impl RiskState {
    fn new() -> Self {
        Self {
            peak: 0.0,
            drawdown: 0.0,
            max_dd: 0.0,
            returns: TimeDecayedStats::new(1000, 0.995), // Increased from 200
            volatility: 0.0,
            risk_score: 50.0,
        }
    }

    fn update(&mut self, bank: f32, profit: f32) {
        if bank > self.peak {
            self.peak = bank;
        }
        self.drawdown = (self.peak - bank) / self.peak.max(1e-8);
        self.max_dd = self.max_dd.max(self.drawdown);
        let ret = if self.peak > 0.0 {
            profit / self.peak
        } else {
            0.0
        };
        self.returns.push(ret);
        if self.returns.values.len() >= 20 {
            self.volatility = self.returns.weighted_var().sqrt();
        }
        // Risk score: 100 = safe, 0 = dangerous
        self.risk_score =
            (100.0 - self.drawdown * 150.0 - self.volatility * 50.0).clamp(0.0, 100.0);
    }

    fn position_mult(&self) -> f32 {
        if self.risk_score > 70.0 {
            1.3
        } else if self.risk_score > 50.0 {
            1.1
        } else if self.risk_score > 30.0 {
            0.8
        } else {
            0.5
        }
    }

    fn should_reduce(&self) -> bool {
        self.risk_score < 30.0 || self.drawdown > 0.2
    }
}

// ============================================================================
// FEATURE 1: CURIOSITY-DRIVEN EXPLORATION
// ============================================================================

/// Tracks novelty of different multiplier ranges and provides intrinsic rewards
#[derive(Debug, Clone)]
struct CuriosityEngine {
    /// How recently each arm was tried (decay over time)
    arm_recency: Vec<f32>,
    /// Prediction error history for each arm
    prediction_errors: Vec<VecDeque<f32>>,
    /// Intrinsic reward bonus (curiosity)
    intrinsic_rewards: Vec<f32>,
    /// Entropy of recent arm selections
    selection_entropy: f32,
    /// Recent arm selection counts
    arm_selection_counts: Vec<u32>,
    /// Total selections for entropy calculation
    total_selections: u32,
}

impl CuriosityEngine {
    fn new(num_arms: usize) -> Self {
        Self {
            arm_recency: vec![0.0; num_arms],
            prediction_errors: vec![VecDeque::with_capacity(20); num_arms],
            intrinsic_rewards: vec![0.0; num_arms],
            selection_entropy: 1.0,
            arm_selection_counts: vec![0; num_arms],
            total_selections: 0,
        }
    }

    /// Record that an arm was selected
    fn record_selection(&mut self, arm_idx: usize) {
        // Increase recency for selected arm
        if arm_idx < self.arm_recency.len() {
            self.arm_recency[arm_idx] = 1.0;
            self.arm_selection_counts[arm_idx] += 1;
            self.total_selections += 1;
        }
        // Decay all recencies
        for r in &mut self.arm_recency {
            *r *= 0.95;
        }
        // Update entropy
        self.update_entropy();
    }

    /// Record prediction error for an arm
    fn record_prediction_error(&mut self, arm_idx: usize, predicted_prob: f32, won: bool) {
        if arm_idx >= self.prediction_errors.len() {
            return;
        }
        let actual = if won { 1.0 } else { 0.0 };
        let error = (predicted_prob - actual).abs();

        self.prediction_errors[arm_idx].push_back(error);
        if self.prediction_errors[arm_idx].len() > 20 {
            self.prediction_errors[arm_idx].pop_front();
        }

        // Intrinsic reward: high prediction error = interesting, explore more!
        let avg_error: f32 = self.prediction_errors[arm_idx].iter().sum::<f32>()
            / self.prediction_errors[arm_idx].len().max(1) as f32;
        self.intrinsic_rewards[arm_idx] = avg_error * 2.0; // Scale up
    }

    /// Update selection entropy
    fn update_entropy(&mut self) {
        if self.total_selections == 0 {
            self.selection_entropy = 1.0;
            return;
        }
        let mut entropy = 0.0;
        for &count in &self.arm_selection_counts {
            if count > 0 {
                let p = count as f32 / self.total_selections as f32;
                entropy -= p * p.ln();
            }
        }
        // Normalize to 0-1
        self.selection_entropy = (entropy / self.arm_selection_counts.len() as f32).min(1.0);
    }

    /// Get novelty bonus for an arm
    fn get_novelty_bonus(&self, arm_idx: usize) -> f32 {
        if arm_idx >= self.arm_recency.len() {
            return 0.0;
        }
        // Arms not tried recently are more novel
        let recency = self.arm_recency[arm_idx];
        let novelty = 1.0 - recency;

        // Combine with intrinsic reward
        let intrinsic = self.intrinsic_rewards.get(arm_idx).copied().unwrap_or(0.0);

        novelty * 0.5 + intrinsic * 0.5
    }

    /// Get exploration probability boost based on entropy
    fn get_entropy_boost(&self) -> f32 {
        // Low entropy = we've been picking same things, need more exploration
        1.0 - self.selection_entropy
    }
}

// ============================================================================
// FEATURE 2: PROFIT-WEIGHTED LEARNING
// ============================================================================

/// Adjusts learning based on profit magnitude
#[derive(Debug, Clone)]
struct ProfitWeightedLearner {
    /// Profit history for Sharpe calculation
    profit_history: VecDeque<f32>,
    /// Cumulative profit
    cumulative_profit: f32,
    /// Running mean and variance for Sharpe
    profit_mean: f32,
    profit_variance: f32,
    profit_count: f32,
    /// Max profit seen (for normalization)
    max_profit: f32,
    /// Max loss seen (for normalization)
    max_loss: f32,
}

impl ProfitWeightedLearner {
    fn new() -> Self {
        Self {
            profit_history: VecDeque::with_capacity(100),
            cumulative_profit: 0.0,
            profit_mean: 0.0,
            profit_variance: 0.0,
            profit_count: 0.0,
            max_profit: 1.0,
            max_loss: 1.0,
        }
    }

    /// Record a profit and get the weighted reward
    fn record_profit(&mut self, profit: f32) -> f32 {
        // Update history
        self.profit_history.push_back(profit);
        if self.profit_history.len() > 100 {
            self.profit_history.pop_front();
        }

        // Update cumulative
        self.cumulative_profit += profit;

        // Track max profit/loss for normalization
        if profit > self.max_profit {
            self.max_profit = profit;
        }
        if profit < -self.max_loss {
            self.max_loss = -profit;
        }

        // Update running mean/variance (Welford's algorithm)
        self.profit_count += 1.0;
        let delta = profit - self.profit_mean;
        self.profit_mean += delta / self.profit_count;
        let delta2 = profit - self.profit_mean;
        self.profit_variance += delta * delta2;

        // Calculate weighted reward
        // Big wins = more positive, big losses = more negative
        let normalized = if profit >= 0.0 {
            profit / self.max_profit.max(1e-8)
        } else {
            profit / self.max_loss.max(1e-8)
        };

        // Apply sigmoid-like scaling
        let scaled = normalized.signum() * (1.0 - (-normalized.abs() * 2.0).exp());

        scaled
    }

    /// Calculate Sharpe ratio
    fn calculate_sharpe(&self) -> f32 {
        if self.profit_count < 2.0 {
            return 0.0;
        }
        let variance = self.profit_variance / (self.profit_count - 1.0);
        let std = variance.sqrt();
        if std < 1e-8 {
            return 0.0;
        }
        self.profit_mean / std
    }

    /// Get reward multiplier based on recent performance
    fn get_performance_multiplier(&self) -> f32 {
        let sharpe = self.calculate_sharpe();
        // Positive Sharpe = doing well, can be more aggressive
        // Negative Sharpe = doing poorly, need to learn faster
        if sharpe > 1.0 {
            1.2 // Doing great, slight boost
        } else if sharpe > 0.0 {
            1.0 // Normal
        } else if sharpe > -1.0 {
            1.1 // Learning opportunity
        } else {
            1.3 // Bad performance, learn aggressively
        }
    }
}

// ============================================================================
// FEATURE 3: ANTI-PERSISTENCE DETECTION
// ============================================================================

/// Detects patterns like alternation, streaks, and pattern breaking
#[derive(Debug, Clone)]
struct AntiPersistenceDetector {
    /// Recent outcomes (true = win, false = loss)
    outcome_history: VecDeque<bool>,
    /// Alternation score (-1 to 1, negative = alternating, positive = clustering)
    alternation_score: f32,
    /// Current streak type and length
    current_streak_type: Option<bool>,
    current_streak_len: u32,
    /// Streak history
    streak_history: VecDeque<u32>,
    /// Pattern break detection
    last_pattern_type: PatternType,
    pattern_break_count: u32,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum PatternType {
    Alternating,
    Clustering,
    Random,
    Unknown,
}

impl AntiPersistenceDetector {
    fn new() -> Self {
        Self {
            outcome_history: VecDeque::with_capacity(50),
            alternation_score: 0.0,
            current_streak_type: None,
            current_streak_len: 0,
            streak_history: VecDeque::with_capacity(20),
            last_pattern_type: PatternType::Unknown,
            pattern_break_count: 0,
        }
    }

    /// Record an outcome and update detection
    fn record_outcome(&mut self, won: bool) {
        let last = self.outcome_history.back().copied();

        // Update alternation score
        if let Some(last_won) = last {
            if won != last_won {
                // Alternation
                self.alternation_score -= 0.1;
            } else {
                // Clustering
                self.alternation_score += 0.1;
            }
            self.alternation_score = self.alternation_score.clamp(-1.0, 1.0);
        }

        // Update streak tracking
        if Some(won) == self.current_streak_type {
            self.current_streak_len += 1;
        } else {
            if self.current_streak_len > 1 {
                self.streak_history.push_back(self.current_streak_len);
                if self.streak_history.len() > 20 {
                    self.streak_history.pop_front();
                }
            }
            self.current_streak_type = Some(won);
            self.current_streak_len = 1;
        }

        // Detect pattern type
        let new_pattern = self.detect_current_pattern();
        if new_pattern != self.last_pattern_type && self.last_pattern_type != PatternType::Unknown {
            self.pattern_break_count += 1;
        }
        self.last_pattern_type = new_pattern;

        // Store outcome
        self.outcome_history.push_back(won);
        if self.outcome_history.len() > 50 {
            self.outcome_history.pop_front();
        }
    }

    /// Detect current pattern type
    fn detect_current_pattern(&self) -> PatternType {
        if self.alternation_score < -0.5 {
            PatternType::Alternating
        } else if self.alternation_score > 0.5 {
            PatternType::Clustering
        } else if self.outcome_history.len() < 10 {
            PatternType::Unknown
        } else {
            PatternType::Random
        }
    }

    /// Get prediction adjustment based on detected patterns
    fn get_prediction_adjustment(&self) -> (f32, f32) {
        // Returns (high_adjustment, low_adjustment)
        match self.last_pattern_type {
            PatternType::Alternating => {
                // Expect opposite of last
                if self.outcome_history.back() == Some(&true) {
                    (0.4, 0.6) // Expect loss, bet low
                } else {
                    (0.6, 0.4) // Expect win, bet high
                }
            }
            PatternType::Clustering => {
                // Expect same as last
                if self.outcome_history.back() == Some(&true) {
                    (0.6, 0.4) // Expect another win
                } else {
                    (0.4, 0.6) // Expect another loss
                }
            }
            PatternType::Random | PatternType::Unknown => {
                (0.5, 0.5) // No adjustment
            }
        }
    }

    /// Get streak exploitation signal
    fn get_streak_signal(&self) -> f32 {
        // Returns signal to ride or fight the streak
        if self.current_streak_len >= 5 {
            if self.current_streak_type == Some(true) {
                0.3 // Hot streak, ride it
            } else {
                -0.3 // Cold streak, should break soon
            }
        } else {
            0.0
        }
    }
}

// ============================================================================
// FEATURE 4: MULTI-STEP LOOKAHEAD PLANNING
// ============================================================================

/// Plans multiple bets ahead using tree search
#[derive(Debug, Clone)]
struct LookaheadPlanner {
    /// Planning horizon (number of bets to look ahead)
    horizon: usize,
    /// Number of simulations per planning step
    num_simulations: usize,
    /// Cached best future actions
    planned_actions: VecDeque<usize>,
    /// Expected bankroll trajectory
    expected_trajectory: VecDeque<f32>,
    /// Risk-adjusted value estimates
    value_estimates: Vec<f32>,
}

impl LookaheadPlanner {
    fn new() -> Self {
        Self {
            horizon: 5,
            num_simulations: 100,
            planned_actions: VecDeque::with_capacity(5),
            expected_trajectory: VecDeque::with_capacity(5),
            value_estimates: vec![0.0; 40], // One per arm
        }
    }

    /// Plan ahead and get recommended action
    fn plan(&mut self, current_bank: f32, win_rates: &[f32], multipliers: &[f32]) -> usize {
        // Simple Monte Carlo lookahead
        let num_arms = win_rates
            .len()
            .min(multipliers.len())
            .min(self.value_estimates.len());

        for arm in 0..num_arms {
            let win_rate = win_rates[arm];
            let multiplier = multipliers[arm];

            // Simulate expected value over horizon
            let mut expected_value = 0.0;
            for _ in 0..self.num_simulations {
                let mut bank = current_bank;
                for step in 0..self.horizon {
                    let bet = bank * 0.1; // Assume 10% bet
                    let win_prob = (100.0 - 5.0) / multiplier / 100.0; // Approximate win prob

                    // Simulate
                    if rand::rng().random::<f32>() < win_prob {
                        bank += bet * (multiplier - 1.0);
                    } else {
                        bank -= bet;
                    }

                    // Decay future value
                    expected_value += (bank - current_bank) * 0.9_f32.powi(step as i32);
                }
            }
            self.value_estimates[arm] = expected_value / self.num_simulations as f32;
        }

        // Find best action
        self.value_estimates
            .iter()
            .enumerate()
            .take(num_arms)
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(0)
    }

    /// Get value estimate for an arm
    fn get_value_estimate(&self, arm_idx: usize) -> f32 {
        self.value_estimates.get(arm_idx).copied().unwrap_or(0.0)
    }

    /// Get expected trajectory
    fn get_expected_return(&self) -> f32 {
        self.expected_trajectory.iter().sum()
    }
}

// ============================================================================
// FEATURE 5: ENSEMBLE PRUNING & WEIGHTING
// ============================================================================

/// Dynamically prunes and weights ensemble components
#[derive(Debug, Clone)]
struct EnsembleManager {
    /// Component performance tracking
    component_scores: Vec<f32>,
    /// Component active status
    component_active: Vec<bool>,
    /// Hierarchical weights (meta-voter confidence)
    meta_weights: Vec<f32>,
    /// Regime-specific weights
    regime_weights: Vec<Vec<f32>>,
    /// Minimum bets before pruning consideration
    min_bets_for_pruning: usize,
    /// Pruning threshold (below this = disable)
    pruning_threshold: f32,
}

impl EnsembleManager {
    fn new(num_components: usize) -> Self {
        Self {
            component_scores: vec![0.5; num_components],
            component_active: vec![true; num_components],
            meta_weights: vec![1.0; num_components],
            regime_weights: vec![vec![1.0; num_components]; 4], // 4 regimes
            min_bets_for_pruning: 500,
            pruning_threshold: 0.45, // Below 45% accuracy
        }
    }

    /// Update component score
    fn update_component(&mut self, component_idx: usize, was_correct: bool, total_bets: usize) {
        if component_idx >= self.component_scores.len() {
            return;
        }

        // Exponential moving average
        let alpha = 0.05;
        self.component_scores[component_idx] = alpha * if was_correct { 1.0 } else { 0.0 }
            + (1.0 - alpha) * self.component_scores[component_idx];

        // Check for pruning
        if total_bets > self.min_bets_for_pruning {
            if self.component_scores[component_idx] < self.pruning_threshold {
                self.component_active[component_idx] = false;
            }
        }
    }

    /// Get effective weight for a component
    fn get_effective_weight(&self, component_idx: usize, regime: usize) -> f32 {
        if component_idx >= self.component_scores.len() {
            return 0.0;
        }

        if !self.component_active[component_idx] {
            return 0.0;
        }

        let base = self.meta_weights.get(component_idx).copied().unwrap_or(1.0);
        let regime_factor = self
            .regime_weights
            .get(regime % 4)
            .and_then(|w| w.get(component_idx))
            .copied()
            .unwrap_or(1.0);
        let performance = self.component_scores[component_idx];

        base * regime_factor * performance
    }

    /// Update meta weights based on recent performance
    fn update_meta_weights(&mut self) {
        for (i, score) in self.component_scores.iter().enumerate() {
            // Boost good performers, reduce bad ones
            if *score > 0.55 {
                self.meta_weights[i] = (self.meta_weights[i] * 1.01).min(2.0);
            } else if *score < 0.45 {
                self.meta_weights[i] = (self.meta_weights[i] * 0.99).max(0.1);
            }
        }
    }

    /// Get number of active components
    fn active_count(&self) -> usize {
        self.component_active.iter().filter(|&&a| a).count()
    }
}

// ============================================================================
// FEATURE 6: SESSION MEMORY & TRANSFER LEARNING
// ============================================================================

/// Stores and retrieves knowledge across sessions
#[derive(Debug, Clone)]
struct SessionMemory {
    /// Best strategies from previous sessions
    strategy_memory: VecDeque<StrategyRecord>,
    /// Casino behavior model
    casino_model: CasinoBehaviorModel,
    /// Time-of-session effects
    time_effects: TimeEffects,
    /// Cross-session pattern library
    pattern_library: VecDeque<CrossSessionPattern>,
    /// Total sessions played
    total_sessions: u32,
}

#[derive(Debug, Clone)]
struct StrategyRecord {
    avg_multiplier: f32,
    win_rate: f32,
    profit_factor: f32,
    total_bets: usize,
    final_profit: f32,
}

#[derive(Debug, Clone)]
struct CasinoBehaviorModel {
    /// Modeled alternation tendency
    alternation_bias: f32,
    /// Modeled streak behavior
    streak_tendency: f32,
    /// Confidence in model
    model_confidence: f32,
}

#[derive(Debug, Clone)]
struct TimeEffects {
    /// Early session performance multiplier
    early_multiplier: f32,
    /// Mid session performance multiplier
    mid_multiplier: f32,
    /// Late session performance multiplier
    late_multiplier: f32,
}

#[derive(Debug, Clone)]
struct CrossSessionPattern {
    pattern_type: String,
    success_rate: f32,
    occurrences: u32,
    recommended_action: f32,
}

impl SessionMemory {
    fn new() -> Self {
        Self {
            strategy_memory: VecDeque::with_capacity(10),
            casino_model: CasinoBehaviorModel {
                alternation_bias: 0.0,
                streak_tendency: 0.0,
                model_confidence: 0.0,
            },
            time_effects: TimeEffects {
                early_multiplier: 1.0,
                mid_multiplier: 1.0,
                late_multiplier: 1.0,
            },
            pattern_library: VecDeque::with_capacity(100),
            total_sessions: 0,
        }
    }

    /// Record end of session
    fn record_session_end(&mut self, record: StrategyRecord) {
        self.strategy_memory.push_back(record);
        if self.strategy_memory.len() > 10 {
            self.strategy_memory.pop_front();
        }
        self.total_sessions += 1;

        // Update time effects based on history
        self.update_time_effects();
    }

    /// Update time effects from history
    fn update_time_effects(&mut self) {
        // Analyze patterns to update time effects
        // This is a simplified version
        if self.total_sessions > 3 {
            // Adjust based on historical performance
            let avg_profit: f32 = self
                .strategy_memory
                .iter()
                .map(|r| r.final_profit)
                .sum::<f32>()
                / self.strategy_memory.len().max(1) as f32;

            if avg_profit > 0.0 {
                self.time_effects.mid_multiplier = 1.1;
            } else {
                self.time_effects.early_multiplier = 0.9;
            }
        }
    }

    /// Get time-adjusted bet multiplier
    fn get_time_adjusted_multiplier(&self, bets_into_session: usize) -> f32 {
        if bets_into_session < 50 {
            self.time_effects.early_multiplier
        } else if bets_into_session < 200 {
            self.time_effects.mid_multiplier
        } else {
            self.time_effects.late_multiplier
        }
    }

    /// Update casino model
    fn update_casino_model(&mut self, alternation_observed: f32, streak_observed: f32) {
        let alpha = 0.1;
        self.casino_model.alternation_bias =
            alpha * alternation_observed + (1.0 - alpha) * self.casino_model.alternation_bias;
        self.casino_model.streak_tendency =
            alpha * streak_observed + (1.0 - alpha) * self.casino_model.streak_tendency;
        self.casino_model.model_confidence = (self.casino_model.model_confidence + 0.01).min(1.0);
    }

    /// Get casino behavior prediction
    fn get_casino_prediction(&self) -> (f32, f32) {
        // Returns (alternation_signal, streak_signal)
        if self.casino_model.model_confidence > 0.3 {
            (
                self.casino_model.alternation_bias,
                self.casino_model.streak_tendency,
            )
        } else {
            (0.0, 0.0)
        }
    }
}

// ============================================================================
// FEATURE 7: CALIBRATED CONFIDENCE
// ============================================================================

/// Calibrates model confidence to match actual accuracy
/// Advanced version with temperature scaling and disagreement calculation
#[derive(Debug, Clone)]
struct AdvancedConfidenceCalibrator {
    /// Bins for reliability diagram
    confidence_bins: Vec<AdvancedCalibrationBin>,
    /// Number of bins
    num_bins: usize,
    /// Temperature scaling parameter
    temperature: f32,
    /// Historical calibration error
    calibration_error: f32,
}

#[derive(Debug, Clone)]
struct AdvancedCalibrationBin {
    total: u32,
    correct: u32,
    avg_confidence: f32,
}

impl AdvancedConfidenceCalibrator {
    fn new(num_bins: usize) -> Self {
        Self {
            confidence_bins: vec![
                AdvancedCalibrationBin {
                    total: 0,
                    correct: 0,
                    avg_confidence: 0.0
                };
                num_bins
            ],
            num_bins,
            temperature: 1.0,
            calibration_error: 0.0,
        }
    }

    /// Record a prediction and its outcome
    fn record(&mut self, confidence: f32, was_correct: bool) {
        let bin_idx = ((confidence * self.num_bins as f32) as usize).min(self.num_bins - 1);

        let bin = &mut self.confidence_bins[bin_idx];
        bin.total += 1;
        if was_correct {
            bin.correct += 1;
        }
        // Update running average confidence
        bin.avg_confidence = bin.avg_confidence * 0.9 + confidence * 0.1;

        // Update calibration error
        self.update_calibration_error();
    }

    /// Update expected calibration error
    fn update_calibration_error(&mut self) {
        let mut total_error = 0.0;
        let mut total_count = 0;

        for bin in &self.confidence_bins {
            if bin.total > 0 {
                let accuracy = bin.correct as f32 / bin.total as f32;
                let error = (accuracy - bin.avg_confidence).abs();
                total_error += error * bin.total as f32;
                total_count += bin.total;
            }
        }

        if total_count > 0 {
            self.calibration_error = total_error / total_count as f32;
        }
    }

    /// Calibrate a confidence value
    fn calibrate(&self, confidence: f32) -> f32 {
        // Apply temperature scaling
        let logit = (confidence / (1.0 - confidence + 1e-8)).ln() / self.temperature;
        let calibrated = 1.0 / (1.0 + (-logit).exp());

        // Apply bin-based calibration if available
        let bin_idx = ((confidence * self.num_bins as f32) as usize).min(self.num_bins - 1);
        let bin = &self.confidence_bins[bin_idx];

        if bin.total > 10 {
            let empirical_accuracy = bin.correct as f32 / bin.total as f32;
            // Blend calibrated with empirical
            0.5 * calibrated + 0.5 * empirical_accuracy
        } else {
            calibrated
        }
    }

    /// Get ensemble disagreement (uncertainty signal)
    fn calculate_disagreement(&self, predictions: &[f32]) -> f32 {
        if predictions.is_empty() {
            return 0.0;
        }

        let mean: f32 = predictions.iter().sum::<f32>() / predictions.len() as f32;
        let variance: f32 =
            predictions.iter().map(|&p| (p - mean).powi(2)).sum::<f32>() / predictions.len() as f32;

        // High variance = high disagreement = high uncertainty
        (variance * 4.0).min(1.0)
    }

    /// Get calibration quality
    fn get_calibration_quality(&self) -> f32 {
        1.0 - self.calibration_error
    }
}

// ============================================================================
// MAIN STRATEGY
// ============================================================================
// MORE INSANE ADVANCED FEATURES - GOING ABSOLUTELY NUCLEAR
// ============================================================================

// FEATURE 8: Transformer Sequence Predictor with Multi-Head Attention
#[derive(Debug, Clone)]
struct TransformerSequencePredictor {
    // Multi-head attention for roll number patterns
    attention_heads: Vec<AttentionHead>,
    // Positional embeddings
    position_embeddings: Vec<f32>,
    // Learned patterns
    pattern_memory: VecDeque<Vec<f32>>,
    // Output projection
    output_weights: Vec<f32>,
}

#[derive(Debug, Clone)]
struct AttentionHead {
    query_weights: Vec<f32>,
    key_weights: Vec<f32>,
    value_weights: Vec<f32>,
    head_dim: usize,
}

impl TransformerSequencePredictor {
    fn new(seq_len: usize, d_model: usize, num_heads: usize) -> Self {
        let mut attention_heads = Vec::with_capacity(num_heads);
        for _ in 0..num_heads {
            attention_heads.push(AttentionHead {
                query_weights: (0..d_model)
                    .map(|_| (rand::rng().random::<f32>() - 0.5) * 0.1)
                    .collect(),
                key_weights: (0..d_model)
                    .map(|_| (rand::rng().random::<f32>() - 0.5) * 0.1)
                    .collect(),
                value_weights: (0..d_model)
                    .map(|_| (rand::rng().random::<f32>() - 0.5) * 0.1)
                    .collect(),
                head_dim: d_model / num_heads,
            });
        }

        Self {
            attention_heads,
            position_embeddings: (0..seq_len).map(|i| (i as f32 * 0.1).sin()).collect(),
            pattern_memory: VecDeque::with_capacity(50),
            output_weights: (0..d_model)
                .map(|_| (rand::rng().random::<f32>() - 0.5) * 0.1)
                .collect(),
        }
    }

    fn predict_next(&self, sequence: &[f32]) -> f32 {
        if sequence.is_empty() {
            return 0.5;
        }

        // Add positional embeddings
        let seq_len = sequence.len();
        let mut embedded = sequence.to_vec();
        for (i, emb) in embedded.iter_mut().enumerate() {
            if i < self.position_embeddings.len() {
                *emb += self.position_embeddings[i];
            }
        }

        // Multi-head attention
        let mut attention_output = vec![0.0; embedded.len()];
        for head in &self.attention_heads {
            let q: Vec<f32> = embedded
                .iter()
                .zip(head.query_weights.iter())
                .map(|(&e, &w)| e * w)
                .collect();
            let k: Vec<f32> = embedded
                .iter()
                .zip(head.key_weights.iter())
                .map(|(&e, &w)| e * w)
                .collect();
            let v: Vec<f32> = embedded
                .iter()
                .zip(head.value_weights.iter())
                .map(|(&e, &w)| e * w)
                .collect();

            // Compute attention weights
            for (i, &qi) in q.iter().enumerate() {
                let mut total_attn = 0.0;
                let mut weighted_sum = 0.0;
                for (j, &kj) in k.iter().enumerate() {
                    let attn = (qi * kj / head.head_dim as f32).exp();
                    total_attn += attn;
                    weighted_sum += attn * v[j];
                }
                if total_attn > 0.0 {
                    attention_output[i] += weighted_sum / total_attn;
                }
            }
        }

        // Output projection
        let output: f32 = attention_output
            .iter()
            .zip(self.output_weights.iter())
            .map(|(&a, &w)| a * w)
            .sum();

        (output.tanh() + 1.0) / 2.0 // Map to 0-1
    }

    fn update(&mut self, sequence: &[f32], outcome: f32, lr: f32) {
        // Store pattern for learning
        self.pattern_memory.push_back(sequence.to_vec());
        if self.pattern_memory.len() > 50 {
            self.pattern_memory.pop_front();
        }

        // Simple gradient descent on attention weights
        let error = outcome - 0.5;
        for head in &mut self.attention_heads {
            for w in &mut head.query_weights {
                *w += lr * error * 0.01;
            }
            for w in &mut head.key_weights {
                *w += lr * error * 0.01;
            }
        }
    }
}

// FEATURE 9: Episodic Memory for Important Betting Sequences
#[derive(Debug, Clone)]
struct EpisodicMemory {
    // Memorable episodes (high reward or surprising)
    episodes: VecDeque<Episode>,
    // Similarity threshold for retrieval
    retrieval_threshold: f32,
    // Maximum episodes stored
    max_episodes: usize,
}

#[derive(Debug, Clone)]
struct Episode {
    // Context before the episode
    context: Vec<f32>,
    // Actions taken
    actions: Vec<usize>,
    // Cumulative reward
    total_reward: f32,
    // Was this a winning or losing streak?
    episode_type: EpisodeType,
    // How surprising was this episode?
    surprise_score: f32,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum EpisodeType {
    WinningStreak,
    LosingStreak,
    Recovery,
    Turnaround,
}

impl EpisodicMemory {
    fn new(max_episodes: usize) -> Self {
        Self {
            episodes: VecDeque::with_capacity(max_episodes),
            retrieval_threshold: 0.7,
            max_episodes,
        }
    }

    fn store_episode(
        &mut self,
        context: Vec<f32>,
        actions: Vec<usize>,
        reward: f32,
        surprise: f32,
    ) {
        let episode_type = if reward > 0.1 {
            EpisodeType::WinningStreak
        } else if reward < -0.1 {
            EpisodeType::LosingStreak
        } else if surprise > 0.5 {
            EpisodeType::Turnaround
        } else {
            EpisodeType::Recovery
        };

        let episode = Episode {
            context,
            actions,
            total_reward: reward,
            episode_type,
            surprise_score: surprise,
        };

        self.episodes.push_back(episode);
        if self.episodes.len() > self.max_episodes {
            self.episodes.pop_front();
        }
    }

    fn retrieve_similar(&self, current_context: &[f32]) -> Option<&Episode> {
        // Find most similar past episode
        self.episodes.iter().max_by(|a, b| {
            let sim_a = self.cosine_similarity(&a.context, current_context);
            let sim_b = self.cosine_similarity(&b.context, current_context);
            sim_a
                .partial_cmp(&sim_b)
                .unwrap_or(std::cmp::Ordering::Equal)
        })
    }

    fn cosine_similarity(&self, a: &[f32], b: &[f32]) -> f32 {
        let min_len = a.len().min(b.len());
        let dot: f32 = a[..min_len]
            .iter()
            .zip(b[..min_len].iter())
            .map(|(x, y)| x * y)
            .sum();
        let norm_a: f32 = a[..min_len].iter().map(|x| x * x).sum::<f32>().sqrt();
        let norm_b: f32 = b[..min_len].iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm_a > 0.0 && norm_b > 0.0 {
            dot / (norm_a * norm_b)
        } else {
            0.0
        }
    }
}

// FEATURE 10: Counterfactual Regret Minimization (CFR)
#[derive(Debug, Clone)]
struct CounterfactualRegretMinimizer {
    // Regret for each action at each information set
    regrets: HashMap<Vec<bool>, Vec<f32>>,
    // Cumulative strategy
    strategy: HashMap<Vec<bool>, Vec<f32>>,
    // Iteration count
    iterations: u32,
}

impl CounterfactualRegretMinimizer {
    fn new() -> Self {
        Self {
            regrets: HashMap::new(),
            strategy: HashMap::new(),
            iterations: 0,
        }
    }

    fn get_strategy(&mut self, info_set: &[bool]) -> Vec<f32> {
        let regrets = self
            .regrets
            .entry(info_set.to_vec())
            .or_insert_with(|| vec![0.0; 40]);

        // Regret matching
        let sum: f32 = regrets.iter().map(|r| r.max(0.0)).sum();
        if sum > 0.0 {
            regrets.iter().map(|r| r.max(0.0) / sum).collect()
        } else {
            vec![1.0 / 40.0; 40] // Uniform
        }
    }

    fn update_regret(
        &mut self,
        info_set: &[bool],
        action: usize,
        payoff: f32,
        counterfactual_payoff: f32,
    ) {
        let regrets = self
            .regrets
            .entry(info_set.to_vec())
            .or_insert_with(|| vec![0.0; 40]);
        if action < regrets.len() {
            regrets[action] += counterfactual_payoff - payoff;
        }
        self.iterations += 1;
    }

    fn get_best_action(&self, info_set: &[bool]) -> usize {
        if let Some(regrets) = self.regrets.get(info_set) {
            regrets
                .iter()
                .enumerate()
                .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
                .map(|(i, _)| i)
                .unwrap_or(0)
        } else {
            0
        }
    }
}

// FEATURE 11: Bayesian Model Averaging with Uncertainty Quantification
#[derive(Debug, Clone)]
struct BayesianModelAverager {
    // Model weights (log marginal likelihood)
    model_log_weights: Vec<f32>,
    // Predictive variance per model
    model_variances: Vec<f32>,
    // Number of models
    num_models: usize,
    // Prior strength
    prior_strength: f32,
}

impl BayesianModelAverager {
    fn new(num_models: usize) -> Self {
        Self {
            model_log_weights: vec![0.0; num_models], // Equal prior
            model_variances: vec![0.1; num_models],
            num_models,
            prior_strength: 1.0,
        }
    }

    fn predict(&self, predictions: &[f32]) -> (f32, f32) {
        // Predictive mean and variance using Bayesian model averaging
        // P(y|x,D) = Σ P(y|x,M_i,D) * P(M_i|D)

        let log_weights: Vec<f32> = self
            .model_log_weights
            .iter()
            .map(|&w| {
                (w - self
                    .model_log_weights
                    .iter()
                    .cloned()
                    .fold(f32::NEG_INFINITY, f32::max))
            })
            .collect();
        let max_log = log_weights
            .iter()
            .cloned()
            .fold(f32::NEG_INFINITY, f32::max);
        let sum_exp: f32 = log_weights.iter().map(|&w| (w - max_log).exp()).sum();
        let weights: Vec<f32> = log_weights
            .iter()
            .map(|&w| (w - max_log).exp() / sum_exp)
            .collect();

        // Predictive mean
        let mean: f32 = predictions
            .iter()
            .zip(weights.iter())
            .map(|(&p, &w)| p * w)
            .sum();

        // Predictive variance = model variance + model uncertainty
        let model_var: f32 = predictions
            .iter()
            .zip(weights.iter())
            .map(|(&p, &w)| w * (p - mean).powi(2))
            .sum::<f32>()
            + self
                .model_variances
                .iter()
                .zip(weights.iter())
                .map(|(&v, &w)| w * v)
                .sum::<f32>();

        (mean, model_var.sqrt())
    }

    fn update_model_weight(&mut self, model_idx: usize, log_likelihood: f32) {
        if model_idx < self.num_models {
            // Bayesian update: posterior ∝ prior × likelihood
            self.model_log_weights[model_idx] += log_likelihood - self.prior_strength.ln();
        }
    }
}

// FEATURE 12: Anomaly Detection (Pattern Change Detection)
#[derive(Debug, Clone)]
struct AnomalyDetector {
    // Baseline statistics
    baseline_mean: f32,
    baseline_std: f32,
    // Rolling window for detection
    window: VecDeque<f32>,
    window_size: usize,
    // Anomaly threshold (number of std deviations)
    threshold: f32,
    // Detected anomalies
    anomalies: VecDeque<usize>,
    // Change point detector
    change_points: Vec<usize>,
}

impl AnomalyDetector {
    fn new(window_size: usize, threshold: f32) -> Self {
        Self {
            baseline_mean: 0.5,
            baseline_std: 0.1,
            window: VecDeque::with_capacity(window_size),
            window_size,
            threshold,
            anomalies: VecDeque::with_capacity(100),
            change_points: Vec::new(),
        }
    }

    fn detect(&mut self, value: f32, bet_number: usize) -> AnomalyResult {
        self.window.push_back(value);
        if self.window.len() > self.window_size {
            self.window.pop_front();
        }

        // Check for anomaly
        let z_score = (value - self.baseline_mean) / self.baseline_std.max(1e-8);
        let is_anomaly = z_score.abs() > self.threshold;

        if is_anomaly {
            self.anomalies.push_back(bet_number);
        }

        // Check for change point using CUSUM
        let cusum = self.compute_cusum();
        if cusum > 5.0 {
            self.change_points.push(bet_number);
            // Reset baseline after change point
            self.update_baseline();
        }

        AnomalyResult {
            is_anomaly,
            z_score,
            cusum,
            trend: if cusum > 2.0 {
                TrendType::Increasing
            } else if cusum < -2.0 {
                TrendType::Decreasing
            } else {
                TrendType::Stable
            },
        }
    }

    fn compute_cusum(&self) -> f32 {
        // Cumulative Sum control chart
        let mean: f32 = self.window.iter().sum::<f32>() / self.window.len().max(1) as f32;
        let cusum: f32 = self
            .window
            .iter()
            .map(|&x| (x - mean).signum() * (x - mean).abs())
            .sum();
        cusum
    }

    fn update_baseline(&mut self) {
        if self.window.len() < 10 {
            return;
        }
        let n = self.window.len() as f32;
        self.baseline_mean = self.window.iter().sum::<f32>() / n;
        self.baseline_std = (self
            .window
            .iter()
            .map(|&x| (x - self.baseline_mean).powi(2))
            .sum::<f32>()
            / n)
            .sqrt()
            .max(0.01);
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum TrendType {
    Increasing,
    Decreasing,
    Stable,
}

#[derive(Debug, Clone)]
struct AnomalyResult {
    is_anomaly: bool,
    z_score: f32,
    cusum: f32,
    trend: TrendType,
}

// FEATURE 13: Risk-Aware RL with CVaR (Conditional Value at Risk)
#[derive(Debug, Clone)]
struct RiskAwareRL {
    // CVaR alpha (quantile level)
    alpha: f32,
    // Historical returns for CVaR calculation
    return_history: VecDeque<f32>,
    // Risk penalty coefficients
    risk_penalty: f32,
    // Risk budget
    risk_budget: f32,
}

impl RiskAwareRL {
    fn new(alpha: f32) -> Self {
        Self {
            alpha,
            return_history: VecDeque::with_capacity(100),
            risk_penalty: 1.0,
            risk_budget: 0.2, // Max 20% CVaR
        }
    }

    fn compute_var(&self) -> f32 {
        // Value at Risk: the alpha-quantile of the loss distribution
        if self.return_history.len() < 10 {
            return 0.0;
        }

        let mut sorted: Vec<f32> = self.return_history.iter().cloned().collect();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

        let var_idx = ((1.0 - self.alpha) * sorted.len() as f32) as usize;
        sorted.get(var_idx).copied().unwrap_or(0.0)
    }

    fn compute_cvar(&self) -> f32 {
        // Conditional Value at Risk: Expected Shortfall
        // CVaR = E[L | L > VaR]
        if self.return_history.len() < 10 {
            return 0.0;
        }

        let var = self.compute_var();
        let mut tail_returns: Vec<f32> = self
            .return_history
            .iter()
            .filter(|&&r| r < var) // In the loss tail
            .cloned()
            .collect();

        if tail_returns.is_empty() {
            return var;
        }

        tail_returns.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        tail_returns.iter().sum::<f32>() / tail_returns.len() as f32
    }

    fn record_return(&mut self, ret: f32) {
        self.return_history.push_back(ret);
        if self.return_history.len() > 100 {
            self.return_history.pop_front();
        }
    }

    fn adjust_for_risk(&self, expected_value: f32, variance: f32) -> f32 {
        let cvar = self.compute_cvar();
        let var = self.compute_var();

        // Risk-adjusted value = EV - risk_penalty * (CVaR - VaR)
        // This penalizes actions with heavy tails
        let tail_risk = (cvar - var).abs();
        expected_value - self.risk_penalty * (variance.sqrt() + tail_risk)
    }

    fn is_within_risk_budget(&self) -> bool {
        let cvar = self.compute_cvar().abs();
        cvar < self.risk_budget
    }
}

// FEATURE 14: Hierarchical RL (High-Level Goals, Low-Level Actions)
#[derive(Debug, Clone)]
struct HierarchicalRL {
    // High-level goals
    current_goal: HighLevelGoal,
    goal_history: VecDeque<HighLevelGoal>,
    // Goal selector Q-values
    goal_q_values: Vec<f32>,
    // Sub-policy for each goal
    sub_policies: Vec<Vec<f32>>,
    // Goal completion threshold
    goal_threshold: f32,
    // Steps in current goal
    goal_steps: u32,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum HighLevelGoal {
    PreserveCapital,    // Minimize losses
    AccumulateProfit,   // Maximize gains
    RecoverLosses,      // Get back to even
    RideWinStreak,      // Press advantage
    SurviveLossStreak,  // Minimize damage
    ExploreNewStrategy, // Try something different
}

impl HierarchicalRL {
    fn new() -> Self {
        let num_goals = 6;
        Self {
            current_goal: HighLevelGoal::PreserveCapital,
            goal_history: VecDeque::with_capacity(50),
            goal_q_values: vec![0.0; num_goals],
            sub_policies: vec![vec![0.5; 40]; num_goals],
            goal_threshold: 0.3,
            goal_steps: 0,
        }
    }

    fn select_goal(&mut self, drawdown: f32, win_streak: u32, loss_streak: u32) -> HighLevelGoal {
        // State-based goal selection with Q-value update
        let goal = if drawdown > 0.3 {
            HighLevelGoal::SurviveLossStreak
        } else if drawdown > 0.15 {
            HighLevelGoal::RecoverLosses
        } else if win_streak >= 5 {
            HighLevelGoal::RideWinStreak
        } else if win_streak >= 3 {
            HighLevelGoal::AccumulateProfit
        } else if loss_streak >= 5 {
            HighLevelGoal::SurviveLossStreak
        } else if self.goal_steps > 100 {
            HighLevelGoal::ExploreNewStrategy
        } else {
            HighLevelGoal::PreserveCapital
        };

        self.current_goal = goal;
        self.goal_history.push_back(goal);
        self.goal_steps = 0;
        goal
    }

    fn get_sub_policy(&self, goal: HighLevelGoal) -> &[f32] {
        match goal {
            HighLevelGoal::PreserveCapital => &self.sub_policies[0],
            HighLevelGoal::AccumulateProfit => &self.sub_policies[1],
            HighLevelGoal::RecoverLosses => &self.sub_policies[2],
            HighLevelGoal::RideWinStreak => &self.sub_policies[3],
            HighLevelGoal::SurviveLossStreak => &self.sub_policies[4],
            HighLevelGoal::ExploreNewStrategy => &self.sub_policies[5],
        }
    }

    fn update_goal(&mut self, reward: f32) {
        let goal_idx = match self.current_goal {
            HighLevelGoal::PreserveCapital => 0,
            HighLevelGoal::AccumulateProfit => 1,
            HighLevelGoal::RecoverLosses => 2,
            HighLevelGoal::RideWinStreak => 3,
            HighLevelGoal::SurviveLossStreak => 4,
            HighLevelGoal::ExploreNewStrategy => 5,
        };

        // Q-learning update for goal selection
        self.goal_q_values[goal_idx] += 0.1 * (reward - self.goal_q_values[goal_idx]);
        self.goal_steps += 1;
    }
}

// FEATURE 15: Model-Based RL (Learn Environment Dynamics)
#[derive(Debug, Clone)]
struct ModelBasedRL {
    // Transition model: (state, action) -> next_state probability
    transition_model: HashMap<(Vec<u8>, usize), Vec<(Vec<u8>, f32)>>,
    // Reward model: (state, action) -> expected reward
    reward_model: HashMap<(Vec<u8>, usize), f32>,
    // State visitation counts
    state_counts: HashMap<Vec<u8>, u32>,
    // Planning depth
    planning_depth: usize,
}

impl ModelBasedRL {
    fn new() -> Self {
        Self {
            transition_model: HashMap::new(),
            reward_model: HashMap::new(),
            state_counts: HashMap::new(),
            planning_depth: 3,
        }
    }

    fn observe(&mut self, state: Vec<u8>, action: usize, next_state: Vec<u8>, reward: f32) {
        // Update transition model
        let key = (state.clone(), action);
        let transitions = self.transition_model.entry(key).or_insert_with(Vec::new);

        // Find or add transition
        let mut found = false;
        for (ns, prob) in transitions.iter_mut() {
            if *ns == next_state {
                // Update probability estimate
                *prob = 0.9 * *prob + 0.1 * 1.0; // Moving average
                found = true;
                break;
            }
        }
        if !found {
            transitions.push((next_state.clone(), 1.0));
        }

        // Update reward model
        let reward_key = (state.clone(), action);
        let old_reward = self.reward_model.get(&reward_key).copied().unwrap_or(0.0);
        self.reward_model
            .insert(reward_key, 0.9 * old_reward + 0.1 * reward);

        // Update state counts
        *self.state_counts.entry(state).or_insert(0) += 1;
        *self.state_counts.entry(next_state).or_insert(0) += 1;
    }

    fn plan(&self, current_state: &[bool], actions: &[f32]) -> usize {
        // Model-based planning: find action with best expected value
        let state_bytes: Vec<u8> = current_state
            .iter()
            .map(|&b| if b { 1 } else { 0 })
            .collect();

        let mut best_action = 0;
        let mut best_value = f32::NEG_INFINITY;

        for (action_idx, &action_value) in actions.iter().enumerate() {
            let expected_value =
                self.simulate_rollout(&state_bytes, action_idx, self.planning_depth);
            if expected_value > best_value {
                best_value = expected_value;
                best_action = action_idx;
            }
        }

        best_action
    }

    fn simulate_rollout(&self, state: &[u8], action: usize, depth: usize) -> f32 {
        if depth == 0 {
            return 0.0;
        }

        let key = (state.to_vec(), action);

        // Get transition probabilities
        if let Some(transitions) = self.transition_model.get(&key) {
            let mut total_value = 0.0;
            let mut total_prob = 0.0;

            for (next_state, prob) in transitions {
                // Immediate reward
                let reward = self
                    .reward_model
                    .get(&(state.to_vec(), action))
                    .copied()
                    .unwrap_or(0.0);
                // Recursive value
                let future_value = self.simulate_rollout(next_state, 0, depth - 1);

                total_value += prob * (reward + 0.95 * future_value);
                total_prob += prob;
            }

            if total_prob > 0.0 {
                total_value / total_prob
            } else {
                0.0
            }
        } else {
            0.0
        }
    }
}

// FEATURE 16: Inverse RL (Learn from Winning Sessions)
#[derive(Debug, Clone)]
struct InverseRL {
    // Expert trajectories (winning sessions)
    expert_trajectories: VecDeque<Vec<f32>>,
    // Learned reward weights
    reward_weights: Vec<f32>,
    // Feature function for states
    feature_dim: usize,
}

impl InverseRL {
    fn new(feature_dim: usize) -> Self {
        Self {
            expert_trajectories: VecDeque::with_capacity(10),
            reward_weights: vec![0.0; feature_dim],
            feature_dim,
        }
    }

    fn store_expert_trajectory(&mut self, trajectory: Vec<f32>) {
        // Only store winning sessions
        self.expert_trajectories.push_back(trajectory);
        if self.expert_trajectories.len() > 10 {
            self.expert_trajectories.pop_front();
        }
        self.update_reward_weights();
    }

    fn update_reward_weights(&mut self) {
        // Learn reward function from expert demonstrations
        // Reward = w^T * features
        // Maximize likelihood of expert actions

        if self.expert_trajectories.is_empty() {
            return;
        }

        // Simple gradient update
        for trajectory in &self.expert_trajectories {
            for (i, &reward) in trajectory.iter().enumerate() {
                if i < self.reward_weights.len() {
                    self.reward_weights[i] += 0.01 * reward.signum();
                }
            }
        }

        // Normalize
        let norm: f32 = self
            .reward_weights
            .iter()
            .map(|w| w * w)
            .sum::<f32>()
            .sqrt()
            .max(1e-8);
        for w in &mut self.reward_weights {
            *w /= norm;
        }
    }

    fn get_reward(&self, features: &[f32]) -> f32 {
        features
            .iter()
            .zip(self.reward_weights.iter())
            .map(|(f, w)| f * w)
            .sum()
    }
}

// FEATURE 17: Theory of Mind (Model the Casino)
#[derive(Debug, Clone)]
struct TheoryOfMind {
    // Beliefs about casino's strategy
    casino_model: CasinoMentalModel,
    // Beliefs about casino's beliefs about us
    second_order_beliefs: Vec<f32>,
    // Counter-strategies
    counter_strategies: Vec<f32>,
    // Prediction accuracy
    prediction_accuracy: f32,
}

#[derive(Debug, Clone)]
struct CasinoMentalModel {
    // Estimated casino strategy parameters
    alternation_probability: f32,
    streak_tendency: f32,
    target_adjustment: f32,
    // Detected casino patterns
    detected_patterns: VecDeque<String>,
}

impl TheoryOfMind {
    fn new() -> Self {
        Self {
            casino_model: CasinoMentalModel {
                alternation_probability: 0.0,
                streak_tendency: 0.0,
                target_adjustment: 0.0,
                detected_patterns: VecDeque::with_capacity(20),
            },
            second_order_beliefs: vec![0.5; 10],
            counter_strategies: vec![0.5; 10],
            prediction_accuracy: 0.5,
        }
    }

    fn update_beliefs(&mut self, outcome: bool, predicted: bool, our_bet: bool) {
        // First-order: What is the casino doing?
        // Second-order: What does the casino think we're doing?

        let prediction_error = if outcome == predicted { 0.0 } else { 1.0 };

        // Update casino model
        if outcome != our_bet {
            // Casino might be opposing us
            self.casino_model.target_adjustment += 0.01;
        }

        // Update second-order beliefs (what casino thinks we'll do)
        if outcome {
            // We won, casino might adjust
            for belief in &mut self.second_order_beliefs {
                *belief = 0.9 * *belief + 0.1 * if our_bet { 1.0 } else { 0.0 };
            }
        }

        // Update prediction accuracy
        self.prediction_accuracy =
            0.95 * self.prediction_accuracy + 0.05 * if outcome == predicted { 1.0 } else { 0.0 };
    }

    fn predict_casino_action(&self) -> (f32, f32) {
        // Returns (probability_high, uncertainty)
        let p_high = if self.casino_model.alternation_probability > 0.3 {
            0.5 - self.casino_model.alternation_probability * 0.2
        } else {
            0.5 + self.casino_model.streak_tendency * 0.2
        };

        let uncertainty = 1.0 - self.prediction_accuracy;

        (p_high.clamp(0.3, 0.7), uncertainty)
    }

    fn get_counter_strategy(&self) -> f32 {
        // What should we do given our model of the casino?
        // If casino alternates, bet opposite of last
        // If casino streaks, bet with the streak
        self.casino_model.alternation_probability * 0.3
            + (1.0 - self.casino_model.streak_tendency) * 0.7
    }
}

// ============================================================================
// MAIN STRATEGY
// ============================================================================

#[derive(Debug)]
pub struct AiStrat {
    high: bool,
    min_bet: f32,
    current_bet: f32,
    bank: f32,
    initial_bank: f32,
    peak_bank: f32,
    profit: f32,
    chance: f32,
    multiplier: f32,
    house_percent: f32,
    total_bets: usize,
    last_prediction: f32,
    last_confidence: f32,
    loss_streak: u32,
    win_streak: u32,
    arms: Vec<BayesianArm>,
    ensemble: Ensemble,
    current_meta: MetaStrategy,
    patterns: PatternMemory,
    recent_seq: VecDeque<bool>,
    // Roll number tracking for high/low prediction
    recent_rolls: VecDeque<u32>, // Actual roll numbers (0-10000)
    high_wins: u32,              // Wins when betting high
    low_wins: u32,               // Wins when betting low
    high_bets: u32,              // Total bets on high
    low_bets: u32,               // Total bets on low
    high_win_streak: u32,        // Consecutive high wins
    low_win_streak: u32,         // Consecutive low wins
    risk: RiskState,
    change_det: ChangeDetector,
    prog_mult: f32,
    last_win: bool,
    cons_wins: u32,
    cons_losses: u32,
    max_bet_pct: f32,
    stop_loss: bool,
    hard_stop: f32,
    session_profit: f32,
    debt: f32,
    rng_state: u64,
    // Advanced features (existing)
    kelly: KellyOptimizer,
    regime: RegimeDetector,
    q_learner: QLearner,
    total_wins: u32,
    total_losses: u32,
    recent_returns: VecDeque<f32>,
    sharpe_ratio: f32,
    sortino_ratio: f32,
    max_consecutive_wins: u32,
    max_consecutive_losses: u32,
    session_high: f32,
    session_low: f32,
    volatility_adjusted_bet: bool,
    // New advanced features
    mcts: MCTSPredictor,
    volatility_forecaster: VolatilityForecaster,
    mean_reversion: MeanReversionDetector,
    trend_strength: TrendStrength,
    risk_parity: RiskParitySizer,
    adaptive_lr: AdaptiveLearningRate,
    markov: MarkovChain,
    bank_history: VecDeque<f32>,
    profit_history: VecDeque<f32>,
    expected_value: f32,
    confidence_interval: (f32, f32),
    // Even more advanced features
    ensemble_forecaster: EnsembleForecaster,
    kalman_filter: KalmanFilter,
    particle_filter: ParticleFilter,
    dqn_agent: DQNAgent,
    linucb: LinUCBDisjoint,
    // Ultra advanced features
    lstm_model: LSTMSequenceModel,
    self_attention: SelfAttention,
    gaussian_process: GaussianProcess,
    policy_gradient: PolicyGradientAgent,
    evolution_strategies: EvolutionStrategies,
    context_builder: ContextBuilder,
    // Experimental quantum-inspired
    hd_memory: HyperdimensionalMemory,
    reservoir: Reservoir,
    spiking_net: SpikingNetwork,
    neat_population: Population,
    dreamer: DreamerWorldModel,
    contrastive: ContrastiveLearner,
    // ===== EXPERIMENTAL THEORETICAL ALGORITHMS =====
    // Transformer for sequence prediction
    transformer: TransformerPredictor,
    // Variational Autoencoder for state representation
    vae: VariationalAutoencoder,
    // Neural Turing Machine with differentiable memory
    ntm: NeuralTuringMachine,
    // Hawkes Process for event prediction
    hawkes: HawkesProcess,
    // Hurst exponent estimator for fractal analysis
    hurst: HurstEstimator,
    // Information theoretic measures
    info_theory: InformationTheoretic,
    // Gaussian Process Thompson Sampling
    gp_thompson: GPThompsonSampling,
    // Categorical DQN (C51)
    categorical_dqn: CategoricalDQN,
    // Quantum Annealing Optimizer
    quantum_annealer: QuantumAnnealingOptimizer,
    // Meta-RL Learner
    meta_learner: MetaRLLearner,
    // Population-Based Training
    pbt: PBTPopulation,
    // Safe RL with constraints
    safe_rl: SafeRLAgent,
    // Ornstein-Uhlenbeck Process
    ou_process: OrnsteinUhlenbeckProcess,
    // Gumbel AlphaZero MCTS
    gumbel_mcts: GumbelMCTS,
    // EXP3 Adversarial Bandit
    exp3_bandit: EXP3Bandit,
    // Temporal Convolutional Network
    tcn: TCN,
    // Data collection phase
    data_collection_target: usize, // How many bets before AI takes over
    data_collection_multiplier: f32, // Multiplier to use during data collection
    data_collection_high_low_random: bool, // Randomize high/low during collection
    data_collected: usize,         // Number of data points collected
    win_rates_by_multiplier: Vec<f32>, // Win rates observed per multiplier arm
    confidence_threshold: f32,     // Minimum confidence to exit collection
    min_patterns_needed: usize,    // Minimum patterns in memory

    // ===== GENUINELY INTELLIGENT FEATURES =====
    edge_detector: EdgeDetector,
    confidence_calibrator: ConfidenceCalibrator,
    strategy_selector: AdaptiveStrategySelector,
    pattern_strength: PatternStrengthEvaluator,
    session_state: SessionStateAnalyzer,
    performance_momentum: PerformanceMomentum,
    risk_adjuster: DynamicRiskAdjuster,
    win_predictor: SessionWinPredictor,
    bankroll_manager: SmartBankrollManager,

    // ===== DYNAMIC MODEL WEIGHTING SYSTEM =====
    // Track each model's prediction accuracy for adaptive weighting
    model_predictions: VecDeque<Vec<ModelPrediction>>, // Last N predictions per model
    model_accuracies: Vec<f32>,                        // Rolling accuracy per model
    model_weights: Vec<f32>,                           // Dynamic weights based on performance
    total_model_prediction_count: usize,               // For per-model tracking
    model_regime_state: ModelRegimeState,              // Regime for model weighting

    // ===== PERFORMANCE TRACKING =====
    model_meta_learner: ModelMetaLearner, // Learns optimal model combinations
    voting_tracker: VotingPerformanceTracker, // Tracks ALL voting component performance

    // ===== ADVANCED IMPROVEMENTS =====
    cached_predictions: CachedPredictions, // Cached expensive predictions
    skip_bet_threshold: f32,               // Uncertainty threshold for skipping
    recent_skips: u32,                     // Track recent skip decisions
    skip_adjustment: f32,                  // Dynamic adjustment to skip threshold

    // ===== ABSURDLY UNNECESSARY FEATURES =====
    lunar_phase: LunarPhaseTracker, // Because the moon affects everything
    biorhythm: BiorhythmCalculator, // Physical, emotional, intellectual cycles
    sentiment_analyzer: SentimentAnalyzer, // Internal "market" sentiment from performance
    dunning_kruger: DunningKrugerDetector, // Detect overconfidence when actually wrong
    hot_hand_tracker: HotHandTracker, // Are we falling for the hot hand fallacy?
    martingale_urge: MartingaleUrgeSuppressor, // Track and suppress martingale impulses
    pattern_confidence: PatternConfidenceCalibrator, // Calibrate confidence based on pattern
    chaos_dragon: ChaosDragon,      // A dragon that eats bad decisions
    divine_intervention: DivineIntervention, // 0.01% chance of divine guidance
    conspiracy_detector: ConspiracyDetector, // Detect if the game is rigged against us
    schrodinger_cat: SchrodingerCat, // Simultaneously winning and losing until observed

    // ===== EVEN MORE ABSURD FEATURES =====
    karma_calculator: KarmaCalculator, // Track if universe owes us
    butterfly_effect: ButterflyEffectTracker, // Small decisions cascade
    pattern_cult_detector: PatternCultDetector, // Seeing patterns that don't exist
    quantum_entanglement: QuantumEntanglement, // Entangled with hypothetical gamblers
    philosophical_uncertainty: PhilosophicalUncertainty, // Questions randomness itself
    akashic_reader: AkashicRecordReader, // Reads the "cosmic record" of all bets
    retrocausality_engine: RetrocausalityEngine, // Future affects past
    probability_manipulator: ProbabilityManipulator, // Attempts to influence probability
    casino_psychology: CasinoPsychologyModel, // Models casino's mind games
    luck_bank: LuckBank,               // Stores and dispenses luck

    // ===== ADVANCED INTELLIGENCE FEATURES =====
    // Feature 1: Curiosity-Driven Exploration
    curiosity_engine: CuriosityEngine,
    // Feature 2: Profit-Weighted Learning
    profit_weighted_learner: ProfitWeightedLearner,
    // Feature 3: Anti-Persistence Detection
    anti_persistence: AntiPersistenceDetector,
    // Feature 4: Multi-Step Lookahead Planning
    lookahead_planner: LookaheadPlanner,
    // Feature 5: Ensemble Pruning & Weighting
    ensemble_manager: EnsembleManager,
    // Feature 6: Session Memory & Transfer Learning
    session_memory: SessionMemory,
    // Feature 7: Calibrated Confidence
    advanced_calibrator: AdvancedConfidenceCalibrator,

    // ===== EVEN MORE INSANE FEATURES (FEATURES 8-17) =====
    // Feature 8: Transformer Sequence Predictor
    transformer_predictor: TransformerSequencePredictor,
    // Feature 9: Episodic Memory
    episodic_memory: EpisodicMemory,
    // Feature 10: Counterfactual Regret Minimization
    cfr: CounterfactualRegretMinimizer,
    // Feature 11: Bayesian Model Averaging
    bayesian_averager: BayesianModelAverager,
    // Feature 12: Anomaly Detection
    anomaly_detector: AnomalyDetector,
    // Feature 13: Risk-Aware RL with CVaR
    risk_aware_rl: RiskAwareRL,
    // Feature 14: Hierarchical RL
    hierarchical_rl: HierarchicalRL,
    // Feature 15: Model-Based RL
    model_based_rl: ModelBasedRL,
    // Feature 16: Inverse RL
    inverse_rl: InverseRL,
    // Feature 17: Theory of Mind
    theory_of_mind: TheoryOfMind,

    // ===== TRAINING STATE =====
    last_arm_idx: usize,           // Arm index used for last bet
    last_context: Vec<f32>,        // Context for last bet (for training)
    last_multiplier_action: usize, // Multiplier action index for DQN training
    replay_buffer: ReplayBuffer,   // Experience replay for DQN
}

/// Individual model prediction record
#[derive(Clone, Debug)]
struct ModelPrediction {
    model_id: usize,      // Which model
    predicted_high: bool, // What it predicted
    confidence: f32,      // How confident (0-1)
    was_correct: bool,    // Did it win?
}

/// Model regime detection state (stored independently from MarketRegime)
#[derive(Clone, Copy, Debug, PartialEq)]
enum ModelRegimeState {
    Trending, // Strong directional movement
    Volatile, // High volatility, choppy
    Recovery, // Deep drawdown, recovery mode
    Stable,   // Low volatility, sideways
    Unknown,  // Not enough data
}

/// Cached predictions computed once per bet cycle
#[derive(Clone, Debug, Default)]
struct CachedPredictions {
    // Computationally expensive predictions - cached
    kalman_state: f32,
    particle_estimate: f32,
    gp_mean: f32,
    gp_var: f32,
    mcts_best_action: usize,
    mcts_best_value: f32,
    markov_pred: f32,
    hurst_exp: f32,
    entropy: f32,
    transfer_entropy: f32,

    // Model ensemble summary
    ensemble_high_vote: f32,
    ensemble_low_vote: f32,
    ensemble_confidence: f32,
    model_agreement: f32, // How much models agree (0-1, higher = more agreement)
    uncertainty_score: f32, // Combined uncertainty measure

    // Whether cache is valid
    valid: bool,
}

// ============================================================================
// GENUINELY INTELLIGENT FEATURES - These actually improve performance
// ============================================================================

/// Edge Detector - Detect if we have a genuine statistical edge
/// Uses binomial test to check if win rate is significantly above expected
#[derive(Clone, Debug)]
struct EdgeDetector {
    recent_wins: VecDeque<bool>,
    edge_history: VecDeque<f32>,
    detected_edge: f32,   // -1 to 1: negative = bad, 0 = neutral, positive = good
    edge_confidence: f32, // How confident we are in the edge detection
    sample_size: usize,
    significance_level: f32,
}

impl Default for EdgeDetector {
    fn default() -> Self {
        Self::new()
    }
}

impl EdgeDetector {
    fn new() -> Self {
        Self {
            recent_wins: VecDeque::with_capacity(200),
            edge_history: VecDeque::with_capacity(50),
            detected_edge: 0.0,
            edge_confidence: 0.0,
            sample_size: 0,
            significance_level: 0.05,
        }
    }

    fn record_outcome(&mut self, won: bool) {
        self.recent_wins.push_back(won);
        if self.recent_wins.len() > 200 {
            self.recent_wins.pop_front();
        }
        self.sample_size = self.recent_wins.len();
        self.detect_statistical_edge();
    }

    fn detect_statistical_edge(&mut self) {
        if self.recent_wins.len() < 30 {
            self.detected_edge = 0.0;
            self.edge_confidence = 0.0;
            return;
        }

        let wins = self.recent_wins.iter().filter(|&&w| w).count() as f32;
        let total = self.recent_wins.len() as f32;
        let observed_rate = wins / total;

        // Expected rate for 2x multiplier with house edge
        let expected_rate = 0.475;

        // Calculate z-score
        let variance = expected_rate * (1.0 - expected_rate);
        let std_error = (variance / total).sqrt();
        let z_score = (observed_rate - expected_rate) / std_error.max(1e-8);

        // Convert to edge (-1 to 1 scale)
        self.detected_edge = z_score.tanh() * 0.5; // Smooth scaling

        // Confidence based on sample size and z-score magnitude
        let sample_confidence = (self.sample_size as f32 / 100.0).min(1.0);
        let z_confidence = (z_score.abs() / 2.0).min(1.0); // 2 sigma = high confidence
        self.edge_confidence = sample_confidence * z_confidence;

        // Store history
        self.edge_history.push_back(self.detected_edge);
        if self.edge_history.len() > 50 {
            self.edge_history.pop_front();
        }
    }

    fn has_positive_edge(&self) -> bool {
        self.detected_edge > 0.05 && self.edge_confidence > 0.3
    }

    fn get_edge_adjustment(&self) -> f32 {
        // Returns multiplier for bet size based on detected edge
        1.0 + self.detected_edge * self.edge_confidence
    }

    fn get_edge_vote(&self) -> (f32, bool) {
        // Vote based on edge direction
        // Positive edge + winning = keep going
        // Negative edge = be cautious
        let vote = self.detected_edge.abs() * self.edge_confidence * 0.2;
        (vote, self.detected_edge > 0.0)
    }
}

/// Confidence Calibrator - Calibrate model confidence to actual accuracy
/// Models tend to be overconfident; this learns to correct for that
#[derive(Clone, Debug, Default)]
struct ConfidenceCalibrator {
    confidence_bins: Vec<ConfidenceBin>,
    calibration_error: f32,
    recent_calibration_errors: VecDeque<f32>,
}

#[derive(Clone, Debug, Default)]
struct ConfidenceBin {
    confidence_range: (f32, f32), // e.g., (0.7, 0.8)
    predictions: u32,
    correct: u32,
    calibrated_confidence: f32,
}

impl ConfidenceCalibrator {
    fn new() -> Self {
        // Initialize 10 bins from 0.0 to 1.0
        let bins: Vec<ConfidenceBin> = (0..10)
            .map(|i| ConfidenceBin {
                confidence_range: (i as f32 * 0.1, (i + 1) as f32 * 0.1),
                predictions: 0,
                correct: 0,
                calibrated_confidence: (i as f32 + 0.5) * 0.1,
            })
            .collect();

        Self {
            confidence_bins: bins,
            calibration_error: 0.0,
            recent_calibration_errors: VecDeque::with_capacity(50),
        }
    }

    fn record_prediction(&mut self, confidence: f32, was_correct: bool) {
        // Find the right bin
        for bin in &mut self.confidence_bins {
            if confidence >= bin.confidence_range.0 && confidence < bin.confidence_range.1 {
                bin.predictions += 1;
                if was_correct {
                    bin.correct += 1;
                }
                // Update calibrated confidence
                if bin.predictions > 5 {
                    bin.calibrated_confidence = bin.correct as f32 / bin.predictions as f32;
                }
                break;
            }
        }

        // Calculate overall calibration error (Brier score)
        self.update_calibration_error();
    }

    fn update_calibration_error(&mut self) {
        let mut total_error = 0.0;
        let mut count = 0;

        for bin in &self.confidence_bins {
            if bin.predictions > 10 {
                let mid_confidence = (bin.confidence_range.0 + bin.confidence_range.1) / 2.0;
                let actual_rate = bin.correct as f32 / bin.predictions as f32;
                total_error += (mid_confidence - actual_rate).powi(2);
                count += 1;
            }
        }

        if count > 0 {
            self.calibration_error = total_error / count as f32;
            self.recent_calibration_errors
                .push_back(self.calibration_error);
            if self.recent_calibration_errors.len() > 50 {
                self.recent_calibration_errors.pop_front();
            }
        }
    }

    fn calibrate_confidence(&self, raw_confidence: f32) -> f32 {
        // Find the calibrate value for this confidence level
        for bin in &self.confidence_bins {
            if raw_confidence >= bin.confidence_range.0 && raw_confidence < bin.confidence_range.1 {
                if bin.predictions > 10 {
                    return bin.calibrated_confidence;
                }
            }
        }
        raw_confidence
    }

    fn get_calibrated_confidence(&self, confidence: f32) -> f32 {
        self.calibrate_confidence(confidence)
    }
}

/// Adaptive Strategy Selector - Picks the best strategy for current conditions
#[derive(Clone, Debug)]
struct AdaptiveStrategySelector {
    strategies: Vec<StrategyPerformance>,
    current_best: StrategyType,
    exploration_rate: f32,
    strategy_history: VecDeque<StrategyType>,
}

#[derive(Clone, Debug, Copy, PartialEq)]
enum StrategyType {
    Conservative, // Low risk, steady
    Aggressive,   // High risk, high reward
    Balanced,     // Middle ground
    Recovery,     // Recovering from losses
    Streak,       // Riding a win streak
    Adaptive,     // Let ML decide
}

#[derive(Clone, Debug)]
struct StrategyPerformance {
    strategy: StrategyType,
    wins: u32,
    losses: u32,
    total_profit: f32,
    avg_bet_size: f32,
    last_used: usize, // bet number when last used
}

impl Default for AdaptiveStrategySelector {
    fn default() -> Self {
        Self::new()
    }
}

impl AdaptiveStrategySelector {
    fn new() -> Self {
        let strategies = vec![
            StrategyPerformance {
                strategy: StrategyType::Conservative,
                wins: 0,
                losses: 0,
                total_profit: 0.0,
                avg_bet_size: 0.02,
                last_used: 0,
            },
            StrategyPerformance {
                strategy: StrategyType::Aggressive,
                wins: 0,
                losses: 0,
                total_profit: 0.0,
                avg_bet_size: 0.15,
                last_used: 0,
            },
            StrategyPerformance {
                strategy: StrategyType::Balanced,
                wins: 0,
                losses: 0,
                total_profit: 0.0,
                avg_bet_size: 0.05,
                last_used: 0,
            },
            StrategyPerformance {
                strategy: StrategyType::Recovery,
                wins: 0,
                losses: 0,
                total_profit: 0.0,
                avg_bet_size: 0.03,
                last_used: 0,
            },
            StrategyPerformance {
                strategy: StrategyType::Streak,
                wins: 0,
                losses: 0,
                total_profit: 0.0,
                avg_bet_size: 0.10,
                last_used: 0,
            },
            StrategyPerformance {
                strategy: StrategyType::Adaptive,
                wins: 0,
                losses: 0,
                total_profit: 0.0,
                avg_bet_size: 0.05,
                last_used: 0,
            },
        ];

        Self {
            strategies,
            current_best: StrategyType::Balanced,
            exploration_rate: 0.1,
            strategy_history: VecDeque::with_capacity(100),
        }
    }

    fn select_strategy(
        &mut self,
        win_streak: u32,
        loss_streak: u32,
        drawdown: f32,
        total_bets: usize,
    ) -> StrategyType {
        // Determine best strategy for conditions
        let recommended = if loss_streak >= 5 || drawdown > 0.3 {
            StrategyType::Recovery
        } else if win_streak >= 5 {
            StrategyType::Streak
        } else if drawdown > 0.15 {
            StrategyType::Conservative
        } else if drawdown < -0.2 {
            // In profit - can be more aggressive
            StrategyType::Aggressive
        } else {
            StrategyType::Balanced
        };

        // Small chance to explore different strategies
        if rand::rng().random::<f32>() < self.exploration_rate && total_bets > 50 {
            let all_strategies = [
                StrategyType::Conservative,
                StrategyType::Aggressive,
                StrategyType::Balanced,
                StrategyType::Recovery,
                StrategyType::Streak,
                StrategyType::Adaptive,
            ];
            let idx = (rand::rng().random::<f32>() * all_strategies.len() as f32) as usize;
            all_strategies[idx]
        } else {
            self.current_best = recommended;
            recommended
        }
    }

    fn record_outcome(
        &mut self,
        strategy: StrategyType,
        won: bool,
        profit: f32,
        bet_size: f32,
        total_bets: usize,
    ) {
        for s in &mut self.strategies {
            if s.strategy == strategy {
                if won {
                    s.wins += 1;
                } else {
                    s.losses += 1;
                }
                s.total_profit += profit;
                s.avg_bet_size = s.avg_bet_size * 0.9 + bet_size * 0.1;
                s.last_used = total_bets;
                break;
            }
        }

        self.strategy_history.push_back(strategy);
        if self.strategy_history.len() > 100 {
            self.strategy_history.pop_front();
        }
    }

    fn get_best_strategy(&self) -> StrategyType {
        let mut best = StrategyType::Balanced;
        let mut best_score = f32::MIN;

        for s in &self.strategies {
            let total = s.wins + s.losses;
            if total > 10 {
                let win_rate = s.wins as f32 / total as f32;
                let profit_factor = s.total_profit.signum() * s.total_profit.abs().ln_1p();
                let score =
                    win_rate * 0.5 + profit_factor * 0.3 + (s.wins + s.losses) as f32 * 0.001;
                if score > best_score {
                    best_score = score;
                    best = s.strategy;
                }
            }
        }

        best
    }

    fn get_strategy_multiplier(&self, strategy: StrategyType) -> f32 {
        for s in &self.strategies {
            if s.strategy == strategy {
                return s.avg_bet_size;
            }
        }
        0.05
    }
}

/// Pattern Strength Evaluator - Evaluates how strong/reliable patterns actually are
#[derive(Clone, Debug, Default)]
struct PatternStrengthEvaluator {
    pattern_outcomes: VecDeque<PatternOutcome>,
    strong_pattern_threshold: f32,
    weak_pattern_threshold: f32,
}

#[derive(Clone, Debug)]
struct PatternOutcome {
    pattern_id: u64,
    pattern_type: String,
    predicted_outcome: bool,
    actual_outcome: bool,
    confidence: f32,
    strength: f32,
}

impl PatternStrengthEvaluator {
    fn new() -> Self {
        Self {
            pattern_outcomes: VecDeque::with_capacity(200),
            strong_pattern_threshold: 0.65,
            weak_pattern_threshold: 0.55,
        }
    }

    fn record_pattern(
        &mut self,
        pattern_type: &str,
        predicted: bool,
        actual: bool,
        confidence: f32,
    ) {
        let outcome = PatternOutcome {
            pattern_id: rand::rng().random::<u64>(),
            pattern_type: pattern_type.to_string(),
            predicted_outcome: predicted,
            actual_outcome: actual,
            confidence,
            strength: if predicted == actual { 1.0 } else { 0.0 },
        };

        self.pattern_outcomes.push_back(outcome);
        if self.pattern_outcomes.len() > 200 {
            self.pattern_outcomes.pop_front();
        }
    }

    fn get_pattern_strength(&self, pattern_type: &str) -> f32 {
        let matching: Vec<_> = self
            .pattern_outcomes
            .iter()
            .filter(|p| p.pattern_type == pattern_type)
            .collect();

        if matching.is_empty() {
            return 0.5;
        }

        let correct = matching
            .iter()
            .filter(|p| p.predicted_outcome == p.actual_outcome)
            .count();
        correct as f32 / matching.len() as f32
    }

    fn get_strong_patterns(&self) -> Vec<String> {
        let mut pattern_strengths: std::collections::HashMap<String, (u32, u32)> =
            std::collections::HashMap::new();

        for outcome in &self.pattern_outcomes {
            let entry = pattern_strengths
                .entry(outcome.pattern_type.clone())
                .or_insert((0, 0));
            if outcome.predicted_outcome == outcome.actual_outcome {
                entry.0 += 1;
            }
            entry.1 += 1;
        }

        pattern_strengths
            .iter()
            .filter(|(_, (correct, total))| {
                *total > 10 && (*correct as f32 / *total as f32) > self.strong_pattern_threshold
            })
            .map(|(name, _)| name.clone())
            .collect()
    }

    fn should_trust_patterns(&self) -> bool {
        let total = self.pattern_outcomes.len();
        if total < 20 {
            return false;
        }

        let correct = self
            .pattern_outcomes
            .iter()
            .filter(|p| p.predicted_outcome == p.actual_outcome)
            .count();

        correct as f32 / total as f32 > self.weak_pattern_threshold
    }
}

/// Session State Analyzer - Analyzes the current state of the gambling session
#[derive(Clone, Debug, Default)]
struct SessionStateAnalyzer {
    session_states: VecDeque<SessionState>,
    current_state: SessionStateType,
    state_duration: u32,
    transitions: Vec<(SessionStateType, SessionStateType, u32)>,
}

#[derive(Clone, Debug, Copy, PartialEq)]
enum SessionStateType {
    WarmingUp,      // First few bets
    BuildingProfit, // Gradually increasing
    AtPeak,         // Maximum profit
    Declining,      // Losing some profit
    Recovery,       // Trying to recover
    CriticalLoss,   // Major drawdown
    Stable,         // Relatively flat
    HotStreak,      // Multiple wins in a row
    ColdStreak,     // Multiple losses in a row
}

impl Default for SessionStateType {
    fn default() -> Self {
        SessionStateType::WarmingUp
    }
}

#[derive(Clone, Debug)]
struct SessionState {
    state_type: SessionStateType,
    entered_at: usize, // bet number
    bank_ratio: f32,   // bank / initial_bank
    win_rate: f32,
}

impl SessionStateAnalyzer {
    fn new() -> Self {
        Self {
            session_states: VecDeque::with_capacity(20),
            current_state: SessionStateType::WarmingUp,
            state_duration: 0,
            transitions: Vec::new(),
        }
    }

    fn update(
        &mut self,
        total_bets: usize,
        bank: f32,
        initial_bank: f32,
        win_streak: u32,
        loss_streak: u32,
        total_wins: u32,
        total_losses: u32,
    ) {
        let bank_ratio = bank / initial_bank.max(1e-8);
        let win_rate = if total_wins + total_losses > 0 {
            total_wins as f32 / (total_wins + total_losses) as f32
        } else {
            0.5
        };

        let old_state = self.current_state;
        self.current_state = self.determine_state(total_bets, bank_ratio, win_streak, loss_streak);

        if old_state != self.current_state {
            self.transitions
                .push((old_state, self.current_state, total_bets as u32));
            self.state_duration = 0;

            self.session_states.push_back(SessionState {
                state_type: self.current_state,
                entered_at: total_bets,
                bank_ratio,
                win_rate,
            });

            if self.session_states.len() > 20 {
                self.session_states.pop_front();
            }
        } else {
            self.state_duration += 1;
        }
    }

    fn determine_state(
        &self,
        total_bets: usize,
        bank_ratio: f32,
        win_streak: u32,
        loss_streak: u32,
    ) -> SessionStateType {
        if total_bets < 10 {
            return SessionStateType::WarmingUp;
        }

        if win_streak >= 5 {
            return SessionStateType::HotStreak;
        }

        if loss_streak >= 5 {
            return SessionStateType::ColdStreak;
        }

        if bank_ratio < 0.5 {
            return SessionStateType::CriticalLoss;
        }

        if bank_ratio < 0.75 {
            return SessionStateType::Recovery;
        }

        if bank_ratio > 1.5 {
            return SessionStateType::AtPeak;
        }

        if bank_ratio > 1.2 {
            return SessionStateType::BuildingProfit;
        }

        if bank_ratio < 0.95 {
            return SessionStateType::Declining;
        }

        SessionStateType::Stable
    }

    fn get_state_risk_modifier(&self) -> f32 {
        match self.current_state {
            SessionStateType::WarmingUp => 0.5,
            SessionStateType::BuildingProfit => 1.0,
            SessionStateType::AtPeak => 0.7, // Protect profits
            SessionStateType::Declining => 0.8,
            SessionStateType::Recovery => 0.6,
            SessionStateType::CriticalLoss => 0.3,
            SessionStateType::Stable => 1.0,
            SessionStateType::HotStreak => 1.3,
            SessionStateType::ColdStreak => 0.5,
        }
    }

    fn get_state(&self) -> SessionStateType {
        self.current_state
    }
}

/// Performance Momentum - Tracks if performance is improving or degrading
#[derive(Clone, Debug, Default)]
struct PerformanceMomentum {
    recent_profit_history: VecDeque<f32>,
    momentum: f32,     // -1 to 1: negative = declining, positive = improving
    velocity: f32,     // Rate of change
    acceleration: f32, // Change in velocity
}

impl PerformanceMomentum {
    fn new() -> Self {
        Self {
            recent_profit_history: VecDeque::with_capacity(50),
            momentum: 0.0,
            velocity: 0.0,
            acceleration: 0.0,
        }
    }

    fn record_profit(&mut self, profit: f32) {
        self.recent_profit_history.push_back(profit);
        if self.recent_profit_history.len() > 50 {
            self.recent_profit_history.pop_front();
        }

        self.calculate_momentum();
    }

    fn calculate_momentum(&mut self) {
        if self.recent_profit_history.len() < 10 {
            return;
        }

        let history: Vec<f32> = self.recent_profit_history.iter().copied().collect();
        let n = history.len();

        // Calculate cumulative profits
        let cumulative: Vec<f32> = history
            .iter()
            .scan(0.0, |acc, &x| {
                *acc += x;
                Some(*acc)
            })
            .collect();

        // Simple linear regression for trend (momentum)
        let sum_x: f32 = (0..n as i32).map(|i| i as f32).sum();
        let sum_y: f32 = cumulative.iter().sum();
        let sum_xy: f32 = cumulative
            .iter()
            .enumerate()
            .map(|(i, &y)| i as f32 * y)
            .sum();
        let sum_x2: f32 = (0..n as i32).map(|i| (i as f32).powi(2)).sum();

        let n_f = n as f32;
        let slope = (n_f * sum_xy - sum_x * sum_y) / (n_f * sum_x2 - sum_x.powi(2)).max(1e-8);

        // Normalize to -1 to 1
        let old_momentum = self.momentum;
        self.momentum = slope.tanh();

        // Velocity is change in momentum
        let old_velocity = self.velocity;
        self.velocity = self.momentum - old_momentum;

        // Acceleration is change in velocity
        self.acceleration = self.velocity - old_velocity;
    }

    fn get_momentum_adjustment(&self) -> f32 {
        // Positive momentum = can afford to be more aggressive
        // Negative momentum = need to be more conservative
        1.0 + self.momentum * 0.2
    }

    fn is_improving(&self) -> bool {
        self.momentum > 0.1
    }

    fn is_declining(&self) -> bool {
        self.momentum < -0.1
    }
}

/// Dynamic Risk Adjuster - Adjusts risk based on multiple factors
#[derive(Clone, Debug, Default)]
struct DynamicRiskAdjuster {
    base_risk: f32,
    current_risk: f32,
    risk_history: VecDeque<f32>,
    max_risk: f32,
    min_risk: f32,
}

impl DynamicRiskAdjuster {
    fn new() -> Self {
        Self {
            base_risk: 0.05,
            current_risk: 0.05,
            risk_history: VecDeque::with_capacity(100),
            max_risk: 0.25,
            min_risk: 0.01,
        }
    }

    fn adjust_risk(
        &mut self,
        edge: f32,
        momentum: f32,
        session_state: SessionStateType,
        confidence: f32,
    ) -> f32 {
        // Start with base risk
        let mut risk = self.base_risk;

        // Adjust based on edge
        risk *= 1.0 + edge * 0.5;

        // Adjust based on momentum
        risk *= 1.0 + momentum * 0.3;

        // Adjust based on session state
        match session_state {
            SessionStateType::HotStreak => risk *= 1.3,
            SessionStateType::ColdStreak => risk *= 0.6,
            SessionStateType::CriticalLoss => risk *= 0.3,
            SessionStateType::Recovery => risk *= 0.7,
            SessionStateType::AtPeak => risk *= 0.8,
            _ => {}
        }

        // Adjust based on confidence
        risk *= 0.5 + confidence * 0.5;

        // Clamp
        risk = risk.clamp(self.min_risk, self.max_risk);
        self.current_risk = risk;

        self.risk_history.push_back(risk);
        if self.risk_history.len() > 100 {
            self.risk_history.pop_front();
        }

        risk
    }

    fn get_current_risk(&self) -> f32 {
        self.current_risk
    }

    fn should_reduce_risk(&self) -> bool {
        if self.risk_history.len() < 10 {
            return false;
        }

        let recent: Vec<f32> = self.risk_history.iter().rev().take(10).copied().collect();
        let avg = recent.iter().sum::<f32>() / recent.len() as f32;
        avg > self.current_risk * 1.5 // Risk is declining
    }
}

/// Session Win Predictor - Predicts likelihood of ending session profitably
#[derive(Clone, Debug, Default)]
struct SessionWinPredictor {
    predictions: VecDeque<SessionPrediction>,
    current_probability: f32,
    feature_history: VecDeque<SessionFeatures>,
}

#[derive(Clone, Debug)]
struct SessionPrediction {
    predicted_win: bool,
    actual_win: bool,
    probability: f32,
    bet_number: usize,
}

#[derive(Clone, Debug)]
struct SessionFeatures {
    bet_number: usize,
    bank_ratio: f32,
    win_rate: f32,
    streak: i32,
    volatility: f32,
    outcome: Option<bool>, // None if not finished
}

impl SessionWinPredictor {
    fn new() -> Self {
        Self {
            predictions: VecDeque::with_capacity(100),
            current_probability: 0.5,
            feature_history: VecDeque::with_capacity(500),
        }
    }

    fn predict_session_win(
        &mut self,
        bank_ratio: f32,
        win_rate: f32,
        win_streak: u32,
        loss_streak: u32,
        total_bets: usize,
    ) -> f32 {
        // Simple heuristic-based prediction
        // Could be replaced with ML model

        let streak_factor = if win_streak > loss_streak {
            (win_streak as f32 / 10.0).min(0.2)
        } else {
            -(loss_streak as f32 / 10.0).min(0.2)
        };

        let bank_factor = (bank_ratio - 1.0) * 0.3;
        let win_rate_factor = (win_rate - 0.5) * 0.4;
        let duration_factor = if total_bets > 100 { -0.05 } else { 0.0 }; // Longer sessions tend to lose

        let raw_prob = 0.5 + bank_factor + win_rate_factor + streak_factor + duration_factor;
        self.current_probability = raw_prob.clamp(0.05, 0.95);

        self.current_probability
    }

    fn record_features(
        &mut self,
        total_bets: usize,
        bank_ratio: f32,
        win_rate: f32,
        win_streak: u32,
        loss_streak: u32,
    ) {
        let features = SessionFeatures {
            bet_number: total_bets,
            bank_ratio,
            win_rate,
            streak: win_streak as i32 - loss_streak as i32,
            volatility: 0.0, // Would need to calculate
            outcome: None,
        };

        self.feature_history.push_back(features);
        if self.feature_history.len() > 500 {
            self.feature_history.pop_front();
        }
    }

    fn get_win_probability(&self) -> f32 {
        self.current_probability
    }

    fn should_keep_playing(&self) -> bool {
        self.current_probability > 0.45
    }
}

/// Smart Bankroll Manager - Intelligent bankroll management
#[derive(Clone, Debug, Default)]
struct SmartBankrollManager {
    target_profit: f32,
    stop_loss: f32,
    current_bank: f32,
    peak_bank: f32,
    valley_bank: f32,
    sessions_played: u32,
    sessions_won: u32,
    avg_session_length: f32,
    recommended_bet_pct: f32,
}

impl SmartBankrollManager {
    fn new() -> Self {
        Self {
            target_profit: 0.5, // 50% profit target
            stop_loss: 0.3,     // 30% loss limit
            current_bank: 0.0,
            peak_bank: 0.0,
            valley_bank: f32::MAX,
            sessions_played: 0,
            sessions_won: 0,
            avg_session_length: 100.0,
            recommended_bet_pct: 0.05,
        }
    }

    fn update(&mut self, bank: f32, initial_bank: f32) {
        self.current_bank = bank;
        self.peak_bank = self.peak_bank.max(bank);
        self.valley_bank = self.valley_bank.min(bank);

        self.calculate_recommended_bet(initial_bank);
    }

    fn calculate_recommended_bet(&mut self, initial_bank: f32) {
        if initial_bank <= 0.0 {
            self.recommended_bet_pct = 0.01;
            return;
        }

        let profit_ratio = (self.current_bank - initial_bank) / initial_bank;

        // Kelly-like criterion with safety factor
        if profit_ratio > self.target_profit {
            // Exceeded profit target - protect winnings
            self.recommended_bet_pct = 0.02;
        } else if profit_ratio < -self.stop_loss {
            // Hit stop loss - minimal bets
            self.recommended_bet_pct = 0.01;
        } else {
            // Normal operation - risk decreases as we approach targets
            let safety_factor = 1.0 - profit_ratio.abs() / self.stop_loss.max(0.1);
            self.recommended_bet_pct = 0.05 * safety_factor.max(0.3);
        }
    }

    fn get_recommended_bet_pct(&self) -> f32 {
        self.recommended_bet_pct
    }

    fn should_stop_session(&self, initial_bank: f32) -> bool {
        if initial_bank <= 0.0 {
            return false;
        }

        let profit_ratio = (self.current_bank - initial_bank) / initial_bank;

        profit_ratio > self.target_profit || profit_ratio < -self.stop_loss
    }

    fn get_profit_ratio(&self, initial_bank: f32) -> f32 {
        if initial_bank <= 0.0 {
            return 0.0;
        }
        (self.current_bank - initial_bank) / initial_bank
    }

    fn record_session(&mut self, won: bool, length: usize) {
        self.sessions_played += 1;
        if won {
            self.sessions_won += 1;
        }

        // Update average session length
        let n = self.sessions_played as f32;
        self.avg_session_length = self.avg_session_length * (n - 1.0) / n + length as f32 / n;

        // Reset trackers
        self.peak_bank = self.current_bank;
        self.valley_bank = f32::MAX;
    }
}

// ============================================================================
// ABSURDLY UNNECESSARY FEATURES
// ============================================================================

/// Lunar phase tracker - because the moon affects gambling apparently
#[derive(Clone, Debug, Default)]
struct LunarPhaseTracker {
    current_phase: f32,  // 0.0 = new moon, 0.5 = full moon, 1.0 = new moon again
    days_since_new: u32, // Days since last new moon
    moon_luck_correlation: f32, // Track if moon phases affect our luck
    full_moon_high_bias: f32, // Track high bet success during full moon
}

impl LunarPhaseTracker {
    fn new() -> Self {
        Self {
            current_phase: 0.0,
            days_since_new: 0,
            moon_luck_correlation: 0.5,
            full_moon_high_bias: 0.5,
        }
    }

    fn update(&mut self, total_bets: usize) {
        // Simulate lunar cycle (~29.5 days, but we use bets as "time")
        self.days_since_new = (total_bets % 295) as u32; // 295 "bet-days" per cycle
        self.current_phase = self.days_since_new as f32 / 295.0;
    }

    fn get_moon_vote(&self) -> (f32, bool) {
        // (vote_strength, high/low)
        // Full moon (0.5 phase) = slight HIGH bias
        // New moon (0.0 or 1.0) = slight LOW bias
        let moon_influence = (self.current_phase - 0.5).abs();
        let is_full_moon = self.current_phase > 0.4 && self.current_phase < 0.6;
        let is_new_moon = self.current_phase < 0.1 || self.current_phase > 0.9;

        let vote = if is_full_moon {
            0.15 // Full moon = bet HIGH (classic superstition)
        } else if is_new_moon {
            0.12 // New moon = bet LOW
        } else {
            0.05 // Weak influence otherwise
        };

        (vote, self.current_phase > 0.5)
    }
}

/// Biorhythm calculator - physical, emotional, intellectual cycles
#[derive(Clone, Debug, Default)]
struct BiorhythmCalculator {
    physical_cycle: f32,     // 23-day cycle
    emotional_cycle: f32,    // 28-day cycle
    intellectual_cycle: f32, // 33-day cycle
    current_day: u32,
}

impl BiorhythmCalculator {
    fn new() -> Self {
        Self {
            physical_cycle: 0.0,
            emotional_cycle: 0.0,
            intellectual_cycle: 0.0,
            current_day: 0,
        }
    }

    fn update(&mut self, total_bets: usize) {
        self.current_day = total_bets as u32;
        // Sinusoidal cycles
        self.physical_cycle = ((self.current_day as f32 / 23.0) * std::f32::consts::TAU).sin();
        self.emotional_cycle = ((self.current_day as f32 / 28.0) * std::f32::consts::TAU).sin();
        self.intellectual_cycle = ((self.current_day as f32 / 33.0) * std::f32::consts::TAU).sin();
    }

    fn get_biorhythm_vote(&self) -> (f32, bool) {
        // Combined biorhythm influence
        let combined = (self.physical_cycle + self.emotional_cycle + self.intellectual_cycle) / 3.0;
        let vote = combined.abs() * 0.1; // Small influence
        (vote, combined > 0.0)
    }

    fn get_energy_level(&self) -> f32 {
        // Are we in a "high energy" period?
        (self.physical_cycle + self.emotional_cycle + self.intellectual_cycle) / 3.0
    }
}

/// Internal sentiment analyzer based on recent performance
#[derive(Clone, Debug, Default)]
struct SentimentAnalyzer {
    fear_greed_index: f32, // 0-100, like the real thing but for our bank
    hope_index: f32,       // How hopeful are we?
    despair_index: f32,    // How despairing are we?
    euphoria_counter: u32, // Count euphoric moments
    panic_counter: u32,    // Count panic moments
}

impl SentimentAnalyzer {
    fn new() -> Self {
        Self {
            fear_greed_index: 50.0,
            hope_index: 0.5,
            despair_index: 0.0,
            euphoria_counter: 0,
            panic_counter: 0,
        }
    }

    fn update(&mut self, win_streak: u32, loss_streak: u32, peak_dd: f32, win_rate: f32) {
        // Fear & Greed Index based on position and streaks
        if win_streak >= 5 {
            self.fear_greed_index = (self.fear_greed_index + 15.0).min(100.0);
            self.euphoria_counter += 1;
        } else if loss_streak >= 5 {
            self.fear_greed_index = (self.fear_greed_index - 15.0).max(0.0);
            self.panic_counter += 1;
        }

        // Hope vs Despair
        self.hope_index = if peak_dd < -0.15 {
            0.8
        } else if peak_dd > 0.2 {
            0.2
        } else {
            0.5
        };
        self.despair_index = if peak_dd > 0.3 { 0.8 } else { peak_dd.max(0.0) };

        // Gradually return to neutral
        self.fear_greed_index = self.fear_greed_index * 0.95 + 50.0 * 0.05;
    }

    fn get_sentiment_vote(&self) -> (f32, bool) {
        // When greed is high, bet bigger/higher
        // When fear is high, bet smaller/lower
        let vote = (self.fear_greed_index - 50.0).abs() / 500.0; // Small influence
        (vote, self.fear_greed_index > 50.0)
    }
}

/// Dunning-Kruger detector - detect when we're overconfident but actually wrong
#[derive(Clone, Debug, Default)]
struct DunningKrugerDetector {
    confidence_when_wrong: f32, // Track confidence on losing bets
    confidence_when_right: f32, // Track confidence on winning bets
    dunning_kruger_score: f32,  // Higher = more likely overconfident
    recent_overconfidence_events: u32,
}

impl DunningKrugerDetector {
    fn new() -> Self {
        Self {
            confidence_when_wrong: 0.5,
            confidence_when_right: 0.5,
            dunning_kruger_score: 0.0,
            recent_overconfidence_events: 0,
        }
    }

    fn record_outcome(&mut self, confidence: f32, was_correct: bool) {
        if was_correct {
            self.confidence_when_right = self.confidence_when_right * 0.9 + confidence * 0.1;
        } else {
            self.confidence_when_wrong = self.confidence_when_wrong * 0.9 + confidence * 0.1;
            // High confidence when wrong = Dunning-Kruger
            if confidence > 0.7 {
                self.recent_overconfidence_events += 1;
            }
        }

        // Dunning-Kruger score = how much more confident we are when wrong
        self.dunning_kruger_score =
            (self.confidence_when_wrong - self.confidence_when_right).max(0.0);
    }

    fn get_overconfidence_penalty(&self) -> f32 {
        // Reduce confidence if we're being Dunning-Kruger
        if self.dunning_kruger_score > 0.15 {
            0.1 * self.dunning_kruger_score // Up to 10% penalty
        } else {
            0.0
        }
    }
}

/// Hot hand tracker - are we falling for the hot hand fallacy?
#[derive(Clone, Debug, Default)]
struct HotHandTracker {
    detected_hot_hand: bool,
    hot_hand_wins: u32,
    hot_hand_losses: u32,
    fallacy_score: f32,  // How much we're falling for it
    rational_check: f32, // Counter-balance with rationality
}

impl HotHandTracker {
    fn new() -> Self {
        Self {
            detected_hot_hand: false,
            hot_hand_wins: 0,
            hot_hand_losses: 0,
            fallacy_score: 0.0,
            rational_check: 0.5,
        }
    }

    fn update(&mut self, win_streak: u32, loss_streak: u32) {
        // Detect "hot hand" feeling
        self.detected_hot_hand = win_streak >= 4;

        if self.detected_hot_hand {
            // Track if hot hand persists or is a fallacy
            self.fallacy_score = self.fallacy_score * 0.9 + 0.1;
        } else {
            self.fallacy_score *= 0.95;
        }

        // Rational check - dice have no memory
        self.rational_check = 0.5;
    }

    fn get_hot_hand_vote(&self) -> (f32, bool, bool) {
        // (vote, follow_hot_hand, is_fallacy)
        if self.detected_hot_hand {
            // Slightly follow the "hot hand" but acknowledge it's probably a fallacy
            let vote = 0.3 * self.fallacy_score;
            (vote, true, self.fallacy_score > 0.6)
        } else {
            (0.0, false, false)
        }
    }
}

/// Martingale urge suppressor - track and suppress the urge to chase losses
#[derive(Clone, Debug, Default)]
struct MartingaleUrgeSuppressor {
    urge_strength: f32,
    times_suppressed: u32,
    times_relapsed: u32, // Times we actually did martingale
    last_loss_amount: f32,
}

impl MartingaleUrgeSuppressor {
    fn new() -> Self {
        Self {
            urge_strength: 0.0,
            times_suppressed: 0,
            times_relapsed: 0,
            last_loss_amount: 0.0,
        }
    }

    fn update(&mut self, loss_streak: u32, current_bet: f32, last_bet: f32) {
        if loss_streak > 0 {
            // Martingale urge = wanting to double after loss
            self.urge_strength = (self.urge_strength + 0.2).min(1.0);
            self.last_loss_amount = last_bet;
        } else {
            self.urge_strength *= 0.8;
        }
    }

    fn should_suppress_martingale(&self) -> bool {
        self.urge_strength > 0.5
    }

    fn get_rational_bet_modifier(&self) -> f32 {
        // Reduce bet if martingale urge is high
        if self.urge_strength > 0.7 {
            0.8 // Slightly reduce bet to avoid martingale
        } else {
            1.0
        }
    }
}

/// Pattern confidence calibrator - calibrate confidence based on pattern strength
#[derive(Clone, Debug, Default)]
struct PatternConfidenceCalibrator {
    pattern_accuracy_history: VecDeque<f32>,
    calibrated_confidence: f32,
}

impl PatternConfidenceCalibrator {
    fn new() -> Self {
        Self {
            pattern_accuracy_history: VecDeque::with_capacity(50),
            calibrated_confidence: 0.5,
        }
    }

    fn record_pattern_accuracy(&mut self, accuracy: f32) {
        self.pattern_accuracy_history.push_back(accuracy);
        if self.pattern_accuracy_history.len() > 50 {
            self.pattern_accuracy_history.pop_front();
        }

        // Calibrate based on history
        let avg: f32 = self.pattern_accuracy_history.iter().sum::<f32>()
            / self.pattern_accuracy_history.len().max(1) as f32;
        self.calibrated_confidence = avg;
    }
}

/// Chaos Dragon - a dragon that eats bad decisions
#[derive(Clone, Debug, Default)]
struct ChaosDragon {
    hunger: f32,          // How hungry the dragon is
    decisions_eaten: u32, // How many bad decisions were sacrificed
    dragon_mood: f32,     // Dragon mood affects decisions
    last_sacrifice: u32,  // Bets since last sacrifice
}

impl ChaosDragon {
    fn new() -> Self {
        Self {
            hunger: 0.5,
            decisions_eaten: 0,
            dragon_mood: 0.5,
            last_sacrifice: 0,
        }
    }

    fn update(&mut self, total_bets: usize, was_loss: bool) {
        self.hunger = (self.hunger + 0.02).min(1.0);
        self.last_sacrifice += 1;

        if was_loss && self.hunger > 0.7 {
            // Dragon ate a bad decision
            self.decisions_eaten += 1;
            self.hunger = 0.2;
            self.dragon_mood = (self.dragon_mood + 0.1).min(1.0);
            self.last_sacrifice = 0;
        }

        // Dragon gets grumpy if not fed
        if self.last_sacrifice > 20 {
            self.dragon_mood = (self.dragon_mood - 0.05).max(0.0);
        }
    }

    fn get_dragon_vote(&mut self, rng_value: f32) -> (f32, bool) {
        // A hungry dragon demands sacrifice - sometimes forces a random direction
        if self.hunger > 0.9 {
            self.hunger = 0.5;
            return (0.25, rng_value > 0.5);
        }
        (0.0, false)
    }
}

/// Divine Intervention - 0.01% chance of divine guidance
#[derive(Clone, Debug, Default)]
struct DivineIntervention {
    interventions_received: u32,
    miracles_witnessed: u32,
    blessing_active: bool,
    last_blessing: u32,
}

impl DivineIntervention {
    fn new() -> Self {
        Self {
            interventions_received: 0,
            miracles_witnessed: 0,
            blessing_active: false,
            last_blessing: 0,
        }
    }

    fn check_for_divine_guidance(&mut self, rng_value: f32, total_bets: usize) -> Option<bool> {
        // 0.01% chance of divine intervention
        if rng_value < 0.0001 {
            self.interventions_received += 1;
            self.blessing_active = true;
            self.last_blessing = total_bets as u32;
            return Some(rng_value > 0.5); // Divine answer
        }

        // Blessing wears off after 10 bets
        if self.blessing_active && total_bets as u32 - self.last_blessing > 10 {
            self.blessing_active = false;
        }

        None
    }

    fn record_miracle(&mut self) {
        self.miracles_witnessed += 1;
    }
}

/// Conspiracy detector - detect if the game is rigged against us
#[derive(Clone, Debug, Default)]
struct ConspiracyDetector {
    paranoid_level: f32, // Changed to match the method naming
    suspicious_losses: u32,
    suspicious_patterns: VecDeque<String>,
    detected_conspiracy: bool,
}

impl ConspiracyDetector {
    fn new() -> Self {
        Self {
            paranoid_level: 0.0,
            suspicious_losses: 0,
            suspicious_patterns: VecDeque::with_capacity(20),
            detected_conspiracy: false,
        }
    }

    fn update(&mut self, loss_streak: u32, roll: u32, expected_high: bool) {
        // Detect suspicious patterns
        if loss_streak > 5 {
            self.paranoid("Long loss streak".to_string());
        }

        // Suspicious if we lose by 1 number
        if (expected_high && roll == 4999) || (!expected_high && roll == 5001) {
            self.paranoid("Loss by 1 number - suspicious!".to_string());
        }

        // Gradually calm down
        self.paranoid_level *= 0.98;
    }

    fn paranoid(&mut self, reason: String) {
        self.paranoid_level = (self.paranoid_level + 0.1).min(1.0);
        self.suspicious_patterns.push_back(reason);
        if self.suspicious_patterns.len() > 20 {
            self.suspicious_patterns.pop_front();
        }
    }

    fn get_paranoia_modifier(&self) -> f32 {
        // High paranoia = bet less confidently
        1.0 - self.paranoid_level * 0.3
    }
}

/// Schrödinger's Cat - simultaneously winning and losing until observed
#[derive(Clone, Debug, Default)]
struct SchrodingerCat {
    alive_probability: f32,
    observation_count: u32,
    cat_state: CatState,
}

#[derive(Clone, Debug, Default)]
enum CatState {
    #[default]
    Alive,
    Dead,
    Superposition,
}

impl SchrodingerCat {
    fn new() -> Self {
        Self {
            alive_probability: 0.5,
            observation_count: 0,
            cat_state: CatState::Superposition,
        }
    }

    fn observe(&mut self, is_win: bool) {
        self.observation_count += 1;
        self.cat_state = if is_win {
            CatState::Alive
        } else {
            CatState::Dead
        };

        // Update probability
        self.alive_probability = self.alive_probability * 0.9 + if is_win { 0.1 } else { 0.0 };

        // Collapse back to superposition after observation
        // (the cat is always in superposition until the next bet)
    }

    fn get_quantum_vote(&self) -> (f32, bool) {
        // In superposition, bet based on probability
        match self.cat_state {
            CatState::Superposition => {
                let vote = 0.1; // Weak quantum vote
                (vote, self.alive_probability > 0.5)
            }
            CatState::Alive => (0.15, true), // Cat is alive = bet HIGH
            CatState::Dead => (0.15, false), // Cat is dead = bet LOW
        }
    }
}

// ============================================================================
// EVEN MORE ABSURDLY UNNECESSARY FEATURES
// ============================================================================

/// Karma Calculator - tracks if the universe owes us
#[derive(Clone, Debug, Default)]
struct KarmaCalculator {
    good_deeds: f32,           // Times we "deserved" to win (but didn't)
    bad_deeds: f32,            // Times we got lucky (didn't deserve it)
    karma_balance: f32,        // Net karma (-1 to 1)
    universe_debt: f32,        // How much the universe owes us
    instant_karma_events: u32, // Immediate karma payback
}

impl KarmaCalculator {
    fn new() -> Self {
        Self {
            good_deeds: 0.0,
            bad_deeds: 0.0,
            karma_balance: 0.0,
            universe_debt: 0.0,
            instant_karma_events: 0,
        }
    }

    fn record_bet(&mut self, was_responsible: bool, won: bool, confidence: f32) {
        // Responsible betting that lost = universe owes us
        // Irresponsible betting that won = we owe the universe
        if was_responsible && !won {
            self.good_deeds += 1.0;
            self.universe_debt += confidence;
        } else if !was_responsible && won {
            self.bad_deeds += 1.0;
            self.universe_debt -= confidence * 0.5;
        } else if was_responsible && won {
            // Justified win
            self.good_deeds += 0.5;
        } else {
            // Irresponsible loss - instant karma
            self.bad_deeds += 0.5;
            self.instant_karma_events += 1;
        }

        self.karma_balance =
            (self.good_deeds - self.bad_deeds) / (self.good_deeds + self.bad_deeds + 1.0);
        self.universe_debt = self.universe_debt.clamp(-5.0, 5.0);
    }

    fn get_karma_vote(&self) -> (f32, bool) {
        // If universe owes us, bet with confidence
        // If we owe universe, bet cautiously
        let vote = self.universe_debt.abs() * 0.05;
        (vote, self.universe_debt > 0.0)
    }

    fn get_karma_modifier(&self) -> f32 {
        // Modify bet size based on karma
        1.0 + self.karma_balance * 0.1
    }
}

/// Butterfly Effect Tracker - small decisions cascade into big outcomes
#[derive(Clone, Debug, Default)]
struct ButterflyEffectTracker {
    wing_flaps: VecDeque<ButterflyWing>, // Small decisions made
    detected_cascades: u32,              // Times we detected a cascade
    cascade_strength: f32,               // Current cascade power
}

#[derive(Clone, Debug)]
struct ButterflyWing {
    bet_number: usize,
    minor_decision: String, // What small thing we did
    potential_impact: f32,  // How much it could matter
}

impl ButterflyEffectTracker {
    fn new() -> Self {
        Self {
            wing_flaps: VecDeque::with_capacity(50),
            detected_cascades: 0,
            cascade_strength: 0.0,
        }
    }

    fn record_minor_decision(&mut self, bet_number: usize, decision: &str, impact: f32) {
        self.wing_flaps.push_back(ButterflyWing {
            bet_number,
            minor_decision: decision.to_string(),
            potential_impact: impact,
        });

        if self.wing_flaps.len() > 50 {
            self.wing_flaps.pop_front();
        }
    }

    fn check_cascade(&mut self, result_changed_pattern: bool) {
        if result_changed_pattern && self.wing_flaps.len() > 5 {
            self.detected_cascades += 1;
            self.cascade_strength = (self.cascade_strength + 0.1).min(1.0);
        }
    }

    fn get_cascade_vote(&self) -> f32 {
        // When cascades are detected, trust chaos more
        self.cascade_strength * 0.1
    }
}

/// Pattern Cult Detector - are we joining a cult of false patterns?
#[derive(Clone, Debug, Default)]
struct PatternCultDetector {
    patterns_believed: u32,
    patterns_disproven: u32,
    cult_membership_level: f32, // How deep in the cult we are
    reality_check_counter: u32, // Times reality snapped us out
    sacred_numbers: Vec<u32>,   // Numbers we irrationally believe in
}

impl PatternCultDetector {
    fn new() -> Self {
        Self {
            patterns_believed: 0,
            patterns_disproven: 0,
            cult_membership_level: 0.0,
            reality_check_counter: 0,
            sacred_numbers: vec![7, 42, 777, 666, 333], // Start with some "sacred" numbers
        }
    }

    fn observe_roll(&mut self, roll: u32, expected_pattern: bool, pattern_held: bool) {
        if expected_pattern && !pattern_held {
            // Pattern failed - reality check
            self.patterns_disproven += 1;
            self.reality_check_counter += 1;
            self.cult_membership_level = (self.cult_membership_level - 0.1).max(0.0);
            if self.sacred_numbers.contains(&roll) {
                // Sacred number broke the pattern
                self.sacred_numbers.retain(|&n| n != roll);
            }
        } else if expected_pattern && pattern_held {
            // Pattern held - cult grows
            self.patterns_believed += 1;
            self.cult_membership_level = (self.cult_membership_level + 0.05).min(1.0);
            if !self.sacred_numbers.contains(&roll) {
                // Add to sacred numbers
                self.sacred_numbers.push(roll);
                if self.sacred_numbers.len() > 10 {
                    self.sacred_numbers.remove(0);
                }
            }
        }
    }

    fn check_sacred_number(&self, roll: u32) -> (f32, bool) {
        // Sacred numbers get a tiny vote
        if self.sacred_numbers.contains(&roll) {
            return (0.02 * self.cult_membership_level, true);
        }
        (0.0, false)
    }

    fn get_cult_vote(&self) -> (f32, bool, bool) {
        // (vote, direction, is_cult_thinking)
        if self.cult_membership_level > 0.5 {
            (self.cult_membership_level * 0.1, true, true)
        } else {
            (0.0, false, false)
        }
    }
}

/// Quantum Entanglement - entangle our outcomes with hypothetical other gamblers
#[derive(Clone, Debug, Default)]
struct QuantumEntanglement {
    entangled_states: Vec<EntangledGambler>,
    coherence: f32,           // How coherent our entanglement is
    spooky_action_count: u32, // Times we detected "spooky action at a distance"
}

#[derive(Clone, Debug)]
struct EntangledGambler {
    id: usize,
    opposite_state: bool, // If we win, they "lose" (and vice versa)
    entanglement_strength: f32,
}

impl QuantumEntanglement {
    fn new() -> Self {
        // Create 3 hypothetical entangled gamblers
        let entangled = (0..3)
            .map(|i| EntangledGambler {
                id: i,
                opposite_state: i % 2 == 0, // Alternate states
                entanglement_strength: 0.5,
            })
            .collect();

        Self {
            entangled_states: entangled,
            coherence: 1.0,
            spooky_action_count: 0,
        }
    }

    fn observe_outcome(&mut self, we_won: bool) {
        // Collapse entangled states
        for gambler in &mut self.entangled_states {
            if gambler.opposite_state {
                // Our win is their loss
                // Did spooky action happen? (randomly detect)
                if rand::rng().random::<f32>() < 0.01 {
                    self.spooky_action_count += 1;
                }
            }
            // Decoherence
            gambler.entanglement_strength *= 0.99;
        }

        self.coherence *= 0.995;
        if self.coherence < 0.1 {
            // Re-entangle
            self.coherence = 1.0;
            for gambler in &mut self.entangled_states {
                gambler.entanglement_strength = 0.5;
                gambler.opposite_state = rand::rng().random::<f32>() > 0.5;
            }
        }
    }

    fn get_entanglement_vote(&self) -> (f32, bool) {
        // Vote based on entangled states' collective influence
        let total_strength: f32 = self
            .entangled_states
            .iter()
            .map(|g| g.entanglement_strength)
            .sum();
        let net_opposite: f32 = self
            .entangled_states
            .iter()
            .filter(|g| g.opposite_state)
            .map(|g| g.entanglement_strength)
            .sum();

        let vote = total_strength * self.coherence * 0.02;
        let high = net_opposite < total_strength / 2.0;
        (vote, high)
    }
}

/// Philosophical Uncertainty - questions the nature of randomness itself
#[derive(Clone, Debug, Default)]
struct PhilosophicalUncertainty {
    philosophical_doubt: f32,   // How much we question everything
    free_will_belief: f32,      // Do we have free will in betting?
    determinism_score: f32,     // Is everything predetermined?
    existential_crises: u32,    // Number of philosophical breakdowns
    enlightenment_moments: u32, // Brief clarity
}

impl PhilosophicalUncertainty {
    fn new() -> Self {
        Self {
            philosophical_doubt: 0.5,
            free_will_belief: 0.5,
            determinism_score: 0.5,
            existential_crises: 0,
            enlightenment_moments: 0,
        }
    }

    fn contemplate(&mut self, loss_streak: u32, win_streak: u32, total_bets: usize) {
        // Long streaks increase determinism belief
        if loss_streak > 5 || win_streak > 5 {
            self.determinism_score = (self.determinism_score + 0.05).min(1.0);
            self.free_will_belief = (self.free_will_belief - 0.05).max(0.0);
        }

        // Random events restore free will belief
        if total_bets % 50 == 0 {
            self.philosophical_doubt = rand::rng().random::<f32>();
        }

        // Existential crisis on big loss streaks
        if loss_streak > 8 {
            self.existential_crises += 1;
            self.philosophical_doubt = 0.9;
        }

        // Enlightenment on perfect balance
        let balance = (win_streak as i32 - loss_streak as i32).abs();
        if balance == 0 && win_streak > 0 {
            self.enlightenment_moments += 1;
            self.philosophical_doubt = 0.1;
        }
    }

    fn get_philosophical_vote(&self) -> (f32, bool, String) {
        // Returns vote, direction, and philosophical stance
        if self.philosophical_doubt > 0.8 {
            (
                0.1,
                rand::rng().random::<f32>() > 0.5,
                "All is chaos".to_string(),
            )
        } else if self.determinism_score > 0.7 {
            (0.05, true, "It is written".to_string())
        } else if self.free_will_belief > 0.7 {
            (0.08, false, "I choose... LOW".to_string())
        } else {
            (0.02, true, "Who knows?".to_string())
        }
    }
}

/// Akashic Record Reader - reads the "cosmic record" of all bets
#[derive(Clone, Debug, Default)]
struct AkashicRecordReader {
    cosmic_memory: VecDeque<CosmicBetRecord>,
    connection_strength: f32,
    downloads_from_akashic: u32,
    cosmic_insights: Vec<String>,
}

#[derive(Clone, Debug)]
struct CosmicBetRecord {
    cosmic_id: usize,
    outcome: bool,
    cosmic_significance: f32,
}

impl AkashicRecordReader {
    fn new() -> Self {
        Self {
            cosmic_memory: VecDeque::with_capacity(100),
            connection_strength: 0.5,
            downloads_from_akashic: 0,
            cosmic_insights: vec![
                "The house always wins... eventually".to_string(),
                "Past performance does not predict future results".to_string(),
                "The dice have no memory".to_string(),
            ],
        }
    }

    fn attempt_download(&mut self, rng: f32) -> Option<String> {
        // 0.1% chance to "download" cosmic insight
        if rng < 0.001 && self.connection_strength > 0.3 {
            self.downloads_from_akashic += 1;
            let insights = vec![
                "The cosmic dice favor balance".to_string(),
                "Chaos brings order, order brings chaos".to_string(),
                "The 47th bet holds secrets".to_string(),
                "Beware the ides of the session".to_string(),
                "Fortune favors the... random".to_string(),
            ];
            let insight = insights[rng as usize % insights.len()].clone();
            self.cosmic_insights.push(insight.clone());
            Some(insight)
        } else {
            None
        }
    }

    fn get_cosmic_vote(&self) -> (f32, bool) {
        (
            self.connection_strength * 0.03,
            self.downloads_from_akashic % 2 == 0,
        )
    }
}

/// Retrocausality Engine - future affects past
#[derive(Clone, Debug, Default)]
struct RetrocausalityEngine {
    future_knowledge: VecDeque<FutureEcho>,
    temporal_paradoxes: u32,
    causality_violations: f32,
}

#[derive(Clone, Debug)]
struct FutureEcho {
    predicted_bet: usize,
    actual_outcome: bool,
    confidence: f32,
    was_correct: bool,
}

impl RetrocausalityEngine {
    fn new() -> Self {
        Self {
            future_knowledge: VecDeque::with_capacity(20),
            temporal_paradoxes: 0,
            causality_violations: 0.0,
        }
    }

    fn receive_future_echo(&mut self, current_bet: usize, outcome: bool, confidence: f32) {
        // "Receive" information from the future
        // (In reality, we're just storing predictions we'll verify later)
        self.future_knowledge.push_back(FutureEcho {
            predicted_bet: current_bet + 5, // Predict 5 bets ahead
            actual_outcome: outcome,
            confidence,
            was_correct: false,
        });

        if self.future_knowledge.len() > 20 {
            self.future_knowledge.pop_front();
        }
    }

    fn verify_temporal_consistency(&mut self, current_bet: usize, actual_outcome: bool) {
        for echo in &mut self.future_knowledge {
            if echo.predicted_bet == current_bet && !echo.was_correct {
                // Check if our "future knowledge" was right
                echo.was_correct = echo.actual_outcome == actual_outcome;
                if !echo.was_correct {
                    self.temporal_paradoxes += 1;
                    self.causality_violations += 0.1;
                }
            }
        }
        self.causality_violations *= 0.95; // Decay
    }

    fn get_temporal_vote(&self) -> (f32, bool) {
        // Vote based on "future knowledge"
        if let Some(echo) = self.future_knowledge.back() {
            let vote = echo.confidence * 0.05 * (1.0 - self.causality_violations);
            (vote, echo.actual_outcome)
        } else {
            (0.0, false)
        }
    }
}

/// Probability Manipulator - attempts to influence probability through sheer will
#[derive(Clone, Debug, Default)]
struct ProbabilityManipulator {
    manipulation_attempts: u32,
    successful_manipulations: u32,
    belief_power: f32,         // How strongly we believe we can influence
    reality_pushback: f32,     // How much reality pushes back
    manifestation_energy: f32, // Accumulated manifestation energy
}

impl ProbabilityManipulator {
    fn new() -> Self {
        Self {
            manipulation_attempts: 0,
            successful_manipulations: 0,
            belief_power: 0.5,
            reality_pushback: 0.0,
            manifestation_energy: 0.0,
        }
    }

    fn attempt_manipulation(
        &mut self,
        desired_outcome: bool,
        actual_outcome: bool,
        confidence: f32,
    ) {
        self.manipulation_attempts += 1;

        if desired_outcome == actual_outcome {
            self.successful_manipulations += 1;
            self.belief_power = (self.belief_power + 0.02).min(1.0);
            self.manifestation_energy += confidence * 0.1;
        } else {
            self.reality_pushback = (self.reality_pushback + 0.05).min(1.0);
            self.belief_power = (self.belief_power - 0.01).max(0.0);
            self.manifestation_energy *= 0.5;
        }

        // Reality always wins eventually
        self.reality_pushback *= 0.98;
        self.manifestation_energy *= 0.99;
    }

    fn get_manipulation_vote(&mut self, rng: f32) -> (f32, bool) {
        // High belief + energy = try to "manifest"
        if self.belief_power > 0.7 && self.manifestation_energy > 1.0 && rng < 0.05 {
            // "Manifest" a vote
            let vote = self.manifestation_energy * 0.1;
            self.manifestation_energy = 0.0; // Used up
            return (vote, true);
        }
        (0.0, false)
    }
}

/// Casino Psychology Model - models the casino's mind games
#[derive(Clone, Debug, Default)]
struct CasinoPsychologyModel {
    detected_techniques: Vec<String>,
    resistance_level: f32,
    times_fooled: u32,
    times_resisted: u32,
    casino_persona: CasinoPersona,
}

#[derive(Clone, Debug, Default)]
enum CasinoPersona {
    #[default]
    Friendly, // Small wins, big losses
    Aggressive, // Quick losses
    Patient,    // Long winning streaks, then crash
    Deceptive,  // Mixed signals
}

impl CasinoPsychologyModel {
    fn new() -> Self {
        Self {
            detected_techniques: vec![
                "Near miss effect".to_string(),
                "Loss disguised as win".to_string(),
                "The entrapment".to_string(),
            ],
            resistance_level: 0.5,
            times_fooled: 0,
            times_resisted: 0,
            casino_persona: CasinoPersona::Friendly,
        }
    }

    fn analyze_casino_behavior(&mut self, win_streak: u32, loss_streak: u32, near_miss: bool) {
        // Detect casino persona
        if win_streak > 5 && loss_streak == 0 {
            self.casino_persona = CasinoPersona::Patient;
        } else if loss_streak > 5 && win_streak == 0 {
            self.casino_persona = CasinoPersona::Aggressive;
        } else if near_miss {
            self.casino_persona = CasinoPersona::Deceptive;
            self.detected_techniques
                .push("Near miss detected".to_string());
        }

        // Adjust resistance
        self.resistance_level = (self.resistance_level + 0.01).min(1.0);
    }

    fn get_counter_psychology_vote(&self) -> (f32, bool) {
        // Vote opposite to what casino "wants"
        match self.casino_persona {
            CasinoPersona::Friendly => (0.05, false), // They're being too nice
            CasinoPersona::Aggressive => (0.08, true), // Fight back
            CasinoPersona::Patient => (0.03, false),  // Don't fall for long con
            CasinoPersona::Deceptive => (0.1, rand::rng().random::<f32>() > 0.5), // Be unpredictable
        }
    }
}

/// Luck Bank - stores and dispenses luck
#[derive(Clone, Debug, Default)]
struct LuckBank {
    luck_balance: f32,      // Current luck in bank
    interest_rate: f32,     // Luck compounds
    withdrawals: u32,       // Times we used stored luck
    deposits: u32,          // Times we "banked" luck
    is_overdrawn: bool,     // Used more luck than we had
    luck_credit_score: f32, // How good is our luck credit?
}

impl LuckBank {
    fn new() -> Self {
        Self {
            luck_balance: 1.0, // Start with some luck
            interest_rate: 0.001,
            withdrawals: 0,
            deposits: 0,
            is_overdrawn: false,
            luck_credit_score: 500.0, // Like a real credit score
        }
    }

    fn deposit_luck(&mut self, was_lucky_win: bool, confidence: f32) {
        if was_lucky_win {
            // We got lucky - deposit some luck back
            self.luck_balance += confidence * 0.1;
            self.deposits += 1;
        }
        // Interest
        self.luck_balance *= 1.0 + self.interest_rate;
        self.luck_balance = self.luck_balance.min(10.0); // Cap luck
    }

    fn withdraw_luck(&mut self, need_luck: bool) -> f32 {
        if need_luck && self.luck_balance > 0.0 {
            self.withdrawals += 1;
            let withdrawal = self.luck_balance * 0.1;
            self.luck_balance -= withdrawal;

            if self.luck_balance < 0.0 {
                self.is_overdrawn = true;
                self.luck_credit_score -= 10.0;
            }

            withdrawal
        } else {
            0.0
        }
    }

    fn get_luck_vote(&self) -> (f32, bool) {
        // High luck balance = bet confidently
        // Overdrawn = bet cautiously
        let vote = if self.is_overdrawn {
            0.02 // Minimal vote when overdrawn
        } else {
            self.luck_balance * 0.02
        };
        (vote, self.luck_balance > 0.5)
    }
}

/// Meta-learner that learns optimal model combinations
#[derive(Clone, Debug)]
struct ModelMetaLearner {
    // Model combination performance tracking
    combination_history: VecDeque<CombinationResult>,

    // Best performing model subsets by regime
    best_for_trending: Vec<usize>,
    best_for_volatile: Vec<usize>,
    best_for_recovery: Vec<usize>,
    best_for_stable: Vec<usize>,

    // Learning rate for updating weights
    learning_rate: f32,

    // Performance baseline (random = ~0.475 for 2x)
    baseline_accuracy: f32,
}

#[derive(Clone, Debug)]
struct CombinationResult {
    model_ids: Vec<usize>,
    combined_weight: f32,
    was_correct: bool,
    regime: ModelRegimeState,
    confidence: f32,
}

/// Track performance of individual voting components
#[derive(Clone, Debug)]
struct ComponentPerformance {
    // Component identification
    name: String,
    component_type: ComponentType,

    // Session tracking (rolling window)
    predictions: VecDeque<bool>, // Last N predictions (true = correct)
    votes: VecDeque<f32>,        // Vote weights used
    confidence_scores: VecDeque<f32>, // Confidence when voting

    // Aggregated stats
    total_predictions: u32,
    total_correct: u32,
    total_votes_cast: f32,

    // Recent performance (last 20, 50, 100)
    recent_accuracy_20: f32,
    recent_accuracy_50: f32,
    recent_accuracy_100: f32,

    // Weight adjustment
    base_weight: f32,
    current_weight: f32,
    weight_adjustment: f32,
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum ComponentType {
    // Smart Direction
    DirectionMomentum,
    AntiStreak,
    TrendFollow,
    RollAnalysis,
    DirectionStreak,

    // ML Models (0-24)
    ModelDQN,
    ModelPolicyGradient,
    ModelQLearning,
    ModelLSTM,
    ModelAttention,
    ModelMarkov,
    ModelPattern,
    ModelContrastive,
    ModelKalman,
    ModelGaussian,
    ModelTransformer,
    ModelVAE,
    ModelNTM,
    ModelHawkes,
    ModelHurst,
    ModelEntropy,
    ModelTransferEntropy,
    ModelCategoricalDQN,
    ModelGPThompson,
    ModelQuantum,
    ModelMetaRL,
    ModelPBT,
    ModelOU,
    ModelTCN,
    ModelMCTS,

    // Experimental
    HotColdRanges,
    PrimeNumbers,
    FibonacciPattern,
    GoldenRatio,
    LuckyNumbers,
    BirthdayParadox,
    PsychicMoments,
    ModuloPattern,
    ChaosIndicator,
    AlternatingPattern,
    RunLength,
    MagicNumbers,
}

impl ComponentPerformance {
    fn new(name: &str, component_type: ComponentType, base_weight: f32) -> Self {
        Self {
            name: name.to_string(),
            component_type,
            predictions: VecDeque::with_capacity(100),
            votes: VecDeque::with_capacity(100),
            confidence_scores: VecDeque::with_capacity(100),
            total_predictions: 0,
            total_correct: 0,
            total_votes_cast: 0.0,
            recent_accuracy_20: 0.5,
            recent_accuracy_50: 0.5,
            recent_accuracy_100: 0.5,
            base_weight,
            current_weight: base_weight,
            weight_adjustment: 1.0,
        }
    }

    /// Record a prediction and update stats
    fn record_prediction(&mut self, was_correct: bool, vote_weight: f32, confidence: f32) {
        self.predictions.push_back(was_correct);
        self.votes.push_back(vote_weight);
        self.confidence_scores.push_back(confidence);

        self.total_predictions += 1;
        if was_correct {
            self.total_correct += 1;
        }
        self.total_votes_cast += vote_weight;

        // Maintain window
        if self.predictions.len() > 100 {
            self.predictions.pop_front();
            self.votes.pop_front();
            self.confidence_scores.pop_front();
        }

        // Update recent accuracies
        self.update_accuracies();

        // Adjust weight based on performance
        self.adjust_weight();
    }

    fn update_accuracies(&mut self) {
        let n = self.predictions.len();

        // Last 20
        if n >= 20 {
            let correct = self
                .predictions
                .iter()
                .rev()
                .take(20)
                .filter(|&&x| x)
                .count() as u32;
            self.recent_accuracy_20 = correct as f32 / 20.0;
        }

        // Last 50
        if n >= 50 {
            let correct = self
                .predictions
                .iter()
                .rev()
                .take(50)
                .filter(|&&x| x)
                .count() as u32;
            self.recent_accuracy_50 = correct as f32 / 50.0;
        }

        // Last 100
        if n >= 100 {
            let correct = self
                .predictions
                .iter()
                .rev()
                .take(100)
                .filter(|&&x| x)
                .count() as u32;
            self.recent_accuracy_100 = correct as f32 / 100.0;
        }
    }

    fn adjust_weight(&mut self) {
        // Only adjust after 10 predictions
        if self.total_predictions < 10 {
            return;
        }

        // Use weighted combination of recent accuracies
        let accuracy = if self.predictions.len() >= 50 {
            // Weight recent more heavily
            self.recent_accuracy_20 * 0.5
                + self.recent_accuracy_50 * 0.3
                + self.recent_accuracy_100 * 0.2
        } else if self.predictions.len() >= 20 {
            self.recent_accuracy_20 * 0.7
                + (self.total_correct as f32 / self.total_predictions as f32) * 0.3
        } else {
            self.total_correct as f32 / self.total_predictions as f32
        };

        // Baseline is 47.5% (house edge on 2x)
        let baseline = 0.475;

        // Calculate confidence-weighted accuracy
        // Components that are confident AND right should be trusted more
        let avg_confidence = if self.confidence_scores.len() > 10 {
            self.confidence_scores.iter().rev().take(20).sum::<f32>() / 20.0
        } else {
            0.5
        };

        // Confidence-weighted performance
        let confidence_weighted_accuracy = if avg_confidence > 0.6 {
            // High confidence predictions matter more
            accuracy * (1.0 + (avg_confidence - 0.5) * 0.5)
        } else {
            accuracy
        };

        // Momentum - how fast should weights change?
        // Learn faster when we're wrong, slower when we're right
        let recent_predictions: Vec<bool> =
            self.predictions.iter().rev().take(10).copied().collect();
        let recent_correct = recent_predictions.iter().filter(|&&x| x).count();
        let recent_accuracy_trend = recent_correct as f32 / recent_predictions.len().max(1) as f32;

        // Momentum: if recent accuracy is improving, change weights faster
        let momentum = if self.predictions.len() >= 30 {
            let mid_accuracy = self
                .predictions
                .iter()
                .rev()
                .take(20)
                .take(10)
                .filter(|&&x| x)
                .count() as f32
                / 10.0;
            let old_accuracy = self
                .predictions
                .iter()
                .rev()
                .skip(20)
                .take(10)
                .filter(|&&x| x)
                .count() as f32
                / 10.0;
            (mid_accuracy - old_accuracy) * 2.0 // Trend direction
        } else {
            0.0
        };

        // Calculate weight adjustment
        // Above baseline: increase weight, Below baseline: decrease weight
        if confidence_weighted_accuracy > baseline + 0.05 {
            // Performing well: increase weight up to 3x
            let boost = (confidence_weighted_accuracy - baseline) * 4.0;
            let momentum_bonus = momentum.max(0.0) * 0.5; // Extra boost if improving
            self.weight_adjustment = 1.0 + boost + momentum_bonus;
            self.weight_adjustment = self.weight_adjustment.min(3.0);
        } else if confidence_weighted_accuracy < baseline - 0.05 {
            // Performing poorly: decrease weight more aggressively
            // Learn faster from mistakes
            let penalty = (baseline - confidence_weighted_accuracy) * 4.0;
            let momentum_penalty = momentum.min(0.0).abs() * 0.3; // Extra penalty if declining
            self.weight_adjustment = (baseline - penalty - momentum_penalty) / baseline;
            self.weight_adjustment = self.weight_adjustment.max(0.1);
        } else {
            // Near baseline: gradual adjustment
            self.weight_adjustment = 0.8 + (confidence_weighted_accuracy / baseline) * 0.4;
        }

        // Apply adjustment to current weight
        // Smooth transition: blend old and new weight
        let target_weight = self.base_weight * self.weight_adjustment;
        self.current_weight = self.current_weight * 0.7 + target_weight * 0.3;
    }

    /// Get weight adjusted for current game state
    fn get_context_weight(
        &self,
        win_streak: u32,
        loss_streak: u32,
        drawdown: f32,
        confidence: f32,
    ) -> f32 {
        let base = self.current_weight;

        // Context multipliers
        let mut multiplier = 1.0;

        // Win streak bonus - trust components more when hot
        if win_streak >= 5 {
            multiplier *= 1.15;
        } else if win_streak >= 3 {
            multiplier *= 1.08;
        }

        // Loss streak penalty - trust components less when cold
        // BUT only if component has been performing poorly
        if loss_streak >= 4 && self.recent_accuracy_20 < 0.45 {
            multiplier *= 0.8;
        } else if loss_streak >= 6 && self.recent_accuracy_20 < 0.50 {
            multiplier *= 0.9;
        }

        // Drawdown adjustment
        if drawdown > 0.3 {
            // Deep drawdown - trust proven components more
            if self.recent_accuracy_50 > 0.52 {
                multiplier *= 1.1;
            } else if self.recent_accuracy_50 < 0.42 {
                multiplier *= 0.85;
            }
        } else if drawdown > 0.2 {
            // Moderate drawdown
            if self.recent_accuracy_50 > 0.50 {
                multiplier *= 1.05;
            }
        }

        // High confidence boost
        if confidence > 0.75 && self.recent_accuracy_20 > 0.50 {
            multiplier *= 1.05;
        }

        // Very poor recent performance - reduce weight significantly
        if self.recent_accuracy_20 < 0.35 {
            multiplier *= 0.5;
        } else if self.recent_accuracy_20 < 0.42 {
            multiplier *= 0.75;
        }

        // Excellent recent performance - boost weight
        if self.recent_accuracy_20 > 0.60 {
            multiplier *= 1.2;
        } else if self.recent_accuracy_20 > 0.55 {
            multiplier *= 1.1;
        }

        base * multiplier
    }

    /// Get the current weight for this component
    fn get_weight(&self) -> f32 {
        self.current_weight
    }

    /// Get performance summary
    fn summary(&self) -> String {
        format!(
            "{}: acc={:.1}% (20:{:.1}% 50:{:.1}% 100:{:.1}%) weight={:.2}x",
            self.name,
            self.total_correct as f32 / self.total_predictions.max(1) as f32 * 100.0,
            self.recent_accuracy_20 * 100.0,
            self.recent_accuracy_50 * 100.0,
            self.recent_accuracy_100 * 100.0,
            self.weight_adjustment
        )
    }
}

/// A pending vote that needs to be evaluated after result is known
#[derive(Clone, Debug)]
struct PendingVote {
    component_name: String,
    voted_high: bool,
    vote_amount: f32,
    confidence: f32,
}

/// Performance tracker for all voting components
#[derive(Clone, Debug)]
struct VotingPerformanceTracker {
    components: std::collections::HashMap<String, ComponentPerformance>,
    // Pending votes from the current betting round
    pending_votes: Vec<PendingVote>,
    total_high_votes: f32,
    total_low_votes: f32,
    // Historical direction tracking for bias correction
    cumulative_high_votes: f32,
    cumulative_low_votes: f32,
    direction_correct_predictions: u32, // Times direction prediction was correct
    total_direction_predictions: u32,
}

impl VotingPerformanceTracker {
    fn new() -> Self {
        let mut tracker = Self {
            components: std::collections::HashMap::new(),
            pending_votes: Vec::with_capacity(50),
            total_high_votes: 0.0,
            total_low_votes: 0.0,
            cumulative_high_votes: 0.0,
            cumulative_low_votes: 0.0,
            direction_correct_predictions: 0,
            total_direction_predictions: 0,
        };

        // Initialize all components with their base weights
        tracker.init_components();
        tracker
    }

    fn init_components(&mut self) {
        // Smart Direction components
        self.add("direction_momentum", ComponentType::DirectionMomentum, 4.0);
        self.add("anti_streak", ComponentType::AntiStreak, 1.5);
        self.add("trend_follow", ComponentType::TrendFollow, 2.5);
        self.add("roll_analysis", ComponentType::RollAnalysis, 2.0);
        self.add("direction_streak", ComponentType::DirectionStreak, 3.0);

        // ML Models (25) - HIGHER WEIGHTS - Core models should dominate
        // Core RL Models
        self.add("dqn", ComponentType::ModelDQN, 3.0);
        self.add("policy_gradient", ComponentType::ModelPolicyGradient, 2.5);
        self.add("q_learning", ComponentType::ModelQLearning, 2.5);

        // Sequence Models (learn patterns from roll history)
        self.add("lstm", ComponentType::ModelLSTM, 3.5);
        self.add("attention", ComponentType::ModelAttention, 3.5);
        self.add("transformer", ComponentType::ModelTransformer, 3.0);
        self.add("tcn", ComponentType::ModelTCN, 2.5);

        // Pattern/Learning Models
        self.add("markov", ComponentType::ModelMarkov, 2.0);
        self.add("pattern", ComponentType::ModelPattern, 2.5);
        self.add("contrastive", ComponentType::ModelContrastive, 2.0);

        // Bayesian/Probabilistic Models
        self.add("kalman", ComponentType::ModelKalman, 2.0);
        self.add("gaussian", ComponentType::ModelGaussian, 2.5);
        self.add("gp_thompson", ComponentType::ModelGPThompson, 2.0);

        // Advanced Neural Models
        self.add("vae", ComponentType::ModelVAE, 1.5);
        self.add("ntm", ComponentType::ModelNTM, 1.5);
        self.add("categorical_dqn", ComponentType::ModelCategoricalDQN, 2.5);
        self.add("meta_rl", ComponentType::ModelMetaRL, 2.5);

        // Statistical/Hybrid Models
        self.add("hawkes", ComponentType::ModelHawkes, 1.0);
        self.add("hurst", ComponentType::ModelHurst, 1.5);
        self.add("entropy", ComponentType::ModelEntropy, 1.5);
        self.add("transfer_entropy", ComponentType::ModelTransferEntropy, 2.0);

        // Experimental/Bandit Models
        self.add("quantum", ComponentType::ModelQuantum, 1.0);
        self.add("pbt", ComponentType::ModelPBT, 1.5);
        self.add("ou", ComponentType::ModelOU, 1.0);
        self.add("mcts", ComponentType::ModelMCTS, 1.5);
        self.add("exp3", ComponentType::ModelMCTS, 1.0);

        // Experimental (lower base weights - fun/novelty)
        self.add("hot_cold", ComponentType::HotColdRanges, 0.4);
        self.add("primes", ComponentType::PrimeNumbers, 0.15);
        self.add("fibonacci", ComponentType::FibonacciPattern, 0.2);
        self.add("golden_ratio", ComponentType::GoldenRatio, 0.03);
        self.add("lucky_numbers", ComponentType::LuckyNumbers, 0.08);
        self.add("birthday_paradox", ComponentType::BirthdayParadox, 0.08);
        self.add("psychic", ComponentType::PsychicMoments, 0.2);
        self.add("modulo", ComponentType::ModuloPattern, 0.02);
        self.add("chaos", ComponentType::ChaosIndicator, 0.1);
        self.add("alternating", ComponentType::AlternatingPattern, 0.6);
        self.add("run_length", ComponentType::RunLength, 0.3);
        self.add("magic", ComponentType::MagicNumbers, 0.03);
    }

    fn add(&mut self, name: &str, component_type: ComponentType, base_weight: f32) {
        self.components.insert(
            name.to_string(),
            ComponentPerformance::new(name, component_type, base_weight),
        );
    }

    /// Reset pending votes for a new betting round
    fn start_new_round(&mut self) {
        self.pending_votes.clear();
        self.total_high_votes = 0.0;
        self.total_low_votes = 0.0;
    }

    /// Get weight for a component (dynamically adjusted based on performance)
    fn get_weight(&self, name: &str) -> f32 {
        self.components
            .get(name)
            .map(|c| c.get_weight())
            .unwrap_or(1.0)
    }

    /// Record that a component voted - stores for later evaluation
    fn record_vote(&mut self, name: &str, voted_high: bool, vote_amount: f32, confidence: f32) {
        // Track totals for this round
        if voted_high {
            self.total_high_votes += vote_amount;
            self.cumulative_high_votes += vote_amount;
        } else {
            self.total_low_votes += vote_amount;
            self.cumulative_low_votes += vote_amount;
        }

        // Store for later evaluation
        self.pending_votes.push(PendingVote {
            component_name: name.to_string(),
            voted_high,
            vote_amount,
            confidence,
        });
    }

    /// Update all component performances after result is known
    /// high_was_correct = true means betting HIGH would have won
    fn update_after_result(&mut self, high_was_correct: bool) {
        // Track overall direction prediction accuracy
        self.total_direction_predictions += 1;
        let consensus_high = self.total_high_votes > self.total_low_votes;
        if consensus_high == high_was_correct {
            self.direction_correct_predictions += 1;
        }

        // Update each component that voted
        for vote in self.pending_votes.drain(..) {
            if let Some(component) = self.components.get_mut(&vote.component_name) {
                // Component was correct if:
                // - It voted high AND high was correct OR
                // - It voted low AND high was NOT correct (low was correct)
                let was_correct = vote.voted_high == high_was_correct;

                component.record_prediction(was_correct, vote.vote_amount, vote.confidence);
            }
        }

        // Clear for next round
        self.pending_votes.clear();
        self.total_high_votes = 0.0;
        self.total_low_votes = 0.0;
    }

    /// Get direction bias correction factor (-1.0 to 1.0)
    /// Positive = system has been biased HIGH, needs LOW correction
    /// Negative = system has been biased LOW, needs HIGH correction
    fn get_direction_bias_correction(&self) -> f32 {
        let total = self.cumulative_high_votes + self.cumulative_low_votes;
        if total < 50.0 {
            return 0.0; // Not enough data
        }
        let high_ratio = self.cumulative_high_votes / total;
        // If high_ratio is 0.7, we've been voting high 70% of the time
        // Return positive value to indicate we need more LOW votes
        (high_ratio - 0.5) * 2.0 // -1.0 to 1.0
    }

    /// Check if system has systematic direction bias
    fn has_direction_bias(&self) -> bool {
        let total = self.cumulative_high_votes + self.cumulative_low_votes;
        if total < 100.0 {
            return false;
        }
        let high_ratio = self.cumulative_high_votes / total;
        high_ratio > 0.6 || high_ratio < 0.4
    }

    /// Get the overall consensus direction from pending votes
    fn get_consensus(&self) -> bool {
        self.total_high_votes > self.total_low_votes
    }

    /// Get consensus confidence (0.0-1.0)
    fn get_consensus_confidence(&self) -> f32 {
        let total = self.total_high_votes + self.total_low_votes;
        if total == 0.0 {
            return 0.5;
        }
        let dominant = self.total_high_votes.max(self.total_low_votes);
        (dominant / total - 0.5) * 2.0 // Scale to 0-1
    }

    /// Get top performing components
    fn get_top_performers(&self, n: usize) -> Vec<(String, f32)> {
        let mut performers: Vec<_> = self
            .components
            .iter()
            .filter(|(_, c)| c.total_predictions >= 10)
            .map(|(name, c)| (name.clone(), c.recent_accuracy_20))
            .collect();
        performers.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        performers.into_iter().take(n).collect()
    }

    /// Get worst performing components
    fn get_worst_performers(&self, n: usize) -> Vec<(String, f32)> {
        let mut performers: Vec<_> = self
            .components
            .iter()
            .filter(|(_, c)| c.total_predictions >= 10)
            .map(|(name, c)| (name.clone(), c.recent_accuracy_20))
            .collect();
        performers.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
        performers.into_iter().take(n).collect()
    }

    /// Get performance summary string
    fn get_performance_report(&self) -> String {
        let top5 = self.get_top_performers(5);
        let worst3 = self.get_worst_performers(3);

        let top_str: Vec<String> = top5
            .iter()
            .map(|(name, acc)| format!("{}: {:.1}%", name, acc * 100.0))
            .collect();
        let worst_str: Vec<String> = worst3
            .iter()
            .map(|(name, acc)| format!("{}: {:.1}%", name, acc * 100.0))
            .collect();

        format!(
            "TOP: {} | WORST: {}",
            top_str.join(", "),
            worst_str.join(", ")
        )
    }
}

impl ModelMetaLearner {
    fn new() -> Self {
        Self {
            combination_history: VecDeque::with_capacity(200),
            // Default: use all models initially
            best_for_trending: (0..25).collect(),
            best_for_volatile: (0..25).collect(),
            best_for_recovery: (0..25).collect(),
            best_for_stable: (0..25).collect(),
            learning_rate: 0.1,
            baseline_accuracy: 0.475,
        }
    }

    /// Get best model subset for current regime
    fn get_best_models(&self, regime: ModelRegimeState) -> &[usize] {
        match regime {
            ModelRegimeState::Trending => &self.best_for_trending,
            ModelRegimeState::Volatile => &self.best_for_volatile,
            ModelRegimeState::Recovery => &self.best_for_recovery,
            ModelRegimeState::Stable => &self.best_for_stable,
            ModelRegimeState::Unknown => &self.best_for_stable,
        }
    }

    /// Record result and learn
    fn record_result(
        &mut self,
        models_used: &[usize],
        was_correct: bool,
        regime: ModelRegimeState,
        confidence: f32,
    ) {
        let result = CombinationResult {
            model_ids: models_used.to_vec(),
            combined_weight: confidence,
            was_correct,
            regime,
            confidence,
        };

        self.combination_history.push_back(result);
        if self.combination_history.len() > 200 {
            self.combination_history.pop_front();
        }

        // Periodically update best models (every 20 results)
        if self.combination_history.len() % 20 == 0 {
            self.update_best_models();
        }
    }

    /// Analyze history and update best model subsets
    fn update_best_models(&mut self) {
        // Group results by regime and model presence
        let mut trending_models: std::collections::HashMap<usize, (u32, u32)> =
            std::collections::HashMap::new();
        let mut volatile_models: std::collections::HashMap<usize, (u32, u32)> =
            std::collections::HashMap::new();
        let mut recovery_models: std::collections::HashMap<usize, (u32, u32)> =
            std::collections::HashMap::new();
        let mut stable_models: std::collections::HashMap<usize, (u32, u32)> =
            std::collections::HashMap::new();

        for result in &self.combination_history {
            for &model_id in &result.model_ids {
                let entry = match result.regime {
                    ModelRegimeState::Trending => trending_models.entry(model_id).or_insert((0, 0)),
                    ModelRegimeState::Volatile => volatile_models.entry(model_id).or_insert((0, 0)),
                    ModelRegimeState::Recovery => recovery_models.entry(model_id).or_insert((0, 0)),
                    ModelRegimeState::Stable => stable_models.entry(model_id).or_insert((0, 0)),
                    ModelRegimeState::Unknown => continue,
                };

                if result.was_correct {
                    entry.0 += 1;
                }
                entry.1 += 1;
            }
        }

        // Select top 15 models per regime (above baseline accuracy)
        self.best_for_trending = Self::select_top_models(&trending_models, self.baseline_accuracy);
        self.best_for_volatile = Self::select_top_models(&volatile_models, self.baseline_accuracy);
        self.best_for_recovery = Self::select_top_models(&recovery_models, self.baseline_accuracy);
        self.best_for_stable = Self::select_top_models(&stable_models, self.baseline_accuracy);
    }

    fn select_top_models(
        model_stats: &std::collections::HashMap<usize, (u32, u32)>,
        baseline: f32,
    ) -> Vec<usize> {
        let mut accuracies: Vec<(usize, f32)> = model_stats
            .iter()
            .filter(|(_, (wins, total))| *total >= 5) // Need at least 5 samples
            .map(|(&id, (wins, total))| {
                let acc = *wins as f32 / *total as f32;
                (id, acc)
            })
            .filter(|(_, acc)| *acc > baseline) // Must beat baseline
            .collect();

        // Sort by accuracy descending
        accuracies.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        // Take top 15, or all if fewer available
        accuracies.iter().take(15).map(|(id, _)| *id).collect()
    }
}

/// Decision on whether to skip betting
#[derive(Clone, Copy, Debug, PartialEq)]
enum BetDecision {
    Bet,          // Proceed with bet
    Skip,         // Skip this bet (uncertainty too high)
    Reduce,       // Reduce bet size significantly
    IncreaseRisk, // Take more risk (high confidence)
}

/// Recovery phases based on drawdown severity
#[derive(Clone, Copy, Debug, PartialEq)]
enum RecoveryPhase {
    Light,      // 25-35% drawdown
    Moderate,   // 35-50% drawdown
    Aggressive, // 50%+ drawdown
    Critical,   // Severe drawdown
}

impl Default for AiStrat {
    fn default() -> Self {
        Self {
            high: false,
            min_bet: 0.00002000,
            current_bet: 0.00002000,
            bank: 0.001,
            initial_bank: 0.001,
            peak_bank: 0.001,
            profit: 0.0,
            chance: 47.5,
            multiplier: 2.0,
            house_percent: 5.0,
            total_bets: 0,
            last_prediction: 0.5,
            last_confidence: 0.0,
            loss_streak: 0,
            win_streak: 0,
            arms: (0..40)
                .map(|i| 1.0 * 1.12_f32.powi(i))
                .filter(|&m| m <= 100.0) // cap at 100x
                .map(BayesianArm::new)
                .collect(),
            ensemble: Ensemble::new(),
            current_meta: MetaStrategy::Adaptive,
            patterns: PatternMemory::new(),
            recent_seq: VecDeque::with_capacity(50),
            recent_rolls: VecDeque::with_capacity(100),
            high_wins: 0,
            low_wins: 0,
            high_bets: 0,
            low_bets: 0,
            high_win_streak: 0,
            low_win_streak: 0,
            risk: RiskState::new(),
            change_det: ChangeDetector::new(0.2),
            prog_mult: 2.0,
            last_win: false,
            cons_wins: 0,
            cons_losses: 0,
            max_bet_pct: 0.25,
            stop_loss: false,
            hard_stop: 0.35,
            session_profit: 0.0,
            debt: 0.0,
            rng_state: 12345,
            // Advanced features (existing)
            kelly: KellyOptimizer::new(0.25), // Quarter Kelly
            regime: RegimeDetector::new(),
            q_learner: QLearner::new(100, 10), // Reduced from 500 states to 100
            total_wins: 0,
            total_losses: 0,
            recent_returns: VecDeque::with_capacity(100), // Reduced from 1000 - 100 is enough for Sharpe
            sharpe_ratio: 0.0,
            sortino_ratio: 0.0,
            max_consecutive_wins: 0,
            max_consecutive_losses: 0,
            session_high: 0.0,
            session_low: f32::MAX,
            volatility_adjusted_bet: true,
            // New advanced features
            mcts: MCTSPredictor::new(),
            volatility_forecaster: VolatilityForecaster::new(),
            mean_reversion: MeanReversionDetector::new(),
            trend_strength: TrendStrength::new(),
            risk_parity: RiskParitySizer::new(),
            adaptive_lr: AdaptiveLearningRate::new(),
            markov: MarkovChain::new(4),                // Reduced from 5
            bank_history: VecDeque::with_capacity(100), // Reduced from 2000
            profit_history: VecDeque::with_capacity(100), // Reduced from 2000
            expected_value: 0.0,
            confidence_interval: (0.0, 1.0),
            // Even more advanced features
            ensemble_forecaster: EnsembleForecaster::new(5), // Reduced from 10 prediction models
            kalman_filter: KalmanFilter::new(0.5, 0.01, 0.1),
            particle_filter: ParticleFilter::new(100), // Reduced from 500 particles
            dqn_agent: DQNAgent::new(50, 10),          // 50 state features, 10 actions (was 20/5)
            linucb: LinUCBDisjoint::new(40, 25, 0.5),  // 40 arms, 25 context features (was 10)
            // Ultra advanced features
            lstm_model: LSTMSequenceModel::new(25, 128), // 25 input, 128 hidden (was 10/16)
            self_attention: SelfAttention::new(32, 50),  // 32-d model, 50 seq length (was 8/20)
            gaussian_process: GaussianProcess::new(1.0, 1.0, 0.1),
            policy_gradient: PolicyGradientAgent::new(10, 25), // 10 actions, 25 state dim (was 5/11)
            evolution_strategies: EvolutionStrategies::new(200), // 200 params (was 50)
            context_builder: ContextBuilder::new(25),          // 25 features (was 11)
            // Experimental quantum-inspired
            hd_memory: HyperdimensionalMemory::new(50000), // 50K dimensional vectors (was 10K)
            reservoir: Reservoir::new(25, 1000, 20, 0.9, 0.3), // Echo state network (was 10/200/5)
            spiking_net: SpikingNetwork::new(&[25, 200, 100, 50, 10]), // SNN layers (was [10,50,20,5])
            neat_population: Population::new(200, 25, 10), // NEAT population (was 50/10/5)
            dreamer: DreamerWorldModel::new(50, 256, 10),  // World model (was 20/64/5)
            contrastive: ContrastiveLearner::new(25, 64, 128), // Reduced from 25/128/256
            // ===== EXPERIMENTAL THEORETICAL ALGORITHMS =====
            transformer: TransformerPredictor::new(16, 2, 1, 32), // Reduced: 16-d model, 2 heads, 1 layer
            vae: VariationalAutoencoder::new(25, 8, 32), // Reduced: 25 input, 8 latent, 32 hidden
            ntm: NeuralTuringMachine::new(25, 32, 16), // Reduced: 25 input, 32 memory slots, 16-d memory
            hawkes: HawkesProcess::new(0.1, 0.5, 1.0), // Baseline, excitation, decay
            hurst: HurstEstimator::new(100),           // Reduced from 500
            info_theory: InformationTheoretic::new(200), // Reduced from 1000
            gp_thompson: GPThompsonSampling::new(1.0, 1.0, 0.1, 50), // Reduced max_samples from 200
            categorical_dqn: CategoricalDQN::new(25, 40, 21, -1.0, 1.0), // Reduced atoms from 51 to 21
            quantum_annealer: QuantumAnnealingOptimizer::new(20),        // Reduced from 100 spins
            meta_learner: MetaRLLearner::new(25, 32, 10),                // Reduced hidden from 64
            pbt: PBTPopulation::new(5, 50), // Reduced from 20 agents, 100 weights
            safe_rl: SafeRLAgent::new(25, 40, 32), // Reduced hidden from 64
            ou_process: OrnsteinUhlenbeckProcess::new(0.15, 0.5, 0.3, 0.5), // theta, mu, sigma, initial
            gumbel_mcts: GumbelMCTS::new(40),                               // 40 actions
            exp3_bandit: EXP3Bandit::new(40, 0.1),                          // 40 arms, gamma
            tcn: TCN::new(11, 2, 16, 3), // Reduced: input_channels, num_layers, hidden, kernel_size
            // Data collection phase - need 500 bets minimum before AI takes over
            data_collection_target: 0,
            data_collection_multiplier: 1.0, // 2x multiplier for data collection
            data_collection_high_low_random: false,
            data_collected: 0,
            win_rates_by_multiplier: vec![0.5; 40], // Initialize with 0.5 win rate
            confidence_threshold: 0.,               // Need 25% better than random to exit
            min_patterns_needed: 0,                 // Need at least 50 patterns in memory
            // Dynamic model weighting system
            model_predictions: VecDeque::with_capacity(100),
            model_accuracies: vec![0.5; 25], // 25 models tracked
            model_weights: vec![1.0; 25],    // Start with equal weights
            total_model_prediction_count: 0,
            model_regime_state: ModelRegimeState::Unknown,
            // Advanced improvements
            cached_predictions: CachedPredictions::default(),
            skip_bet_threshold: 0.7, // Skip when uncertainty > 70%
            recent_skips: 0,
            skip_adjustment: 0.0,
            model_meta_learner: ModelMetaLearner::new(),
            voting_tracker: VotingPerformanceTracker::new(),
            // Genuinely intelligent features
            edge_detector: EdgeDetector::new(),
            confidence_calibrator: ConfidenceCalibrator::new(),
            strategy_selector: AdaptiveStrategySelector::new(),
            pattern_strength: PatternStrengthEvaluator::new(),
            session_state: SessionStateAnalyzer::new(),
            performance_momentum: PerformanceMomentum::new(),
            risk_adjuster: DynamicRiskAdjuster::new(),
            win_predictor: SessionWinPredictor::new(),
            bankroll_manager: SmartBankrollManager::new(),
            // Absurdly unnecessary features
            lunar_phase: LunarPhaseTracker::new(),
            biorhythm: BiorhythmCalculator::new(),
            sentiment_analyzer: SentimentAnalyzer::new(),
            dunning_kruger: DunningKrugerDetector::new(),
            hot_hand_tracker: HotHandTracker::new(),
            martingale_urge: MartingaleUrgeSuppressor::new(),
            pattern_confidence: PatternConfidenceCalibrator::new(),
            chaos_dragon: ChaosDragon::new(),
            divine_intervention: DivineIntervention::new(),
            conspiracy_detector: ConspiracyDetector::new(),
            schrodinger_cat: SchrodingerCat::new(),
            // Even more absurd features
            karma_calculator: KarmaCalculator::new(),
            butterfly_effect: ButterflyEffectTracker::new(),
            pattern_cult_detector: PatternCultDetector::new(),
            quantum_entanglement: QuantumEntanglement::new(),
            philosophical_uncertainty: PhilosophicalUncertainty::new(),
            akashic_reader: AkashicRecordReader::new(),
            retrocausality_engine: RetrocausalityEngine::new(),
            probability_manipulator: ProbabilityManipulator::new(),
            casino_psychology: CasinoPsychologyModel::new(),
            luck_bank: LuckBank::new(),
            // Advanced Intelligence Features
            curiosity_engine: CuriosityEngine::new(40), // 40 arms
            profit_weighted_learner: ProfitWeightedLearner::new(),
            anti_persistence: AntiPersistenceDetector::new(),
            lookahead_planner: LookaheadPlanner::new(),
            ensemble_manager: EnsembleManager::new(70), // ~70 voting components
            session_memory: SessionMemory::new(),
            advanced_calibrator: AdvancedConfidenceCalibrator::new(10),
            // Features 8-17 initialization
            transformer_predictor: TransformerSequencePredictor::new(50, 32, 4), // seq_len=50, d_model=32, heads=4
            episodic_memory: EpisodicMemory::new(100),
            cfr: CounterfactualRegretMinimizer::new(),
            bayesian_averager: BayesianModelAverager::new(70), // ~70 models
            anomaly_detector: AnomalyDetector::new(50, 3.0),   // window=50, threshold=3 sigma
            risk_aware_rl: RiskAwareRL::new(0.05),             // CVaR alpha=0.05 (5% tail)
            hierarchical_rl: HierarchicalRL::new(),
            model_based_rl: ModelBasedRL::new(),
            inverse_rl: InverseRL::new(50), // 50 features
            theory_of_mind: TheoryOfMind::new(),
            // Training state
            last_arm_idx: 0,
            last_context: vec![0.0; 50],
            last_multiplier_action: 0,
            replay_buffer: ReplayBuffer::new(10000),
        }
    }
}

impl AiStrat {
    fn next_rng(&mut self) -> f32 {
        self.rng_state = self
            .rng_state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.rng_state as f32 / u64::MAX as f32).clamp(0.0, 1.0)
    }

    /// Safe float comparison that handles NaN
    fn cmp_f32(a: f32, b: f32) -> std::cmp::Ordering {
        a.partial_cmp(&b).unwrap_or(std::cmp::Ordering::Equal)
    }

    // ========================================================================
    // DYNAMIC MODEL WEIGHTING SYSTEM
    // ========================================================================

    /// Detect model regime for weighting (independent of market regime)
    fn detect_model_regime(&self) -> ModelRegimeState {
        let dd = (self.session_high - self.bank) / self.session_high.max(1e-8);

        // Recovery: deep drawdown
        if dd > 0.25 && self.loss_streak >= 3 {
            return ModelRegimeState::Recovery;
        }

        // Check volatility from recent returns
        if self.recent_returns.len() >= 10 {
            let returns: Vec<f32> = self.recent_returns.iter().copied().collect();
            let mean: f32 = returns.iter().sum::<f32>() / returns.len() as f32;
            let variance: f32 =
                returns.iter().map(|r| (r - mean).powi(2)).sum::<f32>() / returns.len() as f32;
            let volatility = variance.sqrt();

            // Volatile regime
            if volatility > 0.02 {
                return ModelRegimeState::Volatile;
            }
        }

        // Trending: strong momentum in one direction
        if self.recent_returns.len() >= 5 {
            let recent: Vec<f32> = self.recent_returns.iter().rev().take(5).copied().collect();
            let positive = recent.iter().filter(|&&r| r > 0.0).count();

            if positive >= 4 || positive <= 1 {
                // Strong momentum (winning or losing streak)
                return ModelRegimeState::Trending;
            }
        }

        // Stable: low volatility, no clear trend
        ModelRegimeState::Stable
    }

    /// Get model weights adjusted by regime and recent accuracy
    /// Returns weights for each model (25 models tracked)
    fn get_dynamic_model_weights(&self) -> Vec<f32> {
        let mut weights = self.model_weights.clone();

        // Apply regime-specific boosts
        let regime = self.model_regime_state;
        for (i, w) in weights.iter_mut().enumerate() {
            // Base weight from accuracy (models that predict well get more weight)
            let accuracy = self.model_accuracies.get(i).copied().unwrap_or(0.5);

            // Transform accuracy into weight: 50% accuracy = 0.5x, 60% = 1.0x, 70%+ = 1.5x
            // ML models start with higher base weights
            let ml_boost = if i <= 10 { 1.5 } else { 1.0 }; // First 11 models are core ML

            let accuracy_weight = if accuracy > 0.55 {
                (0.5 + (accuracy - 0.5) * 5.0) * ml_boost // 0.55 -> 0.75x+, ML models higher
            } else if accuracy < 0.45 {
                0.25 + accuracy // Poor models get strongly penalized
            } else {
                0.5 * ml_boost // Near-random models, ML models get boost
            };

            // Regime-specific boosts - INCREASED for ML models
            let regime_boost = match (regime, i) {
                // Trending: boost LSTM, Transformer, Trend models (0, 1, 2, 3, 4) - STRONG
                (ModelRegimeState::Trending, 0..=4) => 1.6,
                // Volatile: boost Kalman, GP, Gaussian models (5, 6, 7, 8, 9) - STRONG
                (ModelRegimeState::Volatile, 5..=9) => 1.6,
                // Recovery: boost conservative models (10, 11, 12, 13, 14) - STRONGER
                (ModelRegimeState::Recovery, 10..=14) => 1.8,
                // Stable: boost pattern-based models (15, 16, 17, 18, 19)
                (ModelRegimeState::Stable, 15..=19) => 1.4,
                _ => 1.0,
            };

            *w = accuracy_weight * regime_boost * *w;
        }

        // Normalize weights to sum to ~40 (for voting) - HIGHER total influence
        let sum: f32 = weights.iter().sum();
        if sum > 0.0 {
            for w in &mut weights {
                *w = *w / sum * 40.0;
            }
        }

        weights
    }

    /// Update model accuracy after a bet result
    /// Call this after each bet to track which models are performing
    fn update_model_accuracy(&mut self, won: bool) {
        // Get the stored predictions from last bet
        if let Some(predictions) = self.model_predictions.back() {
            for pred in predictions {
                let model_id = pred.model_id as usize;
                if model_id < self.model_accuracies.len() {
                    // Exponential moving average of accuracy (ema_weight = 0.1)
                    let current = self.model_accuracies[model_id];
                    let new_val = if pred.was_correct { 1.0 } else { 0.0 };
                    self.model_accuracies[model_id] = current * 0.9 + new_val * 0.1;
                }
            }
        }

        self.total_model_prediction_count += 1;
    }

    /// Store a model's prediction for later accuracy tracking
    fn record_model_prediction(&mut self, model_id: usize, predicted_high: bool, confidence: f32) {
        // Keep only last 100 prediction sets
        if self.model_predictions.len() >= 100 {
            self.model_predictions.pop_front();
        }

        // Initialize or add to current prediction set
        if self.model_predictions.is_empty()
            || self.model_predictions.back().map(|v| v.len()) != Some(25)
        {
            self.model_predictions.push_back(Vec::with_capacity(25));
        }

        if let Some(current) = self.model_predictions.back_mut() {
            current.push(ModelPrediction {
                model_id,
                predicted_high,
                confidence,
                was_correct: false, // Will be updated after result
            });
        }
    }

    /// Update model predictions after result is known
    /// high_was_correct = true if high was the winning bet
    fn update_model_predictions_correct(&mut self, high_was_correct: bool) {
        // Get the last set of predictions and mark them correct/incorrect
        if let Some(predictions) = self.model_predictions.back_mut() {
            for pred in predictions.iter_mut() {
                // A prediction was correct if:
                // - It predicted high and high was correct OR
                // - It predicted low and high was NOT correct (low was correct)
                pred.was_correct = pred.predicted_high == high_was_correct;

                // Update model accuracy using exponential moving average
                if pred.model_id < self.model_accuracies.len() {
                    let current_accuracy = self.model_accuracies[pred.model_id];
                    let new_result = if pred.was_correct { 1.0 } else { 0.0 };
                    // Weight recent results more (alpha = 0.15 for faster adaptation)
                    self.model_accuracies[pred.model_id] =
                        current_accuracy * 0.85 + new_result * 0.15;

                    // Also update model weight based on accuracy and confidence
                    // Models with good accuracy AND high confidence get more weight
                    let accuracy_weight = if current_accuracy > 0.55 {
                        0.5 + (current_accuracy - 0.5) * 4.0 // 0.55 -> 0.7, 0.6 -> 0.9, 0.7 -> 1.3
                    } else if current_accuracy < 0.45 {
                        0.5 - (0.5 - current_accuracy) * 2.0 // 0.45 -> 0.4, 0.4 -> 0.3
                    } else {
                        0.5 // Average performers
                    };

                    self.model_weights[pred.model_id] =
                        accuracy_weight * (0.5 + pred.confidence * 0.5);
                }
            }
        }

        // Clear predictions for next round (they'll be rebuilt in next decide_high_low)
        self.model_predictions.push_back(Vec::with_capacity(25));
    }

    // ========================================================================
    // ADVANCED IMPROVEMENTS: CACHING, UNCERTAINTY, REGIME-BASED MULTIPLIERS
    // ========================================================================

    /// Cache expensive predictions at the start of each bet cycle
    fn cache_predictions(&mut self, context: &[f32]) {
        let dd = context.first().copied().unwrap_or(0.5);

        // Kalman and Particle Filter
        self.cached_predictions.kalman_state = self.kalman_filter.get_state();
        self.cached_predictions.particle_estimate = self.particle_filter.estimate();

        // Gaussian Process
        let gp_state = vec![
            self.bank / self.initial_bank.max(1e-8),
            dd,
            self.risk.volatility,
        ];
        let (gp_mean, gp_var) = self.gaussian_process.predict(&gp_state);
        self.cached_predictions.gp_mean = gp_mean;
        self.cached_predictions.gp_var = gp_var;

        // MCTS
        let mcts_policy = self.gumbel_mcts.get_improved_policy();
        if let Some((action, value)) = mcts_policy
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, &v)| (i, v))
        {
            self.cached_predictions.mcts_best_action = action;
            self.cached_predictions.mcts_best_value = value;
        }

        // Markov
        self.cached_predictions.markov_pred = self
            .markov
            .predict(&self.recent_seq.iter().copied().collect::<Vec<_>>());

        // Hurst exponent
        self.cached_predictions.hurst_exp = self.hurst.estimate_hurst();

        // Entropy measures
        self.cached_predictions.entropy = self.info_theory.entropy();
        self.cached_predictions.transfer_entropy = self.info_theory.transfer_entropy();

        // Compute uncertainty score
        self.cached_predictions.uncertainty_score = self.compute_uncertainty_score();

        self.cached_predictions.valid = true;
    }

    /// Compute overall uncertainty score (0 = certain, 1 = very uncertain)
    fn compute_uncertainty_score(&self) -> f32 {
        let mut uncertainty = 0.0;
        let mut factors = 0.0;

        // High entropy = uncertain
        let entropy = self.cached_predictions.entropy;
        if entropy > 0.0 {
            uncertainty += entropy.min(1.0);
            factors += 1.0;
        }

        // High GP variance = uncertain
        let gp_var = self.cached_predictions.gp_var;
        if gp_var > 0.0 {
            uncertainty += (gp_var * 10.0).min(1.0);
            factors += 1.0;
        }

        // Low Hurst (mean-reverting) during losses = uncertain
        let hurst = self.cached_predictions.hurst_exp;
        if hurst < 0.4 && self.loss_streak > 2 {
            uncertainty += 0.3;
            factors += 1.0;
        }

        // Model disagreement = uncertain
        let model_agreement = self.cached_predictions.model_agreement;
        if model_agreement < 0.6 {
            uncertainty += 1.0 - model_agreement;
            factors += 1.0;
        }

        // Transfer entropy too low = no signal
        let te = self.cached_predictions.transfer_entropy;
        if te < 0.01 {
            uncertainty += 0.5;
            factors += 1.0;
        }

        if factors > 0.0 {
            uncertainty / factors
        } else {
            0.5 // Default moderate uncertainty
        }
    }

    /// Determine whether to bet, skip, or adjust based on uncertainty
    fn evaluate_bet_decision(&mut self) -> BetDecision {
        // Don't skip in early betting phase
        if self.total_bets < 30 {
            return BetDecision::Bet;
        }

        let uncertainty = self.cached_predictions.uncertainty_score;

        // Dynamic threshold adjustment based on recent performance
        // If we've been skipping too much, lower the threshold
        let dynamic_threshold = self.skip_bet_threshold + self.skip_adjustment;

        // Very high uncertainty = skip bet
        if uncertainty > dynamic_threshold {
            self.recent_skips += 1;
            // If skipping too often, reduce threshold adjustment
            if self.recent_skips > 5 {
                self.skip_adjustment = (self.skip_adjustment - 0.02).max(-0.2);
            }
            return BetDecision::Skip;
        }

        // Very low uncertainty with high confidence = increase risk
        if uncertainty < 0.25 && self.cached_predictions.model_agreement > 0.8 {
            self.recent_skips = 0;
            self.skip_adjustment = (self.skip_adjustment + 0.01).min(0.1);
            return BetDecision::IncreaseRisk;
        }

        // Moderate uncertainty = reduce bet size
        if uncertainty > 0.5 {
            self.recent_skips = 0;
            return BetDecision::Reduce;
        }

        // Normal bet
        self.recent_skips = 0;
        BetDecision::Bet
    }

    /// Get regime-adjusted multiplier preferences
    fn get_regime_multiplier_adjustment(&self) -> f32 {
        let base_mult = if self.cached_predictions.valid {
            // Use cached predictions
            let hurst = self.cached_predictions.hurst_exp;
            let entropy = self.cached_predictions.entropy;

            match self.model_regime_state {
                ModelRegimeState::Trending => {
                    // High Hurst in trending = momentum, use higher multipliers
                    if hurst > 0.55 {
                        1.3
                    } else {
                        1.1
                    }
                }
                ModelRegimeState::Volatile => {
                    // High entropy in volatile = chaos, use lower multipliers
                    if entropy > 0.7 {
                        0.6
                    } else {
                        0.8
                    }
                }
                ModelRegimeState::Recovery => {
                    // Recovery mode = conservative
                    0.7
                }
                ModelRegimeState::Stable => {
                    // Stable = can be more aggressive
                    1.2
                }
                ModelRegimeState::Unknown => 1.0,
            }
        } else {
            1.0
        };

        // Further adjust based on uncertainty score
        let uncertainty = self.cached_predictions.uncertainty_score;
        if uncertainty > 0.6 {
            base_mult * 0.8 // Reduce multipliers when uncertain
        } else if uncertainty < 0.3 {
            base_mult * 1.1 // Increase when confident
        } else {
            base_mult
        }
    }

    /// Get models that are currently performing well for the regime
    fn get_best_models_for_regime(&self) -> Vec<usize> {
        let best = self
            .model_meta_learner
            .get_best_models(self.model_regime_state);
        if best.is_empty() {
            // Fallback to all models
            (0..25).collect()
        } else {
            best.to_vec()
        }
    }

    // ========================================================================
    // DATA COLLECTION PHASE
    // ========================================================================

    /// Check if we're still in the data collection phase
    /// AI takes control immediately - models learn as they go
    /// Only skip first few bets to avoid numerical issues
    fn is_collecting_data(&self) -> bool {
        // Minimal warmup - just first 5 bets for numerical stability
        self.data_collected < 5
    }

    /// Get data collection progress as a percentage (0.0 to 1.0)
    /// Shows how "warmed up" the models are
    fn data_collection_progress(&self) -> f32 {
        // Models reach full "warmup" perception after 100 bets
        (self.data_collected as f32 / 100.0).min(1.0)
    }

    /// During data collection, select an arm using exploration-focused strategy
    /// Ensures all multipliers get tested evenly, with some random exploration
    fn select_arm_for_data_collection(&mut self) -> usize {
        // First pass: find arms that haven't been pulled much
        let min_pulls = self.arms.iter().map(|a| a.pull_count).min().unwrap_or(0);
        let underexplored: Vec<usize> = self
            .arms
            .iter()
            .enumerate()
            .filter(|(_, a)| a.pull_count <= min_pulls + 2)
            .map(|(i, _)| i)
            .collect();

        if !underexplored.is_empty() {
            // Pick randomly from underexplored arms
            let idx = (self.next_rng() * underexplored.len() as f32) as usize;
            return underexplored[idx.min(underexplored.len() - 1)];
        }

        // Second pass: UCB-style exploration focusing on uncertainty
        // Higher exploration rate during data collection
        let exploration_bonus = 2.0;
        let total_pulls: u32 = self.arms.par_iter().map(|a| a.pull_count).sum();

        let mut best_score = f32::NEG_INFINITY;
        let mut best_idx = 0;

        for (i, arm) in self.arms.iter().enumerate() {
            let win_rate = if arm.pull_count > 0 {
                arm.alpha / (arm.alpha + arm.beta)
            } else {
                0.5
            };

            let uncertainty = if arm.pull_count > 0 {
                (total_pulls as f32 / arm.pull_count as f32).ln()
            } else {
                10.0
            };

            let score = win_rate + exploration_bonus * uncertainty.sqrt();
            if score > best_score {
                best_score = score;
                best_idx = i;
            }
        }

        best_idx
    }

    /// Check if we have enough confidence in predictions to exit data collection early
    fn has_sufficient_confidence(&self) -> bool {
        // Check if win rates show any significant deviation from random (0.475 for 2x with edge)
        let total_wins = self.total_wins;
        let total_bets = self.total_wins + self.total_losses;

        if total_bets < 100 {
            return false;
        }

        let overall_win_rate = total_wins as f32 / total_bets as f32;

        // For 2x multiplier with 2.5% edge, expected win rate is ~47.5%
        // If we're winning significantly more, something might be off
        // If we're winning significantly less, house edge is confirmed

        // Check if variance is acceptable (not too volatile)
        if self.recent_returns.len() < 50 {
            return false;
        }

        let mean: f32 = self.recent_returns.iter().sum::<f32>() / self.recent_returns.len() as f32;
        let variance: f32 = self
            .recent_returns
            .iter()
            .map(|r| (r - mean).powi(2))
            .sum::<f32>()
            / self.recent_returns.len() as f32;
        let std_dev = variance.sqrt();

        // If we have low variance and reasonable win rate, we have good data
        std_dev < 2.0 && overall_win_rate > 0.40 && overall_win_rate < 0.55
    }

    /// Configure data collection phase parameters
    /// - target_bets: Minimum number of bets to collect before AI takes over
    /// - min_patterns: Minimum patterns needed in pattern memory
    pub fn with_data_collection(mut self, target_bets: usize, min_patterns: usize) -> Self {
        self.data_collection_target = target_bets;
        self.min_patterns_needed = min_patterns;
        self
    }

    /// Skip data collection phase entirely (immediately use AI)
    pub fn skip_data_collection(mut self) -> Self {
        self.data_collection_target = 0;
        self.min_patterns_needed = 0;
        self
    }

    /// Get current data collection status
    pub fn data_collection_status(&self) -> (bool, f32, usize, usize) {
        (
            self.is_collecting_data(),
            self.data_collection_progress(),
            self.data_collected,
            self.patterns.sequences.len(),
        )
    }

    /// Build context vector for AI systems from current state
    fn build_context(&self, dd: f32, ws: u32, ls: u32) -> Vec<f32> {
        let win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
        } else {
            0.5
        };

        vec![
            dd.clamp(0.0, 1.0),
            (ws as f32 / 20.0).min(1.0),
            (ls as f32 / 20.0).min(1.0),
            win_rate,
            self.risk.volatility.clamp(0.0, 1.0),
            (self.bank / self.initial_bank.max(1e-8)).min(5.0) / 5.0,
            (self.profit.abs() / self.initial_bank.max(1e-8)).min(2.0) / 2.0,
            self.risk.risk_score / 100.0,
            if self.last_win { 1.0 } else { 0.0 },
            (self.total_bets as f32 / 1000.0).min(1.0),
            self.kelly.fraction.clamp(0.0, 1.0),
        ]
    }

    /// Generate win probability prediction using all AI models
    /// Returns (prediction, confidence) where:
    /// - prediction: 0.0-1.0 probability of win (high)
    /// - confidence: 0.0-1.0 how confident the models are
    fn ai_generate_prediction(&mut self, context: &[f32]) -> (f32, f32) {
        let mut predictions: Vec<(f32, f32)> = Vec::new(); // (prediction, weight)

        // Track how many predictions are meaningful (not just 0.5 defaults)
        let mut meaningful_predictions = 0;

        // DQN prediction - use actual win rate for early training
        let dqn_values = self.dqn_agent.forward(context);
        let dqn_mean: f32 = dqn_values.iter().sum::<f32>() / dqn_values.len().max(1) as f32;
        let dqn_pred = if self.total_bets < 50 {
            // Early: use empirical win rate
            if self.total_wins + self.total_losses > 0 {
                self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
            } else {
                0.5
            }
        } else {
            (dqn_mean.tanh() + 1.0) / 2.0
        };
        let dqn_conf = (dqn_values.par_iter().map(|v| v.abs()).sum::<f32>()
            / dqn_values.len().max(1) as f32)
            .min(1.0);
        predictions.push((dqn_pred.clamp(0.3, 0.7), 2.0 + dqn_conf));
        if dqn_conf > 0.1 {
            meaningful_predictions += 1;
        }

        // Policy gradient
        let pg_action = self.policy_gradient.select_action(context);
        let pg_value = self.policy_gradient.value_estimate(context);
        let pg_pred = if self.total_bets < 30 {
            0.5
        } else {
            (pg_value.tanh() + 1.0) / 2.0
        };
        predictions.push((pg_pred.clamp(0.3, 0.7), 1.5));

        // LSTM sequence prediction - actual predictions from trained model
        let lstm_seq: Vec<f32> = self
            .recent_seq
            .iter()
            .map(|&b| if b { 1.0 } else { 0.0 })
            .collect();
        let lstm_out = self.lstm_model.process_sequence(&lstm_seq);
        let lstm_pred = lstm_out.first().copied().unwrap_or(0.5);
        // LSTM should predict based on recent sequence patterns
        let lstm_pred_actual = if self.recent_seq.len() >= 10 {
            lstm_pred.clamp(0.35, 0.65)
        } else {
            0.5
        };
        predictions.push((lstm_pred_actual, 1.5));

        // Self-attention prediction
        let attn_pred = if self.recent_seq.len() >= 8 {
            let seq: Vec<f32> = self
                .recent_seq
                .iter()
                .map(|&b| if b { 1.0 } else { 0.0 })
                .collect();
            let pred = self.self_attention.predict(&seq);
            pred.clamp(0.35, 0.65)
        } else {
            0.5
        };
        predictions.push((attn_pred, 1.2));

        // Markov chain prediction - good for pattern matching
        let markov_pred = self
            .markov
            .predict(&self.recent_seq.iter().copied().collect::<Vec<_>>());
        predictions.push((markov_pred.clamp(0.35, 0.65), 1.5));

        // Pattern memory prediction - one of the most reliable
        let (pw, pl, _) = self
            .patterns
            .find_similar(&self.recent_seq.iter().copied().collect::<Vec<_>>(), 5);
        let pattern_total = pw + pl;
        if pattern_total >= 3 {
            let pattern_pred = pw as f32 / pattern_total as f32;
            let pattern_weight = (pattern_total as f32 / 10.0).min(2.0); // Increased weight
            predictions.push((pattern_pred.clamp(0.3, 0.7), pattern_weight));
            meaningful_predictions += 1;
        }

        // Contrastive learning prediction
        let contrastive_pred = self.contrastive.predict_outcome(context);
        predictions.push((contrastive_pred.clamp(0.35, 0.65), 1.0));

        // Kalman filter state-based prediction
        let kalman_state = self.kalman_filter.get_state();
        // Interpret state as: positive = wins more likely, negative = losses more likely
        let kalman_pred = 0.5 + kalman_state.clamp(-0.3, 0.3);
        predictions.push((kalman_pred, 0.8));

        // Particle filter
        let particle_state = self.particle_filter.estimate();
        let particle_pred = 0.5 + particle_state.clamp(-0.3, 0.3);
        predictions.push((particle_pred, 0.8));

        // Mean reversion signal - actual strategy
        let mr_z = self.mean_reversion.z_score();
        let mr_pred = if mr_z < -1.5 {
            0.58 // Strong mean reversion expected (bank dropped, expect recovery)
        } else if mr_z < -0.5 {
            0.54 // Mild mean reversion
        } else if mr_z > 1.5 {
            0.42 // Overextended, expect pullback
        } else if mr_z > 0.5 {
            0.46 // Slight pullback expected
        } else {
            0.5
        };
        predictions.push((mr_pred, mr_z.abs().max(0.5)));

        // Reservoir computing
        if self.recent_seq.len() >= 10 {
            let res_in: Vec<f32> = self
                .recent_seq
                .iter()
                .rev()
                .take(10)
                .map(|&b| if b { 1.0 } else { 0.0 })
                .collect();
            self.reservoir.update(&res_in);
            let res_out = self.reservoir.output();
            if !res_out.is_empty() {
                let res_pred = res_out.par_iter().sum::<f32>() / res_out.len() as f32;
                predictions.push((res_pred.clamp(0.35, 0.65), 0.7));
            }
        }

        // ===== EXPERIMENTAL ALGORITHMS =====

        // Transformer prediction (self-attention over sequence)
        if self.recent_seq.len() >= 10 {
            let transformer_input: Vec<Vec<f32>> = self
                .recent_seq
                .iter()
                .take(32) // Max sequence length
                .map(|&b| vec![if b { 1.0 } else { 0.0 }; 32]) // d_model = 32
                .collect();
            let transformer_pred = self.transformer.predict(&transformer_input);
            predictions.push((transformer_pred.clamp(0.0, 1.0), 1.8));
        }

        // VAE latent prediction
        let vae_latent = self.vae.get_latent(context);
        let vae_pred = (vae_latent.first().copied().unwrap_or(0.0).tanh() + 1.0) / 2.0;
        predictions.push((vae_pred, 0.9));

        // Neural Turing Machine memory read
        let ntm_memory = self.ntm.forward(context);
        let ntm_pred = (ntm_memory.first().copied().unwrap_or(0.5)).clamp(0.0, 1.0);
        predictions.push((ntm_pred, 0.8));

        // Hawkes Process - predict win probability
        let hawkes_intensity = self.hawkes.intensity(self.total_bets as f32);
        let hawkes_pred = 1.0 / (1.0 + hawkes_intensity); // Higher intensity = more expected events
        predictions.push((hawkes_pred.clamp(0.0, 1.0), 0.7));

        // Hurst exponent - trending vs mean-reverting
        let hurst = self.hurst.estimate_hurst();
        let hurst_pred = if hurst > 0.55 {
            // Trending - expect continuation
            if self.last_win {
                0.55
            } else {
                0.45
            }
        } else if hurst < 0.45 {
            // Mean-reverting - expect reversal
            if self.last_win {
                0.45
            } else {
                0.55
            }
        } else {
            0.5
        };
        let hurst_confidence = (hurst - 0.5).abs() * 2.0;
        predictions.push((hurst_pred, 0.6 + hurst_confidence));

        // Permutation entropy - randomness measure
        let perm_entropy = self.info_theory.permutation_entropy(4);
        let entropy_pred = if perm_entropy > 0.9 {
            0.5 // High entropy = random, no prediction
        } else {
            // Low entropy = predictable patterns
            let mi = self.info_theory.mutual_information();
            if mi > 0.1 {
                if self.last_win {
                    0.52
                } else {
                    0.48
                }
            } else {
                0.5
            }
        };
        predictions.push((entropy_pred, (1.0 - perm_entropy) * 0.8));

        // Sample entropy - complexity measure
        let sample_ent = self.info_theory.sample_entropy(2, 0.2);
        let sample_pred = if sample_ent < 0.5 {
            // Low entropy = predictable
            if self.last_win {
                0.53
            } else {
                0.47
            }
        } else {
            0.5
        };
        predictions.push((sample_pred, (1.0 - sample_ent.min(1.0)) * 0.5));

        // GP Thompson Sampling
        let (gp_mean, gp_var) = self.gp_thompson.predict(context);
        let gp_pred = (gp_mean.tanh() + 1.0) / 2.0;
        let gp_conf = 1.0 / (1.0 + gp_var);
        predictions.push((gp_pred.clamp(0.0, 1.0), gp_conf * 1.2));

        // Categorical DQN - distributional value
        let c51_dist = self.categorical_dqn.forward(context);
        let c51_mean: f32 = c51_dist
            .first()
            .map(|dist| {
                dist.par_iter()
                    .enumerate()
                    .map(|(i, &p)| p * (-1.0 + 2.0 * i as f32 / 50.0))
                    .sum::<f32>()
            })
            .unwrap_or(0.0);
        let c51_pred = (c51_mean.tanh() + 1.0) / 2.0;
        predictions.push((c51_pred.clamp(0.0, 1.0), 1.6));

        // Quantum Annealing - use spin configuration
        self.quantum_annealer.anneal_step();
        // Use first few spins as prediction (0 = loss, 1 = win)
        let quantum_spins = self.quantum_annealer.get_spin_configuration();
        let quantum_pred = quantum_spins
            .par_iter()
            .take(10)
            .map(|&s| if s > 0 { 1.0_f32 } else { 0.0_f32 })
            .sum::<f32>()
            / 10.0;
        predictions.push((quantum_pred, 0.5));

        // Meta-RL learner
        let meta_pred = self.meta_learner.forward(context, true);
        let meta_pred_val = meta_pred.first().copied().unwrap_or(0.5);
        predictions.push((meta_pred_val.clamp(0.0, 1.0), 1.3));

        // PBT - use best agent's prediction
        let pbt_best = self.pbt.best_agent();
        let pbt_pred = (pbt_best.weights.first().copied().unwrap_or(0.0).tanh() + 1.0) / 2.0;
        predictions.push((pbt_pred.clamp(0.0, 1.0), 0.6 + pbt_best.fitness.min(0.4)));

        // Safe RL - constrained prediction
        let safe_value = self.safe_rl.forward_critic(context);
        let safe_pred = (safe_value.tanh() + 1.0) / 2.0;
        // Adjust by Lagrange multiplier (higher lambda = more constrained)
        let safe_weight = 1.0 / (1.0 + self.safe_rl.lagrange_lambda);
        predictions.push((safe_pred.clamp(0.35, 0.65), safe_weight));

        // Ornstein-Uhlenbeck process - mean reverting
        let ou_value = self.ou_process.current_value;
        let ou_pred = 0.5 + (ou_value.clamp(-0.5, 0.5)); // Centered around 0.5
        predictions.push((ou_pred.clamp(0.35, 0.65), 0.5));

        // Gumbel MCTS - use win rate as prior initially
        let mcts_policy = self.gumbel_mcts.get_improved_policy();
        let mcts_pred = if self.total_bets < 30 {
            if self.total_wins + self.total_losses > 0 {
                self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
            } else {
                0.5
            }
        } else {
            mcts_policy.first().copied().unwrap_or(0.5)
        };
        predictions.push((mcts_pred.clamp(0.35, 0.65), 1.1));

        // EXP3 Bandit - use win rate initially
        let exp3_dist = self.exp3_bandit.get_distribution();
        let exp3_pred = if self.total_bets < 30 {
            if self.total_wins + self.total_losses > 0 {
                self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
            } else {
                0.5
            }
        } else {
            exp3_dist.par_iter().take(20).sum::<f32>() / 20.0
        };
        predictions.push((exp3_pred.clamp(0.35, 0.65), 0.9));

        // TCN prediction
        if self.recent_seq.len() >= 8 {
            let tcn_input: Vec<Vec<f32>> = self
                .recent_seq
                .iter()
                .take(20)
                .map(|&b| vec![if b { 1.0_f32 } else { 0.0_f32 }; 11])
                .collect();
            let tcn_out = self.tcn.forward(&tcn_input);
            let tcn_pred = tcn_out.first().copied().unwrap_or(0.5);
            predictions.push((tcn_pred.clamp(0.35, 0.65), 1.4));
        }

        // DFA (Detrended Fluctuation Analysis) as alternative Hurst
        let dfa_hurst = self.hurst.dfa();
        let dfa_pred = if dfa_hurst > 0.55 {
            // Trending - continue pattern
            if self.last_win {
                0.54
            } else {
                0.46
            }
        } else if dfa_hurst < 0.45 {
            // Mean-reverting - expect reversal
            if self.last_win {
                0.46
            } else {
                0.54
            }
        } else {
            0.5
        };
        predictions.push((dfa_pred, 0.5));

        // Transfer entropy - causal influence
        let te = self.info_theory.transfer_entropy();
        if te > 0.05 && self.total_bets > 50 {
            // Significant information transfer
            let te_pred = if self.last_win { 0.52 } else { 0.48 };
            predictions.push((te_pred, te * 2.0));
        }

        // Add the actual win rate as a baseline predictor
        if self.total_wins + self.total_losses > 20 {
            let win_rate = self.total_wins as f32 / (self.total_wins + self.total_losses) as f32;
            // Win rate is a strong signal, weight it highly
            predictions.push((win_rate.clamp(0.35, 0.65), 3.0));
        }

        // Recent win rate (last 20 bets) - very predictive
        if self.recent_seq.len() >= 10 {
            let recent_wins = self.recent_seq.par_iter().filter(|&&w| w).count() as f32;
            let recent_rate = recent_wins / self.recent_seq.len() as f32;
            predictions.push((recent_rate.clamp(0.3, 0.7), 2.5));
        }

        // Compute weighted average
        let total_weight: f32 = predictions.par_iter().map(|(_, w)| *w).sum();
        let weighted_pred: f32 =
            predictions.par_iter().map(|(p, w)| p * w).sum::<f32>() / total_weight.max(1.0);

        // Compute confidence as agreement between models
        let pred_deviations: Vec<f32> = predictions
            .par_iter()
            .map(|(p, _)| (p - weighted_pred).abs())
            .collect();
        let avg_deviation: f32 =
            pred_deviations.par_iter().sum::<f32>() / pred_deviations.len().max(1) as f32;
        let confidence = 1.0 - (avg_deviation * 4.0).min(1.0); // Lower deviation = higher confidence

        // Debug: print predictions if they seem biased
        if weighted_pred < 0.3 || weighted_pred > 0.7 {
            if self.total_bets % 100 == 0 {
                eprintln!(
                    "[PRED DEBUG] Weighted: {:.3}, preds: {}",
                    weighted_pred,
                    predictions.len()
                );
            }
        }

        (weighted_pred.clamp(0.35, 0.65), confidence.clamp(0.0, 1.0))
    }

    /// Compute scores for all arms using all AI systems
    fn compute_arm_scores(&mut self, dd: f32, ws: u32, ls: u32, mc: f32) -> Vec<f32> {
        let total_pulls: u32 = self.arms.par_iter().map(|a| a.pull_count).sum();
        let rng_vals: Vec<f32> = (0..self.arms.len()).map(|_| self.next_rng()).collect();

        // Build context for context-aware systems
        let context = self.build_context(dd, ws, ls);

        // Get predictions from various AI systems
        let linucb_best_arm = self.linucb.select_arm(&context);
        let dqn_prediction = self.dqn_agent.forward(&context);
        let policy_action = self.policy_gradient.select_action(&context);

        // State estimation from filters
        let kalman_estimate = self.kalman_filter.get_state();
        let particle_estimate = self.particle_filter.estimate();
        let state_estimate = (kalman_estimate + particle_estimate) / 2.0;

        // Volatility forecast (10-period ahead)
        let vol_forecast = self.volatility_forecaster.forecast(10);

        // Mean reversion signal
        let mr_z = self.mean_reversion.z_score();
        let mr_signal = if mr_z.abs() > 2.0 {
            mr_z.signum() * 0.5 + 0.5
        } else {
            0.5
        };
        let mr_strength = mr_z.abs() / 3.0;

        // Trend analysis
        let trend = self.trend_strength.trend_strength();

        // Regime detection
        let (regime_mult, _should_reverse) = self.regime.get_recommended_strategy();

        // Ensemble forecaster - use simple predictions based on context
        let ensemble_preds: Vec<f32> = vec![
            context.get(0).copied().unwrap_or(0.5), // drawdown
            context.get(3).copied().unwrap_or(0.5), // win rate
            context.get(4).copied().unwrap_or(0.5), // volatility
        ];
        let ensemble_pred = self.ensemble_forecaster.predict(&ensemble_preds);

        // Reservoir computing output
        let reservoir_inputs: Vec<f32> = context.iter().take(10).cloned().collect();
        self.reservoir.update(&reservoir_inputs);
        let reservoir_out = self.reservoir.output();
        let reservoir_signal = reservoir_out.get(0).copied().unwrap_or(0.5);

        // Self-attention on recent outcomes
        let attention_context = if self.recent_seq.len() >= 8 {
            let seq: Vec<f32> = self
                .recent_seq
                .iter()
                .map(|&b| if b { 1.0 } else { 0.0 })
                .collect();
            self.self_attention.predict(&seq)
        } else {
            0.5
        };

        // Gaussian process prediction for current state
        let gp_state: Vec<f32> = vec![
            self.bank / self.initial_bank.max(1e-8),
            dd,
            self.risk.volatility,
        ];
        let (_, gp_std) = self.gaussian_process.predict(&gp_state);
        let gp_uncertainty = gp_std;

        // Evolution strategies best params
        let es_best = self.evolution_strategies.get_params();
        let es_risk_adj = es_best.get(0).copied().unwrap_or(0.5);
        let es_mult_adj = es_best.get(1).copied().unwrap_or(1.0);
        let es_bet_frac = es_best.get(2).copied().unwrap_or(0.1);

        // MCTS simulation for best arm prediction
        let mcts_prediction = self
            .mcts
            .predict(&self.recent_seq.iter().copied().collect::<Vec<_>>());
        let mcts_best_arm = if mcts_prediction.0 > 0.5 {
            0
        } else {
            self.arms.len() / 2
        };

        // Markov chain prediction
        let markov_pred = self
            .markov
            .predict(&self.recent_seq.iter().copied().collect::<Vec<_>>());

        // Score each arm
        self.arms
            .iter()
            .enumerate()
            .map(|(i, arm)| {
                // Base Thompson sampling score
                let sample = arm.sample(rng_vals[i]);

                // UCB exploration bonus
                let exploration_bonus = if arm.pull_count > 0 {
                    (2.0 * (total_pulls as f32).ln() / arm.pull_count as f32).sqrt()
                } else {
                    5.0
                };

                // Theoretical win rate
                let theoretical_win_rate = (100.0 - self.house_percent) / arm.multiplier / 100.0;

                // Empirical vs theoretical blend
                let empirical_weight = (arm.pull_count as f32 / 50.0).min(0.8);
                let win_rate = arm.win_rate() * empirical_weight
                    + theoretical_win_rate * (1.0 - empirical_weight);

                // Payout ratio
                let payout_ratio = arm.multiplier - 1.0;

                // === AI System Contributions ===

                // LinUCB bonus for best arm
                let linucb_bonus = if i == linucb_best_arm { 0.4 } else { 0.0 };

                // DQN preference: higher q-values mean better action
                let dqn_pref = dqn_prediction
                    .get(i.min(dqn_prediction.len().saturating_sub(1)))
                    .copied()
                    .unwrap_or(0.0);
                let dqn_normalized = (dqn_pref.tanh() + 1.0) / 2.0; // Normalize to 0-1

                // Policy gradient preference
                let pg_pref = if i == policy_action { 0.3 } else { 0.0 };

                // Gaussian process confidence
                let gp_confidence = 1.0 / (1.0 + gp_uncertainty);

                // Volatility-adjusted score - no multiplier preference
                let vol_adj = 1.0;

                // Mean reversion bonus - no multiplier preference
                let mr_bonus = mr_strength * 0.1;

                // Trend following - no multiplier preference
                let trend_bonus = trend.abs() * 0.1;

                // MCTS bonus for best arm
                let mcts_bonus = if i == mcts_best_arm { 0.5 } else { 0.0 };

                // Markov prediction alignment
                let markov_bonus = if (i < self.arms.len() / 2 && markov_pred > 0.5)
                    || (i >= self.arms.len() / 2 && markov_pred < 0.5)
                {
                    0.1
                } else {
                    0.0
                };

                // Attention context bonus - no multiplier preference
                let sequence_bonus = (attention_context - 0.5).abs() * 0.1;

                // ES params adjustment - no multiplier preference
                let es_adj = es_mult_adj * 0.05;

                // Reservoir signal contribution
                let res_contrib = (reservoir_signal - 0.5) * 0.1 * (1.0 - dd);

                // Ensemble forecaster contribution
                let ensemble_contrib = (ensemble_pred - 0.5) * 0.1;

                // State estimate bonus (higher state = better conditions)
                let state_bonus = (state_estimate - 0.5) * 0.15;

                // Model confidence influence - equal for all multipliers
                let model_bonus = mc * 2.5 * 0.5;

                // Diversity penalty
                let pull_share = if total_pulls > 0 {
                    arm.pull_count as f32 / total_pulls as f32
                } else {
                    0.0
                };
                let diversity_penalty = if pull_share > 0.08 {
                    (pull_share - 0.08) * 10.0
                } else {
                    0.0
                };

                // GP uncertainty exploration bonus
                let exploration_gp = gp_uncertainty * 0.3;

                // Regime multiplier - no multiplier preference
                let regime_bonus = regime_mult.abs() * 0.05;

                // Combine all scores with weights
                let base_score = sample * 2.0
                    + exploration_bonus * 0.5
                    + win_rate
                    + (payout_ratio * 0.1).min(0.5);

                let ai_score = linucb_bonus
                    + dqn_normalized * 0.25
                    + pg_pref
                    + gp_confidence * 0.1
                    + mcts_bonus
                    + markov_bonus
                    + sequence_bonus
                    + mr_bonus
                    + trend_bonus
                    + ensemble_contrib
                    + res_contrib
                    + state_bonus
                    + model_bonus
                    + es_adj
                    + exploration_gp
                    + regime_bonus;

                let context_score = vol_adj - diversity_penalty;

                base_score + ai_score + context_score
            })
            .collect()
    }

    /// Parallel version of arm scoring using Rayon
    fn compute_arm_scores_parallel(
        &self,
        dd: f32,
        ws: u32,
        ls: u32,
        mc: f32,
        rng_vals: &[f32],
        linucb_best_arm: usize,
        dqn_prediction: &[f32],
        policy_action: usize,
        state_estimate: f32,
        vol_forecast: f32,
        mr_z: f32,
        trend: f32,
        regime_mult: f32,
        ensemble_pred: f32,
        reservoir_signal: f32,
        attention_context: f32,
        gp_uncertainty: f32,
        es_risk_adj: f32,
        es_mult_adj: f32,
        mcts_best_arm: usize,
        markov_pred: f32,
    ) -> Vec<f32> {
        let total_pulls: u32 = self.arms.par_iter().map(|a| a.pull_count).sum();
        let mr_signal = if mr_z.abs() > 2.0 {
            mr_z.signum() * 0.5 + 0.5
        } else {
            0.5
        };
        let mr_strength = mr_z.abs() / 3.0;
        let n_arms = self.arms.len();

        // Pre-compute shared context to avoid borrowing issues
        let house_percent = self.house_percent;

        // Parallel arm scoring
        (0..n_arms)
            .into_par_iter()
            .map(|i| {
                let arm = &self.arms[i];
                let rng_val = rng_vals.get(i).copied().unwrap_or(0.5);

                // Base Thompson sampling score
                let sample = arm.sample(rng_val);

                // UCB exploration bonus
                let exploration_bonus = if arm.pull_count > 0 {
                    (2.0 * (total_pulls as f32).ln() / arm.pull_count as f32).sqrt()
                } else {
                    5.0
                };

                // Theoretical win rate
                let theoretical_win_rate = (100.0 - house_percent) / arm.multiplier / 100.0;

                // Empirical vs theoretical blend
                let empirical_weight = (arm.pull_count as f32 / 50.0).min(0.8);
                let win_rate = arm.win_rate() * empirical_weight
                    + theoretical_win_rate * (1.0 - empirical_weight);

                // Payout ratio
                let payout_ratio = arm.multiplier - 1.0;

                // LinUCB bonus for best arm
                let linucb_bonus = if i == linucb_best_arm { 0.4 } else { 0.0 };

                // DQN preference
                let dqn_pref = dqn_prediction
                    .get(i.min(dqn_prediction.len().saturating_sub(1)))
                    .copied()
                    .unwrap_or(0.0);
                let dqn_normalized = (dqn_pref.tanh() + 1.0) / 2.0;

                // Policy gradient preference
                let pg_pref = if i == policy_action { 0.3 } else { 0.0 };

                // Gaussian process confidence
                let gp_confidence = 1.0 / (1.0 + gp_uncertainty);

                // Volatility-adjusted score - no multiplier preference
                let vol_adj = 1.0;

                // Mean reversion bonus - no multiplier preference
                let mr_bonus = mr_strength * 0.1;

                // Trend following - no multiplier preference
                let trend_bonus = trend.abs() * 0.1;

                // MCTS bonus for best arm
                let mcts_bonus = if i == mcts_best_arm { 0.5 } else { 0.0 };

                // Markov prediction alignment
                let markov_bonus = if (i < n_arms / 2 && markov_pred > 0.5)
                    || (i >= n_arms / 2 && markov_pred < 0.5)
                {
                    0.1
                } else {
                    0.0
                };

                // Attention context bonus - no multiplier preference
                let sequence_bonus = (attention_context - 0.5).abs() * 0.1;

                // ES params adjustment - no multiplier preference
                let es_adj = es_mult_adj * 0.05;

                // Reservoir signal contribution
                let res_contrib = (reservoir_signal - 0.5) * 0.1 * (1.0 - dd);

                // Ensemble forecaster contribution
                let ensemble_contrib = (ensemble_pred - 0.5) * 0.1;

                // State estimate bonus
                let state_bonus = (state_estimate - 0.5) * 0.15;

                // Model confidence influence - equal for all multipliers
                let model_bonus = mc * 2.5 * 0.5;

                // Diversity penalty
                let pull_share = if total_pulls > 0 {
                    arm.pull_count as f32 / total_pulls as f32
                } else {
                    0.0
                };
                let diversity_penalty = if pull_share > 0.08 {
                    (pull_share - 0.08) * 10.0
                } else {
                    0.0
                };

                // GP uncertainty exploration bonus
                let exploration_gp = gp_uncertainty * 0.3;

                // Regime multiplier - no multiplier preference
                let regime_bonus = regime_mult.abs() * 0.05;

                // Combine all scores
                let base_score = sample * 2.0
                    + exploration_bonus * 0.5
                    + win_rate
                    + (payout_ratio * 0.1).min(0.5);

                let ai_score = linucb_bonus
                    + dqn_normalized * 0.25
                    + pg_pref
                    + gp_confidence * 0.1
                    + mcts_bonus
                    + markov_bonus
                    + sequence_bonus
                    + mr_bonus
                    + trend_bonus
                    + ensemble_contrib
                    + res_contrib
                    + state_bonus
                    + model_bonus
                    + es_adj
                    + exploration_gp
                    + regime_bonus;

                let context_score = vol_adj - diversity_penalty;

                base_score + ai_score + context_score
            })
            .collect()
    }

    /// AI decides if should bet or skip
    fn ai_should_bet(&mut self, context: &[f32]) -> bool {
        // Don't be too conservative early on - need data to learn!
        if self.total_bets < 200 {
            return true; // Always bet during warmup
        }

        // ===== UNCERTAINTY-BASED SKIP =====
        // Cache predictions if not already done
        if !self.cached_predictions.valid {
            self.cache_predictions(context);
        }

        // Evaluate whether to skip based on uncertainty
        match self.evaluate_bet_decision() {
            BetDecision::Skip => {
                // Skip this bet due to high uncertainty
                return false;
            }
            BetDecision::Reduce => {
                // Continue but bet sizing will be reduced
                // Don't skip, just proceed with caution
            }
            BetDecision::IncreaseRisk => {
                // High confidence - proceed aggressively
            }
            BetDecision::Bet => {
                // Normal bet
            }
        }

        // ===== DRAWDOWN PROTECTION - Only this is hard skip =====
        if self.risk.drawdown > 0.35 {
            return false; // Hard stop at 35% drawdown
        }

        // ===== DREAMER IMAGINATION =====
        let imagination_results: Vec<f32> = (0..5) // Reduced from 10 for speed
            .into_par_iter()
            .map(|_| {
                let policy = |_: &[f32]| vec![0.5];
                let trajectory = self.dreamer.imagine(context, &policy, 3); // Reduced from 5
                trajectory.iter().map(|(_, r)| *r).sum::<f32>()
            })
            .collect();

        let avg_imagined_reward: f32 =
            imagination_results.iter().sum::<f32>() / imagination_results.len() as f32;

        // Only skip if strongly negative AND we have enough data
        if avg_imagined_reward < -0.5 && self.total_bets > 500 && self.next_rng() < 0.3 {
            return false;
        }

        // ===== C51 DISTRIBUTAL DQN =====
        let c51_values = self.dqn_agent.forward(context);
        let c51_mean: f32 = c51_values.par_iter().sum::<f32>() / c51_values.len().max(1) as f32;

        // More lenient threshold
        if c51_mean < -1.0 && self.total_bets > 300 && self.next_rng() < 0.2 {
            return false;
        }

        // ===== LOSS STREAK PROTECTION =====
        if self.loss_streak > 8 && self.next_rng() < 0.3 {
            return false;
        }

        // Default: bet!
        true
    }

    /// AI decides multiplier directly via neural network policy
    fn ai_select_multiplier(&mut self, context: &[f32], dd: f32) -> f32 {
        // Get DQN's preferred action (0-39 mapped to multipliers)
        let dqn_q_values = self.dqn_agent.forward(context);
        let dqn_action = dqn_q_values
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(0);

        // Policy gradient action
        let pg_action = self.policy_gradient.select_action(context);

        // Q-learning action
        let streak = if self.win_streak > 0 {
            self.win_streak as i32
        } else {
            -(self.loss_streak as i32)
        };
        let win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
        } else {
            0.5
        };
        let q_state = self
            .q_learner
            .get_state(dd.max(0.0), streak, self.risk.volatility, win_rate);
        let q_action = self.q_learner.select_action(q_state);

        // Get scores from all arms
        let scores =
            self.compute_arm_scores(dd, self.win_streak, self.loss_streak, self.last_confidence);

        // Weighted ensemble of all AI opinions
        let mut weighted_sum = 0.0_f32;
        let mut total_weight = 0.0_f32;

        for (i, arm) in self.arms.iter().enumerate() {
            let score = scores.get(i).copied().unwrap_or(0.0);
            let weight = (score * 2.0).exp(); // Softmax-like
            weighted_sum += arm.multiplier * weight;
            total_weight += weight;
        }

        let ensemble_mult = if total_weight > 0.0 {
            weighted_sum / total_weight
        } else {
            2.0
        };

        // DQN suggested multiplier
        let dqn_mult = if dqn_action < self.arms.len() {
            self.arms[dqn_action].multiplier
        } else {
            2.0
        };

        // Policy gradient suggested multiplier
        let pg_mult = if pg_action < self.arms.len() {
            self.arms[pg_action].multiplier
        } else {
            2.0
        };

        // Q-learning suggested multiplier
        let q_mults = [1.5, 2.0, 3.0, 5.0, 10.0];
        let q_mult = q_mults[q_action.min(4)];

        // Attention confidence
        let attn_confidence = if self.recent_seq.len() >= 8 {
            let seq: Vec<f32> = self
                .recent_seq
                .iter()
                .map(|&b| if b { 1.0 } else { 0.0 })
                .collect();
            let attn_out = self.self_attention.predict(&seq);
            (attn_out - 0.5).abs() * 2.0
        } else {
            0.5
        };

        // ============================================================================
        // LOWER MULTIPLIER PREFERENCE - Bias toward safer bets
        // ============================================================================
        // Calculate a preference factor that rewards lower multipliers
        // Lower multipliers have higher win probability: P(win) ≈ (100-house_edge)/mult
        // Only apply penalty if models are not confident - let models decide

        let mult_penalty = |m: f32, confident: bool| -> f32 {
            if confident {
                0.0 // Confident? No penalty - GO BIG
            } else {
                0.0 // Even without confidence, let the ensemble decide
            }
        };

        // ============================================================================
        // EXPLORATION: Encourage trying different multipliers
        // ============================================================================
        // Untrained models converge on middle values - add exploration to try all ranges
        // INCREASE exploration when losing to break out of bad patterns
        let base_exploration = if self.total_bets < 100 {
            0.5 // 50% random exploration early
        } else if self.total_bets < 500 {
            0.2 // 20% random exploration mid
        } else if self.total_bets < 2000 {
            0.1 // 10% random exploration
        } else {
            0.05 // 5% random exploration late
        };

        // Boost exploration when on a losing streak
        let loss_boost: f32 = if self.loss_streak >= 10 {
            0.4 // 40% extra exploration when on a bad streak
        } else if self.loss_streak >= 5 {
            0.2 // 20% extra exploration
        } else if self.loss_streak >= 3 {
            0.1 // 10% extra exploration
        } else {
            0.0
        };

        // ----- FEATURE 1: CURIOSITY ENGINE -----
        // Add exploration bonus based on prediction errors
        let entropy_boost = self.curiosity_engine.get_entropy_boost();
        let curiosity_boost = entropy_boost * 0.1; // Up to 10% extra exploration

        // ----- ANTI-OVERFITTING: DYNAMIC EXPLORATION BOOST -----
        // If recent performance is poor, increase exploration
        let recent_performance_boost = if self.total_bets > 100 && self.recent_returns.len() >= 50 {
            let recent: Vec<f32> = self.recent_returns.iter().rev().take(50).copied().collect();
            let recent_mean: f32 = recent.iter().sum::<f32>() / recent.len() as f32;
            // If recent mean is negative (losing), boost exploration
            if recent_mean < -0.01 {
                // Losing heavily - significant exploration boost
                (0.15 - recent_mean).min(0.25) // Cap at 25%
            } else if recent_mean < 0.0 {
                // Slight losing
                (0.05 - recent_mean).min(0.15) // Cap at 15%
            } else {
                0.0
            }
        } else {
            0.0
        };

        let exploration_rate =
            (base_exploration + loss_boost + curiosity_boost + recent_performance_boost).min(0.8);

        if self.next_rng() < exploration_rate {
            // Pick a random multiplier from the full range
            // Use log-uniform distribution to give equal weight to all orders of magnitude
            let log_min = 1.01_f32.ln(); // ln(1.01) ≈ 0.01
            let log_max = 50.0_f32.ln(); // ln(50) ≈ 3.9
            let random_log = self.next_rng() * (log_max - log_min) + log_min;
            let random_mult = random_log.exp();
            let result = random_mult.clamp(1.01, 100.0);

            // Debug: log exploration
            if self.total_bets % 50 == 0 {
                eprintln!(
                    "[EXPLORATION] Bet {} - Random multiplier: {:.2}x (exploration_rate: {:.2}, perf_boost: {:.2})",
                    self.total_bets, result, exploration_rate, recent_performance_boost
                );
            }

            return result;
        }

        // ----- FEATURE 4: LOOKAHEAD PLANNER -----
        // Use Monte Carlo planning for multiplier selection
        let win_rates: Vec<f32> = self.arms.iter().map(|a| a.win_rate()).collect();
        let mults: Vec<f32> = self.arms.iter().map(|a| a.multiplier).collect();
        let lookahead_arm = self.lookahead_planner.plan(self.bank, &win_rates, &mults);
        let lookahead_value = self.lookahead_planner.get_value_estimate(lookahead_arm);
        // This is used below in final blending

        // Blending weights
        let dqn_weight = 0.30;
        let pg_weight = 0.15;
        let q_weight = 0.15;
        let ensemble_weight = 0.25 + attn_confidence * 0.15;

        let mut final_mult = dqn_mult * dqn_weight
            + pg_mult * pg_weight
            + q_mult * q_weight
            + ensemble_mult * ensemble_weight;

        // Apply lower multiplier bias - only if models aren't confident
        let is_confident = attn_confidence > 0.6;
        let penalty = mult_penalty(final_mult, is_confident);
        let biased_mult = final_mult - penalty;

        // Skip the sweet spot pull - it was artificially constraining multipliers
        // Let the ensemble decide - no sweet spot pull
        final_mult = biased_mult;

        // Volatility adjustment
        let vol_forecast = self.volatility_forecaster.forecast(10);
        let adjusted_mult = if vol_forecast > 0.35 {
            final_mult * 0.8
        } else if vol_forecast < 0.1 {
            final_mult * 1.1
        } else {
            final_mult
        };

        // No artificial caps - just clamp to physical limits
        let adjusted_mult = adjusted_mult.clamp(1.01, 100.0);

        // Add influence from experimental algorithms
        let mut experimental_mult = final_mult;

        // C51 distributional - use best action's multiplier
        let c51_q_values = self.categorical_dqn.get_q_values(context);
        if let Some(best_action) = c51_q_values
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
        {
            let c51_mult = if best_action < self.arms.len() {
                self.arms[best_action].multiplier
            } else {
                2.0
            };
            experimental_mult = experimental_mult * 0.85 + c51_mult * 0.15;
        }

        // GP Thompson sample - suggest multiplier from predicted reward
        let gp_sample = self.gp_thompson.sample(context);
        let gp_mult = (2.0_f32 * gp_sample.clamp(-1.0, 1.0).exp())
            .max(1.1)
            .min(50.0); // Map to reasonable multiplier range
        experimental_mult = experimental_mult * 0.9 + gp_mult * 0.1;

        // Hawkes intensity - higher intensity = lower multiplier (more risk)
        let hawkes_intensity = self.hawkes.intensity(self.total_bets as f32);
        if hawkes_intensity > 1.0 {
            experimental_mult *= 0.85; // Reduce multiplier when events are clustering
        }

        // Hurst exponent adjustment
        let hurst = self.hurst.estimate_hurst();
        if hurst > 0.6 {
            // Trending - safer to use higher multipliers
            experimental_mult *= 1.05;
        } else if hurst < 0.4 {
            // Mean-reverting - safer to use lower multipliers
            experimental_mult *= 0.95;
        }

        // Safe RL - reduce multiplier if constraint is active
        if self.safe_rl.lagrange_lambda > 1.0 {
            experimental_mult *= 0.8; // Conservative when constrained
        }

        // Gumbel MCTS - get action distribution
        let mcts_policy = self.gumbel_mcts.get_improved_policy();
        let mcts_best_action = mcts_policy
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(20);
        let mcts_mult = if mcts_best_action < self.arms.len() {
            self.arms[mcts_best_action].multiplier
        } else {
            2.0
        };
        experimental_mult = experimental_mult * 0.88 + mcts_mult * 0.12;

        // EXP3 bandit
        let exp3_arm = self.exp3_bandit.select();
        let exp3_mult = if exp3_arm < self.arms.len() {
            self.arms[exp3_arm].multiplier
        } else {
            2.0
        };
        experimental_mult = experimental_mult * 0.92 + exp3_mult * 0.08;

        // PBT - use best agent's preference
        let pbt_best = self.pbt.best_agent();
        if pbt_best.weights.len() > 1 {
            // Use second weight as multiplier signal
            if let Some(&mult_signal) = pbt_best.weights.get(1) {
                let pbt_mult = (mult_signal * 10.0 + 2.0).max(1.1).min(50.0);
                experimental_mult = experimental_mult * 0.9 + pbt_mult * 0.1;
            }
        }

        // Quantum annealer - use spin configuration
        let quantum_spins = self.quantum_annealer.get_spin_configuration();
        let quantum_high = quantum_spins
            .par_iter()
            .take(20)
            .filter(|&&s| s > 0)
            .count();
        // More high spins = prefer higher multiplier
        let quantum_mult_boost = (quantum_high as f32 / 20.0 - 0.5) * 0.2;
        experimental_mult *= 1.0 + quantum_mult_boost;

        // OU process for multiplier adjustment
        let ou_value = self.ou_process.current_value;
        if ou_value > 0.7 {
            experimental_mult *= 1.05; // Above mean - slightly aggressive
        } else if ou_value < 0.3 {
            experimental_mult *= 0.95; // Below mean - conservative
        }

        // Meta-RL learner suggestion
        let meta_out = self.meta_learner.forward(context, true);
        if meta_out.len() > 1 {
            if let Some(&meta_signal) = meta_out.get(1) {
                let meta_mult = (meta_signal * 5.0 + 2.0).max(1.1).min(20.0);
                experimental_mult = experimental_mult * 0.9 + meta_mult * 0.1;
            }
        }

        // Final blend
        let blended_mult = experimental_mult * 0.7 + final_mult * 0.3;

        // ============================================================================
        // FINAL LOWER MULTIPLIER PREFERENCE CHECK
        // ============================================================================
        // Calculate win probability for chosen multiplier
        let win_prob_estimate = (100.0 - self.house_percent) / blended_mult / 100.0;

        // ===== REGIME-BASED MULTIPLIER ADJUSTMENT =====
        // Apply regime-specific adjustment to multiplier
        let regime_adj = if self.cached_predictions.valid {
            self.get_regime_multiplier_adjustment()
        } else {
            1.0
        };
        let blended_mult = blended_mult * regime_adj;

        // Strong streak = allow higher multipliers (models earning the right to go big)
        let streak_bonus = if self.win_streak >= 5 {
            0.25 // 5+ win streak = can go high
        } else if self.win_streak >= 3 {
            0.10 // 3+ win streak = moderate freedom
        } else {
            0.0
        };

        // High model confidence = override lower-mult bias
        let confidence_threshold = 0.60 - streak_bonus; // streak lowers threshold
        let model_confident = attn_confidence > confidence_threshold;

        // If win probability is below 30%, reconsider (unless confident or recovering)
        // This means multipliers above ~23x are discouraged without confidence
        let final_mult = if win_prob_estimate < 0.30 && dd < 0.15 && !model_confident {
            // Not in recovery, low win prob, low confidence - pull toward safer bet
            let safe_mult = 2.5; // Default to 2.5x when models go too aggressive
            let caution_factor = 0.5; // How much to pull toward safe
            blended_mult * (1.0 - caution_factor) + safe_mult * caution_factor
        } else if win_prob_estimate < 0.20 && dd >= 0.15 && self.loss_streak >= 3 {
            // In recovery with deep losses - allow aggressive recovery bets
            blended_mult.max(3.0) // Minimum 3x for recovery attempts
        } else {
            blended_mult
        };

        // Final clamp - only enforce absolute minimum (1.01x) and reasonable maximum (100x)
        // Let the models decide everything in between
        final_mult.clamp(1.01, 100.0)
    }

    /// AI decides bet size via learned value function
    fn ai_decide_bet_size(&mut self, context: &[f32], multiplier: f32, dd: f32) -> f32 {
        // ============================================================================
        // AGGRESSIVE GAMBLING - PRESS WHEN HOT, SURVIVE WHEN COLD
        // ============================================================================

        let current_bank = self.bank;

        // ===== ULTRA EARLY GAME PROTECTION =====
        // First bets ALWAYS use tiny percentages, no matter what
        // This is critical when bank is small relative to min_bet
        if PROTECTIONS_ENABLED && self.total_bets <= 5 {
            // First 5 bets: use minimal conservative bet
            let ultra_early_pct = match multiplier {
                m if m <= 2.0 => 0.02,  // 2%
                m if m <= 3.0 => 0.015, // 1.5%
                m if m <= 5.0 => 0.01,  // 1%
                _ => 0.005,             // 0.5%
            };
            let early_bet = (current_bank * ultra_early_pct).max(self.min_bet);
            // Hard cap at 5% for first 5 bets
            return early_bet.min(current_bank * 0.05).max(self.min_bet);
        } else if PROTECTIONS_ENABLED && self.total_bets <= 10 {
            // Bets 6-10: still very conservative
            let early_pct = match multiplier {
                m if m <= 2.0 => 0.03,  // 3%
                m if m <= 3.0 => 0.025, // 2.5%
                m if m <= 5.0 => 0.015, // 1.5%
                _ => 0.01,              // 1%
            };
            let early_bet = (current_bank * early_pct).max(self.min_bet);
            // Hard cap at 8% for bets 6-10
            return early_bet.min(current_bank * 0.08).max(self.min_bet);
        } else if PROTECTIONS_ENABLED && self.total_bets <= 20 {
            // Bets 11-20: transition period
            let transition_pct = match multiplier {
                m if m <= 2.0 => 0.05,  // 5%
                m if m <= 3.0 => 0.04,  // 4%
                m if m <= 5.0 => 0.025, // 2.5%
                _ => 0.015,             // 1.5%
            };
            let transition_bet = (current_bank * transition_pct).max(self.min_bet);
            // Hard cap at 12% for bets 11-20
            return transition_bet.min(current_bank * 0.12).max(self.min_bet);
        }

        // ===== CORNERED BY MIN_BET - FIGHT OR DIE =====
        // When min_bet is close to balance, we're trapped - can only make a few bets anyway
        // Might as well be aggressive and try to escape the trap
        if PROTECTIONS_ENABLED {
            let bank_in_min_bets = current_bank / self.min_bet.max(1e-10);

            let cornered_aggression = if bank_in_min_bets < 2.0 {
                // CRITICAL: Bank < 2x min_bet - essentially busted, go ALL IN
                // We can only make 1 more min bet, so bet 50-70% to have a chance
                0.55
            } else if bank_in_min_bets < 3.0 {
                // DIRE: Only 2-3 min bets left - bet 35-50%
                0.40
            } else if bank_in_min_bets < 5.0 {
                // TRAPPED: Only 4-5 min bets left - bet 25-35%
                0.28
            } else if bank_in_min_bets < 8.0 {
                // SQUEEZED: 6-8 min bets - getting squeezed, push moderately
                0.18
            } else {
                0.0 // No cornered aggression
            };

            // Apply cornered aggression - only if there's no early game cap and confidence is decent
            if cornered_aggression > 0.0 && self.total_bets > 20 {
                let voting_confidence_q = self.voting_tracker.get_consensus_confidence();

                // Scale aggression by confidence - when cornered and confident, GO BIG
                let confidence_boost = if voting_confidence_q > 0.7 {
                    1.25 // High confidence - push harder
                } else if voting_confidence_q > 0.55 {
                    1.1 // Medium confidence
                } else if voting_confidence_q > 0.45 {
                    1.0 // Low but not terrible
                } else {
                    0.85 // Bad confidence - still fight but with slightly more caution
                };

                // Additional boost if on a win streak or recovering from drawdown
                let streak_boost = if self.win_streak >= 3 {
                    1.2
                } else if self.win_streak >= 1 {
                    1.1
                } else if self.loss_streak >= 4 {
                    1.15 // Lose streak? FIGHT BACK
                } else {
                    1.0
                };

                let final_cornered_pct = cornered_aggression * confidence_boost * streak_boost;
                return (current_bank * final_cornered_pct)
                    .min(current_bank * 0.70) // Never more than 70% even in worst case
                    .max(self.min_bet);
            }
        } // PROTECTIONS_ENABLED

        let win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
        } else {
            0.5
        };

        let peak_bank = self.session_high.max(self.initial_bank);
        let peak_dd = (peak_bank - current_bank) / peak_bank.max(1e-8);

        // ===== EARLY GAME - BUILD CONFIDENCE FIRST =====
        let early_game = self.total_bets < 30;
        let is_winning = self.win_streak >= 2 || peak_dd < 0.0;
        let is_losing = self.loss_streak >= 3 || peak_dd > 0.2;

        // ===== BASE BET - MORE AGGRESSIVE =====
        let base_pct: f32 = match multiplier {
            m if m <= 2.0 => {
                if early_game && !is_winning {
                    0.05
                } else {
                    0.14
                }
            }
            m if m <= 3.0 => {
                if early_game && !is_winning {
                    0.04
                } else {
                    0.11
                }
            }
            m if m <= 5.0 => {
                if early_game && !is_winning {
                    0.025
                } else {
                    0.07
                }
            }
            m if m <= 10.0 => {
                if early_game && !is_winning {
                    0.015
                } else {
                    0.045
                }
            }
            m if m <= 50.0 => {
                if early_game && !is_winning {
                    0.008
                } else {
                    0.025
                }
            }
            _ => {
                if early_game && !is_winning {
                    0.004
                } else {
                    0.014
                }
            }
        };

        // ===== CONFIDENCE SIGNALS =====
        let voting_confidence = self.voting_tracker.get_consensus_confidence();
        let model_confidence = if self.cached_predictions.valid {
            1.0 - self.cached_predictions.uncertainty_score
        } else {
            0.5
        };
        let ensemble_confidence = self.last_confidence;
        let combined_confidence =
            (voting_confidence * 0.4 + model_confidence * 0.4 + ensemble_confidence * 0.2);

        // ===== SESSION MATURITY =====
        let maturity = if self.total_bets < 10 {
            0.8
        } else if self.total_bets < 30 {
            1.0
        } else if self.total_bets < 100 {
            1.2
        } else {
            1.35
        };

        // ===== THE GAMBLE FACTOR =====
        let mut gamble_factor = 1.0;

        // === WIN STREAKS = PRESS HARDER ===
        if self.win_streak >= 8 {
            gamble_factor *= 5.5; // ON FIRE
        } else if self.win_streak >= 5 {
            gamble_factor *= 4.0; // HOT
        } else if self.win_streak >= 3 {
            gamble_factor *= 2.8;
        } else if self.win_streak >= 2 {
            gamble_factor *= 1.9;
        } else if self.win_streak == 1 {
            gamble_factor *= 1.35;
        }

        // === LOSS STREAKS = FIGHT BACK AGGRESSIVELY ===
        // Don't fold - push harder to recover!
        if self.loss_streak >= 8 {
            gamble_factor *= 0.75; // Fight back hard
        } else if self.loss_streak >= 6 {
            gamble_factor *= 0.85; // Don't fold, fight back
        } else if self.loss_streak >= 4 {
            gamble_factor *= 0.95;
        } else if self.loss_streak >= 3 {
            gamble_factor *= 1.0; // No reduction - stay course
        } else if self.loss_streak >= 2 {
            gamble_factor *= 1.0;
        }

        // === POSITION - AGGRESSIVE RECOVERY ===
        if peak_dd < -0.35 {
            gamble_factor *= 3.5; // HOUSE MONEY - FREE ROLL
        } else if peak_dd < -0.25 {
            gamble_factor *= 2.8; // BIG PROFIT
        } else if peak_dd < -0.15 {
            gamble_factor *= 2.2;
        } else if peak_dd < -0.1 {
            gamble_factor *= 1.7;
        } else if peak_dd < -0.05 {
            gamble_factor *= 1.4;
        } else if peak_dd < 0.0 {
            gamble_factor *= 1.2;
        } else if peak_dd > 0.5 {
            gamble_factor *= 0.85; // Deep hole - fight back HARDER
        } else if peak_dd > 0.4 {
            gamble_factor *= 0.9; // Still fighting
        } else if peak_dd > 0.35 {
            gamble_factor *= 1.0; // No reduction - push to recover
        } else if peak_dd > 0.25 {
            gamble_factor *= 1.05; // Slight boost to recover
        } else if peak_dd > 0.15 {
            gamble_factor *= 1.0;
        }

        //=== WIN RATE - RECOVERY BOOST ===
        if self.total_bets > 15 {
            if win_rate > 0.65 {
                gamble_factor *= 1.6;
            } else if win_rate > 0.55 {
                gamble_factor *= 1.25;
            } else if win_rate < 0.35 {
                // Bad win rate - PUSH HARDER to recover!
                gamble_factor *= 1.1;
            } else if win_rate < 0.42 {
                gamble_factor *= 1.0;
            }
        }

        // === RECOVERY MODE - WHEN LOSING, BE AGGRESSIVE ===
        if peak_dd > 0.15 {
            // In drawdown - FIGHT BACK
            if combined_confidence > 0.65 {
                // Models are confident even while down - trust them MORE
                gamble_factor *= 1.5;
            } else if combined_confidence > 0.5 {
                // Decent confidence - push harder
                gamble_factor *= 1.25;
            } else {
                // Even with low confidence - fight back
                gamble_factor *= 1.1;
            }
        }

        // ===== SMART FEATURE ADJUSTMENTS =====
        // Edge detector - if we have positive edge, increase bets
        if self.edge_detector.has_positive_edge() {
            gamble_factor *= self.edge_detector.get_edge_adjustment();
        }

        // Session state - adjust risk based on current situation
        gamble_factor *= self.session_state.get_state_risk_modifier();

        // Performance momentum - if improving, be more aggressive
        gamble_factor *= self.performance_momentum.get_momentum_adjustment();

        // Risk adjuster - get dynamic risk level
        let dynamic_risk = self.risk_adjuster.get_current_risk();
        gamble_factor *= dynamic_risk / 0.05; // Normalize to base risk of 5%

        // Bankroll manager recommended sizing
        let bankroll_recommended = self.bankroll_manager.get_recommended_bet_pct();
        // Blend with our calculated bet (will be applied later)

        // Win predictor - if session looks bad, be MORE aggressive to recover!
        if !self.win_predictor.should_keep_playing() && peak_dd > 0.15 {
            // Bad session AND in drawdown - FIGHT BACK HARDER
            gamble_factor *= 1.15; // Increase bets to recover
        } else if !self.win_predictor.should_keep_playing() {
            // Bad session but not in deep hole - still push
            gamble_factor *= 1.0; // No reduction
        }

        // Calibrate confidence using historical accuracy
        let calibrated_confidence = self
            .confidence_calibrator
            .get_calibrated_confidence(combined_confidence);
        // Use calibrated confidence instead of raw for boosts

        // === CONFIDENCE = BET SIZE BOOST ===
        // During recovery, confidence matters MORE
        if calibrated_confidence > 0.88 {
            if self.win_streak >= 3 {
                gamble_factor *= 5.0; // VERY confident + winning = GO BIG
            } else if peak_dd > 0.2 {
                gamble_factor *= 4.5; // VERY confident + in drawdown = RECOVER
            } else if peak_dd < 0.0 {
                gamble_factor *= 3.5;
            } else {
                gamble_factor *= 3.0;
            }
        } else if calibrated_confidence > 0.8 {
            if self.win_streak >= 2 {
                gamble_factor *= 3.5;
            } else if peak_dd > 0.15 {
                gamble_factor *= 3.0; // Confident + losing = FIGHT BACK
            } else if peak_dd <= 0.1 {
                gamble_factor *= 2.5;
            } else {
                gamble_factor *= 2.2;
            }
        } else if calibrated_confidence > 0.7 {
            if self.win_streak >= 1 {
                gamble_factor *= 2.2;
            } else if peak_dd > 0.15 {
                gamble_factor *= 1.8; // Push to recover
            } else {
                gamble_factor *= 1.5;
            }
        } else if calibrated_confidence > 0.55 {
            if peak_dd > 0.2 {
                gamble_factor *= 1.4; // Even medium confidence - push to recover
            } else {
                gamble_factor *= 1.2;
            }
        } else if calibrated_confidence > 0.4 && peak_dd > 0.25 {
            // Low confidence but deep in hole - still fight
            gamble_factor *= 1.1;
        }

        // === GAMBLER'S INSTINCT ===
        let luck_roll = self.next_rng();
        if luck_roll > 0.92
            && self.win_streak >= 2
            && peak_dd < 0.15
            && calibrated_confidence > 0.55
        {
            gamble_factor *= 2.5; // 8% chance - "I'M FEELING IT"
        } else if luck_roll > 0.80 && self.win_streak >= 1 && peak_dd <= 0.2 {
            gamble_factor *= 1.8; // 12% chance
        } else if luck_roll > 0.68 && peak_dd < 0.25 {
            gamble_factor *= 1.35; // 20% chance
        } else if luck_roll > 0.55 && peak_dd > 0.2 {
            // Recovery luck boost - more likely when losing
            gamble_factor *= 1.2; // 45% chance when in drawdown
        }

        // === STARS ALIGNED ===
        if self.win_streak >= 4 && calibrated_confidence > 0.8 && peak_dd < 0.1 && win_rate > 0.52 {
            gamble_factor *= 2.2;
        }

        // === RECOVERY LUCK - When losing, embrace variance ===
        if self.loss_streak >= 5 && luck_roll > 0.7 {
            // Due for a win - push harder
            gamble_factor *= 1.25;
        }

        // === CALCULATE TARGET ===
        let mut target_pct = base_pct * maturity * gamble_factor;

        // === MAX CAPS ===
        // Early game gets stricter caps when protections enabled
        let early_game_hard_cap: f32 = if PROTECTIONS_ENABLED && self.total_bets < 3 {
            0.04 // First 3 bets: max 4%
        } else if PROTECTIONS_ENABLED && self.total_bets < 5 {
            0.06 // Next 2 bets: max 6%
        } else if PROTECTIONS_ENABLED && self.total_bets < 10 {
            0.10 // Next 5 bets: max 10%
        } else if PROTECTIONS_ENABLED && self.total_bets < 20 {
            0.15 // Next 10 bets: max 15%
        } else {
            1.0 // No special early cap
        };

        let max_pct = if PROTECTIONS_ENABLED && peak_dd > 0.5 {
            0.50 // Deep drawdown - FIGHT BACK HARDER
        } else if PROTECTIONS_ENABLED && peak_dd > 0.4 {
            0.55 // Serious drawdown - push to recover
        } else if PROTECTIONS_ENABLED && peak_dd > 0.3 {
            0.58 // Moderate drawdown
        } else if PROTECTIONS_ENABLED && peak_dd > 0.25 {
            0.62
        } else if PROTECTIONS_ENABLED && peak_dd > 0.15 {
            0.65 // Light drawdown - can still push
        } else if peak_dd < -0.3 {
            0.80 // 30%+ profit - go big
        } else if peak_dd < -0.2 {
            0.70
        } else if peak_dd < -0.1 {
            0.58
        } else if peak_dd < -0.05 {
            0.50
        } else if peak_dd < 0.0 {
            0.45
        } else {
            0.42
        };

        // Apply early game hard cap
        let effective_max: f32 = f32::min(max_pct, early_game_hard_cap);
        target_pct = target_pct.min(effective_max);

        // Minimum bet floor
        let min_pct = self.min_bet / current_bank.max(1e-8);
        target_pct = target_pct.max(min_pct);

        let final_bet = (current_bank * target_pct)
            .max(self.min_bet)
            .min(current_bank * effective_max);

        // Survival mode - NEVER GIVE UP, FIGHT TO THE END
        // Also consider min_bet trap - if bank is small relative to min_bet, be even more aggressive
        if PROTECTIONS_ENABLED {
            let bank_in_min_bets = current_bank / self.min_bet.max(1e-10);

            if current_bank < peak_bank * 0.15 {
                // 15% of peak bank left - go ALL IN to recover or bust
                let survival_pct = if bank_in_min_bets < 4.0 {
                    0.45 // Cornered + survival = MAXIMUM AGGRESSION
                } else {
                    0.25
                };
                return (current_bank * survival_pct).max(self.min_bet);
            } else if current_bank < peak_bank * 0.25 {
                // 25% of peak - fight hard
                let survival_pct = if bank_in_min_bets < 5.0 {
                    0.35 // Cornered + survival
                } else {
                    0.20
                };
                return (current_bank * survival_pct).max(self.min_bet);
            }
        }

        final_bet
    }

    /// AI decides high/low via multiple prediction systems
    fn ai_decide_high_low(&mut self, context: &[f32]) -> bool {
        // ============================================================================
        // HIGH/LOW DECISION - BALANCED ENSEMBLE
        // ============================================================================
        // Vote Categories (normalized):
        // - Smart Direction Strategy: ~5-10 votes max per component
        // - ML Models: ~1-4 votes each (25 models = 25-100 total)
        // - Experimental: ~0.1-0.5 votes each (minor influence)
        // - Final total typically 50-150 votes

        // Start new voting round for performance tracking
        self.voting_tracker.start_new_round();

        // Update regime detection
        self.model_regime_state = self.detect_model_regime();

        // Get dynamic weights based on accuracy and regime
        let model_weights = self.get_dynamic_model_weights();
        let mut model_idx = 0; // Track which model weight to use

        let mut high_votes = 0.0_f32;
        let mut low_votes = 0.0_f32;

        // ============================================================================
        // CATEGORY 1: SMART DIRECTION STRATEGY (Max ~15 votes total)
        // ============================================================================
        // Each component uses performance-tracked weights

        let recent_rolls_len = self.recent_rolls.len();

        // Direction momentum: if one direction is winning more, weight it
        let total_dir_bets = self.high_bets + self.low_bets;
        let high_success_rate = if self.high_bets > 0 {
            self.high_wins as f32 / self.high_bets as f32
        } else {
            0.5
        };
        let low_success_rate = if self.low_bets > 0 {
            self.low_wins as f32 / self.low_bets as f32
        } else {
            0.5
        };

        // Strong direction bias (using tracked weight)
        let direction_bias = (high_success_rate - low_success_rate).abs();
        if direction_bias > 0.08 && total_dir_bets > 20 {
            // One direction is significantly better
            let direction_weight = self.voting_tracker.get_weight("direction_momentum");
            let direction_vote = (direction_bias * 25.0).min(5.0) * direction_weight / 4.0;
            if high_success_rate > low_success_rate {
                self.voting_tracker.record_vote(
                    "direction_momentum",
                    true,
                    direction_vote,
                    direction_bias,
                );
                high_votes += direction_vote;
            } else {
                self.voting_tracker.record_vote(
                    "direction_momentum",
                    false,
                    direction_vote,
                    direction_bias,
                );
                low_votes += direction_vote;
            }
        }

        // ===== ANTI-STREAK SWITCHING =====
        let anti_streak_weight = self.voting_tracker.get_weight("anti_streak");
        if recent_rolls_len >= 5 {
            let recent: Vec<u32> = self.recent_rolls.iter().rev().take(5).copied().collect();
            let recent_high_count = recent.iter().filter(|&&r| r > 5000).count();
            let recent_low_count = 5 - recent_high_count;

            // Anti-pattern: 5 same outcomes = vote opposite
            if recent_high_count == 5 {
                let vote = 1.0 * anti_streak_weight;
                self.voting_tracker
                    .record_vote("anti_streak", false, vote, 1.0);
                low_votes += vote;
            } else if recent_low_count == 5 {
                let vote = 1.0 * anti_streak_weight;
                self.voting_tracker
                    .record_vote("anti_streak", true, vote, 1.0);
                high_votes += vote;
            }

            // Trend following: 4 of 5 same direction
            let trend_weight = self.voting_tracker.get_weight("trend_follow");
            if recent_high_count >= 4 {
                let vote = 2.0 * trend_weight / 2.5;
                self.voting_tracker
                    .record_vote("trend_follow", true, vote, 0.8);
                high_votes += vote;
            } else if recent_low_count >= 4 {
                let vote = 2.0 * trend_weight / 2.5;
                self.voting_tracker
                    .record_vote("trend_follow", false, vote, 0.8);
                low_votes += vote;
            }
        }

        // ===== WIN/LOSS STREAK ON DIRECTION =====
        let streak_weight = self.voting_tracker.get_weight("direction_streak");
        if self.high_win_streak >= 3 {
            let vote = (1.5 + (self.high_win_streak as f32 * 0.15)).min(3.0) * streak_weight / 3.0;
            self.voting_tracker.record_vote(
                "direction_streak",
                true,
                vote,
                self.high_win_streak as f32 / 10.0,
            );
            high_votes += vote;
        }
        if self.low_win_streak >= 3 {
            let vote = (1.5 + (self.low_win_streak as f32 * 0.15)).min(3.0) * streak_weight / 3.0;
            self.voting_tracker.record_vote(
                "direction_streak",
                false,
                vote,
                self.low_win_streak as f32 / 10.0,
            );
            low_votes += vote;
        }

        // If losing heavily on one direction
        if total_dir_bets > 30 {
            let high_loss_rate = 1.0 - high_success_rate;
            let low_loss_rate = 1.0 - low_success_rate;
            if high_loss_rate > 0.6 {
                let vote = ((high_loss_rate - 0.5) * 5.0).min(2.0);
                low_votes += vote;
            }
            if low_loss_rate > 0.6 {
                let vote = ((low_loss_rate - 0.5) * 5.0).min(2.0);
                high_votes += vote;
            }
        }

        // ===== ROLL NUMBER ANALYSIS =====
        let roll_weight = self.voting_tracker.get_weight("roll_analysis");
        if self.recent_rolls.len() >= 10 {
            let rolls: Vec<u32> = self.recent_rolls.iter().copied().collect();
            let high_count = rolls.par_iter().filter(|&&r| r > 5000).count() as f32;
            let ratio = high_count / rolls.len() as f32;

            // Strong bias detected
            if ratio > 0.6 {
                let vote = (ratio - 0.5) * 3.0 * roll_weight / 2.0;
                self.voting_tracker.record_vote(
                    "roll_analysis",
                    true,
                    vote,
                    (ratio - 0.5).min(1.0),
                );
                high_votes += vote;
            } else if ratio < 0.4 {
                let vote = (0.5 - ratio) * 3.0 * roll_weight / 2.0;
                self.voting_tracker.record_vote(
                    "roll_analysis",
                    false,
                    vote,
                    (0.5 - ratio).min(1.0),
                );
                low_votes += vote;
            }

            // ===== ROLL VALUE ANALYSIS =====
            let mean_roll: f32 = rolls.iter().sum::<u32>() as f32 / rolls.len() as f32;
            let variance: f32 = rolls
                .iter()
                .map(|&r| (r as f32 - mean_roll).powi(2))
                .sum::<f32>()
                / rolls.len() as f32;
            let std_dev = variance.sqrt();

            // Clustering around extremes
            if mean_roll > 5500.0 && std_dev < 2000.0 {
                low_votes += 1.0;
            } else if mean_roll < 4500.0 && std_dev < 2000.0 {
                high_votes += 1.0;
            }
        }

        // ============================================================================
        // CATEGORY 2: ML MODEL VOTES (Weighted by voting_tracker + model_weights)
        // ============================================================================

        // ===== DQN AGENT (Model 0) - CORE ML MODEL =====
        let dqn_values = self.dqn_agent.forward(context);
        let dqn_avg: f32 = dqn_values.par_iter().sum::<f32>() / dqn_values.len().max(1) as f32;
        let dqn_weight =
            self.voting_tracker.get_weight("dqn") * model_weights.get(0).copied().unwrap_or(1.0);
        let dqn_confidence = dqn_avg.abs();
        let dqn_high = dqn_avg > 0.1;
        self.record_model_prediction(0, dqn_high, dqn_confidence);
        if dqn_avg > 0.1 {
            let vote = dqn_weight * (0.5 + dqn_confidence);
            self.voting_tracker
                .record_vote("dqn", true, vote, dqn_confidence);
            high_votes += vote;
        } else if dqn_avg < -0.1 {
            let vote = dqn_weight * (0.5 + dqn_confidence);
            self.voting_tracker
                .record_vote("dqn", false, vote, dqn_confidence);
            low_votes += vote;
        }

        // ===== POLICY GRADIENT (Model 1) =====
        let pg_action = self.policy_gradient.select_action(context);
        let pg_high = pg_action % 2 == 0;
        let pg_weight = self.voting_tracker.get_weight("policy_gradient")
            * model_weights.get(1).copied().unwrap_or(1.0);
        self.record_model_prediction(1, pg_high, 0.5);
        if pg_high {
            let vote = pg_weight;
            self.voting_tracker
                .record_vote("policy_gradient", true, vote, 0.5);
            high_votes += vote;
        } else {
            let vote = pg_weight;
            self.voting_tracker
                .record_vote("policy_gradient", false, vote, 0.5);
            low_votes += vote;
        }

        // ===== Q-LEARNING (Model 2) =====
        let dd = context.get(0).copied().unwrap_or(0.5);
        let streak = if self.win_streak > 0 {
            self.win_streak as i32
        } else {
            -(self.loss_streak as i32)
        };
        let win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
        } else {
            0.5
        };
        let q_state = self
            .q_learner
            .get_state(dd.max(0.0), streak, self.risk.volatility, win_rate);
        let q_action = self.q_learner.select_action(q_state);
        let q_high = q_action % 2 == 0;
        let q_weight = self.voting_tracker.get_weight("q_learning")
            * model_weights.get(2).copied().unwrap_or(1.0);
        self.record_model_prediction(2, q_high, 0.5);
        if q_high {
            let vote = q_weight;
            self.voting_tracker
                .record_vote("q_learning", true, vote, 0.5);
            high_votes += vote;
        } else {
            let vote = q_weight;
            self.voting_tracker
                .record_vote("q_learning", false, vote, 0.5);
            low_votes += vote;
        }

        // ===== LSTM SEQUENCE MODEL (Model 3) =====
        let lstm_weight =
            self.voting_tracker.get_weight("lstm") * model_weights.get(3).copied().unwrap_or(1.5);
        if self.recent_rolls.len() >= 5 {
            let lstm_seq: Vec<f32> = self
                .recent_rolls
                .iter()
                .map(|&r| r as f32 / 10000.0)
                .collect();
            let lstm_out = self.lstm_model.process_sequence(&lstm_seq);
            let lstm_pred = lstm_out.first().copied().unwrap_or(0.5);
            let confidence = (lstm_pred - 0.5).abs() * 2.0;
            let lstm_high = lstm_pred > 0.5;
            self.record_model_prediction(3, lstm_high, confidence);
            let high_vote = lstm_pred * lstm_weight * (0.5 + confidence);
            let low_vote = (1.0 - lstm_pred) * lstm_weight * (0.5 + confidence);
            self.voting_tracker
                .record_vote("lstm", lstm_high, high_vote.max(low_vote), confidence);
            high_votes += high_vote;
            low_votes += low_vote;
        }

        // ===== SELF-ATTENTION (Model 4) =====
        let attn_weight = self.voting_tracker.get_weight("attention")
            * model_weights.get(4).copied().unwrap_or(1.0);
        if self.recent_rolls.len() >= 8 {
            let seq: Vec<f32> = self
                .recent_rolls
                .iter()
                .map(|&r| r as f32 / 10000.0)
                .collect();
            let attn_pred = self.self_attention.predict(&seq);
            let confidence = (attn_pred - 0.5).abs() * 2.0;
            let attn_high = attn_pred > 0.5;
            self.record_model_prediction(4, attn_high, confidence);
            let high_vote = attn_pred * attn_weight * (0.5 + confidence);
            let low_vote = (1.0 - attn_pred) * attn_weight * (0.5 + confidence);
            self.voting_tracker.record_vote(
                "attention",
                attn_high,
                high_vote.max(low_vote),
                confidence,
            );
            high_votes += high_vote;
            low_votes += low_vote;
        }

        // ===== MARKOV CHAIN (Model 5) =====
        let markov_pred = self
            .markov
            .predict(&self.recent_seq.iter().copied().collect::<Vec<_>>());
        let markov_weight =
            self.voting_tracker.get_weight("markov") * model_weights.get(5).copied().unwrap_or(1.0);
        let markov_confidence = (markov_pred - 0.5).abs() * 2.0;
        let markov_high = markov_pred > 0.5;
        self.record_model_prediction(5, markov_high, markov_confidence);
        if markov_pred > 0.5 {
            let vote = markov_pred * markov_weight * (0.5 + markov_confidence);
            self.voting_tracker
                .record_vote("markov", true, vote, markov_confidence);
            high_votes += vote;
        } else {
            let vote = (1.0 - markov_pred) * markov_weight * (0.5 + markov_confidence);
            self.voting_tracker
                .record_vote("markov", false, vote, markov_confidence);
            low_votes += vote;
        }

        // ===== PATTERN MEMORY (Model 6) =====
        let (pattern_wins, pattern_losses, _) = self
            .patterns
            .find_similar(&self.recent_seq.iter().copied().collect::<Vec<_>>(), 5);
        let pattern_total = pattern_wins + pattern_losses;
        if pattern_total >= 5 {
            let pattern_rate = pattern_wins as f32 / pattern_total as f32;
            let pattern_weight = self.voting_tracker.get_weight("pattern")
                * model_weights.get(6).copied().unwrap_or(1.0);
            let pattern_confidence = (pattern_rate - 0.5).abs() * 2.0;
            let pattern_high = pattern_rate > 0.5;
            self.record_model_prediction(6, pattern_high, pattern_confidence);
            let high_vote = pattern_rate * (pattern_total as f32 / 20.0).min(1.0) * pattern_weight;
            let low_vote =
                (1.0 - pattern_rate) * (pattern_total as f32 / 20.0).min(1.0) * pattern_weight;
            self.voting_tracker.record_vote(
                "pattern",
                pattern_high,
                high_vote.max(low_vote),
                pattern_confidence,
            );
            high_votes += high_vote;
            low_votes += low_vote;
        }

        // ===== CONTRASTIVE LEARNING (Model 7) =====
        let contrastive_pred = self.contrastive.predict_outcome(context);
        let contrastive_weight = self.voting_tracker.get_weight("contrastive")
            * model_weights.get(7).copied().unwrap_or(1.0);
        let contrastive_confidence = (contrastive_pred - 0.5).abs() * 2.0;
        let contrastive_high = contrastive_pred > 0.5;
        self.record_model_prediction(7, contrastive_high, contrastive_confidence);
        let high_vote = contrastive_pred * contrastive_weight * (0.5 + contrastive_confidence);
        let low_vote =
            (1.0 - contrastive_pred) * contrastive_weight * (0.5 + contrastive_confidence);
        self.voting_tracker.record_vote(
            "contrastive",
            contrastive_high,
            high_vote.max(low_vote),
            contrastive_confidence,
        );
        high_votes += high_vote;
        low_votes += low_vote;

        // ===== KALMAN & PARTICLE FILTER (Model 8) =====
        let kalman_state = self.kalman_filter.get_state();
        let particle_state = self.particle_filter.estimate();
        let state_estimate = (kalman_state + particle_state) / 2.0;
        let filter_weight =
            self.voting_tracker.get_weight("kalman") * model_weights.get(8).copied().unwrap_or(1.0);
        let filter_confidence = (state_estimate - 0.5).abs() * 2.0;
        let filter_high = state_estimate > 0.5;
        self.record_model_prediction(8, filter_high, filter_confidence);
        if state_estimate > 0.55 {
            let vote = filter_weight * (0.5 + filter_confidence);
            self.voting_tracker
                .record_vote("kalman", true, vote, filter_confidence);
            high_votes += vote;
        } else if state_estimate < 0.45 {
            let vote = filter_weight * (0.5 + filter_confidence);
            self.voting_tracker
                .record_vote("kalman", false, vote, filter_confidence);
            low_votes += vote;
        }

        // ===== GAUSSIAN PROCESS (Model 9) =====
        let gp_state = vec![
            self.bank / self.initial_bank.max(1e-8),
            dd,
            self.risk.volatility,
        ];
        let (gp_mean, gp_var) = self.gaussian_process.predict(&gp_state);
        let gp_confidence = 1.0 / (1.0 + gp_var);
        let gp_weight = self.voting_tracker.get_weight("gaussian")
            * model_weights.get(9).copied().unwrap_or(2.0);
        let gp_high = gp_mean > 0.5;
        self.record_model_prediction(9, gp_high, gp_confidence);
        if gp_mean > 0.5 {
            let vote = (gp_mean - 0.5) * gp_confidence * gp_weight;
            self.voting_tracker
                .record_vote("gaussian", true, vote, gp_confidence);
            high_votes += vote;
        } else {
            let vote = (0.5 - gp_mean) * gp_confidence * gp_weight;
            self.voting_tracker
                .record_vote("gaussian", false, vote, gp_confidence);
            low_votes += vote;
        }

        // ===== TRANSFORMER (Model 10) - CORE ML MODEL =====
        let transformer_weight = self.voting_tracker.get_weight("transformer")
            * model_weights.get(10).copied().unwrap_or(2.5);
        if self.recent_rolls.len() >= 10 {
            let transformer_input: Vec<Vec<f32>> = self
                .recent_rolls
                .iter()
                .take(32)
                .map(|&r| vec![r as f32 / 10000.0; 32])
                .collect();
            let transformer_pred = self.transformer.predict(&transformer_input);
            let confidence = (transformer_pred - 0.5).abs() * 2.0;
            let transformer_high = transformer_pred > 0.5;
            self.record_model_prediction(10, transformer_high, confidence);
            let high_vote = transformer_pred * transformer_weight * (0.5 + confidence) * 1.4;
            let low_vote = (1.0 - transformer_pred) * transformer_weight * (0.5 + confidence) * 1.4;
            self.voting_tracker.record_vote(
                "transformer",
                transformer_high,
                high_vote.max(low_vote),
                confidence,
            );
            high_votes += high_vote;
            low_votes += low_vote;
        }

        // ===== VAE (Model 11) =====
        let vae_latent = self.vae.get_latent(context);
        let vae_weight =
            self.voting_tracker.get_weight("vae") * model_weights.get(11).copied().unwrap_or(1.2);
        if let Some(&vae_val) = vae_latent.first() {
            let confidence = vae_val.abs().min(1.0);
            let vae_high = vae_val > 0.0;
            self.record_model_prediction(11, vae_high, confidence);
            if vae_val > 0.0 {
                let vote = vae_val.abs().min(1.0) * vae_weight * 1.3;
                self.voting_tracker
                    .record_vote("vae", true, vote, confidence);
                high_votes += vote;
            } else {
                let vote = vae_val.abs().min(1.0) * vae_weight * 1.3;
                self.voting_tracker
                    .record_vote("vae", false, vote, confidence);
                low_votes += vote;
            }
        }

        // ===== NEURAL TURING MACHINE (Model 12) =====
        let ntm_memory = self.ntm.forward(context);
        let ntm_weight =
            self.voting_tracker.get_weight("ntm") * model_weights.get(12).copied().unwrap_or(1.0);
        if let Some(&ntm_val) = ntm_memory.first() {
            let confidence = (ntm_val - 0.5).abs() * 2.0;
            let ntm_high = ntm_val > 0.5;
            self.record_model_prediction(12, ntm_high, confidence);
            if ntm_val > 0.5 {
                let vote = ntm_weight * (0.5 + confidence) * 1.2;
                self.voting_tracker
                    .record_vote("ntm", true, vote, confidence);
                high_votes += vote;
            } else {
                let vote = ntm_weight * (0.5 + confidence) * 1.2;
                self.voting_tracker
                    .record_vote("ntm", false, vote, confidence);
                low_votes += vote;
            }
        }

        // ===== HAWKES PROCESS (Model 13) =====
        let hawkes_weight = self.voting_tracker.get_weight("hawkes")
            * model_weights.get(13).copied().unwrap_or(0.4);
        if self.recent_rolls.len() >= 3 {
            let recent_high = self
                .recent_rolls
                .iter()
                .rev()
                .take(3)
                .filter(|&&r| r > 5000)
                .count();
            let hawkes_pred = recent_high >= 2;
            self.record_model_prediction(13, hawkes_pred, 0.3);
            if recent_high >= 2 {
                self.voting_tracker
                    .record_vote("hawkes", true, hawkes_weight, 0.3);
                high_votes += hawkes_weight;
            } else {
                self.voting_tracker
                    .record_vote("hawkes", false, hawkes_weight, 0.3);
                low_votes += hawkes_weight;
            }
        }

        // ===== HURST EXPONENT (Model 14 - Trending Regime Boost) =====
        let hurst = self.hurst.estimate_hurst();
        let hurst_weight =
            self.voting_tracker.get_weight("hurst") * model_weights.get(14).copied().unwrap_or(0.5);
        if hurst > 0.55 {
            // Trending - follow the trend
            if self.recent_rolls.len() >= 5 {
                let recent_high = self
                    .recent_rolls
                    .iter()
                    .rev()
                    .take(5)
                    .filter(|&&r| r > 5000)
                    .count();
                let hurst_pred = recent_high >= 3;
                let confidence = (hurst - 0.5) * 2.0;
                self.record_model_prediction(14, hurst_pred, confidence);
                if recent_high >= 3 {
                    let vote = hurst_weight * (0.5 + (hurst - 0.5));
                    self.voting_tracker
                        .record_vote("hurst", true, vote, confidence);
                    high_votes += vote;
                } else {
                    let vote = hurst_weight * (0.5 + (hurst - 0.5));
                    self.voting_tracker
                        .record_vote("hurst", false, vote, confidence);
                    low_votes += vote;
                }
            }
        } else if hurst < 0.45 {
            // Mean-reverting - go opposite recent
            if self.recent_rolls.len() >= 5 {
                let recent_high = self
                    .recent_rolls
                    .iter()
                    .rev()
                    .take(5)
                    .filter(|&&r| r > 5000)
                    .count();
                let hurst_pred = recent_high < 3; // Opposite
                let confidence = (0.5 - hurst) * 2.0;
                self.record_model_prediction(14, hurst_pred, confidence);
                if recent_high >= 3 {
                    let vote = hurst_weight * (0.5 + (0.5 - hurst));
                    self.voting_tracker
                        .record_vote("hurst", false, vote, confidence);
                    low_votes += vote;
                } else {
                    let vote = hurst_weight * (0.5 + (0.5 - hurst));
                    self.voting_tracker
                        .record_vote("hurst", true, vote, confidence);
                    high_votes += vote;
                }
            }
        }

        // ===== ENTROPY (Model 15 - Confidence Modifier) =====
        let entropy = self.info_theory.entropy();
        let entropy_weight = self.voting_tracker.get_weight("entropy")
            * model_weights.get(15).copied().unwrap_or(1.0);
        if entropy < 0.5 {
            // Low entropy = predictable, trust models more
            high_votes *= 1.1 * entropy_weight.max(1.0);
            low_votes *= 1.1 * entropy_weight.max(1.0);
        } else if entropy > 0.9 {
            // High entropy = unpredictable, add randomness
            let rand_high = self.next_rng() < 0.5;
            self.record_model_prediction(15, rand_high, 0.1);
            self.voting_tracker
                .record_vote("entropy", rand_high, 0.1, 0.1);
            if self.next_rng() < 0.3 {
                return self.next_rng() < 0.5;
            }
        }

        // ===== TRANSFER ENTROPY (Model 16) =====
        let te = self.info_theory.transfer_entropy();
        let te_weight = self.voting_tracker.get_weight("transfer_entropy")
            * model_weights.get(16).copied().unwrap_or(3.0);
        if te > 0.05 {
            // Significant information flow
            self.record_model_prediction(16, te > 0.05, te.min(1.0));
            self.voting_tracker
                .record_vote("transfer_entropy", true, te * te_weight, te.min(1.0));
            high_votes += te * te_weight;
        }

        // ===== CATEGORICAL DQN (Model 17) =====
        let c51_dist = self.categorical_dqn.forward(context);
        let c51_weight = self.voting_tracker.get_weight("categorical_dqn")
            * model_weights.get(17).copied().unwrap_or(1.2);
        if let Some(dist) = c51_dist.first() {
            let c51_mean: f32 = dist
                .par_iter()
                .enumerate()
                .map(|(i, &p)| p * (-1.0 + 2.0 * i as f32 / 50.0))
                .sum();
            let c51_pred = c51_mean > 0.0;
            let confidence = c51_mean.abs().min(1.0);
            self.record_model_prediction(17, c51_pred, confidence);
            if c51_mean > 0.0 {
                let vote = c51_mean.min(1.0) * c51_weight;
                self.voting_tracker
                    .record_vote("categorical_dqn", true, vote, confidence);
                high_votes += vote;
            } else {
                let vote = c51_mean.abs().min(1.0) * c51_weight;
                self.voting_tracker
                    .record_vote("categorical_dqn", false, vote, confidence);
                low_votes += vote;
            }
        }

        // ===== GP THOMPSON SAMPLING (Model 18) =====
        let (gp_th_mean, _gp_th_var) = self.gp_thompson.predict(context);
        let gp_th_sample = self.gp_thompson.sample(context);
        let gp_th_weight = self.voting_tracker.get_weight("gp_thompson")
            * model_weights.get(18).copied().unwrap_or(0.8);
        let gp_th_pred = gp_th_sample > 0.0;
        let gp_th_confidence = gp_th_sample.abs().min(1.0);
        self.record_model_prediction(18, gp_th_pred, gp_th_confidence);
        if gp_th_sample > 0.0 {
            let vote = gp_th_sample.min(1.0) * gp_th_weight;
            self.voting_tracker
                .record_vote("gp_thompson", true, vote, gp_th_confidence);
            high_votes += vote;
        } else {
            let vote = gp_th_sample.abs().min(1.0) * gp_th_weight;
            self.voting_tracker
                .record_vote("gp_thompson", false, vote, gp_th_confidence);
            low_votes += vote;
        }

        // ===== QUANTUM ANNEALER (Model 19) =====
        let quantum_spins = self.quantum_annealer.get_spin_configuration();
        let quantum_high = quantum_spins
            .par_iter()
            .take(10)
            .filter(|&&s| s > 0)
            .count();
        let quantum_weight = self.voting_tracker.get_weight("quantum")
            * model_weights.get(19).copied().unwrap_or(0.4);
        let quantum_pred = quantum_high > 5;
        let quantum_confidence = (quantum_high as f32 / 10.0 - 0.5).abs() * 2.0;
        self.record_model_prediction(19, quantum_pred, quantum_confidence);
        if quantum_high > 5 {
            self.voting_tracker
                .record_vote("quantum", true, quantum_weight, quantum_confidence);
            high_votes += quantum_weight;
        } else {
            self.voting_tracker
                .record_vote("quantum", false, quantum_weight, quantum_confidence);
            low_votes += quantum_weight;
        }

        // ===== META RL (Model 20) =====
        let meta_pred = self.meta_learner.forward(context, true);
        let meta_weight = self.voting_tracker.get_weight("meta_rl")
            * model_weights.get(20).copied().unwrap_or(1.3);
        if let Some(&meta_val) = meta_pred.first() {
            let meta_confidence = (meta_val - 0.5).abs() * 2.0;
            let meta_high = meta_val > 0.5;
            self.record_model_prediction(20, meta_high, meta_confidence);
            if meta_val > 0.5 {
                let vote = (meta_val - 0.5) * meta_weight * (0.5 + meta_confidence);
                self.voting_tracker
                    .record_vote("meta_rl", true, vote, meta_confidence);
                high_votes += vote;
            } else {
                let vote = (0.5 - meta_val) * meta_weight * (0.5 + meta_confidence);
                self.voting_tracker
                    .record_vote("meta_rl", false, vote, meta_confidence);
                low_votes += vote;
            }
        }

        // ===== PBT BEST AGENT (Model 21) =====
        let pbt_best = self.pbt.best_agent();
        let pbt_weight =
            self.voting_tracker.get_weight("pbt") * model_weights.get(21).copied().unwrap_or(0.5);
        if let Some(&pbt_w) = pbt_best.weights.first() {
            let pbt_pred = pbt_w > 0.0;
            self.record_model_prediction(21, pbt_pred, pbt_w.abs());
            if pbt_w > 0.0 {
                self.voting_tracker
                    .record_vote("pbt", true, pbt_weight, pbt_w.abs());
                high_votes += pbt_weight;
            } else {
                self.voting_tracker
                    .record_vote("pbt", false, pbt_weight, pbt_w.abs());
                low_votes += pbt_weight;
            }
        }

        // ===== OU PROCESS (Model 22) =====
        let ou_value = self.ou_process.current_value;
        let ou_weight =
            self.voting_tracker.get_weight("ou") * model_weights.get(22).copied().unwrap_or(0.3);
        let ou_high = ou_value < 0.5;
        self.record_model_prediction(22, ou_high, (ou_value - 0.5).abs() * 2.0);
        if ou_value > 0.6 {
            self.voting_tracker
                .record_vote("ou", false, ou_weight, (ou_value - 0.5).abs() * 2.0);
            low_votes += ou_weight;
        } else if ou_value < 0.4 {
            self.voting_tracker
                .record_vote("ou", true, ou_weight, (ou_value - 0.5).abs() * 2.0);
            high_votes += ou_weight;
        }

        // ===== TCN (Model 23) =====
        let tcn_weight =
            self.voting_tracker.get_weight("tcn") * model_weights.get(23).copied().unwrap_or(1.1);
        if self.recent_rolls.len() >= 8 {
            let tcn_input: Vec<Vec<f32>> = self
                .recent_rolls
                .iter()
                .take(20)
                .map(|&r| vec![r as f32 / 10000.0; 11])
                .collect();
            let tcn_out = self.tcn.forward(&tcn_input);
            if let Some(&tcn_val) = tcn_out.first() {
                let confidence = (tcn_val - 0.5).abs() * 2.0;
                let tcn_high = tcn_val > 0.5;
                self.record_model_prediction(23, tcn_high, confidence);
                let high_vote = tcn_val * tcn_weight * (0.5 + confidence);
                let low_vote = (1.0 - tcn_val) * tcn_weight * (0.5 + confidence);
                self.voting_tracker.record_vote(
                    "tcn",
                    tcn_high,
                    high_vote.max(low_vote),
                    confidence,
                );
                high_votes += high_vote;
                low_votes += low_vote;
            }
        }

        // ===== GUMBEL MCTS (Model 24) =====
        let mcts_policy = self.gumbel_mcts.get_improved_policy();
        let low_mult_weight: f32 = mcts_policy.par_iter().take(20).sum();
        let mcts_pred = low_mult_weight > 0.5;
        let mcts_weight =
            self.voting_tracker.get_weight("mcts") * model_weights.get(24).copied().unwrap_or(0.6);
        let mcts_confidence = (low_mult_weight - 0.5).abs() * 2.0;
        self.record_model_prediction(24, mcts_pred, mcts_confidence);
        if low_mult_weight > 0.5 {
            self.voting_tracker
                .record_vote("mcts", true, mcts_weight, mcts_confidence);
            high_votes += mcts_weight;
        } else {
            self.voting_tracker
                .record_vote("mcts", false, mcts_weight, mcts_confidence);
            low_votes += mcts_weight;
        }

        // ===== EXP3 BANDIT =====
        let exp3_dist = self.exp3_bandit.get_distribution();
        let exp3_first: f32 = exp3_dist.par_iter().take(20).sum();
        if exp3_first > 0.5 {
            self.voting_tracker.record_vote("exp3", true, 0.5, 0.3);
            high_votes += 0.5;
        } else {
            self.voting_tracker.record_vote("exp3", false, 0.5, 0.3);
            low_votes += 0.5;
        }

        // ============================================================================
        // EXPERIMENTAL / FUN DETECTION METHODS
        // ============================================================================
        // These are unconventional but may capture patterns traditional methods miss

        // ===== HOT/COLD NUMBER RANGES =====
        // Track which number ranges are "hot" (appearing more than expected)
        let hot_cold_weight = self.voting_tracker.get_weight("hot_cold");
        if self.recent_rolls.len() >= 20 {
            let rolls: Vec<u32> = self.recent_rolls.iter().rev().take(20).copied().collect();

            // Count in 10 bins (0-999, 1000-1999, ..., 9000-9999)
            let mut bins = [0u32; 10];
            for &r in &rolls {
                let bin = (r / 1000).min(9) as usize;
                bins[bin] += 1;
            }

            // Find hottest and coldest bins
            let max_bin = bins.iter().max().copied().unwrap_or(0);
            let min_bin = bins.iter().min().copied().unwrap_or(0);

            // If bins 0-4 (lower half) are hot, bias LOW
            let low_heat: u32 = bins[0..5].iter().sum();
            let high_heat: u32 = bins[5..10].iter().sum();

            if low_heat > high_heat + 4 {
                let vote = 0.8 * hot_cold_weight;
                self.voting_tracker
                    .record_vote("hot_cold", false, vote, 0.3);
                low_votes += vote;
            } else if high_heat > low_heat + 4 {
                let vote = 0.8 * hot_cold_weight;
                self.voting_tracker.record_vote("hot_cold", true, vote, 0.3);
                high_votes += vote;
            }
        }

        // ===== PRIME NUMBER BIAS =====
        // Check if prime sum rolls correlate with outcomes
        let primes_weight = self.voting_tracker.get_weight("primes");
        if self.recent_rolls.len() >= 10 {
            let rolls: Vec<u32> = self.recent_rolls.iter().rev().take(10).copied().collect();
            let primes_in_last_10: usize = rolls
                .iter()
                .filter(|&&r| {
                    let n = r % 100; // Use mod 100 for prime check
                    n == 2
                        || n == 3
                        || n == 5
                        || n == 7
                        || n == 11
                        || n == 13
                        || n == 17
                        || n == 19
                        || n == 23
                        || n == 29
                        || n == 31
                        || n == 37
                        || n == 41
                        || n == 43
                        || n == 47
                        || n == 53
                        || n == 59
                        || n == 61
                        || n == 67
                        || n == 71
                        || n == 73
                        || n == 79
                        || n == 83
                        || n == 89
                        || n == 97
                })
                .count();

            // Fun: if many primes appeared, slight HIGH bias (arbitrary but fun)
            if primes_in_last_10 >= 5 {
                let vote = 0.3 * (primes_in_last_10 as f32 - 4.0) * primes_weight;
                self.voting_tracker.record_vote("primes", true, vote, 0.2);
                high_votes += vote;
            } else if primes_in_last_10 <= 2 {
                let vote = 0.3 * (3.0 - primes_in_last_10 as f32) * primes_weight;
                self.voting_tracker.record_vote("primes", false, vote, 0.2);
                low_votes += vote;
            }
        }

        // ===== FIBONACCI PATTERN DETECTION =====
        // Check if recent rolls show Fibonacci-like sequences
        let fib_weight = self.voting_tracker.get_weight("fibonacci");
        if self.recent_rolls.len() >= 5 {
            let rolls: Vec<u32> = self.recent_rolls.iter().rev().take(5).copied().collect();
            // Fibonacci ratios: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55...
            // Check if differences follow fibonacci-ish patterns
            let diffs: Vec<i32> = rolls
                .windows(2)
                .map(|w| (w[1] as i32 - w[0] as i32).abs())
                .collect();

            // If differences are small and oscillating, might indicate pattern
            let avg_diff: f32 = diffs.iter().sum::<i32>() as f32 / diffs.len().max(1) as f32;
            if avg_diff < 500.0 {
                // Small oscillations - might be in a pattern, go with trend
                let trend_high = rolls.iter().rev().take(3).filter(|&&r| r > 5000).count();
                if trend_high >= 2 {
                    let vote = 0.4 * fib_weight;
                    self.voting_tracker
                        .record_vote("fibonacci", true, vote, 0.2);
                    high_votes += vote;
                } else {
                    let vote = 0.4 * fib_weight;
                    self.voting_tracker
                        .record_vote("fibonacci", false, vote, 0.2);
                    low_votes += vote;
                }
            }
        }

        // ===== GOLDEN RATIO PREDICTION =====
        // Use φ (1.618...) in prediction
        const PHI: f32 = 1.618033988749;
        let golden_weight = self.voting_tracker.get_weight("golden_ratio");
        let golden_bet = (self.total_bets as f32 * PHI) % 1.0;
        if golden_bet < 0.5 {
            let vote = 0.15 * golden_weight;
            self.voting_tracker
                .record_vote("golden_ratio", true, vote, 0.1);
            high_votes += vote;
        } else {
            let vote = 0.05 * golden_weight;
            self.voting_tracker
                .record_vote("golden_ratio", false, vote, 0.1);
            low_votes += vote;
        }

        // ===== BIRTHDAY PARADOX DETECTION =====
        let birthday_weight = self.voting_tracker.get_weight("birthday_paradox");
        if self.recent_rolls.len() >= 30 {
            let rolls: Vec<u32> = self.recent_rolls.iter().rev().take(30).copied().collect();
            let mut seen = std::collections::HashSet::new();
            let mut repeats = 0;
            for &r in &rolls {
                let bucket = r / 100;
                if !seen.insert(bucket) {
                    repeats += 1;
                }
            }
            if repeats >= 3 {
                let recent_high = rolls.iter().rev().take(5).filter(|&&r| r > 5000).count();
                if recent_high >= 3 {
                    let vote = 0.08 * birthday_weight;
                    self.voting_tracker
                        .record_vote("birthday_paradox", true, vote, 0.1);
                    high_votes += vote;
                } else {
                    let vote = 0.08 * birthday_weight;
                    self.voting_tracker
                        .record_vote("birthday_paradox", false, vote, 0.1);
                    low_votes += vote;
                }
            }
        }

        // ===== PSYCHIC MOMENTS (REDUCED) =====
        let psychic_weight = self.voting_tracker.get_weight("psychic");
        let psychic_chance = if self.win_streak >= 5 {
            0.03
        } else if self.loss_streak >= 5 {
            0.01
        } else {
            0.02
        };
        if self.next_rng() < psychic_chance {
            let psychic_high = self.next_rng() < 0.5;
            let vote = 0.3 * psychic_weight;
            self.voting_tracker
                .record_vote("psychic", psychic_high, vote, 0.1);
            if psychic_high {
                high_votes += vote;
            } else {
                low_votes += vote;
            }
        }

        // ===== MODULO PATTERN =====
        let modulo_weight = self.voting_tracker.get_weight("modulo");
        let bet_mod_7 = self.total_bets % 7;
        let modulo_high = bet_mod_7 == 0 || bet_mod_7 == 3 || bet_mod_7 == 5;
        if modulo_high {
            let vote = 0.02 * modulo_weight;
            self.voting_tracker.record_vote("modulo", true, vote, 0.05);
            high_votes += vote;
        } else {
            let vote = 0.01 * modulo_weight;
            self.voting_tracker.record_vote("modulo", false, vote, 0.05);
            low_votes += vote;
        }

        // ===== CHAOS INDICATOR =====
        let chaos_weight = self.voting_tracker.get_weight("chaos");
        if self.recent_rolls.len() >= 10 {
            let rolls: Vec<f32> = self
                .recent_rolls
                .iter()
                .rev()
                .take(10)
                .map(|&r| r as f32)
                .collect();
            let mut lyapunov_sum = 0.0;
            for i in 1..rolls.len() {
                let diff = (rolls[i] - rolls[i - 1]).abs().ln().max(-10.0);
                lyapunov_sum += diff;
            }
            let lyapunov = lyapunov_sum / 9.0;
            if lyapunov > 1.0 {
                let chaos_high = self.next_rng() > 0.5;
                let vote = 0.15 * chaos_weight;
                self.voting_tracker
                    .record_vote("chaos", chaos_high, vote, 0.1);
                if chaos_high {
                    high_votes += vote;
                } else {
                    low_votes += vote;
                }
            } else if lyapunov < 0.0 {
                // Stable/predictable - follow trend more confidently
                let trend_high = rolls.iter().rev().take(3).filter(|&&r| r > 5000.0).count();
                if trend_high >= 2 {
                    let vote = 0.4 * chaos_weight;
                    self.voting_tracker.record_vote("chaos", true, vote, 0.3);
                    high_votes += vote;
                } else {
                    let vote = 0.4 * chaos_weight;
                    self.voting_tracker.record_vote("chaos", false, vote, 0.3);
                    low_votes += vote;
                }
            }
        }

        // ===== ALTERNATING PATTERN DETECTOR =====
        // Check for HIGH-LOW-HIGH-LOW alternating pattern
        let alternating_weight = self.voting_tracker.get_weight("alternating");
        if self.recent_rolls.len() >= 6 {
            let last_6: Vec<bool> = self
                .recent_rolls
                .iter()
                .rev()
                .take(6)
                .map(|&r| r > 5000)
                .collect();

            let mut alternations = 0;
            for i in 1..last_6.len() {
                if last_6[i] != last_6[i - 1] {
                    alternations += 1;
                }
            }

            // 4+ alternations in 6 rolls = strong alternating pattern
            if alternations >= 4 {
                // Predict opposite of last
                let vote = 1.2 * alternating_weight;
                if last_6[0] {
                    self.voting_tracker
                        .record_vote("alternating", false, vote, 0.5);
                    low_votes += vote; // Last was HIGH, expect LOW
                } else {
                    self.voting_tracker
                        .record_vote("alternating", true, vote, 0.5);
                    high_votes += vote; // Last was LOW, expect HIGH
                }
            }
        }

        // ===== RUN LENGTH ENCODING =====
        // Detect long "runs" of same outcome
        let run_length_weight = self.voting_tracker.get_weight("run_length");
        if self.recent_rolls.len() >= 15 {
            let rolls: Vec<bool> = self
                .recent_rolls
                .iter()
                .rev()
                .take(15)
                .map(|&r| r > 5000)
                .collect();

            // Find longest run
            let mut max_run = 1;
            let mut current_run = 1;
            let mut last_was_high = rolls[0];

            for &is_high in rolls.iter().skip(1) {
                if is_high == last_was_high {
                    current_run += 1;
                    max_run = max_run.max(current_run);
                } else {
                    current_run = 1;
                    last_was_high = is_high;
                }
            }

            // If we just ended a long run, expect change
            if max_run >= 5 && rolls[0] != rolls.get(max_run.min(14)).copied().unwrap_or(false) {
                // Ended a long run - momentum suggests staying in new direction
                let vote = 0.6 * run_length_weight;
                if rolls[0] {
                    self.voting_tracker
                        .record_vote("run_length", true, vote, 0.3);
                    high_votes += vote;
                } else {
                    self.voting_tracker
                        .record_vote("run_length", false, vote, 0.3);
                    low_votes += vote;
                }
            }
        }

        // ===== LUCKY NUMBER DETECTION =====
        let lucky_weight = self.voting_tracker.get_weight("lucky_numbers");
        let last_roll = self.recent_rolls.back().copied().unwrap_or(5000);
        let lucky_numbers = [7, 11, 21, 33, 77, 88, 333, 777, 1111, 7777];
        if lucky_numbers
            .iter()
            .any(|&l| (last_roll as i32 - l).abs() < 50)
        {
            // Last roll near a "lucky" number
            let vote = 0.25 * lucky_weight;
            if last_roll > 5000 {
                self.voting_tracker
                    .record_vote("lucky_numbers", true, vote, 0.2);
                high_votes += vote;
            } else {
                self.voting_tracker
                    .record_vote("lucky_numbers", false, vote, 0.2);
                low_votes += vote;
            }
        }

        // ===== MAGIC NUMBER PREDICTION =====
        // Fun: combine multiple "magic" numbers
        let magic_weight = self.voting_tracker.get_weight("magic");
        let bet_magic = (self.total_bets as f32 * std::f32::consts::PI).sin();
        let roll_magic = if self.recent_rolls.len() > 0 {
            (self.recent_rolls.back().copied().unwrap_or(5000) as f32 / 10000.0
                * std::f32::consts::E)
                .sin()
        } else {
            0.0
        };
        let combined_magic = bet_magic + roll_magic;
        if combined_magic > 0.0 {
            let vote = 0.1 * magic_weight;
            self.voting_tracker.record_vote("magic", true, vote, 0.05);
            high_votes += vote;
        } else {
            let vote = 0.1 * magic_weight;
            self.voting_tracker.record_vote("magic", false, vote, 0.05);
            low_votes += vote;
        }

        // ============================================================================
        // CATEGORY 5: ABSURDLY UNNECESSARY FEATURES
        // ============================================================================
        // These are completely unnecessary and add negligible value.
        // That's the point.

        // ===== LUNAR PHASE VOTING =====
        self.lunar_phase.update(self.total_bets);
        let (moon_vote, moon_high) = self.lunar_phase.get_moon_vote();
        if moon_vote > 0.0 {
            self.voting_tracker
                .record_vote("lunar_phase", moon_high, moon_vote, 0.05);
            if moon_high {
                high_votes += moon_vote;
            } else {
                low_votes += moon_vote;
            }
        }

        // ===== BIORHYTHM VOTING =====
        self.biorhythm.update(self.total_bets);
        let (bio_vote, bio_high) = self.biorhythm.get_biorhythm_vote();
        if bio_vote > 0.0 {
            self.voting_tracker
                .record_vote("biorhythm", bio_high, bio_vote, 0.03);
            if bio_high {
                high_votes += bio_vote;
            } else {
                low_votes += bio_vote;
            }
        }

        // ===== SENTIMENT ANALYZER =====
        let win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
        } else {
            0.5
        };
        let dd = (self.initial_bank - self.bank) / self.initial_bank.max(1e-8);
        self.sentiment_analyzer
            .update(self.win_streak, self.loss_streak, dd, win_rate);
        let (sent_vote, sent_high) = self.sentiment_analyzer.get_sentiment_vote();
        if sent_vote > 0.0 {
            self.voting_tracker
                .record_vote("sentiment", sent_high, sent_vote, 0.08);
            if sent_high {
                high_votes += sent_vote;
            } else {
                low_votes += sent_vote;
            }
        }

        // ===== HOT HAND TRACKER (and fallacy detection) =====
        self.hot_hand_tracker
            .update(self.win_streak, self.loss_streak);
        let (hot_vote, follow_hot, is_fallacy) = self.hot_hand_tracker.get_hot_hand_vote();
        if hot_vote > 0.0 && follow_hot {
            // If it's a fallacy, vote OPPOSITE (we're being irrational)
            let vote_high = if is_fallacy { !self.high } else { true };
            self.voting_tracker
                .record_vote("hot_hand", vote_high, hot_vote, 0.1);
            if vote_high {
                high_votes += hot_vote;
            } else {
                low_votes += hot_vote;
            }
        }

        // ===== CHAOS DRAGON =====
        let dragon_rng = self.next_rng();
        let (dragon_vote, dragon_high) = self.chaos_dragon.get_dragon_vote(dragon_rng);
        if dragon_vote > 0.0 {
            self.voting_tracker
                .record_vote("chaos_dragon", dragon_high, dragon_vote, 0.02);
            if dragon_high {
                high_votes += dragon_vote;
            } else {
                low_votes += dragon_vote;
            }
        }

        // ===== DIVINE INTERVENTION =====
        let divine_rng = self.next_rng();
        let total_bets = self.total_bets;
        if let Some(divine_high) = self
            .divine_intervention
            .check_for_divine_guidance(divine_rng, total_bets)
        {
            // Divine intervention overrides everything with a small vote
            let divine_vote = 0.5;
            self.voting_tracker
                .record_vote("divine", divine_high, divine_vote, 1.0);
            if divine_high {
                high_votes += divine_vote;
            } else {
                low_votes += divine_vote;
            }
        }

        // ===== SCHRODINGER'S CAT =====
        let (cat_vote, cat_high) = self.schrodinger_cat.get_quantum_vote();
        if cat_vote > 0.0 {
            self.voting_tracker
                .record_vote("schrodinger_cat", cat_high, cat_vote, 0.05);
            if cat_high {
                high_votes += cat_vote;
            } else {
                low_votes += cat_vote;
            }
        }

        // ===== KARMA CALCULATOR =====
        let (karma_vote, karma_high) = self.karma_calculator.get_karma_vote();
        if karma_vote > 0.0 {
            self.voting_tracker
                .record_vote("karma", karma_high, karma_vote, 0.03);
            if karma_high {
                high_votes += karma_vote;
            } else {
                low_votes += karma_vote;
            }
        }

        // ===== BUTTERFLY EFFECT =====
        let cascade_vote = self.butterfly_effect.get_cascade_vote();
        if cascade_vote > 0.0 {
            self.voting_tracker
                .record_vote("butterfly", true, cascade_vote, 0.02);
            high_votes += cascade_vote;
        }

        // ===== PATTERN CULT DETECTOR =====
        let (cult_vote, cult_high, is_cult) = self.pattern_cult_detector.get_cult_vote();
        if cult_vote > 0.0 && !is_cult {
            // Only vote if we're NOT in cult thinking
            self.voting_tracker
                .record_vote("pattern_cult", cult_high, cult_vote, 0.04);
            if cult_high {
                high_votes += cult_vote;
            } else {
                low_votes += cult_vote;
            }
        }

        // ===== QUANTUM ENTANGLEMENT =====
        let (entangle_vote, entangle_high) = self.quantum_entanglement.get_entanglement_vote();
        if entangle_vote > 0.0 {
            self.voting_tracker
                .record_vote("quantum_entangle", entangle_high, entangle_vote, 0.03);
            if entangle_high {
                high_votes += entangle_vote;
            } else {
                low_votes += entangle_vote;
            }
        }

        // ===== PHILOSOPHICAL UNCERTAINTY =====
        let (phil_vote, phil_high, _) = self.philosophical_uncertainty.get_philosophical_vote();
        if phil_vote > 0.0 {
            self.voting_tracker
                .record_vote("philosophy", phil_high, phil_vote, 0.02);
            if phil_high {
                high_votes += phil_vote;
            } else {
                low_votes += phil_vote;
            }
        }

        // ===== AKASHIC RECORD =====
        let (akashic_vote, akashic_high) = self.akashic_reader.get_cosmic_vote();
        if akashic_vote > 0.0 {
            self.voting_tracker
                .record_vote("akashic", akashic_high, akashic_vote, 0.02);
            if akashic_high {
                high_votes += akashic_vote;
            } else {
                low_votes += akashic_vote;
            }
        }

        // ===== RETROCAUSALITY ENGINE =====
        let (temporal_vote, temporal_high) = self.retrocausality_engine.get_temporal_vote();
        if temporal_vote > 0.0 {
            self.voting_tracker
                .record_vote("retrocausality", temporal_high, temporal_vote, 0.03);
            if temporal_high {
                high_votes += temporal_vote;
            } else {
                low_votes += temporal_vote;
            }
        }

        // ===== PROBABILITY MANIPULATOR =====
        let manip_rng = self.next_rng();
        let (manip_vote, manip_high) = self
            .probability_manipulator
            .get_manipulation_vote(manip_rng);
        if manip_vote > 0.0 {
            self.voting_tracker
                .record_vote("probability_manip", manip_high, manip_vote, 0.05);
            if manip_high {
                high_votes += manip_vote;
            } else {
                low_votes += manip_vote;
            }
        }

        // ===== CASINO PSYCHOLOGY =====
        let (psych_vote, psych_high) = self.casino_psychology.get_counter_psychology_vote();
        if psych_vote > 0.0 {
            self.voting_tracker
                .record_vote("casino_psych", psych_high, psych_vote, 0.03);
            if psych_high {
                high_votes += psych_vote;
            } else {
                low_votes += psych_vote;
            }
        }

        // ===== LUCK BANK =====
        let (luck_vote, luck_high) = self.luck_bank.get_luck_vote();
        if luck_vote > 0.0 {
            self.voting_tracker
                .record_vote("luck_bank", luck_high, luck_vote, 0.02);
            if luck_high {
                high_votes += luck_vote;
            } else {
                low_votes += luck_vote;
            }
        }

        // ============================================================================
        // CATEGORY 6: GENUINELY INTELLIGENT FEATURES - These actually work!
        // ============================================================================

        // ===== EDGE DETECTOR =====
        // Record current outcome for edge tracking
        let (edge_vote, edge_high) = self.edge_detector.get_edge_vote();
        if edge_vote > 0.0 {
            self.voting_tracker.record_vote(
                "edge_detector",
                edge_high,
                edge_vote,
                self.edge_detector.edge_confidence,
            );
            if edge_high {
                high_votes += edge_vote;
            } else {
                low_votes += edge_vote;
            }
        }

        // ===== PATTERN STRENGTH =====
        // Trust patterns more if they have a track record
        let pattern_trust = if self.pattern_strength.should_trust_patterns() {
            0.1
        } else {
            0.0
        };
        if pattern_trust > 0.0 {
            // Pattern trust amplifies existing votes
            high_votes *= 1.0 + pattern_trust;
            low_votes *= 1.0 + pattern_trust;
        }

        // ============================================================================
        // CATEGORY 6.5: ADVANCED INTELLIGENCE FEATURES (17 NEW FEATURES)
        // ============================================================================

        // ----- FEATURE 3: ANTI-PERSISTENCE DETECTOR -----
        // Detect alternation/streak patterns and predict the opposite
        let (high_adj, low_adj) = self.anti_persistence.get_prediction_adjustment();
        let streak_signal = self.anti_persistence.get_streak_signal();
        let anti_persist_weight = 0.8; // Significant weight for pattern breaking
        if high_adj > low_adj {
            let vote = (high_adj - 0.5) * 2.0 * anti_persist_weight;
            self.voting_tracker.record_vote(
                "anti_persistence",
                true,
                vote.abs(),
                streak_signal.abs(),
            );
            high_votes += vote.abs();
        } else if low_adj > high_adj {
            let vote = (low_adj - 0.5) * 2.0 * anti_persist_weight;
            self.voting_tracker.record_vote(
                "anti_persistence",
                false,
                vote.abs(),
                streak_signal.abs(),
            );
            low_votes += vote.abs();
        }
        // Streak signal: positive = ride hot streak, negative = break cold streak
        if streak_signal.abs() > 0.1 {
            if streak_signal > 0.0 {
                // Hot streak - bet same as last outcome
                if self.last_win {
                    high_votes += streak_signal * 0.5; // Slight bias toward continuing
                }
            } else {
                // Cold streak due to break - small opposite boost
                let vote = streak_signal.abs() * 0.3;
                if !self.last_win {
                    high_votes += vote; // Expect reversal
                }
            }
        }

        // ----- FEATURE 7: ADVANCED CONFIDENCE CALIBRATOR -----
        // Use calibration to weight model agreement
        let calibrator_quality = self.advanced_calibrator.get_calibration_quality();
        // Adjust confidence based on calibration - poorly calibrated models need more exploration
        if calibrator_quality < 0.7 {
            // Poor calibration - add random exploration
            if self.next_rng() < (1.0 - calibrator_quality) * 0.2 {
                let random_vote = 0.1 * (1.0 - calibrator_quality);
                if self.next_rng() < 0.5 {
                    high_votes += random_vote;
                } else {
                    low_votes += random_vote;
                }
            }
        }

        // ----- FEATURE 11: BAYESIAN MODEL AVERAGING -----
        // Combines model predictions using Bayesian averaging
        // Collect recent model predictions for Bayesian averaging
        let model_predictions: Vec<f32> = vec![
            dqn_avg * 0.5 + 0.5, // Normalize to 0-1
            markov_pred,
            state_estimate,
        ];
        let (bayesian_mean, bayesian_uncertainty) =
            self.bayesian_averager.predict(&model_predictions);
        let bayesian_weight = 1.5 * (1.0 - bayesian_uncertainty); // Weight inversely with uncertainty
        if bayesian_mean > 0.55 {
            let vote = (bayesian_mean - 0.5) * bayesian_weight;
            self.voting_tracker
                .record_vote("bayesian_avg", true, vote, 1.0 - bayesian_uncertainty);
            high_votes += vote;
        } else if bayesian_mean < 0.45 {
            let vote = (0.5 - bayesian_mean) * bayesian_weight;
            self.voting_tracker.record_vote(
                "bayesian_avg",
                false,
                vote,
                1.0 - bayesian_uncertainty,
            );
            low_votes += vote;
        }

        // ----- FEATURE 12: ANOMALY DETECTOR -----
        // Detect anomalies in recent win rate and adjust confidence
        let anomaly_result = self
            .anomaly_detector
            .detect(if win_rate > 0.5 { win_rate } else { 0.5 }, self.total_bets);
        if anomaly_result.is_anomaly {
            // Anomaly detected - reduce confidence
            let anomaly_penalty = 0.3;
            high_votes *= 1.0 - anomaly_penalty;
            low_votes *= 1.0 - anomaly_penalty;
            // Add small exploration vote
            if self.next_rng() < 0.5 {
                high_votes += 0.2;
            } else {
                low_votes += 0.2;
            }
        }
        // Use trend information
        match anomaly_result.trend {
            TrendType::Increasing => {
                // Trending upward - slight bias toward optimism
                if self.last_win {
                    high_votes += 0.1;
                }
            }
            TrendType::Decreasing => {
                // Trending downward - caution
                if !self.last_win {
                    low_votes += 0.1;
                }
            }
            TrendType::Stable => {}
        }

        // ----- FEATURE 14: HIERARCHICAL RL -----
        // Get current high-level goal
        let current_goal = self
            .hierarchical_rl
            .select_goal(dd, self.win_streak, self.loss_streak);
        let sub_policy = self.hierarchical_rl.get_sub_policy(current_goal);
        // Get goal-appropriate action distribution
        let goal_vote_weight = 1.0;
        match current_goal {
            HighLevelGoal::PreserveCapital => {
                // Conservative - prefer lower variance (slight LOW bias on coin flip)
                let vote = 0.15 * goal_vote_weight;
                self.voting_tracker
                    .record_vote("hierarchical", false, vote, 0.3);
                low_votes += vote;
            }
            HighLevelGoal::AccumulateProfit => {
                // Aggressive growth - follow the models
                // No additional vote, trust other models
            }
            HighLevelGoal::RecoverLosses => {
                // Recovery mode - calculated risk
                // Slight bias toward the winning direction historically
                if high_success_rate > low_success_rate {
                    let vote = 0.2 * goal_vote_weight * (high_success_rate - low_success_rate);
                    self.voting_tracker
                        .record_vote("hierarchical", true, vote, 0.4);
                    high_votes += vote;
                }
            }
            HighLevelGoal::RideWinStreak => {
                // Hot streak - press hard
                let vote = 0.25 * goal_vote_weight;
                if self.last_win {
                    self.voting_tracker
                        .record_vote("hierarchical", true, vote, 0.5);
                    high_votes += vote;
                } else {
                    self.voting_tracker
                        .record_vote("hierarchical", false, vote, 0.5);
                    low_votes += vote;
                }
            }
            HighLevelGoal::SurviveLossStreak => {
                // Survival mode - minimize further losses
                // Strong conservative bias
                let vote = 0.3 * goal_vote_weight;
                self.voting_tracker
                    .record_vote("hierarchical", false, vote, 0.4);
                low_votes += vote;
            }
            HighLevelGoal::ExploreNewStrategy => {
                // Exploration mode - add randomness
                if self.next_rng() < 0.3 {
                    return self.next_rng() < 0.5;
                }
            }
        }

        // ----- FEATURE 15: MODEL-BASED RL -----
        // Use learned environment model for planning
        let recent_bools: Vec<bool> = self.recent_seq.iter().rev().take(20).copied().collect();
        let action_scores: Vec<f32> = (0..2)
            .map(|action| {
                // Estimate expected value from this action
                self.model_based_rl.simulate_rollout(
                    &recent_bools
                        .iter()
                        .map(|&b| if b { 1 } else { 0 })
                        .collect::<Vec<_>>(),
                    action,
                    3, // Planning depth
                )
            })
            .collect();
        let mbrl_best_action = if action_scores[0] > action_scores[1] {
            0
        } else {
            1
        };
        let mbrl_confidence =
            (action_scores[mbrl_best_action] - action_scores[1 - mbrl_best_action]).abs();
        let mbrl_weight = 0.8;
        if mbrl_best_action == 0 {
            self.voting_tracker.record_vote(
                "model_based_rl",
                true,
                mbrl_weight * (0.5 + mbrl_confidence),
                mbrl_confidence,
            );
            high_votes += mbrl_weight * (0.5 + mbrl_confidence);
        } else {
            self.voting_tracker.record_vote(
                "model_based_rl",
                false,
                mbrl_weight * (0.5 + mbrl_confidence),
                mbrl_confidence,
            );
            low_votes += mbrl_weight * (0.5 + mbrl_confidence);
        }

        // ----- FEATURE 16: INVERSE RL -----
        // Learn from winning sessions what actions are valuable
        if let Some(&inv_rl_reward) = self.last_context.first() {
            let _ = inv_rl_reward; // Used in inverse RL
        }
        // Get reward signal from inverse RL
        let inv_reward = self.inverse_rl.get_reward(&context);
        // If inverse RL suggests this is a high-value state, bias accordingly
        if inv_reward > 0.1 {
            let vote = inv_reward.min(0.5) * 0.5;
            // Positive reward states - trust models slightly more
            let _ = vote; // Add confidence boost elsewhere
        }

        // ----- FEATURE 17: THEORY OF MIND -----
        // Model what the casino might do
        let (casino_p_high, casino_uncertainty) = self.theory_of_mind.predict_casino_action();
        let counter_strategy = self.theory_of_mind.get_counter_strategy();
        // If casino alternates, bet opposite of last; if streaks, follow
        let tom_weight = (1.0 - casino_uncertainty) * 0.5; // Less weight if uncertain
        if casino_p_high < 0.4 {
            // Casino predicting HIGH will lose - bet LOW
            let vote = (0.5 - casino_p_high) * tom_weight;
            self.voting_tracker.record_vote(
                "theory_of_mind",
                false,
                vote,
                1.0 - casino_uncertainty,
            );
            low_votes += vote;
        } else if casino_p_high > 0.6 {
            // Casino predicting LOW will lose - bet HIGH
            let vote = (casino_p_high - 0.5) * tom_weight;
            self.voting_tracker
                .record_vote("theory_of_mind", true, vote, 1.0 - casino_uncertainty);
            high_votes += vote;
        }
        // Counter-strategy influence
        if counter_strategy > 0.3 {
            // Casino might be manipulating - add some randomness
            if self.next_rng() < counter_strategy * 0.3 {
                return self.next_rng() < 0.5;
            }
        }

        // ----- FEATURE 6: SESSION MEMORY -----
        // Get time-adjusted multiplier and casino prediction from memory
        let time_mult = self
            .session_memory
            .get_time_adjusted_multiplier(self.total_bets);
        let (casino_alt, casino_streak) = self.session_memory.get_casino_prediction();
        // Use casino model to weight votes
        if casino_alt.abs() > 0.1 {
            // Detected casino alternation pattern
            let vote = casino_alt.abs() * 0.3 * time_mult;
            if casino_alt < 0.0 {
                // Casino alternating - bet opposite of last
                if self.last_win {
                    self.voting_tracker.record_vote(
                        "session_memory",
                        false,
                        vote,
                        casino_alt.abs(),
                    );
                    low_votes += vote;
                } else {
                    self.voting_tracker
                        .record_vote("session_memory", true, vote, casino_alt.abs());
                    high_votes += vote;
                }
            }
        }
        if casino_streak.abs() > 0.2 {
            // Detected casino streaking
            let vote = casino_streak.abs() * 0.2 * time_mult;
            if casino_streak > 0.0 {
                // Casino on streak - stay with it
                if self.last_win {
                    self.voting_tracker.record_vote(
                        "session_memory_streak",
                        true,
                        vote,
                        casino_streak.abs(),
                    );
                    high_votes += vote;
                }
            }
        }

        // ----- FEATURE 8: TRANSFORMER SEQUENCE PREDICTOR -----
        // Deep attention-based pattern detection
        let transformer_seq_weight = self.voting_tracker.get_weight("transformer_seq") * 1.5;
        if self.recent_rolls.len() >= 10 {
            let seq: Vec<f32> = self
                .recent_rolls
                .iter()
                .map(|&r| r as f32 / 10000.0)
                .collect();
            let transformer_pred = self.transformer_predictor.predict_next(&seq);
            let conf = (transformer_pred - 0.5).abs() * 2.0;
            let is_high = transformer_pred > 0.5;
            self.record_model_prediction(24, is_high, conf);
            let vote = (transformer_pred - 0.5).abs() * transformer_seq_weight * conf;
            self.voting_tracker
                .record_vote("transformer_seq", is_high, vote, conf);
            if is_high {
                high_votes += vote;
            } else {
                low_votes += vote;
            }
        }

        // ----- FEATURE 13: RISK-AWARE RL -----
        // Check if we're within risk budget
        let within_risk_budget = self.risk_aware_rl.is_within_risk_budget();
        let cvar = self.risk_aware_rl.compute_cvar();
        // Adjust confidence based on risk
        if !within_risk_budget {
            // Over risk budget - be more conservative
            high_votes *= 0.9;
            low_votes *= 0.9;
        }
        // VaR/CVaR affect decision confidence
        if cvar.abs() > 0.15 {
            // High tail risk - reduce model confidence slightly
            let risk_penalty = 0.05;
            high_votes *= 1.0 - risk_penalty;
            low_votes *= 1.0 - risk_penalty;
        }

        // ===== SESSION STATE =====
        // Adjust based on current session state
        let state_risk = self.session_state.get_state_risk_modifier();
        // Use this to weight confidence later

        // ===== PERFORMANCE MOMENTUM =====
        let momentum_adj = self.performance_momentum.get_momentum_adjustment();
        // Use this in bet sizing

        // ===== WIN PREDICTOR =====
        // Get probability of profitable session
        let session_win_prob = self.win_predictor.get_win_probability();
        if session_win_prob > 0.6 {
            // Good session - slight HIGH bias
            let vote = (session_win_prob - 0.5) * 0.1;
            self.voting_tracker
                .record_vote("win_predictor", true, vote, session_win_prob);
            high_votes += vote;
        } else if session_win_prob < 0.4 {
            // Bad session - slight LOW bias
            let vote = (0.5 - session_win_prob) * 0.1;
            self.voting_tracker
                .record_vote("win_predictor", false, vote, 1.0 - session_win_prob);
            low_votes += vote;
        }

        // ===== STRATEGY SELECTOR =====
        let current_strategy = self.strategy_selector.current_best;
        // Strategy affects bet sizing, recorded for later

        // ===== DUNNING-KRUGER PENALTY =====
        let overconfidence_penalty = self.dunning_kruger.get_overconfidence_penalty();
        if overconfidence_penalty > 0.0 {
            // Reduce the winning side's votes slightly if we're being overconfident
            if high_votes > low_votes {
                high_votes *= 1.0 - overconfidence_penalty;
            } else {
                low_votes *= 1.0 - overconfidence_penalty;
            }
        }

        // ===== CONSPIRACY DETECTOR =====
        let paranoia_modifier = self.conspiracy_detector.get_paranoia_modifier();
        high_votes *= paranoia_modifier;
        low_votes *= paranoia_modifier;

        // ===== MARTINGALE URGE SUPPRESSION =====
        let rationality = self.martingale_urge.get_rational_bet_modifier();
        // This affects bet sizing, not voting, but we track it here
        let _ = rationality; // Used elsewhere

        // ===== REGIME DETECTOR =====
        let (_, should_reverse) = self.regime.get_recommended_strategy();
        if should_reverse {
            // In bad regime, models may be wrong - add randomness
            if self.next_rng() < 0.15 {
                return self.next_rng() < 0.5;
            }
        }

        // ===== SMART FINAL DECISION =====

        // Calculate confidence from vote difference
        let total_votes = high_votes + low_votes;
        let vote_margin = (high_votes - low_votes).abs();
        let confidence = if total_votes > 0.0 {
            vote_margin / total_votes
        } else {
            0.0
        };

        // Store confidence in cache for use elsewhere
        if self.cached_predictions.valid {
            self.cached_predictions.model_agreement = confidence;
        }

        // ===== SYSTEMATIC DIRECTION BIAS CORRECTION =====
        // Check if voting system has developed a systematic bias
        let bias_correction = self.voting_tracker.get_direction_bias_correction();
        if bias_correction.abs() > 0.15 {
            // System has been biased - add counter-votes
            // bias_correction > 0 means HIGH bias, need LOW correction
            let correction_strength = bias_correction.abs() * total_votes * 0.3;
            if bias_correction > 0.0 {
                // System biased HIGH - boost LOW
                low_votes += correction_strength;
            } else {
                // System biased LOW - boost HIGH
                high_votes += correction_strength;
            }
        }

        // ===== DIRECTION BALANCE ENFORCEMENT =====
        // If we've been heavily biased toward one direction, force exploration
        let dir_imbalance = if total_dir_bets > 10 {
            let high_ratio = self.high_bets as f32 / total_dir_bets as f32;
            (high_ratio - 0.5).abs() // How far from 50/50
        } else {
            0.0
        };

        // Strong imbalance (>70% one direction) - add correction votes
        if dir_imbalance > 0.2 && total_dir_bets > 15 {
            let correction = dir_imbalance * 3.0; // Up to ~1.5 votes
            if self.high_bets > self.low_bets {
                // Been betting high too much - boost low
                low_votes += correction;
            } else {
                // Been betting low too much - boost high
                high_votes += correction;
            }
        }

        // Extreme imbalance (>80% one direction) - stronger correction + random exploration
        if dir_imbalance > 0.3 && total_dir_bets > 20 {
            // 25% chance to just go opposite direction
            if self.next_rng() < 0.25 {
                return self.high_bets < self.low_bets; // Opposite of dominant
            }
        }

        // ===== EXPLORATION: DON'T GET STUCK =====
        // Periodic random exploration to prevent getting stuck in patterns
        if self.total_bets > 30 && self.total_bets % 15 == 0 {
            // Every 15 bets, 10% chance to randomly explore
            if self.next_rng() < 0.1 {
                return self.next_rng() < 0.5;
            }
        }

        // If very low confidence, consider random (models disagree)
        if confidence < 0.05 && self.total_bets > 100 {
            // Models almost perfectly disagree - slight random
            if self.next_rng() < 0.3 {
                return self.next_rng() < 0.5;
            }
        }

        // If one direction has been losing consistently, add small random chance to switch
        if total_dir_bets > 20 && self.loss_streak >= 4 {
            // Been losing streak - 15% chance to try opposite direction
            if self.next_rng() < 0.15 {
                // Pick the direction with FEWER recent bets (try the other side)
                return self.high_bets > self.low_bets;
            }
        }

        // Add small noise to break ties (but keep it small)
        high_votes += (self.next_rng() - 0.5) * 0.05;

        // If votes are very close, slight bias toward direction with better history
        if (high_votes - low_votes).abs() < 2.0 {
            // Near-tie - use direction success rate as tiebreaker
            if high_success_rate > low_success_rate + 0.02 {
                high_votes += 0.5;
            } else if low_success_rate > high_success_rate + 0.02 {
                low_votes += 0.5;
            } else {
                // Still tied - use small random
                if self.next_rng() < 0.25 {
                    return self.next_rng() < 0.5;
                }
            }
        }

        high_votes > low_votes
    }

    /// AI decides recovery mode
    fn ai_recovery_mode(&mut self, context: &[f32], dd: f32) -> (bool, f32) {
        // ============================================================================
        // RECOVERY MODE - EXTREMELY AGGRESSIVE FIGHT BACK
        // ============================================================================
        // When losing, we FIGHT BACK HARDER, not fold.
        // Recovery mode triggers at LOWER drawdown thresholds.

        // Start recovery mode earlier (10% drawdown instead of 15%)
        // Must have at least 20 bets for models to have some data
        if self.total_bets < 20 {
            return (false, 0.0);
        }

        // dd > 0.10 means we've lost 10%+ of STARTING bank - ENTER RECOVERY
        if dd < 0.10 {
            return (false, 0.0);
        }

        // ============================================================================
        // SMART RECOVERY MODE - Multi-factor analysis
        // ============================================================================

        // Factor 1: DQN state evaluation
        let dqn_values = self.dqn_agent.forward(context);
        let dqn_value: f32 = dqn_values.par_iter().sum::<f32>() / dqn_values.len().max(1) as f32;

        // Factor 2: Win rate trend (are we recovering already?)
        let recent_wr = if self.recent_returns.len() >= 20 {
            let recent: Vec<f32> = self.recent_returns.iter().rev().take(20).copied().collect();
            let wins = recent.iter().filter(|&&r| r > 0.0).count();
            wins as f32 / recent.len() as f32
        } else {
            0.5
        };

        // Factor 3: Volatility
        let volatility = self.risk.volatility;

        // Factor 4: Loss streak severity
        let streak_severity = self.loss_streak.min(10) as f32 / 10.0;

        // Factor 5: Hurst exponent (trending vs mean-reverting)
        let hurst = self.hurst.estimate_hurst();
        let is_trending = hurst > 0.55;
        let is_mean_reverting = hurst < 0.45;

        // Factor 6: Model confidence
        let model_confidence = if self.cached_predictions.valid {
            1.0 - self.cached_predictions.uncertainty_score
        } else {
            0.5
        };

        // ===== RECOVERY SCORE CALCULATION =====
        let mut recovery_score = 0.0;

        // Drawdown component (0-50 points - INCREASED)
        recovery_score += (dd * 125.0_f32).min(50.0_f32); // More weight on drawdown

        // DQN bad state (0-25 points - INCREASED)
        if dqn_value < 0.0 {
            recovery_score += (dqn_value.abs() * 25.0_f32).min(25.0_f32);
        }

        // Loss streak (0-20 points - INCREASED)
        recovery_score += streak_severity * 20.0_f32;

        // Low recent win rate (0-20 points - INCREASED)
        if recent_wr < 0.50 {
            recovery_score += ((0.50_f32 - recent_wr) * 100.0_f32).min(20.0_f32);
        }

        // High volatility (adds urgency, 0-15 points - INCREASED)
        if volatility > 0.02 {
            recovery_score += ((volatility - 0.02) * 750.0_f32).min(15.0_f32);
        }

        // ===== NEGATIVE FACTORS (REDUCED - don't ease off recovery) =====

        // Already recovering - MINIMAL reduction
        if recent_wr > 0.50 {
            recovery_score *= 0.85; // Was 0.6
        }

        // Mean-reverting market - MINIMAL reduction
        if is_mean_reverting {
            recovery_score *= 0.9; // Was 0.75
        }

        // High model confidence - MINIMAL reduction
        if model_confidence > 0.7 {
            recovery_score *= 0.95; // Was 0.8
        }

        // ===== RECOVERY DECISION =====
        // Trigger recovery if score > 40 (was 50)
        if recovery_score > 40.0 {
            // Determine recovery phase
            let phase = if dd > 0.45 {
                RecoveryPhase::Critical // Severe drawdown (was 0.50)
            } else if dd > 0.30 {
                RecoveryPhase::Aggressive // Significant drawdown (was 0.35)
            } else if dd > 0.20 {
                RecoveryPhase::Moderate // Mild drawdown (was 0.25)
            } else {
                RecoveryPhase::Light
            };

            // Calculate adaptive aggression based on all factors
            // EXTREMELY AGGRESSIVE RECOVERY: Fight back with everything!
            let base_aggression = match phase {
                RecoveryPhase::Critical => 0.10, // 10% - NUCLEAR when deep in hole (was 5%)
                RecoveryPhase::Aggressive => 0.08, // 8% (was 4%)
                RecoveryPhase::Moderate => 0.06, // 6% (was 4%)
                RecoveryPhase::Light => 0.05,    // 5% (was 3%)
            };

            // Adjust based on volatility - FIGHT THROUGH volatility
            let vol_adjustment = if volatility > 0.03 {
                0.95 // Only slight reduction - FIGHT THROUGH
            } else if volatility > 0.02 {
                1.0 // No reduction
            } else {
                1.1 // Actually INCREASE in low vol
            };

            // Adjust based on trend - BE MORE AGGRESSIVE when trending
            let trend_adjustment = if is_trending {
                1.3 // Trending PUSH MUCH HARDER (was 1.2)
            } else if is_mean_reverting {
                1.15 // Mean-reverting means it WILL come back - PUSH
            } else {
                1.1 // Default still push
            };

            // Adjust based on model confidence - PUSH when confident
            let confidence_adjustment = 0.9 + model_confidence * 0.5;

            // STREAK BONUS - Go even harder on losing streaks
            let streak_bonus = if self.loss_streak >= 8 {
                1.5 // MASSIVE boost on severe losing streak
            } else if self.loss_streak >= 5 {
                1.3 // Big boost on bad streak
            } else if self.loss_streak >= 3 {
                1.15 // Boost on moderate streak
            } else {
                1.0
            };

            // PROFIT BOOST - If we were winning at some point, we can push harder
            let profit_boost = if self.peak_bank > self.initial_bank * 1.2 {
                1.2 // We've been profitable, push harder to get back
            } else if self.peak_bank > self.initial_bank {
                1.1 // Some profit, slight boost
            } else {
                1.0
            };

            let final_aggression = base_aggression
                * vol_adjustment
                * trend_adjustment
                * confidence_adjustment
                * streak_bonus
                * profit_boost;

            // Cap at 20% max to preserve some bankroll
            return (true, final_aggression.min(0.20_f32));
        }

        (false, 0.0)
    }

    /// Get recommended multiplier for recovery mode - MORE AGGRESSIVE
    fn get_recovery_multiplier(&self, dd: f32) -> f32 {
        // Recovery mode should use SAFE BUT STILL MEANINGFUL multipliers
        // Higher win probability = more likely to recover

        // INCREASED multipliers - we need bigger wins to recover
        let base_mult = if dd > 0.50 {
            2.0 // Was 1.5 - need bigger wins in critical
        } else if dd > 0.35 {
            2.5 // Was 2.0
        } else if dd > 0.20 {
            3.0 // Was 2.5
        } else {
            3.5 // Was 2.5 - still need meaningful wins
        };

        // On losing streak, we NEED to win - use safer multipliers
        // But not TOO safe - we need actual progress
        if self.loss_streak >= 8 {
            return 1.8; // Was 1.5 - extremely severe
        } else if self.loss_streak >= 5 {
            return 2.2; // Was 1.5
        } else if self.loss_streak >= 3 {
            return 2.5; // Was 2.0
        }

        // Win streak during recovery? PUSH IT!
        if self.win_streak >= 3 {
            return (base_mult * 1.3_f32).min(5.0_f32); // Boost multiplier on win streak
        }

        base_mult
    }

    fn select_arm(&mut self, dd: f32, ws: u32, ls: u32, mc: f32, _rs: f32) -> usize {
        // Force exploration: always try different arms periodically
        let exploration_rate = 0.15; // 15% chance to explore randomly

        // Initial exploration phase - random exploration
        if self.total_bets < self.arms.len() * 2 {
            return (self.next_rng() * self.arms.len() as f32) as usize;
        }

        // Periodic forced exploration - evenly distributed
        if self.next_rng() < exploration_rate {
            return (self.next_rng() * self.arms.len() as f32) as usize;
        }

        // Pre-compute context for parallel evaluation
        let total_pulls: u32 = self.arms.par_iter().map(|a| a.pull_count).sum();
        let rng_vals: Vec<f32> = (0..self.arms.len()).map(|_| self.next_rng()).collect();
        let context = self.build_context(dd, ws, ls);

        // Pre-compute AI system outputs (these need &mut self, so compute before parallel)
        let linucb_best_arm = self.linucb.select_arm(&context);
        let dqn_prediction = self.dqn_agent.forward(&context);
        let policy_action = self.policy_gradient.select_action(&context);
        let kalman_estimate = self.kalman_filter.get_state();
        let particle_estimate = self.particle_filter.estimate();
        let state_estimate = (kalman_estimate + particle_estimate) / 2.0;
        let vol_forecast = self.volatility_forecaster.forecast(10);
        let mr_z = self.mean_reversion.z_score();
        let trend = self.trend_strength.trend_strength();
        let (regime_mult, _) = self.regime.get_recommended_strategy();
        let ensemble_preds: Vec<f32> = vec![
            context.get(0).copied().unwrap_or(0.5),
            context.get(3).copied().unwrap_or(0.5),
            context.get(4).copied().unwrap_or(0.5),
        ];
        let ensemble_pred = self.ensemble_forecaster.predict(&ensemble_preds);
        let reservoir_inputs: Vec<f32> = context.iter().take(10).cloned().collect();
        self.reservoir.update(&reservoir_inputs);
        let reservoir_out = self.reservoir.output();
        let reservoir_signal = reservoir_out.get(0).copied().unwrap_or(0.5);
        let attention_context = if self.recent_seq.len() >= 8 {
            let seq: Vec<f32> = self
                .recent_seq
                .iter()
                .map(|&b| if b { 1.0 } else { 0.0 })
                .collect();
            self.self_attention.predict(&seq)
        } else {
            0.5
        };
        let gp_state: Vec<f32> = vec![
            self.bank / self.initial_bank.max(1e-8),
            dd,
            self.risk.volatility,
        ];
        let (_, gp_std) = self.gaussian_process.predict(&gp_state);
        let gp_uncertainty = gp_std;
        let es_params = self.evolution_strategies.get_params();
        let es_risk_adj = es_params.get(0).copied().unwrap_or(0.5);
        let es_mult_adj = es_params.get(1).copied().unwrap_or(1.0);
        let mcts_prediction = self
            .mcts
            .predict(&self.recent_seq.iter().copied().collect::<Vec<_>>());
        let mcts_best_arm = if mcts_prediction.0 > 0.5 {
            0
        } else {
            self.arms.len() / 2
        };
        let markov_pred = self
            .markov
            .predict(&self.recent_seq.iter().copied().collect::<Vec<_>>());

        // Use parallel scoring for arm evaluation
        let scores = self.compute_arm_scores_parallel(
            dd,
            ws,
            ls,
            mc,
            &rng_vals,
            linucb_best_arm,
            &dqn_prediction,
            policy_action,
            state_estimate,
            vol_forecast,
            mr_z,
            trend,
            regime_mult,
            ensemble_pred,
            reservoir_signal,
            attention_context,
            gp_uncertainty,
            es_risk_adj,
            es_mult_adj,
            mcts_best_arm,
            markov_pred,
        );

        // Find the best arm
        let mut best = 0;
        let mut best_score = f32::NEG_INFINITY;
        for (i, &score) in scores.iter().enumerate() {
            if score > best_score {
                best_score = score;
                best = i;
            }
        }

        best
    }

    fn calc_bet(&mut self, arm_idx: usize) -> f32 {
        if self.total_bets < 3 {
            return self.min_bet * 4.0;
        }

        let drawdown_pct = (self.initial_bank - self.bank) / self.initial_bank.max(1e-8);
        let in_significant_drawdown = drawdown_pct > 0.10;

        // RECOVERY MODE - only trigger on SIGNIFICANT drawdown (>10% below initial)
        if in_significant_drawdown {
            let recovery_pct = if drawdown_pct > 0.30 {
                0.35
            } else if drawdown_pct > 0.20 {
                0.25
            } else {
                0.15
            };

            let fixed_bet = self.initial_bank * recovery_pct;
            return fixed_bet.min(self.bank).max(self.min_bet);
        }

        let arm = &self.arms[arm_idx];
        let theoretical_win_rate = (100.0 - self.house_percent) / arm.multiplier / 100.0;

        // Kelly Criterion bet sizing
        let kelly_fraction = self
            .kelly
            .calculate_kelly(theoretical_win_rate, arm.multiplier);
        self.kelly.record_bank(self.bank);

        // Build context for AI systems
        let streak = if self.win_streak > 0 {
            self.win_streak as i32
        } else {
            -(self.loss_streak as i32)
        };
        let overall_win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
        } else {
            0.5
        };
        let context = self.build_context(drawdown_pct, self.win_streak, self.loss_streak);

        // Q-Learning state and action
        let q_state =
            self.q_learner
                .get_state(drawdown_pct, streak, self.risk.volatility, overall_win_rate);
        let q_action = self.q_learner.select_action(q_state);
        let q_mult = self.q_learner.get_bet_multiplier(q_action);

        // DQN action for bet sizing
        let dqn_q_values = self.dqn_agent.forward(&context);
        let dqn_action = dqn_q_values
            .iter()
            .enumerate()
            .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
            .map(|(i, _)| i)
            .unwrap_or(0);
        let dqn_mult = 0.5 + dqn_action as f32 * 0.25; // Maps action to 0.5 - 1.5

        // Policy gradient action
        let pg_action = self.policy_gradient.select_action(&context);
        let pg_mult = 0.8 + pg_action as f32 * 0.1; // Maps to 0.8 - 1.3

        // Risk parity position sizing
        let risk_parity_mult = self.risk_parity.calculate_position_size(
            self.risk.volatility,
            drawdown_pct,
            overall_win_rate,
        );

        // Volatility forecast (10-step ahead)
        let vol_forecast = self.volatility_forecaster.forecast(10);
        let vol_adjustment = if vol_forecast > 0.4 {
            0.6 // High volatility - reduce size significantly
        } else if vol_forecast > 0.25 {
            0.8 // Moderate volatility - reduce moderately
        } else if vol_forecast < 0.1 {
            1.15 // Low volatility - can increase slightly
        } else {
            1.0
        };

        // Mean reversion signal
        let mr_z = self.mean_reversion.z_score();
        let mr_signal = if mr_z.abs() > 2.0 {
            mr_z.signum() * 0.5 + 0.5
        } else {
            0.5
        };
        let mr_strength = mr_z.abs() / 3.0;
        let mr_adjustment = if mr_signal > 0.6 {
            // Price is low relative to mean - expect reversion up
            1.0 + mr_strength * 0.2
        } else if mr_signal < 0.4 {
            // Price is high relative to mean - expect reversion down
            1.0 - mr_strength * 0.15
        } else {
            1.0
        };

        // Evolution strategies suggestion
        let es_best = self.evolution_strategies.get_params();
        let es_bet_frac = es_best.get(2).copied().unwrap_or(0.1); // Third param is bet fraction

        // Regime-based adjustment
        let (regime_mult, _should_reverse) = self.regime.get_recommended_strategy();

        // Kalman and particle filter estimates
        let kalman_estimate = self.kalman_filter.get_state();
        let particle_estimate = self.particle_filter.estimate();
        let state_estimate = (kalman_estimate + particle_estimate) / 2.0;
        let state_adjustment = 0.8 + state_estimate * 0.4; // Maps 0-1 to 0.8-1.2

        // Base percentage based on multiplier and AI recommendations
        // EARLY GAME PROTECTION - start small
        let early_game = self.total_bets < 20;
        let base_pct: f32 = match arm.multiplier {
            m if m <= 2.0 => {
                if early_game {
                    0.03
                } else {
                    0.12
                }
            }
            m if m <= 3.0 => {
                if early_game {
                    0.025
                } else {
                    0.10
                }
            }
            m if m <= 5.0 => {
                if early_game {
                    0.015
                } else {
                    0.08
                }
            }
            m if m <= 10.0 => {
                if early_game {
                    0.008
                } else {
                    0.05
                }
            }
            _ => {
                if early_game {
                    0.003
                } else {
                    0.03
                }
            }
        };

        // Combine all multipliers
        let mut final_pct: f32 = base_pct;

        // Kelly adjustment
        final_pct = final_pct.max(kelly_fraction * 0.5);

        // Streak multiplier
        final_pct *= self.streak_mult();

        // Progression multiplier
        final_pct *= self.prog_mult.min(5.0);

        // Q-Learning adjustment
        final_pct *= q_mult;

        // DQN adjustment
        final_pct *= dqn_mult;

        // Policy gradient adjustment
        final_pct *= pg_mult;

        // Risk parity adjustment
        final_pct = final_pct * 0.7 + risk_parity_mult * 0.3;

        // Regime adjustment
        final_pct *= regime_mult;

        // Volatility adjustment (GARCH-based)
        final_pct *= vol_adjustment;

        // Mean reversion adjustment
        final_pct *= mr_adjustment;

        // State estimate adjustment
        final_pct *= state_adjustment;

        // ES suggestion blend
        final_pct = final_pct * 0.85 + es_bet_frac * 0.15;

        // Volatility filter from risk state
        if self.volatility_adjusted_bet && self.risk.volatility > 0.3 {
            final_pct *= 0.7; // Reduce bet in high volatility
        }

        // Sharpe ratio adjustment (if we have enough data)
        if self.sharpe_ratio > 1.0 {
            final_pct *= 1.1; // Slight increase if performing well
        } else if self.sharpe_ratio < 0.0 {
            final_pct *= 0.9; // Slight decrease if underperforming
        }

        // Sortino ratio (downside risk-adjusted)
        if self.sortino_ratio > 0.5 {
            final_pct *= 1.05;
        } else if self.sortino_ratio < -0.5 {
            final_pct *= 0.95;
        }

        // Session performance adjustment
        let session_gain = (self.bank - self.initial_bank) / self.initial_bank;
        if session_gain > 0.5 {
            // Lock in profits - reduce bet size
            final_pct *= 0.8;
        } else if session_gain < -0.1 {
            // In loss - use more conservative sizing
            final_pct *= 0.9;
        }

        // Risk score from risk management
        let risk_adj = self.risk.position_mult();
        final_pct *= risk_adj;

        // Change point detection - reduce if regime change detected
        if self.change_det.changed {
            final_pct *= 0.7;
        }

        // Ensemble forecaster confidence check
        let ensemble_conf = self.ensemble_forecaster.get_confidence();
        if ensemble_conf < 0.3 {
            final_pct *= 0.85; // Reduce when ensemble is uncertain
        }

        // ===== FEATURE 13: RISK-AWARE RL (CVaR-based sizing) =====
        // Adjust bet based on tail risk (Value at Risk / Conditional VaR)
        let cvar = self.risk_aware_rl.compute_cvar();
        let var = self.risk_aware_rl.compute_var();
        let cvar_risk_adj = self.risk_aware_rl.adjust_for_risk(final_pct, vol_forecast);
        // Reduce bet size if tail risk is high
        if cvar.abs() > 0.15 {
            // High downside tail risk - reduce bet
            final_pct *= 0.85;
        } else if var.abs() > 0.1 && cvar.abs() < 0.05 {
            // Moderate risk but contained tail - can be aggressive
            final_pct *= 1.05;
        }
        // Use the RiskAwareRL's own adjustment as additional guidance
        final_pct = final_pct * 0.7 + cvar_risk_adj.abs() * 0.3;
        // Check if within risk budget
        if !self.risk_aware_rl.is_within_risk_budget() {
            final_pct *= 0.8; // Reduce bet if over risk budget
        }

        // ===== FEATURE 2: PROFIT-WEIGHTED LEARNER =====
        // Adjust based on Sharpe-like performance metric
        let performance_mult = self.profit_weighted_learner.get_performance_multiplier();
        final_pct *= performance_mult;

        // Clamp final percentage
        // EARLY GAME: Much stricter caps
        let max_pct = if self.total_bets < 5 {
            0.05 // First 5 bets: max 5%
        } else if self.total_bets < 10 {
            0.08 // Next 5 bets: max 8%
        } else if self.total_bets < 20 {
            0.12 // Next 10 bets: max 12%
        } else {
            0.30 // Normal max
        };
        final_pct = final_pct.clamp(0.01, max_pct);

        // Calculate final bet
        let bet = (self.bank * final_pct)
            .max(self.min_bet)
            .min(self.bank * max_pct);

        // Store Q-learning state for update
        self.q_learner.last_state = q_state;
        self.q_learner.last_action = q_action;

        bet
    }

    fn streak_mult(&self) -> f32 {
        if self.win_streak >= 6 {
            4.0
        } else if self.win_streak >= 4 {
            3.0
        } else if self.win_streak >= 2 {
            2.0
        } else if self.win_streak >= 1 {
            1.5
        } else {
            1.0
        }
    }

    fn select_high(&mut self) -> bool {
        let model_prediction = self.last_prediction;
        let model_conf = self.last_confidence;

        // Get regime suggestion
        let (_, should_reverse) = self.regime.get_recommended_strategy();

        // Model prediction with confidence
        let model_choice = if model_conf > 0.05 {
            model_prediction > 0.5
        } else {
            self.next_rng() < 0.5
        };

        // Apply regime reversal if suggested
        let mut final_choice = if should_reverse && self.regime.confidence > 0.3 {
            !model_choice
        } else {
            model_choice
        };

        // Pattern memory influence
        let (pw, pl, _pe) = self
            .patterns
            .find_similar(&self.recent_seq.iter().copied().collect::<Vec<_>>(), 5);
        let pattern_total = pw + pl;

        if pattern_total >= 10 {
            let pattern_rate = pw as f32 / pattern_total as f32;
            let pattern_choice = self.next_rng() < pattern_rate;
            // Weight pattern memory based on sample size
            let pattern_weight = (pattern_total as f32 / 50.0).min(0.4);
            if self.next_rng() < pattern_weight {
                final_choice = pattern_choice;
            }
        }

        // Recent sequence bias - if last few were same, consider alternating
        if self.recent_seq.len() >= 5 {
            let last_5: Vec<bool> = self.recent_seq.iter().rev().take(5).copied().collect();
            let same_count = last_5.iter().filter(|&&x| x).count();
            // If 4 or 5 out of 5 were same, bias toward opposite
            if same_count >= 4 {
                final_choice = !final_choice;
            } else if same_count <= 1 {
                final_choice = !final_choice;
            }
        }

        final_choice
    }

    fn update_prog(&mut self, won: bool) {
        match self.current_meta {
            MetaStrategy::Conservative => {
                if won {
                    self.prog_mult = 1.0;
                } else {
                    self.prog_mult = (self.prog_mult + 0.5).min(2.0);
                }
            }
            MetaStrategy::Aggressive => {
                if won {
                    self.prog_mult = (self.prog_mult * 1.5).min(3.0);
                } else {
                    self.prog_mult = 1.0;
                }
            }
            MetaStrategy::Recovery => {
                if won {
                    self.prog_mult = (self.prog_mult - 0.25).max(1.0);
                } else {
                    self.prog_mult = (self.prog_mult + 0.25).min(2.5);
                }
            }
            MetaStrategy::Accumulation => {
                if won {
                    self.cons_wins += 1;
                    if self.cons_wins >= 3 {
                        self.prog_mult = 1.0;
                        self.cons_wins = 0;
                    } else {
                        self.prog_mult = (self.prog_mult * 1.3).min(2.0);
                    }
                } else {
                    self.prog_mult = 1.0;
                    self.cons_wins = 0;
                }
            }
            MetaStrategy::Adaptive => {
                if !won {
                    self.cons_losses += 1;
                    let fib = [1, 1, 2, 3, 5, 8, 13, 21];
                    let idx = (self.cons_losses as usize).min(fib.len() - 1);
                    self.prog_mult = (1.0 + fib[idx] as f32 * 0.1).min(3.0);
                } else {
                    self.cons_losses = 0;
                    self.prog_mult = (self.prog_mult - 0.3).max(1.0);
                }
            }
        }
    }

    fn get_q_state(&self) -> usize {
        let drawdown_pct = (self.initial_bank - self.bank) / self.initial_bank.max(1e-8);
        let streak = if self.win_streak > 0 {
            self.win_streak as i32
        } else {
            -(self.loss_streak as i32)
        };
        let win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
        } else {
            0.5
        };
        self.q_learner
            .get_state(drawdown_pct, streak, self.risk.volatility, win_rate)
    }

    fn update_sharpe(&mut self) {
        if self.recent_returns.len() < 10 {
            return;
        }

        let mean: f32 = self.recent_returns.iter().sum::<f32>() / self.recent_returns.len() as f32;

        // Calculate variance
        let variance: f32 = self
            .recent_returns
            .iter()
            .map(|r| (r - mean).powi(2))
            .sum::<f32>()
            / self.recent_returns.len() as f32;
        let std = variance.sqrt();

        if std > 0.0 {
            self.sharpe_ratio = mean / std;
        }

        // Calculate Sortino ratio (downside deviation)
        let downside_returns: Vec<f32> = self
            .recent_returns
            .iter()
            .filter(|&&r| r < 0.0)
            .copied()
            .collect();

        if !downside_returns.is_empty() {
            let downside_mean: f32 =
                downside_returns.iter().sum::<f32>() / downside_returns.len() as f32;
            let downside_var: f32 = downside_returns
                .iter()
                .map(|r| (r - downside_mean).powi(2))
                .sum::<f32>()
                / downside_returns.len() as f32;
            let downside_std = downside_var.sqrt();

            if downside_std > 0.0 {
                self.sortino_ratio = mean / downside_std;
            }
        }
    }
}

impl AiStrat {
    /// Print comprehensive session summary with ALL component data
    pub fn print_session_summary(&self) {
        println!("\n");
        println!(
            "╔══════════════════════════════════════════════════════════════════════════════╗"
        );
        println!(
            "║                    🎰 SESSION SUMMARY - ALL COMPONENTS 🎰                    ║"
        );
        println!(
            "╚══════════════════════════════════════════════════════════════════════════════╝"
        );

        // ===== OVERALL SESSION STATS =====
        let profit = self.bank - self.initial_bank;
        let profit_pct = (profit / self.initial_bank) * 100.0;
        let win_rate = if self.total_wins + self.total_losses > 0 {
            self.total_wins as f32 / (self.total_wins + self.total_losses) as f32 * 100.0
        } else {
            0.0
        };

        println!(
            "\n┌─────────────────────────────────────────────────────────────────────────────┐"
        );
        println!(
            "│                           📊 SESSION OVERVIEW                                │"
        );
        println!("├─────────────────────────────────────────────────────────────────────────────┤");
        println!(
            "│  Total Bets: {:>8}    │  Wins: {:>6}    │  Losses: {:>6}              │",
            self.total_bets, self.total_wins, self.total_losses
        );
        println!(
            "│  Win Rate: {:>7.2}%    │  Profit: {:>10.8} ({:>+7.2}%)              │",
            win_rate, profit, profit_pct
        );
        println!(
            "│  Bank: {:>13.8}  │  Initial: {:>10.8}  │  Peak: {:>10.8}        │",
            self.bank, self.initial_bank, self.peak_bank
        );
        println!(
            "│  Max Win Streak: {:>4}  │  Max Loss Streak: {:>4}                       │",
            self.max_consecutive_wins, self.max_consecutive_losses
        );
        println!(
            "│  High Bets: {:>7}      │  Low Bets: {:>7}                              │",
            self.high_bets, self.low_bets
        );
        println!(
            "│  High Wins: {:>7}      │  Low Wins: {:>7}                              │",
            self.high_wins, self.low_wins
        );
        println!("└─────────────────────────────────────────────────────────────────────────────┘");

        // ===== GENUINELY INTELLIGENT FEATURES =====
        println!(
            "\n┌─────────────────────────────────────────────────────────────────────────────┐"
        );
        println!(
            "│                    🧠 SMART FEATURES PERFORMANCE                             │"
        );
        println!("├─────────────────────────────────────────────────────────────────────────────┤");

        // Edge Detector
        println!("│  EDGE DETECTOR:                                                             │");
        println!(
            "│    Detected Edge: {:>+6.3}  │  Confidence: {:>5.1}%  │  Has Edge: {}        │",
            self.edge_detector.detected_edge,
            self.edge_detector.edge_confidence * 100.0,
            if self.edge_detector.has_positive_edge() {
                "YES"
            } else {
                "NO "
            }
        );
        println!(
            "│    Total Samples: {:>5}   │  Edge Adjustment: {:>5.2}x                     │",
            self.edge_detector.sample_size,
            self.edge_detector.get_edge_adjustment()
        );

        // Confidence Calibrator
        println!("│                                                                             │");
        println!("│  CONFIDENCE CALIBRATOR:                                                     │");
        println!(
            "│    Calibration Error: {:>5.3}  │  Recent Errors: {:>4}                      │",
            self.confidence_calibrator.calibration_error,
            self.confidence_calibrator.recent_calibration_errors.len()
        );
        println!("│    (Calibration corrects overconfident models)");

        // Strategy Selector
        println!("│                                                                             │");
        println!("│  ADAPTIVE STRATEGY SELECTOR:                                                │");
        println!(
            "│    Current Strategy: {:?}                                                   │",
            self.strategy_selector.current_best
        );
        println!(
            "│    Strategies Used: {} total decisions                                       │",
            self.strategy_selector.strategy_history.len()
        );
        for strat in &self
            .strategy_selector
            .strategies
            .iter()
            .take(3)
            .collect::<Vec<_>>()
        {
            let total = strat.wins + strat.losses;
            let wr = if total > 0 {
                strat.wins as f32 / total as f32 * 100.0
            } else {
                0.0
            };
            println!(
                "│      {:?}: {:>4}W/{:<4}L ({:>5.1}%) Profit: {:>10.6}         │",
                strat.strategy, strat.wins, strat.losses, wr, strat.total_profit
            );
        }

        // Session State
        println!("│                                                                             │");
        println!("│  SESSION STATE ANALYZER:                                                    │");
        println!(
            "│    Current State: {:?}                                                      │",
            self.session_state.get_state()
        );
        println!(
            "│    State Duration: {:>4} bets  │  Risk Modifier: {:>5.2}x                   │",
            self.session_state.state_duration,
            self.session_state.get_state_risk_modifier()
        );
        println!(
            "│    State History: {} transitions recorded                                  │",
            self.session_state.transitions.len()
        );

        // Performance Momentum
        println!("│                                                                             │");
        println!("│  PERFORMANCE MOMENTUM:                                                      │");
        println!(
            "│    Momentum: {:>+6.3}  │  Velocity: {:>+6.3}  │  Acceleration: {:>+6.3}     │",
            self.performance_momentum.momentum,
            self.performance_momentum.velocity,
            self.performance_momentum.acceleration
        );
        println!(
            "│    Improving: {:>5}   │  Declining: {:>5}   │  Adjustment: {:>5.2}x        │",
            if self.performance_momentum.is_improving() {
                "YES"
            } else {
                "NO "
            },
            if self.performance_momentum.is_declining() {
                "YES"
            } else {
                "NO "
            },
            self.performance_momentum.get_momentum_adjustment()
        );

        // Win Predictor
        println!("│                                                                             │");
        println!("│  SESSION WIN PREDICTOR:                                                     │");
        println!(
            "│    Win Probability: {:>5.1}%  │  Should Continue: {:>5}                    │",
            self.win_predictor.get_win_probability() * 100.0,
            if self.win_predictor.should_keep_playing() {
                "YES"
            } else {
                "NO "
            }
        );

        // Bankroll Manager
        println!("│                                                                             │");
        println!("│  SMART BANKROLL MANAGER:                                                    │");
        println!(
            "│    Target Profit: {:>5.0}%  │  Stop Loss: {:>5.0}%                                │",
            self.bankroll_manager.target_profit * 100.0,
            self.bankroll_manager.stop_loss * 100.0
        );
        println!(
            "│    Sessions: {:>5} played, {:>5} won  │  Avg Length: {:>5.0} bets            │",
            self.bankroll_manager.sessions_played,
            self.bankroll_manager.sessions_won,
            self.bankroll_manager.avg_session_length
        );

        // ===== 17 ADVANCED INTELLIGENCE FEATURES =====
        println!("│                                                                             │");
        println!("│  ═══════════════ 17 ADVANCED INTELLIGENCE FEATURES ═══════════════════      │");
        println!("│                                                                             │");

        // Feature 1: Curiosity Engine
        println!("│  1. CURIOSITY ENGINE (Novelty-based Exploration):                          │");
        println!(
            "│     Entropy: {:>5.3}  │  Selection Entropy: {:>5.3}                        │",
            self.curiosity_engine.selection_entropy, self.curiosity_engine.selection_entropy
        );
        println!(
            "│     Active Arms: {:>3}/40 tested  │  Novelty boost for exploration         │",
            self.curiosity_engine
                .arm_recency
                .iter()
                .filter(|&&r| r > 0.1)
                .count()
        );

        // Feature 2: Profit-Weighted Learner
        println!("│                                                                             │");
        println!("│  2. PROFIT-WEIGHTED LEARNER (Sharpe-based rewards):                         │");
        println!(
            "│     Sharpe Ratio: {:>6.3}  │  Performance Mult: {:>5.2}x                   │",
            self.profit_weighted_learner.calculate_sharpe(),
            self.profit_weighted_learner.get_performance_multiplier()
        );
        println!(
            "│     Max Profit: {:>10.6}  │  Max Loss: {:>10.6}                        │",
            self.profit_weighted_learner.max_profit, self.profit_weighted_learner.max_loss
        );

        // Feature 3: Anti-Persistence Detector
        println!("│                                                                             │");
        println!("│  3. ANTI-PERSISTENCE DETECTOR (Pattern breaking):                           │");
        println!(
            "│     Pattern: {:?}  │  Alternation Score: {:>+6.3}                         │",
            self.anti_persistence.last_pattern_type, self.anti_persistence.alternation_score
        );
        println!(
            "│     Current Streak: {:>3} {:?}s  │  Streak Signal: {:>+5.2}                │",
            self.anti_persistence.current_streak_len,
            if self.anti_persistence.current_streak_type == Some(true) {
                "win"
            } else {
                "loss"
            },
            self.anti_persistence.get_streak_signal()
        );

        // Feature 4: Lookahead Planner
        println!("│                                                                             │");
        println!("│  4. LOOKAHEAD PLANNER (Monte Carlo simulation):                             │");
        println!(
            "│     Horizon: {:>2} bets  │  Simulations: {:>5}                              │",
            self.lookahead_planner.horizon, self.lookahead_planner.num_simulations
        );
        println!(
            "│     Expected Return: {:>+10.6}  │  Top 3 arm values tracked              │",
            self.lookahead_planner.get_expected_return()
        );

        // Feature 5: Ensemble Manager
        println!("│                                                                             │");
        println!(
            "│  5. ENSEMBLE MANAGER (Auto-pruning & weighting):                             │"
        );
        println!(
            "│     Active Components: {:>3}  │  Pruning Threshold: {:>4.0}%              │",
            self.ensemble_manager.active_count(),
            self.ensemble_manager.pruning_threshold * 100.0
        );

        // Feature 6: Session Memory
        println!("│                                                                             │");
        println!("│  6. SESSION MEMORY (Cross-session learning):                                │");
        println!(
            "│     Sessions Recorded: {:>3}  │  Casino Model Confidence: {:>5.2}          │",
            self.session_memory.total_sessions, self.session_memory.casino_model.model_confidence
        );
        println!(
            "│     Alternation Bias: {:>+5.3}  │  Streak Tendency: {:>+5.3}              │",
            self.session_memory.casino_model.alternation_bias,
            self.session_memory.casino_model.streak_tendency
        );

        // Feature 7: Advanced Confidence Calibrator
        println!("│                                                                             │");
        println!(
            "│  7. CALIBRATED CONFIDENCE (Temperature scaling):                             │"
        );
        println!(
            "│     Calibration Error: {:>5.3}  │  Quality: {:>5.1}%                        │",
            self.advanced_calibrator.calibration_error,
            self.advanced_calibrator.get_calibration_quality() * 100.0
        );
        println!(
            "│     Temperature: {:>5.3}  │  {} bins for reliability diagram                │",
            self.advanced_calibrator.temperature, self.advanced_calibrator.num_bins
        );

        // Feature 8: Transformer Sequence Predictor
        println!("│                                                                             │");
        println!("│  8. TRANSFORMER SEQUENCE (Multi-head attention):                            │");
        println!(
            "│     Attention Heads: {:>2}  │  Position Embeddings: {:>3}                   │",
            self.transformer_predictor.attention_heads.len(),
            self.transformer_predictor.position_embeddings.len()
        );
        println!(
            "│     Pattern Memory: {:>3} patterns stored                                    │",
            self.transformer_predictor.pattern_memory.len()
        );

        // Feature 9: Episodic Memory
        println!("│                                                                             │");
        println!("│  9. EPISODIC MEMORY (Important sequences):                                  │");
        println!(
            "│     Episodes Stored: {:>4}  │  Threshold: {:>5.2}                          │",
            self.episodic_memory.episodes.len(),
            self.episodic_memory.retrieval_threshold
        );

        // Feature 10: Counterfactual Regret Minimizer
        println!("│                                                                             │");
        println!("│  10. COUNTERFACTUAL REGRET (Optimal mixed strategies):                     │");
        println!(
            "│     Info Sets: {:>5}  │  Iterations: {:>6}                                  │",
            self.cfr.regrets.len(),
            self.cfr.iterations
        );

        // Feature 11: Bayesian Model Averager
        println!("│                                                                             │");
        println!("│  11. BAYESIAN MODEL AVERAGING (Uncertainty weighting):                      │");
        println!(
            "│     Models: {:>3}  │  Prior Strength: {:>5.2}                               │",
            self.bayesian_averager.num_models, self.bayesian_averager.prior_strength
        );
        println!(
            "│     Pattern Memory: {:>3} patterns stored                                    │",
            self.transformer_predictor.pattern_memory.len()
        );

        // Feature 9: Episodic Memory
        println!("│                                                                             │");
        println!("│  9. EPISODIC MEMORY (Important sequences):                                  │");
        println!(
            "│     Episodes Stored: {:>4}  │  Threshold: {:>5.2}                          │",
            self.episodic_memory.episodes.len(),
            self.episodic_memory.retrieval_threshold
        );

        // Feature 10: Counterfactual Regret Minimizer
        println!("│                                                                             │");
        println!("│  10. COUNTERFACTUAL REGRET (Optimal mixed strategies):                     │");
        println!(
            "│     Info Sets: {:>5}  │  Iterations: {:>6}                                  │",
            self.cfr.regrets.len(),
            self.cfr.iterations
        );

        // Feature 11: Bayesian Model Averager
        println!("│                                                                             │");
        println!("│  11. BAYESIAN MODEL AVERAGING (Uncertainty weighting):                      │");
        println!(
            "│     Models: {:>3}  │  Prior Strength: {:>5.2}                               │",
            self.bayesian_averager.num_models, self.bayesian_averager.prior_strength
        );

        // Feature 12: Anomaly Detector
        println!("│                                                                             │");
        println!("│  12. ANOMALY DETECTOR (CUSUM & change points):                              │");
        println!(
            "│     Baseline Mean: {:>6.3}  │  Baseline STD: {:>6.3}                        │",
            self.anomaly_detector.baseline_mean, self.anomaly_detector.baseline_std
        );
        println!(
            "│     Anomalies Detected: {:>4}  │  Change Points: {:>4}                     │",
            self.anomaly_detector.anomalies.len(),
            self.anomaly_detector.change_points.len()
        );

        // Feature 13: Risk-Aware RL
        println!("│                                                                             │");
        println!(
            "│  13. RISK-AWARE RL (VaR/CVaR calculations):                                  │"
        );
        println!(
            "│     VaR ({}%): {:>+8.4}  │  CVaR: {:>+8.4}                                │",
            (self.risk_aware_rl.alpha * 100.0) as u32,
            self.risk_aware_rl.compute_var(),
            self.risk_aware_rl.compute_cvar()
        );
        println!(
            "│     Within Risk Budget: {:>5}  │  Risk Budget: {:>5.0}%                     │",
            if self.risk_aware_rl.is_within_risk_budget() {
                "YES"
            } else {
                "NO"
            },
            self.risk_aware_rl.risk_budget * 100.0
        );

        // Feature 14: Hierarchical RL
        println!("│                                                                             │");
        println!("│  14. HIERARCHICAL RL (Goal-directed decisions):                             │");
        println!(
            "│     Current Goal: {:?}                                        │",
            self.hierarchical_rl.current_goal
        );
        println!(
            "│     Goal Steps: {:>5}  │  Q-Values tracked per goal                        │",
            self.hierarchical_rl.goal_steps
        );

        // Feature 15: Model-Based RL
        println!("│                                                                             │");
        println!("│  15. MODEL-BASED RL (Environment dynamics):                                 │");
        println!(
            "│     Transitions Learned: {:>5}  │  States Explored: {:>5}                   │",
            self.model_based_rl.transition_model.len(),
            self.model_based_rl.state_counts.len()
        );
        println!(
            "│     Planning Depth: {:>2}  │  Reward Map Size: {:>5}                        │",
            self.model_based_rl.planning_depth,
            self.model_based_rl.reward_model.len()
        );

        // Feature 16: Inverse RL
        println!("│                                                                             │");
        println!("│  16. INVERSE RL (Learning from wins):                                       │");
        println!(
            "│     Expert Trajectories: {:>3}  │  Feature Dim: {:>3}                       │",
            self.inverse_rl.expert_trajectories.len(),
            self.inverse_rl.feature_dim
        );

        // Feature 17: Theory of Mind
        println!("│                                                                             │");
        println!(
            "│  17. THEORY OF MIND (Casino behavior modeling):                              │"
        );
        println!(
            "│     Prediction Accuracy: {:>5.1}%  │  Counter-Strategy: {:>5.3}            │",
            self.theory_of_mind.prediction_accuracy * 100.0,
            self.theory_of_mind.get_counter_strategy()
        );
        println!(
            "│     Casino Alt Prob: {:>5.3}  │  Streak Tendency: {:>5.3}                  │",
            self.theory_of_mind.casino_model.alternation_probability,
            self.theory_of_mind.casino_model.streak_tendency
        );

        println!("└─────────────────────────────────────────────────────────────────────────────┘");

        // ===== VOTING TRACKER - ALL COMPONENTS =====
        println!(
            "\n┌─────────────────────────────────────────────────────────────────────────────┐"
        );
        println!(
            "│                      🗳️ VOTING COMPONENT PERFORMANCE                          │"
        );
        println!("├─────────────────────────────────────────────────────────────────────────────┤");

        // Get all component summaries
        let top_performers = self.voting_tracker.get_top_performers(50);
        let total_high = self.voting_tracker.total_high_votes;
        let total_low = self.voting_tracker.total_low_votes;
        let cum_high = self.voting_tracker.cumulative_high_votes;
        let cum_low = self.voting_tracker.cumulative_low_votes;
        let dir_correct = self.voting_tracker.direction_correct_predictions;
        let dir_total = self.voting_tracker.total_direction_predictions;

        println!("│  VOTE TOTALS:                                                               │");
        println!(
            "│    This Round: High={:>8.1}  Low={:>8.1}  │  Cumulative: High={:>8.1} Low={:>8.1} │",
            total_high, total_low, cum_high, cum_low
        );
        println!(
            "│    Direction Accuracy: {:>5.1}%  ({:>4}/{:<4} correct)                    │",
            if dir_total > 0 {
                dir_correct as f32 / dir_total as f32 * 100.0
            } else {
                0.0
            },
            dir_correct,
            dir_total
        );
        println!("│                                                                             │");
        println!("│  TOP PERFORMING COMPONENTS:                                                 │");
        println!("│  ┌──────────────────────────────┬──────────┬──────────┬──────────┐          │");
        println!("│  │ Component                    │ Accuracy │ Recent   │ Weight   │          │");
        println!("│  ├──────────────────────────────┼──────────┼──────────┼──────────┤          │");

        for (i, (name, acc)) in top_performers.iter().enumerate() {
            if i < 20 {
                // Show top 20
                let weight = self.voting_tracker.get_weight(name);
                println!(
                    "│  │ {:<28} │ {:>6.1}%  │ {:>6.1}%  │ {:>6.2}x   │          │",
                    if name.len() > 28 { &name[..28] } else { name },
                    acc * 100.0,
                    acc * 100.0, // Using acc for recent too for simplicity
                    weight
                );
            }
        }
        println!("│  └──────────────────────────────┴──────────┴──────────┴──────────┘          │");
        println!(
            "│  Total Components Tracked: {}                                               │",
            self.voting_tracker.components.len()
        );
        println!("└─────────────────────────────────────────────────────────────────────────────┘");

        // ===== ABSURD FEATURES (the fun stuff) =====
        println!(
            "\n┌─────────────────────────────────────────────────────────────────────────────┐"
        );
        println!(
            "│                      🌙 ABSURD FEATURES STATUS 🌙                            │"
        );
        println!("├─────────────────────────────────────────────────────────────────────────────┤");

        // Lunar Phase
        let moon_phase = self.lunar_phase.current_phase;
        let moon_name = if moon_phase < 0.125 {
            "New Moon"
        } else if moon_phase < 0.25 {
            "Waxing Crescent"
        } else if moon_phase < 0.375 {
            "First Quarter"
        } else if moon_phase < 0.5 {
            "Waxing Gibbous"
        } else if moon_phase < 0.625 {
            "FULL MOON 🌕"
        } else if moon_phase < 0.75 {
            "Waning Gibbous"
        } else if moon_phase < 0.875 {
            "Last Quarter"
        } else {
            "Waning Crescent"
        };
        println!(
            "│  🌙 LUNAR PHASE: {} ({:.0}%)                                              │",
            moon_name,
            moon_phase * 100.0
        );

        // Biorhythm
        let bio_energy = self.biorhythm.get_energy_level();
        println!(
            "│  💪 BIORHYTHM: Physical={:>5.2} Emotional={:>5.2} Intellectual={:>5.2}        │",
            self.biorhythm.physical_cycle,
            self.biorhythm.emotional_cycle,
            self.biorhythm.intellectual_cycle
        );
        println!(
            "│     Energy Level: {:>5.2}                                                  │",
            bio_energy
        );

        // Sentiment
        println!(
            "│  📊 SENTIMENT: Fear/Greed={:>5.1}  Hope={:>5.2}  Despair={:>5.2}             │",
            self.sentiment_analyzer.fear_greed_index,
            self.sentiment_analyzer.hope_index,
            self.sentiment_analyzer.despair_index
        );
        println!(
            "│     Euphoria Events: {:>4}  │  Panic Events: {:>4}                          │",
            self.sentiment_analyzer.euphoria_counter, self.sentiment_analyzer.panic_counter
        );

        // Dunning-Kruger
        println!(
            "│  🎓 DUNNING-KRUGER SCORE: {:.3}                                             │",
            self.dunning_kruger.dunning_kruger_score
        );
        println!(
            "│     Overconfidence when wrong: {:.2}%  │  Confident when right: {:.2}%      │",
            self.dunning_kruger.confidence_when_wrong * 100.0,
            self.dunning_kruger.confidence_when_right * 100.0
        );
        println!(
            "│     Overconfidence Events: {:>4}                                            │",
            self.dunning_kruger.recent_overconfidence_events
        );

        // Hot Hand
        println!(
            "│  🔥 HOT HAND: Detected={:>5}  │  Fallacy Score={:>5.2}                       │",
            if self.hot_hand_tracker.detected_hot_hand {
                "YES"
            } else {
                "NO "
            },
            self.hot_hand_tracker.fallacy_score
        );
        println!(
            "│     Hot Hand Wins: {:>4}  │  Hot Hand Losses: {:>4}                         │",
            self.hot_hand_tracker.hot_hand_wins, self.hot_hand_tracker.hot_hand_losses
        );

        // Chaos Dragon
        println!(
            "│  🐉 CHAOS DRAGON: Hunger={:>5.2}  Mood={:>5.2}  Decisions Eaten={:>4}        │",
            self.chaos_dragon.hunger,
            self.chaos_dragon.dragon_mood,
            self.chaos_dragon.decisions_eaten
        );

        // Divine Intervention
        println!(
            "│  ✨ DIVINE INTERVENTION: Interventions={:>4}  Miracles={:>4}  Blessed={}   │",
            self.divine_intervention.interventions_received,
            self.divine_intervention.miracles_witnessed,
            if self.divine_intervention.blessing_active {
                "YES"
            } else {
                "NO "
            }
        );

        // Conspiracy Detector
        println!(
            "│  👁️ CONSPIRACY DETECTOR: Paranoia={:>5.2}%                                 │",
            self.conspiracy_detector.paranoid_level * 100.0
        );
        println!(
            "│     Suspicious Losses: {:>4}  Patterns Found: {:>4}                         │",
            self.conspiracy_detector.suspicious_losses,
            self.conspiracy_detector.suspicious_patterns.len()
        );

        // Schrödinger's Cat
        let cat_state = match self.schrodinger_cat.cat_state {
            CatState::Alive => "ALIVE 🐱",
            CatState::Dead => "DEAD 💀",
            CatState::Superposition => "Schrödinger's Cat 👻",
        };
        println!(
            "│  🐱 SCHRÖDINGER'S CAT: {}  Alive Prob={:>5.1}%                              │",
            cat_state,
            self.schrodinger_cat.alive_probability * 100.0
        );
        println!(
            "│     Observations: {:>6}                                                    │",
            self.schrodinger_cat.observation_count
        );

        // Karma
        println!(
            "│  ⚖️ KARMA CALCULATOR: Balance={:>+6.3}  Universe Debt={:>+6.3}               │",
            self.karma_calculator.karma_balance, self.karma_calculator.universe_debt
        );
        println!(
            "│     Good Deeds: {:>5.0}  │  Bad Deeds: {:>5.0}  │  Instant Karma Events: {:>3} │",
            self.karma_calculator.good_deeds,
            self.karma_calculator.bad_deeds,
            self.karma_calculator.instant_karma_events
        );

        // Quantum Entanglement
        println!(
            "│  ⚛️ QUANTUM ENTANGLEMENT: Coherence={:>5.2}  Spooky Actions={:>4}            │",
            self.quantum_entanglement.coherence, self.quantum_entanglement.spooky_action_count
        );

        // Probability Manipulator
        println!(
            "│  🎲 PROBABILITY MANIPULATOR: Belief={:>5.2}  Reality Pushback={:>5.2}        │",
            self.probability_manipulator.belief_power,
            self.probability_manipulator.reality_pushback
        );
        println!(
            "│     Attempts: {:>5}  │  Successful: {:>5}  │  Manifestation Energy: {:>5.2}  │",
            self.probability_manipulator.manipulation_attempts,
            self.probability_manipulator.successful_manipulations,
            self.probability_manipulator.manifestation_energy
        );

        // Luck Bank
        println!(
            "│  🍀 LUCK BANK: Balance={:>6.3}  │  Credit Score={:>5.0}  │  Overdrawn={}     │",
            self.luck_bank.luck_balance,
            self.luck_bank.luck_credit_score,
            if self.luck_bank.is_overdrawn {
                "YES"
            } else {
                "NO "
            }
        );
        println!(
            "│     Deposits: {:>5}  │  Withdrawals: {:>5}                                 │",
            self.luck_bank.deposits, self.luck_bank.withdrawals
        );

        // Philosophical Uncertainty
        println!(
            "│  🤔 PHILOSOPHICAL UNCERTAINTY: Doubt={:>5.2}  Free Will={:>5.2}              │",
            self.philosophical_uncertainty.philosophical_doubt,
            self.philosophical_uncertainty.free_will_belief
        );
        println!(
            "│     Determinism: {:>5.2}  │  Existential Crises: {:>4}  │  Enlightenments: {:>3} │",
            self.philosophical_uncertainty.determinism_score,
            self.philosophical_uncertainty.existential_crises,
            self.philosophical_uncertainty.enlightenment_moments
        );

        // Akashic Record
        println!(
            "│  📜 AKASHIC RECORD READER: Connection={:>5.2}  Downloads={:>4}              │",
            self.akashic_reader.connection_strength, self.akashic_reader.downloads_from_akashic
        );
        if !self.akashic_reader.cosmic_insights.is_empty() {
            println!(
                "│     Latest Insight: \"{}\"                             │",
                self.akashic_reader
                    .cosmic_insights
                    .last()
                    .unwrap_or(&"None yet".to_string())
                    .chars()
                    .take(50)
                    .collect::<String>()
            );
        }

        // Retrocausality
        println!(
            "│  ⏰ RETROCAUSALITY ENGINE: Temporal Paradoxes={:>4}  Causality Violations={:>5.2}",
            self.retrocausality_engine.temporal_paradoxes,
            self.retrocausality_engine.causality_violations
        );

        // Pattern Cult
        println!(
            "│  🔮 PATTERN CULT: Membership Level={:>5.2}%  Reality Checks={:>4}            │",
            self.pattern_cult_detector.cult_membership_level * 100.0,
            self.pattern_cult_detector.reality_check_counter
        );
        println!(
            "│     Patterns Believed: {:>4}  │  Patterns Disproven: {:>4}                  │",
            self.pattern_cult_detector.patterns_believed,
            self.pattern_cult_detector.patterns_disproven
        );
        println!(
            "│     Sacred Numbers: {:?}                                    │",
            self.pattern_cult_detector
                .sacred_numbers
                .iter()
                .take(5)
                .collect::<Vec<_>>()
        );

        println!("└─────────────────────────────────────────────────────────────────────────────┘");

        // ===== MULTI-ARM BANDIT PERFORMANCE =====
        println!(
            "\n┌─────────────────────────────────────────────────────────────────────────────┐"
        );
        println!(
            "│                      🎰 MULTIPLIER ARM PERFORMANCE                           │"
        );
        println!("├─────────────────────────────────────────────────────────────────────────────┤");

        // Sort arms by pull count for display
        let mut sorted_arms: Vec<_> = self.arms.iter().enumerate().collect();
        sorted_arms.sort_by(|a, b| b.1.pull_count.cmp(&a.1.pull_count));

        println!("│  ┌─────┬──────────┬─────────┬─────────┬─────────┬─────────┐                 │");
        println!("│  │ Arm │ Mult     │ Pulls   │ Wins(α) │ WinRate │ Profit  │                 │");
        println!("│  ├─────┼──────────┼─────────┼─────────┼─────────┼─────────┤                 │");

        for (i, arm) in sorted_arms.iter().take(15) {
            let wins = (arm.alpha - 1.0) as u32; // Alpha starts at 1, so wins = alpha - 1
            let wr = if arm.pull_count > 0 {
                wins as f32 / arm.pull_count as f32 * 100.0
            } else {
                0.0
            };
            println!(
                "│  │ {:>3} │ {:>7.2}x │ {:>7} │ {:>7} │ {:>6.1}% │ {:>+8.6}│                 │",
                i, arm.multiplier, arm.pull_count, wins, wr, arm.total_profit
            );
        }
        println!("│  └─────┴──────────┴─────────┴─────────┴─────────┴─────────┘                 │");
        println!(
            "│  Total Arms: {}                                                              │",
            self.arms.len()
        );
        println!("└─────────────────────────────────────────────────────────────────────────────┘");

        // ===== FINAL VERDICT =====
        let overall_verdict = if profit > self.initial_bank * 0.5 {
            "🏆 LEGENDARY SESSION! 🏆"
        } else if profit > self.initial_bank * 0.2 {
            "🎉 GREAT SESSION!"
        } else if profit > 0.0 {
            "✅ PROFITABLE SESSION"
        } else if profit > -self.initial_bank * 0.1 {
            "😐 MODEST LOSS"
        } else if profit > -self.initial_bank * 0.3 {
            "⚠️ SIGNIFICANT LOSS"
        } else {
            "💀 HEAVY LOSS - SURVIVED!"
        };

        println!(
            "\n┌─────────────────────────────────────────────────────────────────────────────┐"
        );
        println!(
            "│                           📈 FINAL VERDICT                                   │"
        );
        println!("├─────────────────────────────────────────────────────────────────────────────┤");
        println!("│                                                                             │");
        println!(
            "│                          {}                          │",
            overall_verdict
        );
        println!("│                                                                             │");
        println!(
            "│  Started with: {:>14.8}                                    │",
            self.initial_bank
        );
        println!(
            "│  Ended with:   {:>14.8}                                    │",
            self.bank
        );
        println!(
            "│  Net Profit:   {:>+14.8} ({:>+7.2}%)                        │",
            profit, profit_pct
        );
        println!("│                                                                             │");
        println!(
            "│  Best Component: {}                                          │",
            top_performers
                .first()
                .map(|(n, _)| n.as_str())
                .unwrap_or("N/A")
        );
        println!(
            "│  Session State: {:?}                                             │",
            self.session_state.get_state()
        );
        println!(
            "│  Edge Detected: {} (confidence: {:.1}%)                              │",
            if self.edge_detector.has_positive_edge() {
                "YES"
            } else {
                "NO "
            },
            self.edge_detector.edge_confidence * 100.0
        );
        println!("│                                                                             │");
        println!("└─────────────────────────────────────────────────────────────────────────────┘");
        println!();
    }

    /// Train all AI models after a bet result
    fn train_models_after_result(&mut self, won: bool, profit: f32) {
        // ============================================================================
        // ANTI-OVERTRAINING: Train LESS frequently as we learn more
        // ============================================================================
        // Overfitting happens when models see the same patterns repeatedly
        // Solution: DECAY training frequency as total_bets increases

        let base_train_rate = if self.total_bets < 100 {
            1.0 // Train on every bet for first 100 (learning phase)
        } else if self.total_bets < 500 {
            0.8 // Train 80% of bets (rapid learning)
        } else if self.total_bets < 2000 {
            0.5 // Train 50% of bets (consolidation)
        } else if self.total_bets < 10000 {
            0.3 // Train 30% of bets (stable learning)
        } else {
            0.15 // Train only 15% of bets after 10k (prevent overfitting)
        };

        // Skip training randomly based on decay
        if self.next_rng() > base_train_rate {
            // Still update counters but skip weight updates
            self.ensemble_manager.update_meta_weights();
            return;
        }

        let reward = if won { 1.0 } else { -1.0 };
        let scaled_reward = profit.signum() * profit.abs().ln_1p(); // Log-scaled reward

        // ============================================================================
        // LEARNING RATE DECAY - Prevent overfitting to recent outcomes
        // ============================================================================
        // Learning rate exponentially decays with total bets
        let lr_decay = (0.9995_f32).powi(self.total_bets as i32); // ~0.6 after 1000 bets, ~0.05 after 10000
        let effective_lr = 0.1 * lr_decay; // Base lr * decay

        // ===== FEATURE 2: Profit-Weighted Learning =====
        let profit_weighted_reward = self.profit_weighted_learner.record_profit(profit);
        let performance_mult = self.profit_weighted_learner.get_performance_multiplier();

        // ===== FEATURE 3: Anti-Persistence Detection =====
        self.anti_persistence.record_outcome(won);
        let (_high_adj, _low_adj) = self.anti_persistence.get_prediction_adjustment();
        let streak_signal = self.anti_persistence.get_streak_signal();

        // ===== FEATURE 4: Lookahead Planning =====
        // Calculate win rates for each arm for planning
        let win_rates: Vec<f32> = self.arms.iter().map(|arm| arm.win_rate()).collect();
        let multipliers: Vec<f32> = self.arms.iter().map(|arm| arm.multiplier).collect();
        self.lookahead_planner
            .plan(self.bank, &win_rates, &multipliers);

        // ===== FEATURE 5: Ensemble Manager =====
        // Update component scores based on result (will be called per-component in voting)
        self.ensemble_manager.update_meta_weights();

        // ===== FEATURE 6: Session Memory =====
        let _time_mult = self
            .session_memory
            .get_time_adjusted_multiplier(self.total_bets);
        let (alt_bias, streak_tendency) = self.session_memory.get_casino_prediction();

        // ===== FEATURE 7: Calibrated Confidence =====
        self.advanced_calibrator.record(self.last_confidence, won);
        let _calibration_quality = self.advanced_calibrator.get_calibration_quality();

        // ===== FEATURE 1: Curiosity Engine =====
        // Record prediction error for intrinsic motivation
        let predicted_win_rate = (100.0 - self.house_percent) / self.multiplier / 100.0;
        self.curiosity_engine
            .record_prediction_error(self.last_arm_idx, predicted_win_rate, won);
        self.curiosity_engine.record_selection(self.last_arm_idx);

        // 1. Train Bayesian Arms (Thompson Sampling)
        self.arms[self.last_arm_idx].update(won, profit);

        // 2. Train Q-Learning (simplified state)
        // Map arm index (0-39) to Q-action (0-9) by dividing by 4
        let q_action = (self.last_multiplier_action / 4).min(9);
        self.q_learner.update(
            0, // simplified state
            q_action,
            reward * performance_mult, // Apply profit-weighted reward
            0,
        );

        // Note: effective_lr applied via scaled_reward which includes performance_mult
        // Q-Learning uses reward * performance_mult which already decays via lr_decay

        // 3. Update LinUCB - with regularization to prevent overconfidence
        let regularized_reward = scaled_reward * lr_decay;
        self.linucb
            .update(self.last_arm_idx, &self.last_context, regularized_reward);

        // 4. Train Policy Gradient (store transition then update)
        // Only update periodically to prevent overfitting
        self.policy_gradient.store_transition(
            self.last_context.clone(),
            self.last_multiplier_action,
            scaled_reward * performance_mult * lr_decay, // Apply lr decay
        );
        // Update less frequently as we get more data
        let pg_update_freq = if self.total_bets < 500 {
            10
        } else if self.total_bets < 2000 {
            25
        } else {
            50
        };
        if self.policy_gradient.action_history.len() >= pg_update_freq {
            self.policy_gradient.update();
        }

        // 5. Store in Replay Buffer for DQN
        let next_dd = self.risk.drawdown;
        let next_context = vec![
            next_dd,
            self.win_streak as f32 / 100.0,
            self.loss_streak as f32 / 100.0,
        ];
        self.replay_buffer.push(
            self.last_context.clone(),
            self.last_multiplier_action,
            reward * performance_mult,
            next_context,
        );

        // 6. Train DQN less frequently as we accumulate data (prevents overfitting)
        let dqn_train_freq = if self.total_bets < 500 {
            10
        } else if self.total_bets < 2000 {
            25
        } else {
            50
        };
        if self.replay_buffer.len() >= 32 && self.total_bets % dqn_train_freq == 0 {
            self.dqn_agent.train(32);
        }

        // 7. Update Markov Chain (observe the outcome)
        let last_outcome = *self.recent_seq.back().unwrap_or(&true);
        self.markov.observe(
            &self.recent_seq.iter().copied().collect::<Vec<_>>(),
            last_outcome,
        );

        // 8. Update ExP3 Bandit - discounted updates
        self.exp3_bandit
            .update(self.last_arm_idx, scaled_reward * lr_decay);

        // ===== TRAIN ALL 17 ADVANCED INTELLIGENCE FEATURES =====
        // Note: All training now uses effective_lr/via lr_decay to prevent overfitting

        // FEATURE 8: Transformer Sequence Predictor - decay learning rate
        if self.recent_rolls.len() >= 10 {
            let seq: Vec<f32> = self
                .recent_rolls
                .iter()
                .map(|&r| r as f32 / 10000.0)
                .collect();
            let outcome = if won { 1.0 } else { 0.0 };
            // Decay learning rate for transformer (starts at 0.01, decays same way)
            let transformer_lr = 0.01 * lr_decay;
            self.transformer_predictor
                .update(&seq, outcome, transformer_lr);
        }

        // FEATURE 9: Episodic Memory - store important episodes (no training, just memory)
        let surprise_score = (predicted_win_rate - if won { 1.0 } else { 0.0 }).abs();
        if surprise_score > 0.3 || profit.abs() > self.bank * 0.1 {
            // High surprise or big win/loss - store this episode
            self.episodic_memory.store_episode(
                self.last_context.clone(),
                vec![self.last_arm_idx],
                profit,
                surprise_score,
            );
        }

        // FEATURE 10: Counterfactual Regret Minimizer - decay updates
        let info_set: Vec<bool> = self.recent_seq.iter().rev().take(10).copied().collect();
        let cf_payoff = if won { profit } else { -profit.abs() };
        // CFR updates scaled by lr_decay to prevent overfitting
        self.cfr.update_regret(
            &info_set,
            self.last_arm_idx.min(39),
            profit * lr_decay,
            cf_payoff * lr_decay,
        );

        // FEATURE 11: Bayesian Model Averager - update weights based on likelihood (scaled)
        // Compute log likelihood of the outcome given the Bayesian prediction
        let bayesian_ll = if won {
            (self
                .bayesian_averager
                .model_log_weights
                .first()
                .copied()
                .unwrap_or(0.0))
            .exp()
            .ln()
        } else {
            (1.0 - self
                .bayesian_averager
                .model_log_weights
                .first()
                .copied()
                .unwrap_or(0.0))
            .exp()
            .ln()
        };
        // Scale update by lr_decay
        self.bayesian_averager
            .update_model_weight(0, bayesian_ll * 0.1 * lr_decay);

        // FEATURE 12: Anomaly Detector
        self.anomaly_detector
            .detect(if won { 1.0 } else { 0.0 }, self.total_bets);

        // FEATURE 13: Risk-Aware RL - record return for CVaR
        self.risk_aware_rl
            .record_return(profit / self.initial_bank.max(1e-8));

        // FEATURE 14: Hierarchical RL - update goal Q-values
        self.hierarchical_rl
            .update_goal(if won { profit.abs() } else { -profit.abs() });

        // FEATURE 15: Model-Based RL - observe transition
        let state_bytes: Vec<u8> = self
            .recent_seq
            .iter()
            .rev()
            .take(20)
            .map(|&b| if b { 1 } else { 0 })
            .collect();
        let next_state_bytes: Vec<u8> = {
            let mut s = state_bytes.clone();
            s.push(if won { 1 } else { 0 });
            s
        };
        self.model_based_rl
            .observe(state_bytes, self.last_arm_idx, next_state_bytes, profit);

        // FEATURE 16: Inverse RL - store successful trajectories
        if profit > 0.0 {
            self.inverse_rl
                .store_expert_trajectory(self.last_context.clone());
        }
        // Update inverse RL reward weights
        self.inverse_rl.update_reward_weights();

        // FEATURE 17: Theory of Mind - update casino beliefs
        let predicted = self.last_prediction > 0.5;
        self.theory_of_mind
            .update_beliefs(won, predicted, self.high);

        // ===== Update casino model with session memory =====
        self.session_memory
            .update_casino_model(self.anti_persistence.alternation_score, streak_signal);

        // ============================================================================
        // ANTI-OVERFITTING: PERIODIC MODEL RESET
        // ============================================================================
        // If models are performing worse than random after sufficient data, partially reset
        if self.total_bets % 500 == 0 && self.total_bets > 1000 {
            let win_rate = if self.total_wins + self.total_losses > 0 {
                self.total_wins as f32 / (self.total_wins + self.total_losses) as f32
            } else {
                0.5
            };

            // If win rate is below random (47.5%), models may be overfitting
            if win_rate < 0.45 {
                eprintln!(
                    "[ANTI-OVERFIT] Win rate {:.1}% below random at bet {} - applying regularization!",
                    win_rate * 100.0, self.total_bets
                );
                // Decay exploration to force trying new things
                self.curiosity_engine.selection_entropy =
                    (self.curiosity_engine.selection_entropy + 0.5).min(1.0);
                // Decay Q-values to forget potentially wrong patterns
                for row in &mut self.q_learner.q_table {
                    for val in row {
                        *val *= 0.9; // Decay all Q-values
                    }
                }
            }
        }

        // Debug: Log training progress periodically
        if self.total_bets % 100 == 0 {
            let sharpe = self.profit_weighted_learner.calculate_sharpe();
            let calibration = self.advanced_calibrator.get_calibration_quality();
            let active_components = self.ensemble_manager.active_count();
            eprintln!(
                "[TRAINING] Bet {} | Sharpe: {:.3} | Calibration: {:.3} | Active components: {} | Curiosity entropy: {:.3} | LR decay: {:.3}",
                self.total_bets, sharpe, calibration, active_components, self.curiosity_engine.selection_entropy, lr_decay
            );
        }
    }
}

// ============================================================================
// Strategy Trait Implementation
// ============================================================================

impl Strategy for AiStrat {
    fn with_initial_bet(mut self, bet: f32) -> Self {
        self.current_bet = bet;
        self.min_bet = bet;
        self
    }

    fn with_balance(mut self, bal: f32) -> Self {
        self.bank = bal;
        self.initial_bank = bal;
        self.peak_bank = bal;
        self.risk.peak = bal;
        self.profit = 0.0;
        self.session_profit = 0.0;
        self.debt = 0.0;
        self
    }

    fn with_min_bet(mut self, bet: f32) -> Self {
        self.min_bet = bet;
        self.current_bet = bet;
        self
    }

    fn set_balance(&mut self, bal: f32) {
        // === FULL SESSION RESET - Keep AI learned weights ===

        // Bank state
        self.bank = bal;
        self.initial_bank = bal;
        self.peak_bank = bal;
        self.session_high = bal;
        self.session_low = bal;
        self.current_bet = self.min_bet;

        // Profit/debt tracking
        self.profit = 0.0;
        self.session_profit = 0.0;
        self.debt = 0.0;

        // Streaks
        self.loss_streak = 0;
        self.win_streak = 0;
        self.cons_wins = 0;
        self.cons_losses = 0;
        self.max_consecutive_wins = 0;
        self.max_consecutive_losses = 0;

        // High/low tracking
        self.high_wins = 0;
        self.low_wins = 0;
        self.high_bets = 0;
        self.low_bets = 0;
        self.high_win_streak = 0;
        self.low_win_streak = 0;

        // Risk state
        self.risk = RiskState::new();

        // === KEEP LEARNED AI STATE ===
        // NOT reset:
        // - DQN weights (learned)
        // - Policy gradient weights (learned)
        // - Q-learner Q-table (learned)
        // - Markov chain transitions (learned)
        // - Pattern memory (learned)
        // - LinUCB alpha/beta (learned)
        // - All other neural network weights
    }

    fn get_next_bet(&mut self, _pred: f32, _conf: f32) -> (f32, f32, f32, bool) {
        self.total_bets += 1;

        // Build context for all AI systems
        let dd = self.risk.drawdown;
        let ws = self.win_streak;
        let ls = self.loss_streak;
        let context = self.build_context(dd, ws, ls);

        // ===== CALCULATE TRUE DRAWDOWN FROM INITIAL BANK =====
        let initial_bank_dd = (self.initial_bank - self.bank) / self.initial_bank.max(1e-8);

        // ===== CACHE EXPENSIVE PREDICTIONS =====
        self.cached_predictions.valid = false;
        self.cache_predictions(&context);

        // ===== AI DECISION 1: What multiplier to use? =====
        let ai_multiplier = self.ai_select_multiplier(&context, dd);
        self.multiplier = ai_multiplier.max(1.5);
        self.chance = ((100.0 - self.house_percent) / self.multiplier).clamp(0.5, 49.5);

        // ===== AI DECISION 2: High or Low? =====
        self.high = self.ai_decide_high_low(&context);

        // ===== AI DECISION 3: Check recovery mode =====
        let (in_recovery, recovery_aggression) = self.ai_recovery_mode(&context, initial_bank_dd);

        // ===== AI DECISION 4: Bet size =====
        let bet = if in_recovery {
            let base_bet = self.initial_bank * recovery_aggression;
            base_bet.min(self.bank).max(self.min_bet)
        } else {
            self.ai_decide_bet_size(&context, self.multiplier, dd)
        };

        self.current_bet = bet.max(self.min_bet);

        // ===== EARLY GAME PROTECTION =====
        if PROTECTIONS_ENABLED && self.total_bets <= 30 {
            let early_max_pct = if self.total_bets <= 5 {
                0.05
            } else if self.total_bets <= 10 {
                0.08
            } else if self.total_bets <= 20 {
                0.12
            } else {
                0.18
            };
            let early_max = self.bank * early_max_pct;
            if self.current_bet > early_max {
                self.current_bet = early_max.max(self.min_bet);
            }
        }

        // Update selected arm for tracking
        let arm_idx = self
            .arms
            .iter()
            .enumerate()
            .min_by(|(_, a), (_, b)| {
                let diff_a = (a.multiplier - self.multiplier).abs();
                let diff_b = (b.multiplier - self.multiplier).abs();
                diff_a
                    .partial_cmp(&diff_b)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .map(|(i, _)| i)
            .unwrap_or(0);

        self.arms[arm_idx].pull_count += 1;

        // Store state for training after result
        self.last_arm_idx = arm_idx;
        self.last_context = context.clone();
        self.last_multiplier_action = arm_idx; // Use arm index as action

        (self.current_bet, self.multiplier, self.chance, self.high)
    }

    fn on_win(&mut self, res: &BetResult) {
        let win = res.win_amount;
        let profit = win - self.current_bet;
        let roll = res.number;

        self.bank += win;
        self.profit += win;
        self.session_profit += profit;
        self.win_streak += 1;
        self.loss_streak = 0;
        self.last_win = true;
        self.total_wins += 1;

        // Update session high/low
        if self.bank > self.session_high {
            self.session_high = self.bank;
        }
        if self.bank > self.peak_bank {
            self.peak_bank = self.bank;
        }
        if self.debt > 0.0 && profit > 0.0 {
            self.debt = (self.debt - profit).max(0.0);
        }

        // Track high/low betting success
        if self.high {
            self.high_bets += 1;
            self.high_wins += 1;
            self.high_win_streak += 1;
            self.low_win_streak = 0;
        } else {
            self.low_bets += 1;
            self.low_wins += 1;
            self.low_win_streak += 1;
            self.high_win_streak = 0;
        }

        let high_was_correct = self.high;
        self.voting_tracker.update_after_result(high_was_correct);

        // Update various tracking systems
        self.recent_returns
            .push_back(profit / self.current_bet.max(1e-8));
        if self.recent_returns.len() > 100 {
            self.recent_returns.pop_front();
        }

        self.recent_seq.push_back(true);
        if self.recent_seq.len() > 50 {
            self.recent_seq.pop_front();
        }

        // Update max streaks
        if self.win_streak > self.max_consecutive_wins {
            self.max_consecutive_wins = self.win_streak;
        }

        // Update smart features
        self.edge_detector.record_outcome(true);
        self.confidence_calibrator
            .record_prediction(self.last_confidence, true);
        self.performance_momentum
            .record_profit(profit / self.initial_bank.max(1e-8));
        self.bankroll_manager.update(self.bank, self.initial_bank);
        self.session_state.update(
            self.total_bets,
            self.bank,
            self.initial_bank,
            self.win_streak,
            self.loss_streak,
            self.total_wins,
            self.total_losses,
        );

        // Train AI models from this result
        let profit = win - self.current_bet;
        self.train_models_after_result(true, profit);

        // Update absurd features
        self.schrodinger_cat.observe(true);
        self.dunning_kruger
            .record_outcome(self.last_confidence, true);
        self.chaos_dragon.update(self.total_bets, false);
        self.conspiracy_detector
            .update(self.loss_streak, roll, self.high);
        self.martingale_urge.update(0, self.current_bet, 0.0);
        if self.divine_intervention.blessing_active {
            self.divine_intervention.record_miracle();
        }
    }

    fn on_lose(&mut self, res: &BetResult) {
        let loss = res.win_amount;
        let roll = res.number;

        self.bank -= loss;
        self.profit -= loss;
        self.session_profit -= loss;
        self.debt += loss;
        self.loss_streak += 1;
        self.win_streak = 0;
        self.last_win = false;
        self.total_losses += 1;

        // Update session low
        if self.bank < self.session_low {
            self.session_low = self.bank;
        }

        // Track high/low betting
        if self.high {
            self.high_bets += 1;
            self.high_win_streak = 0;
        } else {
            self.low_bets += 1;
            self.low_win_streak = 0;
        }

        let high_was_correct = self.high;
        self.voting_tracker.update_after_result(high_was_correct);

        // Update tracking
        self.recent_returns
            .push_back(-loss / self.current_bet.max(1e-8));
        if self.recent_returns.len() > 100 {
            self.recent_returns.pop_front();
        }

        self.recent_seq.push_back(false);
        if self.recent_seq.len() > 50 {
            self.recent_seq.pop_front();
        }

        // Update max loss streak
        if self.loss_streak > self.max_consecutive_losses {
            self.max_consecutive_losses = self.loss_streak;
        }

        // Update smart features
        self.edge_detector.record_outcome(false);
        self.confidence_calibrator
            .record_prediction(self.last_confidence, false);
        self.performance_momentum
            .record_profit(-loss / self.initial_bank.max(1e-8));
        self.bankroll_manager.update(self.bank, self.initial_bank);
        self.session_state.update(
            self.total_bets,
            self.bank,
            self.initial_bank,
            self.win_streak,
            self.loss_streak,
            self.total_wins,
            self.total_losses,
        );

        // Train AI models from this result
        self.train_models_after_result(false, -loss);

        // Update absurd features
        self.schrodinger_cat.observe(false);
        self.dunning_kruger
            .record_outcome(self.last_confidence, false);
        self.chaos_dragon.update(self.total_bets, true);
        self.conspiracy_detector
            .update(self.loss_streak, roll, self.high);
        self.martingale_urge
            .update(self.loss_streak, self.current_bet, self.current_bet);
        self.karma_calculator
            .record_bet(self.last_confidence < 0.7, false, self.last_confidence);
        self.quantum_entanglement.observe_outcome(false);
        self.philosophical_uncertainty.contemplate(
            self.loss_streak,
            self.win_streak,
            self.total_bets,
        );
        self.win_predictor.predict_session_win(
            self.bank / self.initial_bank.max(1e-8),
            self.total_wins as f32 / (self.total_wins + self.total_losses).max(1) as f32,
            self.win_streak,
            self.loss_streak,
            self.total_bets,
        );

        // Safety reset if bank too low
        if self.bank < self.min_bet * 2.0 {
            self.bank = self.initial_bank;
            self.peak_bank = self.initial_bank;
            self.debt = 0.0;
        }
    }

    fn get_balance(&self) -> f32 {
        self.bank
    }

    fn get_profit(&self) -> f32 {
        self.profit
    }

    fn reset(&mut self) {
        self.bank = self.initial_bank;
        self.profit = 0.0;
        self.session_profit = 0.0;
        self.debt = 0.0;
        self.session_high = self.initial_bank;
        self.session_low = self.initial_bank;
        self.loss_streak = 0;
        self.win_streak = 0;
        self.cons_wins = 0;
        self.cons_losses = 0;
        self.high_wins = 0;
        self.low_wins = 0;
        self.high_bets = 0;
        self.low_bets = 0;
        self.high_win_streak = 0;
        self.low_win_streak = 0;
    }
}
