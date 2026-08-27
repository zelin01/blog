FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 只换 pip 源，apt 不动它。amd64 上这些包都有预编译 wheel，不需要 gcc
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY backend/ .

RUN mkdir -p uploads static

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]