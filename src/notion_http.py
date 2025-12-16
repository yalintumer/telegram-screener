"""
Notion HTTP client with session pooling, retry logic, and rate limiting.

This module handles all low-level HTTP communication with the Notion API.
"""
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.logger import logger
from src.notion_models import NotionConfig
from src.rate_limiter import rate_limit

# Default configuration
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.0


class NotionHTTPClient:
    """
    Low-level HTTP client for Notion API.

    Features:
    - Connection pooling with shared session
    - Automatic retry with exponential backoff
    - Rate limiting integration
    - Proper error handling and logging
    """

    # Class-level session for connection pooling
    _session: requests.Session | None = None

    def __init__(self, config: NotionConfig):
        """
        Initialize the HTTP client.

        Args:
            config: NotionConfig with API credentials and settings
        """
        self.config = config
        self._schema_cache: dict[str, dict[str, Any]] = {}

    @classmethod
    def _get_session(cls) -> requests.Session:
        """
        Get or create a shared session with connection pooling.

        Returns:
            Configured requests.Session instance
        """
        if cls._session is None:
            cls._session = requests.Session()
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=10,
                pool_maxsize=10,
            )
            cls._session.mount("https://", adapter)
            cls._session.mount("http://", adapter)
        return cls._session

    def request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
        *,
        use_rate_limiter: bool = True,
    ) -> requests.Response:
        """
        Make an HTTP request to the Notion API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., "/databases/{id}/query")
            json: Optional JSON payload
            use_rate_limiter: Whether to use rate limiting (default: True)

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure after retries
        """
        url = f"{self.config.base_url}{endpoint}"
        session = self._get_session()

        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                # Apply rate limiting
                if use_rate_limiter:
                    rate_limit("notion")

                response = session.request(
                    method=method,
                    url=url,
                    headers=self.config.headers,
                    json=json,
                    timeout=self.config.timeout,
                )

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    logger.warning(
                        "notion.rate_limited",
                        retry_after=retry_after,
                        attempt=attempt + 1,
                    )
                    time.sleep(retry_after)
                    continue

                # Success or client error (4xx) - don't retry
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.backoff_factor * (2**attempt)
                    logger.warning(
                        "notion.request_retry",
                        attempt=attempt + 1,
                        wait_time=wait_time,
                        error=str(e),
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "notion.request_failed",
                        method=method,
                        endpoint=endpoint,
                        error=str(e),
                    )

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise requests.exceptions.RequestException(
            f"Request failed after {self.config.max_retries} retries"
        )

    def get(
        self, endpoint: str, *, use_rate_limiter: bool = True
    ) -> requests.Response:
        """GET request shorthand."""
        return self.request("GET", endpoint, use_rate_limiter=use_rate_limiter)

    def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        *,
        use_rate_limiter: bool = True,
    ) -> requests.Response:
        """POST request shorthand."""
        return self.request("POST", endpoint, json, use_rate_limiter=use_rate_limiter)

    def patch(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        *,
        use_rate_limiter: bool = True,
    ) -> requests.Response:
        """PATCH request shorthand."""
        return self.request("PATCH", endpoint, json, use_rate_limiter=use_rate_limiter)

    def get_database_schema(self, database_id: str) -> dict[str, Any]:
        """
        Get database schema with caching.

        Args:
            database_id: Notion database ID

        Returns:
            Dictionary of property definitions
        """
        if database_id in self._schema_cache:
            return self._schema_cache[database_id]

        try:
            response = self.get(f"/databases/{database_id}")
            data = response.json()
            properties = data.get("properties", {})
            self._schema_cache[database_id] = properties
            return properties
        except Exception as e:
            logger.error(
                "notion.schema_fetch_failed", database_id=database_id, error=str(e)
            )
            return {}

    def find_title_property(self, properties: dict[str, Any]) -> str | None:
        """
        Find the title property name in a schema.

        Args:
            properties: Database properties dictionary

        Returns:
            Title property name or None
        """
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                return prop_name
        return None

    def find_date_property(self, properties: dict[str, Any]) -> str | None:
        """
        Find a date property name in a schema.

        Args:
            properties: Database properties dictionary

        Returns:
            Date property name or None
        """
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "date":
                return prop_name
        return None

    def clear_schema_cache(self) -> None:
        """Clear the schema cache."""
        self._schema_cache.clear()

    @classmethod
    def close_session(cls) -> None:
        """Close the shared session."""
        if cls._session:
            cls._session.close()
            cls._session = None
