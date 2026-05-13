# -*- coding: utf-8 -*-
"""
Book Compiler Routes
Provides /api/compile-book endpoint
"""
import os
from flask import Blueprint, request, jsonify, send_file, current_app
from config import OUTPUT_FOLDER
from models.file_model import get_all_files
from services.book_compiler_service import compile_book

book_bp = Blueprint("book", __name__)


def get_base_dir():
    """
    Get project root directory (parent of backend/, i.e. vip/).
    Called during request handling when Flask app context is available.
    """
    # current_app.root_path is the backend directory, parent is the vip root
    app_root = current_app.root_path
    return os.path.dirname(app_root)


# Defer BASE_DIR resolution to first request (current_app not available at module load time)
BASE_DIR = None


def get_resolved_base_dir():
    global BASE_DIR
    if BASE_DIR is None:
        BASE_DIR = get_base_dir()
        print(f"[Book Compiler] Project root BASE_DIR = {BASE_DIR}")
    return BASE_DIR


@book_bp.route("/api/compile-book", methods=["POST"])
def api_compile_book():
    """
    Compile a book from a Word outline (.docx) by matching section headings against converted Markdown files.
    Sections in the outline like "1.1 Topic" are matched to Markdown chunks with the same title.
    ---
    tags:
      - Book Compiler
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - docx_path
          properties:
            docx_path:
              type: string
              description: Absolute path to the Word outline file (.docx)
            book_title:
              type: string
              description: Book title (optional, derived from filename if empty)
            file_ids:
              type: array
              items:
                type: integer
              description: Specific file IDs to include (optional, uses all completed files if empty)
    responses:
      200:
        description: Book compiled successfully with download URL
        schema:
          type: object
          properties:
            success:
              type: boolean
            book_title:
              type: string
            matched_count:
              type: integer
            total_sections:
              type: integer
            download_url:
              type: string
      400:
        description: Missing or invalid outline file
    """
    data = request.get_json(silent=True) or {}

    docx_path = data.get("docx_path", "").strip()
    book_title = data.get("book_title", "").strip() or None
    file_ids = data.get("file_ids", None)  # None = use all

    # If no path provided, look for first .docx in project root
    if not docx_path:
        base = get_resolved_base_dir()
        for fname in os.listdir(base):
            if fname.endswith(".docx"):
                docx_path = os.path.join(base, fname)
                break

    if not docx_path:
        return jsonify({"success": False, "message": "Please provide outline Word file path (docx_path)"}), 400

    # Security: path must end with .docx, prevent path traversal
    if not docx_path.lower().endswith(".docx"):
        return jsonify({"success": False, "message": "Outline file must be .docx format"}), 400

    if not os.path.exists(docx_path):
        return jsonify({"success": False, "message": f"File not found: {docx_path}"}), 400

    # Get database records
    all_records = get_all_files()

    # If specific file_ids provided, filter to those only
    if file_ids:
        file_id_set = set(int(i) for i in file_ids)
        records = [r for r in all_records if r.get("id") in file_id_set]
    else:
        records = [r for r in all_records if r.get("status") == "done"]

    if not records:
        return jsonify({"success": False, "message": "No completed files to compile. Upload and parse files first."}), 400

    # Run compilation
    result = compile_book(
        docx_path=docx_path,
        output_folder=OUTPUT_FOLDER,
        file_records=records,
        book_title=book_title
    )

    if not result["success"]:
        return jsonify(result), 500

    # Return download URL (by filename)
    book_filename = os.path.basename(result["book_path"])
    result["download_url"] = f"/api/download-book/{book_filename}"
    return jsonify(result)


@book_bp.route("/api/download-book/<filename>", methods=["GET"])
def download_book(filename):
    """
    Download a compiled book .md file.
    """
    # Security: only allow .md files, block path traversal
    if not filename.endswith(".md") or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400

    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True, download_name=filename, mimetype="text/markdown; charset=utf-8")


@book_bp.route("/api/book-content/<filename>", methods=["GET"])
def get_book_content(filename):
    """
    Get raw Markdown content of a compiled book (for the Notion-style editor).
    """
    # Security check
    if not filename.endswith(".md") or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"success": False, "message": "Invalid filename"}), 400

    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return jsonify({"success": True, "content": content, "filename": filename})


@book_bp.route("/api/book-content/<filename>", methods=["PUT"])
def save_book_content(filename):
    """
    Save edited/rearranged compiled book content.
    """
    # Security check
    if not filename.endswith(".md") or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"success": False, "message": "Invalid filename"}), 400

    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    data = request.get_json(silent=True) or {}
    content = data.get("content", "")
    if not content:
        return jsonify({"success": False, "message": "Content cannot be empty"}), 400

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return jsonify({"success": True, "message": "Saved successfully"})


@book_bp.route("/api/list-books", methods=["GET"])
def list_books():
    """
    List all compiled book files in the outputs/ directory (Chinese-named .md files).
    """
    books = []
    if os.path.exists(OUTPUT_FOLDER):
        for fname in os.listdir(OUTPUT_FOLDER):
            # Compiled books are Chinese-named .md files (vs UUID-named regular exports)
            if fname.endswith(".md") and not all(c in "0123456789abcdef" for c in fname.replace(".md", "")):
                full_path = os.path.join(OUTPUT_FOLDER, fname)
                books.append({
                    "filename": fname,
                    "size": os.path.getsize(full_path),
                    "modified": os.path.getmtime(full_path)
                })
    # Sort by modification time descending
    books.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify({"success": True, "books": books})


@book_bp.route("/api/list-docx", methods=["GET"])
def list_docx():
    """
    List all .docx files in the project root directory (for outline selection in the frontend).
    """
    base = get_resolved_base_dir()
    print(f"[DEBUG] Scanning directory: {base}")
    docx_files = []
    for fname in os.listdir(base):
        if fname.endswith(".docx"):
            full_path = os.path.join(base, fname)
            print(f"[DEBUG] Found docx: {full_path} (exists={os.path.exists(full_path)})")
            docx_files.append({
                "filename": fname,
                "path": full_path
            })
    print(f"[DEBUG] Returning: {docx_files}")
    return jsonify({"success": True, "files": docx_files})
