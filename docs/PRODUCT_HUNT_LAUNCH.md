# DocClean — Product Hunt Launch Kit

> 发布日期：待定
> 准备日期：2026-05-10

---

## 一、Product Hunt 页面

### 1.1 Tagline（一句话介绍）

```
DocClean — Privacy-first document to Markdown converter. OCR with GPU, on your own machine.
```

备选：
```
Your documents never leave your server. PDF/Word/Excel → clean Markdown, with GPU-accelerated OCR.
```

### 1.2 Description（产品描述）

```
DocClean is a self-hosted document intelligence tool that converts PDF, Word, Excel,
and images into clean, editable Markdown — all running locally on your machine.

🔒 Privacy-First: Your documents never touch a third-party server. Everything runs
   on your hardware — critical for legal, healthcare, banking, and anyone who values
   data sovereignty.

🚀 GPU-Accelerated OCR: Powered by PaddleOCR with CUDA GPU support. Extracts text
   from scanned PDFs and images with industry-leading accuracy, especially for
   Chinese-English bilingual documents.

📦 All-in-One: PDF (text + scanned) → Word → Excel → Images → Markdown. No more
   switching between 5 different tools. Built-in Markdown editor with live preview.

🧠 AI Knowledge Base: TF-IDF search + LLM Q&A over your documents. Turn your
   document collection into a queryable knowledge base. Supports any OpenAI-compatible API.

📖 Book Compiler: Drop a Word outline, auto-match your converted Markdown files,
   compile into a structured book. Notion-style drag-and-drop editor included.

### Why I Built This

I was frustrated with uploading sensitive documents to cloud converters just to get
them into Markdown. Mathpix, Docparser, Smallpdf — they all require sending your data
to someone else's server. For lawyers, doctors, bankers, that's a non-starter.

DocClean solves this: one `docker-compose up` and you have a complete document
processing pipeline running locally, with GPU acceleration for OCR.

### Tech Stack
Python Flask · PaddleOCR GPU · SQLite · Vanilla HTML/CSS/JS · Docker
```

### 1.3 First Comment（发布后第一条评论）

```
Hey Product Hunt! 👋

I built DocClean because I needed a document converter that (1) runs locally
and (2) actually handles Chinese-English bilingual documents well.

### The Problem
- Cloud converters (Mathpix, Docparser, Smallpdf) require uploading sensitive docs
  to their servers — a dealbreaker for legal/healthcare/banking
- Open-source alternatives (Marker) are CLI-only, no GUI, no OCR for non-English text
- Existing OCR tools (Tesseract) struggle badly with Chinese characters

### What Makes DocClean Different
1. **100% local processing** — Docker image, your GPU, your data
2. **PaddleOCR** — Baidu's OCR engine, significantly better than Tesseract for CJK text
3. **Full pipeline** — PDF → OCR → clean Markdown → editor → PDF export
4. **AI features** — RAG knowledge base + LLM Q&A over your documents
5. **Book compiler** — Word outline → auto-matched Markdown → compiled book

### Pricing
- **Community** (free, MIT license): PDF/Image OCR, Markdown editor, basic export
- **Pro** ($49/mo or $199/yr): RAG knowledge base, AI Q&A, batch processing
- **Enterprise** ($999/yr): Source code, private deployment support, SLA

### Try It
```bash
git clone https://github.com/[your-org]/docclean
docker-compose up
# Open http://localhost:5000
```

Happy to answer any questions! I'll be here all day.
```

### 1.4 Screenshot Plan（5 张截图）

| # | 内容 | 说明 | 画面要求 |
|---|------|------|----------|
| 1 | **Upload + File List** | Sidebar with file cards, upload zone, batch mode | 拖拽上传区 + 文件列表（状态标签）+ 批量选择 |
| 2 | **PDF + Markdown Split View** | Left: original PDF with page navigation. Right: Markdown source + live preview | 分栏视图，PDF 清晰可见 + Markdown 渲染效果 |
| 3 | **RAG Knowledge Base + Q&A** | Tree view (left), content (center), AI Q&A panel (bottom) | 树状大纲 + 搜索结果高亮 + Q&A 对话 |
| 4 | **Book Compiler (Notion-style Editor)** | Draggable blocks with handles, headings, code blocks | Notion 风格编辑器，展示拖拽手柄、标题层级、代码块 |
| 5 | **Swagger API Docs** | `/api/docs/` page with endpoints | 交互式 API 文档，展示 15+ 端点 |

