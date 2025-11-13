"""
macOS Launch Agent for Telegram Screener
Replaces systemd on macOS systems using launchd
"""

import subprocess
import sys
import os
from pathlib import Path
import pwd


def get_current_user():
    """Get current user's username"""
    return pwd.getpwuid(os.getuid()).pw_name


def get_project_path():
    """Get absolute path to project"""
    return Path(__file__).parent.absolute()


def create_plist():
    """Create launchd plist file for macOS"""
    user = get_current_user()
    project_path = get_project_path()
    python_path = project_path / "venv" / "bin" / "python"
    
    # Check if venv exists
    if not python_path.exists():
        print("❌ Virtual environment not found!")
        print(f"   Expected at: {python_path}")
        print("\n   Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt")
        sys.exit(1)
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.telegram-screener.service</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>src.main</string>
        <string>run</string>
        <string>--interval</string>
        <string>3600</string>
        <string>--config</string>
        <string>config.yaml</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{project_path}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{project_path}/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    
    <key>StandardOutPath</key>
    <string>{project_path}/logs/launchd.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>{project_path}/logs/launchd.err.log</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>ThrottleInterval</key>
    <integer>30</integer>
</dict>
</plist>
"""
    
    # Create logs directory if needed
    logs_dir = project_path / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Write plist file
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.telegram-screener.service.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    
    plist_path.write_text(plist_content)
    print(f"✅ Created plist file: {plist_path}")
    
    return plist_path


def run_cmd(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {result.stderr}")
        if not check:
            return result
        sys.exit(1)
    
    return result


def install():
    """Install launchd service on macOS"""
    print("\n📦 Installing macOS Launch Agent...")
    
    # Check if we're on macOS
    if sys.platform != "darwin":
        print("❌ This script is for macOS only!")
        print("   For Linux, use: systemd service")
        sys.exit(1)
    
    # Create plist
    plist_path = create_plist()
    
    print("✅ Launch Agent installed successfully")
    print("\n💡 Next steps:")
    print("   1. Configure .env file with your credentials")
    print("   2. Run: python deploy_macos.py start")


def start():
    """Start the service"""
    print("\n🚀 Starting service...")
    
    plist_name = "com.telegram-screener.service"
    
    # Load the service
    run_cmd(f"launchctl load ~/Library/LaunchAgents/{plist_name}.plist", check=False)
    run_cmd(f"launchctl start {plist_name}")
    
    print("✅ Service started")
    print("\n💡 View logs:")
    print(f"   tail -f {get_project_path()}/logs/launchd.out.log")


def stop():
    """Stop the service"""
    print("\n🛑 Stopping service...")
    
    plist_name = "com.telegram-screener.service"
    run_cmd(f"launchctl stop {plist_name}", check=False)
    run_cmd(f"launchctl unload ~/Library/LaunchAgents/{plist_name}.plist", check=False)
    
    print("✅ Service stopped")


def restart():
    """Restart the service"""
    print("\n🔄 Restarting service...")
    stop()
    start()
    print("✅ Service restarted")


def status():
    """Check service status"""
    print("\n📊 Service status:")
    
    plist_name = "com.telegram-screener.service"
    result = run_cmd(f"launchctl list | grep {plist_name}", check=False)
    
    if result.returncode == 0 and result.stdout.strip():
        print("✅ Service is running")
        print(result.stdout)
    else:
        print("⚠️  Service is not running")
    
    # Show recent logs
    print("\n📋 Recent logs:")
    log_file = get_project_path() / "logs" / "launchd.out.log"
    if log_file.exists():
        run_cmd(f"tail -20 {log_file}", check=False)
    else:
        print("   No logs yet")


def logs():
    """View service logs"""
    print("\n📋 Service logs:")
    
    out_log = get_project_path() / "logs" / "launchd.out.log"
    err_log = get_project_path() / "logs" / "launchd.err.log"
    
    if out_log.exists():
        print("\n=== STDOUT ===")
        run_cmd(f"tail -50 {out_log}", check=False)
    
    if err_log.exists():
        print("\n=== STDERR ===")
        run_cmd(f"tail -50 {err_log}", check=False)


def uninstall():
    """Uninstall the service"""
    print("\n🗑️  Uninstalling service...")
    
    # Stop first
    stop()
    
    # Remove plist
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.telegram-screener.service.plist"
    if plist_path.exists():
        plist_path.unlink()
        print(f"✅ Removed: {plist_path}")
    
    print("✅ Service uninstalled")


def main():
    if len(sys.argv) < 2:
        print("""
Telegram Screener Service Manager (macOS)

Usage:
    python deploy_macos.py install    - Install Launch Agent
    python deploy_macos.py start      - Start service
    python deploy_macos.py stop       - Stop service
    python deploy_macos.py restart    - Restart service
    python deploy_macos.py status     - Check status
    python deploy_macos.py logs       - View logs
    python deploy_macos.py uninstall  - Remove service

Note: This uses macOS launchd instead of systemd.
        """)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "install":
        install()
    elif command == "start":
        start()
    elif command == "stop":
        stop()
    elif command == "restart":
        restart()
    elif command == "status":
        status()
    elif command == "logs":
        logs()
    elif command == "uninstall":
        uninstall()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
