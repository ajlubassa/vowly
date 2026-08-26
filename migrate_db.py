#!/usr/bin/env python3
"""Safe one-time migration helper for Ceremli SQLite persistence."""
import os
import shutil
import sqlite3
import base64

OLD_DB_DIR='/app'
NEW_DB_DIR='/data'
OLD_DB_PATH=os.path.join(OLD_DB_DIR,'vowly.db')
NEW_DB_PATH=os.path.join(NEW_DB_DIR,'vowly.db')
SIDECAR_SUFFIXES=('-wal','-shm')


def _restore_dump(raw):
    if not raw:
        return False
    text=raw.strip()
    # Accept either a plain SQL dump or a base64-encoded SQL dump.
    if text.startswith('base64:'):
        try:text=base64.b64decode(text[7:]).decode('utf-8')
        except Exception:return False
    elif not any(k in text.upper() for k in ('CREATE TABLE','INSERT INTO','BEGIN TRANSACTION','PRAGMA')):
        try:
            decoded=base64.b64decode(text,validate=True).decode('utf-8')
            if any(k in decoded.upper() for k in ('CREATE TABLE','INSERT INTO','BEGIN TRANSACTION','PRAGMA')):text=decoded
        except Exception:pass
    if not any(k in text.upper() for k in ('CREATE TABLE','INSERT INTO','BEGIN TRANSACTION','PRAGMA')):
        return False
    os.makedirs(NEW_DB_DIR,exist_ok=True)
    tmp=NEW_DB_PATH+'.restore'
    try:
        if os.path.exists(tmp):os.remove(tmp)
        c=sqlite3.connect(tmp)
        c.executescript(text)
        c.commit();c.close()
        os.replace(tmp,NEW_DB_PATH)
        print('[migrate_db] Restored persistent database from durable SQL backup.')
        return True
    except Exception as e:
        print(f'[migrate_db] Backup restore failed: {e}')
        try:
            if os.path.exists(tmp):os.remove(tmp)
        except Exception:pass
        return False


def migrate():
    try:
        if os.path.isfile(NEW_DB_PATH):
            print(f'[migrate_db] Database already present at {NEW_DB_PATH}; skipping migration.')
            return
        os.makedirs(NEW_DB_DIR,exist_ok=True)

        # First preference: an existing database in the image/container.
        if os.path.isfile(OLD_DB_PATH):
            print(f'[migrate_db] Migrating {OLD_DB_PATH} to persistent storage.')
            for suffix in ('',)+SIDECAR_SUFFIXES:
                src=OLD_DB_PATH+suffix
                if os.path.isfile(src):
                    shutil.copy2(src,NEW_DB_PATH+suffix)
            if os.path.isfile(NEW_DB_PATH):
                print(f'[migrate_db] Migration complete: {NEW_DB_PATH}')
                return

        # Safe fallback: Railway can preserve a SQL dump in an environment variable
        # before the old ephemeral container is replaced.
        if _restore_dump(os.getenv('DB_BACKUP_DUMP','')):
            return

        print('[migrate_db] No legacy database or durable backup found; application will initialise a new database.')
    except Exception as e:
        print(f'[migrate_db] Unexpected migration error: {e}')


if __name__=='__main__':
    migrate()
