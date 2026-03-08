# MONEYMAKER V1 Dashboard Service - Multi-stage Docker Build
# Build context: program/ (monorepo root)

# --- Stage 1: Build frontend ---
FROM node:22-alpine AS frontend-builder

WORKDIR /build/frontend
COPY services/dashboard/frontend/package.json services/dashboard/frontend/package-lock.json* ./
RUN npm ci
COPY services/dashboard/frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime ---
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 1000 moneymaker && \
    useradd --uid 1000 --gid moneymaker --shell /bin/bash --create-home moneymaker

WORKDIR /app

# Copy shared libraries
COPY shared/python-common /app/shared/python-common

# Copy dashboard backend + config
COPY services/dashboard/pyproject.toml /app/
COPY services/dashboard/backend/ /app/backend/

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /app/shared/python-common && \
    pip install --no-cache-dir -e /app

USER moneymaker

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/health')" || exit 1

ENTRYPOINT ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8888"]
