# 🔧 Python 3.13 Uyumluluk Sorunu - Hızlı Çözüm

## Sorun
Python 3.13 ile pandas arasında bir uyumsuzluk var (ctypes sorunu).

## Çözüm 1: Python 3.12 Kullan (Önerilen)

```bash
cd '/Users/yalintumer/Desktop/Telegram Proje'

# Eski venv'i sil
rm -rf venv

# Python 3.12 ile yeni venv oluştur
python3.12 -m venv venv

# Aktif et
source venv/bin/activate

# Paketleri yükle
pip install --upgrade pip
pip install -r requirements.txt

# Test et
python -m src.main status
```

## Çözüm 2: Pandas'ı Kaynak Koddan Derle

```bash
cd '/Users/yalintumer/Desktop/Telegram Proje'
source venv/bin/activate

# Pandas'ı kaldır
pip uninstall pandas -y

# En son sürümü kur (Python 3.13 desteği ile)
pip install --no-binary :all: --no-cache-dir pandas
```

## Çözüm 3: Conda Kullan (En Stabil)

```bash
# Conda environment oluştur
conda create -n telegram-screener python=3.12
conda activate telegram-screener

# Projeye git
cd '/Users/yalintumer/Desktop/Telegram Proje'

# Paketleri yükle
pip install -r requirements.txt

# Test et
python -m src.main status
```

## Geçici Çözüm: Conda Python'unu Düzelt

```bash
# Mevcut Python'u kontrol et
which python
# /opt/miniconda3/bin/python ise sorun var

# Proje venv'ini kullan
cd '/Users/yalintumer/Desktop/Telegram Proje'
source venv/bin/activate

# Şimdi kontrol et
which python
# /Users/yalintumer/Desktop/Telegram Proje/venv/bin/python olmalı
```

## Önerilen: Python 3.12 Kur

```bash
# Homebrew ile Python 3.12 kur
brew install python@3.12

# Yeni venv oluştur
cd '/Users/yalintumer/Desktop/Telegram Proje'
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate

# Paketleri yükle
pip install --upgrade pip
pip install -r requirements.txt

# Test et
python -m src.main --help
python -m src.main status
```

## Kontrol

```bash
# Python versiyonunu kontrol et
python --version  # Python 3.12.x olmalı

# Pandas'ı test et
python -c "import pandas; print(pandas.__version__)"

# Projeyi test et
python -m src.main list
```

## Not
Python 3.13 çok yeni ve bazı kütüphaneler henüz tam destek vermiyor. 
**Python 3.12 kullanmanızı öneriyoruz.**
