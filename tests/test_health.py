"""
Tests for health check functionality
"""
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from src.health import HealthCheck, get_health


class TestHealthCheck:
    """Test HealthCheck class functionality"""
    
    def test_init_creates_health_file(self, tmp_path):
        """Test that initialization creates health file"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        assert health_file.exists()
        data = json.loads(health_file.read_text())
        assert data["status"] == "starting"
        assert "started_at" in data
        assert "version" in data
    
    def test_heartbeat_updates_timestamp(self, tmp_path):
        """Test heartbeat updates timestamp"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        # Initial state
        initial_data = json.loads(health_file.read_text())
        initial_heartbeat = initial_data.get("last_heartbeat")
        
        # Call heartbeat
        health.heartbeat()
        
        updated_data = json.loads(health_file.read_text())
        assert updated_data["last_heartbeat"] is not None
        assert updated_data["last_heartbeat"] != initial_heartbeat
    
    def test_scan_started_updates_status(self, tmp_path):
        """Test scan_started updates status and cycle"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        health.scan_started(cycle=5)
        
        data = json.loads(health_file.read_text())
        assert data["status"] == "scanning"
        assert data["current_cycle"] == 5
    
    def test_scan_completed_updates_stats(self, tmp_path):
        """Test scan_completed updates all stats"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        health.scan_completed(
            symbols_scanned=500,
            signals_found=5,
            duration_seconds=120.5
        )
        
        data = json.loads(health_file.read_text())
        assert data["status"] == "healthy"
        assert data["scan_count"] == 1
        assert data["last_scan"]["symbols_scanned"] == 500
        assert data["last_scan"]["signals_found"] == 5
        assert data["last_scan"]["duration_seconds"] == 120.5
    
    def test_scan_completed_increments_count(self, tmp_path):
        """Test that scan_count increments on each completion"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        for i in range(3):
            health.scan_completed(symbols_scanned=100, signals_found=i, duration_seconds=60)
        
        data = json.loads(health_file.read_text())
        assert data["scan_count"] == 3
    
    def test_scan_failed_sets_degraded_status(self, tmp_path):
        """Test scan_failed sets degraded status"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        health.scan_failed("Network error: connection timeout")
        
        data = json.loads(health_file.read_text())
        assert data["status"] == "degraded"
        assert data["error_count"] == 1
        assert "Network error" in data["last_error"]["message"]
    
    def test_scan_failed_truncates_long_errors(self, tmp_path):
        """Test that long error messages are truncated"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        long_error = "x" * 500
        health.scan_failed(long_error)
        
        data = json.loads(health_file.read_text())
        assert len(data["last_error"]["message"]) == 200
    
    def test_get_status_returns_copy(self, tmp_path):
        """Test get_status returns a copy of data"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        status = health.get_status()
        status["status"] = "modified"
        
        # Original should be unchanged
        assert health._data["status"] == "starting"
    
    def test_is_healthy_true_for_healthy_status(self, tmp_path):
        """Test is_healthy returns True for healthy status"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        health.scan_completed(100, 5, 60)
        assert health.is_healthy() is True
    
    def test_is_healthy_true_for_scanning_status(self, tmp_path):
        """Test is_healthy returns True for scanning status"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        health.scan_started(1)
        assert health.is_healthy() is True
    
    def test_is_healthy_false_for_degraded_status(self, tmp_path):
        """Test is_healthy returns False for degraded status"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        health.scan_failed("Some error")
        assert health.is_healthy() is False
    
    def test_atomic_write(self, tmp_path):
        """Test that writes are atomic (no partial writes)"""
        health_file = tmp_path / "health.json"
        health = HealthCheck(health_file=health_file)
        
        # Multiple rapid updates
        for i in range(100):
            health.scan_completed(100, i, 60)
        
        # File should always be valid JSON
        data = json.loads(health_file.read_text())
        assert data["scan_count"] == 100


class TestGlobalHealth:
    """Test global health singleton"""
    
    def test_get_health_returns_same_instance(self):
        """Test that get_health returns singleton"""
        # Reset global state
        import src.health
        src.health._health = None
        
        health1 = get_health()
        health2 = get_health()
        
        assert health1 is health2
    
    def test_get_health_creates_instance(self):
        """Test that get_health creates instance if None"""
        import src.health
        src.health._health = None
        
        health = get_health()
        assert health is not None
        assert isinstance(health, HealthCheck)
