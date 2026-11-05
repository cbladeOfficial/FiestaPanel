#!/usr/bin/env python3
"""
FiestaPanel Cross-Platform Auto-Start Configuration Manager
Supports Linux (systemd), Windows (Startup Folder & Registry), and macOS (launchd).
"""
import os
import sys
import json
import shutil
import platform
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
IS_DOCKER = os.environ.get("DOCKER") == "1" or os.path.exists("/.dockerenv")

def get_config_path(data_dir=None):
    base = data_dir or os.environ.get("FIESTA_DATA_DIR") or os.environ.get("GATEWAY_DATA_DIR") or SCRIPT_DIR
    target = os.path.join(base, "config.json")
    if not os.path.exists(target) and base != SCRIPT_DIR and os.path.exists(os.path.join(SCRIPT_DIR, "config.json")):
        target = os.path.join(SCRIPT_DIR, "config.json")
    return target

def read_config_autostart(data_dir=None):
    path = get_config_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("autostart", True)
        except Exception:
            pass
    return True

def write_config_autostart(enabled: bool, data_dir=None):
    path = get_config_path(data_dir)
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["autostart"] = bool(enabled)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        return False

def get_python_binary():
    venv_py = os.path.join(SCRIPT_DIR, "venv", "Scripts" if IS_WIN else "bin", "python.exe" if IS_WIN else "python3")
    if os.path.exists(venv_py):
        return venv_py
    return sys.executable

# ── Linux (systemd) ───────────────────────────────────────────────────────────
def _get_linux_service_name(data_dir=None):
    cfg_path = get_config_path(data_dir)
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if "service_name" in cfg and cfg["service_name"] in ("fiestapanel", "fiesta-portal"):
                return cfg["service_name"]
        except Exception:
            pass
    for name in ("fiestapanel", "fiesta-portal"):
        if os.path.exists(f"/etc/systemd/system/{name}.service"):
            return name
    return "fiestapanel"

def _linux_get_status(data_dir=None):
    svc = _get_linux_service_name(data_dir)
    if not shutil.which("systemctl"):
        return {"enabled": False, "method": "systemd", "details": "systemctl not found"}
    try:
        res = subprocess.run(["systemctl", "is-enabled", svc], capture_output=True, text=True, timeout=3)
        out = (res.stdout or "").strip()
        if out == "enabled":
            return {"enabled": True, "method": "systemd", "details": f"{svc}.service (enabled)"}
    except Exception as e:
        pass

    # Check user-level systemd
    try:
        res = subprocess.run(["systemctl", "--user", "is-enabled", svc], capture_output=True, text=True, timeout=3)
        if (res.stdout or "").strip() == "enabled":
            return {"enabled": True, "method": "systemd-user", "details": f"{svc}.service (user daemon enabled)"}
    except Exception:
        pass

    return {"enabled": False, "method": "systemd", "details": f"{svc}.service (disabled or not configured)"}

def _linux_set_autostart(enable: bool, data_dir=None):
    svc = _get_linux_service_name(data_dir)
    action = "enable" if enable else "disable"

    if not shutil.which("systemctl"):
        return False, "systemctl is not installed on this system."

    # Try system-level first
    cmd = ["systemctl", action, svc]
    if os.geteuid() != 0 and shutil.which("sudo"):
        cmd = ["sudo", "systemctl", action, svc]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return True, f"Successfully {action}d {svc}.service via systemd."
    except Exception as e:
        pass

    # Fallback to user-level systemd if non-root
    try:
        user_unit_dir = os.path.expanduser("~/.config/systemd/user")
        user_unit_path = os.path.join(user_unit_dir, f"{svc}.service")
        if enable and not os.path.exists(user_unit_path):
            os.makedirs(user_unit_dir, exist_ok=True)
            unit_content = f"""[Unit]
Description=FiestaPanel Minecraft Management Suite User Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory={SCRIPT_DIR}
ExecStart={get_python_binary()} {os.path.join(SCRIPT_DIR, 'app.py')}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
            with open(user_unit_path, "w", encoding="utf-8") as f:
                f.write(unit_content)
            subprocess.run(["systemctl", "--user", "daemon-reload"], timeout=5)

        res = subprocess.run(["systemctl", "--user", action, svc], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return True, f"Successfully {action}d {svc}.service via user systemd."
    except Exception as e:
        return False, f"Failed to {action} systemd service: {e}"

    return False, f"Could not {action} {svc}.service (permission denied or unit not found)."

# ── macOS (launchd) ───────────────────────────────────────────────────────────
def _get_macos_plist_path():
    return os.path.expanduser("~/Library/LaunchAgents/com.fiestapanel.plist")

def _macos_get_status():
    plist = _get_macos_plist_path()
    if os.path.exists(plist):
        return {"enabled": True, "method": "launchd", "details": f"com.fiestapanel (LaunchAgent registered at {plist})"}
    return {"enabled": False, "method": "launchd", "details": "LaunchAgent not registered"}

def _macos_set_autostart(enable: bool):
    plist = _get_macos_plist_path()
    if enable:
        os.makedirs(os.path.dirname(plist), exist_ok=True)
        py_bin = get_python_binary()
        app_py = os.path.join(SCRIPT_DIR, "app.py")
        log_file = os.path.join(SCRIPT_DIR, "fiestapanel.log")

        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fiestapanel</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py_bin}</string>
        <string>{app_py}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{SCRIPT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{log_file}</string>
</dict>
</plist>
"""
        try:
            with open(plist, "w", encoding="utf-8") as f:
                f.write(content)
            if shutil.which("launchctl"):
                subprocess.run(["launchctl", "unload", plist], capture_output=True, timeout=5)
                subprocess.run(["launchctl", "load", "-w", plist], capture_output=True, timeout=5)
            return True, f"Created macOS LaunchAgent at {plist} and loaded into launchd."
        except Exception as e:
            return False, f"Failed to create macOS LaunchAgent: {e}"
    else:
        try:
            if shutil.which("launchctl") and os.path.exists(plist):
                subprocess.run(["launchctl", "unload", "-w", plist], capture_output=True, timeout=5)
            if os.path.exists(plist):
                os.remove(plist)
            return True, "Disabled and removed macOS LaunchAgent."
        except Exception as e:
            return False, f"Failed to remove macOS LaunchAgent: {e}"

