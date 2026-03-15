"""Tests for brain (Algo Engine) commands."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from moneymaker_console.commands.brain import (
    _brain_checkpoint,
    _brain_confidence,
    _brain_drift,
    _brain_features,
    _brain_maturity,
    _brain_pause,
    _brain_regime,
    _brain_resume,
    _brain_sentry,
    _brain_spiral,
    _brain_start,
    _brain_status,
    _brain_stop,
    register,
)
from moneymaker_console.registry import CommandRegistry


@patch("moneymaker_console.commands.brain.ClientFactory")
class TestBrainCommands:
    def test_start_default_mode(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _brain_start()
        assert "rule-based" in result
        assert "[success]" in result

    def test_start_custom_mode(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _brain_start("--mode", "paper")
        assert "paper" in result

    def test_stop_graceful(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        result = _brain_stop()
        mock_docker.restart.assert_called()

    def test_stop_force(self, mock_cf, mock_docker):
        mock_cf.get_docker.return_value = mock_docker
        with patch("moneymaker_console.runner.subprocess.run") as mock_run:
            import subprocess
            mock_run.return_value = subprocess.CompletedProcess(
                args=["docker"], returncode=0, stdout="killed\n", stderr=""
            )
            result = _brain_stop("--force")
            assert mock_run.called

    def test_pause_success(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.set.return_value = True
        result = _brain_pause()
        assert "PAUSED" in result

    def test_pause_redis_fail(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.set.return_value = False
        result = _brain_pause()
        assert "warning" in result.lower()

    def test_resume_success(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.delete.return_value = True
        result = _brain_resume()
        assert "RESUMED" in result

    def test_resume_redis_fail(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.delete.return_value = False
        result = _brain_resume()
        assert "warning" in result.lower()

    def test_status_with_health(self, mock_cf, mock_brain_client):
        mock_brain_client.get_health.return_value = {
            "status": "running",
            "uptime_seconds": 3600,
            "details": {"signals": 42},
        }
        mock_cf.get_brain.return_value = mock_brain_client
        result = _brain_status()
        assert "running" in result
        assert "3600" in result

    def test_status_fallback_db(self, mock_cf, mock_brain_client, mock_db):
        mock_brain_client.get_health.return_value = None
        mock_cf.get_brain.return_value = mock_brain_client
        mock_db.ping.return_value = True
        mock_db.query_one.return_value = ("EURUSD", "BUY", 0.85, "2024-01-15")
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_status()
        assert "EURUSD" in result

    def test_status_unavailable(self, mock_cf, mock_brain_client, mock_db):
        mock_brain_client.get_health.return_value = None
        mock_cf.get_brain.return_value = mock_brain_client
        mock_db.ping.return_value = False
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_status()
        assert "not available" in result.lower()

    def test_regime_from_redis(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get_json.return_value = {
            "regime": "TRENDING",
            "confidence": 0.9,
            "votes": {"vol": "TRENDING"},
        }
        result = _brain_regime()
        assert "TRENDING" in result

    def test_regime_from_db(self, mock_cf, mock_redis_client, mock_db):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get_json.return_value = None
        mock_db.query_one.return_value = ("RANGING", 0.7, "2024-01-15")
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_regime()
        assert "RANGING" in result

    def test_regime_no_data(self, mock_cf, mock_redis_client, mock_db):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get_json.return_value = None
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_regime()
        assert "No regime" in result

    def test_maturity_found(self, mock_cf, mock_db):
        mock_db.query_one.return_value = ("MATURE", "live", 1.0, "2024-01-15")
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_maturity()
        assert "MATURE" in result
        assert "live" in result

    def test_maturity_none(self, mock_cf, mock_db):
        mock_db.query_one.return_value = None
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_maturity()
        assert "No maturity" in result

    def test_drift_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("rsi_14", 2.5, True, "2024-01-15"),
            ("atr_14", 0.3, False, "2024-01-15"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_drift()
        assert "[!!]" in result
        assert "[OK]" in result

    def test_drift_none(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_drift()
        assert "No drift" in result

    def test_spiral_active(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get_json.return_value = {
            "active": True,
            "consecutive_losses": 5,
            "cooldown_remaining": 120,
            "lot_reduction_factor": 0.5,
        }
        result = _brain_spiral()
        assert "True" in result
        assert "5" in result

    def test_spiral_inactive(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.get_json.return_value = None
        result = _brain_spiral()
        assert "INACTIVE" in result

    def test_confidence_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [(3, 15), (7, 8)]
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_confidence()
        assert "Confidence" in result

    def test_confidence_with_symbol(self, mock_cf, mock_db):
        mock_db.query.return_value = [(5, 10)]
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_confidence("EURUSD")
        assert "Confidence" in result

    def test_confidence_none(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_confidence()
        assert "No signal" in result

    def test_features_no_args(self, mock_cf):
        result = _brain_features()
        assert "[error]" in result
        assert "Usage" in result

    def test_features_found(self, mock_cf, mock_db):
        mock_db.query.return_value = [
            ("rsi_14", 55.2, "2024-01-15"),
        ]
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_features("EURUSD")
        assert "EURUSD" in result
        assert "rsi_14" in result

    def test_features_none(self, mock_cf, mock_db):
        mock_db.query.return_value = []
        mock_cf.get_postgres.return_value = mock_db
        result = _brain_features("XAUUSD")
        assert "No feature" in result

    def test_checkpoint_success(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.publish.return_value = True
        result = _brain_checkpoint()
        assert "[success]" in result

    def test_checkpoint_fail(self, mock_cf, mock_redis_client):
        mock_cf.get_redis.return_value = mock_redis_client
        mock_redis_client.publish.return_value = False
        result = _brain_checkpoint()
        assert "warning" in result.lower()


class TestBrainSentry:
    def test_no_dsn(self):
        with patch.dict(os.environ, {}, clear=False):
            if "SENTRY_DSN" in os.environ:
                del os.environ["SENTRY_DSN"]
            result = _brain_sentry()
            assert "not configured" in result

    def test_with_dsn(self):
        with patch.dict(os.environ, {"SENTRY_DSN": "https://abc@sentry.io/123"}):
            result = _brain_sentry()
            assert "Configured" in result


class TestBrainRegister:
    def test_register_adds_commands(self):
        reg = CommandRegistry()
        register(reg)
        assert "brain" in reg.categories
        cmds = reg._commands["brain"]
        expected = ["start", "stop", "pause", "resume", "status",
                    "checkpoint", "regime", "drift", "maturity",
                    "spiral", "confidence", "features", "sentry"]
        for cmd in expected:
            assert cmd in cmds
