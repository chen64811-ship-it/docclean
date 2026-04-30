# -*- coding: utf-8 -*-
"""
PDF 提取诊断脚本
运行方式：python test_pdf_extract.py
然后把目标 PDF 拖入终端或粘贴路径
"""
import os
import sys


def test_pdf(file_path):
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return

    print(f"\n{'='*50}")
    print(f"测试文件: {file_path}")
    print(f"{'='*50}")

    try:
        import fitz
        doc = fitz.open(file_path)
        print(f"页数: {len(doc)}")
        print(f"元数据: {doc.metadata}")
        print()

        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"\n--- 第 {page_num+1} 页 ---")

            # 1. text 模式
            t1 = page.get_text("text")
            print(f"[text模式] 长度={len(t1.strip())} | 内容预览: {repr(t1.strip()[:200])}")

            # 2. blocks 模式
            blocks = page.get_text("blocks")
            if blocks:
                lines = [b[4].strip() for b in blocks if len(b) >= 5 and b[4].strip()]
                t2 = "\n".join(lines)
                print(f"[blocks模式] 长度={len(t2.strip())} | 内容预览: {repr(t2.strip()[:200])}")
            else:
                print("[blocks模式] 无内容")
                t2 = ""

            # 3. dict 模式
            d = page.get_text("dict")
            spans_text = []
            if d and "blocks" in d:
                for block in d["blocks"]:
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                t = span.get("text", "").strip()
                                if t:
                                    spans_text.append(t)
            t3 = "\n".join(spans_text)
            print(f"[dict模式] 长度={len(t3.strip())} | 内容预览: {repr(t3.strip()[:200])}")

            # 4. HTML 模式
            html = page.get_text("html")
            if html:
                print(f"[html模式] html长度={len(html)}")

            # 5. rawdict 模式
            raw = page.get_text("rawdict")
            if raw:
                print(f"[rawdict模式] keys={list(raw.keys()) if isinstance(raw, dict) else type(raw)}")

            # 6. 检查是否有图片（可能是扫描件）
            images = page.get_images()
            print(f"[图片数量]: {len(images)}")

            # 7. 检查字体信息
            xrefs = set()
            for block in (blocks or []):
                if len(block) >= 6:
                    xrefs.add(block[5])
            print(f"[字体xrefs数量]: {len(xrefs)}")

        doc.close()

        # 综合诊断
        print(f"\n{'='*50}")
        print("诊断结果:")
        if not blocks and not spans_text and not t1.strip():
            print("⚠️ 所有文本提取方式都返回空内容")
            print("可能原因：")
            print("  1. PDF 是扫描件（纯图片），需要 OCR")
            print("  2. PDF 使用了特殊加密/字体")
            print("  3. PDF 是矢量图形而非文本")
            print("\n建议：上传这个 PDF，我来手动检查是否需要走 OCR")
        else:
            print("✅ 可以提取到文本内容，问题可能在其他环节")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"打开PDF失败: {e}")


if __name__ == "__main__":
    print("PDF 提取诊断工具")
    print("=" * 40)
    if len(sys.argv) > 1:
        test_pdf(sys.argv[1])
    else:
        print("用法: python test_pdf_extract.py <pdf文件路径>")
        print("或者把 PDF 拖入此窗口...")
        try:
            path = input("\n请输入 PDF 路径: ").strip().strip('"').strip("'")
            if path:
                test_pdf(path)
        except EOFError:
            pass
