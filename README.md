# 🌐 GatewayPanel

> **The Modern & Retro Minecraft Management Suite**  
> *An ultra-fast, lightweight web management portal for Linux VPS with 14 visual themes (including authentic Windows 7 Aero Glass based on `7.css`, Windows 98, Matrix, and Cyber Synthwave), live inventory GUI editing with Minecraft item textures, 1-click Modrinth plugin search, granular Aternos-style sub-user permissions, web terminal, and turnkey systemd daemon.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux%20%7C%20systemd-lightgrey.svg)]()
[![Minecraft: 1.16 - 1.21+](https://img.shields.io/badge/minecraft-1.16--1.21+-brightgreen.svg)]()

---

## ⚡ Quick 1-Command Installation

Install **GatewayPanel** on any clean or existing **Ubuntu / Debian** server with a single automated command:

```bash
curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash
```

The automated installer will:
1. Detect your hardware architecture and system environment.
2. Install minimal dependencies (`python3`, `pip`, `venv`, `screen`, `curl`).
3. Deploy the application into `/opt/gateway-panel`.
4. Prompt for your Minecraft server folder and preferred HTTP port (default: `8080`).
5. Configure systemd service `gateway-panel.service` with auto-restart on boot.
6. Install the `panelctl` CLI utility into `/usr/local/bin/panelctl`.
7. Output your public access URL and generated admin credentials.

---

## 🌟 Key Features

### 🪟 1. Windows 7 Aero Glass Theme (based on `7.css`)
- Faithful recreation of the beloved Windows 7 Aero Glass desktop interface inspired by the open-source **`7.css`** library.
- Translucent specular highlights, frosted blue title bars, glowing cyan focus borders, and authentic split-gradient glossy buttons.
- Features Segoe UI typography and authentic Aero Control Panel layout.

### 🎨 2. 14 Built-In Hardware & Retro Themes
Switch instantly between light, dark, retro, and cyberpunk aesthetics:
| Theme | Style | Description |
|---|---|---|
| **Windows 7 Aero** | 🪟 Glass | Sky-blue glossy title bars, glass reflections, and 7.css buttons |
| **Classic Green** | 🌿 Light | Original legacy TP-Link emerald router console |
| **Obsidian Green** | 🌙 Dark | High-contrast dark stealth green OLED mode |
| **Archer Blue** | 🔷 Light | Modern corporate TP-Link Archer blue styling |
| **Archer Midnight** | 🌌 Dark | Deep sapphire and midnight enterprise dark mode |
| **Retro Amber** | 🔸 Light | Vintage CRT industrial gateway terminal |
| **Amber Glow** | 🔥 Dark | High-contrast glowing phosphor display |
| **Matrix Stealth** | ⚡ OLED | Pure black hacker console with glowing neon green |
| **Cyber Synthwave** | 💜 Neon | 80s outrun neon with cyber magenta & cyan |
| **Nighthawk ROG** | 🔴 Dark | Aggressive gaming router aesthetic with crimson red |
| **Nordic Glacier** | ❄️ Light | Clean arctic ice-blue palette with high readability |
| **Catppuccin Mocha**| ☕ Dark | Cozy pastel developer palette with lavender accents |
| **Windows 98** | 🪟 Retro | Nostalgic teal wallpaper with 3D gray beveled dialogs |
| **Custom Studio** | 🎨 Custom | Interactive live palette builder with custom color pickers |

### 🏷️ 3. Customizable Header Icons & Branding
- **12 Thematic Icon Presets**:
  - `Classic Rings` (TP-Link Interlocking Rings)
  - `Win7 Aero` (Windows 7 Flying Colors Flag)
  - `Minecraft` (Creeper Face Pixel Art)
  - `Windows 98` (16-Color Retro Flag)
  - `Server Rack` (Hardware Blade with Active LEDs)
  - `Terminal >_` (Interactive Command Prompt)
  - `Microchip` (CPU Hardware Core)
  - `Security Shield` (Access Firewall & Protection)
  - `Wi-Fi Antenna` (Wireless Radio Wave Gateway)
  - `Cyber Neon` (Synthwave Lightning Bolt)
  - `Blaze Flame` (Crimson Gaming Core)
  - `Network Globe` (Global WAN Gateway)
- **Custom Logo Upload / SVG**: Direct support for custom SVG markup or external image URLs.
- **Dynamic Portal Branding**: Fully customize brand name, tagline, model number, browser window title, and footer attribution text from the web UI with persistence across login and dashboard.

### 🎒 4. Minecraft Player Inventory GUI Editor
- Live visual inspect and edit of player inventories (Armor slots, Offhand, Hotbar, Main Storage).
- **1,400+ Genuine Minecraft Item Textures**: High-resolution item sprites pulled directly from official Minecraft game assets.
- **Live Item Search & Autocomplete**: Autocomplete dropdown showing real item icons as you type to prevent invalid IDs.
- **Item Count & Slot Editing**: Adjust item counts or clear specific slots with a single click.

### 🔌 5. Modrinth 1-Click Online Plugin Installer
- Search thousands of verified Spigot/Paper/Purpur plugins directly from the Modrinth API.
- 1-click automatic download straight into `/plugins/`.
- Plugin management: Inspect active plugins, safely disable extensions to `plugins/disabled/`, or restore archived jars.

### 👥 6. Granular Sub-Users Access Control (Aternos-Style)
- Share panel management with staff and moderators without sharing Linux root credentials.
- Granular permission checkboxes:
  - `Terminal Console (/diag-console)`
  - `Server Power Controls (/reboot, /start, /stop)`
  - `File Manager (/sys-filemanager)`
  - `Player Management (/players)`
  - `Parameter Editor (/sys-configs)`
  - `Server Software Engine (/sys-software)`
  - `User Access Management`

### 🔄 7. Software Engine Switcher with Snapshot Rollback
- Switch between Purpur, Paper, Fabric, Spigot, and Vanilla engines on the fly.
- Automatic version discovery directly from official upstream distribution APIs.
- **Safety Snapshot Rollback**: Automatically creates `server.jar.bak` before any engine replacement. If a new version causes plugin incompatibility, click **[ ⏪ Rollback ]** to restore the previous jar instantly.

### 📁 8. Web File Manager & Config Editor
- Full-featured web directory explorer for your Minecraft server folder.
- Edit `server.properties`, `bukkit.yml`, `spigot.yml`, and plugin configs with syntax-highlighted editor.
- Automatic inline `.bak` snapshot generation prior to each save.
- File upload, creation, and deletion safeguards.

### 💻 9. Real-Time Terminal Console
- Direct socket log stream from `logs/latest.log`.
- Command input prompt with quick buttons:
  - Quick daylight cycle (Day / Noon / Night)
  - Weather control (Clear sky / Rain / Thunderstorm)
  - Emergency World Flush & Save (`/save-all`)
  - Garbage Collection sweep (`/gc`)

---

## 🛠️ CLI Management Tool (`panelctl`)

GatewayPanel includes a command-line tool installed to `/usr/local/bin/panelctl`:

```bash
# Service Control
panelctl start              # Start panel daemon
panelctl stop               # Stop panel daemon
panelctl restart            # Restart panel daemon
panelctl status             # View live systemd status
panelctl logs               # Stream real-time logs

# Configuration & Security
panelctl reset-admin        # Interactively reset the admin password
panelctl set-port 8080      # Change the HTTP listening port
panelctl set-mc-path /srv   # Change the target Minecraft server path
panelctl info               # View active paths, ports, and configuration
panelctl version            # Show version information
```

---

## 🔧 Manual Installation (Step-by-Step)

If you prefer to configure the panel manually:

```bash
# 1. Clone or download GatewayPanel
git clone https://github.com/debarkak/fiesta-portal.git /opt/gateway-panel
cd /opt/gateway-panel

# 2. Setup Python Virtual Environment
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 3. Configure settings
cp config.example.json config.json
nano config.json   # Set server_dir, admin_pass, and port

# 4. Link CLI tool
chmod +x panelctl
sudo ln -sf /opt/gateway-panel/panelctl /usr/local/bin/panelctl

# 5. Setup Systemd Service
sudo cp -r gateway-panel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gateway-panel.service
```

---

## ⚙️ Configuration Reference (`config.json`)

```json
{
  "admin_user": "admin",
  "admin_pass": "YourSecurePasswordHere",
  "server_dir": "/home/ubuntu/fiesta",
  "service_name": "fiesta",
  "screen_session": "fiesta",
  "host": "0.0.0.0",
  "port": 8080
}
```

Environment variables can also be used to override settings:
- `GATEWAY_PORT`: Web panel listening port (e.g. `8080`)
- `GATEWAY_HOST`: Bind address (e.g. `0.0.0.0` or `127.0.0.1`)
- `GATEWAY_SERVER_DIR`: Path to Minecraft server directory
- `GATEWAY_ADMIN_USER`: Initial admin username
- `GATEWAY_ADMIN_PASS`: Initial admin password

---

## 🔒 Security Best Practices

1. **Reverse Proxy (Nginx / Cloudflare)**: When serving to the public internet, place GatewayPanel behind Nginx with an SSL certificate (`certbot`) or Cloudflare proxy.
2. **Firewall**: Ensure the panel's internal port (`8080`) is bound to `127.0.0.1` when using Nginx reverse proxy.
3. **Change Default Credentials**: Use `panelctl reset-admin` or the web sub-user manager to set a strong password.

---

## 📄 License

GatewayPanel is licensed under the **[MIT License](LICENSE)**. Feel free to use, modify, distribute, and integrate it into your own server infrastructure.
