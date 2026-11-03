import os
import platform
import tarfile
import subprocess
import time
import json
import shutil
import psutil
import glob
import datetime
import socket
import struct
import threading
import urllib.request
import urllib.parse
import nbtlib
import io
import re
import hashlib
import zipfile
from PIL import Image
from functools import wraps
from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file, send_from_directory

app = Flask(__name__)
app.secret_key = os.urandom(32)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_server_config():
    cfg = {
        "admin_user": "admin",
        "admin_pass": "FiestaSMP@Not-222",
        "server_dir": "/home/ubuntu/fiesta",
        "service_name": "fiesta",
        "screen_session": "fiesta",
        "host": "127.0.0.1",
        "port": 8080
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    if os.environ.get("GATEWAY_ADMIN_USER"):
        cfg["admin_user"] = os.environ.get("GATEWAY_ADMIN_USER")
    if os.environ.get("GATEWAY_ADMIN_PASS"):
        cfg["admin_pass"] = os.environ.get("GATEWAY_ADMIN_PASS")
    if os.environ.get("GATEWAY_SERVER_DIR"):
        cfg["server_dir"] = os.environ.get("GATEWAY_SERVER_DIR")
    if os.environ.get("GATEWAY_SERVICE_NAME"):
        cfg["service_name"] = os.environ.get("GATEWAY_SERVICE_NAME")
    if os.environ.get("GATEWAY_HOST"):
        cfg["host"] = os.environ.get("GATEWAY_HOST")
    if os.environ.get("GATEWAY_PORT"):
        try:
            cfg["port"] = int(os.environ.get("GATEWAY_PORT"))
        except ValueError:
            pass
    return cfg

SERVER_CONFIG = load_server_config()
ADMIN_USER = SERVER_CONFIG["admin_user"]
ADMIN_PASS = SERVER_CONFIG["admin_pass"]
SERVER_DIR = SERVER_CONFIG["server_dir"]
SERVICE_NAME = SERVER_CONFIG["service_name"]
SCREEN_SESSION = SERVER_CONFIG.get("screen_session", "fiesta")

STATIC_DIR = os.path.join(BASE_DIR, "static")
MCASSETS_DIR = os.path.join(STATIC_DIR, "mcassets")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
LOG_FILE = os.path.join(SERVER_DIR, "logs", "latest.log")
START_TIME = time.time()

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def tail_file(filepath, n_lines=100, block_size=4096):
    """Cross-platform efficient log tail reader (backward seek without tail command)."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            filesize = f.tell()
            buffer = bytearray()
            pointer = filesize
            lines = []
            while pointer > 0 and len(lines) <= n_lines:
                read_size = min(block_size, pointer)
                pointer -= read_size
                f.seek(pointer)
                chunk = f.read(read_size)
                buffer = chunk + buffer
                lines = buffer.split(b"\n")
            return [l.decode("utf-8", errors="replace").rstrip("\r") for l in lines[-n_lines:] if l]
    except Exception:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return [l.rstrip("\r\n") for l in f.readlines()[-n_lines:]]
        except Exception:
            return []

def detect_java_bin():
    """Locate java binary across Windows, macOS, and Linux."""
    j = shutil.which("java") or shutil.which("java.exe")
    if j:
        return j
    jh = os.environ.get("JAVA_HOME")
    if jh:
        bin_j = os.path.join(jh, "bin", "java.exe" if IS_WINDOWS else "java")
        if os.path.exists(bin_j):
            return bin_j
    if IS_WINDOWS:
        for wr in [r"C:\Program Files\Eclipse Adoptium", r"C:\Program Files\Java", r"C:\Program Files\Microsoft", r"C:\Program Files\Amazon Corretto"]:
            if os.path.exists(wr):
                for root, dirs, files in os.walk(wr):
                    if "java.exe" in files:
                        return os.path.join(root, "java.exe")
    elif IS_MACOS:
        try:
            out = subprocess.check_output(["/usr/libexec/java_home"], text=True).strip()
            if out and os.path.exists(os.path.join(out, "bin", "java")):
                return os.path.join(out, "bin", "java")
        except Exception:
            pass
    return "java"

def detect_java_version_str():
    j_bin = detect_java_bin()
    try:
        res = subprocess.run([j_bin, "-version"], capture_output=True, text=True, timeout=2)
        out = res.stderr or res.stdout
        if out:
            return out.splitlines()[0].strip()
    except Exception:
        pass
    return "OpenJDK / Java Runtime"

class ServerRunner:
    """
    Cross-platform Minecraft server manager for Linux, macOS, and Windows.
    Supports systemd when present, direct process execution with stdin, and screen.
    """
    def __init__(self, server_dir, service_name=None, screen_session=None):
        self.server_dir = os.path.abspath(server_dir)
        self.service_name = service_name
        self.screen_session = screen_session
        self.proc = None
        self.pid_file = os.path.join(self.server_dir, ".fiesta_server.pid")
        self.runtime_config_file = os.path.join(self.server_dir, "runtime_config.json")
        self.lock = threading.Lock()

    def _detect_systemd(self):
        if not IS_LINUX or not shutil.which("systemctl") or not self.service_name:
            return False
        try:
            res = subprocess.run(["systemctl", "status", self.service_name], capture_output=True, timeout=2)
            return res.returncode in (0, 3)
        except Exception:
            return False

    def load_runtime_config(self):
        cfg = {
            "min_ram": "1G",
            "max_ram": "4G",
            "jvm_flags": ["-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=200", "-XX:+UnlockExperimentalVMOptions", "-XX:+DisableExplicitGC", "-XX:+AlwaysPreTouch"],
            "jar_name": "server.jar"
        }
        if os.path.exists(self.runtime_config_file):
            try:
                with open(self.runtime_config_file, "r") as f:
                    cfg.update(json.load(f))
            except Exception:
                pass
        return cfg

    def save_runtime_config(self, cfg):
        os.makedirs(self.server_dir, exist_ok=True)
        try:
            with open(self.runtime_config_file, "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    def is_running(self):
        if self._detect_systemd():
            try:
                res = subprocess.run(["sudo", "systemctl", "is-active", self.service_name], capture_output=True, text=True, timeout=2)
                if res.stdout.strip() == "active":
                    return True
            except Exception:
                pass

        if self.proc and self.proc.poll() is None:
            return True

        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                if psutil and psutil.pid_exists(pid):
                    p = psutil.Process(pid)
                    if any("server.jar" in str(arg) for arg in (p.cmdline() or [])):
                        return True
            except Exception:
                pass

        if psutil:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline') or []
                    if any('server.jar' in str(arg) for arg in cmdline):
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return False

    def get_process_info(self):
        if psutil:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
                try:
                    cmdline = proc.info.get('cmdline') or []
                    if any('server.jar' in str(arg) for arg in cmdline):
                        mem_mb = round(proc.info['memory_info'].rss / (1024 * 1024), 1)
                        return proc.info['pid'], mem_mb, proc.info.get('cpu_percent', 0.0)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return None, 0, 0.0

    def start(self):
        with self.lock:
            if self.is_running():
                return True, "Server is already running."

            jar_path = os.path.join(self.server_dir, "server.jar")
            if not os.path.exists(jar_path):
                return False, "server.jar not found in server directory. Please install server software first."

            # Ensure eula.txt is true
            eula_file = os.path.join(self.server_dir, "eula.txt")
            if not os.path.exists(eula_file):
                try:
                    with open(eula_file, "w") as f:
                        f.write("# By changing the setting below to TRUE you are indicating your agreement to the Mojang EULA (https://aka.ms/MinecraftEULA).\neula=true\n")
                except Exception:
                    pass
            else:
                try:
                    with open(eula_file, "r") as f:
                        content = f.read()
                    if "eula=false" in content:
                        with open(eula_file, "w") as f:
                            f.write(content.replace("eula=false", "eula=true"))
                except Exception:
                    pass

            if self._detect_systemd():
                try:
                    res = subprocess.run(["sudo", "systemctl", "start", self.service_name], capture_output=True, text=True, timeout=10)
                    if res.returncode == 0:
                        return True, f"Started {self.service_name} via systemd."
                except Exception:
                    pass

            java_bin = detect_java_bin()
            cfg = self.load_runtime_config()
            min_ram = cfg.get("min_ram", "1G")
            max_ram = cfg.get("max_ram", "4G")
            jvm_flags = cfg.get("jvm_flags", ["-XX:+UseG1GC"])

            logs_dir = os.path.join(self.server_dir, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            log_file = os.path.join(logs_dir, "latest.log")

            cmd = [java_bin, f"-Xms{min_ram}", f"-Xmx{max_ram}"] + jvm_flags + ["-jar", "server.jar", "nogui"]
            log_out = open(log_file, "a", encoding="utf-8", errors="replace")

            creationflags = 0
            if IS_WINDOWS:
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)

            self.proc = subprocess.Popen(
                cmd,
                cwd=self.server_dir,
                stdin=subprocess.PIPE,
                stdout=log_out,
                stderr=subprocess.STDOUT,
                creationflags=creationflags
            )

            try:
                with open(self.pid_file, "w") as f:
                    f.write(str(self.proc.pid))
            except Exception:
                pass

            return True, f"Server process launched directly (PID: {self.proc.pid})."

    def stop(self):
        with self.lock:
            self.send_command("save-all")
            time.sleep(1)
            self.send_command("stop")

            if self._detect_systemd():
                try:
                    subprocess.run(["sudo", "systemctl", "stop", self.service_name], timeout=15)
                except Exception:
                    pass

            if self.proc and self.proc.poll() is None:
                try:
                    self.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.proc.kill()
                self.proc = None

            if os.path.exists(self.pid_file):
                try:
                    with open(self.pid_file, "r") as f:
                        pid = int(f.read().strip())
                    if psutil and psutil.pid_exists(pid):
                        p = psutil.Process(pid)
                        p.terminate()
                    os.remove(self.pid_file)
                except Exception:
                    pass

            return True, "Server shutdown initiated."

    def restart(self):
        self.stop()
        time.sleep(2)
        return self.start()

    def send_command(self, cmd):
        clean_cmd = cmd.strip()
        executed = False

        if self.proc and self.proc.stdin and self.proc.poll() is None:
            try:
                self.proc.stdin.write(f"{clean_cmd}\n".encode("utf-8"))
                self.proc.stdin.flush()
                executed = True
            except Exception:
                pass

        if not executed and IS_LINUX and shutil.which("screen"):
            screen_name = self.screen_session or "fiesta"
            try:
                cmd_esc = clean_cmd.replace('"', '\"').replace("'", "\'")
                res = subprocess.run(
                    ["screen", "-p", "0", "-S", screen_name, "-X", "eval", f'stuff "{cmd_esc}\\015"'],
                    capture_output=True, timeout=2
                )
                if res.returncode == 0:
                    executed = True
            except Exception:
                pass

        return executed, f"Executed: {clean_cmd}" if executed else "Could not dispatch command."

server_runner = ServerRunner(SERVER_DIR, SERVICE_NAME, SCREEN_SESSION)


def hash_password(pwd):
    return hashlib.sha256(pwd.encode('utf-8')).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            ADMIN_USER: {
                "username": ADMIN_USER,
                "password_hash": hash_password(ADMIN_PASS),
                "role": "owner",
                "permissions": ["all"],
                "created_at": "2026-11-02 12:00:00",
                "status": "active"
            }
        }
        try:
            with open(USERS_FILE, "w") as f:
                json.dump(default_users, f, indent=2)
        except Exception:
            pass
        return default_users
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

BRANDING_FILE = os.path.join(BASE_DIR, "branding.json")

DEFAULT_BRANDING = {
    "brand_name": "FIESTA-LINK",
    "tagline": "The Reliable Choice",
    "model_number": "Model No. FS-GATEWAY-PRO",
    "browser_title": "FIESTA-LINK | FS-GATEWAY-PRO Console",
    "footer_text": "Made by Fiesta and it's developers, Mockup UI of Legacy TP-Link Portal",
    "server_desc": "Server Gateway Console",
    "header_icon": "tplink",
    "header_icon_custom": ""
}

HEADER_ICONS = {
    "tplink": """<svg viewBox="0 0 36 28" width="36" height="28"><path d="M4 14 C4 8 9 4 15 4 L20 4 C24 4 28 8 28 12 L22 12 C22 10 19 8 16 8 L14 8 C11 8 8 11 8 14 C8 17 11 20 14 20 L16 20 C19 20 22 18 22 16 L28 16 C28 20 24 24 20 24 L15 24 C9 24 4 20 4 14 Z" fill="#ffffff" opacity="0.95"/><path d="M32 14 C32 20 27 24 21 24 L16 24 C12 24 8 20 8 16 L14 16 C14 18 17 20 20 20 L22 20 C25 20 28 17 28 14 C28 11 25 8 22 8 L20 8 C17 8 14 10 14 12 L8 12 C8 8 12 4 16 4 L21 4 C27 4 32 8 32 14 Z" fill="#bdf4c9" opacity="0.85"/></svg>""",
    "win7": """<svg viewBox="0 0 32 32" width="32" height="28"><path d="M4 6 C8 4 12 7 15 6 L15 15 C12 16 8 13 4 15 Z" fill="#e73827"/><path d="M17 6 C20 4 24 7 28 5 L28 14 C24 16 20 13 17 15 Z" fill="#4fae32"/><path d="M4 17 C8 15 12 18 15 17 L15 26 C12 27 8 24 4 26 Z" fill="#0080ff"/><path d="M17 17 C20 15 24 18 28 16 L28 25 C24 27 20 24 17 26 Z" fill="#fbb03b"/></svg>""",
    "minecraft": """<svg viewBox="0 0 32 32" width="30" height="28"><rect width="32" height="32" rx="4" fill="#3ca432"/><rect x="5" y="7" width="6" height="6" fill="#111111"/><rect x="21" y="7" width="6" height="6" fill="#111111"/><rect x="11" y="13" width="10" height="11" fill="#111111"/><rect x="8" y="17" width="3" height="11" fill="#111111"/><rect x="21" y="17" width="3" height="11" fill="#111111"/></svg>""",
    "win98": """<svg viewBox="0 0 32 32" width="32" height="28"><path d="M5 8 C8 7 11 9 14 8 L14 15 C11 16 8 14 5 15 Z" fill="#ff0000"/><path d="M16 8 C19 7 22 9 25 7 L25 14 C22 16 19 14 16 15 Z" fill="#00aa00"/><path d="M5 17 C8 16 11 18 14 17 L14 24 C11 25 8 23 5 24 Z" fill="#0000ff"/><path d="M16 17 C19 16 22 18 25 16 L25 23 C22 25 19 23 16 24 Z" fill="#ffcc00"/></svg>""",
    "server": """<svg viewBox="0 0 32 32" width="32" height="28"><rect x="3" y="4" width="26" height="7" rx="2" fill="#1e1e1e" stroke="#fff" stroke-width="1.5"/><circle cx="7" cy="7.5" r="1.5" fill="#00ff66"/><circle cx="12" cy="7.5" r="1.5" fill="#00ff66"/><line x1="17" y1="7.5" x2="25" y2="7.5" stroke="#aaa" stroke-width="1.5"/><rect x="3" y="13" width="26" height="7" rx="2" fill="#1e1e1e" stroke="#fff" stroke-width="1.5"/><circle cx="7" cy="16.5" r="1.5" fill="#00ff66"/><circle cx="12" cy="16.5" r="1.5" fill="#ffcc00"/><line x1="17" y1="16.5" x2="25" y2="16.5" stroke="#aaa" stroke-width="1.5"/><rect x="3" y="22" width="26" height="7" rx="2" fill="#1e1e1e" stroke="#fff" stroke-width="1.5"/><circle cx="7" cy="25.5" r="1.5" fill="#00ff66"/><circle cx="12" cy="25.5" r="1.5" fill="#00ff66"/><line x1="17" y1="25.5" x2="25" y2="25.5" stroke="#aaa" stroke-width="1.5"/></svg>""",
    "terminal": """<svg viewBox="0 0 32 32" width="32" height="28"><rect x="2" y="4" width="28" height="24" rx="3" fill="#111111" stroke="#00ff66" stroke-width="1.5"/><path d="M7 11 L13 16 L7 21" stroke="#00ff66" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/><line x1="16" y1="21" x2="24" y2="21" stroke="#00ff66" stroke-width="2.5" stroke-linecap="round"/></svg>""",
    "chip": """<svg viewBox="0 0 32 32" width="32" height="28"><rect x="7" y="7" width="18" height="18" rx="2" fill="#252525" stroke="#00f0ff" stroke-width="1.5"/><rect x="11" y="11" width="10" height="10" rx="1" fill="#00f0ff" opacity="0.3"/><path d="M11 4 L11 7 M16 4 L16 7 M21 4 L21 7 M11 25 L11 28 M16 25 L16 28 M21 25 L21 28 M4 11 L7 11 M4 16 L7 16 M4 21 L7 21 M25 11 L28 11 M25 16 L28 16 M25 21 L28 21" stroke="#00f0ff" stroke-width="1.5" stroke-linecap="round"/></svg>""",
    "shield": """<svg viewBox="0 0 32 32" width="32" height="28"><path d="M16 3 L27 7 V15 C27 22 22 27 16 29 C10 27 5 22 5 15 V7 Z" fill="#00aa44" stroke="#ffffff" stroke-width="1.5"/><path d="M11 15 L14.5 18.5 L21.5 11.5" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>""",
    "antenna": """<svg viewBox="0 0 32 32" width="32" height="28"><rect x="4" y="18" width="24" height="9" rx="2" fill="#333" stroke="#fff" stroke-width="1.5"/><circle cx="9" cy="22.5" r="1.5" fill="#00ff66"/><circle cx="14" cy="22.5" r="1.5" fill="#00ff66"/><circle cx="19" cy="22.5" r="1.5" fill="#00ff66"/><line x1="8" y1="18" x2="4" y2="7" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="24" y1="18" x2="28" y2="7" stroke="#fff" stroke-width="2" stroke-linecap="round"/><path d="M13 13 C14.5 11 17.5 11 19 13" stroke="#00ff66" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>""",
    "cyber": """<svg viewBox="0 0 32 32" width="32" height="28"><polygon points="16,2 29,8 29,24 16,30 3,24 3,8" fill="#1b0a2a" stroke="#ff2a85" stroke-width="1.5"/><path d="M17 7 L10 17 L16 17 L15 25 L22 15 L16 15 Z" fill="#00f0ff"/></svg>""",
    "flame": """<svg viewBox="0 0 32 32" width="32" height="28"><path d="M16 2 C16 7 20 10 20 14 C20 16 19 18 17 19 C18 15 15 13 14 11 C11 14 10 18 10 20 C10 25 13 29 18 29 C24 29 27 24 27 18 C27 11 21 6 16 2 Z" fill="#ef4444"/><path d="M16 14 C16 17 18 19 18 21 C18 23 17 24 16 25 C14 25 13 23 13 21 C13 18 15 16 16 14 Z" fill="#fbbf24"/></svg>""",
    "globe": """<svg viewBox="0 0 32 32" width="32" height="28"><circle cx="16" cy="16" r="12" fill="#005a9e" stroke="#ffffff" stroke-width="1.5"/><ellipse cx="16" cy="16" rx="6" ry="12" fill="none" stroke="#ffffff" stroke-width="1.2"/><line x1="4" y1="16" x2="28" y2="16" stroke="#ffffff" stroke-width="1.2"/><line x1="6" y1="10" x2="26" y2="10" stroke="#ffffff" stroke-width="1"/><line x1="6" y1="22" x2="26" y2="22" stroke="#ffffff" stroke-width="1"/></svg>"""
}

def get_header_icon_svg(icon_key, custom_val=""):
    if icon_key == "custom" and custom_val:
        custom_val = custom_val.strip()
        if custom_val.startswith("<svg"):
            return custom_val
        else:
            return f'<img src="{custom_val}" alt="logo" style="max-height: 28px; max-width: 36px; object-fit: contain; vertical-align: middle;">'
    return HEADER_ICONS.get(icon_key, HEADER_ICONS["tplink"])

app.jinja_env.globals.update(get_header_icon_svg=get_header_icon_svg)

def load_branding():
    if not os.path.exists(BRANDING_FILE):
        return DEFAULT_BRANDING.copy()
    try:
        with open(BRANDING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_BRANDING.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_BRANDING.copy()

def save_branding(data):
    with open(BRANDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

ALLOWED_CONFIGS = {
    "server.properties": os.path.join(SERVER_DIR, "server.properties"),
    "bukkit.yml": os.path.join(SERVER_DIR, "bukkit.yml"),
    "spigot.yml": os.path.join(SERVER_DIR, "spigot.yml"),
    "purpur.yml": os.path.join(SERVER_DIR, "purpur.yml"),
    "Essentials/config.yml": os.path.join(SERVER_DIR, "plugins", "Essentials", "config.yml"),
    "Essentials/spawn.yml": os.path.join(SERVER_DIR, "plugins", "Essentials", "spawn.yml"),
    "AuthMe/config.yml": os.path.join(SERVER_DIR, "plugins", "AuthMe", "config.yml"),
    "Geyser-Spigot/config.yml": os.path.join(SERVER_DIR, "plugins", "Geyser-Spigot", "config.yml"),
    "TAB/config.yml": os.path.join(SERVER_DIR, "plugins", "TAB", "config.yml"),
    "DeluxeMenus/main_menu.yml": os.path.join(SERVER_DIR, "plugins", "DeluxeMenus", "gui_menus", "main_menu.yml")
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function

def send_mc_command(cmd):
    try:
        clean_cmd = cmd.replace('"', '\\"').replace("'", "\\'").strip()
        subprocess.run(
            ["screen", "-p", "0", "-S", "fiesta", "-X", "eval", f'stuff "{clean_cmd}\\015"'],
            check=True
        )
        return True, f"Executed: {cmd}"
    except Exception as e:
        return False, str(e)

def ping_mc():
    """Queries live Minecraft server on 127.0.0.1:25565 via native SLP handshake."""
    try:
        t0 = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        s.connect(('127.0.0.1', 25565))

        host = '127.0.0.1'.encode('utf-8')
        data = b'\x00' + b'\xff\x05' + bytes([len(host)]) + host + struct.pack('>H', 25565) + b'\x01'
        s.sendall(bytes([len(data)]) + data)
        s.sendall(b'\x01\x00')

        def read_varint(sock):
            val = 0
            for i in range(5):
                b = ord(sock.recv(1))
                val |= (b & 0x7f) << (7 * i)
                if not (b & 0x80):
                    break
            return val

        _ = read_varint(s)
        _ = read_varint(s)
        str_len = read_varint(s)

        received = b''
        while len(received) < str_len:
            chunk = s.recv(min(4096, str_len - len(received)))
            if not chunk:
                break
            received += chunk
        s.close()
        ms = round((time.time() - t0) * 1000, 1)

        info = json.loads(received.decode('utf-8', errors='ignore'))
        return {
            'online': True,
            'ping_ms': ms,
            'version': info.get('version', {}).get('name', 'Purpur 1.21.11'),
            'players_online': info.get('players', {}).get('online', 0),
            'players_max': info.get('players', {}).get('max', 0),
            'player_sample': [p.get('name') for p in info.get('players', {}).get('sample', []) if 'name' in p],
            'motd': info.get('description', {}).get('text', '') if isinstance(info.get('description'), dict) else str(info.get('description', ''))
        }
    except Exception as e:
        return {
            'online': False,
            'ping_ms': -1,
            'error': str(e),
            'version': 'Purpur 1.21.11 (Offline)',
            'players_online': 0,
            'players_max': 0,
            'player_sample': [],
            'motd': ''
        }

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        users = load_users()
        user_entry = users.get(username)
        pwd_hash = hash_password(password)

        is_valid = False
        role = "moderator"
        permissions = ["console", "players"]

        if user_entry:
            if user_entry.get("status") != "active":
                msg = "This sub-user account has been disabled."
                if request.is_json:
                    return jsonify({"success": False, "message": msg}), 403
                return render_template("login.html", error=msg, branding=load_branding())
            if user_entry.get("password_hash") == pwd_hash:
                is_valid = True
                role = user_entry.get("role", "moderator")
                permissions = user_entry.get("permissions", ["console", "players"])
        elif username == ADMIN_USER and password == ADMIN_PASS:
            is_valid = True
            role = "owner"
            permissions = ["all"]

        if is_valid:
            session["logged_in"] = True
            session["user"] = username
            session["role"] = role
            session["permissions"] = permissions
            if request.is_json:
                return jsonify({"success": True})
            return redirect(url_for("dashboard"))

        if request.is_json:
            return jsonify({"success": False, "message": "Invalid username or password"}), 401
        return render_template("login.html", error="Invalid credentials", branding=load_branding())
    return render_template("login.html", branding=load_branding())

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        user=session.get("user", "admin"),
        role=session.get("role", "owner"),
        permissions=session.get("permissions", ["all"]),
        branding=load_branding()
    )

LATEST_PAPER_VERSION_CACHE = {"version": "26.3", "ts": 0}

def get_latest_paper_version():
    global LATEST_PAPER_VERSION_CACHE
    now = time.time()
    if now - LATEST_PAPER_VERSION_CACHE["ts"] < 300:
        return LATEST_PAPER_VERSION_CACHE["version"]

    try:
        req = urllib.request.Request(
            "https://fill.papermc.io/v3/projects/paper",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"}
        )
        with urllib.request.urlopen(req, timeout=4) as r:
            d = json.loads(r.read())
            v_dict = d.get("versions", {})
            for group, vers in v_dict.items():
                for v in vers:
                    if "-" not in v:
                        LATEST_PAPER_VERSION_CACHE["version"] = v
                        LATEST_PAPER_VERSION_CACHE["ts"] = now
                        return v
    except Exception:
        pass

    return LATEST_PAPER_VERSION_CACHE["version"]

@app.route("/api/software/latest", methods=["GET"])
@login_required
def api_software_latest():
    sw = request.args.get("software", "paper").lower().strip()
    ver = get_latest_paper_version()
    return jsonify({
        "success": True,
        "software": sw,
        "latest_version": ver,
        "display_label": f"Paper {ver}"
    })

@app.route("/api/status")
@login_required
def api_status():
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    jar_exists = os.path.exists(os.path.join(SERVER_DIR, "server.jar"))
    mc_running = server_runner.is_running()
    mc_pid, mc_mem_mb, _ = server_runner.get_process_info()

    # Read active OPs
    ops = []
    ops_file = os.path.join(SERVER_DIR, "ops.json")
    if os.path.exists(ops_file):
        try:
            with open(ops_file, "r") as f:
                ops = json.load(f)
        except Exception:
            pass

    # Read Banned players
    banned = []
    ban_file = os.path.join(SERVER_DIR, "banned-players.json")
    if os.path.exists(ban_file):
        try:
            with open(ban_file, "r") as f:
                banned = json.load(f)
        except Exception:
            pass

    # Whitelist
    whitelist_count = 0
    wl_file = os.path.join(SERVER_DIR, "whitelist.json")
    if os.path.exists(wl_file):
        try:
            with open(wl_file, "r") as f:
                whitelist_count = len(json.load(f))
        except Exception:
            pass

    uptime_sec = int(time.time() - START_TIME)
    ping_info = ping_mc()

    service_active = False
    try:
        res = subprocess.run(["sudo", "systemctl", "is-active", "fiesta"], capture_output=True, text=True, timeout=2)
        service_active = (res.stdout.strip() == "active")
    except Exception:
        pass

    return jsonify({
        "server_running": mc_running,
        "service_active": service_active,
        "pid": mc_pid,
        "cpu_usage": cpu_percent,
        "ram_used_mb": round(mem.used / (1024 * 1024), 1),
        "ram_total_mb": round(mem.total / (1024 * 1024), 1),
        "ram_percent": mem.percent,
        "mc_memory_mb": mc_mem_mb,
        "disk_used_gb": round(disk.used / (1024 * 1024 * 1024), 1),
        "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 1),
        "disk_percent": disk.percent,
        "uptime_seconds": uptime_sec,
        "ops_count": len(ops),
        "bans_count": len(banned),
        "whitelist_count": whitelist_count,
        "version": "Active",
        "platform": f"{platform.system()} ({platform.machine()})",
        "os_platform": platform.system(),
        "server_installed": jar_exists,
        "latest_paper_version": get_latest_paper_version(),
        "server_dir": SERVER_DIR,
        "java_version": detect_java_version_str(),
        "runtime_config": server_runner.load_runtime_config(),
        "mc_ping": ping_info
    })

@app.route("/api/server/power", methods=["POST"])
@login_required
def api_server_power():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "power" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Power permission required."}), 403

    data = request.get_json() or {}
    action = data.get("action", "").strip()

    if action == "start":
        def start_worker():
            server_runner.start()
        threading.Thread(target=start_worker, daemon=True).start()
        return jsonify({"success": True, "message": "Server startup sequence dispatched."})

    elif action == "stop":
        def stop_worker():
            server_runner.stop()
        threading.Thread(target=stop_worker, daemon=True).start()
        return jsonify({"success": True, "message": "World data saved; server shutdown dispatched."})

    elif action == "restart":
        def restart_worker():
            server_runner.restart()
        threading.Thread(target=restart_worker, daemon=True).start()
        return jsonify({"success": True, "message": "World data saved; server restart sequence dispatched."})

    return jsonify({"success": False, "message": "Unknown power action"}), 400

@app.route("/api/logs")
@login_required
def api_logs():
    lines_count = int(request.args.get("lines", 100))
    query = request.args.get("q", "").strip().lower()
    level = request.args.get("level", "ALL").upper()

    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": ["Log file not found."]})
    try:
        raw_lines = tail_file(LOG_FILE, lines_count * 2)

        filtered = []
        for line in raw_lines:
            if level != "ALL":
                if level == "WARN" and "WARN" not in line:
                    continue
                elif level == "ERROR" and "ERROR" not in line and "Exception" not in line:
                    continue
                elif level == "INFO" and "INFO" not in line:
                    continue
            if query and query not in line.lower():
                continue
            filtered.append(line)

        return jsonify({"logs": filtered[-lines_count:]})
    except Exception as e:
        return jsonify({"logs": [f"Error reading logs: {e}"]}), 500

@app.route("/api/log/download")
@login_required
def api_download_log():
    if os.path.exists(LOG_FILE):
        return send_file(LOG_FILE, as_attachment=True, download_name="fiesta-latest.log")
    return jsonify({"error": "Log file not found"}), 404

@app.route("/api/players")
@login_required
def api_players():
    usercache_file = os.path.join(SERVER_DIR, "usercache.json")
    ops_file = os.path.join(SERVER_DIR, "ops.json")
    ban_file = os.path.join(SERVER_DIR, "banned-players.json")

    users = []
    ops_names = set()
    banned_names = set()

    if os.path.exists(ops_file):
        try:
            with open(ops_file, "r") as f:
                for op in json.load(f):
                    ops_names.add(op.get("name", "").lower())
        except Exception:
            pass

    if os.path.exists(ban_file):
        try:
            with open(ban_file, "r") as f:
                for b in json.load(f):
                    banned_names.add(b.get("name", "").lower())
        except Exception:
            pass

    ping_info = ping_mc()
    online_names = [name.lower() for name in ping_info.get("player_sample", [])]

    if os.path.exists(usercache_file):
        try:
            with open(usercache_file, "r") as f:
                cached = json.load(f)
                for u in cached:
                    name = u.get("name")
                    is_online = name.lower() in online_names
                    users.append({
                        "name": name,
                        "uuid": u.get("uuid"),
                        "expires": u.get("expiresOn"),
                        "is_op": name.lower() in ops_names,
                        "is_banned": name.lower() in banned_names,
                        "is_online": is_online
                    })
        except Exception:
            pass

    # Sort so online players appear first, then alphabetically
    users.sort(key=lambda x: (not x["is_online"], x["name"].lower()))

    return jsonify({
        "players": users,
        "ops_count": len(ops_names),
        "banned_count": len(banned_names),
        "online_count": ping_info.get("players_online", 0)
    })

@app.route("/api/player/action", methods=["POST"])
@login_required
def api_player_action():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "players" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Player controls permission required."}), 403

    data = request.get_json() or {}
    player = data.get("player", "").strip()
    action = data.get("action", "").strip()
    param = data.get("param", "").strip()

    if not player or not action:
        return jsonify({"success": False, "message": "Missing player or action"}), 400

    cmd_map = {
        "op": f"op {player}",
        "deop": f"deop {player}",
        "kick": f"kick {player} {param or 'Kicked by administrator'}",
        "ban": f"ban {player} {param or 'Banned by administrator'}",
        "ban_ip": f"ban-ip {player} {param or 'Banned by administrator'}",
        "pardon": f"pardon {player}",
        "pardon_ip": f"pardon-ip {player}",
        "gamemode_survival": f"gamemode survival {player}",
        "gamemode_creative": f"gamemode creative {player}",
        "gamemode_adventure": f"gamemode adventure {player}",
        "gamemode_spectator": f"gamemode spectator {player}",
        "hardcore_spectator": f"gamemode spectator {player}",
        "kill": f"kill {player}",
        "heal": f"heal {player}",
        "feed": f"feed {player}",
        "clear": f"clear {player}",
        "tp_spawn": f"tp {player} -58423 69 -9669",
        "msg": f"msg {player} &6[Admin]&f {param}"
    }

    if action in cmd_map:
        success, msg = send_mc_command(cmd_map[action])
        return jsonify({"success": success, "message": msg})

    return jsonify({"success": False, "message": "Unknown player action"}), 400

def extract_item_display_name(item_dict):
    item_id = str(item_dict.get("id", ""))
    clean_title = item_id.split(":")[-1].replace("_", " ").title()
    comps = item_dict.get("components", {})
    if comps and "minecraft:custom_name" in comps:
        raw_cn = comps["minecraft:custom_name"]
        if isinstance(raw_cn, dict):
            extra = raw_cn.get("extra", [])
            if extra and isinstance(extra, list):
                txt = "".join(x.get("text", "") for x in extra if isinstance(x, dict))
                if txt:
                    return txt
            txt = raw_cn.get("text", "")
            if txt:
                return txt
        elif isinstance(raw_cn, str):
            try:
                parsed = json.loads(raw_cn)
                if isinstance(parsed, dict) and "text" in parsed:
                    return parsed["text"]
            except Exception:
                return raw_cn
    tag = item_dict.get("tag", {})
    if tag and "display" in tag and "Name" in tag["display"]:
        name_val = str(tag["display"]["Name"])
        try:
            parsed = json.loads(name_val)
            if isinstance(parsed, dict) and "text" in parsed:
                return parsed["text"]
        except Exception:
            return name_val
    return clean_title

@app.route("/api/player/inventory")
@login_required
def api_player_inventory():
    target = request.args.get("player", "").strip()
    uuid = request.args.get("uuid", "").strip()

    usercache_file = os.path.join(SERVER_DIR, "usercache.json")
    player_name = target

    # Resolve UUID if only name provided
    if not uuid and target:
        if os.path.exists(usercache_file):
            try:
                with open(usercache_file, "r") as f:
                    for u in json.load(f):
                        if u.get("name", "").lower() == target.lower():
                            uuid = u.get("uuid")
                            player_name = u.get("name")
                            break
            except Exception:
                pass

    if not uuid:
        return jsonify({"success": False, "message": "Player UUID not found"}), 404

    # If player name not resolved yet, lookup from UUID
    if not player_name and os.path.exists(usercache_file):
        try:
            with open(usercache_file, "r") as f:
                for u in json.load(f):
                    if u.get("uuid") == uuid:
                        player_name = u.get("name")
                        break
        except Exception:
            pass

    dat_path = os.path.join(SERVER_DIR, "world", "playerdata", f"{uuid}.dat")
    if not os.path.exists(dat_path):
        return jsonify({"success": False, "message": f"No playerdata file found for {player_name or uuid}"}), 404

    try:
        nbt = nbtlib.load(dat_path)

        hotbar = [None] * 9
        main_inv = [None] * 27
        armor = {"head": None, "chest": None, "legs": None, "feet": None}
        offhand = None

        raw_inv = nbt.get("Inventory", [])
        for item in raw_inv:
            s = int(item.get("Slot", -1))
            item_id = str(item.get("id", ""))
            count = int(item.get("count", item.get("Count", 1)))
            clean_name = extract_item_display_name(item)
            item_data = {
                "slot": s,
                "id": item_id,
                "name": clean_name,
                "count": count
            }
            if 0 <= s <= 8:
                hotbar[s] = item_data
            elif 9 <= s <= 35:
                main_inv[s - 9] = item_data
            elif s == 103:
                armor["head"] = item_data
            elif s == 102:
                armor["chest"] = item_data
            elif s == 101:
                armor["legs"] = item_data
            elif s == 100:
                armor["feet"] = item_data
            elif s == -106:
                offhand = item_data

        # Minecraft 1.20.5 / 1.21 modern equipment compound
        equip_compound = nbt.get("equipment", {})
        if equip_compound and isinstance(equip_compound, dict):
            for piece in ["head", "chest", "legs", "feet"]:
                if piece in equip_compound and equip_compound[piece]:
                    eq_item = equip_compound[piece]
                    eq_id = str(eq_item.get("id", ""))
                    if eq_id and eq_id != "minecraft:air":
                        eq_count = int(eq_item.get("count", eq_item.get("Count", 1)))
                        eq_name = extract_item_display_name(eq_item)
                        armor[piece] = {
                            "slot": piece,
                            "id": eq_id,
                            "name": eq_name,
                            "count": eq_count
                        }
            if "offhand" in equip_compound and equip_compound["offhand"]:
                eq_item = equip_compound["offhand"]
                eq_id = str(eq_item.get("id", ""))
                if eq_id and eq_id != "minecraft:air":
                    eq_count = int(eq_item.get("count", eq_item.get("Count", 1)))
                    eq_name = extract_item_display_name(eq_item)
                    offhand = {
                        "slot": "offhand",
                        "id": eq_id,
                        "name": eq_name,
                        "count": eq_count
                    }

        ender_items = []
        for item in nbt.get("EnderItems", []):
            s = int(item.get("Slot", -1))
            item_id = str(item.get("id", ""))
            count = int(item.get("count", item.get("Count", 1)))
            clean_name = extract_item_display_name(item)
            ender_items.append({
                "slot": s,
                "id": item_id,
                "name": clean_name,
                "count": count
            })

        pos = [round(float(p), 1) for p in nbt.get("Pos", [0, 0, 0])]
        health = round(float(nbt.get("Health", 20.0)), 1)
        food = int(nbt.get("foodLevel", 20))
        xp_level = int(nbt.get("XpLevel", 0))
        score = int(nbt.get("Score", 0))
        gamemode_num = int(nbt.get("playerGameType", 0))
        gamemodes = {0: "Survival", 1: "Creative", 2: "Adventure", 3: "Spectator"}
        dimension = str(nbt.get("Dimension", "minecraft:overworld"))

        # Check online status
        ping_info = ping_mc()
        online_sample = [n.lower() for n in ping_info.get("player_sample", [])]
        is_online = player_name.lower() in online_sample if player_name else False

        return jsonify({
            "success": True,
            "player": player_name or uuid,
            "uuid": uuid,
            "is_online": is_online,
            "health": health,
            "food": food,
            "xp_level": xp_level,
            "score": score,
            "gamemode": gamemodes.get(gamemode_num, "Survival"),
            "dimension": dimension.replace("minecraft:", "").replace("_", " ").title(),
            "pos": pos,
            "armor": armor,
            "offhand": offhand,
            "hotbar": hotbar,
            "main_inventory": main_inv,
            "ender_items": ender_items
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error parsing player inventory: {str(e)}"}), 500

@app.route("/api/player/inventory/give", methods=["POST"])
@login_required
def api_player_inventory_give():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "players" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Player controls permission required."}), 403

    data = request.get_json() or {}
    player = data.get("player", "").strip()
    item = data.get("item", "").strip()
    count = int(data.get("count", 1))

    if not player or not item:
        return jsonify({"success": False, "message": "Player and item required"}), 400

    item_id = item if ":" in item else f"minecraft:{item}"
    success, msg = send_mc_command(f"give {player} {item_id} {count}")
    return jsonify({"success": success, "message": f"Issued: give {player} {item_id} {count}"})

@app.route("/api/player/inventory/clear", methods=["POST"])
@login_required
def api_player_inventory_clear():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "players" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Player controls permission required."}), 403

    data = request.get_json() or {}
    player = data.get("player", "").strip()
    item = data.get("item", "").strip()

    if not player:
        return jsonify({"success": False, "message": "Player name required"}), 400

    if item:
        item_id = item if ":" in item else f"minecraft:{item}"
        cmd = f"clear {player} {item_id}"
    else:
        cmd = f"clear {player}"

    success, msg = send_mc_command(cmd)
    return jsonify({"success": success, "message": f"Executed: {cmd}"})

@app.route("/api/mc-item-icon/<path:item_id>")
def api_mc_item_icon(item_id):
    clean = item_id.lower().replace("minecraft:", "").strip()
    clean = re.sub(r"[^a-z0-9_\-]", "", clean)
    cached = os.path.join(MCASSETS_DIR, f"{clean}.png")
    if os.path.exists(cached):
        return send_from_directory(MCASSETS_DIR, f"{clean}.png", mimetype="image/png", max_age=604800)

    # Dynamic fallback check if not cached yet
    for tmpl in [
        f"https://assets.mcasset.cloud/1.21.1/assets/minecraft/textures/item/{clean}.png",
        f"https://assets.mcasset.cloud/1.21.1/assets/minecraft/textures/block/{clean}.png",
        f"https://raw.githubusercontent.com/PrismarineJS/minecraft-assets/master/data/1.21.1/items/{clean}.png"
    ]:
        try:
            req = urllib.request.Request(tmpl, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) > 50:
                        os.makedirs(MCASSETS_DIR, exist_ok=True)
                        with open(cached, "wb") as f_out:
                            f_out.write(data)
                        return send_from_directory(MCASSETS_DIR, f"{clean}.png", mimetype="image/png", max_age=604800)
        except Exception:
            continue

    return jsonify({"error": "Icon not found"}), 404

@app.route("/api/mc-items-list")
def api_mc_items_list():
    catalog_path = os.path.join(MCASSETS_DIR, "catalog.json")
    if os.path.exists(catalog_path):
        return send_from_directory(MCASSETS_DIR, "catalog.json", mimetype="application/json", max_age=86400)
    return jsonify([])

# ── Portal Branding & Customization APIs ──────────────────────

@app.route("/api/system/java", methods=["GET"])
@login_required
def api_system_java():
    j_bin = detect_java_bin()
    ver_str = detect_java_version_str()
    major_ver = None
    m = re.search(r'version\s+"(\d+)', ver_str)
    if m:
        major_ver = int(m.group(1))
    elif "1.8." in ver_str:
        major_ver = 8

    info = {
        "installed": bool(j_bin),
        "path": j_bin,
        "version_str": ver_str,
        "major_version": major_ver,
        "platform": platform.system(),
        "arch": platform.machine(),
        "is_compatible_1_21": bool(major_ver and major_ver >= 21),
        "recommendation": "Java 21 (Temurin / OpenJDK) recommended for Minecraft 1.20.5 - 1.21.x"
    }
    return jsonify({"success": True, "java": info})

@app.route("/api/branding/icon/upload", methods=["POST"])
@login_required
def api_upload_branding_icon():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "parameters" not in curr_perms and "access" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Parameter or Access management required."}), 403

    if "icon" not in request.files and "file" not in request.files:
        return jsonify({"success": False, "message": "No image file uploaded."}), 400

    file = request.files.get("icon") or request.files.get("file")
    if not file or not file.filename:
        return jsonify({"success": False, "message": "No file selected."}), 400

    allowed_exts = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico", ".gif"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        return jsonify({"success": False, "message": f"Unsupported file format ({ext}). Allowed: PNG, SVG, JPG, WEBP, ICO."}), 400

    upload_dir = os.path.join(STATIC_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"branding_logo_{int(time.time())}{ext}"
    target_path = os.path.join(upload_dir, filename)
    file.save(target_path)

    icon_url = f"/static/uploads/{filename}"
    branding = load_branding()
    branding["header_icon"] = "custom"
    branding["header_icon_custom"] = icon_url
    save_branding(branding)

    return jsonify({
        "success": True,
        "message": "Brand logo uploaded and applied successfully!",
        "icon_url": icon_url,
        "branding": branding
    })

@app.route("/api/branding", methods=["GET"])
def api_get_branding():
    return jsonify({"success": True, "branding": load_branding()})

@app.route("/api/branding", methods=["POST"])
@login_required
def api_save_branding():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "parameters" not in curr_perms and "access" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Parameter or Access management required."}), 403

    data = request.get_json() or {}
    cur = load_branding()

    brand_name = data.get("brand_name", cur.get("brand_name", "FIESTA-LINK")).strip()
    tagline = data.get("tagline", cur.get("tagline", "The Reliable Choice")).strip()
    model_number = data.get("model_number", cur.get("model_number", "Model No. FS-GATEWAY-PRO")).strip()
    browser_title = data.get("browser_title", cur.get("browser_title", f"{brand_name} | Console")).strip()
    footer_text = data.get("footer_text", cur.get("footer_text", "Made by Fiesta and it's developers, Mockup UI of Legacy TP-Link Portal")).strip()
    server_desc = data.get("server_desc", cur.get("server_desc", "Server Gateway Console")).strip()
    header_icon = data.get("header_icon", cur.get("header_icon", "tplink")).strip()
    header_icon_custom = data.get("header_icon_custom", cur.get("header_icon_custom", "")).strip()

    if not brand_name:
        return jsonify({"success": False, "message": "Brand name cannot be blank."}), 400

    new_branding = {
        "brand_name": brand_name,
        "tagline": tagline,
        "model_number": model_number,
        "browser_title": browser_title,
        "footer_text": footer_text,
        "server_desc": server_desc,
        "header_icon": header_icon,
        "header_icon_custom": header_icon_custom
    }
    save_branding(new_branding)
    return jsonify({"success": True, "message": "Portal branding updated successfully!", "branding": new_branding})

@app.route("/api/branding/reset", methods=["POST"])
@login_required
def api_reset_branding():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "parameters" not in curr_perms and "access" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied."}), 403

    save_branding(DEFAULT_BRANDING.copy())
    return jsonify({"success": True, "message": "Branding reset to factory default.", "branding": DEFAULT_BRANDING.copy()})

# ── Sub-Users & Access Control APIs (Aternos Style) ───────────
@app.route("/api/access/users", methods=["GET"])
@login_required
def api_get_subusers():
    users = load_users()
    clean_list = []
    for uname, u in users.items():
        clean_list.append({
            "username": uname,
            "role": u.get("role", "moderator"),
            "permissions": u.get("permissions", []),
            "status": u.get("status", "active"),
            "created_at": u.get("created_at", "N/A")
        })
    return jsonify({
        "success": True,
        "users": clean_list,
        "current_user": session.get("user", "admin"),
        "current_role": session.get("role", "owner"),
        "current_permissions": session.get("permissions", ["all"])
    })

@app.route("/api/access/users", methods=["POST"])
@login_required
def api_create_subuser():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "access" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Access management required."}), 403

    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "moderator").strip()
    permissions = data.get("permissions", [])

    if not username or not re.match(r"^[a-zA-Z0-9_\-]{3,24}$", username):
        return jsonify({"success": False, "message": "Username must be 3-24 alphanumeric characters."}), 400
    if not password or len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long."}), 400

    users = load_users()
    if username.lower() in [u.lower() for u in users.keys()] or username.lower() == ADMIN_USER.lower():
        return jsonify({"success": False, "message": f"User '{username}' already exists."}), 400

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    users[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "role": role,
        "permissions": permissions,
        "created_at": now_str,
        "status": "active"
    }
    save_users(users)
    return jsonify({"success": True, "message": f"Sub-user '{username}' created successfully."})

@app.route("/api/access/users/<username>", methods=["PUT"])
@login_required
def api_update_subuser(username):
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "access" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Access management required."}), 403

    users = load_users()
    target_key = None
    for k in users.keys():
        if k.lower() == username.lower():
            target_key = k
            break

    if not target_key:
        return jsonify({"success": False, "message": "User not found."}), 404

    data = request.get_json() or {}
    user_entry = users[target_key]

    if user_entry.get("role") == "owner" and session.get("user") != target_key:
        return jsonify({"success": False, "message": "Cannot modify primary owner account."}), 403

    if "role" in data and user_entry.get("role") != "owner":
        user_entry["role"] = str(data["role"])
    if "permissions" in data and user_entry.get("role") != "owner":
        user_entry["permissions"] = list(data["permissions"])
    if "status" in data and user_entry.get("role") != "owner":
        user_entry["status"] = "active" if data["status"] == "active" else "disabled"
    if "password" in data and data["password"]:
        pwd = str(data["password"]).strip()
        if len(pwd) >= 6:
            user_entry["password_hash"] = hash_password(pwd)
        else:
            return jsonify({"success": False, "message": "Password must be at least 6 characters long."}), 400

    users[target_key] = user_entry
    save_users(users)
    return jsonify({"success": True, "message": f"Sub-user '{target_key}' updated successfully."})

@app.route("/api/access/users/<username>", methods=["DELETE"])
@login_required
def api_delete_subuser(username):
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "access" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Access management required."}), 403

    users = load_users()
    target_key = None
    for k in users.keys():
        if k.lower() == username.lower():
            target_key = k
            break

    if not target_key:
        return jsonify({"success": False, "message": "User not found."}), 404

    if users[target_key].get("role") == "owner" or target_key == ADMIN_USER:
        return jsonify({"success": False, "message": "Cannot delete primary owner account."}), 400
    if target_key == session.get("user"):
        return jsonify({"success": False, "message": "Cannot delete your own active account."}), 400

    del users[target_key]
    save_users(users)
    return jsonify({"success": True, "message": f"Sub-user '{target_key}' deleted."})

# ── Server Software & Version Management (Aternos Style) ─────
def resolve_software_download(software, version, build="latest"):
    software = software.lower().strip()
    version = version.strip()

    if software == "purpur":
        if build == "latest":
            url_meta = f"https://api.purpurmc.org/v2/purpur/{version}"
            req = urllib.request.Request(url_meta, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
            with urllib.request.urlopen(req, timeout=5) as r:
                d = json.loads(r.read())
                build = d.get("builds", {}).get("latest")
                if not build:
                    raise ValueError(f"No builds found for Purpur {version}")
        download_url = f"https://api.purpurmc.org/v2/purpur/{version}/{build}/download"
        return download_url, f"purpur-{version}-{build}.jar", f"Purpur {version} (Build #{build})"

    elif software == "paper":
        url_meta = f"https://fill.papermc.io/v3/projects/paper/versions/{version}"
        req = urllib.request.Request(url_meta, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.loads(r.read())
            builds = d.get("builds", [])
            if not builds:
                raise ValueError(f"No builds found for Paper {version}")
            target_build = max(builds, key=lambda b: int(b) if str(b).isdigit() else 0) if build == "latest" else build

        url_build = f"https://fill.papermc.io/v3/projects/paper/versions/{version}/builds/{target_build}"
        req_b = urllib.request.Request(url_build, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(req_b, timeout=5) as r_b:
            d_b = json.loads(r_b.read())
            dl_info = d_b.get("downloads", {}).get("server:default", {})
            download_url = dl_info.get("url")
            filename = dl_info.get("name", f"paper-{version}-{target_build}.jar")
            if not download_url:
                raise ValueError(f"No download URL found for Paper {version} build {target_build}")
            return download_url, filename, f"Paper {version} (Build #{target_build})"

    elif software == "vanilla":
        req = urllib.request.Request("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(req, timeout=5) as r:
            manifest = json.loads(r.read())
            matched = [v for v in manifest.get("versions", []) if v.get("id") == version]
            if not matched:
                raise ValueError(f"Version {version} not found in Mojang release manifest")
            pkg_url = matched[0]["url"]

        req_pkg = urllib.request.Request(pkg_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(req_pkg, timeout=5) as r_pkg:
            pkg_data = json.loads(r_pkg.read())
            download_url = pkg_data.get("downloads", {}).get("server", {}).get("url")
            if not download_url:
                raise ValueError(f"Server download not available for Vanilla {version}")
            return download_url, f"vanilla-{version}-server.jar", f"Mojang Vanilla {version}"

    elif software == "fabric":
        loaders_url = "https://meta.fabricmc.net/v2/versions/loader"
        req = urllib.request.Request(loaders_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(req, timeout=5) as r:
            loaders = json.loads(r.read())
            loader_ver = loaders[0]["version"]

        download_url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_ver}/1.0.1/server/jar"
        return download_url, f"fabric-server-mc.{version}-loader.{loader_ver}.jar", f"Fabric {version} (Loader {loader_ver})"

    elif software == "spigot":
        download_url = f"https://download.getbukkit.org/spigot/spigot-{version}.jar"
        return download_url, f"spigot-{version}.jar", f"Spigot {version}"

    else:
        raise ValueError(f"Unsupported software engine: {software}")

@app.route("/api/software/info", methods=["GET"])
@login_required
def api_software_info():
    jar_path = os.path.join(SERVER_DIR, "server.jar")
    bak_path = os.path.join(SERVER_DIR, "server.jar.bak")
    meta_path = os.path.join(SERVER_DIR, "installed_software.json")

    has_jar = os.path.exists(jar_path)
    info = {
        "installed": has_jar,
        "software": "Purpur" if has_jar else "None",
        "version": "1.21.11" if has_jar else "Not installed",
        "build": "Build #2568" if has_jar else "N/A",
        "jar_size_mb": 0,
        "has_backup": os.path.exists(bak_path),
        "backup_size_mb": round(os.path.getsize(bak_path) / (1024*1024), 1) if os.path.exists(bak_path) else 0,
        "installed_at": "N/A",
        "java_version": detect_java_version_str(),
        "runtime_config": server_runner.load_runtime_config()
    }

    if os.path.exists(jar_path):
        info["jar_size_mb"] = round(os.path.getsize(jar_path) / (1024*1024), 1)
        info["installed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(jar_path)))

    if os.path.exists(meta_path):
        try:
            with open(meta_path) as f:
                info.update(json.load(f))
        except Exception:
            pass
    else:
        try:
            with zipfile.ZipFile(jar_path, "r") as zf:
                if "version.json" in zf.namelist():
                    vdata = json.loads(zf.read("version.json"))
                    info["version"] = vdata.get("id", info["version"])
        except Exception:
            pass

    try:
        res = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=2)
        java_out = res.stderr or res.stdout
        info["java_version"] = java_out.splitlines()[0] if java_out else "OpenJDK 21"
    except Exception:
        pass

    return jsonify({"success": True, "info": info})

@app.route("/api/software/versions", methods=["GET"])
@login_required
def api_software_versions():
    sw = request.args.get("software", "purpur").lower().strip()
    versions = []

    try:
        if sw == "purpur":
            req = urllib.request.Request("https://api.purpurmc.org/v2/purpur", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
            with urllib.request.urlopen(req, timeout=4) as r:
                d = json.loads(r.read())
                raw_vers = d.get("versions", [])
                versions = list(reversed(raw_vers))
        elif sw == "paper":
            req = urllib.request.Request("https://fill.papermc.io/v3/projects/paper", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
            with urllib.request.urlopen(req, timeout=4) as r:
                d = json.loads(r.read())
                v_dict = d.get("versions", {})
                all_v = []
                for major in ["26.3", "26.2", "26.1", "1.21", "1.20", "1.19", "1.18", "1.17", "1.16"]:
                    if major in v_dict:
                        all_v.extend(v_dict[major])
                versions = all_v if all_v else ["26.3", "26.2", "26.1.2", "1.21.11", "1.21.10", "1.21.4", "1.20.4"]
        elif sw == "vanilla":
            req = urllib.request.Request("https://launchermeta.mojang.com/mc/game/version_manifest_v2.json", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
            with urllib.request.urlopen(req, timeout=4) as r:
                d = json.loads(r.read())
                versions = [v["id"] for v in d.get("versions", []) if v.get("type") == "release"][:40]
        elif sw == "fabric":
            req = urllib.request.Request("https://meta.fabricmc.net/v2/versions/game", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
            with urllib.request.urlopen(req, timeout=4) as r:
                d = json.loads(r.read())
                versions = [v["version"] for v in d if v.get("stable")][:40]
        elif sw == "spigot":
            versions = ["26.3", "26.2", "26.1.2", "1.21.11", "1.21.4", "1.20.4", "1.19.4", "1.18.2", "1.16.5"]
    except Exception as e:
        versions = ["26.3", "26.2", "26.1.2", "1.21.11", "1.21.10", "1.21.4", "1.20.4", "1.19.4", "1.18.2", "1.16.5"]

    return jsonify({"success": True, "software": sw, "versions": versions})

@app.route("/api/software/install", methods=["POST"])
@login_required
def api_software_install():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "software" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Software management required."}), 403

    data = request.get_json() or {}
    software = data.get("software", "purpur").lower().strip()
    version = data.get("version", "1.21.11").strip()
    build = data.get("build", "latest").strip()

    try:
        download_url, filename, label = resolve_software_download(software, version, build)
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to resolve download URL: {str(e)}"}), 400

    jar_path = os.path.join(SERVER_DIR, "server.jar")
    bak_path = os.path.join(SERVER_DIR, "server.jar.bak")
    tmp_path = os.path.join(SERVER_DIR, f"server.jar.{int(time.time())}.tmp")
    meta_path = os.path.join(SERVER_DIR, "installed_software.json")

    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp_path, "wb") as f_out:
            shutil.copyfileobj(resp, f_out)

        dl_size = os.path.getsize(tmp_path)
        if dl_size < 3 * 1024 * 1024:
            if os.path.exists(tmp_path): os.remove(tmp_path)
            return jsonify({"success": False, "message": f"Downloaded jar too small ({dl_size} bytes), download aborted."}), 500

        had_server = os.path.exists(jar_path)
        if had_server:
            send_mc_command("save-all")
            send_mc_command(f"say [Server] Installing {label}, server restarting in a moment...")
            time.sleep(1.5)
            server_runner.stop()
            time.sleep(1)
            shutil.copy2(jar_path, bak_path)

        shutil.move(tmp_path, jar_path)

        # Auto-accept EULA
        eula_file = os.path.join(SERVER_DIR, "eula.txt")
        if not os.path.exists(eula_file) or data.get("auto_eula", True):
            try:
                with open(eula_file, "w") as f_eula:
                    f_eula.write("# By changing the setting below to TRUE you are indicating your agreement to the Mojang EULA (https://aka.ms/MinecraftEULA).\neula=true\n")
            except Exception:
                pass

        # Ensure default server.properties if missing
        props_file = os.path.join(SERVER_DIR, "server.properties")
        if not os.path.exists(props_file):
            try:
                with open(props_file, "w") as f_props:
                    f_props.write(
                        "#Minecraft server properties - Configured by FiestaPanel\n"
                        "server-port=25565\n"
                        "gamemode=survival\n"
                        "difficulty=easy\n"
                        "pvp=true\n"
                        "max-players=20\n"
                        "online-mode=true\n"
                        "enable-rcon=false\n"
                        "motd=A Minecraft Server Powered by FiestaPanel\n"
                    )
            except Exception:
                pass

        # Memory configuration
        if "ram_gb" in data:
            try:
                ram_val = int(data["ram_gb"])
                rt_cfg = server_runner.load_runtime_config()
                rt_cfg["max_ram"] = f"{ram_val}G"
                server_runner.save_runtime_config(rt_cfg)
            except Exception:
                pass

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(meta_path, "w") as f_meta:
            json.dump({
                "software": software.title(),
                "version": version,
                "build": build,
                "installed_at": now_str,
                "jar_name": filename,
                "label": label
            }, f_meta, indent=2)

        # Ensure appropriate addon directory exists for software engine
        if software == "fabric":
            os.makedirs(os.path.join(SERVER_DIR, "mods"), exist_ok=True)
            os.makedirs(os.path.join(SERVER_DIR, "mods", "disabled"), exist_ok=True)
        elif software in ["purpur", "paper", "spigot"]:
            os.makedirs(os.path.join(SERVER_DIR, "plugins"), exist_ok=True)
            os.makedirs(os.path.join(SERVER_DIR, "plugins", "disabled"), exist_ok=True)

        if data.get("autostart", True):
            server_runner.start()

        return jsonify({
            "success": True,
            "message": f"Successfully installed {label}! Server is starting up.",
            "label": label,
            "installed_at": now_str
        })
    except Exception as e:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        return jsonify({"success": False, "message": f"Installation failed: {str(e)}"}), 500

@app.route("/api/software/rollback", methods=["POST"])
@login_required
def api_software_rollback():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "software" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Software management required."}), 403

    jar_path = os.path.join(SERVER_DIR, "server.jar")
    bak_path = os.path.join(SERVER_DIR, "server.jar.bak")
    meta_path = os.path.join(SERVER_DIR, "installed_software.json")

    if not os.path.exists(bak_path):
        return jsonify({"success": False, "message": "No backup server.jar.bak file found to restore."}), 400

    try:
        send_mc_command("save-all")
        time.sleep(1)
        subprocess.run(["sudo", "systemctl", "stop", "fiesta"])
        time.sleep(1)

        current_tmp = os.path.join(SERVER_DIR, "server.jar.pre_rollback")
        if os.path.exists(jar_path):
            shutil.move(jar_path, current_tmp)
        shutil.copy2(bak_path, jar_path)

        if os.path.exists(meta_path):
            try: os.remove(meta_path)
            except Exception: pass

        subprocess.run(["sudo", "systemctl", "start", "fiesta"])
        return jsonify({"success": True, "message": "Successfully rolled back to previous server jar and restarted service."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Rollback failed: {str(e)}"}), 500

@app.route("/api/bans")
@login_required
def api_get_bans():
    ban_file = os.path.join(SERVER_DIR, "banned-players.json")
    banned = []
    if os.path.exists(ban_file):
        try:
            with open(ban_file, "r") as f:
                banned = json.load(f)
        except Exception:
            pass
    return jsonify({"bans": banned, "total": len(banned)})

@app.route("/api/ops")
@login_required
def api_get_ops():
    ops_file = os.path.join(SERVER_DIR, "ops.json")
    ops = []
    if os.path.exists(ops_file):
        try:
            with open(ops_file, "r") as f:
                ops = json.load(f)
        except Exception:
            pass
    return jsonify({"ops": ops, "total": len(ops)})

@app.route("/api/whitelist")
@login_required
def api_get_whitelist():
    wl_file = os.path.join(SERVER_DIR, "whitelist.json")
    wl = []
    if os.path.exists(wl_file):
        try:
            with open(wl_file, "r") as f:
                wl = json.load(f)
        except Exception:
            pass

    # Read whitelist status from server.properties
    enabled = False
    props_path = os.path.join(SERVER_DIR, "server.properties")
    if os.path.exists(props_path):
        try:
            with open(props_path, "r") as f:
                for line in f:
                    if line.strip().startswith("white-list="):
                        enabled = line.strip().split("=", 1)[1].lower() == "true"
                        break
        except Exception:
            pass

    return jsonify({"enabled": enabled, "whitelist": wl, "total": len(wl)})

@app.route("/api/whitelist/action", methods=["POST"])
@login_required
def api_whitelist_action():
    data = request.get_json() or {}
    action = data.get("action", "").strip()
    name = data.get("name", "").strip()

    if action == "toggle":
        enabled = data.get("enabled", False)
        cmd = "whitelist on" if enabled else "whitelist off"
        success, msg = send_mc_command(cmd)
        return jsonify({"success": success, "message": f"Whitelist {'enabled' if enabled else 'disabled'}"})

    elif action == "add":
        if not name:
            return jsonify({"success": False, "message": "Player name required"}), 400
        success, msg = send_mc_command(f"whitelist add {name}")
        return jsonify({"success": success, "message": f"Added {name} to whitelist"})

    elif action == "remove":
        if not name:
            return jsonify({"success": False, "message": "Player name required"}), 400
        success, msg = send_mc_command(f"whitelist remove {name}")
        return jsonify({"success": success, "message": f"Removed {name} from whitelist"})

    return jsonify({"success": False, "message": "Unknown action"}), 400

@app.route("/api/server/properties", methods=["GET", "POST"])
@login_required
def api_server_properties():
    props_path = os.path.join(SERVER_DIR, "server.properties")
    if not os.path.exists(props_path):
        return jsonify({"success": False, "message": "server.properties not found"}), 404

    if request.method == "GET":
        props = {}
        try:
            with open(props_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        props[k.strip()] = v.strip()
            return jsonify({"success": True, "properties": props})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    elif request.method == "POST":
        updates = request.get_json() or {}
        if not updates:
            return jsonify({"success": False, "message": "No updates provided"}), 400

        try:
            # Backup
            shutil.copy2(props_path, props_path + ".bak")

            lines = []
            seen = set()
            with open(props_path, "r") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        k = stripped.split("=", 1)[0].strip()
                        if k in updates:
                            lines.append(f"{k}={updates[k]}\n")
                            seen.add(k)
                        else:
                            lines.append(line)
                    else:
                        lines.append(line)

            for k, v in updates.items():
                if k not in seen:
                    lines.append(f"{k}={v}\n")

            with open(props_path, "w") as f:
                f.writelines(lines)

            return jsonify({"success": True, "message": "Server properties updated successfully (restart needed for some settings)!"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/server/icon", methods=["GET"])
def api_server_icon():
    icon_path = os.path.join(SERVER_DIR, "server-icon.png")
    if os.path.exists(icon_path):
        return send_file(icon_path, mimetype="image/png")
    return jsonify({"error": "No icon found"}), 404

@app.route("/api/server/icon/upload", methods=["POST"])
@login_required
def api_server_icon_upload():
    if "icon" not in request.files:
        return jsonify({"success": False, "message": "No image file provided"}), 400
    file = request.files["icon"]
    if not file.filename:
        return jsonify({"success": False, "message": "No file selected"}), 400

    try:
        image = Image.open(file.stream)
        image = image.convert("RGBA")
        image = image.resize((64, 64), Image.Resampling.LANCZOS)
        icon_path = os.path.join(SERVER_DIR, "server-icon.png")
        image.save(icon_path, format="PNG")
        return jsonify({"success": True, "message": "Server icon updated & resized to 64x64 PNG! Restart server to see it in multiplayer list."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to process icon: {str(e)}"}), 500

@app.route("/api/broadcast", methods=["POST"])
@login_required
def api_broadcast():
    data = request.get_json() or {}
    msg = data.get("message", "").strip()
    msg_type = data.get("type", "chat")

    if not msg:
        return jsonify({"success": False, "message": "Message cannot be empty"}), 400

    if msg_type == "title":
        send_mc_command(f'title @a title {{"text":"{msg}","color":"gold","bold":true}}')
    elif msg_type == "actionbar":
        send_mc_command(f'title @a actionbar {{"text":"{msg}","color":"yellow"}}')
    else:
        send_mc_command(f'say {msg}')

    return jsonify({"success": True, "message": "Broadcast sent!"})

@app.route("/api/command", methods=["POST"])
@login_required
def api_command():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "console" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Console permission required."}), 403

    data = request.get_json() or {}
    cmd = data.get("command", "").strip()
    if not cmd:
        return jsonify({"success": False, "message": "Command is empty"}), 400

    success, msg = send_mc_command(cmd)
    return jsonify({"success": success, "message": msg})

# ── Plugins Management ───────────────────────────────────────────────────────
@app.route("/api/plugins")
@login_required
def api_plugins():
    plugins_dir = os.path.join(SERVER_DIR, "plugins")
    plugins_list = []
    if os.path.exists(plugins_dir):
        for f in sorted(os.listdir(plugins_dir)):
            if f.endswith(".jar"):
                p = os.path.join(plugins_dir, f)
                if os.path.isfile(p):
                    size_kb = round(os.path.getsize(p) / 1024, 1)
                    plugins_list.append({
                        "name": f.replace(".jar", ""),
                        "filename": f,
                        "size_kb": size_kb
                    })
    return jsonify({"plugins": plugins_list, "total": len(plugins_list)})

@app.route("/api/plugins/disabled")
@login_required
def api_plugins_disabled():
    disabled_dir = os.path.join(SERVER_DIR, "plugins", "disabled")
    disabled_list = []
    if os.path.exists(disabled_dir):
        for f in sorted(os.listdir(disabled_dir)):
            p = os.path.join(disabled_dir, f)
            if os.path.isfile(p) and (f.endswith(".jar") or f.endswith(".bak")):
                size_kb = round(os.path.getsize(p) / 1024, 1)
                disabled_list.append({
                    "name": f.replace(".jar", "").replace(".bak", ""),
                    "filename": f,
                    "size_kb": size_kb
                })
    return jsonify({"disabled": disabled_list, "total": len(disabled_list)})

@app.route("/api/plugin/delete", methods=["POST"])
@login_required
def api_plugin_delete():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "Plugin name required"}), 400

    plugins_dir = os.path.join(SERVER_DIR, "plugins")
    disabled_dir = os.path.join(plugins_dir, "disabled")
    src = os.path.join(plugins_dir, f"{name}.jar")

    if not os.path.isfile(src):
        return jsonify({"success": False, "message": f"Plugin file not found: {name}.jar"}), 404

    os.makedirs(disabled_dir, exist_ok=True)
    dst = os.path.join(disabled_dir, f"{name}.jar")
    try:
        shutil.move(src, dst)
        return jsonify({"success": True, "message": f"{name} moved to disabled/ — restart server to unload."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/plugin/enable", methods=["POST"])
@login_required
def api_plugin_enable():
    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "message": "Filename required"}), 400

    plugins_dir = os.path.join(SERVER_DIR, "plugins")
    disabled_dir = os.path.join(plugins_dir, "disabled")
    src = os.path.join(disabled_dir, filename)

    if not os.path.isfile(src):
        return jsonify({"success": False, "message": f"Disabled plugin not found: {filename}"}), 404

    # Ensure extension is .jar
    target_name = filename[:-4] if filename.endswith(".bak") and filename.endswith(".jar.bak") else filename
    if not target_name.endswith(".jar"):
        target_name += ".jar"
    dst = os.path.join(plugins_dir, target_name)

    try:
        shutil.move(src, dst)
        return jsonify({"success": True, "message": f"{target_name} restored to active plugins/ — restart server to load."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/plugin/perm_delete", methods=["POST"])
@login_required
def api_plugin_perm_delete():
    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "message": "Filename required"}), 400

    disabled_dir = os.path.join(SERVER_DIR, "plugins", "disabled")
    target = os.path.join(disabled_dir, filename)

    if not os.path.isfile(target):
        return jsonify({"success": False, "message": f"File not found in disabled/: {filename}"}), 404

    try:
        os.remove(target)
        return jsonify({"success": True, "message": f"Permanently deleted {filename}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/plugin/upload", methods=["POST"])
@login_required
def api_plugin_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part in request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400
    if not file.filename.lower().endswith(".jar"):
        return jsonify({"success": False, "message": "Only .jar files are allowed"}), 400

    plugins_dir = os.path.join(SERVER_DIR, "plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    dst = os.path.join(plugins_dir, safe_name)
    try:
        file.save(dst)
        return jsonify({"success": True, "message": f"{safe_name} uploaded successfully! Restart server to load."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/plugins/search")
@login_required
def api_plugins_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"hits": [], "total_hits": 0})

    try:
        params = {
            "query": query,
            "facets": '[["project_type:plugin"]]',
            "limit": 15
        }
        url = "https://api.modrinth.com/v2/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "FiestaGateway/1.0 (admin@fiesta.net)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        hits = []
        for h in data.get("hits", []):
            hits.append({
                "project_id": h.get("project_id"),
                "slug": h.get("slug"),
                "title": h.get("title"),
                "description": h.get("description", ""),
                "author": h.get("author", "Unknown"),
                "downloads": h.get("downloads", 0),
                "icon_url": h.get("icon_url") or "",
                "categories": h.get("categories", [])
            })
        return jsonify({"success": True, "hits": hits, "total_hits": data.get("total_hits", len(hits))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "hits": []}), 500

@app.route("/api/plugin/install_online", methods=["POST"])
@login_required
def api_plugin_install_online():
    data = request.get_json() or {}
    project_id = data.get("project_id", "").strip()

    if not project_id:
        return jsonify({"success": False, "message": "Project ID required"}), 400

    try:
        loaders = '["paper","spigot","purpur","bukkit"]'
        url = f"https://api.modrinth.com/v2/project/{project_id}/version?" + urllib.parse.urlencode({"loaders": loaders})
        req = urllib.request.Request(url, headers={"User-Agent": "FiestaGateway/1.0 (admin@fiesta.net)"})

        versions = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                versions = json.loads(resp.read().decode())
        except Exception:
            pass

        if not versions:
            url_all = f"https://api.modrinth.com/v2/project/{project_id}/version"
            req_all = urllib.request.Request(url_all, headers={"User-Agent": "FiestaGateway/1.0 (admin@fiesta.net)"})
            with urllib.request.urlopen(req_all, timeout=8) as resp:
                versions = json.loads(resp.read().decode())

        if not versions:
            return jsonify({"success": False, "message": "No release versions found for this plugin."}), 404

        target_file = None
        for v in versions:
            files = v.get("files", [])
            for f in files:
                if f.get("primary", False) and f.get("filename", "").endswith(".jar"):
                    target_file = f
                    break
            if target_file:
                break
            for f in files:
                if f.get("filename", "").endswith(".jar"):
                    target_file = f
                    break
            if target_file:
                break

        if not target_file:
            return jsonify({"success": False, "message": "No valid .jar file found in project releases."}), 404

        download_url = target_file.get("url")
        filename = target_file.get("filename")

        plugins_dir = os.path.join(SERVER_DIR, "plugins")
        os.makedirs(plugins_dir, exist_ok=True)
        dest_path = os.path.join(plugins_dir, filename)

        dl_req = urllib.request.Request(download_url, headers={"User-Agent": "FiestaGateway/1.0 (admin@fiesta.net)"})
        with urllib.request.urlopen(dl_req, timeout=30) as resp, open(dest_path, "wb") as out_f:
            shutil.copyfileobj(resp, out_f)

        file_size_kb = round(os.path.getsize(dest_path) / 1024, 1)

        return jsonify({
            "success": True,
            "filename": filename,
            "size_kb": file_size_kb,
            "message": f"Successfully downloaded {filename} ({file_size_kb} KB)! Restart server to load."
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Download failed: {str(e)}"}), 500

# ── Addons & Mods Management (Cross-Platform Fabric / Forge / Bukkit Support) ──
def detect_addon_context():
    meta_path = os.path.join(SERVER_DIR, "installed_software.json")
    software = "Unknown"
    if os.path.isfile(meta_path):
        try:
            with open(meta_path) as f:
                software = json.load(f).get("software", "Unknown")
        except Exception:
            pass

    plugins_dir = os.path.join(SERVER_DIR, "plugins")
    mods_dir = os.path.join(SERVER_DIR, "mods")

    has_plugins_dir = os.path.isdir(plugins_dir)
    has_mods_dir = os.path.isdir(mods_dir)

    plugins_count = 0
    if has_plugins_dir:
        try:
            plugins_count = len([f for f in os.listdir(plugins_dir) if f.endswith(".jar") and os.path.isfile(os.path.join(plugins_dir, f))])
        except Exception:
            pass

    mods_count = 0
    if has_mods_dir:
        try:
            mods_count = len([f for f in os.listdir(mods_dir) if f.endswith(".jar") and os.path.isfile(os.path.join(mods_dir, f))])
        except Exception:
            pass

    sw_lower = software.lower()
    if any(m in sw_lower for m in ["fabric", "forge", "neoforge", "quilt"]):
        primary = "mods"
    elif any(p in sw_lower for p in ["purpur", "paper", "spigot", "bukkit", "folia"]):
        primary = "plugins"
    elif mods_count > 0 and plugins_count == 0:
        primary = "mods"
    else:
        primary = "plugins"

    return {
        "primary_addon_type": primary,
        "software": software,
        "plugins_count": plugins_count,
        "mods_count": mods_count,
        "has_plugins_dir": has_plugins_dir,
        "has_mods_dir": has_mods_dir
    }

@app.route("/api/addons/context")
@login_required
def api_addons_context():
    return jsonify(detect_addon_context())

@app.route("/api/mods")
@login_required
def api_mods():
    mods_dir = os.path.join(SERVER_DIR, "mods")
    mods_list = []
    if os.path.exists(mods_dir):
        for f in sorted(os.listdir(mods_dir)):
            if f.endswith(".jar"):
                p = os.path.join(mods_dir, f)
                if os.path.isfile(p):
                    size_kb = round(os.path.getsize(p) / 1024, 1)
                    mods_list.append({
                        "name": f.replace(".jar", ""),
                        "filename": f,
                        "size_kb": size_kb
                    })
    return jsonify({"mods": mods_list, "total": len(mods_list)})

@app.route("/api/mods/disabled")
@login_required
def api_mods_disabled():
    disabled_dir = os.path.join(SERVER_DIR, "mods", "disabled")
    disabled_list = []
    if os.path.exists(disabled_dir):
        for f in sorted(os.listdir(disabled_dir)):
            p = os.path.join(disabled_dir, f)
            if os.path.isfile(p) and (f.endswith(".jar") or f.endswith(".bak")):
                size_kb = round(os.path.getsize(p) / 1024, 1)
                disabled_list.append({
                    "name": f.replace(".jar", "").replace(".bak", ""),
                    "filename": f,
                    "size_kb": size_kb
                })
    return jsonify({"disabled": disabled_list, "total": len(disabled_list)})

@app.route("/api/mod/delete", methods=["POST"])
@login_required
def api_mod_delete():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "Mod name required"}), 400

    mods_dir = os.path.join(SERVER_DIR, "mods")
    disabled_dir = os.path.join(mods_dir, "disabled")
    src = os.path.join(mods_dir, f"{name}.jar")

    if not os.path.isfile(src):
        return jsonify({"success": False, "message": f"Mod file not found: {name}.jar"}), 404

    os.makedirs(disabled_dir, exist_ok=True)
    dst = os.path.join(disabled_dir, f"{name}.jar")
    try:
        shutil.move(src, dst)
        return jsonify({"success": True, "message": f"{name} moved to mods/disabled/ — restart server to unload."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/mod/enable", methods=["POST"])
@login_required
def api_mod_enable():
    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "message": "Filename required"}), 400

    mods_dir = os.path.join(SERVER_DIR, "mods")
    disabled_dir = os.path.join(mods_dir, "disabled")
    src = os.path.join(disabled_dir, filename)

    if not os.path.isfile(src):
        return jsonify({"success": False, "message": f"Disabled mod not found: {filename}"}), 404

    target_name = filename[:-4] if filename.endswith(".bak") and filename.endswith(".jar.bak") else filename
    if not target_name.endswith(".jar"):
        target_name += ".jar"
    dst = os.path.join(mods_dir, target_name)

    try:
        shutil.move(src, dst)
        return jsonify({"success": True, "message": f"{target_name} restored to active mods/ — restart server to load."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/mod/perm_delete", methods=["POST"])
@login_required
def api_mod_perm_delete():
    data = request.get_json() or {}
    filename = data.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "message": "Filename required"}), 400

    disabled_dir = os.path.join(SERVER_DIR, "mods", "disabled")
    target = os.path.join(disabled_dir, filename)

    if not os.path.isfile(target):
        return jsonify({"success": False, "message": f"File not found in disabled/: {filename}"}), 404

    try:
        os.remove(target)
        return jsonify({"success": True, "message": f"Permanently deleted {filename}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/mod/upload", methods=["POST"])
@login_required
def api_mod_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part in request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400
    if not file.filename.lower().endswith(".jar"):
        return jsonify({"success": False, "message": "Only .jar files are allowed"}), 400

    mods_dir = os.path.join(SERVER_DIR, "mods")
    os.makedirs(mods_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    dst = os.path.join(mods_dir, safe_name)
    try:
        file.save(dst)
        return jsonify({"success": True, "message": f"{safe_name} uploaded successfully! Restart server to load."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/mods/search")
@login_required
def api_mods_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"hits": [], "total_hits": 0})

    try:
        params = {
            "query": query,
            "facets": '[["project_type:mod"]]',
            "limit": 15
        }
        url = "https://api.modrinth.com/v2/search?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        hits = []
        for h in data.get("hits", []):
            hits.append({
                "project_id": h.get("project_id"),
                "slug": h.get("slug"),
                "title": h.get("title"),
                "description": h.get("description", ""),
                "author": h.get("author", "Unknown"),
                "downloads": h.get("downloads", 0),
                "icon_url": h.get("icon_url") or "",
                "categories": h.get("categories", [])
            })
        return jsonify({"success": True, "hits": hits, "total_hits": data.get("total_hits", len(hits))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "hits": []}), 500

@app.route("/api/mod/install_online", methods=["POST"])
@login_required
def api_mod_install_online():
    data = request.get_json() or {}
    project_id = data.get("project_id", "").strip()

    if not project_id:
        return jsonify({"success": False, "message": "Project ID required"}), 400

    try:
        loaders = '["fabric","quilt","forge","neoforge"]'
        url = f"https://api.modrinth.com/v2/project/{project_id}/version?" + urllib.parse.urlencode({"loaders": loaders})
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})

        versions = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                versions = json.loads(resp.read().decode())
        except Exception:
            pass

        if not versions:
            url_all = f"https://api.modrinth.com/v2/project/{project_id}/version"
            req_all = urllib.request.Request(url_all, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
            with urllib.request.urlopen(req_all, timeout=8) as resp:
                versions = json.loads(resp.read().decode())

        if not versions:
            return jsonify({"success": False, "message": "No release versions found for this mod."}), 404

        target_file = None
        for v in versions:
            files = v.get("files", [])
            for f in files:
                if f.get("primary", False) and f.get("filename", "").endswith(".jar"):
                    target_file = f
                    break
            if target_file:
                break
            for f in files:
                if f.get("filename", "").endswith(".jar"):
                    target_file = f
                    break
            if target_file:
                break

        if not target_file:
            return jsonify({"success": False, "message": "No valid .jar file found in project releases."}), 404

        download_url = target_file.get("url")
        filename = target_file.get("filename")

        mods_dir = os.path.join(SERVER_DIR, "mods")
        os.makedirs(mods_dir, exist_ok=True)
        dest_path = os.path.join(mods_dir, filename)

        dl_req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FiestaPanel/2.1"})
        with urllib.request.urlopen(dl_req, timeout=30) as resp, open(dest_path, "wb") as out_f:
            shutil.copyfileobj(resp, out_f)

        file_size_kb = round(os.path.getsize(dest_path) / 1024, 1)

        return jsonify({
            "success": True,
            "filename": filename,
            "size_kb": file_size_kb,
            "message": f"Successfully downloaded mod {filename} ({file_size_kb} KB)! Restart server to load."
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Download failed: {str(e)}"}), 500

# ── Backups ──────────────────────────────────────────────────────────────────
@app.route("/api/backups")
@login_required
def api_get_backups():
    paths = ['/home/ubuntu/*.tar.gz', '/home/ubuntu/*.tar.zst', '/home/ubuntu/backups/*.tar.*']
    files = []
    for p in paths:
        for f in glob.glob(p):
            if os.path.isfile(f):
                stat = os.stat(f)
                files.append({
                    'filename': os.path.basename(f),
                    'path': f,
                    'size_mb': round(stat.st_size / (1024 * 1024), 1),
                    'size_gb': round(stat.st_size / (1024 * 1024 * 1024), 2),
                    'mtime': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return jsonify({"backups": files, "total": len(files)})

@app.route("/api/backup/create", methods=["POST"])
@login_required
def api_create_backup():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "backups" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Backups permission required."}), 403

    def backup_task():
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = SERVER_CONFIG.get("backup_dir") or os.path.join(os.path.dirname(SERVER_DIR), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        target_tar = os.path.join(backup_dir, f"fiesta_backup_{ts}.tar.gz")
        send_mc_command("save-all")
        time.sleep(2)
        try:
            with tarfile.open(target_tar, "w:gz") as tar:
                tar.add(SERVER_DIR, arcname=os.path.basename(SERVER_DIR))
        except Exception as err:
            print("Backup creation error:", err)

    threading.Thread(target=backup_task, daemon=True).start()
    return jsonify({"success": True, "message": "Background backup archive initiated! Check Backups list shortly."})

@app.route("/api/backup/download")
@login_required
def api_download_backup():
    filename = request.args.get("filename", "").strip()
    safe_name = os.path.basename(filename)
    for folder in ['/home/ubuntu', '/home/ubuntu/backups']:
        p = os.path.join(folder, safe_name)
        if os.path.isfile(p):
            return send_file(p, as_attachment=True, download_name=safe_name)
    return jsonify({"error": "Backup file not found"}), 404

# ── File Manager ─────────────────────────────────────────────────────────────
def safe_fiesta_path(rel_path):
    rel_path = (rel_path or "").strip().lstrip("/")
    base_dir = os.path.realpath(SERVER_DIR)
    abs_path = os.path.realpath(os.path.join(base_dir, rel_path))
    if abs_path == base_dir or abs_path.startswith(base_dir + os.sep):
        return abs_path
    return None

def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{round(size_bytes / 1024, 1)} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{round(size_bytes / (1024 * 1024), 1)} MB"
    else:
        return f"{round(size_bytes / (1024 * 1024 * 1024), 2)} GB"

@app.route("/api/files/list")
@login_required
def api_files_list():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "filemanager" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: File manager permission required."}), 403

    rel_path = request.args.get("path", "").strip().lstrip("/")
    abs_path = safe_fiesta_path(rel_path)
    if not abs_path or not os.path.isdir(abs_path):
        return jsonify({"success": False, "message": "Invalid directory path"}), 404

    base_dir = os.path.realpath(SERVER_DIR)
    current_rel = os.path.relpath(abs_path, base_dir)
    if current_rel == ".":
        current_rel = ""

    parent_rel = ""
    if current_rel:
        parent_rel = os.path.dirname(current_rel)
        if parent_rel == ".":
            parent_rel = ""

    crumbs = [{"name": "fiesta", "path": ""}]
    if current_rel:
        parts = current_rel.split(os.sep)
        curr_p = ""
        for part in parts:
            curr_p = os.path.join(curr_p, part) if curr_p else part
            crumbs.append({"name": part, "path": curr_p})

    items = []
    editable_exts = {'txt', 'yml', 'yaml', 'json', 'properties', 'toml', 'cfg', 'log', 'sk', 'md', 'sh', 'env', 'conf', 'csv'}
    try:
        with os.scandir(abs_path) as entries:
            for entry in entries:
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                    st = entry.stat()
                    name = entry.name
                    item_rel = os.path.join(current_rel, name) if current_rel else name
                    ext = name.split(".")[-1].lower() if "." in name and not is_dir else ""
                    size_b = st.st_size if not is_dir else 0

                    items.append({
                        "name": name,
                        "path": item_rel,
                        "is_dir": is_dir,
                        "size_bytes": size_b,
                        "size_formatted": "-" if is_dir else format_file_size(size_b),
                        "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "extension": ext,
                        "is_editable": (ext in editable_exts or size_b < 500 * 1024) and not is_dir
                    })
                except Exception:
                    pass
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return jsonify({
            "success": True,
            "current_path": current_rel,
            "parent_path": parent_rel,
            "breadcrumbs": crumbs,
            "items": items,
            "total_items": len(items)
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/files/read")
@login_required
def api_files_read():
    rel_path = request.args.get("path", "").strip()
    abs_path = safe_fiesta_path(rel_path)
    if not abs_path or not os.path.isfile(abs_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    try:
        st = os.stat(abs_path)
        if st.st_size > 3 * 1024 * 1024:
            return jsonify({"success": False, "message": "File exceeds 3MB limit for web editor."}), 400

        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        return jsonify({
            "success": True,
            "path": rel_path,
            "filename": os.path.basename(abs_path),
            "size": st.st_size,
            "content": content
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/files/save", methods=["POST"])
@login_required
def api_files_save():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "filemanager" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: File manager permission required."}), 403

    data = request.get_json() or {}
    rel_path = data.get("path", "").strip()
    content = data.get("content", "")

    abs_path = safe_fiesta_path(rel_path)
    if not abs_path:
        return jsonify({"success": False, "message": "Access denied"}), 403

    try:
        if os.path.exists(abs_path):
            shutil.copy2(abs_path, abs_path + ".bak")

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        return jsonify({"success": True, "message": f"Saved {os.path.basename(abs_path)} successfully (backup created)!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/files/delete", methods=["POST"])
@login_required
def api_files_delete():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "filemanager" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: File manager permission required."}), 403

    data = request.get_json() or {}
    rel_path = data.get("path", "").strip()
    abs_path = safe_fiesta_path(rel_path)

    base_dir = os.path.realpath(SERVER_DIR)
    if not abs_path or abs_path == base_dir:
        return jsonify({"success": False, "message": "Cannot delete server root"}), 403

    try:
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        elif os.path.isfile(abs_path):
            os.remove(abs_path)
        return jsonify({"success": True, "message": f"Deleted {os.path.basename(abs_path)}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/files/upload", methods=["POST"])
@login_required
def api_files_upload():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "filemanager" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: File manager permission required."}), 403

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file attached"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "message": "No file selected"}), 400

    target_dir_rel = request.form.get("path", "").strip()
    abs_dir = safe_fiesta_path(target_dir_rel)
    if not abs_dir or not os.path.isdir(abs_dir):
        return jsonify({"success": False, "message": "Invalid target directory"}), 400

    safe_name = os.path.basename(file.filename)
    dst = os.path.join(abs_dir, safe_name)
    try:
        file.save(dst)
        return jsonify({"success": True, "message": f"Uploaded {safe_name} successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/files/mkdir", methods=["POST"])
@login_required
def api_files_mkdir():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "filemanager" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: File manager permission required."}), 403

    data = request.get_json() or {}
    parent_rel = data.get("path", "").strip()
    folder_name = data.get("name", "").strip()

    if not folder_name or "/" in folder_name or "\\" in folder_name:
        return jsonify({"success": False, "message": "Invalid folder name"}), 400

    abs_dir = safe_fiesta_path(os.path.join(parent_rel, folder_name))
    if not abs_dir:
        return jsonify({"success": False, "message": "Invalid path"}), 400

    try:
        os.makedirs(abs_dir, exist_ok=True)
        return jsonify({"success": True, "message": f"Folder '{folder_name}' created."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/files/new_file", methods=["POST"])
@login_required
def api_files_new_file():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "filemanager" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: File manager permission required."}), 403

    data = request.get_json() or {}
    parent_rel = data.get("path", "").strip()
    filename = data.get("name", "").strip()

    if not filename or "/" in filename or "\\" in filename:
        return jsonify({"success": False, "message": "Invalid file name"}), 400

    abs_file = safe_fiesta_path(os.path.join(parent_rel, filename))
    if not abs_file:
        return jsonify({"success": False, "message": "Invalid path"}), 400

    if os.path.exists(abs_file):
        return jsonify({"success": False, "message": "File already exists"}), 400

    try:
        with open(abs_file, "w", encoding="utf-8") as f:
            f.write("")
        return jsonify({"success": True, "message": f"File '{filename}' created."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/files/download")
@login_required
def api_files_download():
    rel_path = request.args.get("path", "").strip()
    abs_path = safe_fiesta_path(rel_path)
    if not abs_path or not os.path.isfile(abs_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path))

# ── Configs ──────────────────────────────────────────────────────────────────
@app.route("/api/configs")
@login_required
def api_list_configs():
    return jsonify({"configs": list(ALLOWED_CONFIGS.keys())})

@app.route("/api/config/read")
@login_required
def api_read_config():
    name = request.args.get("name")
    if name not in ALLOWED_CONFIGS or not os.path.exists(ALLOWED_CONFIGS[name]):
        return jsonify({"success": False, "message": "Config not found"}), 404
    try:
        with open(ALLOWED_CONFIGS[name], "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return jsonify({"success": True, "name": name, "content": content})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/config/save", methods=["POST"])
@login_required
def api_save_config():
    curr_perms = session.get("permissions", [])
    if "all" not in curr_perms and "parameters" not in curr_perms and session.get("role") != "owner":
        return jsonify({"success": False, "message": "Permission denied: Parameter editor permission required."}), 403

    data = request.get_json() or {}
    name = data.get("name")
    content = data.get("content", "")

    if name not in ALLOWED_CONFIGS:
        return jsonify({"success": False, "message": "Unauthorized file target"}), 403

    target_path = ALLOWED_CONFIGS[name]
    try:
        backup_path = target_path + ".bak"
        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8", errors="ignore") as src, \
                 open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"success": True, "message": f"Saved {name} successfully (snapshot {name}.bak created)!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ── Quick Actions ────────────────────────────────────────────────────────────
@app.route("/api/action", methods=["POST"])
@login_required
def api_action():
    data = request.get_json() or {}
    action = data.get("action")
    param = data.get("param", "")

    if action == "restart":
        def restart_worker():
            time.sleep(1)
            server_runner.restart()
        threading.Thread(target=restart_worker, daemon=True).start()
        return jsonify({"success": True, "message": "Server reboot sequence initiated!"})

    elif action == "save":
        send_mc_command("save-all")
        return jsonify({"success": True, "message": "World data flushed and saved to disk (/save-all)!"})

    elif action == "time":
        send_mc_command(f"minecraft:time set {param or 'day'}")
        return jsonify({"success": True, "message": f"Time of day changed to {param}!"})

    elif action == "weather":
        send_mc_command(f"minecraft:weather {param or 'clear'}")
        return jsonify({"success": True, "message": f"Weather state set to {param}!"})

    elif action == "difficulty":
        send_mc_command(f"minecraft:difficulty {param or 'normal'}")
        return jsonify({"success": True, "message": f"Game difficulty set to {param}!"})

    elif action == "reload_plugin":
        if param == "essentials":
            send_mc_command("ess reload")
        elif param == "tab":
            send_mc_command("tab reload")
        elif param == "deluxemenus":
            send_mc_command("dm reload")
        elif param == "skinsrestorer":
            send_mc_command("sr reload")
        elif param == "luckperms":
            send_mc_command("lp reload")
        elif param == "geyser":
            send_mc_command("geyser reload")
        else:
            send_mc_command(f"{param} reload")
        return jsonify({"success": True, "message": f"Reload command dispatched for {param}!"})

    elif action == "gc":
        send_mc_command("gc")
        return jsonify({"success": True, "message": "Garbage collector (/gc) triggered in Minecraft engine!"})

    return jsonify({"success": False, "message": "Unknown action"}), 400

@app.route("/install.sh")
def route_install_script():
    install_path = os.path.join(BASE_DIR, "install.sh")
    if os.path.exists(install_path):
        return send_file(install_path, mimetype="text/x-shellscript")
    return "echo 'FiestaPanel: install.sh not found'; exit 1", 404, {"Content-Type": "text/plain"}

@app.route("/install.ps1")
def route_install_ps1():
    install_path = os.path.join(BASE_DIR, "install.ps1")
    if os.path.exists(install_path):
        return send_file(install_path, mimetype="text/plain")
    return "Write-Error 'FiestaPanel: install.ps1 not found'; exit 1", 404, {"Content-Type": "text/plain"}

if __name__ == "__main__":
    h = SERVER_CONFIG.get("host", "127.0.0.1")
    p = SERVER_CONFIG.get("port", 8080)
    app.run(host=h, port=p, debug=False)
