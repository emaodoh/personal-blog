#!/usr/bin/env python3
import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_path(value, default):
    path = Path(value or default).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def main():
    parser = argparse.ArgumentParser(
        description="Create a consistent online backup of the blog SQLite database."
    )
    parser.add_argument(
        "--database",
        default=os.getenv("DATABASE_PATH", "data.db"),
        help="Path to the source SQLite database.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("BACKUP_DIR", "backups"),
        help="Directory where backup files will be written.",
    )
    parser.add_argument(
        "--retention",
        type=int,
        default=int(os.getenv("BACKUP_RETENTION", "14")),
        help="Number of recent backup files to retain.",
    )
    args = parser.parse_args()

    if args.retention < 1:
        raise SystemExit("BACKUP_RETENTION must be at least 1.")

    database_path = resolve_path(args.database, "data.db")
    output_dir = resolve_path(args.output_dir, "backups")

    if not database_path.is_file():
        raise SystemExit(f"Database not found: {database_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = output_dir / f"data-{timestamp}.db"

    source = sqlite3.connect(database_path)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
        integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        destination.close()
        source.close()

    if integrity != "ok":
        backup_path.unlink(missing_ok=True)
        raise SystemExit(f"Backup integrity check failed: {integrity}")

    backup_path.chmod(0o600)
    backups = sorted(
        output_dir.glob("data-*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old_backup in backups[args.retention:]:
        old_backup.unlink()

    print(f"Created backup: {backup_path}")


if __name__ == "__main__":
    main()
