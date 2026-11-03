#!/usr/bin/env python3
"""
FiestaPanel Cross-Platform CLI Management Utility
Supports Linux, macOS, and Windows
"""
import sys
import os
import json
import time
import shutil
import hashlib
import platform
import subprocess

try:
    import psutil
except ImportError:
    psutil = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
USERS_FILE = os.path.join(SCRIPT_DIR, "users.json")
PID_FILE = os.path.join(SCRIPT_DIR, ".fiestapanel.pid")
LOG_FILE = os.path.join(SCRIPT_DIR, "fiestapanel.log")

IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def load_config():
    cfg = {
        "admin_user": "admin",
        "admin_pass": "admin",
        "server_dir": os.path.join(SCRIPT_DIR, "minecraft_server"),
        "service_name": "fiesta-portal",
        "host": "0.0.0.0",
        "port": 8080
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def is_panel_running():
    # 1. Systemd check on Linux
    if IS_LINUX and shutil.which("systemctl"):
        try:
            res = subprocess.run(["systemctl", "is-active", "fiesta-portal"], capture_output=True, text=True, timeout=2)
            if res.stdout.strip() == "active":
                return True, "systemd (fiesta-portal.service)"
        except Exception:
            pass

    # 2. Check PID file
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if psutil and psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if any("app.py" in str(arg) for arg in (proc.cmdline() or [])):
                    return True, f"PID {pid}"
        except Exception:
            pass

    # 3. Process search
    if psutil:
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = p.info.get('cmdline') or []
                if any("app.py" in str(arg) for arg in cmd) and any("python" in str(arg).lower() for arg in cmd):
                    return True, f"PID {p.info['pid']}"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    return False, "Not running"

def cmd_status():
    cfg = load_config()
    running, details = is_panel_running()
    print("==================================================")
    print("         FiestaPanel Management Suite             ")
    print("==================================================")
    print(f"Platform:      {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Panel State:   {'ONLINE (' + details + ')' if running else 'OFFLINE'}")
    print(f"Web Port:      http://{cfg.get('host', '0.0.0.0')}:{cfg.get('port', 8080)}")
    print(f"MC Directory:  {cfg.get('server_dir')}")
    
    if running and psutil:
        for p in psutil.process_iter(['pid', 'cmdline', 'memory_info', 'cpu_percent']):
            try:
                cmd = p.info.get('cmdline') or []
                if any("app.py" in str(arg) for arg in cmd):
                    mem = round(p.info['memory_info'].rss / (1024 * 1024), 1)
                    print(f"Memory Usage:  {mem} MB")
                    break
            except Exception:
                pass
    print("==================================================")

def cmd_start():
    running, details = is_panel_running()
    if running:
        print(f"FiestaPanel is already running ({details}).")
        return

    # Try systemd if Linux
    if IS_LINUX and shutil.which("systemctl"):
        try:
            res = subprocess.run(["sudo", "systemctl", "start", "fiesta-portal"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                print("FiestaPanel started via systemd (fiesta-portal.service).")
                return
        except Exception:
            pass

    # Fallback to direct python launch
    py_bin = sys.executable
    venv_py = os.path.join(SCRIPT_DIR, "venv", "Scripts" if IS_WIN else "bin", "python.exe" if IS_WIN else "python3")
    if os.path.exists(venv_py):
        py_bin = venv_py

    log_out = open(LOG_FILE, "a", encoding="utf-8")
    flags = 0
    if IS_WIN:
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

    proc = subprocess.Popen([py_bin, os.path.join(SCRIPT_DIR, "app.py")], cwd=SCRIPT_DIR, stdout=log_out, stderr=subprocess.STDOUT, creationflags=flags)
    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))
    print(f"FiestaPanel daemon started in background (PID: {proc.pid}).")
    cfg = load_config()
    print(f"Access panel at: http://localhost:{cfg.get('port', 8080)}")

def cmd_stop():
    running, details = is_panel_running()
    if not running:
        print("FiestaPanel is not currently running.")
        return

    if IS_LINUX and shutil.which("systemctl"):
        try:
            res = subprocess.run(["sudo", "systemctl", "stop", "fiesta-portal"], timeout=10)
            if res.returncode == 0:
                print("FiestaPanel stopped via systemd.")
                return
        except Exception:
            pass

    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if psutil and psutil.pid_exists(pid):
                p = psutil.Process(pid)
                p.terminate()
                p.wait(timeout=5)
            os.remove(PID_FILE)
            print(f"FiestaPanel process (PID {pid}) stopped.")
            return
        except Exception:
            pass

    if psutil:
        for p in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmd = p.info.get('cmdline') or []
                if any("app.py" in str(arg) for arg in cmd) and any("python" in str(arg).lower() for arg in cmd):
                    p.terminate()
                    print(f"Stopped FiestaPanel (PID {p.info['pid']}).")
            except Exception:
                pass

def cmd_restart():
    cmd_stop()
    time.sleep(1)
    cmd_start()

def cmd_logs():
    if IS_LINUX and shutil.which("journalctl"):
        try:
            subprocess.run(["journalctl", "-u", "fiesta-portal", "-f", "-n", "50"])
            return
        except KeyboardInterrupt:
            return
        except Exception:
            pass

    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                for l in lines[-50:]:
                    print(l, end="")
        except Exception as e:
            print("Error reading log:", e)
    else:
        print("No log file found.")

def cmd_reset_admin():
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    new_pass = "Fiesta@" + ''.join(secrets.choice(alphabet) for _ in range(8))
    
    users = {}
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        except Exception:
            pass

    p_hash = hashlib.sha256(new_pass.encode("utf-8")).hexdigest()
    users["admin"] = {
        "username": "admin",
        "password_hash": p_hash,
        "role": "owner",
        "permissions": ["all"],
        "status": "active",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

    cfg = load_config()
    cfg["admin_pass"] = new_pass
    save_config(cfg)

    print("==================================================")
    print("  Administrator Password Reset Successfully!      ")
    print("==================================================")
    print(f"Username: admin")
    print(f"Password: {new_pass}")
    print("==================================================")

def cmd_set_port(port_str):
    try:
        p = int(port_str)
        if not (1 <= p <= 65535):
            raise ValueError()
    except Exception:
        print("Invalid port number. Must be between 1 and 65535.")
        return

    cfg = load_config()
    cfg["port"] = p
    save_config(cfg)
    print(f"HTTP Port updated to: {p}")
    print("Please restart FiestaPanel for changes to take effect: panelctl restart")

def cmd_set_mc_path(mc_dir):
    abs_path = os.path.abspath(mc_dir)
    os.makedirs(abs_path, exist_ok=True)
    cfg = load_config()
    cfg["server_dir"] = abs_path
    save_config(cfg)
    print(f"Minecraft Server directory updated to: {abs_path}")
    print("Please restart FiestaPanel for changes to take effect: panelctl restart")

def cmd_info():
    cfg = load_config()
    print("==================================================")
    print("            FiestaPanel System Info               ")
    print("==================================================")
    print(f"Panel Root:        {SCRIPT_DIR}")
    print(f"Operating System:  {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python Executable: {sys.executable}")
    
    # Check Java
    j = shutil.which("java") or shutil.which("java.exe")
    if j:
        try:
            res = subprocess.run([j, "-version"], capture_output=True, text=True, timeout=2)
            out = res.stderr or res.stdout
            print(f"Java Runtime:      {out.splitlines()[0] if out else j}")
        except Exception:
            print(f"Java Runtime:      {j}")
    else:
        print("Java Runtime:      NOT FOUND in PATH")

    print(f"Web Host & Port:   {cfg.get('host', '0.0.0.0')}:{cfg.get('port', 8080)}")
    print(f"Minecraft Folder:  {cfg.get('server_dir')}")
    print("==================================================")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("Usage: panelctl [command] [args]")
        print("Commands:")
        print("  status              Check panel status & resource usage")
        print("  start               Start panel daemon")
        print("  stop                Stop panel daemon")
        print("  restart             Restart panel daemon")
        print("  logs                View recent panel logs")
        print("  reset-admin         Generate new admin password")
        print("  set-port <port>     Change panel HTTP port")
        print("  set-mc-path <path>  Change Minecraft server directory")
        print("  info                Display system and runtime details")
        print("  version             Display version number")
        return

    cmd = sys.argv[1].lower()
    if cmd == "status":
        cmd_status()
    elif cmd == "start":
        cmd_start()
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "restart":
        cmd_restart()
    elif cmd == "logs":
        cmd_logs()
    elif cmd == "reset-admin":
        cmd_reset_admin()
    elif cmd == "set-port":
        if len(sys.argv) < 3:
            print("Error: Port required. e.g. panelctl set-port 8080")
            sys.exit(1)
        cmd_set_port(sys.argv[2])
    elif cmd == "set-mc-path":
        if len(sys.argv) < 3:
            print("Error: Path required. e.g. panelctl set-mc-path /opt/minecraft")
            sys.exit(1)
        cmd_set_mc_path(sys.argv[2])
    elif cmd == "info":
        cmd_info()
    elif cmd == "version":
        print("FiestaPanel Software Suite v2.1.0")
    else:
        print(f"Unknown command: {cmd}. Run 'panelctl help' for available commands.")

if __name__ == "__main__":
    main()
