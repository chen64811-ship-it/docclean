# ============================================================
# DocClean Docker Image (CPU version)
# Use case: quick demo, machines without NVIDIA GPU
# Start: docker-compose up -d
# ============================================================

FROM python:3.11-slim-bookworm
# Optional: use a regional APT mirror for faster downloads
# Set DEBIAN_MIRROR build arg to override, e.g.:
#   docker build --build-arg DEBIAN_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian .
ARG DEBIAN_MIRROR=""
RUN if [ -n "$DEBIAN_MIRROR" ]; then \
        echo "deb $DEBIAN_MIRROR bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
        echo "deb $DEBIAN_MIRROR bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
        echo "deb ${DEBIAN_MIRROR}-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    fi

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (PaddleOCR base libraries + CJK fonts)
RUN apt-get update -y --fix-missing && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency file first (leverage Docker layer caching)
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
# Note: requirements.txt contains paddlepaddle-gpu which fails on CPU-only machines,
# so remove that line and install CPU version of paddlepaddle
RUN sed -i '/paddlepaddle-gpu/d' /app/requirements.txt && \
    pip install --no-cache-dir paddlepaddle==2.6.2 && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy entire project
COPY . /app/

# Create required directories
RUN mkdir -p /app/uploads /app/outputs

# Expose port
EXPOSE 5000

# Start command
CMD ["python", "backend/app.py"]
