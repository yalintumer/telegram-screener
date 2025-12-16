# Test Strategy - Telegram Screener

## Mevcut Durum (Aralık 2025)

| Metrik | Değer |
|--------|-------|
| **Test Coverage** | %23 |
| **Toplam Test** | 62 (60 passed, 2 failed) |
| **Hedef Coverage** | %50 |

## Coverage Breakdown

### ✅ İyi Test Edilen Modüller (>70%)

| Modül | Coverage | Notlar |
|-------|----------|--------|
| `constants.py` | 100% | Sadece sabitler |
| `market_symbols.py` | 100% | S&P 500 listesi |
| `rate_limiter.py` | 98% | Thread-safe, iyi testli |
| `indicators.py` | 93% | Teknik göstergeler |
| `logger.py` | 91% | Structured logging |
| `exceptions.py` | 89% | Custom exceptions |

### ⚠️ Kısmen Test Edilen (20-70%)

| Modül | Coverage | Eksik |
|-------|----------|-------|
| `telegram_client.py` | 70% | Retry loop coverage |
| `config.py` | 57% | Env loading |
| `data_source_yfinance.py` | 40% | `weekly_ohlc` |
| `notion_client.py` | 12% | 30+ method |

### ❌ Test Edilmemiş (%0)

| Modül | Satır | Öncelik |
|-------|-------|---------|
| `main.py` | 458 | MEDIUM (entry point) |
| `retry.py` | 39 | **HIGH** |
| `health.py` | 50 | **HIGH** |
| `backup.py` | 121 | MEDIUM |
| `signal_tracker.py` | 104 | MEDIUM |
| `analytics.py` | 83 | LOW |
| `cache.py` | 67 | LOW |

---

## Test Stratejisi

### Öncelik 1: Kritik Path (Coverage → %40)

Bu testler sistemin çekirdeğini kapsar:

1. **`test_config.py`** - Config loading, env vars, validation
2. **`test_health.py`** - Health check functionality
3. **`test_retry.py`** - Retry logic with backoff
4. **`test_backup.py`** - Notion backup, atomic writes

### Öncelik 2: Integration (Coverage → %50)

1. **`test_notion_integration.py`** - Notion CRUD operations (mock)
2. **`test_signal_tracker.py`** - Signal tracking logic
3. **`test_main_flow.py`** - Main scan flow (mocked)

### Şimdilik Dışarıda Kalanlar

| Modül | Sebep |
|-------|-------|
| `analytics.py` | Low impact, sadece stats |
| `cache.py` | File-based, integration test gerekli |
| `data_source_alpha_vantage.py` | Deprecated, kullanılmıyor |
| `main.py` (full) | Entry point, unit test zor |

---

## Code Smells - Test Yazımını Zorlaştıran Faktörler

### 1. Tight Coupling (Sıkı Bağımlılık)

```python
# main.py - Doğrudan import, mock edilemez
from .notion_client import NotionClient
from .telegram_client import TelegramClient
```

**Çözüm:** Dependency injection veya factory pattern

### 2. Global State

```python
# rate_limiter.py
_global_limiter = None  # Singleton pattern

# logger.py  
_correlation_id = None  # Global state
```

**Çözüm:** Test setup/teardown'da reset

### 3. I/O Heavy Functions

```python
# backup.py
def backup_database(...):
    # Hem Notion API çağırıyor hem file yazıyor
    response = requests.post(...)  # API
    with open(filename, 'w') as f:  # File I/O
```

**Çözüm:** Mock requests ve tmpdir fixture

### 4. Side Effects in __init__

```python
# notion_client.py
def __init__(self, ...):
    session = self._get_session()
    session.headers.update(self.headers)  # Side effect!
```

**Çözüm:** Lazy initialization

### 5. Long Methods

```python
# main.py - scan_market() 200+ satır
# notion_client.py - add_to_signals() 100+ satır
```

**Çözüm:** Extract smaller functions

---

## Test Fixtures Needed

```python
# conftest.py

@pytest.fixture
def mock_notion_response():
    """Standard Notion API response"""
    return {"results": [...], "has_more": False}

@pytest.fixture
def sample_ohlc_df():
    """100 days of OHLC data"""
    return pd.DataFrame(...)

@pytest.fixture
def tmp_config(tmp_path):
    """Temporary config file"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(...)
    return config_file
```

---

## CI/CD Pipeline Requirements

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    - lint (ruff)
    - test (pytest)
    - coverage report
    - fail if coverage < 40%
```

### Quality Gates

| Gate | Threshold |
|------|-----------|
| All tests pass | Required |
| Coverage | ≥40% (target: 50%) |
| Lint errors | 0 |
| Type errors | 0 (optional) |

---

## Implementation Plan

| Gün | Görev | Est. Coverage |
|-----|-------|---------------|
| 1 | test_config, test_health | 30% |
| 2 | test_retry, test_backup | 40% |
| 3 | test_notion (mock), CI setup | 50% |

---

## Test Çalıştırma Komutları

```bash
# Tüm testler
pytest

# Coverage ile
pytest --cov=src --cov-report=term-missing

# Sadece belirli modül
pytest tests/test_config.py -v

# Paralel (hızlı)
pytest -n auto
```
