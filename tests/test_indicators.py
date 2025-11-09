"""Unit tests for technical indicators"""

import pytest
import pandas as pd
import numpy as np
from src.indicators import rsi, stochastic_rsi, stoch_rsi_buy


class TestRSI:
    """Tests for RSI calculation"""
    
    def test_rsi_basic(self):
        """Test basic RSI calculation"""
        # Create simple uptrend data
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                          110, 111, 112, 113, 114, 115, 116, 117, 118, 119])
        
        result = rsi(prices, period=14)
        
        # RSI should be high (>50) in uptrend
        assert result.iloc[-1] > 50, "RSI should be > 50 in uptrend"
        assert result.iloc[-1] <= 100, "RSI should not exceed 100"
    
    def test_rsi_downtrend(self):
        """Test RSI in downtrend"""
        prices = pd.Series([120, 119, 118, 117, 116, 115, 114, 113, 112, 111,
                          110, 109, 108, 107, 106, 105, 104, 103, 102, 101])
        
        result = rsi(prices, period=14)
        
        # RSI should be low (<50) in downtrend
        assert result.iloc[-1] < 50, "RSI should be < 50 in downtrend"
        assert result.iloc[-1] >= 0, "RSI should not be negative"
    
    def test_rsi_zero_division_protection(self):
        """Test that RSI handles zero division (all gains, no losses)"""
        # All gains
        prices = pd.Series([100 + i for i in range(20)])
        
        # Should not raise ZeroDivisionError
        result = rsi(prices, period=14)
        
        # RSI should be 100 (or very close)
        assert result.iloc[-1] > 95, "RSI should be near 100 with only gains"
    
    def test_rsi_all_losses(self):
        """Test RSI with all losses"""
        prices = pd.Series([100 - i for i in range(20)])
        
        result = rsi(prices, period=14)
        
        # RSI should be 0 (or very close)
        assert result.iloc[-1] < 5, "RSI should be near 0 with only losses"
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data points"""
        prices = pd.Series([100, 101, 102])  # Less than period=14
        
        result = rsi(prices, period=14)
        
        # Should return NaN for most values
        assert result.isna().sum() >= len(result) - 1


class TestStochasticRSI:
    """Tests for Stochastic RSI calculation"""
    
    def test_stoch_rsi_structure(self):
        """Test that stochastic RSI returns correct structure"""
        prices = pd.Series([100 + i + np.sin(i) * 5 for i in range(50)])
        
        result = stochastic_rsi(prices, rsi_period=14, stoch_period=14, k=3, d=3)
        
        # Should return DataFrame with rsi, k, d columns
        assert isinstance(result, pd.DataFrame)
        assert 'rsi' in result.columns
        assert 'k' in result.columns
        assert 'd' in result.columns
        assert len(result) == len(prices)
    
    def test_stoch_rsi_range(self):
        """Test that Stochastic RSI values are in valid range"""
        prices = pd.Series([100 + i + np.sin(i) * 10 for i in range(100)])
        
        result = stochastic_rsi(prices)
        
        # K and D lines should be between 0 and 1
        valid_k = result['k'].dropna()
        valid_d = result['d'].dropna()
        
        assert (valid_k >= 0).all() and (valid_k <= 1).all(), "K line should be 0-1"
        assert (valid_d >= 0).all() and (valid_d <= 1).all(), "D line should be 0-1"
    
    def test_stoch_rsi_zero_division(self):
        """Test stochastic RSI handles zero division"""
        # Constant prices (zero volatility)
        prices = pd.Series([100] * 50)
        
        # Should not raise exception
        result = stochastic_rsi(prices)
        
        # Should have values (may be NaN or handled values)
        assert len(result) == 50


class TestStochRSIBuy:
    """Tests for Stochastic RSI buy signal detection"""
    
    def test_buy_signal_cross_up(self):
        """Test buy signal when K crosses above D in oversold"""
        # Create a cross-up scenario in oversold zone
        # Key: Cross must happen while BOTH lines are still in oversold (<0.2)
        df = pd.DataFrame({
            'rsi': [30, 30, 30, 30, 30],
            'k': [0.12, 0.14, 0.16, 0.18, 0.19],  # K rising slowly
            'd': [0.17, 0.17, 0.17, 0.17, 0.16]   # D stable then falls - creates cross at row 4
        })
        
        result = stoch_rsi_buy(df, lookback_days=3)
        assert result == True, "Should detect cross-up in oversold"
    
    def test_no_signal_cross_down(self):
        """Test no signal when K crosses below D"""
        df = pd.DataFrame({
            'rsi': [70, 70, 70, 70],
            'k': [0.80, 0.75, 0.70, 0.65],  # K falling
            'd': [0.70, 0.72, 0.74, 0.76]   # D rising - cross down
        })
        
        result = stoch_rsi_buy(df, lookback_days=3)
        assert result == False, "Should not signal on cross-down"
    
    def test_no_signal_not_oversold(self):
        """Test no signal when cross happens but not in oversold"""
        df = pd.DataFrame({
            'rsi': [70, 70, 70, 70],
            'k': [0.50, 0.55, 0.60, 0.65],  # K rising
            'd': [0.60, 0.60, 0.59, 0.58]   # D falling - creates cross
        })
        
        result = stoch_rsi_buy(df, lookback_days=3)
        assert result == False, "Should not signal if not oversold (k,d > 0.2)"
    
    def test_insufficient_data(self):
        """Test with insufficient data points"""
        df = pd.DataFrame({
            'rsi': [30, 30],
            'k': [0.15, 0.25],
            'd': [0.20, 0.18]
        })
        
        # lookback_days=3 needs at least 5 rows (3 + 2)
        result = stoch_rsi_buy(df, lookback_days=3)
        assert result == False, "Should return False with insufficient data"
    
    def test_with_nan_values(self):
        """Test handling of NaN values"""
        df = pd.DataFrame({
            'rsi': [np.nan, 30, 30, 30],
            'k': [np.nan, 0.15, 0.19, 0.22],
            'd': [np.nan, 0.20, 0.19, 0.18]
        })
        
        # Should handle NaN gracefully
        result = stoch_rsi_buy(df, lookback_days=2)
        # Should either detect signal or handle NaN properly
        assert isinstance(result, bool)
    
    def test_lookback_parameter(self):
        """Test different lookback periods"""
        # Signal in last day - K crosses above D
        # Row 9: k=0.24 > d=0.20, previous row 8: k=0.21 < d=0.21
        df_recent = pd.DataFrame({
            'rsi': [30] * 10,
            'k': [0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.18, 0.19, 0.21],
            'd': [0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.20, 0.19]
        })
        
        # Should detect with lookback=3 (cross at row 9, within last 3 days)
        assert stoch_rsi_buy(df_recent, lookback_days=3) == True
        
        # Signal more than 3 days ago - cross happened at row 2
        df_old = pd.DataFrame({
            'rsi': [30] * 10,
            'k': [0.15, 0.18, 0.21, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50],
            'd': [0.20, 0.20, 0.19, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50]
        })
        
        # Should NOT detect with lookback=3 (signal is at index -7)
        assert stoch_rsi_buy(df_old, lookback_days=3) == False
    
    def test_exact_threshold_oversold(self):
        """Test exact threshold at k=0.2, d=0.2"""
        # Exactly at threshold
        df = pd.DataFrame({
            'rsi': [30] * 5,
            'k': [0.19, 0.19, 0.22, 0.25, 0.28],
            'd': [0.21, 0.21, 0.20, 0.19, 0.18]
        })
        
        # Should detect (one line below 0.2)
        assert stoch_rsi_buy(df, lookback_days=3) == True


class TestEdgeCases:
    """Edge cases for indicators"""
    
    def test_empty_series(self):
        """Test with empty data"""
        empty = pd.Series([])
        
        result = rsi(empty)
        assert len(result) == 0
    
    def test_single_value(self):
        """Test with single value"""
        single = pd.Series([100])
        
        result = rsi(single, period=14)
        assert len(result) == 1
        assert pd.isna(result.iloc[0])
    
    def test_extreme_volatility(self):
        """Test with extreme price swings"""
        volatile = pd.Series([100, 200, 50, 150, 75, 175, 25] * 5)
        
        # Should not crash
        result = stochastic_rsi(volatile)
        assert len(result) == len(volatile)
    
    def test_negative_prices(self):
        """Test with negative prices (invalid but should handle)"""
        negative = pd.Series([-100, -101, -102, -103])
        
        # Should handle without exception
        result = rsi(negative, period=2)
        assert len(result) == 4
