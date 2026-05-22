# DocClean — Product Hunt Launch Guide

> **Target launch date:** [TBD]
> **Product Hunt URL:** [TBD — create at producthunt.com/upcoming first]

---

## Product Overview

**Tagline:** Privacy-first document to Markdown converter. GPU-accelerated OCR. 100% local processing. No cloud.

**One-liner:** Drop any PDF, Word doc, Excel sheet, or scanned image — get clean Markdown. Everything runs locally on your machine.

**Why it matters:** Every "free online converter" uploads your documents to someone's server. DocClean keeps your data on your machine. For lawyers, researchers, developers, and anyone handling sensitive documents.

---

## Interactive Demo

**URL:** `https://YOUR_DOMAIN/demo`

The interactive demo lets visitors experience DocClean's core workflow without installing anything:

1. **Upload** — Click the drop zone to simulate uploading PDFs, spreadsheets, and scanned images
2. **Process** — Watch GPU-accelerated conversion with real-time progress bars
3. **Preview** — See extracted Markdown with preserved formatting, headings, and tables
4. **Privacy** — Learn about the local-first architecture with zero cloud dependency

The demo is a standalone HTML page served from the Flask backend at `/demo`. No auth required — it's fully public.

### Demo Platforms

If you want to create a more polished guided tour, these platforms offer free Product Hunt launch accounts:

| Platform | Best for | Free tier |
|----------|----------|-----------|
| **Arcade** (arcade.software) | Interactive product tours with branching | Free for PH launches |
| **Storylane** (storylane.io) | No-code demos with analytics | Free tier available |
| **Supademo** (supademo.com) | Quick product walkthroughs | Free tier available |
| **Hexus** (hexus.ai) | AI-powered interactive demos | Free for PH launches |
| **Layerpath** (layerpath.com) | Multi-step interactive guides | Free tier available |
| **ScreenSpace** (screenspace.io) | Narrative product stories | Free tier available |
| **Guideflow** (guideflow.com) | Embeddable interactive demos | Free tier available |

**Recommendation:** Use **Arcade** — best free tier for Product Hunt, and their interactive format converts well. Record your screen showing the real DocClean app, add clickable hotspots and text annotations.

---

## Launch Assets Checklist

### Required
- [ ] **Product Hunt listing** — draft at producthunt.com/posts/new
- [ ] **Tagline** — 60 chars max ("Privacy-first document to Markdown converter with GPU OCR")
- [ ] **Description** — first 260 chars are most visible
- [ ] **Logo** — 240x240px PNG, no transparency issues
- [ ] **Gallery images** — at least 3 screenshots (1270x760px)
- [ ] **First comment** — introduce yourself and the product
- [ ] **Interactive demo link** — `https://YOUR_DOMAIN/demo`

### Recommended
- [ ] **Demo video** — 30-60 sec GIF or MP4 of the product in action
- [ ] **Maker profile** — fill out your PH profile with Twitter/GitHub links
- [ ] **Social proof** — early testimonials or GitHub stars
- [ ] **Hunter** — find a PH influencer to hunt your launch (or self-hunt)
- [ ] **Launch day plan** — time your launch (Tuesday-Thursday, 12:01 AM PST)

### Screenshot Ideas
1. Main upload interface with drag-and-drop zone
2. File processing with progress bars
3. Markdown preview of extracted content
4. Privacy features / settings panel
5. Multi-file batch processing

---

## Launch Day Flow

1. **T-7 days:** Create "Upcoming" page on PH, start collecting followers
2. **T-3 days:** Test demo link, verify all screenshots, prepare first comment
3. **T-0 (12:01 AM PST):** Launch goes live
4. **First hour:** Post first comment, engage with every comment immediately
5. **Throughout day:** Reply to all comments, share on social channels
6. **T+1:** Thank-you post, share results

---

## First Comment Template

```
Hey Product Hunt! 👋

I built DocClean because I was tired of sketchy "free online converters" that upload
your documents to who-knows-where.

DocClean runs 100% on your machine:
🔒 No cloud upload — your files never leave your computer
⚡ GPU-accelerated OCR — 10x faster than cloud tools
📄 Works with PDF, Word, Excel, images, and Markdown
📝 Clean Markdown output — no formatting loss, no watermarks

It's open source (MIT), self-hostable, and Docker-ready.

Try the interactive demo: https://YOUR_DOMAIN/demo
GitHub: https://github.com/chen64811-ship-it/docclean

Happy to answer any questions!
```

---

## Social Media Posts

### Twitter/X
```
I built DocClean — a privacy-first document converter that runs 100% locally.

No cloud. No tracking. No AI training on your documents.

Drop any PDF/Word/Excel/image → clean Markdown. GPU-accelerated OCR.

Open source. MIT. Self-hostable.

Try the demo: YOUR_DOMAIN/demo
```

### Reddit (r/selfhosted, r/privacy, r/SideProject)
Focus on the privacy angle for r/privacy, self-hosting for r/selfhosted, and the build story for r/SideProject.

---

## Tech Stack (for technical audience)

- **Backend:** Python Flask
- **OCR:** PaddleOCR with NVIDIA GPU acceleration
- **PDF:** pdfminer.six + PyMuPDF
- **Frontend:** Vanilla JS with EasyMDE editor
- **Deploy:** Docker, Nginx reverse proxy, Let's Encrypt SSL
- **Auth:** Session cookies + HTTP Basic Auth

---

## Notes

- The interactive demo HTML lives at `frontend/demo-interactive.html`
- Served publicly at `/demo` (no auth required)
- Update `YOUR_DOMAIN` in this file to the actual domain before launch
- The demo is fully self-contained — no dependencies, no API calls
