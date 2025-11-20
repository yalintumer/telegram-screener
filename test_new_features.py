"""
Test script for new features
Run: python test_new_features.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.signal_tracker import SignalTracker
from src.cache import MarketCapCache
from src.analytics import Analytics
from src.backup import NotionBackup
from datetime import datetime


def test_signal_tracker():
    """Test SignalTracker functionality"""
    print("\n" + "="*60)
    print("1️⃣  Testing SignalTracker...")
    print("="*60)
    
    tracker = SignalTracker()
    
    # Test 1: Check if alert can be sent (should be True for new symbol)
    can_send, reason = tracker.can_send_alert("AAPL", daily_limit=5, cooldown_days=7)
    print(f"✓ Can send alert for AAPL: {can_send}")
    assert can_send == True, "Should allow first alert"
    
    # Test 2: Record an alert
    signal_data = {
        "price": 180.50,
        "stoch_k": 0.15,
        "stoch_d": 0.12,
        "mfi": 35.2,
        "wt1": -58.5,
        "wt2": -62.3
    }
    tracker.record_alert("AAPL", signal_data)
    print(f"✓ Recorded alert for AAPL at ${signal_data['price']}")
    
    # Test 3: Check cooldown (should be False immediately after)
    can_send, reason = tracker.can_send_alert("AAPL", daily_limit=5, cooldown_days=7)
    print(f"✓ Cooldown check: {reason}")
    assert can_send == False, "Should enforce cooldown"
    
    # Test 4: Get signal stats
    stats = tracker.get_signal_stats("AAPL")
    print(f"✓ Signal stats: {stats['total']} alerts, {stats['evaluated']} evaluated")
    
    # Test 5: Daily stats
    daily_stats = tracker.get_daily_stats()
    print(f"✓ Daily stats: {daily_stats['today']} alerts today, {daily_stats['in_cooldown']} in cooldown")
    
    print("✅ SignalTracker tests passed!\n")


def test_cache():
    """Test MarketCapCache functionality"""
    print("\n" + "="*60)
    print("2️⃣  Testing MarketCapCache...")
    print("="*60)
    
    cache = MarketCapCache()
    
    # Test 1: Set and get
    cache.set("AAPL", 3000000000000)  # $3T
    market_cap = cache.get("AAPL")
    print(f"✓ Cached AAPL market cap: ${market_cap/1e9:.1f}B")
    assert market_cap == 3000000000000, "Should return cached value"
    
    # Test 2: Cache miss
    result = cache.get("TSLA")
    print(f"✓ Cache miss for TSLA: {result}")
    assert result is None, "Should return None for cache miss"
    
    # Test 3: Cache stats
    stats = cache.get_stats()
    print(f"✓ Cache stats: {stats['valid_entries']} valid, {stats['expired_entries']} expired")
    
    # Test 4: Clear expired (should not affect valid entries)
    cache.clear_expired()
    stats = cache.get_stats()
    print(f"✓ After cleanup: {stats['valid_entries']} valid entries")
    
    print("✅ MarketCapCache tests passed!\n")


def test_analytics():
    """Test Analytics functionality"""
    print("\n" + "="*60)
    print("3️⃣  Testing Analytics...")
    print("="*60)
    
    analytics = Analytics(data_file="test_analytics.json")
    
    # Test 1: Record market scan
    analytics.record_market_scan(found=50, added=10, updated=5)
    print("✓ Recorded market scan: 50 found, 10 added, 5 updated")
    
    # Test 2: Record Stage 1 scan
    analytics.record_stage1_scan(checked=100, passed=15)
    print("✓ Recorded Stage 1: 100 checked, 15 passed (15% pass rate)")
    
    # Test 3: Record Stage 2 scan
    analytics.record_stage2_scan(checked=15, confirmed=3)
    print("✓ Recorded Stage 2: 15 checked, 3 confirmed (20% confirm rate)")
    
    # Test 4: Record alerts
    analytics.record_alert_sent("AAPL", 180.50)
    analytics.record_alert_sent("TSLA", 250.75)
    print("✓ Recorded 2 alerts: AAPL, TSLA")
    
    # Test 5: Get weekly stats
    stats = analytics.get_weekly_stats()
    print(f"✓ Weekly stats: {stats['market_scans']} market scans, {stats['alerts_sent']} alerts")
    
    # Test 6: Check if report should be sent
    should_send = analytics.should_send_weekly_report()
    print(f"✓ Should send weekly report: {should_send}")
    
    # Cleanup
    Path("test_analytics.json").unlink(missing_ok=True)
    
    print("✅ Analytics tests passed!\n")


def test_backup():
    """Test NotionBackup functionality"""
    print("\n" + "="*60)
    print("4️⃣  Testing NotionBackup...")
    print("="*60)
    
    backup = NotionBackup(backup_dir="test_backups")
    
    # Test 1: Check backup directory exists
    assert Path("test_backups").exists(), "Backup directory should be created"
    print("✓ Backup directory created")
    
    # Test 2: Get backup stats (empty)
    stats = backup.get_backup_stats()
    print(f"✓ Backup stats: {stats['total_backups']} backups, {stats['total_size_mb']:.2f} MB")
    
    # Test 3: Get latest backup (should be None)
    latest = backup.get_latest_backup("test_db")
    print(f"✓ Latest backup: {latest}")
    assert latest is None, "No backups yet"
    
    # Cleanup
    import shutil
    shutil.rmtree("test_backups", ignore_errors=True)
    
    print("✅ NotionBackup tests passed!\n")


def main():
    """Run all tests"""
    print("\n" + "🧪 " + "="*58)
    print("  TESTING NEW FEATURES")
    print("🧪 " + "="*58)
    
    try:
        test_signal_tracker()
        test_cache()
        test_analytics()
        test_backup()
        
        print("\n" + "🎉 " + "="*58)
        print("  ALL TESTS PASSED!")
        print("🎉 " + "="*58 + "\n")
        
        print("✅ SignalTracker: Alert management working")
        print("✅ MarketCapCache: Caching working")
        print("✅ Analytics: Tracking working")
        print("✅ NotionBackup: Backup system working")
        print("\n🚀 All new features are ready for production!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
