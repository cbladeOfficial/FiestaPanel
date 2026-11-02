# 🚀 GatewayPanel Installation & Setup Guide

This guide walks you through deploying **GatewayPanel** on any Linux server (Ubuntu, Debian, Raspberry Pi OS, CentOS, AlmaLinux, Rocky Linux, Arch Linux).

---

## 📋 System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **Operating System** | Ubuntu 20.04+, Debian 11+, any Linux with systemd | Ubuntu 22.04 LTS / 24.04 LTS |
| **Python** | Python 3.9+ | Python 3.11+ |
| **RAM** | 128 MB (for panel alone) | 512 MB+ |
| **Disk Space** | 100 MB free space | 1 GB+ |
| **Network** | Port 8080 (or custom port) | Standard HTTPS port 443 with Nginx reverse proxy |
| **Minecraft Server** | Any Java edition (Paper, Purpur, Spigot, Vanilla, Fabric) with `systemd` service or folder path |

---

## ⚡ Option 1: One-Line Automated Quick Install (Recommended)

Run the automated installer as `root` or with `sudo`:

```bash
curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash
```

### Unattended / Custom Flags
You can pass environment variables to configure installation without prompts:

```bash
# Custom HTTP Port & Minecraft Server Directory
PORT=9000 MC_PATH=/opt/minecraft MC_SERVICE=minecraft curl -sSL https://fiesta.debarkak.xyz/install.sh | sudo bash
```

### What the Automated Installer Does:
1. Detects OS package manager (`apt-get`, `dnf`, `pacman`, `zypper`).
2. Installs required system packages: `python3`, `python3-pip`, `python3-venv`, `curl`, `tar`.
3. Creates dedicated directory `/opt/gatewaypanel` (or updates existing installation).
4. Sets up an isolated Python virtual environment (`venv`) and installs dependencies.
5. Installs the `panelctl` CLI tool directly into `/usr/local/bin/panelctl`.
6. Configures and registers a `systemd` service (`gatewaypanel.service`).
7. Auto-generates a secure administrator credential if none exists and prints login details.
8. Starts the service immediately and verifies HTTP health.

---

## 🛠️ Option 2: Manual Installation (Step-by-Step)

If you prefer full control or don't want to use the automated script, follow these steps:

### 1. Install System Dependencies

On Ubuntu / Debian:
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl
```

On Fedora / RHEL / AlmaLinux:
```bash
sudo dnf install -y python3 python3-pip git curl
```

---

### 2. Clone the Repository

```bash
sudo mkdir -p /opt/gatewaypanel
sudo git clone https://github.com/debarkak/gatewaypanel.git /opt/gatewaypanel
cd /opt/gatewaypanel
```

---

### 3. Create Python Virtual Environment & Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Create Configuration File

Copy the example configuration:
```bash
cp config.example.json config.json
```

Edit `config.json` to suit your server:
```json
{
  "host": "0.0.0.0",
  "port": 8080,
  "mc_path": "/home/ubuntu/fiesta",
  "mc_service": "fiesta",
  "debug": false
}
```

- `port`: Port GatewayPanel listens on.
- `mc_path`: Absolute path to your Minecraft server root directory (where `server.properties`, `plugins/`, `world/` are stored).
- `mc_service`: (Optional) Systemd service name running your Minecraft server.

---

### 5. Link `panelctl` CLI Tool

```bash
sudo ln -sf /opt/gatewaypanel/panelctl /usr/local/bin/panelctl
sudo chmod +x /usr/local/bin/panelctl
```

---

### 6. Create Systemd Service

Create `/etc/systemd/system/gatewaypanel.service`:

```ini
[Unit]
Description=GatewayPanel Minecraft Management Suite
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gatewaypanel
ExecStart=/opt/gatewaypanel/venv/bin/python3 /opt/gatewaypanel/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gatewaypanel
sudo systemctl start gatewaypanel
```

Check service status:
```bash
panelctl status
```

---

## 🌐 Setting Up a Reverse Proxy (Production & HTTPS)

To access GatewayPanel over domain name with SSL encryption (e.g., `https://panel.yourdomain.com`), configure a reverse proxy.

### Nginx Configuration

1. Install Nginx and Certbot:
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

2. Create `/etc/nginx/sites-available/gatewaypanel`:
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

3. Enable the site and obtain SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/gatewaypanel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d panel.yourdomain.com
```

### Caddyfile (Alternative)

If using Caddy:
```caddy
panel.yourdomain.com {
    reverse_proxy 127.0.0.1:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
    }
}
```

---

## 🎮 CLI Management (`panelctl`)

GatewayPanel includes a convenient command line interface:

| Command | Description |
|---|---|
| `panelctl status` | Display panel daemon status and live memory consumption |
| `panelctl start` | Start the panel service |
| `panelctl stop` | Stop the panel service |
| `panelctl restart` | Gracefully restart the panel service |
| `panelctl logs` | Stream live application logs via `journalctl` |
| `panelctl reset-admin` | Reset or generate new admin credentials |
| `panelctl set-port <port>` | Change panel listening port |
| `panelctl set-mc-path <path>` | Change target Minecraft server directory |
| `panelctl info` | Display current directory, user count, and settings |
| `panelctl version` | Print panel version |

---

## 🔄 Updating GatewayPanel

To upgrade an existing installation to the latest version:

```bash
cd /opt/gatewaypanel
sudo git pull origin main
sudo ./venv/bin/pip install -r requirements.txt
panelctl restart
```

---

## ❓ Troubleshooting & FAQs

### 1. Panel says "Server Stopped" when Minecraft is running
- Ensure `mc_service` in `config.json` matches your Minecraft service name in systemd (e.g. `fiesta.service` or `minecraft.service`).
- Alternatively, check that `mc_path` points to the exact folder containing `server.properties`.

### 2. Console commands not executing
- Check that RCON is enabled in `server.properties`:
  ```properties
  enable-rcon=true
  rcon.port=25575
  rcon.password=YourRconPassword
  ```
- Or if using tmux/screen/systemd, ensure panel user has permissions to write to Minecraft process input.

### 3. File upload fails with HTTP 413
- When using Nginx, increase `client_max_body_size 500M;` in your Nginx configuration.
