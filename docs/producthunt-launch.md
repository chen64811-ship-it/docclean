# DocClean — Product Hunt Launch Kit

> **Launch date**: TBD
> **Prepared**: 2026-05-13

---

## 1. Tagline

> 优化原则：一个核心承诺，不堆功能点。

**Primary (40 chars):**
```
Convert documents to Markdown. 100% local.
```

**Backup (55 chars):**
```
Your documents never leave your machine. Drag, drop, done.
```

---

## 2. Short Description

> 优化原则：最短演示路径 — 用户看完就知道怎么上手。

**Primary (209 chars):**
```
docker-compose up → drag in any PDF, Word, Excel, or image → get clean Markdown. All on your machine. GPU-accelerated OCR. Built-in editor. Zero cloud. MIT licensed. Free to use.
```

---

## 3. Full Description

> Markdown support. ~500 words. This is the main body of your Product Hunt listing. Tell the story: what the product does, why you built it, who it's for, and what makes it special.

---

### What is DocClean?

**DocClean turns documents into Markdown. On your machine. That's it.**

Every other converter (Mathpix, Smallpdf, Zamzar) makes you upload files to their cloud first. If you handle contracts, medical records, financial reports, or unpublished research — that's a dealbreaker. DocClean runs on your hardware. Your data never leaves.

**Shortest path from zero to working:**
```bash
docker-compose up
# Drag a PDF into the browser. Get Markdown back.
```

---

### Why Pay for Pro When the Core Is Free?

> **Free = you convert documents. Pro = you build a searchable knowledge base from them.**

The free Community edition does the job: convert, edit, export. If you need to ask questions across hundreds of documents, search by keyword, or compile a book from an outline — that's what Pro unlocks.

---

### What You Can Do

**Drop in any file, get clean Markdown.**
PDFs (even scanned ones), Word, Excel, images — DocClean pulls the text out and cleans it up. No settings to configure. Drag, wait a few seconds, done.

**Edit and export right in the browser.**
Built-in Markdown editor with live preview. Fix formatting, adjust structure, then export to PDF or download as a single file.

**Search your documents like a database.**
Pro tier: DocClean indexes everything you've converted. Search by keyword, or ask questions in plain English ("What was Q3 revenue?") and get answers pulled from your files.

**Compile a book from an outline.**
Drop a Word document with chapter headings, and DocClean auto-matches your converted files to build a structured book. Drag chapters to reorder, edit inline, export as one Markdown file.

**Works with your existing tools.**
REST API for everything. Swagger docs at `/api/docs/`. Integrate into your CI/CD pipeline or build a custom frontend.

---

### Why Privacy Matters

Every cloud converter you upload to is a company that can read your documents. Their privacy policies change. Their servers get breached. For anyone handling sensitive information, that risk is unacceptable.

DocClean makes **zero outbound calls** during conversion. The only optional internet access is the AI Q&A feature, which you connect to your own API key. Everything else runs inside your Docker container, behind your firewall.

---

### Under the Hood (for the curious)

- OCR auto-detects language (English, Chinese, Japanese, Korean, 80+ others) and switches models automatically. GPU makes it 3-5x faster.
- Smart text cleaning that removes garbage without destroying real content — works for any language, not hardcoded for English.
- 67 unit tests, CI on Windows + Linux, Python 3.10/3.11.

---

### Getting Started

```bash
git clone https://github.com/chen64811-ship-it/docclean.git
cd docclean
docker-compose up -d
# Open http://localhost:5000
```

One command. Everything running locally. No account creation. No cloud dependency.

If you want GPU acceleration, swap to `Dockerfile.gpu` in the compose file, uncomment the GPU device reservation, and you're running PaddleOCR on your NVIDIA card.

---

### Who Is This For?

- **Individual developers** who want a free, local document converter with no strings attached
- **Power users** who need RAG search and AI Q&A over their document collections
- **Law firms, hospitals, banks** that cannot legally upload client/patient/customer data to cloud services
- **Researchers** working with unpublished data who need OCR + search without the cloud
- **Technical writers and authors** who want to compile scattered Markdown into structured books

