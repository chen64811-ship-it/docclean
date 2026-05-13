# -*- coding: utf-8 -*-
"""
数据库迁移脚本
自动修复老版本数据库缺少 created_at 列的问题
修复后：所有历史文件的 created_at 会补上当前时间
"""
import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "files.db")
DB_PATH = os.path.abspath(DB_PATH)


def migrate():
    if not os.path.exists(DB_PATH):
        print("数据库不存在，跳过迁移")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查 created_at 列是否存在
    cursor.execute("PRAGMA table_info(files)")
    columns = [row[1] for row in cursor.fetchall()]

    print(f"当前表字段: {columns}")

    if "created_at" not in columns:
        print("检测到缺少 created_at 列，开始修复...")
        # 给没有 created_at 的记录补上当前时间
        cursor.execute("ALTER TABLE files ADD COLUMN created_at REAL DEFAULT (strftime('%s', 'now'))")
        conn.commit()
        print("created_at 列已添加，迁移完成")
    else:
        print("created_at 列已存在，无需迁移")

    conn.close()
    print("数据库检查完毕 ✓")


if __name__ == "__main__":
    migrate()
