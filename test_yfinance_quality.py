"""
yfinance veri kalitesi testi ve alternatiflerin araştırılması
"""
import yfinance as yf
from datetime import datetime, timedelta

symbol = 'MSFT'
print('='*60)
print(f'yfinance Veri Kalitesi Analizi - {symbol}')
print('='*60)

ticker = yf.Ticker(symbol)

# Test 1: Farklı periyotlarla veri çek
print('\n1. FARKLI PERİYOTLAR:\n')
periods = ['1d', '5d', '1mo', '3mo']
for period in periods:
    hist = ticker.history(period=period)
    if not hist.empty:
        last_close = hist['Close'].iloc[-1]
        last_date = hist.index[-1]
        print(f'  {period:6s}: Son kapanış = ${last_close:.2f} | Tarih: {last_date}')

# Test 2: Interval karşılaştırma
print('\n2. INTERVAL FARKI:\n')
hist_1d = ticker.history(period='5d', interval='1d')
hist_1h = ticker.history(period='5d', interval='1h')
if not hist_1d.empty and not hist_1h.empty:
    print(f'  1d interval: Son = ${hist_1d["Close"].iloc[-1]:.2f}')
    print(f'  1h interval: Son = ${hist_1h["Close"].iloc[-1]:.2f}')

# Test 3: Info vs History
print('\n3. INFO vs HISTORY KARŞILAŞTIRMA:\n')
info = ticker.info
info_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
hist_price = ticker.history(period='1d')['Close'].iloc[-1] if not ticker.history(period='1d').empty else 0
print(f'  ticker.info price: ${info_price:.2f}')
print(f'  history price: ${hist_price:.2f}')
print(f'  Fark: ${abs(info_price - hist_price):.2f}')

# Test 4: Veri gecikmesi
print('\n4. VERİ GECİKMESİ:\n')
hist = ticker.history(period='1d')
if not hist.empty:
    last_update = hist.index[-1]
    now = datetime.now(last_update.tzinfo)
    delay = now - last_update
    print(f'  Son güncelleme: {last_update}')
    print(f'  Şu an: {now}')
    print(f'  Gecikme: {delay.total_seconds() / 3600:.1f} saat')

# Test 5: Auto adjust karşılaştırma
print('\n5. AUTO ADJUST FARKI:\n')
hist_adj = ticker.history(period='5d', auto_adjust=True)
hist_no_adj = ticker.history(period='5d', auto_adjust=False)
if not hist_adj.empty and not hist_no_adj.empty:
    print(f'  Auto adjust ON: ${hist_adj["Close"].iloc[-1]:.2f}')
    print(f'  Auto adjust OFF: ${hist_no_adj["Close"].iloc[-1]:.2f}')

print('\n' + '='*60)
print('\n📊 ALTERNATİF VERİ KAYNAKLARI:\n')
print('''
1. Alpha Vantage (ÜCRETSİZ)
   - 500 API call/gün (ücretsiz)
   - Yüksek kaliteli veri
   - Real-time + historical
   - Kurulum: pip install alpha-vantage
   
2. Polygon.io (ÜCRETLI başlangıç)
   - Çok kaliteli veri
   - Real-time data
   - $199/ay (temel plan)
   
3. IEX Cloud (ÜCRETLI başlangıç)
   - Orta kaliteli veri
   - 500,000 mesaj/ay ücretsiz
   - Sonrası ücretli
   
4. Twelve Data (ÜCRETSİZ başlangıç)
   - 800 API call/gün ücretsiz
   - İyi kalite
   - Kurulum: pip install twelvedata
   
5. Financial Modeling Prep (ÜCRETSİZ başlangıç)
   - 250 call/gün ücretsiz
   - İyi veri kalitesi
   
6. EOD Historical Data (ÜCRETLI)
   - Çok yüksek kalite
   - $19.99/ay başlangıç
   
ÖNERI:
- yfinance + tolerans (%0.5) en pratik
- Ücretsiz ve güvenilir
- TradingView benzeri sonuçlar için tolerans yeterli
''')
print('='*60)
