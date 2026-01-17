from __future__ import annotations
"""
Target-Aware Dynamic Dice Strategy

A state-machine-based strategy optimized to reach user-defined targets while
enforcing minimum bet and minimum profit constraints under 1% house edge.

States:
- SAFE: Capital preservation (balance < 60% of target)
- BUILD: Controlled growth (60% ≤ balance < 85% of target)
- STRIKE: Risk injection (85% ≤ balance < 97% of target)
- FINISH: Target calculation zone (within striking distance)

Features:
- Multi-currency interactive startup
- Automatic balance detection
- Dynamic drawdown protection
- Minimum profit enforcement
- Target-aware bet sizing
"""
from typing import Any, Dict, Optional
from decimal import Decimal, getcontext
from enum import Enum

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata

getcontext().prec = 28

# Hard constants
HOUSE_EDGE = Decimal("0.01")  # 1% house edge
MIN_CHANCE = Decimal("0.01")  # 0.01%
MAX_CHANCE = Decimal("98")     # 98%


class BettingState(Enum):
    """State machine states for target-aware betting."""
    SAFE = "SAFE"       # < 60% of target
    BUILD = "BUILD"     # 60-85% of target
    STRIKE = "STRIKE"   # 85-97% of target
    FINISH = "FINISH"   # Within striking distance


