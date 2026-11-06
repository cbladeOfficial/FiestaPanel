import unittest
from unittest.mock import patch
from pathlib import Path
import sys
import json
import tempfile
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as portal_app

class AddonReviewsTests(unittest.TestCase):
    def setUp(self):
        portal_app.app.config['TESTING'] = True
        self.client = portal_app.app.test_client()
        self.csrf_token = "test-csrf-token"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.temp_reviews_file = os.path.join(self.temp_dir.name, "addon_reviews.json")
        with open(self.temp_reviews_file, "w", encoding="utf-8") as f:
            json.dump({}, f)

        self.orig_reviews_file = portal_app.addon_manager.reviews_file
        self.orig_reviews = portal_app.addon_manager.reviews.copy()
        portal_app.addon_manager.reviews_file = self.temp_reviews_file
        portal_app.addon_manager.reviews = {}

        self.mock_users = {
            "admin": {
                "username": "admin",
                "role": "owner",
                "permissions": ["all"],
                "password_hash": "scrypt:dummy",
                "status": "active"
            },
            "developer1": {
                "username": "developer1",
                "role": "helper",
                "permissions": ["chat"],
                "password_hash": "scrypt:dummy",
                "status": "active"
            },
            "another_user": {
                "username": "another_user",
                "role": "helper",
                "permissions": ["chat"],
                "password_hash": "scrypt:dummy",
                "status": "active"
            },
            "spammer": {
                "username": "spammer",
                "role": "helper",
                "permissions": ["chat"],
                "password_hash": "scrypt:dummy",
                "status": "active"
            }
        }
        self.patch_users = patch.object(portal_app, 'load_users', return_value=self.mock_users)
        self.patch_pwd_ver = patch.object(portal_app, 'session_password_version', return_value="v1")
        self.patch_users.start()
        self.patch_pwd_ver.start()

    def tearDown(self):
        self.patch_users.stop()
        self.patch_pwd_ver.stop()
        portal_app.addon_manager.reviews_file = self.orig_reviews_file
        portal_app.addon_manager.reviews = self.orig_reviews

    def _login(self, username="admin", role="owner", permissions=None):
        if permissions is None:
            permissions = ["all"]
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = username
            sess['role'] = role
            sess['permissions'] = permissions
            sess['csrf_token'] = self.csrf_token
            sess['password_version'] = "v1"

    def _post(self, url, data=None):
        headers = {"X-CSRF-Token": self.csrf_token}
        if data is not None:
            headers["Content-Type"] = "application/json"
            return self.client.post(url, data=json.dumps(data), headers=headers)
        return self.client.post(url, headers=headers)

    def _delete(self, url):
        return self.client.delete(url, headers={"X-CSRF-Token": self.csrf_token})

    def test_submit_and_delete_own_review(self):
        self._login(username="developer1", role="helper", permissions=["chat"])

        # 1. Submit review
        payload = {
            "rating": 5,
            "comment": "Awesome extension, works perfectly!"
        }
        res = self._post('/api/panel-addons/discord_notifier/review', payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        rev = data.get("review")
        self.assertIsNotNone(rev)
        self.assertEqual(rev.get("reviewer"), "developer1")
        self.assertEqual(rev.get("rating"), 5)
        review_id = rev.get("id")
        self.assertTrue(bool(review_id))

        # Check in memory and disk
        self.assertEqual(len(portal_app.addon_manager.get_addon_reviews("discord_notifier")), 1)

        # 2. Author deletes their own review
        res_del = self._delete(f'/api/panel-addons/discord_notifier/review/{review_id}')
        self.assertEqual(res_del.status_code, 200)
        del_data = res_del.get_json()
        self.assertTrue(del_data.get("success"))
        self.assertEqual(len(portal_app.addon_manager.get_addon_reviews("discord_notifier")), 0)

    def test_non_author_forbidden_from_deleting(self):
        # Admin creates review
        self._login(username="admin", role="owner", permissions=["all"])
        res = self._post('/api/panel-addons/discord_notifier/review', {
            "rating": 4,
            "comment": "Solid integration."
        })
        self.assertEqual(res.status_code, 200)
        review_id = res.get_json()["review"]["id"]

        # Different user logs in (non-admin)
        self._login(username="another_user", role="helper", permissions=["chat"])
        res_del = self._delete(f'/api/panel-addons/discord_notifier/review/{review_id}')
        self.assertEqual(res_del.status_code, 403)
        self.assertFalse(res_del.get_json().get("success"))
        self.assertIn("Permission denied", res_del.get_json().get("error", ""))

        # Review still exists
        self.assertEqual(len(portal_app.addon_manager.get_addon_reviews("discord_notifier")), 1)

    def test_owner_can_moderate_any_review(self):
        # Normal user creates review
        self._login(username="spammer", role="helper", permissions=["chat"])
        res = self._post('/api/panel-addons/discord_notifier/review', {
            "rating": 1,
            "comment": "Inappropriate comment."
        })
        self.assertEqual(res.status_code, 200)
        review_id = res.get_json()["review"]["id"]

        # Owner logs in and moderates/deletes the review
        self._login(username="admin", role="owner", permissions=["all"])
        res_del = self._delete(f'/api/panel-addons/discord_notifier/review/{review_id}')
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json().get("success"))
        self.assertEqual(len(portal_app.addon_manager.get_addon_reviews("discord_notifier")), 0)

    def test_delete_nonexistent_review_returns_404(self):
        self._login(username="admin", role="owner", permissions=["all"])
        res_del = self._delete('/api/panel-addons/discord_notifier/review/rev_nonexistent_999')
        self.assertEqual(res_del.status_code, 404)
        self.assertFalse(res_del.get_json().get("success"))


if __name__ == '__main__':
    unittest.main()
