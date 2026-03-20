# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Canale Telegram — il "messaggero" degli alert via Telegram Bot.

Invia notifiche formattate in HTML al chat ID configurato usando
l'API Telegram Bot (httpx per async HTTP).

Utilizzo:
    channel = TelegramChannel(
        bot_token="123456:ABC-DEF",
        chat_id="-100123456789",
    )
    await channel.send(AlertLevel.CRITICAL, "Titolo", "Corpo del messaggio")
"""

from __future__ import annotations

import os

from algo_engine.alerting.dispatcher import AlertChannel, AlertLevel
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramChannel(AlertChannel):
    """Invia alert via Telegram Bot API."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ) -> None:
        self._bot_token = bot_token or os.environ.get("MONEYMAKER_TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.environ.get("MONEYMAKER_TELEGRAM_CHAT_ID", "")
        self._client = None

        if not self._bot_token:
            logger.warning("Telegram bot_token non configurato (env MONEYMAKER_TELEGRAM_BOT_TOKEN)")
        if not self._chat_id:
            logger.warning("Telegram chat_id non configurato (env MONEYMAKER_TELEGRAM_CHAT_ID)")

    async def _get_client(self):
        """Lazy init del client HTTP."""
        if self._client is None:
            try:
                import httpx

                self._client = httpx.AsyncClient(timeout=10.0)
            except ImportError:
                logger.warning("httpx non disponibile, Telegram alerts disabilitati")
                return None
        return self._client

    async def send(self, level: AlertLevel, title: str, body: str) -> bool:
        """Invia messaggio formattato HTML via Telegram."""
        client = await self._get_client()
        if client is None:
            return False

        text = f"<b>{title}</b>\n\n{body}"

        url = TELEGRAM_API_URL.format(token=self._bot_token)
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return True
            logger.warning(
                "Telegram API errore",
                status=response.status_code,
                body=response.text[:200],
            )
            return False
        except Exception as exc:
            logger.warning("Invio Telegram fallito", error=str(exc))
            return False
