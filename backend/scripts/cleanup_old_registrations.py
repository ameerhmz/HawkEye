#!/usr/bin/env python3
"""Cleanup old camera registrations and their snapshot images.

Usage:
  python cleanup_old_registrations.py [--days N] [--dry-run]

Defaults: --days 30

This script will:
 - Find `Camera` rows with `created_at` older than N days
 - Delete matching snapshot files in backend/static/snapshots named
   like `snapshot_<camera_id>_*.jpg`
 - Delete the Camera rows from the database

By default it performs a dry-run. Use `--no-dry-run` to actually delete.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from sqlalchemy import select

# Use absolute imports so script can be run with PYTHONPATH=backend
from app.db import SessionLocal
from app.models import Camera


SNAPSHOT_DIR = Path(__file__).resolve().parents[1] / "static" / "snapshots"


def find_snapshot_files_for_camera(camera_id: int) -> List[Path]:
    prefix = f"snapshot_{camera_id}_"
    if not SNAPSHOT_DIR.exists():
        return []
    return [p for p in SNAPSHOT_DIR.iterdir() if p.name.startswith(prefix)]


def cleanup(days: int = 30, dry_run: bool = True):
    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        stmt = select(Camera).where(Camera.created_at < cutoff)
        res = db.execute(stmt).scalars().all()
        if not res:
            print(f"No camera registrations older than {days} days (cutoff={cutoff}).")
            return

        print(f"Found {len(res)} camera(s) older than {days} days:")
        for cam in res:
            print(f" - id={cam.id} name={cam.name} created_at={cam.created_at}")
            snaps = find_snapshot_files_for_camera(cam.id)
            if snaps:
                print(f"   -> {len(snaps)} snapshot(s) to remove:")
                for s in snaps:
                    print(f"      {s}")
            else:
                print("   -> no snapshots found")

        if dry_run:
            print("\nDry-run mode: no changes made. Rerun with --no-dry-run to delete.")
            return

        # proceed with deletion
        for cam in res:
            snaps = find_snapshot_files_for_camera(cam.id)
            for s in snaps:
                try:
                    s.unlink()
                    print(f"Deleted snapshot {s}")
                except Exception as e:
                    print(f"Failed to delete {s}: {e}")
            try:
                db.delete(cam)
                db.commit()
                print(f"Deleted camera id={cam.id} name={cam.name}")
            except Exception as e:
                db.rollback()
                print(f"Failed to delete camera id={cam.id}: {e}")

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cleanup old camera registrations and snapshots")
    parser.add_argument("--days", type=int, default=30, help="Age in days to consider old (default: 30)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Actually delete instead of dry-run")
    args = parser.parse_args()

    print(f"Snapshot directory: {SNAPSHOT_DIR}")
    cleanup(days=args.days, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
