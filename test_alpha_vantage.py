"""
Alpha Vantage test - Hassas teknik indikatörler için
"""
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
import os

API_KEY = os.getenv('ALPHA_VANTAGE_KEY', '')

def test_alpha_vantage():
    if not API_KEY:
        print('❌ ALPHA_VANTAGE_KEY environment variable not set')
        print('   Run: export ALPHA_VANTAGE_KEY=your_key_here')
        return False
        
    print('='*60)
    print('Alpha Vantage Test - MSFT')
    print('='*60)
    
    try:
        ts = TimeSeries(key=API_KEY, output_format='pandas')
        
        # Günlük veri çek
        print('\n📊 Fetching daily data...')
        data, meta_data = ts.get_daily(symbol='MSFT', outputsize='compact')
        
        # VERİ TERSTİR - Eski tarihler önce olmalı
        data = data.sort_index(ascending=True)
        
        print(f'✅ Data fetched: {len(data)} days')
        print(f'\nİlk 5 gün (eskiden yeniye):')
        print(data.head())
        print(f'\nSon 5 gün (en yeni):')
        print(data.tail())
        
        # Son kapanış fiyatı
        last_close = data['4. close'].iloc[-1]  # En son gün
        print(f'\n💰 Son kapanış: ${last_close:.2f}')
        
        # Bollinger Bands hesapla
        print('\n📈 Calculating Bollinger Bands...')
        close_prices = data['4. close']
        sma_20 = close_prices.rolling(window=20).mean()
        std_20 = close_prices.rolling(window=20).std()
        bb_upper = sma_20 + (2 * std_20)
        bb_lower = sma_20 - (2 * std_20)
        
        print(f'\nBollinger Bands (20, 2):')
        print(f'  Upper: ${bb_upper.iloc[-1]:.2f}')
        print(f'  Middle: ${sma_20.iloc[-1]:.2f}')
        print(f'  Lower: ${bb_lower.iloc[-1]:.2f}')
        print(f'  Current: ${last_close:.2f}')
        print(f'  Below lower: {"✅ YES" if last_close < bb_lower.iloc[-1] else "❌ NO"}')
        print(f'  Difference: ${abs(last_close - bb_lower.iloc[-1]):.2f}')
        
        print('\n' + '='*60)
        print('✅ Alpha Vantage works perfectly!')
        print('='*60)
        
        return True
        
    except Exception as e:
        print(f'\n❌ Error: {e}')
        return False

if __name__ == '__main__':
    test_alpha_vantage()
