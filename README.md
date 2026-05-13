# DocClean

**Privacy-first document to Markdown converter with OCR, GPU acceleration, and AI knowledge base.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-supported-brightgreen)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![PaddleOCR](https://img.shields.io/badge/OCR-PaddleOCR-orange)](https://github.com/PaddlePaddle/PaddleOCR)

Convert PDF, Word, Excel, images, and Markdown files into clean, editable Markdown — entirely on your own machine. No cloud uploads. No data leaks. No subscriptions required.

---

## Why DocClean?

Most document conversion tools (Mathpix, Docparser, Smallpdf) require uploading your files to their cloud servers. That's a dealbreaker for anyone handling sensitive documents — law firms, hospitals, banks, researchers, and businesses.

**DocClean runs entirely on your own server.** Your documents never leave your machine.

### What makes it different

| Capability | DocClean | Mathpix | Docparser | Marker (OSS) |
|---|---|---|---|---|
| Local / Self-hosted | ✅ | ❌ | ❌ | ✅ |
| PDF + OCR | ✅ | ✅ | ✅ | ✅ |
| Word (.docx) | ✅ | ❌ | ❌ | ❌ |
| Excel (.xlsx) | ✅ | ❌ | ❌ | ❌ |
| Image OCR | ✅ | ✅ | ✅ | ❌ |
| Web UI | ✅ | ✅ | ✅ | ❌ |
| Built-in Markdown editor | ✅ | ❌ | ❌ | ❌ |
| RAG knowledge base + AI Q&A | ✅ | ❌ | ❌ | ❌ |
| Book compiler (outline → book) | ✅ | ❌ | ❌ | ❌ |
| PDF export | ✅ | ✅ | ❌ | ❌ |
| GPU acceleration | ✅ | ❌ | ❌ | ❌ |
| One-time purchase option | ✅ | ❌ | ❌ | N/A |

---

## Features

### Document Processing
- **6 file formats**: PDF (text + scanned), Word (.docx), Excel (.xlsx), Images (PNG/JPG/BMP/WebP/GIF), Markdown, Text
- **OCR engine**: PaddleOCR with GPU acceleration (NVIDIA CUDA), best-in-class Chinese + English recognition
- **Smart chunking**: Auto-split by pages (PDF), headings (Markdown), or fixed lines
- **Real-time progress**: Live progress bar during parsing, 500ms polling

### Data Cleaning & Export
- **Auto-clean**: Removes garbled text, redundant whitespace, and formatting artifacts
- **Markdown output**: Clean, well-structured Markdown ready for editing
- **Inline editor**: Edit Markdown directly in the browser after conversion (EasyMDE)
- **PDF export**: Convert Markdown back to PDF with Chinese font support
- **Batch download**: Select multiple files and download as ZIP

### AI & Knowledge Base
- **RAG search**: TF-IDF keyword search across all documents in your knowledge base
- **LLM Q&A**: Ask questions about your documents — connects to any OpenAI-compatible API (MiniMax, OpenAI, Ollama, etc.)
- **AI classification**: Auto-classify Excel outlines into structured categories, industry-agnostic

### Book Compiler
- **Outline-driven compilation**: Upload a Word outline → automatically matches and merges Markdown chapters into a complete book
- **Drag-and-drop editor**: Notion-style block editor for reordering book content
- **One-click export**: Download compiled books as a single Markdown file

### Privacy & Deployment
- **100% local**: All processing happens on your machine, zero data leaves your server
- **Docker support**: One-command deployment with `docker-compose up -d`
- **GPU-ready**: Leverages NVIDIA GPU for fast OCR (CPU fallback available)

---

## Quick Start

### Option 1: Docker (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/docclean.git
cd docclean

# 2. Create your config file
cp .env.example backend/.env

# 3. (Recommended) Set up authentication
#    Edit backend/.env and set:
#      DOCLEAN_USERNAME=admin
#      DOCLEAN_PASSWORD=your-secure-password
#    Leave empty for open access (not recommended for production).

# 4. (Optional) Add your LLM API key for AI features
#    AI Q&A and classification need this. Basic conversion works without it.

# 5. Start the container
docker-compose up -d

# 6. Open your browser → http://localhost:5000
```

#### Production Deployment (HTTPS)

See [deploy/nginx/docclean.conf](deploy/nginx/docclean.conf) for a ready-to-use Nginx + Let's Encrypt configuration.

**For GPU acceleration** (requires NVIDIA GPU + nvidia-container-toolkit):

1. Open `docker-compose.yml`
2. Change `dockerfile: Dockerfile` → `dockerfile: Dockerfile.gpu`
3. Uncomment the `deploy` section (GPU device reservation)
4. Run `docker-compose up -d`

### Option 2: Manual Installation

**Prerequisites**: Python 3.10 or 3.11, pip

```bash
# 1. Clone and enter the project
git clone https://github.com/yourusername/docclean.git
cd docclean

# 2. Install dependencies
#    CPU version:
pip install paddlepaddle==2.6.2
pip install -r backend/requirements.txt

#    GPU version (CUDA 11.8):
#    pip install paddlepaddle-gpu==2.6.2.post118
#    pip install -r backend/requirements.txt

# 3. Create your config
cp .env.example backend/.env

# 4. Start the server
cd backend
python app.py

# 5. Open http://localhost:5000
```

---

## Configuration

All settings are in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `5000` | Server port |
| `UPLOAD_FOLDER` | `uploads` | Upload storage directory |
| `OUTPUT_FOLDER` | `outputs` | Markdown output directory |
| `MAX_CONTENT_LENGTH` | `52428800` | Max file size in bytes (50 MB) |
| `ALLOWED_EXTENSIONS` | `pdf,docx,xlsx,png,jpg,...` | Allowed file types |
|| `OCR_USE_GPU` | `true` | Enable GPU for OCR (set `false` for CPU Docker) |
|| `OCR_LANG` | `en` | OCR language model (`en`, `ch`, or `auto`) |
|| `OCR_DLL_PATHS` | (empty) | Custom CUDA DLL paths (semicolon-separated, Windows) |
|| `DOCLEAN_USERNAME` | (empty) | Login username (set to enable authentication) |
|| `DOCLEAN_PASSWORD` | (empty) | Login password |
|| `DOCLEAN_LICENSE_SECRET` | (empty) | HMAC secret for license key signing |
| `LLM_API_KEY` | (empty) | API key for AI Q&A (MiniMax, OpenAI, Ollama compatible) |
| `LLM_API_BASE` | `https://api.minimax.chat/v1` | LLM API endpoint (OpenAI-compatible) |
| `LLM_MODEL` | `MiniMax-M2.7` | Model name |

---

## API Reference

All endpoints available at `http://localhost:5000/api/`.

### File Upload & Management

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload one or more files (multipart form) |
| `GET` | `/api/files` | List all uploaded files with status |
| `GET` | `/api/download/<file_id>` | Download converted Markdown file |
| `POST` | `/api/delete` | Batch delete files `{"file_ids": [1, 2]}` |
| `GET` | `/api/download/all` | Download all completed files as ZIP |
| `POST` | `/api/download/batch` | Download selected files as ZIP `{"file_ids": [1, 2]}` |
| `GET` | `/api/export-pdf/<file_id>` | Export Markdown to PDF |
| `GET` | `/api/parse-progress` | Poll parsing progress (for progress bar) |
| `GET` | `/api/file-content/<file_id>` | Read Markdown content for editing |
| `PUT` | `/api/file-content/<file_id>` | Save edited Markdown content |
| `GET` | `/api/tree/<file_id>` | Get document chapter tree structure (JSON) |
| `GET` | `/api/upload-file/<filename>` | Serve original uploaded file |

### Knowledge Base & AI

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/kb/list` | List files in knowledge base |
| `GET` | `/api/kb/tree/<file_id>` | Get knowledge base file tree |
| `GET` | `/api/kb/chunks/<file_id>` | Get text chunks for a file |
| `GET` | `/api/kb/search?q=<query>` | Search knowledge base |
| `POST` | `/api/kb/ask` | Ask AI a question `{"query": "..."}` |
| `GET` | `/api/kb/config` | Get LLM configuration |
| `POST` | `/api/kb/config` | Update LLM configuration |
| `POST` | `/api/kb/test-llm` | Test LLM connection |
| `POST` | `/api/kb/rebuild/<file_id>` | Rebuild knowledge base index |
| `POST` | `/api/kb/classify-excel/<file_id>` | AI classification for Excel files |
| `GET` | `/api/kb/classify-status/<file_id>` | Check classification status |

### Book Compiler

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/compile-book` | Compile book from Word outline `{"docx_path": "..."}` |
| `GET` | `/api/download-book/<filename>` | Download compiled book |
| `GET` | `/api/book-content/<filename>` | Read book content |
| `PUT` | `/api/book-content/<filename>` | Save book content |
| `GET` | `/api/list-books` | List compiled books |
| `GET` | `/api/list-docx` | List available Word outline files |

---

## Project Structure

```
docclean/
├── backend/
│   ├── app.py                  # Flask entry point
│   ├── config.py               # Configuration loader
│   ├── config_manager.py       # LLM config persistence
│   ├── progress_store.py       # Real-time progress tracking
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Environment config (git-ignored)
│   ├── models/
│   │   └── file_model.py       # SQLite file state management
│   ├── routes/
│   │   ├── upload_routes.py    # File upload & management APIs
│   │   ├── knowledge_routes.py # Knowledge base & RAG APIs
│   │   └── book_routes.py      # Book compiler APIs
│   └── services/
│       ├── extractor_service.py    # PDF/Word/Excel/Image text extraction
│       ├── ocr_service.py          # PaddleOCR GPU/CPU engine
│       ├── cleaner_service.py      # Data cleaning & formatting
│       ├── rag_service.py          # TF-IDF search + LLM Q&A
│       ├── book_compiler_service.py # Outline-driven book compiler
│       ├── pdf_service.py          # Markdown → PDF export
│       └── tree_parser.py          # Chapter tree structure parser
├── frontend/
│   └── index.html              # Single-page web UI (English)
├── Dockerfile                  # CPU Docker image
├── Dockerfile.gpu              # GPU Docker image (CUDA 11.8)
├── docker-compose.yml          # One-command deployment
├── .env.example                # Configuration template
└── README.md                   # This file
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Flask 3.0 |
| OCR engine | PaddleOCR 2.7 + PaddlePaddle 2.6 |
| PDF parsing | pdfminer.six + PyMuPDF |
| Word parsing | python-docx |
| Excel parsing | openpyxl |
| PDF generation | fpdf2 |
| Markdown editor | EasyMDE |
| PDF viewer | PDF.js |
| Database | SQLite |
| Containerization | Docker + Docker Compose |

---

## FAQ

**Do I need a GPU?**
No. DocClean works on CPU with the default Docker image. GPU acceleration (NVIDIA CUDA) makes OCR 3-5x faster — recommended if you process scanned PDFs in bulk.

**Does it work on Mac / Linux?**
Yes. Docker runs everywhere. Manual Python install is also cross-platform. GPU OCR is Linux + Windows only.

**What languages does OCR support?**
PaddleOCR supports 80+ languages. DocClean is optimized for English and Chinese. Other languages work with PaddleOCR's built-in models.

**Is my data safe?**
Yes. All processing is local. DocClean never sends your documents to any external server. The only outbound call is the optional LLM API (if you configure AI Q&A).

**Can I use DocClean commercially?**
Yes, MIT licensed. Note: PyMuPDF (fitz) uses AGPL — if you distribute DocClean commercially, either [buy a PyMuPDF license](https://pymupdf.com/pricing/) ($399/year) or replace with `pdfplumber` (MIT).

**How do I update?**
```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Roadmap

- [x] English UI (frontend + API)
- [x] Docker deployment (CPU + GPU)
- [ ] CI/CD with GitHub Actions
- [ ] Swagger/OpenAPI documentation
- [ ] Dedicated English OCR model optimization
- [ ] License key system for commercial distribution
- [ ] Modern UI refresh (Tailwind CSS / Vue 3)

---

## Contributing

Issues and pull requests are welcome. For major changes, open an issue first to discuss.

---

## License

MIT License — see [LICENSE](LICENSE) file.

> Third-party note: PyMuPDF (fitz) is AGPL-licensed. For commercial closed-source distribution, [purchase a commercial license](https://pymupdf.com/pricing/) or replace with `pdfplumber` (MIT).

---

## Acknowledgments

Built with these excellent open-source projects:

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR engine
- [Flask](https://flask.palletsprojects.com/) — Web framework
- [EasyMDE](https://github.com/Ionaru/easy-markdown-editor) — Markdown editor
- [PDF.js](https://mozilla.github.io/pdf.js/) — PDF viewer
- [fpdf2](https://github.com/py-pdf/fpdf2) — PDF generation

---

> **DocClean is not just another file converter.** It's a privacy-first document intelligence tool that keeps your data where it belongs — on your own machine. That's the one thing no cloud competitor can offer, and that's what customers will pay for.
