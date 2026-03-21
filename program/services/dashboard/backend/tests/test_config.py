# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Tests for DashboardSettings configuration."""

from __future__ import annotations

import pytest

from backend.config import DashboardSettings


class TestDashboardSettingsDefaults:
    """Verify all default values are correct when no env vars are set."""

    def test_default_port(self):
        cfg = DashboardSettings()
        assert cfg.dashboard_port == 8888

    def test_default_host(self):
        cfg = DashboardSettings()
        assert cfg.dashboard_host == "0.0.0.0"

    def test_default_db_pool_min(self):
        cfg = DashboardSettings()
        assert cfg.db_pool_min == 2

    def test_default_db_pool_max(self):
        cfg = DashboardSettings()
        assert cfg.db_pool_max == 10

    def test_default_refresh_intervals(self):
        cfg = DashboardSettings()
        assert cfg.refresh_kpi == 10
        assert cfg.refresh_charts == 30
        assert cfg.refresh_macro == 300

    def test_default_prometheus_endpoints(self):
        cfg = DashboardSettings()
        assert cfg.prometheus_data_ingestion == "http://localhost:9090/metrics"
        assert cfg.prometheus_algo_engine == "http://localhost:9093/metrics"
        assert cfg.prometheus_mt5_bridge == "http://localhost:9094/metrics"

    def test_default_frontend_dist_dir(self):
        cfg = DashboardSettings()
        assert cfg.frontend_dist_dir == "frontend/dist"


class TestDashboardSettingsEnvOverrides:
    """Verify env var overrides via monkeypatch work correctly."""

    def test_override_port(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_PORT", "9999")
        cfg = DashboardSettings()
        assert cfg.dashboard_port == 9999

    def test_override_host(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_HOST", "127.0.0.1")
        cfg = DashboardSettings()
        assert cfg.dashboard_host == "127.0.0.1"

    def test_override_db_pool(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_DB_POOL_MIN", "5")
        monkeypatch.setenv("DASHBOARD_DB_POOL_MAX", "20")
        cfg = DashboardSettings()
        assert cfg.db_pool_min == 5
        assert cfg.db_pool_max == 20

    def test_override_refresh_kpi(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_REFRESH_KPI", "60")
        cfg = DashboardSettings()
        assert cfg.refresh_kpi == 60

    def test_override_refresh_charts(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_REFRESH_CHARTS", "120")
        cfg = DashboardSettings()
        assert cfg.refresh_charts == 120

    def test_override_refresh_macro(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_REFRESH_MACRO", "600")
        cfg = DashboardSettings()
        assert cfg.refresh_macro == 600

    def test_override_prometheus_endpoints(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_PROMETHEUS_DI", "http://prom:9090/metrics")
        monkeypatch.setenv("DASHBOARD_PROMETHEUS_BRAIN", "http://prom:9093/metrics")
        monkeypatch.setenv("DASHBOARD_PROMETHEUS_MT5", "http://prom:9094/metrics")
        cfg = DashboardSettings()
        assert cfg.prometheus_data_ingestion == "http://prom:9090/metrics"
        assert cfg.prometheus_algo_engine == "http://prom:9093/metrics"
        assert cfg.prometheus_mt5_bridge == "http://prom:9094/metrics"

    def test_override_frontend_dir(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_FRONTEND_DIR", "/opt/dashboard/dist")
        cfg = DashboardSettings()
        assert cfg.frontend_dist_dir == "/opt/dashboard/dist"
