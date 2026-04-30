# -*- coding: utf-8 -*-
"""
文件状态管理模块
使用 SQLite 数据库记录文件上传和解析状态
"""
import sqlite3
import os
import time
from config import BASE_DIR

# 数据库文件路径
DB_PATH = os.path.join(BASE_DIR, "files.db")


def get_db_connection():
    """
    获取数据库连接
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    初始化数据库，创建 files 表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # 文件状态：uploading（上传中）、parsing（解析中）、done（已完成）、error（失败）
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
    # 迁移：给已有表添加 tree_path 列（如果不存在）
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN tree_path TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 列已存在
    conn.close()


def add_file(original_name, stored_name, file_size, file_ext):
    """
    添加一条文件记录
    返回新文件的 ID（如果是重复文件返回 None）
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # ===== 去重：检查同名文件是否已存在（用 original_name + file_size 组合判断）=====
    cursor.execute(
        "SELECT id, status, output_path FROM files WHERE original_name=? AND file_size=? ORDER BY created_at DESC LIMIT 1",
        (original_name, file_size)
    )
    existing = cursor.fetchone()

    if existing:
        existing_id = existing["id"]
        existing_status = existing["status"]

        # 如果已有文件还在处理中或已完成，不要重复创建记录
        if existing_status in ("uploading", "parsing", "done"):
            print(f"[去重] 文件已存在：{original_name}（id={existing_id}，状态={existing_status}），跳过重复上传")
            conn.close()
            return None  # 返回 None 表示重复

        # 如果已有文件是失败状态，允许重新上传（先删旧记录）
        if existing_status == "error":
            print(f"[去重] 发现之前失败的文件（id={existing_id}），将重新上传")
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
    """
    更新文件状态
    """
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
    获取所有文件列表，按时间倒序
    返回列表，每项是字典
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_file_by_id(file_id):
    """
    根据 ID 获取单个文件
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE id=?", (file_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_file(file_id):
    """
    删除文件记录（同时删除磁盘上的文件）
    兼容新旧路径：output_path 可能是相对路径或包含 ../
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

    # 删除原始上传文件（上传文件可能存在 uploads/ 或 OUTPUT_FOLDER/ 下）
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        fp = os.path.join(folder, stored_name)
        fp = os.path.abspath(fp)  # 规范化路径（处理 ../）
        if os.path.exists(fp):
            try: os.remove(fp)
            except Exception: pass

    # 删除导出的 Markdown 文件
    if output_path:
        # output_path 可能是绝对路径，也可能是包含 ../ 的路径
        op = os.path.abspath(output_path)
        if os.path.exists(op):
            try: os.remove(op)
            except Exception: pass
        # 同时尝试 OUTPUT_FOLDER 下同名 md 文件
        md_basename = os.path.splitext(stored_name)[0] + ".md"
        md_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, md_basename))
        if os.path.exists(md_path):
            try: os.remove(md_path)
            except Exception: pass

    # 删除树结构 JSON 文件
    if tree_path:
        tp = os.path.abspath(tree_path)
        if os.path.exists(tp):
            try: os.remove(tp)
            except Exception: pass

    cursor.execute("DELETE FROM files WHERE id=?", (file_id,))
    conn.commit()
    conn.close()


def delete_files_batch(file_ids):
    """
    批量删除文件
    """
    for fid in file_ids:
        delete_file(fid)


# 初始化数据库
init_db()
