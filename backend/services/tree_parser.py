# -*- coding: utf-8 -*-
"""
Tree Structure Parser Service
Parses Markdown content into a tree structure (nodes: title/page/summary).
Supports PDF format (## Page N), Markdown format (# heading levels).
"""
import re
import uuid


def classify_document_with_llm(md_content, file_name=""):
    """
    Invoke the LLM to classify a document by type, category, and description.

    Returns: {"doc_type": "...", "doc_category": "...", "description": "..."}
    Returns None if LLM is not configured or call fails.
    """
    import os
    import sys
    import json
    import urllib.request

    # Dynamic import from backend directory (parent of services/)
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

    # Use first 5000 chars as document sample (more content = better accuracy)
    sample = md_content[:5000].strip()
    if not sample:
        return None

    prompt = (
        "You are a document semantic analysis expert. Read the following document content carefully and classify it by its PURPOSE and NATURE.\n\n"
        "[Classification Criteria (by purpose, not format)]\n"
        "- knowledge_doc: This document is written for 'people to learn and understand a domain of knowledge'.\n"
        "  Typical traits: concept explanations, principle descriptions, methodology, the reader is a learner.\n"
        "  Examples: technical docs, industry knowledge bases, tutorials, encyclopedia articles.\n\n"
        "- report: This document is written to 'report the results or analysis of something'.\n"
        "  Typical traits: conclusions, data support, time periods, subjects of analysis.\n"
        "  Examples: research reports, project retrospectives, market analysis, performance summaries.\n\n"
        "- log: This document is written to 'record events or status changes that occurred'.\n"
        "  Typical traits: organized by time or event, records status/progress/issues, no conclusion orientation.\n"
        "  Examples: work logs, operations records, changelogs, execution status tables.\n\n"
        "- readme: This document is written to 'tell users how to use a tool/project/system'.\n"
        "  Typical traits: installation steps, usage instructions, API descriptions, user-facing.\n"
        "  Examples: software READMEs, deployment guides, API docs, user guides.\n\n"
        "- data_table: The core content is 'structured data or tables', text is only supplementary.\n"
        "  Typical traits: extensive tables/numbers/field names, row-column relationships, data-driven.\n"
        "  Examples: price tables, product comparison charts, data reports, configuration lists.\n\n"
        "- general: None of the above types clearly apply, or content is mixed with no dominant purpose.\n\n"
        "[Strict Requirements]\n"
        "1. Judge only by content nature — do not be misled by filename or format (.md files can also be reports or logs).\n"
        "2. Select exactly ONE type that best matches the PRIMARY purpose.\n"
        "3. doc_category: the business/technical domain this document belongs to, max 6 words, do NOT repeat the type name.\n"
        "4. description: summarize what this document is about in one sentence, max 25 words.\n\n"
        f"[Filename] {file_name or 'unknown'}\n\n"
        f"[Document Excerpt]\n{sample}\n\n"
        "---\n"
        "Return ONLY the following JSON, no other text:\n"
        '{{"doc_type": "<type>", "doc_category": "<domain>", "description": "<one-line summary>"}}'
    )

    try:
        # Build API URL
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
            "max_tokens": 2000   # reasoning model <think> tags consume many tokens, leave room
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

        # Step 1: strip MiniMax reasoning model <think>...</think> tags
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        # Step 2: strip possible ```json ... ``` code block wrappers
        content = re.sub(r'^```[a-zA-Z]*\s*', '', content)
        content = re.sub(r'\s*```$', '', content).strip()
        # Step 3: extract first complete JSON object from anywhere in the text (most robust)
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if not json_match:
            return None
        content = json_match.group(0)

        classification = json.loads(content)
        # Validate doc_type
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
        # LLM call failure is silently ignored — does not block main flow
        return None


def parse_markdown_to_tree(md_content, file_name=""):
    """
    Parse Markdown content into a tree structure.

    Returns:
    {
        "id": "root",
        "title": filename,
        "type": "root",
        "children": [
            {
                "id": "node_xxx",
                "title": "Page 1 / Chapter 1",
                "type": "chapter|page",
                "page_range": "1-3",
                "page_start": 1,
                "page_end": 3,
                "summary": "Section summary...",
                "content_preview": "First 200 chars...",
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

        # Detect PDF page marker: ## Page N
        page_match = re.match(r'^##\s*Page\s*(\d+)', stripped)
        # Detect Markdown heading: # Title
        heading_match = re.match(r'^(#{1,4})\s+(.+)', stripped)

        if page_match:
            page_num = int(page_match.group(1))
            # Collect page content (exclude heading line)
            page_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                next_page = re.match(r'^##\s*Page\s*(\d+)', next_line)
                next_heading = re.match(r'^#{1,3}\s+', next_line)
                if next_page or next_heading:
                    break
                page_lines.append(lines[j])
                j += 1

            page_text = '\n'.join(page_lines).strip()
            node_counter += 1
            node_id = f"page_{page_num}"

            # Determine end page (look for next page marker)
            end_page = page_num
            k = j
            while k < len(lines):
                nm = re.match(r'^##\s*Page\s*(\d+)', lines[k].strip())
                if nm:
                    end_page = int(nm.group(1)) - 1
                    break
                k += 1

            node = {
                "id": node_id,
                "title": f"Page {page_num}",
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
            # Collect section content
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

            # Insert at correct position based on heading level
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

    # If no nodes found (plain text), chunk by fixed line count
    if not nodes:
        nodes = _chunk_by_lines(lines, lines_per_chunk=100)

    root = {
        "id": "root",
        "title": file_name or "Document",
        "type": "root",
        "children": nodes
    }

    # AI classification: call LLM to identify document type (silently ignored on failure)
    classification = classify_document_with_llm(md_content, file_name)
    if classification:
        root["doc_type"] = classification["doc_type"]
        root["doc_category"] = classification["doc_category"]
        root["description"] = classification["description"]

    return root


def _empty_tree(file_name):
    return {
        "id": "root",
        "title": file_name or "Document",
        "type": "root",
        "children": []
    }


def _make_summary(text, max_len=150):
    """
    Generate content summary: take first max_len meaningful characters.
    """
    if not text:
        return ""
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(' ', 1)[0] + '...'


def _guess_page_range(all_lines, heading_line_idx):
    """
    Infer page range from "Page N" markers near the heading.
    """
    context = '\n'.join(all_lines[max(0, heading_line_idx - 5):heading_line_idx + 20])
    pages = re.findall(r'Page\s*(\d+)', context)
    if pages:
        return f"{pages[0]}-{pages[-1]}"
    return ""


def _find_last_with_children(nodes):
    """
    Find the last node that has children (search backwards).
    """
    for i in range(len(nodes) - 1, -1, -1):
        if nodes[i].get("children"):
            return nodes[i]
    return None


def _chunk_by_lines(lines, lines_per_chunk=100):
    """
    Chunk plain text without structure by fixed line count.
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
            "title": f"Section {start // lines_per_chunk + 1}" if page_num is None else f"Page {page_num}",
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
    """Find the first page number in a chunk."""
    for line in chunk_lines:
        m = re.match(r'^##\s*Page\s*(\d+)', line.strip())
        if m:
            return int(m.group(1))
    return None
