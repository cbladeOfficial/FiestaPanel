# 🚀 FiestaPanel Installation & Setup Guide

This guide walks you through deploying **FiestaPanel** across **Linux, macOS, and Windows**.

> [!TIP]
> **No Pre-installed Minecraft Server Required!**  
> You do NOT need to set up or download Minecraft prior to installing FiestaPanel. Once FiestaPanel is installed, you can choose and install **Purpur, Paper, Fabric, NeoForge, Spigot, or Vanilla** in 1-click directly from the web panel without opening SSH or terminal.

---

## 📋 System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **Operating System** | Linux (Ubuntu, Debian, Fedora, Arch), macOS 11+, Windows 10/11, or Docker | Ubuntu 22.04 / 24.04 LTS, Windows 11, or Docker Container |
| **Python** | Python 3.9+ | Python 3.11+ |
| **Java** | Java 17 or Java 21+ | OpenJDK / Temurin Java 21 (Required for MC 1.20.5+ and 26.x) |
| **RAM** | 128 MB (for panel alone) | 512 MB+ (plus RAM for your Minecraft server) |
| **Disk Space** | 100 MB free space | 2 GB+ |
| **Network** | Port 8080 (customizable) | Standard HTTPS port 443 with Nginx reverse proxy |
| **Minecraft Server** | Any Java edition (Auto-installable from web panel) | Paper or Purpur 26.x / 1.21.x |

---

## 🐧 Option 1: Linux & macOS (1-Line Quick Install)

Run the automated installer directly from GitHub via your terminal:

```bash
curl -sSL https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.sh | sudo bash
```
*(Or via short mirror: `curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash`)*

### Unattended / Custom Flags
Pass arguments to customize your setup:

```bash
# Custom HTTP Port & Minecraft Server Directory
curl -sSL https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.sh | sudo bash -s -- --port 9000 --dir /opt/minecraft
```

For unattended installation, provide `FIESTA_ADMIN_PASS` (at least 12 characters) to the installer process and pass `--unattended`; no default is used. For example, when using `sudo`, preserve that variable explicitly according to your sudo policy. The optional `--admin-pass` argument also works, but can expose the password in shell history or process listings.

### What the Automated Installer Does:
1. Detects OS package manager (`apt-get`, `dnf`, `pacman`, `brew`).
2. Installs required system packages: `python3`, `python3-pip`, `python3-venv`, `curl`, `tar`.
3. Creates dedicated directory `/opt/fiestapanel` (or updates existing installation).
4. Sets up an isolated Python virtual environment (`venv`) and installs dependencies.
5. Installs the `panelctl` CLI tool into `/usr/local/bin/panelctl` (or `~/.local/bin/panelctl`).
6. Configures and registers a `systemd` service (`fiestapanel.service`) on Linux.
7. Prompts for and confirms a password of at least 12 characters for a new owner account; existing accounts are preserved.
8. Starts the service immediately.

---

## 🪟 Option 2: Windows Installation (10 / 11 / Server)

FiestaPanel natively supports Windows without requiring WSL or Docker! First setup asks for and confirms an owner password of at least 12 characters; it stores a scrypt hash and preserves existing accounts on subsequent runs.

### Method A: 1-Line Automated Install (Recommended)

Open **PowerShell** (no Administrator rights strictly required, but recommended) and run directly from GitHub:

```powershell
irm https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.ps1 | iex
```

*(From Windows Command Prompt / CMD)*:
```cmd
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/install.ps1 | iex"
```

*(Or via short mirror)*:
```powershell
irm https://fiesta.debarkak.xyz/install.ps1 | iex
```

#### What the Windows 1-Line Installer Does:
1. Detects Python 3 runtime; if missing, automatically installs Python 3.12 via Windows Package Manager (`winget`).
2. Downloads and extracts the latest FiestaPanel application package into `C:\FiestaPanel` (or `$env:FIESTA_DIR`).
3. Creates a dedicated Python virtual environment (`venv`).
4. Installs required Python dependencies (`flask`, `requests`, `psutil`, `Pillow`, `nbtlib`).
5. Prompts for and confirms the owner password on first setup, then creates `config.json` and the default server storage folder.
6. Creates a convenient desktop shortcut to launch anytime with 1-click.

