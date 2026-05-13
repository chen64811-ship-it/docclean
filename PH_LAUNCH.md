# Product Hunt Launch Checklist — DocClean

## Pre-Launch (Day -7 → Day -1)

### Build presence
- [x] GitHub repo: https://github.com/chen64811-ship-it/docclean
- [ ] Add a demo GIF/screenshot to README (record converting a PDF → Markdown)
- [ ] Add topics to GitHub repo: `self-hosted` `privacy` `ocr` `document-converter` `pdf` `markdown`
- [ ] Create a product logo (use Figma/Canva, 240x240)
- [ ] Set up a simple landing page or point to GitHub README

### Build hype
- [ ] Post a teaser on Twitter/X, Reddit r/selfhosted, Hacker News
- [ ] Find a Hunter on Product Hunt (someone with followers to hunt your product)
- [ ] Prepare 3-5 demo screenshots (upload → conversion → editor → knowledge base)

## Launch Day (Tuesday or Wednesday best)

### Product Hunt Post

**Title (max 40 chars):**
> DocClean — Privacy-first document converter that runs on your machine

**Tagline (max 60 chars):**
> Convert PDF/Word/Excel/Images to Markdown. 100% local. No cloud.

**Description (max 260 chars):**
> Open-source document to Markdown converter with OCR, GPU acceleration, and AI knowledge base. All processing happens on your own server — your documents never leave your machine. PDF, Word, Excel, images → clean Markdown in seconds.

**Thumbnail:** 635x380 GIF showing a PDF being converted

**First comment (post IMMEDIATELY after launching):**
> Hey Product Hunt! 👋
>
> I built DocClean because I was tired of uploading sensitive documents to cloud OCR tools just to convert them to Markdown. Every existing solution (Mathpix, Docparser, Smallpdf) requires sending your files to their servers — a dealbreaker for law firms, hospitals, banks, and anyone handling confidential documents.
>
> **DocClean runs entirely on your own machine.** No data leaves your server.
>
> **What it does:**
> - 📄 PDF, Word, Excel, Images → Clean Markdown (OCR with GPU acceleration)
> - 🔍 RAG knowledge base — search across all your documents
> - 🤖 AI Q&A — ask questions about your documents (bring your own LLM API key)
> - 📖 Book Compiler — turn a Word outline + your notes into a compiled book
> - 🔐 Login system + optional License key for commercial use
>
> **Tech:** Python Flask + PaddleOCR + SQLite + Docker (CPU & GPU images)
>
> **Try it:** `docker-compose up -d` → http://localhost:5000
>
> I'm a solo developer and this is my first product. Brutal honest feedback appreciated! 🙏

## Post-Launch (Day +1 → Day +7)

### Engage
- [ ] Reply to every Product Hunt comment within 1 hour
- [ ] Thank upvoters personally
- [ ] Cross-post to Hacker News: "Show HN: DocClean — Privacy-first document converter that runs on your machine"
- [ ] Post on Reddit r/selfhosted, r/privacy, r/DataHoarder
- [ ] Share on Twitter/X with the PH launch link

### Pricing (post-launch, via Lemon Squeezy)
```
Free tier:    Convert + Edit + PDF Export                         $0
Pro tier:     + RAG Knowledge Base + AI Q&A                       $29/mo or $199 lifetime
Enterprise:   + Book Compiler + REST API + Priority support       $199/mo or $999 lifetime
```

### Iterate
- [ ] Collect feedback from PH comments
- [ ] Ship 1-2 quick improvements based on feedback
- [ ] Write a "How I built DocClean" blog post
- [ ] Record a 2-minute demo video for YouTube
