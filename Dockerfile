FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWREBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1. 换 Debian 国内源，apt-get 从几分钟变几秒
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. pip 换国内源，安装依赖飞快
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY backend/ .

RUN mkdir -p uploads static

# 3. 非 root 用户运行（安全加分）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 4. 生产环境开 4 个 worker（并发更高）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]