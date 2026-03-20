# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Alert Dispatcher — il "centralino" degli allarmi di MONEYMAKER.

Instrada gli alert verso i canali configurati (Telegram, Discord, etc.)
con rate limiting per evitare spam. Come un centralino che smista le
chiamate urgenti ai destinatari giusti.

Utilizzo:
    dispatcher = AlertDispatcher()
    dispatcher.add_channel(TelegramChannel(token, chat_id))
    await dispatcher.send(AlertLevel.CRITICAL, "Kill Switch", "Drawdown critico")
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class AlertLevel(str, Enum):
    """Livelli di severità degli alert."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


LEVEL_EMOJI: dict[AlertLevel, str] = {
    AlertLevel.INFO: "ℹ️",
    AlertLevel.WARNING: "⚠️",
    AlertLevel.CRITICAL: "🚨",
}


class AlertChannel:
    """Interfaccia base per i canali di notifica."""

    async def send(self, level: AlertLevel, title: str, body: str) -> bool:
        """Invia un alert. Restituisce True se inviato con successo."""
        raise NotImplementedError


class AlertDispatcher:
    """Instrada alert verso i canali configurati con rate limiting."""

    def __init__(
        self,
        min_interval_sec: float = 30.0,
        critical_min_interval_sec: float = 5.0,
    ) -> None:
        self._channels: list[AlertChannel] = []
        self._min_interval = min_interval_sec
        self._critical_min_interval = critical_min_interval_sec
        self._last_sent: dict[str, float] = {}

    def add_channel(self, channel: AlertChannel) -> None:
        """Registra un canale di notifica."""
        self._channels.append(channel)

    async def send(
        self,
        level: AlertLevel,
        title: str,
        body: str,
        *,
        context: str = "",
    ) -> None:
        """Invia alert a tutti i canali con rate limiting.

        Args:
            level: Severità dell'alert.
            title: Titolo dell'alert.
            body: Corpo del messaggio.
            context: Contesto opzionale (es. symbol) per namespace nel
                     rate-limit — evita collisioni tra alert con stesso
                     titolo ma contesto diverso.
        """
        if not self._channels:
            return

        # Rate limiting per key (level + title + context)
        key = f"{level.value}:{title}:{context}" if context else f"{level.value}:{title}"
        now = time.monotonic()
        min_interval = (
            self._critical_min_interval if level == AlertLevel.CRITICAL else self._min_interval
        )

        last = self._last_sent.get(key, 0.0)
        if now - last < min_interval:
            return

        self._last_sent[key] = now

        # Cleanup vecchi entries
        cutoff = now - 3600
        self._last_sent = {k: v for k, v in self._last_sent.items() if v > cutoff}

        emoji = LEVEL_EMOJI.get(level, "")
        formatted_title = f"{emoji} [{level.value.upper()}] {title}"

        tasks = [channel.send(level, formatted_title, body) for channel in self._channels]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "Alert channel fallito",
                    channel=type(self._channels[i]).__name__,
                    error=str(result),
                )
