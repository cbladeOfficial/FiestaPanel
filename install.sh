#!/usr/bin/env bash
# ==============================================================================
# FiestaPanel - Turnkey Minecraft Server Management Suite Installer
# Version: 2.1.0
# License: MIT
# Description: Automated one-line installer for Linux & macOS servers
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
  ║     ███████╗██╗███████╗███████╗████████╗ █████╗                       ║
  ║     ██╔════╝██║██╔════╝██╔════╝╚══██╔══╝██╔══██╗                      ║
  ║     █████╗  ██║█████╗  ███████╗   ██║   ███████║                      ║
  ║     ██╔══╝  ██║██╔══╝  ╚════██║   ██║   ██╔══██║                      ║
  ║     ██║     ██║███████╗███████║   ██║   ██║  ██║                      ║
  ║     ╚═╝     ╚═╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝                      ║
  ║                 P A N E L   S O F T W A R E                           ║
  ║                                                                       ║
  ║        Turnkey Retro & Modern Minecraft Management Suite              ║
  ╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${COLOR_RESET}"

IS_DARWIN=false
if [[ "$(uname -s)" == "Darwin" ]]; then
    IS_DARWIN=true
fi

# 1. Require Root on Linux
if [ "$IS_DARWIN" = false ] && [ "$EUID" -ne 0 ]; then
    echo -e "${COLOR_RED}Error: On Linux, the installer must be executed as root or with sudo.${COLOR_RESET}"
    echo "Please re-run: sudo bash $0"
    exit 1
fi

# Parse CLI Arguments
MC_DIR_ARG=""
PORT_ARG=""
ADMIN_PASS_ARG=""
UNATTENDED=false
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

if [ "$IS_DARWIN" = true ]; then
    TARGET_INSTALL_DIR="$HOME/fiestapanel"
    DEFAULT_MC="$HOME/minecraft_server"
else
    TARGET_INSTALL_DIR="/opt/fiestapanel"
    DEFAULT_MC="/opt/minecraft"
fi

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
echo "Target Platform: $(uname -s) ($(uname -m))"
echo ""

# 2. Configure Minecraft Server Path
if [ -d "/home/ubuntu/fiesta" ]; then
    DEFAULT_MC="/home/ubuntu/fiesta"
fi

if [ -n "$MC_DIR_ARG" ]; then
    FINAL_MC_DIR="$MC_DIR_ARG"
elif [ "$UNATTENDED" = true ]; then
    FINAL_MC_DIR="$DEFAULT_MC"
else
    echo -e "${COLOR_YELLOW}Enter the absolute path to your Minecraft server directory:${COLOR_RESET}"
    read -rp "Path [$DEFAULT_MC]: " USER_MC_DIR </dev/tty
    FINAL_MC_DIR="${USER_MC_DIR:-$DEFAULT_MC}"
fi

mkdir -p "$FINAL_MC_DIR"

# 3. Configure Port
DEFAULT_PORT=8080
if [ -n "$PORT_ARG" ]; then
    FINAL_PORT="$PORT_ARG"
elif [ "$UNATTENDED" = true ]; then
    FINAL_PORT=$DEFAULT_PORT
else
    echo -e "${COLOR_YELLOW}Enter the Web Panel HTTP port:${COLOR_RESET}"
    read -rp "Port [$DEFAULT_PORT]: " USER_PORT </dev/tty
    FINAL_PORT="${USER_PORT:-$DEFAULT_PORT}"
fi

# 4. Owner credentials are initialized after dependencies are installed.
# --admin-pass remains available for automation; environment input avoids a shell argument.
if [ -n "$ADMIN_PASS_ARG" ]; then
    export FIESTA_ADMIN_PASS="$ADMIN_PASS_ARG"
fi

# 5. Install System Dependencies
echo ""
echo -e "${COLOR_CYAN}[1/6] Installing system prerequisites (python3, pip, venv)...${COLOR_RESET}"
if [ "$IS_DARWIN" = true ]; then
    if command -v brew >/dev/null 2>&1; then
        brew install python3 curl tar 2>/dev/null || true
    fi
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq || true
    apt-get install -y -qq python3 python3-pip python3-venv curl tar screen >/dev/null 2>&1 || {
        apt-get install -y python3 python3-pip python3-venv curl tar
    }
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y python3 python3-pip curl tar screen 2>/dev/null || true
elif command -v yum >/dev/null 2>&1; then
    yum install -y python3 python3-pip curl tar screen 2>/dev/null || true
fi

