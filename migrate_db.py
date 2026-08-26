#!/usr/bin/env python3
"""One-time migration helper.

Historically vowly.db lived at the ephemeral path /app/vowly.db inside the
container. A persistent Railway volume is now mounted at /data/, and the
application has moved to storing its SQLite database there instead.

On the first deploy after the volume is attached, the new container starts
with a fresh filesystem at /app (no data) and an empty volume at /data (no
database yet). Without intervention the app would just create a brand new,
empty database at /data/vowly.db, silently discarding all existing wedding
data, guests, RSVPs and invitations.

This script runs once at startup, before any database connections are
opened, and copies the old ephemeral database (plus its WAL/SHM sidecar
files, in case there are uncommitted transactions) into the new volume
location. It is safe to run on every startup: once /data/vowly.db exists it
becomes a no-op.
"""
import os
import shutil

OLD_DB_DIR = '/app'
NEW_DB_DIR = '/data'
OLD_DB_PATH = os.path.join(OLD_DB_DIR, 'vowly.db')
NEW_DB_PATH = os.path.join(NEW_DB_DIR, 'vowly.db')

# SQLite may also have write-ahead-log / shared-memory sidecar files with
# uncommitted data that hasn't been checkpointed into the main db file yet.
SIDECAR_SUFFIXES = ('-wal', '-shm')


def migrate():
    try:
        old_exists = os.path.isfile(OLD_DB_PATH)
        new_exists = os.path.isfile(NEW_DB_PATH)

        if not old_exists:
            print(f'[migrate_db] No legacy database found at {OLD_DB_PATH}; nothing to migrate.')
            return

        if new_exists:
            print(f'[migrate_db] Database already present at {NEW_DB_PATH}; skipping migration.')
            return

        print(f'[migrate_db] Found legacy database at {OLD_DB_PATH} and no database at {NEW_DB_PATH}. Migrating...')

        try:
            os.makedirs(NEW_DB_DIR, exist_ok=True)
        except Exception as e:
            print(f'[migrate_db] ERROR: could not create {NEW_DB_DIR}: {e}')
            return

        files_to_copy = [OLD_DB_PATH]
        for suffix in SIDECAR_SUFFIXES:
            sidecar = OLD_DB_PATH + suffix
            if os.path.isfile(sidecar):
                files_to_copy.append(sidecar)

        for src in files_to_copy:
            dest = os.path.join(NEW_DB_DIR, os.path.basename(src))
            try:
                shutil.copy2(src, dest)
                print(f'[migrate_db] Copied {src} -> {dest}')
            except FileNotFoundError:
                print(f'[migrate_db] WARNING: {src} disappeared before it could be copied; skipping.')
            except PermissionError as e:
                print(f'[migrate_db] ERROR: permission denied copying {src} -> {dest}: {e}')
            except Exception as e:
                print(f'[migrate_db] ERROR: failed to copy {src} -> {dest}: {e}')

        if os.path.isfile(NEW_DB_PATH):
            print(f'[migrate_db] Migration complete. Database is now at {NEW_DB_PATH}.')
        else:
            print(f'[migrate_db] Migration did not produce {NEW_DB_PATH}; the app will start with a fresh database.')

    except Exception as e:
        # Never let a migration failure block the app from starting.
        print(f'[migrate_db] Unexpected error during migration: {e}')


if __name__ == '__main__':
    migrate()
