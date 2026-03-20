# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Rate Limiter per segnali — il "semaforo intelligente" anti-overtrading.

Previene l'invio eccessivo di segnali usando una finestra scorrevole.
Il parametro ``brain_max_signals_per_hour`` esiste già nella config
ma non era enforciato: questo modulo lo implementa.

Utilizzo:
    limiter = SignalRateLimiter(max_per_hour=10)
    if limiter.allow():
        limiter.record()
        # processa il segnale
"""

from __future__ import annotations

import time
from collections import deque


class SignalRateLimiter:
    """Limita il numero di segnali inviati per ora con finestra scorrevole."""

    def __init__(self, max_per_hour: int = 10) -> None:
        self._max = max_per_hour
        self._timestamps: deque[float] = deque()
        self._window_sec: float = 3600.0

    def allow(self) -> bool:
        """Restituisce True se un nuovo segnale è permesso."""
        self._cleanup()
        return len(self._timestamps) < self._max

    def record(self) -> None:
        """Registra l'invio di un segnale."""
        self._timestamps.append(time.monotonic())

    @property
    def current_count(self) -> int:
        """Numero di segnali nell'ultima ora."""
        self._cleanup()
        return len(self._timestamps)

    @property
    def remaining(self) -> int:
        """Segnali rimanenti prima del limite."""
        return max(0, self._max - self.current_count)

    def _cleanup(self) -> None:
        """Rimuove timestamp più vecchi della finestra."""
        cutoff = time.monotonic() - self._window_sec
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
