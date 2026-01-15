"""Base API client for *arr applications."""

import httpx
from typing import Any, Dict, Optional
import asyncio
from contextlib import asynccontextmanager


class ArrClientError(Exception):
    """Base exception for *arr client errors."""
    pass


class ArrAPIError(ArrClientError):
    """Raised when the *arr API returns an error response."""
    def __init__(self, status_code: int, message: str, response_data: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"API error {status_code}: {message}")


class ArrConnectionError(ArrClientError):
    """Raised when connection to the *arr instance fails."""
    pass


class BaseArrClient:
    """Base client for *arr applications with connection pooling and retry logic."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the base *arr client.

        Args:
            base_url: Base URL of the *arr instance (e.g., "http://192.168.45.15:8083")
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for transient failures
            retry_delay: Base delay between retries (exponential backoff)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0
                )
            )
        return self._client

    async def close(self):
        """Close the HTTP client and cleanup connections."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _is_transient_error(self, status_code: int) -> bool:
        """Check if an HTTP error is transient and should be retried."""
        # Retry on server errors and rate limiting
        return status_code in (408, 429, 500, 502, 503, 504)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Any:
        """
        Make an authenticated request to the *arr API with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path (e.g., "series" or "series/1")
            params: Query parameters
            json_data: JSON request body
            retry_count: Current retry attempt number

        Returns:
            Parsed JSON response or None for 204 responses

        Raises:
            ArrAPIError: For API errors
            ArrConnectionError: For connection failures
        """
        client = await self._get_client()

        # Build URL
        path = endpoint.lstrip("/")
        url = f"{self.base_url}/api/v3/{path}"

        # Build headers
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers
            )

            # Handle successful responses
            if response.status_code == 204 or not response.text:
                return None

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            # Check if we should retry
            if self._is_transient_error(e.response.status_code) and retry_count < self.max_retries:
                delay = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                await asyncio.sleep(delay)
                return await self._request(method, endpoint, params, json_data, retry_count + 1)

            # Parse error response
            try:
                error_data = e.response.json()
            except Exception:
                error_data = None

            raise ArrAPIError(
                status_code=e.response.status_code,
                message=e.response.text,
                response_data=error_data
            )

        except (httpx.RequestError, httpx.ConnectError, httpx.TimeoutException) as e:
            # Retry transient connection errors
            if retry_count < self.max_retries:
                delay = self.retry_delay * (2 ** retry_count)
                await asyncio.sleep(delay)
                return await self._request(method, endpoint, params, json_data, retry_count + 1)

            raise ArrConnectionError(f"Failed to connect to {self.base_url}: {str(e)}")

        except Exception as e:
            raise ArrClientError(f"Unexpected error: {str(e)}")

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a GET request."""
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json_data: Dict[str, Any]) -> Any:
        """Make a POST request."""
        return await self._request("POST", endpoint, json_data=json_data)

    async def put(self, endpoint: str, json_data: Dict[str, Any]) -> Any:
        """Make a PUT request."""
        return await self._request("PUT", endpoint, json_data=json_data)

    async def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Make a DELETE request."""
        return await self._request("DELETE", endpoint, params=params)
