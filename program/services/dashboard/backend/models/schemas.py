"""Pydantic response schemas for the dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


# --- Overview ---

class ServiceHealth(BaseModel):
    name: str
    status: str  # "connected" | "disconnected"
    latency_ms: float | None = None
    error: str | None = None


class OverviewKPIs(BaseModel):
    signals_today: int = 0
    signals_per_hour: float = 0.0
    daily_pnl: str = "0.00"
    daily_pnl_pct: str = "0.00"
    open_positions: int = 0
    drawdown_pct: str = "0.00"
    kill_switch_active: bool = False
    win_rate: str = "0.00"
    total_trades_today: int = 0


class OverviewResponse(BaseModel):
    kpis: OverviewKPIs
    services: list[ServiceHealth]
    recent_signals: list[dict[str, Any]]
    timestamp: datetime


# --- Trading ---

class TradingSignal(BaseModel):
    signal_id: str
    created_at: datetime
    symbol: str
    direction: str
    confidence: str
    suggested_lots: str | None = None
    stop_loss: str | None = None
    take_profit: str | None = None
    model_version: str | None = None
    regime: str | None = None
    source_tier: str | None = None
    reasoning: str | None = None
    risk_reward: str | None = None


class TradeExecution(BaseModel):
    id: int
    signal_id: str | None = None
    executed_at: datetime
    symbol: str
    direction: str
    requested_price: str | None = None
    executed_price: str | None = None
    quantity: str | None = None
    status: str
    slippage_pips: str | None = None
    profit: str | None = None


class TradingResponse(BaseModel):
    signals: list[TradingSignal]
    executions: list[TradeExecution]
    positions: list[dict[str, Any]]
    total_signals: int
    total_executions: int


# --- Risk ---

class RiskMetrics(BaseModel):
    daily_loss_pct: str = "0.00"
    drawdown_pct: str = "0.00"
    kill_switch_active: bool = False
    kill_switch_reason: str | None = None
    open_positions: int = 0
    max_positions: int = 5
    symbols_exposed: list[str] = []
    maturity_state: str | None = None
    regime: str | None = None


# --- Market Data ---

class OHLCVBar(BaseModel):
    time: datetime
    open: str
    high: str
    low: str
    close: str
    volume: str


class MarketDataResponse(BaseModel):
    symbol: str
    timeframe: str
    bars: list[OHLCVBar]
    total_bars: int


# --- ML Models ---

class ModelInfo(BaseModel):
    id: int
    model_type: str
    model_version: str | None = None
    is_active: bool = False
    validation_accuracy: str | None = None
    created_at: datetime
    checkpoint_path: str | None = None


class MLResponse(BaseModel):
    models: list[ModelInfo]
    tensorboard_online: bool = False
    recent_predictions: list[dict[str, Any]] = []
    training_metrics: list[dict[str, Any]] = []


# --- Macro ---

class MacroSnapshot(BaseModel):
    vix_spot: str | None = None
    vix_regime: str | None = None
    vix_contango: bool | None = None
    yield_slope: str | None = None
    curve_inverted: bool | None = None
    real_rate_10y: str | None = None
    dxy_value: str | None = None
    dxy_trend: str | None = None
    recession_prob: str | None = None
    updated_at: datetime | None = None


# --- Strategy ---

class StrategyPerformance(BaseModel):
    strategy_name: str
    symbol: str | None = None
    total_signals: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: str = "0.00"
    avg_confidence: str = "0.00"
    win_rate: str = "0.00"


# --- Economic ---

class EconomicEvent(BaseModel):
    event_time: datetime
    event_name: str
    country: str | None = None
    currency: str | None = None
    impact: str | None = None
    previous: str | None = None
    forecast: str | None = None
    actual: str | None = None


# --- System ---

class SystemStatus(BaseModel):
    database: ServiceHealth
    redis: ServiceHealth
    tensorboard: ServiceHealth
    services: list[ServiceHealth]
    uptime_seconds: float | None = None
