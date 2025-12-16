"""
Mini E2E Integration Test: Full Signal Flow

This test validates the complete signal flow:
    fetch data → apply filters → write signal to Notion → mark sent → telegram send

All external dependencies are mocked - no network calls.
Each step is clearly labeled for easy debugging.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import responses

from src.notion_http import NotionHTTPClient
from src.notion_models import NotionConfig, SignalData
from src.notion_repo import NotionRepository
from src.signal_tracker import SignalTracker
from src.telegram_client import TelegramClient


@pytest.fixture
def mock_ohlc_data():
    """Generate mock OHLC data that will pass indicator filters."""
    dates = pd.date_range(end=datetime.now(), periods=50, freq='D')

    # Create data that produces oversold RSI/Stoch signals
    # Price dropping then recovering = bullish reversal setup
    prices = [100 - i * 0.5 for i in range(40)]  # Downtrend
    prices += [82 + i * 0.3 for i in range(10)]  # Recovery

    # Create DataFrame with Date as a column (not index)
    # This matches what daily_ohlc returns after reset_index()
    df = pd.DataFrame({
        'Date': dates,
        'Open': prices,
        'High': [p * 1.01 for p in prices],
        'Low': [p * 0.99 for p in prices],
        'Close': prices,
        'Volume': [1000000] * 50,
    })

    return df


@pytest.fixture
def mock_history_data():
    """Generate mock history data as returned by yfinance.Ticker.history()."""
    dates = pd.date_range(end=datetime.now(), periods=50, freq='D')

    prices = [100 - i * 0.5 for i in range(40)]
    prices += [82 + i * 0.3 for i in range(10)]

    # yfinance returns DataFrame with DatetimeIndex named 'Date'
    df = pd.DataFrame({
        'Open': prices,
        'High': [p * 1.01 for p in prices],
        'Low': [p * 0.99 for p in prices],
        'Close': prices,
        'Volume': [1000000] * 50,
    }, index=dates)
    df.index.name = 'Date'

    return df


@pytest.fixture
def notion_config():
    """Test Notion configuration."""
    return NotionConfig(
        api_key="test_notion_api_key",
        database_id="test_watchlist_db",
        signals_database_id="test_signals_db",
        buy_database_id="test_buy_db",
        max_retries=1,
        backoff_factor=0.01,
        timeout=5,
    )


@pytest.fixture
def signal_tracker(tmp_path):
    """Create a fresh signal tracker for testing."""
    return SignalTracker(data_file=str(tmp_path / "signals.json"))


class TestMiniE2ESignalFlow:
    """
    Mini E2E test that validates the complete signal pipeline.

    This is a single test that walks through all steps of the signal flow.
    Each step is clearly labeled with assertions and logging for debugging.
    """

    @responses.activate
    def test_full_signal_flow_fetch_filter_write_notify(
        self, mock_ohlc_data, mock_history_data, notion_config, signal_tracker, tmp_path
    ):
        """
        Full signal flow: fetch → filter → write to Notion → track → notify.

        Steps:
        1. FETCH: Get OHLC data (mocked)
        2. FILTER: Apply technical indicators and check signals
        3. WRITE: Add signal to Notion database (mocked API)
        4. TRACK: Record alert in signal tracker
        5. NOTIFY: Send Telegram notification (mocked)
        """
        symbol = "TEST"

        # =====================================================================
        # STEP 1: FETCH DATA
        # =====================================================================
        print("\n📊 STEP 1: Fetching OHLC data...")

        with patch('src.data_source_yfinance.yf.Ticker') as mock_ticker:
            mock_instance = MagicMock()
            # Return data with DatetimeIndex that matches yfinance format
            mock_instance.history.return_value = mock_history_data
            mock_ticker.return_value = mock_instance

            from src.data_source_yfinance import daily_ohlc
            df = daily_ohlc(symbol, days=50)

        # Verify data fetched
        assert df is not None, "STEP 1 FAILED: No data returned from data source"
        assert len(df) >= 30, f"STEP 1 FAILED: Insufficient data rows ({len(df)})"
        assert 'Close' in df.columns, "STEP 1 FAILED: Missing 'Close' column"
        print(f"   ✅ Fetched {len(df)} rows of OHLC data")

        # =====================================================================
        # STEP 2: APPLY FILTERS / CALCULATE INDICATORS
        # =====================================================================
        print("\n📈 STEP 2: Calculating technical indicators...")

        # Calculate indicators using correct function names
        from src.indicators import mfi as calc_mfi
        from src.indicators import rsi as calc_rsi
        from src.indicators import stochastic_rsi

        rsi_series = calc_rsi(df['Close'], period=14)
        stoch_df = stochastic_rsi(df['Close'], rsi_period=14, stoch_period=14)
        mfi_series = calc_mfi(df, period=14)

        # Verify indicators calculated
        assert rsi_series is not None, "STEP 2 FAILED: RSI calculation returned None"
        assert stoch_df is not None, "STEP 2 FAILED: Stoch RSI calculation returned None"
        assert mfi_series is not None, "STEP 2 FAILED: MFI calculation returned None"

        latest_rsi = float(rsi_series.iloc[-1])
        latest_k = float(stoch_df['k'].iloc[-1])
        latest_d = float(stoch_df['d'].iloc[-1])
        latest_mfi = float(mfi_series.iloc[-1])
        latest_price = float(df['Close'].iloc[-1])

        print(f"   RSI: {latest_rsi:.2f}")
        print(f"   Stoch K: {latest_k:.2f}, D: {latest_d:.2f}")
        print(f"   MFI: {latest_mfi:.2f}")
        print(f"   Price: ${latest_price:.2f}")
        print("   ✅ All indicators calculated")

        # Build signal data
        signal_data = {
            "symbol": symbol,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "rsi": latest_rsi,
            "stoch_k": latest_k,
            "stoch_d": latest_d,
            "mfi": latest_mfi,
            "price": latest_price,
        }

        # =====================================================================
        # STEP 3: WRITE SIGNAL TO NOTION
        # =====================================================================
        print("\n💾 STEP 3: Writing signal to Notion database...")

        # Reset HTTP client session
        NotionHTTPClient._session = None

        # Mock Notion API: schema endpoint
        responses.add(
            responses.GET,
            f"https://api.notion.com/v1/databases/{notion_config.signals_database_id}",
            json={
                "properties": {
                    "Symbol": {"type": "title"},
                    "Date": {"type": "date"},
                    "RSI": {"type": "number"},
                    "Stoch K": {"type": "number"},
                    "Stoch D": {"type": "number"},
                    "MFI": {"type": "number"},
                    "Price": {"type": "number"},
                }
            },
            status=200,
        )

        # Mock Notion API: create page endpoint
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={"id": "new_signal_page_123", "object": "page"},
            status=200,
        )

        # Create repository and add signal
        repo = NotionRepository(notion_config)
        signal = SignalData(
            symbol=symbol,
            date=signal_data["date"],
            rsi=signal_data["rsi"],
            stoch_k=signal_data["stoch_k"],
            stoch_d=signal_data["stoch_d"],
        )

        write_success = repo.add_to_signals(signal)

        # Verify write
        assert write_success is True, "STEP 3 FAILED: Failed to write signal to Notion"

        # Verify API was called correctly
        assert len(responses.calls) >= 1, "STEP 3 FAILED: No API calls made to Notion"

        # Check the page creation call
        page_creation_calls = [c for c in responses.calls if "pages" in c.request.url]
        assert len(page_creation_calls) == 1, "STEP 3 FAILED: Page creation not called"

        print("   ✅ Signal written to Notion (page_id: new_signal_page_123)")

        # =====================================================================
        # STEP 4: RECORD ALERT IN SIGNAL TRACKER
        # =====================================================================
        print("\n📝 STEP 4: Recording alert in signal tracker...")

        # Check if we can send alert (no limits hit)
        can_send, reason = signal_tracker.can_send_alert(symbol)
        assert can_send is True, f"STEP 4 FAILED: Cannot send alert - {reason}"

        # Record the alert
        signal_tracker.record_alert(symbol, signal_data)

        # Verify recorded
        today = datetime.now().date().isoformat()
        daily_count = signal_tracker.data["daily_alerts"].get(today, 0)
        assert daily_count == 1, f"STEP 4 FAILED: Daily count is {daily_count}, expected 1"

        # Verify symbol is now in cooldown
        assert symbol in signal_tracker.data["symbol_cooldown"], \
            "STEP 4 FAILED: Symbol not added to cooldown"

        # Verify signal history updated
        assert len(signal_tracker.data["signal_history"]) == 1, \
            "STEP 4 FAILED: Signal not added to history"

        recorded_signal = signal_tracker.data["signal_history"][0]
        assert recorded_signal["symbol"] == symbol, "STEP 4 FAILED: Wrong symbol recorded"

        print(f"   Daily alerts: {daily_count}")
        print(f"   Symbol in cooldown: {symbol}")
        print("   ✅ Alert recorded successfully")

        # =====================================================================
        # STEP 5: SEND TELEGRAM NOTIFICATION
        # =====================================================================
        print("\n📱 STEP 5: Sending Telegram notification...")

        # Reset Telegram session
        TelegramClient._session = None

        # Mock Telegram API
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            json={"ok": True, "result": {"message_id": 12345}},
            status=200,
        )

        # Create client and send
        telegram = TelegramClient(token="test_bot_token", chat_id="test_chat_id")

        message = f"""🚨 *Signal Alert: {symbol}*

