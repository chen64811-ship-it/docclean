# -*- coding: utf-8 -*-
"""
Excel Outline + LLM Smart Classification Service
Features:
1. Read Excel outline file (.xlsx) from project root, auto-detect classification structure
2. Chunk Markdown content into paragraphs (~500-800 chars/chunk)
3. Call LLM to map each chunk to Excel categories
4. Assemble into structured JSON tree
"""
import re
import json
import os
import urllib.request
import urllib.error
from config_manager import get_config, is_llm_enabled


# ============================================================
# 1. Load Excel Outline
# ============================================================

def load_excel_outline(excel_path=None):
    """
    Read Excel file, return outline structure (for LLM classification).
    Returns dict: { outline_text: str, categories: list[dict] }
    Each category element: { code, name, keywords, level }

    When excel_path is None, auto-scan project root for .xlsx files as outline.
    If no .xlsx found, returns None (caller should gracefully degrade, not error).
    """
    if excel_path is None:
        # From backend/services/excel_classifier.py, go up 3 levels to vip/
        _vip_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Auto-scan project root for .xlsx files (exclude ~$ temp files)
        candidates = []
        try:
            candidates = [
                f for f in os.listdir(_vip_dir)
                if f.endswith(".xlsx") and not f.startswith("~$")
            ]
        except Exception:
            pass
        if candidates:
            # Prefer most recently modified
            candidates.sort(key=lambda f: os.path.getmtime(os.path.join(_vip_dir, f)), reverse=True)
            excel_path = os.path.join(_vip_dir, candidates[0])
        else:
            return None  # No xlsx files — graceful degradation, no error

    if not os.path.exists(excel_path):
        return None

    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))

        # First row is header
        categories = []
        for row in rows[2:]:  # skip header rows (row 1, 2)
            if not row or not any(cell for cell in row):
                continue
            level = row[0]  # L1 / L2
            code = row[1]   # L1, L1.1 etc.
            name = row[2]   # node name
            parent = row[3]  # parent node
            keywords = row[4] if len(row) > 4 else ""  # keywords

            if not code or not name:
                continue

            categories.append({
                "level": str(level or "").strip(),
                "code": str(code or "").strip(),
                "name": str(name or "").strip(),
                "parent": str(parent or "").strip(),
                "keywords": str(keywords or "").strip()
            })

        # Build hierarchy: L1 = root category, L2 = subcategory
        l1_list = [c for c in categories if c["level"] == "L1"]
        l2_map = {}
        for c in categories:
            if c["level"] == "L2":
                parent_code = c["parent"]
                if parent_code not in l2_map:
                    l2_map[parent_code] = []
                l2_map[parent_code].append(c)

        # Generate classification text for LLM (compact: code+name only, reduces prompt size)
        outline_lines = []
        for l1 in l1_list:
            outline_lines.append(f"[{l1['code']}] {l1['name']}")
            children = l2_map.get(l1["code"], [])
            for l2 in children:
                outline_lines.append(f"  - [{l2['code']}] {l2['name']}")

        outline_text = "\n".join(outline_lines)
        return {
            "outline_text": outline_text,
            "categories": categories,
            "l1_list": l1_list,
            "l2_map": l2_map
        }

    except Exception as e:
        print(f"[excel_classifier] Failed to read Excel: {e}")
        return None


# ============================================================
# 2. Chunking (paragraph-based, ~600 chars per chunk)
# ============================================================

