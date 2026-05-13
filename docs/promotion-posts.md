# DocClean — 海外推广发布帖

> 准备好后复制粘贴即可发布。日期待定。

---

## 1. Hacker News — Show HN

**标题：** Show HN: DocClean — Self-hosted doc to Markdown converter. Zero cloud, GPU OCR

**发布时间：** 与 Product Hunt 同一天，北京时间 15:00（对应 PST 00:01）

**链接：** https://news.ycombinator.com/submit

**正文：**

```
DocClean is a privacy-first document converter that runs entirely on your own
hardware. PDF, Word, Excel, images → clean Markdown. GPU-accelerated OCR via
PaddleOCR. Built-in editor. RAG knowledge base. Book compiler. One docker-
compose up and you're done.

Why I built this:

Every major document converter (Mathpix, Smallpdf, Docparser, Zamzar) is a
cloud service. You upload your documents, they process them on their servers,
you download the result. For most people that's fine. For lawyers, doctors,
bankers, and researchers — it's a non-starter. You can't upload client
contracts, patient records, or unpublished research to a random API.

DocClean processes everything locally. Zero outbound network calls in the
core conversion pipeline. The only optional external API is the LLM
integration for AI Q&A, which you control completely.

Technical details:
- OCR: PaddleOCR (Baidu's engine), not Tesseract. Much better for Chinese/
  Japanese/Korean. Auto-detects script type and switches models.
- GPU: NVIDIA CUDA support. 3-5x faster on GPU. CPU fallback works fine.
- Stack: Python/Flask backend, vanilla JS frontend, Docker.
- License: MIT (Community tier). Pro/Enterprise tiers available.

GitHub: https://github.com/chen64811-ship-it/docclean
Docker: docker pull xingyu2003/docclean

I'm a solo developer and this is my first public launch. Harsh feedback very
welcome — especially on the privacy/local-first approach and what would make
you switch from your current workflow.
```

---

## 2. Reddit — r/selfhosted

**标题：** I built DocClean — a self-hosted document converter that never uploads your files to the cloud

**发布时间：** Product Hunt 发布后立即发布

**链接：** https://reddit.com/r/selfhosted/submit

**正文：**

```
Hey r/selfhosted — long time lurker, first time sharing something I built.

**The Problem:**
Every time I needed to convert a PDF or image to Markdown, the answer was
"upload it to Mathpix" or "use Smallpdf." I work with documents that contain
sensitive business information, and the idea of shipping them to someone
else's server just to get clean text felt insane.

**What I Built:**
DocClean is a Docker container that does document conversion entirely on your
hardware. One `docker-compose up` and you have:
- PDF, Word, Excel, image → Markdown conversion
- GPU-accelerated OCR (PaddleOCR, not Tesseract)
- Built-in Markdown editor with live preview
- RAG knowledge base with TF-IDF search + LLM Q&A
- Book compiler (Word outline → compiled Markdown)
- REST API with Swagger docs

**Privacy:**
Zero outbound network calls in the conversion pipeline. Your documents never
leave your machine. The only external call is optional — the LLM API for AI
Q&A, which you configure yourself.

**Tech Stack:**
Python/Flask + vanilla JS + Docker. MIT license for the Community tier.

GitHub: https://github.com/chen64811-ship-it/docclean
Docker Hub: https://hub.docker.com/r/xingyu2003/docclean

Would love feedback from this community especially — you all are exactly the
target audience. What would make you switch from your current setup? What's
missing?
```

---

## 3. Reddit — r/MachineLearning

**标题：** [P] DocClean: PaddleOCR-based document OCR pipeline with GPU acceleration, fully self-hosted

**发布时间：** Product Hunt 发布后 1 小时

**链接：** https://reddit.com/r/MachineLearning/submit

**正文：**

```
I built a self-hosted document processing pipeline that uses PaddleOCR for
text extraction, and wanted to share some implementation details that might
interest this community.

**Why PaddleOCR over Tesseract:**
Tesseract is the default in most open-source OCR pipelines, but its accuracy
on Chinese, Japanese, and Korean text is poor. PaddleOCR (Baidu's engine)
matches or exceeds Tesseract on Latin scripts and dramatically outperforms it
on CJK. The tradeoff has always been deployment complexity — PaddleOCR has
heavy dependencies (PaddlePaddle, CUDA libs, model downloads). I solved this
by containerizing everything in Docker.

**Language-Adaptive OCR:**
The engine auto-detects whether a document is CJK-dominant or Latin-dominant
using character set analysis, then switches PaddleOCR models accordingly.
No manual configuration needed. Works for 80+ languages.

**GPU Acceleration:**
NVIDIA CUDA support with automatic fallback to CPU. Per-language model
instance caching to avoid repeated model reloads. 3-5x speedup on GPU.

**Garbage Text Filtering:**
Language-agnostic text cleaning pipeline that removes OCR artifacts without
hardcoded rules for any specific language. Uses statistical filtering rather
than regex-based approaches that break on non-English text.

**Stack:**
Python/Flask, PaddleOCR, Docker, vanilla JS frontend. MIT license.

GitHub: https://github.com/chen64811-ship-it/docclean
Paper/demo: (product page link)

Not a research contribution — this is an engineering project. But I'd love
feedback on the OCR pipeline design and whether there are better approaches
for the language-adaptive model switching.
```

---

## 4. Reddit — r/programming

**标题：** DocClean: A self-hosted, privacy-first document to Markdown converter — MIT licensed

**发布时间：** Product Hunt 发布后 2 小时

**链接：** https://reddit.com/r/programming/submit

**正文：**

```
I built a tool that converts PDF, Word, Excel, and images into clean Markdown
— running entirely on your own hardware. Thought r/programming might find it
interesting because:

1. It solves a real problem: cloud document converters are privacy nightmares
   for anyone handling sensitive documents.

2. It uses PaddleOCR (Baidu's engine) instead of Tesseract, with automatic
   language detection and GPU acceleration.

3. It's a single Docker container: `docker-compose up` and you have a complete
   pipeline — OCR, text extraction, Markdown editor, RAG knowledge base, and a
   Notion-style book compiler.

4. REST API with Swagger docs for integration into existing workflows.

5. MIT licensed. Free tier includes the core conversion pipeline.

GitHub: https://github.com/chen64811-ship-it/docclean
Docker: docker pull xingyu2003/docclean

I'm a solo dev and this is my first public project. Code review / feedback on
architecture, security, and OCR pipeline very welcome.
```

---

## 发布节奏（北京时间）

| 时间 | 动作 |
|------|------|
| 15:00 (PST 00:01) | Product Hunt 发布 + 第一贴评论 |
| 15:00 | Hacker News Show HN 发布 |
| 15:00 | Reddit r/selfhosted 发布 |
| 16:00 | Reddit r/MachineLearning 发布 |
| 17:00 | Reddit r/programming 发布 |
| 全天 | 30 分钟内回复所有评论 |
| 当天结束时 | 统计票数、星标、反馈 |

---

## 发布前检查清单

- [ ] GitHub 仓库设为 Public
- [ ] 所有 README 链接可用
- [ ] Docker 镜像已推送到 Docker Hub（`xingyu2003/docclean:latest`）
- [ ] Product Hunt "Coming Soon" 页面建好
- [ ] 5 张截图已准备好（1270x760 PNG，每张 <1MB）
- [ ] 90 秒演示视频上传 YouTube（Unlisted）
- [ ] Gumroad 商品页面建好（Pro/Enterprise 付费）
- [ ] 20 个免费推广 License 已生成
- [ ] 检查 Twitter/X 账号活跃度（买家会看开发者可信度）
