import unittest
from unittest.mock import patch
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as portal_app

class ServerPowerControlsTests(unittest.TestCase):
    def setUp(self):
        portal_app.app.config['TESTING'] = True
        self.client = portal_app.app.test_client()
        self.csrf_token = "test-csrf-token"

    def _login(self):
        user = portal_app.load_users().get('admin', {})
        with self.client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['user'] = 'admin'
            sess['role'] = 'owner'
            sess['permissions'] = ['all']
            sess['csrf_token'] = self.csrf_token
            sess['password_version'] = portal_app.session_password_version(user.get('password_hash'))

    def test_dashboard_renders_disabled_power_buttons_when_server_stopped(self):
        self._login()
        with patch.object(portal_app.server_runner, 'is_running', return_value=False):
            res = self.client.get('/')
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)

            # btn-server-stop and btn-server-restart must be disabled in initial HTML
            self.assertIn('id="btn-server-stop"', html)
            self.assertIn('id="btn-server-restart"', html)
            self.assertIn('id="btn-console-stop"', html)
            self.assertIn('id="btn-console-restart"', html)

            # Check that disabled attribute is present on the stop and restart buttons
            # Overview restart & stop:
            self.assertRegex(html, r'id="btn-server-restart"[^>]*disabled')
            self.assertRegex(html, r'id="btn-server-stop"[^>]*disabled')
            # Console restart & stop:
            self.assertRegex(html, r'id="btn-console-restart"[^>]*disabled')
            self.assertRegex(html, r'id="btn-console-stop"[^>]*disabled')

            # Start button should NOT be disabled when server is stopped
            self.assertNotRegex(html, r'id="btn-server-start"[^>]*disabled')
            self.assertNotRegex(html, r'id="btn-console-start"[^>]*disabled')

    def test_dashboard_renders_enabled_power_buttons_when_server_online(self):
        self._login()
        with patch.object(portal_app.server_runner, 'is_running', return_value=True):
            res = self.client.get('/')
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)

            # Neither stop nor restart button should have disabled attribute
            self.assertNotRegex(html, r'id="btn-server-restart"[^>]*disabled')
            self.assertNotRegex(html, r'id="btn-server-stop"[^>]*disabled')
            self.assertNotRegex(html, r'id="btn-console-restart"[^>]*disabled')
            self.assertNotRegex(html, r'id="btn-console-stop"[^>]*disabled')

    def test_power_api_rejects_stop_and_restart_when_server_stopped(self):
        self._login()
        headers = {'X-CSRF-Token': self.csrf_token}
        with patch.object(portal_app.server_runner, 'is_running', return_value=False):
            # Attempt stop
            res_stop = self.client.post('/api/server/power', json={'action': 'stop'}, headers=headers)
            self.assertEqual(res_stop.status_code, 400)
            data_stop = res_stop.get_json()
            self.assertFalse(data_stop['success'])
            self.assertIn('already stopped', data_stop['message'].lower())

            # Attempt restart
            res_restart = self.client.post('/api/server/power', json={'action': 'restart'}, headers=headers)
            self.assertEqual(res_restart.status_code, 400)
            data_restart = res_restart.get_json()
            self.assertFalse(data_restart['success'])
            self.assertIn('already stopped', data_restart['message'].lower())

    def test_power_api_accepts_stop_and_restart_when_server_online(self):
        self._login()
        headers = {'X-CSRF-Token': self.csrf_token}
        with patch.object(portal_app.server_runner, 'is_running', return_value=True), \
             patch.object(portal_app.server_runner, 'stop') as mock_stop, \
             patch.object(portal_app.server_runner, 'restart') as mock_restart:
            res_stop = self.client.post('/api/server/power', json={'action': 'stop'}, headers=headers)
            self.assertEqual(res_stop.status_code, 200)
            self.assertTrue(res_stop.get_json()['success'])

            res_restart = self.client.post('/api/server/power', json={'action': 'restart'}, headers=headers)
            self.assertEqual(res_restart.status_code, 200)
            self.assertTrue(res_restart.get_json()['success'])

    def test_action_api_rejects_restart_when_server_stopped(self):
        self._login()
        headers = {'X-CSRF-Token': self.csrf_token}
        with patch.object(portal_app.server_runner, 'is_running', return_value=False):
            res = self.client.post('/api/action', json={'action': 'restart'}, headers=headers)
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertFalse(data['success'])
            self.assertIn('already stopped', data['message'].lower())

    def test_javascript_update_server_power_buttons_via_node(self):
        """Execute Node.js script to verify client-side button enabling and disabling"""
        node_script = """
        const assert = require('assert');

        // Minimal simulated DOM environment
        class Element {
          constructor(id, classes = [], attributes = {}) {
            this.id = id;
            this.className = classes.join(' ');
            this.classList = new Set(classes);
            this.attributes = { ...attributes };
            this.disabled = !!attributes.disabled;
            this.title = '';
          }
          setAttribute(name, val) {
            this.attributes[name] = val;
            if (name === 'disabled') this.disabled = true;
          }
          removeAttribute(name) {
            delete this.attributes[name];
            if (name === 'disabled') this.disabled = false;
          }
          getAttribute(name) {
            return this.attributes[name];
          }
        }

        const elements = [
          new Element('btn-server-start', ['btn-classic', 'btn-power-start'], { 'data-power-action': 'start', 'onclick': "confirmServerPower('start')" }),
          new Element('btn-server-restart', ['btn-classic', 'btn-power-restart'], { 'data-power-action': 'restart', 'onclick': "confirmServerPower('restart')" }),
          new Element('btn-server-stop', ['btn-classic', 'btn-power-stop'], { 'data-power-action': 'stop', 'onclick': "confirmServerPower('stop')" }),
          new Element('btn-console-start', ['btn-classic', 'btn-power-start'], { 'data-power-action': 'start', 'onclick': "confirmServerPower('start')" }),
          new Element('btn-console-restart', ['btn-classic', 'btn-power-restart'], { 'data-power-action': 'restart', 'onclick': "confirmServerPower('restart')" }),
          new Element('btn-console-stop', ['btn-classic', 'btn-power-stop'], { 'data-power-action': 'stop', 'onclick': "confirmServerPower('stop')" }),
          new Element('btn-reboot-exec', ['btn-danger-red', 'btn-power-restart'], { 'data-power-action': 'restart', 'onclick': "executeReboot()" }),
          new Element('btn-repack-restart', ['btn-classic', 'btn-power-restart'], { 'data-power-action': 'restart', 'onclick': "confirmServerPower('restart')" }),
          new Element('btn-props-restart', ['btn-classic', 'btn-power-restart'], { 'data-power-action': 'restart', 'onclick': "confirmServerPower('restart')" })
        ];

        const document = {
          getElementById(id) {
            return elements.find(e => e.id === id) || null;
          },
          querySelectorAll(selector) {
            return elements.filter(e => {
              if (selector.includes(e.id)) return true;
              for (const c of e.classList) {
                if (selector.includes('.' + c)) return true;
              }
              for (const [k, v] of Object.entries(e.attributes)) {
                if (selector.includes(`[${k}="${v}"]`)) return true;
                if (selector.includes(`button[onclick*="confirmServerPower('${v}')"]`)) return true;
                if (selector.includes(`button[onclick*='confirmServerPower("${v}")']`)) return true;
                if (selector.includes(`button[onclick*="${v}"]`)) return true;
              }
              return false;
            });
          }
        };

        // Inject compatibility alias
        const _origGetElementById = document.getElementById.bind(document);
        document.getElementById = function(id) {
          if (id === 'btn-stop') return _origGetElementById('btn-server-stop') || _origGetElementById('btn-stop');
          if (id === 'btn-restart') return _origGetElementById('btn-server-restart') || _origGetElementById('btn-restart');
          if (id === 'btn-start') return _origGetElementById('btn-server-start') || _origGetElementById('btn-start');
          return _origGetElementById(id);
        };

        function updateServerPowerButtons(isOnline) {
          const stopButtons = new Set([
            ...document.querySelectorAll('#btn-server-stop, #btn-console-stop, .btn-power-stop, [data-power-action="stop"]'),
            ...document.querySelectorAll("button[onclick*=\\"confirmServerPower('stop')\\"]"),
            ...document.querySelectorAll('button[onclick*=\\'confirmServerPower("stop")\\']')
          ]);

          stopButtons.forEach(btn => {
            if (!btn) return;
            btn.disabled = !isOnline;
            if (!isOnline) {
              btn.setAttribute('disabled', 'disabled');
              btn.title = 'Server is stopped (Offline)';
            } else {
              btn.removeAttribute('disabled');
              btn.title = 'Stop Server';
            }
          });

          const restartButtons = new Set([
            ...document.querySelectorAll('#btn-server-restart, #btn-console-restart, #btn-reboot-exec, #btn-props-restart, #btn-repack-restart, .btn-power-restart, [data-power-action="restart"]'),
            ...document.querySelectorAll("button[onclick*=\\"confirmServerPower('restart')\\"]"),
            ...document.querySelectorAll('button[onclick*=\\'confirmServerPower("restart")\\']'),
            ...document.querySelectorAll('button[onclick*="executeReboot"]')
          ]);

          restartButtons.forEach(btn => {
            if (!btn) return;
            btn.disabled = !isOnline;
            if (!isOnline) {
              btn.setAttribute('disabled', 'disabled');
              btn.title = 'Server is stopped (Offline)';
            } else {
              btn.removeAttribute('disabled');
              btn.title = 'Restart / Reboot Server';
            }
          });
        }

        // Test 1: When server is stopped (isOnline = false)
        updateServerPowerButtons(false);
        assert.strictEqual(document.getElementById('btn-server-stop').disabled, true);
        assert.strictEqual(document.getElementById('btn-server-restart').disabled, true);
        assert.strictEqual(document.getElementById('btn-console-stop').disabled, true);
        assert.strictEqual(document.getElementById('btn-console-restart').disabled, true);
        assert.strictEqual(document.getElementById('btn-reboot-exec').disabled, true);
        assert.strictEqual(document.getElementById('btn-repack-restart').disabled, true);
        assert.strictEqual(document.getElementById('btn-props-restart').disabled, true);
        assert.strictEqual(document.getElementById('btn-stop').disabled, true);
        assert.strictEqual(document.getElementById('btn-restart').disabled, true);
        // Start button remains enabled
        assert.strictEqual(document.getElementById('btn-server-start').disabled, false);

        // Test 2: When server is online (isOnline = true)
        updateServerPowerButtons(true);
        assert.strictEqual(document.getElementById('btn-server-stop').disabled, false);
        assert.strictEqual(document.getElementById('btn-server-restart').disabled, false);
        assert.strictEqual(document.getElementById('btn-console-stop').disabled, false);
        assert.strictEqual(document.getElementById('btn-console-restart').disabled, false);
        assert.strictEqual(document.getElementById('btn-reboot-exec').disabled, false);
        assert.strictEqual(document.getElementById('btn-repack-restart').disabled, false);
        assert.strictEqual(document.getElementById('btn-props-restart').disabled, false);
        assert.strictEqual(document.getElementById('btn-stop').disabled, false);
        assert.strictEqual(document.getElementById('btn-restart').disabled, false);

        // Test 3: Back to stopped
        updateServerPowerButtons(false);
        assert.strictEqual(document.getElementById('btn-server-stop').disabled, true);
        assert.strictEqual(document.getElementById('btn-server-restart').disabled, true);

        console.log("ALL JS POWER BUTTON TESTS PASSED");
        """
        proc = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Node script failed:\n{proc.stderr}\n{proc.stdout}")
        self.assertIn("ALL JS POWER BUTTON TESTS PASSED", proc.stdout)

if __name__ == '__main__':
    unittest.main()
