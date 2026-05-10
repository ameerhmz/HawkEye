#!/usr/bin/env python3
"""Force-delete alerts, events, recordings, and cameras.

CAUTION: destructive. Deletes all rows in `alerts`, `events`, `recordings`, and `cameras`.
"""
from app.db import SessionLocal
from app.models import Alert, Event, Recording, Camera


def main(dry_run: bool = True):
    db = SessionLocal()
    try:
        counts = {
            'alerts': db.query(Alert).count(),
            'events': db.query(Event).count(),
            'recordings': db.query(Recording).count(),
            'cameras': db.query(Camera).count(),
        }
        print(f"Counts before delete: {counts}")
        if dry_run:
            print("Dry-run: no changes. Use --no-dry-run to delete.")
            return

        for model_name, model in (('alerts', Alert), ('events', Event), ('recordings', Recording), ('cameras', Camera)):
            try:
                deleted = db.query(model).delete()
                db.commit()
                print(f"Deleted {deleted} rows from {model_name}")
            except Exception as e:
                db.rollback()
                print(f"Failed to delete from {model_name}: {e}")

        counts_after = {
            'alerts': db.query(Alert).count(),
            'events': db.query(Event).count(),
            'recordings': db.query(Recording).count(),
            'cameras': db.query(Camera).count(),
        }
        print(f"Counts after delete: {counts_after}")

    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--no-dry-run', dest='dry_run', action='store_false')
    args = p.parse_args()
    main(dry_run=args.dry_run)
