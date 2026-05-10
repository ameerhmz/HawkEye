#!/usr/bin/env python3
"""Reset camera-related data and stored snapshot images.

This script removes:
- alerts, events, recordings, and cameras from the database
- all snapshot images from backend/static/snapshots and static/snapshots

Use this when you want to wipe previous camera registrations and photo captures.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal
from app.models import Alert, Camera, Event, Recording


SNAPSHOT_DIRS = [
    ROOT / "static" / "snapshots",
    ROOT.parent / "static" / "snapshots",
]


def list_snapshot_files() -> list[Path]:
    files: list[Path] = []
    for directory in SNAPSHOT_DIRS:
        if directory.exists():
            files.extend([path for path in directory.iterdir() if path.is_file()])
    return files


def delete_snapshot_files(dry_run: bool) -> int:
    deleted = 0
    for directory in SNAPSHOT_DIRS:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file():
                continue
            if dry_run:
                print(f"Would delete snapshot {path}")
                deleted += 1
                continue
            try:
                path.unlink()
                print(f"Deleted snapshot {path}")
                deleted += 1
            except Exception as exc:
                print(f"Failed to delete {path}: {exc}")
    return deleted


def reset_database(dry_run: bool) -> None:
    db = SessionLocal()
    try:
        counts = {
            "alerts": db.query(Alert).count(),
            "events": db.query(Event).count(),
            "recordings": db.query(Recording).count(),
            "cameras": db.query(Camera).count(),
        }
        print(f"Counts before reset: {counts}")

        if dry_run:
            print("Dry-run: no database changes made. Use --no-dry-run to delete.")
            return

        for label, model in (("alerts", Alert), ("events", Event), ("recordings", Recording), ("cameras", Camera)):
            try:
                deleted = db.query(model).delete()
                db.commit()
                print(f"Deleted {deleted} rows from {label}")
            except Exception as exc:
                db.rollback()
                print(f"Failed to delete from {label}: {exc}")

        counts_after = {
            "alerts": db.query(Alert).count(),
            "events": db.query(Event).count(),
            "recordings": db.query(Recording).count(),
            "cameras": db.query(Camera).count(),
        }
        print(f"Counts after reset: {counts_after}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset camera registrations and snapshot captures")
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Actually delete instead of just showing what would be removed",
    )
    args = parser.parse_args()

    snapshot_files = list_snapshot_files()
    print(f"Snapshot directories: {', '.join(str(directory) for directory in SNAPSHOT_DIRS)}")
    print(f"Found {len(snapshot_files)} snapshot file(s)")

    if args.dry_run:
        delete_snapshot_files(dry_run=True)
        reset_database(dry_run=True)
        return

    deleted_files = delete_snapshot_files(dry_run=False)
    print(f"Deleted {deleted_files} snapshot file(s)")
    reset_database(dry_run=False)


if __name__ == "__main__":
    main()