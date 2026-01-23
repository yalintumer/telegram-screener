"""Tests for filters module."""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.filters import (
    check_market_filter,
    check_signal_criteria,
    check_wavetrend_signal,
    get_wavetrend_values,
)


class TestCheckMarketFilter:
    """Tests for check_market_filter function."""

    @pytest.fixture
    def mock_price_data(self):
        """Create mock price data DataFrame."""
        np.random.seed(42)
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        base_price = 150.0

        # Generate realistic OHLCV data
        close = base_price + np.cumsum(np.random.randn(100) * 2)
        high = close + np.abs(np.random.randn(100) * 1)
        low = close - np.abs(np.random.randn(100) * 1)
        open_ = close + np.random.randn(100) * 0.5
        volume = np.random.randint(1000000, 10000000, 100)

        return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=dates)

    def test_returns_none_for_insufficient_data(self):
        """Should return None when data is insufficient."""
        with patch("src.filters.daily_ohlc", return_value=None):
            result = check_market_filter("TEST")

        assert result is None

    def test_returns_none_for_short_data(self):
        """Should return None when data has less than 30 rows."""
        short_df = pd.DataFrame(
            {"Open": [100] * 20, "High": [101] * 20, "Low": [99] * 20, "Close": [100] * 20, "Volume": [1000000] * 20}
        )

        with patch("src.filters.daily_ohlc", return_value=short_df):
            result = check_market_filter("TEST")

        assert result is None

    def test_fails_on_low_market_cap(self, mock_price_data):
        """Should fail when market cap is below threshold."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"marketCap": 10_000_000_000}  # 10B < 50B threshold

        with (
            patch("src.filters.daily_ohlc", return_value=mock_price_data),
            patch("src.filters.yf.Ticker", return_value=mock_ticker),
        ):
            result = check_market_filter("TEST")

        assert result is not None
        assert result["passed"] is False
        assert result["reason"] == "market_cap_too_low"

    def test_uses_cache_when_available(self, mock_price_data):
        """Should use cache for market cap when available."""
        mock_cache = Mock()
        mock_cache.get.return_value = 100_000_000_000  # 100B (passes threshold)

        # Make indicators fail so we can check cache was used
        with (
            patch("src.filters.daily_ohlc", return_value=mock_price_data),
            patch("src.filters.stochastic_rsi") as mock_stoch,
        ):
            # Return oversold values
            mock_stoch.return_value = pd.DataFrame(
                {
                    "k": [50.0] * 100,  # Not oversold
                    "d": [50.0] * 100,  # Not oversold (>20)
                }
            )
            result = check_market_filter("TEST", cache=mock_cache)

        mock_cache.get.assert_called_once_with("TEST")
        # Result should fail on stoch_d (not oversold)
        assert result is not None
        assert result["passed"] is False
        assert "stoch" in result["reason"]

    def test_returns_dict_with_passed_key(self, mock_price_data):
        """Result should always have 'passed' key when not None."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"marketCap": 100_000_000_000}

        with (
            patch("src.filters.daily_ohlc", return_value=mock_price_data),
            patch("src.filters.yf.Ticker", return_value=mock_ticker),
        ):
            result = check_market_filter("TEST")

        assert result is not None
        assert "passed" in result


class TestCheckWavetrendSignal:
    """Tests for check_wavetrend_signal function."""

    def test_returns_false_for_no_data(self):
        """Should return False when no data available."""
        with (
            patch("src.filters.hourly_4h_ohlc", return_value=None),
            patch("src.filters.daily_ohlc", return_value=None),
        ):
            result = check_wavetrend_signal("TEST")

        assert result is False

    def test_returns_false_for_insufficient_data(self):
        """Should return False when data is insufficient."""
        short_df = pd.DataFrame(
            {"Open": [100] * 20, "High": [101] * 20, "Low": [99] * 20, "Close": [100] * 20, "Volume": [1000000] * 20}
        )

        with (
            patch("src.filters.hourly_4h_ohlc", return_value=short_df),
            patch("src.filters.daily_ohlc", return_value=short_df),
        ):
            result = check_wavetrend_signal("TEST")

        assert result is False

    def test_returns_bool(self):
        """Should always return a boolean."""
        with (
            patch("src.filters.hourly_4h_ohlc", return_value=None),
            patch("src.filters.daily_ohlc", return_value=None),
        ):
            result = check_wavetrend_signal("TEST")

        assert isinstance(result, bool)

    def test_multi_timeframe_disabled_skips_weekly(self):
        """Should skip weekly check when use_multi_timeframe=False."""
        mock_df = pd.DataFrame(
            {"Open": [100] * 50, "High": [101] * 50, "Low": [99] * 50, "Close": [100] * 50, "Volume": [1000000] * 50}
        )

        with (
            patch("src.filters.hourly_4h_ohlc", return_value=mock_df),
            patch("src.filters.daily_ohlc", return_value=mock_df),
            patch("src.filters.weekly_ohlc") as mock_weekly,
            patch("src.filters.wavetrend") as mock_wt,
            patch("src.filters.wavetrend_buy", return_value=False),
        ):
            mock_wt.return_value = pd.DataFrame({"wt1": [-60.0] * 50, "wt2": [-65.0] * 50})

            check_wavetrend_signal("TEST", use_multi_timeframe=False)

        mock_weekly.assert_not_called()


