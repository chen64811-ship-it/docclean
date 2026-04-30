# -*- coding: utf-8 -*-
"""
文档内容提取服务
支持 PDF、Word（docx）、Excel（xlsx）、Markdown、图片（OCR）
Word 格式：保留标题层级、加粗、斜体、列表、图片

优化：
1. GPU 加速：OCR 使用线程池 + GPU 并行处理
2. 智能判断：原生 PDF 直接提取文字，扫描件才走 OCR
"""
import os
import traceback
import uuid
import re
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from threading import Lock
from config import OUTPUT_FOLDER


# ========== PDF 提取（多进程 + PyMuPDF主力提取 + OCR备选）==========

def _is_garbage_text(text):
    """
    判断提取的文字是否为乱码/垃圾内容（扫描件误识别）
    返回 True 表示需要走 OCR
    """
    if not text or len(text.strip()) < 5:
        return True

    # 统计中文字符比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text.strip())
    chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0

    # 如果中文字符占比低于 30%，极可能是乱码
    if chinese_ratio < 0.30 and chinese_chars > 0:
        return True

    # 如果全是标点符号或ASCII，也是乱码
    meaningful = len(re.findall(r'[\u4e00-\u9fff}a-zA-Z0-9]', text))
    if meaningful < len(text.strip()) * 0.30:
        return True

    # 如果提取的文字太短（少于20个有意义字符），大概率是扫描件
    if meaningful < 20:
        return True

    return False


def _extract_pdfminer_page(file_path, page_num):
    """
    用 pdfminer.six 提取单页文字（对中文 CID 字体支持更好）
    使用 PDFPageExtractor 避免每次都重新解析整篇 PDF
    """
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
        page_count = 0
        for page_layout in extract_pages(file_path):
            if page_count == page_num:
                texts = []
                for element in page_layout:
                    if isinstance(element, LTTextContainer):
                        t = element.get_text().strip()
                        if t:
                            texts.append(t)
                return "\n".join(texts)
            page_count += 1
    except Exception:
        pass
    return ""


def _extract_pdfminer_full(file_path):
    """
    用 pdfminer.six 一次性提取整篇 PDF 文字
    对中文 CID 字体支持最好
    """
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(file_path)
        if text and text.strip():
            return text.strip()
    except Exception:
        pass
    return ""


def _extract_text_from_page_fitz(page):
    """
    用 PyMuPDF 提取单个页面文字，尝试多种模式取最完整结果
    """
    text = page.get_text("text")
    if text and len(text.strip()) > 10 and not _is_garbage_text(text):
        return text.strip()

    # blocks 模式（更完整，包含表格等）
    blocks_text = page.get_text("blocks")
    if blocks_text:
        lines = []
        for block in blocks_text:
            if len(block) >= 5 and block[4].strip():
                lines.append(block[4].strip())
        if lines:
            combined = "\n".join(lines)
            if not _is_garbage_text(combined) and len(combined) > 20:
                return combined

    # dict 模式
    d = page.get_text("dict")
    if d and "blocks" in d:
        parts = []
        for block in d["blocks"]:
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        t = span.get("text", "").strip()
                        if t:
                            parts.append(t)
        if parts:
            combined = "\n".join(parts)
            if not _is_garbage_text(combined) and len(combined) > 20:
                return combined

    return text.strip() if text and not _is_garbage_text(text) else ""


def _pdf_page_worker(args):
    """
    子进程：提取单个 PDF 页面文字
    策略：pdfminer.six（中文最强） -> PyMuPDF 多模式 -> OCR
    返回 (page_num, text, need_ocr)
    """
    file_path, page_num = args
    try:
        import fitz

        # 策略1：pdfminer.six（对中文 CID 字体支持最强）
        text = _extract_pdfminer_page(file_path, page_num)
        if text and len(text) > 5 and not _is_garbage_text(text):
            return (page_num, text, False)

        # 策略2：PyMuPDF 多模式
        doc = fitz.open(file_path)
        page = doc[page_num]
        text = _extract_text_from_page_fitz(page)
        doc.close()
        if text and len(text) > 5 and not _is_garbage_text(text):
            return (page_num, text, False)

        # 策略3：OCR兜底（扫描件）
        return (page_num, None, True)

    except Exception:
        return (page_num, None, True)


