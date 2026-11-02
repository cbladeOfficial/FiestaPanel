#!/usr/bin/env bash
# ==============================================================================
# FiestaPanel - Turnkey Minecraft Server Management Suite Installer
# Version: 2.0.0
# License: MIT
# Description: Automated one-line installer for Ubuntu / Debian / Linux servers
# ==============================================================================

set -e

COLOR_RESET="\033[0m"
COLOR_GREEN="\033[1;32m"
COLOR_CYAN="\033[1;36m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"
COLOR_BOLD="\033[1m"

clear 2>/dev/null || true

echo -e "${COLOR_CYAN}"
cat << "EOF"
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║                                                                       ║
  ║     ██████╗  █████╗ ████████╗███████╗██╗    ██╗ █████╗ ██╗   ██╗     ║
  ║    ██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝██║    ██║██╔══██╗╚██╗ ██╔╝     ║
  ║    ██║  ███╗███████║   ██║   █████╗  ██║ █╗ ██║███████║ ╚████╔╝      ║
  ║    ██║   ██║██╔══██║   ██║   ██╔══╝  ██║███╗██║██╔══██║  ╚██╔╝       ║
  ║    ╚██████╔╝██║  ██║   ██║   ███████╗╚███╔███╔╝██║  ██║   ██║        ║
  ║     ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝        ║
  ║                 P A N E L   S O F T W A R E                           ║
  ║                                                                       ║
  ║        Turnkey Retro & Modern Minecraft Management Suite              ║
  ╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${COLOR_RESET}"

# 1. Require Root
if [ "$EUID" -ne 0 ]; then
    echo -e "${COLOR_RED}Error: The installer must be executed as root or with sudo.${COLOR_RESET}"
    echo "Please re-run: sudo bash $0"
    exit 1
fi

# Parse CLI Arguments
MC_DIR_ARG=""
PORT_ARG=""
ADMIN_PASS_ARG=""
UNATTENDED=false
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
TARGET_INSTALL_DIR="/opt/gateway-panel"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)
            MC_DIR_ARG="$2"
            shift 2
            ;;
        --port)
            PORT_ARG="$2"
            shift 2
            ;;
        --admin-pass)
            ADMIN_PASS_ARG="$2"
            shift 2
            ;;
        --unattended|-y)
            UNATTENDED=true
            shift
            ;;
        --install-dir)
            TARGET_INSTALL_DIR="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo -e "${COLOR_BOLD}Initializing FiestaPanel Installation...${COLOR_RESET}"
echo "Target Platform: Linux ($(uname -m))"
echo ""

# 2. Configure Minecraft Server Path
DEFAULT_MC="/home/ubuntu/fiesta"
if [ ! -d "$DEFAULT_MC" ]; then
    DEFAULT_MC="/opt/minecraft"
fi

if [ -n "$MC_DIR_ARG" ]; then
    FINAL_MC_DIR="$MC_DIR_ARG"
elif [ "$UNATTENDED" = true ]; then
    FINAL_MC_DIR="$DEFAULT_MC"
else
    echo -e "${COLOR_YELLOW}Enter the absolute path to your Minecraft server directory:${COLOR_RESET}"
    read -rp "Path [$DEFAULT_MC]: " USER_MC_DIR
    FINAL_MC_DIR="${USER_MC_DIR:-$DEFAULT_MC}"
fi

# Ensure MC dir exists or warn
if [ ! -d "$FINAL_MC_DIR" ]; then
    echo -e "${COLOR_YELLOW}Directory $FINAL_MC_DIR does not exist yet. Creating it...${COLOR_RESET}"
    mkdir -p "$FINAL_MC_DIR"
fi

# 3. Configure Port
DEFAULT_PORT=8080
if [ -n "$PORT_ARG" ]; then
    FINAL_PORT="$PORT_ARG"
elif [ "$UNATTENDED" = true ]; then
    FINAL_PORT=$DEFAULT_PORT
else
    echo -e "${COLOR_YELLOW}Enter the Web Panel HTTP port:${COLOR_RESET}"
    read -rp "Port [$DEFAULT_PORT]: " USER_PORT
    FINAL_PORT="${USER_PORT:-$DEFAULT_PORT}"
fi

