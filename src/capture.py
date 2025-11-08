from mss import mss
from datetime import datetime
from PIL import Image
from pathlib import Path
import os
import time
import subprocess
import platform
from .logger import logger


def activate_app(app_name: str) -> bool:
    """Activate (focus) an application by name.
    
    Args:
        app_name: Name of the application to activate
        
    Returns:
        True if successful, False otherwise
    """
    if not app_name:
        return False
        
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            script = f'''
            tell application "{app_name}"
                activate
            end tell
            '''
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("app.activated", app_name=app_name, system=system)
            time.sleep(0.5)  # Give app time to come to front
            return True
        elif system == "Windows":
            # Windows için gelecekte eklenebilir
            logger.warning("app.activation.unsupported", system=system)
            return False
        else:
            logger.warning("app.activation.unsupported", system=system)
            return False
    except subprocess.CalledProcessError as e:
        logger.error("app.activation.failed", app_name=app_name, error=str(e))
        return False
    except Exception as e:
        logger.error("app.activation.error", app_name=app_name, error=str(e))
        return False


def capture(region: list[int], out_dir: str = "shots", app_name: str = None) -> str:
    """Take a screenshot of the given region and save it to out_dir.

    region: [left, top, width, height]
    app_name: Application name to activate before capture (macOS)
    returns saved image path
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    
    # Activate application if specified
    if app_name:
        activate_app(app_name)
    
    left, top, width, height = region
    monitor = {"left": left, "top": top, "width": width, "height": height}

    logger.info("capture.start", region=region, app_name=app_name)
    with mss() as sct:
        img = sct.grab(monitor)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(out_dir, f"screener_{ts}.png")
        Image.frombytes("RGB", img.size, img.rgb).save(path)
        logger.info("capture.done", path=path)
        return path
