# CI/CD Pipeline Kullanım Kılavuzu

## 🔄 Pipeline Genel Bakış

GitHub Actions ile otomatik CI/CD pipeline kuruldu. Her push ve PR'da çalışır.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Lint     │────▶│    Test     │────▶│  Security   │
│   (ruff)    │     │  (pytest)   │     │ (gitleaks)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Coverage   │
                    │   Report    │
                    └─────────────┘
```

## 📋 Jobs Açıklaması

### 1. 🔍 Lint Job

**Ne yapar:**
- `ruff check` ile kod kalitesi kontrolü
- `ruff format --check` ile format kontrolü

**Çıktı yorumlama:**
```
✓ src/config.py - passed
✗ src/main.py:45:80 - E501 Line too long
  ^^^^ Satır 45, karakter 80'de hata
```

**Lokal düzeltme:**
```bash
# Linting hatalarını göster
ruff check src/ tests/

# Otomatik düzelt
ruff check src/ tests/ --fix

# Format kontrolü
ruff format src/ tests/ --check

# Otomatik formatla
ruff format src/ tests/
```

### 2. 🧪 Test Job

**Ne yapar:**
- Tüm unit testleri çalıştırır
- Coverage raporu üretir
- Minimum %30 coverage zorunlu

**Çıktı yorumlama:**
```
tests/test_config.py::TestConfigLoad::test_load_valid_config PASSED [ 45%]
                                                             ^^^^^^
                                                             Başarılı

tests/test_retry.py::TestRetryWithBackoff::test_retries FAILED [ 50%]
                                                         ^^^^^^
                                                         Başarısız - detaylara bak
```

**Coverage raporu:**
```
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
src/config.py             91      9    90%   50-54, 102
                         ^^^^   ^^^^  ^^^^   ^^^^^^^^^
                         Toplam  Test   %     Test edilmeyen
                         satır   edilmemiş    satırlar
```

**Lokal test çalıştırma:**
```bash
# Tüm testler
pytest

# Coverage ile
pytest --cov=src --cov-report=term-missing

# Sadece belirli test
pytest tests/test_config.py -v

# Hızlı (paralel)
pytest -n auto
```

### 3. 🔒 Security Job

**Ne yapar:**
- Gitleaks ile secret taraması
- Hardcoded credentials arar
- Uyarı verir, build durdurmaz

**Çıktı yorumlama:**
```
Finding: Possible API key found
File: config.yaml
Line: 15
Secret: ntn_XXXXXXXX...
^^^^
Bu dosyayı .gitignore'a ekle veya env var kullan
```

## ✅ CI Başarı Kriterleri

| Kontrol | Kriter | Zorunlu |
|---------|--------|---------|
| Lint | 0 hata | ✅ |
| Tests | Tümü geçmeli | ✅ |
| Coverage | ≥30% | ✅ |
| Security | Uyarı OK | ⚠️ |

## 🏷️ Badge Ekleme

README.md'ye ekle:

```markdown
![CI](https://github.com/yalintumer/telegram-screener/actions/workflows/ci.yml/badge.svg)
```

Sonuç:
![CI](https://github.com/yalintumer/telegram-screener/actions/workflows/ci.yml/badge.svg)

## 🔧 Yaygın Hatalar ve Çözümler

### 1. Lint Hatası: Import Order

```
I001 Import block is un-sorted or un-formatted
```

**Çözüm:**
```bash
ruff check --fix --select I src/
```

### 2. Test Hatası: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'alpha_vantage'
```

**Çözüm:** Test dosyasında bu modülü kullanan testleri `--ignore` ile atla veya mock kullan.

### 3. Coverage Düşük

```
Coverage 25% is below minimum threshold of 30%
```

**Çözüm:**
1. Eksik testleri ekle
2. `TEST_STRATEGY.md`'ye bak
3. `pytest --cov-report=html` ile detaylı rapor al

### 4. Secret Tespit Edildi

```
Secret detected: API key in config.yaml
```

**Çözüm:**
1. `.gitignore`'a ekle
2. Environment variable kullan
3. Geçmişten silmek için: `git filter-branch`

## 📊 Coverage Hedefleri

| Dönem | Hedef | Mevcut |
|-------|-------|--------|
| Şimdi | 30% | 33% ✅ |
| Q1 2025 | 40% | - |
| Q2 2025 | 50% | - |

## 🚀 Pipeline Tetikleme

**Otomatik:**
- Her `git push main`
- Her Pull Request

**Manuel:**
- GitHub Actions sayfasından "Run workflow"

## 📝 Lokal Pre-commit

Pipeline'ı beklemeden lokal kontrol:

```bash
# Lint + format
ruff check src/ tests/ --fix
ruff format src/ tests/

# Test
pytest --cov=src

# Hepsini tek komutla (Makefile eklenecek)
make ci
```

## 🔗 Linkler

- [GitHub Actions Logs](https://github.com/yalintumer/telegram-screener/actions)
- [Coverage Report](https://codecov.io/gh/yalintumer/telegram-screener)
- [Test Strategy](./TEST_STRATEGY.md)
