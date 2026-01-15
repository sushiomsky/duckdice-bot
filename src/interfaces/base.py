"""
Base interface contract for betting bot interfaces.

All UI implementations (CLI, TUI, GUI, Web) should implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from decimal import Decimal


class BettingInterface(ABC):
    """
    Abstract base class for all betting interface implementations.
    
    This defines the contract that all interfaces must implement to work
    with the betting engine.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the interface.
        
        Called once before the interface is used. Set up display, load config, etc.
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """
        Clean up the interface.
        
        Called when the interface is no longer needed. Close connections, save state, etc.
        """
        pass
    
    @abstractmethod
    def display_session_start(self, strategy: str, config: Dict[str, Any], 
                             starting_balance: Decimal, currency: str) -> None:
        """
        Display session start information.
        
        Args:
            strategy: Name of the strategy being used
            config: Engine configuration
            starting_balance: Initial balance
            currency: Currency symbol
        """
        pass
    
    @abstractmethod
    def display_session_end(self, summary: Dict[str, Any]) -> None:
        """
        Display session summary.
        
        Args:
            summary: Session statistics and results
        """
        pass
    
    @abstractmethod
    def display_bet_placed(self, bet_number: int, amount: Decimal, chance: float) -> None:
        """
        Display information about a placed bet.
        
        Args:
            bet_number: Sequential bet number
            amount: Bet amount
            chance: Win chance percentage
        """
        pass
    
    @abstractmethod
    def display_bet_result(self, bet_number: int, win: bool, profit: Decimal, 
                          balance: Decimal) -> None:
        """
        Display bet result.
        
        Args:
            bet_number: Sequential bet number
            win: Whether the bet won
            profit: Profit/loss from this bet
            balance: Current balance after bet
        """
        pass
    
    @abstractmethod
    def display_stats(self, stats: Dict[str, Any]) -> None:
        """
        Display current session statistics.
        
        Args:
            stats: Dictionary containing total_bets, wins, losses, win_rate, profit, etc.
        """
        pass
    
    @abstractmethod
    def display_warning(self, message: str) -> None:
        """
        Display a warning message.
        
        Args:
            message: Warning message to display
        """
        pass
    
    @abstractmethod
    def display_error(self, message: str) -> None:
        """
        Display an error message.
        
        Args:
            message: Error message to display
        """
        pass
    
    @abstractmethod
    def display_info(self, message: str) -> None:
        """
        Display an informational message.
        
        Args:
            message: Info message to display
        """
        pass
    
    @abstractmethod
    def get_user_input(self, prompt: str, default: Optional[str] = None) -> str:
        """
        Get input from the user.
        
        Args:
            prompt: Prompt to display
            default: Default value if user provides no input
            
        Returns:
            User's input as string
        """
        pass
    
    @abstractmethod
    def get_choice(self, prompt: str, choices: List[str]) -> str:
        """
        Get user choice from a list of options.
        
        Args:
            prompt: Prompt to display
            choices: List of valid choices
            
        Returns:
            Selected choice
        """
        pass
    
    @abstractmethod
    def check_stop_requested(self) -> bool:
        """
        Check if user has requested to stop the session.
        
        Returns:
            True if stop was requested
        """
        pass
    
    @abstractmethod
    def update_progress(self, current: int, total: Optional[int] = None, 
                       message: Optional[str] = None) -> None:
        """
        Update progress indicator.
        
        Args:
            current: Current progress value
            total: Total expected value (None for indeterminate)
            message: Optional progress message
        """
        pass


class HeadlessInterface(BettingInterface):
    """
    Headless interface implementation with no user interaction.
    
    Useful for:
    - Automated/scheduled betting
    - Testing
    - Server deployments
    - Background processes
    """
    
    def __init__(self, log_events: bool = False):
        self.log_events = log_events
        self._stop_requested = False
    
    def initialize(self) -> None:
        """No-op for headless"""
        pass
    
    def shutdown(self) -> None:
        """No-op for headless"""
        pass
    
    def display_session_start(self, strategy: str, config: Dict[str, Any], 
                             starting_balance: Decimal, currency: str) -> None:
        if self.log_events:
            print(f"[SESSION_START] Strategy: {strategy}, Balance: {starting_balance} {currency}")
    
    def display_session_end(self, summary: Dict[str, Any]) -> None:
        if self.log_events:
            print(f"[SESSION_END] {summary}")
    
    def display_bet_placed(self, bet_number: int, amount: Decimal, chance: float) -> None:
        """Silent"""
        pass
    
    def display_bet_result(self, bet_number: int, win: bool, profit: Decimal, 
                          balance: Decimal) -> None:
        """Silent"""
        pass
    
    def display_stats(self, stats: Dict[str, Any]) -> None:
        """Silent"""
        pass
    
    def display_warning(self, message: str) -> None:
        if self.log_events:
            print(f"[WARNING] {message}")
    
    def display_error(self, message: str) -> None:
        if self.log_events:
            print(f"[ERROR] {message}")
    
    def display_info(self, message: str) -> None:
        """Silent"""
        pass
    
    def get_user_input(self, prompt: str, default: Optional[str] = None) -> str:
        """Return default or empty"""
        return default or ""
    
    def get_choice(self, prompt: str, choices: List[str]) -> str:
        """Return first choice"""
        return choices[0] if choices else ""
    
    def check_stop_requested(self) -> bool:
        """Check stop flag"""
        return self._stop_requested
    
    def request_stop(self) -> None:
        """Request stop (for programmatic control)"""
        self._stop_requested = True
    
    def update_progress(self, current: int, total: Optional[int] = None, 
                       message: Optional[str] = None) -> None:
        """Silent"""
        pass
