# -*- coding: utf-8 -*-
"""
Excel 大纲 + LLM 智能分类服务
功能：
1. 读取《餐饮全景运营知识库.xlsx》得到目标分类结构
2. 把 Markdown 内容按段落切块（约 500-800 字/块）
3. 调用 LLM 把每块内容映射到 Excel 分类
4. 组装成结构化 JSON 树
"""
import re
import json
import os
import urllib.request
import urllib.error
from config_manager import get_config, is_llm_enabled


# ============================================================
# 1. 读取 Excel 大纲
# ============================================================

def load_excel_outline(excel_path=None):
    """
    读取 Excel 文件，返回大纲结构（用于给 LLM 分类）
    返回 dict: { outline_text: str, categories: list[dict] }
    categories 里每个元素: { code, name, keywords, level }
    """
    if excel_path is None:
        # 从 backend/services/excel_classifier.py，往上三层到 vip/
        _vip_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        excel_path = os.path.join(_vip_dir, "餐饮全景运营知识库.xlsx")

    if not os.path.exists(excel_path):
        return None

    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))

        # 第一行是标题
        categories = []
        for row in rows[2:]:  # 跳过标题行（第1、2行）
            if not row or not any(cell for cell in row):
                continue
            level = row[0]  # L1 / L2
            code = row[1]   # L1, L1.1 等
            name = row[2]   # 节点名称
            parent = row[3]  # 父节点
            keywords = row[4] if len(row) > 4 else ""  # 关键词

            if not code or not name:
                continue

            categories.append({
                "level": str(level or "").strip(),
                "code": str(code or "").strip(),
                "name": str(name or "").strip(),
                "parent": str(parent or "").strip(),
                "keywords": str(keywords or "").strip()
            })

        # 构建层级树（L1 是根分类，L2 是子分类）
        l1_list = [c for c in categories if c["level"] == "L1"]
        l2_map = {}
        for c in categories:
            if c["level"] == "L2":
                parent_code = c["parent"]
                if parent_code not in l2_map:
                    l2_map[parent_code] = []
                l2_map[parent_code].append(c)

        # 生成供 LLM 阅读的分类文本
        outline_lines = []
        for l1 in l1_list:
            outline_lines.append(f"【{l1['code']}】{l1['name']}（关键词：{l1['keywords']}）")
            children = l2_map.get(l1["code"], [])
            for l2 in children:
                outline_lines.append(f"  - 【{l2['code']}】{l2['name']}（关键词：{l2['keywords']}）")

        outline_text = "\n".join(outline_lines)
        return {
            "outline_text": outline_text,
            "categories": categories,
            "l1_list": l1_list,
            "l2_map": l2_map
        }

    except Exception as e:
        print(f"[excel_classifier] 读取 Excel 失败: {e}")
        return None


# ============================================================
# 2. 切块（粗暴按段落切，约 600 字一块）
# ============================================================

def chunk_markdown(md_content, chunk_size=600, overlap=50):
    """
    把 Markdown 内容切成若干块。
    - 优先按自然段落切（两个换行之间）
    - 每块约 chunk_size 个中文字符
    - 返回 list[dict]: { chunk_id, content, char_count }
    """
    if not md_content:
        return []

    # 先把 Markdown 里的多余空行合并
    md_content = re.sub(r'\n{3,}', '\n\n', md_content)
    # 去掉页眉页脚干扰词
    junk_patterns = [
        r'加微信[^\n]*',
        r'请关注[^\n]*',
        r'扫码[^\n]*',
        r'版权声明[^\n]*',
        r'http\S+',
    ]
    for pat in junk_patterns:
        md_content = re.sub(pat, '', md_content)

    # 按段落分割
    paragraphs = re.split(r'\n\n+', md_content)
    chunks = []
    current = []
    current_len = 0
    chunk_id = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = len(para)
        # 如果单段落超长，继续拆
        if para_len > chunk_size * 1.5:
            # 把超长段落拆成句子
            sentences = re.split(r'(?<=[。！？；\n])', para)
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if current_len + len(sent) > chunk_size and current:
                    chunks.append({
                        "chunk_id": f"chunk_{chunk_id}",
                        "content": "\n".join(current).strip(),
                        "char_count": current_len
                    })
                    chunk_id += 1
                    # overlap：保留最后一句作为下一块开头
                    if overlap > 0 and current:
                        overlap_text = current[-1][-overlap:]
                        current = [overlap_text]
                        current_len = len(overlap_text)
                    else:
                        current = []
                        current_len = 0
                current.append(sent)
                current_len += len(sent)
        elif current_len + para_len > chunk_size and current:
            chunks.append({
                "chunk_id": f"chunk_{chunk_id}",
                "content": "\n".join(current).strip(),
                "char_count": current_len
            })
            chunk_id += 1
            # overlap
            if overlap > 0 and current:
                overlap_text = current[-1][-overlap:]
                current = [overlap_text]
                current_len = len(overlap_text)
            else:
                current = []
                current_len = 0
            current.append(para)
            current_len += para_len
        else:
            current.append(para)
            current_len += para_len

    # 最后一块
    if current:
        chunks.append({
            "chunk_id": f"chunk_{chunk_id}",
            "content": "\n".join(current).strip(),
            "char_count": current_len
        })

    return chunks


