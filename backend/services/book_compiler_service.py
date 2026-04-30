# -*- coding: utf-8 -*-
"""
合成书服务（增强版）
功能：读取 Word 目录大纲 → 读取所有已完成的 .md 文件 → 智能匹配到大纲章节 → 清洗无关内容 → 生成完整的书 .md
策略：优先用 LLM 匹配（如果可用），否则用强力关键词匹配回退。
"""
import os
import re
import json
import datetime
import urllib.request
import urllib.error
from docx import Document
from config_manager import get_config

# 尝试导入 jieba 中文分词
try:
    import jieba
    jieba.setLogLevel(60)
    USE_JIEBA = True
except ImportError:
    USE_JIEBA = False

# 关键词匹配时用于扫描的最大文本长度（防止大文件卡死）
MAX_MATCH_TEXT_LEN = 50000


# ============================================================
# 1. 解析 Word 大纲
# ============================================================

def parse_word_outline(docx_path):
    """
    解析 Word 文档，提取大纲结构。
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
# 2. 内容清洗：去除链接、日期、广告等无关内容，只保留正文
# ============================================================

def clean_md_content(content):
    """
    清洗 Markdown 内容，去除无关信息：
    - 去除网址/链接
    - 去除日期时间戳
    - 去除来源标注（如"来源：xxx"）
    - 去除广告性内容
    - 去除图片引用（如果图片路径无效）
    - 去除多余空行
    - 保留纯正文
    """
    if not content:
        return ""

    lines = content.split('\n')
    cleaned = []

    for line in lines:
        # 去掉第一行 H1 标题（避免和书的标题冲突）
        # 这个由调用方处理

        # 去除纯链接行
        if re.match(r'^\s*https?://\S+\s*$', line):
            continue
        # 去除 Markdown 链接格式但保留链接文字
        line = re.sub(r'\[([^\]]*)\]\(https?://[^)]+\)', r'\1', line)
        # 去除行内网址
        line = re.sub(r'https?://\S+', '', line)
        # 去除「来源：xxx」「出处：xxx」「原文链接：xxx」
        if re.match(r'^\s*[（(]?\s*(来源|出处|原文链接|原文|转载|摘自|参考|版权|免责声明|声明|作者|编辑|责编|发布时间|更新时间)\s*[:：]', line):
            continue
        # 去除纯日期行（如 "2026-04-10" 或 "2026年4月10日"）
        if re.match(r'^\s*\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*$', line):
            continue
        # 去除版权声明行
        if re.match(r'^\s*(©|Copyright|版权所有|All [Rr]ights [Rr]eserved)', line):
            continue
        # 去除空的 Markdown 图片（路径不存在的）
        if re.match(r'^\s*!\[.*\]\((?!http).*\)\s*$', line):
            continue

        cleaned.append(line)

    result = '\n'.join(cleaned)
    # 合并连续3个以上空行为2个
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    return result.strip()


# ============================================================
# 3. 分词工具（用于回退匹配）
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
# 4. 读取所有已完成的 .md 文件
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
# 5. LLM 智能匹配：调用大模型判断每篇文章最适合放到哪个大纲章节
# ============================================================

def _get_llm_url(config):
    """构造 LLM 接口 URL"""
    api_base = config.get("api_base", "https://api.minimax.chat/v1").rstrip("/")
    if any(x in api_base for x in ["/chat/completions"]):
        return api_base
    if api_base.endswith("/v1"):
        return api_base + "/chat/completions"
    return api_base + "/v1/chat/completions"


def _llm_match_file(md_title, md_content_preview, outline_text, config):
    """
    调用 LLM，判断一篇文章应该归到大纲的哪些章节。
    返回: [{"num": "3.3", "reason": "..."}] 或 None
    自带重试机制（最多3次）
    """
    import time

    prompt = f"""你是餐饮知识库内容分类专家。

【任务】判断以下文章内容应该归到大纲的哪个最细级别章节下（可多选，最多3个）。

【大纲目录】：
{outline_text}

【文章标题】：{md_title}

【文章内容预览】（前1500字）：
---
{md_content_preview[:1500]}
---

