# -*- coding: utf-8 -*-
"""
RAG Search Service
Features:
1. Chunk storage: split Markdown content by chapter/page
2. Retrieval: TF-IDF style keyword matching + semantic ranking
3. LLM Q&A: call configured LLM API to generate answers
"""
import re
import math
from collections import Counter
from config_manager import get_config, is_llm_enabled


# ========== LLM URL Construction ==========

def get_llm_url(config):
    """
    Intelligently construct the full API endpoint URL from the configured api_base.
    """
    api_base = config.get("api_base", "https://api.minimax.chat/v1").rstrip("/")
    # If already a complete path
    if any(x in api_base for x in ["/chat/completions"]):
        return api_base
    # If api_base ends with /v1 (MiniMax format), append /chat/completions
    if api_base.endswith("/v1"):
        return api_base + "/chat/completions"
    # Otherwise append default OpenAI-compatible path
    return api_base + "/v1/chat/completions"


# ========== Content Chunking ==========

def chunk_content(md_content, file_id, file_name="", chunk_size=200):
    """
    Split Markdown content into chunks, approximately chunk_size lines each.
    Returns list of chunk objects with id/file_id/title/content/keywords.
    """
    if not md_content:
        return []

    lines = md_content.split('\n')
    total_lines = len(lines)
    chunks = []

    # Strategy 1: split by "## Page N" headers (PDF format)
    page_blocks = re.split(r'(?=^##\s*Page\s*\d+)', md_content, flags=re.MULTILINE)
    if len(page_blocks) > 1 and len(page_blocks) < 50:
        for block in page_blocks:
            block = block.strip()
            if not block:
                continue
            # Extract page number
            pm = re.match(r'^##\s*Page\s*(\d+)', block)
            page_num = int(pm.group(1)) if pm else 0
            title = f"Page {page_num}" if page_num else "Content"
            chunks.append(_make_chunk(file_id, file_name, title, page_num, page_num, block))
        return chunks

    # Strategy 2: split by ## headings (Markdown format)
    heading_blocks = re.split(r'(?=^##\s+)', md_content, flags=re.MULTILINE)
    if len(heading_blocks) > 1 and len(heading_blocks) < 30:
        for block in heading_blocks:
            block = block.strip()
            if not block:
                continue
            hm = re.match(r'^##\s+(.+)', block)
            title = hm.group(1).strip() if hm else "Content"
            page_num = _extract_page_num(block)
            chunks.append(_make_chunk(file_id, file_name, title, page_num, page_num, block))
        return chunks

    # Strategy 3: fixed-size chunking by line count
    for i in range(0, total_lines, chunk_size):
        end = min(i + chunk_size, total_lines)
        block_lines = lines[i:end]
        block = '\n'.join(block_lines)
        if not block.strip():
            continue
        first_line = block_lines[0].strip()
        title = re.sub(r'^#+\s*', '', first_line) if first_line.startswith('#') else f"Section {i // chunk_size + 1}"
        page_num = _extract_page_num(block)
        chunks.append(_make_chunk(file_id, file_name, title, page_num, page_num, block))

    return chunks


def _make_chunk(file_id, file_name, title, page_start, page_end, content):
    """Build a chunk object."""
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
    """Extract the first page number from text."""
    m = re.search(r'Page\s*(\d+)', text)
    return int(m.group(1)) if m else 0


def _extract_keywords(text, top_n=20):
    """Extract keywords: high-frequency content words."""
    text = re.sub(r'[^\w\u4e00-\u9fff]', ' ', text)  # keep only letters and digits
    words = text.split()
    # Filter stop words and words that are too short or too long
    stop_words = {'的', '了', '是', '在', '和', '与', '对', '为', '有', '我', '这', '那', '也', '就', '都', '而', '及', '其', '被', '以', '将', '可', '中', '于', '上', '下', '或', '但', 'not', 'the', 'and', 'of', 'to', 'in', 'is', 'for', 'on', 'with', 'as', 'by'}
    filtered = [w for w in words if len(w) >= 2 and w not in stop_words and not w.isdigit()]
    counter = Counter(filtered)
    return [w for w, _ in counter.most_common(top_n)]


