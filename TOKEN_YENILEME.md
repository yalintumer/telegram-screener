## 🔐 Telegram Bot Token Yenileme

### Token neden çalışmıyor?

401 Unauthorized hatası alıyorsunuz. Bunun nedenleri:
1. ❌ Token iptal edilmiş/revoke edilmiş
2. ❌ Token GitHub'da paylaşıldığı için Telegram tarafından devre dışı bırakılmış
3. ❌ Bot silinmiş

### ✅ Çözüm: Yeni Token Alın

#### Adım 1: BotFather'da Token Yenileme

1. Telegram'da **@BotFather** botunu açın
2. Şu komutu gönderin: `/mybots`
3. Botunuzu seçin
4. **API Token** > **Revoke current token** seçeneğine tıklayın
5. Yeni token'ı kopyalayın (BOŞLUKsuz!)

#### Adım 2: Yeni Token'ı Ekleyin

`.env` dosyasını düzenleyin:
```bash
nano .env
```

Yeni token'ı yapıştırın:
```
TELEGRAM_BOT_TOKEN=YENİ_TOKEN_BURAYA
TELEGRAM_CHAT_ID=6155401829
```

#### Adım 3: Test Edin

```bash
source venv_clean/bin/activate
python test_telegram_simple.py
```

### 🆕 Alternatif: Yeni Bot Oluşturun

Eğer eski botu kullanmak istemiyorsanız:

1. @BotFather'a `/newbot` gönderin
2. Bot adı girin (örn: "My Screener Bot")
3. Bot kullanıcı adı girin (örn: "my_screener_bot")
4. Token'ı kopyalayın
5. `.env` dosyasına yapıştırın

### 📱 Chat ID Nasıl Alınır?

1. Yeni botunuza mesaj gönderin (örn: /start)
2. @userinfobot'a gidin
3. Chat ID'nizi alın
4. `.env` dosyasına yapıştırın

### 🔒 Güvenlik Hatırlatması

- ✅ Yeni token'ı ASLA GitHub'a commit ETMEYİN
- ✅ `.env` dosyası `.gitignore`'da
- ✅ `config.yaml` da placeholder değerlerle bırakın
- ✅ Sadece `.env` dosyasında gerçek değerler olsun