def chunk_markdown(md_content, chunk_size=600, overlap=50):
    """
    Split Markdown content into chunks.
    - Prefers natural paragraph boundaries (double newlines)
    - Each chunk approx. chunk_size characters
    - Returns list[dict]: { chunk_id, content, char_count }
    """
    if not md_content:
        return []

    # Collapse excess blank lines
    md_content = re.sub(r'\n{3,}', '\n\n', md_content)
    # Remove header/footer junk patterns
    junk_patterns = [
        r'Add WeChat[^\n]*',
        r'Follow us[^\n]*',
        r'Scan QR[^\n]*',
        r'Copyright[^\n]*',
        r'http\S+',
    ]
    for pat in junk_patterns:
        md_content = re.sub(pat, '', md_content)

    # Split by paragraph boundaries
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
        # If single paragraph is extra long, split further
        if para_len > chunk_size * 1.5:
            # Split long paragraph into sentences
            sentences = re.split(r'(?<=[.?!;\n])', para)
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
                    # overlap: keep last sentence as next chunk start
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

    # Final chunk
    if current:
        chunks.append({
            "chunk_id": f"chunk_{chunk_id}",
            "content": "\n".join(current).strip(),
            "char_count": current_len
        })

    return chunks


# ============================================================
# 3. LLM Classification (batch calls to reduce requests)
# ============================================================

def _get_llm_url(config):
    """Build LLM API endpoint URL."""
    api_base = config.get("api_base", "https://api.minimax.chat/v1").rstrip("/")
    if any(x in api_base for x in ["/chat/completions"]):
        return api_base
    if api_base.endswith("/v1"):
        return api_base + "/chat/completions"
    return api_base + "/v1/chat/completions"


