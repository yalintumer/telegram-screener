"""Health check and monitoring utilities for production deployment"""

import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional
from . import watchlist
from .logger import logger


class HealthMonitor:
    """Monitor system health and statistics"""
    
    STATS_FILE = Path("stats.json")
    
    @classmethod
    def record_scan(cls, symbols_scanned: int, signals_found: int, errors: int):
        """Record scan statistics"""
        stats = cls._load_stats()
        
        stats["last_scan"] = {
            "timestamp": datetime.now().isoformat(),
            "symbols_scanned": symbols_scanned,
            "signals_found": signals_found,
            "errors": errors
        }
        
        # Update counters
        stats.setdefault("total_scans", 0)
        stats["total_scans"] += 1
        
        stats.setdefault("total_signals", 0)
        stats["total_signals"] += signals_found
        
        cls._save_stats(stats)
        logger.info("health.scan_recorded", 
                   symbols=symbols_scanned, 
                   signals=signals_found, 
                   errors=errors)
    
    @classmethod
    def record_capture(cls, symbols_extracted: int):
        """Record capture statistics"""
        stats = cls._load_stats()
        
        stats["last_capture"] = {
            "timestamp": datetime.now().isoformat(),
            "symbols_extracted": symbols_extracted
        }
        
        stats.setdefault("total_captures", 0)
        stats["total_captures"] += 1
        
        cls._save_stats(stats)
        logger.info("health.capture_recorded", symbols=symbols_extracted)
    
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Get current system status"""
        stats = cls._load_stats()
        wl = watchlist._load()
        history = watchlist._load_signal_history()
        
        # Calculate watchlist age distribution
        today = date.today()
        age_distribution = {"0-1": 0, "2-3": 0, "4-5": 0, "5+": 0}
        
        for symbol, meta in wl.items():
            added = date.fromisoformat(meta.get("added", today.isoformat()))
            days = (today - added).days
            
            if days <= 1:
                age_distribution["0-1"] += 1
            elif days <= 3:
                age_distribution["2-3"] += 1
            elif days <= 5:
                age_distribution["4-5"] += 1
            else:
                age_distribution["5+"] += 1
        
        return {
            "timestamp": datetime.now().isoformat(),
            "watchlist": {
                "total_symbols": len(wl),
                "age_distribution": age_distribution
            },
            "signal_history": {
                "total_records": len(history)
            },
            "stats": stats,
            "status": "healthy" if len(wl) > 0 else "idle"
        }
    
    @classmethod
    def _load_stats(cls) -> Dict[str, Any]:
        """Load statistics from file"""
        if not cls.STATS_FILE.exists():
            return {}
        
        try:
            content = cls.STATS_FILE.read_text()
            if not content.strip():
                return {}
            return json.loads(content)
        except Exception as e:
            logger.error("health.load_stats_error", error=str(e))
            return {}
    
    @classmethod
    def _save_stats(cls, stats: Dict[str, Any]):
        """Save statistics to file"""
        try:
            cls.STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error("health.save_stats_error", error=str(e))
