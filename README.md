# 🌐 GatewayPanel

> **The Modern & Retro Minecraft Server Management Suite**  
> Nostalgic TP-Link & Windows 7 Aero Aesthetics • Real-Time Telemetry • Visual Inventory Inspector • Modrinth Plugin Manager • Jailed File Manager • Turnkey Deployment

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20systemd-orange.svg)]()
[![Minecraft](https://img.shields.io/badge/Minecraft-Java%20Edition-success.svg)]()

---

## ⚡ Quick Start (1-Line Install)

Run the automated installer on any Ubuntu, Debian, or Linux server:

```bash
curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash
```

Or clone and run locally:
```bash
git clone https://github.com/debarkak/gatewaypanel.git /opt/gatewaypanel
cd /opt/gatewaypanel
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

```
┌────────────────────────────────────────────────────────────────────────┐
│                        GatewayPanel Highlights                         │
├───────────────────────────────────┬────────────────────────────────────┤
│ 🎮 Full Process Control           │ 🎒 Visual Inventory Inspector      │
│ Start, stop, restart, kill, and   │ Live armor, offhand, storage &     │
│ tail ANSI logs with scroll jumps. │ hotbar with authentic 1.21 assets. │
├───────────────────────────────────┼────────────────────────────────────┤
│ 🔌 Modrinth Plugin Manager        │ 📁 Jailed File Manager             │
│ Search, filter, and 1-click       │ In-browser code editor, directory  │
│ install plugins from Modrinth API.│ browser & drag-and-drop upload.    │
├───────────────────────────────────┼────────────────────────────────────┤
│ 🌍 World & Weather Controls       │ 👥 Sub-Users & Multi-User Access   │
│ Day/Night cycle, weather clear/   │ Granular permissions (Admin, Op,   │
│ rain/thunder, & safe world flush. │ Viewer) with salted PBKDF2 auth.   │
├───────────────────────────────────┼────────────────────────────────────┤
│ 🎨 Windows 7 Aero & Retro Themes  │ 🏷️ Complete Brand Customization    │
│ Authentic 7.css glass reflection, │ Header icons (12 presets + SVG),   │
│ TP-Link legacy, Win98, Cyberpunk. │ model number, title, and tagline.  │
└───────────────────────────────────┴────────────────────────────────────┘
```

---

## 🧰 The `panelctl` CLI

GatewayPanel installs a system management CLI accessible anywhere:

```bash
panelctl status        # Check daemon health and memory usage
panelctl restart       # Gracefully restart GatewayPanel
panelctl logs          # Tail live systemd journal logs
panelctl reset-admin   # Interactively reset or generate admin password
panelctl set-port 8080 # Update HTTP listener port
panelctl set-mc-path   # Switch managed Minecraft server path
panelctl info          # Print configuration overview
panelctl version       # GatewayPanel Software Suite v2.0.0
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
Copyright (c) 2026 GatewayPanel Contributors & Fiesta Team.
