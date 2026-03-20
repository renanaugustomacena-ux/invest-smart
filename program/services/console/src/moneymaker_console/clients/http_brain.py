# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""REST client for the Algo Engine service (port 8082 health, 9092 metrics)."""

from __future__ import annotations

import os

from moneymaker_console.console_logging import log_event


class BrainClient:
    """HTTP client for the Algo Engine's REST and Prometheus endpoints."""

    def __init__(self) -> None:
        rest_port = os.environ.get("BRAIN_REST_PORT", "8082")
        metrics_port = os.environ.get("BRAIN_METRICS_PORT", "9092")
        self._rest_url = f"http://localhost:{rest_port}"
        self._metrics_url = f"http://localhost:{metrics_port}"
        self._available = True

    def _get(self, url: str, timeout: float = 5.0) -> dict | None:
        """Make a GET request, return JSON dict or None on failure."""
        if not self._available:
            return None
        try:
            import httpx

            resp = httpx.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except ImportError:
            self._available = False
            log_event("brain_client_unavailable", reason="httpx not installed")
            return None
        except Exception as exc:
            log_event("brain_request_error", url=url, error=str(exc))
            return None

    def _get_text(self, url: str, timeout: float = 5.0) -> str | None:
        """Make a GET request, return raw text or None."""
        if not self._available:
            return None
        try:
            import httpx

            resp = httpx.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except ImportError:
            self._available = False
            log_event("brain_client_unavailable", reason="httpx not installed")
            return None
        except Exception as exc:
            log_event("brain_request_error", url=url, error=str(exc))
            return None

    def get_health(self) -> dict | None:
        """Health check via metrics server (Brain has no separate REST server)."""
        if not self._available:
            return None
        try:
            import httpx

            resp = httpx.get(f"{self._metrics_url}/", timeout=5)
            if resp.status_code == 200:
                return {"status": "HEALTHY", "source": "metrics"}
            return None
        except ImportError:
            self._available = False
            log_event("brain_client_unavailable", reason="httpx not installed")
            return None
        except Exception as exc:
            log_event("brain_health_error", error=str(exc))
            return None

    def get_metrics(self) -> str | None:
        """GET /metrics — Prometheus metrics (text format)."""
        return self._get_text(f"{self._metrics_url}/metrics")

    def is_healthy(self) -> bool:
        """Quick health check."""
        data = self.get_health()
        if data is None:
            return False
        status = data.get("status", "")
        return status.upper() in ("HEALTHY", "OK", "UP")

    def parse_metric(self, metrics_text: str | None, name: str) -> float | None:
        """Extract a single metric value from Prometheus text format."""
        if not metrics_text:
            return None
        for line in metrics_text.splitlines():
            if line.startswith(name + " ") or line.startswith(name + "{"):
                parts = line.rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        return float(parts[1])
                    except ValueError:
                        pass
        return None

    @property
    def is_available(self) -> bool:
        return self._available
