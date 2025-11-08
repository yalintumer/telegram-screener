#!/usr/bin/env python3
"""
Ekran bölgesi koordinatlarını bulmak için yardımcı araç.
Fare imlecinin pozisyonunu ve seçili alanı gösterir.
"""
import mss
import time
from PIL import Image
from pynput import mouse
import sys

print("🖱️  Ekran Bölgesi Bulucu")
print("=" * 50)
print("\nTalimatlar:")
print("1. TradingView screener'ı aç")
print("2. Ticker sütununun sol üst köşesine fare ile git")
print("3. Koordinatları not et")
print("4. Ticker sütununun sağ alt köşesine git")
print("5. Koordinatları not et")
print("\nFareyi hareket ettir, koordinatları görmek için...")
print("Çıkmak için Ctrl+C\n")

current_pos = [0, 0]

def on_move(x, y):
    global current_pos
    current_pos = [x, y]
    print(f"\r📍 Pozisyon: x={x:4d}, y={y:4d}   ", end="", flush=True)

def on_click(x, y, button, pressed):
    if pressed:
        print(f"\n🎯 İşaretlendi: x={x}, y={y}")

# Mouse listener
listener = mouse.Listener(on_move=on_move, on_click=on_click)
listener.start()

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n\n✅ Çıkılıyor...")
    listener.stop()
    
print("\n📝 Region hesaplamak için:")
print("   region: [left, top, width, height]")
print("   left   = sol üst x")
print("   top    = sol üst y")
print("   width  = sağ alt x - sol üst x")
print("   height = sağ alt y - sol üst y")
