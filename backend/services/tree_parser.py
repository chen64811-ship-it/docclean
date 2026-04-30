# -*- coding: utf-8 -*-
"""
树结构解析服务
将 Markdown 内容解析为树形结构（节点：标题/页码/摘要）
支持 PDF 格式（## 第 N 页）、Markdown 格式（# 标题层级）
"""
import re
import uuid


def parse_markdown_to_tree(md_content, file_name=""):
    """
    将 Markdown 内容解析为树结构

    返回：
    {
        "id": "root",
        "title": 文件名,
        "type": "root",
        "children": [
            {
                "id": "node_xxx",
                "title": "第1页 / 第一章",
                "type": "chapter|page",
                "page_range": "1-3",
                "page_start": 1,
                "page_end": 3,
                "summary": "本节摘要...",
                "content_preview": "前200字...",
                "children": []
            }
        ]
    }
    """
    if not md_content:
        return _empty_tree(file_name)

    lines = md_content.split('\n')
    nodes = []
    current_node = None
    node_counter = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 检测 PDF 页码标记：## 第 N 页
        page_match = re.match(r'^##\s*第\s*(\d+)\s*页', stripped)
        # 检测 Markdown 标题：# 标题
        heading_match = re.match(r'^(#{1,4})\s+(.+)', stripped)

        if page_match:
            page_num = int(page_match.group(1))
            # 收集该页的内容（去掉标题行）
            page_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                next_page = re.match(r'^##\s*第\s*(\d+)\s*页', next_line)
                next_heading = re.match(r'^#{1,3}\s+', next_line)
                if next_page or next_heading:
                    break
                page_lines.append(lines[j])
                j += 1

            page_text = '\n'.join(page_lines).strip()
            node_counter += 1
            node_id = f"page_{page_num}"

            # 计算该页结束页码（找相邻页码）
            end_page = page_num
            k = j
            while k < len(lines):
                nm = re.match(r'^##\s*第\s*(\d+)\s*页', lines[k].strip())
                if nm:
                    end_page = int(nm.group(1)) - 1
                    break
                k += 1

            node = {
                "id": node_id,
                "title": f"第 {page_num} 页",
                "type": "page",
                "page_start": page_num,
                "page_end": max(page_num, end_page),
                "page_range": f"{page_num}-{max(page_num, end_page)}",
                "summary": _make_summary(page_text),
                "content_preview": page_text[:300] if page_text else "",
                "children": []
            }
            nodes.append(node)
            i = j
            continue

        elif heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            # 收集该章节内容
            section_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                next_h = re.match(r'^#+\s+', next_line)
                if next_h and len(next_h.group()) <= level:
                    break
                section_lines.append(lines[j])
                j += 1

            section_text = '\n'.join(section_lines).strip()
            node_counter += 1
            node = {
                "id": f"heading_{node_counter}",
                "title": title,
                "type": "heading",
                "level": level,
                "page_range": _guess_page_range(lines, i),
                "page_start": 0,
                "page_end": 0,
                "summary": _make_summary(section_text),
                "content_preview": section_text[:300] if section_text else "",
                "children": []
            }

            # 根据标题级别决定插入位置
            if level == 1:
                nodes.append(node)
            elif level == 2 and nodes:
                nodes[-1].setdefault("children", []).append(node)
            elif level == 3 and nodes:
                last = _find_last_with_children(nodes)
                if last:
                    last.setdefault("children", []).append(node)
            else:
                nodes.append(node)

            i = j
            continue

        i += 1

    # 如果没有任何节点（纯文本），按固定行数分块
    if not nodes:
        nodes = _chunk_by_lines(lines, lines_per_chunk=100)

    return {
        "id": "root",
        "title": file_name or "文档",
        "type": "root",
        "children": nodes
    }


def _empty_tree(file_name):
    return {
        "id": "root",
        "title": file_name or "文档",
        "type": "root",
        "children": []
    }


def _make_summary(text, max_len=150):
    """
    生成内容摘要：取前 max_len 个有意义的字符
    """
    if not text:
        return ""
    # 去掉多余空白
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + '...'


def _guess_page_range(all_lines, heading_line_idx):
    """
    根据标题附近是否出现 "第 N 页" 来推断页码范围
    """
    context = '\n'.join(all_lines[max(0, heading_line_idx - 5):heading_line_idx + 20])
    pages = re.findall(r'第\s*(\d+)\s*页', context)
    if pages:
        return f"{pages[0]}-{pages[-1]}"
    return ""


def _find_last_with_children(nodes):
    """
    从后往前找有 children 的节点
    """
    for i in range(len(nodes) - 1, -1, -1):
        if nodes[i].get("children"):
            return nodes[i]
    return None


def _chunk_by_lines(lines, lines_per_chunk=100):
    """
    纯文本没有结构时，按固定行数分块
    """
    chunks = []
    total = len(lines)
    for start in range(0, total, lines_per_chunk):
        end = min(start + lines_per_chunk, total)
        chunk_lines = lines[start:end]
        chunk_text = '\n'.join(chunk_lines)
        page_num = _find_page_num(chunk_lines)
        chunks.append({
            "id": f"chunk_{start // lines_per_chunk + 1}",
            "title": f"第 {start // lines_per_chunk + 1} 节" if page_num is None else f"第 {page_num} 页",
            "type": "chunk",
            "page_start": page_num or (start // lines_per_chunk + 1),
            "page_end": page_num or (end // lines_per_chunk + 1),
            "page_range": str(page_num) if page_num else f"{start // lines_per_chunk + 1}-{end // lines_per_chunk + 1}",
            "summary": _make_summary(chunk_text),
            "content_preview": chunk_text[:300] if chunk_text else "",
            "children": []
        })
    return chunks


def _find_page_num(chunk_lines):
    """从块中找到第一个页码"""
    for line in chunk_lines:
        m = re.match(r'^##\s*第\s*(\d+)\s*页', line.strip())
        if m:
            return int(m.group(1))
    return None
