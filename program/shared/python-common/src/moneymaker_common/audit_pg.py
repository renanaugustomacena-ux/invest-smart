# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Implementazione audit trail con backend PostgreSQL.

Come un archivio notarile digitale con database: persiste le voci
di audit nella tabella `audit_log` definita in 001_init.sql.
Usa asyncpg per accesso asincrono al database. Se la connessione
al database non è disponibile, non fa crashare il servizio — registra
il fallimento ma continua a lavorare (come un notaio che prende
appunti temporanei quando l'archivio è chiuso).

Utilizzo:
    pool = await asyncpg.create_pool(dsn="postgresql://...")
    audit = PostgresAuditTrail("algo-engine", pool)
    entry = await audit.log_async("signal_generated", details={...})
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from prometheus_client import Counter

from moneymaker_common.audit import AuditEntry, AuditTrail

logger = logging.getLogger(__name__)

AUDIT_BUFFER_DROPS = Counter(
    "moneymaker_audit_buffer_drops_total",
    "Number of audit entries dropped due to buffer overflow",
    labelnames=["service"],
)


class PostgresAuditTrail(AuditTrail):
    """Sotto-classe AuditTrail che persiste le voci su PostgreSQL — l'"archivio notarile".

    Il metodo sincrono `_persist()` memorizza le voci in un buffer.
    Il metodo asincrono `flush()` scrive le voci bufferizzate nel database.
    In alternativa, usa `log_async()` per persistenza asincrona immediata.
    """

    _INSERT_SQL = """
        INSERT INTO audit_log (created_at, service, action, entity_type, entity_id, details, prev_hash, hash)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
    """

    def __init__(self, service_name: str, pool: Any = None, max_buffer_size: int = 10_000) -> None:
        """Inizializza l'audit trail PostgreSQL.

        Args:
            service_name: Nome del servizio che produce le voci di audit.
            pool: Un pool di connessioni asyncpg. Se None, le voci vengono
                  solo bufferizzate e devono essere svuotate (flush) quando
                  il pool diventa disponibile.
            max_buffer_size: Limite massimo di voci bufferizzate. Se superato,
                  le voci più vecchie vengono scartate per evitare overflow.
        """
        super().__init__(service_name)
        self._pool = pool
        self._buffer: list[AuditEntry] = []
        self._max_buffer_size = max_buffer_size

    def set_pool(self, pool: Any) -> None:
        """Imposta o aggiorna il pool di connessioni al database."""
        self._pool = pool

    async def connect(self, dsn: str, **pool_kwargs: Any) -> None:
        """Crea un pool asyncpg e lo collega all'audit trail.

        Metodo di convenienza per inizializzazione semplificata.
        Se asyncpg non è disponibile o la connessione fallisce,
        logga un warning e continua senza persistenza DB.

        Args:
            dsn: Stringa di connessione PostgreSQL.
            **pool_kwargs: Argomenti aggiuntivi per asyncpg.create_pool().
        """
        try:
            import asyncpg

            pool_kwargs.setdefault("min_size", 1)
            pool_kwargs.setdefault("max_size", 3)
            pool = await asyncpg.create_pool(dsn, **pool_kwargs)
            self._pool = pool
            logger.info("Audit trail: pool PostgreSQL connesso")
        except ImportError:
            logger.warning("Audit trail: asyncpg non disponibile, log solo in memoria")
        except Exception:
            logger.exception("Audit trail: connessione PostgreSQL fallita, log solo in memoria")

    def _persist(self, entry: AuditEntry) -> None:
        """Bufferizza la voce per persistenza asincrona.

        Chiamato sincronamente dal metodo `log()` della classe base.
        Le voci restano in memoria fino a quando `flush()` viene chiamato.
        Se il buffer è pieno, la voce più vecchia viene scartata.
        """
        if len(self._buffer) >= self._max_buffer_size:
            self._buffer.pop(0)
            AUDIT_BUFFER_DROPS.labels(service=self.service_name).inc()
            logger.warning("Buffer audit pieno, voce più vecchia scartata")
        self._buffer.append(entry)

    async def log_async(
        self,
        action: str,
        details: dict[str, Any] | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> AuditEntry:
        """Crea una voce di audit e la persiste immediatamente su PostgreSQL.

        Percorso asincrono preferito. Se il database non è disponibile,
        la voce resta nel buffer — il notaio prende appunti temporanei.

        Args:
            action: L'azione da registrare.
            details: Dizionario opzionale di dettagli.
            entity_type: Tipo di entità opzionale (es. "signal", "trade").
            entity_id: Identificatore dell'entità opzionale.

        Returns:
            La voce AuditEntry creata.
        """
        entry = self.log(action, details, entity_type, entity_id)

        if self._pool is not None:
            try:
                await self._write_entry(entry)
                # Rimuovi dal buffer perché è stata scritta con successo
                if entry in self._buffer:
                    self._buffer.remove(entry)
            except Exception:
                logger.exception("Persistenza voce audit fallita, bufferizzata per retry")

        return entry

    async def flush(self) -> int:
        """Scrive tutte le voci bufferizzate su PostgreSQL.

        Returns:
            Numero di voci scritte con successo.
        """
        if not self._buffer or self._pool is None:
            return 0

        written = 0
        remaining: list[AuditEntry] = []

        for entry in self._buffer:
            try:
                await self._write_entry(entry)
                written += 1
            except Exception:
                logger.exception("Flush voce audit fallito")
                remaining.append(entry)

        self._buffer = remaining
        return written

    async def _write_entry(self, entry: AuditEntry) -> None:
        """Scrive una singola voce di audit su PostgreSQL."""
        details_json = json.dumps(entry.details, sort_keys=True, default=str)
        async with self._pool.acquire() as conn:
            await conn.execute(
                self._INSERT_SQL,
                entry.timestamp,
                entry.service,
                entry.action,
                entry.entity_type,
                entry.entity_id,
                details_json,
                entry.prev_hash,
                entry.hash,
            )

    @property
    def buffer_size(self) -> int:
        """Numero di voci in attesa di essere svuotate (flush)."""
        return len(self._buffer)

    def start_periodic_flush(self, interval_sec: float = 30.0) -> None:
        """Avvia un task asincrono che svuota il buffer periodicamente.

        Args:
            interval_sec: Intervallo tra flush consecutivi (default 30s).
        """
        if getattr(self, "_flush_task", None) is not None:
            return
        self._flush_task: asyncio.Task[None] | None = asyncio.ensure_future(
            self._periodic_flush_loop(interval_sec)
        )

    async def _periodic_flush_loop(self, interval_sec: float) -> None:
        """Loop interno che esegue flush periodici."""
        while True:
            await asyncio.sleep(interval_sec)
            try:
                flushed = await self.flush()
                if flushed:
                    logger.debug("Audit periodic flush: %d entries written", flushed)
            except Exception:
                logger.exception("Audit periodic flush failed")

    async def close(self) -> None:
        """Ferma il flush periodico ed esegue un flush finale."""
        task = getattr(self, "_flush_task", None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self.flush()
