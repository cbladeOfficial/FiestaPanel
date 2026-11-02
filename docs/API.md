# 📡 GatewayPanel REST API Reference

All API routes communicate using JSON payloads and responses unless otherwise specified. Authentication is managed via secure HTTP cookies or session tokens.

---

## 🔐 Authentication

### `POST /login`
Authenticate into GatewayPanel.

- **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "your_secure_password"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "role": "admin",
    "redirect": "/"
  }
  ```

### `GET /logout`
Clears user session cookie and redirects to `/login`.

---

## 📊 Status & Telemetry

### `GET /api/status`
Retrieves live server telemetry and resource usage.

- **Response**:
  ```json
  {
    "success": true,
    "online": true,
    "cpu_percent": 12.4,
    "ram_used_mb": 2048,
    "ram_total_mb": 8192,
    "disk_percent": 34.2,
    "uptime": "4h 23m",
    "players_online": 3,
    "players_max": 20,
    "version": "Purpur 1.21.11"
  }
  ```

---

## 💻 Console & Service Control

### `GET /api/console/logs`
Fetches recent terminal output lines.

- **Query Parameters**:
  - `limit`: (Optional, default 100) Number of recent log lines.
- **Response**:
  ```json
  {
    "success": true,
    "logs": [
      "[21:28:10 INFO]: Server running on 0.0.0.0:25565",
      "[21:28:15 INFO]: Player debarkak joined the game"
    ]
  }
  ```

### `POST /api/console/execute`
Dispatches a console command to the Minecraft server.

- **Request Body**:
  ```json
  {
    "command": "say Server restart scheduled in 5 minutes"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "message": "Command executed"
  }
  ```

### `POST /api/server/control`
Executes server lifecycle actions (`start`, `stop`, `restart`).

- **Request Body**:
  ```json
  {
    "action": "restart"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "status": "restarting"
  }
  ```

---

## 🎒 Player Management & Inventory

### `GET /api/players`
Fetches list of online and registered players.

- **Response**:
  ```json
  {
    "success": true,
    "players": [
      {
        "name": "debarkak",
        "uuid": "4f9d...",
        "online": true,
        "gamemode": "survival",
        "ping": 18,
        "is_op": true
      }
    ]
  }
  ```

### `GET /api/player/<uuid>/inventory`
Reads player inventory slots and equipment from NBT data.

- **Response**:
  ```json
  {
    "success": true,
    "uuid": "4f9d...",
    "armor": {
      "helmet": {"id": "minecraft:netherite_helmet", "count": 1, "durability": 407},
      "chestplate": {"id": "minecraft:elytra", "count": 1, "durability": 431},
      "leggings": {"id": "minecraft:diamond_leggings", "count": 1},
      "boots": {"id": "minecraft:netherite_boots", "count": 1}
    },
    "offhand": {"id": "minecraft:totem_of_undying", "count": 1},
    "hotbar": [
      {"slot": 0, "id": "minecraft:diamond_sword", "count": 1},
      {"slot": 1, "id": "minecraft:golden_apple", "count": 64}
    ],
    "storage": [
      {"slot": 9, "id": "minecraft:ender_pearl", "count": 16}
    ]
  }
  ```

### `POST /api/player/action`
Executes moderation actions on a target player.

- **Request Body**:
  ```json
  {
    "player": "Steve",
    "action": "kick",
    "reason": "Spamming in chat"
  }
  ```
  *Allowed actions:* `kick`, `ban`, `unban`, `ban-ip`, `op`, `deop`, `gamemode`.

---

## 🔌 Modrinth Plugin Manager

### `GET /api/plugins/search`
Queries Modrinth API for Minecraft plugins.

- **Query Parameters**:
  - `q`: Search keyword (e.g. `luckperms`, `chunky`, `essentials`).
  - `version`: (Optional) Minecraft target version (e.g. `1.21.1`).
- **Response**:
  ```json
  {
    "success": true,
    "hits": [
      {
        "project_id": "Vebnzrzj",
        "title": "LuckPerms",
        "description": "An advanced permissions plugin for Minecraft.",
        "icon_url": "https://cdn.modrinth.com/...",
        "downloads": 4502010
      }
    ]
  }
  ```

### `POST /api/plugins/install`
Installs a chosen plugin from Modrinth directly into `plugins/`.

- **Request Body**:
  ```json
  {
    "project_id": "Vebnzrzj",
    "version_id": "latest"
  }
  ```

---

## 📁 File Manager API

### `GET /api/files/list`
Lists directory contents within server root.

- **Query Parameters**:
  - `path`: Relative path from server root (e.g. `plugins/LuckPerms`).
- **Response**:
  ```json
  {
    "success": true,
    "path": "plugins",
    "files": [
      {"name": "LuckPerms.jar", "type": "file", "size": 1823904, "modified": 1714502900},
      {"name": "LuckPerms", "type": "dir", "size": 0, "modified": 1714503000}
    ]
  }
  ```

### `POST /api/files/write`
Saves contents of a text file.

- **Request Body**:
  ```json
  {
    "path": "server.properties",
    "content": "motd=A GatewayPanel Managed Server\\n..."
  }
  ```

### `POST /api/files/upload`
Uploads files (multipart/form-data) into specified directory path.

---

## 🎨 Branding & Settings API

### `GET /api/branding`
Fetches current branding configuration.

- **Response**:
  ```json
  {
    "success": true,
    "branding": {
      "brand_name": "FIESTA-LINK",
      "tagline": "The Reliable Choice",
      "model_number": "Model No. FS-GATEWAY-PRO",
      "header_icon": "win7",
      "header_icon_custom": "",
      "footer_text": "Made by Fiesta and it's developers, Mockup UI of Legacy TP-Link Portal",
      "browser_title": "FIESTA-LINK | FS-GATEWAY-PRO Console"
    }
  }
  ```

### `POST /api/branding`
Updates panel branding settings (Admin only).
