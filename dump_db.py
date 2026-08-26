#!/usr/bin/env python3
"""Dump the live Ceremli SQLite database to a base64-encoded SQL string.

Usage:
    python3 dump_db.py

Prints `base64:<base64-encoded-sql>` to stdout, suitable for use as the
DB_BACKUP_DUMP environment variable consumed by migrate_db.py.
"""
import os
import sqlite3
import base64

DB_PATH = '/app/vowly.db'


def dump():
    if not os.path.isfile(DB_PATH):
        print(f'[dump_db] No database found at {DB_PATH}; nothing to dump.')
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        sql_text = '\n'.join(conn.iterdump())
        conn.close()
        encoded = base64.b64encode(sql_text.encode('utf-8')).decode('ascii')
        print(f'base64:{encoded}')
    except Exception as e:
        print(f'[dump_db] Failed to dump database: {e}')


if __name__ == '__main__':
    dump()
