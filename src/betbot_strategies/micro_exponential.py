"""
MICRO BALANCE EXPONENTIAL GROWTH ENGINE

Purpose: Turn dust into 100x+ via asymmetric volatility exploitation
Strategy: Adaptive multi-mode system with volatility learning

WARNING: This is an extremely aggressive high-risk strategy designed for
         micro balances. Accepts deep drawdowns (45%) in pursuit of 300x gains.
         NOT suitable for significant balances or conservative bankroll management.

Modes:
- PROBE: Low-risk data collection (60% chance)
- PRESSURE: Loss clustering exploitation (18% chance with martingale)
- HUNT: Asymmetric long-shot engine (0.08-0.20% chance)
- CHAOS: Entropy forcing with random parameters
- KILL: Micro-optimized explosion mode (0.08-0.25% chance, 65% of balance)
"""

import random
from decimal import Decimal
from typing import Dict, Any

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("micro-exponential")
class MicroExponentialStrategy:
    """Micro balance exponential growth (300x target, EXTREME risk)"""
    
    MODE_PROBE = "PROBE"
    MODE_PRESSURE = "PRESSURE"
    MODE_HUNT = "HUNT"
    MODE_CHAOS = "CHAOS"
    MODE_KILL = "KILL"
    
    @classmethod
    def name(cls) -> str:
        return "micro-exponential"
    
    @classmethod
    def describe(cls) -> str:
        return "Micro balance exponential growth (300x target, EXTREME risk, adaptive modes)"
    
    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="EXTREME",
            bankroll_required="Micro (<$1)",
            volatility="Extreme",
            time_to_profit="Variable (high variance)",
            recommended_for="Experimental / Dust Recovery",
            pros=[
                "Targets 300x gains from micro balances",
                "Adaptive strategy switching",
                "Volatility learning system",
                "Multiple betting modes"
            ],
            cons=[
                "EXTREME risk - 45% drawdown tolerance",
                "Kill mode bets 65% of balance",
                "Not suitable for significant balances",
                "High variance"
            ],
            notes=[
                "Designed for micro balances only (<$1)",
                "Uses 5 different betting modes"
            ]
        )
    
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext):
        self.ctx = ctx
        
        # Adjust base bet percent based on balance size
        # For balances under $1, use more aggressive sizing
        starting_balance = Decimal(str(ctx.starting_balance))
        if starting_balance < Decimal('1.0'):
            # For micro balances, use 1% instead of 0.2%
            default_base_percent = '0.01'
        else:
            default_base_percent = '0.002'
        
        self.base_bet_percent = Decimal(str(params.get('base_bet_percent', default_base_percent)))
        
        # Set reasonable minimum bet based on currency
        # USDT/BTC/ETH typically have ~0.001 minimums
        # Altcoins often have higher minimums
        self.min_bet = Decimal(str(params.get('min_bet', '0.001')))
        
        self.max_bet_percent = Decimal(str(params.get('max_bet_percent', '0.90')))
        self.profit_target_x = Decimal(str(params.get('profit_target_x', '300')))
        self.max_drawdown_percent = Decimal(str(params.get('max_drawdown_percent', '45')))
        self.switch_cooldown_bets = int(params.get('switch_cooldown_bets', 10))
        self.kill_chance_min = Decimal(str(params.get('kill_chance_min', '0.08')))
        self.kill_chance_max = Decimal(str(params.get('kill_chance_max', '0.25')))
        self.kill_bet_percent = Decimal(str(params.get('kill_bet_percent', '0.65')))
        self.kill_cooldown = int(params.get('kill_cooldown', 120))
        
        self.initial_balance = starting_balance
        self.peak_balance = self.initial_balance
        self.current_balance = self.initial_balance
        self.current_strategy = self.MODE_PROBE
        self.last_switch_bet = 0
        self.last_kill_bet = -self.kill_cooldown
        self.loss_streak = 0
        self.win_streak = 0
        self.total_bets = 0
        self.vol_window = int(params.get('vol_window', 40))
        self.history = []
        
    def on_session_start(self) -> None:
        pass
        
    def update_volatility(self, win: bool) -> None:
        self.history.append(1 if win else 0)
        if len(self.history) > self.vol_window:
            self.history.pop(0)
    
    def volatility_score(self) -> float:
        if len(self.history) < self.vol_window:
            return 0.0
        switches = sum(1 for i in range(1, len(self.history)) if self.history[i] != self.history[i-1])
        return 1.0 - (switches / (len(self.history) - 1))
    
    def clamp(self, value: Decimal, min_val: Decimal, max_val: Decimal) -> Decimal:
        return max(min_val, min(value, max_val))
    
    def get_base_bet(self) -> Decimal:
        bet = self.current_balance * self.base_bet_percent
        return max(bet, self.min_bet)
    
    def can_switch_strategy(self) -> bool:
        return self.total_bets - self.last_switch_bet >= self.switch_cooldown_bets
    
    def strat_probe(self) -> tuple:
        chance = Decimal('60.0')
        betsize = self.get_base_bet() * Decimal('0.5')
        return chance, betsize
    
    def strat_pressure(self) -> tuple:
        chance = Decimal('18.0')
        multiplier = Decimal('1.3') ** self.loss_streak
        betsize = self.get_base_bet() * multiplier
        betsize = self.clamp(betsize, self.min_bet, self.current_balance * Decimal('0.25'))
        return chance, betsize
    
    def strat_hunt(self) -> tuple:
        chance = Decimal(str(random.uniform(0.08, 0.20)))
        betsize = self.get_base_bet()
        return chance, betsize
    
    def strat_chaos(self) -> tuple:
        chance = Decimal(str(random.uniform(5.0, 70.0)))
        multiplier = Decimal(str(random.uniform(0.3, 2.5)))
        betsize = self.get_base_bet() * multiplier
        betsize = self.clamp(betsize, self.min_bet, self.current_balance * Decimal('0.3'))
        return chance, betsize
    
    def strat_kill(self) -> tuple:
        chance = Decimal(str(round(random.uniform(float(self.kill_chance_min), float(self.kill_chance_max)), 3)))
        betsize = self.current_balance * self.kill_bet_percent
        return chance, betsize
    
    def weighted_pick(self, weights: Dict[str, int]) -> str:
        total = sum(weights.values())
        r = random.random() * total
        acc = 0
        for strategy, weight in weights.items():
            acc += weight
            if r <= acc:
                return strategy
        return self.MODE_PROBE
    
    def evaluate_and_switch(self) -> None:
        if not self.can_switch_strategy():
            return
        
        vol = self.volatility_score()
        profit_x = self.current_balance / self.initial_balance if self.initial_balance > 0 else Decimal('1')
        drawdown = ((self.peak_balance - self.current_balance) / self.peak_balance * 100) if self.peak_balance > 0 else Decimal('0')
        
        if profit_x >= self.profit_target_x:
            self.current_strategy = self.MODE_PROBE
            return
        
        if profit_x >= 20:
            self.base_bet_percent = Decimal('0.001')
        if profit_x >= 50:
            self.base_bet_percent = Decimal('0.0005')
        
        if (vol > 0.72 and drawdown < 20 and 
            self.total_bets - self.last_kill_bet >= self.kill_cooldown and
            random.random() < 0.12):
            self.current_strategy = self.MODE_KILL
            self.last_kill_bet = self.total_bets
            self.last_switch_bet = self.total_bets
            return
        
        weights = {
            self.MODE_PROBE: 30,
            self.MODE_PRESSURE: 25,
            self.MODE_HUNT: 25,
            self.MODE_CHAOS: 20
        }
        
        if self.loss_streak >= 6:
            weights[self.MODE_PRESSURE] += 40
        if self.win_streak >= 3:
            weights[self.MODE_HUNT] += 30
        if vol > 0.6:
            weights[self.MODE_CHAOS] += 40
        if drawdown > 25:
            weights[self.MODE_PROBE] += 60
        
        self.current_strategy = self.weighted_pick(weights)
        self.last_switch_bet = self.total_bets
    
    def next_bet(self) -> BetSpec:
        self.current_balance = Decimal(str(self.ctx.current_balance_str()))
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        self.evaluate_and_switch()
        
        if self.current_strategy == self.MODE_PROBE:
            chance, betsize = self.strat_probe()
        elif self.current_strategy == self.MODE_PRESSURE:
            chance, betsize = self.strat_pressure()
        elif self.current_strategy == self.MODE_HUNT:
            chance, betsize = self.strat_hunt()
        elif self.current_strategy == self.MODE_CHAOS:
            chance, betsize = self.strat_chaos()
        elif self.current_strategy == self.MODE_KILL:
            chance, betsize = self.strat_kill()
        else:
            chance, betsize = self.strat_probe()
        
        betsize = self.clamp(betsize, self.min_bet, self.current_balance * self.max_bet_percent)
        
        # Format chance to 2 decimal places for API compatibility
        chance_formatted = f"{float(chance):.2f}"
        
        return {
            'game': 'dice',
            'amount': str(betsize),
            'chance': chance_formatted,
            'is_high': random.random() > 0.5  # Random over/under
        }
    
    def on_bet_result(self, result: BetResult) -> None:
        win = result.get('win', False)
        balance = Decimal(str(result.get('balance', '0')))
        
        self.current_balance = balance
        self.total_bets += 1
        
        if win:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        self.update_volatility(win)
    
    def on_session_end(self, reason: str) -> None:
        pass
