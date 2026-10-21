# Deployment Guide

## 1. Runtime configuration

Copy `.env.example` to a protected environment file and replace every placeholder:

```bash
cp .env.example /etc/myblog.env
chmod 600 /etc/myblog.env
```

The application reads normal process environment variables; it does not read `.env` automatically. When running under systemd, load the file with `EnvironmentFile=/etc/myblog.env`.

Required production values:

```dotenv
APP_ENV=production
APP_DEBUG=false
ADMIN_USERNAME=your-admin-username
ADMIN_PASSWORD=use-a-long-random-password
SESSION_COOKIE_SECURE=true
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_SECONDS=900
DATABASE_PATH=/var/lib/myblog/data.db
BACKUP_DIR=/var/backups/myblog
```

`ADMIN_USERNAME` and `ADMIN_PASSWORD` create or update the admin account at startup. Do not commit the real environment file. The application uses opaque random session tokens stored as hashes in SQLite, so a separate session-signing secret is not required.

## 2. Persistent database

Create a persistent directory outside the release directory:

```bash
sudo install -d -o www-data -g www-data -m 750 /var/lib/myblog
sudo install -d -o www-data -g www-data -m 750 /var/backups/myblog
```

Set `DATABASE_PATH=/var/lib/myblog/data.db`. Do not rely on a container's ephemeral filesystem. If deploying an existing database, copy `data.db` into that directory before starting the app and keep file permissions at `600`.

## 3. Install and run

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
```

Use one worker while the application uses SQLite. Multiple writers can cause database lock contention.

Login throttling is kept in process memory. With the recommended single-worker setup, restarting the service clears the counters; multiple workers would not share them.

Example systemd service:

```ini
[Unit]
Description=MyBlog FastAPI application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/myblog
EnvironmentFile=/etc/myblog.env
ExecStart=/srv/myblog/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always

[Install]
WantedBy=multi-user.target
```

## 4. HTTPS with Let's Encrypt

Caddy obtains and renews Let's Encrypt certificates automatically:

```caddyfile
blog.example.com {
    encode gzip zstd
    reverse_proxy 127.0.0.1:8000
}
```

Allow inbound ports 80 and 443 in the firewall. Keep Uvicorn bound to `127.0.0.1` so it is only reachable through the HTTPS reverse proxy. Alternatively, use Nginx plus Certbot and proxy to the same local Uvicorn address.

Set `SESSION_COOKIE_SECURE=true` and only access the admin area over HTTPS. The cookie is already `HttpOnly` and `SameSite=Lax`.

## 5. Backups

Run the online backup utility from cron or a systemd timer:

```bash
cd /srv/myblog
.venv/bin/python scripts/backup_database.py
```

Example daily cron entry:

```cron
15 2 * * * cd /srv/myblog && .venv/bin/python scripts/backup_database.py >> /var/log/myblog-backup.log 2>&1
```

Copy backups to off-server storage as well. A backup on the same disk protects against mistakes, but not against disk or server failure.

## 6. Pre-deployment checks

- Run the test suite with `.venv/bin/python -m unittest discover -s tests -v`.
- Confirm `/health` returns HTTP 200 and `{"status": "ok", "database": "ok"}`.
- Confirm `APP_DEBUG=false` and no debug tracebacks appear in production.
- Confirm the admin password is not the development password.
- Confirm `SESSION_COOKIE_SECURE=true` behind HTTPS.
- Confirm `.env`, `data.db`, `backups/`, `.venv/`, and `__pycache__/` are untracked.
- Confirm the database is on persistent storage and backups restore correctly.
- Check `/`, an article page, `/login`, `/admin_dashboard`, and a deliberately missing URL.