请用 JSON 格式返回（不要返回其他任何内容）：
{{
  "matches": [
    {{"num": "章节编号如3.3.1", "reason": "一句话理由"}},
    {{"num": "章节编号如3.3.2", "reason": "一句话理由"}}
  ]
}}

要求：
- num 必须是大纲中存在的编号（如 1.1.1、2.3、3.3.5 等）
- 优先匹配最细级别的章节（如 1.1.1 优于 1.1）
- 如果文章涵盖多个主题，可以返回多个匹配（最多3个）
- 确保匹配合理，不要强行匹配
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
            print(f"[book_compiler] LLM 调用失败 (第{attempt+1}次): {e}")
            if attempt < max_retries - 1:
                wait = 3 * (3 ** attempt)  # 指数退避：3s → 9s
                print(f"  → {wait}秒后重试...")
                time.sleep(wait)
    return None


def _test_llm_available(config):
    """快速测试 LLM 是否可用（1次调用，5秒超时）"""
    try:
        payload = {
            "model": config.get("model", "MiniMax-M2.7"),
            "messages": [{"role": "user", "content": "回复OK"}],
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
        print(f"[book_compiler] LLM 不可用: {e}")
        return False


def llm_match_files_to_sections(sections, md_files, progress_callback=None):
    """
    使用 LLM 智能匹配所有 md 文件到大纲章节。
    如果 LLM 不可用，回退到关键词匹配。
    """
    config = get_config()
    # 合成书默认不启用 LLM，避免长时间等待；需要可在 .env 加 BOOK_USE_LLM=true
    force_llm = os.getenv("BOOK_USE_LLM", "false").strip().lower() in ("1", "true", "yes")
    use_llm = bool(config.get("api_key")) and config.get("enabled") and force_llm

    if use_llm:
        print("[book_compiler] 检测 LLM 是否可用...")
        use_llm = _test_llm_available(config)

    if not use_llm:
        print("[book_compiler] LLM 不可用，使用关键词匹配")
        sections = match_by_filename(sections, md_files)
        sections = match_files_to_sections_keyword(sections, md_files)
        return sections

    # 构建大纲文本（给 LLM 看）
    outline_lines = []
    for sec in sections:
        indent = "  " * (sec["level"] - 1)
        outline_lines.append(f"{indent}{sec['full_title']}")
    outline_text = "\n".join(outline_lines)

    # 创建编号到索引的映射
    num_to_idx = {}
    for idx, sec in enumerate(sections):
        num_to_idx[sec["num"]] = idx

    total = len(md_files)
    for i, md in enumerate(md_files):
        if progress_callback:
            progress_callback(i + 1, total, md["title"])

        print(f"[book_compiler] LLM 匹配 ({i+1}/{total}): {md['title']}")

        matches = _llm_match_file(md["title"], md["content"], outline_text, config)

        if matches:
            for match in matches:
                num = match.get("num", "")
                reason = match.get("reason", "")
                if num in num_to_idx:
                    idx = num_to_idx[num]
                    # 避免重复
                    already = any(mf["title"] == md["title"] for mf in sections[idx]["matched_files"])
                    if not already:
                        sections[idx]["matched_files"].append({
                            "title": md["title"],
                            "content": md["content"],
                            "score": 1.0,
                            "source": "llm",
                            "reason": reason
                        })
                        print(f"  → 匹配到 [{num}] {sections[idx]['title']}（{reason}）")
                else:
                    # 尝试模糊查找（如 LLM 返回 "1.1" 但大纲里是 "1.1"）
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
                                print(f"  → 模糊匹配到 [{sec_num}] {sections[sec_idx]['title']}")
                            break
        else:
            # LLM 失败，回退到关键词匹配
            print(f"  → LLM 未返回结果，使用关键词回退匹配")
            _keyword_match_single(sections, md)

    return sections


def _keyword_match_single(sections, md):
    """对单个 md 文件做强力关键词匹配。
    策略：从每个章节标题提取关键词，在文章全文中搜索出现次数。
    按关键词命中率排序，一篇文章匹配到 top5 最相关章节。
    """
    full_text = md["title"] + "\n" + md["content"]
    # 大文件只取前 N 字符参与匹配，避免卡死
    if len(full_text) > MAX_MATCH_TEXT_LEN:
        full_text = full_text[:MAX_MATCH_TEXT_LEN]

    scores = []
    for idx, sec in enumerate(sections):
        # 从章节标题提取关键词
        kws = _extract_section_keywords(sec["title"])
        if not kws:
            continue

        # 在文章全文中搜索关键词
        hit_count = 0
        total_hits = 0
        for kw in kws:
            count = full_text.count(kw)
            if count > 0:
                hit_count += 1
                total_hits += count

        if hit_count == 0:
            continue

        # 得分 = 命中率 × 频次加权 + 层级加权
        coverage = hit_count / len(kws)
        freq_bonus = min(total_hits / 10.0, 2.0)
        level_bonus = sec["level"] * 0.1
        score = coverage * (1.0 + freq_bonus) + level_bonus

        # 至少命中2个关键词或覆盖率>50%
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
            print(f"  → [{sec['num']}] {sec['title'][:40]}（命中{hit_count}词, 频{total_hits}次, 分{score}）")


def _extract_section_keywords(title):
    """
    从章节标题提取核心关键词（只取专业术语，过滤泛词）。
    如："评价管理——主动邀评、差评跟进、优质评价置顶"
    提取：["评价管理", "主动邀评", "差评跟进", "优质评价", "评价", "差评", "邀评"]
    """
    if not title:
        return []

    # 泛词表：这些词出现在几乎所有文章里，没有区分度
    STOP_WORDS = {
        '产品', '服务', '体验', '用户', '顾客', '客户', '消费', '餐饮', '门店', '餐厅',
        '品牌', '核心', '能力', '管理', '运营', '系统', '设计', '策略', '方式', '方案',
        '模式', '标准', '提升', '优化', '数据', '指标', '成本', '效率', '价格', '质量',
        '市场', '平台', '渠道', '内容', '结构', '流程', '规则', '机制', '影响', '情况',
        '效果', '目标', '需求', '场景', '资源', '活动', '工具', '技术', '信息', '问题',
        '方法', '条件', '关键', '方面', '过程', '水平', '阶段', '计划', '经营', '业务',
        '基础', '环境', '空间', '时间', '行业', '企业', '公司', '团队', '人员', '老板',
        '通过', '进行', '实现', '包括', '确保', '建立', '根据', '利用', '识别', '排查',
        '以及', '其中', '对于', '可以', '等等', '如何', '什么', '怎么', '为什么',
        '这些', '那些', '不是', '就是', '还是', '或者', '并且', '而且',
        '竞争', '对手', '形成', '感知', '区别', '阻止', '模仿',
        '检查', '记录', '清洁', '每日',
    }

    keywords = []

    # 1. 取 —— 前面的短标题（如"评价管理"、"差评拦截"、"榜单逻辑"）
    main_part = re.split(r'——|--', title)[0].strip()
    if main_part and len(main_part) >= 2:
        keywords.append(main_part)

    # 2. 取 —— 后面描述中的术语短句（按 、分割）
    desc_parts = re.split(r'——|--', title)
    if len(desc_parts) > 1:
        desc = desc_parts[1].strip()
        # 去掉括号里的说明
        desc = re.sub(r'[（(][^）)]*[）)]', '', desc)
        sub_parts = re.split(r'[、/，,；;。]', desc)
        for sp in sub_parts:
            sp = sp.strip()
            # 只取短术语（<=10字），长句不要
            if 2 <= len(sp) <= 10 and sp not in STOP_WORDS:
                keywords.append(sp)

    # 3. jieba 分词提取2字以上的非泛词（这步最关键，能提取出"差评""评价""投流""榜单"等核心短词）
    if USE_JIEBA:
        for word in jieba.lcut(title):
            word = word.strip()
            if len(word) >= 2 and not word.isdigit() and word not in STOP_WORDS:
                keywords.append(word)

    # 去重保序
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen and len(kw) >= 2:
            seen.add(kw)
            unique.append(kw)

    return unique

    # 去重保序
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen and len(kw) >= 2:
            seen.add(kw)
            unique.append(kw)

    return unique
    for idx, score, inter in scores[:3]:
        sec = sections[idx]
        already = any(mf["title"] == md["title"] for mf in sec["matched_files"])
        if not already:
            sections[idx]["matched_files"].append({
                "title": md["title"],
                "content": md["content"],
                "score": round(score, 4),
                "source": "keyword"
            })


# ============================================================
# 6. 旧版关键词匹配（作为回退）
# ============================================================

def match_files_to_sections_keyword(sections, md_files, threshold=0.02):
    if not md_files:
        return sections
    for md in md_files:
        print(f"\n[关键词匹配] {md['title']}")
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
# 7. 生成最终的书 .md（增强版：清洗内容、只保留正文）
# ============================================================

def build_book_markdown(sections, book_title="餐饮运营知识大全"):
    """
    按大纲顺序拼接所有章节和匹配到的内容，生成最终的书 .md。
    自动清洗无关内容（链接、日期等）。
    """
    lines = []

    # 书名
    lines.append(f"# {book_title}")
    lines.append("")
    lines.append(f"> 自动生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # 目录（只列2级以内）
    lines.append("## 目录")
    lines.append("")
    for sec in sections:
        if sec["level"] <= 2:
            indent = "  " * (sec["level"] - 1)
            lines.append(f"{indent}- {sec['full_title']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 正文
    for sec in sections:
        hashes = "#" * min(sec["level"] + 1, 6)
        lines.append(f"{hashes} {sec['full_title']}")
        lines.append("")

        if sec["matched_files"]:
            for mf in sec["matched_files"]:
                # 清洗内容
                content = mf["content"]
                # 去掉第一行 H1 标题
                content = re.sub(r'^# .+\n', '', content, count=1)
                # 清洗无关内容
                content = clean_md_content(content)

                if content.strip():
                    lines.append(content.strip())
                    lines.append("")
                    lines.append("---")
                    lines.append("")

    return "\n".join(lines)


# ============================================================
# 8. 主入口：一键合成书
# ============================================================

def compile_book(docx_path, output_folder, file_records, book_title=None, out_path=None,
                 progress_callback=None):
    """
    主函数：完成整个合成流程。
    使用 LLM 智能匹配（如果可用），否则回退到关键词匹配。

    参数：
        docx_path:          大纲 Word 文件路径（.docx）
        output_folder:      outputs/ 目录
        file_records:       数据库里 status=done 的文件记录列表
        book_title:         书名（默认从文件名取）
        out_path:           输出的 .md 文件路径
        progress_callback:  进度回调 fn(current, total, title)
    """
    if not os.path.exists(docx_path):
        return {"success": False, "message": f"大纲文件不存在：{docx_path}"}

    # 1. 解析大纲
    sections = parse_word_outline(docx_path)
    if not sections:
        return {"success": False, "message": "大纲文件中没有找到有效的编号章节（如 1.1、2.3）"}

    # 2. 读取 md 文件
    md_files = load_md_files(output_folder, file_records)

    # 3. 使用 LLM 智能匹配（自动回退到关键词匹配）
    sections = llm_match_files_to_sections(sections, md_files, progress_callback=progress_callback)

    # 4. 统计匹配数量
    matched_count = sum(1 for md in md_files if any(
        any(mf["title"] == md["title"] for mf in sec["matched_files"])
        for sec in sections
    ))
    total_with_content = sum(1 for sec in sections if sec["matched_files"])

    # 5. 书名
    if not book_title:
        book_title = os.path.splitext(os.path.basename(docx_path))[0]

    # 6. 生成 Markdown（自动清洗无关内容）
    book_md = build_book_markdown(sections, book_title=book_title)

    # 7. 保存
    if not out_path:
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', book_title)
        out_path = os.path.join(output_folder, f"{safe_name}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(book_md)

    print(f"[book_compiler] 合成完成：{matched_count}/{len(md_files)} 篇文章匹配到 {total_with_content}/{len(sections)} 个章节")

    return {
        "success": True,
        "book_path": out_path,
        "book_title": book_title,
        "matched_count": matched_count,
        "total_md_files": len(md_files),
        "total_sections": len(sections),
        "sections_with_content": total_with_content
    }
