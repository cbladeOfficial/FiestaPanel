<p align="center">
  <img src="assets/banner.png" alt="FiestaPanel Banner" width="100%">
</p>

<h1 align="center">🌐 FiestaPanel</h1>

<p align="center">
  <strong>The Modern & Retro Minecraft Server Management Suite</strong><br>
  Nostalgic TP-Link & Windows 7 Aero Aesthetics • Real-Time Telemetry • Visual Inventory Inspector • Modrinth Plugin Manager • Jailed File Manager • Turnkey Deployment
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.9+-brightgreen.svg" alt="Python 3.9+"></a>
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20systemd-orange.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Minecraft-Java%20Edition-success.svg" alt="Minecraft">
</p>

---

<img width="1920" height="880" alt="image" src="https://github.com/user-attachments/assets/d291e8bd-0571-44f4-b81b-5b013db7c885" />
<img width="1920" height="880" alt="image" src="https://github.com/user-attachments/assets/f5d5116c-5ef6-4491-b8c3-4e6de4af9bb1" />

## ⚡ Quick Start (1-Line Install)

Run the automated installer on any Ubuntu, Debian, or Linux server:

```bash
curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash
```

Or clone and run locally:
```bash
git clone https://github.com/open-fiestasmp/FiestaPanel.git /opt/fiestapanel
cd /opt/fiestapanel
sudo bash install.sh
```

---

## 📚 Documentation Index

| Guide | Description |
|---|---|
| 🚀 [**Installation Guide**](INSTALL.md) | Complete step-by-step setup, prerequisites, systemd service, and Nginx SSL setup |
| 🏗️ [**Architecture & Design**](docs/ARCHITECTURE.md) | Deep-dive into process model, daemon control, texture atlas, and data flow |
| 🌟 [**Feature Tour**](docs/FEATURES.md) | Exhaustive guide covering console, inventory inspector, Modrinth, world controls, etc. |
| 📡 [**REST API Reference**](docs/API.md) | Full JSON API specification for headless integrations and automation |
| 🛡️ [**Security & Best Practices**](docs/SECURITY.md) | PBKDF2 hashing, path traversal defenses, role-based access control, firewall setup |

---

## ✨ Features at a Glance

| Feature | Highlights |
|---|---|
| 🎮 **Full Process Control** | Start, stop, restart, and tail live ANSI logs with top/bottom scroll navigation. |
| 🎒 **Visual Inventory Inspector** | Real-time armor, offhand, storage & hotbar viewer with authentic 1.21 item textures and giving search tool. |
| 🔌 **Modrinth Plugin Manager** | Search, filter by Minecraft version, and 1-click install plugins directly from the Modrinth API. |
| 📁 **Jailed File Manager** | In-browser code & config editor, directory navigation, and drag-and-drop file uploads with traversal protection. |
| 🌍 **World & Weather Controls** | Day/Noon/Night cycles, weather clear/rain/thunder toggles, and safe world flushing (`/save-all`). |
| 👥 **Sub-Users & Access Control** | Multi-user roles (Admin, Operator, Viewer) with salted PBKDF2 password hashing. |
| 🎨 **Windows 7 Aero & Retro Themes** | Authentic 7.css specular glass reflection, TP-Link legacy, Windows 98, Dark Mode, Matrix, and Cyberpunk. |
| 🏷️ **Complete Brand Customization** | Header icon picker (12 themed presets + custom SVG), custom title, hardware model number, and tagline. |

---

## 🧰 The `panelctl` CLI

FiestaPanel installs a system management CLI accessible anywhere:

```bash
panelctl status        # Check daemon health and memory usage
panelctl restart       # Gracefully restart FiestaPanel
panelctl logs          # Tail live systemd journal logs
panelctl reset-admin   # Interactively reset or generate admin password
panelctl set-port 8080 # Update HTTP listener port
panelctl set-mc-path   # Switch managed Minecraft server path
panelctl info          # Print configuration overview
panelctl version       # FiestaPanel Software Suite v2.0.0
```

---

## 🖼️ Themes Supported

- **Windows 7 Aero**: Recreated with authentic specular gradient buttons, frosted glass window borders, and Segoe UI typography inspired by `7.css`.
- **TP-Link Classic**: Retro 2000s router web interface.
- **Windows 98**: Classic desktop bevels and teal aesthetic.
- **Dark Mode**: High contrast OLED dark styling.
- **Cyberpunk**: Neon cyan and magenta terminal aesthetics.
- **Matrix**: Phosphor green CRT monitor glow.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).  
Copyright (c) 2026 FiestaPanel Contributors & Fiesta Team.
