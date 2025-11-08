# 🔒 Güvenlik Kılavuzu

## API Anahtarlarını Koruma

### ✅ YAPILMASI GEREKENLER

1. **Environment Variables Kullanın**
   ```bash
   # .env dosyası oluşturun (Git'e commit edilmeyecek)
   cp .env.example .env
   # Gerçek değerlerinizi .env'ye girin
   ```

2. **Config Dosyalarını Koruyun**
   - `config.yaml` dosyasını asla Git'e commit etmeyin
   - Placeholder değerlerle örnek dosyalar oluşturun
   - `.gitignore` dosyasına hassas dosyaları ekleyin

3. **API Anahtarlarını Düzenli Yenileyin**
   - Telegram bot token'ı: @BotFather'dan yeni token alın
   - AlphaVantage API key: Dashboard'dan yeni key oluşturun

### ❌ YAPILMAMASI GEREKENLER

1. **API Anahtarlarını Kod İçinde Yazmayın**
   ```python
   # ❌ KÖTÜ
   bot_token = "YOUR_ACTUAL_BOT_TOKEN_HERE"
   
   # ✅ İYİ
   bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
   ```

2. **Config Dosyalarını Paylaşmayın**
   - Screenshot'larda hassas bilgileri blur'layın
   - Log dosyalarını paylaşırken API anahtarlarını maskeleyin

3. **Public Repo'lara Dikkat Edin**
   - Repo'yu public yapmadan önce hassas bilgileri temizleyin
   - Git geçmişinde hassas bilgi olup olmadığını kontrol edin

## Sızıntı Durumunda Yapılması Gerekenler

Eğer API anahtarlarınız sızdıysa:

1. **Hemen Yeni Anahtarlar Oluşturun**
   ```bash
   # Telegram Bot Token
   # @BotFather'a git > /mybots > seç > API Token > Regenerate
   
   # AlphaVantage API Key
   # alphavantage.co/support/#api-key > Yeni key oluştur
   ```

2. **Eski Anahtarları İptal Edin**
   - Telegram: Eski botu silin veya token'ı regenerate edin
   - AlphaVantage: Eski key'i deaktive edin (mümkünse)

3. **Git Geçmişini Temizleyin** (İsteğe bağlı)
   ```bash
   # BFG Repo Cleaner kullanarak
   brew install bfg
   bfg --replace-text passwords.txt .git
   
   # Veya manuel olarak
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch config.yaml' \
     --prune-empty --tag-name-filter cat -- --all
   ```

4. **Değişiklikleri Push Edin**
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

## Güvenlik Kontrol Listesi

- [ ] `.env` dosyası oluşturuldu ve gerçek değerler eklendi
- [ ] `.env` dosyası `.gitignore`'da
- [ ] `config.yaml` dosyası `.gitignore`'da
- [ ] Placeholder değerlerle örnek config dosyaları var
- [ ] README.md'de güvenlik uyarıları var
- [ ] GitHub repo'su private (veya hassas bilgi yok)
- [ ] API anahtarları environment variable olarak kullanılıyor
- [ ] Log dosyalarında hassas bilgi yok

## İletişim

Güvenlik açığı bulursanız:
- GitHub Issues yerine direkt proje sahibine bildirin
- Hassas bilgileri public olarak paylaşmayın
