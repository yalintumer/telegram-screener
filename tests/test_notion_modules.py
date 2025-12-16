"""
Tests for Notion HTTP client and repository.

Uses `responses` library for HTTP mocking - deterministic and fast.
"""
import pytest
import responses
from unittest.mock import patch, MagicMock

from src.notion_http import NotionHTTPClient
from src.notion_models import NotionConfig, SignalData
from src.notion_repo import NotionRepository


@pytest.fixture
def notion_config():
    """Create a test Notion config."""
    return NotionConfig(
        api_key="test_api_key_12345",
        database_id="test_watchlist_db",
        signals_database_id="test_signals_db",
        buy_database_id="test_buy_db",
        max_retries=2,
        backoff_factor=0.01,  # Fast retries for tests
        timeout=5,
    )


@pytest.fixture
def http_client(notion_config):
    """Create a test HTTP client."""
    # Reset session to avoid state leakage between tests
    NotionHTTPClient._session = None
    return NotionHTTPClient(notion_config)


@pytest.fixture
def repo(notion_config):
    """Create a test repository."""
    NotionHTTPClient._session = None
    return NotionRepository(notion_config)


class TestNotionHTTPClient:
    """Tests for NotionHTTPClient."""

    @responses.activate
    def test_successful_get_request(self, http_client):
        """Test successful GET request."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/databases/test_db",
            json={"id": "test_db", "properties": {}},
            status=200,
        )

        response = http_client.get("/databases/test_db")

        assert response.status_code == 200
        assert response.json()["id"] == "test_db"

    @responses.activate
    def test_successful_post_request(self, http_client):
        """Test successful POST request with JSON body."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_db/query",
            json={"results": [{"id": "page1"}]},
            status=200,
        )

        response = http_client.post(
            "/databases/test_db/query",
            json={"filter": {}},
        )

        assert response.status_code == 200
        assert len(response.json()["results"]) == 1

    @responses.activate
    def test_rate_limit_429_retry(self, http_client):
        """Test that 429 rate limit triggers retry with Retry-After header."""
        # First call returns 429, second succeeds
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_db/query",
            status=429,
            headers={"Retry-After": "0"},  # 0 seconds for fast test
        )
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_db/query",
            json={"results": []},
            status=200,
        )

        with patch("src.notion_http.time.sleep"):  # Skip actual sleep
            response = http_client.post("/databases/test_db/query", json={})

        assert response.status_code == 200
        assert len(responses.calls) == 2  # First 429, then success

    @responses.activate
    def test_timeout_retry(self, http_client):
        """Test that timeout triggers retry."""
        import requests

        # First call times out, second succeeds
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_db/query",
            body=requests.exceptions.Timeout("Connection timed out"),
        )
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_db/query",
            json={"results": []},
            status=200,
        )

        with patch("src.notion_http.time.sleep"):  # Skip actual sleep
            response = http_client.post("/databases/test_db/query", json={})

        assert response.status_code == 200
        assert len(responses.calls) == 2

    @responses.activate
    def test_all_retries_exhausted_raises(self, http_client):
        """Test that exception is raised when all retries fail."""
        import requests

        # All calls fail
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_db/query",
            body=requests.exceptions.ConnectionError("Network unreachable"),
        )
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_db/query",
            body=requests.exceptions.ConnectionError("Network unreachable"),
        )

        with patch("src.notion_http.time.sleep"):
            with pytest.raises(requests.exceptions.RequestException):
                http_client.post("/databases/test_db/query", json={})

    @responses.activate
    def test_get_database_schema_caching(self, http_client):
        """Test that schema is cached after first fetch."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/databases/test_db",
            json={
                "properties": {
                    "Name": {"type": "title"},
                    "Date": {"type": "date"},
                }
            },
            status=200,
        )

        # First call - should hit API
        schema1 = http_client.get_database_schema("test_db")
        # Second call - should use cache
        schema2 = http_client.get_database_schema("test_db")

        assert schema1 == schema2
        assert "Name" in schema1
        assert len(responses.calls) == 1  # Only one API call due to caching

    def test_find_title_property(self, http_client):
        """Test finding title property from schema."""
        properties = {
            "Status": {"type": "select"},
            "Symbol": {"type": "title"},
            "Date": {"type": "date"},
        }

        result = http_client.find_title_property(properties)
        assert result == "Symbol"

    def test_find_title_property_not_found(self, http_client):
        """Test when no title property exists."""
        properties = {
            "Status": {"type": "select"},
            "Date": {"type": "date"},
        }

        result = http_client.find_title_property(properties)
        assert result is None


class TestNotionRepository:
    """Tests for NotionRepository."""

    @responses.activate
    def test_get_signals_success(self, repo):
        """Test successful signal retrieval."""
        # Mock schema endpoint
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/databases/test_signals_db",
            json={"properties": {"Symbol": {"type": "title"}}},
            status=200,
        )
        # Mock query endpoint
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_signals_db/query",
            json={
                "results": [
                    {
                        "id": "page1",
                        "properties": {
                            "Symbol": {
                                "type": "title",
                                "title": [{"text": {"content": "AAPL"}}],
                            }
                        },
                    },
                    {
                        "id": "page2",
                        "properties": {
                            "Symbol": {
                                "type": "title",
                                "title": [{"text": {"content": "MSFT"}}],
                            }
                        },
                    },
                ]
            },
            status=200,
        )

        symbols, mapping = repo.get_signals()

        assert symbols == ["AAPL", "MSFT"]
        assert mapping == {"AAPL": "page1", "MSFT": "page2"}

    @responses.activate
    def test_get_signals_empty_database(self, repo):
        """Test getting signals from empty database."""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_signals_db/query",
            json={"results": []},
            status=200,
        )

        symbols, mapping = repo.get_signals()

        assert symbols == []
        assert mapping == {}

    @responses.activate
    def test_get_signals_network_error_returns_empty(self, repo):
        """Test that network errors return empty results gracefully."""
        import requests

        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_signals_db/query",
            body=requests.exceptions.ConnectionError("Network error"),
        )
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/test_signals_db/query",
            body=requests.exceptions.ConnectionError("Network error"),
        )

        with patch("src.notion_http.time.sleep"):
            symbols, mapping = repo.get_signals()

        # Should return empty, not raise
        assert symbols == []
        assert mapping == {}

    @responses.activate
    def test_add_to_signals_success(self, repo):
        """Test adding a signal to the database."""
        # Mock schema
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/databases/test_signals_db",
            json={
                "properties": {
                    "Symbol": {"type": "title"},
                    "Date": {"type": "date"},
                    "RSI": {"type": "number"},
                }
            },
            status=200,
        )
        # Mock page creation
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={"id": "new_page"},
            status=200,
        )

        signal = SignalData(
            symbol="AAPL",
            date="2024-12-16",
            rsi=28.5,
        )
        result = repo.add_to_signals(signal)

        assert result is True
        # Verify page was created with correct data
        assert len(responses.calls) == 2

    @responses.activate
    def test_delete_page_success(self, repo):
        """Test successful page deletion (archiving)."""
        # Mock GET to check if page exists
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={"id": "page123", "archived": False},
            status=200,
        )
        # Mock PATCH to archive
        responses.add(
            responses.PATCH,
            "https://api.notion.com/v1/pages/page123",
            json={"id": "page123", "archived": True},
            status=200,
        )

        result = repo.delete_page("page123")

        assert result is True

    @responses.activate
    def test_delete_page_already_archived(self, repo):
        """Test deleting already archived page returns True."""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={"id": "page123", "archived": True},
            status=200,
        )

        result = repo.delete_page("page123")

        assert result is True
        # Only GET call, no PATCH needed
        assert len(responses.calls) == 1

    def test_get_signals_no_database_id(self, notion_config):
        """Test get_signals when signals_database_id is None."""
        notion_config.signals_database_id = None
        repo = NotionRepository(notion_config)

        symbols, mapping = repo.get_signals()

        assert symbols == []
        assert mapping == {}


class TestSignalDataModel:
    """Tests for SignalData model."""

    def test_to_notion_properties_basic(self):
        """Test converting SignalData to Notion properties."""
        signal = SignalData(
            symbol="AAPL",
            date="2024-12-16",
            rsi=28.5,
            stoch_k=15.0,
        )

        schema = {
            "Symbol": {"type": "title"},
            "Date": {"type": "date"},
            "RSI": {"type": "number"},
            "Stoch K": {"type": "number"},
        }

        props = signal.to_notion_properties("Symbol", schema)

        assert props["Symbol"] == {"title": [{"text": {"content": "AAPL"}}]}
        assert props["Date"] == {"date": {"start": "2024-12-16"}}
        assert props["RSI"] == {"number": 28.5}
        assert props["Stoch K"] == {"number": 15.0}

    def test_to_notion_properties_missing_schema_fields(self):
        """Test that missing schema fields are skipped."""
        signal = SignalData(
            symbol="MSFT",
            date="2024-12-16",
            rsi=30.0,
            macd=0.5,  # Not in schema
        )

        schema = {
            "Name": {"type": "title"},
            "RSI": {"type": "number"},
        }

        props = signal.to_notion_properties("Name", schema)

        assert "Name" in props
        assert "RSI" in props
        assert "MACD" not in props  # Not in schema

    def test_to_notion_properties_none_values_skipped(self):
        """Test that None values are not included."""
        signal = SignalData(
            symbol="GOOG",
            date="2024-12-16",
            rsi=None,  # Should be skipped
        )

        schema = {
            "Symbol": {"type": "title"},
            "RSI": {"type": "number"},
        }

        props = signal.to_notion_properties("Symbol", schema)

        assert "Symbol" in props
        assert "RSI" not in props  # None value skipped
