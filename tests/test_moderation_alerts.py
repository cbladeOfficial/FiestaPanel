import unittest
import subprocess
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as portal_app

class ModerationAlertsTests(unittest.TestCase):
    def setUp(self):
        portal_app.app.config['TESTING'] = True
        self.client = portal_app.app.test_client()

    def test_dashboard_template_does_not_open_dialog_on_log_poll(self):
        """Verify that inspectLogsForAlerts never calls showModerationDialog"""
        dashboard_path = ROOT / "templates" / "dashboard.html"
        self.assertTrue(dashboard_path.exists())
        content = dashboard_path.read_text(encoding="utf-8")

        # Find inspectLogsForAlerts function body
        start = content.find("function inspectLogsForAlerts(")
        self.assertNotEqual(start, -1)
        end = content.find("function showModerationDialog(", start)
        self.assertNotEqual(end, -1)
        fn_body = content[start:end]

        # Ensure showModerationDialog is NOT called inside inspectLogsForAlerts
        self.assertNotIn("showModerationDialog(", fn_body, "inspectLogsForAlerts should not trigger modal dialog")
        # Ensure showBannerAlert is used instead
        self.assertIn("showBannerAlert(", fn_body)

    def test_javascript_moderation_parser_via_node(self):
        """Execute node test script to verify rejection vs ban parsing logic"""
        node_script = """
        const assert = require('assert');

        function parseLogEvent(line) {
          if (!line || typeof line !== 'string') return null;
          if (/»|\\]:\\s*(?:\\[Not Secure\\]\\s*)?<[a-zA-Z0-9_]{2,16}>/i.test(line)) return null;

          let m = line.match(/(?:Banned IP address|Banned IP|Player\\s+[a-zA-Z0-9_]+\\s+banned\\s+IP\\s+address)\\s+([0-9]{1,3}(?:\\.[0-9]{1,3}){3}|[0-9a-fA-F:]{3,39})(?:(?::\\s*|\\s+for:\\s*)(.*))?/i);
          if (m) {
            let r = (m[2] || "Banned by administrator").replace(/^[<\\[].*?[>\\]]/, "").replace(/[\\]\\.]+$/, "").trim();
            return { type: "BAN_IP", target: m[1], reason: r || "Banned by administrator", source: "Server Console" };
          }

          m = line.match(/\\]:\\s*Disconnecting\\s+([a-zA-Z0-9_]{2,16})(?:\\s*\\([^)]+\\))?:\\s*(.*)/i);
          if (m) {
            let p = m[1];
            let r = (m[2] || "").replace(/[\\]\\.]+$/, "").trim();
            if (/banned/i.test(r)) return null;
            return { type: "KICK", target: p, reason: r || "Kicked by operator", source: "Server Enforced" };
          }

          m = line.match(/\\]:\\s*([a-zA-Z0-9_]{2,16})(?:\\s*\\([^)]+\\))?\\s+lost connection:\\s*(.*)/i);
          if (m) {
            let p = m[1];
            let r = (m[2] || "").replace(/[\\]\\.]+$/, "").trim();
            if (/banned/i.test(r)) return null;
            if (/kicked/i.test(r)) {
              let reason = r.replace(/^[kK]icked(?:\\s+for)?[:\\s]*/, "").trim() || "Kicked by administrator";
              return { type: "KICK", target: p, reason, source: "Server Enforced" };
            }
            return null;
          }

          m = line.match(/\\]:\\s*([a-zA-Z0-9_]{2,16})\\s+was kicked(?::\\s*|\\s+due to\\s*|\\s+for\\s*)(.*)/i);
          if (m) {
            let r = (m[2] || "Kicked by administrator").replace(/[\\]\\.]+$/, "").trim();
            return { type: "KICK", target: m[1], reason: r, source: "Server Enforced" };
          }

          m = line.match(/(?:Banned(?:\\s+player)?|Player\\s+[a-zA-Z0-9_]+\\s+banned)\\s+([a-zA-Z0-9_]{2,16})(?::\\s*|\\s+for:\\s*)(.*)/i);
          if (m) {
            let r = (m[2] || "Banned by operator").replace(/^[<\\[].*?[>\\]]/, "").replace(/[\\]\\.]+$/, "").trim();
            return { type: "BAN", target: m[1], reason: r || "Banned by operator", source: "Operator / Command" };
          }

          return null;
        }

        // Banned player reconnection rejections MUST return null
        assert.strictEqual(parseLogEvent('[21:59:23] [Server thread/INFO]: Disconnecting akemi_ehe (/152.59.51.125:49895): You are banned from this server.'), null);
        assert.strictEqual(parseLogEvent('[21:59:23] [Server thread/INFO]: akemi_ehe (/152.59.51.125:49895) lost connection: You are banned from this server.'), null);
        assert.strictEqual(parseLogEvent('[16:56:29] [Server thread/INFO]: Disconnecting akemi_ehh (/152.59.51.223:65130): Your IP address is banned from this server.'), null);

        // Explicit ban commands MUST return BAN
        const ban = parseLogEvent('[16:11:26] [Server thread/INFO]: [Essentials] Player Console banned akemi_ehe for: <secondary>You have been banned:');
        assert.strictEqual(ban.type, 'BAN');
        assert.strictEqual(ban.target, 'akemi_ehe');

        const vanBan = parseLogEvent('[Server thread/INFO]: Banned player Steve: Griefing');
        assert.strictEqual(vanBan.type, 'BAN');
        assert.strictEqual(vanBan.target, 'Steve');
        assert.strictEqual(vanBan.reason, 'Griefing');

        console.log("OK");
        """
        proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Node script failed: {proc.stderr}")
        self.assertIn("OK", proc.stdout)

if __name__ == '__main__':
    unittest.main()
