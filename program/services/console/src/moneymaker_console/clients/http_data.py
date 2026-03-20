# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""HTTP client for the Data Ingestion service (Go, port 8081)."""

from __future__ import annotations

import os

from moneymaker_console.console_logging import log_event


class DataIngestionClient:
    """HTTP client for Data Ingestion health and metrics endpoints."""

    def __init__(self) -> None:
        health_port = os.environ.get("DATA_INGESTION_HEALTH_PORT", "8081")
        metrics_port = os.environ.get("MONEYMAKER_METRICS_PORT", "9090")
        self._health_url = f"http://localhost:{health_port}"
        self._metrics_url = f"http://localhost:{metrics_port}"
        self._available = True

    def get_health(self) -> dict | None:
        """GET /healthz — Data Ingestion health."""
        if not self._available:
            return None
        try:
            import httpx

            resp = httpx.get(f"{self._health_url}/healthz", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except ImportError:
            self._available = False
            log_event("data_client_unavailable", reason="httpx not installed")
            return None
        except Exception:
            # Try /health as fallback
            try:
                import httpx

                resp = httpx.get(f"{self._health_url}/health", timeout=5)
                resp.raise_for_status()
                return resp.json()
            except Exception as fallback_exc:
                log_event("data_health_error", error=str(fallback_exc))
                return None

    def get_readiness(self) -> dict | None:
        """GET /readyz — Readiness check."""
        if not self._available:
            return None
        try:
            import httpx

            resp = httpx.get(f"{self._health_url}/readyz", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            log_event("data_readiness_error", error=str(exc))
            return None

    def get_metrics(self) -> str | None:
        """GET /metrics — Prometheus metrics."""
        if not self._available:
            return None
        try:
            import httpx

            resp = httpx.get(f"{self._metrics_url}/metrics", timeout=5)
            return resp.text
        except Exception as exc:
            log_event("data_metrics_error", error=str(exc))
            return None

    def is_healthy(self) -> bool:
        """Quick health check."""
        return self.get_health() is not None

    @property
    def is_available(self) -> bool:
        return self._available
