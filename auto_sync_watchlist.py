#!/usr/bin/env python3
"""
Auto-sync watchlist to VM
Watches watchlist.json for changes, auto commits, pushes to Git, and updates VM
"""

import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# CONFIGURATION
WATCHLIST_PATH = Path("watchlist.json")
VM_IP = "167.99.252.127"
VM_USER = "root"
VM_PROJECT_PATH = "~/telegram-screener"
CHECK_INTERVAL = 5  # seconds

class WatchlistHandler(FileSystemEventHandler):
    """Handle watchlist.json file changes"""
    
    def __init__(self):
        self.last_sync = 0
        self.cooldown = 10  # Wait 10 seconds between syncs
        
    def on_modified(self, event):
        if event.src_path.endswith("watchlist.json"):
            # Prevent multiple triggers
            now = time.time()
            if now - self.last_sync < self.cooldown:
                return
            
            self.last_sync = now
            print(f"\n🔔 Watchlist changed at {datetime.now().strftime('%H:%M:%S')}")
            self.sync_to_vm()
    
    def sync_to_vm(self):
        """Sync watchlist to VM via Git"""
        try:
            # Show what's in watchlist
            if WATCHLIST_PATH.exists():
                data = json.loads(WATCHLIST_PATH.read_text())
                symbols = list(data.keys())
                print(f"📋 Symbols ({len(symbols)}): {', '.join(symbols[:10])}")
                if len(symbols) > 10:
                    print(f"    ... and {len(symbols) - 10} more")
            
            # Git add
            print("📤 Git add...")
            subprocess.run(["git", "add", "watchlist.json", "signal_history.json"], 
                         check=True, capture_output=True)
            
            # Git commit
            commit_msg = f"Auto-update watchlist - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            print(f"💾 Git commit: {commit_msg}")
            result = subprocess.run(["git", "commit", "-m", commit_msg], 
                                  capture_output=True, text=True)
            
            if "nothing to commit" in result.stdout:
                print("ℹ️  No changes to commit")
                return
            
            # Git push
            print("🚀 Git push...")
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print("✅ Pushed to Git!")
            
            # Update VM
            print(f"🔄 Updating VM ({VM_IP})...")
            ssh_command = f"cd {VM_PROJECT_PATH} && git pull && sudo systemctl restart telegram-screener"
            
            result = subprocess.run(
                ["ssh", f"{VM_USER}@{VM_IP}", ssh_command],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ VM updated and service restarted!")
            else:
                print(f"⚠️  VM update warning: {result.stderr}")
            
            print(f"🎉 Sync complete at {datetime.now().strftime('%H:%M:%S')}\n")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git error: {e}")
            if e.output:
                print(f"   Output: {e.output.decode()}")
        except subprocess.TimeoutExpired:
            print(f"⏱️  VM connection timeout (is SSH configured?)")
        except Exception as e:
            print(f"❌ Sync error: {e}")


def check_ssh_config():
    """Check if SSH to VM is configured"""
    try:
        result = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=5", f"{VM_USER}@{VM_IP}", "echo OK"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False


def main():
    print("=" * 60)
    print("🔄 WATCHLIST AUTO-SYNC TO VM")
    print("=" * 60)
    
    # Check configuration
    if VM_IP == "YOUR_SERVER_IP":
        print("❌ Please configure VM_IP in the script!")
        print("   Edit auto_sync_watchlist.py and set VM_IP")
        sys.exit(1)
    
    print(f"📡 VM: {VM_USER}@{VM_IP}")
    print(f"📂 Watching: {WATCHLIST_PATH.absolute()}")
    
    # Check SSH
    print("\n🔐 Testing SSH connection...")
    if check_ssh_config():
        print("✅ SSH connection OK")
    else:
        print("⚠️  SSH connection failed!")
        print("   Make sure you can SSH without password:")
        print(f"   ssh {VM_USER}@{VM_IP}")
        print("\n   Setup SSH key: ssh-copy-id {VM_USER}@{VM_IP}")
        response = input("\n   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Start watching
    print("\n👀 Watching for changes... (Press Ctrl+C to stop)")
    print(f"   Changes will auto-sync with {CHECK_INTERVAL}s cooldown\n")
    
    event_handler = WatchlistHandler()
    observer = Observer()
    observer.schedule(event_handler, path=".", recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Stopping auto-sync...")
        observer.stop()
    
    observer.join()
    print("✅ Auto-sync stopped")


if __name__ == "__main__":
    main()
