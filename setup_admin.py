"""Create the initial FiestaPanel owner without overwriting existing accounts."""
import argparse
import getpass
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default=os.environ.get('FIESTA_DATA_DIR') or
                        os.environ.get('GATEWAY_DATA_DIR') or os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument('--non-interactive', action='store_true')
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    users_path = data_dir / 'users.json'
    if users_path.exists():
        with users_path.open(encoding='utf-8') as handle:
            users = json.load(handle)
        if not isinstance(users, dict) or not users:
            raise ValueError('Existing users.json is empty or invalid; restore it or remove it explicitly before setup.')
        print('Existing panel accounts preserved.')
        return

    username = os.environ.get('FIESTA_ADMIN_USER', 'admin').strip()
    if not re.fullmatch(r'[A-Za-z0-9_-]{3,24}', username):
        raise ValueError('Owner username must be 3–24 letters, digits, underscores or hyphens.')
    password = os.environ.get('FIESTA_ADMIN_PASS')
    if password is None or password == '':
        if args.non_interactive:
            raise ValueError('First setup requires FIESTA_ADMIN_PASS (at least 12 characters).')
        try:
            password = getpass.getpass('Create admin password (at least 12 characters): ').strip()
            confirm = getpass.getpass('Confirm admin password: ').strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ValueError('Password setup cancelled; no account was created.') from exc
        if password != confirm:
            raise ValueError('Passwords do not match; no account was created.')
    password = password.strip()
    if len(password) < 12:
        raise ValueError('Admin password must be at least 12 characters; no account was created.')
    users = {username: {'username': username, 'password_hash': generate_password_hash(password, method='scrypt'),
                        'role': 'owner', 'permissions': ['all'], 'status': 'active',
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
    fd = os.open(users_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(users, handle, indent=2)
    except BaseException:
        users_path.unlink(missing_ok=True)
        raise
    print(f'Owner account {username!r} created.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'Owner setup failed: {exc}', file=sys.stderr)
        sys.exit(1)
