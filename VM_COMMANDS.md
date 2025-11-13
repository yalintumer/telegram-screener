# 🖥️ Linux VM - Hızlı Komutlar

## İlk Kurulum (VM'de)

```bash
# Otomatik kurulum
cd ~/telegram-screener
bash quick_deploy_vm.sh
```

Veya manuel:

```bash
cd ~/telegram-screener
git pull

# Python3 kullan (python değil!)
python3 deploy_service.py install
python3 deploy_service.py start
```

## Servis Yönetimi

```bash
# Durumu kontrol et
python3 deploy_service.py status

# Logları görüntüle
python3 deploy_service.py logs

# Servisi yeniden başlat
python3 deploy_service.py restart

# Servisi durdur
python3 deploy_service.py stop
```

## Uygulama Komutları

```bash
# Virtual environment'i aktif et
source venv/bin/activate

# Sistem durumu
python3 -m src.main status

# Watchlist'i göster
python3 -m src.main list

# Sembol ekle
python3 -m src.main add AAPL MSFT

# Debug
python3 -m src.main debug AAPL

# Manuel scan
python3 -m src.main scan
```

## Monitoring

```bash
# Canlı loglar (systemd)
sudo journalctl -u telegram-screener -f

# Son 100 satır
sudo journalctl -u telegram-screener -n 100

# Uygulama logları
tail -f logs/screener_$(date +%Y%m%d).log

# Tüm loglar
ls -lh logs/
```

## Güncelleme

```bash
cd ~/telegram-screener

# Servisi durdur
python3 deploy_service.py stop

# Güncelle
git pull

# Bağımlılıkları güncelle (gerekirse)
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Servisi başlat
python3 deploy_service.py start

# Durumu kontrol et
python3 deploy_service.py status
```

## Yapılandırma

```bash
# .env dosyasını düzenle
nano .env

# config.yaml'ı düzenle  
nano config.yaml

# Değişiklikleri uygula
python3 deploy_service.py restart
```

## Sorun Giderme

```bash
# Servis durumu detaylı
sudo systemctl status telegram-screener

# Logları incele
python3 deploy_service.py logs

# Manuel test
source venv/bin/activate
python3 -m src.main scan --dry-run

# Python versiyonu
python3 --version

# Paketleri kontrol et
pip list | grep -E "pandas|yfinance|rich"
```

## Hızlı Testler

```bash
# Telegram bağlantısı test
source venv/bin/activate
python3 -c "from src.telegram_client import TelegramClient; from src.config import Config; cfg = Config.load('config.yaml'); print('✅ Config OK')"

# Watchlist test
python3 -m src.main add TEST123
python3 -m src.main list
python3 -m src.main remove TEST123

# Sistem durumu
python3 -m src.main status
```

## Yedekleme

```bash
# Veri dosyalarını yedekle
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  watchlist.json \
  signal_history.json \
  stats.json \
  .env \
  config.yaml

# Yedeği görüntüle
ls -lh backup_*.tar.gz
```

## Performans

```bash
# Servis kaynak kullanımı
systemctl show telegram-screener --property=MemoryCurrent,CPUUsageNSec

# Sistem kaynakları
free -h
df -h
top -bn1 | grep telegram-screener
```

## Güvenlik

```bash
# Dosya izinlerini kontrol et
ls -la .env config.yaml

# İzinleri düzelt
chmod 600 .env config.yaml

# Servis kullanıcısı
ps aux | grep telegram-screener
```

## Notlar

1. **Python3 kullanın**: VM'de `python` değil `python3` komutunu kullanın
2. **Virtual environment**: Komutlar otomatik olarak venv kullanır
3. **Systemd logları**: `journalctl` ile görüntülenebilir
4. **Auto-restart**: Servis hata durumunda otomatik yeniden başlar
5. **Güncellemeler**: `git pull` sonrası servisi yeniden başlatın

## Hızlı Erişim

VM'de alias tanımlayın (~/.bashrc):

```bash
# Telegram Screener aliases
alias tvstatus='cd ~/telegram-screener && python3 deploy_service.py status'
alias tvlogs='cd ~/telegram-screener && python3 deploy_service.py logs'
alias tvrestart='cd ~/telegram-screener && python3 deploy_service.py restart'
alias tvlist='cd ~/telegram-screener && source venv/bin/activate && python3 -m src.main list'
alias tvhealth='cd ~/telegram-screener && source venv/bin/activate && python3 -m src.main status'
```

Sonra çalıştırın:
```bash
source ~/.bashrc
```

Artık sadece yazın:
- `tvstatus` - Servis durumu
- `tvlogs` - Logları göster
- `tvrestart` - Servisi yeniden başlat
- `tvlist` - Watchlist'i göster
- `tvhealth` - Sistem sağlığı
