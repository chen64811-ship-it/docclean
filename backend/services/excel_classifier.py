# -*- coding: utf-8 -*-
"""
Excel 大纲 + LLM 智能分类服务
功能：
1. 读取项目根目录下的 Excel 大纲文件（.xlsx），自动识别分类结构
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

    excel_path 为 None 时，自动扫描项目根目录下的 .xlsx 文件作为大纲。
    找不到任何 .xlsx 时返回 None（调用方应优雅降级，不报错）。
    """
    if excel_path is None:
        # 从 backend/services/excel_classifier.py，往上三层到 vip/
        _vip_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # 自动扫描项目根目录下的 .xlsx 文件（排除 ~$ 开头的临时文件）
        candidates = []
        try:
            candidates = [
                f for f in os.listdir(_vip_dir)
                if f.endswith(".xlsx") and not f.startswith("~$")
            ]
        except Exception:
            pass
        if candidates:
            # 优先选最近修改过的
            candidates.sort(key=lambda f: os.path.getmtime(os.path.join(_vip_dir, f)), reverse=True)
            excel_path = os.path.join(_vip_dir, candidates[0])
        else:
            return None  # 没有 xlsx 文件时优雅降级，不报错

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

        # 生成供 LLM 阅读的分类文本（精简版，只保留 code+name，减小 prompt 体积）
        outline_lines = []
        for l1 in l1_list:
            outline_lines.append(f"【{l1['code']}】{l1['name']}")
            children = l2_map.get(l1["code"], [])
            for l2 in children:
                outline_lines.append(f"  - 【{l2['code']}】{l2['name']}")

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

【分类大纲】：
{outline_text}

【文本片段】：
---
{chunk_text[:800]}
---

用 JSON 返回（不要其他文字）：
{{"l1_code":"L1编号","l1_name":"L1名称","l2_code":"L2编号","l2_name":"L2名称","reason":"一句话理由","discard":false,"confidence":0.85}}

注意：广告/版权/空白内容 discard=true，confidence<0.4 时 discard=true"""

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
                "thinking": {"type": "disabled"}  # 关闭思维链
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
                    # 去除 <think>...</think> 思考块
                    raw = re.sub(r'<think>[\s\S]*?</think>', '', raw).strip()
                    m = re.search(r'\{[\s\S]*\}', raw)
                    if m:
                        return json.loads(m.group())
        except Exception as e:
            print(f"[excel_classifier] LLM 调用失败 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                wait = 3 * (2 ** attempt)  # 3s → 6s
                print(f"  → {wait}秒后重试...")
                time.sleep(wait)
    return None


def _classify_batch_chunks(batch_chunks, outline_text, config):
    """
    一次 LLM 调用处理多个 chunk（批量模式），减少 API 请求次数。
    返回: list[dict|None] 与 batch_chunks 等长
    """
    import time
    items_text = ""
    for idx, chunk in enumerate(batch_chunks):
        items_text += f"\n[{idx+1}] {chunk['content'][:400]}\n"

    prompt = f"""你是知识库分类助手。请对以下 {len(batch_chunks)} 个文本片段逐一分类。

【分类大纲】：
{outline_text}

【文本片段】：
{items_text}

请用 JSON 数组返回，每项对应一个片段（顺序不变，不要其他文字）：
[{{"l1_code":"L1编号","l1_name":"L1名称","l2_code":"L2编号","l2_name":"L2名称","reason":"理由","discard":false,"confidence":0.85}}, ...]

