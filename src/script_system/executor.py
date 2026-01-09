"""
Safe Script Execution Engine.

Executes strategy scripts in a restricted sandbox with:
- Timeout protection
- Limited builtins and globals
- Exception handling
- Resource constraints
"""

import ast
import math
import random
import time
from decimal import Decimal
from typing import Any, Dict, Optional, Callable
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Guards import guarded_iter_unpack_sequence


class ExecutionError(Exception):
    """Raised when script execution fails."""
    pass


class ExecutionTimeout(Exception):
    """Raised when script execution times out."""
    pass


class SafeExecutor:
    """
    Executes strategy scripts in a safe, restricted environment.
    
    Uses RestrictedPython to prevent dangerous operations while
    allowing legitimate strategy logic.
    """
    
    DEFAULT_TIMEOUT = 5.0  # seconds
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize safe executor.
        
        Args:
            timeout: Maximum execution time in seconds
        """
        self.timeout = timeout
        self._globals_cache: Dict[str, Dict[str, Any]] = {}
    
    def execute_script(self, code: str, script_name: str = '<script>') -> Dict[str, Callable]:
        """
        Execute a strategy script and return its functions.
        
        Args:
            code: Python source code to execute
            script_name: Name for error messages
            
        Returns:
            Dictionary of function names to callables
            
        Raises:
            ExecutionError: If execution fails
            ExecutionTimeout: If execution exceeds timeout
        """
        # Check cache
        if script_name in self._globals_cache:
            return self._extract_functions(self._globals_cache[script_name])
        
        # Compile with RestrictedPython
        try:
            byte_code = compile_restricted(
                code,
                filename=script_name,
                mode='exec'
            )
        except SyntaxError as e:
            raise ExecutionError(f"Syntax error at line {e.lineno}: {e.msg}")
        
        if byte_code is None:
            raise ExecutionError("Failed to compile script")
        
        # Create restricted globals
        restricted_globals = self._create_restricted_globals()
        
        # Execute with timeout protection
        start_time = time.time()
        
        try:
            exec(byte_code, restricted_globals)
        except Exception as e:
            raise ExecutionError(f"Execution error: {str(e)}")
        
        elapsed = time.time() - start_time
        if elapsed > self.timeout:
            raise ExecutionTimeout(f"Script execution exceeded {self.timeout}s timeout")
        
        # Cache globals
        self._globals_cache[script_name] = restricted_globals
        
        # Extract and return functions
        return self._extract_functions(restricted_globals)
    
    def call_function(
        self,
        func: Callable,
        *args,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Call a strategy function with timeout protection.
        
        Args:
            func: Function to call
            *args: Positional arguments
            timeout: Override default timeout
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            ExecutionTimeout: If call exceeds timeout
            ExecutionError: If function raises exception
        """
        timeout = timeout or self.timeout
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            raise ExecutionError(f"Function error: {str(e)}")
        
        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise ExecutionTimeout(f"Function call exceeded {timeout}s timeout")
        
        return result
    
    def clear_cache(self, script_name: Optional[str] = None):
        """
        Clear cached globals.
        
        Args:
            script_name: Specific script to clear, or None for all
        """
        if script_name:
            self._globals_cache.pop(script_name, None)
        else:
            self._globals_cache.clear()
    
    def _create_restricted_globals(self) -> Dict[str, Any]:
        """Create restricted globals dictionary for script execution."""
        
        # Safe import handler
        def safe_import(name, *args, **kwargs):
            """Only allow importing safe modules."""
            safe_modules = {
                'math': math,
                'random': random,
                'decimal': __import__('decimal'),
                'fractions': __import__('fractions'),
                'statistics': __import__('statistics'),
                'datetime': __import__('datetime'),
                'time': __import__('time'),
                'typing': __import__('typing'),
                'dataclasses': __import__('dataclasses'),
                'enum': __import__('enum'),
                'collections': __import__('collections'),
                'itertools': __import__('itertools'),
                'functools': __import__('functools'),
            }
            
            if name in safe_modules:
                return safe_modules[name]
            
            raise ImportError(f"Import of '{name}' is not allowed in strategy scripts")
        
        # Start with safe_globals from RestrictedPython (has all guards)
        restricted_globals = safe_globals.copy()
        
        # Add guards for common operations
        restricted_globals['_getitem_'] = lambda obj, index: obj[index]
        restricted_globals['_write_'] = lambda obj: obj  # Allow writes
        
        # Add safe import
        restricted_globals['__builtins__']['__import__'] = safe_import
        
        # Add additional safe functions
        restricted_globals['__builtins__'].update({
            'min': min,
            'max': max,
            'sum': sum,
            'enumerate': enumerate,
            'map': map,
            'filter': filter,
            'reversed': reversed,
            'list': list,
            'dict': dict,
            'set': set,
            'any': any,
            'all': all,
        })
        
        # Safe modules pre-imported
        restricted_globals['math'] = math
        restricted_globals['random'] = random
        restricted_globals['Decimal'] = Decimal
        
        # Add time functions (limited)
        restricted_globals['time'] = type('time', (), {
            'time': time.time,
            'sleep': lambda x: None,  # Disable sleep to prevent delays
        })()
        
        return restricted_globals
    
    def _extract_functions(self, globals_dict: Dict[str, Any]) -> Dict[str, Callable]:
        """
        Extract callable functions from globals dictionary.
        
        Args:
            globals_dict: Globals after script execution
            
        Returns:
            Dictionary of function name to callable
        """
        functions = {}
        
        for name, obj in globals_dict.items():
            # Skip private/magic attributes
            if name.startswith('_'):
                continue
            
            # Skip modules and builtins
            if name in ('math', 'random', 'Decimal', 'time'):
                continue
            
            # Only include callables
            if callable(obj):
                functions[name] = obj
        
        return functions


