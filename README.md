<p align="center">
  <img src="assets/banner.png" alt="FiestaPanel Banner" width="100%">
</p>

<h1 align="center">🌐 FiestaPanel</h1>

<p align="center">
  <strong>The Modern & Retro Minecraft Server Management Suite</strong><br>
  Frutiger Aero Aesthetics • Real-Time Telemetry • Visual Inventory Inspector • Modrinth Plugin Manager • Jailed File Manager • Turnkey Deployment
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.9+-brightgreen.svg" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS%20%7C%20Docker-blue.svg" alt="Platform: Cross-Platform">
  <img src="https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white" alt="Docker Ready">
  <img src="https://img.shields.io/badge/Minecraft-Java%20Edition-success.svg" alt="Minecraft">
</p>

---

<img width="1920" height="880" alt="image" src="https://github.com/user-attachments/assets/d291e8bd-0571-44f4-b81b-5b013db7c885" />
<img width="1920" height="880" alt="image" src="https://github.com/user-attachments/assets/f5d5116c-5ef6-4491-b8c3-4e6de4af9bb1" />

## ⚡ Quick Start

On first installation, enter and confirm an admin password of at least **12 characters** when prompted. The input is hidden, the owner username is `admin`, and there is no preset password. All installers and standalone launchers use the same setup: a scrypt hash is stored in `users.json`, and existing accounts are preserved. The owner can change passwords under **Security → Sub-Users & Access**. For unattended setup, set `FIESTA_ADMIN_PASS` instead of using an interactive prompt.

### 🐧 Linux & 🍎 macOS (1-Line Install)
```bash
curl -sSL https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.sh | sudo bash
```
*(Or via short mirror: `curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash`)*

### 🪟 Windows 10 / 11 / Server (1-Line PowerShell Install)
Open PowerShell (as regular user or Administrator) and run:
```powershell
irm https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.ps1 | iex
```
*(From Windows Command Prompt (CMD): `powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.ps1 | iex"`)*  
*(Or via short mirror: `irm https://fiesta.debarkak.xyz/install.ps1 | iex`)*  
*(Manual install: Clone repo and run `install.bat` or double-click `start.bat`)*

### 🐳 Docker & Docker Compose (Container Install)
Deploy FiestaPanel and your Minecraft server in an isolated container with Java 21 LTS pre-installed:

