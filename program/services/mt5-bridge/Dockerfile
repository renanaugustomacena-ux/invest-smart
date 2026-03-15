# MONEYMAKER V1 MT5 Bridge - Trade execution layer
# Build context: program/ (monorepo root)
#
# Note: MetaTrader5 Python package is Windows-only and listed as an
# optional dependency. The connector handles ImportError gracefully.

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r moneymaker && useradd -r -g moneymaker -d /app -s /sbin/nologin moneymaker

WORKDIR /app

# Copy shared libraries
COPY shared/python-common /app/shared/python-common
COPY shared/proto /app/shared/proto

# Copy service files
COPY services/mt5-bridge/pyproject.toml /app/
COPY services/mt5-bridge/src/ /app/src/

# Create proto gen directory (gitignored, generated at build time)
RUN mkdir -p /app/shared/proto/gen/moneymaker_proto && \
    touch /app/shared/proto/gen/__init__.py /app/shared/proto/gen/moneymaker_proto/__init__.py

# Install dependencies (MetaTrader5 is optional, not installed on Linux)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /app/shared/python-common && \
    pip install --no-cache-dir -e /app/shared/proto && \
    pip install --no-cache-dir -e /app

USER moneymaker

EXPOSE 50055 9094

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9094/')" || exit 1

ENTRYPOINT ["python", "-m", "mt5_bridge.main"]
