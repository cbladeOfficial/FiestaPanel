import socket

def init_addon(ctx):
    ctx.logger.info("Live Web Map Viewer addon loaded.")

def on_action(ctx, action_name, payload):
    if action_name == "detect_port":
        ports = [8123, 8100, 8085, 8080]
        detected = []
        for p in ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                res = s.connect_ex(('127.0.0.1', p))
                s.close()
                if res == 0:
                    detected.append(p)
            except Exception:
                pass
        return {"success": True, "detected_ports": detected}
    return {"success": False, "error": f"Unknown action: {action_name}"}
