#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from routers.services import add_article, initialize_database, load_article  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Seed an empty blog database from a one-time JSON fixture."
    )
    parser.add_argument(
        "--source",
        default=os.getenv("SEED_ARTICLES_PATH", "data/seed_articles.json"),
        help="JSON file containing article title, content, and summary values.",
    )
    args = parser.parse_args()

    source_path = Path(args.source).expanduser()
    if not source_path.is_absolute():
        source_path = PROJECT_ROOT / source_path

    if not source_path.is_file():
        raise SystemExit(f"Seed file not found: {source_path}")

    articles = json.loads(source_path.read_text(encoding="utf-8"))
    initialize_database()

    existing_count = len(load_article())
    if existing_count:
        print(f"Database already has {existing_count} articles; seed skipped.")
        return

    for article in articles:
        add_article(
            article.get("title", ""),
            article.get("content", ""),
            article.get("summary") or "",
        )

    print(f"Seeded {len(articles)} articles from {source_path}")


if __name__ == "__main__":
    main()
