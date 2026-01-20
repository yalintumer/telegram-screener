"""Tests for analytics module."""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.analytics import Analytics


class TestAnalyticsInit:
    """Tests for Analytics initialization."""

    def test_creates_default_data_when_file_not_exists(self, tmp_path):
        """Should create default data structure when file doesn't exist."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        assert analytics.data == {
            "market_scans": [],
            "stage1_scans": [],
            "stage2_scans": [],
            "alerts_sent": [],
            "last_report_date": None,
        }

    def test_loads_existing_data_from_file(self, tmp_path):
        """Should load existing data from file."""
        data_file = tmp_path / "analytics.json"
        existing_data = {
            "market_scans": [{"timestamp": "2024-01-01T00:00:00", "found": 10}],
            "stage1_scans": [],
            "stage2_scans": [],
            "alerts_sent": [],
            "last_report_date": "2024-01-01T00:00:00",
        }
        data_file.write_text(json.dumps(existing_data))

        analytics = Analytics(data_file=str(data_file))

        assert analytics.data["market_scans"] == existing_data["market_scans"]
        assert analytics.data["last_report_date"] == "2024-01-01T00:00:00"

    def test_handles_corrupted_json_file(self, tmp_path):
        """Should return default data when JSON is corrupted."""
        data_file = tmp_path / "analytics.json"
        data_file.write_text("not valid json {{{")

        analytics = Analytics(data_file=str(data_file))

        assert analytics.data == {
            "market_scans": [],
            "stage1_scans": [],
            "stage2_scans": [],
            "alerts_sent": [],
            "last_report_date": None,
        }

    def test_handles_empty_json_file(self, tmp_path):
        """Should return default data when JSON file is empty."""
        data_file = tmp_path / "analytics.json"
        data_file.write_text("")

        analytics = Analytics(data_file=str(data_file))

        assert analytics.data["market_scans"] == []


class TestRecordMarketScan:
    """Tests for record_market_scan method."""

    def test_records_market_scan_data(self, tmp_path):
        """Should record market scan statistics."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_market_scan(found=100, added=5, updated=10)

        assert len(analytics.data["market_scans"]) == 1
        scan = analytics.data["market_scans"][0]
        assert scan["found"] == 100
        assert scan["added"] == 5
        assert scan["updated"] == 10
        assert "timestamp" in scan

    def test_persists_to_file(self, tmp_path):
        """Should save data to file after recording."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_market_scan(found=50, added=2, updated=3)

        # Verify file was written
        saved_data = json.loads(data_file.read_text())
        assert len(saved_data["market_scans"]) == 1

    def test_appends_multiple_scans(self, tmp_path):
        """Should append multiple market scans."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_market_scan(found=100, added=5, updated=10)
        analytics.record_market_scan(found=200, added=10, updated=20)

        assert len(analytics.data["market_scans"]) == 2


class TestRecordStage1Scan:
    """Tests for record_stage1_scan method."""

    def test_records_stage1_scan_data(self, tmp_path):
        """Should record Stage 1 scan statistics."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_stage1_scan(checked=50, passed=10)

        assert len(analytics.data["stage1_scans"]) == 1
        scan = analytics.data["stage1_scans"][0]
        assert scan["checked"] == 50
        assert scan["passed"] == 10
        assert scan["pass_rate"] == 20.0

    def test_handles_zero_checked(self, tmp_path):
        """Should handle zero checked symbols without division error."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_stage1_scan(checked=0, passed=0)

        scan = analytics.data["stage1_scans"][0]
        assert scan["pass_rate"] == 0


class TestRecordStage2Scan:
    """Tests for record_stage2_scan method."""

    def test_records_stage2_scan_data(self, tmp_path):
        """Should record Stage 2 scan statistics."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_stage2_scan(checked=20, confirmed=5)

        assert len(analytics.data["stage2_scans"]) == 1
        scan = analytics.data["stage2_scans"][0]
        assert scan["checked"] == 20
        assert scan["confirmed"] == 5
        assert scan["confirmation_rate"] == 25.0

    def test_handles_zero_checked(self, tmp_path):
        """Should handle zero checked symbols without division error."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_stage2_scan(checked=0, confirmed=0)

        scan = analytics.data["stage2_scans"][0]
        assert scan["confirmation_rate"] == 0


