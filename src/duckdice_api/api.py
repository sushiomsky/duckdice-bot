from __future__ import annotations
"""
DuckDice API client (requests-based)

Provides `DuckDiceConfig` and `DuckDiceAPI` with small, explicit methods used by
CLI and engine packages.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json
import sys
import requests


@dataclass
class DuckDiceConfig:
    api_key: str
    base_url: str = "https://duckdice.io/api"
    timeout: int = 30


class DuckDiceAPI:
    def __init__(self, config: DuckDiceConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "DuckDiceCLI/1.0.0",
                "Accept": "*/*",
                "Cache-Control": "no-cache",
            }
        )

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[Any, Any]:
        url = f"{self.config.base_url}/{endpoint}"
        params = {"api_key": self.config.api_key}
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=self.config.timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, params=params, json=data, timeout=self.config.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}", file=sys.stderr)
            if hasattr(e.response, "text"):
                print(f"Response: {e.response.text}", file=sys.stderr)
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}", file=sys.stderr)
            raise
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}", file=sys.stderr)
            raise

    def play_dice(
        self,
        symbol: str,
        amount: str,
        chance: str,
        is_high: bool,
        faucet: bool = False,
        wagering_bonus_hash: Optional[str] = None,
        tle_hash: Optional[str] = None,
    ) -> Dict[Any, Any]:
        data: Dict[str, Any] = {
            "symbol": symbol,
            "amount": amount,
            "chance": chance,
            "isHigh": is_high,
            "faucet": faucet,
        }
        if wagering_bonus_hash:
            data["userWageringBonusHash"] = wagering_bonus_hash
        if tle_hash:
            data["tleHash"] = tle_hash
        return self._make_request("POST", "dice/play", data)

    def play_range_dice(
        self,
        symbol: str,
        amount: str,
        range_values: List[int],
        is_in: bool,
        faucet: bool = False,
        wagering_bonus_hash: Optional[str] = None,
        tle_hash: Optional[str] = None,
    ) -> Dict[Any, Any]:
        data: Dict[str, Any] = {
            "symbol": symbol,
            "amount": amount,
            "range": range_values,
            "isIn": is_in,
            "faucet": faucet,
        }
        if wagering_bonus_hash:
            data["userWageringBonusHash"] = wagering_bonus_hash
        if tle_hash:
            data["tleHash"] = tle_hash
        return self._make_request("POST", "range-dice/play", data)

    def get_currency_stats(self, symbol: str) -> Dict[Any, Any]:
        return self._make_request("GET", f"bot/stats/{symbol}")

    def get_user_info(self) -> Dict[Any, Any]:
        return self._make_request("GET", "bot/user-info")
    
    def get_balances(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all balances from user info.
        Returns dict with currency symbols as keys.
        """
        try:
            user_info = self.get_user_info()
            if user_info and "balances" in user_info:
                balances = {}
                for balance in user_info["balances"]:
                    currency = balance.get("currency", "")
                    # Add amount and btc_value for compatibility
                    balance_copy = balance.copy()
                    balance_copy['amount'] = balance.get('main', '0')
                    balance_copy['symbol'] = currency
                    # Estimate BTC value (would need price data for accurate conversion)
                    balance_copy['btc_value'] = 0.0
                    balances[currency] = balance_copy
                return balances
            return {}
        except Exception as e:
            print(f"Failed to get balances: {e}", file=sys.stderr)
            return {}
    
    def get_available_currencies(self) -> list[str]:
        """Fetch list of available currencies from user balances."""
        try:
            user_info = self.get_user_info()
            if user_info and "balances" in user_info:
                currencies = [balance["currency"] for balance in user_info["balances"]]
                return sorted(currencies) if currencies else ["BTC", "ETH", "DOGE", "LTC", "TRX", "XRP"]
            return ["BTC", "ETH", "DOGE", "LTC", "TRX", "XRP"]
        except Exception as e:
            print(f"Failed to fetch currencies: {e}", file=sys.stderr)
            return ["BTC", "ETH", "DOGE", "LTC", "TRX", "XRP"]
    
    def get_main_balance(self, symbol: str) -> float:
        """Get main balance for specific currency."""
        try:
            user_info = self.get_user_info()
            if user_info and "balances" in user_info:
                for balance in user_info["balances"]:
                    if balance.get("currency") == symbol.upper():
                        main = balance.get("main", "0")
                        return float(main) if main else 0.0
            return 0.0
        except Exception as e:
            print(f"Failed to get main balance: {e}", file=sys.stderr)
            return 0.0
    
    def get_faucet_balance(self, symbol: str) -> float:
        """Get faucet balance for specific currency."""
        try:
            user_info = self.get_user_info()
            if user_info and "balances" in user_info:
                for balance in user_info["balances"]:
                    if balance.get("currency") == symbol.upper():
                        # Check if faucet balance exists
                        faucet = balance.get("faucet", "0")
                        return float(faucet) if faucet else 0.0
            return 0.0
        except Exception as e:
            print(f"Failed to get faucet balance: {e}", file=sys.stderr)
            return 0.0
            return 0.0
        except Exception as e:
            print(f"Failed to get faucet balance: {e}", file=sys.stderr)
            return 0.0
    
    def claim_faucet(self, symbol: str, cookie: Optional[str] = None) -> bool:
        """
        Claim faucet for specified currency.
        Requires browser cookie for authentication.
        
        Args:
            symbol: Currency symbol (e.g., "BTC", "DOGE")
            cookie: Browser cookie string (from logged-in session)
            
        Returns:
            True if claim successful, False otherwise
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Content-Type": "application/json",
            }
            
            if cookie:
                headers["Cookie"] = cookie
            
            # Faucet claim endpoint doesn't use API key, uses cookies
            url = f"{self.config.base_url}/faucet"
            response = self.session.post(
                url,
                headers=headers,
                json={"symbol": symbol.upper(), "results": []},
                timeout=self.config.timeout
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to claim faucet: {e}", file=sys.stderr)
            return False
