"""
Turbo-optimized API client for maximum betting speed.

Features:
- Connection pooling with keep-alive
- Reduced timeouts for faster failures
- No artificial delays
- Concurrent request support
- Optimized for speed over reliability
"""
import asyncio
from typing import Dict, Any, Optional, List
import aiohttp
from dataclasses import dataclass
import time

@dataclass
class TurboConfig:
    """Configuration for turbo betting mode"""
    api_key: str
    base_url: str = "https://duckdice.io/api"
    timeout: int = 10  # Reduced from 30s for faster failures
    max_connections: int = 100  # Connection pool size
    keepalive_timeout: int = 30
    enable_tcp_nodelay: bool = True  # Disable Nagle's algorithm for lower latency


class TurboAPIClient:
    """
    High-performance async API client optimized for speed.
    
    Uses connection pooling, keep-alive, and async I/O for maximum throughput.
    Can handle concurrent bets for multi-currency strategies.
    """
    
    def __init__(self, config: TurboConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def connect(self):
        """Initialize connection pool"""
        if self._session:
            return
            
        # Create optimized TCP connector
        self._connector = aiohttp.TCPConnector(
            limit=self.config.max_connections,
            limit_per_host=self.config.max_connections,
            keepalive_timeout=self.config.keepalive_timeout,
            force_close=False,  # Reuse connections
            enable_cleanup_closed=True,
        )
        
        # Set TCP_NODELAY if supported
        if self.config.enable_tcp_nodelay:
            # aiohttp enables TCP_NODELAY by default
            pass
        
        # Create session with optimized settings
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self._session = aiohttp.ClientSession(
            connector=self._connector,
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DuckDiceBot-Turbo/3.9.0",
                "Accept": "*/*",
                "Connection": "keep-alive",
            }
        )
        
    async def close(self):
        """Close connection pool"""
        if self._session:
            await self._session.close()
            self._session = None
        if self._connector:
            await self._connector.close()
            self._connector = None
            
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make async API request"""
        if not self._session:
            await self.connect()
            
        url = f"{self.config.base_url}/{endpoint}"
        params = {"api_key": self.config.api_key}
        
        try:
            if method.upper() == "GET":
                async with self._session.get(url, params=params) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            elif method.upper() == "POST":
                async with self._session.post(url, params=params, json=data) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            else:
                raise ValueError(f"Unsupported method: {method}")
        except aiohttp.ClientError as e:
            raise Exception(f"API request failed: {e}")
            
    async def play_dice(
        self,
        symbol: str,
        amount: str,
        chance: str,
        is_high: bool,
        faucet: bool = False,
    ) -> Dict[str, Any]:
        """Place dice bet (async, fast)"""
        data = {
            "symbol": symbol,
            "amount": amount,
            "chance": chance,
            "isHigh": is_high,
            "faucet": faucet,
        }
        return await self._request("POST", "dice/play", data)
        
    async def play_dice_batch(
        self,
        bets: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Place multiple bets concurrently.
        
        Args:
            bets: List of bet specs with keys: symbol, amount, chance, is_high, faucet
            
        Returns:
            List of results in same order as input
        """
        tasks = []
        for bet in bets:
            task = self.play_dice(
                symbol=bet.get('symbol', 'BTC'),
                amount=bet['amount'],
                chance=bet['chance'],
                is_high=bet.get('is_high', True),
                faucet=bet.get('faucet', False),
            )
            tasks.append(task)
            
        # Execute all concurrently
        return await asyncio.gather(*tasks, return_exceptions=True)
        
    async def get_balances(self) -> Dict[str, Dict[str, Any]]:
        """Get all balances (async)"""
        user_info = await self._request("GET", "bot/user-info")
        balances = {}
        if user_info and "balances" in user_info:
            for balance in user_info["balances"]:
                currency = balance.get("currency", "")
                balance_copy = balance.copy()
                balance_copy['amount'] = balance.get('main', '0')
                balance_copy['symbol'] = currency
                balances[currency] = balance_copy
        return balances
        
    async def get_user_info(self) -> Dict[str, Any]:
        """Get user info (async)"""
        return await self._request("GET", "bot/user-info")


class TurboStats:
    """Track turbo mode performance metrics"""
    
    def __init__(self):
        self.total_bets = 0
        self.total_time = 0.0
        self.fastest_bet = float('inf')
        self.slowest_bet = 0.0
        self.start_time = time.time()
        
    def record_bet(self, duration: float):
        """Record bet timing"""
        self.total_bets += 1
        self.total_time += duration
        self.fastest_bet = min(self.fastest_bet, duration)
        self.slowest_bet = max(self.slowest_bet, duration)
        
    @property
    def avg_bet_time(self) -> float:
        """Average time per bet"""
        return self.total_time / self.total_bets if self.total_bets > 0 else 0
        
    @property
    def bets_per_second(self) -> float:
        """Betting speed in bets/sec"""
        return self.total_bets / self.total_time if self.total_time > 0 else 0
        
    @property
    def session_duration(self) -> float:
        """Total session duration"""
        return time.time() - self.start_time
        
    def summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            'total_bets': self.total_bets,
            'session_duration': self.session_duration,
            'total_betting_time': self.total_time,
            'avg_bet_time': self.avg_bet_time,
            'fastest_bet': self.fastest_bet if self.fastest_bet != float('inf') else 0,
            'slowest_bet': self.slowest_bet,
            'bets_per_second': self.bets_per_second,
            'overhead_time': self.session_duration - self.total_time,
        }
