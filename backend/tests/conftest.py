import os
import sys
import json
import tempfile

# Ensure backend modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory, clean up after test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_markdown():
    """A representative Markdown document for PDF generation tests."""
    return """# Welcome to DocClean

## Overview

DocClean is a **privacy-first** document intelligence tool.

### Features

- PDF OCR with GPU acceleration
- Word and Excel extraction
- Markdown editor with live preview

### Code Example

```python
from docclean import convert

result = convert("document.pdf")
print(result.markdown)
```

### Data Table

| Feature | Status | Notes |
|---------|--------|-------|
| OCR | Done | PaddleOCR GPU |
| Export | Done | Markdown + PDF |
| RAG | Done | TF-IDF + LLM |

> Your documents never leave your server.
> That is the core promise of DocClean.

---

*End of document*
"""


@pytest.fixture
def sample_chinese_text():
    """Chinese text sample for language detection."""
    return "本文档介绍了系统的使用方法，包括文件上传、格式转换、数据清洗等核心功能。用户可以通过简单的操作完成复杂的文档处理任务，大大提升工作效率。"


@pytest.fixture
def sample_english_text():
    """English text sample for language detection."""
    return "This document describes the system's core features including file upload, format conversion, and data cleaning. Users can accomplish complex document processing tasks through simple operations, greatly improving work efficiency."


@pytest.fixture
def sample_mixed_text():
    """Mixed Chinese-English text for language detection."""
    return "This document 介绍了 DocClean 的 OCR 引擎如何 work with both English and Chinese text seamlessly across different document formats."
