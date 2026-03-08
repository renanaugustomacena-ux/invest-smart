"""Configurazione base per tutti i servizi Python di MONEYMAKER.

Come il "quadro elettrico" della fabbrica: tutte le impostazioni
vengono caricate dalle variabili d'ambiente, mai da file che
potrebbero finire nel repository. I segreti non devono MAI apparire
nel codice sorgente o nei file di configurazione — come le chiavi
della cassaforte che non si lasciano in giro.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings

_config_logger = logging.getLogger(__name__)


class MoneyMakerBaseSettings(BaseSettings):
    """Impostazioni base condivise da tutti i servizi — il "quadro elettrico"."""

    moneymaker_env: str = "development"

    # Database — il "magazzino" dei dati
    moneymaker_db_host: str = "localhost"
    moneymaker_db_port: int = 5432
    moneymaker_db_name: str = "moneymaker"
    moneymaker_db_user: str = "moneymaker"
    moneymaker_db_password: str = ""

    # Redis — la "memoria veloce" (cache)
    moneymaker_redis_host: str = "localhost"
    moneymaker_redis_port: int = 6379
    moneymaker_redis_password: str = ""

    # ZeroMQ — il "tubo" di comunicazione tra servizi
    moneymaker_zmq_pub_addr: str = "tcp://localhost:5555"

    # Metriche — i "contatori" di produzione
    moneymaker_metrics_port: int = 9090

    # TLS Configuration — il "lucchetto" per le connessioni sicure
    # Default: disabilitato per retrocompatibilità
    moneymaker_tls_enabled: bool = False
    moneymaker_tls_ca_cert: str = ""

    model_config = {"env_prefix": "", "case_sensitive": False}

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> MoneyMakerBaseSettings:
        """Valida che le password siano impostate in produzione."""
        if self.moneymaker_env == "production":
            if not self.moneymaker_db_password:
                raise ValueError(
                    "MONEYMAKER_DB_PASSWORD è obbligatorio in produzione"
                )
            if not self.moneymaker_redis_password:
                raise ValueError(
                    "MONEYMAKER_REDIS_PASSWORD è obbligatorio in produzione"
                )
        elif self.moneymaker_env in ("staging", "development"):
            if not self.moneymaker_db_password:
                _config_logger.warning(
                    "MONEYMAKER_DB_PASSWORD vuoto — accettabile solo in sviluppo"
                )
        return self

    def _ssl_params(self) -> str:
        """Calcola i parametri SSL per la connessione database."""
        if self.moneymaker_tls_enabled:
            params = "?sslmode=verify-full"
            if self.moneymaker_tls_ca_cert:
                params += f"&sslrootcert={self.moneymaker_tls_ca_cert}"
            return params
        if self.moneymaker_env == "production":
            return "?sslmode=require"
        return "?sslmode=prefer"

    @property
    def database_url(self) -> str:
        """Costruisce l'URL di connessione a PostgreSQL con supporto TLS."""
        password = quote_plus(self.moneymaker_db_password)
        ssl_params = self._ssl_params()
        return (
            f"postgresql://{self.moneymaker_db_user}:{password}"
            f"@{self.moneymaker_db_host}:{self.moneymaker_db_port}/{self.moneymaker_db_name}{ssl_params}"
        )

    @property
    def database_url_async(self) -> str:
        """Costruisce l'URL di connessione asincrona a PostgreSQL con supporto TLS."""
        password = quote_plus(self.moneymaker_db_password)
        ssl_params = self._ssl_params()
        return (
            f"postgresql+asyncpg://{self.moneymaker_db_user}:{password}"
            f"@{self.moneymaker_db_host}:{self.moneymaker_db_port}/{self.moneymaker_db_name}{ssl_params}"
        )

    @property
    def redis_url(self) -> str:
        """Costruisce l'URL di connessione a Redis con supporto TLS.

        Quando TLS è abilitato, usa lo schema 'rediss://' (con doppia 's')
        che indica una connessione Redis over TLS.
        """
        auth = f":{quote_plus(self.moneymaker_redis_password)}@" if self.moneymaker_redis_password else ""
        scheme = "rediss" if self.moneymaker_tls_enabled else "redis"
        return f"{scheme}://{auth}{self.moneymaker_redis_host}:{self.moneymaker_redis_port}/0"

    @property
    def is_production(self) -> bool:
        return self.moneymaker_env == "production"

    @property
    def is_tls_enabled(self) -> bool:
        """Ritorna True se TLS è abilitato per le connessioni."""
        return self.moneymaker_tls_enabled
