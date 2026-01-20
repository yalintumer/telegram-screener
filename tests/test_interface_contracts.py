"""
Interface Contract Tests

These tests verify that public APIs exist and are callable.
They catch interface breaking changes during refactoring.

NO MOCKS - just interface verification.
These tests should BLOCK merges if they fail.
"""

import inspect


class TestNotionClientInterfaceContract:
    """
    Contract tests for NotionClient public interface.

    These methods are used by other modules (backup.py, scanner.py, etc.)
    and MUST exist for backwards compatibility.
    """

    def test_notion_client_importable(self):
        """NotionClient should be importable from src.notion_client."""
        from src.notion_client import NotionClient

        assert NotionClient is not None

    def test_has_request_method(self):
        """NotionClient must have _request method (used by backup.py)."""
        from src.notion_client import NotionClient

        # Check class has the attribute
        assert hasattr(NotionClient, "_request"), "NotionClient missing '_request' method - backup.py will break!"

    def test_request_method_is_callable(self):
        """_request must be a callable method."""
        from src.notion_client import NotionClient

        # Get the method from class (not instance)
        method = getattr(NotionClient, "_request", None)
        assert method is not None, "NotionClient._request not found"
        assert callable(method), "NotionClient._request is not callable"

    def test_request_method_signature(self):
        """_request should accept (self, method, url, json=None)."""
        from src.notion_client import NotionClient

        method = NotionClient._request
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        # Should have: self, method, url, and optionally json/kwargs
        assert "self" in params, "_request missing 'self' parameter"
        assert "method" in params, "_request missing 'method' parameter"
        assert "url" in params, "_request missing 'url' parameter"

    def test_has_base_url_property(self):
        """NotionClient instances must have base_url attribute (used by backup.py)."""
        from src.notion_client import NotionClient

        # Create a minimal instance to check instance attributes
        # We need to check that __init__ sets base_url
        init_source = inspect.getsource(NotionClient.__init__)
        assert "base_url" in init_source, "NotionClient.__init__ should set 'base_url' attribute"

    def test_has_all_public_methods(self):
        """NotionClient must have all documented public methods."""
        from src.notion_client import NotionClient

        required_methods = [
            "get_watchlist",
            "add_to_watchlist",
            "delete_from_watchlist",
            "get_signals",
            "add_to_signals",
            "delete_from_signals",
            "add_to_buy",
            "delete_from_buy",
            "get_all_symbols",
            "_request",  # Legacy facade method
        ]

        for method_name in required_methods:
            assert hasattr(NotionClient, method_name), f"NotionClient missing required method: {method_name}"
            assert callable(getattr(NotionClient, method_name)), f"NotionClient.{method_name} is not callable"


class TestSignalTrackerInterfaceContract:
    """
    Contract tests for SignalTracker public interface.

    These methods are used by analytics.py and other modules.
    """

    def test_signal_tracker_importable(self):
        """SignalTracker should be importable from src.signal_tracker."""
        from src.signal_tracker import SignalTracker

        assert SignalTracker is not None

    def test_has_get_all_stats_method(self):
        """SignalTracker must have get_all_stats method (used by analytics.py)."""
        from src.signal_tracker import SignalTracker

        assert hasattr(SignalTracker, "get_all_stats"), (
            "SignalTracker missing 'get_all_stats' method - analytics.py will break!"
        )

    def test_get_all_stats_is_callable(self):
        """get_all_stats must be a callable method."""
        from src.signal_tracker import SignalTracker

        method = getattr(SignalTracker, "get_all_stats", None)
        assert method is not None, "SignalTracker.get_all_stats not found"
        assert callable(method), "SignalTracker.get_all_stats is not callable"

    def test_get_all_stats_signature(self):
        """get_all_stats should accept only self (no required args)."""
        from src.signal_tracker import SignalTracker

        method = SignalTracker.get_all_stats
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        # Should only have 'self'
        assert params == ["self"], f"get_all_stats should only take 'self', got: {params}"

    def test_has_all_public_methods(self):
        """SignalTracker must have all documented public methods."""
        from src.signal_tracker import SignalTracker

        required_methods = [
            "can_send_alert",
            "record_alert",
            "get_daily_stats",
            "get_symbol_cooldown_status",
            "update_signal_performance",
            "get_signal_stats",
            "get_all_stats",  # Backwards compatibility alias
        ]

        for method_name in required_methods:
            assert hasattr(SignalTracker, method_name), f"SignalTracker missing required method: {method_name}"
            assert callable(getattr(SignalTracker, method_name)), f"SignalTracker.{method_name} is not callable"


class TestTelegramClientInterfaceContract:
    """Contract tests for TelegramClient public interface."""

    def test_telegram_client_importable(self):
        """TelegramClient should be importable."""
        from src.telegram_client import TelegramClient

        assert TelegramClient is not None

    def test_has_send_method(self):
        """TelegramClient must have send method."""
        from src.telegram_client import TelegramClient

        assert hasattr(TelegramClient, "send"), "TelegramClient missing 'send' method"
        assert callable(TelegramClient.send), "TelegramClient.send is not callable"


class TestBackupModuleInterfaceContract:
    """Contract tests for backup module interface."""

    def test_backup_importable(self):
        """Backup classes should be importable."""
        from src.backup import NotionBackup

        assert NotionBackup is not None

    def test_backup_has_required_methods(self):
        """NotionBackup must have backup_database method."""
        from src.backup import NotionBackup

        required_methods = ["backup_database", "backup_all"]

        for method_name in required_methods:
            assert hasattr(NotionBackup, method_name), f"NotionBackup missing required method: {method_name}"


class TestAnalyticsModuleInterfaceContract:
    """Contract tests for analytics module interface."""

    def test_analytics_importable(self):
        """Analytics class should be importable."""
        from src.analytics import Analytics

        assert Analytics is not None

    def test_analytics_has_required_methods(self):
        """Analytics must have generate_weekly_report method."""
        from src.analytics import Analytics

        required_methods = [
            "generate_weekly_report",
            "get_weekly_stats",
            "should_send_weekly_report",
            "record_alert_sent",
        ]

        for method_name in required_methods:
            assert hasattr(Analytics, method_name), f"Analytics missing required method: {method_name}"
            assert callable(getattr(Analytics, method_name)), f"Analytics.{method_name} is not callable"
