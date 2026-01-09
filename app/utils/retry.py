"""
Retry utilities for handling transient failures.

Provides decorators and utilities for retrying failed operations
with exponential backoff and configurable retry strategies.
"""

from functools import wraps
from typing import Callable, TypeVar, Optional, Tuple, Type
import asyncio
import time
from app.utils.logger import log_warning, log_info

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay between retries (seconds)
            backoff_factor: Multiplier for delay on each retry
            max_delay: Maximum delay between retries (seconds)
            exceptions: Tuple of exceptions to retry on
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.exceptions = exceptions
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


def retry_sync(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for retrying synchronous functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to retry on
    
    Returns:
        Decorated function with retry logic
    
    Example:
        >>> @retry_sync(max_attempts=3, delay=1.0)
        ... def fetch_data():
        ...     return api.get_data()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            current_delay = delay
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        log_warning(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    log_info(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for retrying async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to retry on
    
    Returns:
        Decorated async function with retry logic
    
    Example:
        >>> @retry_async(max_attempts=3, delay=0.5)
        ... async def fetch_data():
        ...     return await api.get_data_async()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            attempt = 0
            current_delay = delay
            last_exception = None
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        log_warning(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    log_info(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {current_delay}s: {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic.
    
    Allows more fine-grained control over retry behavior
    with access to attempt number and elapsed time.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.attempt = 0
        self.start_time = 0.0
        self.last_exception: Optional[Exception] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True
        
        if not isinstance(exc_val, self.config.exceptions):
            return False
        
        self.attempt += 1
        self.last_exception = exc_val
        
        if self.attempt >= self.config.max_attempts:
            log_warning(f"Max retry attempts ({self.config.max_attempts}) reached")
            return False
        
        delay = self.config.get_delay(self.attempt)
        elapsed = time.time() - self.start_time
        
        log_info(
            f"Retry attempt {self.attempt}/{self.config.max_attempts} "
            f"after {elapsed:.1f}s, waiting {delay:.1f}s: {exc_val}"
        )
        
        time.sleep(delay)
        return True  # Suppress exception and retry
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since first attempt"""
        return time.time() - self.start_time


async def retry_operation(
    operation: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    Retry an async operation with exponential backoff.
    
    Args:
        operation: Async function to retry
        *args: Positional arguments for operation
        config: Retry configuration
        **kwargs: Keyword arguments for operation
    
    Returns:
        Result from successful operation
    
    Raises:
        Exception from last failed attempt
    
    Example:
        >>> result = await retry_operation(
        ...     api.get_balance,
        ...     config=RetryConfig(max_attempts=5, initial_delay=0.5)
        ... )
    """
    cfg = config or RetryConfig()
    attempt = 0
    last_exception = None
    
    while attempt < cfg.max_attempts:
        try:
            return await operation(*args, **kwargs)
        except cfg.exceptions as e:
            attempt += 1
            last_exception = e
            
            if attempt >= cfg.max_attempts:
                log_warning(
                    f"Operation failed after {cfg.max_attempts} attempts: {e}"
                )
                raise
            
            delay = cfg.get_delay(attempt)
            log_info(
                f"Operation failed (attempt {attempt}/{cfg.max_attempts}), "
                f"retrying in {delay}s: {e}"
            )
            await asyncio.sleep(delay)
    
    raise last_exception
