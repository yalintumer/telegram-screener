import logging
import sys
import os
from pathlib import Path
from datetime import datetime


class StructuredLogger:
    """Simple wrapper to support key-value logging"""
    
    def __init__(self, logger):
        self._logger = logger
    
    def _format_msg(self, msg, **kwargs):
        if kwargs:
            kv_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{msg} {kv_str}"
        return msg
    
    def debug(self, msg, **kwargs):
        self._logger.debug(self._format_msg(msg, **kwargs))
    
    def info(self, msg, **kwargs):
        self._logger.info(self._format_msg(msg, **kwargs))
    
    def warning(self, msg, **kwargs):
        self._logger.warning(self._format_msg(msg, **kwargs))
    
    def error(self, msg, **kwargs):
        self._logger.error(self._format_msg(msg, **kwargs))
    
    def exception(self, msg, **kwargs):
        self._logger.exception(self._format_msg(msg, **kwargs))


def setup_logger(level: str = "INFO", log_file: bool = True):
    """
    Setup logging with console and optional file output
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Whether to also log to file
        
    Returns:
        Configured logger instance
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    base_logger = logging.getLogger("tv_ocr_screener")
    base_logger.setLevel(numeric_level)
    base_logger.handlers = []  # Clear existing handlers
    
    # Console handler with color-friendly format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)
    base_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_path = log_dir / f"screener_{datetime.now():%Y%m%d}.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # File gets all logs
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_fmt)
        base_logger.addHandler(file_handler)
        
        base_logger.debug(f"Logging to file: {log_path}")
    
    return StructuredLogger(base_logger)


# Get log level from environment variable (default: INFO)
_log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = setup_logger(level=_log_level)
