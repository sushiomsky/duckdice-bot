from __future__ import annotations
"""
Faucet Grind Strategy - Automated faucet claiming and optimal betting

This strategy automates the process of:
1. Claiming faucet rewards
2. Making optimal all-in bets to reach $20 cashout threshold
3. Auto-recovering from losses by claiming next faucet
4. Cashing out to main balance when $20 is reached

Perfect for grinding free faucet balance to real withdrawable funds.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("faucet-grind")
class FaucetGrind:
    """Automated faucet claiming with optimal all-in betting to $20 target"""

    @classmethod
    def name(cls) -> str:
        return "faucet-grind"

    @classmethod
    def describe(cls) -> str:
        return "Auto-claim faucet → Calculate optimal chance → All-in bet → Repeat until $20 → Cashout"

    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Very Low",
            bankroll_required="None (Free Faucet)",
            volatility="High (All-in bets)",
            time_to_profit="Medium (depends on luck)",
            recommended_for="Patient grinders",
            pros=[
                "100% free - uses faucet balance only",
                "Automated claim → bet cycle",
                "Optimal chance calculation for maximum profit",
                "Auto-cashout at $20 threshold",
                "No risk to main balance",
                "Can run 24/7 with claims limit"
            ],
            cons=[
                "High variance (all-in bets)",
                "Limited by 35-60 claims per 24h",
                "Requires time and patience",
                "Small claim amounts ($0.01-$0.46)",
                "3% house edge on faucet bets",
                "May take days/weeks to reach $20"
            ],
            best_use_case="Grind free faucet balance to $20 cashout. Perfect for users who want to build bankroll from nothing.",
            tips=[
                "Be patient - this is a slow grind",
                "Let it run automatically",
                "Don't expect quick results",
                "Strategy works best over many claims",
                "Variance means streaks of wins/losses",
                "Cashout happens automatically at $20"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "target_usd": {
                "type": "float",
                "default": 20.0,
                "desc": "Target cashout amount in USD"
            },
            "min_chance": {
                "type": "float",
                "default": 1.1,
                "desc": "Minimum bet chance (safety limit)"
            },
            "max_chance": {
                "type": "float",
                "default": 95.0,
                "desc": "Maximum bet chance (safety limit)"
            },
            "house_edge": {
                "type": "float",
                "default": 0.03,
                "desc": "House edge for faucet bets (3%)"
            },
            "cooldown_after_loss": {
                "type": "int",
                "default": 60,
                "desc": "Seconds to wait after loss before next claim"
            },
            "auto_cashout": {
                "type": "bool",
                "default": True,
                "desc": "Automatically cashout when target reached"
            },
            "max_consecutive_losses": {
                "type": "int",
                "default": 100,
                "desc": "Stop after this many consecutive losses (safety)"
            }
        }

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """Initialize strategy with parameters"""
        params = params or {}
        
        self.target_usd = float(params.get("target_usd", 20.0))
        self.min_chance = float(params.get("min_chance", 1.1))
        self.max_chance = float(params.get("max_chance", 95.0))
        self.house_edge = float(params.get("house_edge", 0.03))
        self.cooldown_after_loss = int(params.get("cooldown_after_loss", 60))
        self.auto_cashout = bool(params.get("auto_cashout", True))
        self.max_consecutive_losses = int(params.get("max_consecutive_losses", 100))
        
        # State
        self.consecutive_losses = 0
        self.total_claims = 0
        self.total_bets = 0
        self.target_reached = False
        self.last_claim_time = 0.0
        self.waiting_for_claim = False

    def calculate_optimal_chance(
        self,
        balance_usd: float,
        target_usd: float,
        house_edge: float
    ) -> float:
        """
        Calculate optimal chance to reach target with all-in bet.
        
        Formula:
        payout = balance * (100 / chance) * (1 - house_edge)
        
        We want: payout >= target
        So: balance * (100 / chance) * (1 - house_edge) >= target
        
        Solving for chance:
        chance = (balance * 100 * (1 - house_edge)) / target
        
        Args:
            balance_usd: Current balance in USD
            target_usd: Target payout in USD
            house_edge: House edge (0.03 for faucet)
            
        Returns:
            Optimal chance percentage
        """
        if target_usd <= 0:
            return self.max_chance
        
        # Calculate raw chance
        chance = (balance_usd * 100 * (1 - house_edge)) / target_usd
        
        # Clamp to valid range
        chance = max(self.min_chance, min(self.max_chance, chance))
        
        return chance

    def next_bet(self, ctx: StrategyContext) -> Optional[BetSpec]:
        """
        Determine next bet in faucet grind cycle.
        
        Cycle:
        1. Check if can claim faucet
        2. If yes: claim, wait cooldown
        3. Calculate optimal chance for $20 payout
        4. Place all-in bet
        5. If win: check cashout
        6. If loss: wait 60s, goto 1
        """
        # Safety check: max consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return None  # Stop strategy
        
        # Check if target reached
        balance_usd = ctx.get_faucet_balance_usd()
        if balance_usd >= self.target_usd:
            self.target_reached = True
            if self.auto_cashout:
                # Trigger cashout (handled externally)
                return None
            else:
                # Continue grinding
                pass
        
        # Check if we need to wait for claim
        current_time = time.time()
        if self.waiting_for_claim:
            if current_time - self.last_claim_time < self.cooldown_after_loss:
                # Still waiting
                return None
            else:
                # Cooldown expired, try to claim
                self.waiting_for_claim = False
        
        # Check if we have balance to bet
        if balance_usd <= 0:
            # Need to claim faucet
            # This would be handled by faucet manager
            # For now, mark as waiting
            self.waiting_for_claim = True
            self.last_claim_time = current_time
            return None
        
        # Calculate optimal chance
        chance = self.calculate_optimal_chance(
            balance_usd,
            self.target_usd,
            self.house_edge
        )
        
        # All-in bet (use entire faucet balance)
        amount = ctx.get_faucet_balance()  # In crypto, not USD
        
        # Create bet spec
        bet = BetSpec(
            amount=amount,
            chance=chance,
            is_high=True  # Always bet high
        )
        
        self.total_bets += 1
        
        return bet

    def on_result(self, ctx: StrategyContext, result: BetResult) -> None:
        """Handle bet result"""
        if result.is_win:
            # Reset loss counter on win
            self.consecutive_losses = 0
        else:
            # Increment loss counter
            self.consecutive_losses += 1
            
            # Mark as waiting for next claim
            self.waiting_for_claim = True
            self.last_claim_time = time.time()

    def should_stop(self, ctx: StrategyContext) -> bool:
        """Check if strategy should stop"""
        # Stop if target reached and auto-cashout enabled
        if self.target_reached and self.auto_cashout:
            return True
        
        # Stop if too many consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            return True
        
        return False

    def get_progress_info(self, ctx: StrategyContext) -> Dict[str, Any]:
        """Get strategy progress information"""
        balance_usd = ctx.get_faucet_balance_usd()
        progress_pct = (balance_usd / self.target_usd) * 100 if self.target_usd > 0 else 0
        
        return {
            'current_balance_usd': balance_usd,
            'target_usd': self.target_usd,
            'progress_percent': min(100, progress_pct),
            'total_claims': self.total_claims,
            'total_bets': self.total_bets,
            'consecutive_losses': self.consecutive_losses,
            'target_reached': self.target_reached,
            'waiting_for_claim': self.waiting_for_claim,
            'time_until_can_claim': max(0, self.cooldown_after_loss - (time.time() - self.last_claim_time))
        }
