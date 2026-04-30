# -*- coding: utf-8 -*-
"""
Markdown → PDF 导出服务
使用 fpdf2 直接渲染，读取 Windows 系统微软雅黑字体，不依赖任何外部系统库
"""
import re
import os
from io import BytesIO


# ──────────────────────────────────────────────
# 查找微软雅黑字体路径（Windows 系统自带）
# ──────────────────────────────────────────────
def _find_msyh():
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\MSYH.TTC",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\MSYH.TTF",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


# ──────────────────────────────────────────────
# 去除行内 Markdown 标记，返回纯文本
# ──────────────────────────────────────────────
def _clean(s):
    s = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', s)   # 粗斜体
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)         # 粗体
    s = re.sub(r'__(.+?)__', r'\1', s)             # 粗体（下划线）
    s = re.sub(r'\*(.+?)\*', r'\1', s)             # 斜体
    s = re.sub(r'_(.+?)_', r'\1', s)               # 斜体（下划线）
    s = re.sub(r'`(.+?)`', r'\1', s)               # 行内代码
    s = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', s)      # 链接
    s = re.sub(r'~~(.+?)~~', r'\1', s)             # 删除线
    s = re.sub(r'!\[.+?\]\(.+?\)', '', s)          # 图片（忽略）
    return s.strip()


