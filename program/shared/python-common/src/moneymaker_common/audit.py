"""Interfaccia audit trail per i servizi MONEYMAKER.

Come un notaio digitale: ogni azione significativa viene registrata
con una catena di hash SHA-256 per garantire che nessuno possa
alterare il registro senza essere scoperto. Ogni nuova voce è
"sigillata" con l'hash della voce precedente.

Formula della catena hash:
    hash = SHA256(hash_precedente || servizio || azione || dettagli_json || tempo_iso)

La prima voce usa hash_precedente = 'GENESIS' — il "Big Bang" del registro.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEntry:
    """Una voce nel registro di audit — un "timbro" nel libro notarile."""

    service: str
    action: str
    entity_type: str | None
    entity_id: str | None
    details: dict[str, Any]
    timestamp: datetime
    prev_hash: str
    hash: str


def compute_audit_hash(
    prev_hash: str,
    service: str,
    action: str,
    details: dict[str, Any],
    timestamp: datetime,
) -> str:
    """Calcola l'hash SHA-256 per una voce di audit — il "sigillo notarile"."""
    time_iso = timestamp.isoformat()
    details_json = json.dumps(details, sort_keys=True, default=str)
    payload = f"{prev_hash}|{service}|{action}|{details_json}|{time_iso}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditTrail:
    """Interfaccia per scrivere voci di audit a prova di manomissione — il "notaio".

    Le implementazioni concrete scrivono su PostgreSQL (produzione)
    o su un file locale (sviluppo/test).
    """

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self._last_hash = "GENESIS"

    def log(
        self,
        action: str,
        details: dict[str, Any] | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> AuditEntry:
        """Crea una voce di audit e la aggiunge alla catena."""
        now = datetime.now(timezone.utc)
        details = details or {}

        entry_hash = compute_audit_hash(
            prev_hash=self._last_hash,
            service=self.service_name,
            action=action,
            details=details,
            timestamp=now,
        )

        entry = AuditEntry(
            service=self.service_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            timestamp=now,
            prev_hash=self._last_hash,
            hash=entry_hash,
        )

        self._last_hash = entry_hash
        self._persist(entry)
        return entry

    def _persist(self, entry: AuditEntry) -> None:
        """Persiste la voce di audit. Sovrascrivere nelle sotto-classi."""
        # Default: no-op. PostgresAuditTrail sovrascrive questo metodo.
        pass
