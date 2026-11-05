#  FiestaPanel Security Architecture & Best Practices

FiestaPanel is built with security, isolation, and defense-in-depth principles in mind. This document outlines the security controls implemented within FiestaPanel and recommended deployment configurations.

---

## Built-in Security Controls

### 1. Password Hashing & Key Derivation
- All user passwords stored in `users.json` are hashed using **scrypt** using unique cryptographic salts generated via `werkzeug.security.generate_password_hash`.
- FiestaPanel never stores plain-text passwords on disk.

### 2. Path Traversal & File Jail
- The File Manager implements strict path resolution (`os.path.abspath`) verifying that any canonical target path begins with the canonical root of the Minecraft server (`SERVER_CONFIG['mc_path']`).
- Any attempt to access `/etc/passwd`, system binaries, or parent directories (`../../`) is intercepted and rejected with an HTTP 403 Forbidden error.

### 3. Session Security
- User sessions are cryptographically signed with a rotating or configured `SECRET_KEY`.
- Cookie headers include `HttpOnly` and `SameSite=Lax` (or `SameSite=Strict`) to mitigate Cross-Site Scripting (XSS) session theft and Cross-Site Request Forgery (CSRF).

### 4. Role-Based Access Control (RBAC)
- Multi-user authentication enforces strict authorization checks across all sensitive API routes:
  - Destructive actions (user creation/deletion, branding changes, system restarts) require **Admin** privileges.
  - In-game moderation and file edits require at least **Operator** privileges.
  - Read-only actions (telemetry, player monitoring) are granted to **Viewer** accounts.

---

##  Recommended Production Deployment

### 1. Run Under a Dedicated System User
While FiestaPanel can run as root, running under an unprivileged user (e.g. `minecraft` or `gateway`) provides stronger defense-in-depth:
```bash
sudo useradd -r -s /bin/false gateway
sudo chown -R gateway:gateway /opt/fiestapanel
```
Ensure sudo permissions for systemctl are scoped tightly using `sudoers.d/fiestapanel`:
```sudoers
gateway ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart fiesta.service, /usr/bin/systemctl status fiesta.service
```

### 2. Enforce HTTPS via Reverse Proxy
Never expose raw port 8080 directly to the public internet without an SSL/TLS termination proxy:
- Use **Nginx** or **Caddy** with automated Let's Encrypt certificates.
- Enforce HTTP Strict Transport Security (HSTS).

### 3. Firewall Rules (UFW / iptables)
Restrict access to internal ports:
```bash
# Allow SSH, Minecraft, and HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 25565/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct access to panel internal port 8080 from the internet
sudo ufw deny 8080/tcp
sudo ufw enable
```

### 4. Admin Password Hygiene
- Choose a unique admin password of at least 12 characters during first installation.
- Use `fiestapanel reset-admin` (or alias `panelctl reset-admin`) to rotate credentials securely.