def _ocr_pdf_page_worker(args):
    """
    对单个 PDF 页面进行 OCR 识别（GPU 加速版）
    使用全局 OCR 实例 + 线程锁保证线程安全
    """
    file_path, page_num = args
    tmp_img = None
    try:
        import fitz

        # 用 PyMuPDF 把 PDF 页面转成图片
        doc = fitz.open(file_path)
        page = doc[page_num]
        mat = fitz.Matrix(2, 2)  # 2x2 倍率，提高清晰度
        pix = page.get_pixmap(matrix=mat)
        tmp_img = f"_tmp_p{page_num}_{os.getpid()}.png"
        pix.save(tmp_img)
        doc.close()

        # 调用 OCR 服务（内部使用 GPU 加速）
        from services.ocr_service import ocr_image
        text = ocr_image(tmp_img)
        return (page_num, text)
    except Exception:
        return (page_num, "")
    finally:
        if tmp_img and os.path.exists(tmp_img):
            try: os.remove(tmp_img)
            except Exception: pass


def extract_text_from_pdf(file_path, file_id=None):
    """
    PDF 提取文字（多进程加速）
    策略：pdfminer.six 主提取 -> PyMuPDF 补漏 -> 并行 OCR 兜底（扫描件）
    """
    try:
        import fitz
        from progress_store import set_progress
        # OCR 可用性检查：失败时不阻塞普通文本 PDF 的提取
        is_gpu = False
        ocr_available = False
        try:
            from services.ocr_service import is_gpu_available
            is_gpu = is_gpu_available()
            ocr_available = True
        except Exception as ocr_err:
            print(f"[OCR] 当前不可用，仅使用文本提取策略：{ocr_err}")

        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()
        if total_pages == 0:
            return ""

        # 先用 pdfminer.six 整体提取（对中文最有效）
        if file_id is not None:
            set_progress(file_id, 100, 5, "提取文字...")
        full_text = _extract_pdfminer_full(file_path)

        if full_text and len(full_text.strip()) > 20 and not _is_garbage_text(full_text):
            # pdfminer 提取成功且内容质量好，直接使用
            if file_id is not None:
                set_progress(file_id, 100, 80, "清洗数据...")
            if file_id is not None:
                set_progress(file_id, 100, 100, "解析完成")
            return full_text

        # pdfminer 不够（内容太少或质量差），用多进程逐页提取 + OCR兜底
        max_workers = min(cpu_count(), total_pages, 8)

        pages_text = {}
        pages_need_ocr = []

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_pdf_page_worker, (file_path, i)): i
                for i in range(total_pages)
            }
            for future in as_completed(futures):
                page_num, text, need_ocr = future.result()
                if need_ocr:
                    pages_need_ocr.append(page_num)
                else:
                    pages_text[page_num] = text
                if file_id is not None:
                    done_count = len(pages_text) + len(pages_need_ocr)
                    pct = int(done_count / total_pages * 50)
                    set_progress(file_id, 100, pct, f"提取第 {done_count}/{total_pages} 页")

        # 并行 OCR 无文字页面（扫描件走这里）
        # GPU 加速：用线程池代替进程池，GPU 共享资源更适合多线程
        if pages_need_ocr and ocr_available:
            ocr_total = len(pages_need_ocr)
            ocr_done = 0
            # GPU 模式下用更多线程并行 OCR
            max_ocr_workers = min(cpu_count() * 2, ocr_total, 16) if is_gpu else min(cpu_count(), ocr_total, 8)
            with ThreadPoolExecutor(max_workers=max_ocr_workers) as executor:
                futures = {
                    executor.submit(_ocr_pdf_page_worker, (file_path, p)): p
                    for p in pages_need_ocr
                }
                for future in as_completed(futures):
                    page_num, text = future.result()
                    ocr_done += 1
                    pages_text[page_num] = text if text else ""
                    if file_id is not None:
                        pct = 50 + int(ocr_done / ocr_total * 50)
                        set_progress(file_id, 100, pct, f"OCR识别 {ocr_done}/{ocr_total} 页")
        elif pages_need_ocr and not ocr_available:
            # OCR 不可用时，这些页无法识别，保留为空，后续统一给出清晰错误
            for p in pages_need_ocr:
                pages_text[p] = pages_text.get(p, "")

        # 按顺序拼接
        parts = []
        for i in range(total_pages):
            text = pages_text.get(i, "")
            if text and text.strip():
                parts.append(f"## 第 {i+1} 页\n{text.strip()}")
        result = "\n\n".join(parts) if parts else ""

        if not result.strip() and pages_need_ocr and not ocr_available:
            raise Exception("PDF 解析失败：当前环境缺少 OCR 依赖（paddle/paddleocr），且该 PDF 需要 OCR 才能识别内容")

        if file_id is not None:
            set_progress(file_id, 100, 100, "解析完成")
        return result

    except Exception as e:
        if file_id is not None:
            from progress_store import set_progress
            set_progress(file_id, 100, 100, "解析失败")
        raise Exception(f"PDF 解析失败：{str(e)}")