class TestRecordAlertSent:
    """Tests for record_alert_sent method."""

    def test_records_alert_data(self, tmp_path):
        """Should record alert information."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_alert_sent(symbol="AAPL", price=150.50)

        assert len(analytics.data["alerts_sent"]) == 1
        alert = analytics.data["alerts_sent"][0]
        assert alert["symbol"] == "AAPL"
        assert alert["price"] == 150.50
        assert "timestamp" in alert


class TestGetWeeklyStats:
    """Tests for get_weekly_stats method."""

    def test_returns_empty_stats_when_no_data(self, tmp_path):
        """Should return zero stats when no data exists."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        stats = analytics.get_weekly_stats()

        assert stats["market_scans"] == 0
        assert stats["stage1_scans"] == 0
        assert stats["stage2_scans"] == 0
        assert stats["alerts_sent"] == 0
        assert stats["avg_stage1_pass_rate"] == 0
        assert stats["avg_stage2_confirm_rate"] == 0

    def test_filters_data_within_7_days(self, tmp_path):
        """Should only include data from past 7 days."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        # Add old data (10 days ago)
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        analytics.data["market_scans"].append({"timestamp": old_timestamp, "found": 100, "added": 5, "updated": 10})

        # Add recent data (2 days ago)
        recent_timestamp = (datetime.now() - timedelta(days=2)).isoformat()
        analytics.data["market_scans"].append({"timestamp": recent_timestamp, "found": 200, "added": 10, "updated": 20})

        stats = analytics.get_weekly_stats()

        assert stats["market_scans"] == 1  # Only recent data

    def test_calculates_average_pass_rate(self, tmp_path):
        """Should calculate average Stage 1 pass rate."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        recent = datetime.now().isoformat()
        analytics.data["stage1_scans"] = [
            {"timestamp": recent, "checked": 100, "passed": 20, "pass_rate": 20.0},
            {"timestamp": recent, "checked": 100, "passed": 40, "pass_rate": 40.0},
        ]

        stats = analytics.get_weekly_stats()

        assert stats["avg_stage1_pass_rate"] == 30.0  # (20 + 40) / 2

    def test_returns_unique_alert_symbols(self, tmp_path):
        """Should return unique alert symbols."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        recent = datetime.now().isoformat()
        analytics.data["alerts_sent"] = [
            {"timestamp": recent, "symbol": "AAPL", "price": 150},
            {"timestamp": recent, "symbol": "GOOGL", "price": 2800},
            {"timestamp": recent, "symbol": "AAPL", "price": 152},  # Duplicate
        ]

        stats = analytics.get_weekly_stats()

        assert stats["alerts_sent"] == 3
        assert set(stats["alert_symbols"]) == {"AAPL", "GOOGL"}


class TestGenerateWeeklyReport:
    """Tests for generate_weekly_report method."""

    def test_generates_report_with_empty_data(self, tmp_path):
        """Should generate report even with no data."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        mock_tracker = Mock()
        mock_tracker.get_all_stats.return_value = {}

        report = analytics.generate_weekly_report(mock_tracker)

        assert "WEEKLY TELEGRAM SCREENER REPORT" in report
        assert "Market Scans" in report
        assert "Stage 1 Scans" in report

    def test_includes_signal_performance(self, tmp_path):
        """Should include signal performance data."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        mock_tracker = Mock()
        mock_tracker.get_all_stats.return_value = {
            "total_signals": 8,
            "evaluated": 5,
            "pending": 3,
            "avg_return": 10.5,
            "win_rate": 60,
        }

        report = analytics.generate_weekly_report(mock_tracker)

        assert "Total Symbols Tracked: 8" in report
        assert "Signals Evaluated" in report
        assert "Average Return" in report

    def test_shows_top_performers(self, tmp_path):
        """Should show signal performance stats when signals are evaluated."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        mock_tracker = Mock()
        mock_tracker.get_all_stats.return_value = {
            "total_signals": 10,
            "evaluated": 5,
            "pending": 5,
            "avg_return": 15.5,
            "win_rate": 80,
        }

        report = analytics.generate_weekly_report(mock_tracker)

        # Check for performance stats in report
        assert "Total Symbols Tracked: 10" in report
        assert "Average Return: 15.5%" in report
        assert "Win Rate: 80.0%" in report

    def test_handles_no_evaluated_signals(self, tmp_path):
        """Should handle case where no signals have been evaluated."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        mock_tracker = Mock()
        mock_tracker.get_all_stats.return_value = {
            "total_signals": 5,
            "evaluated": 0,
            "pending": 5,
            "avg_return": None,
            "win_rate": None,
        }

        report = analytics.generate_weekly_report(mock_tracker)

        assert "No signals evaluated yet" in report


class TestShouldSendWeeklyReport:
    """Tests for should_send_weekly_report method."""

    def test_returns_true_when_no_previous_report(self, tmp_path):
        """Should return True when no report has been sent."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        assert analytics.should_send_weekly_report() is True

    def test_returns_false_when_recent_report_sent(self, tmp_path):
        """Should return False when report sent less than 7 days ago."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        # Mark report sent 3 days ago
        recent = (datetime.now() - timedelta(days=3)).isoformat()
        analytics.data["last_report_date"] = recent

        assert analytics.should_send_weekly_report() is False

    def test_returns_true_after_7_days(self, tmp_path):
        """Should return True when 7+ days since last report."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        # Mark report sent 8 days ago
        old = (datetime.now() - timedelta(days=8)).isoformat()
        analytics.data["last_report_date"] = old

        assert analytics.should_send_weekly_report() is True


