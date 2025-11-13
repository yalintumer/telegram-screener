#!/usr/bin/env python3
"""
Quick deployment script for production VM
Handles system service installation and management
"""

import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        sys.exit(1)
    
    return result


def install_service():
    """Install systemd service"""
    print("\n📦 Installing systemd service...")
    
    service_file = Path("telegram-screener.service")
    if not service_file.exists():
        print("❌ Service file not found: telegram-screener.service")
        sys.exit(1)
    
    # Copy service file
    run_cmd("sudo cp telegram-screener.service /etc/systemd/system/")
    
    # Reload systemd
    run_cmd("sudo systemctl daemon-reload")
    
    # Enable service
    run_cmd("sudo systemctl enable telegram-screener.service")
    
    print("✅ Service installed successfully")


def start_service():
    """Start the service"""
    print("\n🚀 Starting service...")
    run_cmd("sudo systemctl start telegram-screener.service")
    print("✅ Service started")


def stop_service():
    """Stop the service"""
    print("\n🛑 Stopping service...")
    run_cmd("sudo systemctl stop telegram-screener.service")
    print("✅ Service stopped")


def restart_service():
    """Restart the service"""
    print("\n🔄 Restarting service...")
    run_cmd("sudo systemctl restart telegram-screener.service")
    print("✅ Service restarted")


def status_service():
    """Check service status"""
    print("\n📊 Service status:")
    run_cmd("sudo systemctl status telegram-screener.service", check=False)


def logs_service():
    """View service logs"""
    print("\n📋 Service logs (last 50 lines):")
    run_cmd("sudo journalctl -u telegram-screener.service -n 50 --no-pager", check=False)


def main():
    if len(sys.argv) < 2:
        print("""
Telegram Screener Service Manager (Linux/systemd)

Usage:
    python3 deploy_service.py install   - Install systemd service
    python3 deploy_service.py start     - Start service
    python3 deploy_service.py stop      - Stop service
    python3 deploy_service.py restart   - Restart service
    python3 deploy_service.py status    - Check status
    python3 deploy_service.py logs      - View logs

Note: Requires systemd (Linux only). For macOS, use deploy_macos.py
        """)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "install":
        install_service()
        print("\n💡 Next steps:")
        print("   1. Configure .env file with your credentials")
        print("   2. Run: python3 deploy_service.py start")
    elif command == "start":
        start_service()
    elif command == "stop":
        stop_service()
    elif command == "restart":
        restart_service()
    elif command == "status":
        status_service()
    elif command == "logs":
        logs_service()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
