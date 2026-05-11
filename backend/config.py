# -*- coding: utf-8 -*-
"""
配置文件
从 .env 文件读取配置，不在代码里硬编码
"""
import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 获取项目根目录（backend 的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 上传文件夹路径（绝对路径）
UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "uploads"))

# 导出文件夹路径（绝对路径）
OUTPUT_FOLDER = os.path.join(BASE_DIR, os.getenv("OUTPUT_FOLDER", "outputs"))

# 最大文件大小（字节），默认 50MB
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 52428800))

# 允许的文件扩展名集合
ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,xlsx,png,jpg,jpeg,gif,bmp,webp,jfif,md").split(","))

# 服务器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))

# PaddleOCR GPU 配置
OCR_USE_GPU = os.getenv("OCR_USE_GPU", "true").lower() == "true"

# PaddleOCR 语言模型：auto（自动检测）、en（英文）、ch（中文）
# auto 仅适用于 PDF（可从文本中检测），图片默认使用此值
OCR_LANG = os.getenv("OCR_LANG", "en")

# 确保上传和导出目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def is_allowed_file(filename):
    """
    检查文件扩展名是否在允许列表中
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_ext(filename):
    """
    获取文件扩展名（小写）
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
