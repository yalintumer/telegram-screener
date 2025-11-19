# Notion API Kurulum Rehberi

## 🔑 Notion API Token ve Database ID Alma

### Adım 1: Notion Integration Oluştur

1. **Notion Integrations sayfasına git:**
   - https://www.notion.so/my-integrations

2. **"New integration" butonuna tıkla**

3. **Integration bilgilerini doldur:**
   - Name: `Telegram Screener` (veya istediğin isim)
   - Associated workspace: Workspace'ini seç
   - Type: Internal
   - Capabilities: ✅ Read content (sadece okuma yetkisi yeterli)

4. **"Submit" butonuna tıkla**

5. **API Token'ı kopyala:**
   - Integration oluşturduktan sonra `secret_xxx...` ile başlayan token görünecek
   - Bu token'ı `config.yaml` dosyasına yapıştır

### Adım 2: Watchlist Database Oluştur

1. **Notion'da yeni bir page aç**

2. **Database (tablo) ekle:**
   - `/table` yaz ve "Table - Inline" seç
   - Veya menüden "Table" seç

3. **Sütunu düzenle:**
   - Varsayılan "Name" sütununu `Symbol` olarak yeniden adlandır
   - Veya yeni sütun ekle ve `Symbol`, `Ticker` veya `Stock` adını ver

4. **Hisse senetlerini ekle:**
   ```
   Symbol
   -------
   AAPL
   MSFT
   GOOGL
   TSLA
   NVDA
   ```

### Adım 3: Database'i Integration ile Paylaş

1. **Database sayfasının sağ üst köşesindeki "..." (3 nokta) menüsüne tıkla**

2. **"Connections" veya "Connect to" seç**

3. **Oluşturduğun integration'ı bul ve bağlan:**
   - "Telegram Screener" (veya verdiğin isim)
   - ✅ Integration artık database'e erişebilir

### Adım 4: Database ID'yi Al

Database ID'yi almanın **3 yolu** var:

#### Yöntem 1: URL'den Al (En Kolay)
```
https://www.notion.so/your-workspace/abc123def456?v=...
                                     ^^^^^^^^^^^^
                                     Database ID
```
- Database sayfasını aç
- URL'deki ilk uzun hash'i kopyala (soru işaretinden önceki kısım)
- Bu senin Database ID'n

#### Yöntem 2: "Copy link" ile
```
https://www.notion.so/abc123def456789...
                     ^^^^^^^^^^^^
                     Database ID
```
- Database'e sağ tıkla → "Copy link"
- Link'teki hash'i kopyala

#### Yöntem 3: Share menüsünden
- Database'in "Share" menüsünü aç
- "Copy link" butonuna tıkla
- URL'deki ID'yi kopyala

### Adım 5: Config.yaml'ı Doldur

```yaml
notion:
  api_token: "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  database_id: "abc123def456789abc123def456789ab"
```

## ✅ Test Et

Terminal'de test et:

```bash
# Local'de test (config.yaml'ın dolu olduğundan emin ol)
python -m src.main --once
```

Başarılıysa şöyle bir çıktı göreceksin:
```
📋 Watchlist: 5 symbols
   AAPL, MSFT, GOOGL, TSLA, NVDA

🔍 [1/5] Checking AAPL... —
🔍 [2/5] Checking MSFT... —
...
```

## 🔒 Güvenlik İpuçları

1. **API token'ı asla GitHub'a push etme**
   - `.gitignore` dosyasında `config.yaml` var
   - Token'ları sadece VM'de kullan

2. **Integration'a minimum yetki ver**
   - Sadece "Read content" yetkisi yeterli
   - "Update" veya "Insert" gerekmez

3. **Token'ı paylaşma**
   - Her token bir workspace'e özel
   - Token'la database'e tam erişim sağlanır

## ❓ Sorun Giderme

### "Notion API failed" hatası
- Integration'ı database ile paylaştın mı? (Connections)
- API token doğru kopyalandı mı?
- Database ID doğru mu?

### "Symbol sütunu bulunamadı"
- Database'de "Symbol", "Ticker" veya "Stock" adında sütun olmalı
- Sütun adı büyük/küçük harf duyarlı değil

### "No results" hatası
- Database boş mu? En az 1 satır olmalı
- Integration database'e erişebiliyor mu? (Connections kontrol et)

## 📚 Daha Fazla Bilgi

- Notion API Docs: https://developers.notion.com
- Integration Guide: https://www.notion.so/help/create-integrations
