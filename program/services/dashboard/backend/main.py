"""MONEYMAKER Dashboard — FastAPI application entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.db.connection import close_pool, create_pool
from backend.redis_client.client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of database and Redis connections."""
    try:
        await create_pool()
    except Exception as e:
        print(f"[WARN] Database connection failed: {e} — dashboard will retry on first request")

    yield

    await close_pool()
    await close_redis()


app = FastAPI(
    title="MONEYMAKER Dashboard",
    version="0.1.0",
    description="Unified monitoring dashboard for MONEYMAKER V1 Trading Ecosystem",
    lifespan=lifespan,
)

_cors_origins = os.environ.get(
    "DASHBOARD_CORS_ORIGINS",
    "http://localhost:5173,http://localhost:8888",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# --- Register API routes ---
from backend.api.routes import (  # noqa: E402
    economic,
    macro,
    market_data,
    overview,
    risk,
    strategy,
    system,
    trading,
)
from backend.ws.streams import router as ws_router  # noqa: E402

app.include_router(overview.router)
app.include_router(trading.router)
app.include_router(risk.router)
app.include_router(market_data.router)
app.include_router(macro.router)
app.include_router(strategy.router)
app.include_router(economic.router)
app.include_router(system.router)
app.include_router(ws_router)


# --- Health check ---
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "moneymaker-dashboard"}


# --- Serve frontend static files ---
_dashboard_dir = Path(__file__).resolve().parent.parent
_frontend_dist = _dashboard_dir / settings.frontend_dist_dir

if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
