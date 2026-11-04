import urllib.request
import json
import datetime

def init_addon(ctx):
    ctx.logger.info("Discord Webhook Notifier initialized successfully.")

def on_action(ctx, action_name, payload):
    if action_name == "test_ping":
        settings = ctx.get_settings()
        url = payload.get("webhook_url") or settings.get("webhook_url")
        if not url or not url.startswith("http"):
            return {"success": False, "error": "Invalid or empty Webhook URL."}
        
        bot_name = payload.get("bot_name") or settings.get("bot_name", "FiestaPanel Gateway")
        avatar_url = payload.get("avatar_url") or settings.get("avatar_url", "")
        embed_color_hex = (payload.get("embed_color") or settings.get("embed_color", "#38bdf8")).lstrip("#")
        try:
            color_int = int(embed_color_hex, 16)
        except Exception:
            color_int = 3718648

        embed_data = {
            "username": bot_name,
            "avatar_url": avatar_url,
            "embeds": [
                {
                    "title": "FiestaPanel Webhook Bridge Verified",
                    "description": "Connectivity test successful! Your Minecraft server is linked to this Discord channel.",
                    "color": color_int,
                    "fields": [
                        {"name": "Status", "value": "Online & Operational", "inline": True},
                        {"name": "Timestamp", "value": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True}
                    ],
                    "footer": {
                        "text": "FiestaPanel Addon System • Turnkey Deployment"
                    }
                }
            ]
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(embed_data).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "FiestaPanel-Discord/1.2"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status in (200, 204):
                    return {"success": True, "message": "Test ping sent to Discord channel successfully!"}
                return {"success": False, "error": f"Discord returned HTTP status {resp.status}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to deliver payload: {str(e)}"}
            
    return {"success": False, "error": f"Unknown action: {action_name}"}
