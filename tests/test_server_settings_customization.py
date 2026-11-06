import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import json
import tempfile
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as portal_app

class ServerSettingsCustomizationTests(unittest.TestCase):
    def setUp(self):
        portal_app.app.config['TESTING'] = True
        self.client = portal_app.app.test_client()
        self.csrf_token = "test-csrf-token"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        # Snapshot original globals
        self.orig_server_dir = portal_app.SERVER_DIR
        self.orig_service_name = portal_app.SERVICE_NAME
        self.orig_screen_session = portal_app.SCREEN_SESSION
        self.orig_server_config = portal_app.SERVER_CONFIG.copy()

        # Isolate config and branding files to temp directory
        self.temp_config = os.path.join(self.temp_dir.name, "config.json")
        self.temp_branding = os.path.join(self.temp_dir.name, "branding.json")
        if os.path.exists(portal_app.CONFIG_FILE):
            shutil.copy2(portal_app.CONFIG_FILE, self.temp_config)
        else:
            with open(self.temp_config, "w", encoding="utf-8") as f:
                json.dump({"autostart": True}, f)
        shutil.copy2(portal_app.BRANDING_FILE, self.temp_branding)

        self.patch_cfg = patch.object(portal_app, 'CONFIG_FILE', self.temp_config)
        self.patch_br = patch.object(portal_app, 'BRANDING_FILE', self.temp_branding)
        self.patch_cfg.start()
        self.patch_br.start()

    def tearDown(self):
        self.patch_cfg.stop()
        self.patch_br.stop()
        # Restore globals
        portal_app.SERVER_DIR = self.orig_server_dir
        portal_app.SERVICE_NAME = self.orig_service_name
        portal_app.SCREEN_SESSION = self.orig_screen_session
        portal_app.SERVER_CONFIG = self.orig_server_config
        portal_app.server_runner.server_dir = self.orig_server_dir
        portal_app.server_runner.service_name = self.orig_service_name
        portal_app.server_runner.screen_session = self.orig_screen_session

    def _login(self, role="owner", permissions=None):
        if permissions is None:
            permissions = ["all"]
        user = portal_app.load_users().get('admin', {})
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = 'admin'
            sess['role'] = role
            sess['permissions'] = permissions
            sess['csrf_token'] = self.csrf_token
            sess['password_version'] = portal_app.session_password_version(user.get('password_hash'))

    def _post(self, url, data=None):
        headers = {"X-CSRF-Token": self.csrf_token}
        if data is not None:
            headers["Content-Type"] = "application/json"
            return self.client.post(url, data=json.dumps(data), headers=headers)
        return self.client.post(url, headers=headers)

    def test_world_spawn_get_and_post(self):
        self._login()
        # GET default spawn
        res = self.client.get('/api/world/spawn')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('spawn', data)
        self.assertIn('x', data['spawn'])
        self.assertIn('y', data['spawn'])
        self.assertIn('z', data['spawn'])

        # POST update spawn coordinates
        new_coords = {
            "x": 100,
            "y": 72,
            "z": -250,
            "dimension": "minecraft:overworld",
            "radius": 5
        }
        res_post = self._post('/api/world/spawn', new_coords)
        self.assertEqual(res_post.status_code, 200)
        post_data = res_post.get_json()
        self.assertTrue(post_data.get('success'))
        self.assertEqual(post_data['spawn']['x'], 100)
        self.assertEqual(post_data['spawn']['y'], 72)
        self.assertEqual(post_data['spawn']['z'], -250)
        self.assertEqual(post_data['spawn']['radius'], 5)

        # Verify get_spawn_coordinates returns updated values
        current = portal_app.get_spawn_coordinates()
        self.assertEqual(current['x'], 100)
        self.assertEqual(current['y'], 72)
        self.assertEqual(current['z'], -250)

        # Test tp_spawn uses updated coordinates
        with patch.object(portal_app, 'send_mc_command', return_value=(True, 'Executed')) as mock_cmd:
            res_tp = self._post('/api/player/action', {"player": "Notch", "action": "tp_spawn"})
            self.assertEqual(res_tp.status_code, 200)
            mock_cmd.assert_called_with("tp Notch 100 72 -250")

    def test_world_spawn_invalid_input(self):
        self._login()
        res = self._post('/api/world/spawn', {"x": "not-a-number", "y": 64, "z": 0})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get('success'))

    def test_system_settings_get_and_post(self):
        self._login(role="owner", permissions=["all"])
        res = self.client.get('/api/system/settings')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('server_dir', data['settings'])
        self.assertIn('service_name', data['settings'])
        self.assertIn('screen_session', data['settings'])
        self.assertIn('backup_dir', data['settings'])

        # Update environment settings
        test_sdir = os.path.join(self.temp_dir.name, "custom_mc")
        test_bdir = os.path.join(self.temp_dir.name, "custom_backups")
        payload = {
            "server_dir": test_sdir,
            "service_name": "custom-mc-svc",
            "screen_session": "custom-mc-screen",
            "backup_dir": test_bdir
        }
        res_post = self._post('/api/system/settings', payload)
        self.assertEqual(res_post.status_code, 200)
        post_data = res_post.get_json()
        self.assertTrue(post_data.get('success'))
        self.assertEqual(post_data['settings']['service_name'], "custom-mc-svc")
        self.assertEqual(post_data['settings']['screen_session'], "custom-mc-screen")

        # Verify send_mc_command uses the updated screen session
        with patch("subprocess.run") as mock_sub:
            portal_app.send_mc_command("say Hello World")
            mock_sub.assert_called_once()
            args = mock_sub.call_args[0][0]
            self.assertIn("-S", args)
            screen_idx = args.index("-S") + 1
            self.assertEqual(args[screen_idx], "custom-mc-screen")

    def test_branding_public_site_url_and_bedrock_name(self):
        self._login(role="owner", permissions=["all"])
        # Update branding with custom public site and Bedrock name
        payload = {
            "brand_name": "ACME-CRAFT",
            "tagline": "Best Survival Server",
            "model_number": "Model No. ACME-01",
            "browser_title": "ACME-CRAFT | Gateway",
            "footer_text": "Custom Server Footer",
            "public_site_url": "https://acmecraft.example.com",
            "bedrock_server_name": "AcmeBedrockSMP",
            "server_domain": "play.acmecraft.example.com"
        }
        res = self._post('/api/branding', payload)
        self.assertEqual(res.status_code, 200)
        b_data = res.get_json().get('branding', {})
        self.assertEqual(b_data.get('public_site_url'), "https://acmecraft.example.com")
        self.assertEqual(b_data.get('bedrock_server_name'), "AcmeBedrockSMP")

        # Verify rendered dashboard contains the custom public site link
        with patch.object(portal_app.server_runner, 'is_running', return_value=True):
            res_dash = self.client.get('/')
            self.assertEqual(res_dash.status_code, 200)
            html = res_dash.get_data(as_text=True)
            self.assertIn('https://acmecraft.example.com', html)
            self.assertIn('AcmeBedrockSMP', html)

        # Now test blanking public_site_url hides the public site button
        payload['public_site_url'] = ''
        res_blank = self._post('/api/branding', payload)
        self.assertEqual(res_blank.status_code, 200)
        with patch.object(portal_app.server_runner, 'is_running', return_value=True):
            res_dash_blank = self.client.get('/')
            html_blank = res_dash_blank.get_data(as_text=True)
            self.assertIn('id="header-public-site-link"', html_blank)
            self.assertIn('display: none', html_blank)

    def test_permissions_enforced_on_system_settings(self):
        mock_users = {
            "mod": {
                "username": "mod",
                "password_hash": "scrypt:dummy",
                "role": "moderator",
                "permissions": ["console"],
                "status": "active"
            }
        }
        with patch.object(portal_app, 'load_users', return_value=mock_users), \
             patch.object(portal_app, 'session_password_version', return_value="v1"):
            with self.client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user'] = 'mod'
                sess['role'] = 'moderator'
                sess['permissions'] = ['console']
                sess['csrf_token'] = self.csrf_token
                sess['password_version'] = "v1"
            res = self._post('/api/system/settings', {"service_name": "hacked"})
            self.assertEqual(res.status_code, 403)

    def test_multi_jre_switcher_api(self):
        self._login()
        # 1. GET /api/system/java
        res_get = self.client.get('/api/system/java')
        self.assertEqual(res_get.status_code, 200)
        d_get = res_get.get_json()
        self.assertTrue(d_get.get('success'))
        self.assertIn('java', d_get)
        self.assertIn('available', d_get)
        self.assertIsInstance(d_get['available'], list)

        # 2. POST with invalid binary path
        res_inv = self._post('/api/system/java', {"java_path": "/invalid/nonexistent/java/bin"})
        self.assertEqual(res_inv.status_code, 400)

        # 3. POST with test_only flag on valid binary
        host_java = shutil.which("java") or "/usr/bin/java"
        res_test = self._post('/api/system/java', {"java_path": host_java, "test_only": True})
        self.assertEqual(res_test.status_code, 200)
        self.assertTrue(res_test.get_json().get('success'))
        # Config should NOT have changed
        self.assertNotIn("java_path", portal_app.SERVER_CONFIG)

        # 4. POST to switch to valid binary
        res_switch = self._post('/api/system/java', {"java_path": host_java})
        self.assertEqual(res_switch.status_code, 200)
        self.assertEqual(portal_app.SERVER_CONFIG.get("java_path"), host_java)

        # Verify detect_java_bin() now returns the configured binary
        self.assertEqual(portal_app.detect_java_bin(), host_java)

        # 5. POST to reset to default
        res_reset = self._post('/api/system/java', {"java_path": "default"})
        self.assertEqual(res_reset.status_code, 200)
        self.assertNotIn("java_path", portal_app.SERVER_CONFIG)

        # 6. Unauthorized subuser should receive 403
        mock_users = {
            "helper": {
                "username": "helper",
                "password_hash": "scrypt:dummy",
                "role": "helper",
                "permissions": ["chat"],
                "status": "active"
            }
        }
        with patch.object(portal_app, 'load_users', return_value=mock_users), \
             patch.object(portal_app, 'session_password_version', return_value="v1"):
            with self.client.session_transaction() as sess:
                sess['logged_in'] = True
                sess['user'] = 'helper'
                sess['role'] = 'helper'
                sess['permissions'] = ['chat']
                sess['csrf_token'] = self.csrf_token
                sess['password_version'] = "v1"
            res_denied = self._post('/api/system/java', {"java_path": host_java})
            self.assertEqual(res_denied.status_code, 403)

    def test_api_connect_dynip_fallback(self):
        self._login()
        res = self.client.get('/api/connect/dynip')
        self.assertEqual(res.status_code, 200)
        d = res.get_json()
        self.assertTrue(d.get('success'))
        self.assertIn('public_ip', d)
        self.assertIn('java_port', d)
        self.assertIn('dynip_java', d)
        self.assertIn('bedrock_port', d)
        self.assertIn('dynip_bedrock', d)
        self.assertIn('domain', d)
        self.assertTrue(d['dynip_java'].endswith(f":{d['java_port']}"))
        self.assertTrue(d['dynip_bedrock'].endswith(f":{d['bedrock_port']}"))


if __name__ == '__main__':
    unittest.main()
