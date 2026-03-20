# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Kill Switch Globale — il "pulsante rosso d'emergenza" di MONEYMAKER.

Ferma immediatamente tutto il trading quando attivato. Usa Redis come
stato condiviso cosicché tutti i servizi vedano la stessa cosa.

Attivazione automatica quando:
- La perdita giornaliera raggiunge il limite configurato (>= 1x)
- Il drawdown supera il limite configurato

Utilizzo:
    kill_switch = KillSwitch(host="redis", port=6379, password="secret")
    await kill_switch.connect()
    await kill_switch.check_or_raise()  # Lancia eccezione se attivo
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from moneymaker_common.exceptions import RiskLimitExceededError
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

KILL_SWITCH_KEY = "moneymaker:kill_switch"
KILL_SWITCH_AUDIT_KEY = "moneymaker:kill_switch:audit_log"


@dataclass
class HierarchicalAction:
    """Result of hierarchical risk check."""

    level: int  # 0=none, 1=strategy, 2=portfolio, 3=global
    action: str  # "NONE", "PAUSE_STRATEGY", "REDUCE_SIZING", "FLATTEN_ALL"
    sizing_multiplier: Decimal  # 1.0=normal, 0.5=reduced, 0=stopped
    reason: str
    pause_strategy: str | None  # Strategy name to pause (level 1 only)


@dataclass
class KillSwitchAuditEntry:
    """Singola voce nel registro di audit del kill switch."""

    timestamp: float
    action: str  # "ACTIVATED" | "DEACTIVATED" | "AUTO_CHECK_TRIGGERED"
    reason: str
    actor: str = "system"  # "system" | "manual" | "auto_check"
    daily_loss_pct: str = ""
    drawdown_pct: str = ""


