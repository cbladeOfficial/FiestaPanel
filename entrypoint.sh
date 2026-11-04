#!/bin/bash
set -e

DATA_DIR="${FIESTA_DATA_DIR:-/app/data}"
SERVER_DIR="${FIESTA_SERVER_DIR:-/server}"

mkdir -p "$DATA_DIR" "$SERVER_DIR" "$DATA_DIR/uploads"

# Ensure branding.json exists in persistent DATA_DIR
if [ ! -f "$DATA_DIR/branding.json" ] && [ -f "/app/branding.json" ]; then
    cp "/app/branding.json" "$DATA_DIR/branding.json"
fi

# Ensure uploads folder is accessible
if [ -d "/app/static" ] && [ ! -d "/app/static/uploads" ]; then
    mkdir -p "/app/static/uploads"
fi

# Containers cannot prompt reliably. Require a supplied password on first setup.
python3 /app/setup_admin.py --data-dir "$DATA_DIR" --non-interactive

echo "=========================================================="
echo "  FiestaPanel Server Suite Container"
echo "  Web Dashboard:  http://0.0.0.0:${FIESTA_PORT:-8080}"
echo "  Minecraft Path: $SERVER_DIR"
echo "  Data Path:      $DATA_DIR"
echo "=========================================================="

exec "$@"