class TestCheckSignalCriteria:
    """Tests for check_signal_criteria function."""

    def test_returns_none_for_no_data(self):
        """Should return None when no data available."""
        with patch("src.filters.daily_ohlc", return_value=None):
            result = check_signal_criteria("TEST")

        assert result is None

    def test_returns_none_when_no_signal(self):
        """Should return None when no buy signal."""
        mock_df = pd.DataFrame(
            {"Open": [100] * 50, "High": [101] * 50, "Low": [99] * 50, "Close": [100] * 50, "Volume": [1000000] * 50}
        )

        with (
            patch("src.filters.daily_ohlc", return_value=mock_df),
            patch("src.filters.stoch_rsi_buy", return_value=False),
            patch("src.filters.mfi_uptrend", return_value=False),
        ):
            result = check_signal_criteria("TEST")

        assert result is None

    def test_returns_dict_with_signal(self):
        """Should return dict with indicator values when signal found."""
        mock_df = pd.DataFrame(
            {"Open": [100] * 50, "High": [101] * 50, "Low": [99] * 50, "Close": [100] * 50, "Volume": [1000000] * 50}
        )

        mock_stoch = pd.DataFrame({"k": [15.0] * 50, "d": [12.0] * 50})

        mock_mfi = pd.Series([35.0] * 50)

        with (
            patch("src.filters.daily_ohlc", return_value=mock_df),
            patch("src.filters.stochastic_rsi", return_value=mock_stoch),
            patch("src.filters.mfi", return_value=mock_mfi),
            patch("src.filters.stoch_rsi_buy", return_value=True),
            patch("src.filters.mfi_uptrend", return_value=True),
        ):
            result = check_signal_criteria("TEST")

        assert result is not None
        assert "stoch_k" in result
        assert "stoch_d" in result
        assert "mfi" in result
        assert result["mfi_uptrend"] is True


class TestGetWavetrendValues:
    """Tests for get_wavetrend_values function."""

    def test_returns_none_for_no_data(self):
        """Should return None when no data available."""
        with patch("src.filters.daily_ohlc", return_value=None):
            result = get_wavetrend_values("TEST")

        assert result is None

    def test_returns_dict_with_daily_values(self):
        """Should return dict with at least daily WaveTrend values."""
        mock_df = pd.DataFrame(
            {"Open": [100] * 50, "High": [101] * 50, "Low": [99] * 50, "Close": [100] * 50, "Volume": [1000000] * 50}
        )

        mock_wt = pd.DataFrame({"wt1": [-20.0] * 50, "wt2": [-25.0] * 50})

        with (
            patch("src.filters.daily_ohlc", return_value=mock_df),
            patch("src.filters.weekly_ohlc", return_value=None),
            patch("src.filters.wavetrend", return_value=mock_wt),
        ):
            result = get_wavetrend_values("TEST")

        assert result is not None
        assert "daily_wt1" in result
        assert "daily_wt2" in result

    def test_includes_weekly_when_available(self):
        """Should include weekly WaveTrend when data available."""
        mock_df = pd.DataFrame(
            {"Open": [100] * 50, "High": [101] * 50, "Low": [99] * 50, "Close": [100] * 50, "Volume": [1000000] * 50}
        )

        mock_wt = pd.DataFrame({"wt1": [-20.0] * 50, "wt2": [-25.0] * 50})

        with (
            patch("src.filters.daily_ohlc", return_value=mock_df),
            patch("src.filters.weekly_ohlc", return_value=mock_df),
            patch("src.filters.wavetrend", return_value=mock_wt),
        ):
            result = get_wavetrend_values("TEST")

        assert result is not None
        assert "weekly_wt1" in result