### 1.5 截图捕获指南

```bash
# 1. 启动 Docker
docker-compose up

# 2. 上传测试文件（准备一个扫描版 PDF + 一个 Word + 一个 Excel）
#    - 截图1：上传完成后，展示文件列表
#    - 截图2：点击 PDF 文件，展示 PDF+Markdown 双栏

# 3. AI 分类 + 知识库
#    - 点击 AI Classify 按钮，等待分类完成
#    - 切换到 KB 视图
#    - 截图3：展示树状结构 + Q&A 面板

# 4. 书籍编译
#    - 点击 Compile Book
#    - 编译完成后点击 View Online
#    - 截图4：展示 Notion 风格编辑器

# 5. Swagger
#    - 打开 http://localhost:5000/api/docs/
#    - 截图5：展示交互式 API 文档
```

---

## 二、Demo Video Script（2 分钟）

```
[0:00-0:10] 标题画面
DocClean — Privacy-First Document to Markdown Converter
"Your documents never leave your server."

[0:10-0:25] 启动
Terminal: docker-compose up
→ Open browser: localhost:5000
"One command. Everything running locally."

[0:25-0:45] 文件上传 + 转换
Drag & drop PDF → upload progress → file list auto-refresh
→ "Parsing" status → "Done" with green badge
"Supports PDF, Word, Excel, images — all processed on your GPU."

[0:45-1:05] PDF + Markdown 双栏
Click file → left: original PDF with page thumbnails
→ right: extracted Markdown source + live preview
Zoom controls, scroll sync, edit-in-place
"Original PDF on the left, clean Markdown on the right. Edit and preview in real-time."

[1:05-1:25] AI 知识库
Switch to KB view → AI Classify button
→ Auto-detected categories → tree structure
→ Search: "revenue" → highlighted results
→ Q&A: "What was the total revenue in Q3?" → LLM answer
"Turn your documents into a queryable knowledge base. Ask questions, get answers."

[1:25-1:45] Book Compiler
Compile Book → auto-detects Word outline
→ matches content → Notion-style editor with drag-and-drop blocks
→ Export as single Markdown or PDF
"Compile scattered documents into a structured book. Drag, reorder, edit — just like Notion."

[1:45-1:55] 结尾
Docker logo + GitHub logo
"MIT licensed. Self-hosted. Privacy-first."
docker-compose up
→ GitHub URL + Product Hunt badge

[1:55-2:00] CTA
"Try it free at [URL]"
"Available on Product Hunt today 🚀"
```

### Recording Tips
- 用 OBS Studio 录制（免费开源）
- 分辨率：1920×1080，30fps
- 窗口模式：只录制浏览器窗口 + 终端窗口
- 鼠标光标高亮：使用 OBS 的光标高亮插件
- 不需要旁白，用文字叠加层即可（海外用户习惯看字幕）
- 背景音乐：选择无版权的轻电子音乐（YouTube Audio Library）

---

## 三、Pricing Page

### 3.1 定价表（嵌入 README 或独立页面）

```markdown
## Pricing

| Feature | Community | Pro | Enterprise |
|---------|-----------|-----|-------------|
| **Price** | Free | **$49/mo** or **$199/yr** | **$999/yr** |
| PDF/Image OCR | ✅ | ✅ | ✅ |
| Word/Excel/Markdown | ✅ | ✅ | ✅ |
| Markdown Editor | ✅ | ✅ | ✅ |
| PDF Export | ✅ | ✅ | ✅ |
| Knowledge Base (RAG) | — | ✅ | ✅ |
| AI Q&A (LLM) | — | ✅ | ✅ |
| Batch Processing | — | ✅ | ✅ |
| Book Compiler | — | — | ✅ |
| API Access | — | — | ✅ |
| Source Code | ✅ (MIT) | ✅ (MIT) | ✅ (Full) |
| Private Deployment Support | — | — | ✅ |
| SLA | — | — | ✅ |
| **Best for** | Individual devs, hobbyists | Power users, small teams | Law firms, hospitals, banks |

[Get Started Free →](#quick-start)    [Buy Pro →](#)    [Contact Sales →](#)
```

