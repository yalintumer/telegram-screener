#!/usr/bin/env python3
"""Quick add symbols to watchlist and optionally auto-sync to VM"""

import sys
import json
import subprocess
import os
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# VM Configuration (read from environment variables)
VM_IP = os.getenv("VM_IP", "YOUR_SERVER_IP")
VM_USER = os.getenv("VM_USER", "root")
VM_PATH = os.getenv("VM_PATH", "~/telegram-screener")

def quick_add(symbols):
    """Add symbols directly to watchlist.json"""
    watchlist_path = Path("watchlist.json")
    
    # Load existing
    if watchlist_path.exists():
        data = json.loads(watchlist_path.read_text())
    else:
        data = {}
    
    # Add new symbols
    today = date.today().isoformat()
    added = []
    
    for symbol in symbols:
        symbol = symbol.upper().strip()
        if symbol not in data:
            data[symbol] = {"added": today}
            added.append(symbol)
            print(f"✅ Added: {symbol}")
        else:
            print(f"⚠️  Already exists: {symbol}")
    
    # Save
    watchlist_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    print(f"\n📋 Total in watchlist: {len(data)}")
    print(f"➕ Newly added: {len(added)}")
    
    return len(added) > 0


def quick_remove(symbols):
    """Remove symbols from watchlist.json"""
    watchlist_path = Path("watchlist.json")
    
    # Load existing
    if not watchlist_path.exists():
        print("❌ Watchlist file not found!")
        return False
    
    data = json.loads(watchlist_path.read_text())
    
    # Remove symbols
    removed = []
    not_found = []
    
    for symbol in symbols:
        symbol = symbol.upper().strip()
        if symbol in data:
            del data[symbol]
            removed.append(symbol)
            print(f"✅ Removed: {symbol}")
        else:
            not_found.append(symbol)
            print(f"⚠️  Not found: {symbol}")
    
    # Save
    if removed:
        watchlist_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    print(f"\n📋 Total in watchlist: {len(data)}")
    print(f"➖ Removed: {len(removed)}")
    
    return len(removed) > 0

def sync_to_vm(action="Update"):
    """Push changes to Git and update VM"""
    try:
        print("\n🔄 Syncing to VM...")
        
        # Git add (handle missing files gracefully)
        subprocess.run(["git", "add", "watchlist.json"], check=True, capture_output=True)
        
        # Try to add signal_history.json if it exists
        if Path("signal_history.json").exists():
            subprocess.run(["git", "add", "signal_history.json"], capture_output=True)
        
        # Git commit
        commit_msg = f"{action} watchlist - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        result = subprocess.run(["git", "commit", "-m", commit_msg], 
                              capture_output=True, text=True)
        
        if "nothing to commit" in result.stdout:
            print("ℹ️  No changes to commit")
            return
        
        # Git push
        subprocess.run(["git", "push"], check=True, capture_output=True)
        print("✅ Pushed to Git!")
        
        # Update VM (if configured)
        if VM_IP != "YOUR_SERVER_IP":
            ssh_cmd = f"cd {VM_PATH} && git reset --hard && git pull && sudo systemctl restart telegram-screener"
            subprocess.run(["ssh", f"{VM_USER}@{VM_IP}", ssh_cmd],
                         capture_output=True, timeout=30)
            print("✅ VM updated!")
        else:
            print("⚠️  VM_IP not configured (edit quick_add.py to enable)")
            
    except Exception as e:
        print(f"⚠️  Sync error: {e}")

if __name__ == "__main__":
    # Check for sync-only mode
    if "--sync-only" in sys.argv or "--push" in sys.argv:
        print("📤 Sync-only mode: Pushing current watchlist to VM...")
        sync_to_vm("Update")
        sys.exit(0)
    
    if len(sys.argv) < 2:
        print("Usage: python quick_add.py AAPL MSFT TSLA [--sync]")
        print("       python quick_add.py --remove AAPL MSFT [--sync]")
        print("       python quick_add.py --sync-only   (just push current state)")
        print("\nOptions:")
        print("  --sync      Auto push to Git and update VM")
        print("  --remove    Remove symbols instead of adding")
        print("  --sync-only Push current watchlist without adding/removing")
        sys.exit(1)
    
    # Check for flags
    auto_sync = "--sync" in sys.argv
    remove_mode = "--remove" in sys.argv
    symbols = [s for s in sys.argv[1:] if s not in ["--sync", "--remove"]]
    
    # Add or remove symbols
    if remove_mode:
        changed = quick_remove(symbols)
        action = "Remove symbols from"
    else:
        changed = quick_add(symbols)
        action = "Add symbols to"
    
    # Auto sync if requested and changes were made
    if auto_sync and changed:
        sync_to_vm(action)
    elif changed:
        print("\n💡 Tip: Use --sync to auto-push to Git and update VM")
        print("   Example: python quick_add.py AAPL MSFT --sync")
