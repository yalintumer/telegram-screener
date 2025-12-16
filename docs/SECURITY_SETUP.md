# Security Setup Guide

## ⚠️ MANUEL ADIMLAR GEREKLİ

SSH hardening uygulandı ama `screener` user'ın sudo yetkisi console'dan düzeltilmeli.

### 1. DigitalOcean Console'dan Bağlan

1. DigitalOcean Dashboard → Droplets → ubuntu-s-2vcpu-4gb-fra1-01
2. "Access" tab → "Launch Droplet Console"
3. Root şifresiyle giriş yap

### 2. Screener Sudo Yetkisi (Console'da)

```bash
# Root olarak:
echo 'screener ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/screener
chmod 440 /etc/sudoers.d/screener
visudo -c  # Validate
```

### 3. fail2ban Kurulumu (Console'da)

```bash
apt update && apt install -y fail2ban

# SSH jail config
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 24h
EOF

systemctl enable fail2ban
systemctl start fail2ban
fail2ban-client status sshd
```

### 4. Service Dosyasını Güncelle (User: screener)

```bash
# Service'i screener user'a taşı
cp -r /root/telegram-screener /home/screener/
chown -R screener:screener /home/screener/telegram-screener
cp /root/.telegram-screener.env /home/screener/.telegram-screener.env
chown screener:screener /home/screener/.telegram-screener.env
chmod 600 /home/screener/.telegram-screener.env

# systemd service güncelle
cat > /etc/systemd/system/telegram-screener.service << 'EOF'
[Unit]
Description=Telegram Screener
After=network.target

[Service]
Type=simple
User=screener
Group=screener
WorkingDirectory=/home/screener/telegram-screener
EnvironmentFile=/home/screener/.telegram-screener.env
ExecStart=/home/screener/telegram-screener/venv/bin/python -m src.main --interval 3600
Restart=always
RestartSec=60
StandardOutput=append:/home/screener/telegram-screener/logs/service.log
StandardError=append:/home/screener/telegram-screener/logs/service.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart telegram-screener
systemctl status telegram-screener
```

---

## SSH Hardening Özeti (Otomatik Uygulandı ✅)

| Ayar | Değer | Açıklama |
|------|-------|----------|
| PermitRootLogin | no | Root SSH kapalı |
| PasswordAuthentication | no | Sadece SSH key |
| MaxAuthTries | 3 | Brute force koruması |
| AllowUsers | screener | Tek kullanıcı |
| ClientAliveInterval | 300 | Idle timeout |

Config dosyası: `/etc/ssh/sshd_config.d/99-hardening.conf`

---

## Doğrulama Komutları

```bash
# SSH hardening kontrolü
ssh root@161.35.223.82       # ❌ Permission denied olmalı
ssh screener@161.35.223.82   # ✅ Çalışmalı

# fail2ban durumu
sudo fail2ban-client status sshd

# Firewall durumu
sudo ufw status verbose

# Service durumu
sudo systemctl status telegram-screener
```

---

## Rate Limiting (Kod İçi) ✅

Tüm harici API çağrıları rate limit koruması altında:

| Service | Limit | Dosya |
|---------|-------|-------|
| yfinance | 60/min | `data_source_yfinance.py` |
| notion | 30/min | `notion_client.py` |
| telegram | 20/min | `telegram_client.py` |
| alpha_vantage | 5/min | (config'de) |

Kullanım:
```python
from src.rate_limiter import rate_limit
rate_limit("yfinance")  # Waits if limit exceeded
```

---

## 🔐 Secrets Rotation Best Practices

### Telegram Bot Token
```bash
# 1. BotFather'dan yeni token al
# 2. VM'de güncelle:
ssh screener@161.35.223.82
sudo nano /home/screener/.telegram-screener.env
# TELEGRAM_BOT_TOKEN=new_token_here
sudo systemctl restart telegram-screener

# 3. Eski token'ı BotFather'dan revoke et
```

### Notion API Token
```bash
# 1. Notion Settings → Integrations → New token
# 2. VM'de güncelle:
sudo nano /home/screener/.telegram-screener.env
# NOTION_API_TOKEN=new_token_here
sudo systemctl restart telegram-screener

# 3. Eski integration'ı Notion'dan sil
```

### Rotation Schedule
| Secret | Frequency | Last Rotated |
|--------|-----------|--------------|
| Telegram Bot Token | 6 ayda bir | Setup |
| Notion API Token | 6 ayda bir | Setup |
| SSH Keys | Yılda bir | Setup |

---

## ✅ Post-Deploy Security Checklist

### Network & Firewall
- [ ] `ufw status` → active, deny incoming
- [ ] `ufw status | grep 22` → SSH allowed
- [ ] `nmap -p 1-1000 161.35.223.82` → only 22, 80, 443 open

### SSH Security
- [ ] `ssh root@161.35.223.82` → Permission denied
- [ ] `ssh screener@161.35.223.82` → Success (key-only)
- [ ] `grep PermitRootLogin /etc/ssh/sshd_config.d/*` → no

### Secrets
- [ ] `cat config.yaml | grep token` → LOADED_FROM_ENV
- [ ] `ls -la ~/.telegram-screener.env` → -rw------- (600)
- [ ] `git log --all -p | grep -i token | wc -l` → 0 (no tokens in git)

### fail2ban
- [ ] `systemctl status fail2ban` → active
- [ ] `fail2ban-client status sshd` → enabled
- [ ] `fail2ban-client status sshd | grep "Currently banned"` → check count

### Service
- [ ] `systemctl status telegram-screener` → active, User=screener
- [ ] `ps aux | grep python | grep main` → running as screener
- [ ] `journalctl -u telegram-screener --since "10 min ago"` → no errors

### Rate Limiting
- [ ] Check logs for `rate_limit.waiting` messages under load
- [ ] `grep rate_limit logs/screener_*.log | tail -5` → working

---

## 🚨 Emergency Procedures

### If Locked Out of SSH
1. DigitalOcean Console → Access → Launch Droplet Console
2. Login with root password (set at droplet creation)
3. Fix: `nano /etc/ssh/sshd_config.d/99-hardening.conf`
4. `systemctl reload ssh`

### If Secrets Compromised
1. Immediately rotate ALL secrets (see above)
2. Check logs: `grep -i error /home/screener/telegram-screener/logs/*.log`
3. Review access: `cat /var/log/auth.log | grep -i accepted`
4. Consider: IP restrict via ufw

### If Service Crashes
```bash
sudo journalctl -u telegram-screener -n 100 --no-pager
sudo systemctl restart telegram-screener
```
