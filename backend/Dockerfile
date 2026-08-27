FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# System deps for building (psycopg/bcrypt) + ffmpeg for audio validation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/data/uploads

# Runtime deps (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 ffmpeg curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY . .

# Create upload dir + volume mount point
RUN mkdir -p /data/uploads && chmod 777 /data
VOLUME ["/data/uploads"]

EXPOSE 8000

# Railway sets $PORT (default 8000)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]