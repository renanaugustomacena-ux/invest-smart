# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Configurazione del servizio External Data.

Gestisce API keys e parametri per i vari provider di dati macro.
"""

from __future__ import annotations

from moneymaker_common.config import MoneyMakerBaseSettings


class ExternalDataSettings(MoneyMakerBaseSettings):
    """Configurazione per il servizio di dati esterni."""

    # Identità servizio
    external_data_service_name: str = "external-data"
    external_data_metrics_port: int = 9095

    # FRED API (Federal Reserve Economic Data)
    # Free, no API key required for basic access
    # But API key increases rate limits
    fred_api_key: str = ""
    fred_base_url: str = "https://api.stlouisfed.org/fred"
    fred_rate_limit_per_min: int = 120  # Free tier limit

    # CBOE (Chicago Board Options Exchange)
    # VIX data is publicly available
    cboe_vix_url: str = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/_VIX.json"

    # CFTC (Commodity Futures Trading Commission)
    # COT reports are public domain
    cftc_cot_url: str = "https://www.cftc.gov/dea/newcot/c_disagg.txt"

    # Polygon.io (for DXY)
    # Requires API key (free tier available)
    polygon_api_key: str = ""
    polygon_base_url: str = "https://api.polygon.io"

    # Yahoo Finance (backup for VIX)
    yahoo_vix_symbol: str = "^VIX"

    # Redis per caching (uses parent's redis_url property from MONEYMAKER_REDIS_* env vars)
    redis_cache_ttl_seconds: int = 300

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "moneymaker"
    db_password: str = ""
    db_name: str = "moneymaker"

    # Scheduling
    vix_fetch_interval_minutes: int = 1
    yield_fetch_interval_minutes: int = 60
    cot_fetch_interval_hours: int = 24  # Weekly data, check daily
    dxy_fetch_interval_minutes: int = 15

    # Retry settings
    retry_attempts: int = 3
    retry_delay_seconds: float = 2.0
    request_timeout_seconds: int = 30

    model_config = {"env_prefix": "", "case_sensitive": False}