# ──────────────────────────────────────────────
# 主函数：Markdown → PDF 字节流
# ──────────────────────────────────────────────
def markdown_to_pdf(md_text, title=None):
    """
    将 Markdown 字符串转为 PDF，返回 bytes 字节流。
    支持：H1-H6、段落、无序/有序列表、嵌套列表、代码块、表格、引用、分隔线
    """
    from fpdf import FPDF

    # ── 初始化 PDF ──
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(left=20, top=20, right=20)
    pdf.set_auto_page_break(auto=True, margin=22)

    # ── 注册微软雅黑字体 ──
    font_path = _find_msyh()
    if font_path:
        try:
            pdf.add_font('msyh', style='', fname=font_path)
            pdf.add_font('msyh', style='B', fname=font_path)
            FONT = 'msyh'
        except Exception:
            FONT = 'helvetica'
    else:
        FONT = 'helvetica'

    PAGE_W = 170  # A4(210mm) - 左右边距各20mm

    pdf.add_page()

    # ── 辅助函数 ──
    def write_text(text, size=11, bold=False, indent=0, lh=7, fill=False, fill_color=None):
        """写一段文字（支持自动换行）"""
        style = 'B' if bold else ''
        pdf.set_font(FONT, style, size)
        if fill and fill_color:
            pdf.set_fill_color(*fill_color)
        pdf.set_x(20 + indent)
        pdf.multi_cell(
            w=PAGE_W - indent,
            h=lh,
            txt=_clean(text),
            fill=fill,
        )

    def write_heading(text, level):
        cfg = {
            1: (20, 11, True),
            2: (16, 9, True),
            3: (14, 8, True),
            4: (12, 7, True),
            5: (11, 7, True),
            6: (11, 6, False),
        }
        size, lh, bold = cfg.get(level, (11, 7, False))
        pdf.ln(3 if level <= 2 else 2)
        write_text(text, size=size, bold=bold, lh=lh)
        if level == 1:
            # H1 下方画一条浅线
            pdf.set_draw_color(102, 126, 234)
            pdf.set_line_width(0.4)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.set_line_width(0.2)
            pdf.set_draw_color(0, 0, 0)
        pdf.ln(1)

    def write_table(t_lines):
        """渲染 Markdown 表格"""
        rows = []
        for tl in t_lines:
            stripped = tl.strip()
            # 跳过分隔行 |---|---|
            if re.match(r'^\|[\s\-|:]+\|$', stripped):
                continue
            cells = [_clean(c.strip()) for c in stripped.strip('|').split('|')]
            rows.append(cells)
        if not rows:
            return

        n_cols = max(len(r) for r in rows)
        col_w = PAGE_W / n_cols

        for ri, row in enumerate(rows):
            # 计算本行最大行高（内容最多的单元格）
            is_header = (ri == 0)
            pdf.set_font(FONT, 'B' if is_header else '', 10)
            row_h = 7

            x_start = 20
            y_start = pdf.get_y()

            # 检查是否接近页底，提前换页
            if y_start + row_h > pdf.h - 22:
                pdf.add_page()
                y_start = pdf.get_y()

            for ci in range(n_cols):
                cell_text = row[ci] if ci < len(row) else ''
                pdf.set_xy(x_start + ci * col_w, y_start)
                pdf.set_fill_color(230, 234, 255) if is_header else pdf.set_fill_color(255, 255, 255)
                pdf.cell(col_w, row_h, cell_text[:40], border=1, fill=True)

            pdf.set_xy(x_start, y_start + row_h)

        pdf.ln(4)

    def write_code_block(code_lines):
        """渲染代码块"""
        if not code_lines:
            return
        pdf.set_font(FONT, '', 9)
        pdf.set_fill_color(248, 249, 255)
        content = '\n'.join(code_lines)
        # 每行单独写，保证不裁剪
        for cl in code_lines:
            pdf.set_x(22)
            pdf.set_fill_color(248, 249, 255)
            pdf.multi_cell(PAGE_W - 4, 5.5, cl, fill=True)
        pdf.ln(2)

    # ── 逐行解析 ──
    lines = md_text.split('\n')
    i = 0
    in_code = False
    code_lines = []

    while i < len(lines):
        line = lines[i]

        # 代码围栏
        if re.match(r'^```', line):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                write_code_block(code_lines)
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        stripped = line.strip()

        # 表格（收集连续的表格行）
        if stripped.startswith('|'):
            t_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                t_lines.append(lines[i])
                i += 1
            write_table(t_lines)
            continue

        # 空行
        if not stripped:
            pdf.ln(3)
            i += 1
            continue

        # 分隔线
        if re.match(r'^[-*_]{3,}$', stripped):
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.3)
            pdf.line(20, pdf.get_y() + 2, 190, pdf.get_y() + 2)
            pdf.ln(5)
            pdf.set_line_width(0.2)
            pdf.set_draw_color(0, 0, 0)
            i += 1
            continue

        # 标题
        m = re.match(r'^(#{1,6})\s+(.*)', stripped)
        if m:
            level = len(m.group(1))
            write_heading(m.group(2), level)
            i += 1
            continue

        # 引用块
        if stripped.startswith('> '):
            y0 = pdf.get_y()
            write_text(stripped[2:], size=11, indent=8, fill=True, fill_color=(248, 249, 255))
            y1 = pdf.get_y()
            pdf.set_draw_color(102, 126, 234)
            pdf.set_line_width(0.8)
            pdf.line(21, y0, 21, y1)
            pdf.set_line_width(0.2)
            pdf.set_draw_color(0, 0, 0)
            i += 1
            continue

        # 无序列表（支持 -, *, +）
        m = re.match(r'^(\s*)([-*+])\s+(.*)', line)
        if m:
            indent_lvl = len(m.group(1)) // 2
            bullet = '•' if indent_lvl == 0 else ('◦' if indent_lvl == 1 else '▪')
            write_text(f'{bullet} {m.group(3)}', size=11, indent=5 + indent_lvl * 5)
            i += 1
            continue

        # 有序列表
        m = re.match(r'^(\s*)(\d+)[.)]\s+(.*)', line)
        if m:
            indent_lvl = len(m.group(1)) // 2
            write_text(f'{m.group(2)}. {m.group(3)}', size=11, indent=5 + indent_lvl * 5)
            i += 1
            continue

        # 普通段落
        write_text(stripped, size=11)
        i += 1

    # ── 输出字节流 ──
    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf.read()
