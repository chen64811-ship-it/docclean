# -*- coding: utf-8 -*-
"""
File Status Management Module
Uses SQLite database to track file upload and parsing status.
"""
import sqlite3
import os
import time
from config import BASE_DIR

# Database file path
DB_PATH = os.path.join(BASE_DIR, "files.db")


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database, create files table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # File status: uploading, parsing, done, error
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_ext TEXT NOT NULL,
            status TEXT DEFAULT 'uploading',
            output_path TEXT DEFAULT '',
            tree_path TEXT DEFAULT '',
            error_msg TEXT DEFAULT '',
            created_at REAL DEFAULT (strftime('%s', 'now')),
            updated_at REAL DEFAULT (strftime('%s', 'now'))
        )
    """)
    # Migration: add tree_path column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN tree_path TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.close()


def add_file(original_name, stored_name, file_size, file_ext):
    """
    Add a file record.
    Returns the new file ID (None if duplicate).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Dedup: check if a file with the same name + size already exists
    cursor.execute(
        "SELECT id, status, output_path FROM files WHERE original_name=? AND file_size=? ORDER BY created_at DESC LIMIT 1",
        (original_name, file_size)
    )
    existing = cursor.fetchone()

    if existing:
        existing_id = existing["id"]
        existing_status = existing["status"]

        # If file is still processing or done, don't create a duplicate
        if existing_status in ("uploading", "parsing", "done"):
            print(f"[Dedup] File already exists: {original_name} (id={existing_id}, status={existing_status}), skipping duplicate upload")
            conn.close()
            return None  # None = duplicate

        # If previous attempt was error, allow re-upload (delete old record first)
        if existing_status == "error":
            print(f"[Dedup] Previous failed file found (id={existing_id}), re-uploading")
            cursor.execute("DELETE FROM files WHERE id=?", (existing_id,))
            conn.commit()

    cursor.execute(
        "INSERT INTO files (original_name, stored_name, file_size, file_ext, status) VALUES (?, ?, ?, ?, ?)",
        (original_name, stored_name, file_size, file_ext, "uploading")
    )
    conn.commit()
    file_id = cursor.lastrowid
    conn.close()
    return file_id


def update_file_status(file_id, status, output_path="", error_msg="", tree_path=""):
    """Update file status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE files SET status=?, output_path=?, error_msg=?, tree_path=?, updated_at=? WHERE id=?",
        (status, output_path, error_msg, tree_path, time.time(), file_id)
    )
    conn.commit()
    conn.close()


def get_all_files():
    """
    Get all files, sorted by creation time descending.
    Returns list of dicts.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_file_by_id(file_id):
    """Get a single file by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE id=?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_file(file_id):
    """
    Delete a file record (also removes files from disk).
    Compatible with both old and new path formats: absolute and relative (with ../).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stored_name, output_path, tree_path FROM files WHERE id=?", (file_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    stored_name = row["stored_name"]
    output_path = row["output_path"]
    tree_path = row["tree_path"]

    from config import UPLOAD_FOLDER, OUTPUT_FOLDER, BASE_DIR

    # Delete original uploaded file (may be in uploads/ or OUTPUT_FOLDER/)
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        fp = os.path.join(folder, stored_name)
        fp = os.path.abspath(fp)  # normalize path (handle ../)
        if os.path.exists(fp):
            try: os.remove(fp)
            except Exception: pass

    # Delete exported Markdown file
    if output_path:
        # output_path may be absolute or contain ../
        op = os.path.abspath(output_path)
        if os.path.exists(op):
            try: os.remove(op)
            except Exception: pass
        # Also try same-named .md in OUTPUT_FOLDER
        md_basename = os.path.splitext(stored_name)[0] + ".md"
        md_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, md_basename))
        if os.path.exists(md_path):
            try: os.remove(md_path)
            except Exception: pass

    # Delete tree structure JSON file
    if tree_path:
        tp = os.path.abspath(tree_path)
        if os.path.exists(tp):
            try: os.remove(tp)
            except Exception: pass

    cursor.execute("DELETE FROM files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()


def delete_files_batch(file_ids):
    """Batch delete files."""
    for fid in file_ids:
        delete_file(fid)


# Initialize database on module load
init_db()
