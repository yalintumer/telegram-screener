from mss import mss
from datetime import datetime

def capture(region, out_dir="shots"):
    # region: [left, top, width, height]
    import os
    os.makedirs(out_dir, exist_ok=True)
    left, top, width, height = region
    monitor = {"left": left, "top": top, "width": width, "height": height}
    with mss() as sct:
        img = sct.grab(monitor)
        path = f"{out_dir}/screener_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        from PIL import Image
        Image.frombytes("RGB", img.size, img.rgb).save(path)
        return path