class TestMarkReportSent:
    """Tests for mark_report_sent method."""

    def test_updates_last_report_date(self, tmp_path):
        """Should update last_report_date to now."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.mark_report_sent()

        assert analytics.data["last_report_date"] is not None
        # Verify it's a recent timestamp
        report_time = datetime.fromisoformat(analytics.data["last_report_date"])
        assert (datetime.now() - report_time).total_seconds() < 5

    def test_persists_to_file(self, tmp_path):
        """Should save to file after marking report sent."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.mark_report_sent()

        saved_data = json.loads(data_file.read_text())
        assert saved_data["last_report_date"] is not None


class TestSaveDataErrorHandling:
    """Tests for _save_data error handling."""

    def test_handles_permission_error(self, tmp_path):
        """Should handle permission errors gracefully."""
        data_file = tmp_path / "readonly" / "analytics.json"
        # Don't create parent directory - will cause write error
        analytics = Analytics(data_file=str(data_file))

        # This should not raise, just log error
        analytics.record_market_scan(found=10, added=1, updated=1)

        # Data is still in memory
        assert len(analytics.data["market_scans"]) == 1


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_handles_very_large_numbers(self, tmp_path):
        """Should handle very large scan numbers."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_market_scan(found=1_000_000, added=50_000, updated=100_000)

        assert analytics.data["market_scans"][0]["found"] == 1_000_000

    def test_handles_special_characters_in_symbol(self, tmp_path):
        """Should handle symbols with special characters."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_alert_sent(symbol="BRK.B", price=350.00)

        assert analytics.data["alerts_sent"][0]["symbol"] == "BRK.B"

    def test_handles_negative_price(self, tmp_path):
        """Should handle edge case of negative price (shouldn't happen but be safe)."""
        data_file = tmp_path / "analytics.json"
        analytics = Analytics(data_file=str(data_file))

        analytics.record_alert_sent(symbol="TEST", price=-10.00)

        assert analytics.data["alerts_sent"][0]["price"] == -10.00

    def test_multiple_instances_same_file(self, tmp_path):
        """Should handle multiple instances reading same file."""
        data_file = tmp_path / "analytics.json"

        analytics1 = Analytics(data_file=str(data_file))
        analytics1.record_market_scan(found=100, added=5, updated=10)

        analytics2 = Analytics(data_file=str(data_file))

        # Second instance should see the saved data
        assert len(analytics2.data["market_scans"]) == 1
