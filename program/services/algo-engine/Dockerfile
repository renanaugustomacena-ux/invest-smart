# MONEYMAKER V1 Algo Engine — Pure Algorithmic Trading Engine
# Build context: program/ (monorepo root)

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies required by grpcio and asyncpg, apply security patches
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 moneymaker && \
    useradd --uid 1000 --gid moneymaker --shell /bin/bash --create-home moneymaker

WORKDIR /app

# Copy shared libraries
COPY shared/python-common /app/shared/python-common
COPY shared/proto /app/shared/proto

# Copy algo-engine service
COPY services/algo-engine/pyproject.toml /app/
COPY services/algo-engine/src/ /app/src/

# Create proto gen directory (gitignored, generated at build time)
RUN mkdir -p /app/shared/proto/gen/moneymaker_proto && \
    touch /app/shared/proto/gen/__init__.py /app/shared/proto/gen/moneymaker_proto/__init__.py

# Install dependencies: shared libs -> algo-engine
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /app/shared/python-common && \
    pip install --no-cache-dir -e /app/shared/proto && \
    pip install --no-cache-dir -e /app

USER moneymaker

EXPOSE 50057 8087 9097

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9097/')" || exit 1

ENTRYPOINT ["python", "-m", "algo_engine.main"]