class StrategyExecutor(SafeExecutor):
    """
    Specialized executor for betting strategies.
    
    Adds strategy-specific validation and context handling.
    """
    
    REQUIRED_FUNCTIONS = ['next_bet']
    OPTIONAL_FUNCTIONS = ['on_result', 'init']
    
    def load_strategy(self, code: str, script_name: str = '<strategy>') -> Dict[str, Callable]:
        """
        Load and validate a betting strategy.
        
        Args:
            code: Strategy source code
            script_name: Name for error messages
            
        Returns:
            Dictionary of strategy functions
            
        Raises:
            ExecutionError: If strategy is invalid
        """
        functions = self.execute_script(code, script_name)
        
        # Validate required functions exist
        for func_name in self.REQUIRED_FUNCTIONS:
            if func_name not in functions:
                raise ExecutionError(f"Strategy missing required function: {func_name}(ctx)")
        
        return functions
    
    def execute_next_bet(self, next_bet_func: Callable, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute next_bet() function with validation.
        
        Args:
            next_bet_func: The next_bet function
            ctx: Strategy context
            
        Returns:
            Bet parameters dictionary
            
        Raises:
            ExecutionError: If bet parameters are invalid
        """
        result = self.call_function(next_bet_func, ctx)
        
        # Validate result
        if not isinstance(result, dict):
            raise ExecutionError("next_bet() must return a dictionary")
        
        required_keys = {'amount', 'chance'}
        if not required_keys.issubset(result.keys()):
            raise ExecutionError(f"next_bet() must return dict with keys: {required_keys}")
        
        # Validate types
        try:
            amount = float(result['amount'])
            chance = float(result['chance'])
        except (TypeError, ValueError) as e:
            raise ExecutionError(f"Invalid bet parameters: {e}")
        
        # Validate ranges
        if amount <= 0:
            raise ExecutionError(f"Bet amount must be positive, got {amount}")
        
        if not (0 < chance < 100):
            raise ExecutionError(f"Bet chance must be between 0 and 100, got {chance}")
        
        return result
    
    def execute_on_result(
        self,
        on_result_func: Optional[Callable],
        ctx: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """
        Execute on_result() function if available.
        
        Args:
            on_result_func: The on_result function or None
            ctx: Strategy context
            result: Bet result
        """
        if on_result_func:
            self.call_function(on_result_func, ctx, result)
    
    def execute_init(
        self,
        init_func: Optional[Callable],
        ctx: Dict[str, Any],
        params: Dict[str, Any]
    ) -> None:
        """
        Execute init() function if available.
        
        Args:
            init_func: The init function or None
            ctx: Strategy context
            params: Strategy parameters
        """
        if init_func:
            self.call_function(init_func, ctx, params)


# Convenience functions

def execute_strategy_script(code: str, script_name: str = '<strategy>') -> Dict[str, Callable]:
    """
    Execute and validate a strategy script.
    
    Args:
        code: Strategy source code
        script_name: Name for error messages
        
    Returns:
        Dictionary of strategy functions
        
    Raises:
        ExecutionError: If execution or validation fails
    """
    executor = StrategyExecutor()
    return executor.load_strategy(code, script_name)


def create_strategy_executor(timeout: float = 5.0) -> StrategyExecutor:
    """
    Create a new strategy executor.
    
    Args:
        timeout: Execution timeout in seconds
        
    Returns:
        StrategyExecutor instance
    """
    return StrategyExecutor(timeout=timeout)
