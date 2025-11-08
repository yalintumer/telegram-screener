#!/usr/bin/env python3
"""
Tam ekran görüntüsü al ve koordinat bulma konusunda yardım et
"""
from mss import mss
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

print("📸 Tam ekran görüntüsü alınıyor...")

with mss() as sct:
    # Tüm monitörü yakala
    monitor = sct.monitors[1]  # İlk monitör
    img = sct.grab(monitor)
    
    # PIL formatına çevir
    pil_img = Image.frombytes("RGB", img.size, img.rgb)
    
    # Grid çiz (her 100 piksel)
    draw = ImageDraw.Draw(pil_img)
    width, height = pil_img.size
    
    # Dikey çizgiler
    for x in range(0, width, 100):
        draw.line([(x, 0), (x, height)], fill=(255, 0, 0), width=1)
        draw.text((x+5, 5), str(x), fill=(255, 0, 0))
    
    # Yatay çizgiler
    for y in range(0, height, 100):
        draw.line([(0, y), (width, y)], fill=(255, 0, 0), width=1)
        draw.text((5, y+5), str(y), fill=(255, 0, 0))
    
    # Kaydet
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"shots/fullscreen_grid_{ts}.png"
    pil_img.save(path)
    
    print(f"✅ Kaydedildi: {path}")
    print(f"📏 Ekran boyutu: {width} x {height}")
    print("\n📝 Koordinat bulmak için:")
    print("   1. Görüntüyü aç")
    print("   2. Ticker sütununun sol üst ve sağ alt köşelerini bul")
    print("   3. Kırmızı grid çizgileri ve sayıları kullanarak pozisyonu oku")
    print("\n   region: [left, top, width, height]")
    print("   - left: sol üst x koordinatı")
    print("   - top: sol üst y koordinatı")
    print("   - width: sağ - sol")
    print("   - height: alt - üst")
    
    # Aç
    import subprocess
    subprocess.run(["open", path])
