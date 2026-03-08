"""Tests for moneymaker_common.health."""

import time

from moneymaker_common.health import HealthChecker, HealthStatus


class TestHealthChecker:
    def test_liveness_always_healthy(self):
        checker = HealthChecker("test")
        result = checker.liveness()
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "vivo"

    def test_readiness_before_set_ready(self):
        checker = HealthChecker("test")
        result = checker.readiness()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.message == "non pronto"

    def test_readiness_after_set_ready(self):
        checker = HealthChecker("test")
        checker.set_ready()
        result = checker.readiness()
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "pronto"

    def test_readiness_after_set_not_ready(self):
        checker = HealthChecker("test")
        checker.set_ready()
        checker.set_not_ready()
        result = checker.readiness()
        assert result.status == HealthStatus.UNHEALTHY

    def test_uptime_increases(self):
        checker = HealthChecker("test")
        t1 = checker.uptime
        time.sleep(0.01)
        t2 = checker.uptime
        assert t2 > t1

    def test_deep_check_all_pass(self):
        checker = HealthChecker("test")
        checker.register_check("db", lambda: None)
        checker.register_check("redis", lambda: None)
        result = checker.deep_check()
        assert result.status == HealthStatus.HEALTHY
        assert result.details["db"] == "ok"
        assert result.details["redis"] == "ok"

    def test_deep_check_one_fails(self):
        checker = HealthChecker("test")
        checker.register_check("db", lambda: None)
        checker.register_check("redis", _raise_connection_error)
        result = checker.deep_check()
        assert result.status == HealthStatus.UNHEALTHY
        assert result.details["db"] == "ok"
        assert "error" in result.details["redis"]

    def test_deep_check_no_checks_registered(self):
        checker = HealthChecker("test")
        result = checker.deep_check()
        assert result.status == HealthStatus.HEALTHY


def _raise_connection_error():
    raise ConnectionError("Redis connection refused")
