# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Configurazione specifica del MT5 Bridge — i "parametri dello sportello bancario"."""

from __future__ import annotations

from moneymaker_common.config import MoneyMakerBaseSettings


class MT5BridgeSettings(MoneyMakerBaseSettings):
    """Impostazioni per il servizio MetaTrader 5 Bridge — lo "sportello"."""

    # Server gRPC — la "porta d'ingresso" dello sportello
    moneymaker_mt5_bridge_grpc_port: int = 50055
    moneymaker_mt5_bridge_metrics_port: int = 9094

    # Connessione MT5 — le "credenziali bancarie"
    mt5_account: str = ""
    mt5_password: str = ""
    mt5_server: str = ""
    mt5_timeout_ms: int = 10000

    # Limiti di trading (fail-safe) — i "limiti di prelievo giornalieri"
    max_position_count: int = 5
    max_lot_size: str = "1.0"
    max_daily_loss_pct: str = "2.0"
    max_drawdown_pct: str = "10.0"

    # Gestione segnali — il "filtro anti-duplicato"
    signal_dedup_window_sec: int = 60
    signal_max_age_sec: int = 30

    # Filtro spread — protezione contro spread eccessivi
    max_spread_points: int = 30

    # Gestione posizioni — il "guardiano delle posizioni aperte"
    trailing_stop_enabled: bool = True
    trailing_stop_pips: str = "50.0"
    trailing_activation_pips: str = "30.0"

    # Rate limiting — il "vigile urbano" che limita le richieste
    # Protegge da DoS e abusi di trading ad alta frequenza
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 10  # Max trade/min (conservativo)
    rate_limit_burst_size: int = 5  # Capacità extra per burst
