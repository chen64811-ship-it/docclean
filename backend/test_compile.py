# -*- coding: utf-8 -*-
"""测试合成书服务"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.book_compiler_service import parse_word_outline, load_md_files, compile_book
from models.file_model import get_all_files
from config import OUTPUT_FOLDER

docx_path = r"C:\Users\ChengXingYu\Desktop\01_Working\vip\餐饮运营知识大全-目录V3.0.docx"

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
    book_title="餐饮运营知识大全"
)
print(f"\n结果: {result}")
