# -*- coding: utf-8 -*-
"""
RAG 搜索服务
功能：
1. 分块存储：将 Markdown 内容按章节/页分块
2. 检索：TF-IDF 风格关键词匹配 + 语义排序
3. LLM 问答：调用配置的 LLM API 生成答案
"""
import re
import math
from collections import Counter
from config_manager import get_config, is_llm_enabled


# ========== LLM URL 构造 ==========

def get_llm_url(config):
    """
    根据配置的 api_base 智能构造完整接口 URL
    """
    api_base = config.get("api_base", "https://api.minimax.chat/v1").rstrip("/")
    # 如果已经是完整路径
    if any(x in api_base for x in ["/chat/completions"]):
        return api_base
    # 如果 api_base 尾部是 /v1（MiniMax 格式），追加 /chat/completions
    if api_base.endswith("/v1"):
        return api_base + "/chat/completions"
    # 否则拼接默认 OpenAI 兼容格式
    return api_base + "/v1/chat/completions"


# ========== 分块存储 ==========

def chunk_content(md_content, file_id, file_name="", chunk_size=200):
    """
    将 Markdown 内容分块，每块约 chunk_size 行
    返回块列表，每个块含 id/file_id/title/content/keywords
    """
    if not md_content:
        return []

    lines = md_content.split('\n')
    total_lines = len(lines)
    chunks = []

    # 策略1：按 ## 第 N 页 分块（PDF格式）
    page_blocks = re.split(r'(?=^##\s*第\s*\d+\s*页)', md_content, flags=re.MULTILINE)
    if len(page_blocks) > 1 and len(page_blocks) < 50:
        for block in page_blocks:
            block = block.strip()
            if not block:
                continue
            # 提取页码
            pm = re.match(r'^##\s*第\s*(\d+)\s*页', block)
            page_num = int(pm.group(1)) if pm else 0
            title = f"第 {page_num} 页" if page_num else "内容"
            chunks.append(_make_chunk(file_id, file_name, title, page_num, page_num, block))
        return chunks

    # 策略2：按 ## 标题 分块（Markdown格式）
    heading_blocks = re.split(r'(?=^##\s+)', md_content, flags=re.MULTILINE)
    if len(heading_blocks) > 1 and len(heading_blocks) < 30:
        for block in heading_blocks:
            block = block.strip()
            if not block:
                continue
            hm = re.match(r'^##\s+(.+)', block)
            title = hm.group(1).strip() if hm else "内容"
            page_num = _extract_page_num(block)
            chunks.append(_make_chunk(file_id, file_name, title, page_num, page_num, block))
        return chunks

    # 策略3：按固定行数分块
    for i in range(0, total_lines, chunk_size):
        end = min(i + chunk_size, total_lines)
        block_lines = lines[i:end]
        block = '\n'.join(block_lines)
        if not block.strip():
            continue
        first_line = block_lines[0].strip()
        title = re.sub(r'^#+\s*', '', first_line) if first_line.startswith('#') else f"第 {i // chunk_size + 1} 节"
        page_num = _extract_page_num(block)
        chunks.append(_make_chunk(file_id, file_name, title, page_num, page_num, block))

    return chunks


def _make_chunk(file_id, file_name, title, page_start, page_end, content):
    """构建一个块对象"""
    keywords = _extract_keywords(content)
    return {
        "id": f"{file_id}_chunk_{page_start}",
        "file_id": file_id,
        "file_name": file_name,
        "title": title,
        "page_start": page_start,
        "page_end": page_end,
        "content": content,
        "keywords": keywords,
        "content_preview": content[:200].strip() if content else ""
    }


def _extract_page_num(text):
    """从文本中提取第一个页码"""
    m = re.search(r'第\s*(\d+)\s*页', text)
    return int(m.group(1)) if m else 0


def _extract_keywords(text, top_n=20):
    """提取关键词：高频实词"""
    text = re.sub(r'[^\w\u4e00-\u9fff]', ' ', text)  # 只保留文字和数字
    words = text.split()
    # 过滤停用词和太短/太长的词
    stop_words = {'的', '了', '是', '在', '和', '与', '对', '为', '有', '我', '这', '那', '也', '就', '都', '而', '及', '其', '被', '以', '将', '可', '中', '于', '上', '下', '或', '但', 'not', 'the', 'and', 'of', 'to', 'in', 'is', 'for', 'on', 'with', 'as', 'by'}
    filtered = [w for w in words if len(w) >= 2 and w not in stop_words and not w.isdigit()]
    counter = Counter(filtered)
    return [w for w, _ in counter.most_common(top_n)]


# ========== 向量检索（TF-IDF 风格）==========

