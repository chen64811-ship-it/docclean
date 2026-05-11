# -*- coding: utf-8 -*-
"""
合成书路由
提供 /api/compile-book 接口
"""
import os
from flask import Blueprint, request, jsonify, send_file, current_app
from config import OUTPUT_FOLDER
from models.file_model import get_all_files
from services.book_compiler_service import compile_book

book_bp = Blueprint("book", __name__)


def get_base_dir():
    """
    获取项目根目录（backend 的上一级，即 vip/）
    在请求处理时调用，此时有 Flask app context
    """
    # current_app.root_path 是 backend 目录，往上一级就是 vip 根目录
    app_root = current_app.root_path
    return os.path.dirname(app_root)


# 延迟获取 BASE_DIR，在首次请求时再计算（避免模块加载时 current_app 不可用）
BASE_DIR = None


def get_resolved_base_dir():
    global BASE_DIR
    if BASE_DIR is None:
        BASE_DIR = get_base_dir()
        print(f"[合成书] 项目根目录 BASE_DIR = {BASE_DIR}")
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
    file_ids = data.get("file_ids", None)  # None = 全部

    # 如果没传路径，尝试在项目根目录找第一个 .docx 文件
    if not docx_path:
        base = get_resolved_base_dir()
        for fname in os.listdir(base):
            if fname.endswith(".docx"):
                docx_path = os.path.join(base, fname)
                break

    if not docx_path:
        return jsonify({"success": False, "message": "Please provide outline Word file path (docx_path)"}), 400

    # 安全校验：路径必须以 .docx 结尾，防止路径穿越
    if not docx_path.lower().endswith(".docx"):
        return jsonify({"success": False, "message": "Outline file must be .docx format"}), 400

    if not os.path.exists(docx_path):
        return jsonify({"success": False, "message": f"File not found: {docx_path}"}), 400

    # 获取数据库记录
    all_records = get_all_files()

    # 如果指定了 file_ids，只处理这些文件
    if file_ids:
        file_id_set = set(int(i) for i in file_ids)
        records = [r for r in all_records if r.get("id") in file_id_set]
    else:
        records = [r for r in all_records if r.get("status") == "done"]

    if not records:
        return jsonify({"success": False, "message": "No completed files to compile. Upload and parse files first."}), 400

    # 执行合成
    result = compile_book(
        docx_path=docx_path,
        output_folder=OUTPUT_FOLDER,
        file_records=records,
        book_title=book_title
    )

    if not result["success"]:
        return jsonify(result), 500

    # 返回下载链接（文件名）
    book_filename = os.path.basename(result["book_path"])
    result["download_url"] = f"/api/download-book/{book_filename}"
    return jsonify(result)


@book_bp.route("/api/download-book/<filename>", methods=["GET"])
def download_book(filename):
    """
    下载合成好的书 .md 文件。
    """
    # 安全校验：只允许 .md 文件，不允许路径穿越
    if not filename.endswith(".md") or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400

    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "文件不存在"}), 404

    return send_file(file_path, as_attachment=True, download_name=filename, mimetype="text/markdown; charset=utf-8")


@book_bp.route("/api/book-content/<filename>", methods=["GET"])
def get_book_content(filename):
    """
    获取合成书的原始 Markdown 内容（供前端 Notion 风格编辑器使用）。
    """
    # 安全校验
    if not filename.endswith(".md") or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"success": False, "message": "Invalid filename"}), 400

    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "文件不存在"}), 404

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return jsonify({"success": True, "content": content, "filename": filename})


@book_bp.route("/api/book-content/<filename>", methods=["PUT"])
def save_book_content(filename):
    """
    保存编辑/重排后的合成书内容。
    """
    # 安全校验
    if not filename.endswith(".md") or ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"success": False, "message": "Invalid filename"}), 400

    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "文件不存在"}), 404

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
    列出 outputs/ 目录下所有合成书文件（中文名的 .md 文件）。
    """
    books = []
    if os.path.exists(OUTPUT_FOLDER):
        for fname in os.listdir(OUTPUT_FOLDER):
            # 合成书是中文命名的 .md 文件（区分 UUID 命名的普通导出文件）
            if fname.endswith(".md") and not all(c in "0123456789abcdef" for c in fname.replace(".md", "")):
                full_path = os.path.join(OUTPUT_FOLDER, fname)
                books.append({
                    "filename": fname,
                    "size": os.path.getsize(full_path),
                    "modified": os.path.getmtime(full_path)
                })
    # 按修改时间倒序
    books.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify({"success": True, "books": books})


@book_bp.route("/api/list-docx", methods=["GET"])
def list_docx():
    """
    列出项目根目录下所有 .docx 文件，供前端选择大纲。
    """
    base = get_resolved_base_dir()
    print(f"[DEBUG] 扫描目录: {base}")
    docx_files = []
    for fname in os.listdir(base):
        if fname.endswith(".docx"):
            full_path = os.path.join(base, fname)
            print(f"[DEBUG] 找到docx: {full_path} (存在={os.path.exists(full_path)})")
            docx_files.append({
                "filename": fname,
                "path": full_path
            })
    print(f"[DEBUG] 返回结果: {docx_files}")
    return jsonify({"success": True, "files": docx_files})
