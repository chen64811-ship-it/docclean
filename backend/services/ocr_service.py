# -*- coding: utf-8 -*-
"""
PaddleOCR 文字识别服务
支持 GPU 加速（RTX 3060），GPU 不可用时自动降级到 CPU
使用单例模式避免重复初始化

V2 更新（2026-05-10）：
- 支持中英文双语模型切换（en / ch）
- 默认英文模型（海外产品定位）
- 自动语言检测，英文文档不再用中文模型
- 按语言缓存 OCR 实例，避免重复初始化
"""
import os
import sys
import re
import traceback
from config import OCR_USE_GPU, BASE_DIR

# 添加 DLL 搜索路径（确保能找到 zlibwapi.dll 等依赖）
_dll_paths = [
    os.path.dirname(sys.executable),  # 当前 Python 安装目录
    r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin',
    r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin',
    r'C:\Windows\System32',
]
for _p in _dll_paths:
    if os.path.exists(_p):
        try:
            os.add_dll_directory(_p)
        except Exception:
            pass

# 按语言缓存 OCR 实例：{"en": instance, "ch": instance}
_ocr_instances = {}
# 记录各语言实例使用的设备模式
_ocr_mode = {}  # {"en": True/False, "ch": True/False}


def detect_language(text):
    """
    检测文本的主要语言
    采样文本，统计 CJK 字符和 Latin 字符比例，返回推荐的语言代码

    参数：
        text: 待检测的文本字符串

    返回：
        "ch" — 中文为主（含中日韩文字）
        "en" — 英文/拉丁字母为主
        "mixed" — 中英混合
    """
    if not text or len(text.strip()) < 20:
        return "en"  # 太短默认英文

    # 采样前 5000 字符（加快检测速度）
    sample = text[:5000]

    # 统计字符类型
    cjk_count = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', sample))
    latin_count = len(re.findall(r'[a-zA-Z]', sample))
    total_meaningful = cjk_count + latin_count

    if total_meaningful == 0:
        return "en"

    cjk_ratio = cjk_count / total_meaningful

    if cjk_ratio > 0.5:
        return "ch"
    elif cjk_ratio > 0.15:
        return "mixed"  # 混合文档，中文模型兼容性更好
    else:
        return "en"


def _create_ocr_instance(lang, use_gpu):
    """
    创建一个新的 PaddleOCR 实例

    参数：
        lang: "en" 或 "ch"
        use_gpu: True/False
    """
    from paddleocr import PaddleOCR

    # 中英文模型的各自最优参数
    if lang == "en":
        # 英文模型参数：检测阈值稍高（英文排版更规整），识别批次可更大
        ocr = PaddleOCR(
            use_angle_cls=False,       # 关闭方向分类（GPU张量兼容性问题）
            lang="en",                 # 英文专用模型
            use_gpu=use_gpu,
            show_log=False,
            det_db_thresh=0.3,         # 检测阈值
            det_db_box_thresh=0.5,     # 检测框阈值（英文行更清晰，可提高）
            rec_batch_num=16 if use_gpu else 6,
        )
    else:
        # 中文模型参数（保持原有优化参数）
        ocr = PaddleOCR(
            use_angle_cls=False,
            lang="ch",
            use_gpu=use_gpu,
            show_log=False,
            det_db_thresh=0.3,
            rec_batch_num=16 if use_gpu else 6,
        )
    return ocr


def get_ocr_instance(lang="en"):
    """
    获取 PaddleOCR 单例实例
    优先使用 GPU（RTX 3060），GPU 不可用时自动降级到 CPU
    按语言缓存实例，同一语言不会重复初始化

    参数：
        lang: "en"（英文，默认）, "ch"（中文）, "mixed"（混合→用中文模型）

    返回：
        PaddleOCR 实例
    """
    global _ocr_instances, _ocr_mode

    # 混合文档用中文模型（中文模型同时支持中英文）
    if lang == "mixed":
        lang = "ch"

    # 如果这个语言的实例已经存在，直接返回
    if lang in _ocr_instances and _ocr_instances[lang] is not None:
        return _ocr_instances[lang]

    # 检查 PaddleOCR 是否已安装
    try:
        import paddle
    except ModuleNotFoundError:
        raise Exception(
            "OCR dependencies not installed. Please run: pip install paddlepaddle paddleocr"
        )

    # 优先尝试 GPU
    if OCR_USE_GPU:
        try:
            paddle.set_device("gpu:0")
            instance = _create_ocr_instance(lang, use_gpu=True)
            # 快速验证 GPU 可用
            _ocr_instances[lang] = instance
            _ocr_mode[lang] = True
            lang_label = "English" if lang == "en" else "Chinese"
            print(f"[OCR] GPU mode active (RTX 3060) — {lang_label} model loaded")
            return instance
        except Exception as e:
            print(f"[OCR] GPU init failed for {lang}, falling back to CPU: {e}")

    # 降级到 CPU
    try:
        paddle.set_device("cpu")
        instance = _create_ocr_instance(lang, use_gpu=False)
        _ocr_instances[lang] = instance
        _ocr_mode[lang] = False
        lang_label = "English" if lang == "en" else "Chinese"
        print(f"[OCR] CPU mode — {lang_label} model loaded")
        return instance
    except Exception as e:
        raise Exception(f"OCR initialization failed for language '{lang}': {str(e)}")


def is_gpu_available():
    """检查 GPU 模式是否在当前实例中启用"""
    global _ocr_mode
    if _ocr_mode:
        return any(_ocr_mode.values())
    return False


def ocr_image(image_path, lang="en"):
    """
    对图片进行 OCR 识别

    参数：
        image_path: 图片文件的绝对路径
        lang: 语言代码 — "en"（英文，默认）、"ch"（中文）、"auto"（自动检测）

    返回：
        识别出的文字（字符串），按阅读顺序拼接
    """
    try:
        # 获取对应语言的 OCR 实例
        ocr = get_ocr_instance(lang)

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

                # 英文模型置信度阈值可稍低（英文识别更稳定）
                min_conf = 0.4 if lang == "en" else 0.5
                if confidence > min_conf:
                    lines.append(text)

        return "\n".join(lines)

    except Exception as e:
        traceback.print_exc()
        raise Exception(f"OCR failed: {str(e)}")


def reset_ocr_cache():
    """
    重置 OCR 实例缓存（切换语言配置后调用）
    """
    global _ocr_instances, _ocr_mode
    _ocr_instances = {}
    _ocr_mode = {}
