"""
Tests for market scanner functionality (Stage 0)
"""

import pytest
import pandas as pd
import numpy as np
from src.indicators import bollinger_bands
from src.market_symbols import get_sp500_symbols, get_market_cap_threshold


class TestBollingerBands:
    """Test Bollinger Bands indicator calculations"""
    
    def test_bollinger_bands_basic(self):
        """Test basic Bollinger Bands calculation"""
        # Create simple price series
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                           110, 108, 111, 113, 112, 114, 116, 115, 117, 119,
                           120, 118, 121, 123, 122])
        
        bb = bollinger_bands(prices, period=20, std_dev=2.0)
        
        # Check structure
        assert 'upper' in bb
        assert 'middle' in bb
        assert 'lower' in bb
        
        # Check types
        assert isinstance(bb['upper'], pd.Series)
        assert isinstance(bb['middle'], pd.Series)
        assert isinstance(bb['lower'], pd.Series)
        
        # Check length
        assert len(bb['upper']) == len(prices)
        assert len(bb['middle']) == len(prices)
        assert len(bb['lower']) == len(prices)
    
    def test_bollinger_bands_ordering(self):
        """Test that upper > middle > lower"""
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                           110, 108, 111, 113, 112, 114, 116, 115, 117, 119,
                           120, 118, 121, 123, 122])
        
        bb = bollinger_bands(prices, period=20, std_dev=2.0)
        
        # Last value should have proper ordering
        last_upper = bb['upper'].iloc[-1]
        last_middle = bb['middle'].iloc[-1]
        last_lower = bb['lower'].iloc[-1]
        
        assert last_upper > last_middle
        assert last_middle > last_lower
    
    def test_bollinger_bands_middle_is_sma(self):
        """Test that middle band equals SMA"""
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                           110, 108, 111, 113, 112, 114, 116, 115, 117, 119,
                           120, 118, 121, 123, 122])
        
        bb = bollinger_bands(prices, period=20, std_dev=2.0)
        
        # Middle band should equal 20-period SMA
        sma_20 = prices.rolling(window=20).mean()
        
        # Compare last value (first 19 will be NaN)
        assert abs(bb['middle'].iloc[-1] - sma_20.iloc[-1]) < 0.01
    
    def test_bollinger_bands_custom_period(self):
        """Test Bollinger Bands with custom period"""
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                           110, 108, 111, 113, 112, 114, 116, 115, 117, 119,
                           120, 118, 121, 123, 122])
        
        bb = bollinger_bands(prices, period=10, std_dev=2.0)
        
        # Check that it returns valid data
        assert not pd.isna(bb['middle'].iloc[-1])
        assert not pd.isna(bb['upper'].iloc[-1])
        assert not pd.isna(bb['lower'].iloc[-1])
    
    def test_bollinger_bands_price_touches_lower(self):
        """Test scenario where price touches/crosses lower band"""
        # Create data where price drops significantly
        prices = pd.Series([120, 119, 118, 117, 116, 115, 114, 113, 112, 111,
                           110, 109, 108, 107, 106, 105, 104, 103, 102, 101,
                           100, 99, 98, 97, 96])
        
        bb = bollinger_bands(prices, period=20, std_dev=2.0)
        
        # In downtrend, lower band should move down too
        # Test that bands are calculated correctly (lower < middle < upper)
        last_lower = bb['lower'].iloc[-1]
        last_middle = bb['middle'].iloc[-1]
        last_upper = bb['upper'].iloc[-1]
        
        assert last_lower < last_middle < last_upper
        
        # Lower band should be significantly below middle in trending market
        assert (last_middle - last_lower) > 2  # At least $2 difference


class TestMarketSymbols:
    """Test market symbol list functionality"""
    
    def test_get_sp500_symbols_returns_list(self):
        """Test that S&P 500 symbols are returned as list"""
        symbols = get_sp500_symbols()
        
        assert isinstance(symbols, list)
        assert len(symbols) > 0
    
    def test_get_sp500_symbols_contains_common_stocks(self):
        """Test that list contains well-known S&P 500 stocks"""
        symbols = get_sp500_symbols()
        
        # Check for major stocks
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'GOOGL' in symbols
        assert 'AMZN' in symbols
        assert 'TSLA' in symbols
    
    def test_get_sp500_symbols_no_duplicates(self):
        """Test that symbol list has no duplicates"""
        symbols = get_sp500_symbols()
        
        # Check for duplicates
        assert len(symbols) == len(set(symbols))
    
    def test_get_sp500_symbols_count(self):
        """Test that we have approximately 500 symbols"""
        symbols = get_sp500_symbols()
        
        # S&P 500 should have around 500-505 symbols
        assert 450 <= len(symbols) <= 550
    
    def test_get_market_cap_threshold(self):
        """Test market cap threshold value"""
        threshold = get_market_cap_threshold()
        
        assert threshold == 50_000_000_000  # 50 billion
        assert isinstance(threshold, (int, float))


