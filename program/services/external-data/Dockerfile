# MONEYMAKER External Data Service
# Fetches macro data from FRED, CBOE, CFTC
# Build context: program/ (monorepo root)

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 moneymaker && \
    useradd --uid 1000 --gid moneymaker --shell /bin/bash --create-home moneymaker

WORKDIR /app

# Copy shared library
COPY shared/python-common /app/shared/python-common

# Copy service files
COPY services/external-data/requirements.txt /app/requirements.txt
COPY services/external-data/src/ /app/src/

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /app/shared/python-common && \
    pip install --no-cache-dir -r /app/requirements.txt

# Set Python path
ENV PYTHONPATH=/app/src

USER moneymaker

EXPOSE 9095

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9095/health || exit 1

ENTRYPOINT ["python", "-m", "external_data.main"]