---

### Pricing

> **The free version does the job. Pro turns your document folder into something you can ask questions to.**

| Tier | Price | What You Get |
|------|-------|---------------|
| **Community** | Free (MIT) | PDF/Image OCR, Word/Excel/MD conversion, Markdown editor, PDF export |
| **Pro** | $49/mo or $199/yr | Everything in Community + search across all documents + ask questions in plain English + batch processing |
| **Enterprise** | $999/yr | Everything in Pro + full source code + private deployment help + SLA |

[Get Started Free →](#) &nbsp;&nbsp; [Buy Pro →](#) &nbsp;&nbsp; [Contact Sales →](#)

---

## 4. First Comment

> This is the comment you post IMMEDIATELY after launching on Product Hunt. It should be personal, tell the origin story, and invite conversation. Product Hunt's community values authenticity and founder presence.

---

Hey Product Hunt! Maker here.

I built DocClean because I was genuinely frustrated. I work with documents that contain sensitive business information, and every time I needed to convert a PDF or image to Markdown, the answer was always "upload it to Mathpix" or "send it to Smallpdf." That's insane. Why should I ship my private documents to someone else's server just to get clean text out of them?

So I built the thing I wanted to exist.

**The problem with every other document converter:**

They all work the same way — you upload your file, they process it in the cloud, and you download the result. That's fine for memes and public content. It's a dealbreaker for:
- Legal documents with privileged client information
- Medical records covered by HIPAA or equivalent
- Financial projections before earnings calls
- Unpublished research and manuscripts
- Government and defense documents
- Literally anything covered by NDA

**What I built instead:**

DocClean runs entirely on your own hardware. It's a Docker container. You `docker-compose up` and you have a complete document processing pipeline — OCR, text extraction, cleaning, Markdown conversion, editor, knowledge base, and book compiler — all behind your firewall. Zero data leaves your machine.

**What makes it technically interesting (I think):**

- **PaddleOCR instead of Tesseract.** Tesseract is the default for most open-source OCR pipelines, and it's terrible with Chinese, Japanese, and Korean text. PaddleOCR (from Baidu) is dramatically better — it matches or exceeds Tesseract on Latin scripts and absolutely crushes it on CJK. The downside has always been setup complexity. I solved that with Docker.
- **Language-adaptive OCR.** The engine auto-detects whether a document is CJK or Latin-dominant and switches models accordingly. No manual configuration needed.
- **Full pipeline, not just conversion.** Most tools stop at "here's some text." DocClean gives you a Markdown editor with live preview, a RAG knowledge base with TF-IDF search + LLM Q&A, and a Notion-style book compiler that auto-matches content to a Word outline.
- **GPU acceleration out of the box.** If you have an NVIDIA GPU, DocClean uses it. 3-5x faster OCR. If you don't, CPU fallback works fine.

**Some honest context:**

This started as a personal tool for my own workflow. I open-sourced it because I think "local-first" and "privacy-first" are going to be defining differentiators for the next generation of AI tools, and more people should have access to this approach. I'm a solo developer, this is my first product launch, and I'm sure there are rough edges.

**What I'd love feedback on:**
- What would make you switch from your current document converter?
- What features would justify the Pro price for you?
- Is the "privacy-first" angle actually compelling, or is it just something I care about?

I'll be here all day answering questions. Fire away — harsh feedback very welcome.

**Quick try:**
```bash
git clone https://github.com/chen64811-ship-it/docclean
docker-compose up
# Open http://localhost:5000
```

---

## 5. Topic Tags

> Product Hunt lets you select up to 5 topic tags. Choose strategically for maximum visibility in relevant categories.

1. **Developer Tools** — Core category. DocClean is a tool developers use in their workflow.
2. **Open Source** — Essential tag. MIT licensed, GitHub public, community contributions welcome.
3. **Privacy** — Key differentiator. Maps to the growing "privacy-first" movement on PH.
4. **Productivity** — Broad reach. Document processing saves time, fits the productivity narrative.
5. **API** — For API-first positioning. Swagger docs, REST endpoints, embeddable pipeline.

**Alternative tags** (swap in if one of the above feels wrong):
- **Artificial Intelligence** — If emphasizing RAG + LLM Q&A (but might set wrong expectations)
- **SaaS** — If emphasizing the UI polish and subscription model
- **Writing** — If emphasizing the book compiler and Markdown editor

---

## 6. Screenshot Descriptions

> Product Hunt requires at least 3 screenshots, recommends 5-8. Each needs a descriptive caption. Screenshots should be 1270x760 PNG. These are the descriptions you'll write next to each image.

---

### Screenshot 1: Dashboard + File Upload

**Caption:** "Drag and drop any document — PDF, Word, Excel, or image. Upload with real-time progress. File cards show status (Parsing, Done, Error) with automatic refresh. Select multiple files for batch download or delete."

**What to show:**
- The main dashboard with the upload zone prominently visible
- Several file cards in the sidebar showing different status badges (green "Done", amber "Parsing")
- Upload zone with dashed border and the supported format badges (PDF, DOCX, XLSX, PNG, JPG)
- Overall clean, professional SaaS aesthetic — Inter font, indigo accents, card shadows
- Batch selection checkboxes visible on 2-3 file cards

**Setup for this screenshot:**
1. Have 5-6 files already uploaded with mixed statuses
2. One file should show "Error" (red badge) to demonstrate error handling
3. Capture the full browser window at 1270x760

---

### Screenshot 2: PDF + Markdown Split View

**Caption:** "Left: original PDF with page navigation and zoom controls. Right: extracted Markdown source with syntax highlighting and live rendered preview below. Edit in place and see changes instantly. Original document and converted output side by side."

**What to show:**
- Split-pane layout: PDF viewer on the left, Markdown editor + preview on the right
- PDF should be a multi-page document, navigator showing thumbnails or page numbers
- Markdown source in EasyMDE editor with visible formatting (headings, bold, lists)
- Live preview panel below showing the rendered Markdown output
- The document should have meaningful, professional-looking content (not lorem ipsum)
- Zoom controls and page navigation clearly visible

**Setup for this screenshot:**
1. Upload a professionally-formatted PDF (a report or whitepaper, not generic text)
2. Wait for parsing to complete
3. Click the file to open the split view
4. Adjust the panes so both PDF and Markdown are clearly readable

---

### Screenshot 3: Knowledge Base + AI Q&A

**Caption:** "Turn your document collection into a queryable knowledge base. Tree view on the left shows document structure. TF-IDF search finds relevant chunks across all files. Natural language Q&A powered by any OpenAI-compatible LLM — ask questions about your documents and get answers with source references."

**What to show:**
- Knowledge base view with file tree on the left showing categorized documents
- Search bar at the top with a query already typed (e.g., "revenue projection 2025")
- Search results highlighted in the center content panel
- Q&A panel at the bottom showing a conversation: user asks a question, AI responds with a detailed answer that references specific documents
- Configuration panel showing LLM settings (model, API endpoint) visible but collapsed

**Setup for this screenshot:**
1. Upload and convert several documents (ideally 5-10)
2. Run AI classification if available to create the tree structure
3. Perform a search query that returns multiple results
4. Ask the AI a question about the documents
5. Capture while the Q&A response is visible

---

### Screenshot 4: Book Compiler — Notion-Style Editor

**Caption:** "Drop a Word outline and DocClean auto-matches your converted Markdown files to compile a complete book. Rearrange chapters with drag-and-drop block handles. Edit content inline. One-click export to a single Markdown file. Think Notion, but for book compilation."

**What to show:**
- The block editor with multiple sections visible
- Drag handles (six-dot grids) on the left of each block
- Clear heading hierarchy (H1 for chapters, H2 for sections)
- Mixed content types: headings, paragraphs, bullet lists, maybe a code block
- The outline structure visible in a sidebar or breadcrumb
- Export/download button prominently visible

**Setup for this screenshot:**
1. Prepare a Word outline document with multiple chapters
2. Have converted Markdown files that match the outline content
3. Run the book compiler
4. Open the block editor view
5. Ensure several blocks are expanded to show content

---

### Screenshot 5: Swagger API Documentation

**Caption:** "15+ REST API endpoints with interactive Swagger/OpenAPI documentation. Upload files, trigger conversion, query the knowledge base, compile books — all programmatically. Integrate DocClean into your CI/CD pipelines, build custom frontends, or automate document processing at scale."

**What to show:**
- The Swagger UI page at `/api/docs/` with all endpoints listed
- At least 3-4 endpoint groups expanded showing parameters and response schemas
- The "Try it out" button visible on one endpoint
- Clean, readable endpoint descriptions
- The API base URL visible

**Setup for this screenshot:**
1. Navigate to `http://localhost:5000/api/docs/`
2. Expand a few endpoint groups (Upload, Knowledge Base, Book Compiler)
3. Keep the page scrolled so the most interesting endpoints are visible
4. Capture at 1270x760

---

## Appendix: Launch Script (What to Do and When)

### One Week Before Launch

- [ ] Set GitHub repository to Public
- [ ] Verify all README links are working
- [ ] Push Docker image to Docker Hub (`docker push yourorg/docclean:latest`)
- [ ] Create Product Hunt "Coming Soon" page (pre-launch buzz)
- [ ] Take all 5 screenshots (1270x760, PNG format, compress to <1MB each)
- [ ] Record 90-second demo video (upload to YouTube as Unlisted)
- [ ] Set up Gumroad product page for Pro/Enterprise tiers
- [ ] Generate 20 promo license keys for early users
- [ ] Draft Reddit posts (r/selfhosted, r/MachineLearning)
- [ ] Draft Hacker News Show HN post
- [ ] Verify Twitter/X account is active (buyers check maker credibility)

### Launch Day (Tuesday, Wednesday, or Thursday)

1. **[00:01 PST / 15:01 Beijing]** Publish on Product Hunt
2. **[Immediately]** Post your First Comment (see Section 4)
3. **[Simultaneously]** Submit to Hacker News (Show HN)
4. **[Simultaneously]** Post on r/selfhosted
5. **[+1 hour]** Post on r/MachineLearning
6. **[+2 hours]** Post on r/programming
7. **[All day]** Reply to every comment on Product Hunt, HN, and Reddit within 30 minutes
8. **[End of day]** Tally votes, stars, and feedback. Respond to any GitHub issues created.

### First Week After Launch

- [ ] Reply to every GitHub issue within 24 hours
- [ ] Send free Pro license keys to top 10 most helpful commenters
- [ ] Write "How I built DocClean" technical blog post
- [ ] Publish post-launch retrospective on r/SideProject
- [ ] Triangulate feature requests and prioritize roadmap
- [ ] Push at least one bug fix release (shows momentum)

### First Month After Launch

- [ ] Evaluate Pro vs Enterprise demand (decide monetization focus)
- [ ] If enterprise inquiries arrive, prepare enterprise case study page
- [ ] Monthly Docker image update (dependency refresh + bug fixes)
- [ ] Consider HackerNews "Show HN" re-post with new features

---

## Core Messaging Pillars (Use Everywhere)

These four phrases should appear consistently across your Product Hunt page, README, website, social posts, and launch comments:

1. **"Your documents never leave your machine."**
2. **"One docker-compose up and you're done."**
3. **"Privacy-first document intelligence."**
4. **"GPU-accelerated, self-hosted, MIT licensed."**

---

> **All copy is written for a Western, English-speaking developer audience.** The messaging emphasizes privacy (the key differentiator), local-first architecture, technical sophistication (PaddleOCR > Tesseract, GPU acceleration), and the "one command" simplicity. The tone is direct, confident, and authentic — matching Product Hunt community expectations.
