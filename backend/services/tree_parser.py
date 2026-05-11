# -*- coding: utf-8 -*-
"""
树结构解析服务
将 Markdown 内容解析为树形结构（节点：标题/页码/摘要）
支持 PDF 格式（## 第 N 页）、Markdown 格式（# 标题层级）
"""
import re
import uuid


def classify_document_with_llm(md_content, file_name=""):
    """
    调用 MiniMax LLM 对文档进行 AI 分类。
    返回 {"doc_type": "...", "doc_category": "...", "description": "..."}
    LLM 未配置或调用失败时返回 None。
    """
    import os
    import sys
    import json
    import urllib.request

    # 动态引入 config_manager（services 目录的上级 backend 目录）
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    try:
        from config_manager import get_config, is_llm_enabled
    except ImportError:
        return None

    if not is_llm_enabled():
        return None

    config = get_config()
    api_key = config.get("api_key", "").strip()
    if not api_key:
        return None

    # 取前 5000 字作为文档样本（内容越多判断越准）
    sample = md_content[:5000].strip()
    if not sample:
        return None

    prompt = (
        "你是一个文档语义分析专家。请仔细阅读下方文档内容，从**文档的用途和本质**判断它属于哪种类型。\n\n"
        "【判断标准（按用途，不按格式）】\n"
        "- knowledge_doc：这份文档是为了「让人学习和理解某个领域知识」写的。\n"
        "  典型特征：有概念解释、有原理说明、有方法论、读者是学习者。\n"
        "  例：技术文档、行业知识库、教程、百科类文章。\n\n"
        "- report：这份文档是为了「汇报某件事的结果或分析」写的。\n"
        "  典型特征：有结论、有数据支撑、有时间周期、有分析对象。\n"
        "  例：调研报告、项目复盘、市场分析、业绩总结。\n\n"
        "- log：这份文档是为了「记录发生过什么事情/状态变化」写的。\n"
        "  典型特征：按时间或事件排列、记录状态/进展/问题、没有结论导向。\n"
        "  例：工作日志、运营记录、变更日志、执行状态表。\n\n"
        "- readme：这份文档是为了「告诉用户怎么使用某个工具/项目/系统」写的。\n"
        "  典型特征：有安装步骤、有使用说明、有接口描述、面向使用者。\n"
        "  例：软件 README、部署手册、API 文档、使用指南。\n\n"
        "- data_table：这份文档的核心内容是「结构化的数据或表格」，文字只是辅助。\n"
        "  典型特征：大量表格/数字/字段名、行列关系、数据驱动。\n"
        "  例：价格表、产品参数对比、数据报表、配置清单。\n\n"
        "- general：以上类型都不明显符合，或者内容混杂无主导用途。\n\n"
        "【严格要求】\n"
        "1. 只看内容本质，不要被文件名或格式迷惑（.md 文件也可以是报告或日志）。\n"
        "2. 选且只选一个最符合「主要用途」的类型。\n"
        "3. doc_category 写这份文档所属的业务/技术领域，最多6个中文字，不要写类型名。\n"
        "4. description 用一句话说清楚「这份文档具体讲什么」，最多25个字。\n\n"
        f"【文件名】{file_name or '未知'}\n\n"
        f"【文档内容节选】\n{sample}\n\n"
        "---\n"
        "只返回如下 JSON，不要任何其他文字：\n"
        '{{"doc_type": "<类型>", "doc_category": "<领域>", "description": "<一句话简介>"}}'
    )

    try:
        # 构造 API URL
        api_base = config.get("api_base", "https://api.minimax.chat/v1").rstrip("/")
        if "/chat/completions" in api_base:
            url = api_base
        elif api_base.endswith("/v1"):
            url = api_base + "/chat/completions"
        else:
            url = api_base + "/v1/chat/completions"

        payload = {
            "model": config.get("model", "MiniMax-M2.7"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 2000   # 推理模型 <think> 标签会消耗大量 token，必须留足空间
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            choices = result.get("choices", [])
            if not choices:
                return None
            content = choices[0].get("message", {}).get("content", "").strip()

        # 第1步：去掉 MiniMax 推理模型的 <think>...</think> 标签
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        # 第2步：去掉可能的 ```json ... ``` 代码块包裹
        content = re.sub(r'^```[a-zA-Z]*\s*', '', content)
        content = re.sub(r'\s*```$', '', content).strip()
        # 第3步：从任意位置提取第一个完整 JSON 对象（最稳健）
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if not json_match:
            return None
        content = json_match.group(0)

        classification = json.loads(content)
        # 校验 doc_type 合法性
        valid_types = {'knowledge_doc', 'report', 'log', 'readme', 'data_table', 'general'}
        doc_type = str(classification.get('doc_type', 'general'))
        if doc_type not in valid_types:
            doc_type = 'general'
        return {
            'doc_type': doc_type,
            'doc_category': str(classification.get('doc_category', ''))[:10],
            'description': str(classification.get('description', ''))[:40]
        }
    except Exception:
        # LLM 调用失败时静默忽略，不影响主流程
        return None


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

    root = {
        "id": "root",
        "title": file_name or "文档",
        "type": "root",
        "children": nodes
    }

    # AI 分类：调用 LLM 识别文档类型（失败时静默忽略）
    classification = classify_document_with_llm(md_content, file_name)
    if classification:
        root["doc_type"] = classification["doc_type"]
        root["doc_category"] = classification["doc_category"]
        root["description"] = classification["description"]

    return root


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
