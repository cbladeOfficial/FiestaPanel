import unittest
import json
import urllib.parse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as portal_app

class NeoForgeAndModsTests(unittest.TestCase):
    def setUp(self):
        portal_app.app.config['TESTING'] = True
        self.client = portal_app.app.test_client()

    def test_resolve_neoforge_download(self):
        # Test 1.21.11 mapping
        url, filename, label = portal_app.resolve_software_download("neoforge", "1.21.11")
        self.assertIn("maven.neoforged.net", url)
        self.assertTrue(filename.endswith("-installer.jar"))
        self.assertIn("NeoForge", label)
        self.assertIn("1.21.11", label)

    def test_resolve_neoforge_fallback(self):
        url, filename, label = portal_app.resolve_software_download("neoforge", "1.20.4")
        self.assertIn("20.4", url)
        self.assertEqual(filename, "neoforge-20.4.253-installer.jar")
        self.assertIn("NeoForge 1.20.4", label)

    def test_resolve_neoforge_explicit_version(self):
        url, filename, label = portal_app.resolve_software_download("neoforge", "21.1.265")
        self.assertIn("21.1.265", url)
        self.assertEqual(filename, "neoforge-21.1.265-installer.jar")
        self.assertIn("NeoForge", label)

    def test_neoforge_versions_api(self):
        user = portal_app.load_users().get('admin', {})
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = 'admin'
            sess['role'] = 'owner'
            sess['permissions'] = ['all']
            sess['password_version'] = portal_app.session_password_version(user.get('password_hash'))

        res = self.client.get('/api/software/versions?software=neoforge')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('software'), 'neoforge')
        versions = data.get('versions', [])
        self.assertGreater(len(versions), 0)
        # Check standard versions are in the list
        self.assertTrue(any('1.21' in v for v in versions))

    def test_software_latest_neoforge(self):
        user = portal_app.load_users().get('admin', {})
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = 'admin'
            sess['role'] = 'owner'
            sess['permissions'] = ['all']
            sess['password_version'] = portal_app.session_password_version(user.get('password_hash'))

        res = self.client.get('/api/software/latest?software=neoforge')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('software'), 'neoforge')
        self.assertIn('latest_version', data)
        self.assertIn('NeoForge', data.get('display_label', ''))

    def test_mods_search_with_neoforge_loader(self):
        user = portal_app.load_users().get('admin', {})
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = 'admin'
            sess['role'] = 'owner'
            sess['permissions'] = ['all']
            sess['password_version'] = portal_app.session_password_version(user.get('password_hash'))

        res = self.client.get('/api/mods/search?q=jei&loader=neoforge')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('loader'), 'neoforge')
        hits = data.get('hits', [])
        self.assertGreater(len(hits), 0)
        first_hit = hits[0]
        self.assertIn('loaders', first_hit)
        self.assertIn('compatible_neoforge', first_hit)
        self.assertTrue(first_hit.get('compatible_neoforge'))

if __name__ == '__main__':
    unittest.main()