# ========== Vector Retrieval (TF-IDF style) ==========

def compute_tfidf_score(chunk_keywords, query_keywords):
    """
    Compute TF-IDF style similarity score between chunk and query.
    chunk_keywords: list[str]  chunk keywords
    query_keywords: list[str]  query keywords
    Returns: float score
    """
    if not chunk_keywords or not query_keywords:
        return 0.0
    chunk_set = set(chunk_keywords)
    query_set = set(query_keywords)

    # 1. Exact match
    intersection = chunk_set & query_set
    exact_score = len(intersection)

    # 2. Substring match (query word contained in chunk keyword, or vice versa)
    contain_score = 0
    for qk in query_set:
        for ck in chunk_set:
            # Query word contained in chunk keyword
            if qk in ck or ck in qk:
                contain_score += 0.5
                break

    score = exact_score + contain_score
    return round(score, 4)


def search_chunks(chunks, query, top_k=5):
    """
    Search chunks for the top_k most relevant matches.
    chunks: list[dict]  all chunks
    query: str  user query
    Returns: list[dict]  relevant chunks sorted by score descending
    """
    if not chunks or not query:
        return []

    # Extract query keywords
    query_keywords = _extract_keywords(query, top_n=15)
    if not query_keywords:
        # If keyword extraction fails, use the raw query split
        query_keywords = [w for w in query.split() if len(w) >= 2]

    scored = []
    for chunk in chunks:
        chunk_keywords = chunk.get("keywords", [])
        score = compute_tfidf_score(chunk_keywords, query_keywords)

        # Bonus: query word appears in title
        title = chunk.get("title", "")
        for kw in query_keywords:
            if kw in title:
                score += 0.3
                break

        # Bonus: query appears in content
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


# ========== LLM Q&A ==========

def generate_answer(query, context_chunks):
    """
    Call the configured LLM API to generate an answer based on context chunks.
    context_chunks: list[dict]  retrieved relevant chunks
    Returns: str  LLM-generated answer
    """
    if not is_llm_enabled():
        return None

    if not context_chunks:
        return "No relevant content found. Try different query terms."

    # Build context
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        page_info = f"(Page {chunk['page_start']})" if chunk['page_start'] else ""
        context_parts.append(f"[Source {i}] {chunk['title']}{page_info}:\n{chunk['content_preview']}\n")

    context_text = "\n\n".join(context_parts)

    prompt = f"""You are an experienced business consultant who is knowledgeable, adaptable, and approachable. Read the reference materials below carefully, then answer the user's question with professional insight and practical advice.

Core requirements:
1. Don't mechanically list "Source 1, Source 2" like a robot. Don't say "I don't know" just because the materials don't have a direct answer.
2. Think deeply about the real need behind the user's question. Extract useful business principles from the materials (such as consumer trends, user perspectives, sales mechanisms, etc.) and synthesize them to provide practical recommendations.
3. If the materials are relevant to the question, do your best to use that knowledge in your answer. If the materials truly have no connection to the question, you may answer based on general knowledge, but politely mention that "the reference materials don't cover this in depth, but based on my experience..."

---
[Reference Materials]:
{context_text}
---

[User's Question]: {query}

Please respond in the language the user asked in, with a detailed, consultant-style answer:"""

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
        return f"[LLM call failed] {str(e)}, check API config"

    return "LLM response format error"


def test_llm_connection():
    """
    Test LLM connection health.
    Returns: (success: bool, message: str)
    """
    config = get_config()
    api_key = config.get("api_key", "").strip()
    if not api_key:
        return False, "API Key is empty, configure in Settings"

    try:
        import urllib.request
        import json

        llm_url = get_llm_url(config)

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + api_key
        }

        payload = {
            "model": config.get("model", "MiniMax-M2.7"),
            "messages": [{"role": "user", "content": "Say hello"}],
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
                return True, "Connection successful! LLM responding normally."
            return False, "Response format error"

    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            err_msg = err_body.get("error", {}).get("message", str(e))
        except Exception:
            err_msg = str(e)
        return False, f"HTTP error {e.code}: {err_msg}"

    except Exception as e:
        return False, f"Connection failed: {str(e)}"
