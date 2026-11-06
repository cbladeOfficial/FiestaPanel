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
