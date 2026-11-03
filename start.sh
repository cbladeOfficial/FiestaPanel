#!/usr/bin/env bash
# ==============================================================================
# FiestaPanel - Standalone Launcher for Linux & macOS
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COLOR_CYAN="\033[1;36m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_CYAN}Starting FiestaPanel in standalone mode...${COLOR_RESET}"

# 1. Locate Python
PY_BIN="python3"
if [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
    PY_BIN="$SCRIPT_DIR/venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
fi

# 2. Virtual environment check
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo -e "${COLOR_YELLOW}Setting up Python virtual environment...${COLOR_RESET}"
    $PY_BIN -m venv "$SCRIPT_DIR/venv"
    "$SCRIPT_DIR/venv/bin/pip" install --upgrade pip -q || true
    "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q
    PY_BIN="$SCRIPT_DIR/venv/bin/python3"
fi

# 3. Config check
if [ ! -f "$SCRIPT_DIR/config.json" ]; then
    echo -e "${COLOR_YELLOW}Creating initial config.json...${COLOR_RESET}"
    cp "$SCRIPT_DIR/config.example.json" "$SCRIPT_DIR/config.json"
fi

mkdir -p "$SCRIPT_DIR/minecraft_server"

echo -e "${COLOR_GREEN}Launching FiestaPanel on http://localhost:8080${COLOR_RESET}"
exec "$PY_BIN" "$SCRIPT_DIR/app.py"
