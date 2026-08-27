# ── Build backend wheels ────────────────────────────────
FROM python:3.12-slim AS backend-builder
WORKDIR /b
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ── Build frontend static ───────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /f
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# ── Runtime: backend + nginx serving the SPA ───────────
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UPLOAD_DIR=/data/uploads

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 ffmpeg nginx curl && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY backend/ /app/
COPY --from=frontend-builder /f/dist /app/www

COPY nginx.conf /etc/nginx/conf.d/default.conf.template
COPY start.sh /start.sh
RUN chmod +x /start.sh \
    && mkdir -p /data/uploads /app/www && chmod 777 /data \
    && rm -f /etc/nginx/sites-enabled/default && rmdir /etc/nginx/sites-enabled 2>/dev/null || true

EXPOSE 8000 80
CMD ["/start.sh"]