#!/usr/bin/env python3
"""Delete all camera registrations and all snapshot images.

CAUTION: This is destructive. Use only when you intend to remove everything.
"""
from pathlib import Path
import argparse

from app.db import SessionLocal
from app.models import Camera


SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "static" / "snapshots"


def delete_all(dry_run: bool = True):
    print("Snapshot directory:", SNAPSHOT_DIR)
    # list snapshot files
    snaps = []
    if SNAPSHOT_DIR.exists():
        snaps = list(SNAPSHOT_DIR.iterdir())

    db = SessionLocal()
    try:
        cams = db.query(Camera).all()
        print(f"Found {len(cams)} camera registrations and {len(snaps)} snapshot files.")
        if dry_run:
            print("Dry-run: no changes made. Use --no-dry-run to delete.")
            return

        # delete snapshots
        for s in snaps:
            try:
                s.unlink()
                print(f"Deleted snapshot {s}")
            except Exception as e:
                print(f"Failed to delete {s}: {e}")

        # delete camera rows
        try:
            deleted = db.query(Camera).delete()
            db.commit()
            print(f"Deleted {deleted} camera rows from database.")
        except Exception as e:
            db.rollback()
            print(f"Failed to delete camera rows: {e}")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Actually delete instead of dry-run")
    args = parser.parse_args()
    delete_all(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
