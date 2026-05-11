# -*- coding: utf-8 -*-
"""
上传和文件管理路由
"""
import os
import uuid
import traceback
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, OUTPUT_FOLDER, is_allowed_file, get_file_ext
from models.file_model import add_file, update_file_status, get_all_files, get_file_by_id, delete_files_batch
from services.extractor_service import extract_text
from services.cleaner_service import clean_text, text_to_markdown
from services.tree_parser import parse_markdown_to_tree
from progress_store import set_progress, get_progress, del_progress, get_all_progress
import threading

# 创建蓝图
upload_bp = Blueprint("upload", __name__)


def process_file_background(file_id, stored_name, original_name, file_ext):
    """
    后台线程处理文件：提取文字（保留格式） -> 清洗 -> 导出 Markdown
    """
    import time as _time

    # 记录开始时间，用于超时检测
    start_time = _time.time()
    MAX_PROCESS_TIME = 600  # 超过 10 分钟视为超时

    def _check_timeout():
        """检测是否超时，超时则抛异常"""
        if _time.time() - start_time > MAX_PROCESS_TIME:
            raise Exception(f"Timeout (exceeded {MAX_PROCESS_TIME}s). File may be too large or complex.")

    try:
        update_file_status(file_id, "parsing")
        set_progress(file_id, 100, 0, "Starting parse...")
        file_path = os.path.join(UPLOAD_FOLDER, stored_name)

        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")

        # 图片保存目录：outputs/uuid/（用于docx里的图片）
        docx_img_dir = os.path.join(OUTPUT_FOLDER, os.path.splitext(stored_name)[0])
        os.makedirs(docx_img_dir, exist_ok=True)

        # 提取内容（传入 file_id 用于进度上报）
        _check_timeout()
        raw_text = extract_text(file_path, file_ext, file_id=file_id)

        _check_timeout()
        set_progress(file_id, 100, 70, "Cleaning data...")
        cleaned_text = clean_text(raw_text)
        title = os.path.splitext(original_name)[0]

        _check_timeout()
        set_progress(file_id, 100, 85, "Generating Markdown...")
        markdown_content = text_to_markdown(cleaned_text, title=title)

        # 保存 Markdown
        set_progress(file_id, 100, 95, "Saving file...")
        md_basename = os.path.splitext(stored_name)[0] + ".md"
        output_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, md_basename))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # ✨ 生成树结构 JSON（无缝插入：Markdown 生成之后）
        set_progress(file_id, 100, 98, "Generating tree structure...")
        import json
        tree_data = parse_markdown_to_tree(markdown_content, original_name)
        tree_basename = os.path.splitext(stored_name)[0] + "_tree.json"
        tree_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, tree_basename))
        with open(tree_path, "w", encoding="utf-8") as f:
            json.dump(tree_data, f, ensure_ascii=False, indent=2)

        del_progress(file_id)
        update_file_status(file_id, "done", output_path=output_path, tree_path=tree_path)
        print(f"[Done] {original_name} -> {output_path}")

    except Exception as e:
        del_progress(file_id)
        error_msg = str(e)
        print(f"[Failed] {original_name}: {error_msg}")
        traceback.print_exc()
        update_file_status(file_id, "error", error_msg=error_msg)


