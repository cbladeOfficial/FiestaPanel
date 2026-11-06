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
from cloud_backups import CloudBackupManager, DEFAULT_CLOUD_CONFIG

class CloudOffsiteBackupsTests(unittest.TestCase):
    def setUp(self):
        portal_app.app.config['TESTING'] = True
        self.client = portal_app.app.test_client()
        self.csrf_token = "test-cloud-csrf-token"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        # Mock CloudBackupManager instance with isolated directory
        self.mgr = CloudBackupManager(self.temp_dir.name)
        self.orig_mgr = portal_app.cloud_backup_mgr
        portal_app.cloud_backup_mgr = self.mgr
        self.addCleanup(self._restore_mgr)

    def _restore_mgr(self):
        portal_app.cloud_backup_mgr = self.orig_mgr

    def _login(self, user_name="admin", role="owner", perms=None):
        if perms is None:
            perms = ["all"]
        user = portal_app.load_users().get(user_name, {})
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = user_name
            sess["role"] = role
            sess["permissions"] = perms
            sess["csrf_token"] = self.csrf_token
            sess["password_version"] = portal_app.session_password_version(user.get("password_hash"))

    def _post(self, url, data=None):
        headers = {
            "X-CSRF-Token": self.csrf_token,
            "Content-Type": "application/json"
        }
        return self.client.post(url, data=json.dumps(data or {}), headers=headers)

    # ── CloudBackupManager Unit Tests ────────────────────────────────────────
    def test_manager_config_persistence_and_masking(self):
        cfg = self.mgr.load_config()
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["provider"], "s3")

        ok, msg = self.mgr.save_config({
            "enabled": True,
            "provider": "s3",
            "retention_count": 8,
            "s3": {
                "endpoint_url": "https://test.r2.cloudflarestorage.com",
                "bucket_name": "mc-test-bucket",
                "access_key_id": "TEST_KEY_ID",
                "secret_access_key": "SUPER_SECRET_VALUE"
            }
        })
        self.assertTrue(ok)

        # Verify masked export
        masked = self.mgr.get_masked_config()
        self.assertTrue(masked["enabled"])
        self.assertEqual(masked["s3"]["access_key_id"], "TEST_KEY_ID")
        self.assertTrue(masked["s3"]["has_secret"])
        self.assertEqual(masked["s3"]["secret_access_key"], "••••••••••••••••")

        # Verify resaving with mask preserves original secret
        ok, msg = self.mgr.save_config({
            "s3": {
                "secret_access_key": "••••••••••••••••"
            }
        })
        self.assertTrue(ok)
        raw_cfg = self.mgr.load_config()
        self.assertEqual(raw_cfg["s3"]["secret_access_key"], "SUPER_SECRET_VALUE")

    @patch("cloud_backups.boto3.client")
    def test_s3_connection_test_success(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client
        self.mgr.save_config({
            "enabled": True,
            "provider": "s3",
            "s3": {
                "bucket_name": "test-bucket",
                "access_key_id": "K",
                "secret_access_key": "S"
            }
        })

        ok, msg = self.mgr.test_connection()
        self.assertTrue(ok)
        self.assertIn("Successfully connected", msg)

    @patch("cloud_backups.requests.request")
    def test_webdav_connection_test_success(self, mock_req):
        mock_resp = MagicMock()
        mock_resp.status_code = 207
        mock_req.return_value = mock_resp

        self.mgr.save_config({
            "enabled": True,
            "provider": "webdav",
            "webdav": {
                "url": "https://nextcloud.example.com/remote.php/dav/files/user/backups",
                "username": "user",
                "password": "pw"
            }
        })

        ok, msg = self.mgr.test_connection()
        self.assertTrue(ok)
        self.assertIn("Successfully connected", msg)

    @patch("cloud_backups.boto3.client")
    def test_s3_upload_and_status(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client

        # Create dummy local backup file
        test_file = os.path.join(self.temp_dir.name, "server_backup_test.tar.gz")
        with open(test_file, "wb") as f:
            f.write(b"tarball-binary-content-12345")

        self.mgr.save_config({
            "enabled": True,
            "provider": "s3",
            "s3": {
                "bucket_name": "test-bucket",
                "access_key_id": "K",
                "secret_access_key": "S",
                "prefix": "backups/"
            }
        })

        ok, msg = self.mgr.upload_file(test_file)
        self.assertTrue(ok)
        mock_client.upload_file.assert_called_once()

        st = self.mgr.get_status()
        self.assertFalse(st["active"])
        self.assertIsNotNone(st["last_sync"])

    @patch("cloud_backups.boto3.client")
    def test_retention_pruning(self, mock_boto):
        mock_client = MagicMock()
        mock_boto.return_value = mock_client

        self.mgr.save_config({
            "provider": "s3",
            "retention_count": 2,
            "s3": {
                "bucket_name": "test-bucket",
                "access_key_id": "K",
                "secret_access_key": "S"
            }
        })

        # Mock list_remote_backups returning 4 files
        with patch.object(self.mgr, "list_remote_backups") as mock_list:
            mock_list.return_value = [
                {"filename": "backup_4.tar.gz"},
                {"filename": "backup_3.tar.gz"},
                {"filename": "backup_2.tar.gz"},
                {"filename": "backup_1.tar.gz"},
            ]
            deleted = self.mgr.prune_retention()
            self.assertEqual(deleted, 2)
            self.assertEqual(mock_client.delete_object.call_count, 2)

    # ── Flask API Endpoint Tests ─────────────────────────────────────────────
    def test_cloud_config_endpoints_require_auth(self):
        # Unauthenticated API request returns 401
        resp = self.client.get("/api/backup/cloud/config")
        self.assertEqual(resp.status_code, 401)

        # Authenticated owner request succeeds
        self._login()
        resp = self.client.get("/api/backup/cloud/config")
        self.assertEqual(resp.status_code, 200)
        d = resp.get_json()
        self.assertTrue(d["success"])
        self.assertIn("config", d)

    def test_cloud_config_post_and_subuser_permissions(self):
        # Moderator without backups permission gets 403
        mock_users = {
            "mod": {
                "username": "mod",
                "role": "moderator",
                "permissions": ["console"],
                "status": "active",
                "password_hash": "scrypt:dummy"
            }
        }
        with patch.object(portal_app, 'load_users', return_value=mock_users), \
             patch.object(portal_app, 'session_password_version', return_value="v1"):
            with self.client.session_transaction() as sess:
                sess["logged_in"] = True
                sess["user"] = "mod"
                sess["role"] = "moderator"
                sess["permissions"] = ["console"]
                sess["csrf_token"] = self.csrf_token
                sess["password_version"] = "v1"

            resp = self._post("/api/backup/cloud/config", {"enabled": True})
            self.assertEqual(resp.status_code, 403)

        # Owner succeeds
        self._login(user_name="admin", role="owner", perms=["all"])
        resp = self._post("/api/backup/cloud/config", {
            "enabled": True,
            "provider": "s3",
            "retention_count": 6
        })
        self.assertEqual(resp.status_code, 200)
        d = resp.get_json()
        self.assertTrue(d["success"])
        self.assertEqual(d["config"]["retention_count"], 6)

    def test_cloud_test_connection_endpoint(self):
        self._login()
        with patch.object(self.mgr, "test_connection") as mock_test:
            mock_test.return_value = (True, "Mock connection OK")
            resp = self._post("/api/backup/cloud/test", {"provider": "s3"})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.get_json()["success"])

    def test_cloud_list_endpoint(self):
        self._login()
        with patch.object(self.mgr, "list_remote_backups") as mock_list:
            mock_list.return_value = [
                {"filename": "remote_world.tar.gz", "size_mb": 42.0, "mtime": "2026-11-06 14:00:00", "provider": "S3"}
            ]
            resp = self.client.get("/api/backup/cloud/list")
            self.assertEqual(resp.status_code, 200)
            d = resp.get_json()
            self.assertTrue(d["success"])
            self.assertEqual(len(d["backups"]), 1)
            self.assertEqual(d["backups"][0]["filename"], "remote_world.tar.gz")

    def test_local_backup_deletion_endpoint(self):
        self._login()
        # Create a mock backup file in the temp backup dir
        backup_file = os.path.join(self.temp_dir.name, "test_delete_archive.tar.gz")
        with open(backup_file, "w") as f:
            f.write("content")

        with patch("app.get_backup_dir", return_value=self.temp_dir.name):
            # Attempt invalid filename
            resp = self._post("/api/backup/delete", {"filename": "../malicious.txt"})
            self.assertEqual(resp.status_code, 400)

            # Successfully delete valid backup
            resp = self._post("/api/backup/delete", {"filename": "test_delete_archive.tar.gz"})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.get_json()["success"])
            self.assertFalse(os.path.exists(backup_file))

if __name__ == "__main__":
    unittest.main()