# ========== Word (docx) 提取（保留格式和图片）==========

def _extract_run_text(run, paragraph_style):
    """
    提取单个文本片段（run）的格式化文本
    返回 Markdown 格式字符串
    """
    text = run.text if run.text else ""
    if not text:
        return ""

    bold = getattr(run, "bold", False)
    italic = getattr(run, "italic", False)
    underline = getattr(run, "underline", False)
    strike = getattr(run, "strike", False)

    # 加粗 + 斜体组合
    if bold and italic:
        text = f"***{text}***"
    elif bold:
        text = f"**{text}**"
    elif italic:
        text = f"*{text}*"
    if underline:
        text = f"<u>{text}</u>"

    return text


def extract_text_from_docx(file_path, output_base_dir=None):
    """
    从 Word 文档提取内容，保留标题层级、加粗、斜体、列表、图片
    图片保存到 outputs 目录，Markdown 中用相对路径引用

    参数：
        file_path: docx 文件路径
        output_base_dir: 图片保存目录（默认与 docx 同目录的 outputs 下）
    """
    try:
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

        doc = Document(file_path)

        # 设置图片保存目录
        if output_base_dir:
            img_dir = output_base_dir
        else:
            # 提取文件名（不含扩展名）作为图片目录名
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            img_dir = os.path.join(OUTPUT_FOLDER, base_name, "images")
        os.makedirs(img_dir, exist_ok=True)

        result_parts = []

        # 提取文档中的图片
        extracted_images = {}  # rId -> (saved_filename, full_path)
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    img_data = rel.target_part.blob
                    img_ext = rel.target_ref.split(".")[-1].lower()
                    if img_ext not in ["png", "jpg", "jpeg", "gif", "bmp", "webp"]:
                        img_ext = "png"
                    img_name = f"{uuid.uuid4().hex[:12]}.{img_ext}"
                    img_path = os.path.join(img_dir, img_name)
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    extracted_images[rel.rId] = (img_name, img_path.replace("\\", "/"))
                except Exception as img_err:
                    print(f"[docx图片提取失败] {img_err}")

        # 提取正文段落
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            style_name = para.style.name.lower() if para.style else ""

            # 判断标题级别
            if "heading 1" in style_name or "标题 1" in style_name:
                result_parts.append(f"# {text}")
            elif "heading 2" in style_name or "标题 2" in style_name:
                result_parts.append(f"## {text}")
            elif "heading 3" in style_name or "标题 3" in style_name:
                result_parts.append(f"### {text}")
            elif "heading 4" in style_name or "标题 4" in style_name:
                result_parts.append(f"#### {text}")
            elif "title" in style_name:
                result_parts.append(f"# {text}")
            # 列表项
            elif para.style and ("List" in para.style.name or "列表" in para.style.name or "Numbering" in para.style.name):
                num_pr = para._element.find('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr')
                if num_pr is not None:
                    result_parts.append(f"- {text}")
                else:
                    result_parts.append(f"- {text}")
            else:
                # 普通段落，遍历每个 run 保留格式
                runs_text = []
                for run in para.runs:
                    run_text = run.text if run.text else ""
                    if not run_text:
                        continue
                    bold = getattr(run, "bold", False)
                    italic = getattr(run, "italic", False)
                    underline = getattr(run, "underline", False)

                    if bold and italic:
                        run_text = f"***{run_text}***"
                    elif bold:
                        run_text = f"**{run_text}**"
                    elif italic:
                        run_text = f"*{run_text}*"

                    runs_text.append(run_text)

                para_text = "".join(runs_text) if runs_text else text
                if para_text.strip():
                    result_parts.append(para_text)

        # 提取表格
        for table in doc.tables:
            table_rows = []
            for row_idx, row in enumerate(table.rows):
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    if row_idx == 0:
                        table_rows.append("| " + " | ".join(cells) + " |")
                        table_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
                    else:
                        table_rows.append("| " + " | ".join(cells) + " |")
            if table_rows:
                result_parts.append("\n".join(table_rows))

        return "\n\n".join(result_parts)

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Word 文档解析失败：{str(e)}")


