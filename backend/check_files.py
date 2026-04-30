# -*- coding: utf-8 -*-
"""查看5篇文章的标题和前100字，确认主题"""
import sqlite3, os
db = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files.db')
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, original_name, output_path FROM files WHERE status='done'").fetchall()
for r in rows:
    p = r['output_path']
    if p and os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
        # 取前200字
        preview = content[:200].replace('\n', ' ')
        print(f"[{r['id']}] {r['original_name']}")
        print(f"    前200字: {preview}")
        print()
conn.close()