@register("target-aware")
class TargetAwareStrategy:
    """
    Dynamic, target-aware dice betting strategy with state machine.
    
    Enforces:
    - balance ≥ minBet to place bet
    - profit ≥ minBet for any bet
    - Stops when balance ≥ target OR balance < minBet
    """

    @classmethod
    def name(cls) -> str:
        return "target-aware"

    @classmethod
    def describe(cls) -> str:
        return (
            "State-machine strategy optimized to reach user-defined targets "
            "with drawdown protection and minimum profit enforcement"
        )



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Low",
            bankroll_required="Small",
            volatility="Low",
            time_to_profit="Moderate",
            recommended_for="Intermediate",
            pros=[
                "Goal-oriented betting approach",
                "Adjusts bets based on target proximity",
                "Good psychological framework",
                "Helps with discipline and exit planning",
                "Reduces overplay after targets hit"
            ],
            cons=[
                "Target-awareness doesn't change odds",
                "Can be overly conservative near target",
                "Psychological tool more than mathematical",
                "Complexity without proven edge"
            ],
            best_use_case="For disciplined players who benefit from goal-setting. Good session management.",
            tips=[
                "Set realistic profit targets (10-20%)",
                "Actually stop when target hit (discipline!)",
                "Use as session management tool",
                "Combine with other strategies",
                "Good for preventing overplay",
                "Focus on consistency over big wins"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "target": {
                "type": "str",
                "default": "0",
                "desc": "Target balance to reach (in currency units)",
            },
            "min_bet": {
                "type": "str",
                "default": "0.00000001",
                "desc": "Minimum bet amount for this currency",
            },
            # State configuration: SAFE
            "safe_chance_min": {
                "type": "str",
                "default": "95",
                "desc": "Min win chance in SAFE state",
            },
            "safe_chance_max": {
                "type": "str",
                "default": "98",
                "desc": "Max win chance in SAFE state",
            },
            "safe_bet_pct_min": {
                "type": "float",
                "default": 0.001,
                "desc": "Min bet % of balance in SAFE (0.1%)",
            },
            "safe_bet_pct_max": {
                "type": "float",
                "default": 0.002,
                "desc": "Max bet % of balance in SAFE (0.2%)",
            },
            # State configuration: BUILD
            "build_chance_min": {
                "type": "str",
                "default": "70",
                "desc": "Min win chance in BUILD state",
            },
            "build_chance_max": {
                "type": "str",
                "default": "85",
                "desc": "Max win chance in BUILD state",
            },
            "build_bet_pct_min": {
                "type": "float",
                "default": 0.003,
                "desc": "Min bet % of balance in BUILD (0.3%)",
            },
            "build_bet_pct_max": {
                "type": "float",
                "default": 0.006,
                "desc": "Max bet % of balance in BUILD (0.6%)",
            },
            # State configuration: STRIKE
            "strike_chance_min": {
                "type": "str",
                "default": "15",
                "desc": "Min win chance in STRIKE state",
            },
            "strike_chance_max": {
                "type": "str",
                "default": "35",
                "desc": "Max win chance in STRIKE state",
            },
            "strike_bet_pct_min": {
                "type": "float",
                "default": 0.008,
                "desc": "Min bet % of balance in STRIKE (0.8%)",
            },
            "strike_bet_pct_max": {
                "type": "float",
                "default": 0.02,
                "desc": "Max bet % of balance in STRIKE (2%)",
            },
            # Drawdown protection thresholds
            "drawdown_downgrade": {
                "type": "float",
                "default": 0.03,
                "desc": "Drawdown % to downgrade state (3%)",
            },
            "drawdown_force_safe": {
                "type": "float",
                "default": 0.06,
                "desc": "Drawdown % to force SAFE (6%)",
            },
            "drawdown_stop": {
                "type": "float",
                "default": 0.10,
                "desc": "Drawdown % to stop betting (10%)",
            },
            # Other settings
            "is_high": {
                "type": "bool",
                "default": True,
                "desc": "Bet High if True else Low",
            },
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        
        # Parse core parameters
        self.target = Decimal(str(params.get("target", "0")))
        self.min_bet = Decimal(str(params.get("min_bet", "0.00000001")))
        self.is_high = bool(params.get("is_high", True))
        
        # SAFE state parameters
        self.safe_chance_min = Decimal(str(params.get("safe_chance_min", "95")))
        self.safe_chance_max = Decimal(str(params.get("safe_chance_max", "98")))
        self.safe_bet_pct_min = float(params.get("safe_bet_pct_min", 0.001))
        self.safe_bet_pct_max = float(params.get("safe_bet_pct_max", 0.002))
        
        # BUILD state parameters
        self.build_chance_min = Decimal(str(params.get("build_chance_min", "70")))
        self.build_chance_max = Decimal(str(params.get("build_chance_max", "85")))
        self.build_bet_pct_min = float(params.get("build_bet_pct_min", 0.003))
        self.build_bet_pct_max = float(params.get("build_bet_pct_max", 0.006))
        
        # STRIKE state parameters
        self.strike_chance_min = Decimal(str(params.get("strike_chance_min", "15")))
        self.strike_chance_max = Decimal(str(params.get("strike_chance_max", "35")))
        self.strike_bet_pct_min = float(params.get("strike_bet_pct_min", 0.008))
        self.strike_bet_pct_max = float(params.get("strike_bet_pct_max", 0.02))
        
        # Drawdown protection
        self.drawdown_downgrade = float(params.get("drawdown_downgrade", 0.03))
        self.drawdown_force_safe = float(params.get("drawdown_force_safe", 0.06))
        self.drawdown_stop = float(params.get("drawdown_stop", 0.10))
        
        # Session tracking
        self.starting_balance = Decimal("0")
        self.peak_balance = Decimal("0")
        self.current_state = BettingState.SAFE
        self.stop_requested = False
        self.bet_count = 0

    def on_session_start(self) -> None:
        """Initialize session state."""
        try:
            self.starting_balance = Decimal(str(self.ctx.starting_balance))
        except Exception:
            self.starting_balance = Decimal("0")
        
        self.peak_balance = self.starting_balance
        self.current_state = BettingState.SAFE
        self.stop_requested = False
        self.bet_count = 0
        
        print(f"\n{'='*60}")
        print(f"TARGET-AWARE STRATEGY INITIALIZED")
        print(f"{'='*60}")
        print(f"Currency: {self.ctx.symbol}")
        print(f"Starting Balance: {self.starting_balance}")
        print(f"Target Balance: {self.target}")
        print(f"Minimum Bet: {self.min_bet}")
        print(f"Required Gain: {self.target - self.starting_balance}")
        print(f"{'='*60}\n")

    def _get_current_balance(self) -> Decimal:
        """Get current balance from most recent result or starting balance."""
        if self.ctx.recent_results:
            try:
                return Decimal(str(self.ctx.recent_results[-1].get("balance", "0")))
            except Exception:
                pass
        return self.starting_balance

    def _compute_payout_multiplier(self, chance: Decimal) -> Decimal:
        """
        Compute payout multiplier using mandatory formula:
        payoutMultiplier = (100 - houseEdge) / winChance
        """
        if chance <= 0:
            return Decimal("0")
        return (Decimal("100") - HOUSE_EDGE) / chance

    def _compute_profit(self, bet: Decimal, chance: Decimal) -> Decimal:
        """
        Compute net profit for a winning bet:
        profit = bet × (payoutMultiplier - 1)
        """
        multiplier = self._compute_payout_multiplier(chance)
        return bet * (multiplier - Decimal("1"))

    def _find_valid_chance(
        self, 
        min_chance: Decimal, 
        max_chance: Decimal, 
        bet: Decimal
    ) -> Optional[Decimal]:
        """
        Find a valid win chance within range that satisfies min-profit constraint.
        Returns highest chance that ensures profit ≥ minBet.
        """
        # Start from max chance and work down to find valid chance
        chance = max_chance
        
        while chance >= min_chance:
            profit = self._compute_profit(bet, chance)
            if profit >= self.min_bet:
                return chance
            
            # Reduce chance by 1% increments
            chance -= Decimal("1")
        
        return None

    def _compute_bet_size(
        self,
        balance: Decimal,
        pct_min: float,
        pct_max: float,
        chance: Decimal,
    ) -> Optional[Decimal]:
        """
        Compute bet size ensuring all constraints:
        1. bet ≥ minBet
        2. profit ≥ minBet
        3. bet within percentage range of balance
        4. bet ≤ balance
        
        Returns None if constraints cannot be satisfied.
        """
        # Start with percentage-based bet
        pct = self.ctx.rng.uniform(pct_min, pct_max)
        bet = balance * Decimal(str(pct))
        
        # Ensure minimum bet
        bet = max(bet, self.min_bet)
        
        # Ensure minimum profit constraint
        multiplier = self._compute_payout_multiplier(chance)
        if multiplier > Decimal("1"):
            min_bet_for_profit = self.min_bet / (multiplier - Decimal("1"))
            bet = max(bet, min_bet_for_profit)
        
        # CRITICAL: Check if required bet exceeds balance
        if bet > balance:
            # Cannot place a bet that meets minimum profit with current balance
            return None
        
        return bet

    def _compute_drawdown(self, balance: Decimal) -> float:
        """Compute current drawdown as percentage of peak."""
        if self.peak_balance <= 0:
            return 0.0
        dd = (self.peak_balance - balance) / self.peak_balance
        return float(dd)

    def _determine_state(self, balance: Decimal, drawdown: float) -> BettingState:
        """
        Determine current betting state based on target progress and drawdown.
        
        Drawdown protection:
        - > 10%: stop entirely
        - > 6%: force SAFE
        - > 3%: downgrade one state
        """
        if drawdown >= self.drawdown_stop:
            self.stop_requested = True
            return BettingState.SAFE
        
        if drawdown >= self.drawdown_force_safe:
            return BettingState.SAFE
        
        # Calculate progress to target
        progress = float(balance / self.target) if self.target > 0 else 0.0
        
        # Check if we can finish in one bet (FINISH state)
        # This requires calculating max potential profit
        max_profit_bet = balance  # Max we could bet
        max_profit_chance = self.strike_chance_max  # Use aggressive chance
        max_profit = self._compute_profit(max_profit_bet, max_profit_chance)
        
        if balance + max_profit >= self.target:
            state = BettingState.FINISH
        elif progress >= 0.85:
            state = BettingState.STRIKE
        elif progress >= 0.60:
            state = BettingState.BUILD
        else:
            state = BettingState.SAFE
        
        # Apply drawdown downgrade
        if drawdown >= self.drawdown_downgrade:
            if state == BettingState.STRIKE:
                state = BettingState.BUILD
            elif state == BettingState.BUILD:
                state = BettingState.SAFE
        
        return state

    def _create_safe_bet(self, balance: Decimal) -> Optional[BetSpec]:
        """Create bet in SAFE state (capital preservation)."""
        # Choose chance within safe range
        chance = self.ctx.rng.uniform(
            float(self.safe_chance_min),
            float(self.safe_chance_max)
        )
        chance = Decimal(str(chance))
        
        # Compute bet size
        bet = self._compute_bet_size(
            balance,
            self.safe_bet_pct_min,
            self.safe_bet_pct_max,
            chance,
        )
        
        # Check if bet size could be computed
        if bet is None:
            return None
        
        # Validate profit constraint
        if self._compute_profit(bet, chance) < self.min_bet:
            # Find valid chance
            valid_chance = self._find_valid_chance(
                self.safe_chance_min,
                self.safe_chance_max,
                bet,
            )
            if valid_chance is None:
                return None
            chance = valid_chance
        
        return {
            "game": "dice",
            "amount": format(bet, 'f'),
            "chance": format(chance, 'f'),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _create_build_bet(self, balance: Decimal) -> Optional[BetSpec]:
        """Create bet in BUILD state (controlled growth)."""
        chance = self.ctx.rng.uniform(
            float(self.build_chance_min),
            float(self.build_chance_max)
        )
        chance = Decimal(str(chance))
        
        bet = self._compute_bet_size(
            balance,
            self.build_bet_pct_min,
            self.build_bet_pct_max,
            chance,
        )
        
        # Check if bet size could be computed
        if bet is None:
            return None
        
        if self._compute_profit(bet, chance) < self.min_bet:
            valid_chance = self._find_valid_chance(
                self.build_chance_min,
                self.build_chance_max,
                bet,
            )
            if valid_chance is None:
                return None
            chance = valid_chance
        
        return {
            "game": "dice",
            "amount": format(bet, 'f'),
            "chance": format(chance, 'f'),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _create_strike_bet(self, balance: Decimal) -> Optional[BetSpec]:
        """Create bet in STRIKE state (risk injection)."""
        chance = self.ctx.rng.uniform(
            float(self.strike_chance_min),
            float(self.strike_chance_max)
        )
        chance = Decimal(str(chance))
        
        bet = self._compute_bet_size(
            balance,
            self.strike_bet_pct_min,
            self.strike_bet_pct_max,
            chance,
        )
        
        # Check if bet size could be computed
        if bet is None:
            return None
        
        if self._compute_profit(bet, chance) < self.min_bet:
            valid_chance = self._find_valid_chance(
                self.strike_chance_min,
                self.strike_chance_max,
                bet,
            )
            if valid_chance is None:
                return None
            chance = valid_chance
        
        return {
            "game": "dice",
            "amount": format(bet, 'f'),
            "chance": format(chance, 'f'),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def _create_finish_bet(self, balance: Decimal) -> Optional[BetSpec]:
        """
        Create bet in FINISH state (target calculation zone).
        
        Find highest win chance such that profit reaches target.
        """
        required_profit = self.target - balance
        required_profit = max(required_profit, self.min_bet)
        
        # Search for optimal chance from high to low
        best_chance = None
        for chance_pct in range(98, 0, -1):
            chance = Decimal(str(chance_pct))
            multiplier = self._compute_payout_multiplier(chance)
            
            if multiplier <= Decimal("1"):
                continue
            
            # Calculate required bet
            required_bet = required_profit / (multiplier - Decimal("1"))
            required_bet = max(required_bet, self.min_bet)
            
            # Check if we can afford it
            if required_bet <= balance:
                # Verify profit constraint
                actual_profit = self._compute_profit(required_bet, chance)
                if actual_profit >= required_profit and actual_profit >= self.min_bet:
                    best_chance = chance
                    break
        
        if best_chance is None:
            # Fallback to STRIKE behavior
            return self._create_strike_bet(balance)
        
        # Calculate final bet
        multiplier = self._compute_payout_multiplier(best_chance)
        bet = required_profit / (multiplier - Decimal("1"))
        bet = max(bet, self.min_bet)
        bet = min(bet, balance)
        
        return {
            "game": "dice",
            "amount": format(bet, 'f'),
            "chance": format(best_chance, 'f'),
            "is_high": self.is_high,
            "faucet": self.ctx.faucet,
        }

    def next_bet(self) -> Optional[BetSpec]:
        """
        Generate next bet using state machine logic.
        
        Enforces:
        - balance ≥ minBet (hard invariant)
        - balance < target (stop condition)
        - profit ≥ minBet (for any bet)
        """
        balance = self._get_current_balance()
        
        # Hard invariant: balance must be >= minBet
        if balance < self.min_bet:
            self.stop_requested = True
            print(f"\n⛔ STOP: Balance ({balance}) < minBet ({self.min_bet})")
            return None
        
        # Stop condition: target reached
        if balance >= self.target:
            self.stop_requested = True
            print(f"\n🎯 TARGET REACHED! Balance: {balance} ≥ Target: {self.target}")
            return None
        
        # Stop if requested by drawdown
        if self.stop_requested:
            print(f"\n⛔ STOP: Drawdown protection triggered")
            return None
        
        # Update peak
        if balance > self.peak_balance:
            self.peak_balance = balance
        
        # Compute drawdown
        drawdown = self._compute_drawdown(balance)
        
        # Determine state
        old_state = self.current_state
        self.current_state = self._determine_state(balance, drawdown)
        
        # Log state transitions
        if old_state != self.current_state or self.bet_count % 10 == 0:
            progress = float(balance / self.target * 100) if self.target > 0 else 0
            print(f"\n[Bet #{self.bet_count + 1}] State: {self.current_state.value}")
            print(f"  Balance: {balance} | Target: {self.target} | Progress: {progress:.1f}%")
            print(f"  Peak: {self.peak_balance} | Drawdown: {drawdown * 100:.2f}%")
        
        # Create bet based on state
        if self.current_state == BettingState.FINISH:
            bet_spec = self._create_finish_bet(balance)
        elif self.current_state == BettingState.STRIKE:
            bet_spec = self._create_strike_bet(balance)
        elif self.current_state == BettingState.BUILD:
            bet_spec = self._create_build_bet(balance)
        else:  # SAFE
            bet_spec = self._create_safe_bet(balance)
        
        if bet_spec:
            self.bet_count += 1
        
        return bet_spec

    def on_bet_result(self, result: BetResult) -> None:
        """Process bet result and update tracking."""
        self.ctx.recent_results.append(result)
        
        win = result.get("win", False)
        profit_str = result.get("profit", "0")
        balance_str = result.get("balance", "0")
        
        try:
            profit = Decimal(str(profit_str))
            balance = Decimal(str(balance_str))
            
            # Update peak
            if balance > self.peak_balance:
                self.peak_balance = balance
            
            # Log result
            symbol = "✅" if win else "❌"
            print(f"  {symbol} Profit: {profit:+.8f} | New Balance: {balance:.8f}")
            
        except Exception as e:
            print(f"  ⚠️ Error processing result: {e}")

    def on_session_end(self, reason: str) -> None:
        """Report final session statistics."""
        final_balance = self._get_current_balance()
        total_profit = final_balance - self.starting_balance
        
        print(f"\n{'='*60}")
        print(f"SESSION ENDED: {reason}")
        print(f"{'='*60}")
        print(f"Currency: {self.ctx.symbol}")
        print(f"Starting Balance: {self.starting_balance}")
        print(f"Final Balance: {final_balance}")
        print(f"Target Balance: {self.target}")
        print(f"Peak Balance: {self.peak_balance}")
        print(f"Total Profit: {total_profit:+.8f}")
        print(f"Total Bets: {self.bet_count}")
        
        if final_balance >= self.target:
            shortfall = final_balance - self.target
            print(f"\n🎉 SUCCESS! Target reached with surplus: {shortfall:+.8f}")
        else:
            shortfall = self.target - final_balance
            progress = float(final_balance / self.target * 100) if self.target > 0 else 0
            print(f"\n❌ Target not reached. Short by: {shortfall:.8f} ({100 - progress:.1f}% remaining)")
        
        print(f"{'='*60}\n")
