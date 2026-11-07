import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import json
import tempfile
import os
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as portal_app

class AternosFeaturesTests(unittest.TestCase):
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

        # Set up a sandbox SERVER_DIR inside temp_dir
        self.sandbox_server = os.path.join(self.temp_dir.name, "mc_server")
        os.makedirs(self.sandbox_server, exist_ok=True)
        portal_app.SERVER_DIR = self.sandbox_server
        portal_app.server_runner.server_dir = self.sandbox_server

        # Minimal server.properties
        self.props_path = os.path.join(self.sandbox_server, "server.properties")
        with open(self.props_path, "w", encoding="utf-8") as f:
            f.write("motd=A Minecraft Server\\nlevel-name=world\\n")

        # Mock runtime config
        self.runtime_json = os.path.join(self.sandbox_server, "server_runtime.json")
        with open(self.runtime_json, "w", encoding="utf-8") as f:
            json.dump({"jar_file": "server.jar", "jvm_flags": []}, f)

        self.patch_running = patch.object(portal_app.server_runner, 'is_running', return_value=False)
        self.patch_running.start()

        self._login()

    def tearDown(self):
        self.patch_running.stop()
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

    # ── File Manager: Rename, Copy, Batch Delete, Archive, Extract, Download ──

    def test_file_rename_and_traversal_protection(self):
        # Create test file
        test_file = os.path.join(self.sandbox_server, "source_note.txt")
        with open(test_file, "w") as f:
            f.write("hello world")

        # Valid rename
        res = self._post("/api/files/rename", {"old_path": "source_note.txt", "new_name": "renamed_note.txt"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertFalse(os.path.exists(test_file))
        self.assertTrue(os.path.exists(os.path.join(self.sandbox_server, "renamed_note.txt")))

        # Path traversal attack attempt
        res_hack = self._post("/api/files/rename", {"old_path": "renamed_note.txt", "new_name": "../escape.txt"})
        self.assertEqual(res_hack.status_code, 400)
        self.assertFalse(res_hack.get_json()["success"])

    def test_file_copy(self):
        source = os.path.join(self.sandbox_server, "original.yml")
        with open(source, "w") as f:
            f.write("settings: test\n")

        res = self._post("/api/files/copy", {"source_path": "original.yml", "target_name": "original_copy.yml"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        self.assertTrue(os.path.exists(source))
        self.assertTrue(os.path.exists(os.path.join(self.sandbox_server, "original_copy.yml")))

    def test_batch_delete(self):
        f1 = os.path.join(self.sandbox_server, "file_a.log")
        f2 = os.path.join(self.sandbox_server, "file_b.log")
        f3 = os.path.join(self.sandbox_server, "keep_me.txt")
        for p in (f1, f2, f3):
            with open(p, "w") as f: f.write("data")

        res = self._post("/api/files/batch-delete", {"paths": ["file_a.log", "file_b.log"]})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])
        self.assertFalse(os.path.exists(f1))
        self.assertFalse(os.path.exists(f2))
        self.assertTrue(os.path.exists(f3))

    def test_archive_and_extract(self):
        sub = os.path.join(self.sandbox_server, "my_folder")
        os.makedirs(sub, exist_ok=True)
        item1 = os.path.join(sub, "item1.txt")
        item2 = os.path.join(sub, "item2.txt")
        with open(item1, "w") as f: f.write("first item")
        with open(item2, "w") as f: f.write("second item")

        # Archive items
        res_arch = self._post("/api/files/archive", {
            "paths": ["my_folder/item1.txt", "my_folder/item2.txt"],
            "archive_name": "bundle.zip",
            "destination_dir": ""
        })
        self.assertEqual(res_arch.status_code, 200)
        self.assertTrue(res_arch.get_json()["success"])
        archive_path = os.path.join(self.sandbox_server, "bundle.zip")
        self.assertTrue(os.path.exists(archive_path))

        # Extract archive
        res_extr = self._post("/api/files/extract", {
            "archive_path": "bundle.zip",
            "destination_dir": "unpacked"
        })
        self.assertEqual(res_extr.status_code, 200)
        self.assertTrue(res_extr.get_json()["success"])
        self.assertTrue(os.path.exists(os.path.join(self.sandbox_server, "unpacked", "my_folder", "item1.txt")))

    def test_download_directory_zip(self):
        dir_path = os.path.join(self.sandbox_server, "stream_dir")
        os.makedirs(dir_path, exist_ok=True)
        with open(os.path.join(dir_path, "subfile.txt"), "w") as f:
            f.write("content")

        res = self.client.get("/api/files/download_dir?path=stream_dir")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/zip")
        self.assertIn("stream_dir.zip", res.headers.get("Content-Disposition", ""))

    # ── MOTD Editor: GET, POST, & Formatting ──

    def test_motd_get_and_post(self):
        # Initial GET
        res_get = self.client.get("/api/motd")
        self.assertEqual(res_get.status_code, 200)
        d_get = res_get.get_json()
        self.assertTrue(d_get["success"])
        self.assertEqual(d_get["line1"], "A Minecraft Server")

        # Update MOTD with color codes
        res_post = self._post("/api/motd", {
            "line1": "&6Fiesta &bSMP",
            "line2": "&aOnline &e24/7"
        })
        self.assertEqual(res_post.status_code, 200)
        d_post = res_post.get_json()
        self.assertTrue(d_post["success"])
        self.assertIn("span", d_post["line1_html"])
        self.assertIn("span", d_post["line2_html"])

        # Check server.properties content
        with open(self.props_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Fiesta", content)
        self.assertIn("SMP", content)

    # ── Software Engines & Java Advisories ──

    def test_software_versions_and_java_advisories(self):
        res = self.client.get("/api/software/versions?software=paper")
        self.assertEqual(res.status_code, 200)
        d = res.get_json()
        self.assertTrue(d["success"])
        self.assertIsInstance(d["versions"], list)
        self.assertIsInstance(d["java_advisories"], dict)
        self.assertIn("1.21.4", d["java_advisories"])
        self.assertEqual(d["java_advisories"]["1.21.4"], "Java 21+")

        # Bedrock software
        res_bedrock = self.client.get("/api/software/versions?software=bedrock")
        self.assertEqual(res_bedrock.status_code, 200)
        d_b = res_bedrock.get_json()
        self.assertTrue(d_b["success"])
        self.assertIn("1.21.51.02", d_b["versions"])

    def test_software_download_resolution(self):
        url_forge, fn_forge, _ = portal_app.resolve_software_download("forge", "1.20.4", "latest")
        self.assertIn("minecraftforge", url_forge)
        self.assertTrue(fn_forge.endswith(".jar"))

        url_quilt, fn_quilt, _ = portal_app.resolve_software_download("quilt", "1.21.1", "latest")
        self.assertIn("quiltmc", url_quilt)

        url_velocity, fn_vel, _ = portal_app.resolve_software_download("velocity", "3.3.0", "latest")
        self.assertIn("papermc", url_velocity)

        url_bedrock, fn_bds, _ = portal_app.resolve_software_download("bedrock", "1.21.0.03", "latest")
        self.assertIn("minecraft.net", url_bedrock)
        self.assertTrue(fn_bds.endswith(".zip"))

    # ── Worlds Management Hub ──

    def test_worlds_list_set_active_and_optimize(self):
        # Create mock world directory
        world_dir = os.path.join(self.sandbox_server, "custom_survival")
        os.makedirs(os.path.join(world_dir, "region"), exist_ok=True)
        with open(os.path.join(world_dir, "level.dat"), "wb") as f:
            f.write(b"MOCK_NBT")
        with open(os.path.join(world_dir, "region", "r.0.0.mca"), "wb") as f:
            f.write(b"MOCK_REGION")

        # GET /api/worlds
        res_list = self.client.get("/api/worlds")
        self.assertEqual(res_list.status_code, 200)
        d_list = res_list.get_json()
        self.assertTrue(d_list["success"])
        world_names = [w["name"] for w in d_list["worlds"]]
        self.assertIn("custom_survival", world_names)

        # POST /api/worlds/set-active
        res_act = self._post("/api/worlds/set-active", {"world": "custom_survival"})
        self.assertEqual(res_act.status_code, 200)
        self.assertTrue(res_act.get_json()["success"])

        # Check server.properties
        with open(self.props_path, "r", encoding="utf-8") as f:
            props = f.read()
        self.assertIn("level-name=custom_survival", props)

        # POST /api/worlds/optimize
        lock_file = os.path.join(world_dir, "session.lock")
        with open(lock_file, "w") as f: f.write("lock")
        res_opt = self._post("/api/worlds/optimize", {"world": "custom_survival", "mode": "both"})
        self.assertEqual(res_opt.status_code, 200)
        self.assertTrue(res_opt.get_json()["success"])
        self.assertFalse(os.path.exists(lock_file))

    def test_per_world_datapacks(self):
        world_name = "test_dimension"
        dp_dir = os.path.join(self.sandbox_server, world_name, "datapacks")
        os.makedirs(dp_dir, exist_ok=True)

        # Create a mock zip datapack
        zip_path = os.path.join(dp_dir, "timber.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("pack.mcmeta", json.dumps({"pack": {"pack_format": 15, "description": "Timber Datapack"}}))

        res_dp = self.client.get(f"/api/worlds/datapacks?world={world_name}")
        self.assertEqual(res_dp.status_code, 200)
        d_dp = res_dp.get_json()
        self.assertTrue(d_dp["success"])
        self.assertEqual(len(d_dp["datapacks"]), 1)
        self.assertEqual(d_dp["datapacks"][0]["name"], "timber.zip")
        self.assertEqual(d_dp["datapacks"][0]["description"], "Timber Datapack")

    # ── Modrinth Version Explorer & Modpacks ──

    def test_modrinth_versions_endpoint_validation(self):
        res = self.client.get("/api/modrinth/versions")
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

        # Project ID format validation
        res_invalid = self.client.get("/api/modrinth/versions?project_id=../illegal!")
        self.assertEqual(res_invalid.status_code, 400)

    def test_modpacks_endpoints_validation(self):
        # Empty search
        res_s = self.client.get("/api/modpacks/search?limit=abc")
        self.assertEqual(res_s.status_code, 200)

        # Versions validation
        res_empty = self.client.get("/api/modpacks/versions")
        self.assertEqual(res_empty.status_code, 400)

        res_inv = self.client.get("/api/modpacks/versions?project_id=../illegal!")
        self.assertEqual(res_inv.status_code, 400)

    def test_game_options_switchboard_get_and_post(self):
        # Initial GET options
        res_get = self.client.get("/api/options")
        self.assertEqual(res_get.status_code, 200)
        d_get = res_get.get_json()
        self.assertTrue(d_get["success"])
        self.assertIn("options", d_get)

        # POST updates to options
        res_post = self._post("/api/options", {
            "pvp": "false",
            "online-mode": "false",
            "max-players": "50",
            "gamemode": "creative"
        })
        self.assertEqual(res_post.status_code, 200)
        self.assertTrue(res_post.get_json()["success"])

        # Verify options were written to server.properties
        with open(self.props_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("pvp=false", content)
        self.assertIn("online-mode=false", content)
        self.assertIn("max-players=50", content)
        self.assertIn("gamemode=creative", content)

    def test_motd_preview_formatter(self):
        lines = portal_app.format_motd_preview("&aGreen &bBlue\n&cRed &lBold")
        self.assertEqual(len(lines), 2)
        self.assertIn("#55FF55", lines[0])
        self.assertIn("#55FFFF", lines[0])
        self.assertIn("#FF5555", lines[1])
        self.assertIn("font-weight:bold", lines[1])

    def test_clean_jar_name_resolution(self):
        # Existing clean jar name
        name1 = portal_app.resolve_clean_jar_name("LuckPerms-5.4.102.jar", "https://example.com/download")
        self.assertEqual(name1, "LuckPerms-5.4.102.jar")

        # Fallback to URL path
        name2 = portal_app.resolve_clean_jar_name("", "https://cdn.spiget.org/file/spiget-resources/373.jar")
        self.assertEqual(name2, "373.jar")

        # Generic base with special characters sanitized
        name3 = portal_app.resolve_clean_jar_name("HyperEdit (Bukkit) #1", "https://example.com/download")
        self.assertEqual(name3, "HyperEdit (Bukkit) _1.jar")

    def test_get_cf_download_url(self):
        # File with direct downloadUrl
        f1 = {"id": 123456, "fileName": "test.jar", "downloadUrl": "https://edge.forgecdn.net/files/123/456/test.jar"}
        self.assertEqual(portal_app.get_cf_download_url(f1), "https://edge.forgecdn.net/files/123/456/test.jar")

        # File without downloadUrl computes from file ID
        f2 = {"id": 7471535, "fileName": "Deepcore (v1.2).jar"}
        dl2 = portal_app.get_cf_download_url(f2)
        self.assertEqual(dl2, "https://edge.forgecdn.net/files/7471/535/Deepcore%20%28v1.2%29.jar")

    def test_search_plugins_multisource_mocked(self):
        with patch.object(portal_app, "search_spigot", return_value=[{"project_id": "1", "title": "SpigotPlugin", "source": "spigotmc"}]):
            res = self.client.get("/api/plugins/search?q=test&source=spigotmc")
            self.assertEqual(res.status_code, 200)
            d = res.get_json()
            self.assertTrue(d["success"])
            self.assertEqual(d["source"], "spigotmc")
            self.assertEqual(d["hits"][0]["title"], "SpigotPlugin")

        with patch.object(portal_app, "search_bukkitdev", return_value=[{"project_id": "2", "title": "BukkitPlugin", "source": "bukkitdev"}]):
            res = self.client.get("/api/plugins/search?q=test&source=bukkitdev")
            self.assertEqual(res.status_code, 200)
            d = res.get_json()
            self.assertTrue(d["success"])
            self.assertEqual(d["source"], "bukkitdev")
            self.assertEqual(d["hits"][0]["title"], "BukkitPlugin")

        with patch.object(portal_app, "search_curseforge", return_value=[{"project_id": "3", "title": "CFPlugin", "source": "curseforge"}]):
            res = self.client.get("/api/plugins/search?q=test&source=curseforge")
            self.assertEqual(res.status_code, 200)
            d = res.get_json()
            self.assertTrue(d["success"])
            self.assertEqual(d["source"], "curseforge")
            self.assertEqual(d["hits"][0]["title"], "CFPlugin")

    def test_search_mods_multisource_mocked(self):
        with patch.object(portal_app, "search_curseforge", return_value=[{"project_id": "4", "title": "CFMod", "source": "curseforge", "compatible_neoforge": True}]):
            res = self.client.get("/api/mods/search?q=jei&source=curseforge&loader=neoforge")
            self.assertEqual(res.status_code, 200)
            d = res.get_json()
            self.assertTrue(d["success"])
            self.assertEqual(d["source"], "curseforge")
            self.assertEqual(d["hits"][0]["compatible_neoforge"], True)

    def test_multisource_versions_mocked(self):
        # Spigot versions
        mock_spigot_v = [{"id": 100, "name": "v1.2", "releaseDate": 1700000000, "downloads": 50}]
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_spigot_v).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            res = self.client.get("/api/modrinth/versions?project_id=373&source=spigotmc")
            self.assertEqual(res.status_code, 200)
            d = res.get_json()
            self.assertTrue(d["success"])
            self.assertEqual(len(d["versions"]), 1)
            self.assertEqual(d["versions"][0]["version_number"], "v1.2")

        # Curseforge files/versions
        mock_cf_files = {"data": [{"id": 555, "displayName": "CF Mod v2.0", "fileName": "cfmod-2.0.jar", "downloadUrl": "https://example.com/cf.jar", "releaseType": 1, "gameVersions": ["1.21.1", "NeoForge"], "fileDate": "2026-01-01"}]}
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_cf_files).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            res = self.client.get("/api/modrinth/versions?project_id=12345&source=curseforge")
            self.assertEqual(res.status_code, 200)
            d = res.get_json()
            self.assertTrue(d["success"])
            self.assertEqual(len(d["versions"]), 1)
            self.assertEqual(d["versions"][0]["files"][0]["url"], "https://example.com/cf.jar")

if __name__ == "__main__":
    unittest.main()
