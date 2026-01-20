"""
Health check module for telegram-screener.
Provides file-based health status for monitoring and systemd.
"""

import json
from datetime import datetime
from pathlib import Path

from .logger import logger

# Health file location
HEALTH_FILE = Path("health.json")


class HealthCheck:
    """
    File-based health check for monitoring.

    Usage:
        health = HealthCheck()
        health.update(status="healthy", last_scan_symbols=50)

    Check health:
        cat health.json
        # or
        curl -s localhost:8080/health (if HTTP server added later)
    """

    def __init__(self, health_file: Path = HEALTH_FILE):
        self.health_file = health_file
        self._data = {
            "status": "starting",
            "started_at": datetime.now().isoformat(),
            "last_heartbeat": None,
            "last_scan": None,
            "scan_count": 0,
            "error_count": 0,
            "version": "1.0.0",
        }
        self._write()

    def _write(self):
        """Write health data to file atomically."""
        try:
            temp_file = self.health_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(self._data, indent=2))
            temp_file.rename(self.health_file)
        except Exception as e:
            logger.warning("health_write_failed", error=str(e))

    def heartbeat(self):
        """Update heartbeat timestamp."""
        self._data["last_heartbeat"] = datetime.now().isoformat()
        self._write()

    def scan_started(self, cycle: int):
        """Mark scan as started."""
        self._data["status"] = "scanning"
        self._data["current_cycle"] = cycle
        self._data["last_heartbeat"] = datetime.now().isoformat()
        self._write()

    def scan_completed(self, symbols_scanned: int, signals_found: int, duration_seconds: float):
        """Mark scan as completed with stats."""
        self._data["status"] = "healthy"
        self._data["scan_count"] = self._data.get("scan_count", 0) + 1
        self._data["last_scan"] = {
            "completed_at": datetime.now().isoformat(),
            "symbols_scanned": symbols_scanned,
            "signals_found": signals_found,
            "duration_seconds": round(duration_seconds, 2),
        }
        self._data["last_heartbeat"] = datetime.now().isoformat()
        self._write()
        logger.info(
            "health.scan_completed", symbols=symbols_scanned, signals=signals_found, duration=round(duration_seconds, 2)
        )

    def scan_failed(self, error: str):
        """Mark scan as failed."""
        self._data["status"] = "degraded"
        self._data["error_count"] = self._data.get("error_count", 0) + 1
        self._data["last_error"] = {
            "at": datetime.now().isoformat(),
            "message": error[:200],  # Truncate long errors
        }
        self._data["last_heartbeat"] = datetime.now().isoformat()
        self._write()
        logger.error("health.scan_failed", error=error[:100])

    def get_status(self) -> dict:
        """Get current health status."""
        return self._data.copy()

    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self._data.get("status") in ("healthy", "scanning")


# Global health instance
_health: HealthCheck | None = None


def get_health() -> HealthCheck:
    """Get or create global health check instance."""
    global _health
    if _health is None:
        _health = HealthCheck()
    return _health
