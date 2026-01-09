"""
Script System Package

Unified system for managing betting strategies as editable Python scripts.
All strategies (built-in and custom) are stored and executed as scripts.
"""

from .strategy_script import StrategyScript
from .script_storage import ScriptStorage
from .script_loader import ScriptLoader
from .validator import ScriptValidator, ValidationResult, ValidationError, validate_script
from .executor import (
    SafeExecutor,
    StrategyExecutor,
    ExecutionError,
    ExecutionTimeout,
    execute_strategy_script,
    create_strategy_executor
)

__all__ = [
    # Core models
    'StrategyScript',
    'ScriptStorage',
    'ScriptLoader',
    
    # Validation
    'ScriptValidator',
    'ValidationResult',
    'ValidationError',
    'validate_script',
    
    # Execution
    'SafeExecutor',
    'StrategyExecutor',
    'ExecutionError',
    'ExecutionTimeout',
    'execute_strategy_script',
    'create_strategy_executor',
]
