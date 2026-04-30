# -*- coding: utf-8 -*-
import sqlite3, os
db = os.path.join(os.path.dirname(__file__), '..', 'files.db')
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, original_name, stored_name, output_path FROM files WHERE status='done' ORDER BY original_name").fetchall()
for r in rows:
    print(f"{r['id']:>4} | {r['original_name'][:80]:<80} | {r['stored_name']}")
print(f"\n共 {len(rows)} 个已完成文件")
conn.close()
