"""
Currency Converter - Convert cryptocurrency to USD
Uses CoinGecko API with caching
"""

from typing import Dict, Tuple, Optional
import time
import requests


class CurrencyConverter:
    """Convert crypto amounts to USD using CoinGecko API"""
    
    # Mapping of currency symbols to CoinGecko IDs
    COIN_GECKO_IDS = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'DOGE': 'dogecoin',
        'LTC': 'litecoin',
        'TRX': 'tron',
        'XRP': 'ripple',
        'BCH': 'bitcoin-cash',
        'EOS': 'eos',
        'BNB': 'binancecoin',
        'USDT': 'tether',
        'USDC': 'usd-coin',
    }
    
    def __init__(self, cache_ttl: int = 300):
        """
        Initialize currency converter.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
        """
        self._cache: Dict[str, Tuple[float, float]] = {}  # {currency: (price, timestamp)}
        self._cache_ttl = cache_ttl
        self._api_url = "https://api.coingecko.com/api/v3/simple/price"
    
    def to_usd(self, amount: float, currency: str) -> float:
        """
        Convert cryptocurrency amount to USD.
        
        Args:
            amount: Amount in cryptocurrency
            currency: Currency symbol (e.g., 'DOGE', 'BTC')
            
        Returns:
            USD equivalent value
        """
        price = self.get_price(currency)
        return amount * price
    
    def get_price(self, currency: str) -> float:
        """
        Get current USD price of cryptocurrency.
        
        Args:
            currency: Currency symbol
            
        Returns:
            Price in USD (1 coin = X USD)
        """
        currency = currency.upper()
        
        # Check cache first
        if currency in self._cache:
            price, timestamp = self._cache[currency]
            if time.time() - timestamp < self._cache_ttl:
                return price
        
        # Fetch fresh price
        try:
            price = self._fetch_price(currency)
            self._cache[currency] = (price, time.time())
            return price
        except Exception as e:
            # Return cached value if available, else default to 1.0
            if currency in self._cache:
                return self._cache[currency][0]
            
            print(f"Warning: Could not fetch price for {currency}, using 1.0 USD: {e}")
            return 1.0
    
    def _fetch_price(self, currency: str) -> float:
        """
        Fetch price from CoinGecko API.
        
        Args:
            currency: Currency symbol
            
        Returns:
            Price in USD
            
        Raises:
            Exception if API request fails
        """
        # Special cases for stablecoins
        if currency in ('USDT', 'USDC', 'DAI'):
            return 1.0
        
        # Get CoinGecko ID
        coin_id = self.COIN_GECKO_IDS.get(currency)
        if not coin_id:
            raise ValueError(f"Unknown currency: {currency}")
        
        # Fetch price
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd'
        }
        
        response = requests.get(
            self._api_url,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if coin_id not in data or 'usd' not in data[coin_id]:
            raise ValueError(f"No USD price for {currency}")
        
        return float(data[coin_id]['usd'])
    
    def clear_cache(self):
        """Clear price cache"""
        self._cache.clear()
    
    def update_cache(self, currency: str, price: float):
        """
        Manually update cache with known price.
        
        Args:
            currency: Currency symbol
            price: Price in USD
        """
        self._cache[currency.upper()] = (price, time.time())


# Global instance
_converter = CurrencyConverter()


def to_usd(amount: float, currency: str) -> float:
    """
    Convert cryptocurrency to USD (convenience function).
    
    Args:
        amount: Amount in crypto
        currency: Currency symbol
        
    Returns:
        USD equivalent
    """
    return _converter.to_usd(amount, currency)


def get_price(currency: str) -> float:
    """
    Get current USD price (convenience function).
    
    Args:
        currency: Currency symbol
        
    Returns:
        Price in USD
    """
    return _converter.get_price(currency)
