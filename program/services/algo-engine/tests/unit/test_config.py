"""Tests for AlgoEngineSettings — configuration loading and validation.

All tests use REAL class instances — no MagicMock, no @patch, no unittest.mock.
Environment variable overrides use pytest's monkeypatch fixture.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from algo_engine.config import AlgoEngineSettings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_settings(**overrides) -> AlgoEngineSettings:
    """Instantiate AlgoEngineSettings with explicit keyword overrides."""
    return AlgoEngineSettings(**overrides)


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestDefaultValues:
    """Verify that all defaults are loaded correctly without env vars."""

    def test_default_service_identity(self):
        cfg = _build_settings()
        assert cfg.algo_service_name == "algo-engine"

    def test_default_ports(self):
        cfg = _build_settings()
        assert cfg.algo_grpc_port == 50057
        assert cfg.algo_rest_port == 8087
        assert cfg.algo_metrics_port == 9097

    def test_default_signal_thresholds(self):
        cfg = _build_settings()
        assert cfg.algo_confidence_threshold == 0.65
        assert cfg.algo_max_signals_per_hour == 10

    def test_default_risk_limits(self):
        cfg = _build_settings()
        assert cfg.algo_max_open_positions == 5
        assert cfg.algo_max_daily_loss_pct == 2.0
        assert cfg.algo_max_drawdown_pct == 5.0

    def test_default_indicator_periods(self):
        cfg = _build_settings()
        assert cfg.algo_default_rsi_period == 14
        assert cfg.algo_default_ema_fast == 12
        assert cfg.algo_default_ema_slow == 26
        assert cfg.algo_default_sma_period == 20
        assert cfg.algo_default_bb_period == 20
        assert cfg.algo_default_atr_period == 14

    def test_default_timeframes(self):
        cfg = _build_settings()
        assert cfg.algo_primary_timeframe == "M5"
        assert cfg.algo_timeframes == "M1,M5,M15,H1"

    def test_default_position_sizing(self):
        cfg = _build_settings()
        assert cfg.algo_risk_per_trade_pct == 1.0
        assert cfg.algo_default_equity == 1000
        assert cfg.algo_default_leverage == 100
        assert cfg.algo_max_lots == 0.10

    def test_default_telegram_fields_empty(self):
        cfg = _build_settings()
        assert cfg.algo_telegram_bot_token == ""
        assert cfg.algo_telegram_chat_id == ""


# ---------------------------------------------------------------------------
# Validator: risk_per_trade_pct  (0.1 <= v <= 5.0)
# ---------------------------------------------------------------------------


class TestRiskPerTradeValidator:
    def test_lower_boundary_valid(self):
        cfg = _build_settings(algo_risk_per_trade_pct=0.1)
        assert cfg.algo_risk_per_trade_pct == 0.1

    def test_upper_boundary_valid(self):
        cfg = _build_settings(algo_risk_per_trade_pct=5.0)
        assert cfg.algo_risk_per_trade_pct == 5.0

    def test_below_lower_boundary_raises(self):
        with pytest.raises(ValidationError, match="risk_per_trade_pct"):
            _build_settings(algo_risk_per_trade_pct=0.05)

    def test_above_upper_boundary_raises(self):
        with pytest.raises(ValidationError, match="risk_per_trade_pct"):
            _build_settings(algo_risk_per_trade_pct=5.1)


# ---------------------------------------------------------------------------
# Validator: max_drawdown_pct  (1.0 <= v <= 25.0)
# ---------------------------------------------------------------------------


class TestMaxDrawdownValidator:
    def test_lower_boundary_valid(self):
        cfg = _build_settings(algo_max_drawdown_pct=1.0)
        assert cfg.algo_max_drawdown_pct == 1.0

    def test_upper_boundary_valid(self):
        cfg = _build_settings(algo_max_drawdown_pct=25.0)
        assert cfg.algo_max_drawdown_pct == 25.0

    def test_below_lower_boundary_raises(self):
        with pytest.raises(ValidationError, match="max_drawdown_pct"):
            _build_settings(algo_max_drawdown_pct=0.9)

    def test_above_upper_boundary_raises(self):
        with pytest.raises(ValidationError, match="max_drawdown_pct"):
            _build_settings(algo_max_drawdown_pct=25.1)


# ---------------------------------------------------------------------------
# Validator: max_daily_loss_pct  (0.5 <= v <= 10.0)
# ---------------------------------------------------------------------------


class TestMaxDailyLossValidator:
    def test_lower_boundary_valid(self):
        cfg = _build_settings(algo_max_daily_loss_pct=0.5)
        assert cfg.algo_max_daily_loss_pct == 0.5

    def test_above_upper_boundary_raises(self):
        with pytest.raises(ValidationError, match="max_daily_loss_pct"):
            _build_settings(algo_max_daily_loss_pct=10.1)


# ---------------------------------------------------------------------------
# Validator: confidence_threshold  (0.0 < v <= 1.0)
# ---------------------------------------------------------------------------


class TestConfidenceThresholdValidator:
    def test_upper_boundary_valid(self):
        cfg = _build_settings(algo_confidence_threshold=1.0)
        assert cfg.algo_confidence_threshold == 1.0

    def test_zero_raises(self):
        with pytest.raises(ValidationError, match="confidence_threshold"):
            _build_settings(algo_confidence_threshold=0.0)

    def test_negative_raises(self):
        with pytest.raises(ValidationError, match="confidence_threshold"):
            _build_settings(algo_confidence_threshold=-0.1)

    def test_above_one_raises(self):
        with pytest.raises(ValidationError, match="confidence_threshold"):
            _build_settings(algo_confidence_threshold=1.01)


# ---------------------------------------------------------------------------
# Validator: indicator periods must be > 0
# ---------------------------------------------------------------------------


class TestPeriodPositiveValidator:
    def test_zero_rsi_period_raises(self):
        with pytest.raises(ValidationError, match="Indicator period must be > 0"):
            _build_settings(algo_default_rsi_period=0)

    def test_negative_atr_period_raises(self):
        with pytest.raises(ValidationError, match="Indicator period must be > 0"):
            _build_settings(algo_default_atr_period=-1)


# ---------------------------------------------------------------------------
# Validator: max_signals_per_hour > 0
# ---------------------------------------------------------------------------


class TestMaxSignalsValidator:
    def test_zero_raises(self):
        with pytest.raises(ValidationError, match="max_signals_per_hour must be > 0"):
            _build_settings(algo_max_signals_per_hour=0)


# ---------------------------------------------------------------------------
# Validator: max_lots > 0
# ---------------------------------------------------------------------------


class TestMaxLotsValidator:
    def test_zero_raises(self):
        with pytest.raises(ValidationError, match="max_lots must be > 0"):
            _build_settings(algo_max_lots=0.0)

    def test_negative_raises(self):
        with pytest.raises(ValidationError, match="max_lots must be > 0"):
            _build_settings(algo_max_lots=-0.01)


# ---------------------------------------------------------------------------
# Model validator: EMA ordering (fast < slow)
# ---------------------------------------------------------------------------


class TestEmaOrdering:
    def test_fast_less_than_slow_valid(self):
        cfg = _build_settings(algo_default_ema_fast=10, algo_default_ema_slow=20)
        assert cfg.algo_default_ema_fast == 10
        assert cfg.algo_default_ema_slow == 20

    def test_fast_equals_slow_raises(self):
        with pytest.raises(ValidationError, match="ema_fast.*must be <.*ema_slow"):
            _build_settings(algo_default_ema_fast=20, algo_default_ema_slow=20)

    def test_fast_greater_than_slow_raises(self):
        with pytest.raises(ValidationError, match="ema_fast.*must be <.*ema_slow"):
            _build_settings(algo_default_ema_fast=30, algo_default_ema_slow=20)


# ---------------------------------------------------------------------------
# safe_dump() — sensitive field masking
# ---------------------------------------------------------------------------


class TestSafeDump:
    def test_masks_bot_token_when_set(self):
        cfg = _build_settings(algo_telegram_bot_token="super-secret-token-123")
        dumped = cfg.safe_dump()
        assert dumped["algo_telegram_bot_token"] == "***"

    def test_does_not_mask_empty_bot_token(self):
        cfg = _build_settings(algo_telegram_bot_token="")
        dumped = cfg.safe_dump()
        assert dumped["algo_telegram_bot_token"] == ""

    def test_safe_dump_contains_all_fields(self):
        cfg = _build_settings()
        dumped = cfg.safe_dump()
        assert "algo_service_name" in dumped
        assert "algo_grpc_port" in dumped
        assert "algo_confidence_threshold" in dumped
        assert "algo_max_lots" in dumped


# ---------------------------------------------------------------------------
# Env var override via monkeypatch
# ---------------------------------------------------------------------------


class TestEnvVarOverride:
    def test_env_overrides_grpc_port(self, monkeypatch):
        monkeypatch.setenv("ALGO_GRPC_PORT", "60000")
        cfg = AlgoEngineSettings()
        assert cfg.algo_grpc_port == 60000

    def test_env_overrides_confidence_threshold(self, monkeypatch):
        monkeypatch.setenv("ALGO_CONFIDENCE_THRESHOLD", "0.80")
        cfg = AlgoEngineSettings()
        assert cfg.algo_confidence_threshold == 0.80

    def test_env_overrides_service_name(self, monkeypatch):
        monkeypatch.setenv("ALGO_SERVICE_NAME", "custom-engine")
        cfg = AlgoEngineSettings()
        assert cfg.algo_service_name == "custom-engine"
