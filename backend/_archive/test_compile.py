# -*- coding: utf-8 -*-
"""测试合成书服务"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.book_compiler_service import parse_word_outline, load_md_files, compile_book
from models.file_model import get_all_files
from config import OUTPUT_FOLDER

# 自动扫描项目根目录（backend 的上一级）下的 .docx 文件作为大纲
_vip_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
docx_files = [f for f in os.listdir(_vip_dir) if f.endswith(".docx") and not f.startswith("~$")]
docx_path = os.path.join(_vip_dir, docx_files[0]) if docx_files else ""

# 1. 测试大纲解析
secs = parse_word_outline(docx_path)
print(f"总章节数: {len(secs)}")
for s in secs[:15]:
    print(f"  {s['num']} | {s['title'][:40]}")

# 2. 获取已完成文件
records = get_all_files()
done = [r for r in records if r.get("status") == "done"]
print(f"\n已完成文件数: {len(done)}")
for r in done:
    print(f"  [{r['id']}] {r['original_name']}")

# 3. 执行合成
print("\n开始合成（LLM 智能匹配）...")
result = compile_book(
    docx_path=docx_path,
    output_folder=OUTPUT_FOLDER,
    file_records=done,
    book_title=os.path.splitext(os.path.basename(docx_path))[0] if docx_path else "知识库"
)
print(f"\n结果: {result}")
