# 🚀 FiestaPanel Installation & Setup Guide

This guide walks you through deploying **FiestaPanel** across **Linux, macOS, and Windows**.

> [!TIP]
> **No Pre-installed Minecraft Server Required!**  
> You do NOT need to set up or download Minecraft prior to installing FiestaPanel. Once FiestaPanel is installed, you can choose and install **Purpur, Paper, Fabric, Spigot, or Vanilla** in 1-click directly from the web panel without opening SSH or terminal.

---

## 📋 System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **Operating System** | Linux (Ubuntu, Debian, Fedora, Arch), macOS 11+, or Windows 10/11 | Ubuntu 22.04 / 24.04 LTS or Windows 11 |
| **Python** | Python 3.9+ | Python 3.11+ |
| **Java** | Java 17 or Java 21+ | OpenJDK / Temurin Java 21 (Required for MC 1.20.5+) |
| **RAM** | 128 MB (for panel alone) | 512 MB+ (plus RAM for your Minecraft server) |
| **Disk Space** | 100 MB free space | 2 GB+ |
| **Network** | Port 8080 (customizable) | Standard HTTPS port 443 with Nginx reverse proxy |
| **Minecraft Server** | Any Java edition (Auto-installable from web panel) | Purpur or Paper 1.21.x |

---

## 🐧 Option 1: Linux & macOS (1-Line Quick Install)

Run the automated installer in your terminal:

```bash
curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash
```

### Unattended / Custom Flags
Pass environment variables to customize your setup:

```bash
# Custom HTTP Port & Minecraft Server Directory
PORT=9000 MC_PATH=/opt/minecraft curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash
```

### What the Automated Installer Does:
1. Detects OS package manager (`apt-get`, `dnf`, `pacman`, `brew`).
2. Installs required system packages: `python3`, `python3-pip`, `python3-venv`, `curl`, `tar`.
3. Creates dedicated directory `/opt/fiestapanel` (or updates existing installation).
4. Sets up an isolated Python virtual environment (`venv`) and installs dependencies.
5. Installs the `panelctl` CLI tool into `/usr/local/bin/panelctl` (or `~/.local/bin/panelctl`).
6. Configures and registers a `systemd` service (`fiestapanel.service`) on Linux.
7. Auto-generates a secure administrator credential if none exists and prints login details.
8. Starts the service immediately.

---

## 🪟 Option 2: Windows Installation (10 / 11 / Server)

FiestaPanel natively supports Windows without requiring WSL or Docker!

### Quick Windows Setup:

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
   Run the interactive installer:
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

## 🎮 Installing Minecraft Server Software from Web Panel

Once logged into FiestaPanel:

1. If no Minecraft server is installed yet, you will see a prominent banner:
   **"🚀 Welcome to FiestaPanel — Minecraft Server Software Not Installed Yet"**
2. Click **[ ⚡ Install Paper 1.21.4 ]** or navigate to **System Tools ➔ Software**.
3. Select your engine:
   - 🦅 **Purpur** (High-performance Paper fork with extensive customization)
   - 📄 **Paper** (Industry standard high-performance engine)
   - 🧵 **Fabric** (Modular modern modding loader)
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
