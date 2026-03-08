"""HTTP client for the MONEYMAKER Dashboard service (port 8000)."""

from __future__ import annotations

import os

from moneymaker_console.console_logging import log_event


class DashboardClient:
    """REST client for the Dashboard service."""

    def __init__(self) -> None:
        port = os.environ.get("DASHBOARD_PORT", "8000")
        self._base_url = f"http://localhost:{port}"
        self._available = True

    def get_health(self) -> dict | None:
        """GET /health — Dashboard health check."""
        if not self._available:
            return None
        try:
            import httpx
            resp = httpx.get(f"{self._base_url}/health", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except ImportError:
            self._available = False
            log_event("dashboard_client_unavailable", reason="httpx not installed")
            return None
        except Exception as exc:
            log_event("dashboard_health_error", error=str(exc))
            return None

    def is_healthy(self) -> bool:
        return self.get_health() is not None

    @property
    def url(self) -> str:
        return self._base_url

    @property
    def is_available(self) -> bool:
        return self._available
