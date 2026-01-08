"""
Cookie Manager for Faucet Claims

Handles storage and retrieval of browser cookies needed for faucet claiming.
"""

import json
from pathlib import Path
from typing import Optional


class CookieManager:
    """Manages browser cookies for faucet claiming."""
    
    def __init__(self, config_file: str = "faucet_cookies.json"):
        """
        Initialize cookie manager.
        
        Args:
            config_file: Path to cookie storage file
        """
        self.config_file = Path.home() / ".duckdice" / config_file
        self.config_file.parent.mkdir(exist_ok=True)
        self.cookies = self.load()
    
    def load(self) -> dict:
        """Load cookies from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load cookies: {e}")
        return {}
    
    def save(self):
        """Save cookies to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.cookies, f, indent=2)
        except Exception as e:
            print(f"Failed to save cookies: {e}")
    
    def get_cookie(self) -> Optional[str]:
        """Get stored cookie string."""
        return self.cookies.get('cookie_string')
    
    def set_cookie(self, cookie_string: str):
        """
        Store cookie string.
        
        Args:
            cookie_string: Full cookie header string from browser
        """
        self.cookies['cookie_string'] = cookie_string
        self.save()
    
    def clear(self):
        """Clear all stored cookies."""
        self.cookies = {}
        self.save()
    
    def has_cookie(self) -> bool:
        """Check if cookie is configured."""
        cookie = self.get_cookie()
        return cookie is not None and len(cookie) > 0
