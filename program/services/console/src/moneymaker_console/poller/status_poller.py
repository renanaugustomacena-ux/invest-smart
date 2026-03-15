"""Background status polling thread for the TUI dashboard.

Queries all services every 2 seconds and caches results for the renderer.
"""

from __future__ import annotations

import threading
from typing import Any

from moneymaker_console.console_logging import log_event


class StatusPoller:
    """Daemon thread that periodically polls service status.

    Thread-safe cache accessed via ``get()``.
    """

    _POLL_INTERVAL_S = 2.0

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def get(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._cache)

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                cache = self._poll_all()
                with self._lock:
                    self._cache = cache
            except Exception as exc:
                log_event("poller_error", error=str(exc))
            self._stop.wait(self._POLL_INTERVAL_S)

    def _poll_all(self) -> dict[str, Any]:
        """Poll all sources — graceful on errors."""
        cache: dict[str, Any] = {}

        # Database
        cache["db"] = self._check_postgres()

        # Redis
        cache["redis"] = self._check_redis()

        # Algo Engine
        cache.update(self._check_brain())

        # MT5 Bridge
        cache["mt5"] = self._check_mt5()

        # Data Ingestion
        cache["data"] = self._check_data()

        # System resources
        cache.update(self._check_system())

        # Kill switch
        cache.update(self._check_kill_switch())

        return cache

    # -- Individual checks --------------------------------------------------

    @staticmethod
    def _check_postgres() -> str:
        try:
            from moneymaker_console.clients import ClientFactory

            return "OK" if ClientFactory.get_postgres().ping() else "NOT CONNECTED"
        except Exception:
            return "ERROR"

    @staticmethod
    def _check_redis() -> str:
        try:
            from moneymaker_console.clients import ClientFactory

            return "OK" if ClientFactory.get_redis().ping() else "NOT CONNECTED"
        except Exception:
            return "ERROR"

    @staticmethod
    def _check_brain() -> dict[str, str]:
        result: dict[str, str] = {
            "brain_state": "NOT CONNECTED",
            "brain_mode": "N/A",
            "epoch": "N/A",
            "loss": "N/A",
            "lr": "N/A",
            "drift": "N/A",
            "maturity": "N/A",
        }
        try:
            from moneymaker_console.clients import ClientFactory

            brain = ClientFactory.get_brain()
            health = brain.get_health()
            if health:
                status = health.get("status", "UNKNOWN")
                result["brain_state"] = status
                details = health.get("details", {})
                result["brain_mode"] = details.get("mode", "N/A")
                result["epoch"] = str(details.get("epoch", "N/A"))
                result["loss"] = str(details.get("loss", "N/A"))
                result["lr"] = str(details.get("lr", "N/A"))
                result["drift"] = details.get("drift", "N/A")
                result["maturity"] = details.get("maturity", "N/A")
        except Exception as exc:
            log_event("poller_brain_error", error=str(exc))
        return result

    @staticmethod
    def _check_mt5() -> str:
        try:
            from moneymaker_console.clients import ClientFactory

            return "CONNECTED" if ClientFactory.get_mt5().is_healthy() else "NOT CONNECTED"
        except Exception:
            return "ERROR"

    @staticmethod
    def _check_data() -> str:
        try:
            from moneymaker_console.clients import ClientFactory

            return "STREAMING" if ClientFactory.get_data().is_healthy() else "NOT CONNECTED"
        except Exception:
            return "ERROR"

    @staticmethod
    def _check_system() -> dict[str, str]:
        result: dict[str, str] = {
            "cpu": "N/A",
            "ram": "N/A",
            "gpu": "N/A",
            "disk": "N/A",
            "symbols": "N/A",
            "regime": "N/A",
            "session": "N/A",
            "last_tick": "N/A",
            "spread": "N/A",
            "positions": "0",
            "exposure": "$0",
            "pnl": "$0",
            "max_dd": "0%",
            "spiral": "INACTIVE",
            "circuit": "[ARMED]",
            "calendar": "N/A",
        }
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            result["cpu"] = f"{cpu:.1f}%"
            result["ram"] = f"{mem.used / (1024**3):.1f} / " f"{mem.total / (1024**3):.1f} GB"
            result["disk"] = f"{disk.percent:.1f}% used"
        except ImportError:
            log_event("poller_system_warning", reason="psutil not installed")

        try:
            import subprocess

            r = subprocess.run(
                ["rocm-smi", "--showtemp", "--csv"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if r.returncode == 0:
                lines = r.stdout.strip().splitlines()
                if len(lines) > 1:
                    result["gpu"] = lines[1].strip()[:40]
            else:
                result["gpu"] = "ROCm N/A"
        except Exception:
            result["gpu"] = "N/A"

        return result

    @staticmethod
    def _check_kill_switch() -> dict[str, str]:
        try:
            from moneymaker_console.clients import ClientFactory

            redis = ClientFactory.get_redis()
            data = redis.get_json("moneymaker:kill_switch")
            if data and data.get("active"):
                return {"kill_switch": "ACTIVE"}
            return {"kill_switch": "INACTIVE"}
        except Exception as exc:
            log_event("poller_kill_switch_error", error=str(exc))
            return {"kill_switch": "UNKNOWN"}
