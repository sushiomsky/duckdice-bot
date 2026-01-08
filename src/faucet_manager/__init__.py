"""
Faucet Manager Module

Handles automatic faucet claiming for DuckDice.
"""

from .faucet_manager import FaucetManager, FaucetConfig
from .cookie_manager import CookieManager

__all__ = ['FaucetManager', 'FaucetConfig', 'CookieManager']
