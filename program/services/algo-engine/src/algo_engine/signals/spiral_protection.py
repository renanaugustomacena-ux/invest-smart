"""Spiral Protection — riduce il sizing dopo loss consecutive.

Come un paracadute che si apre progressivamente: dopo ogni perdita
consecutiva, il sistema riduce la dimensione dei trade per limitare
i danni. Dopo troppe perdite di fila, ferma il trading per un cooldown.

Utilizzo:
    spiral = SpiralProtection(consecutive_loss_threshold=3)
    spiral.record_trade_result(is_win=False)
    multiplier = spiral.get_sizing_multiplier()  # 1.0, 0.5, 0.25, 0.0
"""

from __future__ import annotations

import asyncio
import json
import time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from algo_engine.kill_switch import KillSwitch

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

SPIRAL_REDIS_KEY = "moneymaker:spiral_protection"


class SpiralProtection:
    """Protezione a spirale contro serie di perdite consecutive.

    Riduce il sizing progressivamente e impone cooldown dopo N perdite.
    Supporta sia l'interfaccia originale (record_trade_result) sia
    la nuova interfaccia separata record_loss/record_win (T3_15).
    """

    def __init__(
        self,
        consecutive_loss_threshold: int = 3,
        max_consecutive_loss: int = 5,
        cooldown_minutes: int = 60,
        size_reduction_factor: Decimal = Decimal("0.5"),
        *,
        max_consecutive_losses: int | None = None,
        redis_client: Any = None,
    ) -> None:
        # max_consecutive_losses è l'alias semplificato che unifica soglia
        # e cooldown nello stesso valore (T3_15 interface).
        if max_consecutive_losses is not None:
            self._threshold = max_consecutive_losses
            self._max_losses = max_consecutive_losses
        else:
            self._threshold = consecutive_loss_threshold
            self._max_losses = max_consecutive_loss

        self._cooldown_seconds = cooldown_minutes * 60
        self._reduction_factor = size_reduction_factor
        self._redis = redis_client

        self._consecutive_losses: int = 0
        self._cooldown_start: float | None = None

    @property
    def consecutive_losses(self) -> int:
        """Numero corrente di perdite consecutive."""
        return self._consecutive_losses

    def record_loss(self) -> None:
        """Registra una perdita — incrementa contatore, avvia cooldown se soglia raggiunta."""
        self.record_trade_result(is_win=False)

    def record_win(self) -> None:
        """Registra una vittoria — reset contatore e cooldown."""
        self.record_trade_result(is_win=True)

    def record_trade_result(self, is_win: bool) -> None:
        """Registra l'esito di un trade."""
        if is_win:
            if self._consecutive_losses > 0:
                logger.info(
                    "Spiral reset: vittoria dopo serie negativa",
                    previous_streak=self._consecutive_losses,
                )
            self._consecutive_losses = 0
            self._cooldown_start = None
        else:
            self._consecutive_losses += 1
            logger.info(
                "Perdita consecutiva registrata",
                streak=self._consecutive_losses,
                threshold=self._threshold,
                max=self._max_losses,
            )
            if self._consecutive_losses >= self._max_losses:
                self._cooldown_start = time.monotonic()
                logger.warning(
                    "Spiral cooldown attivato",
                    losses=self._consecutive_losses,
                    cooldown_minutes=self._cooldown_seconds // 60,
                )
        self._schedule_persist()

    def get_sizing_multiplier(self) -> Decimal:
        """Restituisce il moltiplicatore di sizing corrente.

        Returns:
            Decimal: 1.0 (nessuna riduzione), 0.5, 0.25, o 0.0 (cooldown).
        """
        if self.is_in_cooldown():
            return ZERO

        if self._consecutive_losses < self._threshold:
            return Decimal("1.0")

        # Ogni loss oltre la soglia dimezza ulteriormente
        steps_over = self._consecutive_losses - self._threshold
        multiplier = self._reduction_factor
        for _ in range(steps_over):
            multiplier = multiplier * self._reduction_factor

        # Floor a 0.01 per evitare valori troppo piccoli
        if multiplier < Decimal("0.01"):
            return ZERO

        return multiplier.quantize(Decimal("0.01"))

    def is_in_cooldown(self) -> bool:
        """True se il trading e' sospeso per cooldown."""
        if self._cooldown_start is None:
            return False
        elapsed = time.monotonic() - self._cooldown_start
        if elapsed >= self._cooldown_seconds:
            # Cooldown scaduto: reset completo per ripartire puliti
            self._cooldown_start = None
            self._consecutive_losses = 0
            logger.info("Spiral cooldown scaduto, contatore resettato")
            return False
        return True

    def reset(self) -> None:
        """Reset manuale completo."""
        self._consecutive_losses = 0
        self._cooldown_start = None
        logger.info("Spiral protection resettata manualmente")
        self._schedule_persist()

    # ------------------------------------------------------------------
    # Redis persistence
    # ------------------------------------------------------------------

    def _schedule_persist(self) -> None:
        """Fire-and-forget async persist if event loop is running."""
        if self._redis is None:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist_to_redis())
        except RuntimeError:
            pass  # No event loop — skip (e.g. sync tests)

    async def _persist_to_redis(self) -> None:
        """Persist current state to Redis."""
        if self._redis is None:
            return
        try:
            # Store wall-clock time for cooldown (monotonic resets on restart)
            cooldown_wall: float | None = None
            if self._cooldown_start is not None:
                elapsed = time.monotonic() - self._cooldown_start
                remaining = self._cooldown_seconds - elapsed
                if remaining > 0:
                    cooldown_wall = time.time() + remaining
            data = {
                "consecutive_losses": self._consecutive_losses,
                "cooldown_until": cooldown_wall,
            }
            await self._redis.set(SPIRAL_REDIS_KEY, json.dumps(data))
        except Exception as exc:
            logger.warning("Spiral persist to Redis failed", error=str(exc))

    async def sync_from_redis(self) -> None:
        """Restore state from Redis on startup."""
        if self._redis is None:
            return
        try:
            raw = await self._redis.get(SPIRAL_REDIS_KEY)
            if not raw:
                return
            data = json.loads(raw)
            self._consecutive_losses = int(data.get("consecutive_losses", 0))
            cooldown_until = data.get("cooldown_until")
            if cooldown_until is not None:
                remaining = cooldown_until - time.time()
                if remaining > 0:
                    # Convert wall-clock deadline back to monotonic offset
                    self._cooldown_start = time.monotonic() - (self._cooldown_seconds - remaining)
                else:
                    # Cooldown already expired
                    self._cooldown_start = None
                    self._consecutive_losses = 0
            logger.info(
                "Spiral state restored from Redis",
                consecutive_losses=self._consecutive_losses,
                in_cooldown=self._cooldown_start is not None,
            )
        except Exception as exc:
            logger.warning("Spiral sync from Redis failed", error=str(exc))


