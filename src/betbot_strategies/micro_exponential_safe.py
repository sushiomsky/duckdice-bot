"""
MICRO BALANCE EXPONENTIAL GROWTH ENGINE - SAFE VARIANT

A more conservative version of the micro-exponential strategy with:
- Reduced CHAOS bet sizing (max 10% vs 30%)
- Emergency drawdown protection (auto-PROBE at 50% drawdown)
- Faster mode switching during loss streaks
- Lower KILL mode aggression (50% vs 65%)
- Tighter loss streak limits

Still aggressive, but with safety rails to prevent instant busts.
"""

import random
from decimal import Decimal
from typing import Dict, Any

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("micro-exponential-safe")
class MicroExponentialSafeStrategy:
    """Micro exponential growth with safety limits (100x target, HIGH risk)"""
    
    MODE_PROBE = "PROBE"
    MODE_PRESSURE = "PRESSURE"
    MODE_HUNT = "HUNT"
    MODE_CHAOS = "CHAOS"
    MODE_KILL = "KILL"
    
    @classmethod
    def name(cls) -> str:
        return "micro-exponential-safe"
    
    @classmethod
    def describe(cls) -> str:
        return "Micro exponential with safety limits (100x target, HIGH risk, reduced chaos)"
    
    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="HIGH",
            bankroll_required="Micro (<$1)",
            volatility="High",
            time_to_profit="Variable",
            recommended_for="Intermediate / Dust Recovery",
            pros=[
                "Targets 100x gains (more realistic than 300x)",
                "Emergency drawdown protection",
                "Reduced CHAOS aggression",
                "Faster mode switching in losses",
                "Still adaptive and volatile"
            ],
            cons=[
                "Still HIGH risk (can lose everything)",
                "Less explosive than original",
                "Requires favorable patterns",
                "Not suitable for large balances"
            ],
            notes=[
                "Safer variant of micro-exponential",
                "CHAOS limited to 10% vs 30%",
                "KILL mode 50% vs 65%",
                "Emergency brake at 50% drawdown"
            ]
        )
    
    def __init__(self, params: Dict[str, Any], ctx: StrategyContext):
        self.ctx = ctx
        
        # Adjust base bet percent based on balance size
        starting_balance = Decimal(str(ctx.starting_balance))
        if starting_balance < Decimal('1.0'):
            default_base_percent = '0.01'
        else:
            default_base_percent = '0.002'
        
        self.base_bet_percent = Decimal(str(params.get('base_bet_percent', default_base_percent)))
        self.min_bet = Decimal(str(params.get('min_bet', '0.001')))
        self.max_bet_percent = Decimal(str(params.get('max_bet_percent', '0.90')))
        
        # SAFER: Lower target (100x vs 300x)
        self.profit_target_x = Decimal(str(params.get('profit_target_x', '100')))
        
        # SAFER: Lower max drawdown (35% vs 45%)
        self.max_drawdown_percent = Decimal(str(params.get('max_drawdown_percent', '35')))
        
        self.switch_cooldown_bets = int(params.get('switch_cooldown_bets', 10))
        
        # SAFER: KILL mode less aggressive (50% vs 65%)
        self.kill_chance_min = Decimal(str(params.get('kill_chance_min', '0.08')))
        self.kill_chance_max = Decimal(str(params.get('kill_chance_max', '0.25')))
        self.kill_bet_percent = Decimal(str(params.get('kill_bet_percent', '0.50')))  # 50% vs 65%
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
        self.emergency_mode = False  # NEW: Emergency brake flag
        
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
        # SAFER: Faster switching during loss streaks
        if self.loss_streak >= 5:
            return self.total_bets - self.last_switch_bet >= 3
        return self.total_bets - self.last_switch_bet >= self.switch_cooldown_bets
    
    def strat_probe(self) -> tuple:
        chance = Decimal('60.0')
        betsize = self.get_base_bet() * Decimal('0.5')
        return chance, betsize
    
    def strat_pressure(self) -> tuple:
        chance = Decimal('18.0')
        
        # SAFER: Cap loss streak multiplier at 8 (was unlimited)
        capped_streak = min(self.loss_streak, 8)
        multiplier = Decimal('1.3') ** capped_streak
        
        betsize = self.get_base_bet() * multiplier
        betsize = self.clamp(betsize, self.min_bet, self.current_balance * Decimal('0.20'))  # 20% vs 25%
        return chance, betsize
    
    def strat_hunt(self) -> tuple:
        chance = Decimal(str(random.uniform(0.08, 0.20)))
        betsize = self.get_base_bet()
        return chance, betsize
    
    def strat_chaos(self) -> tuple:
        chance = Decimal(str(random.uniform(5.0, 70.0)))
        
        # SAFER: Reduced multiplier range (0.5-1.5x vs 0.3-2.5x)
        multiplier = Decimal(str(random.uniform(0.5, 1.5)))
        
        betsize = self.get_base_bet() * multiplier
        
        # SAFER: Max 10% of balance (was 30%)
        betsize = self.clamp(betsize, self.min_bet, self.current_balance * Decimal('0.10'))
        return chance, betsize
    
    def strat_kill(self) -> tuple:
        chance = Decimal(str(round(random.uniform(float(self.kill_chance_min), float(self.kill_chance_max)), 3)))
        
        # SAFER: 50% of balance (was 65%)
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
        
        # Check profit target
        if profit_x >= self.profit_target_x:
            self.current_strategy = self.MODE_PROBE
            return
        
        # NEW: EMERGENCY BRAKE - Force conservative mode at 50% drawdown
        if drawdown >= 50:
            if not self.emergency_mode:
                self.emergency_mode = True
            self.current_strategy = self.MODE_PROBE
            self.last_switch_bet = self.total_bets
            return
        else:
            self.emergency_mode = False
        
        # Adapt base bet after big wins
        if profit_x >= 20:
            self.base_bet_percent = Decimal('0.001')
        if profit_x >= 50:
            self.base_bet_percent = Decimal('0.0005')
        
        # KILL MODE (stricter conditions)
        if (vol > 0.75 and  # Higher threshold (0.75 vs 0.72)
            drawdown < 15 and  # Stricter (15% vs 20%)
            self.total_bets - self.last_kill_bet >= self.kill_cooldown and
            random.random() < 0.08):  # Lower chance (8% vs 12%)
            
            self.current_strategy = self.MODE_KILL
            self.last_kill_bet = self.total_bets
            self.last_switch_bet = self.total_bets
            return
        
        # Weighted strategy selection
        weights = {
            self.MODE_PROBE: 40,     # More conservative (40 vs 30)
            self.MODE_PRESSURE: 25,
            self.MODE_HUNT: 25,
            self.MODE_CHAOS: 10      # Less chaos (10 vs 20)
        }
        
        # Adjust weights based on conditions
        if self.loss_streak >= 6:
            weights[self.MODE_PRESSURE] += 30  # Less aggressive (30 vs 40)
        
        if self.win_streak >= 3:
            weights[self.MODE_HUNT] += 30
        
        if vol > 0.6:
            weights[self.MODE_CHAOS] += 20  # Less chaos boost (20 vs 40)
        
        if drawdown > 25:
            weights[self.MODE_PROBE] += 80  # More safety (80 vs 60)
        
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
        
        chance_formatted = f"{float(chance):.2f}"
        
        return {
            'game': 'dice',
            'amount': str(betsize),
            'chance': chance_formatted,
            'is_high': random.random() > 0.5
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
