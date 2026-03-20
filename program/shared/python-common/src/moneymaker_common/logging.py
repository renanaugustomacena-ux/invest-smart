# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Logging strutturato JSON per tutti i servizi MONEYMAKER.

Come il "diario di bordo" della nave: ogni evento viene registrato
con timestamp preciso, livello di gravità e dati strutturati in
formato JSON. Permette di cercare e filtrare i log in modo efficiente.

Utilizzo:
    from moneymaker_common.logging import setup_logging, get_logger

    setup_logging("algo_engine")
    logger = get_logger(__name__)
    logger.info("Segnale generato", symbol="XAUUSD", direction="BUY", confidence="0.78")
"""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(service_name: str, level: str = "INFO") -> None:
    """Configura il logging strutturato per un servizio MONEYMAKER."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    # Lega il nome del servizio a tutte le voci di log successive
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Ottiene un logger legato al nome del modulo specificato."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(component=name)
    return logger
