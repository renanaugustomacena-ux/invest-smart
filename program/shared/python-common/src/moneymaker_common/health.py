# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Protocollo di controllo salute per i servizi MONEYMAKER.

Come il "dottore di bordo" di una nave: controlla periodicamente
che tutto funzioni — dal motore (processo) ai compartimenti (dipendenze).

Ogni servizio implementa tre livelli di controllo:
- /healthz (liveness):  Il processo è in esecuzione? — "il cuore batte?"
- /readyz  (readiness): Il servizio può processare richieste? — "è pronto a lavorare?"
- /health  (deep):      Tutte le dipendenze sono accessibili? — "tutti i sistemi sono operativi?"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Risultato di un controllo di salute — il "referto medico"."""

    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    uptime_seconds: float = 0.0


class HealthChecker:
    """Gestisce i controlli di salute per un servizio MONEYMAKER — il "dottore di bordo"."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self._start_time = time.monotonic()
        self._ready = False
        self._checks: dict[str, Callable[[], object]] = {}

    def set_ready(self) -> None:
        self._ready = True

    def set_not_ready(self) -> None:
        self._ready = False

    def register_check(self, name: str, check_fn: Callable[[], object]) -> None:
        """Registra una funzione di controllo di una dipendenza.

        La funzione deve sollevare un'eccezione se il controllo fallisce.
        """
        self._checks[name] = check_fn

    @property
    def uptime(self) -> float:
        return time.monotonic() - self._start_time

    def liveness(self) -> HealthCheckResult:
        """Controllo di vitalità — il processo è in esecuzione? "Il cuore batte?"."""
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="vivo",
            uptime_seconds=self.uptime,
        )

    def readiness(self) -> HealthCheckResult:
        """Controllo di prontezza — il servizio può processare richieste?"""
        if self._ready:
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="pronto",
                uptime_seconds=self.uptime,
            )
        return HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="non pronto",
            uptime_seconds=self.uptime,
        )

    def deep_check(self) -> HealthCheckResult:
        """Controllo approfondito — tutte le dipendenze sono accessibili?"""
        details: dict[str, Any] = {}
        overall = HealthStatus.HEALTHY

        for name, check_fn in self._checks.items():
            try:
                check_fn()
                details[name] = "ok"
            except Exception as e:
                details[name] = f"errore: {e}"
                overall = HealthStatus.UNHEALTHY

        return HealthCheckResult(
            status=overall,
            message=(
                "tutti i controlli superati"
                if overall == HealthStatus.HEALTHY
                else "alcuni controlli falliti"
            ),
            details=details,
            uptime_seconds=self.uptime,
        )