class TestMarketFilterScenarios:
    """Test realistic market filter scenarios"""
    
    def test_oversold_scenario_data_structure(self):
        """Test that we can create data matching all filters"""
        # Create a scenario matching all filters:
        # - Large market cap (>50B)
        # - Stoch RSI D < 20
        # - Price < BB Lower
        # - MFI <= 40
        
        # This is a valid scenario structure test
        data = {
            'market_cap': 60_000_000_000,  # 60B
            'stoch_rsi_d': 15.0,
            'stoch_rsi_k': 18.0,
            'price': 95.0,
            'bb_lower': 97.0,  # Price below BB lower
            'mfi': 35.0
        }
        
        # All conditions should pass
        assert data['market_cap'] >= get_market_cap_threshold()
        assert data['stoch_rsi_d'] < 20
        assert data['price'] < data['bb_lower']
        assert data['mfi'] <= 40
    
    def test_filter_rejection_scenarios(self):
        """Test various rejection scenarios"""
        
        # Scenario 1: Market cap too low
        data1 = {
            'market_cap': 30_000_000_000,  # 30B < 50B
            'stoch_rsi_d': 15.0,
            'price': 95.0,
            'bb_lower': 97.0,
            'mfi': 35.0
        }
        assert data1['market_cap'] < get_market_cap_threshold()
        
        # Scenario 2: Stoch RSI not oversold
        data2 = {
            'market_cap': 60_000_000_000,
            'stoch_rsi_d': 45.0,  # > 20
            'price': 95.0,
            'bb_lower': 97.0,
            'mfi': 35.0
        }
        assert data2['stoch_rsi_d'] >= 20
        
        # Scenario 3: Price above BB lower
        data3 = {
            'market_cap': 60_000_000_000,
            'stoch_rsi_d': 15.0,
            'price': 100.0,
            'bb_lower': 97.0,  # Price > BB lower
            'mfi': 35.0
        }
        assert data3['price'] >= data3['bb_lower']
        
        # Scenario 4: MFI too high
        data4 = {
            'market_cap': 60_000_000_000,
            'stoch_rsi_d': 15.0,
            'price': 95.0,
            'bb_lower': 97.0,
            'mfi': 55.0  # > 40
        }
        assert data4['mfi'] > 40


class TestBollingerBandsEdgeCases:
    """Test edge cases for Bollinger Bands"""
    
    def test_bollinger_bands_insufficient_data(self):
        """Test BB with insufficient data"""
        prices = pd.Series([100, 102, 101])  # Only 3 points
        
        bb = bollinger_bands(prices, period=20, std_dev=2.0)
        
        # Should return NaN for insufficient data
        assert pd.isna(bb['middle'].iloc[-1])
        assert pd.isna(bb['upper'].iloc[-1])
        assert pd.isna(bb['lower'].iloc[-1])
    
    def test_bollinger_bands_flat_prices(self):
        """Test BB with flat price series"""
        prices = pd.Series([100] * 25)  # Flat prices
        
        bb = bollinger_bands(prices, period=20, std_dev=2.0)
        
        # With zero volatility, bands should converge to price
        assert abs(bb['middle'].iloc[-1] - 100) < 0.01
        assert abs(bb['upper'].iloc[-1] - 100) < 0.01
        assert abs(bb['lower'].iloc[-1] - 100) < 0.01
    
    def test_bollinger_bands_high_volatility(self):
        """Test BB with high volatility"""
        # Create volatile price series
        np.random.seed(42)
        base = 100
        prices = pd.Series([base + np.random.uniform(-10, 10) for _ in range(30)])
        
        bb = bollinger_bands(prices, period=20, std_dev=2.0)
        
        # With high volatility, bands should be wider apart
        last_upper = bb['upper'].iloc[-1]
        last_lower = bb['lower'].iloc[-1]
        band_width = last_upper - last_lower
        
        # Band width should be significant
        assert band_width > 5  # At least $5 difference
