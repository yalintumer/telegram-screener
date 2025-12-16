# 🔄 Refactoring Plan: main.py Parçalama

## Mevcut Durum

| Metrik | Değer |
|--------|-------|
| **main.py satır sayısı** | 891 |
| **Fonksiyon sayısı** | 8 |
| **Cyclomatic complexity (avg)** | ~15 |
| **Import sayısı** | 22 |

## Problem Analizi

```
main.py (891 satır) = God Module
├── Sentry initialization (20 satır)
├── update_signal_performance() (50 satır)
├── check_symbol_wavetrend() (60 satır)
├── check_market_filter() (100 satır)
├── run_market_scan() (180 satır)      ← En büyük
├── check_symbol() (55 satır)
├── run_wavetrend_scan() (180 satır)   ← En büyük
├── run_continuous() (80 satır)
└── main() / CLI (75 satır)
```

---

## Parçalama Planı: 5 Aşamalı

### Aşama 1: Scanner Modülü Çıkarma (Güvenli, Öncelikli)

**Yeni dosya: `src/scanner.py`**

```python
# Taşınacak fonksiyonlar:
- check_symbol_wavetrend()     # 60 satır
- check_market_filter()         # 100 satır  
- check_symbol()                # 55 satır

# Toplam: ~215 satır
```

**Neden güvenli:**
- Saf fonksiyonlar, side effect yok
- Bağımsız testlenebilir
- Diğer modüller değişmez

**Değişiklik:**
```python
# main.py (sonra)
from .scanner import check_symbol_wavetrend, check_market_filter, check_symbol
```

---

### Aşama 2: Workflow Modülü Çıkarma (Orta Risk)

**Yeni dosya: `src/workflows.py`**

```python
# Taşınacak fonksiyonlar:
- run_market_scan()     # 180 satır
- run_wavetrend_scan()  # 180 satır

# Toplam: ~360 satır
```

**Neden orta risk:**
- Notion, Telegram client'ları kullanıyor
- Config'e bağımlı
- Analytics, backup, health çağırıyor

**Bağımlılık inject etme:**
```python
# workflows.py
def run_market_scan(
    cfg: Config,
    notion: NotionClient,
    cache: MarketCapCache,
    analytics: Analytics,
    backup: NotionBackup
) -> dict:
    ...
```

---

### Aşama 3: CLI Modülü Çıkarma (Düşük Risk)

**Yeni dosya: `src/cli.py`**

```python
# Taşınacak:
- main() fonksiyonu
- argparse setup
- run_continuous() 

# Toplam: ~155 satır
```

**main.py kalır:**
```python
# src/main.py (sadece entry point)
from .cli import main

if __name__ == "__main__":
    exit(main())
```

---

### Aşama 4: Sentry Init Çıkarma (Düşük Risk)

**Yeni dosya: `src/monitoring.py`**

```python
# Taşınacak:
- Sentry initialization
- Error tracking utilities
- Future: metrics, tracing

# Toplam: ~30 satır
```

---

### Aşama 5: Performance Modülü (Opsiyonel)

**Yeni dosya: `src/performance.py`**

```python
# Taşınacak:
- update_signal_performance()

# Toplam: ~50 satır
```

---

## Sonuç Yapısı

```
src/
├── main.py          # Entry point only (~10 satır)
├── cli.py           # CLI, argparse, continuous mode (~155 satır)
├── scanner.py       # Symbol check functions (~215 satır)
├── workflows.py     # Market scan, WaveTrend scan (~360 satır)
├── monitoring.py    # Sentry, metrics (~30 satır)
├── performance.py   # Signal performance tracking (~50 satır)
└── ... (existing)
```

| Dosya | Satır | Responsibility |
|-------|-------|----------------|
| main.py | 10 | Entry point |
| cli.py | 155 | CLI, argument parsing, continuous loop |
| scanner.py | 215 | Symbol checks (pure functions) |
| workflows.py | 360 | Orchestration (market scan, wavetrend) |
| monitoring.py | 30 | Observability |
| performance.py | 50 | Performance tracking |

**Toplam**: 820 satır (önceki: 891) - modüler, test edilebilir

---

## Uygulama Sırası ve Risk

| Aşama | Risk | Öncelik | Tahmini Süre |
|-------|------|---------|--------------|
| 1. Scanner | ✅ Düşük | 1 | 30 dk |
| 2. Workflows | ⚠️ Orta | 2 | 1 saat |
| 3. CLI | ✅ Düşük | 3 | 30 dk |
| 4. Monitoring | ✅ Düşük | 4 | 15 dk |
| 5. Performance | ✅ Düşük | 5 | 15 dk |

---

## Dokunulmaması Gerekenler

### ❌ DOKUNMA

| Dosya | Neden |
|-------|-------|
| `indicators.py` | Stabil, %93 coverage, PineScript validated |
| `notion_client.py` | Çalışıyor, 553 satır ama tek responsibility |
| `config.py` | Pydantic models, %90 coverage |
| `rate_limiter.py` | Thread-safe, %98 coverage |
| `retry.py` | Generic utility, %97 coverage |
| `health.py` | Yeni, %96 coverage |

### ⚠️ DİKKATLİ

| Dosya | Risk |
|-------|------|
| `telegram_client.py` | Retry logic kritik |
| `signal_tracker.py` | JSON state management |
| `backup.py` | Atomic writes önemli |

---

## Migration Checklist

### Aşama 1: scanner.py

- [ ] `scanner.py` oluştur
- [ ] `check_symbol_wavetrend()` taşı
- [ ] `check_market_filter()` taşı
- [ ] `check_symbol()` taşı
- [ ] main.py'de import güncelle
- [ ] Testler geç: `pytest tests/ -v`
- [ ] VM'de deploy et ve doğrula

### Aşama 2: workflows.py

- [ ] `workflows.py` oluştur
- [ ] Dependency injection ekle
- [ ] `run_market_scan()` taşı
- [ ] `run_wavetrend_scan()` taşı
- [ ] main.py güncelle
- [ ] Integration test yaz
- [ ] VM'de deploy et

### Her aşamada:

```bash
# Lokal test
pytest tests/ -v

# Lint
ruff check src/

# VM deploy
ssh root@161.35.223.82
cd /root/telegram-screener
git pull
systemctl restart telegram-screener
journalctl -u telegram-screener -f
```

---

## Riskler ve Mitigasyon

### Risk 1: Import Cycle

**Problem:** scanner.py → workflows.py → scanner.py

**Mitigasyon:**
- Scanner saf fonksiyonlar, dependency yok
- Workflows scanner'ı import eder (tek yön)

### Risk 2: State Kaybı

**Problem:** Global state (correlation_id) bozulabilir

**Mitigasyon:**
- Correlation ID logger'da kalıyor (değişmez)
- Health check tek instance (değişmez)

### Risk 3: Test Kırılması

**Problem:** Import path değişiyor

**Mitigasyon:**
- Her aşamada pytest çalıştır
- Backward compatible import:
```python
# main.py (geçiş dönemi)
from .scanner import check_symbol_wavetrend
# OR for backward compatibility
check_symbol_wavetrend = check_symbol_wavetrend  
```

### Risk 4: Production Kesintisi

**Problem:** Deploy sırasında hata

**Mitigasyon:**
- Her aşamayı ayrı commit
- VM'de rollback kolay: `git checkout HEAD~1`
- systemctl restart yeterli