class DrawdownEnforcer:
    """Attiva il kill switch quando il drawdown supera la soglia configurata.

    Opera in modo asincrono: confronta equity corrente con il picco
    e chiama kill_switch.activate() direttamente se il drawdown eccede.

    Esempio:
        enforcer = DrawdownEnforcer(kill_switch, max_drawdown_pct=Decimal("10"))
        await enforcer.check(current_equity=Decimal("9000"), peak_equity=Decimal("10000"))
        # → 10% drawdown → kill switch attivato
    """

    def __init__(
        self,
        kill_switch: KillSwitch,
        max_drawdown_pct: Decimal,
    ) -> None:
        self._kill_switch = kill_switch
        self._max_drawdown_pct = max_drawdown_pct

    async def check(
        self,
        current_equity: Decimal,
        peak_equity: Decimal,
    ) -> None:
        """Controlla il drawdown e attiva il kill switch se supera la soglia.

        Args:
            current_equity: Equity corrente del conto.
            peak_equity: Equity massima raggiunta (picco storico).

        Raises:
            ValueError: Se peak_equity <= 0 (dati non validi).
        """
        if peak_equity <= ZERO:
            raise ValueError(f"peak_equity deve essere > 0, ricevuto: {peak_equity}")

        drawdown_pct = (peak_equity - current_equity) / peak_equity * Decimal("100")

        if drawdown_pct >= self._max_drawdown_pct:
            reason = (
                f"Drawdown {drawdown_pct:.2f}% >= limite {self._max_drawdown_pct}% "
                f"(equity={current_equity}, peak={peak_equity})"
            )
            logger.error(
                "DrawdownEnforcer: soglia superata, attivazione kill switch",
                drawdown_pct=str(drawdown_pct),
                max_pct=str(self._max_drawdown_pct),
            )
            await self._kill_switch.activate(reason)
