"""Dashboard configuration extending MoneyMakerBaseSettings."""

from __future__ import annotations

from pydantic import Field
from moneymaker_common.config import MoneyMakerBaseSettings


class DashboardSettings(MoneyMakerBaseSettings):
    """Dashboard-specific settings.

    Inherits MONEYMAKER_* env vars from MoneyMakerBaseSettings (no prefix override).
    Dashboard-specific vars use DASHBOARD_ prefix via Field(alias=...).
    """

    dashboard_port: int = Field(default=8888, alias="DASHBOARD_PORT")
    dashboard_host: str = Field(default="0.0.0.0", alias="DASHBOARD_HOST")

    # Database pool sizing (conservative for mini PC)
    db_pool_min: int = Field(default=2, alias="DASHBOARD_DB_POOL_MIN")
    db_pool_max: int = Field(default=10, alias="DASHBOARD_DB_POOL_MAX")

    # Refresh intervals (seconds)
    refresh_kpi: int = Field(default=10, alias="DASHBOARD_REFRESH_KPI")
    refresh_charts: int = Field(default=30, alias="DASHBOARD_REFRESH_CHARTS")
    refresh_macro: int = Field(default=300, alias="DASHBOARD_REFRESH_MACRO")

    # TensorBoard (internal = container-to-container, public = browser iframe)
    tensorboard_url: str = Field(default="http://localhost:6006", alias="DASHBOARD_TENSORBOARD_URL")
    tensorboard_public_url: str = Field(default="http://localhost:6006", alias="DASHBOARD_TENSORBOARD_PUBLIC_URL")

    # Prometheus endpoints (direct scrape)
    prometheus_data_ingestion: str = Field(default="http://localhost:9090/metrics", alias="DASHBOARD_PROMETHEUS_DI")
    prometheus_algo_engine: str = Field(default="http://localhost:9093/metrics", alias="DASHBOARD_PROMETHEUS_BRAIN")
    prometheus_mt5_bridge: str = Field(default="http://localhost:9094/metrics", alias="DASHBOARD_PROMETHEUS_MT5")

    # Frontend static files
    frontend_dist_dir: str = Field(default="frontend/dist", alias="DASHBOARD_FRONTEND_DIR")

    model_config = {"env_prefix": "", "case_sensitive": False, "populate_by_name": True}


settings = DashboardSettings()
