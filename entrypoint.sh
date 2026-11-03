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

# Initialize default admin account if not already present
if [ -n "$FIESTA_ADMIN_USER" ] && [ -n "$FIESTA_ADMIN_PASS" ]; then
    python3 -c "
import os, json, hashlib

users_file = os.path.join('$DATA_DIR', 'users.json')
admin_u = os.environ.get('FIESTA_ADMIN_USER', 'admin')
admin_p = os.environ.get('FIESTA_ADMIN_PASS', 'admin')
p_hash = hashlib.sha256(admin_p.encode('utf-8')).hexdigest()

users = {}
if os.path.exists(users_file):
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except Exception:
        users = {}

if admin_u not in users:
    users[admin_u] = {
        'username': admin_u,
        'password_hash': p_hash,
        'role': 'owner',
        'permissions': ['all'],
        'created_at': '2026-11-03 12:00:00',
        'status': 'active'
    }
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)
"
fi

echo "=========================================================="
echo "  FiestaPanel Server Suite Container"
echo "  Web Dashboard:  http://0.0.0.0:${FIESTA_PORT:-8080}"
echo "  Minecraft Path: $SERVER_DIR"
echo "  Data Path:      $DATA_DIR"
echo "=========================================================="

exec "$@"