```bash
# Clone and launch turnkey container
git clone https://github.com/open-fiestasmp/FiestaPanel.git
cd FiestaPanel
read -rs -p "Create admin password (12+ characters): " FIESTA_ADMIN_PASS; echo
export FIESTA_ADMIN_PASS
docker compose up -d
unset FIESTA_ADMIN_PASS
```
*(Or 1-line Docker run)*:
```bash
read -rs -p "Create admin password (12+ characters): " FIESTA_ADMIN_PASS; echo
export FIESTA_ADMIN_PASS
docker run -d --name fiestapanel --restart unless-stopped \
  -e FIESTA_ADMIN_PASS \
  -p 8080:8080 -p 25565:25565 -p 19132:19132/udp \
  -v $(pwd)/minecraft_server:/server \
  -v $(pwd)/data:/app/data \
  ghcr.io/open-fiestasmp/fiestapanel:latest
unset FIESTA_ADMIN_PASS
```
Open **`http://localhost:8080`** in your browser. Complete guide & options in [**INSTALL.md**](INSTALL.md#option-4-docker--docker-compose-containerized).

> [!NOTE]
> **No Pre-installed Server Required**: You do not need to install Minecraft beforehand. You can install and launch **Paper, Purpur, Fabric, Spigot, or Vanilla** in 1-click directly from the web panel without opening SSH or terminal!

---

## 📚 Documentation Index

| Guide | Description |
|---|---|
| 🚀 [**Installation Guide**](INSTALL.md) | Complete step-by-step setup, 1-line Windows/Linux/macOS installers, systemd, and Nginx SSL setup |
| 🧩 [**Addon Developer Guide**](docs/ADDONS_GUIDE.md) | How to build custom FiestaPanel extensions, UI tabs, Discord webhooks, and submit to the Plugin Store |
| 🏗️ [**Architecture & Design**](docs/ARCHITECTURE.md) | Deep-dive into process model, daemon control, texture atlas, and data flow |
| 🌟 [**Feature Tour**](docs/FEATURES.md) | Exhaustive guide covering console, inventory inspector, Modrinth, world controls, etc. |
| 📡 [**REST API Reference**](docs/API.md) | Full JSON API specification for headless integrations and automation |
| 🛡️ [**Security & Best Practices**](docs/SECURITY.md) | scrypt hashing, path traversal defenses, role-based access control, firewall setup |

---

## ✨ Features at a Glance

| Feature | Highlights |
|---|---|
| 🎮 **Full Process Control** | Start, stop, restart, and tail live ANSI logs with top/bottom scroll navigation. |
| 🧩 **Web Panel Addon System & Store** | Modular Python & HTML extensions with 1-click in-panel Plugin Store (Discord Webhooks, Dynmap/BlueMap viewer, Cron Schedulers, MOTD Styler, Maintenance Gate). |
| 🎒 **Visual Inventory Inspector** | Real-time armor, offhand, storage & hotbar viewer with authentic 1.21 item textures and giving search tool. |
| 🔌 **Game Addons (Plugins & Mods)** | Context-aware manager for Bukkit/Spigot/Paper plugins and Fabric/Forge/NeoForge mods with 1-click Modrinth directory installation. |
| 📁 **Jailed File Manager** | In-browser code & config editor, directory navigation, and drag-and-drop file uploads with traversal protection. |
| 🌍 **World & Weather Controls** | Day/Noon/Night cycles, weather clear/rain/thunder toggles, and safe world flushing (`/save-all`). |
| 👥 **Sub-Users & Access Control** | Multi-user roles and scrypt password hashing. |
| 🎨 **Windows 7 Aero & Retro Themes** | Authentic 7.css specular glass reflection, TP-Link legacy, Windows 98, Dark Mode, Matrix, and Cyberpunk. |
| 🏷️ **Complete Brand Customization** | Header icon picker (12 themed presets + local file upload + custom URL/SVG), custom title, hardware model number, and tagline. |

---

## 🔑 Forgotten passwords and account recovery

### Owner (`admin`) password

If you have forgotten the owner password, run `reset-admin` on the machine hosting FiestaPanel. The command generates and displays a new password for the `admin` account; keep that output private. It preserves other accounts when the existing `users.json` is valid. The command requires write access to the panel's data directory.

- **Linux/macOS:** run `panelctl reset-admin`, or `./panelctl reset-admin` from the FiestaPanel directory. Use `sudo` if the data files require it.
- **Windows:** open PowerShell in the FiestaPanel directory and run `.\panelctl.bat reset-admin` (in Command Prompt, run `panelctl.bat reset-admin`).
- **Docker:** run `docker exec -it fiestapanel panelctl reset-admin`. Replace `fiestapanel` with your container name if different.

The command resets or creates the account named `admin`, even if the installation uses a different owner username. It operates on the data directory selected by `FIESTA_DATA_DIR` or `GATEWAY_DATA_DIR`; make sure it is the directory used by your running panel. Back up `users.json` first if you are unsure of its state: the current reset command can replace an unreadable or invalid user file, losing other accounts. For Docker, back up the persistent data volume.

Sign in as `admin` with the generated password, then choose a new password under **Security → Sub-Users & Access → Change Password**. Enter your current owner password and a new password of at least 12 characters. Other sessions for that account will be signed out.

### Sub-user password

Sub-users cannot recover or reset their own passwords. Ask the panel owner to sign in, open **Security → Sub-Users & Access**, and choose **Change Password** next to the affected account. The owner confirms their own current password and enters a new password of at least 12 characters. The sub-user's existing sessions are signed out, and they can then sign in using the new password. Share it through a secure channel.

If the owner has also forgotten their password, recover the owner account first using the steps above, then reset the sub-user's password.

---

## 🧰 The `panelctl` CLI

FiestaPanel installs a system management CLI accessible anywhere:

```bash
panelctl status        # Check daemon health and memory usage
panelctl restart       # Gracefully restart FiestaPanel
panelctl logs          # Tail live systemd journal logs
panelctl reset-admin   # Generate a new admin password
panelctl set-port 8080 # Update HTTP listener port
panelctl set-mc-path   # Switch managed Minecraft server path
panelctl info          # Print configuration overview
panelctl version       # FiestaPanel Software Suite v2.0.0
```

---

## 🖼️ Themes Supported

- **Windows 7 Aero**: Authentic design powered by [**7.css**](https://github.com/khang-nd/7.css) by Khang NT. Vibrant electric azure Aero Glass frames, specular glass reflection buttons, interactive titlebar controls (minimize/maximize/close), and Segoe UI typography.
- **TP-Link Classic**: Retro 2000s router web interface.
- **Windows 98**: Classic desktop bevels and teal aesthetic.
- **Dark Mode**: High contrast OLED dark styling.
- **Cyberpunk**: Neon cyan and magenta terminal aesthetics.
- **Matrix**: Phosphor green CRT monitor glow.

---

## 🙏 Acknowledgements & Credits

- [**7.css**](https://github.com/khang-nd/7.css) by **Khang NT** ([@khang-nd](https://github.com/khang-nd)) — Powers the authentic Windows 7 Aero Glass styling, glossy specular highlights, and window control buttons (MIT License).
- [**Modrinth API**](https://modrinth.com) — Powers the built-in online Mod & Plugin search engine and 1-click installations.
- [**PaperMC API**](https://papermc.io) — Real-time upstream server software version detection and binary downloads.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 FiestaPanel Contributors & Fiesta Team.
