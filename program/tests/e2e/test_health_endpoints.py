"""E2E: Verify all service health endpoints respond correctly.

Requires the full Docker stack to be running.
Run with: python -m pytest tests/e2e/test_health_endpoints.py -v
"""

import os
import pytest

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

BASE = os.getenv("E2E_BASE_URL", "http://localhost")


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestHealthEndpoints:
    """Verify every service's health endpoint returns 200."""

    @pytest.fixture(scope="class")
    def client(self):
        with httpx.Client(timeout=15.0) as c:
            yield c

    def test_algo_engine_health(self, client):
        r = client.get(f"{BASE}:9097/")
        assert r.status_code == 200

    def test_dashboard_health(self, client):
        r = client.get(f"{BASE}:8888/health")
        assert r.status_code == 200

    def test_data_ingestion_health(self, client):
        r = client.get(f"{BASE}:8081/healthz")
        assert r.status_code == 200

    def test_prometheus_health(self, client):
        r = client.get(f"{BASE}:9091/-/healthy")
        assert r.status_code == 200

    def test_grafana_health(self, client):
        r = client.get(f"{BASE}:3000/api/health")
        assert r.status_code == 200


@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestMetricsEndpoints:
    """Verify Prometheus metrics endpoints return valid exposition format."""

    @pytest.fixture(scope="class")
    def client(self):
        with httpx.Client(timeout=15.0) as c:
            yield c

    @pytest.mark.parametrize(
        "service,port",
        [
            ("data-ingestion", 9090),
            ("algo-engine", 9097),
            ("mt5-bridge", 9094),
        ],
    )
    def test_metrics_endpoint(self, client, service, port):
        r = client.get(f"{BASE}:{port}/metrics")
        assert r.status_code == 200
        # Prometheus exposition format contains # HELP or # TYPE lines
        assert "# " in r.text or "python_info" in r.text or "go_" in r.text
