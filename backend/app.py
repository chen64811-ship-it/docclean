# -*- coding: utf-8 -*-
"""
Flask 主入口
多格式文档清洗与 Markdown 导出系统
"""
from flask import Flask, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from config import HOST, PORT, MAX_CONTENT_LENGTH
from routes.upload_routes import upload_bp
from routes.knowledge_routes import knowledge_bp
from routes.book_routes import book_bp


def create_app():
    """
    创建并配置 Flask 应用
    """
    app = Flask(__name__)

    # 允许跨域访问（前端在另一个端口或目录）
    CORS(app)

    # 配置
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # 注册蓝图（路由）
    app.register_blueprint(upload_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(book_bp)

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
    print("文档清洗与 Markdown 导出系统")
    print(f"访问地址：http://localhost:{PORT}")
    print(f"{'='*50}\n")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
