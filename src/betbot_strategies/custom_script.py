from __future__ import annotations
"""
Script-Based Strategy Engine
Allows users to define custom strategies using Python scripts.

The script must define:
- init(params, context) -> None: Initialize strategy
- next_bet() -> dict: Return next bet specification
- on_result(result) -> None: Handle bet result

Example script:
    base = 0.000001
    current = base
    
    def init(params, context):
        global base, current
        base = float(params.get('base_amount', 0.000001))
        current = base
    
    def next_bet():
        return {
            'game': 'dice',
            'amount': str(current),
            'chance': '49.5',
            'is_high': True
        }
    
    def on_result(result):
        global current, base
        if result['win']:
            current = base
        else:
            current *= 2
"""
from decimal import Decimal
from typing import Any, Dict, Optional
import os
import sys

from . import register
from .base import StrategyContext, BetSpec, BetResult, StrategyMetadata


@register("custom-script")
class CustomScript:
    """Execute custom Python betting strategy from script file."""

    @classmethod
    def name(cls) -> str:
        return "custom-script"

    @classmethod
    def describe(cls) -> str:
        return "Load and execute custom Python strategy from script file."



    @classmethod
    def metadata(cls) -> StrategyMetadata:
        return StrategyMetadata(
            risk_level="Variable",
            bankroll_required="Variable",
            volatility="Variable",
            time_to_profit="Variable",
            recommended_for="Experts",
            pros=[
                "Complete customization freedom",
                "Implement any strategy logic",
                "Great for research and testing",
                "Learn Python while betting",
                "Share strategies with community"
            ],
            cons=[
                "Requires programming knowledge",
                "Bugs can cause losses",
                "No safety guarantees",
                "Debugging can be frustrating",
                "Easy to make mistakes"
            ],
            best_use_case="For developers creating custom strategies. Test thoroughly in simulation!",
            tips=[
                "ALWAYS test in simulation mode first",
                "Add extensive error handling",
                "Log everything for debugging",
                "Start with simple logic, add complexity slowly",
                "Review code multiple times before live use",
                "Consider open-sourcing successful strategies"
            ]
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return {
            "script_path": {"type": "str", "required": True, "desc": "Path to Python script file"},
            "faucet": {"type": "bool", "default": False, "desc": "Use faucet balance"},
        }

    def __init__(self, params: Dict[str, Any], ctx: StrategyContext) -> None:
        self.ctx = ctx
        self.params = params
        
        script_path = params.get("script_path", "")
        if not script_path:
            raise ValueError("script_path is required for custom-script strategy")
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")
        
        # Load and execute script
        self._script_globals: Dict[str, Any] = {
            '__builtins__': __builtins__,
            'Decimal': Decimal,
            'ctx': ctx,
            'params': params,
        }
        
        with open(script_path, 'r') as f:
            script_code = f.read()
        
        try:
            exec(script_code, self._script_globals)
        except Exception as e:
            raise RuntimeError(f"Failed to load script {script_path}: {e}")
        
        # Verify required functions
        if 'next_bet' not in self._script_globals:
            raise ValueError("Script must define next_bet() function")
        
        if 'on_result' not in self._script_globals:
            raise ValueError("Script must define on_result(result) function")
        
        # Optional init function
        if 'init' in self._script_globals:
            init_func = self._script_globals['init']
            try:
                init_func(params, ctx)
            except Exception as e:
                raise RuntimeError(f"Script init() failed: {e}")

    def on_session_start(self) -> None:
        # Call optional session_start in script
        if 'on_session_start' in self._script_globals:
            try:
                self._script_globals['on_session_start']()
            except Exception as e:
                print(f"Warning: Script on_session_start() failed: {e}")

    def next_bet(self) -> Optional[BetSpec]:
        try:
            bet = self._script_globals['next_bet']()
            if bet is None:
                return None
            
            # Ensure required fields
            if 'game' not in bet:
                bet['game'] = 'dice'
            if 'faucet' not in bet:
                bet['faucet'] = self.ctx.faucet
            
            return bet  # type: ignore
        except Exception as e:
            print(f"Error in script next_bet(): {e}")
            return None

    def on_bet_result(self, result: BetResult) -> None:
        try:
            self._script_globals['on_result'](result)
        except Exception as e:
            print(f"Error in script on_result(): {e}")
        
        self.ctx.recent_results.append(result)

    def on_session_end(self, reason: str) -> None:
        # Call optional session_end in script
        if 'on_session_end' in self._script_globals:
            try:
                self._script_globals['on_session_end'](reason)
            except Exception as e:
                print(f"Warning: Script on_session_end() failed: {e}")