📊 Indicators:
• RSI: {latest_rsi:.1f}
• Stoch K/D: {latest_k:.1f}/{latest_d:.1f}
• MFI: {latest_mfi:.1f}

💰 Price: ${latest_price:.2f}
📅 Date: {signal_data['date']}
"""

        send_success = telegram.send(message)

        # Verify sent
        assert send_success is True, "STEP 5 FAILED: Telegram send returned False"

        # Verify API was called
        telegram_calls = [c for c in responses.calls if "telegram" in c.request.url]
        assert len(telegram_calls) == 1, "STEP 5 FAILED: Telegram API not called"

        print("   ✅ Telegram notification sent (message_id: 12345)")

        # =====================================================================
        # STEP 6: VERIFY IDEMPOTENCY (same signal should be blocked)
        # =====================================================================
        print("\n🔒 STEP 6: Verifying idempotency (duplicate prevention)...")

        # Try to send another alert for same symbol
        can_send_again, cooldown_reason = signal_tracker.can_send_alert(symbol)

        assert can_send_again is False, \
            "STEP 6 FAILED: Same symbol should be blocked by cooldown"
        assert "cooldown" in cooldown_reason.lower(), \
            f"STEP 6 FAILED: Wrong rejection reason - {cooldown_reason}"

        print(f"   Duplicate blocked: {cooldown_reason}")
        print("   ✅ Idempotency verified")

        # =====================================================================
        # FINAL SUMMARY
        # =====================================================================
        print("\n" + "=" * 60)
        print("✅ MINI E2E TEST PASSED - Full signal flow validated!")
        print("=" * 60)
        print(f"""
