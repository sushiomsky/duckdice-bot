"""
Deprecated compatibility layer.

Runtime API ownership is `duckdice_api.api` (`DuckDiceAPI`, `DuckDiceConfig`).
This module remains as a shim to avoid import breakage for old code paths.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional
import warnings

from .api import DuckDiceAPI, DuckDiceConfig


class APIError(Exception):
    """Legacy API error alias retained for compatibility."""


class APIConnectionError(APIError):
    """Legacy connection error alias retained for compatibility."""


class APITimeoutError(APIError):
    """Legacy timeout error alias retained for compatibility."""


class APIRateLimitError(APIError):
    """Legacy rate-limit error alias retained for compatibility."""


class APIResponseError(APIError):
    """Legacy response error alias retained for compatibility."""


@dataclass
class RetryConfig:
    """Legacy retry config placeholder (not used by canonical client)."""
    max_retries: int = 3
    backoff_factor: float = 0.5
    status_forcelist: tuple = (429, 500, 502, 503, 504)


class EnhancedAPIClient:
    """
    Backward-compatible wrapper around canonical `DuckDiceAPI`.
    New runtime code should import from `duckdice_api.api` directly.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        retry_config: Optional[RetryConfig] = None,
    ):
        warnings.warn(
            "duckdice_api.client.EnhancedAPIClient is deprecated; "
            "use duckdice_api.api.DuckDiceAPI + DuckDiceConfig.",
            DeprecationWarning,
            stacklevel=2,
        )
        _ = retry_config
        self.config = DuckDiceConfig(api_key=api_key, base_url=base_url, timeout=timeout)
        self._api = DuckDiceAPI(self.config)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        include_api_key: bool = True,
    ) -> Dict[Any, Any]:
        _ = params, include_api_key
        return self._api._make_request(method, endpoint.lstrip("/"), data)

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[Any, Any]:
        _ = params
        return self._api._make_request("GET", endpoint.lstrip("/"))

    def post(self, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[Any, Any]:
        _ = params
        return self._api._make_request("POST", endpoint.lstrip("/"), data or {})

    def with_retry(
        self,
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0,
    ) -> Any:
        _ = max_attempts, delay
        return func()

    def close(self):
        self._api.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
