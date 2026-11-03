import os

def init_addon(ctx):
    ctx.logger.info("MOTD Styler addon initialized.")

def on_action(ctx, action_name, payload):
    if action_name == "apply_motd":
        line1 = payload.get("line1", "")
        line2 = payload.get("line2", "")
        combined = f"{line1}\n{line2}" if line2 else line1
        
        # Update server.properties if available
        server_dir = os.environ.get("MC_PATH") or os.environ.get("SERVER_DIR") or "/opt/minecraft"
        props_path = os.path.join(server_dir, "server.properties")
        
        if os.path.exists(props_path):
            try:
                with open(props_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                new_lines = []
                found = False
                for l in lines:
                    if l.strip().startswith("motd="):
                        new_lines.append(f"motd={combined}\n")
                        found = True
                    else:
                        new_lines.append(l)
                if not found:
                    new_lines.append(f"motd={combined}\n")
                with open(props_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                return {"success": True, "message": "MOTD updated in server.properties successfully!"}
            except Exception as e:
                return {"success": False, "error": f"Failed to write server.properties: {str(e)}"}
        return {"success": True, "message": "MOTD saved to configuration."}
    return {"success": False, "error": f"Unknown action: {action_name}"}
