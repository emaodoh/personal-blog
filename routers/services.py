import os
import json
import re
import sqlite3
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_configured_db_path = Path(os.getenv("DATABASE_PATH", "data.db")).expanduser()
DB_PATH = (
    _configured_db_path
    if _configured_db_path.is_absolute()
    else PROJECT_ROOT / _configured_db_path
)
_configured_upload_dir = Path(os.getenv("UPLOAD_DIR", "static/uploads")).expanduser()
UPLOAD_DIR = (
    _configured_upload_dir
    if _configured_upload_dir.is_absolute()
    else PROJECT_ROOT / _configured_upload_dir
)
UPLOAD_URL_PREFIX = os.getenv("UPLOAD_URL_PREFIX", "/static/uploads").rstrip("/")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "blog-media")
if bool(SUPABASE_URL) != bool(SUPABASE_SECRET_KEY):
    raise RuntimeError("Set both SUPABASE_URL and SUPABASE_SECRET_KEY, or leave both unset.")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def _supabase_request(table, method="GET", query=None, body=None, prefer=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if query:
        url += "?" + urlencode(query, doseq=True)
    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
    }
    if SUPABASE_SECRET_KEY.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {SUPABASE_SECRET_KEY}"
    if prefer:
        headers["Prefer"] = prefer
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=payload, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            content = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        detail = exc.read().decode("utf-8", errors="replace") if isinstance(exc, HTTPError) else str(exc)
        raise RuntimeError(f"Supabase request failed: {detail}") from exc
    return json.loads(content) if content else []


def upload_image(folder, filename, image_data, content_type):
    if not USE_SUPABASE:
        target = UPLOAD_DIR / folder
        target.mkdir(parents=True, exist_ok=True)
        (target / filename).write_bytes(image_data)
        return f"{UPLOAD_URL_PREFIX}/{folder}/{filename}"

    object_path = f"{folder}/{filename}"
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{object_path}"
    request = Request(
        url,
        data=image_data,
        headers={
            "apikey": SUPABASE_SECRET_KEY,
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        method="POST",
    )
    if SUPABASE_SECRET_KEY.startswith("eyJ"):
        request.add_header("Authorization", f"Bearer {SUPABASE_SECRET_KEY}")
    try:
        with urlopen(request, timeout=30):
            pass
    except (HTTPError, URLError, TimeoutError) as exc:
        detail = exc.read().decode("utf-8", errors="replace") if isinstance(exc, HTTPError) else str(exc)
        raise RuntimeError(f"Supabase image upload failed: {detail}") from exc
    from urllib.parse import quote
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{quote(object_path, safe='/')}"


def check_database():
    if USE_SUPABASE:
        _supabase_request("settings", query={"select": "key", "limit": 1})
        return
    with get_connection() as connection:
        connection.execute("SELECT 1").fetchone()


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=5)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    if USE_SUPABASE:
        # The schema is installed once from supabase_schema.sql. Seed only missing defaults.
        for slug, title, content in (
            ("home", "What I do", "Tell visitors who you are, what you do, and what you build."),
            ("about", "About", "Add your background, interests, and experience here."),
            ("contact", "Contact", "Add a short invitation for visitors to get in touch."),
        ):
            _supabase_request("pages", method="POST", query={"on_conflict": "slug"},
                              body={"slug": slug, "title": title, "content": content},
                              prefer="resolution=ignore-duplicates,return=minimal")
        defaults = {
            "site_name": "Portfolio", "owner_name": "Your Name", "role": "Developer",
            "contact_email": "", "profile_image_url": "", "resume_url": "",
            "github_url": "", "linkedin_url": "",
        }
        _supabase_request("settings", method="POST", query={"on_conflict": "key"},
                          body=[{"key": key, "value": value} for key, value in defaults.items()],
                          prefer="resolution=ignore-duplicates,return=minimal")
        return

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT ''
            )
            """
        )
        article_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(articles)")
        }
        if "is_published" not in article_columns:
            # Existing articles remain public after the additive migration.
            connection.execute(
                "ALTER TABLE articles ADD COLUMN is_published INTEGER NOT NULL DEFAULT 1"
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                summary TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                technologies TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                demo_url TEXT NOT NULL DEFAULT '',
                repository_url TEXT NOT NULL DEFAULT '',
                is_featured INTEGER NOT NULL DEFAULT 0,
                is_published INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            )
            """
        )
        for slug, title, content in (
            ("home", "What I do", "Tell visitors who you are, what you do, and what you build."),
            ("about", "About", "Add your background, interests, and experience here."),
            ("contact", "Contact", "Add a short invitation for visitors to get in touch."),
        ):
            connection.execute(
                "INSERT OR IGNORE INTO pages (slug, title, content) VALUES (?, ?, ?)",
                (slug, title, content),
            )
        for key, value in (
            ("site_name", "Portfolio"),
            ("owner_name", "Your Name"),
            ("role", "Developer"),
            ("contact_email", ""),
            ("profile_image_url", ""),
            ("resume_url", ""),
            ("github_url", ""),
            ("linkedin_url", ""),
        ):
            connection.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )


def load_article(published_only=False):
    if USE_SUPABASE:
        query = {"select": "id,title,content,summary,is_published", "order": "id.desc"}
        if published_only:
            query["is_published"] = "eq.true"
        return _supabase_request("articles", query=query)
    with get_connection() as connection:
        where = "WHERE is_published = 1" if published_only else ""
        rows = connection.execute(
            f"SELECT id, title, content, summary, is_published FROM articles {where} ORDER BY id DESC"
        ).fetchall()

    return [dict(row) for row in rows]


def get_article_by_id(article_id):
    if USE_SUPABASE:
        rows = _supabase_request("articles", query={
            "select": "id,title,content,summary,is_published", "id": f"eq.{article_id}", "limit": 1,
        })
        if not rows:
            raise ValueError(f"Article with id: {article_id} is not found")
        return rows[0]
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, content, summary, is_published FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()

    if row is None:
        raise ValueError(f"Article with id: {article_id} is not found")

    return dict(row)


def edit_article(article_id, title, content, summary, is_published=None):
    if USE_SUPABASE:
        values = {"title": title, "content": content, "summary": summary}
        if is_published is not None:
            values["is_published"] = bool(is_published)
        rows = _supabase_request("articles", method="PATCH", query={
            "id": f"eq.{article_id}", "select": "id,title,content,summary,is_published",
        }, body=values, prefer="return=representation")
        if not rows:
            raise ValueError(f"Article with id: {article_id} is not found")
        return rows[0]
    with get_connection() as connection:
        if is_published is None:
            cursor = connection.execute(
                "UPDATE articles SET title = ?, content = ?, summary = ? WHERE id = ?",
                (title, content, summary, article_id),
            )
        else:
            cursor = connection.execute(
                "UPDATE articles SET title = ?, content = ?, summary = ?, is_published = ? WHERE id = ?",
                (title, content, summary, int(is_published), article_id),
            )

        if cursor.rowcount == 0:
            raise ValueError(f"Article with id: {article_id} is not found")

    return get_article_by_id(article_id)


def delete_article(article_id):
    if USE_SUPABASE:
        rows = _supabase_request("articles", method="DELETE", query={"id": f"eq.{article_id}", "select": "id"}, prefer="return=representation")
        if not rows:
            raise ValueError(f"Article with id: {article_id} is not found")
        return True
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM articles WHERE id = ?",
            (article_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Article with id: {article_id} is not found")

    return True


def add_article(title, content, summary, is_published=True):
    if USE_SUPABASE:
        rows = _supabase_request("articles", method="POST", query={"select": "id,title,content,summary,is_published"},
                                 body={"title": title, "content": content, "summary": summary,
                                       "is_published": bool(is_published)}, prefer="return=representation")
        return rows[0]
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO articles (title, content, summary, is_published) VALUES (?, ?, ?, ?)",
            (title, content, summary, int(is_published)),
        )
        article_id = cursor.lastrowid

    return get_article_by_id(article_id)


def _slugify(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.lower())).strip("-") or "project"


def _unique_project_slug(title, exclude_id=None):
    base = _slugify(title)
    slug = base
    suffix = 2
    if USE_SUPABASE:
        while True:
            rows = _supabase_request("projects", query={"select": "id", "slug": f"eq.{slug}", "limit": 1})
            if not rows or rows[0]["id"] == exclude_id:
                return slug
            slug = f"{base}-{suffix}"
            suffix += 1
    with get_connection() as connection:
        while True:
            row = connection.execute(
                "SELECT id FROM projects WHERE slug = ?", (slug,)
            ).fetchone()
            if row is None or row["id"] == exclude_id:
                return slug
            slug = f"{base}-{suffix}"
            suffix += 1