---

### Method B: Manual Clone / ZIP Setup

1. **Prerequisites**:
   - Install **Python 3.10+** from [python.org](https://www.python.org/downloads/) *(check "Add Python to PATH" during install)*.
   - Install **Java 21** from [adoptium.net](https://adoptium.net/).

2. **Download & Extract**:
   Download the repository ZIP or clone with Git:
   ```cmd
   git clone https://github.com/open-fiestasmp/FiestaPanel.git C:\FiestaPanel
   cd C:\FiestaPanel
   ```

3. **Install & Launch**:
   Run the interactive batch installer:
   ```cmd
   install.bat
   ```
   Or using PowerShell:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```

4. **Start Anytime**:
   Double-click `start.bat` to start FiestaPanel and open your browser automatically to `http://localhost:8080`.
   Use `panelctl.bat status` or `panelctl.bat restart` to manage it from CMD or PowerShell.

---

## 🍎 Option 3: macOS Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/open-fiestasmp/FiestaPanel.git ~/fiestapanel
   cd ~/fiestapanel
   ```

2. **Run Installer**:
   ```bash
   bash install.sh
   ```
   Or run directly in standalone mode:
   ```bash
   ./start.sh
   ```

3. Open your browser to `http://localhost:8080`.

---

## 🐳 Option 4: Docker & Docker Compose (Containerized)

FiestaPanel includes first-class Docker support with a pre-configured Java 21 LTS runtime, isolated dependencies, and persistent volume mounts.

### Method A: Quick Turnkey Setup with Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/open-fiestasmp/FiestaPanel.git
   cd FiestaPanel
   ```

2. **Choose an admin password and launch** (first run):
   ```bash
   read -rs -p "Create admin password (12+ characters): " FIESTA_ADMIN_PASS; echo
   export FIESTA_ADMIN_PASS
   docker compose up -d
   unset FIESTA_ADMIN_PASS
   ```

3. **Check status**:
   ```bash
   docker compose ps
   docker compose logs -f fiestapanel
   ```

4. Open your browser to **`http://localhost:8080`**.

---

### Method B: Single Command `docker run`

Run FiestaPanel directly with automated storage mounts:

```bash
read -rs -p "Create admin password (12+ characters): " FIESTA_ADMIN_PASS; echo
export FIESTA_ADMIN_PASS
docker run -d \
  --name fiestapanel \
  --restart unless-stopped \
  -p 8080:8080 \
  -p 25565:25565 \
  -p 19132:19132/udp \
  -v $(pwd)/minecraft_server:/server \
  -v $(pwd)/data:/app/data \
  -e FIESTA_ADMIN_USER=admin \
  -e FIESTA_ADMIN_PASS \
  ghcr.io/open-fiestasmp/fiestapanel:latest
unset FIESTA_ADMIN_PASS
```

---

### Method C: Build Docker Image Locally

```bash
git clone https://github.com/open-fiestasmp/FiestaPanel.git
cd FiestaPanel
docker build -t fiestapanel:latest .
read -rs -p "Create admin password (12+ characters): " FIESTA_ADMIN_PASS; echo
export FIESTA_ADMIN_PASS
docker run -d --name fiestapanel -e FIESTA_ADMIN_PASS -p 8080:8080 -p 25565:25565 -v $(pwd)/minecraft_server:/server -v $(pwd)/data:/app/data fiestapanel:latest
unset FIESTA_ADMIN_PASS
```

---

### 📦 Container Configuration & Persistent Volumes

| Mount Path | Host Target | Purpose |
|---|---|---|
| `/server` | `./minecraft_server` | Complete Minecraft server directory (`server.jar`, worlds, `plugins/`, `mods/`, logs) |
| `/app/data` | `./data` | Panel persistence (`users.json`, `branding.json`, `config.json`, uploads) |

### ⚙️ Container Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FIESTA_PORT` | `8080` | Web panel HTTP listener port |
| `FIESTA_HOST` | `0.0.0.0` | Bind host (container interface) |
| `FIESTA_SERVER_DIR` | `/server` | Internal container path to Minecraft server root |
| `FIESTA_DATA_DIR` | `/app/data` | Internal container path to panel data store |
| `FIESTA_ADMIN_USER` | `admin` | Initial admin username if database not created |
| `FIESTA_ADMIN_PASS` | None | Required on first non-interactive setup; at least 12 characters |

Docker environment variables are visible to users with access to container configuration. Restrict Docker access. Existing accounts are preserved on restart; changing the environment variable does not reset their passwords. For interactive installations without a container, run `python setup_admin.py` if initializing an owner manually.

### 🧰 Running `panelctl` Inside Container

You can use the built-in management CLI inside your running container:

```bash
docker exec -it fiestapanel panelctl status
docker exec -it fiestapanel panelctl reset-admin
docker exec -it fiestapanel panelctl logs
```

---

## 🎮 Installing Minecraft Server Software from Web Panel

Once logged into FiestaPanel:

1. If no Minecraft server is installed yet, you will see a prominent banner:
   **"🚀 Welcome to FiestaPanel — Minecraft Server Software Not Installed Yet"**
2. Click **[ ⚡ Install Paper 26.3 ]** or navigate to **System Tools ➔ Software**.
3. Select your engine:
   - 🦅 **Purpur** (High-performance Paper fork with extensive customization)
   - 📄 **Paper** (Industry standard high-performance engine)
   - 🧵 **Fabric** (Modular modern modding loader)
   - 🦊 **NeoForge** (Modern modded Minecraft server platform & Forge successor)
   - 🧊 **Vanilla** (Official Mojang server)
   - ⚡ **Spigot** (Classic plugin platform)
4. Choose your Minecraft game version (e.g. 1.21.4, 1.21.1, 1.20.4, 1.19.4).
5. Select allocated RAM (e.g. 4 GB).
6. Check **Accept Mojang EULA automatically** and **Auto-Start**.
7. Click **[ 🔄 Install & Switch Software ]**.

FiestaPanel will download the JAR, create `eula.txt=true`, generate default `server.properties`, and start the server process. **Zero SSH commands required!**

---

## 🎨 Uploading Local Branding Icons & Logos

You can customize the logo in the header and login screen using local image files:

1. Go to **System Tools ➔ Portal Branding**.
2. Under **Header Brand Icon & Logo**, find **Upload Local Logo**.
3. Click **[ 📁 Choose Local Image / SVG ]**.
4. Select any `.png`, `.svg`, `.jpg`, `.webp`, or `.ico` file from your device.
5. FiestaPanel will upload the logo to `static/uploads/`, immediately update the live preview, and apply it server-wide.
6. Click **[ 💾 Save & Apply Branding ]**.

---

## 🌐 Setting Up a Reverse Proxy (Production & HTTPS)

To access FiestaPanel securely via domain name with SSL encryption (e.g., `https://panel.yourdomain.com`):

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name panel.yourdomain.com;

    client_max_body_size 500M; # Required for large world and file uploads

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for live console log streaming
        proxy_buffering off;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

Enable SSL certificate with Certbot:
```bash
sudo certbot --nginx -d panel.yourdomain.com
```

---

## 🧰 CLI Management (`panelctl`)

| Command | Description |
|---|---|
| `panelctl status` | Display panel daemon status and memory consumption |
| `panelctl start` | Start the panel service |
| `panelctl stop` | Stop the panel service |
| `panelctl restart` | Gracefully restart the panel service |
| `panelctl logs` | Stream live application logs |
| `panelctl reset-admin` | Reset or generate new admin credentials |
| `panelctl set-port <port>` | Change panel listening port |
| `panelctl set-mc-path <path>` | Change target Minecraft server directory |
| `panelctl info` | Display current directory, Java runtime, and settings |
| `panelctl version` | Print panel version |

*(On Windows, use `panelctl.bat <command>` or `python panelctl.py <command>`)*

---

## 🔄 Updating FiestaPanel

```bash
cd /opt/fiestapanel  # or C:\FiestaPanel on Windows
git pull origin main
./venv/bin/pip install -r requirements.txt
panelctl restart
```
