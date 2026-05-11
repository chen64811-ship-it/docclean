# -*- coding: utf-8 -*-
"""
DocClean — Privacy-first Document to Markdown Converter
Flask 主入口
"""
from flask import Flask, send_from_directory
from flask_cors import CORS
from flasgger import Swagger
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from config import HOST, PORT, MAX_CONTENT_LENGTH
from routes.upload_routes import upload_bp
from routes.knowledge_routes import knowledge_bp
from routes.book_routes import book_bp
from routes.license_routes import license_bp


def create_app():
    """
    创建并配置 Flask 应用
    """
    app = Flask(__name__)

    # 允许跨域访问（前端在另一个端口或目录）
    CORS(app)

    # 配置
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # ── Swagger / OpenAPI 文档 ──
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api/docs/",
    }

    swagger_template = {
        "info": {
            "title": "DocClean API",
            "description": (
                "Privacy-first document to Markdown converter with OCR, "
                "GPU acceleration, and AI knowledge base.\\n\\n"
                "**All processing is local — your documents never leave your server.**\\n\\n"
                "### Features\\n"
                "- Upload & convert PDF, Word, Excel, images, Markdown\\n"
                "- OCR with PaddleOCR (GPU accelerated)\\n"
                "- Knowledge base search & LLM Q&A (RAG)\\n"
                "- Book compiler (Word outline → compiled Markdown)\\n"
                "- PDF export\\n\\n"
                "### Authentication\\n"
                "No authentication required for local deployment."
            ),
            "version": "1.0.0",
            "contact": {
                "name": "DocClean",
            },
        },
        "tags": [
            {"name": "File Upload", "description": "Upload, list, delete files"},
            {"name": "File Download", "description": "Download & export converted files"},
            {"name": "File Content", "description": "Read & edit Markdown content"},
            {"name": "Knowledge Base", "description": "RAG search & AI Q&A"},
            {"name": "Book Compiler", "description": "Word outline → compiled book"},
            {"name": "License", "description": "License activation & status"},
        ],
    }

    Swagger(app, config=swagger_config, template=swagger_template)

    # 注册蓝图（路由）
    app.register_blueprint(upload_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(license_bp)

    # 提供前端页面（禁用缓存，每次都读最新文件）
    @app.route("/")
    def index():
        """
        返回前端 HTML 页面
        """
        frontend_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "frontend", "index.html"
        )
        response = send_from_directory(os.path.dirname(frontend_path), "index.html")
        # 强制浏览器每次都从服务器获取最新页面，不缓存
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"\n{'='*50}")
    print("DocClean - Document Cleaning & Markdown Export")
    print(f"Access: http://localhost:{PORT}")
    print(f"{'='*50}\n")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