def load_projects(published_only=False, featured_only=False):
    if USE_SUPABASE:
        query = {"select": "*", "order": "is_featured.desc,id.desc"}
        if published_only:
            query["is_published"] = "eq.true"
        if featured_only:
            query["is_featured"] = "eq.true"
        return _supabase_request("projects", query=query)
    clauses = []
    if published_only:
        clauses.append("is_published = 1")
    if featured_only:
        clauses.append("is_featured = 1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM projects {where} ORDER BY is_featured DESC, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_project_by_slug(slug):
    if USE_SUPABASE:
        rows = _supabase_request("projects", query={"select": "*", "slug": f"eq.{slug}", "limit": 1})
        if not rows:
            raise ValueError(f"Project {slug} was not found")
        return rows[0]
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ValueError(f"Project {slug} was not found")
    return dict(row)


def save_project(project_id, title, summary="", description="", technologies="", image_url="", demo_url="", repository_url="", is_featured=False, is_published=False):
    values = (title.strip(), summary.strip(), description.strip(), technologies.strip(), image_url.strip(), demo_url.strip(), repository_url.strip(), int(is_featured), int(is_published))
    if not values[0]:
        raise ValueError("A project title is required")
    if USE_SUPABASE:
        fields = ("title", "summary", "description", "technologies", "image_url", "demo_url",
                  "repository_url", "is_featured", "is_published")
        payload = dict(zip(fields, values))
        if project_id is None:
            payload["slug"] = _unique_project_slug(values[0])
            rows = _supabase_request("projects", method="POST", query={"select": "*"}, body=payload,
                                     prefer="return=representation")
        else:
            rows = _supabase_request("projects", method="PATCH", query={"id": f"eq.{project_id}", "select": "*"},
                                     body=payload, prefer="return=representation")
            if not rows:
                raise ValueError(f"Project {project_id} was not found")
        return rows[0]
    with get_connection() as connection:
        if project_id is None:
            slug = _unique_project_slug(values[0])
            cursor = connection.execute(
                "INSERT INTO projects (title, slug, summary, description, technologies, image_url, demo_url, repository_url, is_featured, is_published) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (values[0], slug, *values[1:]),
            )
            project_id = cursor.lastrowid
        else:
            cursor = connection.execute(
                "UPDATE projects SET title = ?, summary = ?, description = ?, technologies = ?, image_url = ?, demo_url = ?, repository_url = ?, is_featured = ?, is_published = ? WHERE id = ?",
                (*values, project_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Project {project_id} was not found")
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row)


def delete_project(project_id):
    if USE_SUPABASE:
        rows = _supabase_request("projects", method="DELETE", query={"id": f"eq.{project_id}", "select": "id"},
                                 prefer="return=representation")
        if not rows:
            raise ValueError(f"Project {project_id} was not found")
        return
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    if cursor.rowcount == 0:
        raise ValueError(f"Project {project_id} was not found")


def load_pages():
    if USE_SUPABASE:
        rows = _supabase_request("pages", query={"select": "slug,title,content", "order": "slug"})
        return {row["slug"]: row for row in rows}
    with get_connection() as connection:
        rows = connection.execute("SELECT slug, title, content FROM pages ORDER BY slug").fetchall()
    return {row["slug"]: dict(row) for row in rows}


def save_page(slug, title, content):
    if USE_SUPABASE:
        _supabase_request("pages", method="POST", query={"on_conflict": "slug"},
                          body={"slug": slug, "title": title.strip(), "content": content.strip()},
                          prefer="resolution=merge-duplicates,return=minimal")
        return
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO pages (slug, title, content) VALUES (?, ?, ?) ON CONFLICT(slug) DO UPDATE SET title = excluded.title, content = excluded.content",
            (slug, title.strip(), content.strip()),
        )


def load_settings():
    if USE_SUPABASE:
        rows = _supabase_request("settings", query={"select": "key,value"})
        return {row["key"]: row["value"] for row in rows}
    with get_connection() as connection:
        rows = connection.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def save_settings(values):
    if USE_SUPABASE:
        _supabase_request("settings", method="POST", query={"on_conflict": "key"},
                          body=[{"key": key, "value": value.strip()} for key, value in values.items()],
                          prefer="resolution=merge-duplicates,return=minimal")
        return
    with get_connection() as connection:
        connection.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [(key, value.strip()) for key, value in values.items()],
        )

