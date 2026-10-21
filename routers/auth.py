import hashlib
import hmac
import os
import secrets
import threading
import time

from fastapi import HTTPException, Request

from .services import get_connection


SESSION_COOKIE_NAME = "admin_session"
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", 12 * 60 * 60))
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", 600_000))
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", 5))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", 15 * 60))

_login_failures = {}
_login_failures_lock = threading.Lock()


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _admin_credentials_from_env():
    username = os.getenv("ADMIN_USERNAME", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    return username, password


SESSION_COOKIE_SECURE = _env_bool(
    "SESSION_COOKIE_SECURE",
    os.getenv("APP_ENV", "development").strip().lower() == "production",
)


def _hash_password(password, salt, iterations):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        iterations,
    ).hex()


def _create_password_hash(password):
    salt = secrets.token_hex(16)
    digest = _hash_password(password, salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def _verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt, expected_hash = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        actual_hash = _hash_password(password, salt, int(iterations))
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(actual_hash, expected_hash)


def _hash_session_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def initialize_admin_auth():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token_hash TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                csrf_token TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )
        session_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(admin_sessions)")
        }
        if "csrf_token" not in session_columns:
            connection.execute(
                "ALTER TABLE admin_sessions ADD COLUMN csrf_token TEXT NOT NULL DEFAULT ''"
            )
        connection.execute(
            "DELETE FROM admin_sessions WHERE expires_at <= ?",
            (int(time.time()),),
        )
        admin_count = connection.execute(
            "SELECT COUNT(*) FROM admin_users"
        ).fetchone()[0]
        admin_username, admin_password = _admin_credentials_from_env()

        if admin_username and admin_password:
            connection.execute(
                """
                INSERT INTO admin_users (username, password_hash)
                VALUES (?, ?)
                ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash
                """,
                (admin_username, _create_password_hash(admin_password)),
            )
        elif admin_count == 0:
            raise RuntimeError(
                "No admin account exists. Set ADMIN_USERNAME and ADMIN_PASSWORD "
                "environment variables before starting the application."
            )


def authenticate_admin(username, password):
    username = username.strip().lower()
    if not username or not password:
        return None

    with get_connection() as connection:
        row = connection.execute(
            "SELECT username, password_hash FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None or not _verify_password(password, row["password_hash"]):
        return None

    return row["username"]


def create_admin_session(username):
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    now = int(time.time())

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM admin_sessions WHERE expires_at <= ?",
            (now,),
        )
        connection.execute(
            """
            INSERT INTO admin_sessions (token_hash, username, csrf_token, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _hash_session_token(token),
                username,
                csrf_token,
                now + SESSION_MAX_AGE_SECONDS,
            ),
        )

    return token


def get_admin_session(token):
    if not token:
        return None

    now = int(time.time())
    token_hash = _hash_session_token(token)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT username, csrf_token FROM admin_sessions
            WHERE token_hash = ? AND expires_at > ?
            """,
            (token_hash, now),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_admin_session_username(token):
    session = get_admin_session(token)
    return session["username"] if session else None


def delete_admin_session(token):
    if not token:
        return

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM admin_sessions WHERE token_hash = ?",
            (_hash_session_token(token),),
        )


def require_admin(request: Request):
    session = get_admin_session(request.cookies.get(SESSION_COOKIE_NAME))
    if session is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})

    return session


def require_admin_api(request: Request):
    username = get_admin_session_username(request.cookies.get(SESSION_COOKIE_NAME))
    if username is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    return username


def validate_csrf_token(request: Request, provided_token):
    session = get_admin_session(request.cookies.get(SESSION_COOKIE_NAME))
    if (
        session is None
        or not provided_token
        or not hmac.compare_digest(session["csrf_token"], provided_token)
    ):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    return session


def _login_attempt_key(request, username):
    client_host = request.client.host if request.client else "unknown"
    return client_host, username.strip().lower()


def is_login_rate_limited(request, username):
    now = time.monotonic()
    key = _login_attempt_key(request, username)

    with _login_failures_lock:
        attempts = [
            timestamp
            for timestamp in _login_failures.get(key, [])
            if now - timestamp < LOGIN_WINDOW_SECONDS
        ]
        if attempts:
            _login_failures[key] = attempts
        else:
            _login_failures.pop(key, None)

    return len(attempts) >= LOGIN_MAX_ATTEMPTS


def record_login_failure(request, username):
    key = _login_attempt_key(request, username)
    with _login_failures_lock:
        _login_failures.setdefault(key, []).append(time.monotonic())


def clear_login_failures(request, username):
    key = _login_attempt_key(request, username)
    with _login_failures_lock:
        _login_failures.pop(key, None)