# 4. Configure Admin Password
if [ -n "$ADMIN_PASS_ARG" ]; then
    FINAL_PASS="$ADMIN_PASS_ARG"
elif [ "$UNATTENDED" = true ]; then
    FINAL_PASS="GatewayAdmin@$(openssl rand -hex 4 2>/dev/null || echo '2026')"
else
    echo -e "${COLOR_YELLOW}Enter administrator password (leave blank to auto-generate secure password):${COLOR_RESET}"
    read -rsp "Password: " USER_PASS
    echo ""
    if [ -z "$USER_PASS" ]; then
        FINAL_PASS="GatewayAdmin@$(openssl rand -hex 4 2>/dev/null || echo '2026')"
        echo -e "${COLOR_CYAN}Auto-generated secure admin password: $FINAL_PASS${COLOR_RESET}"
    else
        FINAL_PASS="$USER_PASS"
    fi
fi

# 5. Install System Dependencies
echo ""
echo -e "${COLOR_CYAN}[1/6] Installing system prerequisites (python3, pip, venv, screen)...${COLOR_RESET}"
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq || true
    apt-get install -y -qq python3 python3-pip python3-venv screen curl tar >/dev/null 2>&1 || {
        echo -e "${COLOR_YELLOW}Standard apt-get install notice; ensuring packages are present...${COLOR_RESET}"
        apt-get install -y python3 python3-pip python3-venv screen curl tar
    }
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y python3 python3-pip screen curl tar
elif command -v yum >/dev/null 2>&1; then
    yum install -y python3 python3-pip screen curl tar
fi

# 6. Deploy FiestaPanel Codebase
echo -e "${COLOR_CYAN}[2/6] Deploying application files into $TARGET_INSTALL_DIR...${COLOR_RESET}"
mkdir -p "$TARGET_INSTALL_DIR"

# If running directly from cloned directory, copy files
if [ -n "$SOURCE_DIR" ] && [ -f "$SOURCE_DIR/app.py" ]; then
    cp -r "$SOURCE_DIR/app.py" "$TARGET_INSTALL_DIR/"
    cp -r "$SOURCE_DIR/templates" "$TARGET_INSTALL_DIR/"
    cp -r "$SOURCE_DIR/static" "$TARGET_INSTALL_DIR/" 2>/dev/null || mkdir -p "$TARGET_INSTALL_DIR/static"
    cp -r "$SOURCE_DIR/items_textures.json" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/branding.json" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/requirements.txt" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/panelctl" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
else
    # Remote one-line installer fetch mode
    echo "Downloading FiestaPanel application package..."
    curl -sSL "https://fiesta.debarkak.xyz/static/fiestapanel-latest.tar.gz" | tar -xz -C "$TARGET_INSTALL_DIR" 2>/dev/null || {
        # Fallback to direct file download
        curl -sSL "https://fiesta.debarkak.xyz/app.py" -o "$TARGET_INSTALL_DIR/app.py"
    }
fi

# 7. Setup Virtual Environment & Python Packages
echo -e "${COLOR_CYAN}[3/6] Setting up Python virtual environment and dependencies...${COLOR_RESET}"
python3 -m venv "$TARGET_INSTALL_DIR/venv"
"$TARGET_INSTALL_DIR/venv/bin/pip" install --upgrade pip -q || true
"$TARGET_INSTALL_DIR/venv/bin/pip" install flask requests psutil Pillow nbtlib -q

# 8. Create Configuration Files
echo -e "${COLOR_CYAN}[4/6] Generating config.json and credentials...${COLOR_RESET}"
cat > "$TARGET_INSTALL_DIR/config.json" << EOF
{
  "admin_user": "admin",
  "admin_pass": "$FINAL_PASS",
  "server_dir": "$FINAL_MC_DIR",
  "service_name": "fiesta",
  "screen_session": "fiesta",
  "host": "0.0.0.0",
  "port": $FINAL_PORT
}
EOF

# Calculate SHA256 password hash for users.json
PASS_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('$FINAL_PASS'.encode('utf-8')).hexdigest())")
cat > "$TARGET_INSTALL_DIR/users.json" << EOF
{
  "admin": {
    "username": "admin",
    "password_hash": "$PASS_HASH",
    "role": "owner",
    "permissions": ["all"],
    "created_at": "$(date '+%Y-%m-%d %H:%M:%S')",
    "status": "active"
  }
}
EOF