class KillSwitch:
    """Interruttore d'emergenza globale condiviso via Redis."""

    _MAX_AUDIT_ENTRIES = 200  # Max audit entries kept in Redis list

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: str = "",
        db: int = 0,
        cache_ttl: float = 1.0,
    ) -> None:
        self._redis_host = host
        self._redis_port = port
        self._redis_password = password
        self._redis_db = db
        self._redis: Any = None
        self._cached_active: bool = True  # Fail-CLOSED: blocca trading fino a conferma Redis
        self._cached_reason: str = ""
        self._cache_ts: float = 0.0
        self._cache_ttl: float = cache_ttl
        self._audit_log: list[KillSwitchAuditEntry] = []

    async def connect(self) -> None:
        """Connette a Redis. Fallisce silenziosamente se non disponibile."""
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.Redis(
                host=self._redis_host,
                port=self._redis_port,
                password=self._redis_password or None,
                db=self._redis_db,
                decode_responses=True,
            )
            await self._redis.ping()
            self._cached_active = False  # Redis raggiungibile, sicuro per il trading
            self._cache_ts = time.monotonic()
            logger.info(
                "Kill switch connesso a Redis",
                host=self._redis_host,
                port=self._redis_port,
            )
        except Exception as exc:
            logger.warning(
                "Kill switch: Redis non disponibile, operazione locale",
                error=str(exc),
            )
            self._redis = None

    async def activate(self, reason: str, actor: str = "system") -> None:
        """Attiva il kill switch — semaforo rosso per tutti."""
        self._cached_active = True
        self._cached_reason = reason
        self._cache_ts = time.monotonic()

        payload = json.dumps(
            {
                "active": True,
                "reason": reason,
                "activated_at": time.time(),
            }
        )

        if self._redis is not None:
            try:
                await self._redis.set(KILL_SWITCH_KEY, payload)
                await self._redis.publish(
                    "moneymaker:alerts",
                    json.dumps(
                        {
                            "level": "CRITICAL",
                            "title": "KILL SWITCH ATTIVATO",
                            "body": reason,
                        }
                    ),
                )
            except Exception as exc:
                logger.error("Kill switch: impossibile scrivere su Redis", error=str(exc))

        await self._append_audit(
            KillSwitchAuditEntry(
                timestamp=time.time(),
                action="ACTIVATED",
                reason=reason,
                actor=actor,
            )
        )
        logger.critical("KILL SWITCH ATTIVATO", reason=reason, actor=actor)

    async def deactivate(self, actor: str = "system") -> None:
        """Disattiva il kill switch — semaforo verde."""
        self._cached_active = False
        self._cached_reason = ""
        self._cache_ts = time.monotonic()

        if self._redis is not None:
            try:
                await self._redis.delete(KILL_SWITCH_KEY)
            except (ConnectionError, TimeoutError, OSError) as exc:
                logger.warning("Kill switch deactivate: Redis error", error=str(exc))

        await self._append_audit(
            KillSwitchAuditEntry(
                timestamp=time.time(),
                action="DEACTIVATED",
                reason="Manual deactivation",
                actor=actor,
            )
        )
        logger.info("Kill switch disattivato", actor=actor)

    async def is_active(self) -> tuple[bool, str]:
        """Controlla se il kill switch è attivo. Cache locale per 1 secondo."""
        now = time.monotonic()
        if now - self._cache_ts < self._cache_ttl:
            return self._cached_active, self._cached_reason

        if self._redis is not None:
            try:
                raw = await self._redis.get(KILL_SWITCH_KEY)
                if raw:
                    data = json.loads(raw)
                    self._cached_active = data.get("active", False)
                    self._cached_reason = data.get("reason", "")
                else:
                    self._cached_active = False
                    self._cached_reason = ""
            except (ConnectionError, TimeoutError, OSError) as exc:
                logger.warning(
                    "Kill switch check: Redis error, keeping cached state",
                    error=str(exc),
                )
            except json.JSONDecodeError as exc:
                logger.error("Kill switch: corrupt Redis data", error=str(exc))
                self._cached_active = True  # Fail-closed on corrupt data
                self._cached_reason = "Corrupt kill switch data in Redis"

        self._cache_ts = now
        return self._cached_active, self._cached_reason

    async def check_or_raise(self) -> None:
        """Lancia RiskLimitExceededError se il kill switch è attivo."""
        active, reason = await self.is_active()
        if active:
            raise RiskLimitExceededError(f"Kill switch attivo: {reason}")

    async def auto_check(
        self,
        daily_loss_pct: Decimal,
        max_daily_loss_pct: Decimal,
        drawdown_pct: Decimal,
        max_drawdown_pct: Decimal,
    ) -> None:
        """Attiva automaticamente se i limiti di rischio sono gravemente superati."""
        if daily_loss_pct >= max_daily_loss_pct:
            reason = (
                f"Perdita giornaliera limite raggiunto: {daily_loss_pct}% >= {max_daily_loss_pct}%"
            )
            await self._append_audit(
                KillSwitchAuditEntry(
                    timestamp=time.time(),
                    action="AUTO_CHECK_TRIGGERED",
                    reason=reason,
                    actor="auto_check",
                    daily_loss_pct=str(daily_loss_pct),
                    drawdown_pct=str(drawdown_pct),
                )
            )
            await self.activate(reason, actor="auto_check")
        elif drawdown_pct >= max_drawdown_pct:
            reason = f"Drawdown massimo superato: {drawdown_pct}% >= {max_drawdown_pct}%"
            await self._append_audit(
                KillSwitchAuditEntry(
                    timestamp=time.time(),
                    action="AUTO_CHECK_TRIGGERED",
                    reason=reason,
                    actor="auto_check",
                    daily_loss_pct=str(daily_loss_pct),
                    drawdown_pct=str(drawdown_pct),
                )
            )
            await self.activate(reason, actor="auto_check")

    # ------------------------------------------------------------------
    # Hierarchical kill switch levels (Phase 4)
    # ------------------------------------------------------------------

    async def hierarchical_check(
        self,
        drawdown_pct: Decimal,
        strategy_name: str | None = None,
        strategy_dd_pct: Decimal | None = None,
    ) -> HierarchicalAction:
        """Hierarchical risk check with three levels of escalation.

        Level 1 (Strategy): Strategy DD > 5% → pause that strategy
        Level 2 (Portfolio): Portfolio DD > 3% → reduce all sizing by 50%
        Level 3 (Global): Portfolio DD > 5% → flatten all, activate kill switch

        Returns:
            HierarchicalAction indicating what action to take.
        """
        from decimal import Decimal as D

        # Level 3: Global kill — flatten everything
        if drawdown_pct >= D("5"):
            reason = f"Level 3 kill: portfolio DD {drawdown_pct}% >= 5%"
            await self.activate(reason, actor="hierarchical_check")
            return HierarchicalAction(
                level=3,
                action="FLATTEN_ALL",
                sizing_multiplier=D("0"),
                reason=reason,
                pause_strategy=None,
            )

        # Level 2: Portfolio reduction — cut sizing by 50%
        if drawdown_pct >= D("3"):
            reason = f"Level 2 warning: portfolio DD {drawdown_pct}% >= 3%"
            logger.warning(reason)
            await self._append_audit(
                KillSwitchAuditEntry(
                    timestamp=time.time(),
                    action="LEVEL2_REDUCTION",
                    reason=reason,
                    actor="hierarchical_check",
                    drawdown_pct=str(drawdown_pct),
                )
            )
            return HierarchicalAction(
                level=2,
                action="REDUCE_SIZING",
                sizing_multiplier=D("0.50"),
                reason=reason,
                pause_strategy=None,
            )

        # Level 1: Strategy-level pause
        if strategy_name is not None and strategy_dd_pct is not None and strategy_dd_pct >= D("5"):
            reason = f"Level 1 pause: {strategy_name} DD {strategy_dd_pct}% >= 5%"
            logger.warning(reason)
            await self._append_audit(
                KillSwitchAuditEntry(
                    timestamp=time.time(),
                    action="LEVEL1_STRATEGY_PAUSE",
                    reason=reason,
                    actor="hierarchical_check",
                )
            )
            return HierarchicalAction(
                level=1,
                action="PAUSE_STRATEGY",
                sizing_multiplier=D("1"),
                reason=reason,
                pause_strategy=strategy_name,
            )

        # No action needed
        return HierarchicalAction(
            level=0,
            action="NONE",
            sizing_multiplier=D("1"),
            reason="All risk levels within limits",
            pause_strategy=None,
        )

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    async def _append_audit(self, entry: KillSwitchAuditEntry) -> None:
        """Persiste una voce di audit in Redis e nel buffer locale."""
        self._audit_log.append(entry)
        # Trim local buffer
        if len(self._audit_log) > self._MAX_AUDIT_ENTRIES:
            self._audit_log = self._audit_log[-self._MAX_AUDIT_ENTRIES :]

        if self._redis is not None:
            try:
                payload = json.dumps(asdict(entry))
                await self._redis.rpush(KILL_SWITCH_AUDIT_KEY, payload)
                await self._redis.ltrim(
                    KILL_SWITCH_AUDIT_KEY,
                    -self._MAX_AUDIT_ENTRIES,
                    -1,
                )
            except Exception as exc:
                logger.warning("Kill switch audit write failed", error=str(exc))

        logger.info(
            "kill_switch_audit",
            action=entry.action,
            reason=entry.reason,
            actor=entry.actor,
        )

    async def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        """Restituisce le ultime voci di audit dal registro persistente."""
        if self._redis is not None:
            try:
                raw_entries = await self._redis.lrange(
                    KILL_SWITCH_AUDIT_KEY,
                    -limit,
                    -1,
                )
                return [json.loads(e) for e in raw_entries]
            except Exception as exc:
                logger.warning("Kill switch audit read failed", error=str(exc))

        # Fallback to local buffer
        return [asdict(e) for e in self._audit_log[-limit:]]