@upload_bp.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Upload one or more files for conversion to Markdown.
    Supports PDF, Word (.docx), Excel (.xlsx), images, and Markdown (.md).
    ---
    tags:
      - File Upload
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: File(s) to upload (max 50MB each). Supports PDF, DOCX, XLSX, PNG, JPG, GIF, BMP, WebP, JFIF, MD.
    responses:
      200:
        description: Upload results with file IDs and status
        schema:
          type: object
          properties:
            success:
              type: boolean
            success_count:
              type: integer
              description: Number of files successfully uploaded
            total_count:
              type: integer
            results:
              type: array
              items:
                type: object
                properties:
                  success:
                    type: boolean
                  filename:
                    type: string
                  file_id:
                    type: integer
                  message:
                    type: string
      400:
        description: No file selected or all files invalid
    """
    files = request.files.getlist("file")

    if not files or all(f.filename == "" for f in files):
        return jsonify({"success": False, "message": "No file selected"}), 400

    results = []

    for file in files:
        if not file.filename or file.filename.strip() == "":
            continue

        original_name = file.filename
        filename = secure_filename(original_name)

        # 如果 secure_filename 把文件名清空了（中文或特殊字符），从原始文件名手动提取扩展名
        # 然后生成一个安全的文件名
        if not filename or "." not in filename:
            # 手动从原始名提取扩展名
            if "." in original_name:
                ext = original_name.rsplit(".", 1)[-1].lower().strip()
                safe_ext = "".join(c for c in ext if c.isalnum())
            else:
                safe_ext = ""
            filename = f"file_{uuid.uuid4().hex[:8]}.{safe_ext}" if safe_ext else f"file_{uuid.uuid4().hex[:8]}"

        # 检查文件格式（基于安全文件名）
        if not is_allowed_file(filename):
            results.append({
                "success": False,
                "filename": original_name,
                "message": f"Unsupported file format. Supported: PDF, Word, Excel, Image, Markdown"
            })
            continue

        # 生成唯一存储文件名
        file_ext = get_file_ext(filename)
        stored_name = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(UPLOAD_FOLDER, stored_name)

        # 保存文件
        file.save(file_path)

        # 确认文件确实保存了
        if not os.path.exists(file_path):
            results.append({
                "success": False,
                "filename": original_name,
                "message": "File save failed, please retry"
            })
            continue

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        # 写入数据库（去重逻辑在 add_file 内部）
        file_id = add_file(original_name, stored_name, file_size, file_ext)

        # 如果 file_id 为 None，说明是重复文件，直接跳过
        if file_id is None:
            results.append({
                "success": True,
                "filename": original_name,
                "duplicate": True,
                "message": "File already exists, no need to re-upload"
            })
            continue

        # 启动后台处理线程
        thread = threading.Thread(
            target=process_file_background,
            args=(file_id, stored_name, original_name, file_ext)
        )
        thread.daemon = True
        thread.start()

        results.append({
            "success": True,
            "filename": original_name,
            "file_id": file_id,
            "message": "Uploaded, parsing started"
        })

    # 返回所有文件的上传结果
    success_count = sum(1 for r in results if r.get("success"))
    return jsonify({
        "success": True,
        "success_count": success_count,
        "total_count": len(results),
        "results": results
    })


@upload_bp.route("/api/files", methods=["GET"])
def list_files():
    """
    List all uploaded files with their current processing status.
    ---
    tags:
      - File Upload
    responses:
      200:
        description: File list with statuses
        schema:
          type: object
          properties:
            success:
              type: boolean
            files:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                  original_name:
                    type: string
                  status:
                    type: string
                    enum: [uploading, parsing, done, error]
                  output_path:
                    type: string
    """
    files = get_all_files()
    return jsonify({"success": True, "files": files})


@upload_bp.route("/api/download/<int:file_id>", methods=["GET"])
def download_file(file_id):
    """
    Download the converted Markdown file for a given file ID.
    ---
    tags:
      - File Download
    parameters:
      - name: file_id
        in: path
        type: integer
        required: true
        description: File ID to download
    responses:
      200:
        description: Markdown file download
        content:
          text/markdown:
            schema:
              type: string
      404:
        description: File not found or deleted
      400:
        description: File not yet processed
    """
    file_info = get_file_by_id(file_id)

    if not file_info:
        return jsonify({"success": False, "message": "File not found"}), 404

    if file_info["status"] != "done":
        return jsonify({"success": False, "message": f"File status is {file_info['status']}, cannot download"}), 400

    output_path = file_info["output_path"]
    # 规范化路径（处理 ../ 等相对路径）
    output_path = os.path.abspath(output_path) if output_path else ""
    if not output_path or not os.path.exists(output_path):
        return jsonify({"success": False, "message": "File has been deleted"}), 404

    download_name = os.path.splitext(file_info["original_name"])[0] + ".md"

    return send_file(
        output_path,
        as_attachment=True,
        download_name=download_name,
        mimetype="text/markdown; charset=utf-8"
    )


@upload_bp.route("/api/delete", methods=["POST"])
def delete_files():
    """
    Batch delete files (removes uploaded file + exported Markdown + tree JSON).
    ---
    tags:
      - File Upload
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - file_ids
          properties:
            file_ids:
              type: array
              items:
                type: integer
              description: List of file IDs to delete
              example: [1, 2, 3]
    responses:
      200:
        description: Deletion result
      400:
        description: No files specified
    """
    try:
        data = request.get_json()
        file_ids = data.get("file_ids", [])

        if not file_ids:
            return jsonify({"success": False, "message": "No files specified for deletion"}), 400

        delete_files_batch(file_ids)

        return jsonify({"success": True, "message": f"Deleted {len(file_ids)} files"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Delete failed: {str(e)}"}), 500


@upload_bp.route("/api/download/all", methods=["GET"])
def download_all():
    """
    下载所有已完成的 Markdown 文件（打包成zip）
    """
    import zipfile
    from io import BytesIO

    files = get_all_files()
    done_files = [
        f for f in files
        if f["status"] == "done" and f["output_path"] and
           os.path.exists(os.path.abspath(f["output_path"]))
    ]

    if not done_files:
        return jsonify({"success": False, "message": "No files available for download"}), 400

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in done_files:
            download_name = os.path.splitext(f["original_name"])[0] + ".md"
            f_path = os.path.abspath(f["output_path"])
            zf.write(f_path, download_name)

    memory_file.seek(0)

    return send_file(
        memory_file,
        as_attachment=True,
        download_name="all-documents.md.zip",
        mimetype="application/zip"
    )

@upload_bp.route("/api/download/batch", methods=["POST"])
def download_batch():
    """
    批量下载选中的已完成文件（打包成zip）
    请求体：{"file_ids": [1, 2, 3]}
    """
    import zipfile
    from io import BytesIO

    data = request.get_json()
    file_ids = data.get("file_ids", [])
    if not file_ids:
        return jsonify({"success": False, "message": "No files selected"}), 400

    done_files = []
    for fid in file_ids:
        f = get_file_by_id(fid)
        if f and f["status"] == "done" and f["output_path"] and os.path.exists(os.path.abspath(f["output_path"])):
            done_files.append(f)

    if not done_files:
        return jsonify({"success": False, "message": "No completed files among selected"}), 400

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in done_files:
            download_name = os.path.splitext(f["original_name"])[0] + ".md"
            f_path = os.path.abspath(f["output_path"])
            zf.write(f_path, download_name)

    memory_file.seek(0)

    return send_file(
        memory_file,
        as_attachment=True,
        download_name="batch-export.zip",
        mimetype="application/zip"
    )


@upload_bp.route("/api/export-pdf/<int:file_id>", methods=["GET"])
def export_pdf(file_id):
    """
    Convert a Markdown file to PDF and download it.
    Rendered server-side with fpdf2. Supports Chinese fonts.
    ---
    tags:
      - File Download
    parameters:
      - name: file_id
        in: path
        type: integer
        required: true
        description: File ID to export as PDF
    responses:
      200:
        description: PDF file download
        content:
          application/pdf:
            schema:
              type: string
              format: binary
      404:
        description: File not found or deleted
      400:
        description: File not yet processed
    """
    try:
        import io
        from services.pdf_service import markdown_to_pdf

        file_info = get_file_by_id(file_id)
        if not file_info:
            return jsonify({"success": False, "message": "File not found"}), 404
        if file_info["status"] != "done":
            return jsonify({"success": False, "message": "File not yet parsed"}), 400

        output_path = os.path.abspath(file_info["output_path"])
        if not os.path.exists(output_path):
            return jsonify({"success": False, "message": "Markdown file has been deleted"}), 404

        # 读取 Markdown 文本
        with open(output_path, "r", encoding="utf-8") as f:
            md_text = f.read()

        # 调用 pdf_service 生成 PDF 字节流
        pdf_bytes = markdown_to_pdf(md_text, title=file_info.get("original_name", ""))

        pdf_name = os.path.splitext(file_info["original_name"])[0] + ".pdf"
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=pdf_name,
            mimetype="application/pdf"
        )

    except ImportError as e:
        return jsonify({"success": False, "message": f"Missing dependency, please install: pip install fpdf2\nDetails: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"PDF generation failed: {str(e)}"}), 500


@upload_bp.route("/api/parse-progress", methods=["GET"])
def get_parse_progress():
    """
    Poll parsing progress for all currently-processing files.
    Frontend polls this every 500ms for real-time progress bars.
    ---
    tags:
      - File Upload
    responses:
      200:
        description: Progress data for parsing files
        schema:
          type: object
          properties:
            success:
              type: boolean
            progress:
              type: object
              description: Map of file_id → {total, done, stage, pct}
            parsing_ids:
              type: array
              items:
                type: integer
    """
    import time
    # 获取所有文件状态
    files = get_all_files()
    parsing_ids = [f["id"] for f in files if f["status"] == "parsing"]

    progress_data = {}
    for fid in parsing_ids:
        p = get_progress(fid)
        if p:
            progress_data[str(fid)] = p
        else:
            # 有进度但 store 里没有（刚开始），返回默认
            progress_data[str(fid)] = {"total": 100, "done": 0, "stage": "Preparing...", "pct": 0}

    return jsonify({"success": True, "progress": progress_data, "parsing_ids": parsing_ids})


@upload_bp.route("/api/file-content/<int:file_id>", methods=["GET"])
def get_file_content(file_id):
    """
    Read the full Markdown content of a converted file (for inline editor).
    ---
    tags:
      - File Content
    parameters:
      - name: file_id
        in: path
        type: integer
        required: true
        description: File ID to read
    responses:
      200:
        description: Markdown content
        schema:
          type: object
          properties:
            success:
              type: boolean
            content:
              type: string
            original_name:
              type: string
      404:
        description: File not found
      400:
        description: File not yet processed
    """
    file_info = get_file_by_id(file_id)

    if not file_info:
        return jsonify({"success": False, "message": "File not found"}), 404

    if file_info["status"] != "done":
        return jsonify({"success": False, "message": "File not yet parsed, cannot read"}), 400

    output_path = file_info["output_path"]
    output_path = os.path.abspath(output_path) if output_path else ""
    if not output_path or not os.path.exists(output_path):
        return jsonify({"success": False, "message": "File deleted or path invalid"}), 404

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({
            "success": True,
            "content": content,
            "original_name": file_info["original_name"]
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Read file failed: {str(e)}"}), 500


@upload_bp.route("/api/file-content/<int:file_id>", methods=["PUT"])
def save_file_content(file_id):
    """
    Save edited Markdown content back to the file.
    ---
    tags:
      - File Content
    parameters:
      - name: file_id
        in: path
        type: integer
        required: true
        description: File ID to save
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - content
          properties:
            content:
              type: string
              description: Full Markdown content to save
    responses:
      200:
        description: Save confirmation
      404:
        description: File not found
      400:
        description: File not yet processed
    """
    file_info = get_file_by_id(file_id)

    if not file_info:
        return jsonify({"success": False, "message": "File not found"}), 404

    if file_info["status"] != "done":
        return jsonify({"success": False, "message": "File not yet parsed, cannot save"}), 400

    output_path = file_info["output_path"]
    output_path = os.path.abspath(output_path) if output_path else ""
    if not output_path:
        return jsonify({"success": False, "message": "Invalid file path"}), 400

    try:
        data = request.get_json()
        content = data.get("content", "")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        return jsonify({"success": True, "message": "Saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Save failed: {str(e)}"}), 500


@upload_bp.route("/api/tree/<int:file_id>", methods=["GET"])
def get_tree(file_id):
    """
    获取指定文件的章节树结构 JSON
    """
    file_info = get_file_by_id(file_id)

    if not file_info:
        return jsonify({"success": False, "message": "File not found"}), 404

    if file_info["status"] != "done":
        return jsonify({"success": False, "message": "文件还未解析完成"}), 400

    tree_path = file_info.get("tree_path", "")
    if not tree_path:
        return jsonify({"success": False, "message": "Tree file not found"}), 404

    tree_path = os.path.abspath(tree_path)
    if not os.path.exists(tree_path):
        return jsonify({"success": False, "message": "Tree file has been deleted"}), 404

    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            import json
            tree_data = json.load(f)
        return jsonify({
            "success": True,
            "file_id": file_id,
            "original_name": file_info["original_name"],
            "tree": tree_data
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Read tree file failed: {str(e)}"}), 500


@upload_bp.route("/api/upload-file/<path:filename>", methods=["GET"])
def serve_upload_file(filename):
    """
    提供原始上传文件的访问（供 PDF.js 等前端组件加载文件）
    """
    # filename 就是 stored_name（如 uuid.pdf）
    file_path = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))

    # 安全检查：确保文件在 uploads 目录内
    if not file_path.startswith(os.path.abspath(UPLOAD_FOLDER)):
        return jsonify({"success": False, "message": "Invalid path"}), 403

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    # 根据扩展名返回正确的 MIME 类型
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".jfif": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".md": "text/markdown; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
    }
    mime = mime_types.get(ext, "application/octet-stream")

    return send_file(file_path, mimetype=mime)