# Ensure default branding if not existing
if [ ! -f "$TARGET_INSTALL_DIR/branding.json" ]; then
cat > "$TARGET_INSTALL_DIR/branding.json" << 'EOF'
{
  "brand_name": "GATEWAY-PRO",
  "tagline": "The Modern & Retro Minecraft Management Suite",
  "model_number": "Model No. GP-SERVER-X1",
  "browser_title": "FiestaPanel | Console",
  "footer_text": "FiestaPanel Software Suite • Open Source Minecraft Server Platform",
  "server_desc": "Gateway Console",
  "header_icon": "tplink",
  "header_icon_custom": ""
}
EOF
fi

# 9. Install panelctl CLI Tool
echo -e "${COLOR_CYAN}[5/6] Installing panelctl CLI utility to /usr/local/bin/panelctl...${COLOR_RESET}"
if [ -f "$TARGET_INSTALL_DIR/panelctl" ]; then
    chmod +x "$TARGET_INSTALL_DIR/panelctl"
    ln -sf "$TARGET_INSTALL_DIR/panelctl" /usr/local/bin/panelctl
fi

# 10. Install & Enable Systemd Service
echo -e "${COLOR_CYAN}[6/6] Configuring systemd daemon (gateway-panel.service)...${COLOR_RESET}"
cat > /etc/systemd/system/gateway-panel.service << EOF
[Unit]
Description=FiestaPanel Minecraft Management Suite Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$TARGET_INSTALL_DIR
Environment="GATEWAY_PORT=$FINAL_PORT"
Environment="GATEWAY_SERVER_DIR=$FINAL_MC_DIR"
ExecStart=$TARGET_INSTALL_DIR/venv/bin/python3 $TARGET_INSTALL_DIR/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable gateway-panel.service >/dev/null 2>&1 || true

# If installed on existing server where fiesta-portal was running, keep both or transition
if [ "$TARGET_INSTALL_DIR" != "/home/ubuntu/fiesta-portal" ]; then
    systemctl restart gateway-panel.service || true
else
    systemctl restart fiesta-portal.service || true
fi

# Detect Public IP
PUBLIC_IP=$(curl -s -m 3 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo -e "${COLOR_GREEN}╔═══════════════════════════════════════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_GREEN}║             🎉 FIESTAPANEL INSTALLED SUCCESSFULLY!                  ║${COLOR_RESET}"
echo -e "${COLOR_GREEN}╚═══════════════════════════════════════════════════════════════════════╝${COLOR_RESET}"
echo ""
echo -e "${COLOR_BOLD}Access Credentials & URLs:${COLOR_RESET}"
echo -e "  • Web Portal URL:    ${COLOR_CYAN}http://${PUBLIC_IP}:${FINAL_PORT}/${COLOR_RESET}"
echo -e "  • Localhost URL:     ${COLOR_CYAN}http://127.0.0.1:${FINAL_PORT}/${COLOR_RESET}"
echo -e "  • Username:          ${COLOR_BOLD}admin${COLOR_RESET}"
echo -e "  • Password:          ${COLOR_YELLOW}${FINAL_PASS}${COLOR_RESET}"
echo -e "  • Managed Server:    ${COLOR_CYAN}${FINAL_MC_DIR}${COLOR_RESET}"
echo ""
echo -e "${COLOR_BOLD}CLI Management Commands (panelctl):${COLOR_RESET}"
echo -e "  • Check status:      ${COLOR_CYAN}panelctl status${COLOR_RESET}"
echo -e "  • View live logs:    ${COLOR_CYAN}panelctl logs${COLOR_RESET}"
echo -e "  • Restart panel:     ${COLOR_CYAN}panelctl restart${COLOR_RESET}"
echo -e "  • Reset password:    ${COLOR_CYAN}panelctl reset-admin [new-password]${COLOR_RESET}"
echo -e "  • Change web port:   ${COLOR_CYAN}panelctl set-port [new-port]${COLOR_RESET}"
echo ""
echo -e "${COLOR_GREEN}Thank you for installing FiestaPanel! Enjoy managing your server.${COLOR_RESET}"
echo ""