# 6. Deploy FiestaPanel Codebase
echo -e "${COLOR_CYAN}[2/6] Deploying application files into $TARGET_INSTALL_DIR...${COLOR_RESET}"
mkdir -p "$TARGET_INSTALL_DIR"

if [ -n "$SOURCE_DIR" ] && [ -f "$SOURCE_DIR/app.py" ]; then
    cp -r "$SOURCE_DIR/app.py" "$TARGET_INSTALL_DIR/"
    cp -r "$SOURCE_DIR/templates" "$TARGET_INSTALL_DIR/"
    cp -r "$SOURCE_DIR/static" "$TARGET_INSTALL_DIR/" 2>/dev/null || mkdir -p "$TARGET_INSTALL_DIR/static"
    cp -r "$SOURCE_DIR/items_textures.json" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/branding.json" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/requirements.txt" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/addon_manager.py" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/setup_admin.py" "$TARGET_INSTALL_DIR/"
    cp -r "$SOURCE_DIR/addons" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/fiestapanel" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/fiestapanel.py" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/panelctl" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/panelctl.py" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
    cp -r "$SOURCE_DIR/start.sh" "$TARGET_INSTALL_DIR/" 2>/dev/null || true
else
    echo "Downloading FiestaPanel application package from GitHub..."
    if command -v git >/dev/null 2>&1; then
        git clone --depth 1 https://github.com/open-fiestasmp/FiestaPanel.git "$TARGET_INSTALL_DIR" 2>/dev/null || true
    fi
    if [ ! -f "$TARGET_INSTALL_DIR/app.py" ]; then
        curl -sSL "https://github.com/open-fiestasmp/FiestaPanel/archive/refs/heads/main.tar.gz" | tar -xz --strip-components=1 -C "$TARGET_INSTALL_DIR" 2>/dev/null || {
            curl -sSL "https://fiesta.debarkak.xyz/static/fiestapanel-latest.tar.gz" | tar -xz -C "$TARGET_INSTALL_DIR" 2>/dev/null || {
                curl -sSL "https://raw.githubusercontent.com/open-fiestasmp/FiestaPanel/main/app.py" -o "$TARGET_INSTALL_DIR/app.py"
            }
        }
    fi
fi

# 7. Setup Virtual Environment & Python Packages
echo -e "${COLOR_CYAN}[3/6] Setting up Python virtual environment and dependencies...${COLOR_RESET}"
python3 -m venv "$TARGET_INSTALL_DIR/venv"
"$TARGET_INSTALL_DIR/venv/bin/pip" install --upgrade pip -q || true
"$TARGET_INSTALL_DIR/venv/bin/pip" install -r "$TARGET_INSTALL_DIR/requirements.txt" -q

# 8. Initialize credentials and configuration without overwriting an existing installation.
echo -e "${COLOR_CYAN}[4/6] Checking credentials and config.json...${COLOR_RESET}"
SETUP_FLAGS=()
if [ "$UNATTENDED" = true ]; then SETUP_FLAGS+=(--non-interactive); fi
"$TARGET_INSTALL_DIR/venv/bin/python3" "$TARGET_INSTALL_DIR/setup_admin.py" --data-dir "$TARGET_INSTALL_DIR" "${SETUP_FLAGS[@]}"
if [ ! -f "$TARGET_INSTALL_DIR/config.json" ]; then
    FIESTA_SETUP_MC_DIR="$FINAL_MC_DIR" FIESTA_SETUP_PORT="$FINAL_PORT" \
      "$TARGET_INSTALL_DIR/venv/bin/python3" - "$TARGET_INSTALL_DIR/config.json" <<'PYCONFIG'
import json, os, sys
config = {'admin_user': 'admin', 'server_dir': os.environ['FIESTA_SETUP_MC_DIR'],
          'service_name': 'fiestapanel', 'screen_session': 'fiesta',
          'host': '0.0.0.0', 'port': int(os.environ['FIESTA_SETUP_PORT'])}
with open(sys.argv[1], 'x', encoding='utf-8') as f:
    json.dump(config, f, indent=2)
PYCONFIG
fi

# Ensure default branding
if [ ! -f "$TARGET_INSTALL_DIR/branding.json" ]; then
cat > "$TARGET_INSTALL_DIR/branding.json" << 'EOF'
{
  "brand_name": "FIESTA-LINK",
  "tagline": "The Reliable Choice",
  "model_number": "Model No. FS-GATEWAY-PRO",
  "browser_title": "FiestaPanel | Console",
  "footer_text": "Made by Fiesta and it's developers, Mockup UI of Legacy TP-Link Portal",
  "server_desc": "Gateway Console",
  "header_icon": "tplink",
  "header_icon_custom": ""
}
EOF
fi