# ── Windows (Startup Folder & Registry) ───────────────────────────────────────
def _get_win_startup_paths():
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    startup_dir = os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    bat_path = os.path.join(startup_dir, "FiestaPanel.bat")
    lnk_path = os.path.join(startup_dir, "FiestaPanel.lnk")
    return startup_dir, bat_path, lnk_path

def _windows_get_status():
    startup_dir, bat_path, lnk_path = _get_win_startup_paths()
    reasons = []
    if os.path.exists(bat_path):
        reasons.append("Startup folder (FiestaPanel.bat)")
    if os.path.exists(lnk_path):
        reasons.append("Startup folder (FiestaPanel.lnk)")

    # Check Windows Registry HKCU Run key
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, "FiestaPanel")
            if val:
                reasons.append("Registry HKCU\\Run")
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass

    if reasons:
        return {"enabled": True, "method": "windows-startup", "details": ", ".join(reasons)}
    return {"enabled": False, "method": "windows-startup", "details": "Not registered in Windows Startup or Registry"}

def _windows_set_autostart(enable: bool):
    startup_dir, bat_path, lnk_path = _get_win_startup_paths()
    start_bat = os.path.join(SCRIPT_DIR, "start.bat")
    fiestapanel_bat = os.path.join(SCRIPT_DIR, "fiestapanel.bat")

    if enable:
        errors = []
        successes = []
        # 1. Write Startup Folder .bat
        try:
            os.makedirs(startup_dir, exist_ok=True)
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(f'@echo off\r\ncd /d "{SCRIPT_DIR}"\r\nstart "" /b "{get_python_binary()}" "{os.path.join(SCRIPT_DIR, "app.py")}"\r\n')
            successes.append("Startup folder FiestaPanel.bat created")
        except Exception as e:
            errors.append(f"Startup folder write: {e}")

        # 2. Set Registry Run Key
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            target = f'"{start_bat}"' if os.path.exists(start_bat) else f'"{fiestapanel_bat}" start'
            winreg.SetValueEx(key, "FiestaPanel", 0, winreg.REG_SZ, target)
            winreg.CloseKey(key)
            successes.append("HKCU\\Run registry key registered")
        except Exception as e:
            errors.append(f"Registry write: {e}")

        if successes:
            return True, f"Windows auto-start enabled ({'; '.join(successes)})."
        return False, f"Failed to enable Windows auto-start: {'; '.join(errors)}"
    else:
        # Disable
        removed = []
        for path in (bat_path, lnk_path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                    removed.append(os.path.basename(path))
                except Exception:
                    pass
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "FiestaPanel")
                removed.append("Registry HKCU\\Run")
            except FileNotFoundError:
                pass
            finally:
                winreg.CloseKey(key)
        except Exception:
            pass

        return True, f"Windows auto-start disabled (removed: {', '.join(removed) if removed else 'none found'})."

# ── Unified Public Interface ───────────────────────────────────────────────────
def get_autostart_status(data_dir=None):
    cfg_val = read_config_autostart(data_dir)
    if IS_DOCKER:
        return {
            "supported": True,
            "platform": "docker",
            "enabled": True,
            "method": "docker",
            "details": "Managed via Docker container restart policy (restart: unless-stopped)",
            "config_value": cfg_val
        }

    if IS_WIN:
        st = _windows_get_status()
        st["platform"] = "windows"
    elif IS_MAC:
        st = _macos_get_status()
        st["platform"] = "macos"
    elif IS_LINUX:
        st = _linux_get_status(data_dir)
        st["platform"] = "linux"
    else:
        st = {"enabled": False, "method": "unknown", "details": f"Unsupported platform: {platform.system()}"}
        st["platform"] = platform.system().lower()

    st["supported"] = st["method"] != "unknown"
    st["config_value"] = cfg_val
    return st

def set_autostart(enable: bool, data_dir=None):
    write_config_autostart(enable, data_dir)

    if IS_DOCKER:
        return True, "Docker container startup is controlled by your container runner (e.g. restart: unless-stopped)."

    if IS_WIN:
        ok, msg = _windows_set_autostart(enable)
    elif IS_MAC:
        ok, msg = _macos_set_autostart(enable)
    elif IS_LINUX:
        ok, msg = _linux_set_autostart(enable, data_dir)
    else:
        return False, f"Unsupported operating system: {platform.system()}"

    return ok, msg
