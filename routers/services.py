import os
import sqlite3
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


def load_article():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, content, summary FROM articles ORDER BY id"
        ).fetchall()

    return [dict(row) for row in rows]


def get_article_by_id(article_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, content, summary FROM articles WHERE id = ?",
            (article_id,),
        ).fetchone()

    if row is None:
        raise ValueError(f"Article with id: {article_id} is not found")

    return dict(row)


def edit_article(article_id, title, content, summary):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE articles
            SET title = ?, content = ?, summary = ?
            WHERE id = ?
            """,
            (title, content, summary, article_id),
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


def add_article(title, content, summary):
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO articles (title, content, summary) VALUES (?, ?, ?)",
            (title, content, summary),
        )
        article_id = cursor.lastrowid

    return get_article_by_id(article_id)