# 9. Install fiestapanel CLI Tool
echo -e "${COLOR_CYAN}[5/6] Installing fiestapanel CLI utility...${COLOR_RESET}"
if [ -f "$TARGET_INSTALL_DIR/fiestapanel" ]; then
    chmod +x "$TARGET_INSTALL_DIR/fiestapanel" "$TARGET_INSTALL_DIR/fiestapanel.py" "$TARGET_INSTALL_DIR/panelctl" "$TARGET_INSTALL_DIR/panelctl.py" 2>/dev/null || true
    if [ "$IS_DARWIN" = true ]; then
        mkdir -p "$HOME/.local/bin"
        ln -sf "$TARGET_INSTALL_DIR/fiestapanel" "$HOME/.local/bin/fiestapanel" 2>/dev/null || true
        ln -sf "$TARGET_INSTALL_DIR/fiestapanel" "$HOME/.local/bin/panelctl" 2>/dev/null || true
    else
        ln -sf "$TARGET_INSTALL_DIR/fiestapanel" /usr/local/bin/fiestapanel 2>/dev/null || true
        ln -sf "$TARGET_INSTALL_DIR/fiestapanel" /usr/local/bin/panelctl 2>/dev/null || true
    fi
fi

# 10. Install & Enable Systemd Service (Linux only)
if [ "$IS_DARWIN" = false ] && command -v systemctl >/dev/null 2>&1; then
    echo -e "${COLOR_CYAN}[6/6] Configuring systemd daemon (fiestapanel.service)...${COLOR_RESET}"
    cat > /etc/systemd/system/fiestapanel.service << EOF
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
    systemctl enable fiestapanel.service >/dev/null 2>&1 || true

    if [ "$TARGET_INSTALL_DIR" != "/home/ubuntu/fiesta-portal" ]; then
        systemctl restart fiestapanel.service || true
    else
        systemctl restart fiesta-portal.service || true
    fi
else
    echo -e "${COLOR_CYAN}[6/6] Created start.sh launcher in $TARGET_INSTALL_DIR/start.sh...${COLOR_RESET}"
    chmod +x "$TARGET_INSTALL_DIR/start.sh" 2>/dev/null || true
fi

# Detect Public IP
PUBLIC_IP=$(curl -s -m 3 https://api.ipify.org 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo ""
echo -e "${COLOR_GREEN}╔═══════════════════════════════════════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_GREEN}║             🎉 FIESTAPANEL INSTALLED SUCCESSFULLY!                  ║${COLOR_RESET}"
echo -e "${COLOR_GREEN}╚═══════════════════════════════════════════════════════════════════════╝${COLOR_RESET}"
echo ""
echo -e "${COLOR_BOLD}Access Credentials & URLs:${COLOR_RESET}"
echo -e "  • Web Portal URL:    ${COLOR_CYAN}http://${PUBLIC_IP}:${FINAL_PORT}/${COLOR_RESET}"
echo -e "  • Localhost URL:     ${COLOR_CYAN}http://127.0.0.1:${FINAL_PORT}/${COLOR_RESET}"
echo -e "  • Username:          ${COLOR_BOLD}admin${COLOR_RESET}"
echo -e "  • Password:          ${COLOR_YELLOW}Your chosen password (existing accounts are preserved)${COLOR_RESET}"
echo -e "  • Managed Server:    ${COLOR_CYAN}${FINAL_MC_DIR}${COLOR_RESET}"
echo ""
echo -e "${COLOR_BOLD}CLI Management Commands (fiestapanel):${COLOR_RESET}"
echo -e "  • Check status:      ${COLOR_CYAN}fiestapanel status${COLOR_RESET}"
echo -e "  • View live logs:    ${COLOR_CYAN}fiestapanel logs${COLOR_RESET}"
echo -e "  • Restart panel:     ${COLOR_CYAN}fiestapanel restart${COLOR_RESET}"
echo -e "  • Reset password:    ${COLOR_CYAN}fiestapanel reset-admin${COLOR_RESET}"
echo -e "  • Change web port:   ${COLOR_CYAN}fiestapanel set-port [port]${COLOR_RESET}"
echo ""
echo -e "${COLOR_GREEN}Thank you for installing FiestaPanel! Enjoy managing your server.${COLOR_RESET}"
echo ""
