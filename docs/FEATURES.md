# 🌟 FiestaPanel Feature Guide

This guide covers all capabilities, controls, and workflows in **FiestaPanel**.

---

## 📊 1. System Status & Telemetry

The main status view delivers real-time health metrics:
- **Server Health Status**: Live indication whether the Minecraft server process is `ONLINE`, `STARTING`, or `STOPPED`.
- **System Resource Metrics**:
  - CPU utilization percentage.
  - RAM consumption and available system memory.
  - Disk space usage on the server volume.
  - Server process uptime in hours and minutes.
- **Network & Domain**:
  - Displays primary server domain and port.
  - **1-Click Copy**: Copies server address directly to clipboard for sharing with players.
- **World Management Shortcut**:
  - **"Flush & Save World (/save-all)"**: Issues immediate disk synchronization to prevent data loss before maintenance.

---

## 💻 2. Server Console & Terminal

The retro terminal emulation provides deep inspection and control:
- **Real-Time Log Stream**: Displays colorized ANSI logs straight from the server output.
- **Scroll Controls**:
  - Dedicated **"Scroll to Top"** and **"Scroll to Bottom"** buttons for rapid navigation through long logs.
- **Process Controls**:
  - **Start**: Initiates the Minecraft daemon.
  - **Stop**: Issues a graceful server shutdown.
  - **Restart**: Gracefully cycles the server service.
- **Interactive Command Dispatch**:
  - Input bar with command history support (Up/Down arrow navigation).
  - Instant dispatch to server stdin / RCON.

---

## 🎒 3. Player Management & Visual Inventory Inspector

A comprehensive toolset for moderating players and viewing their gear:
- **All Players Table**:
  - Lists online and offline players with their UUID, avatar head, ping, and status.
  - Moderation actions: **Kick**, **Ban**, **Ban-IP**, **OP**, **De-OP**, **Whitelist**.
- **Visual Inventory Inspector**:
  - Inspect any player's inventory rendered in authentic Minecraft grid format:
    - **Armor Slots**: Helmet, Chestplate, Leggings, Boots.
    - **Offhand Slot**: Shield, Totem, Arrow, etc.
    - **Main Inventory Grid**: 27 storage slots.
    - **Hotbar**: 9 quick-access slots.
  - **Authentic Item Textures**: High-resolution 16x16 pixel textures extracted from vanilla Minecraft assets.
  - **Hover Tooltips**: Shows item names, lore, stack counts, and NBT tags.
- **Item Giving Tool**:
  - Interactive search bar with texture preview for over 1,300 Minecraft items.
  - Select item, quantity, and target player to grant items without command syntax errors.
- **Gamemode Controls**:
  - Switch any player between **Survival**, **Creative**, **Adventure**, and **Spectator** modes.

---

## 🔌 4. Modrinth Plugin Manager

FiestaPanel features built-in search and 1-click installation from Modrinth:
- **Online Catalog Search**: Search thousands of plugins directly from Modrinth's official repository.
- **Compatibility Filtering**: Automatically filters for plugins compatible with your server version (e.g. 1.21.x) and engine (Paper, Purpur, Spigot).
- **1-Click Installation**: Downloads and places JAR files directly into the `plugins/` directory.
- **Local Plugin Management**:
  - View installed plugins with file size and active status.
  - Enable or disable plugins (renaming `.jar` to `.jar.disabled`).
  - Delete obsolete plugins with confirmation safeguards.

---

## 🌍 5. World Controls & Weather

Control the in-game environment on the fly:
- **Time Controls**:
  - Set time to **Day** (`/time set day`), **Noon** (`/time set noon`), **Night** (`/time set night`), or **Midnight** (`/time set midnight`).
- **Weather Controls**:
  - Switch weather to **Clear** (`/weather clear`), **Rain** (`/weather rain`), or **Thunderstorm** (`/weather thunder`).
- **World Maintenance**:
  - Manual world save (`/save-all flush`).
  - Toggle world autosave (`/save-on` / `/save-off`).

---

## ⚙️ 6. Parameter & Configuration Editor

Edit `server.properties` through both a graphical GUI and raw text mode:
- **Dual Mode**:
  - **Graphical Controls**: Toggle switches and dropdowns for server port, max players, PvP, flight, online-mode, view distance, and difficulty.
  - **Raw Text Mode**: Direct text editor for advanced settings and custom flags.
- **Default Gamemode Selector**:
  - Configure default gamemode for new players: Survival, Creative, Adventure, or Hardcore.
- **Seed Viewer & Editor**: View and update the world generation seed.
- **Server Icon Uploader**: Upload 64x64 PNG server icon (`server-icon.png`) directly through the browser.

---

## 📁 7. File Manager

A full-fledged web file manager isolated to the server root:
- **Directory Navigation**: Browse folders with breadcrumb navigation.
- **File Uploads**: Drag-and-drop or select multiple files with progress bar.
- **In-Browser Code Editor**: Edit configuration files (`config.yml`, `paper-global.yml`, `bukkit.yml`) with syntax highlighting and line numbers.
- **File Actions**: Create new files and folders, rename, download, and delete.
- **Security Jailing**: Enforces path validation to prevent traversal outside the Minecraft server folder.

---

## 👥 8. Sub-Users & Multi-User Access (Like Aternos)

Delegate management tasks to staff members with granular permissions:
- **Admin**: Full access to all panel controls, files, settings, and user management.
- **Operator**: Access to console, player moderation, plugins, and world controls.
- **Viewer**: Read-only monitoring of server status, logs, and player counts.
- Add, edit, and revoke sub-user accounts anytime.

---

## 🎨 9. Branding Engine & Theme Studio

Personalize the panel for your server community:
- **Custom Branding**:
  - Change Portal Name (e.g. `MY-NETWORK-CONSOLE`).
  - Change Browser Tab Title.
  - Change Sub-heading / Tagline.
  - Change Hardware Model Number (e.g. `Model No. SRV-ENTERPRISE-X`).
  - Custom Footer Notice.
- **Header Icon Selector**:
  - Choose from 12 built-in icon presets or provide custom SVG/image URL.
- **Theme Selection**:
  - **Windows 7 Aero**: Frosted glass windows, 7.css specular reflection buttons, Segoe UI.
  - **TP-Link Classic**: Retro 2000s router web interface.
  - **Windows 98**: Classic desktop bevels and teal aesthetic.
  - **Dark Mode**: Modern OLED dark contrast.
  - **Cyberpunk**: Glowing neon teal and magenta.
  - **Matrix**: Phosphor green CRT terminal style.
