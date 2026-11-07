import urllib.request
import urllib.error
import json
import datetime
import threading
import ssl
import logging

logger = logging.getLogger("fiestapanel.addon.discord_notifier")

def _send_webhook_payload(url, payload):
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "FiestaPanel-Discord/1.2"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "ignore")
            logger.error(f"Discord webhook HTTP {e.code}: {body}")
        except Exception:
            logger.error(f"Discord webhook HTTP {e.code}: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"Failed to deliver Discord webhook payload: {e}")
        return False

def _deliver_discord_event(ctx, event_type, details=None):
    try:
        details = details or {}
        settings = ctx.get_settings()
        url = (settings.get("webhook_url") or "").strip()
        if not url or not url.startswith("http"):
            return

        bot_name = settings.get("bot_name") or "FiestaPanel Gateway"
        avatar_url = (settings.get("avatar_url") or "").strip()
        embed_color_hex = (settings.get("embed_color") or "#38bdf8").lstrip("#")
        try:
            custom_color = int(embed_color_hex, 16)
        except Exception:
            custom_color = 0x38bdf8

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if event_type in ("server_start", "server_online"):
            if not settings.get("notify_start", True):
                return

            status_info = {}
            try:
                if hasattr(ctx, "get_server_status"):
                    status_info = ctx.get_server_status() or {}
            except Exception:
                pass

            version_str = status_info.get("version") or "Minecraft Server"
            max_players = status_info.get("players_max", 20)
            color = custom_color if custom_color != 0x38bdf8 else 0x22c55e

            embed = {
                "title": "[●] Minecraft Server is Online",
                "description": "The Minecraft server is active and online. Players can now connect.",
                "color": color,
                "fields": [
                    {"name": "Status", "value": "Online / Running", "inline": True},
                    {"name": "Engine", "value": str(version_str), "inline": True},
                    {"name": "Capacity", "value": f"0 / {max_players} Players", "inline": True},
                    {"name": "Timestamp", "value": now_str, "inline": False}
                ],
                "footer": {
                    "text": "FiestaPanel Addon System • Server Status Notification"
                }
            }

        elif event_type == "server_stop":
            if not settings.get("notify_stop", True):
                return

            embed = {
                "title": "[■] Minecraft Server has Stopped",
                "description": "The Minecraft server has been shut down. World data has been saved and all player connections have been closed.",
                "color": 0xef4444,
                "fields": [
                    {"name": "Status", "value": "Offline / Stopped", "inline": True},
                    {"name": "Timestamp", "value": now_str, "inline": True}
                ],
                "footer": {
                    "text": "FiestaPanel Addon System • Server Status Notification"
                }
            }

        elif event_type == "player_join":
            if not settings.get("notify_join", True):
                return

            player_name = str(details.get("player") or "Unknown Player").strip()
            online_count = details.get("players_online", 1)
            max_p = details.get("max_players", 20)

            embed = {
                "title": f"[+] Player Joined: {player_name}",
                "description": f"**{player_name}** connected to the server.",
                "color": 0x22c55e,
                "thumbnail": {
                    "url": f"https://mc-heads.net/avatar/{urllib.parse.quote(player_name)}/64.png"
                },
                "fields": [
                    {"name": "Player", "value": player_name, "inline": True},
                    {"name": "Online Players", "value": f"{online_count} / {max_p}", "inline": True},
                    {"name": "Timestamp", "value": now_str, "inline": False}
                ],
                "footer": {
                    "text": "FiestaPanel Addon System • Player Activity"
                }
            }

        elif event_type == "player_leave":
            if not settings.get("notify_join", True):
                return

            player_name = str(details.get("player") or "Unknown Player").strip()
            online_count = details.get("players_online", 0)
            max_p = details.get("max_players", 20)

            embed = {
                "title": f"[-] Player Left: {player_name}",
                "description": f"**{player_name}** disconnected from the server.",
                "color": 0xeab308,
                "thumbnail": {
                    "url": f"https://mc-heads.net/avatar/{urllib.parse.quote(player_name)}/64.png"
                },
                "fields": [
                    {"name": "Player", "value": player_name, "inline": True},
                    {"name": "Online Players", "value": f"{online_count} / {max_p}", "inline": True},
                    {"name": "Timestamp", "value": now_str, "inline": False}
                ],
                "footer": {
                    "text": "FiestaPanel Addon System • Player Activity"
                }
            }
        else:
            return

        payload = {
            "username": bot_name,
            "embeds": [embed]
        }
        if avatar_url and avatar_url.startswith("http"):
            payload["avatar_url"] = avatar_url

        threading.Thread(target=_send_webhook_payload, args=(url, payload), daemon=True).start()
    except Exception as e:
        ctx.logger.error(f"Failed to process Discord notification for {event_type}: {e}")

def init_addon(ctx):
    ctx.logger.info("Discord Webhook Notifier initialized successfully.")

    def on_server_start(**kwargs):
        ctx.logger.info("Discord Webhook: triggering server start notification.")
        _deliver_discord_event(ctx, "server_start", kwargs)

    def on_server_stop(**kwargs):
        ctx.logger.info("Discord Webhook: triggering server stop notification.")
        _deliver_discord_event(ctx, "server_stop", kwargs)

    def on_player_join(**kwargs):
        ctx.logger.info(f"Discord Webhook: triggering player join notification for {kwargs.get('player')}.")
        _deliver_discord_event(ctx, "player_join", kwargs)

    def on_player_leave(**kwargs):
        ctx.logger.info(f"Discord Webhook: triggering player leave notification for {kwargs.get('player')}.")
        _deliver_discord_event(ctx, "player_leave", kwargs)

    ctx.register_hook("server_start", on_server_start)
    ctx.register_hook("server_online", on_server_start)
    ctx.register_hook("server_stop", on_server_stop)
    ctx.register_hook("player_join", on_player_join)
    ctx.register_hook("player_leave", on_player_leave)

def on_action(ctx, action_name, payload):
    if action_name == "test_ping":
        settings = ctx.get_settings()
        url = (payload.get("webhook_url") or settings.get("webhook_url") or "").strip()
        if not url or not url.startswith("http"):
            return {"success": False, "error": "Invalid or empty Webhook URL. Please enter a valid URL."}

        bot_name = (payload.get("bot_name") or settings.get("bot_name") or "FiestaPanel Gateway").strip()
        avatar_url = (payload.get("avatar_url") or settings.get("avatar_url") or "").strip()
        embed_color_hex = (payload.get("embed_color") or settings.get("embed_color") or "#38bdf8").lstrip("#")
        try:
            color_int = int(embed_color_hex, 16)
        except Exception:
            color_int = 0x38bdf8

        embed_data = {
            "username": bot_name,
            "embeds": [
                {
                    "title": "FiestaPanel Webhook Bridge Verified",
                    "description": "Connectivity test successful! Your Minecraft server is linked to this Discord channel.",
                    "color": color_int,
                    "fields": [
                        {"name": "Status", "value": "[●] Online & Operational", "inline": True},
                        {"name": "Timestamp", "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True}
                    ],
                    "footer": {
                        "text": "FiestaPanel Addon System • Webhook Verification"
                    }
                }
            ]
        }
        if avatar_url and avatar_url.startswith("http"):
            embed_data["avatar_url"] = avatar_url

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(embed_data).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "FiestaPanel-Discord/1.2"}
            )
            ssl_ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
                if resp.status in (200, 204):
                    return {"success": True, "message": "Test ping sent to Discord channel successfully!"}
                return {"success": False, "error": f"Discord returned HTTP status {resp.status}"}
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "ignore")
                err_data = json.loads(body)
                msg = err_data.get("message") or body
                return {"success": False, "error": f"Discord error ({e.code}): {msg}"}
            except Exception:
                return {"success": False, "error": f"Discord HTTP status {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"Connection failed: {e.reason}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to deliver payload: {str(e)}"}

    elif action_name in ("server_start", "server_online"):
        _deliver_discord_event(ctx, "server_start", payload)
        return {"success": True, "message": "Server start notification dispatched."}

    elif action_name == "server_stop":
        _deliver_discord_event(ctx, "server_stop", payload)
        return {"success": True, "message": "Server stop notification dispatched."}

    elif action_name == "player_join":
        _deliver_discord_event(ctx, "player_join", payload)
        return {"success": True, "message": "Player join notification dispatched."}

    elif action_name == "player_leave":
        _deliver_discord_event(ctx, "player_leave", payload)
        return {"success": True, "message": "Player leave notification dispatched."}

    return {"success": False, "error": f"Unknown action: {action_name}"}
