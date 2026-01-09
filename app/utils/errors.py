"""
Centralized error handling and custom exceptions.

This module provides a unified approach to error handling across the application,
with custom exception types and standardized error processing.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import traceback


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BotError(Exception):
    """
    Base exception for all bot-specific errors.
    
    Attributes:
        message: Human-readable error message
        details: Additional context about the error
        timestamp: When the error occurred
        severity: Error severity level
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.severity = severity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value
        }


class APIError(BotError):
    """API-related errors (connection, timeout, invalid response)"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details['status_code'] = status_code


class ConnectionError(APIError):
    """Failed to connect to API"""
    pass


class AuthenticationError(APIError):
    """Invalid API key or authentication failure"""
    pass


class RateLimitError(APIError):
    """API rate limit exceeded"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details['retry_after'] = retry_after


class ConfigError(BotError):
    """Configuration-related errors"""
    pass


class StrategyError(BotError):
    """Strategy execution errors"""
    
    def __init__(self, message: str, strategy_name: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details['strategy'] = strategy_name


class ValidationError(BotError):
    """Input validation errors"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.details['field'] = field


class BettingError(BotError):
    """Bet placement or execution errors"""
    pass


class InsufficientBalanceError(BettingError):
    """Not enough balance for operation"""
    
    def __init__(self, message: str, required: float, available: float, **kwargs):
        super().__init__(message, **kwargs)
        self.details['required'] = required
        self.details['available'] = available


class ErrorHandler:
    """
    Centralized error handling utilities.
    
    Provides consistent error handling, logging, and user-friendly
    error messages across the application.
    """
    
    @staticmethod
    def handle(
        error: Exception,
        context: str = "",
        log_func: Optional[callable] = None
    ) -> Tuple[bool, str]:
        """
        Handle an error and return standardized response.
        
        Args:
            error: The exception to handle
            context: Context where error occurred (e.g., "place_bet")
            log_func: Optional logging function (default: print to stderr)
        
        Returns:
            Tuple of (success: False, error_message: str)
        
        Example:
            >>> try:
            ...     api.get_balance()
            ... except Exception as e:
            ...     success, message = ErrorHandler.handle(e, "get_balance")
            ...     return success, message
        """
        if log_func is None:
            from app.utils.logger import log_error
            log_func = log_error
        
        # Handle custom bot errors
        if isinstance(error, BotError):
            log_func(f"{context}: {error.message}", error.details)
            return False, error.message
        
        # Handle network errors
        elif isinstance(error, (ConnectionRefusedError, TimeoutError)):
            message = f"Network error: Unable to connect to server"
            log_func(f"{context}: {message}", {'error': str(error)})
            return False, message
        
        # Handle import errors
        elif hasattr(error, '__module__') and 'requests' in error.__module__:
            message = f"API request failed: {str(error)}"
            log_func(f"{context}: {message}")
            return False, message
        
        # Handle unexpected errors
        else:
            message = f"An unexpected error occurred: {str(error)}"
            log_func(
                f"{context}: Unexpected error",
                {
                    'error_type': type(error).__name__,
                    'error': str(error),
                    'traceback': traceback.format_exc()
                }
            )
            return False, "An unexpected error occurred. Please try again."
    
    @staticmethod
    def format_error_message(error: Exception) -> str:
        """
        Format error for user display.
        
        Args:
            error: Exception to format
        
        Returns:
            User-friendly error message
        """
        if isinstance(error, BotError):
            return error.message
        elif isinstance(error, ValueError):
            return f"Invalid input: {str(error)}"
        elif isinstance(error, KeyError):
            return f"Missing required data: {str(error)}"
        else:
            return "An error occurred. Please check your input and try again."
    
    @staticmethod
    def create_error_details(
        error: Exception,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create detailed error information for logging.
        
        Args:
            error: The exception
            context: Additional context information
        
        Returns:
            Dictionary with error details
        """
        details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        
        if isinstance(error, BotError):
            details.update(error.to_dict())
        
        if context:
            details['context'] = context
        
        return details


def validate_bet_params(
    amount: float,
    chance: float,
    balance: float,
    min_bet: float = 0.00000001,
    max_chance: float = 98.0,
    min_chance: float = 0.01
) -> None:
    """
    Validate betting parameters.
    
    Args:
        amount: Bet amount
        chance: Win chance percentage
        balance: Available balance
        min_bet: Minimum bet amount
        max_chance: Maximum win chance
        min_chance: Minimum win chance
    
    Raises:
        ValidationError: If parameters are invalid
        InsufficientBalanceError: If balance too low
    """
    if amount < min_bet:
        raise ValidationError(
            f"Bet amount must be at least {min_bet}",
            field="amount"
        )
    
    if amount > balance:
        raise InsufficientBalanceError(
            "Insufficient balance for this bet",
            required=amount,
            available=balance
        )
    
    if not (min_chance <= chance <= max_chance):
        raise ValidationError(
            f"Win chance must be between {min_chance}% and {max_chance}%",
            field="chance"
        )
