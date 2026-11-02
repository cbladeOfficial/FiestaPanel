# 🏗️ FiestaPanel Architecture & Technical Design

This document details the architectural design, internal components, process model, and data flow of **FiestaPanel**.

---

## 🏛️ System Overview

FiestaPanel is designed as a lightweight, zero-overhead management suite tailored for Minecraft Java Edition servers. It blends a nostalgic, responsive UI (TP-Link Legacy, Windows 7 Aero, Windows 98, Cyberpunk) with a modern backend built on Python, Flask, systemd, and direct process interfaces.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          User Web Browser                              │
│   (HTML5 + Vanilla ES6 + Retro CSS / 7.css + High-Res Texture Atlas)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS (Port 443) / HTTP (Port 8080)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Reverse Proxy (Nginx / Caddy)                      │
│                  - SSL Termination & Let's Encrypt                     │
│                  - WebSocket / Chunked Log Streaming                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Reverse Proxy (127.0.0.1:8080)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FiestaPanel Backend                            │
│                 (Flask Application Server / Werkzeug)                  │
├────────────────────────────────────────────────────────────────────────┤
│  • Auth Engine (PBKDF2 SHA-256 session management, Role ACL)           │
│  • Console Controller (journalctl log tailing & systemd/RCON dispatch) │
│  • Player & NBT Engine (Player inventory reader & texture mapper)      │
│  • Modrinth API Client (Online plugin search & direct jar delivery)   │
│  • Parameter & Properties Parser (server.properties bidirectional)     │
│  • File Manager Engine (Jailed path resolver, multipart streaming)     │
│  • Branding & Theming Engine (Dynamic SVG icons & CSS variable bridge) │
└──────────────┬───────────────────┬───────────────────┬─────────────────┘
               │                   │                   │
               ▼                   ▼                   ▼
┌───────────────────────┐ ┌─────────────────┐ ┌──────────────────────────┐
│  Minecraft Server     │ │  Local Files    │ │   External Web APIs      │
│  (Paper / Purpur /    │ │  • config.json  │ │   • Modrinth v2 API      │
│   Spigot / Fabric)    │ │  • users.json   │ │   • Mojang Skin API      │
│  • systemd service    │ │  • branding.json│ │                          │
│  • server.properties  │ │  • static/      │ │                          │
│  • plugins/ & worlds/ │ │    mcassets/    │ │                          │
└───────────────────────┘ └─────────────────┘ └──────────────────────────┘
```

---

## 🧩 Core Subsystems

### 1. Process & Daemon Management
- **Interaction Model**: FiestaPanel controls the underlying Minecraft server using `systemctl` commands via Linux subprocessing, allowing non-blocking starts, stops, and restarts.
- **Log Streaming**: Live console output is read in real time from `journalctl -u <mc_service> -f` or directly from `logs/latest.log` inside the server directory.
- **Console Dispatch**: Commands sent via the retro terminal are executed directly via:
  1. `systemd-cat` / service stdin fifo (if configured).
  2. RCON protocol (using `mcrcon` socket client when enabled).
  3. `screen` / `tmux` process forwarding when deployed in interactive session mode.

### 2. Player Inventory & Texture Atlas Engine
- **Texture Mapping**: FiestaPanel bundles `items_textures.json` and a full offline directory of over 1,300 extracted vanilla Minecraft textures (`static/mcassets/`).
- **NBT Parsing**: Player data files (`world/playerdata/<UUID>.dat`) are uncompressed and parsed into memory.
- **Slot Mapping**:
  - `Equipment / Armor`: Helmet (Slot 103), Chestplate (Slot 102), Leggings (Slot 101), Boots (Slot 100).
  - `Offhand`: Shield / Totem (Slot -106).
  - `Hotbar`: Slots 0 to 8.
  - `Main Inventory`: Slots 9 to 35.
- **Autocomplete Giving**: Item search queries evaluate namespace IDs (`minecraft:diamond_sword`), item display names, and preview textures to prevent command syntax errors.

### 3. Modrinth Integration
- Direct HTTPS queries to the official **Modrinth API v2** (`https://api.modrinth.com/v2/`).
- Queries filter plugins compatible with server platform (Paper, Purpur, Spigot, Bukkit) and current game version (e.g. 1.21.x).
- Downloaded JAR files are safely validated and streamed directly into `<mc_path>/plugins/`.

### 4. File Management & Jailed Path Resolver
- The file manager enforces strict directory jailing:
  ```python
  def safe_path(relative_path):
      base = os.path.abspath(SERVER_CONFIG['mc_path'])
      target = os.path.abspath(os.path.join(base, relative_path))
      if not target.startswith(base):
          raise PermissionError("Access outside server root is denied.")
      return target
  ```
- Protects against directory traversal (`../`) vulnerabilities while providing full read, write, upload, and delete capabilities within the server tree.

### 5. Multi-User Access Control (Sub-Users)
- Stored securely in `users.json` with Werkzeug-generated PBKDF2 salt and hashes.
- Three hierarchical permission tiers:
  1. **Admin**: Full panel access including sub-user management, configuration editing, file deletion, and branding changes.
  2. **Operator**: Server controls, player management, plugin installation, console commands, and file browsing.
  3. **Viewer**: Read-only status telemetry, player list viewing, and log monitoring.

---

## 🎨 Theming & Branding Engine

### Multi-Theme Architecture
Themes are driven purely by semantic CSS variables defined under `[data-theme="<theme_id>"]` attributes on the root `<html>` element.

Supported Themes:
- `classic`: TP-Link Legacy green, grey, and teal retro web style.
- `win7`: Authentic Windows 7 Aero Glass with 7.css specular buttons and Aero borders.
- `win98`: Classic Windows 98 bevels, teal desktop wallpaper, and Win98 system fonts.
- `dark`: High-contrast OLED dark mode.
- `cyber`: Cyberpunk neon teal and magenta terminal aesthetics.
- `matrix`: Phosphor monochrome green-on-black CRT monitor style.

### Dynamic SVG Header Icon Pipeline
Header branding supports 12 built-in SVG glyphs or custom user-supplied SVG/image URLs. Icons are rendered server-side via Jinja2 macros to eliminate Client Layout Shift (CLS) on initial load, and dynamically updated client-side upon theme or configuration changes.
