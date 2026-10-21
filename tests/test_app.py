import asyncio
import json
import os
import re
import shutil
import tempfile
import unittest
import urllib.parse
from pathlib import Path


TEST_DIR = Path(tempfile.mkdtemp(prefix="myblog-tests-"))
os.environ["DATABASE_PATH"] = str(TEST_DIR / "data.db")
os.environ["APP_ENV"] = "production"
os.environ["APP_DEBUG"] = "false"
os.environ["SESSION_COOKIE_SECURE"] = "true"
os.environ["ADMIN_USERNAME"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "correct-horse-battery-staple"
os.environ["LOGIN_MAX_ATTEMPTS"] = "3"
os.environ["LOGIN_WINDOW_SECONDS"] = "60"

from app import app  # noqa: E402


def call_app(method, path, body=None, headers=None):
    parsed = urllib.parse.urlsplit(path)
    request_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]

    if body is not None and "content-type" not in {key.decode() for key, _ in request_headers}:
        body = urllib.parse.urlencode(body).encode()
        request_headers.append((b"content-type", b"application/x-www-form-urlencoded"))
    elif isinstance(body, str):
        body = body.encode()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "https",
        "path": parsed.path,
        "raw_path": parsed.path.encode(),
        "query_string": parsed.query.encode(),
        "root_path": "",
        "headers": request_headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 443),
    }
    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body or b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))

    start = next(message for message in messages if message["type"] == "http.response.start")
    response_headers = {
        key.decode().lower(): value.decode()
        for key, value in start["headers"]
    }
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    ).decode()
    return start["status"], response_headers, response_body


def extract_csrf(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return match.group(1) if match else None


class BlogApplicationTests(unittest.TestCase):
    def login(self, username="testadmin", password="correct-horse-battery-staple"):
        status, headers, body = call_app(
            "POST",
            "/login",
            {"username": username, "password": password},
        )
        cookie = headers.get("set-cookie", "").split(";", 1)[0] or None
        return status, headers, body, cookie

    def test_health_and_public_pages(self):
        status, _, body = call_app("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok", "database": "ok"})

        status, _, body = call_app("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("site.css", body)
        self.assertIn("Latest field notes", body)

    def test_custom_404_and_api_404(self):
        status, headers, body = call_app("GET", "/missing-page")
        self.assertEqual(status, 404)
        self.assertTrue(headers["content-type"].startswith("text/html"))
        self.assertIn("This page wandered off", body)

        status, headers, body = call_app("GET", "/api/articles/999999")
        self.assertEqual(status, 404)
        self.assertTrue(headers["content-type"].startswith("application/json"))
        self.assertIn("detail", json.loads(body))

    def test_admin_routes_require_login(self):
        for path in ["/admin_dashboard", "/add_blog", "/edit_blog/1"]:
            status, headers, _ = call_app("GET", path)
            self.assertEqual(status, 303, path)
            self.assertEqual(headers["location"], "/login", path)

    def test_invalid_login_and_secure_cookie(self):
        status, headers, _, cookie = self.login(password="wrong-password")
        self.assertEqual(status, 401)
        self.assertIsNone(cookie)

        status, headers, _, cookie = self.login()
        self.assertEqual(status, 303)
        self.assertIsNotNone(cookie)
        set_cookie = headers["set-cookie"]
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("Secure", set_cookie)
        self.assertIn("SameSite=lax", set_cookie)

        status, _, body = call_app("GET", "/admin_dashboard", headers={"cookie": cookie})
        self.assertEqual(status, 200)
        self.assertIn("Studio dashboard", body)

    def test_login_rate_limit(self):
        for _ in range(3):
            status, _, _, _ = self.login(username="ratelimit-user", password="wrong")
            self.assertEqual(status, 401)

        status, _, body, _ = self.login(username="ratelimit-user", password="wrong")
        self.assertEqual(status, 429)
        self.assertIn("Too many failed attempts", body)

    def test_admin_crud_and_csrf_protection(self):
        _, _, _, cookie = self.login()
        headers = {"cookie": cookie}

        status, _, add_page = call_app("GET", "/add_blog", headers=headers)
        self.assertEqual(status, 200)
        csrf_token = extract_csrf(add_page)
        self.assertIsNotNone(csrf_token)

        status, _, _ = call_app(
            "POST",
            "/add_blog",
            {
                "title": "Test story",
                "summary": "Test summary",
                "content": "Test content",
                "csrf_token": "invalid-token",
            },
            headers=headers,
        )
        self.assertEqual(status, 403)

        status, _, _ = call_app(
            "POST",
            "/add_blog",
            {
                "title": "Test story",
                "summary": "Test summary",
                "content": "Test content",
                "csrf_token": csrf_token,
            },
            headers=headers,
        )
        self.assertEqual(status, 303)

        status, _, body = call_app("GET", "/api/articles")
        self.assertEqual(status, 200)
        article = next(item for item in json.loads(body) if item["title"] == "Test story")

        status, _, edit_page = call_app(
            "GET",
            f"/edit_blog/{article['id']}",
            headers=headers,
        )
        self.assertEqual(status, 200)
        csrf_token = extract_csrf(edit_page)

        status, _, _ = call_app(
            "POST",
            f"/edit_blog/{article['id']}",
            {
                "title": "Updated test story",
                "summary": "Updated summary",
                "content": "Updated content",
                "csrf_token": csrf_token,
            },
            headers=headers,
        )
        self.assertEqual(status, 303)

        status, _, body = call_app("GET", f"/api/articles/{article['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["summary"], "Updated summary")

        status, _, dashboard = call_app("GET", "/admin_dashboard", headers=headers)
        csrf_token = extract_csrf(dashboard)
        status, _, _ = call_app(
            "POST",
            f"/delete_blog/{article['id']}",
            {"csrf_token": csrf_token},
            headers=headers,
        )
        self.assertEqual(status, 303)

        status, _, _ = call_app("GET", f"/api/articles/{article['id']}")
        self.assertEqual(status, 404)


def tearDownModule():
    shutil.rmtree(TEST_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
