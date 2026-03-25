# ── Stage 1: 构建前端 ────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ .
RUN npm run build

# ── Stage 2: Python 应用 ─────────────────────────────────
FROM python:3.11-slim AS app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev libffi-dev libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 非 root 用户
RUN useradd -r -s /bin/false -d /opt/secftp secftp

WORKDIR /opt/secftp

# Python 依赖（先拷贝 requirements 利用缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .
# 前端构建产物
COPY --from=frontend-builder /app/frontend/../static ./static

# 目录权限
RUN mkdir -p /data/secftp/files /tmp/upload_tmp \
    && chown -R secftp:secftp /opt/secftp /data/secftp /tmp/upload_tmp

USER secftp

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -sf http://localhost:8080/health || exit 1

EXPOSE 8080
CMD ["python", "-m", "waitress", "--host=0.0.0.0", "--port=8080", \
     "--threads=8", "--call", "app:create_app"]