def _classify_single_chunk(chunk_text, outline_text, config):
    """
    Send a single chunk to LLM, return classification result.
    Returns: { l1_code, l1_name, l2_code, l2_name, reason, discard }
    Returns None if LLM unavailable or error.
    """
    prompt = f"""You are a knowledge base classification assistant. Determine which category the following text fragment belongs to.

[Classification Outline]:
{outline_text}

[Text Fragment]:
---
{chunk_text[:800]}
---

Return JSON only (no other text):
{{"l1_code":"L1 code","l1_name":"L1 name","l2_code":"L2 code","l2_name":"L2 name","reason":"one-line reason","discard":false,"confidence":0.85}}

Note: ads/copyright/blank content should have discard=true. If confidence<0.4, set discard=true."""

    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
                "thinking": {"type": "disabled"}  # disable chain-of-thought
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
                    # Remove <think>...</think> blocks
                    raw = re.sub(r'<think>[\s\S]*?</think>', '', raw).strip()
                    m = re.search(r'\{[\s\S]*\}', raw)
                    if m:
                        return json.loads(m.group())
        except Exception as e:
            print(f"[excel_classifier] LLM call failed (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait = 3 * (2 ** attempt)  # 3s -> 6s
                print(f"  -> retrying in {wait}s...")
                time.sleep(wait)
    return None


def _classify_batch_chunks(batch_chunks, outline_text, config):
    """
    Process multiple chunks in a single LLM call (batch mode), reducing API requests.
    Returns: list[dict|None] same length as batch_chunks
    """
    import time
    items_text = ""
    for idx, chunk in enumerate(batch_chunks):
        items_text += f"\n[{idx+1}] {chunk['content'][:400]}\n"

    prompt = f"""You are a knowledge base classification assistant. Classify each of the following {len(batch_chunks)} text fragments.

[Classification Outline]:
{outline_text}

[Text Fragments]:
{items_text}

Return a JSON array only, one entry per fragment (same order, no other text):
[{{"l1_code":"L1 code","l1_name":"L1 name","l2_code":"L2 code","l2_name":"L2 name","reason":"reason","discard":false,"confidence":0.85}}, ...]

Note: ads/copyright/blank content should have discard=true."""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": max(4000, 800 * len(batch_chunks)),  # 800 tokens per chunk (including think block)
                "thinking": {"type": "disabled"}  # disable chain-of-thought
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
                    # Remove <think>...</think> blocks (MiniMax model output)
                    raw = re.sub(r'<think>[\s\S]*?</think>', '', raw).strip()
                    m = re.search(r'\[[\s\S]*\]', raw)
                    if m:
                        arr = json.loads(m.group())
                        if isinstance(arr, list) and len(arr) == len(batch_chunks):
                            return arr
        except Exception as e:
            print(f"[excel_classifier] Batch LLM failed (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait = 3 * (2 ** attempt)
                print(f"  -> retrying in {wait}s...")
                time.sleep(wait)
    # Batch failed, fallback to single-item calls
    print("[excel_classifier] Batch call failed, falling back to single-item processing")
    return [_classify_single_chunk(c["content"], outline_text, config) for c in batch_chunks]


def _classify_chunks_batch(chunks, outline_text, progress_callback=None):
    """
    Batch classify chunks, 5 chunks per LLM call.
    Large files auto-truncated to 200 chunks.
    Returns: list[dict] chunks with l1_code, l2_code etc. fields appended.
    """
    import time

    MAX_CHUNKS = 200
    BATCH_SIZE = 5

    config = get_config()
    if not config.get("api_key"):
        print("[excel_classifier] LLM API Key not configured, cannot classify")
        return []

    if len(chunks) > MAX_CHUNKS:
        print(f"[excel_classifier] File too large, processing first {MAX_CHUNKS} chunks only (total {len(chunks)})")
        chunks = chunks[:MAX_CHUNKS]

    results = []
    total = len(chunks)
    i = 0
    while i < total:
        batch = chunks[i:i + BATCH_SIZE]
        if progress_callback:
            progress_callback(i, total, f"LLM classifying {i+1}-{min(i+BATCH_SIZE, total)}/{total}...")
        print(f"[excel_classifier] Processing chunks {i+1}-{min(i+BATCH_SIZE, total)}/{total}...")

        t0 = time.time()
        classifications = _classify_batch_chunks(batch, outline_text, config)
        print(f"[excel_classifier] Batch complete in {round(time.time()-t0, 1)}s")

        for j, chunk in enumerate(batch):
            cls = classifications[j] if classifications and j < len(classifications) else None
            if cls:
                # Remove any extra content/title fields LLM might return, prevent overwriting original chunk content
                cls.pop("content", None)
                cls.pop("title", None)
                chunk.update(cls)
            else:
                # LLM unresponsive: assign to first outline category (generic fallback, not industry-specific)
                chunk.update({
                    "l1_code": "L1",
                    "l1_name": "Unclassified",
                    "l2_code": "L1.1",
                    "l2_name": "Unclassified Content",
                    "reason": "LLM unresponsive, assigned to default category",
                    "discard": False,
                    "confidence": 0.1
                })
            results.append(chunk)

        i += BATCH_SIZE
        if i < total:
            time.sleep(0.3)  # brief pause between batches

    return results


# ============================================================
# 4. Assemble into Excel-structured JSON Tree
# ============================================================

def _classify_whole_doc(md_content, outline_text, original_name, config):
    """
    Whole-document classification: send entire document to LLM, get classification in one call.
    Suitable for files < 8000 chars, avoids per-chunk sequential calls.
    Returns: (tree, stats)
    """
    import time
    prompt = f"""You are a knowledge base classification assistant. Analyze the following document, determine which category it belongs to, and segment it into paragraphs for individual classification.

[Classification Outline]:
{outline_text}

[Document Content]:
---
{md_content[:6000]}
---

Return a JSON array, each element representing a major paragraph/section of the document, in this format (no other text):
[{{"title":"section title","content":"core content (50 chars max)","l1_code":"L1 code","l1_name":"L1 name","l2_code":"L2 code","l2_name":"L2 name","reason":"one-line reason","discard":false,"confidence":0.9}}, ...]

Note: return 3-8 elements, covering the document's main content."""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4000,
                "thinking": {"type": "disabled"}  # disable chain-of-thought for faster response
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
                            # Convert to chunks format
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
                                    key = c.get("l2_name", "Unknown")
                                    stats["by_category"][key] = stats["by_category"].get(key, 0) + 1
                            return tree, stats
        except Exception as e:
            print(f"[excel_classifier] Whole-doc classification failed (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    return None, None


def build_excel_tree(classified_chunks, original_name=""):
    """
    Assemble LLM-classified chunks into a tree matching the Excel L1/L2 structure.
    Returns tree JSON (format consistent with existing tree_parser).
    """
    # Group by Excel classification
    # key: (l1_code, l2_code), value: list[chunk]
    category_chunks = {}
    for chunk in classified_chunks:
        if chunk.get("discard"):
            continue
        key = (chunk.get("l1_code", "L1"), chunk.get("l2_code", "L1.1"))
        if key not in category_chunks:
            category_chunks[key] = []
        category_chunks[key].append(chunk)

    # L1 name mapping
    l1_names = {}
    for chunk in classified_chunks:
        l1_names[chunk.get("l1_code", "L1")] = chunk.get("l1_name", "")

    # Build tree
    children = []
    for (l1_code, l2_code), chunks in sorted(category_chunks.items()):
        # Find or create L1 node
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

        # Merge all chunk content under this L2
        combined_content = "\n\n".join(c["content"] for c in chunks)
        # Take L2 info from first chunk
        first = chunks[0]

        # Build L2 node
        l2_node = {
            "id": f"{l1_code}_{l2_code}",
            "title": first.get("l2_name", l2_code),
            "type": "heading",
            "level": 2,
            "page_range": "",
            "summary": _make_summary(combined_content, 150),
            "content_preview": combined_content,  # L2 node keeps full merged content
            "children": [
                {
                    "id": c.get("chunk_id", f"leaf_{i}"),
                    "title": _extract_title(c["content"]),  # extract title from content
                    "type": "chunk",
                    "content_preview": c["content"],  # full original text, no truncation
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
        "title": original_name or "Document",
        "type": "root",
        "children": children
    }


def _make_summary(text, max_len=150):
    """Generate summary."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + '...'


def _extract_title(content, max_len=40):
    """Extract title from paragraph content (prefer first Markdown heading, otherwise first 40 chars)."""
    if not content:
        return "Paragraph"
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('#'):
            title = re.sub(r'^#+\s*', '', line).strip()
            if title:
                return title[:max_len]
    # No heading line, use first non-empty line
    for line in content.splitlines():
        line = line.strip()
        if line:
            return line[:max_len]
    return "Paragraph"


# ============================================================
# 5. Complete Flow: Excel Outline + LLM Classification
# ============================================================

def excel_classify_and_build(md_content, original_name="", excel_path=None,
                             progress_callback=None):
    """
    Complete flow:
    1. Read Excel outline
    2. Chunk Markdown (preserve original text, no content loss)
    3. LLM applies classification labels only (does not modify original content)
    4. Assemble tree by Excel structure

    Returns: (tree_json, stats_dict)
    stats: { total_chunks, discarded, by_category }
    """
    # Step 1: Read Excel
    if progress_callback:
        progress_callback(0, 100, "Reading Excel outline...")
    outline = load_excel_outline(excel_path)
    if not outline:
        excel_name = os.path.basename(excel_path) if excel_path else "outline file"
        raise Exception(f"Cannot read Excel outline file ({excel_name}), please verify the file format is correct and located in project root")

    # Step 2: Chunk (preserve all original content)
    if progress_callback:
        progress_callback(15, 100, "Chunking content...")
    chunks = chunk_markdown(md_content)
    if not chunks:
        raise Exception("Markdown content is empty, cannot classify")

    # Step 3: LLM applies classification labels (does not modify chunk content)
    total_chunks = len(chunks)
    if progress_callback:
        progress_callback(20, 100, f"Starting AI classification ({total_chunks} chunks)...")
    classified = _classify_chunks_batch(chunks, outline["outline_text"], progress_callback)

    # Step 4: Assemble tree
    if progress_callback:
        progress_callback(95, 100, "Building classification tree...")
    tree = build_excel_tree(classified, original_name)

    # Stats
    stats = {
        "total_chunks": len(classified),
        "discarded": sum(1 for c in classified if c.get("discard")),
        "by_category": {}
    }
    for c in classified:
        if c.get("discard"):
            continue
        key = c.get("l2_name", "Unknown")
        stats["by_category"][key] = stats["by_category"].get(key, 0) + 1

    if progress_callback:
        progress_callback(100, 100, "Classification complete!")

    return tree, stats
