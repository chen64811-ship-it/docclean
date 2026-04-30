# -*- coding: utf-8 -*-
"""
数据清洗服务
去除乱码、空格、空行，整理排版
"""
import re


def clean_text(raw_text):
    """
    对原始文本进行清洗

    参数：
        raw_text: 原始文本（可能包含乱码、多余空格空行等）

    返回：
        清洗后的干净文本
    """
    if not raw_text:
        return ""

    text = raw_text

    # 1. 修复 Windows 换行符，统一为 \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. 去除不可见的乱码字符
    # 移除控制字符（除了换行和Tab）
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 移除 UTF-8 编码错误产生的替换字符（�）
    text = text.replace("�", "")

    # 3. 去除行首行尾空格
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)  # 行尾空格
    text = re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)  # 行首空格

    # 4. 合并多个空行为单个空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 4.5. 修复 + 符号周围的多余空格（在通用空格压缩之前处理原始多空格情况）
    # 例如："词语  +  词语" → "词语 + 词语"（排除行首的 Markdown 列表项 "+ 列表"）
    fixed_lines = []
    for _ln in text.split('\n'):
        if not re.match(r'^\+\s', _ln):
            _ln = re.sub(r'[ \t]{2,}(\+)', r' \1', _ln)
            _ln = re.sub(r'(\+)[ \t]{2,}', r'\1 ', _ln)
        fixed_lines.append(_ln)
    text = '\n'.join(fixed_lines)

    # 5. 去除每行之间多余的空格（保留句子结构）
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 5b. 去除中文字符之间、中文与标点之间的多余空格
    # 例如 "完成多个 AI" 正常保留，但 "独立 完成" → "独立完成"
    # 规则：中文字符（\u4e00-\u9fff）两侧相邻时，中间的单个空格也删除
    text = re.sub(r'([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]) ([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef，。！？、；：""''【】《》（）])', r'\1\2', text)
    text = re.sub(r'([，。！？、；：""''【】《》（）]) ([\u4e00-\u9fff])', r'\1\2', text)
    # 再跑一次（处理连续中文间多个空格先被压缩为1个再消除）
    text = re.sub(r'([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]) ([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef，。！？、；：""''【】《》（）])', r'\1\2', text)

    # 6. 去除全角空格和各种特殊空白字符
    text = text.replace("\u3000", " ")  # 全角空格
    text = re.sub(r"[\u00a0\u2000-\u200b\u2028\u2029\u202f\u205f\u3000]+", " ", text)

    # 6b. 再次压缩行内多余空格（全角空格等转换后可能产生连续空格，统一消除）
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)  # 清理行尾空格
    text = re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)  # 清理行首空格

    # 7. 去除 Unicode 方向的格式字符
    text = re.sub(r"[\u200e\u200f\u202a-\u202e]", "", text)

    # 8. 去除一些常见的爬虫/OCR 残留乱码模式（如连续无意义符号）
    text = re.sub(r"[_\-=]{5,}", "", text)  # 超过5个的连续横线
    text = re.sub(r"[*#]{5,}", "", text)     # 超过5个的连续星号/井号

    # 9. 去除前后多余空行
    text = text.strip()

    # 10. 最后再合并一次多余的空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 11. 去除重复的段落（保留第一次出现的版本）
    text = _remove_duplicate_paragraphs(text)

    return text


def _remove_duplicate_paragraphs(text):
    """
    删除重复的段落（以双空行分隔的内容块为单位）
    保留每个段落第一次出现的版本，后续重复的全部删除。
    """
    paragraphs = text.split('\n\n')
    seen = set()
    unique = []
    for para in paragraphs:
        # 对段落内容做规范化（去首尾空白）再比较，避免空白差异导致误判
        key = para.strip()
        if not key:
            continue
        if key not in seen:
            seen.add(key)
            unique.append(para)
    return '\n\n'.join(unique)


def text_to_markdown(text, title=None):
    """
    将清洗后的文本格式化为 Markdown

    参数：
        text: 清洗后的文本
        title: 可选，文件标题（会作为 H1 放在最前面）

    返回：
        格式化后的 Markdown 字符串
    """
    lines = []

    # 如果有标题，加在开头
    if title:
        lines.append(f"# {title}\n")

    # 把文本内容附加上去
    if text:
        lines.append(text)

    result = "\n".join(lines)

    # 确保末尾没有多余空行
    result = result.rstrip("\n") + "\n"

    return result
