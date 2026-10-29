import os
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_configured_db_path = Path(os.getenv("DATABASE_PATH", "data.db")).expanduser()
DB_PATH = (
    _configured_db_path
    if _configured_db_path.is_absolute()
    else PROJECT_ROOT / _configured_db_path
)


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
    with get_connection() as connection:
        where = "WHERE is_published = 1" if published_only else ""
        rows = connection.execute(
            f"SELECT id, title, content, summary, is_published FROM articles {where} ORDER BY id DESC"
        ).fetchall()

    return [dict(row) for row in rows]


def get_article_by_id(article_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, content, summary, is_published FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()

    if row is None:
        raise ValueError(f"Article with id: {article_id} is not found")

    return dict(row)


def edit_article(article_id, title, content, summary, is_published=None):
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
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM articles WHERE id = ?",
            (article_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Article with id: {article_id} is not found")

    return True


def add_article(title, content, summary, is_published=True):
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
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ValueError(f"Project {slug} was not found")
    return dict(row)


def save_project(project_id, title, summary="", description="", technologies="", image_url="", demo_url="", repository_url="", is_featured=False, is_published=False):
    values = (title.strip(), summary.strip(), description.strip(), technologies.strip(), image_url.strip(), demo_url.strip(), repository_url.strip(), int(is_featured), int(is_published))
    if not values[0]:
        raise ValueError("A project title is required")
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
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    if cursor.rowcount == 0:
        raise ValueError(f"Project {project_id} was not found")


def load_pages():
    with get_connection() as connection:
        rows = connection.execute("SELECT slug, title, content FROM pages ORDER BY slug").fetchall()
    return {row["slug"]: dict(row) for row in rows}


def save_page(slug, title, content):
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO pages (slug, title, content) VALUES (?, ?, ?) ON CONFLICT(slug) DO UPDATE SET title = excluded.title, content = excluded.content",
            (slug, title.strip(), content.strip()),
        )


def load_settings():
    with get_connection() as connection:
        rows = connection.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def save_settings(values):
    with get_connection() as connection:
        connection.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [(key, value.strip()) for key, value in values.items()],
        )

