"""
Faucet Manager

Automatic faucet claiming with cooldown management.
"""

import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from .cookie_manager import CookieManager


@dataclass
class FaucetConfig:
    """Configuration for faucet auto-claiming."""
    enabled: bool = False
    interval: int = 60  # Cooldown in seconds
    currency: str = "DOGE"
    last_claim_time: float = 0.0


class FaucetManager:
    """
    Manages automatic faucet claiming.
    
    Features:
    - Auto-claim with configurable interval
    - Cooldown tracking
    - Cookie management
    - Threaded background claiming
    """
    
    def __init__(self, api_client, config: Optional[FaucetConfig] = None):
        """
        Initialize faucet manager.
        
        Args:
            api_client: DuckDiceAPI instance
            config: Faucet configuration
        """
        self.api = api_client
        self.config = config or FaucetConfig()
        self.cookie_manager = CookieManager()
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Callbacks
        self.on_claim_success: Optional[Callable[[str, float], None]] = None
        self.on_claim_failure: Optional[Callable[[str, str], None]] = None
    
    def can_claim(self) -> bool:
        """Check if faucet can be claimed (cooldown expired)."""
        if not self.config.enabled:
            return False
        
        if not self.cookie_manager.has_cookie():
            return False
        
        elapsed = time.time() - self.config.last_claim_time
        return elapsed >= self.config.interval
    
    def claim_now(self, currency: Optional[str] = None) -> bool:
        """
        Manually claim faucet immediately.
        
        Args:
            currency: Currency to claim (uses config currency if None)
            
        Returns:
            True if claim successful, False otherwise
        """
        symbol = currency or self.config.currency
        cookie = self.cookie_manager.get_cookie()
        
        if not cookie:
            if self.on_claim_failure:
                self.on_claim_failure(symbol, "No cookie configured")
            return False
        
        # Check cooldown
        if not self.can_claim():
            remaining = self.config.interval - (time.time() - self.config.last_claim_time)
            if self.on_claim_failure:
                self.on_claim_failure(symbol, f"Cooldown: {int(remaining)}s remaining")
            return False
        
        # Attempt claim
        success = self.api.claim_faucet(symbol, cookie)
        
        if success:
            self.config.last_claim_time = time.time()
            
            # Get new balance
            balance = self.api.get_faucet_balance(symbol)
            
            if self.on_claim_success:
                self.on_claim_success(symbol, balance)
        else:
            if self.on_claim_failure:
                self.on_claim_failure(symbol, "Claim failed")
        
        return success
    
    def start_auto_claim(self):
        """Start automatic faucet claiming in background thread."""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._auto_claim_loop, daemon=True)
        self._thread.start()
    
    def stop_auto_claim(self):
        """Stop automatic faucet claiming."""
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
    
    def _auto_claim_loop(self):
        """Background loop for automatic claiming."""
        while self._running and not self._stop_event.is_set():
            if self.config.enabled and self.can_claim():
                try:
                    self.claim_now()
                except Exception as e:
                    print(f"Auto-claim error: {e}")
            
            # Check every 5 seconds
            self._stop_event.wait(5.0)
    
    def set_cookie(self, cookie_string: str):
        """Set browser cookie for claiming."""
        self.cookie_manager.set_cookie(cookie_string)
    
    def get_cookie(self) -> Optional[str]:
        """Get current cookie."""
        return self.cookie_manager.get_cookie()
    
    def clear_cookie(self):
        """Clear stored cookie."""
        self.cookie_manager.clear()
    
    def get_next_claim_time(self) -> float:
        """Get seconds until next claim available."""
        if self.config.last_claim_time == 0:
            return 0.0
        
        elapsed = time.time() - self.config.last_claim_time
        remaining = max(0, self.config.interval - elapsed)
        return remaining
    
    def enable(self, enabled: bool = True):
        """Enable or disable auto-claiming."""
        self.config.enabled = enabled
        
        if enabled and not self._running:
            self.start_auto_claim()
        elif not enabled and self._running:
            self.stop_auto_claim()
