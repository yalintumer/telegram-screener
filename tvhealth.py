#!/usr/bin/env python3
"""Health check for Telegram Screener system"""

import subprocess
import json
import sys
from pathlib import Path

def main():
    print("╭─────────────────────────────────────────╮")
    print("│     🏥 System Health Check              │")
    print("╰─────────────────────────────────────────╯")
    print()
    
    # Local checks
    print("📍 Local Status:")
    
    # Check watchlist
    try:
        with open("watchlist.json") as f:
            wl = json.load(f)
        print(f"   ✅ Watchlist: {len(wl)} symbols")
        if wl:
            print(f"      Latest: {', '.join(list(wl.keys())[:3])}")
    except FileNotFoundError:
        print("   ❌ watchlist.json not found")
    except Exception as e:
        print(f"   ❌ Error reading watchlist: {e}")
    
    # Check config
    try:
        with open("config.yaml") as f:
            print("   ✅ config.yaml exists")
    except:
        print("   ⚠️  config.yaml not found")
    
    # Check signal history
    try:
        with open("signal_history.json") as f:
            history = json.load(f)
        print(f"   📊 Signal history: {len(history)} signals")
    except FileNotFoundError:
        print("   ℹ️  No signal history yet")
    except:
        print("   ⚠️  Error reading signal history")
    
    print()
    
    # VM checks
    print("🌐 VM Status:")
    
    vm_ip = "167.99.252.127"
    vm_user = "root"
    
    # Check service status
    try:
        result = subprocess.run(
            ["ssh", f"{vm_user}@{vm_ip}", "systemctl is-active telegram-screener"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip() == "active":
            print("   ✅ Service: Running")
        else:
            print("   ❌ Service: Stopped")
    except subprocess.TimeoutExpired:
        print("   ❌ Connection timeout")
    except Exception as e:
        print(f"   ❌ Cannot connect to VM: {e}")
    
    # Check VM watchlist
    try:
        result = subprocess.run(
            ["ssh", f"{vm_user}@{vm_ip}", "cat ~/telegram-screener/watchlist.json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            vm_wl = json.loads(result.stdout)
            print(f"   ✅ VM Watchlist: {len(vm_wl)} symbols")
            if vm_wl:
                print(f"      Symbols: {', '.join(list(vm_wl.keys())[:3])}")
        else:
            print("   ❌ Cannot read VM watchlist")
    except:
        print("   ⚠️  Cannot check VM watchlist")
    
    print()
    
    # Git status
    print("📊 Git Status:")
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            print("   ⚠️  Uncommitted changes:")
            for line in result.stdout.strip().split("\n")[:5]:
                print(f"      {line}")
        else:
            print("   ✅ Clean working tree")
    except:
        print("   ⚠️  Not a git repository")
    
    print()

if __name__ == "__main__":
    main()
