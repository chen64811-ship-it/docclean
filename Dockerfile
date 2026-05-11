# ============================================================
# DocClean Docker 镜像（CPU 版本）
# 适用场景：快速体验、没有 NVIDIA 显卡的机器
# 启动命令：docker-compose up -d
# ============================================================

FROM python:3.11-slim-bookworm
# 专为精简版Debian更换清华源（无报错，必成功）
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list


# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖（PaddleOCR 需要的底层库 + 中文字体）
RUN apt-get update -y --fix-missing && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*
# 设置工作目录
WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存）
COPY backend/requirements.txt /app/requirements.txt

# 安装 Python 依赖
# 注意：requirements.txt 里有 paddlepaddle-gpu，在 CPU 环境下装不上
# 所以先删掉那一行，再装 CPU 版 paddlepaddle
RUN sed -i '/paddlepaddle-gpu/d' /app/requirements.txt && \
    pip install --no-cache-dir paddlepaddle==2.6.2 && \
    pip install --no-cache-dir -r /app/requirements.txt

# 复制整个项目
COPY . /app/

# 创建必要的目录
RUN mkdir -p /app/uploads /app/outputs

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "backend/app.py"]