# ========== Excel 提取 ==========

def extract_text_from_xlsx(file_path):
    """Excel 提取，输出 Markdown 表格"""
    try:
        import openpyxl

        wb = openpyxl.load_workbook(file_path, data_only=True)
        all_sheets = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows_data = []
            for row in ws.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    row_cells = [str(cell) if cell is not None else "" for cell in row]
                    rows_data.append(row_cells)

            if rows_data:
                lines = [f"### 工作表：{sheet_name}\n"]
                for i, row in enumerate(rows_data):
                    if i == 0:
                        lines.append("| " + " | ".join(row) + " |")
                        lines.append("| " + " | ".join(["---"] * len(row)) + " |")
                    else:
                        lines.append("| " + " | ".join(row) + " |")
                all_sheets.append("\n".join(lines))

        return "\n\n".join(all_sheets)

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"Excel 文件解析失败：{str(e)}")


# ========== Markdown 读取 ==========

def extract_text_from_markdown(file_path):
    """读取 Markdown 文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Markdown 文件读取失败：{str(e)}")


# ========== 图片 OCR ==========

def extract_text_from_image(file_path):
    """图片 OCR 文字识别"""
    from services.ocr_service import ocr_image
    return ocr_image(file_path)


# ========== 统一入口 ==========

def extract_text(file_path, file_ext, file_id=None):
    """
    根据文件扩展名，自动选择提取方法

    参数：
        file_path: 文件绝对路径
        file_ext: 文件扩展名（小写，不带点）
        file_id: 文件ID，用于进度上报（仅 PDF 支持详细进度）
    """
    extractors = {
        "pdf": lambda fp: extract_text_from_pdf(fp, file_id=file_id),
        "docx": lambda fp: _docx_with_progress(fp, file_id),
        "xlsx": lambda fp: _xlsx_with_progress(fp, file_id),
        "md": extract_text_from_markdown,
        "png": lambda fp: _image_with_progress(fp, file_id),
        "jpg": lambda fp: _image_with_progress(fp, file_id),
        "jpeg": lambda fp: _image_with_progress(fp, file_id),
        "jfif": lambda fp: _image_with_progress(fp, file_id),
        "gif": lambda fp: _image_with_progress(fp, file_id),
        "bmp": lambda fp: _image_with_progress(fp, file_id),
        "webp": lambda fp: _image_with_progress(fp, file_id),
    }

    extractor = extractors.get(file_ext.lower())
    if not extractor:
        raise Exception(f"不支持的文件格式：.{file_ext}")

    return extractor(file_path)


def _docx_with_progress(file_path, file_id):
    """docx 带进度上报"""
    from progress_store import set_progress
    if file_id is not None:
        set_progress(file_id, 100, 30, "解析 Word 文档...")
    result = extract_text_from_docx(file_path)
    if file_id is not None:
        set_progress(file_id, 100, 80, "处理完成")
    return result


def _xlsx_with_progress(file_path, file_id):
    """xlsx 带进度上报"""
    from progress_store import set_progress
    if file_id is not None:
        set_progress(file_id, 100, 50, "解析 Excel...")
    result = extract_text_from_xlsx(file_path)
    if file_id is not None:
        set_progress(file_id, 100, 90, "处理完成")
    return result


def _image_with_progress(file_path, file_id):
    """图片 OCR 带进度上报"""
    from progress_store import set_progress
    if file_id is not None:
        set_progress(file_id, 100, 20, "OCR 识别中...")
    result = extract_text_from_image(file_path)
    if file_id is not None:
        set_progress(file_id, 100, 90, "识别完成")
    return result
