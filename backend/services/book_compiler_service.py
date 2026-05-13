# -*- coding: utf-8 -*-
"""
Book Compiler Service (Enhanced)
Functionality: Parse Word outline -> load all completed .md files -> smart match to outline sections -> clean irrelevant content -> generate complete book .md
Strategy: Prefer LLM matching (if available), fallback to keyword matching.
"""
import os
import re
import json
import datetime
import urllib.request
import urllib.error
from docx import Document
from config_manager import get_config

# Try to import jieba for Chinese word segmentation
try:
    import jieba
    jieba.setLogLevel(60)
    USE_JIEBA = True
except ImportError:
    USE_JIEBA = False

# Maximum text length for keyword matching scan (prevents large file hangs)
MAX_MATCH_TEXT_LEN = 50000


# ============================================================
# 1. Parse Word Outline
# ============================================================

def parse_word_outline(docx_path):
    """
    Parse Word document and extract outline structure.
    """
    doc = Document(docx_path)
    sections = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        m = re.match(r'^(\d+(?:\.\d+)*)\s*(.+)$', text)
        if m:
            num = m.group(1)
            title_body = m.group(2)
            level = num.count('.') + 1

            sections.append({
                "num": num,
                "title": title_body,
                "full_title": text,
                "level": level,
                "matched_files": []
            })

    return sections


# ============================================================
# 2. Content Cleaning: remove links, dates, ads, keep body only
# ============================================================

def clean_md_content(content):
    """
    Clean Markdown content, remove irrelevant information:
    - Remove URLs/links
    - Remove date timestamps
    - Remove source annotations (e.g. "Source: xxx")
    - Remove advertising content
    - Remove invalid image references
    - Remove excess blank lines
    - Preserve body text
    """
    if not content:
        return ""

    lines = content.split('\n')
    cleaned = []

    for line in lines:
        # Remove pure link lines
        if re.match(r'^\s*https?://\S+\s*$', line):
            continue
        # Remove Markdown link format but preserve link text
        line = re.sub(r'\[([^\]]*)\]\(https?://[^)]+\)', r'\1', line)
        # Remove inline URLs
        line = re.sub(r'https?://\S+', '', line)
        # Remove source/credit lines
        if re.match(r'^\s*[（(]?\s*(Source|Credit|Original|Reprint|Excerpt|Reference|Copyright|Disclaimer|Author|Editor|Published|Updated)\s*[:：]', line):
            continue
        # Remove pure date lines (e.g. "2026-04-10" or "Apr 10, 2026")
        if re.match(r'^\s*\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*$', line):
            continue
        # Remove copyright lines
        if re.match(r'^\s*(©|Copyright|All [Rr]ights [Rr]eserved)', line):
            continue
        # Remove empty Markdown images (paths that don't exist)
        if re.match(r'^\s*!\[.*\]\((?!http).*\)\s*$', line):
            continue

        cleaned.append(line)

    result = '\n'.join(cleaned)
    # Collapse 4+ blank lines to 2
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    return result.strip()


# ============================================================
# 3. Tokenization (for fallback matching)
# ============================================================

def tokenize(text):
    if not text:
        return set()
    text = re.sub(r'[#*_`>\[\]!]', ' ', text)
    text = re.sub(r'https?://\S+', ' ', text)
    if USE_JIEBA:
        words = jieba.lcut(text)
    else:
        words = re.findall(r'[\u4e00-\u9fff]{1,4}|[a-zA-Z]{2,}', text)
    filtered = set()
    for w in words:
        w = w.strip()
        if len(w) >= 2 and not w.isdigit():
            filtered.add(w)
    return filtered


