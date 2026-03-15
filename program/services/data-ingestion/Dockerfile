# MONEYMAKER V1 Data Ingestion Service - Multi-stage Docker Build
# Build context: program/ (monorepo root)

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM golang:1.25-alpine AS builder

# hadolint ignore=DL3018
RUN apk add --no-cache git ca-certificates tzdata

WORKDIR /build

# Copy the shared go-common module first (for the replace directive).
COPY shared/go-common/ /build/shared/go-common/

# Copy go.mod and go.sum first to leverage Docker layer caching.
COPY services/data-ingestion/go.mod services/data-ingestion/go.sum* /build/services/data-ingestion/

WORKDIR /build/services/data-ingestion

# Adjust the replace directive for the Docker build context and download deps.
RUN go mod edit -replace github.com/moneymaker-v1/shared/go-common=/build/shared/go-common && \
    go mod download

# Copy the full service source code.
COPY services/data-ingestion/ /build/services/data-ingestion/

# Build static binary.
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-s -w -X main.version=$(date +%Y%m%d)" \
    -trimpath \
    -o /build/data-ingestion \
    ./cmd/server/

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM alpine:3.21

# hadolint ignore=DL3018
RUN apk add --no-cache \
    ca-certificates \
    tzdata \
    curl \
    && rm -rf /var/cache/apk/*

RUN addgroup -S moneymaker && adduser -S moneymaker -G moneymaker

RUN mkdir -p /app/config /app/data && chown -R moneymaker:moneymaker /app

WORKDIR /app

COPY --from=builder /build/data-ingestion /app/data-ingestion
COPY services/data-ingestion/config.yaml /app/config/config.yaml

RUN chown -R moneymaker:moneymaker /app

USER moneymaker

EXPOSE 5555 9090 9091

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9091/healthz || exit 1

ENV MONEYMAKER_ENV=production \
    MONEYMAKER_ZMQ_PUB_ADDR=tcp://*:5555 \
    MONEYMAKER_METRICS_PORT=9090

ENTRYPOINT ["/app/data-ingestion"]