def compute_tfidf_score(chunk_keywords, query_keywords):
    """
    计算块与查询的 TF-IDF 风格相似度得分
    chunk_keywords: list[str]  块的关键词
    query_keywords: list[str]  查询的关键词
    返回: float 得分
    """
    if not chunk_keywords or not query_keywords:
        return 0.0
    chunk_set = set(chunk_keywords)
    query_set = set(query_keywords)

    # 1. 精确匹配
    intersection = chunk_set & query_set
    exact_score = len(intersection)

    # 2. 包含匹配（查询词是否包含在块关键词中，或块关键词是否包含查询词）
    contain_score = 0
    for qk in query_set:
        for ck in chunk_set:
            # 查询词包含在块关键词中
            if qk in ck or ck in qk:
                contain_score += 0.5
                break

    score = exact_score + contain_score
    return round(score, 4)


def search_chunks(chunks, query, top_k=5):
    """
    在块列表中搜索最相关的 top_k 个块
    chunks: list[dict]  所有块
    query: str  用户查询
    返回: list[dict]  相关块，按得分降序
    """
    if not chunks or not query:
        return []

    # 提取查询关键词
    query_keywords = _extract_keywords(query, top_n=15)
    if not query_keywords:
        # 如果关键词提取失败，用查询字符串本身
        query_keywords = [w for w in query.split() if len(w) >= 2]

    scored = []
    for chunk in chunks:
        chunk_keywords = chunk.get("keywords", [])
        score = compute_tfidf_score(chunk_keywords, query_keywords)

        # 额外加分：查询词出现在标题中
        title = chunk.get("title", "")
        for kw in query_keywords:
            if kw in title:
                score += 0.3
                break

        # 额外加分：查询词出现在内容中
        content = chunk.get("content", "")
        content_lower = content.lower()
        query_lower = query.lower()
        if query_lower in content_lower:
            score += 0.5
        else:
            for kw in query_keywords:
                if kw in content_lower:
                    score += 0.1

        if score > 0:
            scored.append({**chunk, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ========== LLM 问答 ==========

def generate_answer(query, context_chunks):
    """
    调用配置的 LLM API，基于上下文块生成答案
    context_chunks: list[dict]  检索到的相关块
    返回: str  LLM 生成的答案
    """
    if not is_llm_enabled():
        return None

    if not context_chunks:
        return "没有找到相关内容，请尝试其他查询词。"

    # 构建上下文
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        page_info = f"（第{chunk['page_start']}页）" if chunk['page_start'] else ""
        context_parts.append(f"【来源{i}】{chunk['title']}{page_info}:\n{chunk['content_preview']}\n")

    context_text = "\n\n".join(context_parts)

    prompt = f"""你现在是一位资深的、懂得变通的商业咨询顾问。请仔细阅读以下参考资料，用专业、有启发性且接地气的口吻回答用户的提问。

核心要求：
1. 不要像机器一样生硬地罗列“来源1、来源2”，也不要因为资料里没有直接的答案就说“不知道”。
2. 请深度思考用户问题背后的真实需求，提取参考资料中有用的商业底层逻辑（比如消费趋势、用户视角、销售机制等），将它们融会贯通，给用户提供实用的建议。
3. 如果资料内容与问题确实有一定关联，请尽力运用资料中的知识来解答；如果资料真的和问题八竿子打不着，你可以基于常识回答，但要礼貌地提一句“参考资料中未过多涉及，但基于经验我的建议是...”。

---
【参考资料】:
{context_text}
---

【用户的提问】：{query}

请以顾问的口吻，用中文给出你的详细回答："""


    config = get_config()
    try:
        import urllib.request
        import json

        payload = {
            "model": config.get("model", "MiniMax-M2.7"),
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": float(config.get("temperature", 0.7)),
            "max_tokens": int(config.get("max_tokens", 2000))
        }

        req = urllib.request.Request(
            get_llm_url(config),
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
                return choices[0].get("message", {}).get("content", "")

    except Exception as e:
        return f"[LLM 调用失败] {str(e)}，请检查 API 配置"

    return "LLM 响应格式异常"


def test_llm_connection():
    """
    测试 LLM 连接是否正常
    返回: (success: bool, message: str)
    """
    config = get_config()
    api_key = config.get("api_key", "").strip()
    if not api_key:
        return False, "API Key 为空，请在设置中配置"

    try:
        import urllib.request
        import json

        llm_url = get_llm_url(config)

        # MiniMax 特殊处理：需要 GroupId（从 API Key 中提取或用默认）
        # MiniMax API Key 格式: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... 或 sk-cp-xxx 格式
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key
        }

        payload = {
            "model": config.get("model", "MiniMax-M2.7"),
            "messages": [{"role": "user", "content": "说 hello"}],
            "max_tokens": 10
        }

        req = urllib.request.Request(
            llm_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            choices = result.get("choices", [])
            if choices:
                return True, "连接成功！LLM 响应正常"
            return False, "响应格式异常"

    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            err_msg = err_body.get("error", {}).get("message", str(e))
        except Exception:
            err_msg = str(e)
        return False, f"HTTP 错误 {e.code}: {err_msg}"

    except Exception as e:
        return False, f"连接失败: {str(e)}"