Summary:
  • Symbol: {symbol}
  • Data rows fetched: {len(df)}
  • Indicators calculated: RSI, Stoch RSI, MFI
  • Notion write: SUCCESS
  • Signal tracked: YES
  • Telegram sent: SUCCESS
  • Duplicate prevention: WORKING
""")


class TestMiniE2EEdgeCases:
    """Edge case tests for the signal flow."""

    @responses.activate
    def test_notion_failure_does_not_crash_flow(self, notion_config, signal_tracker):
        """
        Test graceful handling when Notion API fails.

        The flow should continue and not crash, even if Notion write fails.
        """
        print("\n🔴 Testing Notion failure handling...")

        NotionHTTPClient._session = None

        # Mock Notion API failure
        responses.add(
            responses.GET,
            f"https://api.notion.com/v1/databases/{notion_config.signals_database_id}",
            json={"error": "unauthorized"},
            status=401,
        )

        repo = NotionRepository(notion_config)
        signal = SignalData(symbol="FAIL", date="2024-12-16", rsi=25.0)

        # Should return False, not raise
        result = repo.add_to_signals(signal)

        assert result is False, "Expected False when Notion fails"
        print("   ✅ Notion failure handled gracefully")

    @responses.activate
    def test_telegram_failure_does_not_block_tracking(self, signal_tracker):
        """
        Test that signal is tracked even if Telegram notification fails.
        """
        print("\n🔴 Testing Telegram failure handling...")

        TelegramClient._session = None

        # Mock Telegram API failure
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest_bot_token/sendMessage",
            json={"ok": False, "description": "Bad Request"},
            status=400,
        )

        # Record signal first
        signal_tracker.record_alert("TRACK_ME", {"price": 100.0})

        # Verify signal is tracked
        assert len(signal_tracker.data["signal_history"]) == 1, \
            "Signal should be tracked regardless of Telegram status"

        # Now try to send Telegram (will fail)
        telegram = TelegramClient(token="test_bot_token", chat_id="test_chat")
        result = telegram.send("Test", critical=False)

        # Should return False, not crash
        assert result is False, "Expected False when Telegram fails"

        # Signal should still be tracked
        assert len(signal_tracker.data["signal_history"]) == 1, \
            "Signal tracking should not be affected by Telegram failure"

        print("   ✅ Telegram failure handled gracefully")
        print("   ✅ Signal still tracked despite notification failure")
