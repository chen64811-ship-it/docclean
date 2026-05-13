# -*- coding: utf-8 -*-
"""
一键导出：PDF/Word/Excel/图片/Markdown → 清洗 → 导出 PDF 到桌面
用法：python export_to_desktop.py "文件路径"
不传参数时自动处理桌面上所有 PDF 文件
"""
import sys
import os
import glob

# 把 backend 目录加入模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from services.cleaner_service import clean_text, text_to_markdown
from services.pdf_service import markdown_to_pdf

DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")


def process_file(input_path):
    """处理一个文件，导出清洗后的 PDF 到桌面"""
    input_path = os.path.abspath(input_path)
    if not os.path.exists(input_path):
        print(f"[错误] 文件不存在：{input_path}")
        return False

    filename = os.path.basename(input_path)
    name_no_ext = os.path.splitext(filename)[0]
    file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
    out_pdf_path = os.path.join(DESKTOP, name_no_ext + "_清理版.pdf")

    print(f"\n处理：{filename}")

    # ── 1. 提取文字（直接传完整路径，不依赖 UPLOAD_FOLDER）──
    print("  → 正在提取文字...")
    raw_text = _extract_direct(input_path, file_ext)

    if not raw_text or not raw_text.strip():
        print("  [警告] 提取到的文字为空，可能是扫描件")
        return False

    # ── 2. 清洗文字 ──
    print("  → 正在清洗文字...")
    cleaned = clean_text(raw_text)

    # ── 3. 转为 Markdown ──
    md_text = text_to_markdown(cleaned, title=name_no_ext)

    # ── 4. 生成 PDF ──
    print("  → 正在生成 PDF...")
    pdf_bytes = markdown_to_pdf(md_text, title=name_no_ext)

    # ── 5. 写入桌面 ──
    with open(out_pdf_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"  ✓ 已保存到桌面：{os.path.basename(out_pdf_path)}")
    return True


def _extract_direct(file_path, file_ext):
    """直接从文件完整路径提取文字，不依赖 UPLOAD_FOLDER 配置"""
    if file_ext == "pdf":
        return _extract_pdf(file_path)
    elif file_ext == "docx":
        return _extract_docx(file_path)
    elif file_ext == "xlsx":
        return _extract_xlsx(file_path)
    elif file_ext == "md":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise Exception(f"不支持的格式：{file_ext}")


def _extract_pdf(file_path):
    """用 pdfminer + PyMuPDF 提取 PDF 文字"""
    text = ""

    # 先用 pdfminer，使用更紧的间距参数，避免对齐/两栏布局产生大量假空格
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        from pdfminer.layout import LAParams
        laparams = LAParams(
            char_margin=0.5,    # 默认2.0，降低后不会把字间距误判为空格
            word_margin=0.05,   # 默认0.1，更紧，减少对齐空格
            line_margin=0.3,    # 默认0.3，保持段落分隔
            boxes_flow=0.5,     # 多栏布局阅读顺序权重
        )
        text = pdfminer_extract(file_path, laparams=laparams) or ""
    except Exception:
        pass

    # 如果 pdfminer 结果太少，用 PyMuPDF 补充
    if len(text.strip()) < 50:
        try:
            import fitz
            doc = fitz.open(file_path)
            parts = []
            for page in doc:
                parts.append(page.get_text("text"))
            text = "\n".join(parts)
            doc.close()
        except Exception:
            pass

    return text


def _extract_docx(file_path):
    """提取 Word 文字"""
    from docx import Document
    doc = Document(file_path)
    parts = []
    for para in doc.paragraphs:
        parts.append(para.text)
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return "\n".join(parts)


def _extract_xlsx(file_path):
    """提取 Excel 文字"""
    import openpyxl
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"## {ws.title}")
        for row in ws.iter_rows(values_only=True):
            row_texts = [str(c) if c is not None else "" for c in row]
            parts.append(" | ".join(row_texts))
    return "\n".join(parts)


def main():
    if len(sys.argv) > 1:
        # 传入了具体文件路径
        targets = sys.argv[1:]
    else:
        # 没传参数：处理桌面上所有受支持的文件
        exts = ["*.pdf", "*.docx", "*.xlsx", "*.png", "*.jpg", "*.jpeg", "*.md"]
        targets = []
        for ext in exts:
            targets.extend(glob.glob(os.path.join(DESKTOP, ext)))

        if not targets:
            print("桌面上没有找到可处理的文件（pdf/docx/xlsx/png/jpg/md）")
            print("用法：python export_to_desktop.py \"C:\\path\\to\\file.pdf\"")
            return

        print(f"在桌面找到 {len(targets)} 个文件，开始处理...")

    ok, fail = 0, 0
    for t in targets:
        if process_file(t):
            ok += 1
        else:
            fail += 1

    print(f"\n完成！成功 {ok} 个，失败 {fail} 个")
    print(f"PDF 已保存到桌面：{DESKTOP}")
    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
