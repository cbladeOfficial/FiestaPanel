import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import json
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as portal_app
from addon_manager import AddonManager, AddonContext

class DiscordNotifierAddonTests(unittest.TestCase):
    def setUp(self):
        portal_app.app.config['TESTING'] = True
        self.client = portal_app.app.test_client()

        # Load discord_notifier module directly
        module_path = ROOT / "addons" / "discord_notifier" / "main.py"
        self.assertTrue(module_path.exists())
        spec = importlib.util.spec_from_file_location("test_discord_notifier", str(module_path))
        self.discord_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.discord_mod)

    def test_init_addon_registers_start_and_stop_hooks(self):
        registered = {}
        ctx = MagicMock()
        def mock_register(event, callback):
            registered[event] = callback
        ctx.register_hook.side_effect = mock_register

        self.discord_mod.init_addon(ctx)
        self.assertIn("server_start", registered)
        self.assertIn("server_stop", registered)
        self.assertIn("server_online", registered)

    def test_server_start_event_delivers_embed_when_enabled(self):
        with patch.object(self.discord_mod, "_send_webhook_payload") as mock_send:
            ctx = MagicMock()
            ctx.get_settings.return_value = {
                "webhook_url": "https://discord.com/api/webhooks/test/123",
                "bot_name": "TestBot",
                "avatar_url": "",
                "notify_start": True,
                "notify_stop": True,
                "embed_color": "#22c55e"
            }
            ctx.get_server_status.return_value = {
                "online": True,
                "version": "Paper 1.21.11",
                "players_max": 100
            }

            # Trigger delivery
            self.discord_mod._deliver_discord_event(ctx, "server_start")

            # Mock send called via daemon thread, wait a tiny bit
            import time
            time.sleep(0.1)

            self.assertTrue(mock_send.called)
            args, kwargs = mock_send.call_args
            url, payload = args
            self.assertEqual(url, "https://discord.com/api/webhooks/test/123")
            self.assertEqual(payload["username"], "TestBot")
            self.assertNotIn("avatar_url", payload) # Empty avatar_url should be omitted
            self.assertEqual(len(payload["embeds"]), 1)
            self.assertIn("Online", payload["embeds"][0]["title"])

    def test_server_stop_event_delivers_embed_when_enabled(self):
        with patch.object(self.discord_mod, "_send_webhook_payload") as mock_send:
            ctx = MagicMock()
            ctx.get_settings.return_value = {
                "webhook_url": "https://discord.com/api/webhooks/test/123",
                "bot_name": "TestBot",
                "avatar_url": "https://example.com/avatar.png",
                "notify_start": True,
                "notify_stop": True
            }

            self.discord_mod._deliver_discord_event(ctx, "server_stop")

            import time
            time.sleep(0.1)

            self.assertTrue(mock_send.called)
            args, kwargs = mock_send.call_args
            url, payload = args
            self.assertEqual(payload["avatar_url"], "https://example.com/avatar.png")
            self.assertIn("Stopped", payload["embeds"][0]["title"])

    def test_notification_skipped_when_disabled_in_settings(self):
        with patch.object(self.discord_mod, "_send_webhook_payload") as mock_send:
            ctx = MagicMock()
            ctx.get_settings.return_value = {
                "webhook_url": "https://discord.com/api/webhooks/test/123",
                "notify_start": False,
                "notify_stop": False
            }

            self.discord_mod._deliver_discord_event(ctx, "server_start")
            self.discord_mod._deliver_discord_event(ctx, "server_stop")

            import time
            time.sleep(0.1)
            self.assertFalse(mock_send.called)

    def test_addon_manager_triggers_registered_hooks(self):
        fired_events = []
        addon_manager = AddonManager(str(ROOT), str(ROOT), None)
        addon_manager.register_hook("discord_notifier", "server_start", lambda **kw: fired_events.append("started"))
        addon_manager.register_hook("discord_notifier", "server_stop", lambda **kw: fired_events.append("stopped"))

        addon_manager.trigger_event("server_start")
        self.assertEqual(fired_events, ["started"])

        addon_manager.trigger_event("server_stop")
        self.assertEqual(fired_events, ["started", "stopped"])

    def test_player_join_and_leave_events_delivered(self):
        with patch.object(self.discord_mod, "_send_webhook_payload") as mock_send:
            ctx = MagicMock()
            ctx.get_settings.return_value = {
                "webhook_url": "https://discord.com/api/webhooks/test/123",
                "bot_name": "TestBot",
                "notify_join": True
            }

            self.discord_mod._deliver_discord_event(ctx, "player_join", {"player": "Steve", "players_online": 1, "max_players": 20})

            import time
            time.sleep(0.1)

            self.assertTrue(mock_send.called)
            args, _ = mock_send.call_args
            _, payload = args
            self.assertIn("Player Joined: Steve", payload["embeds"][0]["title"])
            self.assertIn("Steve", payload["embeds"][0]["description"])
            self.assertIn("avatar/Steve/64.png", payload["embeds"][0]["thumbnail"]["url"])

            mock_send.reset_mock()
            self.discord_mod._deliver_discord_event(ctx, "player_leave", {"player": "Alex", "players_online": 0, "max_players": 20})
            time.sleep(0.1)

            self.assertTrue(mock_send.called)
            args, _ = mock_send.call_args
            _, payload = args
            self.assertIn("Player Left: Alex", payload["embeds"][0]["title"])
            self.assertIn("Alex", payload["embeds"][0]["description"])

    def test_render_addon_tab_prepopulates_inputs(self):
        orig_entry = portal_app.addon_manager.installed_addons.get("discord_notifier")
        if orig_entry:
            orig_copy = dict(orig_entry)
            orig_copy["settings"] = dict(orig_entry.get("settings", {}))
            self.addCleanup(lambda: portal_app.addon_manager.installed_addons.__setitem__("discord_notifier", orig_copy))
        portal_app.addon_manager.installed_addons["discord_notifier"] = {
            "id": "discord_notifier",
            "dir_path": str(ROOT / "addons" / "discord_notifier"),
            "settings": {
                "webhook_url": "https://discord.com/api/webhooks/saved/token",
                "bot_name": "SavedBotName",
                "avatar_url": "https://example.com/bot.png",
                "embed_color": "#123456",
                "notify_start": True,
                "notify_stop": False,
                "notify_join": True
            }
        }
        html = portal_app.addon_manager.render_addon_tab("discord_notifier")
        self.assertIn('value="https://discord.com/api/webhooks/saved/token"', html)
        self.assertIn('value="SavedBotName"', html)
        self.assertIn('value="https://example.com/bot.png"', html)
        self.assertIn('value="#123456"', html)
        self.assertIn('window.__ACTIVE_ADDON_SETTINGS__', html)

    def test_api_settings_get_and_post(self):
        orig_settings = dict(portal_app.addon_manager.get_addon_settings("discord_notifier"))
        self.addCleanup(lambda: portal_app.addon_manager.update_addon_settings("discord_notifier", orig_settings))
        csrf = "test-csrf-token"
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = "admin"
            sess["role"] = "owner"
            sess["permissions"] = ["all"]
            sess["csrf_token"] = csrf
            sess["password_version"] = portal_app.session_password_version(
                portal_app.load_users().get("admin", {}).get("password_hash", "")
            )

        # GET settings
        res = self.client.get("/api/panel-addons/discord_notifier/settings")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("settings", data)

        # POST updated settings
        res_post = self.client.post(
            "/api/panel-addons/discord_notifier/settings",
            json={
                "settings": {
                    "webhook_url": "https://discord.com/api/webhooks/new/token456",
                    "bot_name": "UpdatedBot"
                }
            },
            headers={"X-CSRF-Token": csrf}
        )
        self.assertEqual(res_post.status_code, 200)
        data_post = res_post.get_json()
        self.assertTrue(data_post.get("success"))
        self.assertEqual(data_post.get("settings", {}).get("webhook_url"), "https://discord.com/api/webhooks/new/token456")

        # Verify saved in manager
        saved = portal_app.addon_manager.get_addon_settings("discord_notifier")
        self.assertEqual(saved.get("webhook_url"), "https://discord.com/api/webhooks/new/token456")
        self.assertEqual(saved.get("bot_name"), "UpdatedBot")

    @patch("urllib.request.urlopen")
    def test_on_action_test_ping_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        ctx = MagicMock()
        ctx.get_settings.return_value = {}
        res = self.discord_mod.on_action(ctx, "test_ping", {
            "webhook_url": "https://discord.com/api/webhooks/valid/123",
            "bot_name": "TestBot"
        })
        self.assertTrue(res.get("success"))
        self.assertIn("Test ping sent", res.get("message", ""))

    @patch("urllib.request.urlopen")
    def test_on_action_test_ping_error_handling(self, mock_urlopen):
        import urllib.error
        import io
        err_response = io.BytesIO(b'{"message": "Unknown Webhook", "code": 10015}')
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://discord.com/api/webhooks/invalid", 404, "Not Found", {}, err_response
        )

        ctx = MagicMock()
        ctx.get_settings.return_value = {}
        res = self.discord_mod.on_action(ctx, "test_ping", {
            "webhook_url": "https://discord.com/api/webhooks/invalid/123"
        })
        self.assertFalse(res.get("success"))
        self.assertIn("Unknown Webhook", res.get("error", ""))

    def test_on_action_test_ping_empty_url(self):
        ctx = MagicMock()
        ctx.get_settings.return_value = {"webhook_url": ""}
        res = self.discord_mod.on_action(ctx, "test_ping", {"webhook_url": ""})
        self.assertFalse(res.get("success"))
        self.assertIn("Invalid or empty Webhook URL", res.get("error", ""))

    @patch.object(portal_app.addon_manager, "trigger_event")
    def test_check_and_notify_server_state_transitions(self, mock_trigger):
        # Reset state
        with portal_app._state_notification_lock:
            portal_app._last_known_server_running = False

        # Transition: False -> True (server start)
        portal_app.check_and_notify_server_state(True)
        mock_trigger.assert_any_call("server_start")
        mock_trigger.assert_any_call("server_online")

        mock_trigger.reset_mock()

        # Same state: True -> True (no duplicate trigger)
        portal_app.check_and_notify_server_state(True)
        mock_trigger.assert_not_called()

        # Transition: True -> False (server stop)
        portal_app.check_and_notify_server_state(False)
        mock_trigger.assert_called_once_with("server_stop")

if __name__ == '__main__':
    unittest.main()
