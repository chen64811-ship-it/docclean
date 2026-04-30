# -*- coding: utf-8 -*-
"""
PaddleOCR 文字识别服务
支持 GPU 加速（RTX 3060），GPU 不可用时自动降级到 CPU
使用单例模式避免重复初始化
"""
import os
import traceback
from config import OCR_USE_GPU, BASE_DIR

# 添加 DLL 搜索路径（确保能找到 zlibwapi.dll）
_dll_paths = [
    r'C:\Users\ChengXingYu\AppData\Local\Programs\Python\Python311',
    r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin',
    r'C:\Windows\System32',
]
for _p in _dll_paths:
    if os.path.exists(_p):
        try:
            os.add_dll_directory(_p)
        except Exception:
            pass

# 全局 OCR 实例，避免重复初始化
_ocr_instance = None
_ocr_use_gpu = None  # 记录实际使用的模式


def get_ocr_instance():
    """
    获取 PaddleOCR 单例实例
    优先使用 GPU（RTX 3060），GPU 不可用时自动降级到 CPU
    """
    global _ocr_instance, _ocr_use_gpu
    if _ocr_instance is not None:
        return _ocr_instance

    try:
        import paddle
        from paddleocr import PaddleOCR
    except ModuleNotFoundError as e:
        raise Exception(
            "OCR 依赖未安装：请安装 paddlepaddle 与 paddleocr（例如：pip install paddlepaddle paddleocr）"
        ) from e

    # 优先尝试 GPU
    if OCR_USE_GPU:
        try:
            # 仅在 GPU 模式下设置设备，避免 CPU 环境直接报错
            paddle.set_device("gpu:0")
            _ocr_instance = PaddleOCR(
                use_angle_cls=True,    # 启用方向分类
                lang="ch",              # 中文
                use_gpu=True,           # 启用 GPU
                show_log=False,         # 关闭日志
                det_db_thresh=0.3,      # 检测阈值（降低提高召回）
                rec_batch_num=16,       # 批处理大小（GPU 适合大批次）
            )
            # 提前测试 GPU 是否可用
            _ocr_use_gpu = True
            print("[OCR] 使用 GPU 加速模式 (RTX 3060)")
            return _ocr_instance
        except Exception as e:
            print(f"[OCR] GPU 初始化失败，降级到 CPU: {e}")
            _ocr_instance = None

    # 降级到 CPU
    try:
        paddle.set_device("cpu")
        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            use_gpu=False,
            show_log=False,
            rec_batch_num=6,  # CPU 适合小批次
        )
        _ocr_use_gpu = False
        print("[OCR] 使用 CPU 模式")
        return _ocr_instance
    except Exception as e:
        raise Exception(f"OCR 初始化失败：{str(e)}")


def is_gpu_available():
    """检查 GPU 模式是否启用"""
    global _ocr_use_gpu
    if _ocr_use_gpu is not None:
        return _ocr_use_gpu
    # 初始化一次来检查
    get_ocr_instance()
    return _ocr_use_gpu


def ocr_image(image_path):
    """
    对图片进行 OCR 识别

    参数：
        image_path: 图片文件的绝对路径

    返回：
        识别出的文字（字符串），按阅读顺序拼接
    """
    try:
        # 获取已初始化的实例
        ocr = get_ocr_instance()

        # 执行 OCR 识别
        result = ocr.ocr(image_path, cls=True)

        if not result or not result[0]:
            return ""

        # 按从上到下、从左到右的顺序提取文字
        lines = []
        for line in result[0]:
            if line and len(line) >= 2:
                text = line[1][0]  # 识别出的文字
                confidence = line[1][1]  # 置信度
                # 过滤低置信度的结果
                if confidence > 0.5:
                    lines.append(text)

        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"OCR识别失败：{str(e)}")
