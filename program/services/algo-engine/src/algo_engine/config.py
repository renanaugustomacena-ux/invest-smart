"""Configuration for the Algo Engine service.

Mirrors BrainSettings from algo-engine but excludes all ML-related fields.
Uses ALGO_ prefix for environment variables.
"""

from __future__ import annotations

from pydantic import field_validator, model_validator

from moneymaker_common.config import MoneyMakerBaseSettings


class AlgoEngineSettings(MoneyMakerBaseSettings):
    """Settings for algo-engine — mirrors BrainSettings minus ML fields."""

    # --- Service identity ---
    algo_service_name: str = "algo-engine"

    # --- Ports ---
    algo_grpc_port: int = 50057
    algo_rest_port: int = 8087
    algo_metrics_port: int = 9097

    # --- ZeroMQ data feed ---
    algo_zmq_data_feed: str = "tcp://localhost:5555"

    # --- MT5 Bridge target ---
    algo_mt5_bridge_target: str = "localhost:50055"

    # --- Signal thresholds ---
    algo_confidence_threshold: float = 0.65
    algo_max_signals_per_hour: int = 10

    # --- Risk limits ---
    algo_max_open_positions: int = 5
    algo_max_daily_loss_pct: float = 2.0
    algo_max_drawdown_pct: float = 5.0

    # --- Indicator periods ---
    algo_default_rsi_period: int = 14
    algo_default_ema_fast: int = 12
    algo_default_ema_slow: int = 26
    algo_default_sma_period: int = 20
    algo_default_bb_period: int = 20
    algo_default_atr_period: int = 14

    # --- Timeframes ---
    algo_primary_timeframe: str = "M5"
    algo_timeframes: str = "M1,M5,M15,H1"

    # --- Position sizing ---
    algo_risk_per_trade_pct: float = 1.0
    algo_default_equity: int = 1000
    algo_default_leverage: int = 100
    algo_max_lots: float = 0.10

    # --- Correlation ---
    algo_max_exposure_per_currency: int = 3

    # --- Spiral protection ---
    algo_spiral_loss_threshold: int = 3
    algo_spiral_max_losses: int = 5
    algo_spiral_cooldown_minutes: int = 60

    # --- Redis ---
    algo_redis_url: str = "redis://localhost:6379/0"

    # --- Telegram alerting ---
    algo_telegram_bot_token: str = ""
    algo_telegram_chat_id: str = ""

    # --- Economic calendar ---
    algo_calendar_file: str = ""
    algo_calendar_blackout_before_min: int = 15
    algo_calendar_blackout_after_min: int = 15

    model_config = {"env_prefix": "", "case_sensitive": False}

    @field_validator("algo_risk_per_trade_pct")
    @classmethod
    def _validate_risk_per_trade(cls, v: float) -> float:
        if not 0.1 <= v <= 5.0:
            raise ValueError(f"risk_per_trade_pct must be 0.1–5.0, got {v}")
        return v

    @field_validator("algo_max_drawdown_pct")
    @classmethod
    def _validate_max_drawdown(cls, v: float) -> float:
        if not 1.0 <= v <= 25.0:
            raise ValueError(f"max_drawdown_pct must be 1.0–25.0, got {v}")
        return v

    @field_validator("algo_max_daily_loss_pct")
    @classmethod
    def _validate_max_daily_loss(cls, v: float) -> float:
        if not 0.5 <= v <= 10.0:
            raise ValueError(f"max_daily_loss_pct must be 0.5–10.0, got {v}")
        return v

    @field_validator("algo_confidence_threshold")
    @classmethod
    def _validate_confidence_threshold(cls, v: float) -> float:
        if not 0.0 < v <= 1.0:
            raise ValueError(f"confidence_threshold must be (0.0, 1.0], got {v}")
        return v

    @field_validator(
        "algo_default_rsi_period",
        "algo_default_ema_fast",
        "algo_default_ema_slow",
        "algo_default_sma_period",
        "algo_default_bb_period",
        "algo_default_atr_period",
    )
    @classmethod
    def _validate_periods_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"Indicator period must be > 0, got {v}")
        return v

    @field_validator("algo_max_signals_per_hour")
    @classmethod
    def _validate_max_signals(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"max_signals_per_hour must be > 0, got {v}")
        return v

    @field_validator("algo_max_lots")
    @classmethod
    def _validate_max_lots(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"max_lots must be > 0, got {v}")
        return v

    @model_validator(mode="after")
    def _validate_ema_ordering(self) -> AlgoEngineSettings:
        if self.algo_default_ema_fast >= self.algo_default_ema_slow:
            raise ValueError(
                f"ema_fast ({self.algo_default_ema_fast}) must be < "
                f"ema_slow ({self.algo_default_ema_slow})"
            )
        return self

    def safe_dump(self) -> dict:
        """Return settings dict with sensitive fields masked."""
        data = self.model_dump()
        for key in ("algo_telegram_bot_token",):
            if data.get(key):
                data[key] = "***"
        return data