注意：广告/版权/空白内容 discard=true"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": max(4000, 800 * len(batch_chunks)),  # 每块留足 800 token（含 think 块）
                "thinking": {"type": "disabled"}  # 关闭思维链
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    raw = choices[0].get("message", {}).get("content", "").strip()
                    # 去除 <think>...</think> 思考块（MiniMax 模型会输出）
                    raw = re.sub(r'<think>[\s\S]*?</think>', '', raw).strip()
                    m = re.search(r'\[[\s\S]*\]', raw)
                    if m:
                        arr = json.loads(m.group())
                        if isinstance(arr, list) and len(arr) == len(batch_chunks):
                            return arr
        except Exception as e:
            print(f"[excel_classifier] 批量LLM失败 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                wait = 3 * (2 ** attempt)
                print(f"  → {wait}秒后重试...")
                time.sleep(wait)
    # 批量失败，回退到逐个调用
    print("[excel_classifier] 批量调用失败，回退逐个处理")
    return [_classify_single_chunk(c["content"], outline_text, config) for c in batch_chunks]


def _classify_chunks_batch(chunks, outline_text, progress_callback=None):
    """
    批量分类 chunks，每 5 块一次 LLM 调用。
    超大文件自动截断到 200 块。
    返回: list[dict] 附加了 l1_code, l2_code 等字段的 chunks
    """
    import time

    MAX_CHUNKS = 200
    BATCH_SIZE = 5

    config = get_config()
    if not config.get("api_key"):
        print("[excel_classifier] LLM API Key 未配置，无法分类")
        return []

    if len(chunks) > MAX_CHUNKS:
        print(f"[excel_classifier] 文件过大，仅处理前 {MAX_CHUNKS} 块（共 {len(chunks)} 块）")
        chunks = chunks[:MAX_CHUNKS]

    results = []
    total = len(chunks)
    i = 0
    while i < total:
        batch = chunks[i:i + BATCH_SIZE]
        if progress_callback:
            progress_callback(i, total, f"LLM 分类中 {i+1}-{min(i+BATCH_SIZE, total)}/{total}...")
        print(f"[excel_classifier] 处理第 {i+1}-{min(i+BATCH_SIZE, total)}/{total} 块...")

        t0 = time.time()
        classifications = _classify_batch_chunks(batch, outline_text, config)
        print(f"[excel_classifier] 批次完成，耗时 {round(time.time()-t0, 1)}s")

        for j, chunk in enumerate(batch):
            cls = classifications[j] if classifications and j < len(classifications) else None
            if cls:
                # 删除 LLM 可能多返回的 content/title 字段，防止覆盖原始切块内容
                cls.pop("content", None)
                cls.pop("title", None)
                chunk.update(cls)
            else:
                # LLM 未响应时归入大纲的第一个分类（通用兜底，不写死特定行业）
                chunk.update({
                    "l1_code": "L1",
                    "l1_name": "未分类",
                    "l2_code": "L1.1",
                    "l2_name": "未分类内容",
                    "reason": "LLM 未响应，归入默认分类",
                    "discard": False,
                    "confidence": 0.1
                })
            results.append(chunk)

        i += BATCH_SIZE
        if i < total:
            time.sleep(0.3)  # 批次间短暂停顿

    return results


# ============================================================
# 4. 组装成 Excel 结构的 JSON 树
# ============================================================

def _classify_whole_doc(md_content, outline_text, original_name, config):
    """
    小文件整体分类：把整篇文档发给 LLM，一次返回分类结果。
    适用于 < 8000 字的文件，避免分块串行调用。
    返回: (tree, stats)
    """
    import time
    prompt = f"""你是知识库分类助手。请分析以下文档，判断其内容属于哪个分类，并把文档切分成若干段落分别归类。

【分类大纲】：
{outline_text}

【文档内容】：
---
{md_content[:6000]}
---

请用 JSON 数组返回，每个元素代表文档的一个主要段落/章节，格式如下（不要其他文字）：
[{{"title":"段落标题","content":"段落核心内容（50字内）","l1_code":"L1编号","l1_name":"L1名称","l2_code":"L2编号","l2_name":"L2名称","reason":"一句话理由","discard":false,"confidence":0.9}}, ...]

注意：返回 3-8 个元素即可，覆盖文档主要内容。"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4000,
                "thinking": {"type": "disabled"}  # 关闭思维链，加快响应速度
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    raw = choices[0].get("message", {}).get("content", "").strip()
                    raw = re.sub(r'<think>[\s\S]*?</think>', '', raw).strip()
                    m = re.search(r'\[[\s\S]*\]', raw)
                    if m:
                        arr = json.loads(m.group())
                        if isinstance(arr, list) and len(arr) > 0:
                            # 转成 chunks 格式
                            chunks = []
                            for i, item in enumerate(arr):
                                chunks.append({
                                    "chunk_id": f"chunk_{i}",
                                    "content": item.get("content", ""),
                                    "char_count": len(item.get("content", "")),
                                    "l1_code": item.get("l1_code", "L1"),
                                    "l1_name": item.get("l1_name", ""),
                                    "l2_code": item.get("l2_code", "L1.1"),
                                    "l2_name": item.get("l2_name", ""),
                                    "reason": item.get("reason", ""),
                                    "discard": item.get("discard", False),
                                    "confidence": item.get("confidence", 0.8)
                                })
                            tree = build_excel_tree(chunks, original_name)
                            stats = {
                                "total_chunks": len(chunks),
                                "discarded": sum(1 for c in chunks if c.get("discard")),
                                "by_category": {}
                            }
                            for c in chunks:
                                if not c.get("discard"):
                                    key = c.get("l2_name", "未知")
                                    stats["by_category"][key] = stats["by_category"].get(key, 0) + 1
                            return tree, stats
        except Exception as e:
            print(f"[excel_classifier] 整体分类失败 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    return None, None


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
            "content_preview": combined_content,  # L2 节点保留全部合并内容
            "children": [
                {
                    "id": c.get("chunk_id", f"leaf_{i}"),
                    "title": _extract_title(c["content"]),  # 从内容提取标题
                    "type": "chunk",
                    "content_preview": c["content"],  # 完整原文，不截断
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


def _extract_title(content, max_len=40):
    """从段落内容中提取标题（优先取第一个 Markdown 标题行，否则取前40字）"""
    if not content:
        return "段落"
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('#'):
            title = re.sub(r'^#+\s*', '', line).strip()
            if title:
                return title[:max_len]
    # 无标题行，取首行非空文字
    for line in content.splitlines():
        line = line.strip()
        if line:
            return line[:max_len]
    return "段落"


# ============================================================
# 5. 完整流程：Excel 大纲 + LLM 分类
# ============================================================

def excel_classify_and_build(md_content, original_name="", excel_path=None,
                             progress_callback=None):
    """
    完整流程：
    1. 读取 Excel 大纲
    2. 把 Markdown 切块（保留原文，不丢任何内容）
    3. LLM 只贴分类标签（不改原文内容）
    4. 按 Excel 结构组装树

    返回: (tree_json, stats_dict)
    stats: { total_chunks, discarded, by_category }
    """
    # Step 1: 读 Excel
    if progress_callback:
        progress_callback(0, 100, "读取 Excel 大纲...")
    outline = load_excel_outline(excel_path)
    if not outline:
        excel_name = os.path.basename(excel_path) if excel_path else "大纲文件"
        raise Exception(f"无法读取 Excel 大纲文件（{excel_name}），请确认文件格式正确且位于项目根目录")

    # Step 2: 切块（保留原文全部内容）
    if progress_callback:
        progress_callback(15, 100, "切分内容段落...")
    chunks = chunk_markdown(md_content)
    if not chunks:
        raise Exception("Markdown 内容为空，无法分类")

    # Step 3: LLM 只贴分类标签（不修改 chunk 原文）
    total_chunks = len(chunks)
    if progress_callback:
        progress_callback(20, 100, f"开始 AI 分类（共 {total_chunks} 块）...")
    classified = _classify_chunks_batch(chunks, outline["outline_text"], progress_callback)

    # Step 4: 组装树
    if progress_callback:
        progress_callback(95, 100, "正在生成分类树结构...")
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
        progress_callback(100, 100, "分类完成！")

    return tree, stats