### 3.2 定价页 HTML（独立 pricing 页面）

If you want a dedicated pricing page, create `frontend/pricing.html` with the above table styled using the same CSS variables from the main app.

### 3.3 收款方案

推荐起步方案：**Gumroad**
- 支持 License Key 自动分发
- 抽成 10%（高于 Stripe 但免去税务合规的麻烦）
- 操作步骤：
  1. 注册 Gumroad 账号
  2. 创建产品 → 选择 "Software License"
  3. 上传 License Key CSV（用 `generate_license.py --count 100` 生成）
  4. 设置价格 + 描述
  5. 获取链接，嵌入 README 和 Product Hunt 页面

---

## 四、Reddit / Hacker News 推广文案

### 4.1 r/selfhosted 帖子

```markdown
Title: I built a self-hosted document-to-Markdown converter with GPU OCR.
       Your documents never leave your server.

Body:

After getting frustrated with uploading sensitive work documents to cloud
converters, I built DocClean — a Docker-based document processing pipeline
that runs entirely on your own hardware.

**What it does:**
- Converts PDF (text + scanned), Word, Excel, images → clean Markdown
- GPU-accelerated OCR via PaddleOCR (CUDA 11.8)
- Built-in Markdown editor with live preview
- RAG knowledge base with LLM Q&A over your documents
- Notion-style book compiler from Word outlines

**Privacy angle:**
All processing is local. No API calls to third-party services for the core
conversion pipeline. Your documents stay on your machine. This is the main
reason I built it — I work with sensitive data that can't leave the network.

**Tech stack:**
Python Flask + PaddleOCR GPU + SQLite + Vanilla JS frontend. MIT licensed.

**Try it:**
```bash
git clone https://github.com/[org]/docclean
docker-compose up
# Open http://localhost:5000
```

Happy to answer questions. Been working on this for a few months,
just finished making it production-ready for non-Chinese users.

[Link to GitHub]
```

### 4.2 r/MachineLearning 帖子

```markdown
Title: DocClean — Open-source document OCR pipeline with PaddleOCR GPU
       for multilingual text extraction

Body:

Sharing a project I've been working on: a complete document-to-Markdown
conversion pipeline optimized for bilingual (Chinese-English) documents.

**Why PaddleOCR?**
Most open-source OCR pipelines use Tesseract. PaddleOCR from Baidu
significantly outperforms Tesseract on CJK text (Chinese, Japanese, Korean)
while matching or exceeding on Latin scripts. The downside has always been
setup complexity — we solved this with Docker.

**Pipeline:**
1. PDF → pdfminer text extraction (for digital PDFs)
2. Fallback → PaddleOCR GPU for scanned pages
3. Language auto-detection (CJK ratio → `lang="ch"`, else `lang="en"`)
4. Garbage text filtering (language-agnostic, not Chinese-only like most tools)
5. Output → clean Markdown

**What's interesting for ML folks:**
- TF-IDF + LLM RAG pipeline for document Q&A
- LLM-powered outline classification for any industry (zero-shot)
- Language-adaptive OCR with per-language model caching

**GitHub:** [link]
**Demo:** docker-compose up → localhost:5000

Open to feedback on the OCR pipeline. The language detection and garbage
filtering logic is in `backend/services/ocr_service.py` and
`backend/services/extractor_service.py`.
```

### 4.3 Hacker News — Show HN

