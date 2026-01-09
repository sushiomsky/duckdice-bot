"""
Utility modules for the DuckDice Bot application.

This package provides reusable utilities for error handling, retrying,
caching, and logging throughout the application.
"""

from app.utils.errors import (
    BotError,
    APIError,
    ConnectionError as BotConnectionError,
    AuthenticationError,
    RateLimitError,
    ConfigError,
    StrategyError,
    ValidationError,
    BettingError,
    InsufficientBalanceError,
    ErrorHandler,
    validate_bet_params
)

from app.utils.retry import (
    RetryConfig,
    retry_sync,
    retry_async,
    RetryContext,
    retry_operation
)

from app.utils.cache import (
    TTLCache,
    cached,
    CachedAPIClient,
    get_cached,
    set_cached,
    clear_cache
)

__all__ = [
    # Error handling
    'BotError',
    'APIError',
    'BotConnectionError',
    'AuthenticationError',
    'RateLimitError',
    'ConfigError',
    'StrategyError',
    'ValidationError',
    'BettingError',
    'InsufficientBalanceError',
    'ErrorHandler',
    'validate_bet_params',
    
    # Retry utilities
    'RetryConfig',
    'retry_sync',
    'retry_async',
    'RetryContext',
    'retry_operation',
    
    # Caching
    'TTLCache',
    'cached',
    'CachedAPIClient',
    'get_cached',
    'set_cached',
    'clear_cache',
]
