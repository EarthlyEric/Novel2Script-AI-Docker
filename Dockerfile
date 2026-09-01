# syntax=docker/dockerfile:1

# =============================================================
# Novel2Script-AI single-image multi-stage build
#   Stage 1: Node builds the Vue 3 frontend into static assets
#   Stage 2: Python (FastAPI/Uvicorn) + Nginx runtime
#   - Nginx serves the frontend and reverse-proxies /api to Uvicorn (127.0.0.1:8000)
#   - SSE streaming endpoint (/api/script/convert-stream) is served unbuffered
# =============================================================

# ---------- Stage 1: Frontend build ----------
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy dependency manifests first to leverage layer caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENAI_API_KEY="" \
    OPENAI_BASE_URL="" \
    OPENAI_MODEL_NAME=""

# Install Nginx + backend Python dependencies (single merged layer for smaller image)
COPY backend/requirements.txt /tmp/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt /etc/nginx/sites-enabled/default

# Backend code (uvicorn must be started from /app as backend.main:app)
WORKDIR /app
COPY backend/ ./backend/

# Frontend static assets (Vite build output)
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

# Nginx site config + startup script
COPY docker/nginx-default.conf /etc/nginx/conf.d/default.conf
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/api/script/schema', timeout=4)" || exit 1

ENTRYPOINT ["sh", "/app/start.sh"]