```markdown
Title: Show HN: DocClean — Self-hosted document to Markdown (GPU OCR, privacy-first)

URL: https://github.com/[org]/docclean

Body:

Hi HN,

I built DocClean because I needed to convert PDFs, Word docs, and scanned
images into clean Markdown — without uploading anything to the cloud.

**The privacy problem with document converters:**
Mathpix, Docparser, Smallpdf, Zamzar — they all process your documents on
their servers. For anyone in legal, healthcare, finance, or defense, this
is a complete non-starter. You simply cannot upload client documents to a
random third-party API.

**What DocClean does differently:**
- Runs entirely on your machine (Docker, one command)
- GPU-accelerated OCR (PaddleOCR + CUDA)
- Converts PDF/Word/Excel/Images → editable Markdown
- Built-in editor with live preview
- RAG knowledge base + LLM Q&A over your docs
- Book compiler: Word outline → auto-matched content → compiled book

**Technical highlights:**
- Language-adaptive OCR (auto-detects CJK vs Latin, switches models)
- HMAC-SHA256 license system for commercial tiers
- OpenAPI/Swagger docs on /api/docs/
- 67-unit-test suite, GitHub Actions CI (Windows + Linux, py3.10/3.11)

**Why I think this is worth your attention:**
"Local-first" and "privacy-first" are becoming major differentiators in
the AI tools space. People are waking up to the fact that every cloud API
call is a data exfiltration risk. DocClean proves you can have powerful
document AI without the cloud.

**Pricing:**
- Community: Free (MIT license)
- Pro: $49/mo (RAG + AI Q&A + batch)
- Enterprise: $999/yr (source code + deployment support + SLA)

**Quick start:**
```bash
git clone https://github.com/[org]/docclean
docker-compose up
```

I'd love feedback from the HN community. This is my first product launch
and I'm sure there are things I'm missing. What would make you use this
over cloud alternatives? What features would justify the Pro price for you?

Thanks for reading!
```

---

## 五、Launch Checklist（上线清单）

### 上线前（提前 1 周）

- [ ] GitHub 仓库设为 Public
- [ ] README 确认所有链接可点击
- [ ] Docker Hub 推送镜像（`docker push [org]/docclean:latest`）
- [ ] 截图拍摄（5 张，1920×1080，PNG 格式）
- [ ] 演示视频录制 + 上传 YouTube（设为 Unlisted）
- [ ] Product Hunt 页面草稿（可提前创建，设置为 "Coming Soon"）
- [ ] 定价页面确认（Gumroad 产品链接就绪）
- [ ] 准备 10 个 License Key（给早期用户免费发 Pro Key 攒口碑）

### 上线当天（按顺序）

1. **[08:00 UTC+8 / 00:00 UTC]** Product Hunt 发布（选在周二/周三/周四）
2. **[同时]** Reddit r/selfhosted 发帖
3. **[同时]** Hacker News Show HN 发帖
4. **[1小时后]** Reddit r/MachineLearning 发帖
5. **[持续]** 回复所有评论和 Issue，保持活跃
6. **[当天结束]** 总结反馈，记录 feature requests

### 上线后（第一周）

- [ ] 每天回复 GitHub Issues
- [ ] 整理用户反馈，排序优先级
- [ ] 给活跃用户发免费 Pro License Key
- [ ] 写一篇 "How I built DocClean" 技术博客
- [ ] 在 r/programming 发技术深潜帖
- [ ] 记录下载量 / GitHub Stars / Product Hunt 投票数

### 上线后（第一个月）

- [ ] 根据反馈决定是深挖路线 A（Pro 订阅）还是路线 C（私有化部署）
- [ ] 如果企业咨询多，准备企业案例页面
- [ ] 每月更新一次 Docker 镜像（依赖更新 + bug 修复）

---

## 六、Maker Profile（Product Hunt 个人资料）

- **Name**: [你的名字，建议用英文名]
- **Headline**: Building privacy-first developer tools
- **Bio**: Indie developer focused on local-first, privacy-respecting software.
  Built DocClean to solve my own document conversion needs without the cloud.
- **Twitter/X**: [你的 Twitter 账号，海外社区必备]
- **GitHub**: [你的 GitHub 主页]
- **Website**: [产品官网或 GitHub Pages]

> 建议：注册一个 Twitter/X 账号，在海外开发者社区保持活跃。Product Hunt 的投票者通常会查看 Maker 的 Twitter 账号来评估可信度。

---

## 七、Product Hunt Launch 时间表建议

最佳发布时间：**周二/周三/周四 PST 凌晨 00:01**（即北京时间下午 15:01）

- Product Hunt 以 PST 时区为基准，每天重置投票
- 凌晨发布意味着你的产品一整天都在首页
- 避免周五/周末发布（新闻疲劳，投票量低）
- 避免周一发布（竞争激烈，大公司通常周一发布）

---

> 所有文案已按照 "Privacy-First + Local-First" 核心信息展开。
>
> 关键话术（在所有渠道反复出现）：
> - "Your documents never leave your server"
> - "One docker-compose up"
> - "Privacy-first document intelligence"
> - "GPU-accelerated, self-hosted"
