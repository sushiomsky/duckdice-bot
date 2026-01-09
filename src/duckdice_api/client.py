"""
Enhanced DuckDice API client with retry logic and better error handling.
"""

import time
import logging
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    backoff_factor: float = 0.5  # 0.5, 1.0, 2.0 seconds
    status_forcelist: tuple = (429, 500, 502, 503, 504)
    
    def to_urllib3_retry(self) -> Retry:
        """Convert to urllib3 Retry object"""
        return Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )


class APIError(Exception):
    """Base exception for API errors"""
    pass


class APIConnectionError(APIError):
    """Connection-related errors"""
    pass


class APITimeoutError(APIError):
    """Timeout errors"""
    pass


class APIRateLimitError(APIError):
    """Rate limit exceeded"""
    pass


class APIResponseError(APIError):
    """Invalid API response"""
    pass


class EnhancedAPIClient:
    """
    Enhanced API client with retry logic, better error handling, and logging.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        retry_config: Optional[RetryConfig] = None
    ):
        """
        Initialize enhanced API client.
        
        Args:
            base_url: Base URL for API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            retry_config: Retry configuration
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        
        # Create session with retry logic
        self.session = self._create_session()
        
        logger.info(f"Initialized API client for {base_url}")
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        # Configure retry logic
        retry = self.retry_config.to_urllib3_retry()
        adapter = HTTPAdapter(max_retries=retry)
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "DuckDiceBot/3.9.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        })
        
        return session
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        include_api_key: bool = True
    ) -> Dict[Any, Any]:
        """
        Make HTTP request with error handling and logging.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            data: JSON data for POST requests
            params: Query parameters
            include_api_key: Whether to include API key
            
        Returns:
            JSON response as dict
            
        Raises:
            APIError: On various error conditions
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Add API key to params if requested
        if include_api_key:
            params = params or {}
            params['api_key'] = self.api_key
        
        # Log request
        logger.debug(f"{method} {endpoint} - params: {params}, data: {data}")
        
        try:
            start_time = time.time()
            
            # Make request
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.timeout
            )
            
            elapsed = time.time() - start_time
            logger.debug(f"{method} {endpoint} - {response.status_code} in {elapsed:.2f}s")
            
            # Handle specific status codes
            if response.status_code == 429:
                raise APIRateLimitError("Rate limit exceeded")
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Parse JSON
            try:
                json_data = response.json()
                logger.debug(f"Response: {json_data}")
                return json_data
            except ValueError as e:
                logger.error(f"Invalid JSON response: {response.text}")
                raise APIResponseError(f"Invalid JSON: {str(e)}")
        
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {str(e)}")
            raise APITimeoutError(f"Request timed out after {self.timeout}s")
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            raise APIConnectionError(f"Failed to connect: {str(e)}")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}")
            raise APIError(f"HTTP error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise APIError(f"Unexpected error: {str(e)}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[Any, Any]:
        """Make GET request"""
        return self._make_request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[Any, Any]:
        """Make POST request"""
        return self._make_request("POST", endpoint, data=data, params=params)
    
    def with_retry(
        self,
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0
    ) -> Any:
        """
        Execute function with manual retry logic.
        
        Args:
            func: Function to execute
            max_attempts: Maximum retry attempts
            delay: Delay between retries (exponential backoff)
            
        Returns:
            Function result
        """
        last_error = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                return func()
            except (APIConnectionError, APITimeoutError) as e:
                last_error = e
                if attempt < max_attempts:
                    wait_time = delay * (2 ** (attempt - 1))  # Exponential backoff
                    logger.warning(f"Attempt {attempt} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_attempts} attempts failed")
        
        if last_error:
            raise last_error
    
    def close(self):
        """Close session"""
        self.session.close()
        logger.info("API client session closed")
    
    def __enter__(self):
        """Context manager enter"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
