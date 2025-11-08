from mss import mss
from datetime import datetime
from PIL import Image
from pathlib import Path
import os
import time
import subprocess
import platform
from .logger import logger

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("pyautogui.not.available", message="Mouse click feature disabled")


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


def capture(region: list[int], out_dir: str = "shots", app_name: str = None, click_before: tuple[int, int] = None) -> str:
    """Take a screenshot of the given region and save it to out_dir.

    region: [left, top, width, height]
    app_name: Application name to activate before capture (macOS)
    click_before: (x, y) coordinates to click before taking screenshot (to focus window)
    returns saved image path
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    
    # Activate application if specified
    if app_name:
        activate_app(app_name)
        
        # Switch to first tab with Cmd+1 (for TradingView)
        if PYAUTOGUI_AVAILABLE and platform.system() == "Darwin":
            try:
                logger.info("capture.switching_to_first_tab")
                pyautogui.hotkey('command', '1')
                time.sleep(0.5)  # Wait for tab switch
            except Exception as e:
                logger.error("capture.tab_switch_failed", error=str(e))
    
    # Click on specific coordinates before capture (to ensure correct window focus)
    if click_before and PYAUTOGUI_AVAILABLE:
        x, y = click_before
        try:
            pyautogui.click(x, y)
            logger.info("capture.click", x=x, y=y)
            time.sleep(0.3)  # Wait for click to register
        except Exception as e:
            logger.error("capture.click.failed", x=x, y=y, error=str(e))
    
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
