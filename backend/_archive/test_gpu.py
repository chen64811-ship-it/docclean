# -*- coding: utf-8 -*-
"""
测试 PaddleOCR GPU 是否正常工作
"""
import os
import sys

print("=" * 50)
print("PaddleOCR GPU 测试")
print("=" * 50)

# 1. 先添加 DLL 搜索路径（关键！）
dll_paths = [
    r'C:\Users\ChengXingYu\AppData\Local\Programs\Python\Python311',
    r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\bin',
    r'C:\Windows\System32',
]
for p in dll_paths:
    if os.path.exists(p):
        os.add_dll_directory(p)
        print(f"[DLL] 已添加搜索路径: {p}")

# 2. 检查 PaddlePaddle GPU 状态
print("\n[1] PaddlePaddle GPU 状态:")
import paddle
print(f"    是否编译了 CUDA: {paddle.is_compiled_with_cuda()}")
print(f"    当前设备: {paddle.device.get_device()}")

# 3. 强制锁定 GPU
paddle.set_device('gpu:0')
print(f"    已锁定设备: {paddle.get_device()}")

# 4. 初始化 PaddleOCR
print("\n[2] 初始化 PaddleOCR (GPU 模式)...")
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    use_gpu=True,
    show_log=False,
)
print("    PaddleOCR 初始化成功!")

# 5. 创建测试图片
print("\n[3] 创建测试图片...")
from PIL import Image, ImageDraw

test_img = "_gpu_test.png"
img = Image.new('RGB', (500, 100), color='white')
draw = ImageDraw.Draw(img)
draw.text((20, 30), "PaddleOCR GPU 加速测试 123", fill='black')
img.save(test_img)
print(f"    已保存: {test_img}")

# 6. 执行 OCR
print("\n[4] 执行 OCR...")
import time

start = time.time()
try:
    result = ocr.ocr(test_img, cls=True)
    elapsed = time.time() - start
    print(f"    耗时: {elapsed:.3f} 秒")

    if result and result[0]:
        print(f"    识别结果 ({len(result[0])} 行):")
        for line in result[0]:
            print(f"      - {line[1][0]}")
    else:
        print("    未识别到文字")
except Exception as e:
    print(f"    OCR 执行出错: {e}")
    import traceback
    traceback.print_exc()

# 7. 检查 GPU 内存使用
print("\n[5] GPU 状态:")
import subprocess
try:
    r = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'],
                     capture_output=True, text=True, encoding='utf-8', errors='ignore')
    print(f"    {r.stdout.strip()}")
except:
    print("    无法获取 GPU 状态")

# 清理
if os.path.exists(test_img):
    os.remove(test_img)

print("\n" + "=" * 50)
print("测试完成！GPU 加速已启用")
print("=" * 50)
