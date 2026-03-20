# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Scheduler per il fetch periodico dei dati macro.

Usa APScheduler per gestire job periodici con diverse frequenze:
- VIX: ogni 1 minuto (durante market hours)
- Yield Curve: ogni ora
- DXY: ogni 15 minuti
- COT: ogni 24 ore (dati settimanali)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class MacroDataScheduler:
    """Scheduler per fetch periodico dati macro."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._running = False
        self._tasks: dict[str, asyncio.Task] = {}

    def add_job(
        self,
        job_id: str,
        func: Callable[[], Coroutine[Any, Any, None]],
        interval_seconds: int,
        run_immediately: bool = True,
    ) -> None:
        """Registra un job periodico.

        Args:
            job_id: Identificatore univoco del job
            func: Funzione asincrona da eseguire
            interval_seconds: Intervallo tra esecuzioni
            run_immediately: Se eseguire subito all'avvio
        """
        self._jobs[job_id] = {
            "func": func,
            "interval": interval_seconds,
            "run_immediately": run_immediately,
            "last_run": None,
            "run_count": 0,
            "error_count": 0,
        }
        logger.info(
            "Job registered",
            job_id=job_id,
            interval_seconds=interval_seconds,
        )

    def remove_job(self, job_id: str) -> bool:
        """Rimuove un job.

        Args:
            job_id: ID del job da rimuovere

        Returns:
            True se rimosso, False se non trovato
        """
        if job_id in self._jobs:
            del self._jobs[job_id]
            if job_id in self._tasks:
                self._tasks[job_id].cancel()
                del self._tasks[job_id]
            logger.info("Job removed", job_id=job_id)
            return True
        return False

    async def _run_job_loop(self, job_id: str) -> None:
        """Loop di esecuzione per un singolo job."""
        job = self._jobs.get(job_id)
        if not job:
            return

        func = job["func"]
        interval = job["interval"]

        # Run immediately if configured
        if job["run_immediately"]:
            await self._execute_job(job_id, func)

        while self._running and job_id in self._jobs:
            try:
                await asyncio.sleep(interval)

                if not self._running or job_id not in self._jobs:
                    break

                await self._execute_job(job_id, func)

            except asyncio.CancelledError:
                logger.debug("Job cancelled", job_id=job_id)
                break
            except Exception as e:
                logger.error("Job loop error", job_id=job_id, error=str(e))
                # Continue running despite errors
                await asyncio.sleep(interval)

    async def _execute_job(
        self,
        job_id: str,
        func: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        """Esegue un job con error handling."""
        job = self._jobs.get(job_id)
        if not job:
            return

        try:
            await func()
            job["run_count"] += 1
            job["last_run"] = datetime.now(timezone.utc)
            logger.debug(
                "Job executed",
                job_id=job_id,
                run_count=job["run_count"],
            )
        except Exception as e:
            job["error_count"] += 1
            logger.error(
                "Job execution failed",
                job_id=job_id,
                error=str(e),
                error_count=job["error_count"],
            )

    async def start(self) -> None:
        """Avvia lo scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        logger.info("Scheduler starting", job_count=len(self._jobs))

        # Start a task for each job
        for job_id in self._jobs:
            task = asyncio.create_task(self._run_job_loop(job_id))
            self._tasks[job_id] = task

    async def stop(self) -> None:
        """Ferma lo scheduler."""
        if not self._running:
            return

        self._running = False
        logger.info("Scheduler stopping")

        # Cancel all tasks
        for job_id, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        logger.info("Scheduler stopped")

    def get_job_stats(self) -> dict[str, dict[str, Any]]:
        """Restituisce statistiche per tutti i job."""
        stats = {}
        for job_id, job in self._jobs.items():
            stats[job_id] = {
                "interval_seconds": job["interval"],
                "run_count": job["run_count"],
                "error_count": job["error_count"],
                "last_run": job["last_run"].isoformat() if job["last_run"] else None,
                "running": job_id in self._tasks and not self._tasks[job_id].done(),
            }
        return stats

    @property
    def is_running(self) -> bool:
        """Restituisce True se lo scheduler è in esecuzione."""
        return self._running
