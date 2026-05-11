"""
Unit tests for pdf_service.py

Covers: Markdown to PDF conversion, font detection, markdown cleaning.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.pdf_service import markdown_to_pdf, _clean, _find_msyh


class TestMarkdownCleaning:
    """Tests for the _clean helper that strips inline markdown."""

    def test_bold_italic(self):
        assert _clean("***bold italic***") == "bold italic"

    def test_bold(self):
        assert _clean("**bold text**") == "bold text"
        assert _clean("__bold text__") == "bold text"

    def test_italic(self):
        assert _clean("*italic text*") == "italic text"
        assert _clean("_italic text_") == "italic text"

    def test_inline_code(self):
        assert _clean("`code here`") == "code here"

    def test_links(self):
        assert _clean("[Click me](https://example.com)") == "Click me"

    def test_strikethrough(self):
        assert _clean("~~deleted text~~") == "deleted text"

    def test_images_removed(self):
        # Image syntax: ![alt](url) → alt text only remains if regex misses
        result = _clean("![alt text](image.png)")
        # At minimum, the URL part should be gone
        assert "image.png" not in result
        assert "](" not in result

    def test_plain_text_unchanged(self):
        assert _clean("plain text without markdown") == "plain text without markdown"

    def test_mixed_formatting(self):
        text = "**Important**: read the `config.py` file [here](https://docs.example.com)"
        result = _clean(text)
        assert "Important" in result
        assert "read the" in result
        assert "config.py" in result
        assert "here" in result


class TestFontDetection:
    """Tests for _find_msyh font detection."""

    def test_returns_string_or_none(self):
        result = _find_msyh()
        assert result is None or isinstance(result, str)

    def test_returns_existing_path(self):
        result = _find_msyh()
        if result is not None:
            assert os.path.exists(result)


class TestMarkdownToPDF:
    """Integration tests for markdown_to_pdf."""

    def test_basic_conversion(self, sample_markdown):
        """Convert a full Markdown document to PDF bytes."""
        pdf_bytes = markdown_to_pdf(sample_markdown)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF magic bytes
        assert pdf_bytes[:5] == b"%PDF-"

    def test_empty_markdown(self):
        pdf_bytes = markdown_to_pdf("")
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_title_param(self, sample_markdown):
        pdf_bytes = markdown_to_pdf(sample_markdown, title="Test Doc")
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"

    def test_headings(self):
        md = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6"
        pdf_bytes = markdown_to_pdf(md)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_code_block(self):
        md = """```python
def hello():
    print("Hello, World!")
```"""
        pdf_bytes = markdown_to_pdf(md)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_table(self):
        md = """| Col A | Col B | Col C |
|-------|-------|-------|
| a1    | b1    | c1    |
| a2    | b2    | c2    |"""
        pdf_bytes = markdown_to_pdf(md)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_lists(self):
        md = """- item one
- item two
  - nested one
  - nested two
- item three

1. first
2. second
3. third"""
        pdf_bytes = markdown_to_pdf(md)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_blockquote(self):
        md = "> This is a blockquote\n> with multiple lines"
        pdf_bytes = markdown_to_pdf(md)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_horizontal_rule(self):
        md = "Some text\n\n---\n\nMore text"
        pdf_bytes = markdown_to_pdf(md)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_chinese_text(self):
        md = "# 中文文档\n\n这是一个中文测试文档。\n\n## 功能列表\n\n- 文件上传\n- OCR识别\n- 格式转换"
        pdf_bytes = markdown_to_pdf(md)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_output_is_valid_pdf(self, sample_markdown):
        """Verify the output has basic PDF structure."""
        pdf_bytes = markdown_to_pdf(sample_markdown)
        # PDF must start with %PDF-
        assert pdf_bytes.startswith(b"%PDF-")
        # PDF must have at least one page
        assert b"/Type /Page" in pdf_bytes or b"/Type/Page" in pdf_bytes
        # PDF must end with %%EOF
        assert pdf_bytes.rstrip().endswith(b"%%EOF")
