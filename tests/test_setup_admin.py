import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import check_password_hash

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('setup_admin', ROOT / 'setup_admin.py')
setup_admin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_admin)


class SetupAdminTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)

    def setup(self, password=None):
        env = os.environ.copy()
        env.pop('FIESTA_ADMIN_USER', None)
        env.pop('FIESTA_ADMIN_PASS', None)
        if password is not None:
            env['FIESTA_ADMIN_PASS'] = password
        return subprocess.run([sys.executable, str(ROOT / 'setup_admin.py'), '--data-dir', str(self.data), '--non-interactive'],
                              env=env, capture_output=True, text=True)

    def test_noninteractive_setup_hashes_and_preserves_credentials(self):
        password = "twelve'\"$\\! characters"
        result = self.setup(password)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.data / 'users.json'
        original = path.read_bytes()
        account = json.loads(original)['admin']
        self.assertTrue(account['password_hash'].startswith('scrypt:'))
        self.assertTrue(check_password_hash(account['password_hash'], password))
        self.assertNotIn(password, path.read_text())
        self.assertNotIn(password, result.stdout + result.stderr)
        if os.name != 'nt':
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        result = self.setup('another strong password')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_bytes(), original)

    def test_missing_and_short_passwords_fail_without_creating_account(self):
        for password in (None, 'too short'):
            result = self.setup(password)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.data / 'users.json').exists())

    def test_interactive_confirmation_is_required(self):
        env = dict(os.environ)
        env.pop('FIESTA_ADMIN_PASS', None)
        env.pop('FIESTA_ADMIN_USER', None)
        with patch.dict(os.environ, env, clear=True), patch.object(sys, 'argv', ['setup_admin.py', '--data-dir', str(self.data)]), \
             patch('getpass.getpass', side_effect=['first password long', 'different password']):
            with self.assertRaisesRegex(ValueError, 'do not match'):
                setup_admin.main()
        self.assertFalse((self.data / 'users.json').exists())

    def test_invalid_existing_users_are_not_overwritten(self):
        path = self.data / 'users.json'
        path.write_text('{}', encoding='utf-8')
        self.assertNotEqual(self.setup('a secure password').returncode, 0)
        self.assertEqual(path.read_text(), '{}')

    def test_container_entrypoint_requires_password_only_on_first_run(self):
        entry = (ROOT / 'entrypoint.sh').read_text().replace('/app/setup_admin.py', str(ROOT / 'setup_admin.py'))
        script = self.data / 'entrypoint.sh'
        script.write_text(entry)
        env = os.environ.copy()
        env.update(FIESTA_DATA_DIR=str(self.data / 'data'), FIESTA_SERVER_DIR=str(self.data / 'server'))
        env.pop('FIESTA_ADMIN_PASS', None)
        def run():
            return subprocess.run(['bash', str(script), 'true'], env=env, capture_output=True, text=True)
        self.assertNotEqual(run().returncode, 0)
        env['FIESTA_ADMIN_PASS'] = 'a secure container password'
        self.assertEqual(run().returncode, 0)
        path = self.data / 'data' / 'users.json'
        original = path.read_bytes()
        env.pop('FIESTA_ADMIN_PASS')
        self.assertEqual(run().returncode, 0)
        self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