def calc_similarity(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    inter = set_a & set_b
    union = set_a | set_b
    return len(inter) / len(union)


# ============================================================
# 4. Load all completed .md files
# ============================================================

def load_md_files(output_folder, file_records):
    result = []
    for rec in file_records:
        if rec.get("status") != "done":
            continue
        output_path = rec.get("output_path", "")
        if not output_path or not os.path.exists(output_path):
            stored = rec.get("stored_name", "")
            output_path = os.path.join(output_folder, os.path.splitext(stored)[0] + ".md")
            if not os.path.exists(output_path):
                continue

        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        title = rec.get("original_name", os.path.basename(output_path))
        title = os.path.splitext(title)[0]

        sample = title + " " + content[:2000]
        tokens = tokenize(sample)

        result.append({
            "id": rec.get("id"),
            "name": rec.get("original_name", ""),
            "title": title,
            "content": content,
            "tokens": tokens,
            "output_path": output_path
        })

    return result


# ============================================================
# 5. LLM Smart Matching: ask LLM which outline section each article belongs to
# ============================================================

def _get_llm_url(config):
    """Build LLM API endpoint URL."""
    api_base = config.get("api_base", "https://api.minimax.chat/v1").rstrip("/")
    if any(x in api_base for x in ["/chat/completions"]):
        return api_base
    if api_base.endswith("/v1"):
        return api_base + "/chat/completions"
    return api_base + "/v1/chat/completions"


def _llm_match_file(md_title, md_content_preview, outline_text, config):
    """
    Call LLM to determine which outline section(s) an article should be placed under.
    Returns: [{"num": "3.3", "reason": "..."}] or None
    Built-in retry mechanism (up to 2 retries).
    """
    import time

    prompt = f"""You are a knowledge base content classification expert, skilled in semantic understanding and categorization across multiple industries.

[Task] Determine which most specific-level outline section the following article belongs to (can be multiple, up to 3).

[Outline]:
{outline_text}

[Article Title]: {md_title}

[Article Content Preview] (first 1500 chars):
---
{md_content_preview[:1500]}
---

Return JSON format only (no other text):
{{
  "matches": [
    {{"num": "section number e.g. 3.3.1", "reason": "one-line reason"}},
    {{"num": "section number e.g. 3.3.2", "reason": "one-line reason"}}
  ]
}}

Requirements:
- num must be a number that exists in the outline (e.g. 1.1.1, 2.3, 3.3.5)
- Prefer the most specific level (e.g. 1.1.1 is better than 1.1)
- If the article covers multiple topics, return multiple matches (up to 3)
- Ensure matches are reasonable, don't force matches
"""

    max_retries = 2
    for attempt in range(max_retries):
        try:
            payload = {
                "model": config.get("model", "MiniMax-M2.7"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 500
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

            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    raw = choices[0].get("message", {}).get("content", "").strip()
                    m = re.search(r'\{[\s\S]*\}', raw)
                    if m:
                        data = json.loads(m.group())
                        return data.get("matches", [])
        except Exception as e:
            print(f"[book_compiler] LLM call failed (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                wait = 3 * (3 ** attempt)  # exponential backoff: 3s -> 9s
                print(f"  -> retrying in {wait}s...")
                time.sleep(wait)
    return None


def _test_llm_available(config):
    """Quick test if LLM is available (1 call, 15s timeout)."""
    try:
        payload = {
            "model": config.get("model", "MiniMax-M2.7"),
            "messages": [{"role": "user", "content": "Reply OK"}],
            "temperature": 0.1,
            "max_tokens": 10
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
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True
    except Exception as e:
        print(f"[book_compiler] LLM unavailable: {e}")
        return False


def llm_match_files_to_sections(sections, md_files, progress_callback=None):
    """
    Use LLM to smart-match all md files to outline sections.
    Falls back to keyword matching if LLM is unavailable.
    """
    config = get_config()
    # Book compiler defaults to NOT using LLM to avoid long waits; set BOOK_USE_LLM=true in .env to enable
    force_llm = os.getenv("BOOK_USE_LLM", "false").strip().lower() in ("1", "true", "yes")
    use_llm = bool(config.get("api_key")) and config.get("enabled") and force_llm

    if use_llm:
        print("[book_compiler] Testing LLM availability...")
        use_llm = _test_llm_available(config)

    if not use_llm:
        print("[book_compiler] LLM unavailable, using keyword matching")
        sections = match_by_filename(sections, md_files)
        sections = match_files_to_sections_keyword(sections, md_files)
        return sections

    # Build outline text (for LLM context)
    outline_lines = []
    for sec in sections:
        indent = "  " * (sec["level"] - 1)
        outline_lines.append(f"{indent}{sec['full_title']}")
    outline_text = "\n".join(outline_lines)

    # Build number-to-index mapping
    num_to_idx = {}
    for idx, sec in enumerate(sections):
        num_to_idx[sec["num"]] = idx

    total = len(md_files)
    for i, md in enumerate(md_files):
        if progress_callback:
            progress_callback(i + 1, total, md["title"])

        print(f"[book_compiler] LLM matching ({i+1}/{total}): {md['title']}")

        matches = _llm_match_file(md["title"], md["content"], outline_text, config)

        if matches:
            for match in matches:
                num = match.get("num", "")
                reason = match.get("reason", "")
                if num in num_to_idx:
                    idx = num_to_idx[num]
                    # Avoid duplicates
                    already = any(mf["title"] == md["title"] for mf in sections[idx]["matched_files"])
                    if not already:
                        sections[idx]["matched_files"].append({
                            "title": md["title"],
                            "content": md["content"],
                            "score": 1.0,
                            "source": "llm",
                            "reason": reason
                        })
                        print(f"  -> matched to [{num}] {sections[idx]['title']} ({reason})")
                else:
                    # Try fuzzy matching
                    for sec_num, sec_idx in num_to_idx.items():
                        if sec_num.startswith(num) or num.startswith(sec_num):
                            already = any(mf["title"] == md["title"] for mf in sections[sec_idx]["matched_files"])
                            if not already:
                                sections[sec_idx]["matched_files"].append({
                                    "title": md["title"],
                                    "content": md["content"],
                                    "score": 0.8,
                                    "source": "llm_fuzzy",
                                    "reason": reason
                                })
                                print(f"  -> fuzzy matched to [{sec_num}] {sections[sec_idx]['title']}")
                            break
        else:
            # LLM failed, fallback to keyword matching
            print(f"  -> LLM returned no result, using keyword fallback")
            _keyword_match_single(sections, md)

    return sections


def _keyword_match_single(sections, md):
    """Aggressive keyword matching for a single md file.
    Strategy: extract keywords from each section title, search in article full text by occurrence count.
    Rank by keyword hit rate, match one article to top 5 most relevant sections.
    """
    full_text = md["title"] + "\n" + md["content"]
    # Large files: only scan first N chars to avoid hanging
    if len(full_text) > MAX_MATCH_TEXT_LEN:
        full_text = full_text[:MAX_MATCH_TEXT_LEN]

    scores = []
    for idx, sec in enumerate(sections):
        # Extract keywords from section title
        kws = _extract_section_keywords(sec["title"])
        if not kws:
            continue

        # Search keywords in article full text
        hit_count = 0
        total_hits = 0
        for kw in kws:
            count = full_text.count(kw)
            if count > 0:
                hit_count += 1
                total_hits += count

        if hit_count == 0:
            continue

        # Score = hit rate * frequency weight + level weight
        coverage = hit_count / len(kws)
        freq_bonus = min(total_hits / 10.0, 2.0)
        level_bonus = sec["level"] * 0.1
        score = coverage * (1.0 + freq_bonus) + level_bonus

        # At least 2 keyword hits or 50%+ coverage
        if hit_count >= 2 or coverage >= 0.5:
            scores.append((idx, round(score, 4), hit_count, total_hits))

    if not scores:
        return

    scores.sort(key=lambda x: -x[1])
    for idx, score, hit_count, total_hits in scores[:5]:
        sec = sections[idx]
        already = any(mf["title"] == md["title"] for mf in sec["matched_files"])
        if not already:
            sections[idx]["matched_files"].append({
                "title": md["title"],
                "content": md["content"],
                "score": score,
                "source": "keyword"
            })
            print(f"  -> [{sec['num']}] {sec['title'][:40]} (hits:{hit_count}, freq:{total_hits}, score:{score})")


def _extract_section_keywords(title):
    """
    Extract core keywords from section title (specialized terms only, filter generic words).
    Example: "Review Management — Proactive Solicitation, Negative Review Follow-up, Top Reviews Pinning"
    Extracts: ["Review Management", "Proactive Solicitation", "Negative Review Follow-up", ...]
    """
    if not title:
        return []

    # Stop words: these appear in almost all articles, no distinguishing power
    # Note: industry-specific words removed, kept cross-industry generic
    STOP_WORDS = {
        'product', 'service', 'experience', 'user', 'customer', 'client', 'consumer',
        'brand', 'core', 'capability', 'management', 'operations', 'system', 'design', 'strategy', 'approach', 'solution',
        'model', 'standard', 'improvement', 'optimization', 'data', 'metric', 'cost', 'efficiency', 'price', 'quality',
        'market', 'platform', 'channel', 'content', 'structure', 'process', 'rule', 'mechanism', 'impact', 'situation',
        'effect', 'goal', 'requirement', 'scenario', 'resource', 'activity', 'tool', 'technology', 'information', 'problem',
        'method', 'condition', 'key', 'aspect', 'process', 'level', 'phase', 'plan', 'business',
        'foundation', 'environment', 'space', 'time', 'industry', 'enterprise', 'company', 'team', 'personnel',
        'through', 'implement', 'achieve', 'include', 'ensure', 'establish', 'based', 'using', 'identify',
        'and', 'with', 'for', 'can', 'etc', 'how', 'what', 'why',
        'these', 'those', 'not', 'is', 'or', 'but', 'also',
        'competition', 'competitor', 'form', 'perception', 'difference', 'prevent', 'imitation',
        'check', 'record', 'daily',
    }

    keywords = []

    # 1. Take the short title before "——" or "--"
    main_part = re.split(r'——|--', title)[0].strip()
    if main_part and len(main_part) >= 2:
        keywords.append(main_part)

    # 2. Take terminology phrases from after "——" or "--"
    desc_parts = re.split(r'——|--', title)
    if len(desc_parts) > 1:
        desc = desc_parts[1].strip()
        # Remove parenthetical explanations
        desc = re.sub(r'[（(][^）)]*[）)]', '', desc)
        sub_parts = re.split(r'[、/，,；;。]', desc)
        for sp in sub_parts:
            sp = sp.strip()
            # Only short terms (<=10 chars), skip long sentences
            if 2 <= len(sp) <= 10 and sp not in STOP_WORDS:
                keywords.append(sp)

    # 3. jieba segmentation: extract 2+ char non-stop words (critical for extracting core short words)
    if USE_JIEBA:
        for word in jieba.lcut(title):
            word = word.strip()
            if len(word) >= 2 and not word.isdigit() and word not in STOP_WORDS:
                keywords.append(word)

    # Deduplicate, preserve order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen and len(kw) >= 2:
            seen.add(kw)
            unique.append(kw)

    return unique


# ============================================================
# 6. Legacy Keyword Matching (as fallback)
# ============================================================

def match_files_to_sections_keyword(sections, md_files, threshold=0.02):
    if not md_files:
        return sections
    for md in md_files:
        print(f"\n[Keyword Matching] {md['title']}")
        _keyword_match_single(sections, md)
    return sections


def match_by_filename(sections, md_files):
    for md in md_files:
        fname = md.get("name", "")
        for sec in sections:
            num = sec["num"]
            if num in fname:
                already = any(m["title"] == md["title"] for m in sec["matched_files"])
                if not already:
                    sec["matched_files"].append({
                        "title": md["title"],
                        "content": md["content"],
                        "score": 1.0,
                        "source": "filename"
                    })
                break
    return sections


# ============================================================
# 7. Generate Final Book .md (Enhanced: cleaned content, body only)
# ============================================================

def build_book_markdown(sections, book_title="Knowledge Base Book"):
    """
    Concatenate all sections and matched content in outline order to generate the final book .md.
    Automatically cleans irrelevant content (links, dates, etc.).
    """
    lines = []

    # Book title
    lines.append(f"# {book_title}")
    lines.append("")
    lines.append(f"> Auto-generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Table of contents (up to level 2)
    lines.append("## Table of Contents")
    lines.append("")
    for sec in sections:
        if sec["level"] <= 2:
            indent = "  " * (sec["level"] - 1)
            lines.append(f"{indent}- {sec['full_title']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Body
    for sec in sections:
        hashes = "#" * min(sec["level"] + 1, 6)
        lines.append(f"{hashes} {sec['full_title']}")
        lines.append("")

        if sec["matched_files"]:
            for mf in sec["matched_files"]:
                # Clean content
                content = mf["content"]
                # Remove first H1 title line
                content = re.sub(r'^# .+\n', '', content, count=1)
                # Clean irrelevant content
                content = clean_md_content(content)

                if content.strip():
                    lines.append(content.strip())
                    lines.append("")
                    lines.append("---")
                    lines.append("")

    return "\n".join(lines)


# ============================================================
# 8. Main Entry Point: One-Click Book Compilation
# ============================================================

def compile_book(docx_path, output_folder, file_records, book_title=None, out_path=None,
                 progress_callback=None):
    """
    Main function: complete compilation flow.
    Uses LLM smart matching (if available), falls back to keyword matching.

    Args:
        docx_path:          outline Word file path (.docx)
        output_folder:      outputs/ directory
        file_records:       list of file records from DB with status=done
        book_title:         book title (default: derived from filename)
        out_path:           output .md file path
        progress_callback:  progress callback fn(current, total, title)
    """
    if not os.path.exists(docx_path):
        return {"success": False, "message": f"Outline file not found: {docx_path}"}

    # 1. Parse outline
    sections = parse_word_outline(docx_path)
    if not sections:
        return {"success": False, "message": "No valid numbered sections found in outline file (e.g. 1.1, 2.3)"}

    # 2. Load md files
    md_files = load_md_files(output_folder, file_records)

    # 3. LLM smart matching (auto fallback to keyword matching)
    sections = llm_match_files_to_sections(sections, md_files, progress_callback=progress_callback)

    # 4. Count matches
    matched_count = sum(1 for md in md_files if any(
        any(mf["title"] == md["title"] for mf in sec["matched_files"])
        for sec in sections
    ))
    total_with_content = sum(1 for sec in sections if sec["matched_files"])

    # 5. Book title
    if not book_title:
        book_title = os.path.splitext(os.path.basename(docx_path))[0]

    # 6. Generate Markdown (auto-cleaned)
    book_md = build_book_markdown(sections, book_title=book_title)

    # 7. Save
    if not out_path:
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', book_title)
        out_path = os.path.join(output_folder, f"{safe_name}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(book_md)

    print(f"[book_compiler] Compilation complete: {matched_count}/{len(md_files)} articles matched to {total_with_content}/{len(sections)} sections")

    return {
        "success": True,
        "book_path": out_path,
        "book_title": book_title,
        "matched_count": matched_count,
        "total_md_files": len(md_files),
        "total_sections": len(sections),
        "sections_with_content": total_with_content
    }