# ============================================================
# 3. LLM 分类（批量调用，避免多次请求）
# ============================================================

def _get_llm_url(config):
    """构造 LLM 接口 URL"""
    api_base = config.get("api_base", "https://api.minimax.chat/v1").rstrip("/")
    if any(x in api_base for x in ["/chat/completions"]):
        return api_base
    if api_base.endswith("/v1"):
        return api_base + "/chat/completions"
    return api_base + "/v1/chat/completions"


def _classify_single_chunk(chunk_text, outline_text, config):
    """
    把单个 chunk 发给 LLM，返回分类结果。
    返回: { l1_code, l1_name, l2_code, l2_name, reason, discard }
    如果 LLM 不可用或出错，返回 None
    """
    prompt = f"""你是知识库分类助手。请判断以下文本片段属于哪个分类。

【Excel 分类大纲】：
{outline_text}

【文本片段】（约 {len(chunk_text)} 字）：
---
{chunk_text[:1200]}
---

请用 JSON 格式返回分类结果（不要返回其他内容）：
{{
  "l1_code": "L1的编号，如 L1",
  "l1_name": "L1的完整名称",
  "l2_code": "L2的编号，如 L1.1（最匹配的一个子分类）",
  "l2_name": "L2的完整名称",
  "reason": "一句话说明为什么归到此类",
  "discard": false,
  "confidence": 0.85
}}

注意：
- 如果文本片段全是广告、版权信息、空白等无意义内容，discard 设为 true
- confidence 表示匹配置信度（0-1），低于 0.4 的设为 discard: true
- 只需返回 JSON，不要有任何其他文字
"""

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 300
            }

            req = urllib.request.Request(
                _get_llm_url(config),
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + config.get("api_key", "")
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    raw = choices[0].get("message", {}).get("content", "").strip()
                    # 提取 JSON（可能包裹在 ```json 里）
                    m = re.search(r'\{[\s\S]*\}', raw)
                    if m:
                        return json.loads(m.group())
        except Exception as e:
            print(f"[excel_classifier] LLM 调用失败 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                wait = 3 * (3 ** attempt)  # 指数退避：3s → 9s → 27s
                print(f"  → {wait}秒后重试...")
                time.sleep(wait)
    return None


def _classify_chunks_batch(chunks, outline_text, progress_callback=None):
    """
    批量分类 chunks，每块调用一次 LLM。
    返回: list[dict] 附加了 l1_code, l2_code 等字段的 chunks
    """
    config = get_config()
    if not config.get("api_key"):
        print("[excel_classifier] LLM API Key 未配置，无法分类")
        return []

    results = []
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(i, total, f"LLM 分类中 {i+1}/{total}...")

        # 加延迟避免 API 限流（0.5秒/请求）
        import time
        time.sleep(0.5)

        classification = _classify_single_chunk(chunk["content"], outline_text, config)
        if classification:
            chunk.update(classification)
        else:
            # LLM 失败时，标记为待定
            chunk.update({
                "l1_code": "L1",
                "l1_name": "战略、收益与品牌根基层",
                "l2_code": "L1.1",
                "l2_name": "收益管理与定价系统",
                "reason": "LLM 未响应，归入默认分类",
                "discard": False,
                "confidence": 0.1
            })
        results.append(chunk)

    return results


# ============================================================
# 4. 组装成 Excel 结构的 JSON 树
# ============================================================

def build_excel_tree(classified_chunks, original_name=""):
    """
    把 LLM 分类好的 chunks，按 Excel 的 L1/L2 结构组装成树。
    返回树形 JSON（格式与现有 tree_parser 一致）
    """
    # 按 Excel 分类汇总
    # key: (l1_code, l2_code), value: list[chunk]
    category_chunks = {}
    for chunk in classified_chunks:
        if chunk.get("discard"):
            continue
        key = (chunk.get("l1_code", "L1"), chunk.get("l2_code", "L1.1"))
        if key not in category_chunks:
            category_chunks[key] = []
        category_chunks[key].append(chunk)

    # L1 节点映射
    l1_names = {}
    for chunk in classified_chunks:
        l1_names[chunk.get("l1_code", "L1")] = chunk.get("l1_name", "")

    # 构建树
    children = []
    for (l1_code, l2_code), chunks in sorted(category_chunks.items()):
        # 找或创建 L1 节点
        l1_node = next((c for c in children if c["id"] == l1_code), None)
        if l1_node is None:
            l1_node = {
                "id": l1_code,
                "title": l1_names.get(l1_code, l1_code),
                "type": "heading",
                "level": 1,
                "page_range": "",
                "summary": "",
                "content_preview": "",
                "children": []
            }
            children.append(l1_node)

        # 合并该 L2 下所有 chunks 的内容
        combined_content = "\n\n".join(c["content"] for c in chunks)
        # 取第一个 chunk 的 l2 信息
        first = chunks[0]

        # 构建 L2 节点
        l2_node = {
            "id": f"{l1_code}_{l2_code}",
            "title": first.get("l2_name", l2_code),
            "type": "heading",
            "level": 2,
            "page_range": "",
            "summary": _make_summary(combined_content, 150),
            "content_preview": combined_content[:500] if combined_content else "",
            "children": [
                {
                    "id": c.get("chunk_id", f"leaf_{i}"),
                    "title": f"段落 {i+1}",
                    "type": "chunk",
                    "content_preview": c["content"][:300] if c["content"] else "",
                    "summary": _make_summary(c["content"], 100),
                    "confidence": c.get("confidence", 0),
                    "reason": c.get("reason", ""),
                    "children": []
                }
                for i, c in enumerate(chunks)
            ]
        }
        l1_node["children"].append(l2_node)

    return {
        "id": "root",
        "title": original_name or "文档",
        "type": "root",
        "children": children
    }


def _make_summary(text, max_len=150):
    """生成摘要"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + '...'


# ============================================================
# 5. 完整流程：Excel 大纲 + LLM 分类
# ============================================================

def excel_classify_and_build(md_content, original_name="", excel_path=None,
                             progress_callback=None):
    """
    完整流程：
    1. 读取 Excel 大纲
    2. 把 Markdown 切块
    3. LLM 分类每块
    4. 按 Excel 结构组装树

    返回: (tree_json, stats_dict)
    stats: { total_chunks, discarded, by_category }
    """
    # Step 1: 读 Excel
    if progress_callback:
        progress_callback(0, 100, "读取 Excel 大纲...")
    outline = load_excel_outline(excel_path)
    if not outline:
        raise Exception("无法读取 Excel 大纲文件，请确认《餐饮全景运营知识库.xlsx》存在于项目根目录")

    # Step 2: 切块
    if progress_callback:
        progress_callback(10, 100, "切分内容段落...")
    chunks = chunk_markdown(md_content)
    if not chunks:
        raise Exception("Markdown 内容为空，无法分类")

    # Step 3: LLM 分类
    if progress_callback:
        progress_callback(20, 100, f"开始 LLM 分类（共 {len(chunks)} 块）...")
    classified = _classify_chunks_batch(chunks, outline["outline_text"], progress_callback)

    # Step 4: 组装树
    if progress_callback:
        progress_callback(95, 100, "组装分类结构...")
    tree = build_excel_tree(classified, original_name)

    # 统计
    stats = {
        "total_chunks": len(classified),
        "discarded": sum(1 for c in classified if c.get("discard")),
        "by_category": {}
    }
    for c in classified:
        if c.get("discard"):
            continue
        key = c.get("l2_name", "未知")
        stats["by_category"][key] = stats["by_category"].get(key, 0) + 1

    if progress_callback:
        progress_callback(100, 100, "完成！")

    return tree, stats
