"""
Caching utilities for performance optimization.

Provides TTL-based caching for API responses and expensive computations
to reduce redundant calls and improve application responsiveness.
"""

from typing import Any, Optional, Callable, TypeVar, Dict
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from collections import OrderedDict

T = TypeVar('T')


class TTLCache:
    """
    Time-To-Live cache with automatic expiration.
    
    Thread-safe cache that automatically expires entries after
    a specified time period. Useful for caching API responses.
    """
    
    def __init__(self, default_ttl: int = 30, max_size: int = 100):
        """
        Initialize TTL cache.
        
        Args:
            default_ttl: Default time-to-live in seconds
            max_size: Maximum number of cache entries (LRU eviction)
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._expiry: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value if present and not expired, None otherwise
        """
        async with self._lock:
            # Check if key exists and not expired
            if key in self._cache:
                if datetime.now() < self._expiry[key]:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    return self._cache[key]
                else:
                    # Expired, remove
                    del self._cache[key]
                    del self._expiry[key]
            
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        async with self._lock:
            # Evict oldest if at max size
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._expiry[oldest_key]
            
            # Set new value
            self._cache[key] = value
            self._expiry[key] = datetime.now() + timedelta(
                seconds=ttl if ttl is not None else self.default_ttl
            )
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if key was present, False otherwise
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._expiry[key]
                return True
            return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._expiry.clear()
    
    async def cleanup(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                k for k, exp_time in self._expiry.items()
                if now >= exp_time
            ]
            
            for key in expired_keys:
                del self._cache[key]
                del self._expiry[key]
            
            return len(expired_keys)
    
    @property
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'default_ttl': self.default_ttl,
            'keys': list(self._cache.keys())
        }


def cached(ttl: int = 30, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key from args
    
    Example:
        >>> @cached(ttl=60)
        ... async def get_user_info(user_id: str):
        ...     return await api.fetch_user(user_id)
        
        >>> @cached(ttl=30, key_func=lambda args, kwargs: f"balance_{kwargs['currency']}")
        ... async def get_balance(currency: str):
        ...     return await api.fetch_balance(currency)
    """
    cache = TTLCache(default_ttl=ttl)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(args, kwargs)
            else:
                # Default key: function name + args
                cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        
        # Add cache management methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        
        return wrapper
    return decorator


class CachedAPIClient:
    """
    Wrapper for API client with automatic caching.
    
    Caches frequently accessed endpoints to reduce API calls
    and improve performance.
    """
    
    def __init__(self, api_client: Any, default_ttl: int = 30):
        """
        Initialize cached API client.
        
        Args:
            api_client: Original API client instance
            default_ttl: Default cache TTL in seconds
        """
        self.api = api_client
        self.cache = TTLCache(default_ttl=default_ttl)
        self._hit_count = 0
        self._miss_count = 0
    
    async def get_user_info(self, ttl: Optional[int] = None) -> Dict[str, Any]:
        """
        Get user info with caching.
        
        Args:
            ttl: Override default TTL
        
        Returns:
            User info dictionary
        """
        cache_key = "user_info"
        cached = await self.cache.get(cache_key)
        
        if cached is not None:
            self._hit_count += 1
            return cached
        
        self._miss_count += 1
        result = await asyncio.to_thread(self.api.get_user_info)
        await self.cache.set(cache_key, result, ttl)
        return result
    
    async def get_balances(self, ttl: Optional[int] = None) -> Dict[str, Any]:
        """
        Get balances with caching.
        
        Args:
            ttl: Override default TTL
        
        Returns:
            Balances dictionary
        """
        cache_key = "balances"
        cached = await self.cache.get(cache_key)
        
        if cached is not None:
            self._hit_count += 1
            return cached
        
        self._miss_count += 1
        result = await asyncio.to_thread(self.api.get_balances)
        await self.cache.set(cache_key, result, ttl)
        return result
    
    async def invalidate(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache.
        
        Args:
            key: Specific key to invalidate, or None to clear all
        """
        if key:
            await self.cache.delete(key)
        else:
            await self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total * 100) if total > 0 else 0
        
        return {
            'hits': self._hit_count,
            'misses': self._miss_count,
            'hit_rate': f"{hit_rate:.1f}%",
            'total_requests': total,
            **self.cache.get_stats()
        }


# Global cache instance for simple use cases
_global_cache = TTLCache()


async def get_cached(key: str) -> Optional[Any]:
    """Get value from global cache"""
    return await _global_cache.get(key)


async def set_cached(key: str, value: Any, ttl: int = 30) -> None:
    """Set value in global cache"""
    await _global_cache.set(key, value, ttl)


async def clear_cache() -> None:
    """Clear global cache"""
    await _global_cache.clear()
